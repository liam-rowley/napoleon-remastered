# J43: Battle camera and speed route

Phase 1. J4 built the control API (`harness/core/ctl.py`) but hit its kill criterion: the battle script objects (`empire_battle`,
`battle_manager`, `camera`, controllers) are unreachable from `ctl lua`, and the battle UI pump that runs `ctl lua` stops by itself
20 to 175 s after a load (fact `napoleon.battle.script_api_reachable`). So `cam`, `pause` and `speed` are refused, and J44 (the
scenario library and the 20-pass gate), and through it J8, J9, J12, J23 and J28, wait on this job. The goal: `cam`, `pause` and
`speed` return checked results in land, siege and naval battles and in the campaign, through a route that holds for a whole battle.
`order` stays J28's; this job only records what the found route offers it.

Model: Opus, reason: reverse engineering on Napoleon.exe and a likely proxy DLL route (a pump that does not stop, camera readback, maybe
an engine call or Empire's camera servo). Budget about 250 tool calls; at the cap, stop, commit, report what is left. At most 2
subagents, only for independent read-only work (for example, reading the historical battle scripts in data.pack, or Empire's camctl
sources and reports). Waiting belongs to the harness: `job.sh` and ctl requests block inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J43`). Read:
  - `docs/DECISIONS.md` (D2, D3, D15, D26-D28, D30, D32)
  - `docs/plans/PLAN.md` section 5, phase 1 (control API)
  - `jobs/J4/brief.md`, `report.md` and `review.md` (round 1 items 2 and 3 are this job's first steps), and
    `harness/runs/20261029_j4pc/README.md` (the probe run)
  - `harness/README.md`, `proxy/README.md` "Hooks", "Dev control channel" and "Headless", `harness/core/ctl.py` (its header is the result
    contract), `harness/napoleon/adapter.json` `ctl.routes`
  - `jobs/J3/report.md` (pump, autostart, warm reset) and `jobs/J15/report.md` (the engine-call pattern: `campaign.cli_*` rows in
    `registries/engine_sites.jsonl`, preference 2, no detour)
- Search before writing: `python3 core/wsc.py find camera battleui pump speed pause battle_script lua`. Extend what exists:
  `proxy/napoleon/lua/{wsp.lua,wrappers.txt,battles/*.txt,probes/}`, `proxy/tools/build_dev_pack.py`, `proxy/tools/pc_deploy.py sync-lua`,
  `proxy/core/{dev.cpp,devcore.h,luabridge.cpp,hooks.cpp,headless.cpp}`, `harness/core/ctl.py`.
- Other jobs touching the same files: J16 (resolution change crash, queued: `proxy/core` device and headless code) and J18 (rule guards
  in `job.sh` and the watcher, queued). Keep `headless.cpp` and watcher changes small and additive; rebase on `main` before the pull request.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, not the numbers:
  - `rml_mod/src/camctl.h`, `gesture_cam.h`, `orchestrator/reports/2026-10-27_camctl.md` and `2026-10-27_camctl-pc.md` (the servo
    on a captured view matrix), `2026-10-27_light0.md` (`BattleUI.CameraZoomTo` behaviour)
  - `guides/19-battle-controls.md` sections 11.1 (G1: no battle-script API in custom battles) and 17 (camctl commands)
  - `rml_mod/docs/atlas/ENGINE_API.md` "Scripting environments"
  - `docs/learnings/LEARNINGS_HARNESS.md`: search "camctl", "Camera keys", "No battle-script API"

## Target facts
Recorded by J3, J4 and Empire. Check each again on Napoleon before relying on it:
- **The pumping battle UI environment** has `BattleUI` with `CameraZoomTo`, `CameraFocusOnSelection`, `BackProjectPosition` and
  `Current_Selection_*`, and a global `RequestSpeed`; none has been called. `require "Scripting_Library"` succeeds and adds a
  `battle_manager` table but not `empire_battle` (run `20261029_j4pc`).
- **The pump stall**: chunks run for 20 to 175 s after the load, then no pump arrives (`pump_age_s` grows, the scene tracker says
  `loading`, the battle keeps rendering). Every probe ran on J4's build 5c984fbabb49 with `dev.perf=1`; the stall has not been seen on
  `main`'s DLL with `dev.perf=0`. Once it followed `require "Scripting_Library"`, twice `battleui_names.lua`.
- **Only the battle root gets update calls** (`OnUpdatePulse`, fact `napoleon.lua.update_callbacks`); the front end pumps only on the
  main menu.
- **Historical battles** run `napoleon_historical_battles\<name>\<name>_battle.battle_script` with `battle = empire_battle:new()` and
  `battle:camera()`; `profiling_scripts\landbattle x1.battle_script` drives a scripted camera (`camera:move_to`, `camera:position`) and
  `battle:modify_battle_speed`. On Empire this state existed only in historical and tutorial battles, never in a custom battle (G1).
- **Empire's route**: `BattleUI.CameraZoomTo(x,y,z,f)` moves the look point in x/z only (facing ignored, pitch reset to 15); camctl
  reads the pose from the view matrix of one vertex shader's constants and pulses the vanilla camera keys in closed loop (0.25 m,
  0.15 deg). Height is clamped to terrain + about 12 m to about 56 m. **Naval had no capture** (that shader does not draw at sea).
- **Headless input**: the proxy makes DirectInput non-exclusive and foreground-only (`core/display_guard.h`), and a headless game
  never has the foreground, so key presses sent from outside do not reach it. A servo has to inject its keys inside the proxy.
- **Campaign camera**: `CampaignUI.CameraTarget()` reads the target (probe `campaign_camera.lua`, J15); `SetCameraTarget`,
  `CameraPosition` and `CameraZoomTo` are untested.
- The exe is on this PC now (D30), unlike Empire's cloud agents: the engine's camera object can be reverse-engineered.

## Decisions already made for this job
- **Order of routes, cheapest first; stop each at its allowance (Kill criteria) and take the next:**
  1. Reproduce the stall once on `main`'s DLL with `dev.perf=0` and only `ctl state` and an idle chunk (J4 review 3). Then isolate the
     cause in a few launches: no probe at all, `require "Scripting_Library"` alone, one BattleUI call. Whatever the cause, every Lua
     route depends on a pump that lasts the whole battle: find one (another root's callback, a wrapper on a battle script that pulses,
     or a pump driven from the proxy on the game's own Lua thread) before building on Lua.
  2. **A `.battle_script` on a custom battle preset** (J4 review 2): can a custom battle (or the historical battle screen's route) run a
     battle script that the D27 virtual pack serves, so that `ctl lua` reaches `empire_battle` and `battle:camera()`? If it can, this
     state gives camera, speed, pause and the controllers J28 needs.
  3. **The UI Lua calls**: `BattleUI.CameraZoomTo`, `RequestSpeed`, the pause call, `Current_Selection_*`, with a camera readback (Lua
     if one exists, `BackProjectPosition` or the DLL readback below).
  4. **The DLL route**: a camera readback (the view matrix from the land and naval shaders' constants, or the engine camera object
     found in the exe) and a setter: an engine call on the camera object (preference 2, no detour, as J15) or a port of Empire's
     camctl servo with its keys injected inside the proxy (a DirectInput `GetDeviceState` hook or the engine's own input path, never
     `SendInput`). Speed and pause by engine call if Lua has none.
- **Everything in the proxy is a dev feature**: new `[dev]` keys default 0 with release value 0, a `config_keys` row, the shipped ini,
  the pass-through lint (`tests/test_dev.cpp`), host tests for the pure logic (pose maths, servo, readback parsing). Every engine
  address goes in `engine_sites` with anchor bytes behind the exe-identity guard; the exe stays vanilla on disk (D2). New ctl verbs get
  rows in the `proxy/README.md` ctl table.
- **The control API keeps its shape.** `cam <scenario:pose | x y z yaw pitch [fov]>`, `pause on|off`, `speed <x>` in `ctl.py` keep J4's
  result contract (rule 77: no ok without a `check`). `cam` reads the pose back and fails beyond a tolerance you measure; `pause` and
  `speed` check that battle time stops or advances at the asked rate. The routes are chosen in the adapter's `ctl.routes` (per kind:
  land, siege, naval, campaign), not hard-coded, and a route that does not work for a kind stays `refused` with its reason and fact.
- **Poses are coordinates read back from the camera**, never key-tap scripts (rule 78). Record the clamps you find (height, pitch) so
  J44 can check poses against them before a launch.
- **`order` is not built here.** Record, as facts, which unit routes the found state offers (controllers, `Current_Selection_*`, an
  engine command path) so J28 can choose; leave the verb refused.
- **Rule 79** stays inert until J44 commits a measured baseline (`acceptance_active`), so this branch's proxy and harness changes are
  not blocked by it. Do not commit a baseline or ledger lines.

## Deliverables
1. **The stall**: reproduced (or not) on `main`'s DLL with `dev.perf=0`; its cause, or the cases that rule causes out, as an
   `engine_facts` row with run ids; a pump that lasts a whole battle (at least 10 minutes in land_small), or the reason none exists.
2. **The route probe**, in land_small, siege_small, naval_small and a campaign (`campaign:new:mp_eur_napoleon:<faction>`): for each route
   tried, does it set and read the camera, set speed, pause and resume? One `engine_facts` row per answer with a run id, including the
   routes that failed (so no later job tries them again).
3. **The chosen route built**: Lua under `proxy/napoleon/lua/`, and the proxy part if needed, with host tests; engine sites with anchor
   bytes; `config_keys` rows.
4. **`ctl.py` wired**: `cam`, `pause`, `speed` return checked results through `ctl.routes` for every kind the route works in; host tests
   against the fake game for the new paths; `adapter.json` `ctl.routes` updated with status, why and fact per verb and kind.
5. **Measured numbers**, as `config_keys` or adapter fields with the run id: the `cam` tolerance (position and angle), its settle time,
   the camera clamps, and repeatability (the same pose on two launches: readback difference and a shot difference with the metric you
   use). These are J44's inputs.
6. **Unit route notes for J28** (facts only, see Decisions).
7. **Registries**: `tools` rows for new tools and probes' headers, `engine_facts`, `engine_sites`, `config_keys`; the `ctl.py` and
   tools rows no longer say "refused until J43" for what now works.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py` (Lua by `sync-lua`), sha-checked; every launch uses
`dev.skip_intro=1`. No sitting with Liam is needed; if a step would need a visible window, stop and ask. Results go in a dated run
report under `harness/runs/` or `proxy/runs/` with job ids, ctl results and screenshots.

Steps:
- a) Dev keys off (every new key 0): the J3 behaviour is unchanged.
- b) The stall reproduction on `main`'s DLL (deliverable 1), before any new build.
- c) The route probe (deliverable 2).
- d) On the final build: `cam` to three poses in land_small, siege_small and naval_small (or refused with the reason), `pause on`,
  `pause off`, `speed` at two rates, each checked; the same `cam` pose on a second launch for repeatability; a 10-minute battle with the
  pump alive at the end.
- e) Uninstall is byte-identical; `save_games` and every settings file are as found.

## Kill criteria
- **The stall** is not explained after about 30 calls: record what was ruled out and move to the routes that do not need the Lua pump
  (route 4), or to a proxy-driven pump if one is cheaper.
- **Lua routes (2 and 3)** give no checked camera pose after about 50 calls together: stop them and take route 4.
- **Route 4** finds no camera readback or setter after about 80 calls: stop, commit, report what is known (candidate sites, shaders,
  what failed) and propose the next job. The gate stays blocked: say so plainly.
- **Naval** has no readback (as on Empire) after about 15 calls: leave naval `cam` refused with its reason and fact; pause and speed
  still count.
- **Any crash or hang**: read WER and the watcher's hang folder first. Two for the same cause: stop that route and report with the dumps.
- **Any write into the game folder outside a deploy, into `core/`, or into Liam's saves would be needed**: stop and ask Liam.

## Finish
Write `jobs/J43/report.md`. Cover:
- the stall: reproduction, cause, the pump the routes use
- every route tried, per kind, with run ids and its fact (worked, failed, not tried and why)
- what was built (Lua, proxy, `ctl.py`), its keys, sites and tests
- the measured tolerances, clamps, settle and repeatability for J44
- unit routes found for J28
- deviations from this brief and why
- open questions, listed separately for J44, J28 and J12 (what in `proxy/core` or `harness/core` becomes a core candidate)

Then `wsc reg set jobs J43 status=review report=jobs/J43/report.md`.
