# J43 report: Battle camera and speed route

**`cam`, `pause` and `speed` now return checked results in land, siege and naval battles** (run `harness/runs/20261030_j43pc`). The
campaign camera is not done: it stays refused with its reason. The J4 pump stall was one call to the engine's `string.find`, not the route.

## The stall
- Reproduced on `main`'s DLL (91715512ec85) with `dev.perf=0`: the battle pump ran 13 minutes in deployment with no probe and survived
  `require "Scripting_Library"`, `pairs(BattleUI)` and `string.lower`. It stopped within 16 s of `battleui_names.lua`, and on a fresh launch
  within 16 s of a single plain `("camera"):find("me", 1, true)`, which also returned the wrong answer (nil). The engine replaces `string.find`
  and `string.sub` with its own C functions (as on Empire, PANEL_GUIDE gotcha 20); every J4 probe that stalled used find or gmatch.
- Fact `napoleon.lua.string_find_stalls_pump`. Coded: `tests/test_repo_rules.py` refuses find, sub and gmatch in `proxy/*.lua`; the three
  probes that used them now use match and gsub.
- The pump the routes use is the existing battle root `OnUpdatePulse` wrapper. With clean chunks it lasted the whole 11-minute battle
  (`raw/pump_10min.txt`). No new pump was needed.

## Routes tried, per kind
| route | land | siege | naval | campaign | fact |
|---|---|---|---|---|---|
| 1. stall, then the existing pump | works | works | works | not run | `napoleon.lua.string_find_stalls_pump` |
| 2. `.battle_script` on a custom preset | not tried: route 3 and 4 gave everything, and `empire_battle` is never registered in the UI state | - | - | - | `napoleon.battle.script_api_reachable` |
| 3. UI Lua: camera readback `BattleUI.BackProjectPosition` | works | works | works (unlike Empire) | - | `napoleon.battle.camera_route` |
| 3. UI Lua: `CameraZoomTo` as setter | moves the look point only (facing, height, pitch ignored) | - | - | - | `napoleon.battle.camera_route` |
| 3. UI Lua: `RequestSpeed`, pause, `ElapsedBattleTime` | works | works | works | refused (no battle clock) | `napoleon.battle.speed_route` |
| 4. DLL: engine call `SetTargetAndPosition` on the active camera mode | works | works | works | - | `napoleon.battle.camera_route` |
| campaign: `CampaignUI.CameraPosition`/`CameraTarget` readback, `Set*` | - | - | - | readback yes; the setters were not usable (the camera pans on its own; `SetCameraZoom` corrupted the stack) | `napoleon.campaign.camera_route` (open) |

Camera keys and a servo were not needed: the engine call sets the exact pose in one frame.

## What was built
- **Proxy** (`dev.camera`, default and release value 0; `config_keys` row, shipped ini, `test_dev` lint): `core/camera.h` (pose to look-at
  target, refusals), `core/camera.cpp` (chain owner global, +0xf8, +0x281b8, +0x800; vtable slot 0xbc checked against the site before every
  call; the engine thread only), `wsp.cam_set(x, y, z, yaw, pitch)` in `core/luabridge.cpp`, the adapter's `CameraAdapter`. Engine sites
  `battle.camera_chain_read`, `battle.camera_mode_read`, `battle.camera_set_target_pos` (anchor and stock bytes, each unique in the exe). Host
  tests `proxy/tests/test_camera.cpp` (34 checks: maths, refusals, every adapter offset against its row's bytes, source lints). Fix: ctl
  `lua <file> <t> --` with empty args read the whole tail as the file name (`ParseCtl`, test in `test_dev`).
- **Lua** `proxy/napoleon/lua/ctl/`: `cam_set.lua`, `cam_read.lua` (the readback), `speed.lua` (slow|play|fwd|ffwd|pause|resume|start|read).
- **Harness**: `harness/core/campose.py` (the readback's pinhole fit, pure Python); `ctl.py` `cam`, `pause`, `speed` through
  `adapter.json` `ctl.routes`, now per verb and per kind (`current_kind`: the scenario row, else the proxy's scene and naval probe). `cam`
  refuses a pitch outside the clamp before setting, fails with the clamp named when the height comes back clamped; `pause`/`speed` read the
  clock first, refuse in deployment without changing anything, and check the rate over 4 s. Host tests in `tests/test_ctl.py` against a fake
  game that projects a real pinhole camera (14 new cases).
- Registries: tools rows, 5 engine facts (one updated), 3 engine sites, 1 config key.

## Measured numbers (J44's inputs, run 20261030_j43pc)
- **cam tolerance**: adapter 0.05 m and 0.05 degrees per field, fit at most 0.05 px. Observed worst over 13 checked poses: 0.0004 m, 0.0003
  degrees, 0.0013 px. **Settle**: the set is complete on the next frame; `settle_ms` 200 is margin. A `ctl cam` takes 2.9 to 4.0 s.
- **Clamps**: pitch [-45, 45]; vertical fov fixed 70.0; height above terrain [2.5, 44.556] m on land and siege, [15, 150] m above the sea in
  naval_small. Stored in `adapter.json` `ctl.routes.camera.<kind>.clamps`.
- **Repeatability**: the same pose on two launches read back identically (difference 0 in every field). The two shots match in geometry but
  not in lighting (mean abs difference 16.4/255; 32x32 block means 16.1): the custom battle's time of day or weather varies per launch.
- **Speed**: pause 0.0; slow 0.42 to 0.45 (not 0.5: `speed 0.5` names the slow setting and is checked against 0.43); play 1.0; fwd 2.0;
  ffwd 4.0; tolerance 10 % of the rate. A pause or speed check takes about 10 s.

## Unit routes for J28
Fact `napoleon.battle.unit_routes`: `BattleUI.Current_Selection_*` (about 60 toggles), `CancelOrderForSelection`, `SelectAll*`,
`SelectUnitBasedOnUnitType`, `UnitListForBattleIds`, `SquadInfoByPointer`, `Move_Selection_To_Rader_Location`, formation calls. No
move-to-coordinates call and no unit controller in the UI Lua. The camera route's chain (battle owner, battle +0xf8) is a starting point for
an engine command path. `order` stays refused.

## Deviations
- Route 2 (`.battle_script` on a preset) was not tried: the brief ranked it before routes 3 and 4 as the cheaper one, but routes 3 and 4
  answered every verb first.
- Discovery used a read-only memory dump and three heap writes from scratch watcher jobs (`_scratch\j43\memdump.ps1`, `memwrite.ps1`),
  out of process, to prove which fields are canonical. Nothing was written into the exe image; the built route never writes memory.
- The campaign probe was cut short at the stack-corruption sign rather than spending more calls.
- The siege route uses the land clamps; it was measured with land-kind detection, because `current_kind` sees a siege as land unless the
  scenario row says so.
- About 230 tool calls of the 250 budget.

## Open questions
- **J44**: pin the custom battle's time of day and weather before shots are compared (the camera repeats exactly, the lighting does not).
  Siege needs the `scene` verb (the row's kind) to choose its route. `speed 0.5` means the engine's slow (0.43). `pause`/`speed` need the
  battle out of deployment: `lua napoleon_remastered/lua/ctl/speed.lua -- start` (or add a deployment-end step to `scene`). Height clamps
  depend on the terrain under the camera: check poses against them before a launch. The campaign camera remains open.
- **J28**: the unit routes above; whether an engine command path exists off the battle object.
- **J12**: core candidates: `campose.py` with `ctl.py`; `camera.h`/`camera.cpp` follow the console's adapter pattern and could move with it;
  the engine-Lua string lint belongs in the core's repo rules.
