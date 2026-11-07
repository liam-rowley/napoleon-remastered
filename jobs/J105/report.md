# J105 report

## What was built
Decisions are one file per row. Three `meta/` pull requests, all merged by Liam: #227 added the glob, #230 migrated the 66 rows to `registries/decisions/`, #239 retired `docs/DECISIONS.md` and repointed the docs. On `job/J105`: the first two new rows, and the `CLAUDE.md` Usage line.

- `D261107-5dc6`: Opus across the board, replacing D52.
- `D261107-85d1`: the exception in D46 is over, the rest of D46 stands.

## Evidence
Merge commits: #227 `62d4f416`, #230 `d72ed931`, #239 `1c88a829`.

### Step 1: `meta/decisions-glob`
- Pull request #227, opened ready, cut from `origin/main` at `ef8ca7e9`, head `bc116974`. Merged by Liam (D50). Merge commit: `62d4f416`.
- `policy --branch meta/decisions-glob --base origin/main`: ok (1 files changed), judged with `origin/main` at `ef8ca7e9d90a` (core 0.47.0).
- `gates --fast`: 14 ok, 1 warn (`hooks`, this worktree's path form), 0 failed. `tests.test_repo_rules`: 13 tests, OK. `jobs check`: 110 rows, ok.
- `build_id.py`: `96722f4b8d52` on `bc116974` and on `origin/main` at `ef8ca7e9`, each with a clean tree.
- `gh pr list --state open` before opening: nothing open.
- Session note: the worktree isolation check refuses a Bash call that chains git commands with variables or heredocs, so commits went as plain separate commands with the message in a file. Not a repo rule, nothing to fix here.

### Step 2: `meta/decisions-registry`
- Pull request #230, opened ready, cut from `origin/main` at `62d4f416`, head `e2a10465`. Merged by Liam (D50). Merge commit: `d72ed931`.
- `wsc.toml` first, then the migrate, as the brief says. `reg migrate decisions --from-md docs/DECISIONS.md`: added 66 rows, 0 already there. `--check`: "docs/DECISIONS.md: 66 rows, every one in registries/decisions", exit 0.
- `docs/DECISIONS.md` identical to `origin/main`. No `registries/decisions.jsonl`, no committed view. 67 files changed: `wsc.toml` and 66 rows.
- `policy --branch meta/decisions-registry --base origin/main`: ok (67 files changed), judged with `origin/main` at `62d4f4167489` (core 0.47.0).
- `gates --fast`: 14 ok, 1 warn (`hooks`, this worktree's path form), 0 failed. `tests.test_repo_rules`: 13 tests, OK. `jobs check`: 110 rows, ok. These three ran on the staged tree, before a commit refused for its missing `--trailer` flag was repeated with it; the content is the same.
- `build_id.py`: `96722f4b8d52` on `e2a10465` and on `origin/main` at `62d4f416`, each with a clean tree.
- `gh pr list --state open` before opening: nothing open, so no open branch changes the file's table.

### Step 3: `meta/decisions-retire`
- Pull request #239, opened ready, cut from `origin/main` at `91bba26a`, head `4d31d2be`. Waiting for Liam's merge (D50). Merge commit: not yet.
- `policy --branch meta/decisions-retire --base origin/main`: ok (8 files changed), judged with `origin/main` at `91bba26a9cd8` (core 0.50.1; J88 moved the pin after step 2 was cut).
- `gates --fast`: 14 ok, 1 warn (`hooks`, this worktree's path form), 0 failed. `tests.test_repo_rules`: 13 tests, OK. `jobs check`: 110 rows, ok.
- `test_no_gate_silenced_without_a_decision` read 66 rows and passes; with `[gates] skip = ["tests"]` planted in memory, `silenced` names it, so the test still bites.
- `build_id.py`: `96722f4b8d52` on `4d31d2be` and on `origin/main` at `91bba26a`.
- `gh pr list --state open` before opening: nothing open.
- Living copies beyond the brief's list: `README.md`'s `wsc.toml, registries/` row also listed the one-file-per-row registries, so `decisions` joined it. `docs/plans/MOONSHOTS_2026-11-01.md` still names the file three times; it is a dated record that `doc_paths` does not fail on, so it stays.

### Step 4: the rows
- `git merge origin/main` at `1c88a829`. Guards first: `release/napoleon/components.json` sets `proxy.file_rules`, and `release/napoleon/release.json` has `allowed_dev_keys` empty, so the D46 row stands.
- `reg add decisions --mint`: added `D261107-5dc6` and `D261107-85d1`. Each `replaces` D52 and D46.
- `CLAUDE.md` Usage now gives the Opus rule and cites `D261107-5dc6`. `git grep -n -i sonnet` over the living docs: only `wsc.toml` line 44 (open question 3) and `docs/plans/MOONSHOTS_2026-11-01.md`, a dated record, left as it is.

### Step 5: the proof
`build_id.py` was `96722f4b8d52` on all three `meta/` branches and on `origin/main` at each cut (the steps above), and `--no-dirty` on `job/J105` after merging `1c88a829`. No rule 79 run.

Full `wsc gates` was not run locally for step 4: J85's acceptance run was on the PC, and this step changes two rows and one line of `CLAUDE.md`. `gates --fast`, `tests.test_repo_rules`, `jobs check` and `policy` were run; CI's `gates` decides.

## Deviations from the brief and why
- The brief says to append each step's lines to this file, but `jobs check` (and so the pre-push hook) refuses a `report.md` whose row has no `report=` or that lacks this section and the next. So the row has `report=` already, with its status still `queued`, and these two headings exist from step 1. Status goes to `review` only at Finish, as the brief says. No hook was bypassed.
- **The Opus row ends `Recorded by J105.`, which the brief's command does not have.** J88 turned on `decisions_cite_job` after the brief was written, so a row added on `job/J105` must name the job. The D46 row already did, in `who`.
- **Steps 4 and 5 and this report were done by session `0280ca96-6ae4-4807-ae31-4e3119d8e245`, not a `Continue J105` session,** because no new session may start during an acceptance run and J85's was on. That session did not write the steps before it.

## Open questions
The brief's three took their recommended answers: `LANGUAGE.md` was repointed, the Opus row keeps the effort sentence, and queued briefs were not edited.

For core or `meta/` rows, left as the brief says:
1. `jobs check` still wants `reason:` on a `Model: Opus` line, which means nothing now every job is Opus. recommended: a core row drops it.
2. `wsc.toml` `ref_models` still says D15. recommended: point it at `D261107-5dc6` on a `meta/` branch.
3. **`wsc.toml` `[jobs] models` is still `["sonnet", "opus"]`, found here.** `launch_argv` in `core/warscape/jobq.py` takes the first entry for a brief, so a brief started from the `jobs view` page runs on Sonnet against `D261107-5dc6`. recommended: swap the order on the same `meta/` branch as 2.

Usage: about 8 tool calls for steps 4 and 5; the earlier steps were not counted.
