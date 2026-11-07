# J85 report: Unattended 20-pass acceptance on the PC

**20 passes ran unattended on `scratch/j85-proof`, fired by the scheduler, and rule 79 is satisfied there.** The runner showed no window, nobody touched the PC, and the end state is clean. The real task is installed and stays disabled until Liam enables it. The run also gave J101 its first quiet number for layout D, **1 death in 122 launches**, and showed that one lost launch was a healthy game the watcher killed.

## What was built
- **`tools/acceptance_auto.py`:** verbs `tick [--dry-run]`, `request`, `status`, and `task install|remove|enable|disable`. It covers decisions 2 to 13: a run needs a committed request, every tick checks its guards cheapest first, the watcher follows the branch's core, a stop lands on the next pass line, a resume reinstalls the same kit, a dead run is cleaned up, and the end of every run uninstalls and pushes the evidence. Passes are counted only by `acceptance_problems`.
- **`tests/test_acceptance_auto.py`:** 72 tests on fake seams, no process starts. They include every case in deliverable 2.
- **`harness/README.md`:** the `Unattended acceptance` section.
- **The tasks:** `napoleon_remastered acceptance-auto` is registered and Disabled. The proof task was removed at the end.
- **Run folder:** `harness/runs/20261107_j85pc/`, with a README covering all seven PC steps.

No change under `core/`, `proxy/` or a counted `harness/` path.

## Evidence
All from run `20261107_j85pc`, 2026-11-07, layout D throughout. Its `README.md` has the detail and the log names.

### The three "not known" facts
- **Does a pass move `GetLastInputInfo`? No.** `SetCursorPos` moved the cursor at both mode changes and `last_input` did not change (`idle_step1.log`). Across the 20 passes it stayed `25197562` on every line of all three runs' idle logs. So the idle guard can be trusted.
- **Which Python and `PATH` does a task get?** `pythonw.exe` from `pythoncore-3.15-64`, Pillow present, user `liamr` (`task_env.json`). `bash` on that `PATH` is the WSL launcher, so the tool uses `gitbash.git_bash()`. `git push` worked from the task on all three runs.
- **Does the PC sleep when idle? Not on mains:** `powercfg` `STANDBYIDLE` AC index 0 (DC 600 s). The run still holds it awake with `SetThreadExecutionState`.

### The task's action line
```
C:\Users\liamr\AppData\Local\Python\pythoncore-3.15-64\pythonw.exe C:\Users\liamr\repos\napoleon-remastered\.claude\worktrees\J85\tools\acceptance_auto.py launch tick
```
Every 30 minutes (`PT30M`), `MultipleInstances IgnoreNew`, logon type `Interactive`. **It points at this job's worktree:** see open question 1.

### Runs
| Step | Run | Passes | Result | Commit on `scratch/j85-proof` |
|---|---|---|---|---|
| 3, 4 | `20261107_j85auto1` | 2 | stopped by the test file during pass 2, as asked | `63d67e81` |
| 3, 4 | `20261107_j85auto2` | 3 | complete, same kit, `dll_sha256` unchanged | `f8025f0c` |
| 6 | `20261107_j85auto3` | 15 | complete, 16:06:43 to 17:52:29 UTC | `242b38e3` |

- **20 ledger lines on the proof branch, all `pass`,** on kit `kit_20261107T151922Z_d5c6378c11aa`, one `dll_sha256` (`5dac94823fc5`), one `watcher_sha`.
- **Rule 79:** `tick --dry-run --branch scratch/j85-proof --job J85` at 17:55:42 UTC said `skip scratch/j85-proof: rule 79 is satisfied`.
- **Windows:** `observer_step3.log` and `observer_step6.log` show only Explorer's own shell windows on the virtual display's rect.
- **Stop and resume (step 4):** test file down at 15:30:55, stop after pass 2's line at 15:36:34, pushed at 15:37:12. That left no game, lock or profile, and the exe vanilla. The next firing reused the kit and carried on from a streak of 2.
- **Update with nothing to do (step 5):** `update.ps1` exit 4 on a kit equal to the installed watcher. Versions did not differ, so no real update was run.
- **End state (step 7):** proof task gone, real task Disabled, `pc_deploy.py status` not installed and exe vanilla, `job.sh status` `not_running` with no lock and no profile.
- **Shots:** I looked at all 20 of passes 8 and 10 of `20261107_j85auto3`, the two passes that lost a launch. Each is the scene its name says, the campaign map and nine battles, nothing black or broken.

### Start-up deaths, counted from `watcher.log`
| Runs | Passes | Launches | Deaths | Healthy game killed |
|---|---|---|---|---|
| `20261107_j85auto1`, `20261107_j85auto2` | 5 | 30 | 0 | 0 |
| `20261107_j85auto3` | 15 | 92 | 1 | 1 |
| **All** | **20** | **122** | **1** | **1** |

Load during step 6: free memory 18.2 GB average, 17.5 GB lowest, CPU 85% average, 100% highest (104 readings). Docker was up. No session worked during the passes.

- **The death:** pass 10's first launch, pid 2816, 17:12:24 UTC, `starting DllMain`, WER `c0000374`, `StackHash_1892`. Dump `Napoleon.exe.2816.dmp` is left in `CrashDumps/napoleon_remastered` under local AppData for J101.
- **The kill:** pass 8's last launch, pid 21688, 17:02:16 UTC. The watcher logged `no on_virtual status for pid 21688 within 180 s` and killed the game. **The game was fine:** it had written `on_virtual`, first frame at 1.2 s, at 17:02:18, but the write went to VirtualStore (`virtualstore_status_pid21688.json`). That is `napoleon.harness.uac_virtualstore`.
- **The earlier case:** the same thing hit J25 on 2026-11-06 at 02:28 UTC (`virtualstore_status_pid11832.json`). `watcher.log` has exactly 2 `no on_virtual status` lines and 2 VirtualStore moves, and they pair up.

**What this says for J101:** J101's table has D at 32/135 from 2026-11-05 on, and J78 had 2 in 122 on M. So layout D alone does not bring the high rate. It does not say why the rate was high. This DLL has W33, which arrived with J78 after that 32/135 was counted, and this PC was quiet, while J101 says load was recorded for almost none of those launches. Either could be the reason. One sample of 122 launches also leaves room for a rate of a few percent.

### Ticks refused
**None logged:** `status` prints `refusals by reason: none`. That does not show how often the PC was usable, because the real task never fired and I fired the proof task only once the guards would pass. Step 2's two dry-run refusals (idle 1246 s, then the present file) are not logged, by design. `status` will give the real figure once the task is enabled.

### Gates and build id
`build_id.py --no-dirty` printed `96722f4b8d52` before and after the job, including after merging `main` (pin v0.50.1). `python3 core/wsc.py gates` on the merged branch, 18:06:45 UTC: `14 ok, 2 warn, 0 failed in 199.9 s`. 796 tests passed and 47 skipped, `timing: workers 1`. The two warnings are the `hooks` line for this worktree and the skipped tests. `ProxyHostTests` skipped because the proxy inputs are unchanged, so this time says nothing about J109's 580 s.

Usage: 106 tool calls in session `5589c70a-4722-444e-a364-10b33a6296b4`, counted from its transcript. Session `0280ca96-6ae4-4807-ae31-4e3119d8e245` carried on from there but also ran other jobs and did not count its J85 share, so the total is above 106 and not known.

## Deviations from the brief and why
1. **20 passes came from three runs, not one.** Step 6 asks for one full run. Steps 3 and 4 had already put 5 passes on the proof branch, and the tool runs `20 - streak`, so the last run was 15. The longest single run is therefore 1 hour 46 minutes, not 2.7 hours. The hard limit of 4 hours was never approached.
2. **`acceptance.py streak` says 40, not the 20 the brief asks for.** It reads build and watcher but not the branch, so it adds J78's 20 lines on the same build. The ledger holds 20 on each branch, and the gate's answer is the one above.
3. **Failed results in the cited runs:** no ctl result file has `status` `failed`, and all 20 pass files say `pass`. The watcher logged two failed `launch` jobs, both in `20261107_j85auto3`, both retried by `ctl.py`: `acceptance-auto-20261107t160642z-20261107T170215Z-3200131067` (the kill) and `acceptance-auto-20261107t160642z-20261107T171220Z-2886732213` (the death).
4. **Neither lost launch shows in a pass file.** `pass_08.json` and `pass_10.json` list 6 launches and no retry. J78 found this for a pass's first launch; pass 8's was its last, so it reaches further than J78 said. `last_result.json` also says `complete` with no notes, so an unattended run gives no sign of a lost launch unless someone reads `watcher.log`.
5. **Steps 3 and 4 ran together.** The 3-pass run was also the stop-and-resume test, which saved a run. The second run did 3 passes of its own, so the two together made 5.
6. **Liam and this session installed the tasks, not the builder.** The permission check refused `task install` for both sessions. Liam ran the first two with `!`, then asked this session to add allow rules for `task install`, `task remove --proof` and `task enable`. This session ran the later installs and the remove. It did not run `task enable`.
7. **Docker was started by a session, on Liam's word,** so it was up for every pass. The tool never starts it.
8. **`--ignore-session` is not in the brief.** The session driving the proof shows as `working`, so the guard would refuse every tick. It takes one session id, and `tick` refuses it on anything but a `scratch/` branch.
9. **Two sessions built this.** `J85-build` stopped at 11:49 UTC after step 5, and session `0280ca96-6ae4-4807-ae31-4e3119d8e245` drove steps 3, 4, 6 and 7 and wrote this report. Neither can review it.
10. **J88's `--peek` fix was cherry-picked** (`5b8feaf2`) because a bare `jobs next` in the hook corpus test claimed a job on every gates run. `main` now has the same change.
11. **Rule A is an error now, not a warning.** The brief's target fact predates J88 setting `reviewer_code = "error"`. A ledger commit in a fix round now needs a newer review round from a fresh session. A job in `fix` gets that round anyway, so the tool did not change.
12. **A change outside the brief, in `tests/test_claude_hook_corpus.py`.** The first full `gates` run failed `test_commands_printed_by_the_job_steps`. The test checks every command `jobs next --peek` prints, and with a live remote that now includes `git push origin --delete job/J27` for each empty claim, which the hook denies on purpose. CI on `main` is green because it does not see those lines. The test now drops that one line. Without this, every full local `gates` run fails while an empty claim exists, and J109 needs five in a row.

## Open questions
1. **For Liam: enabling the real task.** After this merges, run `python3 tools/acceptance_auto.py task install` from the main checkout first, because the action line points at `.claude/worktrees/J85` and stops working when that worktree goes. Then `task enable`. recommended: enable it after the merge. It only runs for a branch with a request, so it does nothing until a job asks.
2. **For Liam: J47 is worth a line.** Its row says the watcher reads stale files. It does not say that a healthy game gets killed, costing 3 minutes each time, and that two in a row would spend a flake. recommended: leave J47 where it is and add that reason when its brief is written. It blocks nothing today: the retry saved the pass.
3. **For J101:** read the other `virtualstore_*` folders under the watcher's `_to_delete`. There are several from 2026-11-03 on, and J101 asks about J30's 180 s spin at `starting DllMain`. This job did not check whether any of them explains that.
4. **W rows recommended, none filed, none blocks a game-facing job:**
   - `acceptance.py` records a retry for every launch in a pass, and the pass file shows it (extends J78's open question 1).
   - `acceptance.py streak` takes a branch.
   - A stop flag in `acceptance.py`, so a stop does not have to end the process (out of scope here).
   - The autopilot holds back non-PC sessions during a run (out of scope here).
5. **`scratch/j85-proof` stays until review,** then the reviewer or Liam deletes it.
