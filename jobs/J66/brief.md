# J66: UI scale stop-gap: vanilla UI at 2x for 4K

Phase 5, D40. Liam plays at 3840x2160, and the vanilla UI is drawn at its 1080p pixel size, so it is too small to play ("We need the stop-gap port ASAP - like now", 2026-11-02).
J53's play packs replace the art but draw it in the vanilla rect (`napoleon.ui_art.hires_same_rect`). Empire's remaster solved this before RmlUi by scaling the vanilla
UI's data: the layouts, `uied.templates`, fonts and art, rebuilt at a fixed factor and installed as packs. Target: Liam runs one install command, plays Napoleon at 4K with the front end,
campaign HUD and battle HUD at 2x, and one uninstall command leaves the game folder snapshot-identical. Speed matters more than coverage here: J67 takes the Lua constants,
1440p and the screens this job leaves.

Model: Opus, reason: binary layout and template formats (V039 animation records), the engine's font-slot and file-route behaviour probed in game, and possibly a proxy
file rule under rule 79 (D15). Budget about 250 tool calls; at the cap, stop, commit, report what is left. At most 2 subagents, for independent work only (for example the font
build while you port the layout scaler). Waiting belongs to the harness: `job.sh` and `ctl.py` block inside one call; never poll.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J66`; the watcher is the only launcher; D2: exe vanilla on disk; never git in a game folder; `empire-remastered` is read-only evidence).
- **Empire evidence** (`C:\Users\liamr\repos\empire-remastered`, read only):
  - On main: `ui_scale_mod/README.md` (pipeline, backlog, the problems at lines 57-80), `ui_scale_mod/FORMAT.md` (layout fields), and the tools
    `scale.py`, `uic.py`, `scale_templates.py`, `tpl.py`, `build_all.py`, `cuf.py`, `cuf_encode.py`, `build_lora_set.py`, `build_fonts.py`, `upscale_textures.py`, `build_art_pack.py`, `check_install.py`.
  - On branch `origin/ui/multiscale` (6da83af; read with `git -C ../empire-remastered show origin/ui/multiscale:<path>`): `ui_scale_mod/docs/multiscale.md`
    (sections 3.2 and 10-11) and `multiscale_check.py`.
  - In `docs/learnings/LEARNINGS_ENGINE.md`: the `uied.templates` open lines (around line 136) and the multiscale lines (around line 391).
- **Napoleon facts:** `napoleon.diff.layouts.versions`, `napoleon.diff.layouts.v039`, `napoleon.diff.layouts.template_records`, `napoleon.diff.fonts.cuf`,
  `napoleon.ui.layout_base`, `napoleon.ui.uied_templates_runtime`, `napoleon.files.loose_override`, `napoleon.files.loose_probe_dirs`, `napoleon.ui_art.*`.
- **Already ported** (`discovery/core/`, J6 and J10): `uic.py` (with V039), `tpl.py`, `cuf.py`, `luachunk.py`. Extend them; do not copy Empire's codecs again.
- **Also read:** J53's `upscale/pc/play.py`, `upscale/core/pack.py` and `upscale/README.md` "Play test" (install, held-back rules, mod_packs), and `jobs/J10/report.md` (the UI atlas: screens and their layouts).
- **Search first:** `python3 core/wsc.py find layout template font scale uic cuf`.

## Decisions already made for this job
- **One factor, 2.0.** 4K is height 2160 = 2 x 1080 (D19's ratio at slider 100 %). No slider, no 1.25x or 1.5x (J67). Pack names `ui_scale_2x*.pack` in `discovery/napoleon/games.json`
  `mod_packs` (extend `tests/test_mod_packs.py`). New code goes in `uiscale/core/` (game-agnostic) and `uiscale/napoleon/` (paths, overrides, skip lists), shaped like `upscale/`, with a `wsc uiscale` verb.
  Nothing in `core/` changes.
- **Layouts:** scale every vanilla layout by Empire's rules:
  - component x/y, state w/h, image-use x/y/w/h, image-def w/h for textured images, and the font name to a slot file;
  - absolute edge snapping `floor(x + 0.5)`, never per-value rounding (that opened about 1,000 one-pixel gaps on Empire);
  - never touch the 9-slice stretch flags;
  - **V039 keyframe geometry (x, y, w, h)** too.
  Check the 1280x960 base canvas (`napoleon.ui.layout_base`): if the engine docks it, decide from a shot whether the canvas scales or stays. Every scaled file must round-trip
  through `uic.py`, and a host test pins edge-snapping on abutting pairs.
- **Templates:** scale `uied.templates` with `tpl.py`. Each embedded TGA is scaled with its image def, never apart (a def changed alone crashed Empire's campaign). Leave `Cursor`,
  `InputWindow`, `BattleEditor` and `slider` vanilla as Empire did, unless a shot says otherwise. Pre-v27 records that carry text store a numeric font id: Empire rewrote them as v33
  (`UPGRADE_TO_33`); check this against Napoleon's v35/v39 records before relying on it.
- **Template file route: probe first, cheapest first, and record a fact.**
  1. A movie pack entry at `ui\templates\uied.templates`. It crashed Empire at Empire.exe+0xb76ca3; it is unproven on Napoleon. One launch.
  2. Otherwise a redirect rule in the proxy adapter (the J3 file rules: `rules line` entries like the fixed sky). Napoleon opens the file attribute-only first (Empire: access 0x80), and
     that open must be redirected too. This changes `proxy/`, so **rule 79 applies: 20 acceptance passes** on the final build.
  3. A loose `data\` copy needs a new core kit role (`napoleon.files.loose_override`, J9). That is a warscape-core PR: stop and ask Liam before taking it.
- **Fonts:** Napoleon's 73 shared `.cuf` files are byte-identical to Empire's and `editor_13.cuf` is new (`napoleon.diff.fonts.cuf`).
  - Re-render the fonts the 2x layouts name with Empire's recipe: Lora, freetype-py 2.5.1 (FreeType 2.13.2), line pitch h2 + 2.
  - Probe which font files each context loads (Empire: Ingame 18 and Frontend 32 fail; the 2x build used the slots `ingame_24`, `ingame_b_24`, `frontend_38`, `frontend_24`).
  - Fonts and their build need Pillow and freetype-py: build in the art_build Python (`C:\napoleon_remastered_pc\upscale\art_build`). A dependency added there needs a dated DECISIONS row.
- **Art at 2x, from the J36 masters:**
  - Resample `<work>\out` (2.5x) to exactly 2x the vanilla size with the upscaler's resample code (`upscale/core/resample.py`: linear-light RGB, plain alpha, mips for DDS), and keep the vanilla format.
  - Real 2x textures are required: the engine tiles frame pieces at the texture's real size (Empire: doubled frame lines at 2.5x).
  - The J53 held-back rules apply (DXT not a multiple of 4, over 4096 px).
  - Assets with no J36 output (skipped or not UI art) are Lanczos 2x from vanilla, stated in the pack's `.pack.json`.
- **Install:** extend `upscale/pc/play.py` with `install --scale 2`. It installs the scale packs (and the template route chosen above) after the kit, records them in `play.json`, and the existing
  `uninstall` takes them out and must end `identical`. Clear the engine's UI cache if Napoleon has one (Empire: `components.empire_ui_cache`, stale caches gave false bugs): find
  it, and make the install and uninstall move it to `_to_delete` (it lives under AppData, never in the game folder; record it in `play.json`).
- **Hold back, do not guess:** an element that cannot be scaled by data is left at 1x and listed in the report for J67. Empire's list is the starting point:
  - Lua pixel constants: grids, tooltips, map hover;
  - the loading screen;
  - the tooltip 200x200 pre-size;
  - engine-drawn text (map and battle labels, the loading quote);
  - the cursor.

## Deliverables
1. `uiscale/` (core and napoleon), `wsc uiscale build --factor 2` writing `ui_scale_2x.pack` (layouts, art), `ui_scale_2x_fonts.pack` and the templates file into
   `C:\napoleon_remastered_pc\uiscale\work\`, each with a `.pack.json` (entries, sha256, held back, method). Builds are byte-identical on a re-run.
2. Host tests: the scaler on synthetic layouts of each version incl. V039 keyframes, edge snapping, stretch flags untouched, template image-def/TGA pairing, every vanilla layout
   round-trips after scaling, the font slot mapping, and the play install with `--scale 2` against J53's fake game folder (install, uninstall `identical`).
3. Tools rows (header format: `core/warscape/tools.py`), `uiscale/README.md`, the `upscale/README.md` "Play test" section extended, `mod_packs`, `python3 core/wsc.py gates` green.
4. **PC (watcher, headless 3840x2160, lock owner `J66`):** the template-route probe, then the full 2x set. Shots at 3840x2160 (JPG, about 3 MB in all) of:
   - the main menu and its first sub-screens;
   - `campaign_start`: the HUD, a settlement panel, a unit's card row and a tooltip;
   - `land_small`: the battle HUD, unit cards and the radar.
   Load time against J53's 3.9 s. WER and dumps after each launch.
5. `engine_facts` rows with the run id: the template route, the font slots loaded per context, whether the canvas docks, and `napoleon.ui.scale_2x_packs` (what draws at 2x, what stays 1x).
6. A dated run report under `uiscale/runs/`, and the final state: the game folder snapshot-identical to the start, no proxy, lock released.

## PC test
Headless through the watcher, lock owner `J66`, at **3840x2160** (check the virtual display and the profile give that size; J53 ran at 1920x1080). If the lock is held by another job,
wait once through the watcher's own queueing; if the PC is not free after that, commit what is done and report. Liam's visible play launch comes after this job: do not start a visible
launch. Order:
- a) snapshot the game folder and compare it with the last known one, kit and send the proxy;
- b) the route probe and the 2x set;
- c) everything out, `identical`.

## Kill criteria
- The same crash twice in a row with the scale packs that is not the known init heap corruption (`napoleon.proxy.init_heap_corruption`): read WER and the dump first. Bisect by
  pack (layouts, fonts, art, templates) only if that takes under about 15 calls; report which one. Do not hand Liam an install that crashes.
- The template route needs a core change (route 3) or engine memory work: stop and ask Liam. Ship the layouts, fonts and art without scaled templates only if the shots show the
  screens usable, and say so.
- The uninstall does not end `identical` after one honest repair: stop, report the diff, and do not hand Liam the install command.
- Over about 250 tool calls, or the PC part past about 80 of them: stop, commit, report what is left.

## Open questions
1. **Fonts:** keep Empire's Lora re-render, or scale Napoleon's own font art? The brief says Lora: it is the proven route and the CUF files are the same. Liam can overrule in the review.
2. **Release:** this is a play-test install, not the shipped mod (J38 packages). Whether the stop-gap ships in 0.1.0 is Liam's call once he has played it.

## Finish
Write `jobs/J66/report.md`:
- what was built;
- the PC evidence (job ids, run folder, shots, load times, snapshots);
- what Liam will see at 4K and what stays 1x (the J67 list);
- the exact install, uninstall and status commands;
- deviations from this brief and why;
- open questions.

Then `wsc reg set jobs J66 status=review report=jobs/J66/report.md`.
