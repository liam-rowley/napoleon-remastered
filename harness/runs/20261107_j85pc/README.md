# Run 20261107_j85pc: J85's PC test

Session `5589c70a-4722-444e-a364-10b33a6296b4`, 2026-11-07, layout D throughout (`DELL S2721DGF` and `VDD by MTT` by `WmiMonitorID`; `DEL41DB*` and `MTT1337` from the tool's own reading). **Partial: steps 1, 2 and 5 are done. Steps 3, 4, 6 and 7 are not, see the end.**

## Step 1: preflight and the "not known" facts
Before anything: `pc_deploy.py status` exe vanilla (sha1 `9aebcd2172f2`), nothing installed, no foreign files; `job.sh status` watcher 1.5.0, `not_running`, no lock; 22 GB free of 31.1.

- **Does a pass move `GetLastInputInfo`? No, for the path that was the question.** `idle_step1.log`: a logger once a second across one headless launch through `ctl.py scene land_small` and `job.sh`, on kit `kit_20261106T180846Z_6e96ce56fed1` (J78's). The cursor moved at both mode changes (launch at 11:43:04, restore at 11:43:49, to 1024,576 and back), and `last_input` stayed 13313078 from 11:42:32 to the end. **`SetCursorPos` does not move it.** One launch and one scene, not a whole pass: step 3's `<run>.idle.log` is the full reading.
- **Does the PC sleep when idle? Not on mains:** `powercfg` `STANDBYIDLE` AC index 0 (DC 600 s). The run still holds it awake with `SetThreadExecutionState`.
- **Which Python and `PATH` a scheduled task gets: not answered.** No task could be registered, see the end.

## Step 2: dry run
From Git Bash, 11:45:19 UTC. `tick --dry-run` refused on idle (1246 s), `tick --dry-run --present-file <scratch>\test_present` refused on the file. Exit 0 both times and `_scratch\acceptance-auto` was empty before and after.

Also read that minute: `watcher_diff` against the real installed files is empty, so the LF comparison holds on `watcher.ps1`, the adapter and the identity copy.

## Step 5: update with nothing to do
`update kit=harness_20261107T114520Z_1ec1b6b0c5fa`, built from this checkout: `watcher.log` 11:45:36 `[update] NOTHING TO DO: every file of kit ... is already in place (sha256) - no backup, no restart`, which is `update.ps1` exit 4. Versions do not differ, so no real update was run.

## Not done
- **Steps 3, 4, 6, 7** need a registered task, and the session's permission classifier denied `task install`. They also need Docker for the first build, which was not running at 11:30 UTC and which this job may not start.
- `pc_deploy.py status` and `job.sh status` were clean after step 1's uninstall: identical to the pre-install snapshot, 1564 files, no lock, no profile.
