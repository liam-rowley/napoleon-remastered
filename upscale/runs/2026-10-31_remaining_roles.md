# Run report 2026-10-31: remaining roles (J51)

Session `81e5ee96-6775-41b5-be20-1c94ec3e8ebf`, branch `job/J51`. Same method as J36 (D35): models, per-role split, size and alpha rules and encoder unchanged.
Roles: `technology_icon`, `achievement_icon`, `loading_screen`, `map_pip`, `event_picture`, `building_icon`, `unit_card`, `portrait`, `flag`.

## a) Environment and disk
`python3 core/wsc.py upscale env` (2026-10-31): Python 3.12.10, numpy 2.5.2, PIL 12.3.0, spandrel 0.4.2, torch 2.14.1+cu130, CUDA on
NVIDIA GeForce RTX 4090 (24563 MiB, sm_89); `nomos_esrgan_2x` `65c8fe23425e0bca` ok, `hfa2k_compact_2x` `c31eaefe3253283a` ok; `ENV OK`.
`wsc upscale plan` over the nine roles: 5956 rows, 5954 `run`, 2 `skip:no_header` (flag animation TGAs). The plan has no output-size field; the
144-asset spot check below wrote 436.8 MB (3 MB per asset, loading screens heaviest), so the whole set was bounded at about 18 GB. Free on `C:` (the
work folder's drive): 566 GB of 1.5 TB. It fits with far more than 20 % to spare; the real total was 2.69 GB.

## b) Determinism spot check (`--sample 144`, 16 per role, fixed sha256 order)
| Run | Work folder | Done | Failed | Seconds |
|---|---|---|---|---|
| A | `C:\napoleon_remastered_pc\upscale\j51_sampleA` | 144 | 0 | 67.9 |
| B | `C:\napoleon_remastered_pc\upscale\j51_sampleB` | 144 | 0 | 66.3 |

All 144 outputs byte-identical: the `out.sha256` of every manifest entry matches between A and B, and so does a sha256 of every output file on disk.

## c) Full run (`wsc upscale run --roles <nine> --registry`, work `C:\napoleon_remastered_pc\upscale\work`)
First pass: 5953 done, 2 skipped, 1 failed, 376.0 s wall. The failure was `ui/flags/spain/large.dds`, a **DXT2** DDS (premultiplied BC2), a format
`upscale/core/dds.py` did not read. Fixed in the tool (DXT2 is DXT3 blocks with premultiplied colour: decoded to straight alpha, premultiplied again
on encode, vanilla header kept; host test `test_dxt2_is_premultiplied_dxt3`, 19 of 19 tests pass in the art_build Python). Second pass (resume):
1 fresh, 0 failed, 23.6 s. Output checked: DXT2 1280x640, 11 mips, colour within alpha in every texel.

| Role | Model | Done | Skipped | Failed | Model seconds | Output MB |
|---|---|---|---|---|---|---|
| `technology_icon` | nomos | 69 | 0 | 0 | 1.9 | 1.3 |
| `achievement_icon` | nomos | 73 | 0 | 0 | 2.7 | 29.2 |
| `loading_screen` | nomos | 39 | 0 | 0 | 128.4 | 582.7 |
| `map_pip` | compact | 149 | 0 | 0 | 0.5 | 2.7 |
| `event_picture` | nomos | 229 | 0 | 0 | 18.3 | 537.1 |
| `building_icon` | nomos | 657 | 0 | 0 | 19.2 | 102.8 |
| `unit_card` | nomos | 1105 | 0 | 0 | 30.4 | 160.3 |
| `portrait` | nomos | 1375 | 0 | 0 | 59.6 | 169.1 |
| `flag` | nomos | 2258 | 2 | 0 (1 before the fix) | 109.5 | 1105 |

"Model seconds" is the sum of the per-asset `seconds` in the manifest; the wall time includes reading the packs and encoding.
`wsc upscale verify --roles <nine>`: 5954 checked, 0 with problems.

23 outputs are longer than 4096 px on one side (loading screens 1920x1200 -> 4800x3000, `screenshot.dds` -> 4800x2250): `native_cap` 4096 is tested on
the source size, so they are inside the configured rule. Whether the engine takes a texture over 4096 is J50's to see (J51 report, Open questions).

## d) Packs (`wsc upscale pack --roles <nine>`, `C:\napoleon_remastered_pc\upscale\work\packs\`, credits in `<pack>.json`)
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

Not installed (brief: J50 owns installing and loading). The game folder was only read.

## Sheets
`wsc upscale sheets`, 24 fixed assets per role, written as JPG (quality 85) over J36's sample sheets of the same roles: `upscale/sheets/<role>.jpg`, 2.5 MB for the nine.
