# J29: Alt-drag move and Alt+Ctrl-drag rotate

Phase 4, controls, second job (PLAN section 5, phase 4; D1). Alt+left-drag moves the selected units to the drawn line, with the
frontage taken from the drag length. Alt+Ctrl+left-drag rotates the selection in place. Every other mouse and key message stays
vanilla. A preview of where the units will stand is drawn while the button is down; the orders go out once, on release, through
J28's route. This job is the Napoleon half: the adapter, the bindings, the proof and Liam's sign-off. The game-agnostic half (the
gesture state machine with its host tests, the window-message hook, the overlay drawing) is a warscape-core job, `W<n>` below, and
this job starts only when that job's tag is pinned here.

Model: Sonnet, medium effort (the D15 default). The reverse engineering is done (J28, J43) and the heavy C++ is in the core job;
what is left is an adapter over known offsets, registry rows, a harness walk and the 20-pass run. An adapter step that needs new
engine reverse engineering stops at a kill criterion and is proposed as an Opus job. Budget about 200 tool calls; at the cap, stop,
commit, report what is left. Subagents are not needed (one read-only one to read Empire's tests is fine). Waiting belongs to the
harness: `job.sh`, ctl requests and the acceptance runner block or run in the background inside one call; never poll with repeated calls.

PC: yes (needs_pc), unattended and headless through the watcher for everything except the last step, which is Liam playing a real
battle. Rule 79 applies (below): the branch changes `proxy/` and moves the core pin, so it needs 20 consecutive acceptance passes on its final DLL build id.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J29`; "The core": **never edit `core/`**). Read `docs/DECISIONS.md` (D1, D15, D30, D44),
  `docs/plans/PLAN.md` phase 4, `docs/REVIEW.md` (Rule 79), `core/docs/PROXY_ORDERS.md` (the contract J29 calls),
  `jobs/J28/report.md` (C++ entry points for J29, Open questions), `jobs/J21/report.md` (the Alt rows and the free-key table),
  `jobs/J46/report.md` (the `land_40` row and the scenario table), `jobs/J43/report.md` (the camera readback).
- **Gate zero, before anything else:** the core must already carry the gesture layer. Check `ls core/proxy/src/gesture_*.h` and
  `cat core/VERSION`. If the gesture headers are not there, the core job is not merged or not pinned: stop at once (kill criterion 1).
  Do not write them here and do not edit `core/`.
- Facts to start from (all registry ids; read them with `python3 core/wsc.py find <words>` and re-check any you rely on):
  `napoleon.battle.camera_route` (verified 2026-10-30, run 20261030_j43pc: the camera mode holds position at +8 and target at +0x14,
  the pinhole fit gives a 70.0 degree vertical field of view to 0.001 px, pitch clamp [-45, 45], height clamp [2.5, 44.556] m),
  `napoleon.battle.order_route`, `napoleon.battle.order_threads` (verified 2026-11-02, run 20261102_j28pc: Present, the window
  procedure and the Lua pump are one thread, so a gesture may call `OrdersMove` from its Present tick),
  `napoleon.battle.order_deployment` (verified 2026-11-02, run 20261102_j28pc: orders in the deployment phase do not walk; **gestures are inert there**),
  `napoleon.battle.selection_source`, `napoleon.battle.unit_layout`, `napoleon.battle.bearing_convention` (0 = +z, 90 = +x, clockwise from above),
  `napoleon.battle.frontage_ranks` (open: ranks not found, depth is derived), `napoleon.battle.order_sound` (open, owned by this job).
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, check every fact again on Napoleon:
  `rml_mod/src/gesture_sm.h` (the state machine and its transition table in the header comment), `gesture_math.h`, `gesture_feed.h`,
  `gesture_group.h`, `gesture_v4.h`, `gesture_v5.h` (rotate by horizontal mouse, orbit, per-unit fallback), `gesture_marker.h` and
  `rml_mod/src/tests/gesture_test.cpp` with `gesture_vectors.txt` (the host tests); the run notes `rml_mod/docs/runs/20261026_controls_v5/README.md`.
  **Not ported, on purpose**: the R32F depth-prepass pick (`gesture_ground.h`, the men-in-prepass jitter), the camera vertex-shader
  capture (`gesture_cam.h`) and the engine's per-man marker call (`gesture_marker.h` style 1). Napoleon has an exact camera readback instead (below).
- Search before writing: `python3 core/wsc.py find gesture hotkeys order camera selection config`. Extend `proxy/napoleon/adapter.cpp`,
  `harness/napoleon/adapter.json`, `registries/hotkeys.jsonl` (through `wsc reg`), `tests/test_hotkeys.py` and `tests/test_ctl.py`.
- Other jobs touching the same files: J30 (RmlUi host, queued; its core half is warscape-core W2) also needs a window-message hook.
  Only one path may subclass the game's window procedure; see the core job below. J8, J16, J27, J47 and J60 may also change the DLL
  inputs: run `git log origin/main -- proxy core` before the measure run and merge `main` in (never rebase) if they did.

## The route, and why (chosen 2026-11-03 from the evidence)
- **Selection, state, orders**: J28's route as built: `OrdersSelection`/`OrdersArmy`/`OrdersUnit` to read, `OrdersMove` on the engine
  thread (the Present tick) to order. Passed on `land_small` and `siege_small` (2026-11-02, run 20261102_j28pc); no new engine site.
- **Where the cursor lands on the ground**: the camera pose is exact and readable (fact above), so the pick is geometry: the ray through the cursor pixel
  from the camera mode's position and target, a 70 degree vertical field of view and the client aspect, met with the ground. First the horizontal plane through the
  selection's mean ground height, then two or three refinements of the height at the hit point with the engine's own ground projector
  (`battle.ground_project`, already used by `OrdersMove` for y). This replaces Empire's depth-prepass pick, which needed shader hooks and had the men-in-the-pick jitter.
  It is checked, not trusted (step 3): a picked point is projected back with `BattleUI.BackProjectPosition` and must land within 1 px of the cursor.
- **The preview** (the row asks for a route; three were weighed):
  1. *Proxy-drawn footprints in Present* (**chosen**): each unit's ordered rectangle (frontage x derived depth, from J28's measured 1.75 m at 31.9 m for 120 men),
     a front-edge tick for facing, drawn as screen-space lines and translucent quads projected from the same camera maths, with `DrawPrimitiveUP` before the
     real Present. Needs no engine site and no other job: the projection is the same maths as the pick, host-testable, and the headless walk can read the planned
     rectangles back as numbers. Cost: it is not the vanilla per-man marker look.
  2. *The engine's own per-man markers* (Empire controls-v1b): looks like vanilla right-drag, but needs a Napoleon-side reverse engineering of the marker call and
     a crash-safe call from the render tick. Not reachable in this job's budget; proposed as a later Opus job if Liam wants the vanilla look (open question 1).
  3. *An RmlUi overlay*: waits for J30/W2 (not a dependency of this job), and its text and shapes cannot show per-unit footprints better than (1).
  Footprints are draped: each corner uses the ground height at its own x, z. A unit whose order would be refused (`CheckMove`, off the map, a target the
  ground projector cannot place) draws red; units that would be refused are skipped at release, the rest are ordered (as Empire's per-unit fallback, without
  the search).

## Behaviour (what the state machine and the adapter must give)
- **Eligible**: a land or siege battle, not the deployment phase, a non-empty selection of orderable units (`UnitOrderable`). Naval, campaign and
  battle-less screens: the layer is inert and every message passes. A press that is not eligible passes to the engine.
- **Alt+left press on the world** starts Pending (the press is swallowed). Movement past the drag threshold makes it Active; a release without a drag
  replays a plain click at the press point (Alt+click still selects). Right press, Escape, focus loss, or a move without the button cancels, and the rest
  of that press is swallowed so the engine never sees a lone left release (Empire's Drain rule; ported with its tests).
- **Alt+drag = move to the drawn line.** The press point and the cursor are the two ends of the line on the ground. The selected units are laid along it in
  their current left-to-right order across the line, each taking an equal share of the length as its frontage, clamped to the unit's own limits; a drag shorter than
  a few metres keeps each unit's own width and moves the block centre to the press point. Facing is the line's normal on the side the selection already faces.
  One unit: its frontage is the line length (clamped). The clamps are `napoleon.battle.frontage_ranks`' neighbours: measure the engine's accepted min and max
  width per unit class with J28's `order` verb on `land_40` (a few orders each), record a fact, and put the numbers in the adapter, never in the core.
- **Alt+Ctrl+drag = rotate in place.** Left-right mouse travel turns the whole selection rigidly about the selection's centre (one unit: about itself); theta is
  absolute since the rotate began (Empire's v5 orbit, so a full circle of travel returns to the start). Pressing or releasing Ctrl mid-gesture switches
  between move and rotate (Empire controls-v2, with its rebase of the pose). The pivot offset (Empire used 2 m ahead) is a config value with default 0 here, so "in place" is literal; Liam may change it at sign-off.
- **Release = commit**: one `OrdersMove` per unit with its x, z, facing and width, on the engine thread, in one Present tick. A bodyguard that will not hold a facing
  (J28 open question) is treated as facing-free in the readback only, never skipped in the order.
- **Vanilla untouched**: every other message passes unchanged, including plain left-drag box select, right-drag orders, Alt+key chords (the vanilla Alt+S, Alt+M,
  Alt+1 to Alt+9 rows of `registries/hotkeys.jsonl`) and above all **Alt+F4 and Alt+Tab: key messages are never swallowed by the layer, only mouse messages inside a gesture**.
  Host tests in the core job pin this; the harness walk counts passed and swallowed messages.

## The core job (this brief does not do it)
The core is pinned; the following is game-agnostic C++ and goes to warscape-core as a `job/W<n>` with its own brief (the orchestrator writes it from this
section; the number is the next free `W` id). Recommended model there: Opus (DLL work in a 32-bit process across the window procedure and the D3D9 device). J29 plans no edit of `core/`.
1. `core/proxy/src/gesture_*.h`: the ported state machine, math (pick ray, projection, line layout, orbit), feed and footprint plan, with `proxy/tests/test_gesture.cpp`
   porting Empire's host tests and `gesture_vectors.txt` (sections for the state machine, math vectors, the Ctrl switch, v4 and v5, the drain rules, plus new ones for
   the line layout and the ray pick); no Windows types in the headers.
2. A window-message hook for the gesture layer that coexists with W2's input routing (one subclass of the game's window procedure, ordered: RmlUi panels first, then
   gestures, then the game). If W2 is not merged when this is built, it builds the shared router and W2 adopts it; the orchestrator sequences the two.
3. A D3D9 overlay in the Present path (lines and translucent quads from the plan, device state saved and restored), a `CameraRead` beside `CameraSet` (position and
   target from the camera mode, through `CameraAdapter`), `GroundAt(x, z)` over the engine ground projector, and a `GestureAdapter` in `adapter.h` (selection feed, the
   frontage clamps, the click/drag thresholds, the key bindings as data).
4. A ctl `gesture` verb (`gesture press|move|release|cancel` with screen coordinates and the modifier set, `gesture plan`, `gesture info`) that feeds the **same
   entry point as real window messages** and returns the plan and the counters, so the headless walk exercises the whole layer without a physical mouse (rules 77, 78: no ok without a readback).
   A config key (working name `controls.gestures`; the `config_keys` row, default on in release) and docs in `core/docs/`. A core tag, and Liam merges it (as for J28).
The core job's own acceptance is host tests green, null-game smoke, and `docs/PROXY_GESTURES.md`; the proof on the real game is this job.

## Decisions already made for this job
- **Line semantics over Empire's grab**: the row says "moves the selection to the drawn line (frontage from the drag length)", so the press is one end of the line, not
  a grab point (open question 2 asks Liam to confirm at sign-off).
- **No order is sent while dragging**; only the release commits. No reach search while dragging (Empire's v4 finding).
- **Single-player land and siege only.** Naval waits for J60's ship orders (`napoleon.battle.ship_orders`).
- **The player's ini**: gestures need the orders route, which is a dev key (`dev.orders`, omitted from the player ini by D46/J38). Do not change D46 here. This job
  keeps `dev.orders` on in `ctl.launch.keys` and records in the report what J38 must do to ship gestures (open question 3).
- **Order sound**: observe it, do not fix it. One commit sends one order per unit in the same millisecond; Empire heard a stacked click. Liam's play run answers
  `napoleon.battle.order_sound`; a fix (Empire hooked the Miles sound calls) would be a follow-up job.
- Lua rules: never `string.find`, `string.sub` or `gmatch` in engine Lua (`napoleon.lua.string_find_stalls_pump`).

## Deliverables
1. **Napoleon adapter**: `GestureAdapter` in `proxy/napoleon/adapter.cpp` (camera read offsets with their site rows, selection feed, thresholds, frontage clamps from step 2),
   the shipped ini key, the pin bump to the core tag, every new offset in `engine_sites` or an `engine_facts` row with a dated run id.
2. **Frontage facts**: the engine's accepted min and max width per unit class measured with `ctl.py order`; fact(s) with run ids.
3. **Pick and preview proof** (headless, `land_40`, `siege_small`): for 10 cursor points across the screen at the deploy and turned poses, the picked ground point projected back by
   `BackProjectPosition` lands within 1 px; the planned rectangles for a 20-unit line equal the geometry computed independently in the test; the red/skipped cases are shown.
4. **Move and rotate walk** through `ctl gesture` on `land_40`: select all infantry (the call J28's step b used), then
   (a) Alt+drag a line 60 m wide: all 20 units stand on the line at the planned frontage (centre within 0.6 m, facing within 1 degree, width exact: J28's tolerances) after the settle;
   (b) Alt+Ctrl+drag a quarter turn: every unit's bearing changes by 90 degrees +- 1 and the block centre stays within 0.6 m;
   (c) Ctrl switched mid-gesture, a cancel (right press, Escape) sends no order, a release without a drag sends none and passes a click;
   (d) in the deployment phase, with an empty selection, on a naval scene and in the campaign: no swallowed message, no order, `gesture info` says why;
   (e) plain left-drag, right-drag and key messages are passed untouched (counts), and Alt+F4 / Alt+Tab key messages are never swallowed.
   Results as dated runs under `harness/runs/`, every ok with its readback. Add fixtures to `tests/test_ctl.py` for the new verb's parser and route block in `harness/napoleon/adapter.json`.
5. **Bindings**: rows `mod.gesture.move` (`Alt+LeftDrag`) and `mod.gesture.rotate` (`Ctrl+Alt+LeftDrag`), context `battle_land`, source `mod`, added through `python3 core/wsc.py reg add hotkeys`
   (the binding grammar takes a CamelCase key name; if it rejects `LeftDrag`, extend `tools/verbs/hotkeys.py`'s key names, not the schema). `python3 core/wsc.py hotkeys check` green with no clash, and a case in `tests/test_hotkeys.py` that the gesture rows
   are mouse bindings, hold Alt, and are not F4 or any OS combo. The clash gate is the Alt+F4 guard (Gate of phase 4).
6. **Gate**: host tests green (the core job's `test_gesture.cpp` run through `build.sh tests` here too), `python3 core/wsc.py gates` green, `dev.gestures`-equivalent key on in
   `ctl.launch.keys` so every acceptance pass runs with the layer idle, then 20 consecutive acceptance passes (Rule 79).
7. **Liam's feel sign-off** (the phase 4 gate): a checklist in the report for a real battle on `land_40` with Liam's own mouse: move a line, rotate, Ctrl switch mid-gesture, cancel, Alt+click select,
   box select and right-drag orders untouched, the preview readable at low and high camera, the order sound. The job reaches `review` without it and says so; the verdict is Liam's.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py`, sha-checked; every launch uses `dev.skip_intro=1`; the game lock is held by the job's owner id.
Steps: (a) the game folder against `C:\napoleon_remastered_pc\snapshots\pre_install_20261030T090208Z.json` before the first install; (b) frontage clamps on `land_40`;
(c) the pick proof; (d) the walk (deliverable 4) on `land_40` then `siege_small`; (e) `acceptance.py measure` is not needed (the baseline is unchanged unless a scenario
changes); (f) the 20 passes in the background inside one call; (g) uninstall byte-identical to the snapshot, the lock released, the profile restored, no `zz_` file in `save_games`,
Liam's settings and saves as found. A dated run report under `harness/runs/`.

## Rule 79
The branch changes `proxy/` and moves the core pin so the core's own `proxy/` changes: it needs 20 consecutive acceptance passes on its final DLL build id and watcher version
(`CLAUDE.md`, "Rule 79 and history edits"; ledger lines with run ids and committed evidence, `acceptance.py streak` printed in the report). Finish every `proxy/` change and the pin
bump before the run, merge `main` in (never rebase) if `git log origin/main -- proxy core` shows DLL-input changes since your base, then run. A later change to the DLL inputs needs a new run.

## Kill criteria
- **The core gesture layer is not in the pin** (gate zero): stop, write nothing but a short report `jobs/J29/report.md` naming the missing core job and tag; status stays queued for the orchestrator.
- **The adapter needs new engine reverse engineering** (a camera read that is not at the known offsets, a ground height the projector cannot give, a window procedure the layer cannot subclass on
  Napoleon): about 25 tool calls on it, then record the facts as open and propose an Opus job. Do not write game memory beyond J28's route.
- **The pick proof fails** (a picked point more than 2 px from the cursor after the camera maths is checked against `cam read`): stop that line after about 30 tool calls, report the measured
  error table and the likely cause (aspect, fov, near plane); do not fall back to a depth-prepass pick.
- **The walk's orders miss J28's tolerances** for a reason in the layer (not the engine's own unreachable targets): about 30 tool calls to fix; then report.
- **The 20-pass run** fails for three different causes you cannot fix: stop, report each cause with its evidence, and say plainly that the gate is not passed. A failure resets the count.
- **Any crash or hang** in a scenario: read WER and the watcher's hang folder first; two for the same cause, drop that scenario and go on.
- **Anything that would write into the game folder outside a deploy, `core/`, Liam's saves or preferences, or add a second window-procedure hook**: stop and ask Liam.

## Finish
Write `jobs/J29/report.md` with these headings: `## What was built`, `## Evidence` (the pick table, the walk table, the 20 passes with `acceptance.py streak`, run ids),
`## Deviations` (from this brief, and why), `## Open questions`, `## Liam's feel checklist`. Open questions to carry: (1) vanilla-look markers (engine per-man markers) as an Opus job;
(2) line semantics against the grab, and the rotate pivot; (3) how the player's ini enables `dev.orders` for release (J38); (4) the order sound; (5) the facing-free bodyguard; (6) whether a grouped
selection (Empire's `gesture_group.h` case) reaches `OrdersSelection`. Then `wsc reg set jobs J29 status=review report=jobs/J29/report.md`.
