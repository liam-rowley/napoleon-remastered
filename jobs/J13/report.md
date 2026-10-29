# J13 report: headless runs on the virtual display

Branch `job/J13`, 2026-10-29, one PC sitting: `proxy/runs/20261029_j13pc` (17:37-18:53Z, 35 launches). Built by Opus 5.5 as briefed, the
harness half by one Sonnet subagent against a fixed contract (status file, ini keys, exit code, marker). The PC ends on proxy kit
`kit_20261029T183743Z_8565a96e131c` (build `8565a96e131c`, headless off by default, every dev key off) and watcher kit
`harness_20261029T184644Z_8f2625b5715e` (watcher 1.0.1); the virtual display back at 3840x2160 at 3839,2160.

## What exists

| deliverable | state | where |
|---|---|---|
| 1 target resolution | done: monitor list logged every launch (device, adapter, monitor, physical rect, DPI, primary); target = the one non-primary display named `headless.display_name` at exactly `headless.size`; refusal with the reason otherwise | `proxy/core/display_guard.h` `SelectTarget`, `proxy/core/headless.cpp` `ResolveLocked` |
| 2 mode list from the target | done: `IDirect3D9` slots 6/7/8/15 answer from the target on every adapter (the backend said 116 modes, the engine got the target's 6); `CreateDevice`/`Reset` refuse fullscreen or a wrong size; a windowed tiny device (the battle loader's 1x1) passes | `headless.cpp`, `GateDevice` |
| 3 placement and visibility gate | done: windows created hidden, borderless, no-activate, placed on the target, shown `SW_SHOWNA`; geometry owned by the guard; minimise = hide; post-check after each hooked call and at every Present; `ChangeDisplaySettingsW` never applied; `MessageBoxW`/`DialogBoxIndirectParamW` never shown; `SetFocus` dropped while another process has the foreground; DirectInput non-exclusive and foreground-only | `headless.cpp`, `GateCreate`/`GateShow`/`GatePos`/`GateStyle`/`GateCoopLevel` |
| 4 topology guard | done: metrics poll (~4 ms), layout signature, live target rect, WM_DISPLAYCHANGE/DPICHANGED/SETTINGCHANGE/DEVICECHANGE; cloak first, re-resolve by name, move, verify, uncloak after `headless.settle_ms`; no target for `headless.refuse_grace_ms` = refusal. Host tests: both of Liam's topologies, a moving, vanishing, returning and resized virtual display, the 3839,2160 corner origin (millisecond simulation) | `Decide`, `proxy/tests/test_display_guard.cpp` (193 checks) |
| 5 status file + watcher wait + pre-launch check | done: `napoleon_remastered\headless_status.json` (in the heartbeat files); `launch` waits for `on_virtual` (or fails with the refusal detail; no status in time kills the game); `vdisplay_probe.ps1 -Check -Size` before every headless launch | `harness/core/watcher.ps1` `Launch-Job`, `Headless-*` |
| 6 prefs kept clean | done: overlay style `prefs` (UTF-16LE, value replaced in place) on top of Liam's current prefs: `x_res`, `y_res`, `gfx_fullscreen false`, and muted (`sound_master_enabled false`, `sound_master_volume 0`, Liam's request); restore byte-identical after all 35 launches including refused and killed ones; warning when the base prefs carry `x_pos`/`y_pos` inside the virtual display | `harness/napoleon/adapter.json` `headless`, watcher `Apply-PrefsOverlay` |
| 7 whole-launch window probe | done: every launch (headless and visible), 10 ms samples from before the start to the exit, monitor list re-read every sample; longest/total ms on a real monitor, off-target count, cloaked ms, monitor changes, cursor recentres, game-foreground ms | `harness/core/win_probe.ps1` |
| 8 virtual display mode tool | done: `vdisplay_probe.ps1` `-Check`/`-Set`/`-Origin`/`-Restore`, only on the display selected by name (unit-tested with fake topologies); puts back a cursor Windows recentred; watcher `size=WxH`, mode kept for the whole lock and restored at release | `harness/core/vdisplay_probe.ps1` |
| 9 registries and docs | done: 5 `config_keys` (`headless.*`), tools rows (`win_probe`, `vdisplay_probe`, `exe_info`), 8 engine facts (window imports, create request, SetFocus, background render, helper device, prefs at exit, DXVK mode list, vdd modes updated); `proxy/README.md` "Headless", `harness/README.md` "Headless launch", "Display tool", "Window probe" | `registries/` |

**How an agent launches headless and reads the status** (`harness/README.md`): take the lock, apply a profile (e.g. `dev-dxvk`), then
`launch owner=<you>` (4K) or `launch owner=<you> size=1920x1080`; the job ends ok only at `on_virtual` and names the probe folder
`runs\<utc>_winprobe`. Read `napoleon_remastered\headless_status.json` (`state`, `detail`, `target`, sizes) and, after the exit,
`winprobe.json`. `visible=1` only with Liam present.

## Tests

PC: `proxy/runs/20261029_j13pc/README.md` (per-launch table with launch ids and probe numbers). In short: (a) the visible build puts the
window on the primary (112.7 s longest on a real monitor); (b) 5 + 3 headless 4K launches and (e) 8 at 1080p + 1 + 8 at 1440p: **0 ms on
a real monitor in every headless launch**, `on_virtual` at the size, no activation, frames presented and ctl/autostart/warm reset working
in the background; (c) a size the driver does not offer is refused by the watcher before the start, a forced no-target is refused by the
proxy (exit 2160, 0 ms shown); (d) the virtual display moved mid-run and back: cloaked, relocated in 85 ms, uncloaked after the settle, 0 ms
on a real monitor. Liam's prefs sha256 `83b9b32b2b738ebcafa4910a9b3b6f0c69b9a06e3e6270fb55d6e51bdee2cea7` before and after every launch.
Host: `proxy/tools/build.sh --docker all` (all 7 suites pass, `test_display_guard` 193); harness unit 40 passed; integration 25 passed
(subagent, full suite) and the 6 headless/display cases again after the last watcher change.

## Deviations from the brief, and why
- **Muted** (out of scope in the brief): Liam asked during the sitting. Done through the prefs overlay, so the byte-identical restore returns
  his values and nothing can stay muted (Empire's per-app mixer mute could).
- **The virtual display's mode is restored when the lock is released, not after every launch**: each mode change makes Windows move Liam's
  real cursor to the centre of his primary (measured, 2026-10-29); the display tool also puts a recentred cursor back.
- **Additions not in the brief, from the sitting**: `SetFocus` dropped (it activated the window), DirectInput forced non-exclusive and
  foreground-only (hardening; the engine already asks for `0x16`), a tiny windowed helper device allowed, probe fields
  `cursor_recentres` and `game_foreground_ms`.
- **Left out of Empire's guard**: the blocked-poll watchdog and the WndProc chain ping (no other module subclasses the window here; port the
  design, not the size). `headless.cpp` is about 700 lines against Empire's 1,636.
- **The display tool keeps the name `vdisplay_probe.ps1`** although it now applies modes (renaming needed the kit list in `pc_deploy.py`
  changed too; deferred to J12, which moves it anyway).
- Baseline (a) ran on the J13 build with `visible=1` (headless off), which is the behaviour of the build before it.
- The 1080p menu launches ran before the probe recorded cursor recentres; the 1080p battles and all 1440p launches after the fix have it.
- **Kill criterion hit once** (prefs not byte-identical, `d_0_killed_by_orphan_loop`): an orphaned scratch loop of mine had overlaid the prefs
  of its own launch; the watcher's snapshot restored them byte-identical at once. Cause understood (run README "Incident") before going on.
- Tool calls: about 250 including the sitting; two Sonnet subagent runs counted as one agent.

## What moves to the core in J12
`proxy/core/display_guard.h`, `proxy/core/headless.cpp`, `proxy/tests/test_display_guard.cpp` (game-agnostic, linted for game names);
`harness/core/win_probe.ps1`, `harness/core/vdisplay_probe.ps1` (rename to `vdisplay.ps1` then), and the watcher's headless launch flow (it
reads everything game-specific from the adapter's `headless` block).

## Open questions
1. **ps1 watcher jobs report `ok exit=0` when the script they call exits non-zero** (the display tool's "bad arguments" looked ok in run
   `d_1`). The watcher should propagate `$LASTEXITCODE` of the last native/script call; a harness fix for a later job.
2. A real-monitor topology change (Liam switching the primary or unplugging a monitor) was not tested: the brief allows it only if Liam
   offers. The host simulation covers the Empire incident (3 ms on a real monitor before the cloak, under one 4 ms poll).
3. The display tool's cursor put-back has host tests but was not seen acting on the PC (no recentre happened in the two switches after the
   fix while the probe ran). If Liam still sees jumps, the probe's `cursor_recentres` and the tool's `cursor:` output line will show it.
4. `napoleon.dxvk.menu_display_mode` stays open: headless always runs windowed borderless, so it neither confirms nor refutes exclusive
   fullscreen through DXVK.
5. Headless at 1080p/1440p sizes the DXVK swapchain to the virtual display only; a performance baseline (J23) should state the size and that
   Liam may be using the PC.
