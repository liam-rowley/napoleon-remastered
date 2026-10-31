# UI art upscaler (J36)

D19: vanilla UI art is ML-upscaled by an integer factor, resampled to 2.5x its vanilla pixel size, given a full mip chain (DDS) and packed. UI art only (D14).
Report and evidence: `jobs/J36/report.md`, `upscale/runs/`. Sheets to judge: `upscale/sheets/`.

## Run
1. Once: `upscale\pc\setup_env.cmd` (a self-contained Python with torch in `C:\napoleon_remastered_pc\upscale\art_build`; nothing system-wide). Check: `python3 core/wsc.py upscale env`.
2. `python3 core/wsc.py upscale plan --roles icon` (decisions, no work), `run --roles icon --registry` (writes `<work>\out`, `manifest.json`, the registry fields), `verify`,
   `sheets` (before/after under `/extract/napoleon/upscale_sheets/`), `compare --sample 192` (model side by side), `pack` (one `ui_art_2x5_<role>.pack` per role in `<work>\packs`).
   Default work folder `C:\napoleon_remastered_pc\upscale\work`; `--roles` defaults to `first_roles` in `upscale/napoleon/config.json`.
3. Install a pack only through a watcher job running `upscale\pc\install_packs.ps1` (sha-checked copy, uninstall moves to `_to_delete`; example jobs in
   `upscale/runs/2026-10-31_j50/`); the tools never write the game folder. Every `ui_art_2x5_<role>.pack` is in `discovery/napoleon/games.json` `mod_packs`
   (`tests/test_mod_packs.py`), so the indexer never reads one as a game pack. In game (J50): the packs load without a crash; a movie pack's entry at a
   vanilla path replaces the `data.pack` art in the front end, campaign and battle, and 2.5x art there is drawn into the vanilla rect.

## Rules (code: `upscale/core/rules.py`, `resample.py`, `batch.py`)
- Target = floor(2.5 x size + 0.5) per axis; a longest side at or above `native_cap` (2048) or a non-image file is skipped with a reason.
- RGB goes through the model (x2) after dilation under A = 0, then Lanczos to the exact target; alpha never meets the model (Lanczos, cut at 128 when the vanilla alpha is a cut-out).
- DDS keeps the vanilla format and header (size and mips change) with the full chain: RGB box in linear light, alpha plain box. TGA and JPG keep their container, no mips: a DDS at a `.tga` path was not drawn (fact `napoleon.ui_art.dds_at_tga_paths`, refuted in J50 on one probe whose DXT size was not a multiple of 4: see the fact's notes).
- Resume key = input sha256 + model sha256 + settings; a second run changes nothing. Pack entries sit under `ui_art_2x5\<vanilla path>`.
- Models are pinned in `upscale/napoleon/models.json` (URL, sha256, licence) and fetched into the work folder, never committed.
