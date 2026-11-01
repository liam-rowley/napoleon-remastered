# J8 review

## Round 1 (2026-11-01, branch job/J8 at ee92f6a)

**Verdict: merge after fixes.**

Reviewed cold from the brief, the report, `docs/REVIEW.md` and the branch (cloud session, read-only clone; not the builder). The core
of the job is sound: the capture code is correct where it matters (slot indices, desc layouts, hash walk), the catalogue regenerates
deterministically, rule 79 holds and the shadow-pass answers are backed by committed summaries. The fixes below are about evidence
the brief asked for and two claims that say more than the evidence shows.

### Machines
- `wsc gates`: 10 ok, 1 warn (hooks not wired in this clone), 1 failed: `tests` with 3 failures, all environmental here and checked
  against `main`: `test_harness_host_tests` (no `powershell.exe`; fails on this branch only because it changes harness inputs; CI's
  `harness-windows` runs it), `test_job_sh...registered_default` and `test_saves...read_only` (fail on `main` too in this container, root user).
- `pr_policy.py --branch job/J8 --base origin/main`: refused only for the missing review and the row not `done`, as expected before a
  merge verdict. Commit trailers pass.
- `shader_catalog.py build --check`: ok (168 shaders, 163 mapped). `wsc jobs check`: ok.
- `core/proxy/tools/build.sh id` on the branch: `2b56389bc740`, the id of the 20 passes (run `20261101_j8acc`: 20 of 20, each
  `passed: true`, 13:06 to 14:34 UTC).
- **CI not read:** this session has no GitHub API access to the repo, so the checks on the head were not seen. Read them before the
  round-2 verdict (`wsc jobs review`).

### Risk-first reading
Picked `core/proxy/src/capture.cpp` and `capture.h` at v0.7.0 (36 vtable hooks on the live device, file writes from the render thread)
and the adapter keys. Checked every `IDirect3DDevice9` slot index (30 to 114), the surface, texture, volume and declaration slots, the
`D3DSURFACE_DESC`/`D3DVOLUME_DESC` layouts, `ShaderLength` (comment skip, SM2+ operand counts) and `ValidCaptureName` (no path
traversal; `devcore.h` refuses a bad name before `CaptureRun`). All correct. Key off: nothing hooked (`CaptureInstall` returns first);
`config_keys` rows and the ini ship `capture=0`. On the system backend both devices' originals are identical
(`raw/sys_proxy.log` lines 99 and 181), so keeping the first original is safe there.

### Should-fix (job chat; items 1, 3 and 4 need the PC)
1. **The key-on idle check ran on a build that is not the one merged.** `harness/runs/20261101_j8idle/pass_01.json` `build_id`
   `f3e33f228416-dirty`; every capture also came from that pre-tag dirty kit (run README, "Builds"). The final DLL `2b56389bc740` never
   ran with `dev.capture=1` and no capture. The README says the code differs only in the result's shader count, but a dirty build has
   no source to check that against. Fix: one acceptance pass on `2b56389bc740` with `dev.capture=1`, committed as a run (about 5 min).
   Deliverable 1 and kill criterion 1 are about this build.
2. **State blocks are a blind spot the doc dismissed.** `frame_anatomy.md` said no `SBBEGIN` means none are expected; but
   `CreateStateBlock` (slot 59) and `IDirect3DStateBlock9::Apply` are not hooked (`capture.cpp:341-361`), and D3DX effects save and
   restore state through state blocks unless created with `D3DXFX_DONOTSAVESTATE`. Per-draw render/sampler state and textures after an
   effect's `End` may be stale in the summaries; targets, depth surfaces and shader binds are not affected, so the pass order, the
   target inventory and the shadow-pass facts stand. Doc line corrected in this round (commit `a7d5582`); the hook is a core item (later).
   See it: no hook for slot 59 in the table at `capture.cpp:341`.
3. **The shadow caps path is the prefs' path, not the caps'.** Deliverable 5 asks which caps path the PC takes; the answer
   `SOFTWARE_SHADOWS` follows from `gfx_hardware_shadows false` in the baseline prefs (`frame_anatomy.md:53`), not from the RTX 4090's
   caps, and the hardware path (`NVIDIA_HARDWARE_SHADOWS`: depth texture, hardware PCF) was never captured. J24 and J25 need to know
   whether that path exists and how its map differs. Fix: one `land_small` capture through a profile with `gfx_hardware_shadows true`
   (map format, size, registers), or an open fact for J24 naming the gap. The report does not list it as a deviation.
4. **The view-angle numbers cannot be regenerated.** `napoleon.shadow.view_angle` and `frame_anatomy.md:74` give texels per metre
   computed by hand; the metric ("texels per metre on the view ray") is not defined in a tool. Recomputed here from the committed
   summaries (`captures/y_*.json`: `shadow_map_projection_matrix`, `camera_position`, the view ray from `view_projection`), as the
   square root of the ground-plane Jacobian at 1024 texels per unit uv: yaw 0 5.2/5.2/5.1, yaw 45 3.6/3.2/2.6, yaw 90 20.8/12.7/6.5, yaw
   315 10.1/9.0/7.3. Same finding (flat and low with the sun behind, a gradient side-on, 45 and 315 about 3x apart), different near
   values from the fact's 13.9/10.0/6.4, so the metric matters. Fix: a `shader_catalog.py` subcommand (or an anatomy table) that computes
   it with the metric named, and the fact regenerated from it. (Empire repeats: a number in prose that a tool could own.)
5. **The system-backend fact claimed a cause.** It said vtable hooks do not see the game's calls on Windows' d3d9; the evidence shows
   frame 0 already at the front end with the first device, and there is no control launch with `dev.capture=0`, so the capture's own
   hooks are not ruled out. Claim reworded to the observation in this round (commit `0887615`); J16 should start with that control.
6. **Run README time window** said 11:49 to 13:15; the files run to 14:35 (front end `f1_frontend` 14:35:00, acceptance to 14:34).
   Fixed in this round (commit `e3ad054`).

### Later
- **Core (warscape-core `docs/BACKLOG.md`):** `CaptureRun` timeout path (`capture.cpp:423-436`): if the second 30 s wait also times out,
  it returns ok with a partial frame, sets `kIdle` while the render thread still has `s_rec` set and `frame.txt` open, and the next
  capture reopens over it. Report `failed` and let the render thread own the close. Not hit in this job (recording took 4 to 76 ms).
- **Core:** `s_depth`, `s_buf` and `Line()` are unsynchronised globals (`capture.cpp:38`, `:146`, `:331`); a device call or a D3DPERF
  event from a second thread during a recording would race. Record the render thread id at arm and count, not record, calls from others.
- **Core:** hook `CreateStateBlock` and `IDirect3DStateBlock9::Apply`/`Capture` (finding 2), at least as counted record lines.
- Facts carry `evidence` paths but no run field; `napoleon.shadow.registers` and `napoleon.render.pass_order` point at the generated
  anatomy doc rather than a run. The brief asked for run ids.
- The report's Deviations list omits two deviations it describes elsewhere: the blob-shadow reinterpretation (deliverable 6) and the
  captures coming from the dirty pre-tag build.
- `wsc setup` still checks `harness/core/job.sh` (report's own open question): needs a queue row.

### Fixes made in this round
- `e3ad054` run README time window; `a7d5582` frame anatomy state-block limit; `0887615` system-backend fact wording.
  `shader_catalog.py build --check` ok after each.
