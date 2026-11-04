#!/usr/bin/env python3
"""J24 run helper: one-screen summary of a fit.sh launch folder (raw/<tag>): keys, site lines, scene loads, cam readbacks, captures, perf.

usage: python3 harness/runs/20261103_j24pc/summ.py <tag> [<tag> ...]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def j(p):
    try:
        return json.loads(p.read_text(encoding='utf-8', errors='replace'))
    except Exception as e:
        return {'status': f'unreadable ({e.__class__.__name__})'}


for tag in sys.argv[1:]:
    d = HERE / 'raw' / tag
    print(f'== {tag}')
    if (d / 'keys.txt').exists():
        print('  ini:', (d / 'keys.txt').read_text().strip())
    log = (d / 'proxy.log').read_text(encoding='utf-8', errors='replace') if (d / 'proxy.log').exists() else ''
    sites = [l for l in log.splitlines() if 'shadow.' in l and 'site' in l.lower()]
    for l in sites:
        print('  ', l[l.find('shadow.'):][:150])
    for l in log.splitlines():
        if re.search(r'patch_engine: (apply|plan|wrote|nothing)|build ', l):
            print('  ', l[-170:])
            break
    for s in sorted(d.glob('scene_*.json')):
        r = j(s)
        print(f"  {s.stem}: {r.get('status')} load {r.get('load_s')} {r.get('reason', '')[:120]}")
    bad = []
    for c in sorted(d.glob('*_cam.json')):
        r = j(c)
        chk = r.get('check', {})
        if r.get('status') != 'ok' or chk.get('within') is False or chk.get('ok') is False:
            bad.append(f"{c.stem}: {r.get('status')} {r.get('reason', '')[:100]} got {r.get('got')}")
    print('  cams:', len(list(d.glob('*_cam.json'))), 'not ok:', bad or 'none')
    caps = sorted(d.glob('*_capture.txt'))
    capbad = [c.stem for c in caps if '"ok"' not in c.read_text(errors='replace') and 'ok' not in c.read_text(errors='replace')[-400:]]
    print('  captures:', len(caps), 'suspect:', capbad or 'none')
    if (d / 'perf_land.json').exists():
        r = j(d / 'perf_land.json')
        print('  perf land p6 pose:', {k: r.get(k) for k in ('status', 'p50_ms', 'p99_ms', 'build', 'va_used_mb')})
    print('  shots:', len(list(d.glob('j24_*.jpg'))))
