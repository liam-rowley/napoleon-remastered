# J42 review: CI reliability: no red check a branch did not cause

2026-10-30. Independent review of `job/J42` at `7a19bd9` (the builder's head), by a fresh session that did not build it
(`docs/REVIEW.md`), session `27970a04-43ed-413e-884f-c0142548397a`.

**Verdict: merge.**

Every deliverable is present and follows the brief's decisions: the failure table generated from the API with its classes in code;
`gates.yml` on push and dispatch only with `policy` in its own `pull_request` workflow; the `notify` jobs as the only ones with
`pull-requests: write`; each harness race fixed in the test or the watcher with a static unit guard; the wine smoke test and the
harness unit suite on local routes with injected-probe unit tests; `proxy/runs/` out of the proxy input set; `wsc jobs next|review|view`
listing red pull requests first; no `core/` change; no change to what `gates`, `proxy` or `harness-windows` test. The deviations
(integration suite CI-only under the kill criterion, one `gates.yml` run plus a small `policy.yml` run, the start wait raised alongside
the measured start, the builder's own PR for proofs c and d) are named and sound.

## Machines
- `python3 core/wsc.py gates` on the PC: 11 ok, 1 warn (`hooks`: this clone's `core.hooksPath` is the absolute form), 0 failed;
  `tests` 207 passed in 185 s with `--docker all`, `--docker smoke` and the harness unit suite running (every input changed).
- `python3 tools/pr_policy.py --branch job/J42 --base origin/main`: refused only for the missing review and the `review` status.
- CI on `7a19bd9`: run 40976935315 (`changes`, `gates`, `proxy`, `harness-windows` green); `policy` run 40976938009 red by design,
  one comment. `wsc jobs review` printed that red check first.

## Claims against evidence
- a) 40972586726 (`auto-restore` 20/20), 40972589614 (`update: a good kit` and `rollback 1`, 40 passed, 0 failed), 40972592575
  (`hang watchdog` 20/20): all `workflow_dispatch` on `97358f5`, `harness-windows` success.
- b) 40972595755 and 40975999320 opened: `integration : 25 passed, 0 failed`, `watcher up after 24930 ms`; the push run 40972531553
  ran the full suite green.
- c) `97358f5` and `7a19bd9` each have exactly one `gates` run and one `policy` run.
- d) PR #57 carries one `ci_notify` comment per failed run (seven at review time), none repeated; the `--dry-run` against run
  40976938009 says the comment exists.
- The report's "17 to 35 s" start: `watcher up after 24930 ms` in run 40972595755 (above); the 39.9 s is in run 40970029940.

## Risk-first reading
`harness/core/watcher.ps1` (runs on the PC, holds the game lock) and the two workflows with `tools/ci_notify.py` (the only write
permission in CI). The watcher change is two log lines, `Up-Ms` guarded by a try, and `Write-Alive` moved before the first housekeeping
pass: an earlier heartbeat, nothing else. `notify` has `pull-requests: write` on that job only, comments once per run attempt by marker,
and only sees same-repository branch names. `Hash-OrAbsent`: `Test-Integration.ps1` sets `$ErrorActionPreference = 'Stop'`, so a
missing file throws `ItemNotFoundException` and takes the `absent` branch.

## Findings
**should-fix, fixed on the branch**
1. `tools/ci_failures.py` (render): the report says each row records "whether the same commit passed that job in another run"; the
   generator fetched `passed_elsewhere` but never rendered it, so the flaky class had no evidence column. Fixed: column "same commit
   passed elsewhere"; `tests/test_ci_failures.py`.
2. `tools/ci_failures.py` (fetch): `gh run list -L 300` is the newest 300 runs, and after J42's dispatches that reaches back only to
   15:06 UTC on the 29th: a regeneration of the committed table gave 31 rows, not 53. Fixed: the API's `created=since..until` filter,
   paginated (`list_runs`, unit test); regenerated: 53 rows, identical to the committed ones plus the new column.
3. Proof d covered `policy.yml`'s `notify` only; `gates.yml`'s `notify` (a different `if`, `needs` across four jobs) had never run.
   Proved here: throwaway commit `47c00f9` (a failing unit test) on this branch, push run 41018232019: `gates` failed, `notify`
   succeeded, one comment on PR #57; reverted in `71dd53b`. Still unproven: `if: failure()` when `proxy` and `harness-windows` are
   skipped (a branch that touches no proxy or harness input); this branch changes the workflows, so every input counts as changed and
   the case cannot be built before the merge. The first red `gates` on a docs-only branch after the merge proves it; if no comment
   appears there, the fix is `if: ${{ !cancelled() && contains(needs.*.result, 'failure') }}`.

**later**
4. `.github/workflows/gates.yml`: the `pull_request` run used to test the merge of the branch with `main`; the push run tests the
   branch tip. A branch green on its tip that breaks only once merged (two branches each changing `registries/jobs.jsonl` cleanly) is
   now caught by `main`'s push run after the squash, not before. If that bites, a merge queue (`merge_group` event) is the route.
5. `docs/CI_FAILURES.md`: 6 of the 13 `flaky` rows now show "no" in the new column (the commit never had a second run); their class
   rests on the builder's log reading, which the note column carries. The class definition ("the same commit passed in another run")
   is stricter than the table; keep the column as the evidence and the note as the reasoning.
6. The lost runner (40972644940) and the shallow-tag `pin_problems` reading in warscape-core stay as the report's open questions.
7. Both workflows have a job named `notify`, so a commit shows two `notify` checks; cosmetic.

## For the next session
- After the merge, one `gh workflow run gates.yml --ref main` (the full suite on `main`), as the report asks; the 20-on-main count
  the row asks for is a dispatch loop the next session fires and reads once.
- Every open job and brief branch gets the new CI on its next push: one `gates.yml` run plus `policy.yml`. No branch is stranded.
