"""J28 run helper: one line per ctl.py order result (status, reason, errors per checked field, settle time, the before/after centre).

usage: python3 harness/runs/20261102_j28pc/sum.py <result.json>...
"""
import json
import sys

for p in sys.argv[1:]:
    try:
        d = json.load(open(p, encoding='utf-8'))
    except ValueError:
        print(p, 'not json:', open(p, encoding='utf-8').read()[:300])
        continue
    f = (d.get('check') or {}).get('fields', {})
    errs = ' '.join(f"{k}={v['got']}(err {v['err']}{'' if v['within'] else ' OUT'})" for k, v in f.items())
    b, g, st = d.get('before') or {}, d.get('got') or {}, d.get('settle') or {}
    print(f"{d['status']} {d.get('reason', '')} | {errs} | settle {st.get('waited_s')} s moved={st.get('moved')} | centre "
          f"({b.get('x')}, {b.get('z')}) -> ({g.get('x')}, {g.get('z')}) facing {b.get('facing')} -> {g.get('facing')}")
