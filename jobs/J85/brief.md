# J85: Unattended 20-pass acceptance on the PC

Phase 1, tooling. Audit 2026-11-03 (`docs/audits/AUDIT_2026-11-03.md`, automation 5). A rule 79 run takes about 2.7 hours of quiet PC and today a Claude session sits beside it. This job adds a
plain script, fired by a scheduled task, that runs the passes for a job branch that asks for them, while nobody is at the PC, and pushes the ledger lines and evidence. Almost every guard the row
names is already in the pin: the session as lock owner (W10), the watcher preflight, unique run ids and the flake rule (W9), and the `update` job. **So this job is a runner on top of those, not new
harness code.** What is new is what no session has had to think about: no person is there when it starts, when Liam comes back, or when it fails.

Model: Opus, reason: Liam's "Opus across the board" (2026-11-06, the row J105 writes), and an unattended script that drives the PC and pushes to job branches has no one to catch a wrong guard.
Budget about 200 tool calls (W25, W10, W9 and J52 were budgeted 150, 170, 190 and 120; no job has a `Usage:` line to read). Subagents are not needed. Waiting belongs to the harness: the task and a
background shell wait, you do not poll.

**No DLL or harness input changes: this job carries no 20 passes of its own (rule 79).** New code goes under `tools/` and `tests/`, the docs change is a `README.md`, and `rule79_path` exempts READMEs and
`runs/` folders. `needs_pc` is true for the proof below, not for rule 79. If a deliverable turns out to need `proxy/`, `harness/` outside those, or the pin: see Kill criteria.

## Start
- If this session's model is not the row's, stop and say so.
- Follow `CLAUDE.md` (Jobs: branch `job/J85`). Read `docs/REVIEW.md` (rule 79), `harness/README.md` in full, `jobs/J78/report.md` (with its `## Fix round 1`), `jobs/J75/report.md`, and `jobs/J101/brief.md`
  (`## Target facts`: the layouts and the rates) plus `jobs/J101/report.md` if it exists by then.
- Read in the core, never edit: `core/harness/acceptance.py` (`cmd_run`, `run_problems`, `run_id_problems`, `who`, `streak`, `classify`), `core/harness/job.sh`, `core/harness/ctl.py` (`resolve_identity`),
  `core/harness/update.ps1`, `core/harness/install.ps1` (how a task is registered without admin), `core/harness/spawn_detached.ps1`, `core/warscape/trailer.py`, `core/warscape/policy.py` (rules A and B),
  `core/warscape/jobq.py` (`auto_tick`, `ACCEPTANCE_PURPOSE`). Game side: `tools/gates/pipeline.py` (`acceptance_problems`, `collect_acceptance`).
- Search first: `python3 core/wsc.py find acceptance watcher lock kit`. Reuse those functions and verbs. Do not write a second rule 79 reader or a second streak counter.

## Target facts
Check each again before relying on it; the pin may have moved (J88).
- **`acceptance.py run` already does:** the refusal of a held lock or an active profile, the refusal of a run id with evidence, the watcher bytes check, one pass file and one ledger line per attempt,
  a `flake` that neither counts nor stops up to `acceptance.max_flakes`, and a stop at the first `fail`. Each pass takes and releases its own lock, so **the lock is free between passes**.
- **It has no way to stop between passes.** A `kill` of the process leaves the game up under the lock, and `finally` does not run on `TerminateProcess`.
- **A streak can span runs.** `acceptance_problems` only needs pass numbers to rise within one run, the same branch, the same `watcher_sha` and, once `watcher_sha` is present, **the same `dll_sha256`**.
  So a stopped run can be finished by a later run with a new run id, on the same DLL bytes.
- **`--branch` is explicit-friendly.** `run_problems` needs a branch only to label lines, so a detached checkout works with `--branch job/J<n>`. `git worktree add` refuses a branch checked out elsewhere
  (a builder's worktree), so detached is the safe form.
- **`resolve_identity`** reads `--session`, then `WSC_SESSION_ID`, then `CLAUDE_CODE_SESSION_ID`. A scheduled script has neither of the last two unless it sets one. Owner rule: `^[a-z0-9][a-z0-9_-]{0,39}$`.
- **The commit hook is on** (`[policy] commit_msg_hook`) and needs `core/wsc.py` in the checkout, so a worktree needs its submodule initialised or every commit is refused. The pre-push hook runs too.
  `tools/claude_hook.py` judges Claude's shell calls only: **a scheduled script has none of its guards, so this tool has to keep each rule itself.**
- **`policy` rule A:** after the first review commit, a commit by a session neither the builder's nor a round's belongs to the next round. A ledger commit in a fix round lands there. It is a warning here
  (`reviewer_code` is not set), and rule B needs a session id unused by earlier rounds.
- **`update kit=<id>` does not replace `watch.cmd`** (J64 open question 4), so a kit whose `watch.cmd` differs needs `Install watcher.cmd`, a double-click. That is why Liam installed the current watcher by hand (J78).
- **`job/*` branches are never deleted.** `git ls-remote` lists every job ever built, so "any branch whose rule 79 fails" cannot be read literally.
- **Autopilot:** `auto_tick` starts no `needs_pc` session while an acceptance lock is held. It reads the lock, which is free between passes, and it does not hold back a non-PC session at all.
- **A window on the virtual display fails a pass:** J64 lost a pass to a Windows Terminal window over the game (`jobs/J64/report.md`, run 20261104_j64pc4). The observer is `harness/runs/20261104_j64pc5/foreign_windows.ps1`.
- **Layouts:** J101 names D and M and tabulates deaths per launch, and says M looks like daytime and D evenings and nights. Read that table. J78's 20 passes ran on M with 2 deaths in 122 launches. **At D's latest rate,
  two lost launches in a row come up several times in a run of about 120 launches, and the allowance is `acceptance.max_flakes`: a run on D cannot be expected to pass, whatever the DLL.**
- **Free memory:** J64's run 20261104_j64pc5 failed a load with 5.9 GB free. Core row W105 (a floor in the runner) is `later`.
- **Not known, find out in step 1 of the PC test and put in the report:** whether anything in a pass moves `GetLastInputInfo` with nobody there (`ctl` has no OS-level input, but the display tool calls `SetCursorPos`);
  which Python and `PATH` a scheduled task gets (Pillow is needed, `python3` may not resolve, and `git push` needs Liam's credentials, so the task must run in his logon session: `GetLastInputInfo` needs that session too);
  whether the PC sleeps when idle.

## Decisions already made for this job
1. **A game-side tool, no core change.** `tools/acceptance_auto.py` with `tests/test_acceptance_auto.py`, a header and a `tools` row. In the core it would move the pin, and a core `harness/` change costs 20 passes;
   Napoleon is the only consumer. If Empire needs it, that is a W row then.
2. **A plain script, not a Claude session:** 2.7 hours of waiting must cost no tokens. Its identity is one id per run, `acceptance-auto-<utc stamp>`, used as `--owner`, `--session` and the `Claude-Session:` trailer. Never a real
   session's id: the trailer says who made the commit, and a unique id keeps rule B true.
3. **A run needs a request** (narrows the row: open question 1). A builder whose final build needs passes commits `jobs/<id>/acceptance_request.json` (`build_id`, `watcher_sha`) on `job/<id>`, pushes, leaves the row at `queued` or `fix`
   and ends. A `request` verb writes the file. A tick takes a branch only if: the row on `main` is not `done`, the row on the branch is `queued` or `fix` (so the autopilot starts no review before the passes), head's `build_id.py` equals the
   request, and `acceptance_problems` still reports rule 79 for it. Oldest request first, one run at a time.
4. **Every tick checks these in order, cheapest first. A refusal is one log line, exit 0, nothing touched:** `<state>/liam_present` exists; idle under the threshold (open question 2); `job.sh status` shows a lock or a profile;
   `pc_deploy.py status` says the exe is not vanilla, or shows foreign files or a kit this tool did not install; a session is `working` in `claude agents --json`; free memory under 8 GB; the layout is not M (open question 3); and,
   only when a build is needed, Docker does not answer. Starting Docker or changing a display is never this tool's job.
5. **The watcher follows HEAD before anything is built.** Compare the installed files with the checkout's core, as `acceptance.py` does. If only `update` files differ: `pc_deploy.py kit --what harness`, `send`, `job.sh ... update kit=<id>`, and go on only on
   `CONFIRMED`. If `watch.cmd` differs: refuse and log that `Install watcher.cmd` is Liam's. No change to `watcher.ps1`: the row's "the watcher updating itself" is this step.
6. **The run.** One long-lived detached worktree, `.claude/worktrees/acceptance-auto`, submodule initialised. Build with `core/proxy/tools/build.sh --docker all`, check `build_id.py` equals the request, then `pc_deploy.py kit --what proxy`, `send`, `install`, wait 5 minutes (J78's
   preflight), then `core/harness/acceptance.py run --passes <20 minus the streak> --run <date>_<id>auto<n> --branch job/<id>`. Hold the PC awake for the run with `SetThreadExecutionState`, no power plan change. Hard limit 4 hours.
7. **Stopping when Liam comes back, or the layout changes.** Read the run's stdout. On a `liam_present` file, input, or a layout change, stop at the next `acceptance pass N:` line, so no finished pass is lost: end the process, then through `job.sh` as the same owner and session
   `kill`, `unlock`, wait for the restore, and `pc_deploy.py uninstall`. Never touch the game any other way. The check is whether a game is up under the lock, not whether the run looks finished.
8. **Resuming.** Keep the kit id in the state file and reinstall **that kit, no rebuild**, so `dll_sha256` holds. The next tick runs `20 minus the streak` under a new run id. Stopped runs do not consume a request.
9. **The end of every run**, whatever happened: uninstall, `status` must say vanilla, commit `harness/acceptance/ledger.jsonl` and the run's pass files with the trailer, `git fetch`, then push `HEAD:job/<id>`. If the remote head moved: rebase only if `build_id.py` is unchanged and the rebase is clean,
   else leave the commit local and log it. A `fail`, or the flake allowance spent, **consumes the request**: no retry until a new commit asks again.
10. **A tick that finds its own state file with no live process** (reboot, crash, logoff) cleans up what that run owned, by the same route, then commits what it finds. It touches nothing it did not install.
11. **Logs and state** go to `job.sh scratch acceptance-auto`. `<state>/liam_present` is only ever read, and made by Liam by hand. One `last_result.json` says what the last tick or run did and why.
12. **The task:** `task install`, `task remove`, `task enable`, `task disable` verbs, by `Register-ScheduledTask` for the current user (no admin), interactive logon, `MultipleInstances IgnoreNew`, every 30 minutes. **It installs disabled, and only Liam runs `task enable`, after reading the report.** A disabled task cannot be fired, so the proof uses its own task: `task install --proof` registers a second task with no time trigger, bound to `scratch/j85-proof`, and `task remove --proof` takes it away. Either task starts one hidden console that every child
    inherits, the way `spawn_detached.ps1` does, because a child console on the virtual display fails a pass.
13. **This tool never:** force-pushes, uses `--no-verify`, edits `baseline.json` or a limit, writes `report.md`, sets a row, merges, or runs `git` in a game folder or the state folder.
14. **The next step after a green run stays with a person or a session:** a finish session writes the evidence into `report.md` and sets `status=review`, as J78's second session did.

## Deliverables
1. `tools/acceptance_auto.py`: verbs `tick`, `request`, `status`, `task ...`, and `--dry-run` on `tick` (says what it would do, changes nothing). Decisions 2 to 13.
2. `tests/test_acceptance_auto.py`, with fake seams for git, `job.sh`, `pc_deploy.py`, the clock and the idle reading, no process starts (the `tests` gate sits at its time cap: J109). At least: every refusal of decision 4 and that it touches nothing;
   a stale `job/*` branch is skipped; a request whose `build_id` is not head's is skipped; `20 minus the streak` after a stop; a stop reinstalls the same kit and never builds; a `fail` consumes the request; a stop does not; a moved remote head with a new build id never pushes;
   `watch.cmd` differing refuses; the trailer passes `message_problem`; crash cleanup leaves another job's kit alone.
3. `harness/README.md`: a short `Unattended acceptance` section: how a builder asks, what a tick checks, how Liam holds it off, what to do after a `fail`.
4. Run folder `harness/runs/<YYYYMMDD>_j85pc/` with a `README.md` whose paths exist (`run_refs` gate): the tick logs, the observer log, the idle readings.
5. `python3 core/wsc.py gates` green, `build_id.py` the same before and after.

## PC test
Needs Liam: a window with nothing else running, on layout M. The proof branch is `scratch/j85-proof`, cut from `job/J85` with one harmless change under `harness/` so rule 79 fails on it, and a request on it. **Its ledger lines never reach `job/J85`, and the branch stays until review.**
A `--passes N` and `--branch` override exist for this proof only. Preflight first, each result in the report:
1. `python3 core/proxy/tools/pc_deploy.py status` (exe vanilla, no foreign files, nothing installed from another job) and `bash core/harness/job.sh status` (watcher matches the core, `not_running`, no lock). `python3 core/wsc.py find <scenario>` for the rows in the adapter's `acceptance.order`.
   The game is launched and killed only through `job.sh`. Answer the three "not known" facts above; **a wrong answer changes the guards, so settle them before step 2.**
2. `tick --dry-run` from Git Bash, then with a test `--present-file` under the scratch folder: it refuses and nothing changes.
3. `task install` (it stays disabled and you never enable it), `task install --proof`, then fire the proof task with `Start-ScheduledTask`, with the observer running (J78's rect for M). A 3-pass run on the proof branch, fired by the scheduler and not by a shell, because its environment is the thing under test. **The observer must show no window from the runner.** Log the idle reading once a minute: this answers the `SetCursorPos` question.
4. Stop and resume: put the test present file down during pass 2. It must stop after that pass's line, leave no game, lock or active profile, and uninstall. Remove the file, fire again: same kit, `dll_sha256` unchanged, the streak continues.
5. `update kit=<id>` with a kit equal to the installed watcher: exit 4, nothing to do. A real update only if the versions differ by then.
6. **One full run, 20 passes, unattended, on the proof branch, ending in `acceptance.py streak` saying 20.** This is the row's title. Leave it to the task and end your turn; a background shell brings you back. Say which layout held, and look at the shots of at least one pass and say so.
7. At the end: `task remove --proof`, the real task still disabled, `pc_deploy.py status` says vanilla, no lock. Every `failed` ctl result in a cited run is named under `## Deviations`.

## Out of scope
Any change under `core/`, including a stop flag for `acceptance.py` or the autopilot holding back non-PC sessions (write those as W rows in the report, no build). The cause of the crash and anything about D (J101). Changing a display or starting Docker. Telling anyone about a result beyond the pushed evidence and `last_result.json`.
Starting a finish session after a green run (W46's area). Real job branches: no run for a real job in this job.

## Open questions
All four answered by Liam on 2026-11-07, "Yes follow recs". They are recorded here because `docs/DECISIONS.md` has no room until J105 brings row files. Start on these; none is open.
1. The row says any branch whose rule 79 fails. **Answer: a run needs the request file**, because a branch still being built would waste a 2.7-hour run and most `job/*` branches are long merged.
2. How long must Liam be idle before a run starts? **Answer: 30 minutes, a constant in the tool.**
3. Should a run start on layout D? **Answer: no, refuse D until J101 reports**, because a failure there says nothing about the DLL. Nights look like D, so the hours the task can run may be few: the report's refused-tick count is what shows this.
4. Registering the task, and enabling it. **Answer: register it disabled; Liam alone runs `task enable`, after reading the report.** The proof runs on its own on-demand task (decision 12).

## Kill criteria
- `build_id.py` differs before and after the job, or a deliverable needs a change under `proxy/`, `core/` or a counted `harness/` path: stop, commit, report (the job would then carry 20 passes and a W row).
- Step 1's `GetLastInputInfo` reading moves with nobody there and no input source can be told apart: stop the idle guard work, keep `liam_present`, report the readings and ask Liam.
- A scheduled firing cannot reach `python3` with Pillow, or `git push`, after 2 attempts at the task definition: stop and report what the task saw.
- After step 3 or 4, `foreign_windows.log` shows a window from the runner on the virtual display and a second attempt at the hidden console shows one too: stop and report.
- Step 4 leaves a lock, an active profile or a game up after the stop path has run: stop, clear it through `job.sh`, report; no second try without changing the path.
- `pc_deploy.py status` is not vanilla after any `uninstall`: stop and report before anything else.
- Layout is D, or exit 2160, during a proof pass: stop at that point, keep the evidence, say the layout. Do not wait out a night in this session.
- A proof pass ends `fail`: stop, keep the evidence, no retry, except the tool's own retry of a start-up exit. Row `blocked` if it is not the runner's fault and needs J101.
- Over about 200 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J85/report.md`: `## What was built`, `## Evidence`, `## Deviations from the brief and why`, `## Open questions`. It must also say: the three "not known" answers, with the date and run id; the task's exact action line; the run ids of steps 3, 4 and 6 and the commit on `scratch/j85-proof` that holds them;
start-up deaths per launch for those runs, counted from `watcher.log` (pass files undercount: J78 open question 1); how many ticks were refused and why, so Liam can see how often the PC was usable; the W rows you recommend. Then `wsc reg set jobs J85 status=review report=jobs/J85/report.md`.
