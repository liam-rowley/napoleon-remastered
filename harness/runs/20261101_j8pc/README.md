# J8 PC run 20261101_j8pc: frame captures, shadow sweep, view-angle sweep

PC (RTX 4090, Windows 11), watcher 1.2.0, 2026-11-01 11:49 to 14:36 UTC (captures to 13:02, acceptance 13:06 to 14:34, front end 14:35), game lock `j8`. DXVK unless named. Every scene through
`ctl.py scene` with the adapter's `ctl.launch.keys` (fixed sky) plus `dev.capture=1` and `dev.capture_dir=C:\napoleon_remastered_pc\captures`;
headless 1920x1080 unless named. Prefs: the PC's as the acceptance baseline uses them (`gfx_shadow_quality 3`, `gfx_hardware_shadows false`,
`gfx_hdr/ssao/distortion/depth_of_field false`, `gfx_unit_quality 2`, `gfx_gamma_setting 2`). Builds: the capture branch before the tag
(`f3e33f228416-dirty`, kit `kit_20261101T114832Z_60c6d5d6bbd0`) for every capture; the final build from the v0.7.0 pin `2b56389bc740`
(kit `kit_20261101T124657Z_ee06e0f96f50`) for the system-backend attempt and the 20 passes (run `20261101_j8acc`). The capture code is the
same in both but for the result's `shaders` count (core commit "capture result shaders = distinct shaders bound in this capture").

## Files
- `captures/<name>.json`: the committed summary of each capture (`discovery/core/shader_catalog.py import`): passes, render targets,
  shader use and first-draw constant values, the raw file's size and sha256.
- `raw/`: ctl results (`*_scene.json`, `*_capture.json`, `*_perf.json`, `*_cam.json`, `*_shot.json`), shots (`blob_*.jpg`, `yaw*.jpg`),
  `sys_proxy.log` (the system-backend launch).
- The raw captures (13 MB: `frame.txt` per capture and the bytecode) are kept under `C:\napoleon_remastered_pc\_scratch\j8\captures\`;
  each summary's `raw.sha256` names its `frame.txt`. The bytecode and its disassembly are committed in `discovery/napoleon/shaders/`.

## a) Idle frame with the key on (kill criterion 1)
Run `20261101_j8idle`: one acceptance pass with `dev.capture=1` and no capture running: **pass**. Shot differences land 0.75 (threshold 4.0),
siege 1.158 (4.0), naval 2.324 (9.07), Dresden 2.955 (7.64), Nile 2.55 (9.81); loads within limits (land 3.9 s against 3.9); perf p50 1.869 ms
against the baseline's 1.868; settings byte-identical after the exit.

## b) Captures (1 frame each)
| capture | scene | draws | bytes | what |
|---|---|---|---|---|
| t1_land_small | battle_deploy | 675 | 380917 | first test |
| r1_land_small, r1_siege_small, r1_naval_small, r1_hist_dresden, r1_hist_nile, r1_campaign_start | per row | 675, 626, 248, 1446, 653, 1084 | 0.12 to 0.76 MB | the acceptance order |
| r1_campaign_after_reset | campaign | 175 | 62749 | meant as the front end: `ctl.py reset` from the campaign failed ("no result": the campaign has no quit flow, fact `napoleon.campaign.quit_to_menu`), so it is the campaign again (raw folder `r1_frontend`) |
| q0..q4_land_small | battle_deploy | 626, 660, 670, 673, 680 | | `gfx_shadow_quality` 0 to 4 through profiles `j8-shadow-q<N>` |
| w1440_land_small | battle_deploy | 671 | 380647 | launched at 2560x1440 |
| b_near, b_deploy, b_d700, b_d1000, b_d1400 | battle_deploy | 1282, 674, 608, 601, 593 | up to 4.2 MB | camera on the deploy line at z 330, 446.14, 700, 1000, 1400 (x -0.08, yaw 180; the last three clamped in height by the engine, readback outside tolerance, pose as read back in `raw/blob_*_cam.json`) |
| y_0 .. y_315 | battle_deploy | 503 to 691 | | camera (-0.08, 59.02, 446.14), pitch -25, yaw 0 to 315 in 45 degree steps (yaw 270's readback outside tolerance) |
Every capture: `shaders_unwalked` 0 and `shaders_size_differs` 0 (the walked length agrees with `GetFunction`); recording took 4 to 76 ms.
Frame p50 (ms, `perf 10` after each acceptance-order capture): land 2.255, siege 2.259, naval 1.688, Dresden 4.439, Nile 3.558, campaign 1.951.

## c) Shadow sweep and view angle
Per quality and per yaw: `discovery/napoleon/frame_anatomy.md` "The shadow pass" (facts `napoleon.shadow.*`). Texels per metre are computed
from each capture's uploaded `shadow_map_projection_matrix` (clip = dot(register row, P), uv = clip.xy / clip.w, times the map size / 2) at
points 20, 60 and 140 m along the view ray from `camera_position`.

## d) System d3d9 backend (deliverable 5's backend check): not taken
Profile `j8-system` (`proxy.backend=system`). Headless: twice "HEADLESS FAILED: no on_virtual status ... (last: target_ok target resolved at
Direct3DCreate9)" and killed. Visible (`visible=1`, Liam allowed it 2026-11-01): the battle loaded to `battle_deploy` but `ctl.py scene`
never settled: `frame` stayed 0: no Present reached the hook, though both devices' vtables were hooked (`raw/sys_proxy.log`: Present slot
at 13c1e340 and 3075dfc0, heap vtables, against DXVK's shared one). Fact `napoleon.render.system_backend` (open, owner J16). The first visible
attempt relaunched headless because the final kit's install had reset the ctl launch keys; set again before the second.

## e) Incidents
- `wsc setup` reports the watcher check failing with `harness/core/job.sh` not found: the check still uses the pre-J12 path (`core/harness/job.sh`
  works). Not fixed here (setup is outside J8's files); in the report's open questions.
- The first acceptance attempt was refused: run with `python3` (Pillow), and with the j8 lock and the headless profile still held.

## f) After the 20 passes
Front end from a fresh launch (`f1_frontend`, 33 draws), final fxmap (168 shaders, 163 mapped), then `pc_deploy uninstall`: the game
folder is identical to the pre-install snapshot (1564 files), the exe vanilla; no lock and no active profile.

## g) Review round 1 fixes (15:03 to 15:13 UTC)
- Key on, no capture, on the final build: run `20261101_j8idle2`, one acceptance pass, **pass** (land 0.857, siege 1.017, naval 1.811,
  Dresden 3.226, Nile 4.658 against the same thresholds; perf p50 1.915 ms); the DLL logged "build 2b56389bc740 loaded"
  (`harness/runs/20261101_j8idle2/proxy.log`). `acceptance.py` labelled the pass with the kit id `ee06e0f96f50` (no proxy.log yet after a
  fresh install, so `build_info` fell back to install.json); the ledger line and `pass_01.json` were corrected to `2b56389bc740` with a
  `note` (Liam's choice, 2026-11-01). Streak: 21.
- Hardware shadows: profile `j8-hwshadow` (`gfx_hardware_shadows true`), capture `hw_land_small`: 675 draws, the same 83 shaders and the
  same 2048 R16F map as `r1_land_small`. The prefs file has the key twice (lines 24 and 37) and the overlay sets the first only, so the
  path was not reached: fact `napoleon.shadow.hardware_path` (open, J24).
- Then `pc_deploy uninstall`: identical to the pre-install snapshot (1564 files).
