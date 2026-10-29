# J13: Headless runs on the virtual display

Phase 1, job 13: every watcher launch puts the game window on the PC's virtual display and never on one of Liam's real monitors,
fail closed, so agents can run the game while Liam uses the PC. 4K now; 1080p and 1440p as soon as the virtual display offers them.
The window position never leaks into Liam's preferences file. Measured over whole launches, not sampled.

Model: Opus, reason: DLL and Windows native work (window and D3D9 hooks, DPI, display topology) (D15). Budget about 250 tool calls;
at the cap, stop, commit, report what is left. At most 2 subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J13`). Read `docs/DECISIONS.md`, `docs/plans/PLAN.md` (phase 1), `proxy/README.md`
  (build, deploy, "Hooks", "Dev control channel"), `harness/README.md`, and the reports of J2 and J3 (`jobs/J2/report.md` open
  questions 1 and 2, `jobs/J3/report.md` open question 3).
- Evidence base, read only (`--add-dir ../empire-remastered`; never edit there). **Port the design, not the size:** Empire's
  `rml_mod/src/headless.cpp` is 1,636 lines because it grew features this job does not want.
  - `rml_mod/docs/headless_virtual_display.md`: section "The design", "Fail closed + the engine's mode list" (why the device followed
    the primary under DXVK, and the `IDirect3D9` mode hooks that fixed it), the visibility gate, `headless_status.json`.
  - `rml_mod/src/headless_guard.h` and `src/tests/headless_guard_test.cpp`: the display-topology guard as pure logic (cloak first,
    re-resolve by adapter name, move, verify, uncloak after a settle; layout signature).
  - `rml_mod/docs/runs/20261020_headless_fix/README.md` and `20261022_headless_display_change/README.md`: the two incidents (fell back
    to a real monitor for ~75 s; window a quarter on a real monitor for 0.3-1.3 s after Windows moved the virtual display).
  - `rml_mod/tools/remote/headless_verify/win_probe.ps1` (whole-launch window probe), `rml_mod/tools/remote/vdisplay_mode.ps1`,
    `rml_mod/tools/remote/prefs_guard.sh` (Liam's prefs kept byte-identical around headless launches).
  - `docs/learnings/LEARNINGS_HARNESS.md` section "Headless runs and the virtual display", and lines on display topology and the
    start-up `c0000374` (topology-dependent crash rate: record the topology on every launch).
  Do NOT port: FSR/upscaling, the overlay, input bridging or hotkeys, `force_foreground` start-up hacks, refresh-rate switching for perf
  runs, audio muting (Empire's mute left the game muted for Liam: out of scope here), or any `display=<n>` / `\\.\DISPLAYn` selector.

## Target facts
Read 2026-10-29 on `officepc` (`harness/core/vdisplay_probe.ps1 -Test 1920x1080,2560x1440,3840x2160`, exit 6); check them again.
- Displays change between sittings. Today: `\\.\DISPLAY1` 3840x2160@240 primary (NVIDIA), `\\.\DISPLAY2` Dell 2560x1440@144 at
  -2560,327, `\\.\DISPLAY10` "Virtual Display Driver" 3840x2160@60 at **3839,2160**. Fact `napoleon.display.vdd_modes` (2026-10-29,
  J2) recorded the Dell as primary and no MSI. The GDI number of the virtual display is not stable (Empire saw 20, 21, 23).
- The virtual display offers **only 3840x2160** (60 and 240 Hz); 1920x1080 and 2560x1440 are `DISP_CHANGE_BADMODE`. Liam's
  `vdd_settings.xml` edit (J2 open question 1; the probe prints it) is still not done.
- `preferences.script.txt` (fact `napoleon.config.preferences_format`, UTF-16LE with BOM) holds `x_res`, `y_res`, `x_pos`, `y_pos`,
  `gfx_fullscreen` (true today), `fix_res`, `fix_window_pos`. Whether and when the game writes `x_pos`/`y_pos` back is not known.
- Fact `napoleon.dxvk.menu_display_mode` (open): on DXVK the menu looked borderless, not exclusive. Fact
  `napoleon.crash.res_switch_stack_overflow` (J16): switching resolution in game to 4K kills the game; launching straight into 4K works.
  Headless runs never switch resolution in game.
- The proxy hooks through the exe's import table and D3D vtable slots, never MinHook (`proxy/core/hooks.cpp`, J3 decision).

## Decisions already made for this job
- **Ask Liam once, at the start,** to make the `vdd_settings.xml` edit (paste the probe's text). Do not wait for it: build and prove
  4K first; run the 1080p and 1440p checks in the same sitting if the modes exist by then, otherwise report them as open with the
  code path host-tested. Agents never edit the driver's settings or reload the driver.
- Code: pure decision logic in `proxy/core/display_guard.h` (no Windows headers, host-tested like `guard.h`), the driver in
  `proxy/core/headless.cpp`; anything Napoleon-specific in the adapter. Both are core candidates (J12 moves them).
- Hooks: through the existing `IatHook` / `VtableHook` machinery. First establish which user32 calls the exe imports for its window
  (`CreateWindowExA/W`, `ShowWindow`, `SetWindowPos`, `MoveWindow`, `SetWindowLong*`, `ChangeDisplaySettings*`, `EnumDisplay*`,
  `MonitorFromWindow`, ...) and record them as an engine fact. The `IDirect3D9` mode queries (`GetAdapterModeCount`, `EnumAdapterModes`,
  `GetAdapterDisplayMode`, `GetAdapterMonitor`) and `CreateDevice` are vtable hooks on the object returned by `Direct3DCreate9`.
- **Target selection** is by adapter or monitor name ("Virtual Display Driver", from the adapter config, overridable) plus an exact
  size match with the wanted back buffer, never by index or `DISPLAYn` and never by assuming an origin. Rects in physical pixels
  (per-monitor DPI aware V2 around every query and move).
- **Fail closed, no fallback:** under headless there is no path that puts the window on a real monitor. No target, a target the wrong
  size, or a back buffer that does not match: hide every window of the process, write the status, exit with one documented code.
- **Windowed borderless on the target** (the engine's exclusive fullscreen on a non-primary virtual display is not attempted); the
  headless profile sets what that needs in the prefs.
- The window never takes the foreground or activation (`SW_SHOWNA`, no `SetForegroundWindow`), and the game keeps rendering and
  answering the dev control channel while it is not foreground. Measure first whether Napoleon pauses or stops presenting when
  unfocused; only if it does, swallow the deactivation (Empire's `swallow_activation`), logged.
- Headless is the watcher's default for every launch once this job lands; a visible launch needs an explicit `visible=1` and is only
  for sittings with Liam present. The proxy key's own default stays off, so Liam's normal play is unchanged.
- The virtual display's mode (1080p / 1440p / 4K) is set before a launch by a harness tool that can only ever change the virtual
  display (refuses any other target, checked by a host test) and restores the previous mode afterwards; Liam's monitors are never
  touched.

## Deliverables
1. **Target resolution** at `Direct3DCreate9`, before the engine makes its window: the monitor list logged every launch (name,
   adapter, rect, DPI, primary), the chosen target and why, or a refusal.
2. **Mode list from the target:** the `IDirect3D9` mode hooks answer from the target's modes on every adapter, so the engine sizes its
   device for the virtual display whatever the primary is (Empire's DXVK finding: every adapter reports the primary). Proven in the
   topology where the primary's size differs from the wanted size.
3. **Placement and visibility gate:** the game window is created on the target (never visible first at 0,0); show, move, style and
   minimise calls that would make a game window visible outside the target are refused or rewritten, and a post-check after each and at
   every Present hides any window found visible elsewhere. The 1x1 helper window, if any, is left alone and logged.
4. **Topology guard:** on any sign of a display change (`WM_DISPLAYCHANGE`, layout signature change, window off target) the window is
   cloaked first (`DWMWA_CLOAK`), the target re-resolved by name, the window moved and verified, then uncloaked after a settle; target
   gone means refusal. Pure logic in `display_guard.h` with host tests covering both of Liam's topologies, a virtual display that moves,
   one that disappears, and the corner-touching origin seen today (3839,2160).
5. **Status file** `napoleon_remastered\headless_status.json` (`pid`, `state` starting | target_ok | on_virtual | refused, `detail`,
   `target`, window/client/back-buffer sizes, `exit_code`), in the adapter's heartbeat files. The watcher's `launch` waits for
   `on_virtual` (or reports `refused` with the detail) and a pre-launch check refuses a headless launch when there is no unique virtual
   display at the wanted size (extend `vdisplay_probe.ps1`, do not write a second probe).
6. **Prefs kept clean:** a headless profile changes only the keys headless needs (`x_res`, `y_res`, `gfx_fullscreen`, and what the
   measurement shows) on top of Liam's current prefs, so runs use his real graphics settings; that needs an overlay style for the
   UTF-16LE prefs format in the watcher's profiles (today `style: none`). After every run, crashed and refused ones included, the
   restore leaves `preferences.script.txt` byte-identical (sha256 checked; the watcher already restores; prove it). A check warns if
   Liam's prefs ever carry an `x_pos`/`y_pos` inside the virtual display's rect.
7. **Whole-launch window probe** in the harness: samples from process start to exit, re-reads the monitor list every sample, and
   reports the longest time any game window was visible on a real monitor, visible-off-target count, cloaked time and monitor changes.
   Every PC launch in this job runs under it.
8. **Virtual display mode tool** (deliverable above) with its host test, and the watcher `launch` argument that uses it.
9. Registries: `config_keys` rows for every new key (default, release value, owner), `tools` rows, `engine_facts` for every measured
   claim (window imports, whether the game writes `x_pos`/`y_pos` and when, background rendering, the modes, the exit code) with date and
   run id. `proxy/README.md` and `harness/README.md` updated (one owner per topic; no Empire prose copied).

## PC test
Through the watcher only (`harness/core/job.sh`), every launch under the window probe, `dev.skip_intro=1`, Liam's prefs sha recorded
before and checked after each launch. Ask Liam before the sitting; he does not need to watch, but must not be surprised.
a) Visible baseline, current build: record where the window goes today.
b) 4K headless: 5 launches to the main menu and 3 into `battle:land_small` via autostart, plus a warm reset and dev control commands
   while Liam's foreground app keeps focus. Pass: 0 ms on a real monitor in every launch, `on_virtual`, frames presented in the background.
c) Refusal: wanted size missing on the virtual display (e.g. ask for 1440p before the edit) and a forced no-target case: the game
   refuses, nothing is shown anywhere, the watcher reports it, prefs byte-identical.
d) Topology: move the virtual display's origin with the mode tool (the only display change an agent may make) mid-run: cloaked, moved,
   uncloaked, 0 ms on a real monitor. A real-monitor change (Liam switching primary or unplugging the MSI) only if Liam offers to do it.
e) 1080p and 1440p: the same as b) at each size, if the modes exist.
Results in a dated run report under `proxy/runs/` with run ids, the probe's numbers per launch, and the topology at the time.

## Kill criteria
- Any game window seen on a real monitor during a launch with the guard in place: stop launching, keep the probe output and logs,
  report the timeline from the log; do not retry until the cause is understood.
- The window calls do not go through the exe's import table (an inline hook would be needed): stop and report the evidence; that
  needs Liam's decision against the J3 hooks rule.
- An intermittent start-up crash with headless on: collect WER dumps and the topology, stop after the second, report.
- Liam's prefs not byte-identical after a run: stop, restore from the watcher's snapshot, report.

## Finish
Write `jobs/J13/report.md`: what exists, how an agent launches headless and reads the status, the test table with run ids and probe
numbers per launch, the prefs shas, deviations from this brief and why, what moves to the core in J12, open questions (including the
1080p/1440p state if the modes were still missing). Then `wsc reg set jobs J13 status=review report=jobs/J13/report.md`.
