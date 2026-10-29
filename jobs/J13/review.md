# Review of J13 (Headless runs on the virtual display)

## Round 1 (2026-10-29, branch `job/J13` at 06d3fe9)

Reviewer: a fresh Opus chat (session `f344a376-5999-4e57-84c1-8b8b6727e7e5`) that built none of the branch (builder:
`60013e38-0823-4be3-875e-42ea3e457b97`). Checked against `jobs/J13/brief.md` and `jobs/J13/report.md`.

**Verdict: merge.** Every deliverable is present, and the PC evidence backs the central claim: 0 ms on a real monitor in each of the
32 headless launches, `on_virtual` at 4K, 1440p and 1080p, refusals that show nothing, a mid-run display move handled cloaked, and
Liam's prefs byte-identical after every launch. The deviations are all named in the report. Two should-fix items remain. Both are
gaps in hardening on code paths Napoleon does not exercise, and both need a PC run to prove the fix, so they move to J12. J12 moves
this code to the core and has to re-prove it on the PC anyway (see "Should-fix").

### Machines
- `wsc gates` (at 06d3fe9, this worktree): 11 ok, 1 warn (`hooks`: this clone's hooksPath is absolute, a local setting), 90 host tests.
- `harness/tests/Test-Unit.ps1`: 40 passed, 0 failed, including the display tool's static name-only selection and the marker refusal.
- `proxy/tools/build.sh --docker all`: not completed locally. The container stalled in `apt-get update` (no network progress for 21
  min) and never reached the build, so I stopped it. CI's `proxy` job (build, host tests including `test_display_guard`, wine smoke)
  passed on 06d3fe9 (run 40935357945, with `gates` and `harness-windows`), and the merge waits for it again on the review commit.

### Claims re-checked independently (2026-10-29, this session)
- Run `proxy/runs/20261029_j13pc`: for `a_visible`, `c_no_target`, `d_topology_move` and `e1440_bt_1`, the `winprobe.json`,
  `headless_status.json` and prefs sha lines in `raw/` match the README table: 112745 ms on the primary for the visible baseline; 0 ms
  for the others; `refused` with exit 2160 and no window for the no-target case; 1352 ms cloaked and 2 monitor changes for the move;
  2560x1440 back buffer and window at 3839,2160. The prefs read `83b9b32b…` before and after every one of them.
- `c_size_not_offered`: the watcher refused 1280x720 before starting the game. CDS_TEST said `DISP_CHANGE_BADMODE` and nothing changed.
- `d_topology_move` proxy.log: cloaked on the metrics change (guard thread t31368), relocated and checked 85 ms later (run 20261029_j13pc), uncloaked
  after the 500 ms settle, on both moves.
- Fact `napoleon.exe.window_imports`: I re-ran `proxy/tools/exe_info.py Napoleon.exe --imports user32.dll dinput8.dll` on the PC's
  exe. Every hooked call is in the IAT (`CreateWindowExW`, `ShowWindow`, `SetWindowPos`, `MoveWindow`, `SetWindowLongW`,
  `ChangeDisplaySettingsW`, `MessageBoxW`, `DialogBoxIndirectParamW`, `SetFocus`, `DirectInput8Create`), and there is no `*A` variant
  that would bypass them.
- No other open job branch's profiles ship a prefs file, so moving `prefs` from style `none` to `prefs` breaks none of them.

### Risk-first reading
I read in depth: `proxy/core/headless.cpp` and `display_guard.h` (engine window and D3D hooks: a mistake there puts a window on
Liam's monitor), the watcher's `Apply-PrefsOverlay`, `Headless-Overlay`, `Headless-Prepare`, `Headless-Wait` and `Launch-Job`
(persistent data: Liam's prefs), and the display tool's apply paths (the only code that changes a display). The display tool holds
its rule: only `Cds-Test` and `Cds-Apply` call `ChangeDisplaySettingsEx`, both take the name-based selection and refuse a primary,
and all changes are dynamic. The prefs overlay records `_active.json` before the first write and verifies each write by sha.

### Findings
**Blocker:** none.

**Should-fix (moved to J12; J12's brief must carry both, and fix and PC-prove them before the move):**
1. `proxy/core/headless.cpp:234` with `:304`: the guard's own relocation is lost when the thread calling it does not own the window.
   `PlaceLocked` adds `SWP_ASYNCWINDOWPOS` in that case and clears `s_ownMoveThread` as soon as the call returns. The window's thread
   handles `WM_WINDOWPOSCHANGING` later, sees `own == false`, and `GatePos` adds `SWP_NOMOVE|SWP_NOSIZE`, which drops the move.
   `PlacementVerified` then never passes, so `Decide` re-queues the relocation on every poll and the window stays cloaked for good.
   Fail closed, so nothing shows on a real monitor, but the run is dead. It does not happen on Napoleon: the render thread is the
   window thread (`d_topology_move` proxy.log, t11432 logs both `WM_DISPLAYCHANGE` and the relocation). It will happen on any core
   consumer that presents from another thread. To see it fail, present from a worker thread and move the virtual display. Fix
   direction: recognise the guard's move by its target rect in `GuardProc`, not by thread id.
2. `proxy/core/headless.cpp:285` (`PostCheckLocked`): the post-check only covers windows created through the exe's own
   `CreateWindowExW` (`s_wins`). A window that a DLL creates through its own imports (a third-party DLL, a CRT or loader dialog, a
   DLL's `MessageBoxW`) is swept once, at `Ensure` (`SweepCb`, `:378`), and never again. Brief deliverable 3 asks for "a post-check
   after each and at every Present [that] hides any window found visible elsewhere". The window probe would still report such a
   window afterwards. To see it fail, have any loaded DLL show a window after start-up: nothing in the proxy hides it. Fix direction:
   run the `SweepCb` sweep from the guard thread every ~250 ms, outside `s_cs`, then check it on the PC with the probe.

**Later (this repo):**
3. Watcher marker (`harness/napoleon/adapter.json` `headless.marker` = `headless_status.json`): the watcher finds this ASCII string in
   `d3d9.dll` only because of a log format string (`headless.cpp:109`). The status path itself is a wide string. Rewording that log
   line would make every headless launch refuse with a misleading "this proxy build cannot run headless". Use an explicit marker
   constant in the proxy that a host test pins.
4. `headless.cpp:329` (guard thread): the thread holds `s_cs` while it enumerates monitors (every 25th poll, and every poll while
   cloaked), and `HeadlessPresent` waits on the same lock. That can add frame-time spikes. J23's baseline should measure with headless
   on and say so.
5. Muting (`adapter.json` `headless.prefs` `sound_master_*`): the brief listed audio muting as out of scope. The report says Liam asked
   for it during the sitting, but nothing in the repo records that. The implementation is safe (the byte-identical restore returns
   his values, as the run shows). Liam to confirm.
6. A kill criterion was hit (prefs not byte-identical, `d_0_killed_by_orphan_loop`) and the job carried on after the diagnosis. The
   report names this, and the cause was the agent's own scratch loop, not the system under test, so I accept it. The lesson about
   orphaned background loops stays as prose because it concerns scratch scripts, not repo code.
7. Report open question 1 is a real watcher bug: a ps1 job reports `ok exit=0` when its script exits non-zero. It needs a
   `needs_brief` row.
8. The evidence for fact `napoleon.exe.window_imports` is `jobs/J13/report.md`, which does not hold the import list. The notes give the
   command, and the claim reproduces (above). Point the evidence at the command or a committed output.

### Effect on other open branches
After this merge every watcher launch is headless unless it passes `visible=1`. A headless launch needs the J13 proxy on the PC (the
watcher refuses a `d3d9.dll` without the marker). The PC already has kit `kit_20261029T183743Z_8565a96e131c`. Job branches that launch
the game should rebase onto this before their next PC sitting.
