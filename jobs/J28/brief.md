# J28: Battle unit control route

Phase 4, controls, first job. Give the proxy a checked way to read the player's selection and live unit state (position, facing,
frontage, ranks) from engine memory and to give units move, face and formation orders through the engine's own command path, and expose
it as the control API's `order` verb. Empire's route (c), re-found on Napoleon.exe. J29 (Alt+drag move, Alt+Ctrl+drag rotate) is built
on this job's C++ entry points and nothing else; PLAN section 5, phase 4.

Model: Opus, reason: reverse engineering on Napoleon.exe (UNIT layout, command objects, the order queue), a proxy DLL feature that calls
engine functions in a 32-bit process, and crash reading (D15). Effort high. Budget about 350 tool calls; at the cap, stop, commit, report
what is left (cut line in "Order of work"). Subagents (D34) only for independent read-only work, for example reading Empire's route while
you probe. Waiting belongs to the harness: `job.sh`, ctl requests and the acceptance runner block or run in the background inside one call;
never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J28`; "The core": the feature is game-agnostic code in a separate `warscape-core` clone beside this
  one, on a branch, as a pull request with host tests, then a tag (Liam merges and tags, as for J8 and J30) and the pin bump here; "Exe
  stays vanilla"). Read `docs/DECISIONS.md` (D2, D15, D26, D30, D34), `docs/plans/PLAN.md` phase 4, `proxy/README.md` ("Battle camera
  (J43)" is the model feature: `core/proxy/src/camera.{h,cpp}`, `CameraAdapter` in `core/proxy/src/adapter.h`, `wsp.cam_set` in
  `core/proxy/src/luabridge.cpp`, `proxy/tests/test_camera.cpp`), `harness/README.md`, and the registry rows of J29 (what it needs from you).
- Reports to read: `jobs/J9/report.md` ("J28" under Open questions and deliverable 4), `jobs/J43/report.md` ("Unit routes for J28", the pump
  and `string.find` rule), `jobs/J44/report.md` (scenes, `--deploy end`, settle, the table of poses), `jobs/J4/report.md` (what `order`
  was meant to be and why the script route died), `jobs/J46/brief.md` (the 20 against 20 battle you do not wait for).
- **The static work is already done: start from `harness/runs/20261101_j9pc/j28_candidates.md`** (J9, static RE, nothing run): the UNIT and
  entity offsets with their proving instructions, the selection, order, queue and formation functions with guard bytes, the queue path and
  the selection holder, and what is open. Its addresses are static VAs (rebase every one). The matching `engine_sites` rows are
  `battle.selection_ctor`, `battle.selection_add_unit`, `battle.order_move_ctor`, `battle.order_move_push`, `battle.order_formation_ctor`,
  `battle.order_formation_push`, `battle.command_dtor`, `battle.unit_position_get`, `battle.unit_bearing_get` (verify-only today) and the
  camera chain `battle.camera_chain_read` (it also reads the battle owner global). Search before writing:
  `python3 core/wsc.py find battle unit order selection camera ctl`.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, check every fact again on Napoleon:
  `rml_mod/src/controls.cpp` ("step 6' route (c)": `DirectOrder`, the guard table `eng::kFns`, the UI-owner queue path),
  `rml_mod/src/unit_layout.h` (`ReadUnit`: the decode with a fake memory image, the `armyIndex` cross-check), `rml_mod/docs/runs/battle_controls/RESULTS.md`
  sections 11 to 15 (what failed: the battle-script route, posted drags, the engine's own `Current_Selection_Turn_*`; what worked; one sound per
  command), `orchestrator/reports/2026-10-23_controls-v1.md` (the accuracy numbers and the "wait for the units to settle" lesson),
  `docs/learnings/LEARNINGS_ENGINE.md` (search "route (c)", "UNIT"). **Do not try the battle-script route or posted drags again** (J28's row;
  Napoleon's script objects are unreachable too: fact `napoleon.battle.script_api_reachable`).
- Other jobs touching the same files: J46 (queued: scenario rows, `harness/` and `proxy/` presets) and J8/J16/J30 (DLL) may merge first;
  rebase on `main` before the pull request (the DLL build id hashes the DLL inputs' content, `CLAUDE.md` Rule 79 paragraph).

## Target facts
Static, from J9 (2026-11-01, `harness/runs/20261101_j9pc`); every one is checked in a run here and recorded as an `engine_facts` row
(date, run id) before anything relies on it.
- **Order chain** (Empire route (c), same shape): `Selection` object (0x44 bytes) built by `battle.selection_ctor`, units added with
  `battle.selection_add_unit` (refuses a routing or dead unit), `battle.order_move_ctor(sel, loc[5]*, int16 angle, float width, bool run,
  bool queue)`, pushed with `battle.order_move_push` onto the queue at `[[[owner global]+0xf8]+0x28048]`, released with `battle.command_dtor`
  and the engine free. The angle is the int16 binary angle of the bearing (65536 = 360 degrees).
- **Owner path:** the battle UI owner global (operand of the `battle.camera_chain_read` site) -> battle at +0xf8 -> queue at +0x28048. The
  script-interface global is not used (unknown whether it is 0 in custom battles; Empire's was).
- **Unit state:** UNIT -> entity E = `[UNIT+0xadc+4*[UNIT+0xae8]]`; position floats at E+0x6dc/+0x6e0/+0x6e4 (frame pointer E+0x6ec, 0 on
  land), facing int16 at E+0x64c, men alive `[UNIT+0x204]`, army `[UNIT+0x1ec]` with the unit list at army+0xf0 (count) and +0xf4 (UNIT*[]),
  queued orders E+0x460 (count) and E+0x418 (8-byte entries). Formation front centre and width are only inferred (UNIT+0x310 and +0x324);
  ranks have no anchor.
- **Selection:** the UI's own selection is `H = [[owner]+0x450]`, `S = H+0x20` (same Selection type; loose land units: count `[S+0x1c]`,
  UNIT*[] `[S+0x20]`; land groups `[S+0xc]`/`[S+0x10]`, entries then carry the group). `BattleUI.SelectionChanged` runs the owner update that
  rebuilds S. The UICardManager route is the Lua one: `UICardManager:Selected` returns card components and a card's own script answers
  `ItemAddress` (Empire's `CardManager():Selected()` then `ItemAddress`).
- Napoleon.exe sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, ASLR on, 32-bit; `dev.camera` shows the pattern for an engine call from the
  Lua pump (`wsp.cam_set` on the engine thread). Engine Lua never calls `string.find`, `sub` or `gmatch` (fact `napoleon.lua.string_find_stalls_pump`).

## Decisions already made for this job
- **Order of work** (so a cut by the budget costs the least; at the cap finish the item in hand, commit, and write the rest as open facts):
  1 read-only state and selection reads with the live cross-checks; 2 the move/face order on land, checked by readback; 3 the `order` verb
  with checked results and failing fixtures; 4 the siege; 5 `halt` and the formation order; 6 frontage, ranks, the run flag, the thread facts;
  7 the 20-pass run on the final build. Items 1 to 3 and 7 are the minimum J29 can build on; 4 is in the job's description; 5 and 6 may move
  to a follow-up if the cut line is reached (say so in the report).
- **Where the code lives.** The mechanism is game-agnostic and goes to warscape-core under a `[dev]` key `dev.orders` (default 0, release 0,
  a `config_keys` row, the shipped ini): `proxy/src/orders.{h,cpp}` with pure parts in a header (unit-state decode against a fake memory image
  as `unit_layout.h` does, argument checks, the degrees to int16 conversion, the settle and tolerance logic) and host tests; an `OrdersAdapter`
  in `adapter.h` (sites and offsets by `engine_sites` id, like `CameraAdapter`; nothing in the core names a game or an address); Lua
  functions on `wsp` (`wsp.unit_list`, `wsp.unit_state`, `wsp.selection`, `wsp.order_move`, `wsp.order_halt`, `wsp.order_formation`: names
  yours to choose, one table each, all refusing with a reason when `dev.orders=0`); the `order` verb in the core's `harness/ctl.py` on the
  adapter's `ctl.routes.orders` (the stub says "reachable but not implemented (J28)"). Napoleon's adapter data, the Lua chunks
  (`proxy/napoleon/lua/ctl/`), the route block in `harness/napoleon/adapter.json`, the sites, keys and tests are here. Do not edit `core/`
  in this repo.
- **Engine calls only, no detours (D2, D26).** Same as the camera: the functions are called, never patched; the sites are `hook` rows whose
  anchors are checked at start-up behind the exe-identity guard; a mismatch means the feature is off, never a guess. The mingw build has no
  SEH, so every pointer is checked with `VirtualQuery` before it is read or called through (as `camera.cpp` does) and the preconditions
  are all checked before the first engine call; a call that faults cannot be recovered, so the first calls of a new site are made on a
  one-unit selection in a scratch battle, never on the 40-unit scene.
- **Selection source.** The row says "the engine's card manager". Read the engine-side selection `S` directly in C++ (it is what the card
  manager's `SelectionChanged` fills, and what the engine's own orders consume); prove it against the cards: select units with the engine's
  `BattleUI.SelectAll*` calls and by `UICardManager:Selected` plus each card's `ItemAddress`, and check `S` lists exactly the same UNIT
  pointers. If `S` and the cards disagree, or `S` cannot be read safely, take the cards route (Lua gives the addresses, C++ does the rest)
  and say so. Orders take explicit UNIT pointers and build their own one-unit `Selection`, as the script path and Empire did, so a test
  never needs a UI selection.
- **One command per unit.** A rigid block move needs a different target per unit, so the API orders one unit per command (Empire's choice).
  Also record whether many commands in the same millisecond play the confirmation sound many times (Empire did; J29 decides whether to
  gate it): an observation for J29, not built here.
- **Layout offsets are proven by readback, not trusted.** For every UNIT/entity offset you read, name the engine_sites row whose stock bytes
  contain the proving instruction (extend the row's anchor and stock bytes where the schema's byte limit allows) or cross-check it live
  against an engine getter that uses the same chain (the UI `BattleUnit:Position` Lua method, `BattleUI.SquadInfoByPointer`), and record
  the comparison. The `armyIndex >= 0` check (the UNIT is in its army's list) runs on every read. A unit whose frame pointer is not 0
  is refused (ships and anything on a moving frame are out of scope).
- **Units are named by a stable id.** Pick the id scheme from what the engine offers (the player's army list at army+0xf4, `UnitListForBattleIds`) and
  print it with the unit's name and men count in a `wsp.unit_list` / `ctl state` listing, so `order <unit> ...` is repeatable across
  launches of the same scenario.
- **The checked result of `order`** (CLAUDE.md rule 77: no ok without a check). After the push the verb waits for the unit to stop (queued
  orders at 0 and no movement for N reads, or a timeout derived from distance and the unit's speed; `speed` can be raised for the wait,
  and restored), reads the unit back and compares position, facing and width with what was ordered. Thresholds start at 1.0 m, 1.0 degree
  and 0.5 m and are set by measurement (Empire reached 0.13 m and 0.05 degrees); the route block in `harness/napoleon/adapter.json` carries
  them with the run id, like the camera route. Not arrived, refused by the engine (`AddUnit` took no unit) or an unreadable unit is
  `failed` or `refused` with the evidence, never ok. Failing fixtures in the host tests: a unit that does not move, a target the engine
  cannot path to (the push succeeds and the units do not arrive), a dead unit.
- **Facing and coordinates.** Calibrate and record the bearing convention (zero direction and sign) against `campose` yaw by ordering known
  facings and reading back, as `engine_facts`; J29 turns drag directions into orders with it. Find whether the order's y matters (the script
  path projects the target onto the ground first) and, if it does, the ground-height call, so `order x z` needs no y.
- **Threading.** The calls run on the Lua pump thread (the camera's finding). Record which thread each of the pump, the `Present` hook and the
  window procedure runs on (a `GetCurrentThreadId` log in one launch), because J29's gesture commit happens on a different path than a Lua chunk. Deliver
  `OrdersIssue` as a C++ entry that refuses off the engine thread, plus a post queue that the pump drains, unless Present shares the pump's
  thread (then say so and J29 may call from its tick).
- **Rule 79 applies**: the branch changes `proxy/` and `harness/`, so it needs 20 consecutive acceptance passes on its final DLL build id,
  run for this branch (the id hashes the DLL inputs' content, so rewording or merging `main` keeps them unless `main` changed those inputs).

## Deliverables
1. **The core pull request**: `orders.{h,cpp}`, the `OrdersAdapter`, the Lua functions, the `order` verb in `ctl.py`, host tests
   (`proxy/tests/test_orders.cpp` in the core: decode against a fake image, argument checks, angle conversion, adapter offsets inside their
   sites' stock bytes, `dev.orders=0` refuses everything), a core proxy docs section, then the tag and the pin bump here. Say in the report
   how the PR waited on Liam's merge.
2. **Sites and keys here**: `engine_sites` rows promoted from verify-only to the hooks the feature uses (with `config_key` `dev.orders`, a
   real `verified` {date, run} and longer guards where J9 said 16 bytes are shared by sibling ctors: `battle.order_move_ctor` needs 32 and
   its relocated vtable dwords rebased), new rows for the owner path and selection holder (J9's suggested `battle.ui_queue_site`,
   `battle.ui_owner_setter`, `battle.selection_dispatch`) as needed, the `config_keys` rows, the generated tables current.
3. **State and selection reads** (item 1): a unit listing (id, name, position, facing, men alive, frontage centre and width, ranks or the
   reason there are none, queued orders) for the player's army and for the selection `S`, with the cross-checks above and the `S` against cards
   result. Frontage: confirm or correct UNIT+0x310 and +0x324 by ordering a unit to a known location and width and diffing; ranks: look for
   it (diff the unit's block before and after a formation change); if not found, define depth as men over files from the width and a measured
   file spacing, and mark ranks derived, not read.
4. **Move and face orders** (items 2 and 4): `order <unit> move x z [facing] [width]` on a land battle and a siege (the player's units in
   the open, ordered in the deployed, running battle: `ctl.py scene <id> --deploy end`), plus `halt`; the run flag (where double-right-click
   running comes from; the UI ground handler passes 0) and what the second 7-argument move constructor is for, each answered or listed open.
5. **Formation orders** (item 5): `order <unit> formation <f>` with the formation list from the engine's own mapping (the UI dispatcher
   passes the float argument as the int; the script path maps a name), checked by the unit's frontage and ranks changing as the engine's own
   `BattleUI.Single_Line_*`/`Column_*` call does, or by a readback of the formation if one is found.
6. **The `order` verb**: `ctl.py order` per the contract above, route block in the adapter, `tests/test_ctl.py` fixtures, rule 77 and rule 78
   scans still green (no key or click in the route).
7. **Scenarios**: orders proven in `land_small` and `siege_small` (`harness/napoleon/adapter.json` `acceptance.order` is not changed by this
   job); if `land_40` exists on `main` (J46) when you run, also one 20 against 20 pass and its `perf` with `dev.orders` on and idle.
8. **The acceptance run**: `dev.orders` joins the adapter's `ctl.launch.keys` (so `order` works from `scene`), and the 20 passes in a row on
   the final build run with it on; its idle cost must not move a shot or a load time past the baseline thresholds.
9. **Facts and tools**: `engine_facts` rows (each with date and run id, or open with an owner) for the order route and queue path, the selection
   source, each UNIT offset, the bearing convention, frontage and ranks, the thread facts, the confirmation sound observation, the
   siege result and anything refuted; `tools` rows with headers for the new Lua chunks and probes.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py` (Lua by `sync-lua`), sha-checked; `dev.skip_intro=1`. No sitting
with Liam is needed unless a step needs a visible window or admin: then stop and ask. Results go in a dated run report
`harness/runs/<date>_j28pc/README.md` with ctl results, run ids and unit-state tables.
- a) Install the build with `dev.orders=1`; the start-up log shows every site accepted and the owner path read; the idle frame matches the
  baseline shot and load time (`ctl.py scene land_small`).
- b) Read-only first: unit listing, selection `S` after `BattleUI.SelectAll*`, the cards cross-check, the live comparison with the UI getter.
- c) One unit, one short move: orders reach the queue (queued orders count rises), the unit walks, readback matches. Then facing and width,
  `halt`, then a long move at `speed` ffwd; the bearing and thread calibrations.
- d) The failing fixtures (unreachable target, dead unit if one can be had by letting a unit die, a refused unit), each reported `failed` or
  `refused` with evidence. Then the whole army moved to a drawn line, every unit read back (the Empire 11 of 11 shape).
- e) The same in `siege_small`. f) Formation orders. g) Orders in the deployment phase (before `--deploy end`): record whether units
  walk or only side-step (Empire's did not walk); an observation for J29, not a deliverable.
- h) The 20-pass acceptance run. i) Uninstall; the game folder is byte-identical to the pre-install snapshot, `save_games` and settings
  untouched (J44 step f).

## Out of scope
Naval battles and ships (`battle.ship_controller` is a different chain), campaign armies, the gesture state machine, drag input,
preview or ghost drawing, hotkeys, the order-sound gate (J29), grouped-unit commands (one multi-unit selection per command: note what the engine does,
build nothing), and anything in `core/` in this repo. Ordering a player's units in a multiplayer or replay battle is never exercised.

## Kill criteria
- The engine accepts a pushed move command (queue push returns true, queued orders rise) but the unit does not move, after 3 attempts that
  each change one thing (the owner path, the selection, the argument layout): stop, report with the run ids and the command bytes, and
  propose the next step. Do not fall back to posted drags or the battle-script route (J28's row), and do not try `Current_Selection_Turn_*`
  (it broke the Lua stack on Empire).
- Any engine-call crash or hang twice for the same cause: stop, collect WER dumps and the watcher's hang folder first, report; do not keep relaunching.
- A needed offset (UNIT/entity layout) cannot be proven by readback after about 25 calls: mark it open, finish the items that do not need it.
- With `dev.orders=1` and no order running, a scene's shot or load time falls outside the baseline thresholds: stop, fix or report.
- The 20-pass run fails twice for a cause in the orders code: stop and report; do not keep re-running.
- Any write into game memory beyond the engine's own command queue, a write into the game folder outside a deploy, or a change to `core/` in
  this repo would be needed: stop and ask.

## Open questions
Recommendations for Liam; the job proceeds on them unless overruled.
- **Selection source** departs slightly from the row's wording ("the engine's card manager"): C++ reads the selection the card manager's own
  update fills, and the cards route stays as the proven fallback. Recommended as written.
- **Deployment-phase orders** (before the battle starts) are measured only. Recommend J29 keeps them inert unless the numbers show units walk.
- **J29's 40-unit walk** needs the `land_40` row, which is J46's; J29 does not depend on J46 today. Recommend adding J46 to J29's `depends_on`
  (a queue change for Liam or the next planner, not made here).
- **Naval and ship orders** are out of scope here and in D14's scope; recommend a separate job only if Liam wants them.

## Finish
Write `jobs/J28/report.md`: what was built (core PR and tag, sites, keys, Lua functions, the verb), the evidence with run ids (the unit-state
tables, the checked order results for land and siege, the failing fixtures, the 20 passes and ledger lines), the layout facts and what stayed
open (frontage, ranks, run flag, formation readback), the thread and sound observations for J29, the C++ entry points J29 builds on, deviations
from this brief and why, and open questions. Then `wsc reg set jobs J28 status=review report=jobs/J28/report.md`.
