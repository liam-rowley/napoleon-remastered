# J57 report: review merge cannot run on a skipped policy; a failed changes job runs every slow job; Deploy tests ignore the live game

Built: the three holes from J54's review round 1 ("later" items 1 to 3), each with its fix and its test, nothing in `core/`. The
reviewer now marks the pull request ready before pushing the review commit, so the merged head gets a real `policy` run; a failed
`changes` job no longer skips `proxy`, `viewer` and `harness-windows`; and the `Deploy` host tests no longer fail when the real
`Napoleon.exe` is running.

## What was built
### Problem 1: a merge cannot land on a skipped `policy`
- `tools/verbs/jobs.py` `review_steps`: a merge verdict now says to commit the review and the row locally without pushing, then in
  this order: local `pr_policy.py` (must say ok); `gh pr view` (create the draft if none); `gh pr ready`; `git push`;
  `gh pr merge --auto --squash`. The non-merge branch says push, leave the draft open, never `gh pr ready`. The module docstring is updated.
- `docs/REVIEW.md` "Merging": the same five steps, numbered, with the reason (a draft's skipped `policy` counts as passed).
- `.github/workflows/policy.yml`: `notify`'s `if:` is `failure() && github.event.action != 'ready_for_review'`, so the red-by-design
  run on the pre-review head does not comment; `policy`'s own `if:` still skips drafts. A header comment explains the order.
- Other copies of the old order: none outside `jobs/J54/*`, which is history.

### Problem 2: a failed `changes` job runs the slow jobs
- `.github/workflows/gates.yml`, three `if:` lines wrapped in `${{ }}`:
  - `proxy`: `!cancelled() && github.event_name != 'workflow_dispatch' && (needs.changes.result != 'success' || needs.changes.outputs.proxy == 'true')`
  - `viewer`: the same with `viewer`.
  - `harness-windows`: `!cancelled() && (github.event_name == 'workflow_dispatch' || needs.changes.result != 'success' || needs.changes.outputs.harness == 'true')`
- A two-line header comment says why. The pass-marker steps are untouched: a broken `changes` outputs nothing, so the
  `*_tree != ''` guards stay false.

### Problem 3: `Deploy` tests and the live game
- `tests/test_pc_deploy.py` `Deploy.setUp` patches `pd.windows_images` to return an empty set (with `addCleanup`), the narrowest
  seam: `require_closed` and `running_check` stay real. The guard's own tests (`test_running_check`, `HarnessKit`) keep their explicit patches.

## Tests added or changed
- `tests/test_jobs.py`: the old order test is replaced by `test_review_steps_mark_the_pull_request_ready_before_the_push`. It asserts
  `pr_policy` < `gh pr view` < `gh pr ready` < `git push` < `gh pr merge`, "do not push yet", and that the non-merge branch says
  "never gh pr ready".
- `tests/test_workflows.py` (new, no dependency): reads the job `if:` lines as text and evaluates each slow job's expression for every
  event / `changes` result / output combination, including GitHub's implicit `success()`. The three jobs contain `!cancelled()` and
  `needs.changes.result != 'success'`; a failed or skipped `changes` runs all three on push; push with a good `changes` and dispatch
  behave as before (`proxy` and `viewer` never run on dispatch, `harness-windows` always does); the pre-J57 expressions fail the same
  check; six `*_tree != ''` guards remain; `policy` still skips drafts and still runs on `synchronize`; `notify` excludes `ready_for_review`.
- `tests/test_pc_deploy.py`: `TasklistSaysRunning` simulates the game at the lowest layer;
  `test_install_ignores_a_running_game_with_the_setup_patch_in_force` runs `install`, `status` and `uninstall` under it;
  `test_the_guard_still_refuses_a_running_game_without_this_patch` shows `install` refuses with
  `refusing: tasklist: Napoleon.exe is running` and installs nothing.

## Evidence
- Scratch run for problem 2 (D38): branch `scratch/j57-changes-fail` = this branch plus `exit 1` at the top of `changes`' `diff`
  step; gates run `41492174324`: `changes` failed (by design), and `gates`, `proxy`, `viewer` and `harness-windows` all ran and succeeded (none skipped); `notify` ran (success); the run's conclusion is failure only because `changes` failed (read 2026-11-02 with `gh run view 41492174324`). The scratch branch never had a pull request; it is still on origin (deleting it was refused in this session): `git push origin --delete scratch/j57-changes-fail`.
- Host tests on the PC (2026-11-02): `python3 -m unittest tests.test_workflows tests.test_jobs tests.test_pc_deploy` passes;
  `python3 core/wsc.py gates --fast` 11 ok.

## Gates
- `python3 core/wsc.py gates` (full, 2026-11-02, on the PC): 532 tests pass once the row is set (18 skipped: numpy/Pillow, capstone and the viewer wasm are not installed); `wsc jobs check`: 67 rows, ok.
- `python3 tools/pr_policy.py --branch job/J57 --base origin/main` (2026-11-02): refuses only on the reviewer's part (no
  `review.md`, row not `done`), as expected before review; nothing else.

## Deviations
- The problem-3 test swaps only `pc_deploy`'s own `os` for a stand-in with `name='nt'`, not the global `os.name`: the global patch
  breaks `pathlib` on Linux.
- The `if:` lines are wrapped in `${{ }}` because a leading `!` is a YAML tag.
- Built by a subagent of an orchestrating chat; the subagent's harness refused it writing this file, so the orchestrating chat
  (same Claude-Session) wrote it from the subagent's text, with Liam's approval (2026-11-02).

## Open questions
- Live evidence for problem 1 is not claimed: J57's own review merge follows the new order, so `policy` on the merged head should
  be a real, non-skipped run. The reviewer can confirm it there.
- The pre-J57 `if:` lines were not shown failing on the real workflow file; `test_the_old_lines_fail_these_checks` runs the old
  expressions through the evaluator only.
- warscape-core backlog: the core's own copy of `test_pc_deploy`, if there is one, has the same live-game dependency. Not checked.
