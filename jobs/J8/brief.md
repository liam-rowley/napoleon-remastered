# J8: Shader catalogue and frame anatomy

Phase 2, discovery. Capture what Napoleon draws, shader by shader and pass by pass, in the scenario library J44 built: the runtime shader
catalogue by hash with its fx source and technique, the render targets of each scene kind, the shadow pass, what draws blob shadows and
why, and the matrix and constant registers each shader class reads. The answers go into `engine_facts` with run ids and into one frame
anatomy doc. J24 (shadow resolution and fit), J25 (cascades spike) and the distance and upscaler work read this job's output and nothing else.

Model: Opus, reason: shader bytecode, a proxy device-layer capture (DLL) and reading the renderer's passes (D15). Budget about 300 tool
calls; at the cap, stop, commit, report what is left. At most 2 subagents, only for independent read-only work (for example, mapping
captured shaders to fx techniques while you run captures). Waiting belongs to the harness: `job.sh`, ctl requests and the acceptance runner
block or run in the background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J8`; "The core": a core change is made in a separate `warscape-core` clone beside this one, on a
  branch, as a pull request, and arrives here as a new tag and a pin bump). Read:
  - `docs/DECISIONS.md` (D2, D15, D30, D32) and `docs/plans/PLAN.md` section 5, phase 2 and phase 3 items 2 and 3 (what the output feeds)
  - `jobs/J6/report.md` "For J8", `jobs/J44/report.md` (Open questions: J8) and `jobs/J12/report.md` (the last job that changed core proxy code)
  - `proxy/README.md` "Dev control channel", `harness/README.md`, `harness/core/ctl.py` (header = result contract), `core/proxy/src/hooks.cpp`
    (`VtableHook`), `core/proxy/src/dev.cpp` (the Present path and `perf`), `core/docs/CONSUMING.md` (upgrading the pin)
- Search before writing: `python3 core/wsc.py find shader shadow render target capture perf scenario`. The facts to start from:
  `napoleon.diff.shaders.fx` (136 fx sources, no compiled shaders shipped: the catalogue is captured live), `napoleon.diff.shaders.j8_flags`
  (the changed sources to read first: `sprite.fx`, `variantmesh.fx`, `weighted.fx`, `vegetation_billboard.fx`, `imposter.fx`,
  `rigid_imposter.fx_fragment`, `shadowmap.fx_fragment`), `napoleon.ctl.settle_signal` (no shader-creation signal today), and the tool
  `discovery.core.shaders` (`discovery/diff/shaders.json`).
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, then check every fact again on Napoleon:
  - `rml_mod/src/shader_dump.cpp`, `shader_bindcache.h`: Empire's capture (first draw per VS/PS pair only)
  - `gfx_mod/shaders/docs/frame_anatomy.md`, above all what the capture "cannot see" and its Gaps section: this job closes those gaps
  - `gfx_mod/shaders/catalog.json` (shape), `gfx_mod/shaders/tools/{frame_anatomy,fx_variants,srcset,ps_const_decode}.py`
  - `docs/learnings/LEARNINGS_ENGINE.md`: the shader hash convention trap (top of the file) and "Shader swap, ports and hash collisions"
  - `docs/graphics/GRAPHICS_NOTES.md` "Shadows" and `docs/graphics/SHADOW_FIT_UNITS.md`: Empire's shadow pass, its RT, the param block
    (projection, texture transform, linear_z, farz, slope_bias) and the caps-dependent paths (NVIDIA hardware PCF, software, ATI Fetch4)
- Other jobs touching the same files: J16 (queued: device recreation in the proxy) hooks the device too; keep the capture's hooks
  re-armed on device reset and rebase on `main` before the pull request. J9 (engine sites for sprite, LOD and shadow settings) has no
  brief yet: engine addresses this job meets are recorded as open facts with owner J9, never as `engine_sites` rows here.

## Decisions already made for this job
- **The capture is a proxy dev feature in the core**, game-agnostic, in the device layer: a warscape-core pull request with host tests, then
  a new core tag and the pin bump on `job/J8`. A `[dev]` key turns it on (default 0, release 0, a `config_keys` row, the shipped ini); with
  the key off nothing is hooked. A ctl verb takes the capture (`capture <name> [frames]`), with a checked result naming its files.
  Rule 79 applies: the branch needs 20 acceptance passes on its final DLL build id.
- **Record every call of the captured frames, not the first draw per pair:** draws, `SetRenderTarget`, `SetDepthStencilSurface`, `Clear`,
  `StretchRect`, shader binds, vertex and pixel constant uploads (start register, count and values), textures per stage with their desc,
  sampler and render states that change the output, and surface descs with their MSAA. Shader bytecode is written once per hash.
  Start with 1 frame; size and address-space cost go in the report.
- **One hash convention, fixed once and host-tested:** canonical FNV-1a-64 over the whole bytecode up to and including the real end token,
  found by walking the instruction stream, not the first `0x0000FFFF` DWORD (Empire's trap: a wrong basis and a cut inside the CTAB
  comment). The test uses a shader whose CTAB holds `0x0000FFFF`. Empire's hashes are not comparable; match the two games by fx source
  and technique.
- **Capture through `ctl.py scene`** so the fixed-sky pack and the launch keys apply (J44), at the scene's settle, on the DXVK backend at
  1920x1080 with the graphics profile the acceptance baseline uses. Prefs changes for a capture go through the watcher's config profile,
  restored byte for byte; never hand-edit the prefs file.
- Disassembly and the fx mapping are offline tools in this repo (one tool, registered, header and row); pick the disassembler (a Python one
  or `D3DDisassemble` from a d3dcompiler DLL already on the PC) and say why in its header. Nothing is downloaded to the PC for it.
- Out of scope: shader replacement, any change to shadows, LOD or distances, `engine_sites` rows, the upscaler.

## Deliverables
1. The capture: the warscape-core pull request (feature, host tests, `[dev]` key, ctl verb, a section in the core proxy docs), the tag,
   and the pin bump here with the adapter's keys. A check that the frame with the key on and no capture running matches the baseline shot.
2. Captures of the acceptance order (`land_small`, `siege_small`, `naval_small`, `hist_dresden`, `hist_nile`, `campaign_start`) plus the
   front end, in a run folder `harness/runs/<date>_j8pc/` with a README (run ids, build, profile, sizes). Commit the bytecode, the
   disassembly and the derived tables; raw captures over a few MB stay under `<state>\_scratch\J8\` with their sha256 in the README.
3. The shader catalogue: a committed generated JSON under `discovery/napoleon/` (per hash: stage, shader model, size, class, fx source and
   technique where mapped, CTAB constants and samplers with their registers, the scenes and passes it was seen in), its generator as a
   registered tool with a `--check` mode, and a count of how many captured shaders map to a source. Every flagged source in
   `napoleon.diff.shaders.j8_flags` is mapped or listed as unmapped with the reason.
4. The frame anatomy doc (`discovery/napoleon/frame_anatomy.md`, the one owner of the topic; tables regenerated by the tool, not typed):
   per scene kind the pass order, the render-target inventory (size, format, MSAA, which are tied to the backbuffer: prove it with one
   extra capture of `land_small` at 2560x1440), the depth prepass, the post chain and the scene/UI boundary.
5. **The shadow pass**, for J24 and J25: which draws make it, its RT size and format per `gfx_shadow_quality` (capture `land_small` at each
   quality the game offers), the light matrix and its registers (projection, texture transform, linear z, farz, slope bias or what Napoleon
   has instead), which receiving shaders sample the map and at which sampler, whether the pass is one contiguous block with clear begin and
   end markers (the isolability question J25 asks), its draw count and cost (`perf` at each quality), and which caps path the PC takes.
   One `land_small` capture on the system d3d9 backend shows whether the pass differs by backend.
6. **Blob shadows:** what draws them (draw, shader, texture, geometry), when they appear (distance, unit LOD or imposter, quality setting)
   and why, with shots at fixed poses (`cam` stored poses) that show them. If the why is an engine switch, name the evidence and hand the
   address to J9 as an open fact.
7. **Matrix and constant registers** per shader class: view-projection, view, world, bones and instance blocks, and any
   resolution-dependent constants, from the CTAB and confirmed by uploaded values.
8. `engine_facts` rows for each answer, each with a date and run id (or open, with an owner); close `napoleon.diff.shaders.j8_flags`.

## PC test
All game launches through the watcher and `ctl.py`; Liam is not needed unless a step needs admin. Order: install the build with the key on,
check the idle frame against the baseline, capture the front end and the six scenes, then the shadow-quality sweep, the 2560x1440 capture
and the system-backend capture, then the 20-pass acceptance run on the final build (in the background). Uninstall at the end and compare
with the snapshot, as J44 step f.

## Kill criteria
- With the key on and no capture running, a scene's shot or load time falls outside the baseline thresholds: stop, fix or report; a
  capture that changes what it measures is worthless.
- A full-frame capture of a battle cannot fit in the address space (the process is 32-bit) or crashes the game twice: fall back to Empire's
  first-draw-per-pair capture plus the render-target calls, record why, and carry on with that.
- The shadow pass cannot be told apart from the rest of the frame after about 40 calls on it: write down what is known, mark the
  isolability fact open for J25, and finish the other deliverables.
- The 20-pass run fails twice for a cause in the capture code: stop and report; do not keep re-running.

## Finish
Write `jobs/J8/report.md`: what was built (core PR and tag, tools), the captures with run ids, the catalogue and anatomy summaries, the
answers for the shadow pass, blob shadows and registers, deviations from this brief and why, and open questions for J9, J23, J24 and J25.
Then `wsc reg set jobs J8 status=review report=jobs/J8/report.md`.
