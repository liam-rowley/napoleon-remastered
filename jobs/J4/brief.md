# J4: Scenario library, control API, acceptance gate

Phase 1, job 4, the phase 1 gate. The goal: an agent names a scenario and a camera pose and gets a settled, checked frame back
(`scene land_large`, `cam land_large:wide`, `shot ...`), with frame time and memory on request, from any state of the game. Then
an acceptance script proves it holds: 20 passes in a row. J12 (core promotion), J8, J9, J23 and J28 all wait for this job.
It builds on what exists: the ctl channel, autostart and warm reset (J3), headless (J13), save tools (J14) and the campaign
console (J15). It writes a thin, checked layer on top of them, not a second copy.

Model: Sonnet. The battle script Lua API (below) holds the camera, battle speed and unit orders, so no reverse engineering is
planned. The one DLL change is a frame-time recorder behind a dev key. If a route turns out to need engine memory, a kill
criterion stops that line and the report proposes an Opus job. Budget about 300 tool calls; at the cap, stop, commit, report
what is left. At most 2 subagents, only for independent read-only work (for example, reading the historical battle scripts
while you write the presets). Waiting belongs to the harness: `job.sh` and the acceptance runner block or run in the
background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J4`). Read:
  - `docs/DECISIONS.md` (D2, D3, D11, D15, D26-D28, D30, D32)
  - `docs/plans/PLAN.md` section 5, phase 1 (scenario library, control API, gate)
  - `harness/README.md`, all of it, and `proxy/README.md` "Dev control channel", "Campaign console" and "Headless"
  - `jobs/J3/report.md` and `review.md`, `jobs/J13/report.md`, `jobs/J14/report.md` and `review.md`, `jobs/J15/report.md`
  - `jobs/J5/rules.md` rows 28, 74, 75, 77, 78, 79: this job turns them into code (deliverable 8)
- Search before writing: `python3 core/wsc.py find scenario camera ctl autostart reset shot save recipe perf`. Extend these;
  do not write a second of any:
  - `harness/core/job.sh` (lock, launch, `ctl`) and `shot.sh`
  - `proxy/napoleon/lua/{autostart,reset}.lua`, `battles/*.txt`, `probes/`
  - `saves/napoleon/{stage_save.py,load_save.sh,save_map.py,recipes/}`
  - `proxy/tools/pc_deploy.py`, `discovery/core/packfs.py` (reads any file in the packs)
- Other jobs touching the same files: J42 (CI and watcher races) is in progress and J18 (rule guards in `job.sh` and the
  watcher) is queued. Keep your `job.sh` and watcher changes small and additive, and rebase on `main` before the pull request.
- Evidence in `empire-remastered`. It is read-only: never edit, commit or push there. Port the method, not the numbers:
  - `rml_mod/dev/tools/make_fixed_sky_pack.py` (fixed sky from `battle_sky_types`)
  - `rml_mod/src/camctl.h`, `orchestrator/reports/2026-10-27_camctl-pc.md` (Empire's DLL camera; only a fallback here, see
    Kill criteria), `rml_mod/src/weather_pin.{h,cpp}` and `orchestrator/reports/2026-10-27_dllpc.md` (the rain pin)
  - `rml_mod/dev/scenarios/lighting_scene_set.json` (a golden set with poses and pinned weather)
  - `docs/learnings/LEARNINGS_HARNESS.md`: the lightcap, S04/S12 rain and `dev_fixed_sky` bullets (search "camctl" and
    "fixed_sky")

## Target facts
Recorded by J3, J13, J14 and J15. Check each again before relying on it:
- **Battle Lua API in the game's own scripts.** `profiling_scripts\landbattle x1.battle_script` (data.pack; read it with
  `packfs`) does `battle = empire_battle:new()`, `camera = battle:camera()`, `camera:move_to(target, pos, speed)`,
  `camera:position()`, `battle:modify_battle_speed(1.0)` and drives units through `battle_manager` controllers. The same
  interface runs the historical battles (`napoleon_historical_battles\<name>\<name>_battle.battle_script`). Not yet known:
  whether `empire_battle` is reachable from the state that `ctl lua` runs in (the battle root's `OnUpdatePulse`, fact
  `napoleon.lua.update_callbacks`). That is the first probe of this job.
- **Profiling scripts** for land (`landbattle x1`, `x4`) and naval (`navalbattle x1`, `x4`) battles exist in data.pack: CA's
  own scripted camera paths for performance runs. Read them before you design poses and the perf capture.
- **Determinism data:** Napoleon has the db tables `battle_sky_types`, `battles_to_battle_sky_types_junctions` and
  `battle_weather_types` (`discovery/db/tables.json`). The Lua API has `BattleWeatherTypeOptionsString` and
  `BattleWeatherAndTimeOfDayOptionsString` (custom battle setup).
- **Autostart** (J3): `battle:<preset>` for land, naval and siege, map checked; `campaign:new:mp_eur_napoleon:<faction>` and
  `campaign:<save>` (J14 staged saves). The episodic button carries no campaign key and Spain is absent
  (`napoleon.campaign.keys`).
- **Warm reset** works from a battle (27-33 s); from a campaign it does not (`napoleon.campaign.quit_to_menu`, open), so a
  relaunch is the campaign reset.
- **Campaign placement:** `teleport_to` with `PosX/PosY` from `RetrieveFactionAgentsList` (`napoleon.console.teleport_units`);
  `transport_to_region` does not move (J40 owns it). Save ids are per file: key edits by (faction, region, type) and read ids
  from the save being edited (`napoleon.save.ids_per_file`).
- **Unattended EndTurn** stops at AI diplomacy and turn-start modals (`napoleon.campaign.modal_stops_pump`). J40 item 3 owns that.
- **Headless** is the watcher's default (J13): `launch owner=<you> [size=WxH]`, status in `headless_status.json`, screenshots
  through `shot.sh`. Never `visible=1`: no sitting with Liam is planned.
- **Absolute load times vary with the PC's state** (J3: 18.2 s in one morning, 3.4 s after a restart). Baselines record the
  date, the build and a fresh-boot flag, and compare with tolerances.

## Decisions already made for this job
- **Layering.** The control API is a host-side client over `job.sh` and the ctl channel. It is game-agnostic in `harness/core/`
  (suggested: `ctl.py`, a J12 core candidate) and reads everything Napoleon-specific from the adapter, the scenarios registry
  and Lua under `proxy/napoleon/lua/`. Each verb is one call that blocks until a checked result. New proxy ctl verbs are
  allowed only where Lua cannot do the job (the frame-time recorder); add their rows to the `proxy/README.md` ctl table.
- **Every verb returns one JSON result**: `status` ok | failed | refused, `reason`, the verb's fields, `settle` (what it waited
  for and how long), `check` (what it compared, expected against got), `evidence` (paths: shot, state, log) and `start_utc`
  and `end_utc`. A failure names the step and keeps its evidence. Exit code 0 only for ok.
- **Settle is defined once and shared:** scene ready (state.json) plus N presented frames plus no new shader creation for T ms.
  Pick N and T from measurement and record them as `config_keys` or adapter fields, never as sleeps in callers. If the proxy
  cannot see shader creation through existing hooks, use frame-time stability and say so.
- **Camera through the battle script API first** (`camera:move_to` / `camera:position`). A pose is `x y z yaw pitch [fov]`
  (the scenarios schema), converted to the API's target and position. `cam` reads the position back and fails beyond a
  tolerance you measure. Campaign poses use `CampaignUI.SetCameraTarget` / `CameraPosition` / `CameraZoomTo`, with the same
  readback. Naval is a separate case: Empire's camera had no capture there, so check it rather than assume it.
- **Poses are stored by id in the scenario's `camera_poses`**, addressed `<scenario>:<pose>`. A pose that was found by key taps
  is converted to coordinates by reading the camera back, then stored. `key` stays a probe verb only (rule 78).
- **Fixed sky and weather from data first**, in this order: (1) the battle preferences and custom-battle options pin weather
  and time of day per preset; (2) a dev pack that fixes the sky (port `make_fixed_sky_pack.py` to Napoleon's
  `battle_sky_types` and junctions, served through the D27 virtual pack or a file rule, zero-touch); (3) only if a per-launch
  random state remains (Empire's rain intensity), stop that line (Kill criteria). Determinism is proved by images, not
  assumed: the same scenario and pose on two launches, compared with a pixel metric and threshold you record.
- **`order` is a minimal verb for J4.** Move or halt one named unit through a battle script controller, and check that it
  arrived within a tolerance. J28 replaces the route with the engine's command path and keeps the verb's shape, so define the
  shape for both: `order <unit> move x z [facing] | halt | formation <f>`. If controllers are unreachable from `ctl lua`, the
  verb is refused with that reason, and J28 owns it.
- **Scenarios are rows in `registries/scenarios.jsonl`** with the fields the core schema already has (`time_of_day`,
  `weather`, `armies`, `save`, `camera_poses`, `launch`, `load_time_s`, `good_for`). The schema lives in `core/` and is not
  changed here; a field you need goes in the report as a proposed core change. `launch` is the one generated command:
  `ctl.py scene <id>`. A tool generates, from the rows, whatever per-scenario files the launch needs (battle presets, prefs
  overlays, staged saves); the `tests` gate checks that rows and generated files agree.
- **Campaign mid- and late-game states are generated, never played:** from `campaign:new` or J14's saves through recipes
  (more regions, armies, buildings, technologies, treasury) and console commands, keyed by name and never by id, and
  regenerated on demand (no kept edited saves, as in J14). Recipes reuse `saves/napoleon/recipes/_common.py`.
- **Campaign reset is a relaunch** unless the quit flow is solved in at most about 10 calls (J3 open question 2). `reset`
  hides the difference and reports which path ran.
- **Liam's saves are never touched.** Stage only `zz_` copies (`stage_save.py`) and leave `save_games` as found. Keep new base
  saves under `C:\napoleon_remastered_pc\saves\` with a `j4_` name, and record their sha256 in `saves/napoleon/saves.json`.
- **Lua and kit sync is a verb:** add `pc_deploy.py sync-lua` (or extend `send`) with unique staged names and a sha check
  (J3 review item 6). No scratch helper copies files to the PC.

## Deliverables
1. **Route probe.** From `ctl lua`, in a land battle, a siege and a naval battle: is `empire_battle` (or the object the
   historical scripts use) reachable, and do `camera:position`, `camera:move_to`, `modify_battle_speed`, pause and a unit
   controller work? Also the campaign camera calls. Each answer is an `engine_facts` row with a run id. This decides the
   routes for deliverables 3 and 4.
2. **Scenario library**, every row loadable through `scene <id>`, with `load_time_s` measured and at least two poses:
   - land: small, large, 40 units (20 against 20); siege: fort, city; naval: small, large, storm. Each has pinned
     `time_of_day` and `weather`. The presets and armies are generated from the rows.
   - historical: at least one land and one naval (for example Austerlitz and Trafalgar). Find the autostart route through the
     front end's historical battle screen (`faction_selection_historical`) and add a target `historical:<key>`. Add the rest
     of the historical list if it costs little.
   - campaign: the grand campaign (`mp_eur_napoleon`) at start, mid-game and late-game. Italy and Egypt (the episodic
     screen) at start if the route takes no more than about 15 calls; otherwise record the route's state as an open fact.
   - the existing rows (`land_small`, `naval_small`, `siege_small`, the J14 campaign rows) brought to the same standard.
3. **Control API verbs** with the result contract above: `scene <id>`, `cam <scenario:pose | x y z yaw pitch [fov]>`,
   `shot <name>` (after a settle, through `shot.sh`), `order ...`, `pause on|off`, `speed <x>`, `reset [<id>]`, `perf ...`
   (deliverable 5), plus `state`. `key`, `click` and `wait` stay underneath and are marked probe-only. Host tests cover result
   building, scenario resolution, pose parsing, the tolerance checks and the refusals.
4. **Fixed sky and weather** as described in the decisions, with the determinism proof per scenario kind (land, siege,
   naval, historical, campaign) recorded as facts. A scenario that is not deterministic is marked so in its row and in the
   baseline, never silently.
5. **Frame-time and memory capture:** `perf <seconds>` at the current scene and pose. It returns frame time p50, p99 and max
   and the frame count; process address space (the 32-bit 4 GB limit matters), commit and working set; VRAM; and the build,
   backend and size. Frame times come from a recorder in the proxy's Present path behind a new dev key (default 0, release
   value 0, `config_keys` row, host tests, pass-through lint). VRAM comes from wherever it can be read without touching the
   engine (DXGI/NVAPI in the proxy, or `nvidia-smi` from a watcher job); say which. J23 builds its baseline on this verb.
6. **Acceptance script** (`harness/core/acceptance` or similar, game-agnostic, scenario list from the adapter). One pass:
   check that `Napoleon.exe`'s sha1 equals the pin (rule 28); launch headless; `scene` every kind (land, siege, naval,
   historical, campaign); one `cam` pose and one `shot` each; `perf 10` once; a warm reset; a relaunch; exit. Each step is
   compared with the **committed baseline file** (rule 74): its load time is within a tolerance, its shot matches the
   baseline shot within the determinism threshold, and every settings file is byte-identical after the exit. It runs N passes
   by itself in the background, stops at the first failure with evidence, and appends one line per pass (pass number, build
   id, watcher version, kit, results) to a committed ledger.
7. **The gate passes 20 times in a row** on the final build (rule 79), at one size you name (1080p unless measurement argues
   otherwise; record why). Any failure resets the count; fix the cause first, then restart.
8. **Rules into code:**
   - **Row 77:** every verb waits for its settle and checks its result. A host test fails when a verb returns ok without a
     `check` field.
   - **Row 78:** a test refuses `key` / `click` camera moves in scenario rows, generated files and the acceptance script.
   - **Row 79:** a check (in the `tests` gate, through `wsc jobs check` or `pr_policy.py`) refuses a `job/` branch that changes
     `proxy/` or `harness/` unless the acceptance ledger holds 20 consecutive passes on that branch's final DLL and watcher
     build. It applies to branches after this job, never to this job's own earlier commits. Give it a failing fixture.
   - **Row 74:** the baseline file has a schema and a checker; acceptance refuses to run without it.
   - **Row 28:** the exe sha1 check in every acceptance pass (J18 adds the check after every install; do not duplicate its
     guard, call it if it has landed).
   - **Row 75:** `wsc jobs view` also shows the PC state (lock holder, watcher version, installed kit, the last acceptance
     pass and its result) when run on the PC. Usage numbers have no source yet: the report names one or hands the row to a
     meta job.
9. **Carried from J14 (review "Later"):** the round trip on a save from a second turn, and ladder C's EndTurn survival (fact
   `napoleon.save.endturn_survival`), through `load_save.sh --end-turn`. Run them only if J40 has landed an answer for the AI
   diplomacy modal. Otherwise leave both facts open, name J40, and spend nothing on the modal. Note the first time
   `load_save.sh`'s stop after 4 silent polls fires in a real run.
10. **Registries:** a `scenarios` row for every scenario; `tools` rows for every new tool; `config_keys` for the settle
    parameters and the frame-time key; `engine_facts` for every finding (routes, determinism, settle numbers, perf capture
    sources), each with a run id.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py`, sha-checked; every launch uses
`dev.skip_intro=1`. No sitting with Liam is needed. If a step would need a visible window, stop and ask. Results go in a dated
run report under `harness/runs/` or `proxy/runs/`, with job ids, ctl results and screenshots.

Steps:
- a) Dev keys off: the J3 behaviour is unchanged.
- b) Deliverable 1 (the route probe).
- c) Every scenario through `scene`, two poses each, determinism shots on two launches.
- d) `perf` on land_small and the 40-unit battle at the acceptance size.
- e) The acceptance run to 20 in a row.
- f) Uninstall is byte-identical; `save_games` and every settings file are as found.

## Kill criteria
- **Battle script objects are unreachable from `ctl lua`** after about 20 calls (direct construction, the battle's script
  environment, attaching a `.battle_script` to a custom battle preset): stop the camera, speed and order lines. Store poses as
  coordinates read back where possible. Propose an Opus job porting Empire's `camctl` to the proxy. The gate is then not
  passed: say so plainly.
- **Sky or weather is still random per launch after the data routes:** do not reverse engineer a pin. Mark those scenarios
  non-deterministic and propose a follow-up job (Empire's `weather_pin` route).
- **Any crash or hang during a scenario:** read WER and the watcher's hang folder first. Two for the same cause: stop that
  scenario, report with the dumps, and keep the rest of the library going without it.
- **The acceptance run fails for three different causes** that you cannot fix in the harness or the tools: stop and report
  every cause with its evidence.
- **A historical or episodic route costs more than its allowance** (see deliverable 2): record the route's state as an open
  fact and move on.
- **Any write into the game folder outside a deploy, into `core/`, or into Liam's saves would be needed:** stop and ask Liam.

## Finish
Write `jobs/J4/report.md`. Cover:
- what exists: the verbs, the scenario table (with load times and determinism), the acceptance script, the baseline and the
  ledger
- the route probe answers, with run ids
- the 20-pass evidence (ledger lines and run ids)
- the rules turned into code (rows 28, 74, 75, 77, 78, 79), each with its test
- deviations from this brief and why
- proposed core changes (schema fields) and follow-up jobs
- what moves to the core in J12
- open questions, listed separately for J8, J12, J23 and J28

Then `wsc reg set jobs J4 status=review report=jobs/J4/report.md`.
