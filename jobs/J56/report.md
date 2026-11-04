# J56 report: jobs verbs fetch the job branches in one call

`branch_rows` (`tools/verbs/jobs.py`) now makes one `git fetch` for all the job branches instead of one per branch. It skips the
branches of jobs already `done` on main and reads the rest with two local git calls in total. On the PC, a warm `jobs review` went from
16.8 s to 1.8 s, a cold one from 34.1 s to 3.9 s, and `--offline` from 2.0 s to 0.3 s. The page `jobs view` writes is byte-identical
before and after.

## What exists
- `branch_rows(root, branches, offline, jobs_path, only=None, done=(), run=subprocess.run)`:
  - Reads only the job branches not in `done` (`only` = `--id`: that one branch, done or not). With nothing to read it makes no git
    call at all.
  - Unless `--offline`, one fetch: `git fetch -q origin +refs/heads/job/*:refs/remotes/origin/job/*` (`--id`: just
    `refs/heads/job/<id>`). A failed fetch raises `ValueError` with git's message and the rerun-with-`--offline` hint.
  - One `git for-each-ref refs/remotes/origin/job/` for every head sha, and one `git cat-file --batch` (`_blobs`) for every row and
    `review.md`. Before this job it was a fetch, two `git show` and a `rev-parse` per branch.
- `branch_row_spec(ref, jid, jobs_path)`: the one place that says where a branch keeps a job's row, as a blob spec plus its parser.
  J55 changes this one function.
- `done_ids()` in `run()`: the `--serve` snapshot (and so `--auto`), `view` and `review`/`fix` without `--id` pass main's done ids.
  `--all` (new, on `review`, `fix` and `view`) passes none.
- `not_ready()`: when a branch is missing from `on_branch` because its job is done, review/fix now return `<id> is done on main`
  instead of "has no row". `remote_branches` is unchanged, so `lane()` and `not_ready()` still see every branch name.
- The module docstring paragraph on what `next`, `review`, `fix` and `view` read from origin, the usage line and the tools row are
  updated.

## Evidence
On the PC, 2026-11-01, Git Bash. Times are wall-clock for `python3 core/wsc.py jobs …`. Every run includes `print_red_prs` (one `gh pr
list`), and `review` also includes `branch_checks` (one `gh api`). "Warm" is the second run in a row in the main clone. "Cold" is the
first run in a fresh `git clone --single-branch --recurse-submodules` under `_scratch/`, which has no `origin/job/*` refs.

| run | before (origin/main 32b0d15) | after (job/J56) |
|---|---|---|
| `jobs review`, warm | 16.8 s (17.6 s first) | 1.8 s |
| `jobs view --no-open`, warm | 20.2 s (18.5 s first) | 1.9 s |
| `jobs review`, cold | 34.1 s | 3.9 s |
| `jobs view --no-open`, cold (refs deleted after the cold review) | 16.8 s | 2.8 s |
| `jobs review --offline` | 2.0 s | 0.3 s |
| `jobs view --no-open --offline` | 2.3 s | 0.3 s |
| `jobs view --no-open --all`, warm | – | 1.9–2.2 s |

- Branches: 29 `origin/job/*` branches. 27 of those jobs are `done` on main; J16 (blocked) and J56 (this job) are not. The brief's row
  counted 27 branches at 9.1 s warm, 19.7 s cold and 0.3 s offline. This PC was slower than those numbers before the change (16.8 s, 34.1
  s, 2.0 s).
- The cold "view" row before is not truly cold: deleting the refs left the fetched objects in the clone. The after row was measured the
  same way, so the two compare like for like.
- Kill criterion not met: the glob fetch is faster than the per-branch loop even cold, where it downloads every job branch in one call
  (3.9 s against 34.1 s). It updates the same `refs/remotes/origin/job/<id>` refs the loop did (`git for-each-ref` after the cold run:
  every branch present).
- Same output: `jobs view --no-open --offline` written by origin/main's `jobs.py` and by this branch's, and with `--all`, are
  byte-identical once the time stamp is removed (`diff`: 0 lines). `jobs review` names the same "nothing waiting" state.
  `jobs review --id J54` (a done job) reads that branch and refuses with `J54 is done on job/J54, not review`, as before.
- Calls per branch: I kept two batched local calls, `for-each-ref` and `cat-file --batch`, rather than three per branch. Offline, three
  calls per branch for 29 branches cost about 1.7 s on Windows, where each git process start costs about 20–30 ms.

## Tests
`tests/test_jobs.py` class `BranchRows`, with a fake git that records its calls:
- `test_one_fetch_for_n_branches`: 10 branches give one fetch (the glob refspec), one `for-each-ref` and one `cat-file`, so 3 git
  calls where there were 40.
- `test_offline_makes_no_fetch`.
- `test_done_jobs_read_no_blobs_unless_all`: done jobs read no blob; with every job done there are no git calls at all; with no done set
  (`--all`) every branch is read.
- `test_id_of_a_done_job_still_reads_that_branch_only`: one fetch of `refs/heads/job/<id>`, and blobs from that branch only.
- `test_a_missing_file_reads_as_none`: a `missing` reply from `cat-file` gives 0 rounds.
- `test_a_fetch_failure_names_offline`.
- `test_a_done_job_skipped_on_the_branch_is_refused_as_done`.
- `test_blobs_reads_a_real_repo`: `_blobs` against this repo's real git (one present path, one missing).

The existing readiness, autopilot and `review`/`fix` run() tests are unchanged and green, so a `review` or `fix` branch row is still
seen as before. `python3 -m unittest tests.test_jobs`: 81 tests OK. `python3 core/wsc.py gates`: 11 ok, 1 warn (viewer render tests
skipped, no wasm build), 0 failed.

## Deviations
- With `--id`, the fetch names that one branch, as the brief allows. With nothing left to read (every job branch done), I skip even the
  fetch; the brief only asked for one fetch.
- A fetch failure now gives one message for every branch, carrying git's stderr, instead of `could not fetch job/<id>`. It still names
  `--offline`.
- I added a refusal for a done job seen from the server or autopilot path (`is done on main`), so a skipped branch is never reported
  as "has no row".

## Open questions
- Merged job branches: 27 of the 29 `origin/job/*` branches belong to done jobs. They stay, as the brief says (reports and fix rounds
  cite shas that only those branches keep), and they cost little now that they are neither fetched one by one nor read. Deleting them
  is Liam's call.
- A glob fetch never prunes: a deleted remote branch keeps its local `origin/job/*` ref. Online this is harmless, because the branch set
  comes from `ls-remote`. `--offline` may still show it, as it did before this job.
