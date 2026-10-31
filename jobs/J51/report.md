# J51 report: Upscale the remaining UI art roles

Branch `job/J51`, session `81e5ee96-6775-41b5-be20-1c94ec3e8ebf`. Run report with every number: `upscale/runs/2026-10-31_remaining_roles.md`.

## What was built
- The J36 pipeline, unchanged in method (D35), run over the nine remaining roles: 5954 assets done, 2 `not_needed`, 0 failed; `verify` 0 problems.
- One tool fix: `upscale/core/dds.py` reads and writes DXT2 (premultiplied BC2), found by the full run on `ui/flags/spain/large.dds`; host test
  `test_dxt2_is_premultiplied_dxt3` in `tests/test_upscale.py`; the tools row updated for the new purpose line.
- Nine packs `ui_art_2x5_<role>.pack` in `C:\napoleon_remastered_pc\upscale\work\packs\` (5954 entries, 2.69 GB), not installed.
- `registries/assets.jsonl` and `assets.md`: every row of the nine roles has `upscale_status` and `upscale_method`.
- Per-role sheets of the full run under `upscale/sheets/` (they replace J36's sample sheets of the same nine roles).

## Counts and timings
| Step | Result |
|---|---|
| a) `wsc upscale env` | `ENV OK`, both model pins match; 566 GB free on `C:` against at most about 18 GB (real: 2.69 GB) |
| b) Spot check, 144 assets x 2 | 144 done each (67.9 s, 66.3 s); 144 of 144 outputs byte-identical (manifest sha256 and file sha256) |
| c) Full run | pass 1: 5953 done, 2 skipped, 1 failed (DXT2), 376.0 s; after the fix: 1 fresh, 0 failed, 23.6 s |
| c) Verify | 5954 checked, 0 with problems |
| d) Packs | nine, table below |

| Pack | Entries | MB | sha256 (first 16) |
|---|---|---|---|
| `ui_art_2x5_technology_icon` | 69 | 1.4 | `fe3be0a8cd480c55` |
| `ui_art_2x5_achievement_icon` | 73 | 29.2 | `b03c81cc9779c916` |
| `ui_art_2x5_loading_screen` | 39 | 582.7 | `7dbc70cb124551fb` |
| `ui_art_2x5_map_pip` | 149 | 2.7 | `88954ffe43276f20` |
| `ui_art_2x5_event_picture` | 229 | 537.1 | `6e132d963212ecea` |
| `ui_art_2x5_building_icon` | 657 | 102.8 | `cf742889021886bb` |
| `ui_art_2x5_unit_card` | 1105 | 160.4 | `0c2fb63d67441712` |
| `ui_art_2x5_portrait` | 1375 | 169.2 | `08e64398e508de26` |
| `ui_art_2x5_flag` | 2258 | 1105.1 | `e783b3c466671623` |

Registry, nine roles: 5954 `done` (method text, e.g. `nomos_esrgan_2x(x2)+lanczos->2.5x fp16 tile256/ov16`); 2 `not_needed` with `upscale_method`
`skipped:no_header`: `ui/flags/punjab/flag_animation0011.tga`, `ui/flags/quebec/flag_animation0000.tga` (the animation TGAs J7 could not parse). No `todo` left.

## Evidence
- Run report: `upscale/runs/2026-10-31_remaining_roles.md`. Manifests: `C:\napoleon_remastered_pc\upscale\work\manifest.json`, spot check
  `...\upscale\j51_sampleA\manifest.json` and `...\j51_sampleB\manifest.json`. Run log `...\upscale\run_j51.log`.
- Sheets checked by eye before commit: `portrait`, `map_pip`, `loading_screen` (edges, alpha cut-outs and text strokes kept; nothing invented that I could see),
  and the fixed DXT2 flag at full size.
- `python3 core/wsc.py gates --fast`: 10 ok, 1 warn (the `hooks` warning: the clone's hooksPath is absolute, not `core/.githooks`), 0 failed.

## Deviations from the brief and why
- **Role order.** The batch runs assets in registry order, not in `--roles` order, so the small roles did not go first. At 376 s for the lot, no fault would
  have shown sooner; resume made the fix cost 23.6 s.
- **One tool fault fixed mid-run (allowed by the brief):** DXT2 support in `dds.py`, with a host test. The method is unchanged; DXT2 only reaches the encoder
  through the python path (texconv and quicktex have no premultiplied BC2 here).
- **Free disk against "the plan's output size":** `plan` reports no output size, so the bound came from the spot check (3 MB per asset, about 18 GB worst case).
- **Not a separate job session:** built in an interactive session on Liam's word ("Build it here") after the app refused to start a new session over Remote Control.
- Sheets are JPG quality 85 so the nine stay near the brief's 3 MB (2.5 MB).

## Open questions
1. **Textures over 4096 px.** 23 outputs (loading screens 4800x3000, `ui/frontend_ui/loadingscreen/screenshot.dds` 4800x2250) are over 4096 on one side,
   because `native_cap` 4096 is tested on the source size. J50 should see whether the engine takes them; if not, cap the target (not the source) at 4096
   for `loading_screen`, a size-rule change for Liam.
2. **Pack size.** The nine packs are 2.69 GB (with J36's four, 3.4 GB). Loading screens and event pictures are 42 % of it for 268 assets; worth a look when J50
   measures load time and memory.
3. **Model split.** Nothing in the nine sheets argued for moving a role to the other model (D35 stands); `map_pip` on Compact looks clean at 65x65.
4. **CI and host tests** (J36 open question 1) still stand: the DXT2 test is one of those that skip in the gate image without numpy and Pillow.
