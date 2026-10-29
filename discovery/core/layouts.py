#!/usr/bin/env python3
"""Layouts pass of the Empire-to-other-game diff: UI layout versions, byte-exact round trip, uied.templates record versions, font names.

purpose: list every UI layout file (Version0NN) and uied.templates record of two games with its version and whether the ported Empire codec (uic.py, tpl.py) round-trips it byte for byte, plus the font names the layouts reference
usage: python3 discovery/core/layouts.py [--games discovery/napoleon/games.json] [--out discovery/diff/layouts.json]   (needs the extract: discovery/README.md)
when: J6 layouts area; re-run after a codec change (a V039 field decoded) to see the round-trip count move; the fonts pass reads detail.fonts_referenced
not-a-verb: reads extracted game files and the loose uied.templates in the install, outside the wsc registry operations
"""
import argparse
import collections
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from diffout import row, write  # noqa: E402
from extracted import effective, load_games  # noqa: E402
import tpl  # noqa: E402
import uic  # noqa: E402

FONT = re.compile(rb'[\x05-\x40]\x00([A-Z][A-Za-z_]*(?: [A-Za-z_]+)* \d{1,2}, [A-Z][A-Za-z ]*?)(?=[\x00-\x1f])')


def roundtrip(b, name):
    try:
        return 'ok' if uic.serialise(uic.parse(b, name)) == b else 'mismatch'
    except Exception as e:  # noqa: BLE001 (any decode failure is a result, not an error)
        return f'fail: {type(e).__name__}'


def layouts(games, game):
    files = {p: f for p, f in effective(games, game, exts={''}, under='ui\\').items()}
    out, fonts = {}, collections.Counter()
    for p, f in files.items():
        b = open(f, 'rb').read()
        if not b.startswith(b'Version'):
            continue
        out[p] = {'version': int(b[7:10]), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'roundtrip': roundtrip(b, p)}
        fonts.update(m.decode('latin-1') for m in FONT.findall(b))
    return out, fonts


def templates(games, game):
    g = games[game]
    p = os.path.join(g['root'], g['data'], 'ui', 'templates', 'uied.templates')
    b = open(p, 'rb').read()
    recs, out, fonts = tpl.split(b), {}, collections.Counter()
    for r in recs:
        try:
            res = 'ok' if tpl.serialise_record(tpl.parse_record(r), r['ver']) == r['payload'] else 'mismatch'
        except Exception as e:  # noqa: BLE001
            res = f'fail: {type(e).__name__}'
        out[r['name']] = {'version': r['ver'], 'textures': r['ntex'], 'bytes': len(r['payload']), 'roundtrip': res}
        fonts.update(m.decode('latin-1') for m in FONT.findall(r['payload']))
    return {'file': 'data\\ui\\templates\\uied.templates (loose)', 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'records': dict(sorted(out.items()))}, fonts


def by_version(items):
    v = collections.defaultdict(collections.Counter)
    for x in items.values():
        v[x['version']]['ok' if x['roundtrip'] == 'ok' else 'fail'] += 1
    return v


def describe(c):
    return f"{c['ok'] + c['fail']} ({c['ok']} round-trip)" if c else '-'


V039 = ('V033 plus a u32 default-state id after c_flag (uic.py state_ref) and a per-component animation list before the child '
        'count (name, empty str, u32 n, 48-byte keyframes: f32 x, f32 y, size, rgba, u32 time ms at +36, u32 interpolation at +40); '
        'state transitions are longer than V033 (about 18 bytes each, not decoded: napoleon.diff.layouts.v039_transitions)')


def compare(el, nl, et, nt):
    rows = []
    ve, vn = by_version(el), by_version(nl)
    for v in sorted(set(ve) | set(vn)):
        e, n = ve.get(v), vn.get(v)
        verdict = 'gone' if not n else 'new' if not e else 'same' if not n['fail'] else 'adapter'
        note = V039 if v == 39 else ('Empire codec unchanged' if verdict == 'same' else '')
        if verdict == 'new' and n and n['fail']:
            verdict = 'adapter'
        rows.append(row(f'layout Version{v:03d}', describe(e), describe(n), verdict, note, 'detail.*_layouts'))
    te, tn = by_version(et['records']), by_version(nt['records'])
    for v in sorted(set(te) | set(tn)):
        e, n = te.get(v), tn.get(v)
        verdict = 'gone' if not n else 'new' if not e else 'same' if n['fail'] == e['fail'] else 'adapter'
        note = {35: 'not decoded (kill criterion): napoleon.diff.layouts.template_v35', 39: 'same component codec as layout V039'}.get(v, '')
        if e and n and e['fail'] and n['fail'] == e['fail']:
            note = 'fails in Empire too (Empire codec limit, not a Napoleon change)'
        rows.append(row(f'uied.templates record v{v}', describe(e), describe(n), verdict, note, 'detail.*_templates'))
    rows.append(row('uied.templates container', f"{len(et['records'])} records, loose file", f"{len(nt['records'])} records, loose file",
                    'same', 'tpl.split unchanged', 'detail.*_templates'))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--games')
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'diff', 'layouts.json'))
    a = ap.parse_args(argv)
    g = load_games(a.games)
    el, ef = layouts(g, 'empire')
    nl, nf = layouts(g, 'napoleon')
    et, etf = templates(g, 'empire')
    nt, ntf = templates(g, 'napoleon')
    rows = compare(el, nl, et, nt)
    write(a.out, 'layouts', rows, {
        'empire_layouts': el, 'napoleon_layouts': nl, 'empire_templates': et, 'napoleon_templates': nt,
        'fonts_referenced': {'empire': dict(sorted((ef + etf).items())), 'napoleon': dict(sorted((nf + ntf).items()))},
        'napoleon_loose_ui_layouts': 'none: data\\UI holds only .tga, .cur, .ani and uied.templates (packs.json detail.napoleon_loose)'})
    print(f'{a.out}: {len(rows)} rows; Napoleon {len(nl)} layouts, {len(nt["records"])} template records; Empire {len(el)}, {len(et["records"])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
