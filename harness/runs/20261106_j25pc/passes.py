#!/usr/bin/env python3
"""J25 questions 1, 2 and 6 from raw frame.txt: the shadow pass's shape, casters, receivers, and every other draw of the main pass.

Run evidence (as J24's helpers), not a registered tool. usage: python3 harness/runs/20261106_j25pc/passes.py <captures dir> <name> [<name> ...] > out.json
Frame 1 of each capture only. Register tracking is by the VC/PC lines, so a matrix is the last upload before the draw.
"""
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAT = json.loads((ROOT / 'discovery' / 'napoleon' / 'shader_catalog.json').read_text(encoding='utf-8'))['shaders']
SHADOW_FMT = {'111', '114'}
DRAWS = {'DP', 'DIP', 'DPUP', 'DIPUP'}


def names(h):
    return {c['name']: c for c in (CAT.get(h, {}).get('ctab') or {}).get('constants', [])}


def label(h):
    s = CAT.get(h)
    if not s:
        return f'{h} NOT IN CATALOGUE'
    fx = (s.get('fx') or [{}])[0]
    return f"{h} {s['model']} {fx.get('fx')} {fx.get('technique')}"


def analyse(path):
    raw = Path(path).read_bytes()
    surf, passes, cur = {}, [], None
    vs = ps = None
    vc, pc, tex = {}, {}, {}
    frame = 0
    for line in raw.decode('latin1').splitlines():
        p = line.split(' ')
        t = p[0]
        if t == 'FRAME':
            frame = int(p[1])
            if frame > 1:
                break
        elif t == 'SURF':
            surf[p[1]] = {'w': p[2], 'h': p[3], 'fmt': p[4], 'usage': p[5], 'tex': p[-1]}
        elif frame != 1:
            if t == 'VS': vs = p[1]
            elif t == 'PS': ps = p[1]
        elif t == 'RT' and p[1] == '0':
            cur = {'rt': p[2], 'draws': [], 'other': collections.Counter(), 'clears': [], 'ds': None, 'streams': set(), 'freq': collections.Counter()}
            passes.append(cur)
        elif cur is None:
            if t == 'VS': vs = p[1]
            elif t == 'PS': ps = p[1]
        elif t == 'DS': cur['ds'] = p[1]
        elif t == 'CLEAR': cur['clears'].append(line)
        elif t == 'VS': vs = p[1]
        elif t == 'PS': ps = p[1]
        elif t == 'VC':
            s, n = int(p[1]), int(p[2])
            for i in range(n):
                vc[s + i] = [float(x) for x in p[3 + 4 * i:7 + 4 * i]]
        elif t == 'PC':
            s, n = int(p[1]), int(p[2])
            for i in range(n):
                pc[s + i] = [float(x) for x in p[3 + 4 * i:7 + 4 * i]]
        elif t == 'T': tex[p[1]] = p[2]
        elif t in DRAWS:
            cur['draws'].append({'kind': t, 'vs': vs, 'ps': ps, 'prim': int(p[-1]) if t == 'DIP' else int(p[3]) if t == 'DP' else 0})
            if 'first_vc' not in cur:
                cur['first_vc'], cur['first_pc'] = dict(vc), dict(pc)
        elif t == 'SSRC': cur['streams'].add(p[2])
        elif t == 'FREQ': cur['freq'][p[2]] += 1
        elif t in ('SBAPPLY', 'SBCAPTURE', 'SBCREATE', 'STRETCH', 'UPDTEX', 'UPDSURF', 'FILL', 'READBACK', 'EVENT', 'MARKER', 'OTHERTHREAD'):
            cur['other'][t] += 1
    return surf, passes, hashlib.sha256(raw).hexdigest()


def main():
    root = Path(sys.argv[1])
    out = {}
    for n in sys.argv[2:]:
        surf, passes, sha = analyse(root / n / 'frame.txt')
        idx = [i for i, p in enumerate(passes) if p['draws']]
        shadow = [i for i in idx if surf.get(passes[i]['rt'], {}).get('fmt') in SHADOW_FMT]
        r = {'sha256': sha, 'passes': len(passes), 'passes_with_draws': len(idx), 'shadow_passes': shadow, 'first_draw_pass': idx[0] if idx else None}
        r['pass_list'] = [{'i': i, 'rt': {k: surf.get(passes[i]['rt'], {}).get(k) for k in ('w', 'h', 'fmt')}, 'draws': len(passes[i]['draws'])} for i in idx]
        if shadow:
            s = passes[shadow[0]]
            cnt = collections.Counter(d['vs'] for d in s['draws'])
            casters = []
            for h, c in cnt.most_common():
                nm = names(h)
                casters.append({'vs': label(h), 'draws': c, 'M': nm.get('shadow_map_projection_matrix', {}).get('reg'), 'Lz': nm.get('linear_z_shadow_map_projection_matrix', {}).get('reg'),
                                'ps': sorted({label(d['ps']) for d in s['draws'] if d['vs'] == h})})
            r['shadow'] = {'rt': surf.get(s['rt']), 'ds': surf.get(s['ds']), 'clears': s['clears'], 'draws': len(s['draws']), 'kinds': collections.Counter(d['kind'] for d in s['draws']),
                           'casters': casters, 'other': s['other'], 'streams': len(s['streams']), 'freq': s['freq'],
                           'unknown_vs': [h for h in cnt if h not in CAT or 'shadow_map_projection_matrix' not in names(h)]}
            b = next((int(names(h)['shadow_map_projection_matrix']['reg'][1:]) for h in cnt if 'shadow_map_projection_matrix' in names(h)), None)
            if b is not None:
                first = next(d['vs'] for d in s['draws'] if 'shadow_map_projection_matrix' in names(d['vs']))
                b = int(names(first)['shadow_map_projection_matrix']['reg'][1:])
                r['shadow']['M_rows'] = [s['first_vc'].get(b + i) for i in range(4)]
                r['shadow']['Lz_rows'] = [s['first_vc'].get(b + 4 + i) for i in range(4)]
        recv, rest = collections.Counter(), collections.Counter()
        for i in idx:
            if i in shadow:
                continue
            for d in passes[i]['draws']:
                if 'shadow_map_texture_sampler' in names(d['ps']):
                    recv[(i, label(d['ps']), label(d['vs']))] += 1
                else:
                    rest[(i, label(d['ps']))] += 1
        r['receivers'] = [{'pass': k[0], 'ps': k[1], 'vs': k[2], 'draws': v} for k, v in recv.most_common()]
        r['other_draws'] = [{'pass': k[0], 'ps': k[1], 'draws': v} for k, v in rest.most_common()]
        out[n] = r
    json.dump(out, sys.stdout, indent=1, default=lambda o: dict(o) if isinstance(o, collections.Counter) else sorted(o))


if __name__ == '__main__':
    main()
