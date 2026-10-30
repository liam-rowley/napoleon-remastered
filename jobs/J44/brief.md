# J44: Scenario library and the 20-pass acceptance gate

Phase 1, the phase 1 gate. J4 built the control API (`harness/core/ctl.py`), the frame-time recorder and the acceptance script's
host side, but stopped at its kill criterion with no camera route. J43 found the route: `cam`, `pause` and `speed` return checked
results in land, siege and naval battles (run `harness/runs/20261030_j43pc`). This job finishes J4 on that route: run every verb on the
PC and measure its settle values, build the scenario library with fixed sky and weather and two poses each, prove determinism per kind,
wire `acceptance.py` to the PC, commit the measured baseline and pass 20 in a row. J8, J9, J12, J23 and J28 wait on this job.

Model: Sonnet. No reverse engineering is planned: the camera, speed and pause routes exist, the sky pin goes through data first, and a
route that would need engine memory stops at a kill criterion and is proposed as an Opus job. Budget about 300 tool calls; at the cap,
stop, commit, report what is left. At most 2 subagents, only for independent read-only work (for example, reading `battle_sky_types` and
the historical battle data from the packs while you write presets). Waiting belongs to the harness: `job.sh`, ctl requests and the
acceptance runner block or run in the background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J44`). Read:
  - `docs/DECISIONS.md` (D2, D3, D11, D15, D26-D28, D30, D32)
  - `docs/plans/PLAN.md` section 5, phase 1 (scenario library, control API, gate)
  - `jobs/J4/brief.md` (its Decisions and Deliverables 2, 4-8 are this job's, unless changed below), `report.md` and `review.md`
    (round 2 "Still open" and round 1 items 7 and 9)
  - `jobs/J43/report.md` and `review.md`, and `harness/runs/20261030_j43pc/README.md`
  - `harness/README.md`, `proxy/README.md` "Dev control channel" and "Headless", `harness/core/ctl.py` (header = result contract),
    `harness/core/acceptance.py`, `harness/napoleon/adapter.json` `ctl`
- Search before writing: `python3 core/wsc.py find scenario camera ctl autostart reset shot perf sky weather acceptance baseline`.
  Extend what exists: `ctl.py`, `campose.py`, `acceptance.py`, `proxy/napoleon/lua/{autostart,reset}.lua`, `battles/*.txt`, `ctl/*.lua`,
  `saves/napoleon/{stage_save.py,load_save.sh,recipes/}`, `proxy/tools/pc_deploy.py` (`sync-lua`), `discovery/core/packfs.py`.
- Other jobs touching the same files: J16 (proxy device and headless code) and J18 (rule guards in `job.sh`, the watcher and
  `pc_deploy`) are queued. Keep `job.sh`, watcher and `pc_deploy` changes small and additive; rebase on `main` before the pull request.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, not the numbers:
  `rml_mod/dev/tools/make_fixed_sky_pack.py`, `rml_mod/dev/scenarios/lighting_scene_set.json`, `rml_mod/src/weather_pin.{h,cpp}` with
  `orchestrator/reports/2026-10-27_dllpc.md`, `docs/learnings/LEARNINGS_HARNESS.md` (search "fixed_sky", "lightcap", "S04").

## Target facts
Recorded by J3, J4, J13, J14 and J43. Check each again before relying on it:
- **Camera** (`napoleon.battle.camera_route`): `wsp.cam_set` behind `dev.camera=1`; readback by `BattleUI.BackProjectPosition` and
  `campose.py`, worst error 0.0004 m and 0.0003 degrees over 13 poses; settle is the next frame; one `ctl cam` takes 2.9 to 4.0 s.
  **With `dev.camera=0`, `cam` fails at step set** (`tests/test_ctl.py`), so every launch this job makes for `cam` needs `dev.camera=1`.
- **Clamps** (`adapter.json` `ctl.routes.camera.<kind>.clamps`): pitch [-45, 45], vertical fov 70.0, height above terrain [2.5, 44.556] m
  on land_small and siege_small, [15, 150] m above the sea in naval_small. Height depends on the terrain under the camera: a pose stored
  in a row must be checked against its scenario's clamps before it is committed.
- **Speed and pause** (`napoleon.battle.speed_route`): rates 0 / 0.43 (slow; `speed 0.5` names it) / 1 / 2 / 4; refused in deployment.
  Deployment ends with `BattleUI.InformOfDeploymentFinished` (`lua napoleon_remastered/lua/ctl/speed.lua -- start`).
- **Kind detection**: without a scenario row loaded, `ctl.py current_kind` sees a siege as land. Every acceptance and library step goes
  through `scene <id>` so the row's kind chooses the route.
- **Lighting varies per launch**: the same pose on two launches read back identically, but the shots differed by mean 16.4/255
  (`repeat_a.jpg`, `repeat_b.jpg`): the custom battle picks time of day or weather per launch. The sky pin is the determinism work.
- **Engine Lua**: never `string.find`, `string.sub` or `gmatch` (`napoleon.lua.string_find_stalls_pump`; lint in `tests/test_repo_rules.py`).
  The battle root's `OnUpdatePulse` pump lasted an 11-minute battle with clean chunks.
- **Campaign camera** (`napoleon.campaign.camera_route`, open): `CameraPosition`/`CameraTarget` read; the setters were not usable
  (`SetCameraZoom` corrupted the stack). Campaign rows get poses only if a route is found within the allowance (Kill criteria).
- **Warm reset** works from a battle (27-33 s); a campaign reset is a relaunch (`napoleon.campaign.quit_to_menu`, open).
- **Absolute load times vary with the PC's state** (J3: 18.2 s and 3.4 s on one morning): baselines carry date, build and a fresh-boot flag.
- **The PC game folder is not as found today** (J43 review finding 1): the watcher's headless auto-restore wrote main's
  `napoleon_remastered.ini` back 2 s after J43's uninstall. Compare the folder with `C:\napoleon_remastered_pc\snapshots\pre_install_20261030T090208Z.json`
  before the first install; if the stray ini is still there, stop and ask Liam (an install would treat it as found).

## Decisions already made for this job
- **J4's decisions stand** (layering, the one-result contract, settle defined once, poses by id, scenarios as rows with generated
  launch files, generated campaign states, Liam's saves never touched, `sync-lua`), with these changes:
  - The camera, pause and speed routes are J43's. `order` stays refused (J28).
  - The settle values in `adapter.json` `ctl.settle` are measured on the PC here (frames, quiet ms, timeout per kind) and the note
    "provisional" goes. Record the run id beside them.
- **`scene <id>` launches with the dev keys the row's verbs need** (`dev.camera=1`, `dev.ctl=1`, `dev.lua_bridge=1`, `dev.state_json=1`,
  `dev.skip_intro=1`), from the adapter, not from callers. A row may name `deploy: end` so `scene` ends deployment after the settle
  (pause, speed and battle-time shots need it); the default leaves deployment running.
- **Sky and weather from data first**, J4's order: (1) battle preferences and custom-battle options per preset; (2) a dev pack fixing
  `battle_sky_types` and its junctions through the D27 virtual pack or a file rule; (3) a random state that remains stops that line.
  Determinism is proved by shots on two launches with a metric and threshold you record per kind, and the camera readback must match
  too (J43 showed it does).
- **The baseline** (`harness/acceptance/baseline.json`, schema and checker from J4) is measured on this job's final build, never written
  by hand. Committing it turns rule 79 on for every later branch that touches `proxy/` or `harness/`.
- **Before the baseline lands** (J4 review round 2): `tools/pr_policy.py acceptance_active` must not import `harness/core/acceptance.py`
  from the branch being judged. Load it from the base (`show(a.base, ...)`) or keep a copy of the check in `pr_policy.py`, with a test
  that a branch weakening `baseline_problems` does not switch the rule off for itself.
- **Ledger lines are evidence, not claims** (J4 review 7): each line carries the run id and the evidence path, and rule 79's check
  refuses a line whose run folder is not committed. Test with a failing fixture.
- **Rule 28**: the exe sha1 check in every pass. If J18 has landed its guard, call it; otherwise keep `exe_pin_ok` and say so.
- **Rule 75**: `wsc jobs view` shows the PC state when run on the PC (lock holder, watcher version, installed kit, last acceptance pass
  and its result) and names a usage source, or the report hands the usage source to a meta row with the reason.
- **J14 carry-over** (J4 deliverable 9) only if J40 has answered the AI diplomacy modal. J40 is `needs_brief` today: check once, and if
  it has not landed, leave both facts open, name J40 and spend nothing.

## Deliverables
1. **Verbs on the PC**: `scene`, `shot`, `reset`, `perf`, `state` run through `ctl.py` on the PC in every battle kind and the campaign,
   with the result JSONs in the run folder; measured settle values in `ctl.settle`; `perf` with VRAM (say the source: `nvidia-smi` from a
   watcher job or the proxy). The `ctl.py` header and tools rows drop "untested on the PC" for what ran.
2. **Scenario library** (J4 deliverable 2): land small, large, 40 units (20 against 20); siege fort and city; naval small, large, storm;
   historical land and naval (a `historical:<key>` autostart; the rest of the list if cheap); grand campaign start, mid and late; the
   existing rows brought to the same standard. Each row: pinned `time_of_day` and `weather`, measured `load_time_s` with date and run, and
   at least two `camera_poses` stored as coordinates read back and checked against the kind's clamps (campaign rows: only if the campaign
   camera route is found, else marked open). The `tests` gate checks rows and generated files agree.
3. **Fixed sky and weather and the determinism proofs** per kind (land, siege, naval, historical, campaign) as `engine_facts` with run
   ids. A row that is not deterministic says so, in its row and in the baseline.
4. **`acceptance.py` wired to the PC**: launch, `scene` every kind, one `cam` pose and one `shot` each, `perf 10` once, a warm reset, a
   relaunch, exit, settings files byte-identical after the exit, each compared with the baseline. It runs N passes by itself in the
   background, stops at the first failure with evidence, and appends one ledger line per pass.
5. **The measured baseline** committed, with the `acceptance_active` fix and the ledger evidence check above.
6. **The gate: 20 passes in a row** on the final DLL build and watcher version, at one size you name (1080p unless measurement argues
   otherwise; say why). A failure resets the count; fix the cause, then restart.
7. **Rule 75** as above.
8. **Registries**: `scenarios` rows; `tools` rows for new tools; `config_keys` or adapter fields for settle and thresholds; `engine_facts`
   for routes, determinism, settle and perf sources, each with a run id.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py` (Lua by `sync-lua`), sha-checked; every launch uses
`dev.skip_intro=1`. No sitting with Liam is needed; if a step would need a visible window, stop and ask. Results go in a dated run report
under `harness/runs/` with job ids, ctl results and screenshots.

Steps:
- a) The game folder against the pre-install snapshot (Target facts, last bullet). Dev keys off: the J3 behaviour is unchanged.
- b) Every verb on the PC, settle measured (deliverable 1).
- c) Every scenario through `scene`, two poses each; determinism shots on two launches per kind.
- d) `perf` on land_small and the 40-unit battle at the acceptance size.
- e) The acceptance run to 20 in a row.
- f) Uninstall is byte-identical, checked **after** the game lock is released and the profile restored; `save_games` and every
   settings file are as found.

## Kill criteria
- **Sky or weather still random per launch after the data routes** (about 30 calls): do not reverse engineer a pin. Mark those rows
  non-deterministic, keep them out of the shot comparison in the baseline (load and readback still count), and propose an Opus job for a
  weather pin (Empire's `weather_pin` route).
- **The campaign camera** gives no checked setter after about 15 calls: campaign rows keep the default camera, `cam` stays refused for
  campaign with its fact, and the acceptance pass shoots the campaign at the default view.
- **A historical or episodic route** costs more than about 15 calls: record its state as an open fact and move on.
- **Any crash or hang** during a scenario: read WER and the watcher's hang folder first. Two for the same cause: stop that scenario,
  report with the dumps, keep the rest of the library going without it.
- **The acceptance run fails for three different causes** you cannot fix in the harness or the tools: stop and report every cause with
  its evidence. The gate is then not passed: say so plainly.
- **Any write into the game folder outside a deploy, into `core/`, or into Liam's saves would be needed**: stop and ask Liam.

## Finish
Write `jobs/J44/report.md`. Cover:
- the verbs as run on the PC, with the measured settle values
- the scenario table: kind, load time, poses, determinism, run ids
- the sky and weather route per kind, and what stays non-deterministic
- the baseline, the 20-pass evidence (ledger lines and run ids), the size and why
- rules 28, 74, 75, 77, 78, 79 as they now stand, each with its test, and the `acceptance_active` and ledger-evidence fixes
- deviations from this brief and why
- open questions, listed separately for J8, J12, J23 and J28

Then `wsc reg set jobs J44 status=review report=jobs/J44/report.md`.
