# J105 report (in progress)

Step log for the later sessions; the required sections come at Finish.

## Step 1: `meta/decisions-glob`
- Pull request #227, opened ready, cut from `origin/main` at `ef8ca7e9`, head `bc116974`. Merged by Liam (D50). Merge commit: `62d4f416`.
- `policy --branch meta/decisions-glob --base origin/main`: ok (1 files changed), judged with `origin/main` at `ef8ca7e9d90a` (core 0.47.0).
- `gates --fast`: 14 ok, 1 warn (`hooks`, this worktree's path form), 0 failed. `tests.test_repo_rules`: 13 tests, OK. `jobs check`: 110 rows, ok.
- `build_id.py`: `96722f4b8d52` on `bc116974` and on `origin/main` at `ef8ca7e9`, each with a clean tree.
- `gh pr list --state open` before opening: nothing open.
- Session note: the worktree isolation check refuses a Bash call that chains git commands with variables or heredocs, so commits went as plain separate commands with the message in a file. Not a repo rule, nothing to fix here.

## Step 2: `meta/decisions-registry`
- Pull request #230, opened ready, cut from `origin/main` at `62d4f416`, head `e2a10465`. Merged by Liam (D50). Merge commit: `d72ed931`.
- `wsc.toml` first, then the migrate, as the brief says. `reg migrate decisions --from-md docs/DECISIONS.md`: added 66 rows, 0 already there. `--check`: "docs/DECISIONS.md: 66 rows, every one in registries/decisions", exit 0.
- `docs/DECISIONS.md` identical to `origin/main`. No `registries/decisions.jsonl`, no committed view. 67 files changed: `wsc.toml` and 66 rows.
- `policy --branch meta/decisions-registry --base origin/main`: ok (67 files changed), judged with `origin/main` at `62d4f4167489` (core 0.47.0).
- `gates --fast`: 14 ok, 1 warn (`hooks`, this worktree's path form), 0 failed. `tests.test_repo_rules`: 13 tests, OK. `jobs check`: 110 rows, ok. These three ran on the staged tree, before a commit refused for its missing `--trailer` flag was repeated with it; the content is the same.
- `build_id.py`: `96722f4b8d52` on `e2a10465` and on `origin/main` at `62d4f416`, each with a clean tree.
- `gh pr list --state open` before opening: nothing open, so no open branch changes the file's table.

## Step 3: `meta/decisions-retire`
- Pull request #239, opened ready, cut from `origin/main` at `91bba26a`, head `4d31d2be`. Waiting for Liam's merge (D50). Merge commit: not yet.
- `policy --branch meta/decisions-retire --base origin/main`: ok (8 files changed), judged with `origin/main` at `91bba26a9cd8` (core 0.50.1; J88 moved the pin after step 2 was cut).
- `gates --fast`: 14 ok, 1 warn (`hooks`, this worktree's path form), 0 failed. `tests.test_repo_rules`: 13 tests, OK. `jobs check`: 110 rows, ok.
- `test_no_gate_silenced_without_a_decision` read 66 rows and passes; with `[gates] skip = ["tests"]` planted in memory, `silenced` names it, so the test still bites.
- `build_id.py`: `96722f4b8d52` on `4d31d2be` and on `origin/main` at `91bba26a`.
- `gh pr list --state open` before opening: nothing open.
- Living copies beyond the brief's list: `README.md`'s `wsc.toml, registries/` row also listed the one-file-per-row registries, so `decisions` joined it. `docs/plans/MOONSHOTS_2026-11-01.md` still names the file three times; it is a dated record that `doc_paths` does not fail on, so it stays.

**For the step 4 session: the first command in Deliverable 4 will be refused as written.** J88 set `[policy] decisions_cite_job = true` after the brief was written, so the brief's "`decisions_cite_job` is not set here" no longer holds. Rule F (`core/warscape/policy.py`) refuses a decisions row added on `job/J105` unless the row contains `J105`. The D46 row has it in `who`; the Opus row does not. Recommended: end the Opus row's `decision` text with `Recorded by J105.` and name that under Deviations. Checked 2026-11-07 on `origin/main` at `91bba26a`: `components.json` still sets `proxy.file_rules`, `allowed_dev_keys` is still empty; check both again at step 4.

## Deviations from the brief and why
- The brief says to append each step's lines to this file, but `jobs check` (and so the pre-push hook) refuses a `report.md` whose row has no `report=` or that lacks this section and the next. So the row has `report=` already, with its status still `queued`, and these two headings exist from step 1. Status goes to `review` only at Finish, as the brief says. No hook was bypassed.

## Open questions
None yet. The brief's three stand, and the two it says to name for a core row come at Finish.
