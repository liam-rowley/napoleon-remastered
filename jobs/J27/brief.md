# J27: Imposter and LOD distances

Phase 3, distances (PLAN section 5, phase 3 item 3; D1: "imposter and LOD distances pushed out"). Push the unit imposter (sprite) switch,
the unit mesh LOD, the ship rope/knot distances, the tree far distance, the grass range and the building LOD out in measured steps, through
the sites, tweakers and data routes J9 proved; every value is a numeric config key with a release value; a memory gate stops each family at
a set headroom below the 4 GB address space. Liam judges pop-in from fixed poses; the release values are the last step that passed every
gate and that Liam accepts.

Model: Opus, reason: engine reverse engineering where J9 left holes (the grass budget loop, the building scalers, the three unit-LOD
tweakers, the atlas budget loop), a core proxy change (a numeric patch value), and reading memory-pressure crashes (D15). Effort high.
Budget about 300 tool calls; at the cap, stop, commit, report what is left (cut line in "Order of work"). Subagents (D34) only for independent
read-only work. Waiting belongs to the harness: `job.sh`, ctl requests, `tools/perf_baseline.py measure` and the acceptance runner block or
run in the background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J27`; "The core": the numeric-patch feature is game-agnostic code in a separate `warscape-core`
  clone beside this one, on a branch, as a pull request with host tests, then a tag that Liam merges and sets, then the pin bump here; "Exe
  stays vanilla"). Read `docs/DECISIONS.md` (D2, D14, D15, D26, D38, D40), `docs/plans/PLAN.md` phase 3 items 1 and 3, `proxy/README.md`
  ("Runtime patch engine", "Adding a site"), `harness/README.md`, `perf/budgets.md`.
- Reports to read: `jobs/J9/report.md` (routes, open questions "J27", deviations; the proofs and what they did not cover), `jobs/J23/report.md`
  (the baseline, the budgets, the noise rules, `tools/perf_baseline.py`), `jobs/J28/report.md` ("How the core PR waited on Liam": the
  model for this job's core PR), `jobs/J44/report.md` (scenes, poses, settle) and `jobs/J46/brief.md` (the large battles you do not wait for).
- **The routes table is the starting point**: `discovery/napoleon/engine_sites_routes.md` (stock values, encodings, places, proof runs).
  Rows to turn into configured values: `unit_lod.override_default`, `unit_lod.imposter_distance_default`, `unit_lod.large_imposter_distance_default`,
  `sprite.page_q0..q3`, `ship_lod.rope_distance_default`, `ship_lod.rope_distance_fadeout_default`, `ship_lod.knot_distance_default`,
  `trees.far_q1..q3` and `trees.far_other`, `grass.grid_q3`, `grass.grid_q4`. Their proof keys `gfx.unit_lod_proof`, `gfx.sprite_page_proof`,
  `gfx.ship_lod_proof`, `gfx.tree_lod_proof`, `gfx.grass_proof` are owned by this job and are replaced, not kept (see Deliverables 2).
  Facts: `napoleon.lod.*`, `napoleon.sprite.*`, `napoleon.shadow.unit_lod`, `napoleon.exe.options_object`, `napoleon.tweakers.table`,
  `napoleon.perf.*`. Search before writing: `python3 core/wsc.py find lod sprite imposter distance grass tree rope perf_baseline`.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there; check every fact again on Napoleon): `docs/graphics/GRAPHICS_NOTES.md`
  "Configurable graphics keys" and the imposter section, `docs/learnings/LEARNINGS_ENGINE.md` entry "Configurable sprites, animation, water,
  sky (gfxcfg ...)", `rml_mod/data/exe_patches.json` (the Empire LOD and sprite keys and the values Empire shipped).
- Other jobs touching the same files: J24 (shadows) and J26 write to the same proxy tables and `config_keys`; rebase on `main` before the
  pull request. J46 (queued) adds the large scenes; J59 re-runs the baseline on them.

## Target facts
From J9 (2026-11-01, `harness/runs/20261101_j9pc`) and J23 (`harness/runs/20261101_j23pc`); each is checked again in a run here before it is relied on.
- `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`; DLL, DXVK 3.1.1 stock, RTX 4090, headless (windowed on the virtual display).
- **Stock values by route:** unit imposter switch 100 m at `gfx_unit_quality` 3 (`LARGE_IMPOSTER_DISTANCE` default 200, `IMPOSTER_DISTANCE`
  default 100), imposter atlas 2048 (cell 1024; 1024 at texture quality 0), tree far 100 / 150 / 200 m at tree quality 1 / 2 / 3 and 50 m at 0
  and 4, grass grid N 5 (80 m), rope 200 / fade 150 / knot 50 m, mast 250 m (no observable effect), building LOD in db
  `warscape_rigid_lod_range` (600 / 600-1200 / 200-400-750 / 200-400-750-1500 m), unit mesh LOD in db `warscape_animated_lod` (per mesh, e.g.
  15 / 40 / 50 m), ship model LOD in db `warscape_naval_lod` (26 rows, all 0).
- **Encoding:** the tweaker and tree sites are float imm32 (one place each; trees one place per quality case); the grass sites are int32 data
  in `.rdata`; the unit LOD route is `ENTITY_LOD_OVERRIDE` on (one byte) plus the tweaker defaults. Tweaker defaults take effect because the
  proxy patches in DllMain, before the exe's CRT runs the static initialisers.
- **The unit LOD route replaces the per-quality table with five tweaker values at every quality** (J9 open question): with the override on,
  `LARGE_IMPOSTER_DISTANCE`, `IMPOSTER_DISTANCE`, `NO_VARIANT_DISTANCE`, `SHARED_POSE_DISTANCE` and `FEATHERED_SHARED_POSE_RANGE` come from
  their tweaker defaults, and only the first two have rows. Quality 3's table is 100, 100, 150, 50 or 70, 0 (fact `napoleon.lod.unit_distances`).
- **Budgets (PROPOSED, `perf/budgets.md`, not yet AGREED):** distances may add p50 1.0 ms and p99 2.0 ms at every size, 600 MB address space
  at the peak, 500 MB commit and 1024 MB VRAM over the baseline cell; the **address-space stop line is a peak of 3400 MB in any cell** (today's
  highest peak: 2096 MB in `hist_dresden`). Launch-to-launch noise is about 50 MB VA and 220 MB VRAM: read `va_used_mb` as well as the peak.
  The frame is CPU bound (draw calls), not pixel bound.
- The scenes that exist today (J44/J23): `land_small`, `siege_small`, `naval_small`, `naval_storm`, `hist_dresden` (largest land army, the
  address-space peak), `hist_nile` (large fleets), `campaign_start`. `land_40`, `land_large`, `naval_large` and a city siege do not exist until J46.

## Decisions already made for this job
- **Order of work** (so a cut by the budget costs the least; at the cap finish the item in hand, commit, and write the rest as open facts):
  0 the core change (numeric patch values) and the config keys; 1 unit imposter distance and unit LOD; 2 trees; 3 grass; 4 ship rope and knot;
  5 the imposter atlas; 6 building LOD; 7 the combined release candidate, its sheets and the acceptance run. Items 0, 1, 2, 3 and 7 are the
  minimum (units, trees and grass are what players see first); 4 and 5 may move to a follow-up if the cut line is reached; 6 is stretch
  (say so in the report).
- **Numeric patch values need a core change; do it first and keep it small.** Today the patch engine writes fixed `patch_bytes` gated by a
  boolean key (`core/proxy/src/patch_engine.h`, `patch_driver.cpp`), which is why J9 left the stepping to this job. Add to warscape-core a
  site option that takes its value from a numeric config key (float and int32 encodings; the site's `len` decides the width; int8 for the
  override byte stays a boolean key), with the pure encoding, clamping and "never below stock" logic in a header and host tests (round trip
  against stock bytes for every row of this job, out-of-range and NaN refused with a log line and the site left stock). Registered through
  the `engine_sites` schema (a `value_key` or equivalent, name yours to choose) and `core/proxy/tools/gen_tables.py`. Do not edit `core/` in
  this repo: a separate `warscape-core` clone, a pull request, Liam merges and tags, then the pin bump (J28's report, "How the core PR waited
  on Liam", is the model; run the acceptance on the PR head's content and say so). The imposter frame time (`value_offset`, core backlog B41)
  is not part of this job.
- **One configured value per family, never below stock.** The value written at every quality case of a family is `max(stock case value,
  configured)`, so a lower quality setting is never pulled in below stock and the stock quirks (tree far 50 m at quality 0 and 4) are raised
  to the configured value. Value 0 or an absent key means stock. A key is clamped to its tested ceiling (the last step that passed the
  gates), so a hand-edited ini cannot ask for an untested value. Keys: `gfx.dist.unit_imposter`, `gfx.dist.unit_mesh` (the three mesh
  distances scale together; the builder decides if they need separate keys and says why), `gfx.dist.tree_far`, `gfx.dist.grass_grid`,
  `gfx.dist.ship_rope` (the fade and knot follow at stock ratios, or separate keys if the sheets show they must), `gfx.dist.sprite_page`,
  `gfx.dist.building_scale`; each `config_keys` row has default (stock), release value, owner J27 and the step table it came from.
- **Unit LOD without surprises.** Before turning the override on, read the stock defaults of `NO_VARIANT_DISTANCE`, `SHARED_POSE_DISTANCE`
  and `FEATHERED_SHARED_POSE_RANGE` (`napoleon.tweakers.table`, `tweakers.tsv`) and compare them with quality 3's table. If they differ, add
  rows for them and write quality 3's values, so the override changes the imposter switch and nothing else by accident; record any quality
  whose table the override would change (1, 2, 0) and what players on it get. A moved imposter switch also moves the shadow casters (fact
  `napoleon.shadow.unit_lod`: 48 to 90 shadow-pass draws at 1000 m), so every unit step is measured with shadows as they are on `main`.
- **Grass is the memory and draw-call risk.** Range is N x 16 m and draws/prims scale with N squared (N 9: 97/117,958 to 213/260,694 at
  quality 3). The function at 0x11d0c90 steps the quality down when N squared x density is over a budget: read that budget from the code
  before choosing steps above N 9, and either keep N under it, or register the budget constant as a site, or record that the engine will
  step down and what that looks like. The ladder is N 5 (stock), 7, 9, 12, 16, stopped by the budget loop, the gates or Liam's sheets.
- **Building LOD: scalers first, db second.** J9 found the tweakers `lod_distance_scaler` 1.0 (reader 0x1146b20) and `rigid_lod_distance_scaler`
  10.0 (reader 0x1146e30) but did not prove them. Prove in one launch whether either scales the building switch distances (a pose with
  buildings between 600 and 1500 m, draw/prim counts); if yes, it is one float row and a key. If not, the route is the db
  `warscape_rigid_lod_range`, which is a data pack: use the play-pack route and install of J53 (`jobs/J53/report.md`, `upscale/pc/play.py`) only if it
  carries a db table without a harness change; otherwise stop item 6 and write what a db pack needs (a core kit role) as an open fact.
- **Steps are measured the J23 way.** Every step of every family is a launch with that family's key at that value, measured with
  `tools/perf_baseline.py measure` on the same sizes and scenes as the baseline (1080p and 4K at minimum; 1440p for the release candidate),
  3 passes, then `compare --run <dir> --feature distances`. A step passes only if all of: p50 and p99 deltas inside the budget, address-space
  peak under 3400 MB and its delta over the baseline cell inside 600 MB (cumulative across families in the release candidate, not per
  family), no crash, hang or watcher incident, and the start-up site check passes. Re-measure the baseline cells in the same sitting when a delta is
  within noise. The ladders start at: unit imposter 100 (stock), 150, 250, 400, 700, 1000 m; tree far 150 (stock q2), 250, 400, 600, 1000 m;
  rope 200 (stock), 400, 800, 1200 m; atlas 2048 (stock), 4096; building scale 1.0 (stock), 1.5, 2, 3. Cut or add steps when the numbers
  say so, and say why. Stop a family at the first failing step; the step before it is its ceiling.
- **Scenes.** Measure in every scene that exists (`land_small`, `siege_small`, `naval_small`, `naval_storm`, `hist_dresden`, `hist_nile`);
  `hist_dresden` and `hist_nile` stand in for "the 40-unit battle" and "a large naval battle" and `siege_small` for "the largest siege" until
  J46 lands. If `land_40`, `land_large`, `naval_large` or a city siege are on `main` when you run, measure them too and say they replace the
  stand-ins. Whatever is missing is listed as not covered, and J59 re-runs the release candidate on J46's rows and re-agrees the budgets (D38).
  A cell the baseline does not have is measured fresh, vanilla key off and key on, in the same sitting.
- **Fixed poses for Liam.** Pop-in is judged from a distance ladder: for each family a pose set on one subject (a unit block, a building row,
  a stand of trees, a patch of grass, a ship) with the camera at the stock switch distance, then at distances that straddle each step, from
  the scenes' fixed sky (the fixed-sky pack). Poses are registered by id in the scenarios registry like the J44 poses (`reg set scenarios`),
  shots by `ctl.py shot` at the settled pose. For each family produce a sheet: stock against the release candidate at the same pose, with
  the draw and prim counts printed, plus a dolly strip (the same path shot at 6 to 8 camera distances, stock and candidate side by side) so
  the pop is visible. Search the tools registry for the sheet builder to extend before writing one. Sheets are committed small (JPEG, under
  about 5 MB in all); full-size shots stay in the state folder with sha256 in the run README. Liam looks at the sheets; nothing in this job
  claims his approval, and the release values are written as release only after his judgement (see Finish).
- **Rule 79 applies**: the branch changes `proxy/napoleon/generated/` and the pin, so it needs 20 consecutive acceptance passes on its final
  DLL build id, run for this branch. Make the DLL changes in as few builds as you can: every rebuild after the acceptance run restarts it.
- Out of scope: shadow resolution, fit and cascades (J24, J25, J26), the imposter frame time (B41), the mast distance (no observable
  effect), flag sizes, tree near distance, texture or model replacement, anything in `core/` in this repo, any change to the render path.

## Deliverables
1. **The core pull request**: the numeric patch value (pure logic in a header, `engine_sites` schema field, `gen_tables.py`, the patch driver,
   host tests including failing fixtures), a core proxy docs paragraph, then the tag and the pin bump here.
2. **Sites and keys here**: the J9 proof rows for this job's families rewritten to take their value from the numeric keys (anchors and stock
   bytes unchanged; rows added for the three unit mesh tweakers and, if proven, the two building scalers); the `gfx.*_proof` keys removed or
   made aliases with no effect (say which, and update `registries/config_keys.jsonl` and the descriptions that name them); the `gfx.dist.*`
   keys with default, release value, owner and ceiling; the generated tables and the shipped ini current (`python3 core/proxy/tools/gen_tables.py`).
3. **The step tables**: per family, every step with its key value, the scenes and sizes measured, p50 / p99 against the baseline cell, VA
   used and peak, commit, VRAM, load time, draw and prim counts at the pose, and the verdict (pass, fail, with the reason); the ceiling per
   family. In the run README as generated tables (extend `perf_baseline.py` rather than writing a second tool) and a summary in the report.
4. **The memory gate**: a table of peak and used address space for the release candidate in every scene and size against 3400 MB, the
   cumulative delta over the baseline, and the first step of each family where the gate or the budget fails (if any). One measurement of the
   whole candidate at the highest peak scene with the caches warm and again after a second load in the same process (warm reset), since the
   process peak is since launch. If the 3400 MB line is too low or too high by the numbers (allocation failures start earlier, or much
   later), say so with evidence and propose the number; Liam agrees it.
5. **The release candidate**: all families at their ceilings (or the cut family's stock), one `gfx.dist.*` value set, measured in every scene at
   1080p, 1440p and 4K, compared with `perf/budgets.json` `distances`, with the combined sheets and dolly strips ready for Liam.
6. **The proofs that J9 did not cover**: the grass budget loop result, the building scalers, the three mesh tweakers against quality 3's
   table, what the override does at unit quality 0 to 2, and what a larger atlas costs in load time, commit and VA at 4096 (DXT1 about 8 MB
   per J9) with the imposters actually used (the atlas matters only while imposters are drawn: with the switch far out, say whether the larger
   atlas still earns anything and recommend `gfx.dist.sprite_page` accordingly).
7. **Facts and tools**: `engine_facts` rows (each with date and run id, or open with an owner) for every family's ceiling, the grass budget,
   the scalers, the override's effect per quality, the memory behaviour and anything refuted; `tools` rows with headers for new scripts.
8. **The acceptance run**: the 20 passes in a row on the final build with the release candidate's keys in the profile and with the keys at
   stock (idle cost must not move a shot or a load time past the baseline thresholds), in the background inside one call.

## PC test
Unattended and headless through the watcher; Liam is not needed to run it. Kits go over by `pc_deploy.py`, sha-checked; `dev.skip_intro=1`.
Run folder `harness/runs/<date>_j27pc/` with a README (run ids, build, profile, one line per step and the generated tables); raw cells
committed if small, otherwise in `<state>\_scratch\J27\` with sha256 in the README. Order inside the sitting:
- a) Idle check: the build with every `gfx.dist.*` at stock; the start-up site check passes; `land_small` matches the acceptance baseline shot
  and `perf_baseline.py` reproduces the baseline cell (the J23 smoke).
- b) One launch per family with its key on at one non-stock value (the core feature's first live proof: log shows the written bytes), then the
  ladders, one family at a time, families never combined until item 7.
- c) The J9-uncovered proofs (deliverable 6), the pose sets and sheets, then the release candidate in all scenes and sizes.
- d) The 20-pass run (deliverable 8). e) Uninstall; the game folder is byte-identical to the pre-install snapshot, settings untouched (J44 step f).
No Liam sitting. His pop-in judgement is on the committed sheets after the job is in review.

## Kill criteria
- A family's first non-stock step crashes the game or hangs: read the WER dump and the proxy log once, record it, drop to the previous step
  (stock if none). A second crash in the same family stops that family; do not relaunch in a loop.
- A site's anchor or stock bytes do not match in the running process: stop writing that site, keep the row out, record an open fact.
- The numeric-patch core change cannot pass its host tests and a live one-site proof after about 40 calls: stop, report, and propose
  fixed-value steps as boolean keys (each step one `patch_bytes` set) as the fallback; do not hand-roll a proxy-side patch in this repo.
- The address-space peak reaches 3400 MB, or an allocation or resource failure appears in the log, in any cell: that step fails, the family's
  ceiling is the step before, and no larger step is tried in any other family on top of it until the report says what was seen.
- The release candidate's idle frame (all keys at stock) moves a baseline shot or load time past the thresholds: stop and fix before anything else.
- The 20-pass run fails twice for a cause in this job's code: stop and report; do not keep re-running. A failure from the PC or the display is
  the watcher's: report it with the ledger lines.
- Any write into game memory beyond the sites' own bytes, a write into the game folder outside a deploy, or a change to `core/` in this repo
  would be needed: stop and ask.
- Over about 300 tool calls: stop, commit, report what is left.

## Open questions (settle in the report; the first two are Liam's)
- **Which scenes count as "the 40-unit battle", "the largest siege" and "a large naval battle" today?** Recommended: `hist_dresden`,
  `siege_small` and `hist_nile` as stand-ins, with `land_40`, `land_large`, `naval_large` and a city siege added if J46 is on `main` when the
  job runs, and J59 re-running the release candidate on J46's rows (D38). Alternative: add J46 to this job's `depends_on` and wait for it.
- **Are the proposed budgets and the 3400 MB stop line agreed?** `perf/budgets.json` still says PROPOSED. Recommended: build against them
  as proposed and report the real headroom; Liam agrees or changes the numbers with the sheets in front of him.
- Does the player-facing quality setting still matter once a distance key is set (this brief: the configured value is a floor over every
  quality case)? Recommended as written; the alternative is one value per quality case, which needs more keys and more steps.
- Should lower unit qualities (0 to 2) get the override at all? Recommended: yes, the key applies at every quality; the report names what
  the override changes there and Liam can ask for a quality-3-only route.

## Finish
Write `jobs/J27/report.md`: what was built (the core PR and how it waited on Liam, rows, keys, tools), the runs with ids, the step tables and
the per-family ceilings, the memory gate table, the release candidate and its sheets (paths) for Liam, the answers to the J9 open questions
for J27, deviations from this brief and why, what was cut and what J59 must re-run, and open questions. The release values in
`config_keys` are the candidate's until Liam says otherwise: the report says plainly that his pop-in judgement is pending, and a review
that finds it not yet given sends the job to a fix round with his answer, not a merge. Then
`wsc reg set jobs J27 status=review report=jobs/J27/report.md`.
