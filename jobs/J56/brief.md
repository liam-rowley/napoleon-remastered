# J56: jobs verbs fetch the job branches in one call

Phase 1, tooling (pipeline audit 2026-10-31, item 4). `branch_rows` in `tools/verbs/jobs.py` fetches every `origin/job/*` branch one at a
time: 27 branches cost 9.1 s warm and 19.7 s cold against 0.3 s with `--offline`, and 25 of the 27 are already merged. Every `jobs next`,
`review` and `fix` call, every `jobs view`, and every autopilot tick (300 s, D36) pays it, and it grows with the queue (about 18 s at 53
jobs). This job makes it one fetch, and stops reading branches whose job is already `done` on main.

Model: Sonnet. Python tooling and tests in this repo; no engine, DLL or PC work. Budget about 60 tool calls; at the cap, stop, commit,
report what is left. Subagents are not needed.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J56`). Read `docs/DECISIONS.md` (D16, D36), and in `tools/verbs/jobs.py` its docstring,
  `_git`, `remote_branches`, `branch_rows`, `Branch`, `branch_state`, `not_ready`, `pick_branch`, `lane` and every caller of
  `branch_rows` in `run()` (the `--serve` snapshot, `view`, `review`/`fix`). Tests: `tests/test_jobs.py`.
- Search before writing: `python3 core/wsc.py find jobs branch fetch`. Change `jobs.py` and its tests only; never change `core/`.
- J55 (registry rows one file per job) will change how `branch_rows` reads a row from a branch; keep the reading in one small function
  (`git show <ref>:<path>` today) so J55 changes one place.

## Target facts
Check each again before relying on it, and write the numbers in the report:
- Time `python3 core/wsc.py jobs review` and `jobs view --no-open` on the PC, warm (the second run in a row) and cold
  (no `origin/job/*` refs yet: a fresh `git clone --single-branch --recurse-submodules` under `_scratch/`), before your change and after
  it, and with `--offline`. The row's numbers are 9.1 s warm, 19.7 s cold and 0.3 s offline for 27 branches.
- How many `origin/job/*` branches exist, and how many of those jobs are `done` on main.

## Decisions already made for this job
- **One fetch.** `branch_rows` runs one `git fetch -q origin '+refs/heads/job/*:refs/remotes/origin/job/*'` (unless `--offline`), then
  reads each branch from the local remote-tracking ref (`git show`, `git rev-parse`), as `--offline` does today. With `only=<id>` it may
  fetch just that branch (one call either way). A failed fetch raises the same `ValueError` with the rerun-with-`--offline` hint.
- **Skip done jobs.** A branch whose job is `done` on main is not read (its row, review and head are not needed by any readiness rule or
  lane: `lane()` returns `done` from main's row first). `branch_rows` takes the main rows (or the set of done ids) to decide this.
  `--all` on `jobs review`, `fix` and `view` reads them anyway (for looking at an old branch); `--id` of a done job reads that one branch.
  Keep the remote branch set from `remote_branches` unchanged: `lane()` and `not_ready()` still see every branch name.
- **Fewer git calls per branch.** Read the row, the review rounds and the head with as few calls as is simple (for example one
  `git cat-file --batch` for all the blobs, or keep three calls per branch now that they are local and fast: measure and choose; say which
  in the report).
- **Branch deletion stays as it is.** Do not add `--delete-branch` to the reviewer's `gh pr merge` in `docs/REVIEW.md`: job reports and
  fix rounds cite commit shas on `job/<id>` that a squash merge does not keep on main, so deleting the branch would leave those shas
  unreachable. Say in the report how many merged branches there are; deleting them is Liam's call (an open question).
- **Out of scope:** `remote_branches` (one `ls-remote`, already one call); `red_prs`; anything in `core/`.

## Deliverables
1. `tools/verbs/jobs.py`: `branch_rows` with one fetch and the done-job skip; `--all` on `review`, `fix` and `view`; the docstring's
   paragraph on what `next`, `review` and `view` read from origin updated.
2. Tests in `tests/test_jobs.py` with a fake git that records its calls: one fetch for N branches (not N); no fetch with `--offline`;
   done jobs read zero blobs unless `--all`; `--id` of a done job still reads it; a fetch failure raises the `--offline` hint; the
   autopilot snapshot and the `review`/`fix` path still see a `review` or `fix` branch row as before (an existing readiness test kept green
   proves it).
3. The before and after timings (warm, cold, offline) for `jobs review` and `jobs view --no-open` on the PC, in the report.
4. `python3 core/wsc.py gates` green.

## Kill criteria
- The glob refspec fetch is slower than the per-branch loop on the PC, or does not update the refs the loop did: stop, report the
  timings, and propose the alternative (`git ls-remote` heads plus fetch of only the not-done branches).
- Over about 60 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J56/report.md`: what was built, the timings before and after, the git-call counts from the tests, the test list and the gates
result, deviations from this brief and why, open questions (deleting merged job branches). Then
`wsc reg set jobs J56 status=review report=jobs/J56/report.md`.
