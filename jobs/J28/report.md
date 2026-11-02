# J28 report: Battle unit control route

Branch `job/J28`, 2026-11-02. The proxy reads live unit state and the UI's own selection from engine memory and gives units move/face
orders through the engine's own command path, plus halt and formation toggles through the UI's own selection dispatcher, behind
`dev.orders`. All of it lives in the core (warscape-core PR #15, merged and tagged `v0.8.0` by Liam, pinned here). `ctl.py order`
pushes one order per unit and reads every unit back at rest. Proven on the PC in `land_small` and `siege_small`
(run `harness/runs/20261102_j28pc`):
- Front centre: exact.
- Facing: 0.03 to 0.55 degrees off.
- Centre: within 0.01 to 0.55 m of the ordered axis.
- A 9-unit line: 8 of 9 settled in 12.7 s at ffwd. The general's bodyguard does not hold its facing.

Targets the engine cannot reach (cliffs, off the map) fail, and units it will not take are refused. 20 acceptance passes on the final
build `715e9dfc0727`: run `20261102_j28acc` (result under Evidence).

## What was built
- **Core (v0.8.0, warscape-core PR #15):**
  - `proxy/src/orders.h` (pure: the `OrdersAdapter`, `ReadUnit` against any memory reader, the int16 angle conversion, `CheckMove`,
    `ResolveMove`, `UnitOrderable`, `CheckArrival`, `AtRest`).
  - `proxy/src/orders.cpp` (the driver: install from the sites, `OrdersUnit/Army/Selection/Move/Command/Post/Peek/Info`; engine
    calls only, `VirtualQuery` on every pointer, every check before the first call, orders refused off the engine thread).
  - The `wsp` Lua functions in `luabridge.cpp`, `dev.orders` in `dev.cpp`, and `OrdersAdapter*` in `adapter.h`.
  - `ctl.py order` (list, one or several units' move, commands; the settle and the readback check).
  - `proxy/tests/test_orders.cpp` (828 checks), `docs/PROXY_ORDERS.md` (the contract), and C17 (proposed: an order's readback never
    trusts what the order wrote). Details are in the PR body.
- **Here:**
  - Sites: `engine_sites` grows from 45 to 57 rows; every orders row is keyed `dev.orders` with a real `verified`. The 5 verify-only
    rows are promoted or moved to the instruction that proves an offset: `battle.unit_position_get` and `battle.unit_bearing_get`
    move past the wrapper check, and `battle.order_move_ctor` is 32 bytes with its two vtable dwords relocated. The 12 new rows are
    `battle.ui_queue_site`, `selection_dispatch(_b)`, `selection_command`, `unit_entity_index`, `entity_has_order`, `position_xyz`,
    `world_position_copy`, `unit_men_get`, `unit_army_list`, `ground_chain` and `ground_project`.
  - Key and adapter: the `config_keys` row `dev.orders` and the shipped ini; Napoleon's `OrdersAdapter` in
    `proxy/napoleon/adapter.cpp`.
  - Lua: the chunk `proxy/napoleon/lua/ctl/orders.lua` and the probe `probes/j28_units.lua` (both registered).
  - Harness: the `ctl.routes.orders` block in `harness/napoleon/adapter.json` (land and siege reachable; tolerance, settle with
    `wait_speed` ffwd, the command codes), and `dev.orders` in `ctl.launch.keys`.
  - Tests, docs and facts: 9 `tests/test_ctl.py` fixtures, `proxy/README.md` "Battle unit orders (J28)", and 16 `engine_facts` rows.
  - The pin bump v0.7.0 -> v0.8.0.

**C++ entry points for J29** (`dev.h`, contract in warscape-core `docs/PROXY_ORDERS.md`):
- `OrdersMove(unit, MoveArgs{x, z, facing, width, run, queue}, info, why)` runs on the engine thread only.
- `OrdersCommand(unit, cmd, arg, info, why)` sends a dispatcher command.
- `OrdersPost`/`OrdersPostResult` queue an order from any thread.
- `OrdersUnit`, `OrdersArmy` and `OrdersSelection` read state; `RawFromDeg`/`DegFromRaw` convert angles.

Present, the window procedure and the Lua pump run on one thread, so J29 can call `OrdersMove` from its Present tick.

## Evidence
Run `harness/runs/20261102_j28pc`: the README walks through steps a to i, and its table lists every order, generated from `raw/` by `table.py`.
- **a:** 57 of 57 sites accepted, with every operand named in the install line.
- **b:** the UI selection after `SelectAllInfantry` equals army list entries 4 to 9, which are the same pointers as
  `UnitListForBattleIds().Land`. The listing is stable across 5 launches.
- **c1, the first order:** a 10 m move; the front came back at 0.0 m, facing 0.08 degrees, width exact.
- **c2 to c4:** bearing 0 = +z, 90 = +x, clockwise from above.
- **c7:** cavalry 64 m at ffwd, settled in 13.4 s.
- **d4:** the army line: 8 of 9 ok; the general's facing was 6.7 degrees off.
- **e1/e2:** the run flag (33.7 s walking against 20.3 s running over 25 m).
- **f1 to f3:** the fixtures: off the map `failed`, stale pointer `refused`, bad width `refused`.
- **g, siege:** reachable orders land; targets across the cliffs are taken but never walked (g2 exposed the weak first check; g7 now fails).
- **h, deployment:** orders side-step or jump, never walk.
- **i:** halt stops a walking unit; square on/off changes the shape; wedge has no effect on these units.

The idle cost, the 20 passes and the uninstall are under the acceptance run `20261102_j28acc` (see Finish).

## What each deliverable found
1. **Core PR**: built and tested. Every host test passes with Napoleon's adapter in the pinned Docker image, and the core gates are
   green. The null-game build is left to the core's CI: it would not run from this Windows clone (the Docker mount of a relative game
   root).
2. **Sites and keys**: all promoted, keyed and verified on the PC (2026-11-02, run 20261102_j28pc). J9's suggested `battle.ui_owner_setter` was not needed: the queue
   site carries the owner global.
3. **State and selection** (`napoleon.battle.unit_layout`, `selection_source`, `unit_ids`): every UNIT and entity offset is proven by
   a site's stock bytes. Front centre (UNIT+0x310) and width (+0x324) are proven by readback, and turn out to be the **destination**
   the last order wrote, not the live formation. Ranks: not found. Depth is derived as twice the centre-to-front distance (1.75 m at
   31.9 m width for 120 men), marked derived, and left open (`napoleon.battle.frontage_ranks`). The listing carries id, name (by
   type), position, facing, men, front centre, width, queued orders and the engine's `is_moving`. Idle units report one queued order.
4. **Move and face** (`napoleon.battle.order_route`, `order_siege`, `bearing_convention`): land and siege as above.
   - `order x z`: the engine's own ground projection supplies y (15.442 for a unit standing at 15.467).
   - The run flag works.
   - The 7-argument move-type ctor stays untraced.
5. **Formations and halt** (`napoleon.battle.order_commands`):
   - Halt (cmd 7) and square (0x22/0x23) through the dispatcher are checked by their effect.
   - Wedge (0x24) is accepted with no effect on the infantry and cavalry here.
   - Diamond, loose and prone codes are read from the exe but not run.
   - The group layouts (`Single_Line_*`, ...) are whole-army formations: out of scope (one command per unit).
6. **The verb**: as built; rules 77 and 78 hold (no key or click; every ok carries a check), and `tests/test_ctl.py` covers it.
7. **Scenarios**: land_small and siege_small. `land_40` is not on `main` (J46 is queued), so there was no 20 against 20 pass.
8. **Acceptance**: `dev.orders` is in `ctl.launch.keys`, so every pass ran with the key on and idle: run `20261102_j28acc`.
9. **Facts and tools**: 16 facts: 13 verified (2026-11-02, run 20261102_j28pc), 3 open (frontage and ranks, the sound, ship orders for J60). Tool rows exist for the
   chunk and the probe; the run helpers have headers.

## Deviations
- **One verb for halt and formations, generic in the core:** `OrdersCommand` and `order <unit> <command>`, with the codes in the
  game's route block. The brief asked for `order_halt` and `order_formation`. One dispatcher call covers both and keeps every game
  number out of the core.
- **Front centre and width are destinations**, so the arrival check is the live centre, `is_moving` and "moved", not the destination
  readback the brief describes (C17). Without this, a unit that never moved passed (g2).
- **The settle uses the engine's `is_moving`** (an added engine call, the battle.unit.is_moving callee, at a checked site), not queued
  orders: idle units always report one queued order.
- **Unit ids are army list positions**, pinned to the pointer per call; a lost unit renumbers the rest. A stable cross-launch id beyond
  the list order was not needed.
- **The sound observation was not made** (headless, no audio): left open for J29.
- **How the core PR waited on Liam:** the acceptance run started before the tag, with the core gitlink committed at the PR head so the
  DLL came from committed content (no `-dirty`). Liam merged and tagged `v0.8.0` while it ran; the tag's tree equals the PR head
  (empty diff), so the pin bump changed no file and the build id stayed `715e9dfc0727`.

## Open questions
- The general's bodyguard does not hold an ordered facing. Should J29 treat the general's unit as facing-free?
- Ranks or files: no field found. Is it worth a follow-up (diff the UNIT block around a width change), or is derived depth enough for J29?
- Wedge had no visible effect on this map's cavalry. Is that the unit type, or does the code need an argument? Diamond, loose and
  prone were not run.
- J60 (ships): see `napoleon.battle.ship_orders`.

## Finish
Pinned to `v0.8.0` (`build.sh id`: `715e9dfc0727`, the acceptance build); `wsc reg set jobs J28 status=review report=jobs/J28/report.md`; the draft pull request is open for the review.
