#!/usr/bin/env python3
"""J25 go criterion 2: where the tint changes in a shot against where the captured matrices put the cascade's edge.

Run evidence (as J24's helpers), not a registered tool. usage: python3 harness/runs/20261106_j25pc/pick_check.py <frame.txt> <shot.jpg> <unused> <row> [row ...]
Each pixel's ray meets the plane y = ground, the cascade's receiver rows (c216, c217 from the capture) give u, v, and the pick is saturate(min(u, 1-u, v, 1-v) / blend),
as the shader has it. Observed: the columns on each row where the tint's brightness falls halfway. The terrain height under the footprint is not in the capture, so one
ground height is fitted to every edge at once: the footprint's diagonal sides answer to it differently from row to row, so a wrong matrix cannot fit them all. The
terrain is not a plane, and this is in screen pixels: it cannot reach one shadow texel (5.6 cm at 2048), a screen pixel covers several at this distance.
"""
import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('sc', ROOT / 'core' / 'discovery' / 'shader_catalog.py')
sc = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'core' / 'discovery'))
spec.loader.exec_module(sc)
CAT = json.loads((ROOT / 'discovery' / 'napoleon' / 'shader_catalog.json').read_text(encoding='utf-8'))['shaders']
VS = '3d96bea8aca31bbe'   # grid.fx grid_far_sm3, the battle terrain's vertex shader: stock in every arm
reg = next(c['index'] for c in CAT[VS]['ctab']['constants'] if c['name'] == 'view_projection')

vc, pc, vs, frame, got, surf, rt = {}, {}, None, 0, None, {}, None
for line in open(sys.argv[1], encoding='latin1'):
    p = line.split()
    if not p:
        continue
    if p[0] == 'FRAME':
        frame = int(p[1])
    elif p[0] == 'VS':
        vs = p[1]
    elif p[0] == 'SURF':
        surf[p[1]] = p[2]
    elif p[0] == 'RT' and p[1] == '0':
        rt = p[2]
    elif p[0] in ('VC', 'PC'):
        d = vc if p[0] == 'VC' else pc
        s, n = int(p[1]), int(p[2])
        for i in range(n):
            d[s + i] = [float(x) for x in p[3 + 4 * i:7 + 4 * i]]
    elif p[0] in ('DIP', 'DP') and vs == VS and frame == 1 and surf.get(rt) == '1920':   # the main pass: the 960 reflection pass draws the terrain first, with a mirrored camera
        got = [vc[reg + i] for i in range(4)]
        break
inv = sc._inv4(got)
rows, blend, ground = (pc[216], pc[217]), pc[220][2], float(sys.argv[3])
im = Image.open(sys.argv[2]).convert('L')
W, H = im.size


def world(x, y):
    nx, ny = 2 * (x + 0.5) / W - 1, 1 - 2 * (y + 0.5) / H
    def un(z):
        q = [sum(inv[i][k] * v for k, v in enumerate((nx, ny, z, 1.0))) for i in range(4)]
        return [q[i] / q[3] for i in range(3)]
    a, b = un(0.1), un(0.9)
    if abs(b[1] - a[1]) < 1e-9:
        return None
    t = (ground - a[1]) / (b[1] - a[1])
    return None if t < 0 else [a[i] + t * (b[i] - a[i]) for i in range(3)]


def pick(w):
    u = sum(rows[0][i] * w[i] for i in range(3)) + rows[0][3]
    v = sum(rows[1][i] * w[i] for i in range(3)) + rows[1][3]
    return max(0.0, min(1.0, min(u, 1 - u, v, 1 - v) / blend))


def edges_at(row, g):
    """Predicted left and right columns of pick = 0.5 on `row` with the ground at y = g, or None."""
    global ground
    ground = g
    inside = [x for x in range(0, W, 2) if (w := world(x, row)) and pick(w) >= 0.5]
    return (inside[0], inside[-1]) if inside else None


def observed(row):
    """Left and right columns where a row's smoothed brightness falls to halfway between the lit outside and the dark middle."""
    lum = [im.getpixel((x, row)) for x in range(W)]
    sm = [sum(lum[max(x - 8, 0):x + 9]) / len(lum[max(x - 8, 0):x + 9]) for x in range(W)]
    dark = sum(sm[W // 2 - 60:W // 2 + 60]) / 120
    left, right = sum(sm[10:50]) / 40, sum(sm[W - 50:W - 10]) / 40
    l = next((x for x in range(W) if sm[x] < (left + dark) / 2), None)
    r = next((x for x in range(W - 1, -1, -1) if sm[x] < (right + dark) / 2), None)
    return l, r


rws = [int(c) for c in sys.argv[4:]]
obs = {r: observed(r) for r in rws}
print(f'shot {W}x{H}, blend {blend}; observed edges (left, right) per row: {obs}')
best = None
for gi in range(100, 420):   # ground y from 10 to 42 m in 0.1 m steps
    g = gi / 10
    err, n = 0, 0
    for r in rws:
        e = edges_at(r, g)
        if not e or None in obs[r]:
            err = None
            break
        err += abs(e[0] - obs[r][0]) + abs(e[1] - obs[r][1])
        n += 2
    if err is not None and (best is None or err / n < best[0]):
        best = (err / n, g)
print(f'best single ground height {best[1] if best else None} m, mean edge error {round(best[0], 1) if best else None} px over {2 * len(rws)} edges' if best else 'no ground height fits')
if best:
    for r in rws:
        print(f'  row {r}: predicted {edges_at(r, best[1])} observed {obs[r]}')
