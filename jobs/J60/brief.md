# J60: Naval ship orders route

Phase 4, controls, naval half. J28 gave the proxy a checked way to read land units and order them through the engine's own command path;
it refuses ships on purpose (a ship stands on a moving frame and takes a different controller). This job extends that route to ships:
read the player's ships and their live state (position, heading, speed, sails) from engine memory and give them move and face orders
through the engine's own command path, exposed as the control API's `order` verb in naval battles. Ship orders are in scope by D39
(they add to D1's battle controls, D14). J29's gestures drive a fleet through this job's C++ entry points and nothing else. The
battle-script route and posted drags are not tried (J28's row; Napoleon's script objects are unreachable: fact
`napoleon.battle.script_api_reachable`).

Model: Opus, reason: reverse engineering on Napoleon.exe (the ship layout, the ship controller and its command objects, the frame pointer
and the wind), a proxy DLL feature that calls engine functions in a 32-bit process, and crash reading (D15). Effort high. Budget about
350 tool calls; at the cap, stop, commit, report what is left (cut line in "Order of work"). Subagents (D34) only for independent read-only
work, for example reading J28's route while you probe. Waiting belongs to the harness: `job.sh`, ctl requests and the acceptance runner
block or run in the background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J60`; "The core": the mechanism is game-agnostic code in a separate `warscape-core` clone beside
  this one, on a branch, as a pull request with host tests, then a tag (Liam merges and tags, as for J28's v0.8.0) and the pin bump here;
  "Exe stays vanilla"). Read `docs/DECISIONS.md` (D2, D15, D26, D30, D34, D39), `docs/plans/PLAN.md` phase 4, `proxy/README.md` ("Battle
  unit orders (J28)", "Battle camera (J43)"), `harness/README.md`, and the pinned core's `core/docs/PROXY_ORDERS.md` (the contract you extend).
- **J28 is merged: start from its report and code.** Read `jobs/J28/report.md` (what was built, the C++ entry points, the open questions
  that name J60, the weak-check lesson C17: an order's readback never trusts what the order wrote) and `jobs/J28/review.md`. The code is in
  the core: `core/proxy/src/orders.{h,cpp}` (the driver), `OrdersAdapter*` in `core/proxy/src/adapter.h`, `wsp.*` in `luabridge.cpp`,
  `ctl.py order` in `core/harness/ctl.py`, the host tests `core/proxy/tests/test_orders.cpp`; Napoleon's data is `proxy/napoleon/adapter.cpp`,
  `proxy/napoleon/lua/ctl/orders.lua`, the `ctl.routes.orders` block in `harness/napoleon/adapter.json` (its `naval` entry says
  "unreachable ... J60 builds ship orders on this route": you flip it) and the run `harness/runs/20261102_j28pc` (README, `raw/`, `order.sh`,
  `table.py`: the shape of a run report to copy).
- **Static work for ships is NOT done** (J9 mapped the land chain only). Start from `harness/runs/20261101_j9pc/j28_candidates.md`: section 1
  lists the battle-script tables (`battle.ship` 0x1451520 with 11 entries, `battle.ships` 0x1451590, `battle.army` units/ships,
  `battle.ship_controller` 0x1451990 with 35 entries, `battle.unit_controller` 0x1451750 with 49 as the land analogue) and the helper
  scripts under `harness/runs/20261101_j9pc/re/` (`j28_regs.py` dumps a luaL_Reg table with names, `j28_edis.py`/`j28_dis.py` disassemble,
  `j28_fstart.py` finds function starts and callers, `j28_guard.py` prints guard bytes; they need the stock exe and the venv python `-I`,
  see the J9 README). Its selection section gives the ship containers of the selection object. Its addresses are static VAs (rebase every one).
  Search before writing: `python3 core/wsc.py find battle ship order selection unit`.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there): Empire never built ship orders (its battle controls
  list naval as out of scope: `guides/19-battle-controls.md` lines 70 and 311, which name a separate `bcq_ship_order_*` family; nothing
  there was run). It is a lead for names, not a route to port. `docs/learnings/LEARNINGS_ENGINE.md` has the naval facts that bear on
  this job (search "BattleShipSailingIntoWind", "naval").
- Other jobs touching the same files: J46 (scenario rows, `harness/` and `proxy/` presets), J8/J16/J30 (DLL) and J29 may merge first;
  rebase on `main` before the pull request (the DLL build id hashes the DLL inputs' content, `CLAUDE.md` Rule 79 paragraph).

## Target facts
What is known (all static or from J28's runs; every one is checked again here and recorded as an `engine_facts` row with date and run id
before anything relies on it). Napoleon.exe sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, ASLR on, 32-bit.
- **The shared chain** (J28, verified 2026-11-02, run 20261102_j28pc): owner global -> battle at +0xf8 -> command queue at +0x28048 (`battle.ui_queue_site`); the UI's own
  selection `S = [[owner]+0x450]+0x20`; the owner's "current selection" dispatcher `battle.selection_command` (this = owner+0x454) with
  codes read from the BattleUI functions; the army list at army+0xf0 (count) and +0xf4; orders build their own one-unit `Selection` and
  never touch the UI's. Present, the window procedure and the Lua pump run on one thread (fact `napoleon.battle.order_threads`).
- **Ships in the selection object** (J9, static): ship groups at `[S+0x2c]`/`[S+0x30]`, loose ships at `[S+0x3c]`/`[S+0x40]`; `0x6f2300`
  counts ships as `0x6f2350` counts land units; the rebuild `0x5f0be0` refills ships through slot 1 of the holder's vtable
  (`0x69ffb0`/`0x6a00d0`, ship group id at `[ship+0x4c0]`). Whether a ship is a UNIT in an army list (so J28's decode applies) or a
  separate object with its own list is **open**; the `battle.army` table has both `units` and `ships`, which says separate.
- **Ships stand on a moving frame**: J28's position decode refuses any unit whose frame pointer (E+0x6ec on land, 0 there) is non-zero;
  `battle.world_position_copy` (0x80e9d0) is the generic frame-aware copy ("frame == 0 -> plain x,y,z"). Whether a ship's own position is
  frame-free (the ship is the frame) or relative to one is open and decides what `x z` means in `order`.
- **The ship controller** (`battle.ship_controller`, 35 script methods) is the naval analogue of `battle.unit_controller`
  (`goto_location_angle_width`, `change_formation`, ...). Its method names, the engine functions behind the move, face, speed and sail
  entries, and the command objects they build are **open**: that is the first deliverable. The land route built `Selection`, `AddUnit`,
  a move command ctor and a queue push; a ship command may be the same objects with a ship constructor, or a different queue.
- **Wind and turning**: the script event `BattleShipSailingIntoWind` fires every tick in a naval battle (Empire fact); a ship cannot sail
  straight into the wind and turns on a circle, so a target the engine accepts may be reached late, by a detour, or not at all. Open:
  where the wind direction and strength live in memory, whether the order has a heading argument, and what the engine does with a
  target inside the turning circle.
- **Scenarios** (on `main`, J44, measured): `naval_small` and `naval_storm` (custom battle, caribbean, same armies, storm = torrential rain;
  load 3.5 s for small; deploy and turned poses for small), `hist_nile` (the Nile 1v1, historical: it leaves by a relaunch; 4.5 s). All
  start in a deployment phase; `ctl.py scene <id> --deploy end` ends it and checks the battle clock runs. The scene probe reports
  `naval`. `naval_large` does not exist (J46's gap); nothing here depends on it.

## Decisions already made for this job
- **Order of work** (so a cut by the budget costs the least; at the cap finish the item in hand, commit, and write the rest as open facts):
  1 static RE of the ship chain and read-only state with live cross-checks; 2 a move order for one ship in `naval_small`, checked by
  readback; 3 facing and the `order` verb with checked results and failing fixtures; 4 speed and sails; 5 `naval_storm` and `hist_nile`;
  6 deployment-phase measurement; 7 the 20-pass run on the final build. Items 1 to 3 and 7 are the minimum J29 can build on; 4 to 6 may
  move to a follow-up if the cut line is reached (say so in the report). Items 5 and 6 are cheap once 3 works: do them before 4 if 4 is
  stuck in the RE.
- **Where the code lives.** Extend the core, not this repo: ship decode, argument checks, angle and arrival logic as pure parts in a header
  with host tests on a fake memory image (as `orders.h`/`ReadUnit` do), the driver in the same family as `orders.cpp` (a sibling
  `ships.{h,cpp}` or an extension of `orders.cpp`: your call, say which and why), a ship section in the `OrdersAdapter` (or a sibling
  adapter) naming sites and offsets by `engine_sites` id (nothing in the core names a game or an address), Lua functions on `wsp`
  (names yours to choose, mirroring `unit_state`/`unit_list`/`order_move`/`order_command`, all refusing with a reason when the key is
  off), and `ctl.py order` extended in `core/harness/ctl.py` so that in a naval scene the same verb names ships. **Use the key
  `dev.orders`** (same feature family, same default 0, shipped ini, `ctl.launch.keys`) unless the design needs a second key: a new key is
  a `config_keys` row and a shipped-ini line, and must be justified in the report. Napoleon's adapter data, the Lua chunk, the `naval`
  entry of the route block in `harness/napoleon/adapter.json`, the sites, tests and facts are here. Do not edit `core/` in this repo.
- **Engine calls only, no detours (D2, D26).** As J28: the functions are called, never patched; the sites are `hook` rows with anchors
  checked at start-up behind the exe-identity guard; a mismatch means the ship half is off and the land half unaffected, never a guess.
  The mingw build has no SEH, so every pointer is checked with `VirtualQuery` before it is read or called through, and all preconditions
  are checked before the first engine call; a call that faults cannot be recovered, so the first calls of every new site are made on a
  one-ship selection in `naval_small`, never in `hist_nile`.
- **Land stays as J28 left it.** `OrdersMove` and `ReadUnit` keep refusing a unit on a moving frame; ships go through their own entry
  points. J28's tests, fixtures and the `land`/`siege` route entries must stay green and unchanged (the only edit to the route block is the
  `naval` entry and, if needed, a shared key).
- **Selection source.** Read the ship part of `S` directly in C++ (it is what the card manager's update fills) and prove it as J28 did: select
  with the engine's own BattleUI calls (find the naval `SelectAll*`/ship-card calls in the exe strings; do not assume the land names) and
  check `S` lists exactly the ship pointers the engine's ship lists hand out (`BattleUI.UnitListForBattleIds` or its ship counterpart, the
  `BattleShip` UI class's `ItemAddress`/address method). If `S` and the lists disagree or `S` cannot be read safely, take the Lua list route
  and say so. Orders take explicit ship pointers and build their own one-ship `Selection`; a test never needs a UI selection.
- **One command per ship.** As J28: the API orders one ship per command, so a fleet line is a set of commands. If the engine's ship command
  also takes a group, note what it does and build nothing.
- **Layout offsets are proven by readback, not trusted.** Every ship and entity offset read names the `engine_sites` row whose stock bytes
  contain the proving instruction, or is cross-checked live against an engine getter on the same chain (the `BattleShip` UI class's methods,
  the script getters of `battle.ship`), and the comparison is recorded. The ship's membership of its army's list (or whatever list the
  engine keeps) is checked on every read, as `armyIndex >= 0` is for land.
- **The checked result of `order`** (CLAUDE.md rule 77: no ok without a check). A ship does not stop on arrival unless the order says so,
  and it is wind-driven, so "at rest" is not the land test. Define the settle from what the engine offers (the ship's own speed and moving
  flag, queued orders, distance to the target) and set thresholds by measurement; start from J28's (1.0 m, 1.0 degree) and expect to widen
  them for ships: report the measured spread, with the run id, in the route block like J28's `tolerance`. The verb waits (timeout derived
  from distance and the measured speed; the sim `speed` can be raised for the wait and restored, as J28 does), reads the ship back and
  compares position, heading and, if ordered, speed or sails with what was ordered, **using a live reading, not what the order wrote**
  (C17: J28 found the destination fields are written at the push and prove nothing alone). A ship that never moved, one the engine refuses,
  or an unreadable ship is `failed` or `refused` with the evidence, never ok. Failing fixtures in the host tests: a ship that does not
  move, a target in the wind's no-go zone or on land, a sunk or routed ship, a stale pointer.
- **Frame, heading and coordinates.** Find what the frame pointer is on water and whether the order's `x z` are world or frame
  coordinates; calibrate and record the heading convention (zero direction and sign) against `campose` yaw and J28's land bearing
  convention (0 = +z, 90 = +x, clockwise from above: fact `napoleon.battle.bearing_convention`) by ordering known headings and reading back,
  as `engine_facts`. J29 turns drag directions into orders with it. Find whether the order's y matters (sea level, or a ground-height
  call as the land route's `ground_project`) so `order x z` needs no y.
- **Wind and turning circles are measured, not modelled.** Read the wind from memory if it is found cheaply (record where) and report, for
  at least one ship, the radius or distance a 90 degree and a 180 degree turn took at the measured speed. Do not model them in the core:
  the arrival check reads the ship, it does not predict it.
- **Speed and sails.** Record what orders exist on the ship controller for speed and sails (the script table names them); implement the
  ones the engine's own command path takes and that read back from the ship (speed, sail setting), each with a checked result. A control
  with no readback is listed as unchecked and not exposed as ok.
- **Threading.** As J28: the calls run on the engine thread (Present, the window procedure and the Lua pump are one thread in a battle:
  fact `napoleon.battle.order_threads`); ship entry points refuse other threads and a post queue serves other callers. Confirm the ship
  calls need nothing different (a naval battle may run a separate sim thread: log the thread ids once in `naval_small`).
- **Rule 79 applies**: the branch changes `proxy/` and `harness/`, so it needs 20 consecutive acceptance passes on its final DLL build id,
  run for this branch with the key on and idle (the id hashes the DLL inputs' content, so rewording or merging `main` keeps them unless
  `main` changed those inputs). `acceptance.order` is not changed by this job (it already holds `hist_nile` and `naval_small`). Mind the
  ledger lesson in J28's open questions: confirm the first pass names the final build id before counting it.

## Deliverables
1. **The core pull request**: the ship decode and driver, the adapter section, the Lua functions, the `ctl.py order` extension, host tests
   (decode against a fake image, argument checks, adapter offsets inside their sites' stock bytes, the failing fixtures above, key off
   refuses everything, the land tests unchanged), the `core/docs/PROXY_ORDERS.md` ship section, then the tag and the pin bump here. Say in
   the report how the PR waited on Liam's merge.
2. **Sites and keys here**: new `engine_sites` rows for the ship chain (keyed `dev.orders`, a real `verified` {date, run}, guards long
   enough to be unique with their relocated dwords rebased: the 16-byte guards of sibling constructors are shared, as J28 found), the
   generated tables current, the shipped ini unchanged unless a key was added.
3. **State and selection reads**: a ship listing in naval scenes (id, name or class, position, heading, speed, sail state, hull or men if
   cheap, queued orders, the engine's moving flag) for the player's fleet and for the selection `S`, with the cross-checks above and the
   `S` against engine lists result. Ship ids: army-list position pinned to the pointer per call, as J28.
4. **Move and face orders**: `order <ship> move x z [heading]` checked, in `naval_small` first; facing as an argument or a separate order,
   whichever the engine's command takes (say which); `halt`/stop if the ship controller has one; the order's behaviour when the target is
   inside the turning circle or upwind, recorded.
5. **Speed and sails** (item 4 of the order of work) as above.
6. **The `order` verb**: `ctl.py order` per the contract, the `naval` entry of the route block flipped to `reachable` with tolerance,
   settle, commands and the run id; `tests/test_ctl.py` fixtures for naval (list, move, refusal, failure); rules 77 and 78 scans still
   green (no key or click in the route).
7. **Scenarios**: orders proven in `naval_small`, `naval_storm` (rain and a different wind: does the arrival spread change?) and
   `hist_nile` (a fleet moved to a drawn line, every ship read back, the 11-of-11 shape J28 aimed for, with the failures named).
   Deployment phase: record whether ships sail or only reposition (measured only; J29 keeps them inert unless the numbers show ships move).
8. **The acceptance run**: the 20 passes in a row on the final build with the key on (idle cost must not move a shot or a load time past
   the baseline thresholds).
9. **Facts and tools**: `engine_facts` rows (each with date and run id, or open with an owner) for the ship layout and list, the selection
   source, the frame and coordinates, the heading convention, the command objects and queue, the wind, turning, speed and sails results,
   the thread observation, the deployment result and anything refuted; **close or replace `napoleon.battle.ship_orders`** (open, owner
   J60); `tools` rows with headers for new Lua chunks and probes.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py` (Lua by `sync-lua`), sha-checked; `dev.skip_intro=1`. No sitting
with Liam is needed unless a step needs a visible window or admin: then stop and ask. Results go in a dated run report
`harness/runs/<date>_j60pc/README.md` with ctl results, run ids and ship-state tables (copy the shape of J28's).
- a) Install the build with `dev.orders=1`: the start-up log shows every site accepted (J28's 57 plus the new ship rows) and the ship
  chain read; the idle frame matches the baseline shot and load time (`ctl.py scene naval_small`). A land scene still behaves as in J28.
- b) Read-only first: ship listing, the selection `S` after the engine's own ship selection call, the lists cross-check, the live comparison
  with a UI getter; wind, thread ids.
- c) One ship, one short move: the order reaches the queue, the ship sails, the readback matches. Then heading, then speed and sails, a
  stop, then a long move at `speed` ffwd; the heading and frame calibrations; one turn timed.
- d) The failing fixtures (upwind or land target, a stale pointer, a sunk ship if one can be had by letting a ship sink or by a refused
  one), each reported `failed` or `refused` with evidence. Then the whole fleet moved to a drawn line, every ship read back.
- e) The same in `naval_storm`, then `hist_nile` (a relaunch scene). f) Orders in the deployment phase (before `--deploy end`).
- g) The 20-pass acceptance run. h) Uninstall; the game folder is byte-identical to the pre-install snapshot, `save_games` and settings
  untouched (J44 step f).

## Out of scope
Firing and gunnery orders (fire at will, target selection, ammunition, the firing arcs toggle), boarding and capturing, ship formations
and group commands (one command per ship; note what the engine does), campaign fleets and the campaign map, the gesture state machine,
drag input and any preview (J29), hotkeys, the order-sound gate (J29), the battle-script route and posted drags, ship LOD or graphics,
`naval_large` (J46), and anything in `core/` in this repo. Ordering ships in a multiplayer or replay battle is never exercised.

## Kill criteria
- The engine accepts a pushed ship command (the push returns true, queued orders rise) but the ship does not move, after 3 attempts that
  each change one thing (the owner path, the selection, the argument layout): stop, report with the run ids and the command bytes, and
  propose the next step. Do not fall back to posted drags or the battle-script route, and do not try `Current_Selection_Turn_*` (it broke
  the Lua stack on Empire).
- The ship command path turns out to be a different queue or object model that needs more than about 60 tool calls of RE beyond the land
  route after the first live read of a ship: stop and report what is known (the cut line then is items 1 and the facts), rather than
  guess at engine objects.
- Any engine-call crash or hang twice for the same cause: stop, collect WER dumps and the watcher's hang folder first, report; do not keep
  relaunching.
- A needed offset (ship or entity layout) cannot be proven by readback after about 25 calls: mark it open, finish the items that do not
  need it.
- With `dev.orders=1` and no order running, a scene's shot or load time falls outside the baseline thresholds: stop, fix or report.
- The 20-pass run fails twice for a cause in the orders code: stop and report; do not keep re-running.
- Any write into game memory beyond the engine's own command queue, a write into the game folder outside a deploy, or a change to `core/`
  in this repo would be needed: stop and ask.

## Open questions
Recommendations for Liam; the job proceeds on them unless overruled.
- **One key or two.** Recommended: ships share `dev.orders` with land (one feature, one default-off key, one ini line); a second key only
  if the design needs the ship half switchable alone. Not settled by D39.
- **What J29 does with ships.** Empire left naval gestures inert (ships cannot strafe). This job only gives J29 the entry points; whether
  Alt+drag moves a fleet to a drawn line (each ship its own target, heading from the drag) or ships stay on the vanilla controls is J29's
  brief, after this job's numbers (turn radius, arrival spread). Recommended: decide it when J29 is briefed.
- **Deployment-phase ship orders** are measured only, as land's were (fact `napoleon.battle.order_deployment`: land units side-step or jump,
  never walk). Recommended: J29 keeps them inert unless the numbers show ships move.
- **`hist_nile` in the acceptance proof.** It is a relaunch scene and only a 1v1 fleet; recommended: prove the fleet line in `naval_small`
  and `hist_nile` once each, and keep the 20 passes idle (the key on, no order), as J28 did.
- **If the ship chain cannot be reached** within the kill criteria, ship orders move to a follow-up with the RE facts recorded, and J29
  proceeds land-only (it does not depend on this job).

## Finish
Write `jobs/J60/report.md`: what was built (core PR and tag, sites, keys, Lua functions, the verb), the evidence with run ids (the ship
tables, the checked order results for the three scenarios, the failing fixtures, the 20 passes and ledger lines), the layout, frame,
heading, wind and turning facts and what stayed open (speed, sails, deployment), the thread observation, the C++ entry points J29 builds
on, deviations from this brief and why, and open questions. Then `wsc reg set jobs J60 status=review report=jobs/J60/report.md`.
