# Run 20261107_j85pc: J85's PC test

Session `5589c70a-4722-444e-a364-10b33a6296b4`, 2026-11-07, layout D throughout (`DELL S2721DGF` and `VDD by MTT` by `WmiMonitorID`; `DEL41DB*` and `MTT1337` from the tool's own reading). **Partial: steps 1 to 5 are done. Steps 6 and 7 are not, see the end.** Steps 3 and 4 were driven by session `0280ca96-6ae4-4807-ae31-4e3119d8e245`, which carried on after the first session ended.

## Step 1: preflight and the "not known" facts
Before anything: `pc_deploy.py status` exe vanilla (sha1 `9aebcd2172f2`), nothing installed, no foreign files; `job.sh status` watcher 1.5.0, `not_running`, no lock; 22 GB free of 31.1.

- **Does a pass move `GetLastInputInfo`? No, for the path that was the question.** `idle_step1.log`: a logger once a second across one headless launch through `ctl.py scene land_small` and `job.sh`, on kit `kit_20261106T180846Z_6e96ce56fed1` (J78's). The cursor moved at both mode changes (launch at 11:43:04, restore at 11:43:49, to 1024,576 and back), and `last_input` stayed 13313078 from 11:42:32 to the end. **`SetCursorPos` does not move it.** One launch and one scene, not a whole pass: step 3's `<run>.idle.log` is the full reading.
- **Does the PC sleep when idle? Not on mains:** `powercfg` `STANDBYIDLE` AC index 0 (DC 600 s). The run still holds it awake with `SetThreadExecutionState`.
- **Which Python and `PATH` a scheduled task gets:** `task_env.json`, written by the task at 15:13:45 UTC: `pythonw.exe` from `pythoncore-3.15-64`, Pillow present, user `liamr`. `bash` on that `PATH` is the WSL launcher in `WindowsApps`; the tool runs `gitbash.git_bash()`, so it did not matter (`build.sh` ran under `C:\Program Files\Gitinash.exe`).

## Step 2: dry run
From Git Bash, 11:45:19 UTC. `tick --dry-run` refused on idle (1246 s), `tick --dry-run --present-file <scratch>\test_present` refused on the file. Exit 0 both times and `_scratch\acceptance-auto` was empty before and after.

Also read that minute: `watcher_diff` against the real installed files is empty, so the LF comparison holds on `watcher.ps1`, the adapter and the identity copy.

## Step 5: update with nothing to do
`update kit=harness_20261107T114520Z_1ec1b6b0c5fa`, built from this checkout: `watcher.log` 11:45:36 `[update] NOTHING TO DO: every file of kit ... is already in place (sha256) - no backup, no restart`, which is `update.ps1` exit 4. Versions do not differ, so no real update was run.

## Step 3: the scheduler's run (with step 4 inside it)
`task install` and `task install --proof --passes 3` were run by Liam with `!`: the permission check refused them for both sessions. `Start-ScheduledTask` at 15:13:45 UTC, 1868 s idle. Docker Desktop was started by the session on Liam's word, so it was up for every pass. The 3 passes ran as runs `20261107_j85auto1` and `20261107_j85auto2`, because step 4's stop fell inside them; the second run did 3 passes of its own, so the streak ended at 5, not 3.

- **The runner showed no window:** `observer_step3.log`, rect 2560,1440 3840x2160, 15:13:38 to 16:01 UTC. Nothing but Explorer's own shell windows, which track the mode change.
- **`SetCursorPos` does not move `GetLastInputInfo` across whole passes:** `last_input=25197562` on every line of `20261107_j85auto1.idle.log` and `20261107_j85auto2.idle.log`, and `idle_step3.log` climbs 1861 to 4741 s with no reset.
- **Layout:** D on every line of both idle logs, and `layout D` in `tick_step3_4.log`.
- **Build:** the first tick took 5.5 minutes in `build.sh --docker all`. Each run spent about 5 minutes on install before its first launch.

## Step 4: stop and resume
`test_present` put down at 15:30:55 UTC, in pass 2. `tick_step3_4.log`: stop wanted 15:30:57, `stop after: acceptance pass 2: pass` 15:36:34, pushed and stopped 15:37:12. `last_result.json` said `vanilla` and `clean`; `pc_deploy.py status` not installed, exe vanilla; `job.sh status` `not_running`, no lock. File removed, fired again: `3 passes after a streak of 2`, kit `kit_20261107T151922Z_d5c6378c11aa` (reused). `dll_sha256_logged` is `5dac94823fc5...` in pass 1 of the first run and pass 3 of the second.

## Deaths so far (layout D, Docker up)
**0 deaths in 30 launches:** `watcher_step3_4.log` has 30 `launch:` lines for 5 passes, 6 per pass, so no attempt was retried, and no line names a death. Load from `observer_step3.log`, 48 readings: free memory 18.7 GB average, 17.6 GB lowest, CPU 57% average with the game running. This is a small sample; step 6 adds to it.

## Not done
- **Steps 6 and 7.** `task install --proof` with no `--passes` runs `20 - streak`, so 15 more passes on this kit would end at 20.
- `pc_deploy.py status` and `job.sh status` were clean after step 1's uninstall: identical to the pre-install snapshot, 1564 files, no lock, no profile.
