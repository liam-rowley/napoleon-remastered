# J37: Engine-drawn text and fonts

Phase 5, D7. J10's atlas leaves a few things drawn by the engine, not by a layout or RmlUi: the text on battle unit banners and flags, the campaign map labels and settlement
bars, movie subtitles and the loading-screen quote. All of it is drawn from `.cuf` bitmap fonts (CUF0, the engine's only text path), which are fixed-size glyph bitmaps read at game
start. Empire's answer was to render the whole font set from a TTF (Lora, SIL OFL) into `.cuf` files and ship them as a movie pack that overrides the stock fonts. J66 (D40) now ports
that route for the layouts of the vanilla UI at 2x. This job is what J66 and J67 leave: prove, for every engine-drawn text item, which font file it uses and that it is crisp at 4K with the
J66 set; close the gaps J66 does not cover; and record the fonts and their licences for J38. Target: shots at 1080p and 4K from fixed poses show engine text at the right size and
sharp, and `fonts` and `licences` are in the repo for the release.

Model: Sonnet. Budget about 140 tool calls, about 50 of them on the PC; at the cap, stop, commit, report what is left. No subagents are needed.
Waiting belongs to the harness: `job.sh` and `ctl.py` calls block inside one call; never poll.
Python and shell only, in this repo. No change to `core/`, `proxy/` or `harness/` (rule 79 must not apply) and no exe patch (D2); a route that needs one is a kill criterion below.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J37`; the watcher is the only launcher; D2; never git in a game folder; `empire-remastered` is read-only evidence).
- **J66 first.** Read `jobs/J66/brief.md` and, once on `main`, `jobs/J66/report.md`, `uiscale/README.md`, the `uiscale/` tools and `uiscale/runs/`: they own the font build
  (Lora, freetype-py, line pitch h2 + 2), the font slots each context loads, `ui_scale_2x_fonts.pack`, and the install (`upscale/pc/play.py install --scale 2`). This job extends
  them; do not write a second font encoder, pack builder or installer. Also read the J67 row (`wsc reg`): its Lua constants and other factors are not this job.
- **Empire evidence** (`C:\Users\liamr\repos\empire-remastered`, read only): `docs/ui/FONTS.md` (the whole route: delivery proven, line pitch, the exe's hardcoded name list, "Exe findings"),
  `ui_scale_mod/README.md` (fonts lines and the problems list), `ui_scale_mod/FORMAT.md` "Bitmap fonts", tools `cuf.py`, `cuf_encode.py`, `build_lora_set.py`, `build_fonts.py`, `check_install.py`,
  and `docs/plans/LEGAL_NOTES.md` (rows A2 FreeType, A6 Lora; the `.cuf` files carry no font name, so none is named "Lora").
- **Napoleon facts:** `napoleon.diff.fonts.cuf` (74 `.cuf`; 73 byte-identical to Empire's; `editor_13.cuf` is new), `napoleon.ui_art.movie_pack_overrides`, `napoleon.ui_art.hires_same_rect`,
  `napoleon.files.loose_override`, `napoleon.ui.layout_base`, `napoleon.campaign.camera_route` and `napoleon.campaign.determinism`, `napoleon.battle.camera_route`, and the J66 facts when they exist.
- **Atlas rows:** `engine.battle_unit_banners`, `engine.campaign_map_labels`, `engine.subtitles`, `engine.loading_screen` (`python3 core/wsc.py find engine`; detail in `discovery/ui/engine_drawn.json`
  and `jobs/J10/report.md` item 4). `engine.cursors` is not text and stays a later art job.
- **Exe strings** (`discovery/napoleon/exe_strings.tsv.gz`, read with J9's tools): the hardcoded font name list (`Ingame 10 ... 24`, `Frontend 12 ... 38`, near rva `0xff1d78`), the loading-screen
  quote files `frontend_10.cuf` to `frontend_20.cuf` (rva `0x100cfe0`, code refs near `0xd0d907`), the `font/` and `.cuf` path pieces (`0x1012e84`), `fontsize` (`0xf1565c`), and the subtitle strings
  (`Display subtitles during movies`, `subtitles_table`, `videos_subtitles_junctions_table`, `read_subtitles_file`). Empire's identical list explained "only some sizes load".
- **Search first:** `python3 core/wsc.py find cuf font engine_drawn`. `discovery/core/cuf.py` (read and re-serialise) and `fonts.py` (name map) exist; `layouts.py` reads each layout's `fonts_referenced`.
- **Also read:** `docs/plans/UI_PIPELINE.md` sections 1, 2.1 and 2.5 (engine-drawn text follows Empire's `.cuf` route; scale model), `jobs/J38/brief.md` (the `LICENSES.txt` data it expects from this job),
  and `harness/runs/20261102_j10pc/README.md` (the shot and scene sequence that worked).

## Target facts
Check each again before relying on it, and record the answer as an `engine_facts` row with the date and run id:
- Which font file each text item opens, in each context (front end, campaign, battle): from the proxy log's file survey of `font\*.cuf` opens (J9 file survey) with and without the J66 fonts pack.
  Empire's answer was that Ingame 18 and Frontend 32 fail to load and that only the preload list loads; do not assume Napoleon is the same.
- Whether unit banners and flags (`lb_unit_id`, `nb_unit_id`, `battle_hud_flags`) and the campaign `city_info_bar` and `faction_hud_flags` are layouts whose text uses the same slots as the other layouts
  (then J66's 2x set already covers them, and the work is the proof) or use fonts or sizes of their own. Read the font names from the layouts with `uic.py`.
- The loading-screen quote font (Empire: one of `frontend_10` to `frontend_20`) and what Napoleon draws on the loading screen as text.
- Subtitles: which font, and what `fontsize` is (a preference, a script argument or a table field); whether any scenario in the library plays a movie with subtitles.
- Text that is drawn as art, not as `.cuf` text (for example `loading_screen_heading_txt.tga`, `quote_test.tga`): it belongs to the art roles (J36, J53), not to fonts. List it, do not fix it here.

## Decisions already made for this job
- **Bitmap fonts do not follow a runtime slider.** A `.cuf` is read at game start and cannot change with D5's slider. Engine-drawn text follows the **factor chosen at install** (J66's 2x now; J67 adds
  1.25x and 1.5x), through a fonts pack per factor; the slider (D19) is RmlUi's, through FreeType at the final size (D7). Say so in `uiscale/README.md`. No proxy font hook in this job.
- **One font face: Lora**, as J66 (its open question 1). If Liam overrules J66, follow the ruling. Every one of the 74 shipped `.cuf` is accounted for in the build manifest: rendered from Lora at the
  factor, or left vanilla with a reason. `editor_*` and `console_12` follow J66's decision for them; they are not UI text.
- **Extend J66's builder, do not fork it.** New code goes in J66's `uiscale/core` and `uiscale/napoleon` (shaped like `upscale/`), as new passes of its `wsc uiscale` verb (names are the builder's:
  for example `uiscale engine-text` for the inventory, `uiscale check-fonts` for the per-factor consistency check). If J66 put things elsewhere, follow where it put them. Pack names for any new pack go in
  `discovery/napoleon/games.json` `mod_packs` and `tests/test_mod_packs.py`.
- **The font name list is the exe's, and stays.** A slot the engine never loads is not worked around by editing the exe's list (an exe change, D2) or by a proxy patch (rule 79). The route is: put the
  glyphs a context needs into the slots it does load, as J66 does. A text item whose slot cannot be changed is left vanilla and listed in the report.
- **Text drawn from art (TGA) is out.** So are cursors, the radar and any RmlUi text.
- **Licences for J38.** Write `uiscale/napoleon/font_licences.json` (one row per font component: family, version, licence name and SPDX id, copyright line, reserved font name and what it means for the
  `.cuf` files, source URL, the pinned sha256 of the TTF used, the OFL text's sha256, date checked, `shipped`), with a host test and a `--check`, so J38's generator can read it. Read the licence from the TTF's name
  table and the upstream licence file, not from Empire's notes. The TTF is fetched by pin (URL and sha256, like `fetch_dxvk.py`), never committed unless the licence data says it ships; CA's vanilla fonts are
  never committed and never in a pack. State in the report that this is not legal advice, like J38's `LICENSES.txt`.
- **Shots are crops that can be compared by eye and by number.** Campaign camera pose cannot be set and the opening pan makes the default view non-deterministic (`napoleon.campaign.determinism`), so
  campaign label shots are compared by crop and by measured glyph height, never by a pixel diff. Battle poses are deterministic (`napoleon.battle.camera_route`): use the scenario rows' own pose ids.

## Deliverables
1. **Engine-text inventory:** `uiscale/napoleon/engine_text.json`, generated and checked: every engine-drawn text item (unit banner and flag text, campaign map labels, settlement info bars, faction flags,
   subtitles, loading-screen quote), the layout and component or exe site behind it, the font name and `.cuf` file it opens per context, and its state (`covered_by_j66`, `built_here`, `vanilla_left` with a reason,
   `art_not_text`). Re-runs give byte-identical output. Status of the four `engine.*` rows in `ui_elements` is not changed by this job (UI_PIPELINE statuses are set by tools at their gates); the inventory is linked from
   their descriptions only if the generator for them allows it, otherwise name it in the report.
2. **Font gaps closed:** the fonts packs per factor carry every slot an engine-drawn item uses, built by J66's pipeline (factor as a parameter; 2x proven on the PC, other factors built and host-tested only). A
   consistency check (like Empire's `check_install.py`) confirms every font name a scaled layout, a template or the inventory references resolves to a file in the pack for that factor. Builds are byte-identical on a re-run.
3. **Host tests:** inventory against synthetic layouts (a banner layout, a label layout), the slot-resolution check including a missing slot, per-factor pack manifest, the licence data (`--check` fails on a missing
   field and a changed sha256), and that no vanilla CA font ends up in a built pack. Tools rows (header format: `core/warscape/tools.py`), `uiscale/README.md` section "Engine text", `python3 core/wsc.py gates` green.
4. **PC (watcher, headless, lock owner `J37`)**, shots (JPG, about 3 MB in all) at **1920x1080 and 3840x2160** from fixed poses:
   - `land_small` poses `deploy` and `turned` (banners and flags at close and far range), `naval_small` pose `deploy`, `siege_small` pose `deploy`;
   - `campaign_start` default view (map labels and info bars), with the pan allowed to finish by the harness's own settle, not by repeated calls;
   - the front-end main menu once, only to show the layout text next to the engine text.
   Matrix: 1080p vanilla; 4K vanilla; 4K with the J66 2x set plus this job's additions. For each engine-text item a crop pair (vanilla 4K against 2x at 4K) and the measured text height in pixels. The
   loading-screen quote and subtitles are shot only if a route exists in the library; otherwise prove them by the file survey (which `.cuf` is opened) and mark them `static_only` with the reason.
   Load time against J66's. WER and the dumps folder checked after each launch.
5. **`engine_facts` rows** with the run id: `napoleon.fonts.engine_text_slots` (item to file, per context), `napoleon.fonts.banner_text`, `napoleon.fonts.loading_quote`, `napoleon.fonts.subtitles` (or the reason it
   cannot be shot), `napoleon.fonts.factor_follows_install` (what follows the install factor and what does not) and `napoleon.fonts.licence` (face, licence, date checked).
6. A dated run report under `uiscale/runs/`, and the final state: the game folder snapshot-identical to the start, no proxy, lock released.

## PC test
Headless through the watcher, lock owner `J37`. Check the virtual display and the profile give 1920x1080 and then 3840x2160 (J66 ran 4K; J53 ran 1080p). If the lock is held by another job, wait once through the
watcher's own queueing; if the PC is not free after that, commit what is done and report. Do not start a visible launch: Liam plays the result later. Order:
- a) snapshot the game folder, kit and send the proxy, install nothing else;
- b) vanilla shots at 1080p and 4K, with the file survey of font opens;
- c) `play.py install --scale 2` (J66's command, with this job's fonts), the same shots at 4K, the file survey again;
- d) everything out; the uninstall ends `identical`.

## Kill criteria
- J66 is not `done` (no report on `main`, or its fonts pack and install command do not exist): stop at once, commit nothing but a note in the report, and say so. This job's PC part cannot start without them.
- The same crash twice in a row with the fonts pack that is not the known init heap corruption (`napoleon.proxy.init_heap_corruption`): read WER and the dump first, bisect (J66 packs alone, then the added
  slots) only if that takes under about 10 calls, and report which one. Do not hand Liam an install that crashes.
- An engine-drawn text item cannot be made crisp or sized by font data alone and needs a proxy hook, an exe patch or a core change: stop, list the item in the report as `vanilla_left` with the evidence, and
  ask Liam; do not start a proxy change here.
- The uninstall does not end `identical` after one honest repair: stop, report the diff, and do not hand over any install command.
- Over about 140 tool calls, or the PC part past about 50 of them: stop, commit, report what is left.

## Open questions
1. **Dependency on J66.** The row said `depends_on` J10 only, but `jobs next` takes the lowest-numbered ready job, so J37 would start before J66's fonts exist. This brief's row adds J66 (`depends_on` J10 and J66).
   Liam can remove it if he wants the inventory and licence record done first (those two deliverables need no PC and no J66 packs, and could be split out as a smaller job).
2. **Face.** Lora again (proven on Empire, OFL, Liam liked it there), or Napoleon's own look (D8) with a different face for engine text? RmlUi text will use whatever J33 picks, so engine text and RmlUi text may
   end up in different faces. Recommended: Lora now, revisit after J33 chooses the design language.
3. **Slider.** Engine text follows the install factor (a fixed 2x, 1.25x or 1.5x), not D5's slider. Players who move the slider will see RmlUi screens change and engine labels stay. Is that acceptable until the
   engine-text screens are rebuilt, or should a later job add a proxy hook that swaps the font pack by `ui.scale` at launch (an exe-adjacent change under rule 79)?
4. **Campaign labels.** The campaign camera cannot be posed (`napoleon.campaign.camera_route`, open), so campaign label shots are crop comparisons at the default view, not repeatable poses. A job that solves the
   campaign camera would make them deterministic; this brief does not wait for it.
5. **Subtitles and loading screens** may have no route in the scenario library to shoot. Recommended: prove them by the file survey now and capture them in the one Liam-present sitting before release (D38's
   visible-window sitting), not here.

## Finish
Write `jobs/J37/report.md`:
- what was built, and the tools and commands;
- the inventory table (item, file, state);
- the PC evidence (job ids, run folder, shots, load times, snapshots);
- what engine text is crisp at 4K and what stays vanilla (the list for Liam and J67);
- the fonts and licences record for J38;
- deviations from this brief and why;
- open questions.

Then `wsc reg set jobs J37 status=review report=jobs/J37/report.md`.
