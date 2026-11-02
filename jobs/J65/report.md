# J65 report: J10 reach fix: two live-reached units marked static_only

Two STATIC_ONLY patterns in `discovery/core/ui_atlas.py` no longer override live evidence: `battle.deployment_end` and `frontend.player_stats` are
reached again (44 of 220, as J10 reported), and a new guard fails the regeneration whenever a STATIC_ONLY pattern overrides a unit that the run
found live under its own name.

Written by the orchestrator from the build agent's hand-back: the build ran as a subagent, and the harness refuses a subagent's Write of a
report file, so the parent writes it. Same Claude-Session as the build.

## What was built
- **Patterns narrowed** (`discovery/core/ui_atlas.py`): `deployment_end` is out of the battle-ending STATIC_ONLY pattern, `player_stats` out of
  the multiplayer pattern.
- **Guard** (`live()`): the name match now runs before the known-reason check. When a STATIC_ONLY pattern matches a unit whose own head is found
  under its own name as a top-level live node (no `/` in the live path) at agreement 0.75 or more, `live()` raises `StaticOnlyConflict`, naming
  the unit, the pattern and its reason, the live path, the state and the agreement. A match nested inside another page's node (for example
  `options/password_entry`) is not a conflict, so the pattern still wins there.
- **Tests** (`tests/test_discovery_ui.py`, class `Live`): `test_guard_fails_on_a_pattern_that_overrides_live_evidence` and
  `test_guard_allows_a_match_inside_another_pages_node`. `test_known_reason_beats_a_name_match` now uses head `password_entry`: with head `page`
  its unit sat on a top-level named node, which is exactly the conflict the guard catches.
- **Regenerated** with `python3 core/wsc.py discovery ui`: `discovery/ui/reach.json`, `discovery/ui/summary.json`, `discovery/ui/README.md` and
  two rows of `registries/ui_elements.jsonl`. No unit id and no `used_by` changed.

## Evidence
Live data: the committed run `harness/runs/20261102_j10pc` (no game launch, as the brief says).

| | Reached | Components agreeing | Mean agreement |
|---|---|---|---|
| Before (main 94ab291) | 42 of 220 | 1,549 of 1,556 | 0.995 |
| After (job/J65 a26afdb) | 44 of 220 | 1,597 of 1,610 | 0.992 |

- By context after: battle 7 of 32, frontend 15 of 40, matching the J10 report.
- The only two units that changed in `reach.json`: `battle.deployment_end` reached (state `hist_deploy`, live path `finish_deployment`, 15 of 15),
  and `frontend.player_stats` reached (state `fe_player_stats`, live path `player_stats`, 33 of 39, 0.846).
- The guard ran over all 220 units and raised for no other unit.
- `reach.json` sha256 identical over two runs: `223839baa62ae768fb2e70f2ffd6fa69e7d409bdce3b7e2a9c676bc2cf163bef` (rechecked by the orchestrator
  2026-11-02 on a26afdb).
- `python3 -m unittest tests.test_discovery_ui`: 18 tests, OK (builder; rerun by the orchestrator: OK).
- `python3 core/wsc.py discovery check`: "6 area files valid, J7 and J10 results in step, READMEs current, gate ok" (builder and orchestrator).
- Gates: the pre-push `gates --fast` passed on a26afdb (13 ok, 0 failed). Full `python3 core/wsc.py gates` on a26afdb (orchestrator,
  2026-11-02): 13 ok, 1 failed in 191.6 s. The one failure is `tests`: 557 run, 1 failure, 43 skipped. The failing test is
  `test_job_sh.JobSh.test_ctl_without_an_ini_uses_the_registered_default` (stderr came back empty), which is outside this job's files. The run
  happened while J46 had the game running on this PC (the same log skips the install tests for "a game is running: Napoleon 34796"), so the
  likely cause is the live session, not this branch. CI on the pull request is the check that counts.

## Deviations from the brief and why
- **The guard also requires a top-level live path.** The brief's rule alone ("a pattern overrides a unit's own named live match") would also fire
  on `frontend.password_entry`, whose head is found by name inside the options page, where the pattern is right. The top-level condition is what
  tells the two cases apart.
- **Extract access from a worktree.** The worktree has no git-ignored `extract/napoleon`, so the builder linked it to the main checkout's copy
  with a directory junction (nothing copied). A first `discovery ui` run without it silently wrote empty `reach.json` and `art_keys.json`; that
  output was reverted and not committed.

## Open questions
- The top-level rule would miss an over-broad pattern whose live match is nested under the unit's own container (a HUD piece, say). None exists
  today. Should the guard cover that case too?
- `discovery ui` writes empty outputs, without an error, when `extract/napoleon` is missing (as in any worktree). That is a guard worth adding
  (a later item for the review to rank).
