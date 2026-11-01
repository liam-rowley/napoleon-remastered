# J57: Review merge cannot run on a skipped policy; a failed changes job runs every slow job; Deploy tests ignore the live game

Phase 1, tooling. From J54's review round 1, "later" items 1 to 3 (`jobs/J54/review.md`), which Liam asked to build. Three separate
holes, each with its own fix and its own test. No core change, no PC, no DLL.

Model: Sonnet (medium). Python, a workflow file and docs in this repo.
Budget about 60 tool calls; at the cap, stop, commit, report what is left. Subagents are not needed.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J57`). Read `jobs/J54/review.md` (round 1, later items 1 to 3) and `jobs/J54/report.md`
  (Open questions), `docs/REVIEW.md` ("Merging"), `.github/workflows/gates.yml` (job `changes` and the three slow jobs) and
  `.github/workflows/policy.yml`, `tools/verbs/jobs.py` (`review_steps`), `tests/test_jobs.py` (`test_review_steps_mark_the_draft_ready_before_the_merge`),
  `tests/test_pc_deploy.py` (`Deploy`, `test_running_check`) and `core/proxy/tools/pc_deploy.py` (`require_closed`, `running_check`, `windows_images`).
- Check each target fact again before relying on it.

## Problem 1: a merge can land on a skipped `policy`
Today the reviewer commits and pushes the review while the pull request is still a draft, then runs `gh pr ready`, then
`gh pr merge --auto --squash` (`review_steps`, `docs/REVIEW.md` "Merging"). On a draft, `policy` is skipped on every push
(`policy.yml`: `if: github.event.pull_request.draft == false`), and a skipped check counts as passed. `gh pr merge --help`
(gh 2.92.0): "If required checks have not yet passed, auto-merge will be enabled", so when they have passed, it merges at once. `gates`
takes about 40 s; if it has finished on the review commit by the time the two commands run, the pull request is already clean and
merges before the `ready_for_review` run of `policy` registers. CI then never enforced `pr_policy` on the merged head (J54 PR 96,
run `41287792800`, is the case shape: `gates` green, slow jobs skipped).

Decision (Liam asked to build the review's first option): **mark the pull request ready before the review commit is pushed**, so the
pushed head gets a real `policy` run (`synchronize` on a non-draft pull request). Order in `review_steps` and `docs/REVIEW.md`
"Merging": commit the review and the row locally, run `python3 tools/pr_policy.py --branch job/<id> --base origin/main` on the local
branch (it must say ok), `gh pr view` (create the draft first if there is none), `gh pr ready job/<id>`, `git push`,
`gh pr merge job/<id> --auto --squash`. A non-merge verdict is unchanged: push, leave it a draft, never `gh pr ready`.

The cost is one `policy` run on the pre-review head (`ready_for_review` on a head with no merge verdict) that is red by design, and
the push usually cancels it (`policy.yml` concurrency group, `cancel-in-progress`). If it does finish red it must not comment:
`policy.yml`'s `notify` job gets `github.event.action != 'ready_for_review'` in its `if:`, so the expected red is not told.
(A red `policy` on an old head does not block the merge: required checks are read on the new head.)

Fix location: this repo (`tools/verbs/jobs.py`, `docs/REVIEW.md`, `.github/workflows/policy.yml` comment and `if:`).
Proof: `tests/test_jobs.py` asserts, on `review_steps` text, the order local `pr_policy.py` < `gh pr ready` < `git push` <
`gh pr merge --auto --squash`, and that the non-merge branch of the text says never `gh pr ready`; a test (repo-rules or
`tests/test_jobs.py`) reads `policy.yml` and asserts `notify`'s `if:` excludes `ready_for_review` while `policy`'s still skips
drafts. Update the old order test; grep for every living copy of the old order (`docs/REVIEW.md`, `policy.yml` header, `jobs.py` docstring, CLAUDE.md) and fix it.
Live evidence: J57's own review merge follows the new order; the report says what to look at (`policy` on the merged head is a
real, non-skipped run) and does not claim it.

## Problem 2: a failed `changes` job skips every slow job, and a skip counts as passed
`proxy`, `viewer` and `harness-windows` have `needs: changes` and an `if:` on `needs.changes.outputs.<set> == 'true'`
(`gates.yml`, the three `if:` lines). If `changes` fails (its `diff` or `run` step), `needs` skips all three; branch protection reads
a skip as passed, `changes` is not a required check, and only `notify` says anything. Fix: each `if:` becomes
`!cancelled() && <the existing dispatch term> && (needs.changes.result != 'success' || <the existing output test>)`, keeping each job's
current `workflow_dispatch` behaviour exactly (`proxy` and `viewer` never on dispatch, `harness-windows` always on dispatch). With a
status function in the `if:` the implicit `success()` is gone, which is the point: the job runs when `changes` failed. A broken
`changes` outputs nothing, so the pass-marker steps (`*_tree != ''`) already do not save a marker: keep it so.

Fix location: `.github/workflows/gates.yml` only. Proof, two parts:
1. A host test (`tests/test_repo_rules.py` or a new `tests/test_workflows.py`) that reads the three `if:` lines from the file (text
   or the repo's existing parser; no new dependency) and asserts each contains `!cancelled()` and `needs.changes.result != 'success'`,
   that the dispatch behaviour per job is as above, and that the test fails against the pre-J57 lines.
2. One CI run: push a throwaway branch `scratch/j57-changes-fail` from the finished branch with `exit 1` added to `changes`' `diff`
   step, and read with `gh run view` that `proxy`, `viewer` and `harness-windows` ran (or were not skipped) and `notify` ran. Record the
   run id in the report, delete the scratch branch, and do not open a pull request for it. If it cannot be done after two honest
   attempts, the host test is the proof; say so in the report.

## Problem 3: `Deploy` tests depend on the real game being closed
`tests/test_pc_deploy.py` `Deploy` calls `pd.install` and `pd.uninstall` (lines 94 to 270, about 17 calls) without `assume_closed`,
and nothing stubs the process check, so `require_closed` runs `tasklist` for the real `Napoleon.exe`. `wsc gates` (the `tests` gate)
therefore fails on the PC whenever the game runs: `refusing: tasklist: Napoleon.exe is running` (J52 review, 8 errors; J54 report;
J40 report). Fix: `Deploy.setUp` patches the process check so it reports nothing running (`mock.patch.object(pd, 'windows_images',
...)` returning an empty set is the narrowest, and keeps `require_closed` and `running_check` under test; if another seam is
smaller, use it and say why), with `addCleanup`. The guard's own tests keep their explicit patches and `images=` arguments
(`test_running_check`, `HarnessKit`), and must still prove that `install` refuses a running game.

Fix location: `tests/test_pc_deploy.py` only. `pc_deploy.py` is in `core/`: do not touch it. The same fix could go to the core's own
test copy, if one exists; that is a warscape-core backlog line in the report, not part of this job.
Proof: a new test that makes the lowest layer report the game running (patch `os.name` to `nt` and `pd.subprocess.run` to return a
`tasklist` CSV containing `"Napoleon.exe"`, or equivalent) and shows that, with `Deploy`'s setUp in force, `pd.install` still passes;
and the existing refusal test still fails closed without the setUp patch. It must pass on Linux CI and on the PC with the game open
(do not start the game: simulate it).

## Deliverables
1. Problem 1: `review_steps`, `docs/REVIEW.md` "Merging", `policy.yml` (`notify` `if:` and the header comment), the tests above.
2. Problem 2: `gates.yml` (three `if:` lines plus a short header comment line), the host test, the scratch-branch run id.
3. Problem 3: `Deploy.setUp` and its test.
4. Every living copy of the old review order or the old `if:` claims fixed (grep first); the J54 header text in `gates.yml` and
   `policy.yml` stays accurate.
5. `python3 core/wsc.py gates` green (the game closed or not).

## Out of scope
- `gates` itself skipping on an unchanged tree; changing which checks are required; a `policy` job for drafts (the review's second
  option); anything in `core/`.

## Kill criteria
- The `if:` form is rejected by GitHub (workflow does not start) or `changes` failing still skips a slow job in the scratch run: stop,
  report the run id and the expression; do not merge a guess.
- A test needs a new dependency or a change under `core/`: stop and ask.
- Over about 60 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J57/report.md`: what was built per problem, the scratch run id, the tests added, the gates result, deviations from this
brief and why, open questions. Then `wsc reg set jobs J57 status=review report=jobs/J57/report.md`.
