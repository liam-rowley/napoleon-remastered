# J8 report: Shader catalogue and frame anatomy

Branch `job/J8`, 2026-11-01. A frame capture in the core proxy (warscape-core PR #12, merged and tagged v0.7.0 by Liam, pinned here),
captures of the acceptance scenes, a shadow-quality sweep, a 2560x1440 capture, unit-LOD and view-angle sweeps (run
`harness/runs/20261101_j8pc`), a shader catalogue of 168 runtime shaders of which 163 map byte for byte to an fx source and technique
(`discovery/napoleon/shader_catalog.json`), the frame anatomy (`discovery/napoleon/frame_anatomy.md`) and 12 engine facts. The shadow
pass is the frame's first draw pass and isolable; its quality collapses when the view lines up with the light (the low-quality shadows
with the sun behind the camera). Idle check with the key on: run `20261101_j8idle`; 20 passes on the final build `2b56389bc740`: run
`20261101_j8acc`, **20 of 20** (`acceptance.py streak --build 2b56389bc740 --watcher 1.2.0`: 20). After the run the proxy was uninstalled:
the game folder is identical to the pre-install snapshot (1564 files), the exe vanilla. `main` (J55) was merged after the run; the build id
is unchanged (`build.sh id`: `2b56389bc740`).

## What was built
- **Core (v0.7.0, warscape-core PR #12):** `proxy/src/capture.{h,cpp}`: `dev.capture` hooks 36 `IDirect3DDevice9` slots at `CreateDevice`
  (nothing with the key off; one flag test per call while idle); ctl `capture <name> [frames]` (1-8) records every device call of the
  next frames (draws, targets with descs and parent textures, clears, copies, shader binds, constant uploads with exact values, textures,
  sampler/render/stage states, viewport, streams and instancing frequency, declarations, state blocks, the engine's D3DPERF events) after a
  `STATE` block read back with `Get*`, and each shader's bytecode once per hash. Hash: canonical FNV-1a-64 to the walked end token (C16),
  host-tested with a CTAB holding `0x0000FFFF`; 63 host checks in `proxy/tests/test_capture.cpp`. `dev.capture_dir` outside the game folder.
- **Here:** the pin bump v0.5.0 -> v0.7.0 (0.6.0's opt-in storage is unused); `config_keys` rows `dev.capture`, `dev.capture_dir` and the
  shipped ini; `proxy/README.md` "Frame capture" (the verb, result fields and the record format); profiles `j8-shadow-q0..q4`, `j8-system`.
- **Tool `discovery/core/shader_catalog.py`** (registered): `import` (bytecode, disassembly with `D3DDisassemble` from System32
  `D3DCompiler_47.dll`, per-capture summaries), `fxmap` (compiles the shipped fx with System32 `d3dx9_40.dll`, the game's compiler version
  9.24.950.2656, under a base macro set from the PC's prefs and one-change variants, and maps a shader only on an identical hash, technique
  by technique), `build [--check]` (the catalogue and the anatomy tables; deterministic, checks anywhere), `hash`.

## What each deliverable found
1. **Capture and idle check:** 36 of 36 slots hooked on DXVK; every capture walked every shader to an end token matching `GetFunction`'s
   size; a full battle frame is 0.06 to 4.2 MB and records in 4 to 76 ms (the 32-bit address space is no concern: the kill criterion's
   fallback was not needed). Key on, no capture: one acceptance pass inside every threshold, perf p50 1.869 ms against 1.868 (`20261101_j8idle`).
2. **Captures:** `land_small`, `siege_small`, `naval_small`, `hist_dresden`, `hist_nile`, `campaign_start` (248 to 1446 draws). The front
   end (`f1_frontend`, a fresh launch): the same skeleton with nothing drawn (clears only), then the composite and the UI (33 draws). The
   first attempt's reset from the campaign failed (no quit flow) and captured the campaign again, kept as `r1_campaign_after_reset`.
3. **Catalogue:** 168 shaders (stage, model, size, class, fx source and technique with the macro profile, CTAB constants and samplers, the
   captures it was seen in); 163 mapped; 5 pixel shaders seen only with shadows off stay unmapped (not even with both shadow macros off).
   Flagged sources: sprite.fx 11, variantmesh.fx 9, weighted.fx 9, vegetation_billboard.fx 6, custom_sprite.fx 6, imposter.fx 5 mapped
   shaders; extendedsprite.fx 11 (a macro template included by sprite.fx); the fragments by the mapped shaders that include them
   (shadowmap.fx_fragment 117, rigid_imposter.fx_fragment 12). The engine does not pass every macro to every effect (44 rigid records
   reproduce only without `SOFTWARE_SHADOWS`). `napoleon.diff.shaders.j8_flags` closed.
4. **Frame anatomy:** one skeleton for every 3D scene with these prefs: shadow map, a cleared full-size target, half-size water reflection
   and refraction, the main pass (A8R8G8B8 + D24S8), sprites (the engine's only D3DPERF event "Drawing sneaky sprites"), a 6-draw composite to
   the backbuffer (the scene/UI boundary), UI. No HDR, SSAO, DoF or depth prepass. Naval uploads 17 sea textures first; the campaign adds a
   2400x1350 overlay (1.25x). At 2560x1440 every target but the shadow map scales with the backbuffer.
5. **Shadow pass:** `SOFTWARE_SHADOWS` (the receivers reproduce only with it); quality 1-4: 512/1024/2048 R16F, 2048 R32F, with D24X8 depth,
   36 to 54 casters, frame p50 2.04 to 2.35 ms against 1.76 with shadows off; first draw pass, one contiguous block with fixed begin and end
   calls (isolable, J25); registers and values in the anatomy doc and `napoleon.shadow.registers` (farz 72 to 473 m, far_fade 5, slope bias
   2.301, texture_size uploaded). The backend comparison: not made (below).
6. **"Blob shadows":** I first read this as distant-unit shadows and answered that (units switch to imposters between camera z 330 and 446 on
   `land_small`; their shadow is the imposter frame on a light-facing quad: `napoleon.shadow.unit_lod`). Liam then named the real symptom:
   shadows dropping to very low quality at some view angles, worst with the sun behind the camera. Measured from the uploaded light matrix
   at one camera position in 45 degree yaw steps: texels per metre at 20 m are 13.9 side-on to the sun and 5.1 with the sun behind (2.5 at
   45 degrees), and the near-to-far gradient vanishes: the perspective warp degenerates when view and light line up; farz does not change;
   the fit also depends on the scene (yaw 45 and 315 differ 3.6x). `napoleon.shadow.view_angle`; the code is open for J9.
7. **Registers:** generated per class in the anatomy doc (view_projection, world, bone/animation stacks, instance blocks, shadow matrices,
   camera position, light direction, sizes), values per shader in the summaries.
8. **Facts:** `napoleon.shaders.{runtime_compile,catalogue,macros}`, `napoleon.render.{pass_order,targets_backbuffer,system_backend}`,
   `napoleon.shadow.{map,isolable,registers,view_angle,fit_code,unit_lod}`.

## Deviations
- **Backend check not made:** on `proxy.backend=system` the headless launch fails, and a visible launch (Liam allowed it) presents nothing
  through the hooked vtables (frame 0), so nothing could be captured. Recorded as `napoleon.render.system_backend`, open for J16.
- **The core proxy docs** are this repo's `proxy/README.md` (the core has no proxy doc); the section went there.
- **Shots for the view-angle sweep** show open ground (no casters near the camera), so the drop is shown by numbers, not pictures.
- **The disassembler** is `D3DDisassemble` (64-bit System32 `D3DCompiler_47.dll`) and the fx compiler System32 `d3dx9_40.dll` of the same
  version as the game's debug `D3dx9d_40.dll` (the game's 32-bit DLL cannot load into 64-bit Python); identical hashes prove the match.
- **Run raw files:** the raw `frame.txt` captures (13 MB) stay in `<state>\_scratch\j8\captures\`, sha256 in each summary.
- **Subagents:** one, read-only (the Empire evidence summary).

## Open questions
- **J9:** the shadow projection code on Napoleon (warp, its degenerate case, the caster crop; Empire's sites in `napoleon.shadow.fit_code`)
  and the unit imposter switch distance (`napoleon.shadow.unit_lod`).
- **J24:** the view-angle collapse first: a fit that falls back to a stable projection when view and light line up, or more texels;
  poses with casters near the camera to show it in shots; quality 4 already uses R32F at 2048.
- **J25:** the pass is isolable by its target and depth formats; with the software path the map is linear depth in a colour target.
- **J16:** why Windows' d3d9 shows no Present through the hooked device vtables, and the headless failure on that backend.
- **J23:** frame p50 per scene with the key on is in the run README; GPU time per pass is not measured.
- **Liam:** `wsc setup`'s watcher check still uses `harness/core/job.sh` (the path before J12): a one-line fix outside J8's files.

## Finish
`wsc reg set jobs J8 status=review report=jobs/J8/report.md`
