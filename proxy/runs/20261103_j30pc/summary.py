#!/usr/bin/env python3
"""Summarise this run folder: interaction checks, dump checks and perf cells from results.jsonl and checks/*.json.
usage: python3 proxy/runs/20261103_j30pc/summary.py [--detail]
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
detail = '--detail' in sys.argv
if '--recheck' in sys.argv:   # re-run tools/ui_hosttest.py check on every dump: <scene>_<height>_<percent>.png -> dp = height/1080 x percent/100
    import subprocess
    for png in sorted((HERE / 'dumps').glob('*.png')):
        parts = png.stem.split('_')
        h, pct = (int(parts[-2]), int(parts[-1])) if parts[-1].isdigit() and parts[-2].isdigit() else (int(parts[-1]), 100)
        subprocess.run([sys.executable, str(HERE.parents[2] / 'tools' / 'ui_hosttest.py'), 'check', str(png), '--dp', str(h / 1080 * pct / 100),
                        '--crops', str(HERE / 'crops'), '--json', str(HERE / 'checks' / f'{png.stem}.json')], capture_output=True)
rows = [json.loads(l) for l in (HERE / 'results.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
# the first cells run (18:28-18:37 UTC, before the VtableHook fix) hung in the battle: its lines are kept as a record, summarised apart
since = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--since=')), '2026-11-02T18:50:30Z')
rows = [r for r in rows if r['utc'] >= since]
print('== interaction')
for r in rows:
    if r['step'] == 'interaction':
        bad = [k for k, v in r['checks'].items() if not v]
        print(f"  {r['tag']:<22} {'ok' if r['ok'] else 'FAIL ' + ','.join(bad)}")
        if detail and bad:
            for k in ('wheel_list', 'hidden_click', 'shown_click', 'reloaded_click'):
                print('     ', k, r['steps'][k])
    elif r['step'] in ('warm_reset', 'scene') and r.get('status') not in ('ok', None):
        print(f"  {r['step']} {r.get('size')} {r.get('scene', '')}: {r.get('status')} {r.get('reason')}")
print('== dumps')
for f in sorted((HERE / 'checks').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    t = c['checks']['text_height']['lines']
    print(f"  {f.stem:<22} {'ok' if c['ok'] else 'FAIL'} dp {c['dp']:.4f} " + ' '.join(f"{k}={'ok' if v['ok'] else 'FAIL'}" for k, v in c['checks'].items())
          + '  H ink/expected: ' + ' '.join(f"{l['ink_rows']}/{l['expected_cap_px']}" for l in t))
print('== perf (frame ms p50 / p99, mean of runs; ui update+render p50 ms)')
cells = {}
for r in rows:
    if r['step'] == 'perf' and r.get('frame_ms'):
        k = (r['backend'], r['size'], r['scene'], r['setting'])
        cells.setdefault(k, []).append(r)
for k, rs in sorted(cells.items()):
    p50 = statistics.mean(x['frame_ms']['p50'] for x in rs)
    p99 = statistics.mean(x['frame_ms']['p99'] for x in rs)
    ui = [x['ui_cost'] for x in rs if x.get('ui_cost')]
    u = statistics.mean(c['update']['p50'] + c['render']['p50'] for c in ui) if ui else None
    h = statistics.mean(c['hook_all_presents']['p50'] for c in ui) if ui else None
    mem = rs[-1].get('mem') or {}
    print(f"  {k[0]:<6} {k[1]:<10} {k[2]:<9} {k[3]:<5} n={len(rs)} frame p50 {p50:6.2f} p99 {p99:6.2f}"
          + (f"  ui upd+rnd p50 {u:.3f} hook p50 {h:.3f}" if u is not None else '') + f"  va {mem.get('va_used_mb')} commit {mem.get('commit_mb')}")
