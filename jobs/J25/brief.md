# J25: Cascaded shadows spike

Phase 3, shadows, the spike before any cascade build (PLAN section 5, phase 3 item 2; D12). The engine draws one shadow map. J24 showed that no
control on that one map gets the best-to-worst yaw ratio at 20 m within 2: the sun-behind yaws follow farz and the extrusion, not the warp
(fact `napoleon.shadow.fit_controls`). This job answers one question with a working prototype. Can the shadow pass be drawn once per cascade, each
with its own light matrix, and can the receiving shaders be replaced so that each pixel picks and samples the right cascade? There are two
candidate routes: the proxy replays the pass's draws, or a hook calls the engine's own pass again. The prototype has two cascades and runs in
the 40-unit battle (J46's `land_40`). The job measures its cost against the cascade budget, settles what the blob shadows are and whether
cascades remove them, and ends with a go or no-go plus a design for J26. Nothing built here ships.

Model: Opus, reason: D3D9 device-path work in the 32-bit proxy (interception and replay of draw calls, render targets, shader-constant
bookkeeping), shader bytecode replacement, and static reverse engineering of the engine's shadow pass on `Napoleon.exe` (D15). Effort high. Budget about 220 tool
calls; at the cap, stop, commit, report what is left. Time-box: two working sessions, with at most about 5 hours of watcher time across at most two PC
sittings. At the time-box the job ends with whatever answer the evidence gives: no-go or not proven is a valid result. Subagents (D34) only for
independent read-only work, for example the static read of the shadow pass while the prototype builds. Waiting belongs to the harness: `job.sh`,
ctl requests and `perf_baseline.py measure` block or run in the background inside one call. Never poll with repeated calls.

PC: yes (needs_pc), headless through the watcher, unattended. Another job may hold the PC when this starts, so do the offline steps first (below).
Rule 79 is not expected to apply: this branch ships no DLL input (see "Nothing ships"). If it ends up shipping one, it needs 20 consecutive
acceptance passes on the final build.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J25`; "The core": **never edit `core/`**; "Exe stays vanilla"; "Never run git in a game folder"). Read
  `docs/DECISIONS.md` (D2, D12, D15, D30, D34, D38), `docs/plans/PLAN.md` phase 3 item 2, `docs/REVIEW.md` (Rule 79) and `proxy/README.md`
  ("Hooks", "Frame capture", "Runtime patch engine", "Headless").
- Reports to read, not their briefs: `jobs/J24/report.md` and `jobs/J24/review.md` (the fit code, the hardware path, the ladder, the
  same-sitting finding, the release proposal) and `jobs/J8/report.md` (deliverables 5 and 6, Open questions: J25, Fix round 1). Also read
  `jobs/J46/report.md` (the `land_40` row) and `perf/budgets.md` (the cascades row, Noise).
- Read in the repo: `discovery/napoleon/frame_anatomy.md` ("The shadow pass (J24, J25)", "Shadow texel density", the registers table) and
  `discovery/napoleon/shader_catalog.json` (every caster and receiver by hash, with fx source, technique, macros and CTAB). Read
  `discovery/napoleon/engine_sites_routes.md` (the shadow rows) and `harness/runs/20261103_j24pc/README.md` (the drivers, the shot poses,
  how keys were set with the game closed, the incidents).
- Search before writing: `python3 core/wsc.py find shadow cascade receiver caster capture density perf`.
- Facts to start from (re-check any you rely on):
  - `napoleon.shadow.isolable` (the pass is the first draw pass and one contiguous block: `SetRenderTarget(0, R16F|R32F map)`,
    `SetDepthStencilSurface(D24X8)`, `Clear(target|z, 0xffffffff, 1.0)`, the casters, then the next `SetRenderTarget`; no D3DPERF event);
  - `napoleon.shadow.map` and `.size_route` (sizes and formats per quality; the setup 0x11868f0; 8192 created by DXVK);
  - `napoleon.shadow.registers` (casters: `shadow_map_projection_matrix`, `linear_z_shadow_map_projection_matrix`, PS `shadow_map_slope_bias`;
    receivers: `shadow_projection_texture_transform_matrix`, `linear_z_shadow_projection_texture_transform_matrix`, `shadow_map_farz`,
    `shadow_map_inv_farz`, `shadow_map_far_fade`, `shadow_map_texture_size`, sampler at s0, s1 or s2; registers differ per shader);
  - `napoleon.shadow.fit_code` (the update 0x119ab50, renderer vtable slot 21; the shadow pass 0x114b440, slot 22, and its mode switch at
    0x114b473 to the orthographic builder 0x1150390 or the trapezoidal builder 0x1152530; the frustum-to-light-AABB 0x11552a0, called at 0x119aff3;
    the crop 0x1176b10; farz at [+0x82c] from the far clip [+0x7c]; light position = light direction x [+0x9c] at 0x119abf2);
  - `napoleon.shadow.fit_fields` (the 34 renderer fields, constructor 0x1127580, debug-property getter 0x117ad20);
  - `napoleon.shadow.kernel` (one fetch4 2x2 software PCF, footprint one texel; `USE_MULTI_TAP` off);
  - `napoleon.shadow.hardware_path` (NVIDIA branch under DXVK, 27 receivers not in the catalogue) and `napoleon.shadow.format_route`
    (the receivers' define is chosen at 0x11a7e60, renderer vtable slot 34);
  - `napoleon.shadow.unit_lod` and `napoleon.lod.unit_distances` (the imposter caster past the unit LOD switch, LOD function 0x756e80);
  - `napoleon.shadow.view_angle` (the sun-behind collapse);
  - `napoleon.shaders.runtime_compile` (the engine compiles its fx at runtime with D3DX 9.24.950.2656, and `shader_catalog.py fxmap`
    reproduces the bytecode byte for byte);
  - `napoleon.battle.camera_route` (exact camera position and target, 70.0 degree vertical fov);
  - `napoleon.battle.order_threads` (Present and the engine tick are one thread).
- Tools to reuse, not rewrite:
  - the proxy's `capture <name> [frames]` (`dev.capture`);
  - `discovery/core/shader_catalog.py` (`import`, `fxmap`, `density`: the one owner of the texel-density metric);
  - `tools/shadow_density.py`, `tools/shot_sheet.py`, `tools/perf_baseline.py` (`measure`, `compare --feature cascades`, `ladder`) and
    `tools/acceptance_summary.py`;
  - `ctl.py cam` / `shot` / `perf` / `scene`;
  - the RE kit `discovery/core/x86re.py` and `exe_strings.py`;
  - `core/proxy/tools/pc_deploy.py` (`set` with the game closed, as J24's `fit.sh`).
- Empire has no cascade evidence (its notes say "single shadow map (no cascades)"). Nothing is ported. `empire-remastered` stays read-only.

## Questions the builder answers first (before any prototype code; each answer is a fact or a run note)
1. **The pass in `land_40`.** Capture `land_40` at the deploy and turned poses on the current `main` build (no new code; `dev.capture=1`), then
   run `shader_catalog.py import`. Check that the shadow pass has the shape of `napoleon.shadow.isolable` there too. Record the caster draw
   count, every caster vertex-shader hash with its register for each of the two caster matrices, and every receiver: a shader whose CTAB holds
   `shadow_projection_texture_transform_matrix`, with fx, technique, shader model and draw count. List any caster or receiver not in the
   catalogue.
2. **Are the casters' buffers stable for the length of the pass?** Look for dynamic vertex or index buffers locked with DISCARD between two
   caster draws (the capture does not hook `Lock`), instancing streams (`FREQ`), and state blocks applied inside the pass (core B34: not
   captured). This decides between replaying after the pass and duplicating at each draw (below).
3. **Does 0x114b440 draw the casters itself?** The other possibility is that it only builds the matrices while the scene graph submits the
   draws elsewhere. Answer statically with `x86re.py`: what the call sets up (target, clear, matrix upload, the caster list), what it reads
   from the renderer object, and whether a second call in the same frame is safe (per-frame counters, caster lists, the crop state). This is
   the hook route's feasibility. About 30 calls; if it is not settled by then, record it as open and say so.
4. **The frame's light direction and camera**, where the proxy can read them before the shadow pass. The light direction is either the
   receivers' uploaded light-direction register of the previous frame (the sun is fixed in a battle) or the field behind 0x119abf2. The
   camera is J43's readback for the current frame, checked against the previous frame's `view_projection` upload.
5. **Room in the receivers.** For each receiver from question 1, from its CTAB and the fx:
   - are a free sampler slot and about 12 free constant registers available?
   - does a two-cascade pick fit the shader model's limits? ps_2_0 is 64 arithmetic and 32 texture instructions. Moving a ps_2_0 receiver to
     ps_3_0 needs a vs_3_0 vertex shader with it.
   - can the modified shader keep **every stock constant and sampler in its stock register**? The engine uploads by the registers of its own
     stock compile.
6. **What a "blob shadow" is here.** In the `land_40` captures, look for any draw that puts a round dark decal or sprite under units in the
   main pass, besides the imposter caster of `napoleon.shadow.unit_lod`. Name it (draw, shader, texture) or say there is none.

## The two routes, and which one is built
- **Route 1, proxy replay (built first).** A dev-only module in the device path recognises the pass: the first `SetRenderTarget` to the
  shadow map's texture, recognised at creation by its format and size from `napoleon.shadow.map`. For each caster draw it also draws into a
  second cascade target, with that cascade's caster matrices in the registers from question 1. It keeps a shadow copy of every register and
  state it overwrites and restores them before the engine's next call. The engine's state is never left changed. Variants, chosen by the
  answer to question 2 and then by cost:
  - (a) **inline duplication into a separate target**: correct even with dynamic buffers and unseen state blocks, but two target switches per
    caster draw (DXVK splits a render pass at each);
  - (b) **replay after the pass**: one target switch, only if question 2 shows the buffers are stable;
  - (c) **an atlas**: the engine's map created twice as wide, one viewport per cascade, so a switch is a viewport change. The stock receivers'
    uploaded matrix then needs a u scale and offset, so take (c) only if (a) or (b) breaches the budget.

  The engine culls casters against its own light volume, so each extra cascade must lie inside the engine's fitted volume. Check this, and count
  any caster that should be in a cascade but was culled.
- **Route 2, the engine's pass again through a hook.** This means a vtable hook on renderer slot 22 (0x114b440) that calls the original a
  second time with the near cascade's farz and far clip ([+0x82c], [+0x7c]) and the proxy's target. Its benefits: the engine's own culling,
  matrices and buffers for each cascade. Its risks: re-entrancy and a crash in engine code. It is answered statically (question 3).
  Prototype it only if route 1 fails a go criterion that route 2 would fix (caster coverage, culling), and only if question 3 says a second
  call is safe.
- **Cascade layout for the prototype.** Two cascades.
  - **Cascade 1 is the engine's own map**, untouched: its matrix, its warp, J24's fit.
  - **Cascade 0 is new:** a near cascade from the camera to a split distance, a stable orthographic fit (bounding sphere of the frustum slice,
    snapped to whole texels so it does not shimmer), the same size and format as the engine's map. Start with a split at 40 m and try 25 and
    60 m. It writes the same linear depth the receivers compare against.
  - A receiver left stock still samples the engine's map and looks as it does today, so a partial swap degrades to stock, not to a hole.
- **Receivers: bytecode swap by hash (built).** At `CreateVertexShader` and `CreatePixelShader` the proxy swaps the bytecode of each listed
  receiver for one compiled offline. The offline compile uses a modified copy of the shadow sampling fragment (see the Registry gaps
  section), the same D3DX build and the same macros, through `shader_catalog.py fxmap`'s compile path. The replacement:
  - picks cascade 0 when the pixel's cascade-0 uv is inside the map with a margin, else cascade 1;
  - blends across a band at the split, so no seam shows;
  - takes cascade 0's matrices and its sampler in free registers that the proxy binds when a swapped shader is set.
  - **Gate for each replacement:** a check that its CTAB keeps every stock name at the stock register and sampler (fail = no swap, logged).
    Swap the receivers that `land_40` draws in view at the two poses (terrain and unit meshes at least; trees, buildings and imposters if
    question 5 allows), and list the rest. Every receiver is J26's job.
  - The other receiver route is an fx override in a data pack, which the engine would compile at runtime: all receivers at once. It depends on
    the open fact `napoleon.files.loose_override` and on how packs load. It is weighed in the design for J26, not built here.
- **A debug view.** A dev key tints each pixel by its cascade. This is the proof that the pick works, and it goes in the shots.

## Decisions already made for this job
- **Nothing ships; the prototype lives outside this repo's DLL inputs.**
  - The prototype's C++ is core device-path code: the game adapter has no device hooks (`core/proxy/src/adapter.h`), and only the core installs
    hooks (`proxy/README.md` "Hooks"). Write it on a **local warscape-core branch `spike/J25-cascades` cut from tag v0.9.0** (this repo's pin), in a
    warscape-core clone beside this one.
  - Build it from a scratch clone of `job/J25` whose `core` submodule is checked out at the spike commit. That checkout is never committed;
    J8's captures and J24's 4096 kit were also "-dirty" builds. Its dev keys (`dev.cascade_proto`, `dev.cascade_tint`, split and size) are
    `config_keys` rows in that scratch checkout only.
  - Do not push the spike branch or open a pull request. The orchestrator decides whether to push it as a draft for the record.
  - Commit the prototype as a `git format-patch` series in the run folder, with the spike commit sha.
- **What `job/J25` may change:** `jobs/J25/`, the J25 row, `harness/runs/<run>/` (run evidence; rule 79 exempts `runs/` folders), `registries/engine_facts/`
  rows, `discovery/napoleon/frame_anatomy.md` (the shadow-pass section, the one owner of that topic) and `discovery/core/shader_catalog.py` if the
  density metric needs it (below). It may not change `proxy/`, `harness/` outside `runs/`, `core/` or its pin, `registries/engine_sites.jsonl` or
  `registries/config_keys.jsonl`. Engine addresses this job finds go into `engine_facts` rows; J26 makes them sites.
- **The density metric has one owner.** Cascade 0's matrix is the proxy's, and swapped receivers have new hashes. Extend `shader_catalog.py
  density` (or `tools/shadow_density.py`) to take the cascade matrix that the prototype logs or uploads. Do not write a second metric. Add a
  host test for the new input.
- **Measure cost against a same-sitting control** (J24: p99 noise between sittings is about 1.5 ms, the size of the shadows budget).
  - Use the same kit for both arms, with the prototype key off and on, set with the game closed (`pc_deploy.py set`).
  - Interleave the arms (control, prototype, control, prototype), at least 2 blocks of 2 repeats each, with `perf_baseline.py measure` on
    `land_40` (deploy and turned) at 1080p and 4K, plus `hist_dresden` (the heaviest cell) at 1080p.
  - Report the p50 and p99 deltas as medians over the blocks, with the spread. Read `va_used_mb` as well as the peak, plus VRAM and draw calls.
  - `compare --feature cascades` against `perf/baseline.json` is printed but does not decide: `land_40` is not in the baseline (J59), and the
    baseline is another sitting.
  - Both arms run with J24's proposed release values on (`gfx.shadow_map_large`, `gfx.shadow_height_cutoff`, `gfx.shadow_extrusion`) because
    that is what would ship under cascades. The quality sweep also runs at stock 2048, so it compares with J8 and J24.
- **The budget is the cascades row of `perf/budgets.md`** (PROPOSED, J23): p50 +1.5 ms, p99 +2.0 ms, VA peak +50 MB, commit +50 MB, VRAM +768 MB,
  as a delta against the control. It is not agreed; report against it and let Liam trade.
- **Quality is measured with the J8/J24 method:** the yaw sweep on `land_small` (camera (-0.08, 59.02, 446.14), pitch -25, yaws 0 to 315 in
  45 degree steps), texels per metre at 20, 60 and 140 m, one capture per yaw. The shots are J24's poses p1..p6 and s1 (run README) plus the
  two `land_40` poses, all at identical poses before and after, with the cascade tint as a third column.
- **Out of scope:**
  - three or more cascades (cost is extrapolated from two);
  - swapping every receiver, the hardware path's 27 receivers, and softer filtering: J26;
  - unit LOD or imposter distances: J27;
  - any edit to `core/` here, `empire-remastered`, or the acceptance baseline.

## Deliverables
1. **Answers to questions 1 to 6** as facts (date and run id, or open with an owner). Suggested ids:
   - `napoleon.shadow.casters` (land_40 caster set and registers);
   - `napoleon.shadow.caster_buffers` (question 2);
   - `napoleon.shadow.pass_call` (question 3: 0x114b440's shape and re-entrancy);
   - `napoleon.shadow.receivers` (the receiver set and its room);
   - `napoleon.shadow.blob` (question 6 and the blob answer).
   - Update `napoleon.shadow.isolable` with the `land_40` result.
2. **The prototype**: route 1 (the variant used, and why), the receiver swap with its CTAB gate, the tint. It is committed as the patch series
   and spike sha. Host tests for the parts that can be tested without the game (the pass recogniser on a recorded call sequence, the cascade fit
   and texel snap, the CTAB check) are on the spike branch and run with `build.sh --docker all` in the scratch checkout.
3. **Correctness evidence**:
   - caster coverage per frame: caster draws seen, duplicated, skipped for an unknown shader (must be 0), culled-but-needed;
   - receivers swapped per frame, against receivers drawn;
   - no D3D error in `dxvk.log`, no crash, and no hang across the sittings;
   - the tint shots showing the split at the configured distance, with no seam at the blend band;
   - stock look outside cascade 0: a swapped receiver beyond the split compares with the control shot within the acceptance thresholds.
4. **Quality**: the yaw-sweep density table for cascade 0 and cascade 1, against stock and J24's best 2048 combination (cutoff + extrusion:
   worst 7.86, ratio 3.37), at the three split distances.
5. **Cost**: the interleaved table above (`perf_baseline.py ladder` output) with the per-cascade cost in draws and ms, and an extrapolation to
   3 and 4 cascades and to `hist_dresden`.
6. **Blob shadows**: why they are drawn (what draws them and when: unit LOD switch distance, imposter caster, the sun-behind collapse of near
   mesh shadows, any decal from question 6), shown in shots at the same poses with and without cascade 0. For each kind, say whether cascades
   remove it, what else would (for example J27's unit LOD distance: J9 saw 90 shadow draws instead of 48 with the imposter switch at 1000 m),
   and what that costs.
7. **The go/no-go** against the criteria below, criterion by criterion, with run ids.
8. **The design for J26** (in the report, its own heading):
   - route and variant;
   - cascade count and the split scheme, with config keys and proposed release values;
   - map size and format per cascade, and the VRAM;
   - whether the engine's map stays as the last cascade (and with which J24 fit values);
   - the receiver route (bytecode swap table, fx pack override, or both), with every receiver by fx and technique;
   - the core job and the napoleon half: the device-path cascade module, CTAB reader and shader swap in a `W<n>` core job; the hash and
     register tables and engine addresses in the adapter;
   - the expected cost and the risks (hardware path, ps_2_0 receivers, culling);
   - J26's own kill criteria.

## Go / no-go for J26
**Go** only if every one of these holds on the prototype (two cascades, `land_40` plus the `land_small` sweep):
1. **Isolable and complete:** every caster draw of the pass is drawn into cascade 0 in every captured frame: 0 skipped for an unknown shader,
   and no caster missing from cascade 0 that the control's map has in the same region. This holds in `land_40` (deploy, turned), `land_small` and
   `siege_small`.
2. **Receivers replaceable:** every swapped receiver passes the CTAB gate. The tint shows the pick at the split, within a texel of where the
   design puts it, and no seam is visible at the blend band at the shot poses. At least terrain and unit meshes are swapped, and every other
   receiver drawn in `land_40` has a stated route (question 5), even if it is not built.
3. **Quality:** at 20 m on the yaw sweep, at stock size 2048 for both cascades, cascade 0's worst yaw is at least J24's best 2048 result
   (7.86 texels per metre) and **best-to-worst is within 2**. That is the target no single-map control met. Cascade 1 is no worse than
   the control.
4. **Cost:** on `land_40` at 1080p and 4K, the median delta against the same-sitting control is within the cascades budget: p50 <= 1.5 ms,
   p99 <= 2.0 ms, `va_used_mb` <= 50 MB, VRAM <= 768 MB (variant (c) may be tried before this criterion is called). The extrapolation to 3
   cascades is stated; it does not decide.
5. **Stable:** no crash or hang caused by the prototype in the sittings, and no device error in `dxvk.log`.

**No-go** if 1 or 2 fails with no route, or 4 fails after variant (c). The report says which, and the fallback is J24's map and fit. Then J26's
row is closed by a dated decision, which Liam makes. **Go with conditions** if one criterion fails for a cause the design for J26 can name and
fix (for example route 2 for culling, or ps_3_0 pairs for ps_2_0 receivers). The report then says exactly which, and Liam decides.

## PC test
All launches go through the watcher and `ctl.py`, headless on the virtual display. The agent never starts `Napoleon.exe`.
- Check `job.sh status` first. Another job may hold the lock. Never take a lock another owner holds, and never stop their game. Until the PC
  is free, work on questions 3 and 5, the spike code and its host tests.
- Take the lock with owner `j25` and release it at the end of each sitting. Install kits only with `pc_deploy.py`: sha-checked, unique staged
  names, keys set with the game closed. Never edit a running driver `.sh` (J24). Stop and ask if a step needs a visible window or admin.

Steps:
- (a) Snapshot check, then the `land_40` and `land_small` captures on the current `main` build (questions 1, 2 and 6).
- (b) Install the prototype kit with every prototype key off, and check that the start-up log shows the stock sites and the prototype idle.
  Run one `land_small` launch against the baseline shots.
- (c) Correctness: captures and tint shots on `land_40`, `land_small` and `siege_small`.
- (d) The yaw sweep at the three split distances.
- (e) The interleaved cost blocks.
- (f) The shots for the blob question.
- (g) Uninstall. The game folder must match the pre-install snapshot byte for byte, the prefs must be back byte for byte, and the exe must be
  vanilla (sha1 9aebcd2172f2878d781b079f7feb45b0e12e0250). The lock is released.

**No 20-pass acceptance run:** the prototype kit is a dev kit and no DLL input ships. `python3 core/wsc.py policy --branch job/J25 --base origin/main`
must not raise rule 79. If it does, something under `proxy/`, `harness/` (outside `runs/`) or the pin changed: undo it. If the job must
ship it, run the 20 passes on the final build with `acceptance.py run` and print `acceptance.py streak`.

Typical cost: about 3 to 5 hours of watcher time, most of it the interleaved cost blocks.

## Evidence to commit
- `harness/runs/<date>_j25pc/README.md`: the builds and kits table (spike sha, build id, kit id, keys), the sittings with UTC times, the poses
  (with any readback outside tolerance stated), and the incidents.
- The prototype as a patch series from v0.9.0 with the spike sha.
- The capture summaries through `shader_catalog.py import`. Raw `frame.txt` stays in `<state>\_scratch\j25\`, with its sha256 in each summary
  (J8).
- `density.tsv` from `tools/shadow_density.py`, the cost table from `perf_baseline.py ladder`, and the per-frame coverage counts.
- Contact sheets from `tools/shot_sheet.py` (JPEG, a few MB): before, cascade 0, and tint, at every pose.
- The facts of deliverable 1, and the shadow-pass section of `frame_anatomy.md` updated.
- The report with the go/no-go and the design for J26.

## Kill criteria
- **The pass cannot be isolated** in `land_40`: a shadow pass that is not one block, casters drawn outside it, or caster draws that cannot be
  duplicated with correct state after about 40 calls on route 1. Answer route 2 statically, then stop: no-go, fallback J24. Report the
  evidence; do not keep patching.
- **The receivers cannot be replaced without moving a stock register or sampler,** or the pick will not fit the shader model of the receivers
  that matter (terrain, unit meshes), after about 40 calls: stop, report go-with-conditions or no-go with the exact blocker.
- **Cost over the cascades budget** after variants (a) and (c) (or (b) if allowed): stop measuring and report no-go on cost with the table. The
  fallback is J24.
- **A crash or hang twice for the same cause:** stop, collect the WER dumps and the watcher's hang folder first, and report. Never keep
  relaunching. A crash in engine code from route 2 ends route 2.
- **Anything that would edit `core/` here, move the pin, add an `engine_sites` or `config_keys` row on this branch, or write into the game
  folder outside a deploy:** stop and ask.
- **The PC is held by another job past the time-box:** finish the offline answers and the spike with host tests, and report the PC steps as
  not run.
- **Over about 220 tool calls or the time-box:** stop, commit what exists, and report what is left. Not proven is a valid answer.

## Finish
Write `jobs/J25/report.md` with the headings `## What was built`, `## Evidence` (questions 1 to 6, coverage, quality, cost, blob, with run ids),
`## Go or no-go` (criterion by criterion), `## Design for J26`, `## Deviations` (from this brief, and why) and `## Open questions` (for Liam, J26,
J27 and the core). The core items go to the orchestrator to file in warscape-core `docs/BACKLOG.md` or a `W<n>` brief. Then
`wsc reg set jobs J25 status=review report=jobs/J25/report.md`.

## Open questions (conservative reading taken; Liam may overrule before or during the build)
- **The budget is PROPOSED** (`perf/budgets.md`, cascades: 1.5 / 2.0 ms, 50 MB VA, 768 MB VRAM). The job reports against it, and Liam may agree
  or change it. The kill on cost reads the proposed row.
- **"Slicing artefacts" (D12) has no definition in the repo.** The conservative reading is the far cut-off line at farz (J24's cutoff brings
  it in to about 150 m at deploy height) plus any seam between cascades. The shots show both. Liam names it if it is something else.
- **"Blob shadows" has two readings** (J8 deliverable 6): imposter casters past the unit LOD switch, and the sun-behind collapse of near shadows.
  Both are answered. Liam says which one D12 meant.
- **J24's release values are not agreed yet** (8192 + height cutoff + extrusion). The cost arms run with them on. If Liam picks 4096 or 8192
  alone, the cost difference is in VRAM only (J24: no frame cost at any size).
- **The spike branch in warscape-core** stays local and unpushed. The orchestrator or Liam decides whether to push it as a draft.

## Registry gaps
- path: fx/shadowmap.fx_fragment; owner: J25; reason: the shadow sampling fragment that every software receiver includes (J8 counts 117 mapped shaders) is named in the shader catalogue but has no assets row; the receiver swap compiles a modified copy of it
