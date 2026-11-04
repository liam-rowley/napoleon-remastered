"""J28 run helper: the Markdown table of every ctl.py order result in raw/ (one row per unit: tag, scene, unit, status, errors, settle).

usage: python3 harness/runs/20261102_j28pc/table.py   (prints the table README.md carries)
"""
import json
from pathlib import Path

RAW = Path(__file__).resolve().parent / 'raw'
SCENE = {'c': 'land_small', 'd': 'land_small', 'e': 'land_small', 'f': 'land_small', 'g': 'siege_small', 'h': 'land_small (deploying)', 'i': 'land_small'}
print('| run | scene | unit | action | status | front m | facing deg | width m | centre lateral m | centre ahead m | moved | settle s |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|')
for p in sorted(RAW.glob('[c-i][0-9]*.json')):
    if p.stem.endswith(('_list', '_scene', '_shot')) or 'scene' in p.stem or 'list' in p.stem:
        continue
    d = json.loads(p.read_text(encoding='utf-8'))
    units = d.get('units') if isinstance(d.get('units'), list) and d.get('units') and 'check' in d['units'][0] else [d]
    for u in units:
        f = (u.get('check') or {}).get('fields', {})
        def e(k):
            v = f.get(k)
            return '' if not v else f"{v.get('err', v.get('got'))}{'' if v.get('within', True) else ' **out**'}"
        st = u.get('settle') or {}
        act = d.get('action') or (u.get('pushed', '')[:0] + ('move' if 'move' in str(d.get('evidence', {})) else ''))
        if 'shape_change_m' in f:
            act, e_front = d.get('action'), f"shape {f['shape_change_m']['got']}"
        elif 'moving' in f and len(f) == 1:
            act, e_front = d.get('action'), f"moving {f['moving']['got']}"
        else:
            e_front = e('position_m')
        reason = ((u.get('reason') if u is not d else d.get('reason')) or '')[:70].replace('|', '/')
        print(f"| {p.stem} | {SCENE.get(p.stem[0], '?')} | {u.get('unit', '')} | {act or ''} | {u.get('status', d['status'])}{': ' + reason if reason else ''} | {e_front} | "
              f"{e('facing_deg')} | {e('width_m')} | {e('centre_lateral_m')} | {e('centre_ahead_m')} | {st.get('moved', '')} | {st.get('waited_s', '')} |")
