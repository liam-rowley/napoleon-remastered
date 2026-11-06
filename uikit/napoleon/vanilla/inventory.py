#!/usr/bin/env python3
"""Write components.json: every reusable vanilla UI kind, its sizes, states, use and the proposed library class (J99).

purpose: build the vanilla component inventory from the UI atlas and the assets registry: templates, frames and button art families, each mapped to a J34 library class or marked a gap
usage: python3 uikit/napoleon/vanilla/inventory.py [--check] [--stats]
when: after the atlas or the assets registry changes (the tests run --check); J69 walks the result with Liam
not-a-verb: one generator for one committed file, like uikit/napoleon/build.py; gallery.py reads what it writes

Kinds (`kind`): `template` (a name in a surface's templates_used: `script:<name>` or `template:<record>`), `frame` (a 9-slice frame group of sibling
components), `state_frame` (a frame drawn by one component: eight or more image uses in one state, which the atlas's frame groups do not see), `button`
(a family of `button_state` art, split on the state suffix of the file name). Committed data holds ids, keys, sizes and counts only (J7): no loc text.
`library` is a proposal for J69: a J34 class or `gap`, with `uncertain: true` where the match is a guess.
"""
import argparse
import collections
import gzip
import json
import posixpath
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'components.json'
CONTEXTS = ('battle', 'campaign', 'common', 'frontend', 'template')
SIZES_KEPT = 12              # a kind used at many sizes keeps its most used ones; sizes_total says how many there were
FRAME_USES = 8               # image uses in one state from which that state is a frame drawn by one component

# Proposed mapping, first match wins: (name pattern, library class, uncertain). Tag selectors are the library's scrollbars.
TEMPLATE_MAP = (
    (r'^tab$', '.tab', False),
    (r'^tabgroup$', '.tab-group', False),
    (r'^checkbox$', '.check', False),
    (r'^vslider$', 'scrollbarvertical', False),
    (r'^vslider_handle$', 'scrollbarvertical', False),
    (r'^tooltip$', '.tooltip', False),
    (r'^heading$', '.section-head', False),
    (r'^list$', '.list-row', False),
    (r'^(listview|sortable_list|list_header)$', '.list-row', True),
    (r'^(button_close|button_toggle|fe_button_standard)$', '.btn', True),
    (r'^buttongroup$', '.tab-group', True),
    (r'^(slider|slider_handle)$', '.bar', True),
    (r'^textview$', '.t-body', True),
    (r'tooltip', '.tooltip', True),
    (r'tab(title)?$', '.tab', True),
    (r'card$', '.card', True),
    (r'(entry|_row|row_|_item)', '.list-row', True),
    (r'(flag)', '.flag-slot', True),
    (r'(icon|pip)', '.icon', True),
)
BUTTON_MAP = (
    (r'^ui/battle_ui/buttons/', '.order-btn', True),
    (r'v_slider|scroll', 'scrollbarvertical', True),
    (r'slider', '.bar', True),
    (r'tab', '.tab', True),
    (r'check', '.check', True),
    (r'', '.btn', True),
)
SUFFIX = re.compile(r'^(.*?)[_ ](selected_roll|selected_down|normal|active|inactive|selected|roll|hover|down|up|off|locked)$', re.I)


def surfaces():
    """{surface path: record} over the five atlas files."""
    out = {}
    for ctx in CONTEXTS:
        with gzip.open(ROOT / 'discovery' / 'ui' / f'{ctx}.json.gz') as f:
            out.update(json.load(f)['surfaces'])
    return out


def jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def unit_index(rows):
    """{surface path, lower case with '/': [ui_elements ids]}: layouts by vanilla_source.layout, uied records by their template row."""
    idx = collections.defaultdict(set)
    for r in rows:
        lay = (r.get('vanilla_source') or {}).get('layout')
        if lay:
            idx[lay.replace('\\', '/').lower()].add(r['id'])
        if r['id'].startswith('template.'):
            idx['uied.templates/' + r['id'][len('template.'):]].add(r['id'])
    return idx


def units_of(path, idx):
    return sorted(idx.get(path.lower(), ()))


def mapped(name, table):
    for pat, cls, unsure in table:
        if re.search(pat, name):
            return {'library': cls, 'uncertain': True} if unsure else {'library': cls}
    return {'library': 'gap'}


def size_list(counter):
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:SIZES_KEPT]
    return [[w, h] for (w, h), _ in top]


def state_list(comps):
    """The union of the states of one kind's components: name and the art ids seen under that name, in first-seen order of the sorted instances."""
    seen = {}
    for c in comps:
        for st in c['states']:
            imgs = seen.setdefault(st['name'], [])
            imgs.extend(i for i in st['images'] if i not in imgs)
    return [{'name': n, 'assets': seen[n]} for n in sorted(seen)]


def template_kinds(surf, idx):
    named = collections.defaultdict(set)
    for path, rec in surf.items():
        for t in rec.get('templates_used', []):
            if t.startswith(('script:', 'template:')):
                named[t].add(path)
    by_script = collections.defaultdict(list)
    for path in sorted(surf):
        for c in surf[path].get('components', []):
            base = posixpath.basename(c.get('script', ''))
            if base.startswith('template.') and base.endswith('.luac'):
                by_script[base[len('template.'):-len('.luac')]].append((path, c))
    records = {k.split('/', 1)[1].lower(): k for k in surf if k.startswith('uied.templates/')}
    out = []
    for key, users in named.items():
        how, _, name = key.partition(':')
        if how == 'script':
            inst = by_script.get(name, [])
        else:
            rec = records.get(name.lower())
            inst = [(rec, surf[rec]['components'][0])] if rec and surf[rec].get('components') else []
        comps = [c for _, c in inst]
        sizes = collections.Counter((c['w'], c['h']) for c in comps)
        units = {u for p in users for u in units_of(p, idx)}
        if f'template.{name.lower()}' in {u for v in idx.values() for u in v}:
            units.add(f'template.{name.lower()}')
        e = {'id': key, 'kind': 'template', 'source': how, 'sizes': size_list(sizes), 'sizes_total': len(sizes), 'states': state_list(comps),
             'use_count': len(users), 'instances': len(inst), 'surfaces': sorted(users), 'ui_elements': sorted(units)}
        if inst:
            e['sample'] = {'surface': inst[0][0], 'path': inst[0][1]['path']}
        e.update(mapped(name.lower(), TEMPLATE_MAP))
        out.append(e)
    return out


def stem_of(art):
    """The file stem of an art id; a UI-editor path keeps only its file name."""
    return re.split(r'[\\/]', art)[-1].rsplit('.', 1)[0]


def unique_ids(kinds):
    """Two art sets can share a corner and a count: number the later ones, in a fixed order."""
    seen = collections.Counter()
    for e in sorted(kinds, key=lambda e: json.dumps(e['states'], sort_keys=True)):
        seen[e['id']] += 1
        if seen[e['id']] > 1:
            e['id'] += f"#{seen[e['id']]}"
    return kinds


def frame_kinds(surf, idx):
    groups = collections.defaultdict(list)
    for path in sorted(surf):
        for g in surf[path].get('frame_groups', []):
            art = tuple(sorted((k, tuple(v)) for k, v in g['pieces'].items()))
            groups[art].append((path, g))
    out = []
    for art, uses in groups.items():
        first = uses[0][1]
        stem = stem_of(dict(art)['TL'][0]) if dict(art)['TL'] else 'frame'
        users = sorted({p for p, _ in uses})
        out.append({'id': 'frame:' + stem, 'kind': 'frame', 'insets': first['insets'], 'sizes': [], 'sizes_total': 0,
                    'states': [{'name': k, 'assets': list(v)} for k, v in art], 'use_count': len(uses), 'instances': len(uses),
                    'surfaces': users, 'ui_elements': sorted({u for p in users for u in units_of(p, idx)}),
                    'sample': {'surface': uses[0][0], 'path': first['parent']},
                    **({'library': '.tooltip'} if 'tooltip' in stem else {'library': '.panel', 'uncertain': True})})
    return unique_ids(out)


def state_frame_kinds(surf, idx):
    groups = collections.defaultdict(list)
    for path in sorted(surf):
        for c in surf[path].get('components', []):
            for st in c['states']:
                if len(st['images']) >= FRAME_USES and len(set(st['images'])) >= 2:
                    groups[tuple(sorted(set(st['images'])))].append((path, c, st))
    out = []
    for art, uses in groups.items():
        sizes = collections.Counter((st['w'], st['h']) for _, _, st in uses)
        users = sorted({p for p, _, _ in uses})
        stem = stem_of(next((a for a in art if 'corner' in a), art[0]))
        out.append({'id': f'state_frame:{stem}+{len(art)}', 'kind': 'state_frame', 'sizes': size_list(sizes), 'sizes_total': len(sizes),
                    'states': [{'name': 'art', 'assets': list(art)}], 'use_count': len(users), 'instances': len(uses), 'surfaces': users,
                    'ui_elements': sorted({u for p in users for u in units_of(p, idx)}),
                    'sample': {'surface': uses[0][0], 'path': uses[0][1]['path'], 'state': uses[0][2]['name']},
                    'library': '.panel', 'uncertain': True})
    return unique_ids(out)


def button_kinds(assets):
    fams = collections.defaultdict(list)
    for r in assets:
        if r.get('role') != 'button_state':
            continue
        d, base = posixpath.split(r['id'])
        stem = base.rsplit('.', 1)[0]
        m = SUFFIX.match(stem)
        fams[f'{d}/{m.group(1) if m else stem}'].append((m.group(2).lower() if m else 'default', r))
    out = []
    for fam, members in fams.items():
        sizes = collections.Counter()
        for _, r in members:
            m = re.search(r'(\d+)x(\d+)$', r.get('format', ''))
            if m:
                sizes[(int(m.group(1)), int(m.group(2)))] += 1
        units = sorted({u for _, r in members for u in r.get('used_by', [])})
        states = sorted({(n, r['id']) for n, r in members})
        out.append({'id': 'button:' + fam, 'kind': 'button', 'sizes': size_list(sizes), 'sizes_total': len(sizes),
                    'states': [{'name': n, 'assets': [i]} for n, i in states], 'use_count': len(units), 'instances': len(members),
                    'surfaces': [], 'ui_elements': units, **mapped(fam, BUTTON_MAP)})
    return out


def build():
    surf = surfaces()
    idx = unit_index(jsonl(ROOT / 'registries' / 'ui_elements.jsonl'))
    kinds = template_kinds(surf, idx) + frame_kinds(surf, idx) + state_frame_kinds(surf, idx) + button_kinds(jsonl(ROOT / 'registries' / 'assets.jsonl'))
    kinds.sort(key=lambda e: (-e['use_count'], e['id']))
    return kinds


def dumps(kinds):
    """One kind per line, sorted keys: a small diff when one kind changes."""
    return '[\n' + ',\n'.join(json.dumps(e, sort_keys=True, separators=(',', ':')) for e in kinds) + '\n]\n'


def stats(kinds):
    by = collections.Counter(e['kind'] for e in kinds)
    return {'kinds': len(kinds), **{f'kind_{k}': n for k, n in sorted(by.items())}, 'gaps': sum(e['library'] == 'gap' for e in kinds),
            'uncertain': sum(bool(e.get('uncertain')) for e in kinds), 'mapped_sure': sum(e['library'] != 'gap' and not e.get('uncertain') for e in kinds)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true', help='fail when components.json differs from a rebuild')
    ap.add_argument('--stats', action='store_true', help='print the counts')
    a = ap.parse_args(argv)
    kinds = build()
    text = dumps(kinds)
    if a.check:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print('components.json is stale: python3 uikit/napoleon/vanilla/inventory.py', file=sys.stderr)
            return 1
    else:
        OUT.write_text(text, encoding='utf-8', newline='\n')
    if a.stats or not a.check:
        print(json.dumps(stats(kinds)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
