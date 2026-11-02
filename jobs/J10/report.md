# J10 report: Vanilla UI atlas

J10 built the vanilla UI atlas for Napoleon. The Version039 layout reader now round-trips all 174 layouts (136 of them Version039, up from 45). It
also reads 124 of the 126 `uied.templates` records, up from 117. A static atlas reads every layout, template record and compiled UI script (497).
It is written to `discovery/ui/` and gives 262 `ui_elements` rows at `atlas`: 248 screen, HUD-piece and template units and 14 `engine.*` items,
each with a proposed route. `used_by` is set on 6,335 asset rows. Art-by-key rules cover 9 of the 10 key-named roles. A live pass on the PC
(run `20261102_j10pc`) reached 44 of 220 layout and template units in 31 states, and the static and live trees agree on 1,597 of 1,610 of their components. The game
folder ended identical to the pre-install snapshot (1,564 files). Re-runs give byte-identical files; tests and gates are green.

## What was built

### How to re-run
- `python3 core/wsc.py discovery ui` runs every static pass (atlas, rows, art) and then the live pass against the committed run. `python3 core/wsc.py
  discovery check` checks that the committed results are current (the sha256 of every atlas file and the row ids).
- `python3 discovery/core/ui_atlas.py atlas|rows|live|art|all [--run harness/runs/20261102_j10pc]` runs one step.
- The live drivers are `harness/runs/20261102_j10pc/sit1.sh` (battles), `sit1fe.sh` and `sit1fe2.sh` (front end) and `sit2.sh` (campaign and
  fleet). Each needs the kit installed and the watcher idle. The run README lists every state.

### Tools (each has a header, a `tools` row and host tests)
| Tool | What it does | Tests |
|---|---|---|
| `discovery/core/uic.py` (extended) | Version039 transitions (18-byte records), keyframes with a state change, the v35 template record (V033 + animations + transitions, no state_ref), v18 | `tests/test_discovery.py` (2 new) |
| `discovery/core/ui_walk.py` (new) | Empire's `atlas_static.py` symbolic register walk re-done on Napoleon's Lua 5.1 bytecode: engine calls, fields read off results, handlers, inline Lua facts | `tests/test_discovery_ui.py` Walk |
| `discovery/core/ui_atlas.py` (new) | atlas, units and rows, handler owners, the engine-drawn list, art by key, live matching, README, `problems()` for `discovery check` | `tests/test_discovery_ui.py` (13 tests) |
| `tools/verbs/discovery.py` (extended) | the `ui` pass in `wsc discovery`, its README and its check | through the gates |

### Item 1: layout reader
| | Before (`discovery/diff/layouts.json` on main) | After |
|---|---|---|
| Version039 layouts byte-exact | 45 of 136 | 136 of 136 |
| all layouts byte-exact | 83 of 174 | 174 of 174 |
| `uied.templates` records read | 117 of 126 | 124 of 126 |

The two unread template records are v4 records (`InputWindow`, `BattleEditor`) from the UI editor. Empire's reader fails on them too, and no
screen uses them. Facts updated: `napoleon.diff.layouts.v039` and `napoleon.diff.layouts.v039_transitions` (both verified),
`napoleon.diff.layouts.template_records` and `napoleon.diff.layouts.versions`.

### Items 2 and 3: static atlas, rows and coverage
`discovery/ui/<context>.json.gz` (battle, campaign, common, frontend, template), `scripts.json.gz`, `units.json.gz`, `summary.json` and
`README.md` (generated). The rows are in `registries/ui_elements.jsonl`.

| Coverage | Count |
|---|---|
| layouts read | 174 of 174 |
| template records read | 124 of 126 (34 of them created at runtime by scripts) |
| compiled scripts walked | 497 of 497 |
| components | 8,245 |
| units (rows) | 248 + 14 `engine.*` = 262: battle 32, campaign 56, common 18, frontend 40, template 102 (40 template layouts, 34 `uied` records, 28 shared widget scripts), engine 14 |
| text and tooltip keys resolved to `loc` | 3,120 of 4,245 (the other 1,125 are UI-editor placeholder keys set at runtime) |
| art references resolved to `assets` ids | 21,432 of 22,583 (1,018 are UI-editor absolute paths) |
| assets with `used_by` | 6,335 |
| data fields sourced | 3,062 |
| data fields unresolved | 3,711: parameter 1,798, upvalue 915, text_key 940, dynamic_text 58 |
| interactions (event handlers) | 2,073: 113 engine commands, 21 in scripts the game does not ship, 50 handlers not found |
| scripts named but not shipped | 106 |
| 9-slice frame groups | 13 |
| getters named that are not in `engine_api.json` | 13 calls not in the API, 4 not in the state they run in (listed in `summary.json`, not dropped) |

### Item 4: engine-drawn items
`discovery/ui/engine_drawn.json` and the `engine.*` rows (route in `description`, D39). Every evidence item (an exe string, a script call, a layout
component) is re-checked on each run, and the pass prints any that no longer matches.

| Item | Route | Why | Later owner |
|---|---|---|---|
| `engine.battle_radar` | render_target | the engine generates the terrain texture and draws unit pips each frame | J35 (panel host), then the battle HUD job |
| `engine.campaign_radar` | render_target | `CampaignUI.AttachRadarView` attaches an engine view; `UpdateRadarView` refreshes it | J35, then the campaign HUD job |
| `engine.movies` | render_target | Bink movies played into a component (`PlayMovieInComponent`) | J35 |
| `engine.unit_3d_preview` | render_target | the engine renders the model; the layout only has the rotate handlers | J35 |
| `engine.selection_box` | rml | already a `uied.templates` record (`box_selection`) created by a script | the battle HUD job |
| `engine.tooltips` | rml | layout-based templates that the engine creates and places on hover | J35 |
| `engine.battle_unit_banners` | engine_drawn | placed in 3D every frame from the `lb_unit_id`/`nb_unit_id` layouts; Empire kept them native | J37 |
| `engine.campaign_map_labels` | engine_drawn | 3D-anchored on the campaign map | J37 |
| `engine.subtitles` | engine_drawn | drawn with the movie | J37 |
| `engine.loading_screen` | engine_drawn | drawn while the Lua UI does not pump; no layout | J37 (text), a later art job |
| `engine.cursors` | engine_drawn | Windows cursors (`LoadCursorFromFileA`) | a later art job |
| `engine.escape_menu_background` | engine_drawn | the escape menu layouts have no background: the paused 3D view shows through | the escape menu contract |
| `engine.campaign_map` | engine_drawn | world rendering, not UI | none |
| `engine.selection_and_order_markers` | engine_drawn | 3D world decals | none |

### Item 5: live pass (run `20261102_j10pc`)
The run README (`harness/runs/20261102_j10pc/README.md`) has one line per state. The watcher ran everything headless at 1920x1080 with the 20-pass
kit (DLL 46f52d356ce8). Afterwards the uninstall left the game folder **identical to the pre-install snapshot (1,564 files)**, with no lock, the
profile restored and the exe vanilla. That covers 31 states: 6 battle (land and naval in deployment and running, siege, Dresden), 13 front end
(the main menu and 12 pages) and 12 campaign (the HUD, a popup, army, agent, settlement and fleet selections, and six panels). Each state has a
component tree, the visible top level and one shot; getters were sampled once per context.

| Context | Reached | Static-only, main reasons |
|---|---|---|
| battle | 7 of 32 | battle endings, escape menu and options (probes send no input), the minimised HUD (its pieces are the full HUD's) |
| campaign | 11 of 56 | event popups (`layout_*`, 19), orders and destructive popups (13), multiplayer, panels with no proven safe route |
| common | 2 of 18 | options and dialogs (no input), multiplayer, `unit_information` (no proven safe route) |
| frontend | 15 of 40 | multiplayer and lobby pages (8), credits (stops the Lua pump), the `mp_` copies of the `sp_` pages |
| template | 9 of 74 | 27 templates have fewer than 3 components, so a tree match by name is no evidence |
| **all** | **44 of 220** | `discovery/ui/reach.json` gives every unit's reason |

**Static-vs-live agreement: 1,597 of 1,610 components (99.2 %, mean 0.992 per unit) of the 44 reached units.** A unit is reached when at least
75 % of its static component names sit under one live node, it has at least 3 components, and no other unit explains that node better (the
rules and their tests are in `tests/test_discovery_ui.py` Live). The 28 shared widget scripts are not layouts and have no reach.

What the live trees showed beyond the names (facts in item 7):
- **Layout base.** The UI is not scaled at 1080p. The 1280x960 canvas is drawn 1:1 and docked: the battle HUD bottom-centred, front-end pages
  centred, the radar top right. The API reports canvas units, equal to the layout file's (`width_scale` median 1.0 over 44 units).
- **Placeholders.** The orders bars load into the HUD's `veneer_DY/orders` and take its name. The matcher finds a head under another name by
  its children.
- **Visibility is per component.** A hidden parent keeps children that report visible, for example the formations panel and the ability buttons.
- **Front end.** A page's tree is taken in the same call that enters it, so animated parts (the page heading) have pre-animation positions.
  Pages entered by `TransitionTo` alone show the layout's placeholder content (`sp_battle2`'s "Lorem ipsum").

**Three side-by-side checks** (shots in `harness/runs/20261102_j10pc/shots/`):

| Unit, row and atlas file | Shot | What matched | What did not, and Empire |
|---|---|---|---|
| `battle.land_battle_orders` (`registries/ui_elements.jsonl`; `discovery/ui/battle.json.gz` `battle ui/land_battle_orders`) | `j10_land_running.jpg` | 41 of 42 names under `veneer_DY/orders` (the 42nd, `land_battle_ordersOLD`, is a second root child that is in no live tree); the six round order buttons (halt, move speed, melee, group, formations, withdraw) at canvas x 228 to 488 (screen + 320); the six-segment `UC_frame` dial; both flags; the button strips | The five ability slots and the formations panel report visible children but draw nothing (no unit selected; visibility is not inherited). Empire's layout has 36 components and Napoleon's 52: 32 names are shared, and Napoleon adds `orders_LB`, the button strips, five ability slots and a leftover `land_battle_ordersOLD` |
| `frontend.sp_battle2` (`frontend.json.gz` `frontend ui/sp_battle2`) | `j10_fe_sp_battle2.jpg` | 44 of 44 names, 91 of 100 nodes visible; map list, centre panel, battle settings, the back and continue buttons in place (canvas + (320, 60)) | The heading's tree position (y −77) is pre-animation; the page shows placeholder text and one `name / 4 on 4` row because the probe skipped what its button does first. Empire's `sp_battle2` has the same 46 names: the page is unchanged |
| `campaign.hud.card_strip` with a settlement selected (`campaign.json.gz` `campaign ui/layout`; `template.buildingframe`) | `j10_camp_settlement.jpg` | Innsbruck, Tyrol on the Construction tab: the selected `Building1` card, the empty `Slot2`, and `Building1_Upgrade1` with its 5-turn badge and 1,500 cost. The alternate chains and `Constructable1` are hidden in both tree and shot | The region panel is not opened by a selection (fact `napoleon.ui.campaign_selection_cards`). Empire's note that the upgrade card shows only for the selected building card (`LEARNINGS_ENGINE.md`) holds in Napoleon |

### Item 6: art by key
`discovery/ui/art_keys.json`, with `used_by` on the matched assets. J7 asked for db-key-driven names; these are the rules.

| Role | db table.field | Rule | Coverage |
|---|---|---|---|
| flag | `factions.flags_path` | `ui\flags\{value}\...` | 1,260 of 2,260 assets (all 53 factions resolve) |
| unit_card | `uniforms.uniform_name` | `ui\units\icons\{value}_icon.tga` | 1,064 of 1,105 (95 % of values resolve) |
| unit_info_picture | `uniforms.uniform_name` | `ui\units\info\{value}_info.tga` | 1,064 of 1,101 |
| technology_icon | `technologies.icon_name` | `ui\campaign ui\technologies\{value}.tga` | 67 of 69 |
| achievement_icon | `achievements.key` | `ui\achievements\{value}.tga` | 73 of 73 (96 % of keys resolve) |
| building_icon | `building_culture_variants.icon` | `ui\buildings\icons\{value}.tga` | 133 of 657 |
| building_info_picture | `building_culture_variants.icon` | `ui\buildings\info\{value}.tga` | 133 of 671 |
| event_picture | `cultures.fallback_ui_culture` | `ui\eventpics\{value}\...` | 229 of 229 (folder rule) |
| portrait | `ancillary_types.type` | `ui\portraits\{value}.tga` | 49 of 1,375 |
| loading_screen | none | no db field names these files | 0 of 22 |

The 13 frame groups put each `skins` 9-slice frame (corner, edge, fill) in one group, which answers J7's question: one group per frame, not one row per piece.

### Item 7: engine facts and README
New facts: `napoleon.ui.uied_templates_runtime`, `napoleon.ui.unshipped_scripts`, `napoleon.ui.panel_registry`,
`napoleon.ui.placeholder_text_keys`, `napoleon.ui.screen_routes`, `napoleon.ui.v039_layout_bases` (static); `napoleon.ui.layout_base`, `napoleon.ui.hud_placeholder_attach`, `napoleon.ui.frontend_credits_stops_pump`, `napoleon.ui.visible_not_inherited` and `napoleon.ui.campaign_selection_cards` (live, run
`20261102_j10pc`). `discovery/ui/README.md` is generated.

### Proposals (for Liam; UI_PIPELINE is not edited)
Complexity per unit is in `summary.json` `units.<id>.complexity`.

| Proposal | Unit | Components / states / text keys / art / interactions / templates | Reached live | Why |
|---|---|---|---|---|
| (a) small tabbed info panel | `campaign.region_details` | 94 / 136 / 60 / 73 / 10 / 4 | no: no proven safe route (probes send no clicks) | tabs, a data-heavy region readout, 4 templates; one getter (the region) feeds it all |
| (b) popup | `common.unit_information` | 138 / 354 / 61 / 87 / 14 / 12 | no: no proven safe route (probes send no clicks) | the richest popup: stats, abilities, a 3D preview (render_target) and the `UnitInfoPopup` panel id; shared by battle and campaign |
| (c) J33 test screens | `campaign.region_details`, `common.unit_information`, `battle.land_battle_orders` | orders: 52 / 202 / 27 / 127 / 29 / 0 | yes (41 of 42 names; the 42nd is a second root child that is in no live tree) | one panel, one popup, one HUD piece; the orders bar is the most state-heavy HUD piece (202 states, 29 interactions) and was reached in every battle |

### What J6, J7 and J9 asked of J10
- **J7: finer roles, db-key names, 9-slice groups.** Item 6 answers all three: key rules per role (`art_keys.json`), `used_by` on the matched assets,
  and 9-slice frame groups instead of a row per piece. J10 kept J7's roles.
- **J7 review: empty db tables.** The art rules use seven tables (`factions`, `uniforms`, `technologies`, `achievements`,
  `building_culture_variants`, `cultures`, `ancillary_types`), all with rows; no rule reads an empty table.
- **J9: `engine_api.json` per state, argument counts.** Every getter the atlas names is checked against the table for the state its script runs in.
  The 13 not in the API and the 4 not in their state are listed in `summary.json`, not dropped.
- **J9 review 1: `campaign_show_prestige` is not the prestige panel.** The atlas does not use that state. `campaign ui\prestige` has no layout file
  (fact `napoleon.ui.panel_registry`).
- **J9 review 2: count Lua names from the table, not the report.** The atlas reads `engine_api.json` directly.
- **J9 review 4: move the fix probes into `proxy/napoleon/lua/probes/`.** Not done here: J10 changes no DLL input, so the 20-pass build stays valid.
  The J10 probes (`tree.lua`, `fe_page.lua`) are in the run folder too; both, with J9's, move at the next `proxy/napoleon` change (J24 is likely).

### Core later
`ui_atlas.py`'s readers (the layout walk, the handler owners, the live tree parser and matcher) are game-agnostic apart from `CONTEXTS`, `NAMES`,
`PIECES` and `STATIC_ONLY`. They move to the core when Empire's atlas is rebuilt on them; the tables become adapter data.

## Deviations from the brief and why
- **Call budget lifted by Liam.** The brief's limit was about 300 tool calls, about 100 of them on the PC. Liam lifted it during the job ("Override the tool
  call limit for this job"), as he did for J9. Every other kill criterion stayed in force.
- **Three crashes, all from one probe misuse of mine; no crash rule was triggered.** All three dumps fault at `Napoleon.exe+0x538e5` (read access
  violation) on the Lua thread (`raw/attempt1`, `raw/attempt2`). Each one is J9's `getters.lua` called without its list argument (`dofile(nil)`); the
  call times match the dumps to the second (07:59:15, 08:06:21.5, 08:19:33.4). The second and third came from attempt 1's driver: stopping its
  background task ended only the `tee`, so the old driver kept running beside attempt 2 under the same lock owner until 09:17. The tree probe, the end
  of deployment and the battles are not involved, so nothing is `static_only` for a crash. Code fix: the drivers write a pid file and refuse to start
  while another driver is alive, and they run without a pipe. Clean battle run: attempt 3 (`sit1.sh`, no crash).
- **A stale virtual-display restore record blocked every launch (J48).** The watcher had saved the virtual display's mode before the 08:05 launch
  (3840x2160 at 2560,1440). It could not restore it once the main monitor reported 3840x2160 at 0,0, so it refused every launch. With Liam's OK I
  moved `C:\napoleon_remastered_pc\watcher\vdisplay_restore.json` into the watcher's `_to_delete` folder, which J44 had also done by hand. This is
  more evidence for J48.
- **The front end took three sittings.** `sit1.sh` reset to the front end after `hist_dresden`. A warm reset from a historical battle stops at the
  post-battle screen; only `ctl scene` relaunches there. So its 13 pages ran inside the battle; those results are filed under
  `raw/attempt3_fe_in_battle` and not used. In the front end only the main menu pumps Lua (J9), so `fe_page.lua` takes each page's tree and returns
  to `main` in the same call. Front-end shots use `core/harness/shot.sh`, because `ctl shot` waits for a game scene; each shot stays on its page and
  relaunches. Entering **credits** stops the front-end Lua pump, so credits is `static_only` with that reason, and the pages after it were re-run
  in `sit1fe2.sh`.
- **The proxy log keeps only the last launch.** A sitting that relaunches loses its earlier trees from `proxy.log`. `parse_trees` also reads each
  ctl result's `log` list, which carries the same lines, and a later file replaces a label whole. Both have tests.
- **Probes stay in the run folder.** `tree.lua` and `fe_page.lua` live in `harness/runs/20261102_j10pc/probes/`, like J9's fix probes, because
  `proxy/napoleon` is a DLL input and changing it would void the 20 passes. `fe_page.lua` calls `TransitionTo` (a page change, as J9's
  `fe_pages.lua` did); `camp_select.lua` and `camp_panel.lua` (J9) select and open panels. Nothing else changes state.
- **Getters were sampled with J9's `getters.lua`** in battle, the front end and the campaign. J9 already has these samples per state; J10 adds
  no new getter list.
- **Loc text is never committed.** The atlas records text keys and whether they resolve, not the text, as the brief's data rules require.
- **The v4 template records are not read.** These are the two UI-editor records; Empire's reader fails on them too.
- **Not reached in battle: unit information and the escape menu.** The brief lists them under the battle states.
  They open on a click or a key, and the probes send no input (the brief's no-setter rule). They are `static_only` with that reason. The
  advisor panel itself was reached (`common.advice_interface`).
- **One file copy overwrote the real front-end results, then was repaired.** Sitting 2 shared the attempt-3 scratch folder with `sit1.sh`. Its
  final copy brought back the in-battle front-end results over the `sit1fe` ones. I removed the 53 files identical to those under
  `raw/attempt3_fe_in_battle` and copied `sit1fe` and `sit1fe2` again. `shots.json` takes each shot from the sitting that made it.
- **The `all` step now redoes the live match.** `wsc discovery ui` first kept an old `reach.json`, so units stayed `static_only` after the atlas
  changed. Now the step re-matches the run that `reach.json` names, and a `PIECES` path that is no component fails the build (the minimised HUD
  pieces were wrong).
- **No contact sheet.** That was a stretch goal. `shots.json` indexes all 31 shots (state, PC file, sha256, the units each shows), and the three
  spot-check shots are in the run folder.

Re-run evidence: two `python3 core/wsc.py discovery ui` runs gave byte-identical outputs. The sha256 prefixes are `battle.json.gz` 1235a2fc, `campaign.json.gz`
1281143e, `common.json.gz` 0d1c46f3, `frontend.json.gz` bf771178, `template.json.gz` 5a282e25, `scripts.json.gz` 0a20db25, `units.json.gz` 83308245,
`summary.json` 85a0ee58, `reach.json` 86822eca, `engine_drawn.json` 3e5e3b09, `art_keys.json` 065c15f2, `ui_elements.jsonl` eae3c82d and
`assets.jsonl` 212b5a9b. `summary.json` records the full sha256 of each atlas file, and `discovery check` verifies them.

## Open questions
1. **Proposals.** Confirm or overrule (a) `campaign.region_details` as the small tabbed panel, (b) `common.unit_information` as the popup and (c)
   those two plus `battle.land_battle_orders` as J33's three test screens.
2. **The layout base.** At 1920x1080 the UI is not scaled: the 1280x960 layout canvas is drawn at 1:1 pixels and its components dock to the screen
   edges (`napoleon.ui.layout_base`). J33's design language needs a scaling rule for 1440p and 4K. Should it scale uniformly by height (1080/960)
   or keep 1:1 like vanilla? This is a design choice for Liam, not an engine fact.
3. **Core backlog.** `job.sh lock` lets two drivers with the same owner run at once, and a Claude background task's stop ends only the end of a
   pipeline in Git Bash. The pid-file guard here is local to the J10 drivers. A core guard (an exclusive driver token per lock) would stop the next
   job from repeating this. Should it be a backlog row? The same row could make `ctl reset` relaunch from a historical battle, as `ctl scene`
   already does, rather than stopping at the post-battle screen.
4. **Units that need input.** 69 units have no proven safe route, mostly panels opened by a click: unit information, the region details and
   the escape menu. D39 leaves event-only units to the contract stage. Should click-opened panels be captured there too, from a staged save with
   a scripted click, or in one Liam-present sitting before J33?
