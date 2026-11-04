# J54 review

## Round 1 (2026-11-01, branch job/J54 at cb35760)

**Verdict: merge.**

Reviewer: session 6b736c90, a fresh chat. It wrote neither report.md nor any commit on the branch.

### Machines
- `wsc gates`: 11 ok, 1 warn (`tests`: 431 host tests passed, 14 skipped for numpy/Pillow and an unbuilt viewer), 0 failed; the game was closed, so `test_pc_deploy` passed.
- `tests.test_jobs`, `tests.test_ci_notify`, `tests.test_changed_inputs`: ok once the J54 row was set (a run while this review.md existed without the row failed only `ThisRepo.test_the_queue_passes_jobs_check`, as it should).
- `pr_policy.py --branch job/J54 --base origin/main`: refused only for the verdict and the `done` row this round sets; ok after (below).
- `wsc jobs review --id J54`: no red check on the branch; PR #96 is a draft and its `policy` was skipped, as designed.

### Claims against evidence
- Run `41286632065` (commit `92eef49`): `changes`, `gates`, `proxy`, `viewer` and `harness-windows` all success (read with `gh run view`).
- Run `41287792800` (commit `e30d612`): `changes` and `gates` success; `proxy`, `viewer` and `harness-windows` skipped. The `changes` log
  has the summary lines naming run `41286632065`, its commit and the `gh run download ... -n proxy-d3d9-napoleon` command.
- Cache scoping, the replay table and the `lookup-only` deviation are argued in the report with sources; the replay script lives in a
  scratchpad, so its numbers are not reproducible from the repo. Not a finding for this job: the numbers only size the benefit.

### Brief
All seven deliverables are present. The two deviations (an exact-key full restore instead of `lookup-only` plus a second restore;
gh's `{owner}/{repo}` placeholders) are named and argued, and both are simpler than the brief's route. Cancelled counting as red in
`branch_checks` is named. Nothing in `core/`; the input sets and `pr_policy.py` are unchanged.

### Risk-first reading
I read in depth what can let unverified code reach main: the `changes` job (restore, `decide`, outputs), the marker save steps and
their `if:`s, and `policy.yml`'s draft skip. The tree hash is over `git ls-tree -r --full-tree` entries (mode, object, path), so the
`core` gitlink pins the core commit; a workflow file is in all three sets, so any CI change invalidates every marker; a marker is
written only on `success()` of a push run, never on `workflow_dispatch`; a cache error (`continue-on-error`), an empty hash or a marker
without `run=<digits>` runs the job. `decide` is safe under `bash -e` (the `[ -n "$4" ] &&` short-circuit is not the list's last
command). The `jobs.py` changes (check reader, draft step, ready-before-merge) are covered by the new tests and skimmed.

### Findings
**blocker**: none. **should-fix**: none.

**later**
1. **`gh pr ready` then `gh pr merge --auto` can merge on a skipped `policy`** (`docs/REVIEW.md` "Merging", `tools/verbs/jobs.py`
   `review_steps`). The report raises this as an open question; it is more than a theory. `gh pr merge --help` (gh 2.92.0): "If required
   checks have not yet passed, auto-merge will be enabled", i.e. when they have passed it merges at once. A reviewer who pushes the
   review commit while the pull request is a draft gets a *skipped* `policy` on that head. If `gates` on it has finished by the time
   the reviewer runs `gh pr ready` and `gh pr merge --auto` (a minute of tool calls is enough; `gates` takes about 40 s), the pull
   request is already clean and merges before the `ready_for_review` run of `policy` registers. To see it: on a report-only head with
   `gates` green, run the two commands back to back and watch `policy` on the merged head. The local `pr_policy.py` step still runs
   the same rule, so a reviewer following the steps cannot slip a non-`merge` branch through; what is lost is CI enforcing it on a
   session that skips the step. Options for Liam: `gh pr ready` before pushing the review commit (the review push then runs `policy`
   for real on the merge head, at the cost of one red `policy` and one `ci_notify` comment on the old head), or a `policy` job on drafts
   that passes only when `pr_policy.py` would (no red, no bypass).
2. **A failed `changes` job skips the slow jobs, and a skip counts as passed** (`.github/workflows/gates.yml` lines 146-148, 190-192,
   235-238). This predates J54, but J54 adds steps to `changes` and the brief's "fails safe" rule does not cover it: if the `run` step
   (or the `diff` step) fails, `proxy`, `viewer` and `harness-windows` are skipped through `needs`, and branch protection reads that as
   passed. `changes` is not a required check, so only `notify` would say so. A guard: give each slow job
   `if: ${{ !cancelled() && (needs.changes.result != 'success' || needs.changes.outputs.<set> == 'true') }}` (plus the dispatch term),
   so a broken `changes` runs everything.
3. **`tests.test_pc_deploy.Deploy` fails locally whenever the real game runs** (report "Open questions"): a core item for
   warscape-core `docs/BACKLOG.md`, as the report says; J52's review round 1 noted the same.

### Rule changes for other open branches
`policy` now skips draft pull requests. No open job branch has a pull request yet except this one, so nothing is stranded; reviews of
branches built before J54 (no draft) follow `docs/REVIEW.md` as before (`gh pr create`, then `gh pr ready` is a no-op).
