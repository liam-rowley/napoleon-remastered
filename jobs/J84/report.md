# J84 report

`tools/claude_hook.py` no longer denies `gh pr merge` of a `plan/` branch (D62); `meta/` stays denied, and every other merge guard is unchanged.

## What was built
- Hook: `merge_reason` denies only `meta/` branches. A PR number, URL or no target is still resolved with `gh pr view` (unresolvable is denied); `gh api` merges and the remote-branch delete guard are untouched. `merge_msg`, the file header and the `tools.claude_hook` registry row say `meta/` only (D50) and name D62 for `plan/`.
- Corpus (`tests/test_claude_hook_corpus.py`): the `plan/` merge cases (name, `refs/heads/`, `-R`, number 12, URL) are now allowed; added `gh pr merge plan/J84 --auto --squash` and a PowerShell form as allowed; every `meta/` case, the no-target case (resolves to `meta/y`), the unresolvable 99 and the `gh api` cases stay denied; the message-route test uses a `meta/` command. `tests.test_claude_hook_corpus` plus `tests.test_claude_hook`: 30 tests ok (decide() 0.14 ms, hook round trip 69 ms).
- Prose: `CLAUDE.md` (the merge sentence now says D62 is in force and carries the step that a `plan/` branch queues its own merge with `gh pr merge plan/<name> --auto --squash`, as `brief/` does; the Guard line lists `meta/` only), `docs/REVIEW.md` "Merging", and the tools registry row.

## Deviations from the brief and why
- None. `README.md` and `docs/plans/PLAN.md` had no living copy of the old claim.

## Open questions
- None. J103 still owns the narrowed `plan/` rules; until it lands a `plan/` branch can change `CLAUDE.md`, `docs/REVIEW.md` and the core's docs on green CI alone (D62).
