# J60 static RE: the naval ship order path (desk phase, 2026-11-03)

Exe: `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250` (a sha-checked read-only copy in the session scratchpad; nothing
under the game folder or `C:\napoleon_remastered_pc` was written, no game run). ImageBase 0x400000, ASLR on: every address below
is a static VA (rebase `va - 0x400000 + module`). RE environment: `discovery/core/re_env.py` (capstone 5.0.6, pefile 2024.8.26 from
pinned wheels) outside the repo; tools `re/j60re.py` (tables, disassembly, callers) and `re/j60rows.py` (the 18 `engine_sites` rows).
Nothing here is PC-verified: the sites carry no `verified` until the J60 PC slot runs (`PC_PLAN.md`).

## 1. Script tables (luaL_Reg, `j60re.py <exe> regs ...`)

| Table | VA | Entries (name -> function) |
|---|---|---|
| `battle.ship` | 0x1451520 | name 0x611d40, type 0x611e30, position 0x611e90, bearing 0x611ef0, ship_in_range 0x611f90, hull_damage 0x612000, sail_damage 0x612060, deploy_reinforcement 0x612180, is_routing 0x6120a0, is_surrendered 0x6120f0, number_of_men_alive 0x612130 |
| `battle.ships` | 0x1451590 | item 0x6124c0, count 0x6124f0 |
| `battle.army` | 0x14515d0 | units 0x612680, ships 0x6126a0, create_unit_controller, create_ship_controller 0x612720, ... |
| `battle.ship_controller` | 0x1451990 | add_ships, add_all_ships, add_group, **halt 0x6149a0**, fire_at_will, clear_all, sink, take_control, release_control, withdraw(_q), **rotate 0x614e80 / rotate_q 0x614e90**, broadside_attack, toggle_boarding_mode, change_shot_type, **move_forward 0x615090**, **goto_location 0x615140 / goto_location_q 0x615150**, **set_sail 0x614bd0**, change_formation(_q), attack_ship(_q), fire_at_ship, board_ship(_q), morale_behavior_*, blow_up_ship, destroy_mast, ignite_deck, ignite_sails, force_surrender (35) |

No speed order exists on the ship controller: speed is the sail setting.

## 2. The SHIP object (read-only state)

Ships are **not** UNITs: a separate class with its own army list.

| Field | Where | Proof |
|---|---|---|
| object | 0x2120 bytes, operator new at 0x506372, ctor 0x691c10 (args army, ...) | the allocator pushes the new SHIP into army+0x104/+0x108/+0x10c (0x5063a9..) |
| vtable | 0x1338780 | ctor `mov [edi],0x1338780` at 0x691f22 (also 0x69ba7b, a second ctor) |
| script wrapper | SHIP = [wrapper+4] | every battle.ship getter |
| army | [SHIP+0x43c] | ctor 0x691fae; name getter 0x611d8c |
| fleet list | army+0x108 count, army+0x10c SHIP*[] | name getter 0x611d92/0x611d9c, battle.ships.count 0x61250d |
| position x,y,z | floats SHIP+0x54/+0x58/+0x5c | battle.ship.position calls vtable slot 0 = 0x6dfe00 `lea eax,[ecx+0x54]; ret` |
| orientation | 3x3 at SHIP+0x504 (identity at ctor: +0x504, +0x514, +0x524 = 1.0) | ctor 0x69214a..0x69219a |
| heading | atan2([SHIP+0x50c], [SHIP+0x524]) * 32768/pi -> int16 -> degrees (+360 if negative) | battle.ship.bearing 0x611f03..0x611f59 (same int16 to degrees code as the land getter) |
| sail level | float SHIP+0x1b88, set by 0x6ea890 (SetSailLevel) | 0x6d8be0 reads it; 0x6e05f0 maps > 0.5 -> 8 full, > 0.25 -> 4 half, > 0 -> 2 battle, else 1 stationary; the UI sail buttons (0x60d8b3 -> 0x5f5f80: 1, 2 BattleSail, 4 HalfSail, 8 FullSail) |
| orderable | byte [SHIP+0x20dd] == 0, byte [SHIP+0x20de] == 0, [SHIP+0x1c58] != 2, not routing 0x6d03b0(SHIP+0x1ef4) | the check 0x6d01e0 inside Selection AddShip |
| surrendered | [SHIP+0x1f00] == 4 | battle.ship.is_surrendered 0x61210d |
| routing | 0x6d03b0(SHIP+0x1ef4) (a call) | battle.ship.is_routing 0x6120c0 |
| hull damage | ([+0x1d80]+[+0x1d84]+[+0x1d88]+[+0x1d8c]) * 0.25 | battle.ship.hull_damage 0x61201e |
| sail damage | [SHIP+0x1d90] | battle.ship.sail_damage 0x61207e |
| men | [[+0x48c]+0x18] + [[+0x46c]+0x18] + [+0x4f0] + [+0x4d0] | battle.ship.number_of_men_alive 0x61214d |
| wind-relative angle | int16 SHIP+0x5a8 = atan2(wind) - atan2(heading), every tick | 0x6f6fb1..0x6f700d; `BattleShipSailingIntoWind` fires when it exceeds 30037 (165 deg) |
| wind | W = [[[SHIP+0x1e0]+8]+0xd8]; prevailing wind (x, z) floats W+0x48, W+0x4c; 0x611460 adds local gusts (list W+0x20/+0x24) at a point | 0x6f6f6f..0x6f6fac |
| speed | **not found**: no getter in battle.ship or the UI; 0x5cd26f shows a record speed (`[x+0x1b30] * 1.9417`, knots) in the unit details, not a live value | derive from two position reads (a live reading) |

Frame: a ship's position is SHIP+0x54 directly; no frame pointer is involved (the land refusal is about units *standing on* a ship).

## 3. The order path (script `goto_location` 0x6454c0, `rotate` 0x645c00, `halt` 0x6149a0, `set_sail` 0x614bd0)

All build their own selection from the controller (0x646940: Selection ctor 0x68f580, AddShip 0x69ffb0 per ship, 0x6a00d0 per ship
group), construct a command, push it on `[[[0x14d0154]+0x404]+0x28048]` (the same queue as J28's land route, which reaches it from the
owner global) and run the command dtor 0x5a95b0.

| Step | Function | Arguments | Push (type id) |
|---|---|---|---|
| target | 0x7fd730 (thiscall, this unused) | loc[5] out, float xz[2] in; ret 8 | builds (x, **0**, z) with 0x7ead50: sea level, no terrain projection |
| move | ctor **0x599510** (ret 0x14; vtable 0x132b648) | Selection*, loc[5]*, int sail, int mode, bool queue | **0x58db40** ([0x14a6268]) |
| facing | ctor **0x599810** (ret 0x10; vtable 0x132b650) | Selection*, int16 angle (deg * 182.044), bool flag, bool queue | **0x58dc60** ([0x14a6110]) |
| halt | ctor **0x599140** (ret 4; vtable 0x132b678) | Selection* | **0x58dae0** ([0x14a5f98]) |
| sails | ctor 0x5992c0 (ret 8; vtable 0x132b688, a generic one-int command) | Selection*, int sail (1, 2, 4, 8) | **inline only**: type [0x14a5fac] (helper 0x58e000) has no out-of-line push |
| forward | ctor 0x599640 | Selection*, float (script passes 2.0), 0, 0 | 0x58dba0 ([0x14a6268]-family, helper 0x58dfc0) |

- **The move carries the sail setting**: goto_location(loc[, sail string]) maps the string with 0x6593d0 over the table at 0x1451968
  ("" 0, "stationary" 1, "battle sail" 2, "half sail" 4, "full sail" 8); default 4. The UI ship move handler (0x5df4c0..0x5df52c)
  passes sail 4 and mode 0, 2 or 5; the script passes mode 0. So sails are ordered through the move, not through set_sail's
  inline-only push.
- **No heading argument on the move**: facing is the separate rotate command, so `move x z heading` is a move then a queued rotate.
- The rotate flag: the script's second argument; the owner dispatcher codes 0..3 (0x5dde2d..0x5ddf2e) build it with
  (-a, 0), (+a, 0), (+a, 1), (-a, 1) (scales [0x1331c78] = -182.04 and [0x1331c1c] = +182.04). Absolute or relative is open (PC).
- Selection layout (ships): AddShip 0x69ffb0 checks 0x6d01e0, then pushes into sel+0x34 (count +0x3c, data +0x40); ship groups at
  sel+0x24 (+0x2c/+0x30). The UI's S = [[owner]+0x450]+0x20 has the same layout; 0x6f2300 counts its ships.
- Dispatcher with ships in the selection (codes >= 0x53, table 0x5de868): 0x53/0x57 -> 0x599200(sel, 1/0) push 0x58d660;
  0x54/0x55/0x56 -> 0x5992c0(sel, 0/7/8) push 0x58d960 (type 0x58df20: not set sail; probably shot type); 0x59, 0x5a, 0x5f ->
  0x599140-shaped commands of types 0x58e010, 0x58e020, 0x58dfe0; 0x5e -> 0x599640 (forward); 0x60..0x63 -> formation 0x599320.
  Codes 4/5/6 -> 0x5992c0(sel, 2/0/1) push 0x58d720 (type [0x14a5808], not set sail). Not used by the route.
- Threads: the same callers as land (Lua C functions and UI handlers); nothing ship-specific found.

## 4. Sites

18 candidate `engine_sites` rows in `re/candidate_sites.jsonl` (`j60rows.py`, all `kind: hook`, keyed `dev.orders`). They are **not in
the registry**: its gate requires `verified {date, run}` on every row, and they have no PC run yet; the PC slot adds them with its run
(`wsc reg add engine_sites --json <row>` per line, then `gen_tables.py`). With the core ship half and no rows, the ship half refuses to
install ("site ... not accepted") and the land route is unaffected. The core host tests passed against Napoleon's adapter with the rows
in place (182 checks, the pinned image, 2026-11-03). Rows: `battle.ship_vtable_store`,
`ship_position_slot`, `ship_bearing_get`, `ship_fleet_list`, `ship_sail_get`, `ship_orderable`, `ship_surrendered_get`,
`selection_add_ship`, `ship_move_ctor`, `ship_move_push`, `ship_location`, `order_rotate_ctor`, `order_rotate_push`,
`order_halt_ctor`, `order_halt_push`, `ship_wind_chain`, `wind_vector_get`, `ship_wind_angle`. Every stock window is unique in the
image with relocated dwords masked, except `ship_vtable_store` (a second SHIP ctor at 0x69ba7b stores the same 32 bytes): unique with
its anchor (36 bytes).

## 5. Open (settled on the PC: `PC_PLAN.md`)
- Heading sign: atan2(m02, m22) against J28's bearing convention (0 = +z, 90 = +x, clockwise from above).
- Whether SHIP+0x54 is world coordinates (land units' frame) and the target y = 0 is accepted on every map.
- The rotate flag (absolute or relative), what a move does at the target (stops, keeps sailing), and the sail argument's effect.
- A live speed or moving field (derived from positions until found).
