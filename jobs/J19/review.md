# Review of J19 (Hang watchdog test race on hang.txt)

## Round 1 (2026-10-29, branch `job/J19` at 0507c06)

Reviewer: a fresh Opus 5.5 Claude Code session on the PC that built none of the branch (session `c2557374`). Checked against
`jobs/J19/brief.md`, `jobs/J19/report.md` and `docs/DECISIONS.md`. About 20 tool calls.

**Verdict: merge.**

### Machines
- CI push run 40901778677 on 0507c06 (the report commit): `gates`, `proxy` and `harness-windows` succeeded; `policy` is skipped on push.
- 10 runs in a row: dispatch run 40900019359 on 69a6732. Its log shows `run 1/10` to `run 10/10`, then
  `PASS hang watchdog ... (10/10 runs passed)` and `integration : 10 passed, 0 failed (1 cases matched -Only 'hang watchdog')`.
  Opened and read, not taken from the report.
- Push runs 40898886583 (8be13f7) and 40900010030 (69a6732) succeeded, as the report says. Dispatch 40898907246 is correctly
  labelled "not proof" (it ran the whole suite once because of the `$script:Only` collision).
- Local `wsc gates` on the PC: 11 ok, 1 failed. The failure is `tests`, in `test_job_sh` (path separators: Git Bash resolves to
  a POSIX `/` join) and `test_pc_deploy` (`running_check` on the real host). The branch touches neither file; these are the
  Windows-host failures the report and J6 already name.
- Local `Run-HostTests.ps1 -Suite unit` under Windows PowerShell 5.1: 29 passed, 0 failed before my fix; 30 passed after it.

### Brief
- Deliverable 1 (watcher): present. `Handle-Hang` writes `hang.txt` with `Write-Atomic` and `kill: pending` before `Kill-Game`,
  then rewrites it atomically ending `kill: killed` or `kill: ZOMBIE ...`, then logs `HANG handled`. `$Version` is 1.0.1. Thresholds,
  the dump logic and `Kill-Game` are unchanged (out of scope, respected).
- Deliverable 2 (test): present. It waits for `HANG handled: killed`, matching only text logged since the case started, then asserts
  `kill: killed` and no `kill: pending`. Every old assertion is kept; the folder check is tightened to "exactly one new `*_hang`".
- Deliverable 3 (sweep): present, with a table of every case. I spot-checked `zombie`: `Kill-Game` writes the zombie record before
  it returns `$false`, and the case asserts the file only after the kill job's `.done`. The claim holds.
- Deliverable 4 (`-Only`/`-Repeat`): present in both scripts, with unit tests (selection rules, parameter defaults read from the AST,
  the name-collision guard, and an end-to-end probe in a child PowerShell).
- Proof: met, through `workflow_dispatch` (the brief's preferred route). The dispatch inputs reach the step through env, not
  interpolated into the script; dispatch runs have their own concurrency group, and `gates`/`proxy` are skipped on dispatch.
- Deviations named in the report: Opus instead of Sonnet; two extra fixes (the version literal in the update case, the
  `$script:Only` collision), both with guards and both inside the harness-tests scope. Accepted.

### Risk-first reading
I read `Handle-Hang` and `Test-Lib.ps1` `Invoke-Selected`/`Test-Case`/`Finish-Tests` in depth:
- `Handle-Hang` touches the real PC game process. A wrong order there loses hang evidence.
- A runner bug in `Test-Lib` would make every harness test report a pass it did not earn.

Both are correct:
- `Write-Atomic` uses the same BOM-less `$Utf8` encoding the old `WriteAllText` did.
- A filter that matches nothing now fails the suite.
- `$script:Pass` counts passed runs, so `-Repeat 1` behaves exactly as before.

I skimmed `gates.yml`, the README and the registries.

### Findings
**Blocker:** none.

**Should-fix (fixed by me on the branch):**
1. `harness/tests/Test-Integration.ps1:7` (fixed in 7d7eb7a): `-Repeat n` without `-Only` repeated every integration case.
   - **What fails:** the file's own header says the suite is not repeat-safe. Auto-restore counts exactly one expired lock, and the
     update rollbacks build on `update: a good kit`. So a dispatch with `repeat=10` and an empty `only` fails cases that are fine,
     which reads as new flakes.
   - **How to see it fail before the fix:** `gh workflow run gates.yml --ref job/J19 -f repeat=3`.
   - **Fix:** the script now refuses that combination as its first statement (`exit 2`, before the watcher starts). The unit case
     `static: Test-Integration refuses -Repeat without -Only ...` guards it, statically, so the guard can never start a watcher on a
     host if it breaks.
   - **Checked:** `Test-Integration.ps1 -Repeat 2` printed `FAILED: -Repeat needs -Only ...` with exit 2; unit 30 passed.

**Later (this repo):**
2. `harness/tests/Test-Lib.ps1` `Invoke-Selected`: the comment says every local a case body can see carries a `tc` prefix. The
   parameters `$name`, `$body`, `$only`, `$repeat` and `$onStart` do not, and case bodies run in that dynamic scope.
   - **What fails:** nothing reads them today (checked with grep). A future body that reads an uninitialised `$repeat` or `$only`
     would silently get the runner's value.
   - **Fix, when Test-Lib is next touched:** rename the parameters to `$tcName` and the like, or run `$body` through
     `.GetNewClosure()`.
3. D15 (model choice): the job ran on Opus against a Sonnet row and brief. The report names it, but nothing checks it.
   - **Proposed gate:** `wsc jobs check` (`tools/verbs/jobs.py`) compares the report's `Model:` line with the row's `model` and
     requires the deviation to be named under Deviations. Then the next mismatch is a gate failure, not a reviewer's catch.
4. Follow-up already in the report: watcher 1.0.1 is not on the PC yet (`update kit=`); the next PC job ships it.

### Status
Merge verdict: row set to `status=done review=jobs/J19/review.md`.
