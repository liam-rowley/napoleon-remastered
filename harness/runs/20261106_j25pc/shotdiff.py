#!/usr/bin/env python3
"""J25 shots against their controls with the acceptance metric (core/harness/acceptance.py mean_abs_diff), and control against control for the noise floor.

Run evidence (as J24's helpers), not a registered tool. usage: python3 harness/runs/20261106_j25pc/shotdiff.py   writes shotdiff.md
The acceptance threshold for a land or siege shot is 4.0. Whole-shot difference: unit formations differ a little launch to launch at the low poses.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[2] / 'core' / 'harness'))
from acceptance import mean_abs_diff  # noqa: E402

POSES = ['l40_deploy', 'l40_turned', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 's1']


def shot(tag, pose):
    p = HERE / 'raw' / tag / f'j25_{tag}_{pose}.jpg'
    return p.read_bytes() if p.exists() else None


def d(a, b, pose):
    x, y = shot(a, pose), shot(b, pose)
    return round(mean_abs_diff(x, y), 2) if x and y else None


rows = ['| pose | 8192: control vs control (b_idle, a_main) | 8192: cascade vs control (d_on, b_idle) | 8192: stale receivers vs control (c_on, b_idle) | 2048: cascade vs control (e_on2k, e_ctl2k) |', '|---|---|---|---|---|']
alias = {'l40_deploy': 'l40_deploy', 'l40_turned': 'l40_turned', 'p5': 'ls_deploy', 's1': 's1'}
for p in POSES:
    x = shot('b_idle', p)
    y = shot('a_main', alias[p]) if p in alias else None
    cc = round(mean_abs_diff(x, y), 2) if x and y else None
    rows.append(f"| {p} | {cc} | {d('d_on', 'b_idle', p)} | {d('c_on', 'b_idle', p)} | {d('e_on2k', 'e_ctl2k', p)} |")
text = '\n'.join(rows) + '\n'
(HERE / 'shotdiff.md').write_text(text, encoding='utf-8', newline='\n')
print(text)
