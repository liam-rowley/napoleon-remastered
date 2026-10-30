# J43 PC run 20261030_j43pc: the battle pump, the camera, speed and pause routes

PC, headless 1920x1080 (watcher launches), `dev.skip_intro=1`, `dev.ctl=1 dev.lua_bridge=1 dev.state_json=1 dev.timeline=1 dev.perf=0`,
2026-10-30 09:02 to about 10:45 UTC. Builds: `main`'s DLL 91715512ec85 (kit `kit_20261030T090202Z_91715512ec85`) for the stall, then this
branch's e137f1f8f312 (kit `kit_20261030T095731Z_e137f1f8f312`, `dev.camera=1`). Scratch probes lived in `C:\napoleon_remastered_pc\_scratch\j43\`
(not the game folder). Raw ctl results are in `raw/`; times are UTC.

## 1. The pump stall (main's DLL, dev.perf=0)
| step | pump |
|---|---|
| land_small loaded, no probe | alive 13 min in deployment (09:06 to 09:19) |
| `require "Scripting_Library"` alone (`probes/require_sl.lua`) | alive (3.5 more minutes) |
| `probes/battleui_names.lua` (gmatch + find) | **stopped** within 16 s; scene tracker `loading`, battle still rendering |
| relaunch: `pairs(BattleUI)` with tostring only | alive |
| `("CameraZoomTo"):lower()` | alive |
| one `("camera"):find("me", 1, true)` (returned nil, nil) | **stopped** within 16 s |

Cause: the engine's own `string.find` (it replaces find and sub). Fact `napoleon.lua.string_find_stalls_pump`; the probes now use
match/gsub and `tests/test_repo_rules.py` refuses find/sub/gmatch in `proxy/*.lua`. With the probes clean, the battle pump lasted 11 minutes
of a running battle (`raw/pump_10min.txt`, section 5).

## 2. Routes found
- **Camera readback (Lua)**: `BattleUI.BackProjectPosition(x, y, z, 0)` returns screen x, screen y, depth and the distance from the camera.
  `lua/ctl/cam_read.lua` trilaterates the position from four distances and projects a 3x3x3 cluster 100 m ahead; `harness/core/campose.py`
  fits yaw, pitch and the focal length (first solve: position (-0.075, 59.020, 446.136), yaw 179.906, pitch -25.000, vertical fov 70.000,
  0.001 px). It works at sea too.
- **Camera setter**: `BattleUI.CameraZoomTo(x, y, z, facing)` (Lua C function at RVA 0x1ce960) only moves the look point in x/z (the same target twice is a no-op;
  facing and height ignored). It reaches the controller `*(*(*global + 0xf8) + 0x281b8)`, whose active mode `*(controller + 0x800)` is a
  look-at camera: position +8, target +0x14, height above terrain +0x150 (canonical, clamped by the update), angles as 16-bit binary angles
  (65536 / 2 pi). Its vtable slot 0xbc `SetTargetAndPosition(target, pos)` (RVA 0x1fb320) sets both in world coordinates and recomputes the
  height from the terrain. Out-of-process writes to +8/+0x14/+0x150 (a scratch experiment, `_scratch\j43\memwrite.ps1`, heap only) proved
  the fields; the built route calls slot 0xbc from the proxy (`wsp.cam_set`, `dev.camera`), never writes memory.
- **Speed and pause**: the battle root's `RequestSpeed` (calls `BattleUI.Slow/Play/Fwd/Ffwd/Pause`), `ReinstatePrePauseBattleSpeed`;
  clock `BattleUI.ElapsedBattleTime` (0.1 s steps) against `BattleUI.WindowsTime`; `BattleUI.TickPeriod` names the speed. Deployment ends with
  `BattleUI.InformOfDeploymentFinished` (the start button's call; `DeploymentFinishYesStart` alone did nothing).
- **Campaign** (`campaign:new:mp_eur_napoleon:austria`; `france` is not offered): `CampaignUI.CameraPosition()`/`CameraTarget()` read the pose;
  the camera kept panning by itself; `SetCameraZoom(40)` returned (true, function), the stack-corruption sign. Stopped there (fact
  `napoleon.campaign.camera_route`, open).

## 3. ctl.py on the PC (this branch's build)
| kind | cam (3 poses) | pause on / off | speed |
|---|---|---|---|
| land_small | ok x3 (`land_cam1-3.json`), ok while paused | ok 0.0 / ok 0.99-1.01 | 2: 2.000, 4: 4.000, 1: 0.99-1.01, 0.5: 0.427 (slow, checked on its measured 0.43), 3: refused |
| siege_small | ok x3 (`siege_cam1-3.json`) | ok 0.0 / ok 0.989 | 4: 4.006, 1: 1.009 |
| naval_small | ok x3 (`naval_cam1-3.json`) | ok 0.0 / ok 1.005 | 2: 1.995, 1: 1.006 |
| campaign | refused (route unknown) | refused (no battle clock) | refused |

Every cam readback was within 0.0004 m and 0.0003 degrees of the pose asked (fit 0.0001 to 0.0013 px); a ctl cam takes 2.9 to 4.0 s.
In deployment, pause and speed are refused without changing the speed (`land_speed_deploy.json`).

## 4. Clamps and repeatability (J44's inputs)
- Pitch [-45, 45] degrees (land and naval: -50 and -60 gave -45, 60 and 85 gave 45). Vertical fov fixed at 70.0.
- Height above terrain [2.5, 44.556] m on land (land_small y=200 gave terrain + 44.556, y=0 terrain + 2.5); [15, 150] m above the sea in naval_small.
- The set is complete on the next frame: settle 200 ms is margin, not a measured wait.
- Repeatability: `cam 0 30 200 180 -25` in land_small on two launches (`repeat_a_cam.json`, `repeat_b_cam.json`): readback difference 0 in
  every field. The shots (`repeat_a.jpg`, `repeat_b.jpg`, both in deployment) have the same geometry (trees, horizon, minimap) but different
  lighting: mean abs difference 16.4 / 255 full resolution, 16.1 on 32x32 block means. The custom battle picks its time of day or weather
  per launch: J44's sky pin, not the camera.

## 5. The 10-minute battle
`raw/pump_10min.txt`: land_small after deployment ended (10:19), ctl state every 30 s from 10:20:08 to 10:31:34: 23 samples, scene
`battle` throughout, `pump_age_s` 0.0 in every one; the battle clock read 709.6 s at the end.

## 6. Dev keys off, uninstall
- `dev.camera=0` on this branch's build (`keyoff_*.json`): `scene land_small` ok; `cam` failed at the set step with `cam_set refused:
  dev.camera=0`; the log shows `camera: dev.camera=0` and no install line (no site read).
- Uninstall: game folder identical to the pre-install snapshot (1564 files). The lock release restored the headless overlay (no active
  profile left); `save_games` unchanged (newest file 2026-10-29); the campaign start (`campaign:new:mp_eur_napoleon:austria`) wrote no save.
- **Corrected by the reviewer (2026-10-30, `jobs/J43/review.md` finding 1):** the "identical" check ran at 10:32:30, before the lock
  release. At 10:32:32 the watcher's auto-restore wrote the headless profile's saved `mod_ini` (main's `napoleon_remastered.ini`, 5331 bytes,
  sha256 8d8a4af0..., saved at 09:02:33 after main's kit install) back into the game folder. The folder ended at 1565 files: one stray ini, inert
  without `d3d9.dll`, but not as found.
