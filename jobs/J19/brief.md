# J19: Hang watchdog test race on hang.txt

Phase 1, job 19: make the `hang watchdog` integration test deterministic. It failed once on PR 20 (run 40878131007) and passed on
the push run 40878099563 for the same commit c0a2389: a race, not a regression.

Model: Sonnet, no reason needed (PowerShell harness code and tests, D15). Budget about 60 tool calls; at the cap, stop, commit,
report what is left. No subagents. No PC work: everything is proved on GitHub's Windows runner.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J19`). Read `harness/README.md` (watchdog section) and `jobs/J2/report.md` row 3.
- Search before writing: `python3 core/wsc.py find hang watchdog`, `find Wait-Until`.

## The race (read 2026-10-29 on main 336058c)
- `harness/core/watcher.ps1` `Handle-Hang`: dumps and archives, then `Kill-Game` (line 724), and only after it returns writes
  `runs\<utc>_hang\hang.txt` (line 725), sets `$LastHang`, and logs `HANG handled: ...` (line 728). `Kill-Game` itself waits up to
  `zombie_wait_s` for the process to go.
- `harness/tests/Test-Integration.ps1` case `hang watchdog` (line 321): waits for the fake game to exit (line 341), then at once
  asserts `hang.txt` exists and holds `no CPU-time progress` (lines 348-349). The process can be gone while the watcher is still
  inside `Kill-Game`'s polling loop, so `hang.txt` is not written yet.

## Deliverables
1. Watcher: `Handle-Hang` writes `hang.txt` (all notes so far, plus a line `kill: pending`) **before** `Kill-Game`, then rewrites it
   atomically with the kill result after (use the existing `Write-Atomic` or the same temp-and-rename pattern). A watcher killed
   mid-kill still leaves evidence. Bump `$Version` (patch) in `watcher.ps1`.
2. Test: the case waits for the completion signal, `Wait-LogMatch 'HANG handled: killed'`, before any assertion on the run folder,
   and asserts `hang.txt` holds the kill result (not `kill: pending`). Keep every existing assertion.
3. Sweep: check every other integration case for the same pattern (waiting on a side effect, process exit or file, then asserting
   on something the watcher writes later). Fix each one found the same way (wait for the watcher's own completion log line or status
   field); list every case checked and the verdict in the report. If a missing completion signal is the real gap, add the log line
   to the watcher, not a sleep to the test.
4. A way to repeat one test: `Run-HostTests.ps1` (and `Test-Integration.ps1`) gain `-Only <regex>` (case name filter) and
   `-Repeat <n>` (run the selected cases n times, fail on the first failure, print the pass count). Default behaviour unchanged.
   Unit-test the parameter handling in `Test-Unit.ps1`.

## Proof
`hang watchdog` passes 10 runs in a row on the Windows runner, plus one normal full `harness-windows` run green on the final commit.
Preferred route: a `workflow_dispatch` trigger on `gates.yml` with `only` and `repeat` inputs passed to `Run-HostTests.ps1`
(push and pull_request behaviour unchanged; mind `concurrency: cancel-in-progress`, which cancels overlapping runs on one ref).
If you cannot dispatch workflows from the session, use one temporary commit that sets `-Only 'hang watchdog' -Repeat 10` in the
harness-windows step, record its run id, then revert it. Record run ids in the report.

## Out of scope
Deploying the new watcher to the PC (`update kit=`): note it in the report as a follow-up; the next PC job ships it.
No change to watchdog thresholds, dump logic or `Kill-Game`'s zombie handling.

## Kill criteria
- The hang case still fails after deliverables 1 and 2: stop, keep the failing run's log, report what the watcher log shows.
- Any other harness case fails intermittently during the repeat runs: do not chase it; record run id and case, report it as a new job.

## Finish
Write `jobs/J19/report.md`: what changed and why, the cases checked in the sweep with verdicts, the 10-in-a-row run id and the final
full run id, deviations from this brief and why, open questions. Then `wsc reg set jobs J19 status=review report=jobs/J19/report.md`.
