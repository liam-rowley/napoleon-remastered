#!/usr/bin/env python3
"""J60 engine_sites rows for the ship chain, generated from a copy of the stock Napoleon.exe.

purpose: print one engine_sites JSON row per J60 ship site (anchor = the 4 bytes before, stock bytes, relocated dwords named in the
         description); warns on stderr when the stock bytes (relocated dwords masked) are not unique in the image
usage: <re venv python> -I harness/runs/20261103_j60re/re/j60rows.py <exe> > rows.jsonl   (then wsc reg add engine_sites --json <row>)
when: re-deriving or extending the J60 rows (the PC slot adds `verified` with its run id)
not-a-verb: reads a copy of the exe (read only); writes stdout only
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'discovery', 'core'))
import x86re  # noqa: E402
im = x86re.Image(sys.argv[1])
R = set(im.relocs())
EXE = 'sha1:9aebcd2172f2878d781b079f7feb45b0e12e0250'
NOTE = 'J60 static RE (harness/runs/20261103_j60re/README.md)'
CALL = 'called by dev.orders (orders.cpp, ship route) on the engine thread; nothing detoured'
READ = 'read only: offsets read from these bytes at install (dev.orders, ship route); nothing detoured'

ROWS = [
    ('battle.ship_vtable_store', 0x691f22, 32, READ,
     'SHIP ctor 0x691c10 (operator new 0x2120 at 0x506372): mov [edi], <SHIP vtable 0x1338780> (dword at +2, relocated); mov [edi+0x130], <vtable 0x13387c4> (+12, relocated)',
     'J60 ship state: the SHIP vtable (dword at +2): every read checks [ship] == it (a stale or foreign pointer is refused)'),
    ('battle.ship_position_slot', 0x6dfe00, 16, READ,
     'SHIP vtable slot 0 (the battle.ship.position getter 0x611e90 calls [[ship]+0]): lea eax,[ecx+0x54]; ret',
     'J60 ship state: position x,y,z = SHIP + imm8 at +2 (0x54); install checks the vtable slot 0 is this function'),
    ('battle.ship_bearing_get', 0x611ef0, 32, READ,
     'battle.ship.bearing (table entry 0x1451538): fld [ship+0x50c]; fld [ship+0x524]; fpatan; * 32768/pi -> int16 binary angle (m02, m22 of the 3x3 at SHIP+0x504)',
     'J60 ship state: heading = atan2([ship+m02] (dword at +21), [ship+m22] (+27)), the engine getter formula'),
    ('battle.ship_fleet_list', 0x611d87, 27, READ,
     'battle.ship.name (table entry 0x1451520): mov ecx,[esi+4]; xor esi,esi; mov eax,[ecx+0x43c] (army); mov edx,[eax+0x108] (ship count); ...; mov eax,[eax+0x10c] (SHIP*[]); the allocator 0x5063a9 grows the same vector (army+0x104 capacity)',
     'J60 ship state: army SHIP+0x43c (+7), ship count +0x108 (+13) and list +0x10c (+23): the fleet index check'),
    ('battle.ship_sail_get', 0x6d8be0, 16, READ,
     'SHIP sail setting (thiscall; callers 0x60d8b3 the UI sail buttons, 0x5d03d6): movss xmm0,[ecx+0x1b88]; 0x6e05f0 maps the level to 8 full (>0.5), 4 half (>0.25), 2 battle (>0), 1 stationary',
     'J60 ship state: the live sail level float at SHIP + dword at +4 (0x1b88)'),
    ('battle.ship_orderable', 0x6d01e0, 25, READ,
     'SHIP check used by Selection AddShip 0x69ffb0: cmp byte [ecx+0x20dd],0; jne; cmp byte [ecx+0x20de],0; jne; cmp [ecx+0x1c58],2; je; then routing 0x6d03b0(ship+0x1ef4)',
     'J60 ship state: the two blocking flags (+2, +11) and the state dword (+20) the engine refuses a ship on'),
    ('battle.ship_surrendered_get', 0x61210a, 12, READ,
     'battle.ship.is_surrendered (table entry 0x1451568): mov ecx,[esi+4]; cmp dword [ecx+0x1f00],4; sete cl',
     'J60 ship state: surrendered = [ship + dword at +5] == imm8 at +9'),
    ('battle.selection_add_ship', 0x69ffb0, 32, CALL,
     'Selection AddShip (thiscall, SHIP*; ret 4): the ship check 0x6d01e0, then pushes into the vector at sel+0x34 (lea ecx,[edi+0x34] at +28); called by the controller selection 0x6469f5 and the UI rebuild 0x5f0b21/0x5f0cd5',
     'J60 ship orders: add one ship to our own selection; the ship vector offset (imm8 at +30)'),
    ('battle.ship_move_ctor', 0x599510, 32, CALL,
     'ship move command ctor (thiscall: Selection*, loc[5]*, int sail, int mode, bool queue; ret 0x14; vtable 0x132b648 at +0x11, selection vtable at +0x18, both relocated): loc -> +0x48..+0x58, sail +0x60, mode +0x64, queue +0x68; callers: script ship goto_location 0x6455d1, the UI ship move handler 0x5df50d, 0x5e59fe',
     'J60 ship orders: build the move command'),
    ('battle.ship_move_push', 0x58db40, 16, CALL,
     'command queue push for the ship move type (thiscall on [battle+0x28048], Command*; returns al): type helper 0x58dfb0 ([0x14a6268]); callers 0x6455ec (script), 0x5df523 (UI)',
     'J60 ship orders: push the move command'),
    ('battle.ship_location', 0x7fd730, 16, CALL,
     'ship target location (thiscall, this unused: loc[5] out, float xz[2] in; ret 8): builds (x, 0, z) and the location ctor 0x7ead50 (no terrain projection: sea level); the script ship goto calls it before the move ctor',
     'J60 ship orders: the target location the engine builds for (x, z)'),
    ('battle.order_rotate_ctor', 0x599810, 32, CALL,
     'rotate command ctor (thiscall: Selection*, int16 angle, bool flag, bool queue; ret 0x10; vtable 0x132b650): angle word +0x48, flag +0x4a, queue +0x4b; callers: script ship rotate 0x645cd1/0x645e11, the dispatcher codes 0..3 0x5dded0/0x5ddf2e',
     'J60 ship orders: build the facing command'),
    ('battle.order_rotate_push', 0x58dc60, 16, CALL,
     'command queue push for the rotate type (type helper 0x58dff0, [0x14a6110]); callers 0x5dded8, 0x5ddf36 (dispatcher)',
     'J60 ship orders: push the facing command'),
    ('battle.order_halt_ctor', 0x599140, 32, CALL,
     'halt command ctor (thiscall: Selection*; ret 4; vtable 0x132b678): the dispatcher code 7 (0x5ddf5d) and the script ship halt 0x6149d6 build it',
     'J60 ship orders: build the halt command'),
    ('battle.order_halt_push', 0x58dae0, 16, CALL,
     'command queue push for the halt type (type helper 0x58df90, [0x14a5f98]); caller 0x5ddf65 (dispatcher code 7)',
     'J60 ship orders: push the halt command'),
    ('battle.ship_wind_chain', 0x6f6f6f, 26, READ,
     'ship tick 0x6f6xxx before the wind read: mov eax,[ebx+0x1e0]; ...; mov ecx,[eax+8]; ...; mov ecx,[ecx+0xd8] (the wind); call 0x611460(out, ship pos)',
     'J60 ship state: wind object W = [[[ship + dword at +2] + imm8 at +15] + dword at +22]'),
    ('battle.wind_vector_get', 0x611460, 32, READ,
     'wind at a point (thiscall on W: out xz, pos): copies the prevailing wind [W+0x48], [W+0x4c], then adds the local gust list [W+0x20]/[W+0x24]',
     'J60 ship state: the prevailing wind x (imm8 at +19), z (+27)'),
    ('battle.ship_wind_angle', 0x6f7005, 15, READ,
     'ship tick: mov eax,[esp+0x1c]; sub eax,[esp+0x18]; mov word [ebx+0x5a8],ax (wind direction minus heading, int16); BattleShipSailingIntoWind fires when |angle| > 30037 (165 degrees, 0x6f7014)',
     'J60 ship state: the wind-relative angle int16 at SHIP + dword at +11'),
]
for sid, va, n, hook, desc, purpose in ROWS:
    b = im.bytes_at(va, n)
    rel = sorted(r - va for r in R if va <= r < va + n)
    pat, i = b'', 0
    while i < n:
        if i in rel:
            pat += b'....'; i += 4
        else:
            pat += re.escape(b[i:i + 1]); i += 1
    cnt = len(re.findall(pat, im.img, re.S))
    if cnt != 1:
        sys.stderr.write('NOT UNIQUE %s %d\n' % (sid, cnt))
    row = {'id': sid, 'description': desc + ('; relocated dwords at +' + ', +'.join(str(x) for x in rel) if rel else '') + '; ' + NOTE,
           'purpose': purpose, 'exe': EXE, 'rva': hex(va - 4 - im.base), 'anchor_bytes': im.bytes_at(va - 4, 4).hex(' '),
           'stock_bytes': b.hex(' '), 'kind': 'hook', 'hook': hook, 'config_key': 'dev.orders'}
    print(json.dumps(row))
