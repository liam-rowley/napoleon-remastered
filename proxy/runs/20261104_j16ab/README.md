# Run 20261104_j16ab: the J16 A/B arms (J16 deliverable 2)

officepc, 2026-11-04, Liam present (visible launches, he switched the resolution by hand in Options > Graphics). Lock owner `j16`,
session `ed0f955b-6885-5035-b233-0a11a4c51d0c`. Kit `kit_20261104T175716Z_382e189740a6` (branch `job/J16` at `382e189`, whose DLL inputs
equal `main` 0271d10: DLL build `cb34c06baf42`, sha256 `b9c2bc2b7c38...`, DXVK 3.1.1 `d3d9_dxvk.dll` sha256 `265888c31ca7...`), installed
with `pc_deploy.py install`, `dev.skip_intro=1` and `proxy.minidump=2` set, uninstalled afterwards (game folder identical to the
pre-install snapshot, 1564 files; exe vanilla sha1 `9aebcd21...`). The guard (`proxy.dxvk_wndproc_fix`) is not in this build: it moves
to warscape-core W39, so every DXVK arm here is the unguarded case. Start state for every launch: Liam's prefs, 3840x2160 fullscreen.

Dumps (WER LocalDumps, full, `DumpCount=5`) copied to `C:\napoleon_remastered_pc\_scratch\j16\ab\` (not committed); the five older dumps
that were in the WER folder are kept in `_scratch\j16\prior_dumps_20261103\`. Read with `dump_read.py` (branch history `95f5a1e`) and
cdb x86. The last arm's proxy and DXVK logs are in `C:\napoleon_remastered_pc\_to_delete\uninstall_20261104T180649Z\napoleon_remastered\`.

## Arms

| arm | config | switch (by hand) | watcher launch | outcome | dump: exception, cycle |
|---|---|---|---|---|---|
| a | DXVK (`proxy.enabled=1`, backend dxvk) | 3840x2160 -> 2560x1440 fullscreen | `20261104T175807Z` (pid 27124) | instant hang, then crash 29 s after start; DXVK's log ends after the 2560x1440 swapchain | `27124`: `c000041d` in `user32!UserCallWinProcCheckWow`, 1,036,308 B of stack, period-8 cycle `opengl32!wglWndProc` <-> `d3d9_dxvk` window proc, 1,060 repeats, entered from `PeekMessageW` |
| b | `proxy.enabled=0` (proxy log: `system d3d9 loaded from C:\WINDOWS\system32\d3d9.dll`) | 3840x2160 -> 2560x1440 -> 3840x2160 | `20261104T180058Z` (pid 18660) | **survives both ways**; clean exit, no dump | none |
| c | DXVK with the AMD ICD hidden | not run | | skipped: nothing in the proxy or watcher sets a variable for the game process alone (a machine-wide `VK_LOADER_DRIVERS_DISABLE` would be needed), and `amdvlk32` has no frame in any of the five J16 cycles | |
| d | DXVK | 3840x2160 -> 1920x1080 fullscreen | `20261104T180308Z` (pid 30100) | the switch completes (DXVK log: swapchain 1920x1080), the confirm/cancel popup shows, then the crash | `30100`: `c000041d`, same cycle, 1,064 repeats, entered from `DispatchMessageW` |
| e | DXVK | fullscreen -> windowed at 3840x2160, not confirmed; the 15 s timer reverts to fullscreen | `20261104T180443Z` (pid 28404) | windowed works (DXVK: `ResetSwapChain` Windowed true, buffer 3862x2216, a window larger than the 3840x2160 screen) but the mouse does not reach the game, so Liam cannot confirm; the revert (`ResetSwapChain` Windowed false, 3840x2160) crashes | `28404`: `c000041d`, same cycle, 1,061 repeats, entered from `PeekMessageW` |

## What the arms settle
- **The bug is DXVK's, not the game's or the driver's:** vanilla d3d9 survives the same switch both ways (arm b). The brief's second
  kill criterion does not apply, so the fix stays in the proxy.
- **Any fullscreen re-entry triggers it, not 4K:** 4K to 1440p (a), 4K to 1080p (d) and windowed to fullscreen (e) all end in the same
  window-proc cycle as the 2026-10-29 dumps (`20261030_j16dumps`). This matches that report's mechanism: DXVK re-subclasses the window
  in `EnterFullscreenMode` over `opengl32!wglWndProc` and saves it as its previous proc.
- **No in-game workaround:** windowed mode cannot be reached and kept, since the window comes up larger than the screen without mouse
  input and the revert to fullscreen crashes. Until the guard ships, the only safe route is to change the resolution in the
  launcher or prefs and restart.
- **For the fix arm** (after W39 reaches napoleon in a pin bump): the same three switches with `proxy.dxvk_wndproc_fix=1`, plus a check
  that mouse input still reaches the game after a fullscreen-to-windowed switch (arm e's lost input may be the same chain fault or the
  oversized window; the fix arm tells which).
