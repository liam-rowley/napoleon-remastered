# J56 review

## Round 1 (2026-11-01, branch job/J56 at 6aa2db2)

**Verdict: merge.**

Fresh session (not the builder: the branch's commits carry Claude-Session 7bbb614b, this review a8f77724).

### Machines
- `python3 core/wsc.py gates`: 11 ok, 1 warn (viewer render tests skipped, no wasm build; upscale image tests skipped, no numpy or
  Pillow), 0 failed, 83.9 s.
- `python3 -m unittest tests.test_jobs`: 81 tests OK.
- `python3 tools/pr_policy.py --branch job/J56 --base origin/main` before this review: refused only for the missing review and the row
  not yet `done`, which this commit supplies.
- `wsc jobs review`: CI on job/J56 at 6aa2db2, all 8 checks passed or skipped.

### Claims against evidence
- Timings: re-measured on the PC in this session (PowerShell `Measure-Command`, warm): `jobs review` 2.5 s, `jobs review --offline`
  0.3 s. These agree with the report's 1.8 s and 0.3 s (network variance on the one fetch and the `gh` calls), against 16.8 s before.
  The cold and `view` numbers were not re-run here; they are consistent with the warm ones.
- Branch count: `git ls-remote origin 'refs/heads/job/*'` gives 29, as the report says.
- Call counts: `BranchRows.test_one_fetch_for_n_branches` asserts one glob fetch, one `for-each-ref` and one `cat-file` for 10 branches.

### The brief
Every deliverable is present: one fetch (glob, or the one branch with `--id`), the done-job skip with `--all` on `review`, `fix` and
`view`, `remote_branches` unchanged, the row read kept in one function (`branch_row_spec`, for J55), the docstring and tools row
updated, the tests the brief lists, the timings and the open question on merged branches. `docs/REVIEW.md` keeps no
`--delete-branch`. Only `jobs.py`, its tests, the report and the registries changed; nothing in `core/`. The three deviations are named
and reasoned in the report and are improvements (no fetch with nothing to read, git's stderr in the fetch error, a `done on main`
refusal instead of "has no row").

### Risk-first reading
I read `_blobs` and `branch_rows` in depth: they feed every readiness decision the autopilot acts on, so a mis-parse would start or
withhold sessions. The `cat-file --batch` parser slices the body by the byte size from the header and skips the trailing LF, handles
`missing`, and stops cleanly on cut-short output; byte slicing before decode is right for non-ASCII content. `for-each-ref
--format=%(refname:strip=4)` gives the bare `J<n>`, which is the key used. `not_ready`'s new `done on main` branch only fires when the
branch was skipped, so `--id` of a done job still reaches the branch-row check (report: `J54 is done on job/J54, not review`).

### Findings
No blocker, no should-fix.

**later**
1. `tools/verbs/jobs.py` `_blobs` and the `for-each-ref` call in `branch_rows` ignore the return code: a failing `cat-file` reads
   every row as missing ("has no row") and a failing `for-each-ref` gives every head `None`. Before J56, `_git` returned None on failure
   and behaved the same way, so this is not a regression; but a head of `None` weakens the autopilot's once-per-head rule. A non-zero
   return could raise the same `ValueError` as a failed fetch. See it fail: a fake `run` returning rc 128 for `cat-file`.
2. A glob fetch never prunes (named in the report): `--offline` can list a job branch already deleted on origin. Online is unaffected
   (names come from `ls-remote`). Adding `--prune` scoped to the job refspec would close it if merged branches are ever deleted.
3. Open question for Liam (from the report): 27 of 29 `origin/job/*` branches belong to done jobs. They now cost nothing per call; the
   brief keeps them because reports cite their shas.
