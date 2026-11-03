#!/usr/bin/env python3
"""J24 run helper: the map-size ladder as one Markdown table from perf_baseline.py summaries (medians), with deltas against the control.

usage: python3 harness/runs/20261103_j24pc/ladder_table.py <control run> <run> [<run> ...]   (runs are harness/runs/<id>; each needs summary.json)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M = ('p50_ms', 'p99_ms', 'load_s', 'va_used_mb', 'va_peak_mb', 'commit_mb', 'vram_mb')


def load(run):
    p = ROOT / 'harness' / 'runs' / run / 'summary.json'
    return json.loads(p.read_text(encoding='utf-8'))['cells']


ctl = load(sys.argv[1])
print('| run | cell | ' + ' | '.join(M) + ' |')
print('|---|---|' + '---|' * len(M))
for run in sys.argv[1:]:
    cells = load(run)
    for key in sorted(cells):
        c = cells[key]
        vals = []
        for m in M:
            v = (c.get(m) or {}).get('median')
            b = ((ctl.get(key) or {}).get(m) or {}).get('median')
            if v is None:
                vals.append('-')
            elif run == sys.argv[1] or b is None:
                vals.append(f'{v:g}')
            else:
                vals.append(f'{v:g} ({v - b:+.2f})' if m in ('p50_ms', 'p99_ms', 'load_s') else f'{v:g} ({v - b:+.0f})')
        print(f"| {run.replace('20261103_j24ladder_', '')} | {key.replace('dxvk|', '')} | " + ' | '.join(vals) + ' |')
