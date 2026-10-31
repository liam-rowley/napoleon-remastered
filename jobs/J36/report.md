# J36 report: UI art upscaling pipeline

Branch `job/J36`, session `514575b5-1a42-4166-9195-672b2b3d3a73`, model Sonnet 5.5. Run evidence with dates and ids:
`upscale/runs/2026-10-31_first_roles.md`. **One brief item is not done: the packed files were never loaded by the game** (see Deviations).

## What was built
- `upscale/core/` (game-agnostic): `dds.py` (DDS read and write for DXT1, DXT3, DXT5, A8R8G8B8 and R8G8B8, vanilla header kept, python, quicktex and texconv encoders), `imageio.py`
  (TGA, JPG, PNG in and out), `resample.py` (dilate RGB under A = 0, per-channel Lanczos, binary-alpha rule, linear-light mip chain), `model.py` (pinned model fetch with sha256,
  tiled runner with overlap context, a Lanczos stand-in for host tests), `batch.py` (plan, run with resume by input hash, per-asset manifest, verify), `pack.py` (movie pack,
  two-phase `.building`, sha-check while copying and after), `contact.py` (before/after sheets, hard-case crops, model comparison), `rules.py` (size rule, skip rules, status mapping).
- `upscale/napoleon/`: `config.json` (roles, model per role, pack prefix), `models.json` (pins: URL, sha256, licence, credit), `cli.py` (the driver over the assets registry and the J7 `PackFS`).
- `tools/verbs/upscale.py`: `python3 core/wsc.py upscale env|plan|run|verify|sheets|compare|pack`. It starts the art_build Python; the verbs of the brief are all there, plus `compare`.
- `upscale/pc/setup_env.cmd` and `env_check.py`: the PC environment in `C:\napoleon_remastered_pc\upscale\art_build` (embeddable Python 3.12.10, torch 2.14.1+cu130, spandrel, pinned models; nothing system-wide).
  `wsc upscale env` prints GPU, torch, spandrel and each model's sha256 against its pin.
- `tests/test_upscale.py`: 18 host tests (size rule, status mapping, pack writer and its re-read by the J7 reader, DDS header round trip for 5 formats, alpha rules, dilation, mip chain and
  linear light, manifest, resume, byte-identical second run, verify catching a flipped byte, a wrong size and a flat output). 9 need numpy and Pillow (see Open questions 1).
- Registry: `upscale_method` and `upscale_status` set for all 9619 in-scope rows by the tool. 12 tool rows, 4 engine facts, `upscale/sheets/*.jpg` (2.8 MB; full size under `/extract/napoleon/upscale_sheets/`).

## Counts and timings
| Role | Rows | Status | Note |
|---|---|---|---|
| `ui_art` 397, `icon` 555, `panel_frame` 517, `button_state` 2015 | 3484 | done, 0 failed | full run 43.9 s on the RTX 4090; `verify` 0 problems |
| `map_pip` 149, `building_icon` 657, `technology_icon` 69, `achievement_icon` 73, `event_picture` 229, `unit_card` 1105, `portrait` 1375, `flag` 2258, `loading_screen` 39 | 5954 | `todo` (planned: all would run) | a 13-role sample of 208 of them ran clean (68 s, about 0.33 s each) |
| `cursor` 179 | 179 | `not_needed`, `skipped:not_an_image_file` | `.cur` and `.ani`, see Open questions 3 |
| `flag` | 2 | `not_needed`, `skipped:no_header` | the two flag animation TGAs J7 could not parse |

Nothing was skipped as already large or under 2x: the largest UI art is under the 2048 px cap. Sample, determinism and pack figures are in the run report.

## Evidence
- Sample of 208, two runs: 207 of 207 outputs byte-identical; a third run (after one code fix) 208 done. First roles: 3484 done, verify clean. Run report above; local `wsc gates`: 12 ok, 319 host tests.
- Pack sync and uninstall: watcher jobs `J36-20261031T000049Z-2475724347` (install, 4 packs sha-checked) and `J36-20261031T000109Z-15215980` (uninstall); `pc_deploy.py diff` of the snapshots: `identical`.
- Models: `nomos_esrgan_2x` and `hfa2k_compact_2x`, both CC BY 4.0 (release pages, read 2026-10-30), which allows redistributing outputs with credit; the pack manifest carries the credit lines.
  `2xAoMR_mosr` (used in Empire) is not used: its page says "CC-BY-0.4".
- 1080p authoring (brief: "check on a sample"): the sizes are in line with 1080p art (round battle buttons 56 px, radio buttons 22 px, button strips 256 x 40, corner frames 72 px) and none is near a 4K
  size. I did **not** compare them with layout component sizes, so this is plausibility, not a check.
- Sheets (Liam judges, nothing is claimed approved): `upscale/sheets/{ui_art,icon,panel_frame,button_state}.jpg` for the first roles, the other roles from the 208 sample, `compare_<role>.jpg`
  (Lanczos | Nomos | Compact), `hard_cases_work.jpg` and `hard_cases_sampleA.jpg`. In the hard-case crops I see no invented detail (0 of 9 in the sample sheet).

## Deviations from the brief and why
- **The game did not load the packs (PC test d).** The game folder has no proxy, so the watcher refuses a headless launch (job `J36-20261031T000057Z-756112982`, exit -2); a visible launch
  needs Liam present. I installed the packs sha-checked, stopped there, and uninstalled (e, byte-identical). `napoleon.ui_art.pack_loads` is an `open` engine fact. The kill criterion "any crash when
  the packed files load" is therefore neither hit nor cleared.
- **`upscale_status` words.** The brief asks for `pending | done | skipped:<reason> | failed:<reason>`, but the core's assets schema only allows `todo | done | not_needed` (and `wsc.toml` uses it unchanged).
  The tool writes `todo` for pending and for failed, `not_needed` for skipped, and puts `skipped:<reason>` or `failed:<reason>` in `upscale_method` (a done row has the method text). The full words are in
  the manifest. Widening the enum is a warscape-core change (Open questions 2).
- **TGA stays TGA, JPG stays JPG** (brief: write DDS where the engine loads it; else TGA): whether the engine loads DDS at a TGA path is unprobed (open fact `napoleon.ui_art.dds_at_tga_paths`),
  so TGA outputs have no mips here and the UI host builds them. DDS sources get the full chain. Of the 9,619 in-scope rows 8,668 are TGA, 665 JPG, 106 DDS and 179 cursor files (counts from the registry formats).
- **Pack entries sit under `ui_art_2x5\` plus the vanilla path**, so installing a pack replaces no vanilla file (the brief's own test expects nothing to use them yet). Packs are per role.
- **Model per role is provisional** (Nomos for photographic art, Compact for flat art and buttons), chosen from a side by side by eye on 8 assets in 6 roles; no 4x model was tried (the two with a clear licence are 2x).
- **Alpha check is the mean alpha**, not a threshold coverage (it is the same for a cut-out and stable for soft alpha near 128); tolerance 0.02 plus a term for small images and mips. Found by the first verify (7 false alarms, run report).
- Encoder: the pure numpy `python` DXT encoder is the default (deterministic, no external binary); texconv and quicktex are ported but untested here. DXT quality was not compared.
- Work happened in a git worktree (the session guard), and the first files were written before that; they were moved into the worktree unchanged.

## What moves to the core later
All of `upscale/core/` is game-agnostic (nothing in it names Napoleon): `dds.py`, `imageio.py`, `resample.py`, `model.py`, `batch.py`, `pack.py`, `contact.py`, `rules.py`, with `pc/setup_env.cmd` and `env_check.py`.
`upscale/napoleon/` and `tools/verbs/upscale.py` stay as the adapter. `dds.py` duplicates Empire's (ported with normal maps removed and DXT3 and R8G8B8 added): the core copy should replace both.

## Open questions
1. **Host tests in CI.** The gate image has neither numpy nor Pillow, so 9 of the 18 tests skip there (stdlib tests run). Add `pip install -r upscale/requirements.txt` to the gates workflow, or run them only on the PC?
2. **Status words.** Widen the core `upscale_status` enum to the brief's words, or keep the mapping above?
3. **Cursors** (179 `.cur` and 1 `.ani`) are not images to Pillow and were skipped. They need a cursor-specific path (the RmlUi host draws its own cursors?). Decide whether they are in scope.
4. **Load test.** Who deploys the proxy (J20 flow) so a headless launch with the packs installed can prove loading? Until then `napoleon.ui_art.pack_loads` stays open.
5. **Order of the other roles** (Liam, from the sheets): 5954 assets are `todo`; `wsc upscale run --roles <role> --registry` then `pack`. The `flag` role is 2258 files, `portrait` 1375, `unit_card` 1105.
6. **J7 re-index with the packs installed.** `ui_art_2x5_*.pack` in `data\` would be indexed as game packs; add them to the games.json `mod_packs` skip list before installing for real.
7. **Soft models and flags.** The flags and portraits are art with film grain; Nomos keeps grain, Compact smooths it. Liam's call from `compare_flag.jpg` and `compare_portrait.jpg`.
