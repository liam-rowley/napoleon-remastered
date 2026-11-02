## Round 2 (2026-11-02, branch job/J10 at 74f7837)

**Verdict: merge.**

Fresh reviewer session (Opus; neither the builder nor the round 1 reviewer or fixer). Checked the three open items of round 1 against the branch, not the report:
- **3 (template rows list screens):** `registries/ui_elements.jsonl` `template.buildingframe` now reads "Used by: construction.luac (a script shared by the whole context)". The report names the 34 template rows with no static opener and why; that is an acceptable, stated limit. `Ids.test_template_users` passes.
- **4 (known static_only wins over a name match):** `frontend.password_entry` is `static_only` with "needs a multiplayer lobby or Steam session". `Live.test_known_reason_beats_a_name_match` passes.
- **5 (hyphen):** no `load-save` id remains in any registry; `Ids.test_unit_id_has_no_hyphen` passes.
- `python3 -m unittest tests.test_discovery_ui tests.test_discovery`: 29 tests OK. `wsc jobs check`: ok. `tools/pr_policy.py` refuses only for the verdict and the row, which this round sets.
- PR #123's failed `policy` check was that same pair of lines (round 1 said "merge after fixes").

Later items from round 1 stay as listed there (getters.lua guard, one-driver-per-lock, `used_by` check in `discovery check`, `db:` fields, rows without `data_fields`, click-opened units). No other open pull request depends on a rule this merge changes.

## Round 1 (2026-11-02, branch job/J10 at 83a466b)

**Verdict: merge after fixes.**

Reviewer session `56406bbf-7e38-49cb-ac02-c04779aa11dd` (Opus, independent check: D15; neither the builder nor a fixer). An autopilot review
session (`6bd33de8`, `J10-review`) ran in the same checkout at the same time and committed a `merge` round 1 on top of this round's two fixes
(`65e211c`, `74ab440`). Liam stopped it on 2026-11-02 and this round replaces it; its later items are kept below.

Ran `wsc gates` (11 ok, 1 warn: skipped tests that need numpy, Pillow, capstone or the viewer build), `tools/pr_policy.py` (refused only for
the missing review and the row) and both generator steps again on the PC. Risk-first read: the `assets.jsonl` rewrite (persistent data that the
upscale packs read), the PC sittings (game folder, three crashes) and the live matcher (`ui_atlas.py live`: it decides reached or static_only).

### What holds (checked, not taken from the report)
- `registries/assets.jsonl`: the same 12,295 ids in the same order. 6,335 rows differ, and only in `used_by`, and every `used_by` id is a `ui_elements` row.
- `registries/ui_elements.jsonl`: 262 rows, all at `atlas`, no `decision` or `reason`, no empty `interactions`, sources only `getter:` (485) and `loc:` (2,586).
- Re-runs: `ui_atlas.py all` and `ui_atlas.py art` on the PC leave every committed file byte-identical.
- The uninstall: pc_deploy's record on the PC (`history/install_20261102T105953Z.json`) says `identical: true`, `diffs: []` and the exe is vanilla.
- Live: `reach.json` gives the report's numbers (44 of 220 reached; 1,597 of 1,610 components agree; `width_scale` median 1.0 over 44). In
  `j10_land_running.jpg` the orders bar sits where `napoleon.ui.layout_base` puts it (canvas + (320, 120)).
- Probes: `tree.lua` and `fe_page.lua` only read, apart from `TransitionTo` (J9's route). The drivers use J9's proven panel and selection probes.
  The three crashes trace to `getters.lua` being called without its list, and the report names them.

### Should-fix (fixed in this review)
1. **`wsc discovery ui` did not re-run the art rules** (`discovery/core/ui_atlas.py` `main`). The report says it runs "atlas, rows, art", but the
   default `all` step skipped `art`, so a re-run never checked `art_keys.json`. Fixed in `8ae13eb`: `all` runs art too, and the header and tool row
   list every step. A re-run on the PC leaves every file unchanged.
2. **The "identical" uninstall had no evidence in the repo.** The record was only on the PC. Fixed in `41cc196`: it is filed as
   `harness/runs/20261102_j10pc/raw/pc_deploy_install_20261102T105953Z.json`, and the run README cites it.

### Should-fix (for the fix session)
3. **Template rows do not list the screens that use them, which the brief's Decisions ask for** (`discovery/core/ui_atlas.py:649` `describe`).
   The 102 `template.*` descriptions name the script that creates the template instead. For example, `template.buildingframe` says
   "Opened by CreateComponentFromTemplate("BuildingFrame") in construction.luac CreateBuildingFoundation and 2 more". 17 rows cut the list
   off at "and N more", and 32 say "Opener not found statically". The screens' atlas files list `templates_used` as `template:<name>`,
   `script:<name>` or `layout:<path>`, not row ids. The report does not name this as a deviation. To see it:
   `grep '"id": "template.buildingframe"' registries/ui_elements.jsonl`. The screens' `templates_used` lists give screens for 94 of the 102
   template units. They miss the templates that scripts create (BuildingFrame's only hit is itself), so the opener scripts must be mapped to
   their screens too.
4. **Matching by component names can mark a unit as reached, and a known static_only reason is lost** (`ui_atlas.py:1003-1022`). `STATIC_ONLY`
   is used only when the best score is under 0.75. `frontend.password_entry` (0.833) and `frontend.host_campaign_popup` (0.75) match inside
   the options page. They end up `static_only` only because the options page claimed that node first, and their reason is "its best live match
   (fe_options options) is frontend.options's" instead of "needs a multiplayer lobby". With no options unit, they would count as reached. To see
   it: `reach.json` `units_reach["frontend.password_entry"]`. Apply `STATIC_ONLY` before the score, or require a match to keep its head's name,
   and add a test.
5. **`campaign.load-save_game` keeps a hyphen in its id.** Ids never change after this merge (Decisions, "Ids"). Decide now whether
   `unit_id` (`ui_atlas.py:523`) maps `-` to `_`.

### Later
- J9's `harness/runs/20261101_j9fix/probes/getters.lua:8` runs `dofile(nil)` when called without its list, and that crashed the game three
  times in this run. When the probes move into `proxy/napoleon/lua/probes/` (the next DLL change, likely J24), it should refuse a missing argument.
- The pid-file guard is local to the J10 drivers. A core guard (one driver per lock) and `ctl reset` relaunching from a historical battle are
  the report's open question 3, for Liam; if he wants them, they go to warscape-core `docs/BACKLOG.md`.
- `discovery check` checks the atlas files and the row ids, but not `used_by` in `assets.jsonl`, so a hand edit there passes (`ui_atlas.py:1120`).
- No row has a `db:` data field, although `art_keys.json` has a db rule for 9 roles (for example unit cards from `uniforms.uniform_name`).
  The contract stage can add them from there.
- 92 rows have no `data_fields` (from the stopped review). The contract stage should read an empty list as "none traced" and use the atlas
  file's `unresolved` list.
- 69 units are `static_only` because they open on a click. D39 leaves them to the contract stage.
