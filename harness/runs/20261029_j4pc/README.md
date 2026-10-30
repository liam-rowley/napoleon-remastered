# J4 PC run 20261029_j4pc: the battle script route probe (deliverable 1)

PC, headless 1920x1080 (watcher launches), `dev.skip_intro=1`, `dev.ctl=1 dev.lua_bridge=1 dev.state_json=1 dev.perf=1 dev.timeline=1`,
DLL build 5c984fbabb49 (kit `kit_20261029T234619Z_5c984fbabb49`), `land_small` through `ctl autostart battle:land_small`. Four launches
(23:46 to 23:57 UTC on 2026-10-29). The proxy was installed for the run and uninstalled after it: the game folder was byte-identical to the
pre-install snapshot (1564 files). `save_games` and the settings files were not touched by me (the watcher's headless overlay is restored by the lock release).
Raw logs went with the uninstall to `C:\napoleon_remastered_pc\_to_delete`; only `raw/after_probe.jpg` is kept here.

| probe | answer |
|---|---|
| `probes/battle_api.lua` (land_small, battle context) | `empire_battle`, `battle_manager`, `battle`, `bm` are all nil in the pumping UI Lua; `empire_battle:new()` errors "attempt to index global 'empire_battle'" (3 launches) |
| `probes/battle_route.lua` | the UI environment has `BattleUI` (camera: `CameraZoomTo`, `CameraFocusOnSelection`, `BackProjectPosition`; orders `Current_Selection_*`; `RequestSpeed` is a global); `package.loaded` has `io`, `os`, `debug`; `require "Scripting_Library"` succeeds and adds a `battle_manager` table but not `empire_battle` |
| the pump | `ctl lua` chunks ran for 20 to 175 s after the load, then no pump arrived again (`pump_age_s` grew, the scene tracker said `loading`, the battle itself kept rendering: `raw/after_probe.jpg`). The cause was not found (once it followed `require Scripting_Library`, twice `battleui_names.lua`) |
| `probes/echo_args.lua -- a=1,b=2` | `args=[a=1,b=2] ctx=battle`: the new `lua <file> -- <args>` reaches the chunk (fact `napoleon.ctl.lua_args`) |
| `battleui_names.lua` | returned nothing in three tries; the BattleUI names above come from `battle_route.lua`'s output only |

Kill criterion of the brief reached (about 17 calls): the camera, speed and order lines stop; see `jobs/J4/report.md`.
