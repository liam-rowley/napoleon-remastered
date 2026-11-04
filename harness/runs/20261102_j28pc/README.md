# J28 PC run: battle unit orders (2026-11-02)

Napoleon.exe sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, headless 1920x1080, DXVK, fixed sky. Every launch through `ctl.py scene`
with the adapter's `ctl.launch.keys` (`dev.orders=1` among them). Dev builds from warscape-core branch `j28-orders` (PR #15) in the
submodule while it was being built (`46f52d356ce8-dirty` to `6e913ef90a70-dirty`); the acceptance build is `715e9dfc0727` (run
`20261102_j28acc`). Orders through `ctl.py order` (`order.sh <tag> ...` here keeps each JSON in `raw/`; `sum.py`, `step10.py` and
`table.py` are the helpers); probes `proxy/napoleon/lua/probes/j28_units.lua`.

## a) Install and start-up
All 57 engine sites accepted (`patch_engine: 55 sites: 55 ok` on the first build, 57 with the dispatcher sites); the install line names
every operand read from the sites (owner global, battle +0xf8, queue +0x28048, UI selection [owner+0x450]+0x20, UNIT and entity
offsets, ground chain [[battle+8]+0xb4]). Threads in three launches: Present, the window procedure and the Lua pump on one thread
(`orders: threads: Present 34860, the game window's procedure 34860, ...`).

## b) Read-only (b1 to b3)
`wsp.selection()` after `BattleUI.SelectAllInfantry`: 6 UNIT pointers, exactly army list entries 4 to 9 (the infantry); empty before.
`BattleUI.UnitListForBattleIds()` returns `{EntityDisplay, Land, Naval}`; `Land` holds 17 `Pointer<UNIT>` userdata (the player's 9
first, then the enemy's 8) whose first dword is the UNIT the army list holds. The listing (army list order = the unit id):

| id | men | x | z | facing | width | front z |
|---|---|---|---|---|---|---|
| 1 general | 18 | 0.17 | 331.25 | 176.8 | 14.0 | 326.73 |
| 2 artillery | 18 | 62.65 | 303.26 | 180.1 | 27.0 | 303.33 |
| 3 cavalry | 45 | 142.75 | 308.46 | 179.9 | 32.0 | 303.96 |
| 4-7 line infantry | 120 | 28.2 / -5.7 / -45.4 / -90.9 | 303.7 to 303.9 | 179.8 to 179.9 | 31.9 / 31.9 / 43.6 / 43.6 | 301.9 to 302.1 |
| 8-9 light infantry | 60 | 102.1 / -137.7 | 304.4 | 179.6 / 179.7 | 40.6 | 302.2 / 301.9 |

The same order and positions in all five land_small launches (`c0_list.json`, `e0_list.json`, ...). An idle unit has one queued
order. **b2:** calling `BattleUI.SquadInfoByPointer()` without its argument raised a Lua error and the battle UI pump stopped for
good (`raw/b2_stall.jpg`: the battle runs, no pump; fact `napoleon.lua.battleui_error_stops_pump`); relaunched.

## c, d, e) Moves on land, the army line, the run flag
c1 is the first engine order: unit 4, 10 m forward; the front centre read back at exactly (28.2, 292.0), the centre walked 10.08 m
and stays 1.8 m behind it. c2 to c4 calibrate the bearing: 0 = +z, 90 = +x, clockwise from above (the camera's yaw convention).
c5/c6 ran while the enemy closed in: men fell (45 -> 35, 120 -> 93) and the general's unit left the army list, renumbering the rest, so
c6 read unit 5 as "4" (fixed: ctl.py pins a number to its pointer per call). d1 assigned line slots by id, not by position (units
crossed the field for up to 286 m at ffwd, into the enemy); d2/d3 timed out because the settle read one unit per call (~15 s a round
for 9 units; fixed: one chunk call per round) and the centre of a unit at rest shuffles more than 0.02 m per poll at ffwd (fixed: the
engine's `is_moving` is the rest signal). **d4: 9 units pushed back to back, 8 of 9 at rest and within tolerance in 12.7 s** (facing
<= 0.55 degrees, centre lateral <= 0.55 m); the general's bodyguard reached its front centre but not its facing (6.7 degrees; 4.5 and
7.3 in d2/d3). e1/e2: the same 25 m walked in 33.7 s and run (the move ctor's run flag) in 20.3 s.

## f) Failing fixtures
f1: a target off the map is taken; the unit walks off and leaves its army during the wait (`failed`, step settle). f2: a pointer from an
earlier launch: `refused` (its army is not readable). f3: width 0.2 m: `refused` by the argument check. g2/g7 below are the
"pushed but never arrives" fixture. A dead unit (men 0, still listed) is a host fixture only: no unit died while being ordered.

## g) siege_small
The player's army stands on a ridge below the fort. g8 (12 m back) and g4's units 7 and 9 landed (facing 0.04 to 0.12 degrees). Units
4, 5 and 8 of g4 and the g2/g7 targets are across the ridge's cliffs: the engine takes the order (push 1, the destination written:
the front centre reads back exact) but the unit never walks there. g2 passed the first check (the stored destination and a 30 m
centre bound) though the unit never moved: the check now compares the centre with the unit's own depth and fails a unit ordered away
that never moved (g7: failed). `raw/g5_siege_after.jpg`.

## h) Deployment phase (observation for J29)
Before the start call a 20 m move side-stepped the unit 1.6 m and did not walk; a 90 degree turn turned it at once and its centre jumped
about 6.5 m. J29 keeps deployment orders inert.

## i) Halt and formations
i2: unit 5 sent 51 m away, halted 6 s later through the dispatcher (cmd 7, `moving 1` at the dispatch): at rest 4 m on, short of its
target. i3/i4: square on (0x22) changed the depth by 1.38 m, square off (0x23) back by 1.38 m. i5/i6: wedge (0x24) had no effect on
infantry or on the cavalry unit (`failed: no effect read back`).

## Every order (generated by `table.py` from `raw/`)

| run | scene | unit | action | status | front m | facing deg | width m | centre lateral m | centre ahead m | moved | settle s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c1_move | land_small | 4 | move | ok | 0.0 | 0.0824 | 0.0 |  |  | True | 18.43 |
| c2_face90 | land_small | 4 | move | failed: not at rest before the timeout | 0.0 | 0.1428 | 0.0 | 0.0316 | 0.0 | True | 16.03 |
| c3_face270_w50 | land_small | 5 | move | failed: not at rest before the timeout | 0.0 | 0.0385 | 0.0 | 0.0778 | 0.0 | True | 43.12 |
| c4_face0_w20 | land_small | 6 | move | ok | 0.0 | 0.0494 | 0.0 | 0.0073 | 0.0 | True | 22.82 |
| c5_long_cav | land_small | 3 | move | failed: readback outside tolerance | 0.0 | 1.4832 **out** | 0.0 | 1.273 | 0.0 | True | 33.92 |
| c6_back90 | land_small | 4 | move | failed: readback outside tolerance | 40.0405 **out** | 89.989 **out** | 18.1 **out** | 11.8755 **out** | 37.3321 **out** | True | 56.5 |
| c7_long_cav | land_small | 3 | move | ok | 0.0 | 0.0659 | 0.0 | 0.0273 | 0.0 | True | 13.4 |
| c8_back | land_small | 4 | move | ok | 0.0 | 0.1593 | 0.0 | 0.1037 | 0.0 | True | 13.01 |
| d1_army_line | land_small | 1 | move | failed: readback outside tolerance | 0.0 | 36.0571 **out** | 0.0 | 2.7684 **out** | 0.0 | True | 80.46 |
| d1_army_line | land_small | 2 | move | failed: readback outside tolerance | 0.0 | 0.3351 | 0.0 | 0.094 | 0.0384 **out** | True | 96.67 |
| d1_army_line | land_small | 3 | move | ok | 0.0 | 0.4669 | 0.0 | 1.2936 | 0.0 | True | 90.25 |
| d1_army_line | land_small | 4 | move | failed: not at rest before the timeout | 0.0 | 0.39 | 0.0 | 0.0632 | 0.0 | True | 101.81 |
| d1_army_line | land_small | 5 | move | ok | 0.0 | 0.0 | 0.0 | 0.05 | 0.0 | True | 90.25 |
| d1_army_line | land_small | 6 | move | ok | 0.0 | 0.2032 | 0.0 | 0.8323 | 0.0 | True | 80.46 |
| d1_army_line | land_small | 7 | move | ok | 0.0 | 0.3131 | 0.0 | 0.3669 | 0.0 | True | 90.25 |
| d1_army_line | land_small | 8 | move | failed: not at rest before the timeout | 0.0 | 0.9613 | 0.0 | 0.7804 | 0.0 | True | 101.81 |
| d1_army_line | land_small | 9 | move | failed: not at rest before the timeout | 0.0 | 0.39 | 0.0 | 0.3996 | 0.0 | True | 101.81 |
| d2_army_line | land_small | 9 | move | failed: not at rest before the timeout | 0.0 | 0.1758 | 0.0 | 0.5602 | 0.0 | True | 41.07 |
| d2_army_line | land_small | 7 | move | failed: not at rest before the timeout | 0.0 | 0.0275 | 0.0 | 0.1511 | 0.0 | False | 41.07 |
| d2_army_line | land_small | 6 | move | failed: not at rest before the timeout | 0.0 | 0.6042 | 0.0 | 0.1976 | 0.0 | True | 41.07 |
| d2_army_line | land_small | 5 | move | failed: not at rest before the timeout | 0.0 | 0.1099 | 0.0 | 0.007 | 0.0 | False | 41.07 |
| d2_army_line | land_small | 1 | move | failed: not at rest before the timeout | 0.0 | 7.2729 **out** | 0.0 | 0.2918 | 0.0 | False | 41.07 |
| d2_army_line | land_small | 4 | move | failed: not at rest before the timeout | 0.0 | 0.0494 | 0.0 | 0.0579 | 0.0 | False | 41.07 |
| d2_army_line | land_small | 2 | move | failed: not at rest before the timeout | 0.0 | 0.2197 | 0.0 | 0.006 | 0.0 | False | 41.07 |
| d2_army_line | land_small | 8 | move | failed: not at rest before the timeout | 0.0 | 0.379 | 0.0 | 0.9165 | 0.0 | False | 41.07 |
| d2_army_line | land_small | 3 | move | failed: not at rest before the timeout | 0.0 | 0.0989 | 0.0 | 0.2621 | 0.0 | False | 41.07 |
| d3_army_line | land_small | 9 | move | failed: not at rest before the timeout | 0.0 | 0.2087 | 0.0 | 0.1727 | 0.0 | True | 40.68 |
| d3_army_line | land_small | 7 | move | failed: not at rest before the timeout | 0.0 | 0.033 | 0.0 | 0.0299 | 0.0 | True | 40.68 |
| d3_army_line | land_small | 6 | move | failed: not at rest before the timeout | 0.0 | 0.0 | 0.0 | 0.0845 | 0.0 | False | 40.68 |
| d3_army_line | land_small | 5 | move | failed: not at rest before the timeout | 0.0 | 0.0275 | 0.0 | 0.0548 | 0.0 | False | 40.68 |
| d3_army_line | land_small | 1 | move | failed: not at rest before the timeout | 0.0 | 4.5044 **out** | 0.0 | 0.0747 | 0.0 | False | 40.68 |
| d3_army_line | land_small | 4 | move | failed: not at rest before the timeout | 0.0 | 0.0 | 0.0 | 0.0048 | 0.0 | False | 40.68 |
| d3_army_line | land_small | 2 | move | failed: not at rest before the timeout | 0.0 | 0.0275 | 0.0 | 0.0294 | 0.0 | False | 40.68 |
| d3_army_line | land_small | 8 | move | failed: not at rest before the timeout | 0.0 | 0.0714 | 0.0 | 0.0467 | 0.0 | False | 40.68 |
| d3_army_line | land_small | 3 | move | failed: not at rest before the timeout | 0.0 | 0.033 | 0.0 | 0.2574 | 0.0 | False | 40.68 |
| d4_army_line | land_small | 9 | move | ok | 0.0 | 0.5548 | 0.0 | 0.0955 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 7 | move | ok | 0.0 | 0.0934 | 0.0 | 0.099 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 6 | move | ok | 0.0 | 0.1154 | 0.0 | 0.0122 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 5 | move | ok | 0.0 | 0.0824 | 0.0 | 0.0309 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 1 | move | failed: readback outside tolerance | 0.0 | 6.6852 **out** | 0.0 | 0.2687 | 0.0 | True | 12.73 |
| d4_army_line | land_small | 4 | move | ok | 0.0 | 0.0 | 0.0 | 0.0018 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 2 | move | ok | 0.0 | 0.1044 | 0.0 | 0.0398 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 8 | move | ok | 0.0 | 0.3461 | 0.0 | 0.5522 | 0.0 | True | 10.37 |
| d4_army_line | land_small | 3 | move | ok | 0.0 | 0.1154 | 0.0 | 0.2972 | 0.0 | True | 10.37 |
| e1_walk | land_small | 5 | move | ok | 0.0 | 0.0249 | 0.0 | 0.0065 | 0.0 | True | 33.71 |
| e2_run | land_small | 6 | move | ok | 0.0 | 0.0525 | 0.0 | 0.196 | 0.0 | True | 20.25 |
| f1_offmap | land_small |  |  | failed: RuntimeError: step read 0x3b30c988: orders refused: 0x3b30c988: the un |  |  |  |  |  |  |  |
| f2_stale_ptr | land_small |  |  | refused: unit 0x33d694c8: orders refused: 0x33d694c8: the unit's army is not re |  |  |  |  |  |  |  |
| f3_bad_width | land_small |  |  | refused: unit 4: width must be in (0.5, 1000] metres |  |  |  |  |  |  |  |
| g2_siege_move | siege_small | 4 | move | ok | 0.0 | 0.0015 | 0.0 | 0.012 | 0.0 | False | 9.13 |
| g3_siege_turn | siege_small | 5 | move | failed: readback outside tolerance | 0.0 | 89.7328 **out** | 0.0 | 3.5835 **out** | 0.0 | True | 18.2 |
| g4_siege_line | siege_small | 8 | move | failed: readback outside tolerance | 0.0 | 0.1318 | 0.0 | 16.8728 **out** | 12.2801 **out** | False | 8.47 |
| g4_siege_line | siege_small | 4 | move | failed: readback outside tolerance | 0.0 | 0.0385 | 0.0 | 30.4952 **out** | 0.0 | False | 8.47 |
| g4_siege_line | siege_small | 5 | move | failed: readback outside tolerance | 0.0 | 0.2637 | 0.0 | 20.8718 **out** | 0.0 | False | 8.47 |
| g4_siege_line | siege_small | 6 | move | failed: readback outside tolerance | 0.0 | 32.6129 **out** | 0.0 | 16.668 **out** | 0.0 | True | 18.01 |
| g4_siege_line | siege_small | 7 | move | ok | 0.0 | 0.1208 | 0.0 | 0.147 | 0.0 | True | 13.23 |
| g4_siege_line | siege_small | 9 | move | ok | 0.0 | 0.0879 | 0.0 | 0.1193 | 0.0 | True | 13.23 |
| g7_siege_cliff | siege_small | 4 | move | failed: not at rest before the timeout | 0.0 | 10.7266 **out** | 0.0 | 45.6227 **out** | 6.2706 **out** | True | 85.83 |
| g8_siege_back | siege_small | 7 | move | ok | 0.0 | 0.0376 | 0.0 | 0.0381 | 0.0 | True | 22.19 |
| h2_deploy_move | land_small (deploying) | 4 | move | failed: the unit never moved: the engine took the order and found no path (a c | 0.0 | 0.0589 | 0.0 | 0.0496 | 14.945 **out** | False | 8.4 |
| h3_deploy_turn | land_small (deploying) | 6 | move | failed: readback outside tolerance | 0.0 | 0.3469 | 0.0 | 8.0707 **out** | 0.0 | False | 9.24 |
| i2_halt | land_small | 5 | halt | ok | moving 0 |  |  |  |  | True | 13.44 |
| i3_square | land_small | 4 | square | ok | shape 1.3821 |  |  |  |  | True | 18.23 |
| i4_square_off | land_small | 4 | square_off | ok | shape 1.3844 |  |  |  |  | True | 13.52 |
| i5_wedge | land_small | 6 | wedge | failed: wedge: no effect read back | shape 0.0 |  |  |  |  | False | 8.69 |
| i6_wedge_cav | land_small | 3 | wedge | failed: wedge: no effect read back | shape 0.0 |  |  |  |  | False | 8.62 |
