"""J9 capture summary: draws per fx technique, RT sizes, textures bound on imposter/sprite draws, shadow farz (PC c of shadow_map_farz)."""
import sys, json, re, collections
cat = json.load(open(r'C:\Users\liamr\repos\napoleon-remastered\discovery\napoleon\shader_catalog.json', encoding='utf-8'))
def find_map(o):
    if isinstance(o, dict):
        if o and all(re.fullmatch(r'[0-9a-f]{16}', k) for k in list(o)[:5]): return o
        for v in o.values():
            r = find_map(v)
            if r: return r
    return None
smap = find_map(cat) or {}
def fxname(h):
    e = smap.get(h) or {}
    fx = e.get('fx') or []
    return f"{fx[0]['fx']}:{fx[0]['technique']}" if fx else f'?{h[:8]}'
for path in sys.argv[1:]:
    tex, surf = {}, {}
    vs = ps = None; bound = {}
    draws = collections.Counter(); prims = collections.Counter(); imp_tex = collections.Counter(); rts = collections.Counter(); farz = collections.Counter()
    pc = {}; cur_rt = None; rt_draws = collections.Counter(); texsize = collections.Counter()
    farreg = None
    if True:
        pass
    for line in open(path, encoding='utf-8', errors='replace'):
        p = line.split()
        if not p: continue
        k = p[0]
        if k == 'TEX': tex[p[1]] = (int(p[4]), int(p[5]), p[7])
        elif k == 'SURF': surf[p[1]] = (int(p[2]), int(p[3]), p[4])
        elif k == 'RT' and p[1] == '0': rts[surf.get(p[2], ('?',))] += 1; cur_rt = surf.get(p[2], ('?',))
        elif k == 'VS': vs = p[1]
        elif k == 'PS': ps = p[1]
        elif k == 'T': bound[int(p[1])] = p[2]
        elif k == 'PC':
            st, n = int(p[1]), int(p[2]); vals = p[3:]
            for i in range(0, len(vals) // 4): pc[st + i] = vals[i*4:i*4+4]
        elif k in ('DIP', 'DP'):
            n = fxname(vs) if vs and vs != '0000000000000000' else 'none'
            draws[n] += 1
            rt_draws[cur_rt] += 1
            prims[n] += int(p[-1])
            pe = smap.get(ps) or {}
            for c in (pe.get('ctab') or {}).get('constants', []):
                if c['name'] == 'shadow_map_farz' and c['index'] in pc: farz[pc[c['index']][0]] += 1
                if c['name'] == 'shadow_map_texture_size' and c['index'] in pc: texsize[tuple(pc[c['index']][:2])] += 1
            if 'imposter' in n or 'sprite' in n:
                for st, t in bound.items():
                    if t in tex: imp_tex[(n.split(':')[1], st, tex[t][:2], tex[t][2])] += 1
    print('==', path)
    print(' RTs (w,h,fmt): ', dict(rts))
    for n, c in sorted(draws.items(), key=lambda x: -x[1])[:40]: print(f'  {c:5d} draws {prims[n]:8d} prims  {n}')
    print('  shadow_map_farz values (ps):', dict(farz))
    print('  shadow_map_texture_size (ps):', dict(texsize))
    print('  draws per RT:', {str(k): v for k, v in rt_draws.items()})
    for k_, c in sorted(imp_tex.items(), key=lambda x: -x[1])[:12]: print('  imp/sprite tex', k_, c)
