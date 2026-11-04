import sys, json, struct
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(sys.argv[1])
EXE = 'sha1:9aebcd2172f2878d781b079f7feb45b0e12e0250'
rel = set()
for r in im.relocs():
    rel.update(range(r, r+4))
f2h = lambda f: ' '.join(f'{b:02x}' for b in struct.pack('<f', f))
i2h = lambda v, n=4: ' '.join(f'{b:02x}' for b in v.to_bytes(n, 'little'))
hx = lambda b: ' '.join(f'{x:02x}' for x in b)
# (id, key, value VA, anchor len, stock hex expected, patch hex, description, purpose)
S = []
def site(id_, key, val_va, alen, stock, patch, desc, purpose):
    a0 = val_va - alen
    anchor = im.bytes_at(a0, alen); st = im.bytes_at(val_va, len(stock.split()))
    assert hx(st) == stock, (id_, hx(st), stock)
    bad = [x for x in range(a0, val_va + len(st)) if x in rel]
    assert not bad, (id_, 'reloc in anchor/stock', [hex(b) for b in bad])
    S.append({'id': id_, 'description': desc, 'purpose': purpose, 'exe': EXE, 'rva': hex(a0 - im.base),
              'anchor_bytes': hx(anchor), 'stock_bytes': stock, 'kind': 'patch', 'patch_bytes': patch, 'config_key': key})
K = 'gfx.shadow_proof'
site('shadow.map_size_q34', K, 0x1186986, 3, i2h(0x800), i2h(0x1000),
     'shadow map setup 0x11868f0 (jump table on gfx_shadow_quality, options field +0x69d18): mov ebx, 0x800 shared by quality 3 and 4 (quality 4 adds mov dl,1 = R32F); ebx is the colour map and depth buffer size',
     'shadow map edge at gfx_shadow_quality 3 and 4: imm32 2048; J9 proof value 4096 (J24 owns the value)')
site('shadow.far_cap_q3', K, 0x1186976, 3, f2h(500.0), f2h(1000.0),
     'shadow map setup 0x11868f0, quality 3 case: mov dword [esi+0x7c], 500.0 (q1 100, q2 250, q4 1000); the per-quality cap on the fitted shadow far distance (J8 measured farz 72/139/250/473 under it)',
     'shadow distance cap at gfx_shadow_quality 3: float 500 m; J9 proof value 1000 m (J24 owns the value)')
K = 'gfx.sprite_page_proof'
for q, va, stock in ((0, 0x12400d4, 512.0), (1, 0x1240113, 1024.0), (2, 0x1240100, 1024.0), (3, 0x12400e5, 1024.0)):
    site(f'sprite.page_q{q}', K, va, 3, f2h(stock), f2h(2048.0),
         f'unit imposter (sprite) page setup 0x1240010: switch on options field +0x69d00 (setter index 1); case {q if q else "0 and >3"}: mov dword [esi+0x5c], {stock:g} (the page edge, also squared into the page cost; a budget loop steps the case down while the cost is over budget)',
         f'imposter page edge for switch case {q if q else "0/other"}: float {stock:g}; J9 proof value 2048 on every case (J27 owns the value)')
K = 'gfx.unit_lod_proof'
site('unit_lod.override_default', K, 0x415431, 4, '00', '01',
     'CRT static initialiser of the bool tweaker ENTITY_LOD_OVERRIDE ("use explicit lod distances from tweakers", object 0x150d190, ctor 0x4548c0): mov byte [esp+0x1b], <default>',
     'unit LOD distances from the tweakers instead of the gfx_unit_quality table in 0x756e80: J9 proof turns the override on')
for name, va, stock, new in (('imposter_distance', 0x4155a1, 100.0, 1000.0), ('large_imposter_distance', 0x4156c1, 200.0, 1000.0)):
    site(f'unit_lod.{name}_default', K, va, 4, f2h(stock), f2h(new),
         f'CRT static initialiser of the float tweaker {name.upper()} (ctor 0x454730): mov dword [esp+0x18], <default>; read by the unit LOD function 0x756e80 only when ENTITY_LOD_OVERRIDE is on',
         f'{name.upper()} default: float {stock:g} m; J9 proof value {new:g} (J27 owns the value)')
K = 'gfx.ship_lod_proof'
for name, va, stock, new in (('mast_lod_distance', 0x415711, 250.0, 1000.0), ('rope_distance', 0x4159c1, 200.0, 1000.0),
                             ('rope_distance_fadeout', 0x415a11, 150.0, 900.0), ('knot_distance', 0x415631, 50.0, 400.0)):
    site(f'ship_lod.{name}_default', K, va, 4, f2h(stock), f2h(new),
         f'CRT static initialiser of the float tweaker {name.upper()} (ctor 0x454730): mov dword [esp+0x18], <default>; read unconditionally by the ship draw 0x782210 (distance squared against the camera distance squared)',
         f'{name.upper()} default: float {stock:g} m; J9 proof value {new:g} (J27 owns the value)')
K = 'gfx.grass_proof'
site('grass.grid_q3', K, 0x1419ad8, 12, i2h(5), i2h(9),
     'grass quality table .rdata 0x1419ab4, rows of (grid N, cell size, density) per gfx_grass_quality (options field +0x69d20), read by 0x11d0c90; quality 3 row (5, 16, 28): range N x 16 m',
     'grass grid N at gfx_grass_quality 3: int 5 (80 m); J9 proof value 9 (144 m) (J27 owns the value)')
site('grass.grid_q4', K, 0x1419ae4, 8, i2h(5), i2h(9),
     'grass quality table .rdata 0x1419ab4, quality 4 row (5, 16, 32); anchor = the quality 3 row cell size and density (8 bytes: the row before is grass.grid_q3)',
     'grass grid N at gfx_grass_quality 4: int 5 (80 m); J9 proof value 9 (144 m) (J27 owns the value)')
K = 'gfx.tree_lod_proof'
for q, va, stock in (('other', 0x11e14c6, 50.0), ('q1', 0x11e14fc, 100.0), ('q2', 0x11e14f2, 150.0), ('q3', 0x11e14dc, 200.0)):
    site(f'trees.far_{q}', K, va, 4, f2h(stock), f2h(600.0),
         f'tree display init 0x11e1220 (from 0x11e1417): after reading the tweakers it switches on options field +0x69d1c (gfx_tree_quality) and overwrites tweaker tree_far_distance (object 0x1839330) through the setter 0x5aa4a0; case {q}: mov dword [esp+0x14|0x18], {stock:g}',
         f'tree far distance for gfx_tree_quality case {q} (1/2/3; other = 0 and 4): float {stock:g} m; the tweaker default 200 is overwritten here; J9 proof value 600 (J27 owns the value)')
site('shadow.light_sweep', 'gfx.shadow_sweep_proof', 0x11276ac, 6, f2h(-75.0), f2h(-400.0),
     'shadow renderer constructor 0x1127580 (Empire 0x103f160, fields +0x14): mov dword [edi+0x9c], -75.0, the light sweep (Empire [r+0x88]: the caster volume reaches -sweep metres towards the sun); J6 candidate RVA 0xd27696 is this window',
     'shadow light sweep: float -75 m; J9 proof value -400 (the Empire value; J24 owns the value)')
ONLY = set(sys.argv[2:])
for s in S:
    if not ONLY or s['id'] in ONLY: print(json.dumps(s))
