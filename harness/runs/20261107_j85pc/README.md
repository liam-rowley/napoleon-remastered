# Run 20261107_j85pc: J85's PC test

Session `5589c70a-4722-444e-a364-10b33a6296b4`, 2026-11-07, layout D throughout (`DELL S2721DGF` and `VDD by MTT` by `WmiMonitorID`; `DEL41DB*` and `MTT1337` from the tool's own reading). Steps 1, 2 and 5 were driven by that session; steps 3, 4, 6 and 7 by session `0280ca96-6ae4-4807-ae31-4e3119d8e245`, which carried on after the first session ended. All seven steps are done.

## Step 1: preflight and the "not known" facts
Before anything: `pc_deploy.py status` exe vanilla (sha1 `9aebcd2172f2`), nothing installed, no foreign files; `job.sh status` watcher 1.5.0, `not_running`, no lock; 22 GB free of 31.1.

- **Does a pass move `GetLastInputInfo`? No, for the path that was the question.** `idle_step1.log`: a logger once a second across one headless launch through `ctl.py scene land_small` and `job.sh`, on kit `kit_20261106T180846Z_6e96ce56fed1` (J78's). The cursor moved at both mode changes (launch at 11:43:04, restore at 11:43:49, to 1024,576 and back), and `last_input` stayed 13313078 from 11:42:32 to the end. **`SetCursorPos` does not move it.** One launch and one scene, not a whole pass: step 3's `<run>.idle.log` is the full reading.
- **Does the PC sleep when idle? Not on mains:** `powercfg` `STANDBYIDLE` AC index 0 (DC 600 s). The run still holds it awake with `SetThreadExecutionState`.
- **Which Python and `PATH` a scheduled task gets:** `task_env.json`, written by the task at 15:13:45 UTC: `pythonw.exe` from `pythoncore-3.15-64`, Pillow present, user `liamr`. `bash` on that `PATH` is the WSL launcher in `WindowsApps`; the tool runs `gitbash.git_bash()`, so it did not matter (`build.sh` ran under `C:/Program Files/Git/bin/bash.exe`).

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

## Step 6: 20 passes, unattended
`task install --proof` with no `--passes` runs `20 - streak`. `Start-ScheduledTask` at 16:06:39 UTC, run `20261107_j85auto3`: 15 passes after a streak of 5, same kit, ended 17:52:29 with `complete: every pass ran` (`tick_step6.log`, `20261107_j85auto3.out`, `last_result_step6.json`). Evidence commit on `scratch/j85-proof`: `242b38e3`.

- **20 ledger lines on the proof branch, all `pass`:** 2 + 3 + 15 across the three runs, one `dll_sha256` (`5dac94823fc5`), one `watcher_sha`.
- **Rule 79 is satisfied.** `tick --dry-run --branch scratch/j85-proof --job J85`, 17:55:42 UTC: `skip scratch/j85-proof: rule 79 is satisfied`. That is `acceptance_problems`' own answer.
- **`acceptance.py streak` says 40, not 20.** It reads build and watcher but no branch, so it adds J78's 20 lines on the same build. The ledger holds 20 on each of `job/J78` and `scratch/j85-proof`.
- **Layout D throughout:** `layout=D` on all 101 lines of `20261107_j85auto3.idle.log`.
- **Nobody touched the PC:** `last_input=25197562` on all 101 lines. No session worked during the passes: J105's last push ended at 16:10:03, and pass 1 started at 16:11:47.
- **No window from the runner:** `observer_step6.log`, rect 2560,1440 3840x2160, 16:06:29 to 17:53:06. Explorer's own shell windows and nothing else.
- **Load:** 104 readings in `observer_step6.log`. Free memory 18.2 GB average, 17.5 GB lowest. CPU 85% average, 100% highest.
- **Shots looked at:** all 20 of passes 8 and 10 of `20261107_j85auto3`, the two passes that lost a launch, by eye on 2026-11-07. Each is the scene its name says: the campaign map and nine battles, nothing black or broken. The pass's own shot step only checks that the file was written.

## Lost launches, counted from `watcher.log`
| Runs | Passes | Launches | Deaths | Healthy game killed |
|---|---|---|---|---|
| `20261107_j85auto1`, `20261107_j85auto2` (`watcher_step3_4.log`) | 5 | 30 | 0 | 0 |
| `20261107_j85auto3` (`watcher_step6.log`) | 15 | 92 | 1 | 1 |
| **All** | **20** | **122** | **1** | **1** |

Both lost launches were retried by `ctl.py` and the pass went on. **Neither shows in a pass file:** `pass_08.json` and `pass_10.json` list 6 launches and no retry, which is why this table comes from `watcher.log` (J78 open question 1).

- **The death: pass 10's first launch, pid 2816, 17:12:24 UTC.** It exited 4 s after launch, `the game exited before reporting on_virtual (last status: starting DllMain)`. WER: `c0000374`, `StackHash_1892`, the same signature as the dump of 2026-11-06 20:36 UTC. Dump `Napoleon.exe.2816.dmp` in `CrashDumps/napoleon_remastered` under local AppData, 190 MB, left there for J101.
- **The kill: pass 8's last launch, pid 21688, 17:02:16 UTC. This was not a death.** The watcher logged `no on_virtual status for pid 21688 within 180 s (last: (no status yet)); the game was killed (fail closed)`. But the game had written `on_virtual`, `first frame presented there at 1.2 s`, at 17:02:18.669, two seconds after launch. The write went to VirtualStore, where the watcher does not read, and the guard moved it aside at the next launch: `virtualstore_status_pid21688.json`. That is `napoleon.harness.uac_virtualstore`, which J47 owns.
- **The same thing happened once before:** pid 11832, 2026-11-06 02:28 UTC, on J25 (`virtualstore_status_pid11832.json`). `watcher.log` has 2 `no on_virtual status` lines and 2 VirtualStore moves, and they are these two pairs.

**Deaths on D, quiet PC, J78's DLL: 1 in 122 (0.8%).** J101's table has D at 32/135 from 2026-11-05 on, and J78 had 2 in 122 on M. So D on its own does not bring the high rate. This run cannot say why: the PC was quiet and the DLL has W33, and both differ from most of that 32/135.

## Step 7: the end state
`task remove --proof` at 17:54 UTC, then `Get-ScheduledTask`: `napoleon_remastered acceptance-auto` Disabled, the proof task gone. `pc_deploy.py status`: not installed by this tool, exe vanilla (`9aebcd2172f2`), no `.git`. `job.sh status`: watcher 1.5.0, `not_running`, `lock` null, `profile_active` null.

`scratch/j85-proof` stays until review.
