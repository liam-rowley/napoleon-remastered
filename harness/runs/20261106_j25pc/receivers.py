#!/usr/bin/env python3
"""J25 receiver swap, offline half: compile each fx twice with the game's compiler (stock, and with the cascade fragment) and gate the pairs.

Run evidence (as J24's helpers), not a registered tool. Windows only (d3dx9_40 through core/discovery/shader_catalog.py).
usage: python3 harness/runs/20261106_j25pc/receivers.py --fx <extract>/data/fx --work <scratch dir> --out <dir>

Every catalogue pixel shader naming shadow_map_texture_sampler, compiled under the profile that reproduces it, its named technique alone in both
trees so the pair is that technique's receiver. Status: ok (swappable); gate_failed (a stock constant or sampler moved: the brief's CTAB gate,
fail = no swap); no_cascade_code (the fx calls shadow_map_occlusion directly, the macro never reached it, so the output is stock); needs_vs (the
new shader reads an input the stock vertex shader may not write); unpaired. Writes <out>/swap/<stock hash>.ps and <out>/receivers.json.
"""
import argparse
import importlib.util
import json
import re
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'core' / 'discovery'))
spec = importlib.util.spec_from_file_location('shader_catalog', ROOT / 'core' / 'discovery' / 'shader_catalog.py')
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)

SNIPPET = (Path(__file__).parent / 'cascade.fx_fragment').read_text(encoding='ascii')
OLD = ('#define CALC_OCCLUSION_SHADOW(shadow,v) shadow_map_occlusion(shadow,CALC_DISTANCE(v))\t\n'
       '#define CALC_OCCLUSION(v) shadow_map_occlusion(v.shadow,CALC_DISTANCE(v))\n')
NEW = ('#define CALC_OCCLUSION_SHADOW(shadow,v) cascade_occlusion(shadow,v.world_position.xyz,CALC_DISTANCE(v))\n'
       '#define CALC_OCCLUSION(v) cascade_occlusion(v.shadow,v.world_position.xyz,CALC_DISTANCE(v))\n')
TAIL = '#endif //SOFTWARE_SHADOWS\n\n#endif // SHADOW_MAP_FX_FRAGMENT'


def patch_fragment(path):
    t = path.read_bytes().decode('latin1').replace('\r\n', '\n')
    assert OLD in t and TAIL in t, 'the fragment is not the stock text'
    t = t.replace(OLD, NEW).replace(TAIL, SNIPPET + '\n' + TAIL)
    path.write_bytes(t.encode('latin1'))


def ctab(code):
    """{name: (set, index, count)} of a shader's CTAB comment (D3DX constant table)."""
    o = 4
    while o + 4 <= len(code):
        tok = struct.unpack_from('<I', code, o)[0]
        if tok & 0xFFFF != 0xFFFE:
            break
        n = (tok >> 16) & 0x7FFF
        if code[o + 4:o + 8] == b'CTAB':
            base = o + 8
            _, _, _, nconst, cinfo = struct.unpack_from('<5I', code, base)[:5]
            out = {}
            for i in range(nconst):
                nm, regset, regidx, regcnt = struct.unpack_from('<IHHH', code, base + cinfo + 20 * i)
                s = code[base + nm:code.index(b'\0', base + nm)].decode('latin1')
                out[s] = ('bifs'[regset], regidx, regcnt)
            return out
        o += 4 + 4 * n
    return {}


def gate(stock, new):
    bad = []
    for k, v in stock.items():
        if k not in new:
            bad.append(f'{k} gone')
        elif new[k][:2] != v[:2] or new[k][2] < v[2]:
            bad.append(f'{k} {v} -> {new[k]}')
    extra = [k for k in new if k not in stock and not k.startswith('cascade0_') and k != 'shadow_map_texture_size']
    return bad, extra


def inputs(code):
    """{(usage, index): mask} of a ps_3_0 stream's input declarations (dcl, opcode 0x1F, destination register type 1 = v#)."""
    t = struct.unpack(f'<{len(code) // 4}I', code[:len(code) // 4 * 4])
    i, out = 1, {}
    while i < len(t):
        tok = t[i]
        if tok == 0x0000FFFF:
            break
        op = tok & 0xFFFF
        if op == 0xFFFE:
            i += 1 + ((tok >> 16) & 0x7FFF)
            continue
        n = (tok >> 24) & 0x0F
        if op == 0x1F and n == 2:
            dst = t[i + 2]
            if ((dst >> 28) & 7) | ((dst >> 8) & 0x18) == 1:
                out[(t[i + 1] & 0x1F, (t[i + 1] >> 16) & 0xF)] = (dst >> 16) & 0xF
        i += 1 + n
    return out


def receivers_of(blob):
    """The effect's pixel streams that sample the shadow map, in stream order (duplicates kept once, as streams_in)."""
    return [(h, c) for h, c in sc.streams_in(blob).items() if 'shadow_map_texture_sampler' in ctab(c)]


def one_technique(tree, fx, name, tag):
    """A copy of fx holding only this technique, as cmd_fxmap names a technique (everything before the first, then this one)."""
    f = tree / fx
    text = f.read_text(encoding='latin1')
    techs = sc.techniques(text)
    hit = next((t for t in techs if t[0] == name), None)
    if hit is None:
        return None
    tmp = f.with_name(f'{f.stem}__{tag}.fx')
    tmp.write_text(text[:techs[0][1]] + text[hit[1]:hit[2]] + '\n', encoding='latin1')
    return tmp


def pair(trees, h, entry, variants):
    """(stock code, new code, how) for catalogue shader h, or (None, None, why). A named technique compiles alone in both trees, so the pair is
    the same technique's receiver; a shader with no named technique pairs by position in the whole effect, and says so."""
    prof = entry.get('profiles')
    prof = 'base' if prof == 'base' or 'base' in (prof or []) else prof[0]
    macros = variants[prof]
    fx, tech = entry['fx'], entry.get('technique')
    srcs = {}
    for tag, tree in trees.items():
        srcs[tag] = one_technique(tree, fx, tech, 'J25') if tech else tree / fx
        if srcs[tag] is None:
            return None, None, f'technique {tech} not found'
    blobs = {}
    for tag in trees:
        b, e = sc.compile_effect(srcs[tag], macros)
        if tech:
            srcs[tag].unlink()
        if b is None:
            return None, None, f'{tag} compile failed: {e[:160]}'
        blobs[tag] = receivers_of(b)
    s0, s1 = blobs['stock'], blobs['mod']
    idx = [i for i, (x, _) in enumerate(s0) if x == h]
    if not idx:
        return None, None, f'profile {prof} does not reproduce the stock hash'
    if len(s0) != len(s1):
        return None, None, f'{len(s0)} stock receivers against {len(s1)} modified'
    return s0[idx[0]][1], s1[idx[0]][1], f"{prof}, {'technique' if tech else 'POSITION in the whole effect'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fx', required=True); ap.add_argument('--work', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    cat = json.loads((ROOT / 'discovery' / 'napoleon' / 'shader_catalog.json').read_text(encoding='utf-8'))['shaders']
    want = sorted(h for h, s in cat.items() if s['stage'] == 'ps' and any(c['name'] == 'shadow_map_texture_sampler' for c in (s.get('ctab') or {}).get('constants', [])))
    trees = {}
    for tag in ('stock', 'mod'):
        w = Path(a.work) / tag / 'a' / 'fx'
        if w.parent.parent.exists():
            shutil.rmtree(w.parent.parent)
        shutil.copytree(a.fx, w)
        (w.parent.parent / 'personal_config.h').write_text('', encoding='ascii')
        trees[tag] = w
    patch_fragment(trees['mod'] / 'shadowmap.fx_fragment')
    variants = sc.profile_variants()
    out = Path(a.out)
    if (out / 'swap').exists():
        shutil.rmtree(out / 'swap')
    (out / 'swap').mkdir(parents=True)
    rows = []
    for h in want:
        entry = (cat[h].get('fx') or [{}])[0]
        r = {'hash': h, 'fx': entry.get('fx'), 'technique': entry.get('technique'), 'model': cat[h]['model']}
        code, new, how = pair(trees, h, entry, variants)
        r['paired_by'] = how
        if code is None:
            r['status'] = 'unpaired'
        else:
            c0, c1 = ctab(code), ctab(new)
            bad, extra = gate(c0, c1)
            i0, i1 = inputs(code), inputs(new)
            more = [f'{k} mask {v:x} over {i0.get(k, 0):x}' for k, v in i1.items() if v & ~i0.get(k, 0)]
            r.update(size=len(code), new_size=len(new), moved=bad, extra=extra, new_inputs=more)
            # the gate alone would pass a shader the macro never reached: it must also carry the cascade code
            r['status'] = 'no_cascade_code' if 'cascade0_matrix' not in c1 else 'gate_failed' if bad or extra else 'needs_vs' if more else 'ok'
            if r['status'] == 'ok':
                (out / 'swap' / f'{h}.ps').write_bytes(new)
        rows.append(r)
        print(f"{r['status']:16} {h} {r['fx']} {r['technique']} {r.get('size')} -> {r.get('new_size')} [{how}] {(r.get('moved') or [])[:2]} {(r.get('new_inputs') or [])[:2]}")
    (out / 'receivers.json').write_text(json.dumps(rows, indent=1) + '\n', encoding='utf-8', newline='\n')
    c = {}
    for r in rows:
        c[r['status']] = c.get(r['status'], 0) + 1
    print(f'{len(rows)} catalogue receivers: {c}')


if __name__ == '__main__':
    main()
