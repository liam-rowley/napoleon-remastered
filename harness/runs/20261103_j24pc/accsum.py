#!/usr/bin/env python3
"""J24 run helper: per-pass result, build and the shot diffs against their thresholds for acceptance runs.

usage: python3 harness/runs/20261103_j24pc/accsum.py <run id> [<run id> ...]   (harness/runs/<id>/pass_*.json)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for run in sys.argv[1:]:
    for p in sorted((ROOT / 'harness' / 'runs' / run).glob('pass_*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        shots = []
        for s in (d.get('steps') or []):
            if isinstance(s, dict) and ('diff' in s or 'shot' in str(s.get('step', s.get('name', '')))):
                shots.append(f"{s.get('scenario', s.get('step', s.get('name')))}:{s.get('diff', s.get('mean_abs_diff'))}/{s.get('threshold')}")
        fails = [s for s in (d.get('steps') or []) if isinstance(s, dict) and s.get('ok') is False]
        print(run, p.stem, d.get('passed'), d.get('build_id'), 'fails:', [f.get('step', f.get('name')) for f in fails][:5])
        if shots:
            print('   ', ' '.join(shots))
        if isinstance(d.get('steps'), dict):
            st = d['steps']
            bad = [k for k, v in st.items() if isinstance(v, dict) and v.get('ok') is False]
            sh = [f"{k.split(':')[0]}={v.get('mean_abs_diff', v.get('diff'))}/{v.get('threshold')}" for k, v in st.items()
                  if k.endswith(':shot_match') and isinstance(v, dict)]
            print('    failed steps:', bad or 'none', '| shots:', ' '.join(sh))
