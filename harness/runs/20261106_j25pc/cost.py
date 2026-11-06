#!/usr/bin/env python3
"""J25 cost table: prototype minus its same-sitting control, per block, then the median over the blocks with the spread, against the cascades budget.

Run evidence (as J24's helpers), not a registered tool. usage: python3 harness/runs/20261106_j25pc/cost.py
Reads harness/runs/20261106_j25cost_<size>_<arm><block>/summary.json. Blocks pair in time order: ctl1 with pro1, ctl2 with pro2. Budget: perf/budgets.md
cascades row (PROPOSED): p50 1.5 ms, p99 2.0 ms, VA 50 MB, VRAM 768 MB. A cell breaches on the median; the spread says how far to believe it. Writes cost.md.
"""
import json
import statistics
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1]
BUDGET = {'p50_ms': 1.5, 'p99_ms': 2.0, 'va_used_mb': 50, 'vram_mb': 768}
EXTRA = ('va_peak_mb', 'commit_mb', 'load_s')


def load(size, arm):
    return json.loads((RUNS / f'20261106_j25cost_{size}_{arm}' / 'summary.json').read_text(encoding='utf-8'))['cells']


rows, breaches = [], []
for size in ('1080', '4k'):
    ctl = [load(size, 'ctl1'), load(size, 'ctl2')]
    pro = [load(size, 'pro1'), load(size, 'pro2')]
    for cell in sorted(ctl[0]):
        r = {'cell': cell.replace('dxvk|', '')}
        for m in list(BUDGET) + list(EXTRA):
            d = [p[cell][m]['median'] - c[cell][m]['median'] for c, p in zip(ctl, pro)]
            r[m] = (round(statistics.median(d), 2), round(max(d) - min(d), 2))
            if m in BUDGET and r[m][0] > BUDGET[m]:
                breaches.append(f"{r['cell']} {m} +{r[m][0]} over {BUDGET[m]} (spread {r[m][1]})")
        r['ctl_p50'] = round(statistics.median(c[cell]['p50_ms']['median'] for c in ctl), 2)
        r['ctl_p99'] = round(statistics.median(c[cell]['p99_ms']['median'] for c in ctl), 2)
        r['ctl_spread_p99'] = round(abs(ctl[0][cell]['p99_ms']['median'] - ctl[1][cell]['p99_ms']['median']), 2)
        r['noisy'] = [i for i, s in enumerate(ctl + pro) if s[cell].get('noisy')]
        rows.append(r)
hdr = '| cell | control p50 / p99 | p50 delta (spread) | p99 delta (spread) | control-to-control p99 | VA used | VA peak | commit | VRAM | load s |'
lines = ['Median over 2 blocks of prototype minus same-sitting control; spread = the two blocks\' difference. Budget (PROPOSED): p50 1.5, p99 2.0, VA 50, VRAM 768.', '', hdr, '|' + '---|' * 10]
f = lambda t: f'{t[0]:+} ({t[1]})'
for r in rows:
    lines.append(f"| {r['cell']} | {r['ctl_p50']} / {r['ctl_p99']} | {f(r['p50_ms'])} | {f(r['p99_ms'])} | {r['ctl_spread_p99']} | {f(r['va_used_mb'])} | {f(r['va_peak_mb'])} | {f(r['commit_mb'])} | {f(r['vram_mb'])} | {f(r['load_s'])} |")
lines += ['', 'Breaches of the median: ' + ('; '.join(breaches) if breaches else 'none')]
text = '\n'.join(lines) + '\n'
(Path(__file__).parent / 'cost.md').write_text(text, encoding='utf-8', newline='\n')
print(text)
