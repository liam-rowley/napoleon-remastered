# J24: Shadow map resolution and fit

Phase 3, job 2 (PLAN section 5, phase 3 item 2). Empire's route re-found on `Napoleon.exe`: a larger shadow map (stepped up to 8K), the fit
fix for shadows that collapse when the view lines up with the sun, and better filtering where a route exists, all through runtime engine
sites behind config keys, never an exe edit (D2). Every step is measured against the J23 baseline and the shadow budget in
`perf/budgets.md`; before and after shots at fixed poses go to Liam. This job is also the fallback if cascades fail (J25 and J26 build on
its sites and keys).

Model: Opus, reason: reverse engineering on `Napoleon.exe` (the per-frame shadow fit is not located yet), a proxy DLL change and runtime patches
proven by capture (D15). Effort high. Budget about 250 tool calls; at the cap, stop, commit, report what is left. Subagents (D34) only for
independent read-only work, for example the static search for the fit functions while a PC run is in the background. Waiting belongs to the
harness: `job.sh`, ctl requests, `perf_baseline.py measure` and the acceptance runner block or run in the background inside one call; never
poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J24`; "Exe stays vanilla", "Never run git in a game folder"). Read `docs/DECISIONS.md` (D2, D12, D14, D15, D31, D34,
  D38), `docs/plans/PLAN.md` phase 3 items 1 and 2, `proxy/README.md` ("Frame capture", the engine-sites paragraphs, "Adding a site"), `harness/README.md`.
- Reports to read, not their briefs: `jobs/J8/report.md` (deliverables 4 to 6 and the Fix round: shadow pass, the view-angle collapse, the hardware path
  not captured), `jobs/J9/report.md` (the routes table, "8K shadows", Open questions: J24), `jobs/J23/report.md` ("Budgets", "Open questions: J24, J26, J27"),
  and the J8 and J9 review rounds for what was challenged. Do not reread the briefs.
- Read first in the repo: `discovery/napoleon/engine_sites_routes.md` (the shadow rows, stock values, encodings), `discovery/napoleon/frame_anatomy.md`
  ("The shadow pass", "Shadow texel density"), `perf/budgets.md` (the shadows row: 1.0 ms p50, 1.5 ms p99, 50 MB VA, 512 MB VRAM, PROPOSED) and `perf/baseline.json`.
- Search before writing: `python3 core/wsc.py find shadow sweep farz fit crop warp perf density`. Starting facts: `napoleon.shadow.size_route`, `.format_route`,
  `.fit_code` (open, owner J24), `.view_angle`, `.hardware_path` (open, owner J24), `.map`, `.registers`, `.isolable`, `.unit_lod`. Starting rows (all `kind=patch`,
  verified 2026-11-01, run `20261101_j9pc`): `shadow.map_size_q34` (RVA 0xd86983, `mov ebx, 0x800`), `shadow.far_cap_q3` (0xd86973, 500.0 m), `shadow.light_sweep`
  (0xd276a6, -75.0 m), with proof keys `gfx.shadow_proof` and `gfx.shadow_sweep_proof` (default off) that this job replaces.
- Tools to reuse, not rewrite: the proxy's `capture <name> [frames]` ctl request (frame capture, `dev.capture`, sent through `job.sh ctl`), `discovery/core/shader_catalog.py` (`import`, `density` and the generated
  texel-density table are the one owner of the fit metric: J8 review 1, finding 4), `tools/perf_baseline.py` (`measure`, `compare --feature shadows`),
  `ctl.py cam` / `shot` / `perf` / `scene`, the RE kit `discovery/core/x86re.py` and `exe_strings.py` (`find`; the debug property names of the fit tunables are at 0x1468a50).
- Evidence in `empire-remastered` (read-only: never edit, commit or push there): `docs/graphics/SHADOW_FIT_UNITS.md` (the per-frame fit steps, the crop and warp flags, the
  `crop_behind_full` fix, the 250 m floor as a runtime setting) and `docs/graphics/GRAPHICS_NOTES.md` (shadow sections). Port the method, then check every address and every
  claim again on Napoleon: Napoleon's constructor fields are Empire's shifted by +0x14, nothing else is assumed.

## Decisions already made for this job
- **Scope is D12's first half only:** resolution, fit and filtering. Cascades are J25 and J26; this job builds nothing a cascade needs except sites, keys and measurements they can reuse.
  Imposter and LOD distances are J27 (the unit LOD switch also moves what casts a shadow: record what you see, do not tune it). No receiving-shader replacement here: the
  proxy has no shader-swap route, building one is J26's work if the cascades go ahead.
- **Everything is a runtime site and a config key.** Each patch is an `engine_sites` row with anchor and stock bytes and a dated run id, each value a `config_keys` row (owner
  `J24`, default and release value, what it does); the proof keys `gfx.shadow_proof` and `gfx.shadow_sweep_proof` are replaced, not kept. With every key at its default the
  exe in memory is stock: the start-up check reports "key off", nothing is written.
- **Configured values (route).** Today a patch row writes fixed `patch_bytes` behind a bool key; J9 left "any proxy feature that writes a configured number" to this job
  and J27 needs the same. The adapter struct (`core/proxy/src/adapter.h`) has no hook after the patch plan, so a numeric key is a core change (a warscape-core PR and tag,
  made in a separate `warscape-core` clone, Liam merges it; `core/docs/CONSUMING.md`). Conservative reading: **measure with the route that needs no core change** (one row
  per step at the same RVA, each gated by its own bool key, only if `core/proxy/tools/gen_tables.py` and the patch plan accept rows that share an RVA while only one is on;
  check this in the first ten calls and record the answer), and **file the numeric-key core change as a warscape-core backlog row or PR** (an int `config_keys` key
  supplies the immediate, int or float, for a `patch` row; the stock check is unchanged) for Liam. If the ladder is accepted by Liam as the shipped form, no core change is needed.
- **Measure first, tune second.** The ladder for the map edge is 2048 (stock), 4096, 8192 at `gfx_shadow_quality` 3 (Liam's prefs; R16F), one change at a time against a control in the
  same sitting; the distance cap (`shadow.far_cap_q3`, 500 -> 1000 m lifts the fitted farz from 250.5 to 473.3: J9) and the sweep are separate steps after the edge. The one
  `mov ebx, 0x800` serves quality 3 and 4; quality 4 adds R32F, so 8192 at quality 4 is double the memory (arithmetic to check: 8192 R16F + D24X8 is about 400 MB of VRAM,
  8192 R32F + D24X8 about 540 MB, against a 512 MB budget). Qualities 1 and 2 have their own immediates (unregistered); register them only if the measurement shows they matter.
- **The fit problem is the headline, not the size.** J8 measured (fact `napoleon.shadow.view_angle`) texels per metre at 20/60/140 m of 20.9/12.8/6.6 side-on to the sun and
  5.2/5.2/5.1 with the sun behind the camera, at the same map size. A bigger map multiplies both; the fix is a fit that does not degenerate when view and light line up.
  Empire's cause was a perspective (trapezoidal) warp whose eye sits behind the camera plus a caster crop that is thrown away; Napoleon's collapse looks like the warp degenerating,
  not yet proven to be the same code. Candidates, each tried as a key and measured with `shader_catalog.py density` on the J8 yaw sweep (`y_0 .. y_315`, camera (-0.08, 59.02, 446.14),
  pitch -25, 45 degree steps, run `20261101_j8pc`): the warp mode ([renderer+0x5c], Empire +0x48: plain orthographic fit), the crop flags ([+0x64..0x67], `01 01 01 01`; the
  "crop behind eye resets to full" flag is the third), the snap flag ([+0x6c]), the min range ([+0x84], 50) and max range ([+0x7c], 400), the height factor ([+0x98], 100), the sweep ([+0x9c]).
  These are constructor stores (J9 `napoleon.shadow.fit_code`); the per-frame functions that read them are not located: find them from the field offsets (readers of `[r+0x5c]`,
  `[r+0x66]`, farz) with the RE kit before trusting an Empire address, and record each as a fact. The per-frame code may need a hook, not a patch: a hook is a new `engine_sites`
  row of `kind=hook`, behind the same guard; ask first if it needs more than a flag or a constant.
- **Filtering.** The stock receivers filter in the pixel shader (software path: linear depth in a colour target). Three things to settle with evidence, none by shader replacement:
  (1) the stock kernel from the captured receiver disassembly (`discovery/napoleon/shader_catalog.json`): taps and radius in texels or metres, and so what a larger map does to the blur;
  (2) the NVIDIA hardware path (`gfx_hardware_shadows`, a depth-texture map with hardware PCF; open fact `napoleon.shadow.hardware_path`): capture it properly. The prefs file holds the
  key twice and the watcher overlay sets only the first (core backlog B30), so a profile cannot flip it; find a route that does (the options byte `+0x69d09` through a site, or a
  prefs edit made by `pc_deploy.py` with the game closed, prefs restored byte for byte), and if neither works in about 15 calls, record it open and stop on this item;
  (3) whether 8K alone shimmers or aliases at the fixed poses (shots). If filtering needs a shader change, write that as an open fact for J26 and stop.
- **Measure against what exists.** "The 40-unit battle" and the city siege are J46's rows (`land_40`, J46 is queued) and are not built here. Measure in the J23 cells: `land_small` (deploy and
  `--deploy end`), `siege_small`, `hist_dresden` (the heaviest cell: 4.47 ms p50, VA peak 2096 MB) at 1080p and 4K, and, if `land_40` or a city siege row is on `main` when you run, also those.
  Follow J23's advice: `perf_baseline.py measure` on your build (same sizes and scenes), `compare --run <dir> --feature shadows`, read `va_used_mb` as well as the peak, and re-measure the
  baseline cells in the same sitting when a delta is close to the launch-to-launch noise (VA about 50 MB, VRAM about 250 MB). The frame is CPU-bound: watch draw calls (the sweep adds casters,
  48 -> 53 draws at -400).
- **Shots for Liam.** Before and after at fixed poses, committed as one contact sheet (JPEG, a few MB at most) per scene in the run folder, not 4K PNGs. The J8 yaw sweep showed open ground, so
  the poses must have casters near the camera: take them from the deployed armies in `land_small` (a low camera among the lines with the sun behind it, side-on, and 45 degrees), a siege pose
  with the wall and units in view, and one distant pose. Poses are `ctl.py cam` poses (x y z yaw pitch) written in the run README (the same ones before and after; a readback outside tolerance is said, not hidden).
  Compare map sizes and fit settings at identical poses; label each image with the key values.
- **Release values** are proposals for Liam: the smallest map and fit settings that give the look at the budget. State them with the numbers; do not ship a value that breaches the budget. A budget breach
  alone is not a veto: report it and let Liam trade it.
- **Rule 79 applies.** This job changes DLL inputs (the generated site and key tables are inputs): 20 consecutive acceptance passes on the final build, with the new keys at their release values
  (`acceptance.py streak --build <id> --watcher <version>`). Idle check: with every new key off, one pass must match the baseline shots and load times.
- **Out of scope:** cascades (J25, J26), receiving-shader replacement, other render targets (water, the campaign overlay: PLAN section 7 candidates), unit/LOD/imposter distances (J27), the
  scenario library (J46), any change to `core/` in this repo, the acceptance baseline files, `empire-remastered`.

## Deliverables
1. **Sites and keys.** Rows in `engine_sites` for the map edge, the distance cap (all four qualities only if measured useful), the sweep, and each fit control that works (flags, ranges, warp
   mode), each with anchor bytes that carry no relocated dword, `stock_bytes`, `verified` (date and run id); `config_keys` rows for every value (default, release value, owner J24); the shipped
   ini (generated) carries them; the proof rows and keys replaced. `proxy/README.md` shadow paragraph updated; `discovery/napoleon/engine_sites_routes.md` rows updated (the one owner of
   routes, J9).
2. **The map-size ladder** 2048 / 4096 / 8192 at quality 3 (and quality 4 at the largest size for the R32F cost): frame p50 and p99, draw calls, `va_used_mb`, VA peak, commit and VRAM per scene
   at 1080p and 4K against the J23 baseline, `compare --feature shadows` output, and the load time (a larger map is created once per battle). Does DXVK create 8192 on this GPU and driver
   (D3D9 caps, creation result in `dxvk.log`), and what does the process do on a smaller card (record the VRAM figure; no other GPU is tested: D13)?
3. **The fit fix.** The per-frame fit code located (facts with addresses and the readers of each constructor field), each candidate control tried and measured with `shader_catalog.py density`
   on the yaw sweep at 20, 60 and 140 m, a chosen combination, and the proposed target met or not: **worst-yaw density at 20 m at least doubles against stock at the same map size, and
   best-to-worst yaw at 20 m is within a factor of 2 (stock about 4)**. Say which controls cost shadows elsewhere (clipped casters at the map edge, a cut-off line, missing shadows from units on the
   sun side) with captures or shots, as Empire's risk note did for `crop_behind_full`.
4. **Filtering.** The three items above answered with captures, or left open with the exact blocker and an owner.
5. **Shots.** The contact sheets above and the pose table in the run README; no judgement is made for Liam.
6. **Facts and tools.** `engine_facts` rows (date and run id, or open with an owner) for each located fit function, each field's reader, each key's measured effect, the DXVK 8192 result, the hardware
   path and the kernel; update `napoleon.shadow.fit_code`, `.hardware_path`, `.size_route`, `.view_angle`; `tools` rows with headers for anything new (a driver script under `tools/` rather than
   `harness/` where possible, to keep rule 79's scope to the DLL work that needs it). `python3 core/wsc.py gates` green.
7. **Core backlog.** The numeric-key change (and `value_offset`, B41, if a site needs it) written as a warscape-core backlog row or draft PR; B30 (prefs overlay duplicates) referenced if it blocks the hardware path.
8. **The acceptance run**: 20 passes in a row on the final build with the release values on, ledger lines committed; idle check with the keys off.

## PC test
All game launches through the watcher and `ctl.py`; the agent never starts `Napoleon.exe`. Take the lock with an owner name (`job.sh`), release it at the end. Kits go over by `pc_deploy.py`
(sha-checked, unique staged names); check `status` for a foreign lock first. Headless on the virtual display, as J23's cells; shots are headless shots. No sitting with Liam is needed: the shots are
reviewed afterwards from the contact sheets. Stop and ask if a step needs a visible window or admin.
a) Install the build with the new keys off: start-up log shows every row "key off" and all rows checked; one `land_small` pass matches the baseline (idle check).
b) The ladder at quality 3 (control, 4096, 8192), then quality 4 at 8192; `perf_baseline.py measure` per scene and size, `compare`.
c) Fit experiments on the yaw sweep: capture per setting (`capture`), `shader_catalog.py import` and `density`; one control changed at a time, each against the stock row of the same sitting.
d) The hardware path capture (item 4 (2)). e) The shots at the fixed poses, before and after, same session as the matching measurements.
f) The chosen release values at the three real scenes plus any J46 row; then the 20-pass run. g) Uninstall; the game folder is byte-identical to the pre-install snapshot, prefs back byte for byte
(J44 step f).
Typical cost: 3 to 5 hours of watcher time in the background, most of it the ladder and the 20 passes.

## Kill criteria
- The shadow fit's per-frame code cannot be located after about 40 calls of static search plus two capture-guided attempts: stop searching, ship resolution and the constants that did move the density
  (ranges, sweep, flags), record the rest as open facts, and say so in the report. Do not patch bytes that no capture shows doing anything.
- Any key combination crashes or hangs the game twice for the same cause (an 8192 target the driver refuses, a patch that breaks the fit): stop, collect WER dumps and the watcher's hang folder
  first, report; do not keep relaunching.
- The 8192 step breaches the shadows budget by more than 2x on p50 or p99 in `hist_dresden` or the siege: do not ship 8192; keep 4096 as the proposed release value and report both.
- The ladder shows no difference in the shadow map's sharpness at 4096 against 2048 in the shots at all poses (so the fit, not the size, is the whole story): finish the fit work, ship the cheaper size.
- The fit controls change the density only at the cost of visibly missing or clipped shadows at the poses, and no combination fixes the sun-behind case: stop, report with shots; the fallback is
  size and range only. Cascades (J25) are then the real fix.
- A needed change cannot be made without editing `core/` here or without a new core tag: finish with the no-core route (Deliverable 1), file the core change (Deliverable 7), do not edit `core/`.
- The 20-pass run fails twice for a cause in this job's code: stop and report; do not keep re-running.
- Over about 250 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J24/report.md`: what was built (rows, keys, route used for configured values, any core change filed), the ladder table with run ids and the budget comparison, the fit findings (functions,
fields, measured densities per yaw and distance before and after), filtering answers, the shots and where they are, the proposed release values, deviations from this brief and why, and open questions
for Liam, J25 and J27. Then `wsc reg set jobs J24 status=review report=jobs/J24/report.md`.

## Open questions (conservative reading taken; Liam may overrule before or during the build)
- **Configured numeric values need a core change or a ladder of fixed-value rows.** Recommend: measure on the ladder, file the numeric-key change in warscape-core (J27 needs it too), and ship whichever
  is merged by the time of the 20-pass run; one release value per setting is all a player needs. Liam decides whether to merge the core change.
- **Quality 3 and 4 share the size instruction.** 8192 at quality 4 is R32F and about 540 MB of VRAM. Recommend the release value is chosen for quality 3 (Liam's prefs) and the report states the quality 4 cost
  so Liam can decide whether to cap it (a cap would need the format site, `napoleon.shadow.format_route`).
- **No 40-unit battle exists** (J46 is queued, `land_40` not on `main`). Recommend `hist_dresden` and `siege_small` as the stand-ins now and J59 re-running the shadow cells on J46's rows (D38), not waiting for J46.
  If `land_40` is on `main` when the job starts, measure it too.
- **The shadow budget (1.0 ms p50, 1.5 ms p99, 512 MB VRAM) is PROPOSED, not agreed** (`perf/budgets.md`). The job reports against it; Liam may agree or change it, and may accept a breach for the look.
- **Hardware shadow path.** If the prefs duplicate (B30) blocks a clean capture, recommend leaving the hardware path open for the core fix rather than hand-editing prefs; filtering then waits for J26's receiving shaders.
- **Release default for the fit fix.** If a fit control helps one case and costs another (for example missing shadows from units on the sun side), recommend shipping it only if the worst case is better than stock
  at every pose; otherwise leave it off and leave the problem to cascades (J26).
