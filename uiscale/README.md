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

## Held back at 1x (J67)
- **Lua pixel constants:** grids, tooltip sizes, map hover, and the battle radar group's position (it sits about 1290 px left of the top-right corner at 4K).
- **Loading screen and cursor.**
- **The tooltip 200x200 pre-size.**
- **Engine-drawn text:** map and unit labels, the version string, the loading quote.
- **Front-end "New content" box:** clipped.
- **Unchecked in game:** tooltips, the campaign settlement panel and unit-card row (run 2026-11-02_j66).
- **Font face (D42):** vendored at `uiscale/fonts/Lora-Variable.ttf` (J68; SIL OFL text beside it). The same file in the empire-remastered clone is only a fallback (`config.json` `font_faces`).
