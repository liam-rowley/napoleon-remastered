# J19 report: Hang watchdog test race on hang.txt

Branch `job/J19`. Code commits 8be13f7 and 69a6732 (2026-10-29). Model: Opus 5.5 (the brief said Sonnet; see Deviations).

## What was built
- **Watcher 1.0.1** (`harness/core/watcher.ps1` `Handle-Hang`): `hang.txt` is written atomically (`Write-Atomic`) with every note so
  far plus `kill: pending` **before** `Kill-Game`. After the kill it is rewritten atomically ending `kill: killed` or
  `kill: ZOMBIE - PC needs a reboot`, and only then is `HANG handled: ...` logged. If the watcher is stopped mid-kill, the evidence
  is still on disk.
- **Hang test** (`Test-Integration.ps1`, case `hang watchdog`): after the fake game exits, the case waits for
  `HANG handled: killed`, matching only log text written since the case started (`Log-Mark`, `Wait-LogMatch ... -Since`), so a
  repeated run never matches the previous run's line. It then asserts that exactly one new `*_hang` folder exists and that
  `hang.txt` holds `kill: killed` and no `kill: pending`. Every existing assertion is kept.
- **`-Only <regex>` / `-Repeat <n>`** on `Run-HostTests.ps1` (passed to the integration suite only; the unit suite always runs
  whole) and `Test-Integration.ps1`. The selection logic is `Invoke-Selected` in `Test-Lib.ps1`. A selected case runs n times and
  stops at its first failure. The output prints `(k/n runs passed)`, and a filter that matches no case fails. Default behaviour is
  unchanged.
- **`gates.yml` `workflow_dispatch`** with `only` and `repeat` inputs. Only `harness-windows` runs on a dispatch. The inputs reach
  the step through env vars, not pasted into the script. A dispatched run has its own concurrency group
  (`-dispatch-<run_id>`), so it neither cancels nor is cancelled by the push run on the same ref. Push and pull_request behaviour is
  unchanged. Usage is in `harness/README.md` Tests.
- **Unit tests** (`Test-Unit.ps1`, 29 cases, all passing locally under Windows PowerShell 5.1):
  - the `Invoke-Selected` rules: filter, repeat, stop at first failure, repeat below 1 runs once;
  - the declared parameters, defaults and `ValidateRange` of both scripts (from the AST);
  - a static guard that `Handle-Hang` writes `hang.txt` once before and once after `Kill-Game`, with `HANG handled` logged last;
  - a guard against the variable collision found during the job (next section).

## Bugs found on the way (fixed in code, with a guard)
1. **The update test hard-coded the watcher version.** Case `update: a good kit` replaced the literal `$Version = '1.0.0'`, so any
   version bump would have silently left the kit at the current version and failed the case. It now does a regex replace of
   whatever the version is.
2. **`-Only`/`-Repeat` never reached the cases on the first try.** The first dispatch (run 40898907246) ran all 20 cases once,
   although the step's env showed `HT_ONLY: hang watchdog`, `HT_REPEAT: 10`. The cause: `Test-Lib.ps1` assigned `$script:Only` and
   `$script:Repeat`. A suite script's parameters live in its script scope and PowerShell names are case-insensitive, so dot-sourcing
   the library reset `-Only` to `''` and `-Repeat` to 1. Fixed by renaming the library's state to `$script:TcOnly` and
   `$script:TcRepeat`. Two new unit checks guard it:
   - a static check: Test-Lib assigns no script variable named like any parameter of the three suite scripts;
   - an end-to-end check: a probe suite script run in a child PowerShell with `-Only 'hang watchdog' -Repeat 3` must see both
     values.

## Sweep: every other integration case (exit-then-assert pattern)
Checked against the write order in `watcher.ps1` and `update.ps1`. No other case asserts on watcher output before the watcher's own
completion signal:

| Case | What it waits for, then asserts | Verdict |
|---|---|---|
| noop and status | `.done`; reads `.out`, `watcher.log`, `watcher.status` | safe: `Collect-Part` writes `.out` before `Finish-Job` writes `.done` |
| queue | `.done` of each job, then `.out` | safe (same order) |
| single instance | process exit code of the second watcher (`-Wait`) | safe: the exit code is the thing asserted |
| one job error | `.done`, `.out` | safe |
| job ids never reused | `Wait-Until` on the refused `.done` | safe |
| job timeout | `.done`; game alive; kill job `.done`, then `Wait-Until` game gone | safe |
| refusals | `.done` of each refusal | safe |
| launch and kill | kill job `.done`, then no `Fake*` process | safe: `Kill-Game` polls until the process is gone before the job closes |
| zombie | kill `.done`; `Wait-Until` status; `watcher.zombie.json`; `is gone` log line after waiting for the flag to clear | safe: the zombie file is written inside `Kill-Game` before the job closes; the `is gone` line is logged before the status clears |
| profiles | `.done` of each profile job, then hashes | safe |
| auto-restore | already waits for the log lines (fixed in J2 review, run 40832860145) | safe |
| hang watchdog | **process exit, then `hang.txt`** | **the race: fixed (both sides)** |
| dump.ps1 64-bit | synchronous call | safe |
| spawn detached | `.done`, then `Wait-Until` marker | safe |
| launcher restart | `Wait-Until` a new watcher pid, then `.done` (lost) | safe: `lost` is written at watcher start |
| update good | `Wait-Until` version and `CONFIRMED`, then file and backup | safe: files and backup exist before the new watcher reports its version |
| update rollback 1 and 2 | `REVERTED` log line, then sha | safe: `update.ps1` logs `REVERTED` after restoring the files and seeing the old watcher healthy |
| update stale | `ABORT` log line, then sha | safe |
| installer | synchronous `install.ps1` calls | safe |

No watcher completion line was missing, so no new log line was needed.

## Evidence
- **10 runs in a row:** dispatch run **40900019359** on 69a6732, `gh workflow run gates.yml --ref job/J19 -f only='hang watchdog' -f repeat=10`
  ran `run 1/10` to `run 10/10` and printed `PASS hang watchdog ... (10/10 runs passed)`,
  `integration : 10 passed, 0 failed (1 cases matched -Only 'hang watchdog')`.
- **Full run on the final code commit:** push run **40900010030** on 69a6732: `gates`, `proxy`, `harness-windows` all green.
  The earlier push run 40898886583 on 8be13f7 was green too (integration 20 passed, 0 failed).
- Not proof: dispatch run 40898907246 was green, but it ran the whole suite once because of bug 2.
- Local `wsc gates` on this Windows host: the `tests` gate fails in `test_job_sh` and `test_pc_deploy` (2 failures, 4 errors).
  Neither file is touched by J19. These are the Windows-host failures described in J6's report (bash resolves to WSL), plus
  `pc_deploy`'s check that the game is closed, which acts on the host's real state. CI's Linux `gates` job passed on both J19
  pushes, and `wsc jobs check` is ok.
- The commit adding this report changes only `jobs/J19/report.md` and the jobs registry; its push run is the formal final run.

## Deviations
- **Dispatch instead of a temporary commit.** The brief expected `workflow_dispatch` might not work before the trigger was on main.
  GitHub accepted the dispatch on `job/J19` because main already has a `gates.yml`, so no temporary commit or revert was needed.
- **Two extra fixes** beyond the brief: the hard-coded version in the update case (the version bump the brief asked for would have
  broken it) and the `-Only` variable collision. Both are within the brief's scope (the harness tests) and both carry a guard.
- **The model was Opus 5.5, not Sonnet.** That is the session the job ran in. No subagents. About 50 tool calls, under the 60
  budget.
- `-Repeat` is repeat-safe for `hang watchdog`. Some other cases assume state from earlier cases (for example the update rollbacks
  need `update: a good kit` first, and auto-restore counts `game.lock.expired_ci5_*` as exactly 1). That is documented in the
  `Test-Integration.ps1` header rather than changed: making every case repeat-safe is out of this job's scope.

## Follow-ups
- **Deploy watcher 1.0.1 to the PC** (`update kit=`): out of scope here; the next PC job ships it.

## Open questions
- None blocking. Should the dispatch also allow `suite=unit` for chasing a unit case? Not needed so far.
