# Run 20261030_j16dumps: what kills the game at an in-game resolution change (J16 deliverable 1)

officepc, 2026-10-30, read-only: no launch. Dumps copied from `%LOCALAPPDATA%\CrashDumps\napoleon_remastered\` to
`C:\napoleon_remastered_pc\_scratch\j16\dumps\` (sha256 in `SHA256SUMS` there; not committed). Read with
`proxy/tools/dump_read.py` (cdb x86 from WinDbg 1.2610.1001.0, Microsoft symbol server for system DLLs). DXVK source: tag `v3.1.1`
(the pinned build, `d3d9_dxvk.dll` sha256 `265888c3...`). Event log: Application Error 1000 entries, one per dump.

## Classification

| dump (pid) | written (UTC) | uptime | event log fault | what it is |
|---|---|---|---|---|
| `11252` (0x2BF4) | 10-29 11:18:57 | 1:34 | ntdll+0x827cd AV | **J16**: the window-proc cycle below; not a hang dump (WER after a real AV, not `TerminateProcess`) |
| `4556` (0x11CC) | 10-29 11:25:14 | 2:28 | ntdll+0x827cd AV | **J16** again, same cycle (no watcher run at that time: a manual launch, not identified further) |
| `1824` and `(1).1824` (0x720) | 10-29 10:05:13 / :19 | 0:12 / 0:18 | KERNELBASE+0x16bae4 | not J16: the game's own `RaiseException` 12 s after start, 14 KB of stack used, no DXVK frames on the stack |
| `30708` (0x77F4) | 10-30 14:29:54 | 0:03 | ntdll c0000374 (heap) | not J16: heap corruption 3 s after start, before DXVK loads (`d3d9` loaded, no `d3d9_dxvk`), in `CoreMessaging` on an input thread |
| `3248` | 10-29 10:01 | | d3d9_dxvk+0x10e2d7 AV | rotated out (WER `DumpCount=5`) before this job; event log: NVIDIA "OpenGL out of memory" 3 s earlier, DXVK log `Memory allocation failed` (watcher run `20261029T100115Z_hang`): address-space exhaustion, not J16 |

The 09:34 crash after J3's fix (`ntdll+0x827cd`, `proxy/runs/20261029_4kcrash`) has the same fault offset as `11252` and `4556`.

## The two J16 dumps

Main thread (the DllMain thread) in both; ESP past the 1 MB reservation:

| dump | StackBase | StackLimit | ESP | used | ESP - limit | frames |
|---|---|---|---|---|---|---|
| `11252` | `0x02300000` | `0x02201000` | `0x02200f28` | 1,044,696 B | -216 | 8,528 |
| `4556` | `0x00b00000` | `0x00a01000` | `0x00a00f08` | 1,044,728 B | -248 | 8,520 |

**Repeating cycle, period 8, 1,060 repeats in both** (frame owners: user32 6,369, opengl32 1,062, d3d9_dxvk 1,061):

```
opengl32!wglWndProc
user32!_InternalCallWinProc / UserCallWinProcCheckWow / CallWindowProcW
d3d9_dxvk+0x71d06 (return address inside D3D9WindowProc; nearest export Direct3DCreate9On12Ex)
user32!_InternalCallWinProc / UserCallWinProcCheckWow / CallWindowProcW
-> opengl32!wglWndProc ...
```

- **Entry side** (below the cycle): `user32!DispatchClientMessage` <- `KiUserCallbackDispatcher` <- `user32!PeekMessageW` <-
  `gameoverlayrenderer` <- `Napoleon`: the game's message pump delivered a sent message to its window. The cycle starts at the first
  message after the switch, not inside `Reset`/`CreateDevice`.
- **Fault side** (above the cycle): the cycle hits the guard page (`STATUS_STACK_OVERFLOW`), the dispatcher runs
  `KERNELBASE!UnhandledExceptionFilter`, whose `LoadLibraryExW` is hooked by `gameoverlayrenderer` (Steam overlay), which calls
  `GetModuleHandleW` -> `ntdll!LdrpLogInternal` -> `_woutput_l`, which writes past the limit: the AV in the event log. No proxy
  frame anywhere on the stack: the proxy's handlers are not involved (J3's record-only path never ran here).
- Loaded graphics modules: `d3d9` (proxy), `d3d9_dxvk`, `vulkan-1`, `nvoglv32` 32.0.16.1714 (NVIDIA's OpenGL and Vulkan ICD),
  `nvgpucomp32`, `opengl32` 10.0.26100.9549, **`amdvlk32` 32.0.13018.6** (an AMD Vulkan ICD from a 2024-12 AMD driver), `dxgi`,
  `gameoverlayrenderer`.

## Mechanism (DXVK 3.1.1 `src/d3d9/d3d9_window.cpp`, `d3d9_swapchain.cpp`)

1. `EnterFullscreenMode` -> `HookWindowProc`: DXVK subclasses the game window; its map keeps the game's proc as `proc`.
2. Another module subclasses the window on top of DXVK: `opengl32!wglWndProc`, whose saved previous proc is DXVK's.
3. On the switch, DXVK calls `ResetWindowProc` (old swapchain destroyed, or `HookWindowProc` again on a new fullscreen swapchain):
   it reads `GWLP_WNDPROC`, finds `wglWndProc`, not its own, so it **does not unhook** and only erases its map entry.
4. `HookWindowProc` subclasses again: `SetWindowLongPtr` returns `wglWndProc`, which DXVK saves as its previous proc. Now DXVK ->
   `wglWndProc` -> DXVK: the next message recurses until the stack is gone (1,060 rounds at ~985 bytes each).

A fullscreen-to-fullscreen `Reset` (`changeFullscreen` false) does not rehook, so the trigger is a device recreate or a
windowed-to-fullscreen `Reset`; the 11:17 launch's DXVK log was not kept (manual launch, the folder was later uninstalled), so which
of the two this game uses is open. Launching straight into 4K hooks once and never meets step 3: it works (J3 run `20261029T094029Z-p16232`).
Upstream DXVK `master` has the same `ResetWindowProc` (checked 2026-10-30): a newer DXVK does not fix it.

Not yet shown on the PC (needs the A/B sitting, J16 report): which module makes opengl32 subclass the window (likely `nvoglv32` as the
Vulkan ICD; `amdvlk32` is a candidate too), and that vanilla d3d9 survives the switch.

## Fix built (not yet run on the PC)

`proxy.dxvk_wndproc_fix` (default on): `core/dxvk_wndproc.cpp` points only `d3d9_dxvk.dll`'s four user32 import slots
(`GetWindowLongW/A`, `SetWindowLongW/A`, which the pinned DLL imports) at a guard. When DXVK reads `GWL_WNDPROC` on a window it
hooked and a foreign proc is on top, the guard reports DXVK's own (`core/wndprocpolicy.h`), so DXVK restores the game's proc; the
foreign layer is dropped and the log names its module. Host test `proxy/tests/test_wndproc.cpp` models DXVK's hook code: unguarded,
the J16 sequence leaves the cycle; guarded, the chain ends at the game's proc after any number of switches.

## Next: the PC sitting (blocks J16 deliverables 2 and 3)

Headless launches cannot reproduce this: `core/headless.cpp` refuses an exclusive-fullscreen device and any back buffer other than the
target's size, and the switch needs both. Every arm is a `launch owner=<you> visible=1` with Liam present (the game shows on his
monitor; he does the switch by hand if `ctl lua` cannot, at most 3 tries). Kit a build of `job/J16`, profile at 2560x1440 fullscreen,
WER LocalDumps on, at most 3 launches per arm, `proxy.minidump=2`:

| arm | config | expect |
|---|---|---|
| a | current kit, `proxy.dxvk_wndproc_fix=0` | cycle and crash (reproduces J16 on the record) |
| b | `proxy.enabled=0` (system d3d9) | survives: the bug is DXVK's, not the game's |
| c | `=0` and `VK_LOADER_DRIVERS_DISABLE` for the AMD ICD | tells whether amdvlk32 matters (expect: no, opengl32 is NVIDIA's) |
| d | `=0`, 1920x1080->2560x1440, 2560x1440->1920x1080, 3840x2160->2560x1440 | any fullscreen re-entry, not 4K |
| fix | `proxy.dxvk_wndproc_fix=1` (default): 2560 and 4K launches, switch both ways 3x | survives; proxy.log shows `wndproc guard: ... (opengl32.dll) above DXVK's proc` |

Proxy log lines to read: `backend: wndproc guard on DXVK's imports: 4 slots` at start, then `DXVK hooked/restored window` per switch.
Also check after the fix run that input still reaches the game and the Steam overlay (Shift+Tab) still opens.
