"""J28 run helper: print the ctl order arguments that move a listed unit `dist` metres along its own facing, keeping facing and width.

usage: python3 harness/runs/20261102_j28pc/step10.py <list.json> <unit id> <dist m> [turn deg]   -> "<id> move <x> <z> <facing> <width>"
"""
import json
import math
import sys

d = json.load(open(sys.argv[1], encoding='utf-8'))
u = next(x for x in d['units'] if x['id'] == int(sys.argv[2]))
dist = float(sys.argv[3])
turn = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
b = math.radians(u['facing'])
x, z = u.get('fx', u['x']) + dist * math.sin(b), u.get('fz', u['z']) + dist * math.cos(b)
print(f"{u['id']} move {x:.2f} {z:.2f} {(u['facing'] + turn) % 360:.2f} {u.get('width', 30):.2f}")
