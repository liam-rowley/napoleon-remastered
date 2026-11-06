#!/usr/bin/env python3
"""J25 question 6: what the main pass's sprite draws are. Per pixel shader: the state each draw runs with (blend, z, textures, vertex counts).

Run evidence (as J24's helpers), not a registered tool. usage: python3 harness/runs/20261106_j25pc/sprites.py <frame.txt> <ps hash> [<ps hash> ...]
Frame 1, the 1920-wide main colour pass only (the pass that holds the most draws). Render states by number: 7 ZENABLE, 14 ZWRITEENABLE,
19 SRCBLEND, 20 DESTBLEND, 27 ALPHABLENDENABLE, 15 ALPHATESTENABLE, 22 CULLMODE, 171 BLENDOP.
"""
import collections
import sys

want = set(sys.argv[2:])
rs, tex, texdesc, vc = {}, {}, {}, {}
ps = vs = None
frame, passes, cur = 0, [], None
for line in open(sys.argv[1], encoding='latin1'):
    p = line.split()
    if not p:
        continue
    t = p[0]
    if t == 'FRAME':
        frame = int(p[1])
        if frame > 1:
            break
    elif t == 'TEX':
        texdesc[p[1]] = p[2:]
    elif t == 'RS':
        rs[int(p[1])] = p[2]
    elif t == 'T':
        tex[int(p[1])] = p[2]
    elif t == 'PS':
        ps = p[1]
    elif t == 'VS':
        vs = p[1]
    elif t == 'RT' and p[1] == '0' and frame == 1:
        cur = []
        passes.append(cur)
    elif t in ('DIP', 'DP', 'DPUP', 'DIPUP') and frame == 1 and cur is not None:
        cur.append({'ps': ps, 'vs': vs, 'kind': t, 'args': p[1:], 'rs': {k: rs.get(k) for k in (7, 14, 15, 19, 20, 22, 27, 171)},
                    'tex': {s: texdesc.get(x, ['?'])[:6] for s, x in tex.items() if x != '0' and s < 8}, 'texid': {s: x for s, x in tex.items() if x != '0' and s < 8}})
main = max(passes, key=len)
print('main pass draws', len(main))
order = [d['ps'] for d in main]
for h in want:
    ds = [d for d in main if d['ps'] == h]
    print(f'== {h}: {len(ds)} draws, positions {[i for i, x in enumerate(order) if x == h][:4]}.. of {len(order)}; vs {collections.Counter(d["vs"] for d in ds).most_common(3)}')
    print('   kinds', collections.Counter(d['kind'] for d in ds).most_common(3))
    print('   blend (z, zwrite, alphatest, src, dst, cull, alphablend, op)', collections.Counter(tuple(d['rs'].values()) for d in ds).most_common(3))
    print('   args sample', [d['args'] for d in ds[:3]])
    print('   textures (type levels w h d fmt) by stage:')
    seen = collections.Counter()
    for d in ds:
        for s, x in d['tex'].items():
            seen[(s, tuple(x))] += 1
    for k, v in seen.most_common(10):
        print('    ', v, k)
    print('   distinct stage-0 textures', len({d['texid'].get(0) for d in ds}))
