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

The build writes these files to `C:\napoleon_remastered_pc\uiscale\work\`, each with a `.json` (entries, sha256, held back, method), `<tag>` = `125`, `15` or `2`:
- `ui_scale_<tag>x.pack` (movie): every vanilla layout (174), the patched UI scripts (J67, at each script's own pack entry) and the UI art.
- `ui_scale_<tag>x_fonts.pack` (movie): the slot fonts, rendered at the size `napoleon/font_slots.json` gives for the factor.
- `uied.templates.ui_scale_<tag>x` and `ui_scale_<tag>x.rules` (the `dev.file_rules` redirect of the loose templates; fact `napoleon.ui.templates_route`).

A re-run is byte-identical: the art is cached by input sha256, and the pack is kept when its plan is unchanged.

## Factors (for J38)
| Resolution | Factor | Packs | Status |
|---|---|---|---|
| 1920x1080 | none | vanilla | - |
| 3840x2160 | 2.0 | `ui_scale_2x.pack` (about 1.8 GB), `ui_scale_2x_fonts.pack`, templates, rules | proven in game for layouts, art, fonts (run 2026-11-02_j66); the Lua is J67's PC slot |
| 2560x1440 | 1.25 (default until the shots) or 1.5 | `ui_scale_125x.pack` (about 0.8 GB estimated), `ui_scale_15x.pack` (about 1.1 GB estimated), their fonts packs | built and host-tested only: unproven in game until J67's PC slot |

The installer picks one factor by resolution (`napoleon/config.json` `resolution_factor`). 1440p: `uiscale check --factor 1.5 --height 1440` finds no
layout that loses content against 1080p; six front-end pages (credits, load_replay, mp_load_game, player_stats, sp_episodic_campaign, sp_load_game)
draw their 1280x961 background 1 vanilla px past the 960-tall root, a bleed. So the check allows 1.5; by the J67 rule the 1440p shots decide, and until
then the default is 1.25. Whether all three ship or are built on the player's machine is J38's call.

## Code
- `core/scale.py`: the layout and template rules (multiscale.md section 4 of the Empire branch).
  - **Geometry:** absolute edge snapping `px(x) = floor(x + 0.5)` on edges relative to the root. It covers component x/y, state w/h, image-use rects, V039 keyframe x/y/w/h, and textured image defs (`ceil(t * f)`).
  - **Left alone:** the image-use tail (9-slice stretch flags) and blank image defs.
  - **Fonts:** onto the slot files each context loads (Empire: `Ingame 24` Normal/Bold, `Frontend 24`, `Frontend 38`; the front end takes the nearest vanilla-named size), chosen as at 2x at every factor.
  - **Templates:** each embedded TGA is scaled with its image defs (nearest neighbour at 2x). The pre-v27 text records in `UPGRADE_TO_33` are rewritten as v33. `Cursor`, `slider`, `InputWindow` and `BattleEditor` pass through unchanged.
- `core/lua_consts.py` (J67): the classifier. A symbolic walk of all 497 scripts (registers, upvalues, globals, string-keyed fields, calls into and returns out of Lua functions, branches joined, loop bodies twice) lists every numeric constant that reaches a pixel-taking call (`MoveTo`, `Resize`, `CreateComponentFromTemplate` x/y, `SetStateTextXOffset`, `CallByAddress` of those) or a calculation with a pixel value (`Width`, `Height`, `Bounds`, `Position`, `Dimensions`, `ScreenSize`, ...). Rules: an offset, size, pitch or threshold scales; a ratio, zero, one, a fraction or a sentinel is left. `napoleon/lua_overrides.json` corrects a rule with a reason.
- `core/lua_patch.py` (J67): the patch applier and list writer (Empire's `apply_patches.py` syntax; every number in vanilla pixels, written as `px(v * factor)`; every item asserts the vanilla constant or instruction; factor 1.0 changes nothing).
- `core/check.py` (J67): a factor against a screen (Empire's `multiscale_check.py` idea): each layout's scaled extent against the screen and against vanilla 1080p, abutting pairs, the scaled layouts' fonts against the slot table.
- `core/art.py`: the J36 2.5x masters resampled to the factor. RGB is Lanczos in linear light, after dilation under alpha 0; alpha keeps its kind. With no master, Lanczos from vanilla.
- `core/cuf_encode.py`: Lora re-render of a vanilla `.cuf` (freetype-py 2.5.1, HarfBuzz pair kerning with a GPOS-reader fallback (D42), the vanilla header kept, so line pitch = h2 + 2). Empire's recipe; J67 adds the per-slot render scale of `font_slots.json` (1.0 at 2x: J66's pack unchanged).
- `napoleon/cli.py`, `napoleon/config.json`: paths, factors, the art roles, the never-scaled helpers and the font face.
- `napoleon/lua_consts.json`, `napoleon/lua_patches.txt` (generated), `napoleon/lua_overrides.json` (hand classes), `napoleon/lua_empire_items.json` (Empire's items, a snapshot for the cross-check), `napoleon/font_slots.json` (J37 adds its `engine_text` key beside `layouts`).
- Tests: `tests/test_uiscale.py` (scaler), `tests/test_uiscale_lua.py` (applier, classifier, tables, the list against the game's scripts), `tests/test_uiscale_fonts.py` (encoder), `tests/test_play.py` (install `--scale`), `tests/test_mod_packs.py`.

## Lua pixel constants (J67, desk phase 2026-11-03)
`lua_consts.json`: 1014 uses in 145 of the 497 scripts reach a pixel: 258 `scale`, 756 `leave` (each with its reason), no `manual` and none unclassified.
`lua_patches.txt`: 204 items in 69 scripts. Of Empire's 109 items, every one whose script and value exist in Napoleon is `scale` here, except the ones
listed under "Not ported" below. Causes found:
- **Battle radar group** (`battle.hud.radar`, `battle.minimised_hud.radar`): `ui/huds.luac` `RegisterHud` clamps the HUD width to 1280 (`if h_width > 1280 then h_width = 1280`),
  and `MoveRelativeToHUD` places a right-docked part at `h_width - width`. At 2x the HUD is 2560 wide, so the radar sat 1280 px left of its place. Patched: the 1280 scales.
- **Campaign minimap content** (`campaign.hud.radar`, `template.map_image`): the map draws at texture pixels x zoom x 2, and the theatre-map textures stay 1x; the x 2 and
  the two `FindRegion` multiplies (hover and click) scale together.
- **Generic tooltip** (`template.tooltip`): the 200x200 pre-size and the 16 px padding scale (vanilla wrap and padding at every factor).
- Patched scripts the dev wrappers also wrap (`proxy/napoleon/lua/wrappers.txt`): `ui/battle_ui/root.luac` and `ui/frontend_ui/main.advert.luac`. Which copy `wsp.vanilla`
  runs under the harness is the first PC probe (`napoleon.ui.lua_pack_route`).

## Held back or left (what is still 1x or unchecked)
- **Unproven in game:** every Lua patch, and the 1.25x and 1.5x sets (J67 PC slot).
- **Unseen headless:** tooltips and map hover (no hover verb); they are checked statically. Liam's first play session: hover a settlement, a unit card, a building and a technology.
- **Not ported from Empire (design changes, not scale fixes):** the wider tooltip wraps (900 at 2x) and equal right insets, and the map tooltip's right padding (inserted instructions).
  Vanilla has the same insets at 1080p. Empire's government one-letter fix and its religion-icon offset have no counterpart in Napoleon's script.
- **Theatre-map art:** the minimap and the diplomacy and objectives maps draw at the scaled size from the 1x textures (Empire made 4x art; a later job).
- **Loading screen and cursor** (`engine.loading_screen`, `engine.cursors`): after the J67 cut line. Empire's recipe for the progress bar is data only (2x trough and end-cap, the 1-px fill strip kept 1 px wide); the cursor has no known data route.
- **Engine-drawn text** (map and unit labels, the version string, the loading quote and subtitles): J37. `ui/labels.luac` is left vanilla here for that reason (`lua_overrides.json` `exclude_scripts`).
- **Font face (D42):** `uiscale/fonts/Lora-Variable.ttf` when vendored, else the same file in the empire-remastered clone (`config.json` `font_faces`).
