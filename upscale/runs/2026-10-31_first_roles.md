# Run report 2026-10-31: first roles, sample, pack sync (J36)

Session `514575b5-1a42-4166-9195-672b2b3d3a73`, branch `job/J36`. PC: RTX 4090 (24563 MiB, sm_89), torch 2.14.1+cu130, spandrel 0.4.2,
Python 3.12.10 (embeddable) in `C:\napoleon_remastered_pc\upscale\art_build`. Settings: fp16, tile 256, overlap 16, cudnn deterministic.
Models (pins in `upscale/napoleon/models.json`, both CC BY 4.0, read on the release pages 2026-10-30): `nomos_esrgan_2x`
`65c8fe23425e…`, `hfa2k_compact_2x` `c31eaefe3253…`.

## a) Environment
`python3 core/wsc.py upscale env`: GPU, torch, spandrel and both model sha256 match the pins. Set up by `upscale\pc\setup_env.cmd` on the
first attempt after one fix (GNU `tar` from Git Bash cannot read `C:\` paths: the script now calls `System32\tar.exe`).
Nothing is installed system-wide; the folder is outside the game's `data\`.

## b) 208-asset sample, two runs (`--sample 208`, 16 per role over 13 roles; the sample is a fixed sha256 order)
| Run | Fresh | Failed | Seconds |
|---|---|---|---|
| A | 207 | 1 (a 24-bit DDS, then unsupported) | 69.3 |
| B | 207 | 1 | 67.8 |

All 207 outputs byte-identical between A and B (sha256 per asset from the two manifests). The failure was `ui/frontend_ui/loadingscreen/border_corner.dds`
(uncompressed `R8G8B8`); the DDS code now reads and writes that format and the sample re-ran with 208 done, 0 failed (68.1 s).
About 0.33 s per asset over a mix of portraits, flags, unit cards and icons. Verify on the sample: clean.

## c) First roles: `ui_art`, `icon`, `panel_frame`, `button_state`
3484 assets, 0 skipped, 0 failed, 43.9 s (small art: about 13 ms each). `verify`: 3484 checked, 0 problems (18.8 s).
The first verify found 7 problems that were faults of the checks, not of the output, and the checks were fixed:
- A fully transparent source (`avatar_stranger.tga`) has no colour to spread; it is no longer dilated, and "flat" now compares the RGB of visible texels only.
- Coverage by a threshold at 128 is unstable for soft alpha that sits near 128 (`card_cav.tga` has 70 % of its texels at 128 to 191, mean alpha unchanged to 0.04 %). The check is now the mean alpha, which equals coverage for a cut-out, with a tolerance that grows for small images and small mips.
- Table of the roles that ran: `ui_art` 397, `icon` 555, `panel_frame` 517, `button_state` 2015, all `done`.

Packs (`wsc upscale pack`, movie type 4, entries under `ui_art_2x5\<vanilla path>` so no vanilla path is overridden, credits in `<pack>.json`):

| Pack | Entries | MB | sha256 (first 16) |
|---|---|---|---|
| `ui_art_2x5_ui_art` | 397 | 354.4 | `7415a856fbcbc177` |
| `ui_art_2x5_icon` | 555 | 17.8 | `6b5c7846cec43893` |
| `ui_art_2x5_panel_frame` | 517 | 193.9 | `633c99f823ee8643` |
| `ui_art_2x5_button_state` | 2015 | 142.8 | `1f521cc9a1a067f7` |

## d) Sync and load
A watcher job (lock owner `J36`, `install_packs.ps1`) copied the four packs into `data\` with sha256 checked on the source, on the copy and
against the pack manifest: all four matched. **The launch did not happen**: the game folder has no proxy (`d3d9.dll` without `headless_status.json`)
and the watcher refuses a headless launch (job `J36-20261031T000057Z-756112982`, exit -2, "Deploy the current proxy, or use visible=1 only with Liam
present"). No visible launch was made. So "the packed files load" is **not verified**; it needs the proxy deployed (J20 flow) or Liam present.

## e) Uninstall
A second watcher job moved the four packs to `watcher\_to_delete\J36_packs` (nothing is deleted). `pc_deploy.py snapshot` before and after
(1564 entries each): `pc_deploy.py diff` prints `identical`. The game lock was released.

## Model side by side (fixed sample, 1:1 crops of the 2.5x size, `upscale/sheets/compare_*.jpg`)
Six roles x 8 assets: `ui_art`, `icon`, `panel_frame`, `button_state`, `flag`, `portrait`. Both models keep every edge, bevel and text stroke; `hfa2k_compact_2x`
is a little smoother and slightly darker in fills, `nomos_esrgan_2x` keeps more grain (paper, flags, portraits). The configured split (Nomos for photographic
art, Compact for flat art and buttons) is provisional: Liam picks from the sheets.

## Hard cases (`upscale/sheets/hard_cases_work.jpg`, `hard_cases_sampleA.jpg`)
Thin frames, glyph-like icons, soft alpha edges (first roles), flag cloth, portraits, soft alpha on a unit card (sample). By my eye no crop shows
invented detail (0 of 9 in the sample sheet); this is a reading by the author of the tool, not an approval. Cursors are not in the sheets: see open question 3.
