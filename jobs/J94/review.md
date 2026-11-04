# Review of J94 (Napoleon tools, tests and gates: small fixes)

## Round 1 (2026-11-04, branch `job/J94` at a65ff3e)

**Verdict: fix.** One blocker: the new `BARE_BASH` rule flags a file that merged to `main` after the builder's last full run, so the `tests` gate is red on this branch.

Reviewer: a fresh session that built none of the branch. Checked against `jobs/J94/brief.md` and `jobs/J94/report.md`.

## Blocker
- `python3 -m unittest tests.test_repo_rules` fails `ThisRepo.test_no_bare_bash_in_tests_and_tools`: `tests/test_viewer_prune.py:37: b = shutil.which('bash')`.
  That line came in with J97 (`c3ac8d5`, merged into the branch by `ce95c94`). It is `find_bash()`, which rejects the `system32` (WSL) launcher itself,
  so it is a legitimate use. The brief says "a new hit in the tree is fixed at the caller; allowlist only with a reason in `BARE_BASH_ALLOWED`".
  Fix: either route it through `bash_for_tests()` or add `'tests/test_viewer_prune.py::find_bash': '<why: it refuses the system32 launcher>'` to `BARE_BASH_ALLOWED`.
  The builder's `gates --fast` skips the tests gate and the full run was at `3aa3889`, before the merge of `main`, which is how this slipped through.
  Re-run the full `gates` (or at least `python3 -m unittest tests.test_repo_rules`) after the fix and after any further merge of `main`.

## What checks out (against the branch)
- Items 1, 2, 3, 4, 6: the diff matches the report. `hotkeys` reads games.json and `hotkeys_known.json` with no `tests/` import, and `canon()` replaces `capitalize()`.
  `quoted_by_a_row` needs one table row with `wsc.toml`, the section and the value. `BARE_BASH` runs over the whole text with a `file::function` allow-list.
  `watcher_detail`, the `LOCALAPPDATA/Git` removal and `pillow_result` are present with tests. Fixtures are renamed and the real-table test added. The `shot_sheet` header and row are fixed.
  The four test modules pass here apart from the blocker above (98 of 99).
- Deviation, item 5 stopped: acceptable. Registry-only leaves the committed ini stale (the `tests` gate fails) and regenerating it changes the DLL build id (rule 79, 20 PC passes), which a `needs_pc: false` job cannot do. It is the brief's own kill criterion. The open question is the hand-off: ride on the next PC job that changes `proxy/napoleon/`; Liam to move triage row J23-L1 there.
- Deviation, item 7 split: acceptable. Policy forbids a job branch changing another row, and an entry naming an absent row fails rule 76, so J100 on `plan/J100-release-core-row` (PR #194, Liam merges, D50) with `PROMOTIONS['release/core'] = None` plus a comment here is the only route that passes. Follow-up once #194 is on main: set `PROMOTIONS['release/core'] = 'J100'` and add `('release/core', 'J100')` to `test_promotions_name_rows_that_exist`. Not a blocker; Liam should queue it with the merge of #194.
- Deviation, `uikit/napoleon/changes.py` allow-listed rather than fixed: acceptable (outside the brief's files, reason recorded).
- No game, PC, watcher or `core/` change on the branch.

## Not decided here
- Policy at this head lists only the review and the `done` row as open. The report was committed by the orchestrator from the builder's hand-back (same session id as the builder), so it is not an own-review problem.
- CI on `a65ff3e` was still running when this was written; the local `tests` failure is enough for the verdict.
