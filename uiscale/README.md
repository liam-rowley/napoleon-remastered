# UI scale stop-gap (J66, D40)

This scales the vanilla UI's data by a fixed factor, so that the UI is playable at 4K before the RmlUi screens exist. It is ported from empire-remastered
`ui_scale_mod` (read-only evidence). There is one factor, **2.0**: 3840x2160 is 2 x 1080. 1.25x, 1.5x, the Lua pixel constants and the screens this
job leaves are **J67**.

## Build and install
```
python3 core/wsc.py uiscale build [--factor 2] [--no-art] [--no-fonts]      # in the art_build Python; nothing touches the game folder
python3 upscale/pc/play.py install --scale 2  |  status  |  uninstall        # Liam's play install (upscale/README.md "Play test")
```
The build writes these files to `<state folder>\uiscale\work\` (`tools/pc_state.py`: the adapter's `state_dir`, `C:\napoleon_remastered_pc`, or `$NAPOLEON_STATE_DIR`). Each has a `.json` with its entries, sha256, what was held back and the method:
- `ui_scale_2x.pack` (movie): every vanilla layout (174) and the UI art at 2x.
- `ui_scale_2x_fonts.pack` (movie): the slot fonts.
- `uied.templates.ui_scale_2x`: the scaled templates file.
- `ui_scale_2x.rules`: a `dev.file_rules` line that redirects the loose `data\ui\templates\uied.templates` to the scaled file. This is the proxy's
  existing file-rule mechanism (attribute check and open), so the DLL does not change (fact `napoleon.ui.templates_route`).

A re-run is byte-identical: the art is cached by input sha256, and the pack is kept when its plan is unchanged.

## Code
- `core/scale.py`: the rules (multiscale.md section 4 of the Empire branch), and Empire's long-form pass (J79): only a TextView's `Text` child keeps the spaced `Frontend 24` slot, every other user of it takes `Ingame 24`.
  - **Geometry:** absolute edge snapping `px(x) = floor(x + 0.5)` on edges relative to the root, never per-value rounding. It covers component x/y, state w/h, image-use rects, V039 keyframe x/y/w/h, and textured image defs (`ceil(t * f)`).
  - **Left alone:** the image-use tail (9-slice stretch flags) and blank image defs.
  - **Fonts:** onto the slot files each context loads (Empire: `Ingame 24` Normal/Bold, `Frontend 24`, `Frontend 38`; the front end takes the nearest vanilla-named size).
  - **Templates:** each embedded TGA is scaled with its image defs (nearest neighbour at 2x). The pre-v27 text records in `UPGRADE_TO_33` are rewritten as v33. `Cursor`, `slider`, `InputWindow` and `BattleEditor` pass through unchanged.
- `core/art.py`: the J36 2.5x masters resampled to exactly 2x. RGB is Lanczos in linear light, after dilation under alpha 0. Alpha keeps its kind (binary stays binary). The output keeps the vanilla container; DDS gets a full mip chain. With no master, it falls back to Lanczos from vanilla.
- `core/cuf_encode.py`: Lora re-render of a vanilla `.cuf` (freetype-py 2.5.1, HarfBuzz pair kerning (D42; required since J79, no GPOS fallback; golden shas in `napoleon/font_golden.json`), the vanilla header kept, so line pitch = h2 + 2). Empire's recipe: wght 500 at em = 23/24 h2, bold 700 fitted to 99 % of the vanilla width, `frontend_24` spaced h2 = 28.
- `napoleon/cli.py`, `napoleon/config.json`: paths, the art roles, the never-scaled helpers (`1x1*`, `1px_*`, `fe_1x1*`, `progressbar_beige`, loading screens, cursors) and the font face.
- Tests: `tests/test_uiscale.py` (scaler), `tests/test_uiscale_fonts.py` (encoder), `tests/test_play.py` (install `--scale 2`), `tests/test_mod_packs.py`.

## Held back at 1x (J67)
- **Lua pixel constants:** grids, tooltip sizes, map hover, and the battle radar group's position (it sits about 1290 px left of the top-right corner at 4K).
- **Loading screen and cursor.**
- **The tooltip 200x200 pre-size.**
- **Engine-drawn text:** map and unit labels, the version string, the loading quote.
- **Front-end "New content" box:** clipped.
- **Unchecked in game:** tooltips, the campaign settlement panel and unit-card row (run 2026-11-02_j66).
- **Font face (D42):** vendored at `uiscale/fonts/Lora-Variable.ttf` (J68; SIL OFL text beside it). The same file in the empire-remastered clone is only a fallback (`config.json` `font_faces`).
