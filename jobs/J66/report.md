# J66 report: UI scale stop-gap: vanilla UI at 2x for 4K

One build command and one install command now put the whole vanilla UI at 2x on Napoleon at 3840x2160:
- every vanilla layout, with edge snapping and the V039 keyframes;
- `uied.templates`, through a proxy file rule (a config key, so no DLL change and no rule-79 run);
- Lora slot fonts;
- 9365 UI textures resampled from the J36 masters.

One uninstall command leaves the game folder snapshot-identical. A headless 4K run showed the front end, the campaign HUD and the battle HUD at 2x, docked as at 1080p. Load times were unchanged (3.8 s, against J53's 3.9 s), with no crash, dump or WER report. What stays 1x or is misplaced (the battle radar group, engine-drawn text, the loading screen) is listed for J67.

## What was built
- **`uiscale/core/scale.py`:** the scaler, game-agnostic and ported from empire-remastered `ui_scale_mod` (main plus `origin/ui/multiscale`).
  - **Geometry:** absolute edge snapping `floor(x + 0.5)` on root-relative edges. It covers component x/y, state w/h, image-use rects, V039 keyframe x/y/w/h, and textured image defs (`ceil(t*f)`).
  - **Left alone:** the stretch flags (image-use tail) and blank image defs.
  - **Fonts:** onto per-context slots (Empire's proven set).
  - **Templates:** the `uied.templates` container is rebuilt. Each embedded TGA is scaled with its image defs (nearest neighbour). The 7 pre-v27 text records are upgraded to v33, and `Cursor`, `slider`, `InputWindow` and `BattleEditor` pass through. It extends J6/J10's `uic.py` and `tpl.py`; neither is copied.
- **`uiscale/core/art.py`:** the J36 2.5x masters resampled to exactly 2x with the upscaler's code (`resample.py`, `dds.py`, `imageio.py`). RGB is Lanczos in linear light after dilation, alpha keeps its kind, and the output keeps the vanilla container (DDS with mips). With no master, it falls back to Lanczos from vanilla (not needed: every referenced texture had a master).
- **`uiscale/core/cuf_encode.py`** (subagent): a Lora re-render of `.cuf` fonts with Empire's recipe (freetype-py 2.5.1, FreeType 2.13.2, header kept so line pitch = h2 + 2, `frontend_24` spaced). Kerning comes from a built-in GPOS reader instead of HarfBuzz (see deviations).
- **`uiscale/napoleon/cli.py` + `config.json`, verb `wsc uiscale build|status`** (`tools/verbs/uiscale.py`): writes `ui_scale_2x.pack`, `ui_scale_2x_fonts.pack`, `uied.templates.ui_scale_2x` and `ui_scale_2x.rules` into `C:\napoleon_remastered_pc\uiscale\work\`, each with a `.json`. The art is cached by input sha256, and builds are byte-identical (checked across two work folders: 60 art files and the templates file).
- **`upscale/pc/play.py install --scale 2`:**
  - installs the kit and the two scale packs;
  - sets `dev.file_rules` to the rules file;
  - moves any UI-cache files (`%APPDATA%\...\Napoleon\ui_cache`) to the play trash at install and at uninstall, recorded in `play.json`;
  - `status` checks the templates sha;
  - `uninstall` is unchanged and ends `identical`.
- **`discovery/napoleon/games.json`:** `mod_packs` gains `ui_scale_2x.pack` and `ui_scale_2x_fonts.pack`, with a test in `tests/test_mod_packs.py`.
- **Host tests:** `tests/test_uiscale.py`:
  - synthetic layouts V028-V039 with keyframes;
  - abutting pairs at 1.25, 1.5 and 2, where per-value rounding overlaps;
  - stretch flags untouched;
  - template TGA/def pairing and byte-exact pass-through;
  - font slots;
  - every vanilla layout and the templates file round-trip after scaling (skipped without the game).

  Also `tests/test_uiscale_fonts.py` (skips without freetype-py or the face), and `tests/test_play.py` with `--scale 2` install, uninstall `identical`, UI cache moved, and the refusals.
- **Docs and registries:** `uiscale/README.md`, the `upscale/README.md` Play test section, tools rows, D41 (the freetype-py dependency), and four `engine_facts` rows.

## Evidence
Run report: `uiscale/runs/2026-11-02_j66/README.md` (shots in `raw/`).
- **Build:**
  - `ui_scale_2x.pack`: `bd351fa39ae9`, 9539 entries, 1.81 GB;
  - fonts: `f699ca5db25b` in the run (GPOS kerning); rebuilt with HarfBuzz after D42 as `5f510b27afa3`;
  - templates: `4797e415b6ea`.
- **PC, lock `J66`, 16:38-16:55 UTC:**
  - start snapshot identical to the last known one (`post_uninstall_20261102T161306Z`);
  - kit `kit_20261102T154016Z_23dbc9e2d143` (build 715e9dfc0727 = this branch's DLL inputs);
  - packs in: job `J66-20261102T163918Z-106224043`;
  - `campaign_start` loaded in 3.0 s;
  - `land_small` loaded in 3.8 s (launch `20261102T164658Z-p36980`);
  - redirect hit in proxy.log;
  - 96540 entries indexed;
  - packs out: job `J66-20261102T165343Z-1342610164`;
  - `pc_deploy uninstall` identical; end snapshot **identical** to the start; no proxy left; lock released.
- **Health:** no dump, no new WER report, and `ui_cache` stayed empty.
- **Facts:** `napoleon.ui.templates_route`, `napoleon.ui.canvas_docks_scaled`, `napoleon.ui.font_slots_2x`, `napoleon.ui.scale_2x_packs`.
- **Gates:** `python3 core/wsc.py gates` (see the commit). Host tests `tests.test_uiscale`, `test_play` and `test_mod_packs` pass locally; `test_uiscale_fonts` passes in the art_build Python.

## For Liam: what you will see, and the commands
From the repo checkout in Git Bash, with the game closed and no agent holding the lock:
```
python3 core/wsc.py uiscale build          # already built on this PC; re-running is a no-op
python3 upscale/pc/play.py install --scale 2
# set 3840x2160 in the game's own options if it is not already, then play from Steam
python3 upscale/pc/play.py status
python3 upscale/pc/play.py uninstall       # must end "identical"
```
**At 4K, at 2x:**
- the main menu and its pages;
- the campaign HUD (bottom bar, minimap frame, buttons) and the advisor;
- the battle HUD: unit cards with legible counts, orders buttons, the time controls;
- template-built pieces through the scaled `uied.templates`;
- the text, drawn in Lora at the slot sizes.

**Still 1x or wrong (J67):**
- the battle radar and Start Battle box sit about 1290 px left of the top-right corner;
- the front-end "New content" box is clipped;
- Lua pixel constants: grids, tooltip sizes, map hover;
- the tooltip 200x200 pre-size;
- the loading screen and the cursor;
- engine-drawn text: map and unit labels, the version string, the loading quote.

**Not seen in game:** tooltips, the settlement panel and the campaign unit-card row. Look at those first.

## Deviations from the brief and why
- **Template route.** No DLL change was needed. Route 2 is the proxy's existing `dev.file_rules` (a config key that redirects both the attribute check and the open), so rule 79 does not apply. Route 1 was launched once (a pack entry at `ui\templates\uied.templates`, no redirect). Its shot matched route 2's, but no template-built element was on screen, so route 1 is undecided. Route 2 ships because the log proves it is read.
- **Font probe.** I did not probe which sizes each context loads by swapping candidates. The scaler keeps to Empire's proven slots. The shots show no tiny fallback in the front end, campaign or battle.
- **Lora face (D42: vendor it).** The copy from empire-remastered is refused by the project deny rule `Edit(~/repos/empire-remastered/**)`, which matches the copy's source path. I did not edit the settings. `config.json` `font_faces` takes `uiscale/fonts/Lora-Variable.ttf` first and falls back to the same file in the empire-remastered clone, so the build works either way. The OFL text is in `uiscale/fonts/OFL.txt`.
- **HarfBuzz (D42: yes).** The first session's `uharfbuzz` install was refused; after Liam's answer it is installed (0.56.4) and drives the pair kerning. With it, `ingame_24` and `frontend_38` are byte-identical to Empire's in-game-proven 2x fonts (glyphs, header and all 122,500 pair entries). The GPOS reader stays as the fallback when uharfbuzz is missing. The fonts pack is now `5f510b27afa3`; it was not launched again, because only the pair steps changed (by ±1 px).
- **Shots are not full size.** They are 1280 px wide: `shot.sh` caps committed evidence at that width. The game ran at 3840x2160 (adapter `ctl.launch.size`).
- **Campaign shots are limited.** Settlement panel, unit-card row and tooltip were not shot: there is no click or hover verb (`ctl.py` rule 78), and the warm reset from the campaign stalls (the known `napoleon.campaign.quit_to_menu`).
- **Art scope.** All J36 roles except `loading_screen` and `cursor` are in the pack (1.8 GB). Including the cards, portraits and flags keeps them sharp in the 2x slots.

## Open questions
Questions 1-4 are settled by Liam (D42): vendor the face, use uharfbuzz, keep Lora, ship in 0.1.0.
1. **Vendored face:** backlog row J68 (PR #129, needs_brief). Until it lands, the build reads the same file from the empire-remastered clone.
2. **Radar group.** Its position is not data-driven at 2x. J67 should find the Lua constant or engine docking behind it.
