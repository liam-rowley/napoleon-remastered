# J51: Upscale the remaining UI art roles

Phase 5, follow-up to J36. J36 built the UI art upscaler and ran it on the first four roles (`ui_art`, `icon`, `panel_frame`, `button_state`: 3484 assets,
0 failed, `verify` clean). Liam approved the contact sheets on 2026-10-31 (D35), so the pinned models and the per-role model choice stand. This job runs the
same pipeline, unchanged in method, on the 5954 assets that are still `todo` in the nine other roles, verifies them, builds one pack per role, records every
asset in the `assets` registry and writes a dated run report. It builds packs; it does not install them (Decisions below).

Model: Sonnet. No reverse engineering: the pipeline exists (J36); this is a batch run, checks and a report. Budget about 120 tool calls; at the cap, stop,
commit, report what is left. Subagents are not needed. Waiting belongs to the harness: the batch run goes through one blocking call or a background command,
never a polling loop.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J51`). Read `docs/DECISIONS.md` (D5, D14, D19, D35), `upscale/README.md`, `jobs/J36/report.md` (Counts and timings,
  Deviations, Open questions 3, 5 and 7), `jobs/J36/review.md` and `upscale/runs/2026-10-31_first_roles.md`.
- Search before writing: `python3 core/wsc.py find upscale pack verify sheets assets`. Use `python3 core/wsc.py upscale <env|plan|run|verify|sheets|pack>`;
  fix a fault in `upscale/core/` or `upscale/napoleon/` with a host test, and add no near-duplicate tool.

## Target facts
Check each again before relying on it:
- The GPU environment is `C:\napoleon_remastered_pc\upscale\art_build` (RTX 4090, torch 2.14.1+cu130, spandrel 0.4.2, fp16, tile 256, overlap 16); the work folder
  is `C:\napoleon_remastered_pc\upscale\work`. `wsc upscale env` must match both model pins in `upscale/napoleon/models.json` before any run.
- The remaining roles and their `todo` counts (from the J36 report; recount with `wsc upscale plan` and use the plan's numbers): `map_pip` 149, `building_icon` 657,
  `technology_icon` 69, `achievement_icon` 73, `event_picture` 229, `unit_card` 1105, `portrait` 1375, `flag` 2258 (2 more are `not_needed`: animation TGAs J7
  could not parse), `loading_screen` 39.
- Speed on the J36 sample was about 0.33 s per asset for these roles, so the whole run is about 35 minutes. Pack size is not measured: the first four roles gave
  709 MB for 3484 assets, but portraits, event pictures and loading screens are larger images. Check free disk on the work folder's drive against the plan's
  output size before the run.
- Pack entries go under `ui_art_2x5\<vanilla path>`, so a pack replaces no vanilla file. TGA stays TGA and JPG stays JPG until J50 answers
  `napoleon.ui_art.dds_at_tga_paths`.

## Decisions already made for this job
- **Method unchanged (D35).** The same two pinned models and the per-role split in `upscale/napoleon/config.json`: `hfa2k_compact_2x` for `map_pip`;
  `nomos_esrgan_2x` for the other eight roles. No new model, no 4x side by side, no change to the size rule (2.5x vanilla, the configured caps, with
  `loading_screen` at `native_cap` 4096), the alpha rules or the encoder.
- **All nine roles in one run.** Order does not matter at this speed; run the small roles first (`technology_icon`, `achievement_icon`, `loading_screen`, `map_pip`,
  `event_picture`) so a fault shows early, then `building_icon`, `unit_card`, `portrait`, `flag`. Resume is the batch's own (`run` skips done outputs).
- **Determinism spot check.** Before the full run, run a fixed sample of 16 assets per remaining role twice and compare the per-asset sha256 from the two manifests:
  every output must be byte-identical, as in J36.
- **Verify every asset**, then build one pack per role with `wsc upscale pack` (`ui_art_2x5_<role>.pack`, credits in `<pack>.json`), and record entries, size and the
  first 16 characters of the sha256 per pack.
- **No install.** The packs replace no vanilla path, so copying them into `data\` proves nothing J36's sha-checked sync did not; J50 owns installing and loading, and
  the `mod_packs` skip list. This job never writes the game folder. (The J51 row text said "install and uninstall as in J36"; this brief narrows that, for this reason.)
- **Registry.** Run with `--registry` so every asset in the nine roles ends `done` (method text in `upscale_method`) or `not_needed` with its reason, using J36's mapping
  of the status words (J36 report, Deviations). No `todo` row may be left in these roles without a stated reason.
- **Sheets for the record.** One sheet per role from the full run (`wsc upscale sheets`, a fixed 24 assets per role) under `upscale/sheets/`, JPG, about 3 MB in all. Liam
  has approved the method; these are the record of the output, not a new approval gate.
- **Out of scope:** cursors (`.cur`, `.ani`), DDS-at-TGA conversion, in-game loading, the core `upscale_status` enum, CI dependencies.

## Deliverables
1. `wsc upscale env` output and the free-disk check in the run report.
2. The determinism spot check: 144 assets, two runs, sha256 compared, all identical.
3. The full run of the nine roles: done, skipped and failed counts and seconds per role; `verify` 0 problems, or every problem explained and fixed.
4. Nine packs in `C:\napoleon_remastered_pc\upscale\work\packs\` with a table of entries, MB and sha256 (first 16).
5. `registries/assets.jsonl` and its rendered view updated for every asset in the nine roles; `python3 core/wsc.py gates` green.
6. Per-role sheets under `upscale/sheets/`.
7. A dated run report `upscale/runs/<date>_remaining_roles.md` and an update of `upscale/README.md` if a command or count there changed.

## PC test
On the PC, unattended; the game is not launched and the game folder is only read. Steps:
- a) `wsc upscale env`; free disk against the plan's output size.
- b) The 144-asset spot check, twice; sha256 compared.
- c) The full run in the order above; `verify`.
- d) `pack` per role; the pack table; `sheets`.

## Kill criteria
- `wsc upscale env` does not match a model pin, or the environment needs rebuilding beyond `upscale\pc\setup_env.cmd`: stop and report.
- Any output differs between the two spot-check runs: stop, keep both manifests, report; do not run the full set.
- A role fails or fails `verify` on more than 1 % of its assets after one fix of a tool fault: stop that role, keep its outputs out of any pack, report the cases and go on
  with the other roles.
- The output would not fit on the work folder's drive with 20 % to spare: stop before the run and ask Liam where it goes.
- The run would need a new model, a change to the size or alpha rules, a write into the game folder or into `core/`: stop and ask Liam.

## Finish
Write `jobs/J51/report.md`: what was run (run report path, timings), the spot-check result, per-role counts and verify results, the pack table, the registry change,
deviations from this brief and why, open questions (for example roles whose model split looked wrong in the sheets). Then
`wsc reg set jobs J51 status=review report=jobs/J51/report.md`.
