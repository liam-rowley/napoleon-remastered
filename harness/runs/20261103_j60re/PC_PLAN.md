# J60 PC plan (the later slot)

Written 2026-11-03 at the end of the desk phase (static RE in `README.md`; code on `job/J60` here and on the local warscape-core branch
`job/J60`, tests green off the PC). Run report: `harness/runs/<date>_j60pc/README.md` in J28's shape (`harness/runs/20261102_j28pc`).
Every launch through the watcher, kits by `pc_deploy.py` (Lua by `sync-lua`), `dev.skip_intro=1`, `dev.orders=1`. First calls of every
new site on one ship in `naval_small`, never in `hist_nile`. Call estimates are tool calls, waits inside one call (`job.sh`, ctl).

## 0. Before the slot (no PC)
- Core: the ship half lands in warscape-core as a job of its own queue (a W row and its brief, then the PR from the main chat), is
  merged and tagged; the pin here moves to it (it also brings W6's `gesture` field; `adapter.cpp` already builds with or without it).
  Or, as J28 did, point the gitlink at the PR head for the run so the DLL comes from committed content. **2 to 4 calls** (main chat).
- Add the 18 candidate rows (`re/candidate_sites.jsonl`) to `engine_sites` (`wsc reg add engine_sites --json <row>` per line; the
  `verified` field is set from the step a run, the gate requires it), `gen_tables.py`, `build.sh --docker all`: the probe kit is built
  from these uncommitted rows (a `-dirty` build id is fine for probes, never for the 20 passes); after step a accepts every site, stamp
  `verified` with the run id, commit, rebuild, and run the gates. **4 calls.**

## a. Install and idle (5 calls)
`pc_deploy.py install` with the key on; `ctl.py scene naval_small`: the start-up log shows 82 sites accepted (64 + the 18 ship rows),
the `orders: ships install:` line with every operand (expected: vtable 0x1338780 rebased, pos +0x54, heading atan2(+0x50c, +0x524),
army +0x43c, count +0x108, list +0x10c, sail +0x1b88, wind [[[+0x1e0]+8]+0xd8] (+0x48, +0x4c), angle +0x5a8, ship vector +0x34);
shot and load time inside the baseline. `land_small` still behaves as in J28 (one `order list`).

## b. Read-only (10 calls)
1. `lua ctl/ships.lua -- list` in `naval_small`: every player ship decodes (vtable, fleet index, finite position, heading, sail).
   Which `UnitListForBattleIds` key holds ships (the chunk tries Naval, Ships, Ship, Sea): record it, drop the others. 2 calls.
2. Cross-check against the engine: `battle.ship` getters are unreachable from Lua (fact `napoleon.battle.script_api_reachable`), so
   compare with the UI: `BattleUI.UnitListForBattleIds` ship entries (their first dword) equal the fleet list pointers; select ships
   with the engine's own UI call (find the naval `SelectAll*`/ship-card name in the exe strings first, statically) and check
   `selection` lists exactly those pointers. 3 calls.
3. Heading and position: `wsp.peek` the ship at +0x504 (the 3x3) and +0x54; compare `camera` / `campose` over the ship. 2 calls.
4. Wind: `wind_x`, `wind_z`, `wind_angle` in `naval_small` and `naval_storm`; the thread ids line (`orders_info`). 2 calls.
5. Speed field hunt (cheap, optional): peek SHIP 0x1b00..0x1c00 twice while sailing; a float that tracks the position delta per second is
   the speed (record it as an engine_facts row; until then speed is derived). 1 call.

## c. One ship, orders (20 calls)
1. `move 1 <x> <z+150> - - 0`: short move ahead of the bow; push true, the ship sails, readback. Kill rule: pushed but no motion after
   3 attempts that each change one thing (mode 0 -> 2 -> 5, sail 4 -> 8, queue) -> stop and report the command bytes. 4 calls.
2. Heading convention: `face 1 0`, `90`, `180`, `270` with flag 0, then flag 1; read back heading and m02/m22: record 0 = ?, sign, and
   whether the flag means absolute or relative (two `face 1 90` in a row: absolute stays at 90). 5 calls.
3. Sails: `move` with `stationary`, `battle`, `half`, `full`; read `sail` and `sail_level` after the transition; time to change. 3 calls.
4. `halt` while sailing: speed falls (two reads). 1 call.
5. Long move at ffwd (`settle.wait_speed`), and one 90 and one 180 degree turn timed (distance and radius from the position track). 4 calls.
6. Target behaviour: inside the turning circle, straight upwind (into `wind_angle` 180), on land: record what the engine does. 3 calls.

## d. The verb and fixtures (15 calls)
1. Route block `naval` entry -> `reachable`: chunk `napoleon_remastered/lua/ctl/ships.lua`, tolerance (pos_m, heading_deg) and settle
   (eps_m, eps_deg, rest_reads, min_speed_mps, wait_speed) from the c measurements, the run id. `tests/test_ctl.py` naval fixtures (list,
   move ok, refused stale pointer, failed never-moved). 4 calls (desk, before the next launch).
2. `ctl.py order list` and `order 1 move x z [heading]` in `naval_small`: checked ok. 2 calls.
3. Fixtures: an upwind or land target (`failed`), a stale pointer (`refused`), a sunk or surrendered ship if one can be had (`refused`). 4 calls.
4. The fleet to a drawn line (one command per ship), every ship read back. 2 calls.
5. ctl.py core change if the land verb's settle does not fit ships (it waits on `moving` and centre stillness; ships may never stop):
   use `CheckShipArrival`/`ShipSettled` semantics in the naval branch. Desk work, core PR. 3 calls.

## e, f. Scenarios and deployment (8 calls)
`naval_storm` (spread vs small), `hist_nile` (relaunch scene; the fleet line, 11 of 11 shape), deployment phase before `--deploy end`
(sail or reposition, measured only).

## g, h. Acceptance and uninstall (6 calls)
20 passes on the final build id with the key on and idle (confirm pass 1 names the final id: J28's ledger lesson); uninstall and the
byte-identical folder check.

**Total: about 70 PC calls plus about 10 desk calls**, inside the brief's 350 with the desk phase's ~200.

## Open questions the PC settles
- Heading sign and zero of atan2(m02, m22) against `napoleon.battle.bearing_convention`.
- The rotate flag; whether a move stops at the target; the move's mode argument (0 script, 0/2/5 UI); sail values 1/2/4/8 in practice.
- Whether y = 0 targets are taken on every naval map; a live speed field.
- Whether the UI list key for ships exists (else the fleet is seeded from the ship selection or a pointer).
