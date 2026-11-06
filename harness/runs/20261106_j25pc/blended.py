#!/usr/bin/env python3
"""J25 question 6: every alpha-blended draw of the main colour pass, by shader: a soft dark decal under a unit has to be one of these.

Run evidence (as J24's helpers), not a registered tool. usage: python3 harness/runs/20261106_j25pc/blended.py <frame.txt> [<frame.txt> ...]
A state block's read-back (the RS lines after SBAPPLY) is followed as any other line, so the state is the one the draw ran with.
"""
import collections
import json
import sys
from pathlib import Path

CAT = json.loads((Path(__file__).resolve().parents[3] / 'discovery' / 'napoleon' / 'shader_catalog.json').read_text(encoding='utf-8'))['shaders']


def label(h):
    s = CAT.get(h)
    if not s:
        return f'{h} NOT IN CATALOGUE'
    fx = (s.get('fx') or [{}])[0]
    return f"{h} {s['model']} {fx.get('fx')} {fx.get('technique')}"


for path in sys.argv[1:]:
    rs, ps, frame, passes, cur = {}, None, 0, [], None
    for line in open(path, encoding='latin1'):
        p = line.split()
        if not p:
            continue
        t = p[0]
        if t == 'FRAME':
            frame = int(p[1])
            if frame > 1:
                break
        elif t == 'RS':
            rs[int(p[1])] = p[2]
        elif t == 'PS':
            ps = p[1]
        elif t == 'RT' and p[1] == '0' and frame == 1:
            cur = []
            passes.append(cur)
        elif t in ('DIP', 'DP', 'DPUP', 'DIPUP') and frame == 1 and cur is not None:
            cur.append((ps, rs.get(27), rs.get(19), rs.get(20), rs.get(14)))
    main = max(passes, key=len)
    blended = collections.Counter((d[0], d[2], d[3], d[4]) for d in main if d[1] not in ('0', None))
    print(f'== {Path(path).parent.name}: {len(main)} draws, {sum(blended.values())} blended (src, dst, zwrite)')
    for k, v in blended.most_common():
        print(f'  {v:4} {label(k[0])[:78]} src {k[1]} dst {k[2]} zwrite {k[3]}')
