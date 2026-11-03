# J65: J10 reach fix: two live-reached units marked static_only

Phase 2 follow-up to J10 (merged in PR #123). J10's fix round (`699ddb1`) made the known `static_only` reasons (`STATIC_ONLY` in
`discovery/core/ui_atlas.py`) apply before name matching. Two of those patterns are too broad, and they now override real live evidence from
run `20261102_j10pc`:

| Unit | Before the fix round (`43e471b`) | On main (`a06f026`) |
|---|---|---|
| `battle.deployment_end` | reached: state `hist_deploy`, live path `finish_deployment`, 15 of 15 components | `static_only`: "needs a battle ending or a multiplayer battle" |
| `frontend.player_stats` | reached: state `fe_player_stats`, live path `player_stats`, 33 of 39 (0.846) | `static_only`: "needs a multiplayer lobby or Steam session" |

Both reasons are wrong. `deployment_end` is the end-deployment panel shown before a battle starts, and `fe_page.lua` entered `player_stats` from
the single-player front end. `discovery/ui/reach.json` on main says 42 of 220 units are reached, with 1,549 of 1,556 components agreeing. The J10
report, `napoleon.ui.layout_base` ("over the 44 units reached") and the run README say 44 and 1,597 of 1,610. The fix round's report said "Reach
counts are unchanged for the reached units", which was not true. Round 2 did not catch it.

Model: Sonnet medium (D15). Budget about 30 tool calls; at the cap, stop, commit, report what is left. No subagents, no game launch.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J65`). Read `jobs/J10/report.md` (`## Fix round 1`), `jobs/J10/review.md` (rounds 1 and 2) and
  `discovery/core/ui_atlas.py` `STATIC_ONLY` and `live()`.
- The regeneration reads the extract (`extract/napoleon/`, git-ignored, on the PC: `discovery/README.md`). Nothing is launched: the live data
  is the committed run `harness/runs/20261102_j10pc`.

## Deliverables
1. **The patterns.** Take `deployment_end` out of the battle-ending pattern and `player_stats` out of the multiplayer pattern. Check every other
   `STATIC_ONLY` alternative against the run the same way: the units that were `reached` at `43e471b` and are `static_only` now must be exactly
   these two. Say so in the report, with the command you used.
2. **A guard, so the next broad pattern fails loudly** ("a learning becomes code first"). In `live()`, when a `STATIC_ONLY` pattern matches a
   unit whose own head is found under its own name in a live tree (the match `live()` marks `_named`) at agreement 0.75 or more, the step
   fails. It prints the unit, the pattern and the live path. A match under another page's node (`frontend.password_entry` inside the options
   page) is not a conflict: the pattern still wins there. Add a test in `tests/test_discovery_ui.py` `Live` for both cases.
3. **Regenerate** with `python3 core/wsc.py discovery ui` (it re-runs the live match and the art rules). Expected result: `reach.json` 44
   reached with 1,597 of 1,610 components agreeing, matching the J10 report again. Only `reach.json`, `summary.json`, `units.json.gz`, the two
   rows' descriptions in `registries/ui_elements.jsonl`, `discovery/ui/README.md` and possibly `used_by` should change. If the numbers differ,
   report the difference and its cause; do not hand-edit any generated file.
4. `python3 core/wsc.py gates` green, `wsc discovery check` ok, and a second `discovery ui` run byte-identical (give the sha256 of `reach.json`).

## Out of scope
- J10's report and review are merged history: do not edit them. This job's report carries the corrected numbers.
- J10's other "Later" items (the `getters.lua` guard, one driver per lock, the `used_by` check, `db:` fields).

## Kill criteria
- The guard (deliverable 2) flags a unit other than these two: stop, list each one with its pattern and live path, and leave the pattern
  decision to Liam.
- The regeneration changes any unit id or any `used_by` beyond these two units: stop and report the diff.

## Finish
Write `jobs/J65/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): the pattern change,
the guard and its tests, the reach numbers before and after with the command, the sha256 of `reach.json` from two runs, and the gates output.
Then `wsc reg set jobs J65 status=review report=jobs/J65/report.md`.
