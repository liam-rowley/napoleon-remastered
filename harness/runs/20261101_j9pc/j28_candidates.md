# J28 candidates on Napoleon.exe: unit state, selection, direct orders (J9 deliverable 4, static RE)

Exe: `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, ImageBase 0x400000, ASLR on (every VA below is a static VA:
rebase as `va - 0x400000 + GetModuleHandle(NULL)`, and rebase relocated dwords inside guard bytes the same way).
Static only, 2026-11-01, nothing run on the PC. Empire VAs appear only in the "Empire analogue" column, never as Napoleon facts.

Helper scripts (read-only, venv python `-I`): `C:\napoleon_remastered_pc\_scratch\J9\re\py\`
`j28_regs.py lo hi` (luaL_Reg dumper), `j28_edis.py [--nap] [-r] va[:n]` (section-aware disassembler for both exes),
`j28_dis.py`, `j28_fstart.py` (function start + callers), `j28_disp.py` (disp32 search), `j28_guard.py va...` (guard bytes,
relocations, ret, caller count: the table columns below come from it). Outputs kept: `py\j28_regs_out.txt`, `py\j28_qpush.txt`.

"Relocs" = offsets (from the entry) of relocated dwords overlapping the first 16 bytes; "first 8" = whether one falls in bytes 0-7.
"Unique" = the first N bytes occur once in `.text`.

---------------------------------------------------------------------------------------------------------------------------------

## 1. Battle-script luaL_Reg tables and the unit getters (the UNIT layout)

The battle-script interface is compiled in, as on Empire. Tables are Lunar method tables (name ptr, func ptr), each referenced
twice from its class's register function (class name pushed in the same function). Full dump: `py\j28_regs_out.txt`.

| Table (class) | VA | Entries | Found by |
|---|---|---|---|
| `battle.units` (item, count, kill_commander) | 0x14514fc | 3 | register fn 0x6285c2 |
| `battle.ship` | 0x1451520 | 11 | register fn 0x627512 |
| `battle.ships` | 0x1451590 | 2 | 0x627772 |
| `battle.armies` | 0x14515a8 | 2 | 0x625fb2 |
| `battle.army` (units, ships, create_unit_controller, ...) | 0x14515d0 | 7 | 0x626212 |
| `empire_battle` (the `battle` global: register_*_handler, camera, ...) | 0x1451610 | 37 | 0x626df2 |
| `battle.unit_controller` (goto_location_angle_width, change_formation, ...) | 0x1451750 | 49 | 0x628822 |
| `battle.ship_controller` | 0x1451990 | 35 | 0x6279d2 |
| `battle.alliances` | 0x1451e00 | 2 | 0x625d52 |
| **`battle.unit`** | **0x1451e28** | 22 | register fn refs 0x628362/0x62836a; `battle.unit` string refs 0x628167/0x628183 in the same fn |

Found by: `exe_strings find '^(number_of_men_alive|is_moving|bearing|position)$'` gave data refs RVA 0x1051e38..0x1051e60; the
dumper walked the pairs.

### 1a. Getters

| What | VA / RVA | How found | First 16 bytes | Relocs / first 8 | Ret, callers | Conf. |
|---|---|---|---|---|---|---|
| `battle.unit.position` | 0x616d10 / 0x216d10 | `battle.unit` table entry 0x1451e38 | `83 ec 0c 56 ff 74 24 14 8b f1 e8 21 3a 06 00 8b` | none / no | ret 4, 0 E8 (table only); unique at 16 | high |
| `battle.unit.bearing` | 0x616d60 / 0x216d60 | table entry 0x1451e40 | `56 ff 74 24 08 8b f1 e8 d4 39 06 00 8b 46 04 83` | none / no | ret 4; unique at 16 | high |
| `battle.unit.is_moving` | 0x616de0 / 0x216de0 | table entry 0x1451e48 | `56 57 ff 74 24 0c 8b f9 e8 53 39 06 00 8b 0d 54` | +15 (0x14d0154) / no | ret 4 | high |
| `battle.unit.number_of_men_alive` | 0x616f40 / 0x216f40 | table entry 0x1451e60 | `56 ff 74 24 08 8b f1 e8 f4 37 06 00 8b 0d 54 01` | +14 / no | ret 4 | high |
| `battle.unit.name` (gives the army list) | 0x616bc0 / 0x216bc0 | table entry 0x1451e28 | `83 ec 24 56 8b f1 8b 0d 54 01 4d 01 57 e8 de 1a` | +8 / no | ret 4 | high |
| UNIT is_moving impl (thiscall, ecx = UNIT) | 0x55c320 / 0x15c320 | called by is_moving | `83 b9 e8 0a 00 00 00 74 17 8b 81 e8 0a 00 00 8b` | none / no | ret, 26 callers | high |
| entity "has order" impl (ecx = E) | 0x55c2e0 / 0x15c2e0 | tail of 0x55c320 | `83 b9 60 04 00 00 00 75 03 32 c0 c3 8b 81 60 04` | none / no | ret, 13 callers | high |
| position block -> (P+0xb0) | 0x53fbe0 | called by position | `8d 81 b0 00 00 00 c3` | none | 635 callers (generic) | high |
| world position copy (frame == 0 -> plain x,y,z) | 0x80e9d0 | called by position | `8b 41 10 85 c0 74 13 51 ff 74 24 08 8b c8 e8 6d` | none | ret 4, 1215 callers (generic) | high |
| UI `BattleUnit:Position` (only Lunar method of BattleUnit; table 0x1456298) | 0x859750 / 0x459750 | BattleUnit register fn 0x859a50 reads method table 0x1456298 | `83 ec 0c 56 ff 74 24 14 8b f1 e8 f1 ef 7f 00 89` | none / no | ret 4 | high |

Script wrapper: `UNIT = [wrapper+4]` (all battle.unit getters: `mov eax,[esi+4]` / `mov ecx,[esi+4]`). UI wrapper:
`UNIT = [wrapper+0x24]` (0x859765 `mov eax,[esi+0x24]`), and it walks the same chain as the script getter, so the UI
`BattleUnit` and the script UNIT are the same object type (high).

### 1b. UNIT / entity offsets proven statically

| Field | Napoleon | Proving instruction(s) | Empire analogue | Conf. |
|---|---|---|---|---|
| entity E | `E = [UNIT+0xadc]` | 0x616d25 `8b 88 dc 0a 00 00` mov ecx,[eax+0xadc] (position); 0x616d75 `8b 80 dc 0a 00 00` (bearing); 0x85976c (UI) | +0xa28 | high |
| facing, int16 binary angle | `movsx [E+0x64c]` | 0x616d7c `0f bf 80 4c 06 00 00`; scaled by [0x13359f4] = 360/65536 (0.0054931640625), +[0x1335a60] = 360.0 when negative (via [0x1325c60] = 2pi/65536) | E+0x648 | high |
| position block P | `P = E+0x62c` | 0x616d2b `8d 89 2c 06 00 00` lea ecx,[ecx+0x62c] | E+0x628 | high |
| live position x,y,z (formation centre per Empire) | floats `[E+0x6dc], [E+0x6e0], [E+0x6e4]` (= P+0xb0..+0xb8) | 0x53fbe0 `lea eax,[ecx+0xb0]`; 0x80e9ea..0x80ea01 copies [+0],[+4],[+8] when frame == 0 | E+0x6d8/+0x6dc/+0x6e0 | high (meaning "centre": from Empire, medium) |
| frame pointer (0 on land) | `[E+0x6ec]` (= P+0xc0) | 0x80e9d0 `8b 41 10` mov eax,[ecx+0x10] with ecx = P+0xb0; `je` to the plain copy when 0 | E+0x6e8 | high |
| men alive | `[UNIT+0x204]` | 0x616f5d `ff b1 04 02 00 00` push [ecx+0x204]; UNIT ctor 0x51b8a0 zeroes it | +0x178 | high |
| army | `[UNIT+0x1ec]` | 0x616c09 `8b 81 ec 01 00 00`; UNIT ctor 0x51b872 `mov [ebp+0x1ec],ecx` | +0x160 | high |
| army unit count / UNIT*[] | `[army+0xf0]` / `[army+0xf4]` | 0x616c0f `8b 90 f0 00 00 00`, 0x616c19 `8b 80 f4 00 00 00`; the allocator 0x531347 pushes each new UNIT into the container at army+0xe4 (0x483d40: +8 cap, +0xc count, +0x10 data) | same | high |
| active entity index | `[UNIT+0xae8]`; entity i = `[UNIT+0xadc+i*4]` | 0x55c320 `83 b9 e8 0a 00 00 00`, 0x55c32f `8b 8c 81 dc 0a 00 00` | +0xa34 | high |
| entity order count / entries (8 B each) | `[E+0x460]` / `[E+0x418+i*8]` | 0x55c2ec `8b 81 60 04 00 00`, 0x55c2f2 `8b 8c c1 18 04 00 00` | same | high |
| unit record (name at record+0xf0) | `[UNIT+0x1c]` | 0x616be3 `8b 49 1c`, 0x616be6 `add ecx,0xf0` | n/a | high |
| group pointer (grouped units) | `[UNIT+0xaec]` | 0x5f0c79 `8b 80 ec 0a 00 00` (selection rebuild adds the group, not the unit, when the entry's group id != -1) | n/a | medium |
| UNIT object size | 0xe38 | allocator 0x531320: `68 38 0e 00 00` push 0xe38; `call 0x10d3140` (operator new); then the only call of the UNIT ctor 0x51b7d0 | "stride 0xD68" (Empire got it from a runtime log, not statically) | high (size of the heap object; units are separate allocations, walk them through army+0xf4 pointers, not by stride) |
| formation front centre / width | probably `UNIT+0x310` (x,y,z) and `UNIT+0x324` (width) | NOT proven by an access. Structural: Empire's +0x284/+0x298 lie in the 0x84-byte sub-object built at Empire UNIT+0x274 by 0x5098f0 (`c6 81 80 00 00 00 00 8b c1 c3`); Napoleon builds the byte-identical sub-object at UNIT+0x300 (0x51ba08 `lea ecx,[ebp+0x300]`, ctor 0x51d400 same 10 bytes), and the neighbouring inits shift by exactly 0x8c (Empire +0x26c/+0x270/+0x2f8 = Napoleon +0x2f8/+0x2fc/+0x384) | +0x284 / +0x298 | medium: check on the PC (compare +0x310 against the order location after a move; +0x324 against the drag width) |
| ranks | not found | no getter in battle.unit; no static anchor tried beyond the above | none on Empire either | open |

Shift summary (Empire -> Napoleon): UNIT fields before ~+0x300 move by +0x8c, the entity block by +0xb4, entity-internal fields by +4
(0x648 -> 0x64c, 0x628 -> 0x62c), the order fields (+0x418/+0x460) not at all. Do not extrapolate other offsets from this.

---------------------------------------------------------------------------------------------------------------------------------

## 2. Direct order path

Two reference call sequences in the exe, both matching Empire's route (c) shape:
- script `battle.unit_controller.goto_location_angle_width` 0x613590 -> impl 0x645770 (args: queue flag 0, `_q` 0x6135a0 passes 1);
  it builds the selection (0x646a20), the order (0x599760), then **inlines** the queue push on `[[[0x14d0154]+0x404]+0x28048]`.
- the UI ground-order handler 0x5deab0 (slot 11 of UI command vtable 0x132fdd0): `0x599760(sel=[this+0xc], &loc, angle, width, 0, queue)`
  at 0x5dec34, `mov ecx,[ebp+0xf8]; mov ecx,[ecx+0x28048]; call 0x58dc00` at 0x5dec39..0x5dec4a, then `call 0x5a95b0` (dtor) at
  0x5dec53. ebp = the handler's context argument, whose +0xf8 is the battle.

| What | VA / RVA | How found | First 16 bytes | Relocs / first 8 | Ret, callers, unique | Conf. |
|---|---|---|---|---|---|---|
| **Selection ctor** (thiscall, no args; object 0x44 bytes: vtable 0x132b5e8, four 16-byte containers at +4/+0x14/+0x24/+0x34) | 0x68f580 / 0x28f580 | the order ctor writes the selection vtable 0x132b5e8 at order+4; the only function storing it to [ecx] with Empire's body shape (`mov [ecx],vt; mov eax,ecx; 12 x mov [ecx+n],0; ret`); one of J6's `multiple` candidates (0x28f580) for Empire 0x746120 | `c7 01 e8 b5 32 01 8b c1 c7 41 08 00 00 00 00 c7` | **+2 (vtable 0x132b5e8) / YES** | ret, 14 callers (incl. 0x646a35 script path, 0x5f0bec UI rebuild); unique at 16 | high |
| **Selection AddUnit** (thiscall, 1 arg UNIT*; checks the unit with 0x55c440, pushes into the sel+0x14 container) | 0x6a0480 / 0x2a0480 | J6 signature `unique` for Empire 0x752770 (32 bytes, 4 masked = 28 fixed); called per unit by the script path 0x646ad5 and the UI rebuild 0x5f0c72 | `56 8b 74 24 08 57 8b f9 8b ce e8 b1 bf eb ff 84` | none / no | ret 4, 3 callers; unique at 16 | high |
| unit check used by AddUnit (ecx = UNIT; refuses state [UNIT+0xaa0] 0/2, ...) | 0x55c440 / 0x15c440 | first call in AddUnit | `56 8b f1 8b 86 a0 0a 00 00 85 c0 74 2c 83 f8 02` | none / no | ret, 8 callers | high |
| **Order ctor "move/face"** (thiscall, 6 args: Selection*, loc[5]*, int16 angle, float width, bool run, bool queue; object >= 0x74 bytes, vtables 0x132b64c / 0x132b5e8) | 0x599760 / 0x199760 | callee of 0x645770 (goto_location_angle_width) and of the UI handler 0x5dec34; instruction-for-instruction the body of Empire 0x581b70 (copies sel+4/+0x14/+0x24/+0x34, loc to +0x48..+0x58, angle word +0x5c, width +0x60, run +0x64, queue +0x70, +0x68 = 0, +0x6c = 8) | `56 8b 74 24 08 57 8b f9 8d 46 04 50 8d 4f 08 c7` | none in 16 / no (vtables at +0x11 and +0x18 are relocated) | **ret 0x18**, 2 callers; **first 16 bytes shared by ~23 sibling command ctors: unique only at 32 bytes** (guard 32 bytes, rebasing the dwords at +0x11 and +0x18) | high |
| **Queue push for this command type** (thiscall on the queue, 1 arg Command*; returns al) | 0x58dc00 / 0x18dc00 | template family `83 ec 10 53 56 51 54 8b f1 e8 <type id helper>` (33 instances, `py\j28_qpush.txt`); this instance's type helper 0x58dfd0 (reads [0x14a6610]) is the one the inlined push in 0x645770 uses (0x6458d6/0x6458eb); its two callers both push a 0x599760/0x5996b0 command on `[battle+0x28048]` | `83 ec 10 53 56 51 54 8b f1 e8 c2 03 00 00 83 c4` | none / no (the E8 rel32 makes it unique) | ret 4, 2 callers (0x5dec4a, 0x5df2a8); unique at 16 | high |
| **Command dtor** (thiscall, frees the 4 selection buffers at +0x44/+0x34/+0x24/+0x14, resets vtables) | 0x5a95b0 / 0x1a95b0 | J6 signature `unique` for Empire 0x5ac3a0 (24 fixed); called right after the push at 0x5dec53, 0x5df2b1, and after the formation push 0x645152 | `56 8b f1 8b 46 44 85 c0 74 09 50 e8 30 e9 a4 00` | none / no | ret, 56 callers; unique at 16 | high |
| engine free (cdecl) | 0xff7ef0 / 0xbf7ef0 | already matched (J6, 16/16 fixed); called by 0x5a95b0 | `8b 44 24 04 83 ec 08 85 c0 74 1a 50 8d 44 24 04` | none / no | ret | high |
| Formation command ctor (thiscall, 3 args: Selection*, int formation, bool queue; ret 0xc) | 0x599320 / 0x199320 | script `change_formation` 0x6143a0 -> 0x644fa0 -> 0x64512e; UI dispatcher 0x5de1d6 (formation = (int) of the float argument) | `56 8b 74 24 08 57 8b f9 8d 46 04 50 8d 4f 08 c7` | none in 16 / no (vtables +0x11, +0x18) | ret 0xc, 4 callers; unique at 24 | high (meaning of the int: index from a name lookup 0x6b3e90 in the script path; medium) |
| Queue push for the formation command | 0x58d780 / 0x18d780 | callee right after 0x599320 at 0x645149 / 0x5de1de, on the same `[battle+0x28048]` | `83 ec 10 53 56 51 54 8b f1 e8 42 07 00 00 83 c4` | none / no | ret 4, 4 callers; unique at 16 | high |
| Second UI move-type ctor (7 args, ret 0x1c) | 0x5996b0 / 0x1996b0 | UI handler 0x5df0b0 (slot 11 of vtable 0x132fe08) at 0x5df292, pushed with 0x58dc00 | `56 8b 74 24 08 57 8b f9 8d 46 04 50 8d 4f 08 c7` | none / no | ret 0x1c, 1 caller | medium (role not traced: probably move with an extra mode argument, pushes 4 and 1) |
| reference: goto_location_angle_width impl | 0x645770 / 0x245770 | table entry 0x1451898 -> thunk 0x613590 | `81 ec ac 00 00 00 53 56 8b b4 24 b8 00 00 00 8b` | none / no | ret 8 | high |

Argument facts (all from 0x645770 unless marked):
- angle: Lua degrees * [0x1325c7c] (pi/180) * [0x1325dac] (10430.378 = 32768/pi), `fistp` -> int16 binary angle (65536 = 360 deg), the
  same unit as the bearing at [E+0x64c].
- loc: 5 dwords; the ctor copies [loc+0..+0x10] to order+0x48..+0x58. The script projects (x, z) to the ground with 0x7fcff0
  (ecx = `[[[[0x14d0154]+0x404]+8]+0xb4]`) before building it.
- width: float, the script rejects <= 0 (0x645822).
- run: script arg 4 (`setne`); the UI ground handler passes 0. queue: 0 / 1 (`_q` variants); the UI passes byte [input+2].

### 2a. Globals the queue hangs off

| Global | VA | Evidence | Path to the queue | Conf. |
|---|---|---|---|---|
| **battle UI owner** (Empire analogue 0x137d488) | **0x14a418c** | one writer: setter 0x5f67e0 `8b 44 24 04 a3 8c 41 4a 01 c3` (callers 0x598e09, 0x5a959b); already in the registry as the CameraZoomTo owner (RVA 0x1ce994) | battle = `[owner+0xf8]`; queue = **`[[[0x14a418c]+0xf8]+0x28048]`**. UI-side site (Empire analogue 0x5f741d): **0x5d0520** `a1 8c 41 4a 01 51 54 8b 80 f8 00 00 00 8b b0 48 80 02 00 e8` (reloc at +1, unique at 16); second site 0x5ced64 | high |
| battle script interface (Empire analogue 0x13a8ad0) | 0x14d0154 | set at 0x61b63d `mov [0x14d0154],ebx` (end of its ctor), cleared at 0x622ef5 | battle = `[iface+0x404]`; queue = `[[[0x14d0154]+0x404]+0x28048]` (0x6458c3..0x6458d0, and ~40 script commands 0x611c5a..0x644d28) | high for the path; **whether it is 0 in custom battles is not known statically** (it was 0 on Empire) |
| owner+0x454 | | 0x5ae8c1 `add ecx,0x454` then 0x5ddd09 `mov eax,[ebx]` -> `[eax+0x28048]` | another battle pointer in the owner (same queue) | medium |

Before the push the engine also checks `[battle+0x281e4]` (0x5deac9 / 0x5ddd09: if non-null and its vtable+0xe0 returns true, the
order is dropped): a cheap pre-check J28 can copy.

---------------------------------------------------------------------------------------------------------------------------------

## 3. UICardManager / how the UI gets the selected units

| What | VA / RVA | How found | First 16 bytes | Conf. |
|---|---|---|---|---|
| UICardManager Lunar table (ManageSelection, AddCard, RemoveCard, RemoveAll, Selected, SelectCardList, DeselectAll, DeselectCard, Cards, DragSelected, AddToGroup, RemoveFromGroup, PositionCards, ToggleGrouping, FindContainingGroupID, ManageGroupSelection, SetInactive, SetAsActive, IsShiftHeld, IsCtrlHeld) | table 0x1464078 (20 entries) | `Selected`/`DeselectAll` data refs; register fn 0x45e112 pushes `UICardManager` | n/a | high |
| `UICardManager:Selected` | 0x1018e30 / 0xc18e30 | table entry 0x1464098 | `83 ec 58 56 57 ff 74 24 64 8b f1 89 74 24 60 e8` (no relocs, ret 4) | high |
| UISelectionManager Lunar table (ManageSelection, Add, Remove, RemoveAll, Selected, DeselectAll) | 0x1464248 | register fn 0x1031372 | n/a | high |
| **BattleUI.SelectionChanged** ("Notify the game that unit selection has changed") | 0x5d3410 / 0x1d3410 | static registrar at 0x40b6f0 (doc, name, func; ecx = 0x14a5b3e, registrar 0x59eb40) | `ff 74 24 04 e8 37 53 a8 00 83 c4 04 85 c0 74 0d` | high |
| owner selection update (thiscall on the owner, 1 arg) | 0x5af710 / 0x1af710 | SelectionChanged: `mov ecx,[0x14a418c]; push 1; call 0x5af710` | `83 ec 28 53 56 8b f1 57 8b 8e 08 01 00 00 85 c9` (ret 8) | high |
| selection rebuild (ecx = holder H) | 0x5f0be0 / 0x1f0be0 | tail of 0x60d9c0, which 0x5af710 calls on `[owner+0x450]` | `83 ec 48 53 56 8b d9 8d 4c 24 0c 57 e8 8f e9 09` | high |
| "current selection" command dispatcher (thiscall on owner: cmd, float) -> 0x5ddd00(sel, cmd, float, byte [owner+0x42b]) | 0x5ae8a0 / 0x1ae8a0 | every `Current_Selection_*` BattleUI function calls it (e.g. Halt 0x5cdfd0 -> cmd 7; Square formation 0x5cfdf0 -> cmd 0x22) | `0f b6 81 2b 04 00 00 f3 0f 10 44 24 08 50 8b 81` (ret 8, 96 callers) | high |

What the code shows:
- `UICardManager` object: selected cards = count `[mgr+0x20]`, array `[mgr+0x24]` (component pointers); groups = count `[mgr+0x40]`,
  array `[mgr+0x44]` (0x1018ea6..0x1018f2d). `Selected` returns the card components; card -> UNIT is the card's own Lua
  (`LuaCall("ItemAddress")`, string 0xf31210 used from C++ at 0x5886c6 to call into the component script), not a C++ field.
  So C++ should not go through the cards.
- **The engine-side selection the UI orders use:** `H = [[0x14a418c]+0x450]` (selection holder), `S = H+0x20` (a Selection,
  same type as 0x68f580 builds). Proofs: 0x5ae8ae..0x5ae8ba `mov eax,[ecx+0x450]; add eax,0x20` passed as the selection to the
  dispatcher; 0x5af733..0x5af739 the same, and the UI move command object gets it as `[cmd+0xc]` (ctor 0x598d00), which the ground
  handler passes to the order ctor at 0x5dec31 `push [edi+0xc]`.
- Selection layout (from 0x68f580, AddUnit 0x6a0480 + container push 0x448b90, and the counters 0x6f2350 / 0x6f2300): container =
  (+4 capacity, +8 count, +0xc data). Land groups: count `[S+0xc]`, array `[S+0x10]`; **loose land units: count `[S+0x1c]`,
  UNIT*[] `[S+0x20]`**; ship groups `[S+0x2c]/[S+0x30]`; ships `[S+0x3c]/[S+0x40]`. 0x6f2350 = number of land units (sum of group
  sizes via 0x5ea790 + loose count); 0x6f2300 = the same for ships.
- The rebuild 0x5f0be0 resets S and refills it from H's list (H vtable slot 0: entries of 0x14 bytes, +0xc -> UNIT**, +0x10 group
  id; -1 = AddUnit(UNIT), else 0x6a04b0(UNIT+0xaec group)); slot 1 gives ships (0x69ffb0 / 0x6a00d0 with [ship+0x4c0]).
  So J28 can (a) read S directly for "the units the player has selected", or (b) build its own Selection with 0x68f580 + 0x6a0480,
  as the script path does, without touching the UI's.

---------------------------------------------------------------------------------------------------------------------------------

## Suggested engine_sites rows (all `kind: hook`, read or call only; nothing patched)

Guard windows: 16 bytes unless noted; rebase the relocated dword(s) before comparing.

| id (suggested) | RVA | Bytes to check | Relocated dwords |
|---|---|---|---|
| battle.unit_position_getter | 0x216d10 | 16 | none |
| battle.unit_bearing_getter | 0x216d60 | 16 | none |
| battle.selection_ctor | 0x28f580 | 16 | +2 |
| battle.selection_add_unit | 0x2a0480 | 16 | none |
| battle.order_move_ctor | 0x199760 | **32** (16 is shared by sibling ctors) | +0x11, +0x18 |
| battle.order_queue_push | 0x18dc00 | 16 | none |
| battle.command_dtor | 0x1a95b0 | 16 | none |
| battle.order_formation_ctor | 0x199320 | **24** | +0x11 (+0x18 if 32) |
| battle.order_formation_push | 0x18d780 | 16 | none |
| battle.ui_queue_site (owner -> battle -> queue) | 0x1d0520 | 16 | +1 |
| battle.ui_owner_setter | 0x1f67e0 | 10 | +5 |
| battle.selection_dispatch (current selection orders) | 0x1ae8a0 | 16 | none |

Engine free 0xbf7ef0 is already matched.

## Not found / open

- **Front centre and width:** UNIT+0x310 / +0x324 is a structural inference (see 1b), not an access. Tried: tiny getters for
  0x284/0x298 (Empire) vs 0x310/0x324/0x338/0x34c (Napoleon), disp32 co-occurrence with the entity offset, the drag-frontage helper
  0x6d9280 (reads the selection, not UNIT fields). The order serialiser 0x5dc810 (vtable 0x132b64c slot 0) shows the command is
  serialised into the queue, so the code that writes the unit's destination is on the deserialise/execute side (0x5f09xx area), not traced.
- **Ranks:** no anchor found.
- **Custom battles:** whether `[0x14d0154]` is 0 there (it was on Empire) needs a live peek; use the owner path `[[0x14a418c]+0xf8]`
  regardless. Also check on the PC that `[owner+0xf8]` and `[owner+0x454]` hold the same battle.
- **Run flag:** the UI ground handler passes run = 0; where double-right-click running comes from was not traced.
- 0x5996b0 (7-arg move-type ctor) role, and the UI handler vtables 0x132fdd0 / 0x132fe08 slots other than 11, not traced.
- Threading: like Empire, call the order path on the thread that runs the UI (the callers here are UI handlers and Lua C
  functions); not verified statically.
