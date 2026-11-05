# UI scale stop-gap (J66, J67, D40)

This scales the vanilla UI's data, and the pixel constants of its Lua scripts, by a fixed factor, so that the UI is playable at 4K and 1440p
before the RmlUi screens exist. It is ported from empire-remastered `ui_scale_mod` (read-only evidence). Factors: **2.0** (3840x2160 = 2 x 1080),
**1.25** and **1.5** (2560x1440); one is installed at a time. 1080p stays vanilla.

## Build and install
```
python3 core/wsc.py uiscale build --factor 2|1.5|1.25 [--no-art] [--no-fonts] [--no-lua]   # in the art_build Python; nothing touches the game folder
python3 core/wsc.py uiscale check --factor 1.5 --height 1440                                 # a factor against a screen (standard Python)
python3 core/wsc.py uiscale lua-consts [--check]                                             # regenerate (or compare) lua_consts.json and lua_patches.txt
python3 core/wsc.py uiscale lua-patches --check                                              # every patch assert against the installed game's scripts
python3 upscale/pc/play.py install --scale 2|1.5|1.25  |  status  |  uninstall               # Liam's play install (upscale/README.md "Play test")
```
`--scripts DIR` points lua-consts, lua-patches and check at an extract folder (`extract/napoleon`) instead of the game.

The build writes these files to `<state folder>\uiscale\work\` (`tools/pc_state.py`: the adapter's `state_dir`, `C:\napoleon_remastered_pc`, or `$NAPOLEON_STATE_DIR`), each with a `.json` (entries, sha256, held back, method), `<tag>` = `125`, `15` or `2`:
- `ui_scale_<tag>x.pack` (movie): every vanilla layout (174), the patched UI scripts (J67, at each script's own pack entry) and the UI art.
- `ui_scale_<tag>x_fonts.pack` (movie): the slot fonts, rendered at the size `napoleon/font_slots.json` gives for the factor.
- `uied.templates.ui_scale_<tag>x` and `ui_scale_<tag>x.rules` (the `dev.file_rules` redirect of the loose templates; fact `napoleon.ui.templates_route`).

A re-run is byte-identical: the art is cached by input sha256, and the pack is kept when its plan is unchanged.

## Factors (for J38)
| Resolution | Factor | Packs | Status |
|---|---|---|---|
| 1920x1080 | none | vanilla | - |
| 3840x2160 | 2.0 | `ui_scale_2x.pack` (1810 MB), `ui_scale_2x_fonts.pack` (4.9 MB), templates (39 MB), rules | proven in game, Lua included (run 2026-11-05_j67pc) |
| 2560x1440 | 1.5 | `ui_scale_15x.pack` (1025 MB), `ui_scale_15x_fonts.pack` (4.2 MB), templates (22 MB), rules | seen in game; battle and campaign on the harness build only (below) |
| 2560x1440, not the default | 1.25 | `ui_scale_125x.pack` (717 MB), `ui_scale_125x_fonts.pack` (4.0 MB), templates (16 MB), rules | seen in game on the same terms; black bars on the front end |

The installer picks one factor by resolution (`napoleon/config.json` `resolution_factor`). 1440p takes 1.5 (fact `napoleon.ui.scale_factor_1440p`): `uiscale check --factor 1.5 --height 1440` finds no
layout that loses content against 1080p (six front-end pages bleed 1 vanilla px), and its shots read better than 1.25. Whether all three ship or are built on the player's machine is J38's call.

**Harness builds at 1.25x and 1.5x:** with the patched scripts in those packs the dev wrapper of the main menu does not run, so the bridge never pumps (fact `napoleon.ui.dev_wrapper_lost_at_fractional`, cause unknown; a play install
has no wrappers). `wsc uiscale build --factor F --no-wrapped --work <scratch>` leaves out the wrapped scripts for a harness run, and `play.py install --scale F --uiscale-work <scratch>` takes it. Never ship that build.

## Code
- `core/scale.py`: the layout and template rules (multiscale.md section 4 of the Empire branch), and Empire's long-form pass (J79): only a TextView's `Text` child keeps the spaced `Frontend 24` slot, every other user of it takes `Ingame 24`.
  - **Date cells (J67):** a list row's `save_date` or `date` cell on a Frontend slot takes a 200 vanilla px wrap width and moves 10 vanilla px left (the slot is wider than a true factor): `date_cell_pass`.
  - **Geometry:** absolute edge snapping `px(x) = floor(x + 0.5)` on edges relative to the root. It covers component x/y, state w/h, image-use rects, V039 keyframe x/y/w/h, and textured image defs (`ceil(t * f)`).
  - **Left alone:** the image-use tail (9-slice stretch flags) and blank image defs.
  - **Fonts:** onto the slot files each context loads (Empire: `Ingame 24` Normal/Bold, `Frontend 24`, `Frontend 38`; the front end takes the nearest vanilla-named size), chosen as at 2x at every factor.
  - **Templates:** each embedded TGA is scaled with its image defs (nearest neighbour at 2x). The pre-v27 text records in `UPGRADE_TO_33` are rewritten as v33. `Cursor`, `slider`, `InputWindow` and `BattleEditor` pass through unchanged.
- `core/lua_consts.py` (J67): the classifier. A symbolic walk of all 497 scripts (registers, upvalues, globals, string-keyed fields, calls into and returns out of Lua functions, branches joined, loop bodies twice) lists every numeric constant that reaches a pixel-taking call (`MoveTo`, `Resize`, `CreateComponentFromTemplate` x/y, `SetStateTextXOffset`, `CallByAddress` of those) or a calculation with a pixel value (`Width`, `Height`, `Bounds`, `Position`, `Dimensions`, `ScreenSize`, ...). Rules: an offset, size, pitch or threshold scales; a ratio, zero, one, a fraction or a sentinel is left. `napoleon/lua_overrides.json` corrects a rule with a reason.
- `core/lua_patch.py` (J67): the patch applier and list writer (Empire's `apply_patches.py` syntax; every number in vanilla pixels, written as `px(v * factor)`; every item asserts the vanilla constant or instruction; factor 1.0 changes nothing).
- `core/check.py` (J67): a factor against a screen (Empire's `multiscale_check.py` idea): each layout's scaled extent against the screen and against vanilla 1080p, abutting pairs, the scaled layouts' fonts against the slot table.
- `core/art.py`: the J36 2.5x masters resampled to the factor. RGB is Lanczos in linear light, after dilation under alpha 0; alpha keeps its kind. With no master, Lanczos from vanilla.
- `core/cuf_encode.py`: Lora re-render of a vanilla `.cuf` (freetype-py 2.5.1, HarfBuzz pair kerning (D42; required since J79, no GPOS fallback; golden shas in `napoleon/font_golden.json`), the vanilla header kept, so line pitch = h2 + 2). Empire's recipe; J67 adds the per-slot render scale of `font_slots.json` (1.0 at 2x: J66's pack unchanged).
- `napoleon/cli.py`, `napoleon/config.json`: paths, factors, the art roles, the never-scaled helpers and the font face.
- `napoleon/lua_consts.json`, `napoleon/lua_patches.txt` (generated), `napoleon/lua_overrides.json` (hand classes), `napoleon/lua_empire_items.json` (Empire's items, a snapshot for the cross-check), `napoleon/font_slots.json` (J37 adds its `engine_text` key beside `layouts`).
- Tests: `tests/test_uiscale.py` (scaler), `tests/test_uiscale_lua.py` (applier, classifier, tables, the list against the game's scripts), `tests/test_uiscale_fonts.py` (encoder), `tests/test_play.py` (install `--scale`), `tests/test_mod_packs.py`.

## Engine text (J37)
Text the engine draws without a layout's font choice, from `.cuf` files it opens by itself. The static RE is run `uiscale/runs/2026-11-03_j37_static` (no PC yet).
- **The install factor decides it, not the slider.** A `.cuf` is read once at game start, so engine text follows the factor of the installed fonts pack (2x now; J67's 1.25x and 1.5x
  get their own pack). D5's slider (D19) moves RmlUi text only, through FreeType at the final size (D7). Players who move the slider see RmlUi screens change and engine text stay.
- **How the exe picks a file** (`font_slots.json` `engine`): a layout font name must be one of 19 listed names, or it draws as `Ingame 12, Normal`. Every list name and every fixed size goes
  through `GetFont(family, size, bold)`, which rounds the size down to even and clamps it to 6..32: **`Frontend 38` opens `frontend_32.cuf`**.
- **What is built** (`font_slots.json` `engine_text`, built by `wsc uiscale build` into the same `ui_scale_<f>x_fonts.pack`):
  - `frontend_22.cuf` at the factor: the two fixed `GetFont("Frontend", 22)` callers, a UI text style and the `ribbon.fx` text;
  - `frontend_10.cuf` .. `frontend_20.cuf` at the factor: the loading-screen quote, which keeps the largest file that fits its box;
  - `frontend_32.cuf`: the same bytes as the `Frontend 38` slot render (the clamp target).

  A file that a scaled layout already uses as a slot at that factor is skipped, with the reason (`cuf_encode.render_scaled`, `fontcheck.plan_engine`).
- **Inventory:** `uiscale/napoleon/engine_text.json`, generated by `python3 core/wsc.py uiscale engine-text` (`--check` in the tests). Each item has its state:
  - battle banners and flags: `art_not_text` (no text state);
  - `city_info_bar`: `covered_by_j66` (`Ingame 12` -> `Ingame 24`);
  - the engine files above: `built_here`;
  - developer text: `vanilla_left`;
  - subtitles and credits: `open`.
- **Slot check:** `python3 core/wsc.py uiscale check-fonts [--factor F]` reads the built fonts pack's manifest. It refuses:
  - an unlisted name;
  - a resolved file missing from the pack;
  - an alias whose bytes differ from its slot;
  - a pack file byte-identical to a vanilla CA font.

  It notes files nothing opens.
- **Licences:** `uiscale/napoleon/font_licences.json` (for J38), checked by `python3 core/wsc.py uiscale licences --check`. It holds the face's own name-table facts, the pinned sha256 of the TTF and of `OFL.txt`, and what the Reserved Font Name means for the `.cuf` files. It is not legal advice.

## Lua pixel constants (J67, proven in run 2026-11-05_j67pc)
`lua_consts.json`: 1014 uses in 145 of the 497 scripts reach a pixel: 258 `scale`, 756 `leave` (each with its reason), no `manual` and none unclassified.
`lua_patches.txt`: 204 items in 69 scripts. Of Empire's 109 items, every one whose script and value exist in Napoleon is `scale` here, except the ones
listed under "Not ported" below. Causes found:
- **Battle radar group** (`battle.hud.radar`, `battle.minimised_hud.radar`): `ui/huds.luac` `RegisterHud` clamps the HUD width to 1280 (`if h_width > 1280 then h_width = 1280`),
  and `MoveRelativeToHUD` places a right-docked part at `h_width - width`. At 2x the HUD is 2560 wide, so the radar sat 1280 px left of its place. Patched: the 1280 scales.
- **Campaign minimap content** (`campaign.hud.radar`, `template.map_image`): the map draws at texture pixels x zoom x 2, and the theatre-map textures stay 1x; the x 2 and
  the two `FindRegion` multiplies (hover and click) scale together.
- **Generic tooltip** (`template.tooltip`): the 200x200 pre-size and the 16 px padding scale (vanilla wrap and padding at every factor).
- Patched scripts the dev wrappers also wrap (`proxy/napoleon/lua/wrappers.txt`): `ui/battle_ui/root.luac` and `ui/frontend_ui/main.advert.luac`. At 2x `wsp.vanilla` runs the patched copy (`napoleon.ui.lua_pack_route`).

## Held back or left (what is still 1x or unchecked)
- **Seen on the front end only:** the shipping 1.25x and 1.5x packs with all 69 scripts; their battle root patch has not run in a battle (harness builds above).
- **Unreached headless:** pre-battle, reinforcements, battle results, the minimised HUD, the options tabs' content, the recruitment tab; the screen table is in `runs/2026-11-05_j67pc/README.md`.
- **Front-end page titles:** about half their vanilla share of the screen at 2x. `Frontend 38` is the largest slot and `GetFont` clamps at 32, so a larger title needs a new slot plan (J37's side).
- **Slot quantisation:** text drawn at a size between two slots looks a little small or large, as the first four Player Stats rows do.
- **Unseen headless:** tooltips and map hover (no hover verb); they are checked statically. Liam's first play session: hover a settlement, a unit card, a building and a technology.
- **Not ported from Empire (design changes, not scale fixes):** the wider tooltip wraps (900 at 2x) and equal right insets, and the map tooltip's right padding (inserted instructions).
  Vanilla has the same insets at 1080p. Empire's government one-letter fix and its religion-icon offset have no counterpart in Napoleon's script.
- **Theatre-map art:** the minimap and the diplomacy and objectives maps draw at the scaled size from the 1x textures (Empire made 4x art; a later job).
- **Loading screen and cursor** (`engine.loading_screen`, `engine.cursors`): after the J67 cut line. Empire's recipe for the progress bar is data only (2x trough and end-cap, the 1-px fill strip kept 1 px wide); the cursor has no known data route.
- **Engine-drawn text:** J37 (section above). `ui/labels.luac` is left vanilla here for that reason (`lua_overrides.json` `exclude_scripts`).
- **Font face (D42):** vendored at `uiscale/fonts/Lora-Variable.ttf` (J68; SIL OFL text beside it). The same file in the empire-remastered clone is only a fallback (`config.json` `font_faces`).
