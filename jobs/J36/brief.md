# J36: UI art upscaling pipeline

Phase 5. D5 and D19: vanilla UI art is ML-upscaled, then resampled to the 2.5x master size (the 1080p reference x 2.5, the largest
dp in use: 4K x 125 %) with mipmaps. This job builds the pipeline, runs it on the UI art roles, records method and status per asset in
the `assets` registry, and gives Liam before and after contact sheets to judge. It is deterministic, re-runnable, and its output is
packed sha-checked. UI art only (D14): no unit, building or terrain textures.

Model: Sonnet. No reverse engineering: the pack reader and asset index exist (J7), the pipeline is image processing and pack writing.
Budget about 250 tool calls; at the cap, stop, commit, report what is left. At most 2 subagents, only for independent read-only work
(for example, reading Empire's batch tool while you port). Waiting belongs to the harness: long batch runs go through the watcher or a
background command, never a polling loop.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J36`). Read `docs/DECISIONS.md` (D5, D14, D19), `docs/plans/UI_PIPELINE.md` section 2.5 and
  `docs/plans/PLAN.md` section 4 (core candidate: game-agnostic pipeline in `*/core/`, Napoleon roles in the adapter).
- Read `jobs/J7/report.md` and `discovery/assets/README.md`: `discovery/core/packfs.py` (read effective files), `imagehdr.py`,
  `sheets.py` (contact sheets, Pillow), the `assets` registry roles and the `discovery/napoleon/asset_roles.json` rules. Reuse them.
- Evidence, read only (`--add-dir ../empire-remastered`, never edit there; Empire facts are rechecked on Napoleon):
  `art_mod/tools/{dds.py, remaster_batch.py, build_texture_pack.py, requirements_batch.txt}` and
  `art_mod/docs/{batch_tool.md, pc_batch_env.md, PIPELINE_GUIDE.md}`. Port the ideas (DDS reader and writer that keeps the vanilla
  header, per-channel Lanczos for alpha, tiled fp16 inference, pack writer with two-phase `.building`, resume, sha-check while
  copying); do not port the unit, building, normal or gloss rules.

## Decisions already made for this job
- Scope: the 2D UI art roles in the assets registry: `ui_art`, `icon`, `panel_frame`, `button_state`, `map_pip`, `cursor`,
  `building_icon`, `technology_icon`, `achievement_icon`, `event_picture`, `unit_card`, `portrait`, `flag`, `loading_screen`.
  Fonts, layouts, scripts and db tables are out. Run first the roles the proving screens need (`ui_art`, `icon`, `panel_frame`,
  `button_state`); the rest is a configured role list, run in the order Liam picks from the sheets.
- Target size per asset = 2.5 x the vanilla pixel size, on both axes, rounded to an integer. Vanilla UI art is authored for 1080p
  layouts; check that on a sample and write what you find in the report. An asset that is already at or above its target, or that
  would end up under 2x, is skipped with a stated reason.
- Method: ML upscale by an integer factor (2x or 4x model, chosen per role by a side by side on a fixed sample), then Lanczos resample
  to the exact target. Models are pinned by name, source URL and sha256, fetched by a committed tool into the work folder (never
  committed); the licence is recorded next to the pin.
- Alpha never goes through the model: resample it per channel with Lanczos, and keep it binary where the vanilla alpha is a binary
  cut-out. Dilate RGB under A = 0 before the model so no dark or light fringes appear.
- Mipmaps: full chain, box filter in linear light for RGB, plain box for alpha. Output keeps the vanilla format family (DXT1, DXT5,
  uncompressed) with the vanilla DDS header fields except size and mip count. For TGA sources, check whether the engine loads DDS in
  that place; if not, write a TGA and say that the mip chain is built by the UI host.
- Determinism: the same inputs, model sha and settings give byte-identical outputs; pin device, precision and tile settings and record
  them in the manifest. Re-runs skip finished assets by input hash (resume).
- Packs: a movie-type pack named `ui_art_2x5_*`, never touching vanilla packs (D2), with a manifest; every entry sha-checked while
  copying and again after. The game folder is a deploy target: install only through the existing sha-checked sync.

## Deliverables
1. `upscale/core/` (game-agnostic: DDS read and write with mips, resample and alpha rules, tiled model runner, manifest, resumable
   batch, pack builder) and `upscale/napoleon/` (role list, size rule, model choice per role). Registered tools with headers and a
   `wsc upscale` verb (`plan`, `run`, `verify`, `sheets`, `pack`).
2. A documented, repeatable GPU environment for the PC outside the game's `data\` folder (see Empire's `pc_batch_env.md`; nothing
   installed system-wide), set up by a committed script and checked by an `env` command that prints GPU, torch and model sha. A CPU
   path exists for the host tests.
3. `verify` per asset: exact target size, mip count and format as stated, alpha coverage within a tolerance of vanilla at each mip, no
   NaN or flat output, sha matches the manifest. Failing assets are listed, never silently kept.
4. The `assets` registry: `upscale_method` (model, factor, resample) and `upscale_status` (`pending`, `done`, `skipped:<reason>`,
   `failed:<reason>`) for every in-scope row, set by the tool and kept when the J7 indexer re-runs.
5. Contact sheets: before and after per role at the same display scale, plus 1:1 crops of a fixed set of hard cases (thin frames,
   glyph-like icons, flag cloth, portraits, cursors, soft alpha edges). Small versions committed, full size under `/extract`. Liam
   judges the look; do not claim it is approved.
6. Host tests (synthetic images, no GPU, no game): size rule, alpha rules, mip chain and coverage, DDS header round trip, manifest and
   resume, determinism of the CPU path, pack writer.

## PC test
The upscale runs in the work folder; any command that touches the game folder goes through the watcher.
a) environment check; b) a 200 asset sample across roles, timed, run twice to prove byte-identical output; c) the full run for the
first roles; d) pack, sync with sha checks, launch to the main menu with the pack installed and take a shot: it proves loading only,
because nothing uses the files until the RmlUi screens do. Whether the vanilla UI picks them up at another size is a recorded fact,
not a goal; e) uninstall and check the folder is byte-identical. Results go in a dated run report under `upscale/runs/` and as
`engine_facts` rows.

## Kill criteria
- No working GPU environment after 3 attempts: stop, report what failed and the CPU time per asset, propose a plan.
- No model with a licence that allows redistributing its outputs: stop, report, propose alternatives.
- On the sample, the model invents detail on more than a fifth of the hard cases: stop after the sheets, report, and propose a
  per-role Lanczos fallback instead of guessing.
- Any crash when the packed files load: stop, collect dumps, report; do not keep relaunching.

## Finish
Write `jobs/J36/report.md`: what exists, how to run it, counts per role and status, timings, the sheets, deviations from this brief
and why, what moves to the core later, open questions. Then `wsc reg set jobs J36 status=review report=jobs/J36/report.md`.
