# J105 review

## Round 1 (2026-11-07, branch job/J105 at 407c45d6)

**Verdict: merge.**

Session `6779787e-f143-4e76-ae92-1a4db1ad87d1`, a fresh one; it wrote none of the report. The three `meta/` pull requests did what the brief asked, the migration lost nothing, and both new rows say what the repo shows. No blockers and no should-fix items. One local gate failure is not this job's (Later 1).

### Machines
- CI on 407c45d6: `gates` success, run 42389904801. `proxy`, `harness-windows`, `viewer` skipped; `policy` skipped on the draft, as designed. Pull request #240 is MERGEABLE, CLEAN.
- Local `wsc gates`, 2026-11-07: 14 ok, 1 warn, 1 failed. The warn is `hooks`, this worktree's path form, as in the report. **The failure is `tests`: `test_commands_printed_by_the_job_steps`, 1 of 724.** It fails the same way alone on `origin/main` at 1c88a829, and the branch changes nothing under `tests`, `tools` or `core`, so it is not J105's. Later 1.
- `jobs check`: 110 rows, ok. `build_id.py --no-dirty` on 407c45d6: `96722f4b8d52`, the report's id. The diff has no `proxy/`, `harness/`, pin or acceptance change, so no rule 79.
- Local `policy` before this round refused only for the missing review and the row not being `done`, which is expected.

### Claims against evidence
- **Three pull requests:** `gh pr view` gives #227, #230 and #239 MERGED by `liam-rowley`, not draft, at 62d4f416, d72ed931 and 1c88a829, the commits the report names.
- **The migration, read independently (the risk-first pick: this is the only copy of the project's decisions now).** A script parsed the 66 table lines of `docs/DECISIONS.md` at d72ed931 and compared date, who, decision and reversible with `registries/decisions/*.json` on this head: 66 of 66 equal, 0 missing, every line 5 columns, and the only extra rows are the two new ones.
- **The D46 row:** `release/napoleon/components.json:27` sets `proxy.file_rules`, no component sets `dev.file_rules`, `allowed_dev_keys` is `{}` (`release/napoleon/release.json:31`), `upscale/pc/play.py:251` stays on `dev.file_rules`. The notes of fact `napoleon.ui.templates_route` say no launch has used `proxy.file_rules`, and J106 is `needs_brief`. Every clause holds.
- **The Opus row** matches the brief's command, plus `Recorded by J105.`; `decisions_cite_job` is on at `wsc.toml:78`, so the named deviation was needed.
- **Open question 3 is real:** `core/warscape/jobq.py:1183` takes `S.models[0]` for a brief, and `wsc.toml:44` puts `sonnet` first. Later 2.
- **Read paths `CLAUDE.md` now gives:** `wsc find Opus across` finds the new row; `reg render decisions` writes 68 rows to `_scratch/registries/decisions.md`.
- **Minted ids against the code that reads ids.** `quoted_by_a_row` (`tests/test_repo_rules.py:192`) does not read the id. The one `D\d+` parser, `release/core/build_release.py:208`, matches `D261107-5dc6` (run, not assumed). No code reads `docs/DECISIONS.md` any more; the fixture in `tests/test_proxy_host.py:206` may stay, as the brief says.
- **Not re-checked:** the `build_id.py` values on the `meta/` branches at each cut and the `gates --fast` counts of steps 1 to 3. Only the id on this head was run; the unchanged id across all of them rests on the report and on CI's skipped `proxy`.

### The brief
Deliverables 1 to 5 are present. `decisions_retired` and the temporary `LANGUAGE.md` glob are gone from `wsc.toml`; the `registries/decisions/*` glob is in `plan` and `meta`. The test reads the rows and asserts they are not empty. All three deviations are named with a reason. Nothing under `core/`, and no other job's brief, was changed.

Merging changes no rule for other open branches: `gh pr list` shows only #241 (`job/J85`) besides this one, and it touches neither the rows nor the old file.

### Blockers
None.

### Should-fix
None.

### Later
1. **`tests/test_claude_hook_corpus.py:395`: local `wsc gates` is red for every session while origin holds an empty claim.** Not caused here. The test runs the live `jobs next --peek` and requires the hook to allow every command in its output. That output now carries the `git push origin --delete job/J27` line of `empty_claims` (`core/warscape/jobq.py:1014`), for J27, J48, J69 and J93, and the hook rightly denies it. See it fail: `python3 -m unittest tests.test_claude_hook_corpus.PipelineIsNeverBlocked.test_commands_printed_by_the_job_steps`. Fix: the test drops the empty-claim lines, which are advice to Liam and not job steps. Deleting the four branches clears it only until the next stale claim. Why CI's `gates` passed at the same commit was not established.
2. **`wsc.toml:44`: a brief started from the `jobs view` page still runs on Sonnet, against `D261107-5dc6`.** The report's open question 3, confirmed. Its recommended swap, with `ref_models` at `wsc.toml:65`, needs a `meta/` branch, so it is Liam's. No row tracks it yet.
3. **`docs/REVIEW.md:8` and the `CLAUDE.md:85` heading still cite D15 for the model rule.** The brief's `git grep -i sonnet` cannot find them, because neither line says Sonnet. Neither instructs anything wrong today ("Opus is allowed" stays true), so this is tidying for a `plan/` branch.
4. **Core: `reg render` and `wsc find` do not mark a replaced row.** `find Opus across` lists D52 with no sign it is replaced, and the rendered table has no `replaces` column, so a reader who lands on D52 or D46 alone sees the old rule. `CLAUDE.md` now sends agents to exactly these views. A `later` row for warscape-core; not filed by this review.
5. **`jobs/J105/report.md:30` still says #239 is "Waiting for Liam's merge" and "Merge commit: not yet".** The Evidence line at the top of the same section is right. Its Usage line counts steps 4 and 5 only, so the brief's budget of about 80 calls cannot be checked.
6. **"No new session may start during an acceptance run" (report, Deviations) is not in the repo.** It is in a session's memory only. It changed how this job ran, so it belongs in a guard or in `CLAUDE.md`.
7. **`release/core/build_release.py:209` says "(D<n>)"** in its message and docstring; a minted id passes, so only the wording is old.
