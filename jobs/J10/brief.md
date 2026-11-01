# J10: Vanilla UI atlas

Phase 2, discovery (`docs/plans/UI_PIPELINE.md` section 2.1, `docs/plans/PLAN.md` phase 2). Write down what the vanilla UI is, once, so that
every later UI job cites registry ids instead of searching: every screen and popup with its elements, the data each element shows and the
getter, db table or loc key behind it, every interaction and the handler behind it, its states and its art; plus everything the engine draws
outside the layout system, with a route for each (rebuilt in RmlUi from engine data, an engine render target shown in an RmlUi element, or left
engine-drawn). The result seeds `registries/ui_elements.jsonl` at status `atlas` (the gate: "screen present in the atlas with elements, data and
interactions", UI_PIPELINE section 3). J33 (design language: real data and art for three test screens), J32 (host route per screen kind), J37
(engine-drawn text) and the contract stage of every screen read it. Nothing is designed, rebuilt or hooked here.

Model: Sonnet, medium effort (D15). Python in this repo and Lua probes in the game's own Lua; no DLL work, no change to `core/`, `proxy/` or
`harness/` (rule 79 must not apply: see Decisions). If the V039 layout format turns out to need exe reverse engineering, that is a kill criterion
and an Opus job, not a change of model here. Budget about 300 tool calls, of which the PC part is about 100; at the cap, stop, commit, report what
is left. Read-only subagents are welcome (D34) for the static walk, at most one per context (front end, campaign, battle), each capped at about
80 calls and told to write only their own output file; check their output before it is committed. Waiting belongs to the harness: `job.sh`, `ctl.py`
and the probe drivers block inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J10`; "The game is launched ... only through the watcher"; "Exe stays vanilla on disk (D2)"; "Never run git in a
  game folder"). Read `docs/DECISIONS.md` (D6, D7, D8, D14, D19, D34, D37), `docs/plans/UI_PIPELINE.md` sections 2 and 3, and `jobs/J6/report.md`,
  `jobs/J7/report.md` and `jobs/J9/report.md` (their "Open questions" name this job: J6 "layouts", J7 "For J10", J9 "J10").
- Search before writing: `python3 core/wsc.py find layout uic tpl luachunk api_inventory engine_api probe ui_tree autostart reset fonts cuf`. Reuse:
  - Static: `discovery/core/{uic,tpl,luachunk,api_inventory,layouts,lua_api,fonts,cuf,engine_api,exe_strings,packfs,loc,db}.py`, the J6 results
    `discovery/diff/{layouts,lua_api,fonts}.json`, J9's `discovery/napoleon/{engine_api.json,lua_cfuncs.json,probe_safe.json}` and `exe_strings.tsv.gz`, J7's
    `discovery/assets/{index.tsv.gz,refs.json}`, `registries/assets.jsonl`, `discovery/loc/keys.tsv.gz`, `discovery/db/tables.json`, `registries/hotkeys.jsonl`
    (128 vanilla rows), `discovery/napoleon/{frame_anatomy.md,shader_catalog.json}` (J8, for what the frame draws outside the UI).
  - Live: `proxy/napoleon/lua/probes/{ui_tree,api_surface}.lua`, `proxy/napoleon/lua/{autostart,reset}.lua`, `harness/ctl.py` (`scene`, `reset`, `shot`, `state`),
    `harness/core/shot.sh`, `core/harness/job.sh`, `core/proxy/tools/pc_deploy.py` (kit, install, uninstall, snapshot, diff). The scenarios are in
    `registries/scenarios.jsonl` (`land_small`, `naval_small`, `siege_small`, `hist_*`, `campaign_start`, `campaign_britain_1805`).
  - **J9's fix-round run `harness/runs/20261101_j9fix/` is the working recipe** for reaching screens: front-end pages with `fe_pages.lua` (TransitionTo, as
    `autostart.lua` does), campaign panels with `camp_panel.lua` (the root functions the menu buttons call; hotkeys do not work), selections with
    `camp_select.lua`, getter samples with `getters.lua`, visible top-level components with `vis.lua`. Probes run from the run folder by absolute path through
    the proxy's `lua` verb so that `proxy/` stays untouched. Its "What did not work first" list is required reading.
- Evidence base `empire-remastered` (read only, never modified; bring it in with `--add-dir ../empire-remastered`): the method, not the facts.
  `rml_mod/docs/atlas/atlas_static.py` (static atlas: layouts + templates + compiled scripts with a symbolic register walk that attributes field names to
  engine getters), `rml_mod/docs/atlas_live/README.txt` (live probe findings), `rml_mod/tools/battle/{dump_battle,gen_parity,luasym,script_index}.py`,
  `rml_mod/docs/BATTLE_HUD_NOTES.md` (parity tables; section 3.6 and its "engine-drawn: radar picture, banners, 3D markers, selection box, cursor"),
  `rml_mod/design/screens_schema.md`. Port, don't copy blindly: every Empire fact about layouts, scripts and getters is checked again on Napoleon.

## Target facts
Check again before relying on them; record what changes as `engine_facts` rows (date and run id):
- 174 layouts (J6): `campaign ui` 52, `frontend ui` 40, `templates` 40, `battle ui` 24, `common ui` 18; versions 028-033 (38 files) all round-trip, **Version039 (136
  files) round-trips for 45 only** (facts `napoleon.diff.layouts.v039`, `.v039_transitions`: state transitions are about 18 bytes, keyframe fields partly guessed).
  `uied.templates` records are v35 (not decoded) and v39. 497 compiled UI scripts parse (`luachunk.py`). So the first deliverable is a reader that gets all of them.
- The engine API per state is J9's `engine_api.json` (19 states, 5,521 names, binding argument counts for 986 C functions, 45 probe-safe getters with samples).
  Engine bindings read arguments from the top of the stack down: an extra argument shifts every value (`napoleon.lua.arg_stream`). Never use `string.find`,
  `string.sub` or `gmatch` in engine Lua (`napoleon.lua.string_find_stalls_pump`); `string.match` is safe. `SelectAndZoomToRegion(nil, -1)` crashed the game
  (`napoleon.campaign.region_list_no_address`); `ShowPrestige` needs menu arguments.
- J7: 12,295 UI-first asset rows in 15+ roles; 10,500 have no string reference (flags, unit cards, portraits and similar are named from db keys at runtime); `refs.json`
  names referrers (files), not screens. `registries/assets.jsonl` rows have a `used_by` field whose items must be `ui_elements` ids (schema `x-ref`).
- Display model: the vanilla layout base resolution is unknown for Napoleon (Empire's was 1280x960, scaled by the engine); measure it (the layout coordinates
  against the live component rects and a shot) and record `napoleon.ui.layout_base`.
- Known risks: `napoleon.proxy.init_heap_corruption` (a launch that dies at init is not the probes' fault); the front end is the main menu pump only until a page is entered.

## Decisions already made for this job
Settled by the conservative reading of the row and D38; Liam can overrule in the review.
- **Row granularity.** A `ui_elements` row is a **pipeline unit**: one vanilla screen, popup, HUD piece, tooltip family or shared widget (the thing that goes
  through `atlas -> contract -> design -> ...`), not one row per component. Element-level detail (every component, rect, state, text key, font, art, event, handler) lives in
  the atlas files and is linked from the row's `vanilla_source.layout`. A layout that is several pipeline units (the battle HUD is one layout with the radar, card strip,
  order bars, minimap frame, message stack) gets one row per unit with `screen` = the layout's screen id. Expect about 150 to 250 rows; state the number.
- **Ids.** `<context>.<name>`, lower case, spaces to underscores, `context` one of `frontend`, `campaign`, `battle`, `common`, `template`, `engine`; for example
  `campaign.region_details`, `battle.land_battle_orders`, `template.unit_card`, `engine.battle_radar`. Ids never change afterwards (J33, J35 and every contract cite them). Pieces of a
  layout append `.<piece>`. `screen` is the id of the screen the unit belongs to (equal to `id` for a whole screen). `template` rows list the screens that instantiate them in
  `description`, and the screens' atlas files list the template rows.
- **Row content at status `atlas`** (schema `core/schemas/ui_elements.schema.json`; `core/` cannot change):
  - `description`: what it is, when it shows, who opens it (the entry point), and for `engine.*` rows `route: rml | render_target | engine_drawn` first, then why;
  - `vanilla_source.layout` = the layout path and `vanilla_source.script` = its `.luac` path(s);
  - `data_fields`: every field the unit shows, `source` = `getter:<Owner>.<fn>[.<path>]` (traced to the engine call whose result the script reads),
    `loc:<key>` (text from `ui.loc` / `localisation.loc`) or `db:<table.field>` (a field whose value is a db key, only with evidence: a loc prefix, a script that
    names the table, or an art rule in `art_keys.json`). A field no source can be traced for stays out of the row and goes in the atlas file under `unresolved` with the
    reason (the contract stage must answer it); never invent a source to fill the row;
  - `interactions`: one entry per interaction, `name` = the component, the event and the handler (`btn_ok LClickUp -> Lua OnClick (campaign ui/foo.luac) -> CampaignUI.Bar`);
    `decision` and `reason` are not set at this status (the schema requires them from `contract`); a display-only unit carries one entry named `none: display only`;
  - `status`: `atlas`. `review_link` stays empty.
- **Reach, not guess.** Every unit says in the atlas file how the live game shows it (`reach`: the route that opens it, `reached` with a run id, or `static_only` with the
  reason: needs a multiplayer lobby, needs an event, destructive to open, no safe route). `static_only` is allowed and must not be hidden; the contract stage handles it.
  The static layout and the live component tree are compared for every reached unit (ids in the layout, ids on screen, which differ) and the agreement is a reported number.
- **Probes read, never act.** Live probes only open and close screens through the routes J9 proved (root functions, TransitionTo, SelectAndZoom with nil-guards, `scene`/`reset`), enumerate the
  component tree, call getters from `probe_safe.json` and getters whose script call site you have read and whose arguments are known. No setter, no order, no end turn, no save written except through the
  existing stage tools; Liam's preferences, keys and saves are never touched. A getter outside the probe-safe list is `static_only` for its fields until a call site justifies it.
- **Asset roles stay as J7 set them.** The J36 and J51 upscale packs and manifests are built per role (`upscale/napoleon/config.json`), so renaming or splitting a role would invalidate them. J7's
  open questions are answered in the atlas instead: the 9-slice and 3-slice frame pieces of `skins` are grouped by the component state that draws them (`frame_groups` in the atlas file, with the asset
  ids and the slice insets the layout gives), the `icon` / `ui_art` and `button_state` / `panel_frame` splits stay path rules, and no `assets` row is added or removed. A role that is clearly wrong on a
  sheet is listed in the report for a later asset job.
- **Art by key.** For the roles named at runtime from db keys (`flag`, `unit_card`, `portrait`, `unit_info_picture`, `building_info_picture`, `building_icon`, `event_picture`, `technology_icon`, `achievement_icon`,
  `loading_screen`) write the rule in `discovery/ui/art_keys.json`: db table and field, the string the script assembles (read from the compiled script; the 561 unresolved strings in `refs.json` are
  the starting list), and the resulting path. Verify every rule against the asset index (resolve rate and the misses listed). Then `used_by` is filled for those assets with the unit ids,
  through the generator so a re-run keeps it. Do not decode all 310 db tables again; read only the tables a rule names (`/extract/napoleon/db/`).
- **Rule 79 does not apply.** All new Lua probes live in `harness/runs/<run id>/probes/` and run from there by absolute path (as J9's fix round did); nothing under `proxy/` or `harness/core` changes, so
  the 20-pass build stays valid. A probe worth keeping moves into `proxy/napoleon/lua/probes/` at the next DLL change, and the report says which.
- **Proposals, not decisions.** UI_PIPELINE 2.6 says the proving screens are picked after the atlas, and J33 needs three test screens. The atlas computes a reproducible complexity record per unit (component
  count, states, text keys, art count, getters, interactions, templates used, live-reached or not) and the report proposes (a) a small tabbed info panel, (b) a popup or tooltip (unit information), (c) the three J33
  test screens (rich in data, art and states; one panel, one popup, one HUD piece), each with the reason. Liam confirms; do not edit UI_PIPELINE.

## Deliverables
Priority order; at the cut line stop and report (the cut line is marked). Each item is a committed tool with a header and a `tools` row (header format `core/warscape/tools.py`; extend the `wsc discovery`
verb in `tools/verbs/discovery.py` with a `ui` pass rather than adding a second CLI), deterministic output (sorted, no timestamps, deterministic gzip as `tsvgz.py`), a host test on a synthetic fixture
in `tests/test_discovery_ui.py` (stdlib only; skip with a reason what needs capstone or Pillow), and a check in `discovery check` that the committed results are current.
1. **Layout reader** (`discovery/core/uic.py`, `tpl.py`). Finish Version039 (state transitions, animation keyframes, the v35 template record) so that all 174 layouts and every `uied.templates` record
   parse; byte-exact round trip is the check (it proves the decode), but a layout also counts as read when the parse consumes the whole file with a sane tree. Report the counts before and after
   (`discovery/diff/layouts.json` re-run). Time-box in Kill criteria. Update `napoleon.diff.layouts.v039*`.
2. **Static atlas** (`discovery/core/ui_atlas.py` -> `discovery/ui/<context>.json.gz`, `discovery/ui/summary.json`). Per layout and per template record: components (id, type, parent, rect and anchors,
   default visibility, priority), states (name, image ids resolved to `assets` ids, text key, font name, colours), transitions and animations, events and their handlers (a script function or inline Lua),
   tooltip keys, text keys resolved to `loc` text, fonts, the templates instantiated, and the engine calls each handler makes. From the compiled scripts (`api_inventory` / `luachunk`, the symbolic register walk of
   Empire's `atlas_static.py` re-done on Napoleon): the fields each script reads off each engine result and where the data was passed in (`Initialise(details)`, `panel_manager.OpenPanel`, `LuaCall`,
   `SetSpecialTooltip`). Every getter named must exist in `engine_api.json` for the state it runs in (a name that does not is listed, not dropped). Scripts attached to no surface are listed. Record the
   hotkeys a screen answers (`OnShortcut` actions matched to `registries/hotkeys.jsonl` ids).
3. **Registry rows** (`registries/ui_elements.jsonl`, generated: `discovery/core/ui_atlas.py rows`, then `reg add` / the registry framework; `reg check` must pass). One row per pipeline unit as in Decisions, all at `atlas`.
   Then `used_by` on the assets the units draw (`registries/assets.jsonl`; x-ref check). Coverage table in the report: layouts, templates, scripts, units, fields, interactions; unresolved fields by reason.
4. **Engine-drawn list** (`discovery/ui/engine_drawn.json`, rows `engine.*`). Everything on screen that is not a layout component: at least the battle radar (land, naval), unit banners and flags
   (and the `3D_` components the layout system places for them), map labels and the campaign map and its minimap, selection box, move and attack markers, cursors (the 179 `cursor` assets), 3D previews
   (unit and building previews, the battle setup), movies and loading screens, the escape menu background, damage and tooltip overlays, anything a shot shows that no component explains. For each: what draws it
   (exe string, shader from `shader_catalog.json`, render target from `frame_anatomy.md`, or a script call such as `Init_Radar`), the data and interactions it has (the radar has drag, double-click and right-click
   handlers in the HUD's Lua), a shot, and a **proposed route** with the cost: `rml` (rebuilt from engine data, which data), `render_target` (an engine texture shown in an RmlUi element, which texture and
   what the host must provide), or `engine_drawn` (then its font route is Empire's `.cuf` route, D7, which J37 owns). Evidence labels as in Empire's notes: read (layout, script, exe) or observed (run id).
   The report ends this section with a table: item, route, why, which later job owns it.
5. **Live pass on the PC** (see PC test): component tree per reached unit, the visible top-level components (`vis.lua`), getter samples for the probe-safe getters in the state they run in, one shot per unit at
   1080p. Compare with the static atlas (the agreement number). Reached/static_only for every unit in `discovery/ui/reach.json`.
   **--- cut line: items 1 to 4 are the deliverable; item 5 may be partial (say which contexts) and the rest follows. ---**
6. **Art by key** (`discovery/ui/art_keys.json`, `used_by` for the key-named roles) and the frame groups, as in Decisions. Stretch: a per-context contact sheet of the shots (one JPG per context, under about 1 MB each).
7. `engine_facts` rows `napoleon.ui.*` (layout base, how each screen kind opens, which screens only exist in a state, the radar and 3D preview findings, the V039 format) with date and run id, and
   a generated `discovery/ui/README.md` (counts, how to re-run, where the files are; under the doc cap). Do not copy atlas content into prose.

## PC test
Unattended and headless through the watcher, lock owner `J10`, no Liam needed; the visible play launch is never an agent's. If the lock is held by another job, wait through the watcher's own queueing in one
blocking call and do not poll; if the PC is not free after one such wait, commit what is done and report. Sequence (the J9 pattern): a) snapshot the game folder and send/install the existing proxy kit
(`pc_deploy kit`, `send`, `install`; nothing built here); b) front end: `fe_pages.lua` through every page that is safe, a shot and a tree per page; c) campaign: `campaign_start` and, for the fleet, the coalition
campaign as Britain through the proxy's `autostart campaign:new:mp_eur_napoleon:britain` (J9), selections (army, fleet, agent, settlement with the nil guard), every panel `camp_panel.lua` can open, popups that
open by root function; d) battle: `land_small`, `naval_small`, `siege_small` and `hist_*` in deployment and running (`scene --deploy end`), the order bars, card strip, unit information, escape menu, advisor;
e) uninstall and diff: the game folder identical to the pre-install snapshot, no lock, profile restored. Group launches so that one launch serves many units (J9 did 19 states); read WER and the dumps folder
after each launch. Raw logs and the drivers go in `harness/runs/<run id>/` (README with one line per state, as J9's); shots stay in the PC state folder (`captures`), the repo keeps an index (unit id, state, file,
sha256) and a few small JPGs only.

## Evidence required
- Counts, reproducible by `wsc discovery ui` and `wsc discovery check`: layouts and templates read (before and after), scripts walked, units and rows, fields (sourced / `unresolved` by reason), interactions, assets
  with `used_by`, engine-drawn items, units reached live of units total (per context) and the static-vs-live agreement.
- A re-run of every pass gives byte-identical files (state the sha256 of the committed results before and after, as J7 did); `reg check` and `python3 core/wsc.py gates` green; `ui_elements` rows pass the schema and every
  `used_by` resolves.
- Three units spot-checked by eye against a shot and against Empire's notes where one exists (for example the settlement or region panel, the battle order bar, the custom battle setup): row, atlas file, shot
  side by side in the report with what matched and what did not.
- Every `engine.*` row has a shot or a read source, and a route.
- Run ids on every live-derived fact. Facts verified carry date and run id (`verified_dates` gate).

## Kill criteria
- V039 reading: stop decoding after about 40 tool calls or when 95 % of the 136 files still do not parse to the end of file. Keep what parses, mark the rest `layout_unread` with the first failing offset and field, take
  those screens from their compiled scripts plus the live component tree (item 5), and report which units are thinner for it. If the next step needs the exe's layout loader (reverse engineering), do not start it: propose an
  Opus job with the failing offsets as its brief.
- A crash in a live launch that is not the known init heap corruption: read WER and the hang folder first, repeat once; the same crash twice on the same probe: stop that probe, keep the dumps, mark the units `static_only` with
  the crash as the reason, and carry on with other contexts. The same init heap corruption twice in a row: stop the PC part, report the dump names and `napoleon.proxy.init_heap_corruption`; it needs the crash job, not more launches.
- Any probe that would need a setter, an order, a save write, a proxy or DLL change, a change under `core/` or `harness/core`, or a write into a game folder outside `pc_deploy` and a watcher job: stop and ask Liam.
- The uninstall does not end `identical` after one honest repair: stop, report the diff, leave the kit out of the next launch.
- Over about 300 tool calls, or the PC part past about 100 of them: stop, commit what is committed, report what is left in cut-line order. Do not extend the budget; Liam can lift it as he did for J9.

## Open questions
Recommendations, for Liam to confirm or overrule in the review:
**Settled by Liam 2026-11-01 (D39):** all three as recommended: `engine.*` rows with the route in `description`; the atlas's routes are the default for J35 and J37; event-only units stay `static_only` and are captured in the contract stage.
1. **Engine-drawn items as `ui_elements` rows.** The schema has no `route` field and `core/` cannot change in this job, so `engine.*` rows carry the route in `description` (and in `engine_drawn.json`). Recommendation: do that
   now; a `route` field is a core backlog item if Liam wants it queryable. The alternative (engine-drawn items only in `engine_drawn.json`) hides them from `wsc find` and from the review page.
2. **Routes for the big engine-drawn items are proposals.** The radar, unit banners, the campaign map and the 3D previews decide how much of the HUD jobs is RmlUi work versus host work (render-target elements). Recommendation: take
   the atlas's proposal as the default for J35 and J37 and review it when J35 is briefed; Empire kept the radar and banners native.
3. **Units reachable only with Liam or an event** (multiplayer lobby, post-battle results, diplomacy events, tutorials, loading screens). Recommendation: leave them `static_only` with the reason and capture them in the contract
   stage from a staged save or a scripted battle ending, not in a sitting for the atlas. If Liam would rather see them all reached before the design language starts, that is one Liam-present sitting added to J33's start.

## Finish
Write `jobs/J10/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`, plus evidence): what exists and how to re-run it, the coverage table and the V039 result, the live
runs (ids, states reached, static-vs-live agreement, snapshot `identical`), the three side-by-side checks, the engine-drawn table with routes, the proposals for J33's test screens and the proving screens, the
`engine_facts` added, what J6, J7 and J9 asked of this job and where it is answered, and what moves to the core later (`ui_atlas.py` readers). Then
`wsc reg set jobs J10 status=review report=jobs/J10/report.md`.
