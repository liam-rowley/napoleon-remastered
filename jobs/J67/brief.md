# J67: UI scale stop-gap: Lua constants, 1440p factors, remaining screens

Phase 5, D40, part 2. J66 put the vanilla UI at 2x for 4K with data alone (layouts, `uied.templates`, Lora slot fonts, 2x art) and proved it headless: the front end, campaign HUD and battle HUD
draw at 2x and dock as at 1080p. What it could not scale by data, it listed. This job takes that list. Target: Liam plays at 3840x2160 and the screens he opens (tooltips, grids, settlement
panel, unit-card rows, map hover, the radar group, the front-end pages) are sized and placed right, with the same one-command install and a snapshot-identical uninstall; and the same set
exists for 1440p at 1.25x and 1.5x, with the choice for 1440p made from numbers and shots. The order is the cut line (below): 4K first, because that is what Liam plays today.

Model: Opus, reason: Lua 5.1 bytecode patching of 497 compiled scripts, working out why the radar group is misplaced (engine docking or a script), the engine's script-delivery behaviour probed in game, and a possible proxy file rule (D15). Budget about 260 tool calls, about 90 of them on the PC; at the cap, stop, commit, report what is left. At most 2 subagents, for independent work only (for example the Lua constant classification while you generalise the builder to other factors). Waiting belongs to the harness: `job.sh` and `ctl.py` block inside one call; never poll.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J67`; the watcher is the only launcher; D2: exe vanilla on disk; never git in a game folder; `empire-remastered` is read-only evidence). Read `docs/DECISIONS.md` D40 to D42.
- **J66 first** (merged): `jobs/J66/report.md` and `jobs/J66/review.md` (finding 2: the campaign minimap content stays 1x inside its 2x frame; it is not in the report's list), `uiscale/README.md`
  ("Held back at 1x"), `uiscale/runs/2026-11-02_j66/README.md` and its shots in `raw/` (`r2_land.jpg`, `r2_campaign.jpg`, `r2_frontend.jpg`, `r2_fe_single_player.jpg`), the code in `uiscale/core/`
  and `uiscale/napoleon/` (`config.json` already has `factors` and a `tag_of` for pack names), and `upscale/pc/play.py` (`install --scale`, `scale_files`, the UI-cache handling). Extend them; do not fork.
- **Engine facts:** `napoleon.ui.scale_2x_packs`, `napoleon.ui.canvas_docks_scaled`, `napoleon.ui.layout_base`, `napoleon.ui.font_slots_2x`, `napoleon.ui.templates_route`, `napoleon.ui_art.movie_pack_overrides`,
  `napoleon.packs.dev_pack_precedence`, `napoleon.ui.unshipped_scripts`, `napoleon.ui.panel_registry`, `napoleon.lua.update_callbacks`, `napoleon.diff.lua_api.surface`.
- **Registry ids (cite and search by these, never by a pack path):** scripts are `assets` rows (`python3 core/wsc.py find <script name>`; for example `ui/templates/template.map_image.luac`, `ui/templates/template.tooltip.luac`,
  `ui/battle_ui/root.luac`, `ui/campaign_ui/layout.root.luac`). Screens are `ui_elements` rows: `battle.hud.radar`, `battle.minimised_hud.radar`, `campaign.hud.radar`, `engine.battle_radar`, `engine.campaign_radar`,
  `engine.tooltips`, `template.tooltip`, `template.map_image`, `campaign.region_details`, `campaign.popup_pre_battle`, `frontend.main`, `frontend.sp_battle1`, `engine.loading_screen`, `engine.cursors`.
  In the brief, report, facts and tool output name game files by registry id or repo path, not by a pack-form or extracted-store path (a found-path rule is coming from J11).
- **Empire evidence** (`C:/Users/liamr/repos/empire-remastered`, read only):
  - On main: `ui_scale_mod/lua/patches.txt` (every Lua fix with its comment: the syntax in its header, the screens it covers, the why), `ui_scale_mod/README.md` lines 57-125 (what was learned the hard way; Lua fixes so far; the open list),
    and the tools `luapatch.py`, `apply_patches.py`, `consts.py`, `luadis.py` (`const_uses`), `scale.py` and `scale_templates.py` (the `TEMPLATE_OVERRIDES`).
  - On branch `origin/ui/multiscale` (read with `git -C ../empire-remastered show origin/ui/multiscale:<path>` from a normal checkout): `ui_scale_mod/docs/multiscale.md` (sections 3.2, 4, 10 and 11) and `multiscale_check.py`.
  - `docs/learnings/LEARNINGS_ENGINE.md`: the multi-scale lines (about 140-150 and 391-393) say the per-factor build, why 1440p used 1.25x (1.5x overflowed the 1024-tall panels by 96 px; only `popup_pre_battle` and `prestige` lost content), and that texture sizes use `ceil`.
- **Already ported** (`discovery/core/`): `luachunk.py` (parse, edit primitives and the assembler, byte-exact on all 497 scripts), `ui_walk.py` (symbolic walk: which getter feeds which field), `uic.py`, `tpl.py`, `cuf.py`, and the Lua API inventory (`discovery/napoleon/engine_api.json`,
  `lua_cfuncs.json`). Use these. What is **not** ported is Empire's patch applier, constant-use lister and check tool: write them in `uiscale/core/`, shaped like the rest.
- **PC probes that open screens without a click or hover verb:** J10's `harness/runs/20261102_j10pc/probes/` (`tree.lua`, `fe_page.lua`) and J9's `harness/runs/20261101_j9fix/probes/` (`camp_select.lua army|agent|settlement`,
  `camp_panel.lua <root function>`, `vis.lua`) with the driver scripts `sit1.sh`, `sit1fe.sh`, `sit1fe2.sh`, `sit2.sh` in the J10 run folder. `click`, `key` and `wait` are probe-only ctl verbs (rule 78: never in a scenario row or script); look at what the
  installed watcher actually offers before relying on them. Known traps from that run: argument-less getters calls crash the game; credits stop the front-end pump; a warm reset from a campaign stalls (`napoleon.campaign.quit_to_menu`).

## Scope against J37 (read this before building)
J37 (engine-drawn text and fonts, queued) also extends J66's font pipeline. The two jobs share files, so the line is drawn here:
- **J67 owns the per-factor layout side:** the factor list, pack and file names per factor, the layout and template and art builds at 1.25 and 1.5, and the table that says, for each factor, which slot `.cuf` files the scaled **layouts and templates** name
  and at what render size. That table is a data file (`uiscale/napoleon/font_slots.json`: factor, slot file, render height, bold and spacing flags) read by the font build; J67 builds `ui_scale_<tag>x_fonts.pack` for 1.25 and 1.5 from it.
- **J37 owns engine-drawn text:** the inventory of engine text items, any extra slots they need, the loading-quote and subtitle fonts, the consistency check that every font name resolves in the pack, and the licence data. J37 adds rows to the same slot table
  (a separate `engine_text` key), and extends the same `wsc uiscale` verb; it does not change the layout rows.
- **Not here:** the map and unit labels, the version string, the loading quote and subtitles are J37's. Do not build a second slot table, encoder or check for them. If J37 has merged when you start, build on its table and check verb; if it has not, create the table with the `layouts`
  key only and leave room for J37's key, and J37's builder will rebase onto it.
- The 2x fonts pack from J66 does not change except by the slot table moving into data (its bytes must stay identical: a test pins this).

## Decisions already made for this job
- **Lua is delivered the way the 4K layouts are: as entries in `ui_scale_<tag>x.pack`** (a movie pack, `mod_packs`), at each script's own pack entry. Probe it first (below). One patched list per factor, built from one factor-neutral list.
- **The patch list is factor-neutral.** `uiscale/napoleon/lua_patches.txt` uses Empire's syntax (`func:K` scale a constant, `func:K=v` set it, `func@pc[INSTR]=INSTR` replace with a vanilla-instruction assert first, `func@pc+INSTR` insert) but every number is stated in **vanilla pixels**,
  and the builder multiplies by the factor with the one shared `px(x) = floor(x + 0.5)`. Empire's list has 2x results baked in (a `28` that is 14 vanilla, `900` that is 450); port the vanilla value, not the 2x one. A test pins that factor 1.0 changes nothing.
- **Every patch asserts the vanilla instruction it changes**, so a game update fails the build loudly instead of patching the wrong constant. Constants are float32 (Napoleon's Lua number): patch in place with `luachunk.py`; every patched chunk must still round-trip, and a build is byte-identical on a re-run.
- **Classify, do not guess.** A generated list `uiscale/napoleon/lua_consts.json` (a `wsc uiscale lua-consts` pass over the 497 scripts) holds every numeric constant that reaches a pixel-taking engine call or a position or size calculation (Resize, position and offset setters and getters from the API inventory,
  arithmetic on component positions and dimensions, grid pitches in loops), each with script id, function, pc, the call and a class: `scale`, `set`, `leave` (with a reason: a time, a count, an index, an alpha, a colour) or `manual` (needs inserted instructions). No `unclassified` row may remain. Start from Empire's `patches.txt`, check each item against
  Napoleon's own script (the scripts are mostly the same lineage, but they are not byte-identical), then add what only Napoleon has (naval, the Napoleon-only panels).
- **Edit constants first.** An item that needs inserted instructions (Empire's right-hand tooltip padding, the government text) is `manual`: do the ones that show on screens Liam opens, to a limit of about 15 in all, and list the rest in the report with the screen they affect.
- **Delivery under the dev wrappers.** The proxy kit's dev pack wraps four root scripts (`proxy/napoleon/lua/wrappers.txt`: the front end's main advert and root, the campaign root, the battle root); a wrapper runs the vanilla copy with `wsp.vanilla`, and `dev.lua_bridge` is on for the harness but not for Liam's play install. Find out which copy `wsp.vanilla` returns when a scale pack
  patches one of those scripts (the battle root and the campaign root are likely patch targets), so what the harness shows is what Liam gets. If they differ, say so in the fact and test the play condition too.
- **Factors:** built 1.25, 1.5 and 2.0, one installed at a time (`play.py install --scale F` refuses a second while one is in; `uninstall` is unchanged and ends `identical`). Packs and files per factor named by `tag_of`; every name goes in `discovery/napoleon/games.json` `mod_packs` with `tests/test_mod_packs.py`.
  1080p stays vanilla (no packs). Rules: the scaled layouts' edge snapping at the new factors (the abutting-pair tests exist for 1.25, 1.5 and 2), `ceil` texture sizes, templates' embedded TGAs resampled with Lanczos at non-integer factors (nearest neighbour only at integer factors: 2x as J66 did), art from the J36 2.5x masters
  with the upscaler's resample code. D5's slider is not built here: a factor is fixed at install.
- **1440p factor: decide from data.** Empire chose 1.25 because its 1024-tall panels overflowed at 1.5. Napoleon's layout root is 1280x960 (`napoleon.ui.layout_base`), and 960 x 1.5 = 1440, so 1.5x may fit where Empire's did not. Do not assume either way. A `wsc uiscale check --factor F --height H` pass (Empire's `multiscale_check.py` idea, ported) reports, for each layout, the scaled root and
  the extent of its components against the screen, abutting-pair gaps and overlaps against the vanilla pairs, template image-def and TGA pairing, and the font names against the pack's slots (the slot half is the table above; J37 later adds the engine-text half). Choose 1.5 only if that check lists no layout that loses content at 1440p **and** the 1440p shots read better than 1.25; otherwise 1.25. State the choice and the numbers.
- **Held back, as J66 did:** an element no data or Lua constant can fix is left at 1x and listed with its `ui_elements` id and the reason.

## Deliverables
1. **Lua tooling and list:** `uiscale/core/lua_patch.py` (apply a patch list to a chunk, assert, scale by factor; `luapatch` and `apply_patches` of Empire, on `discovery/core/luachunk.py`) and `uiscale/core/lua_consts.py` (the classification pass), `wsc uiscale lua-consts`, `lua-patches` (apply, `--check` verifies every assert against the installed game's scripts) and the
   `build` verb writing the patched scripts into `ui_scale_<tag>x.pack`. `lua_consts.json` and `lua_patches.txt` committed, regenerated byte-identically.
2. **Screens, 4K, in this order** (the cut line is after item f; each is fixed by the cheapest route: layout data, then a Lua constant, then `manual`, else held back and listed):
   a. **The battle radar group and the Start Battle box** (`battle.hud.radar`, `battle.minimised_hud.radar`, `engine.battle_radar`): found about 1290 px (4K) left of the top-right corner. Find the cause first (an engine docking rule, a script constant such as a screen-minus-canvas offset in the battle root, or the minimised-HUD adjustment Empire patched) and record it as a fact.
   b. **The campaign minimap content** (`campaign.hud.radar`, `engine.campaign_radar`) filling about a quarter of its 2x frame, and `template.map_image` (map draw size and the hover and click mapping, which must change together: Empire's hover picked the wrong region when only the draw size changed).
   c. **Tooltips:** the generic tooltip's pre-size, padding and wrap widths (`template.tooltip` and the ornate ones, `engine.tooltips`); the first thing the J66 report says to look at.
   d. **Grids and fixed Resize calls** the classification finds: construction, recruitment, pre-battle units and reinforcements, results cards, message icon stack, diplomacy lists, character and agent panels (Empire's list is the checklist, Napoleon's list is the source).
   e. **The front end:** the clipped "New content" box and the pages J10 reached (the twelve `fe_page.lua` pages).
   f. **The campaign settlement panel and unit-card row, and the other unchecked screens** from J66's "Not seen" list: open them with the J9 and J10 probes and shoot them.
   g. After the cut line, only if calls remain: the loading screen's progress-bar textures (`engine.loading_screen`; Empire's recipe keeps the 1-px fill strip one pixel wide) and whether the cursor can follow by data (`engine.cursors`). Otherwise leave both, with the reason, for a later job.
3. **Factors 1.25 and 1.5:** `wsc uiscale build --factor 1.25|1.5` and the matching fonts, templates, rules and Lua; the check above green for 2, 1.5 and 1.25; `play.py install --scale 1.25|1.5` and its tests; `uiscale/README.md` gets a factor table for J38 (resolution to factor, the packs and their sizes, which factor ships for 1440p, and that the installer picks by resolution).
4. **Host tests:** patch applier (scale, set, assert failure on a changed instruction, insert, byte-identical re-run, factor 1.0 changes nothing, float32 rounding), the classifier on a synthetic chunk, `lua_patches.txt` parse and a `--check` against the game when present (skipped without it), the factor-neutral values at three factors, the font slot table at 2x byte-identical to J66's pack, per-factor builds and `play.py` install and uninstall `identical` against J53's fake game folder at each factor, a second install refused,
   `mod_packs`. Tools rows (header format: `core/warscape/tools.py`), `python3 core/wsc.py gates` green.
5. **PC (watcher, lock owner `J67`)**, three parts in one sitting each, headless:
   - **Probe the Lua route first** (one launch): a movie-pack entry at a script path replaces the script, using the first real patch whose effect shows on a fixed scene (the radar or minimap fix, or a marker constant if neither is Lua). If the pack entry is ignored, try the proxy's `dev.file_rules` `add` line (config only, as the fixed-sky and templates rules; no DLL change). Record `napoleon.ui.lua_pack_route`.
   - **4K, 3840x2160:** the patched 2x set; shots (1280-wide JPG, as J66) of the screens in item 2 at `campaign_start`, `land_small`, `naval_small`, `siege_small` and the front-end pages, with the J9 and J10 probes opening settlement, army, agent, building, technology, diplomacy, government and missions panels; a tooltip if a probe or a ctl verb can raise one. A screen table in the run report: screen, `ui_elements` id, state (`ok`, `fixed here`, `left` with reason, `unreached`). Load time against J66's 3.8 s.
   - **1440p, 2560x1440:** first check the virtual display and the profile can give that size (PLAN: Empire's could only do 4K; J53 ran 1080p, J66 4K). Then the chosen factor (and the other if calls allow) on `campaign_start`, `land_small` and the front end, with the overflow check's worst layouts opened. If the headless display cannot give 1440p after one honest try, build and host-test 1.25 and 1.5, mark them unproven in game in the README, the facts and `play.py status`, and list a 1440p shot sequence for Liam's visible sitting.
   - After each launch: WER and the dumps folder. At the end: the game folder snapshot-identical to the start, no proxy, lock released.
6. **`engine_facts` rows** with the run id: `napoleon.ui.lua_pack_route`, `napoleon.ui.lua_pixel_constants` (counts by class, the screens they cover), `napoleon.ui.radar_placement` (the cause), `napoleon.ui.scale_factor_1440p` (the choice and its numbers), `napoleon.ui.scale_1_25x_packs` and `napoleon.ui.scale_1_5x_packs` (proven or not), and an update to `napoleon.ui.scale_2x_packs` for each J66 held-back item (fixed, or still 1x and why). Docs: the "Held back" section of `uiscale/README.md` rewritten to what is left, and the `upscale/README.md` Play test section extended.
7. A dated run report under `uiscale/runs/`, and the final state: game folder snapshot-identical, no proxy, lock released.

## PC test
Headless through the watcher, lock owner `J67`. If the lock is held by another job, wait once through the watcher's own queueing; if the PC is not free after that, commit what is done and report. Do not start a visible launch: Liam plays the result later. Order:
- a) snapshot the game folder and compare it with the last known one, kit and send the proxy;
- b) the Lua route probe, then the 4K sweep with the 2x set;
- c) the 1440p part (display check first);
- d) everything out, `identical`.
The 4K part is done and committed before the 1440p part starts, so that the install Liam plays is never held back by the factors.

## Kill criteria
- The Lua route fails twice (pack entry ignored, then the `dev.file_rules` `add` line ignored): stop and ask Liam. A proxy or `wsp.lua` change is a DLL input, so rule 79 would apply (20 acceptance passes); do not start it here.
- The same crash twice in a row with the scale packs that is not the known init heap corruption (`napoleon.proxy.init_heap_corruption`): read WER and the dump first, then bisect by pack (layouts, Lua, fonts, art, templates) only if that takes under about 15 calls, and report which one. Do not hand Liam an install that crashes. A patch that crashes is dropped from the list with the evidence, not worked around.
- More than about 15 `manual` (inserted-instruction) patches look necessary for screens Liam opens: do the highest-impact 15 and list the rest.
- The 4K sweep still shows an unusable screen after one fix round for it: leave it, record the screen and the cause, and go on; do not spend the budget on one panel.
- The uninstall does not end `identical` after one honest repair: stop, report the diff, and do not hand Liam the install command.
- Over about 260 tool calls, or the PC part past about 90 of them: stop, commit, report what is left. At the cap the 4K part (items 1 and 2a to 2f) comes first; the factors may be reported as built and host-tested only.

## Open questions
1. **1440p default.** 1.25 or 1.5 (Empire: 1.25). This brief decides from the overflow check and the shots; Liam can overrule in the review. Whichever is not chosen for 1440p stays built (it may suit 1620p or ultrawide, which are out of scope).
2. **Pack size.** Three factor sets (about 1.8 GB at 2x; roughly 1.1 GB at 1.5x and 0.8 GB at 1.25x) is a large download for 0.1.0 (D42 ships the stop-gap). The installer picks one by resolution; whether all three ship, or the packs are built on the player's machine from the upscale work folder, is J38's call. Recorded in the factor table.
3. **Lua delivery under the dev wrappers.** If `wsp.vanilla` returns the unpatched copy for the wrapped root scripts, a patch in them applies in Liam's play install (bridge off) but not in the harness (bridge on), or the other way round. The brief asks for both conditions to be tested; if one cannot be, say which.
4. **Tooltips and hover.** There may be no way to raise a tooltip headless. Then the tooltip fixes are checked statically (the classified constants and the chunk round trip) and listed as "unseen" for Liam's first play session, with the exact screens to open.
5. **Loading screen and cursor** are after the cut line; whether they are worth a later job depends on how they look at 4K.

## Finish
Write `jobs/J67/report.md`:
- what was built, and the tools and commands;
- the screen table (screen, id, state) and what Liam will see at 4K and at 1440p, and what stays 1x or is unseen;
- the Lua patch list in numbers (classes, patched, left, `manual`) and the route the packs use;
- the PC evidence (job ids, run folder, shots, load times, snapshots);
- the exact install, uninstall and status commands for each factor;
- the factor table for J38;
- how the work was kept apart from J37 and what J37 should rebase onto;
- deviations from this brief and why;
- open questions.

Then `wsc reg set jobs J67 status=review report=jobs/J67/report.md`.
