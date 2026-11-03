#!/usr/bin/env python3
"""Effects pass (static) of the Empire-to-other-game diff: the particle and smoke definitions, their textures and fx, the exe names and the effect db tables.

purpose: diff both games' effects\\ entries file by file, the XML effect definitions per SCRIPTED_EFFECT_INFO and SCRIPTED_EFFECT_GROUP name (tags and attribute names new or gone), the textures and fx the other game's definitions reference and whether Empire has them, the counts of the new names in both exes, and the particle_effects, projectiles_explosions and projectile_trails tables; the smoke subset is what the projectile rows point at
usage: python3 discovery/core/effects.py [--games discovery/napoleon/games.json] [--out discovery/diff/effects.json] [--check] | --trim-schema <empire-remastered rml_mod/tools/db/schema_emp.json>
when: J72 (the Empire smoke backport question, PLAN section 4); re-run after a game update; --check in review (reads both installs, PC only)
not-a-verb: reads both installs' packs and exes in place (read only), outside the wsc registry operations

Packs are read through packfs.PackFS by index offset (each game's pack_order, its mod_packs skipped). Loose data\\ files are mod
files here: listed under detail.<game>_loose_skipped, never compared. Game data values are not committed: names, counts and
hashes only. Empire's db tables decode with discovery/napoleon/empire_db_schema_effects.json (trimmed from empire-remastered's
converted RPFM schema by --trim-schema), Napoleon's with discovery/napoleon/db_schema.json, both through db.decode_table.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from db import decode_table, load_schema  # noqa: E402
from diffout import dumps, row  # noqa: E402
from packfs import LOOSE, PackFS, key  # noqa: E402

OUT = os.path.join(REPO, 'discovery', 'diff', 'effects.json')
GAMES = os.path.join(REPO, 'discovery', 'napoleon', 'games.json')
SHADERS = os.path.join(REPO, 'discovery', 'diff', 'shaders.json')
DB_TABLES = os.path.join(REPO, 'discovery', 'db', 'tables.json')
EMPIRE_SCHEMA = os.path.join(REPO, 'discovery', 'napoleon', 'empire_db_schema_effects.json')
UNDER = 'effects\\'
TABLES = ('particle_effects', 'projectiles_explosions', 'projectile_trails')
SMOKE_TABLES = ('projectiles', 'projectiles_explosions', 'projectile_trails')
SCHEMA_TABLES = TABLES + ('projectiles',)
REF_EXTS = ('.dds', '.tga', '.fx', '.fx_fragment')
INFO, GROUP = 'SCRIPTED_EFFECT_INFO', 'SCRIPTED_EFFECT_GROUP'
SMOKE_RX = re.compile(r'smoke|musket|cannon|gun|volley|explosion|blast|fire|dust', re.I)
VERDICT = {'identical': 'same', 'changed': 'adapter', 'new': 'new', 'gone': 'gone'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---- files -------------------------------------------------------------------------------------------------------------

def pack_view(fs, under=''):
    """({key: effective pack Copy}, [shadowed pack Copy], [loose Copy]) under a prefix; loose files never win here."""
    eff, shadowed, loose = {}, [], []
    for c in fs.copies():
        k = key(c.path)
        if under and not k.startswith(under):
            continue
        if c.source == LOOSE:
            loose.append(c)
        elif k not in eff or c.order >= eff[k].order:
            if k in eff:
                shadowed.append(eff[k])
            eff[k] = c
        else:
            shadowed.append(c)
    return dict(sorted(eff.items())), sorted(shadowed, key=lambda c: (key(c.path), c.order)), sorted(loose, key=lambda c: key(c.path))


def file_status(e, n):
    if e is None:
        return 'new'
    if n is None:
        return 'gone'
    return 'identical' if e['sha256'] == n['sha256'] else 'changed'


def classify_files(ef, nf):
    """{path: {status, empire: {pack, bytes, sha256}?, napoleon: {...}?}}"""
    return {p: {'status': file_status(ef.get(p), nf.get(p)), **({'empire': ef[p]} if p in ef else {}), **({'napoleon': nf[p]} if p in nf else {})}
            for p in sorted(set(ef) | set(nf))}


def kind(path):
    ext = os.path.splitext(path)[1]
    return ext[1:] if ext else 'none'


# ---- definitions -------------------------------------------------------------------------------------------------------

def flatten(el):
    """{attribute key: value} of an element's subtree (the element's own attributes under '.'); a child tag repeated among its
    siblings carries its index, and the key is the leaf tag alone when that tag path is unique in the subtree."""
    out = {}

    def walk(e, path):
        for a, v in e.attrib.items():
            out[(path, a)] = v
        seen = collections.Counter(c.tag for c in e)
        idx = collections.Counter()
        for c in e:
            t = c.tag + (f'[{idx[c.tag]}]' if seen[c.tag] > 1 else '')
            idx[c.tag] += 1
            walk(c, path + (t,))
    walk(el, ())
    paths = collections.Counter(p[-1] for p in {p for p, _ in out if p})
    flat = {}
    for (p, a), v in out.items():
        if not p:
            k = a
        elif paths[p[-1]] == 1:
            k = f'{p[-1]}.{a}'
        else:
            k = '/'.join(p) + '.' + a
        flat[k] = v
    return flat


def parse_definition(b):
    """Summary of one XML definition file plus its named infos and groups ({name: flat attributes}); values stay in memory."""
    s = {'bytes': len(b), 'sha256': sha(b)}
    try:
        root = ET.fromstring(b)
    except ET.ParseError as ex:
        s['parse'] = f'error: {ex}'
        return s, {}, {}
    tags, attrs = collections.Counter(), collections.defaultdict(set)
    for e in root.iter():
        tags[e.tag] += 1
        attrs[e.tag] |= set(e.attrib)
    s.update(parse='ok', root=root.tag, tags=dict(sorted(tags.items())), attrs={t: sorted(v) for t, v in sorted(attrs.items())})
    named = {}
    for tag in (INFO, GROUP):
        d, dup = {}, []
        for e in root.iter(tag):
            n = e.get('name', '')
            if n in d:
                dup.append(n)
            d[n] = flatten(e)
        named[tag] = d
        if dup:
            s.setdefault('duplicate_names', {})[tag] = sorted(set(dup))
    return s, named[INFO], named[GROUP]


def diff_named(e, n):
    """{name: {status[, attrs_changed, attrs_added, attrs_removed, add_only]}} for one tag's named elements."""
    out = {}
    for name in sorted(set(e) | set(n)):
        a, b = e.get(name), n.get(name)
        if a is None or b is None:
            out[name] = {'status': 'new' if a is None else 'gone'}
            continue
        if a == b:
            out[name] = {'status': 'identical'}
            continue
        d = {'status': 'changed', 'attrs_changed': sorted(k for k in set(a) & set(b) if a[k] != b[k]),
             'attrs_added': sorted(set(b) - set(a)), 'attrs_removed': sorted(set(a) - set(b))}
        d['add_only'] = not d['attrs_changed'] and not d['attrs_removed']
        out[name] = d
    return out


def counts(diff):
    c = collections.Counter(v['status'] for v in diff.values())
    out = {s: c[s] for s in ('identical', 'changed', 'new', 'gone')}
    out['changed_add_only'] = sum(1 for v in diff.values() if v.get('add_only'))
    return out


def format_diff(es, ns):
    """Tags and attribute names (per tag) new in the second summary and gone from it."""
    et, nt = set(es.get('attrs', {})), set(ns.get('attrs', {}))
    an, ag = {}, {}
    for t in sorted(et & nt):
        x, y = set(es['attrs'][t]), set(ns['attrs'][t])
        if y - x:
            an[t] = sorted(y - x)
        if x - y:
            ag[t] = sorted(x - y)
    for t in sorted(nt - et):
        an[t] = list(ns['attrs'][t])
    for t in sorted(et - nt):
        ag[t] = list(es['attrs'][t])
    return {'tags_new': sorted(nt - et), 'tags_gone': sorted(et - nt), 'attrs_new': an, 'attrs_gone': ag}


def text_summary(b):
    t = b.decode('latin-1')
    lines = [x.strip() for x in t.splitlines()]
    body = [x for x in lines if x and not x.startswith('//')]
    head = body[0] if body else ''
    recs = body[1:] if head.lower().startswith('version') else body
    shapes = collections.Counter(len(x.split()) for x in recs)
    fmt = (f'plain text: a "{head}" line, // comments, then one record per line of {"/".join(str(k) for k in sorted(shapes))} '
           f'whitespace-separated fields') if recs else 'plain text, no records'
    return {'bytes': len(b), 'sha256': sha(b), 'header': head, 'records': len(recs), 'format': fmt}


# ---- references --------------------------------------------------------------------------------------------------------

def norm_ref(v):
    return v.strip().replace('/', '\\').lstrip('\\').lower()


def is_ref(v):
    return v.strip().lower().endswith(REF_EXTS)


def info_refs(flat):
    return sorted({norm_ref(v) for v in flat.values() if is_ref(v)})


def fx_key(ref):
    return ref if ref.startswith('fx\\') else 'fx\\' + ref


def ref_status(ref, empire_has, napoleon_has, fx_files):
    """'same' | 'changed' | 'missing' for a texture (against Empire's files) or an fx (against shaders.json detail.files)."""
    if ref.endswith(('.fx', '.fx_fragment')):
        st = (fx_files.get(fx_key(ref)) or {}).get('status')
        return {'identical': 'same', 'changed': 'changed', 'new': 'missing', 'gone': 'gone_from_napoleon'}.get(st, 'unknown')
    e, n = empire_has(ref), napoleon_has(ref)
    if e is None:
        return 'missing' if n is not None else 'absent_in_both'
    return 'same' if n is not None and e == n else ('changed' if n is not None else 'empire_only')


# ---- exe names ---------------------------------------------------------------------------------------------------------

def name_counts(blob, name):
    a, u = name.encode('ascii'), name.encode('utf-16-le')
    return {'ascii': blob.count(a), 'utf16': blob.count(u),
            'ascii_exact': blob.count(b'\0' + a + b'\0'), 'utf16_exact': blob.count(b'\0\0' + u + b'\0\0')}


# ---- db ----------------------------------------------------------------------------------------------------------------

def key_fields(fields):
    ks = [i for i, f in enumerate(fields) if f.get('key')]
    if ks:
        return ks
    return [next((i for i, f in enumerate(fields) if f['name'] == 'key'), 0)]


def read_table(view, fs, table, versions):
    """(summary, {key: {field: value}} or None) of a table's effective pack copy (every file of its folder, rows merged)."""
    pre = f'db\\{table}_tables\\'
    cs = [c for k, c in view.items() if k.startswith(pre)]
    if not cs:
        return {'status': 'absent'}, None
    s = {'files': [{'pack': c.source, 'file': key(c.path), 'bytes': c.size} for c in cs]}
    rows, fields, decoded = {}, None, True
    for c in cs:
        b = fs.read(c)
        s['files'][cs.index(c)]['sha256'] = sha(b)
        d = decode_table(b, versions)
        s['files'][cs.index(c)].update(version=d['version'], rows=d['rows_declared'], status=d['status'])
        if not d['status'].startswith('decoded'):
            decoded = False
            s['files'][cs.index(c)]['reason'] = '; '.join(d.get('errors', [])) or d['status']
            continue
        s['files'][cs.index(c)]['schema_version'] = d['schema_version']
        fields = d['fields']
        names = [f['name'] for f in fields]
        kf = key_fields(fields)
        for r in d['rows']:
            rows['|'.join(str(r[i]) for i in kf)] = dict(zip(names, r))
    s['decoded'] = decoded
    if fields is not None:
        s['fields'] = [f['name'] for f in fields]
        s['key_fields'] = [fields[i]['name'] for i in key_fields(fields)]
    s['rows'] = len(rows) if decoded else None
    return s, (rows if decoded else None)


def row_hash(r, names):
    return sha(json.dumps([r.get(n) for n in names], sort_keys=True).encode())


def diff_rows(er, nr, nfields, efields):
    common = [n for n in nfields if n in efields]
    st = collections.defaultdict(list)
    for k in sorted(set(er) | set(nr)):
        if k not in er:
            st['new'].append(k)
        elif k not in nr:
            st['gone'].append(k)
        else:
            st['identical' if row_hash(er[k], common) == row_hash(nr[k], common) else 'changed'].append(k)
    return {'compared_on': common, 'fields_new': [n for n in nfields if n not in efields], 'fields_gone': [n for n in efields if n not in nfields],
            **{s: st.get(s, []) for s in ('identical', 'changed', 'new', 'gone')}}


def particle_refs(db_tables_doc, tables=SMOKE_TABLES):
    """{table: [field]} of the fields whose ref is particle_effects, per discovery/db/tables.json."""
    out = {}
    for t in db_tables_doc.get('tables', []):
        if t['name'] in tables:
            out[t['name']] = [f['name'] for f in t.get('fields', []) if (f.get('ref') or {}).get('table') == 'particle_effects']
    return {t: out.get(t, []) for t in tables}


# ---- the pass ----------------------------------------------------------------------------------------------------------

def build(games, shader_files, refs_by_table):
    """games: {'empire'|'napoleon': {'fs': PackFS, 'exe': bytes, 'schema': {table_tables: [versions]}}}. Returns (rows, detail)."""
    view, effx, loose, shadow, everything = {}, {}, {}, {}, {}
    for g in ('empire', 'napoleon'):
        fs = games[g]['fs']
        everything[g], sh, lo = pack_view(fs)
        view[g] = {k: c for k, c in everything[g].items() if k.startswith(UNDER)}
        shadow[g] = [{'pack': c.source, 'path': key(c.path), 'bytes': c.size} for c in sh if key(c.path).startswith(UNDER)]
        loose[g] = [key(c.path) for c in lo if key(c.path).startswith(UNDER) or key(c.path).startswith('db\\')]
        effx[g] = {}
        for k, c in view[g].items():
            b = fs.read(c)
            effx[g][k] = {'pack': c.source, 'bytes': c.size, 'sha256': sha(b), '_b': b}
    for s in shadow.values():
        for x in s:
            fs = games['empire' if s is shadow['empire'] else 'napoleon']['fs']
            c = next(c for c in fs.copies() if c.source == x['pack'] and key(c.path) == x['path'])
            x['sha256'] = sha(fs.read(c))
    strip = lambda d: {k: {kk: vv for kk, vv in v.items() if kk != '_b'} for k, v in d.items()}
    files = classify_files(strip(effx['empire']), strip(effx['napoleon']))

    # definitions
    defs, infos, groups = {}, {'empire': {}, 'napoleon': {}}, {'empire': {}, 'napoleon': {}}
    texts = {}
    for p in files:
        if p.endswith('.xml'):
            sm = {}
            for g in ('empire', 'napoleon'):
                if p in effx[g]:
                    sm[g], infos[g][p], groups[g][p] = parse_definition(effx[g][p]['_b'])
            d = {g: sm[g] for g in sm}
            if len(sm) == 2:
                d['infos'] = diff_named(infos['empire'][p], infos['napoleon'][p])
                d['groups'] = diff_named(groups['empire'][p], groups['napoleon'][p])
                d['info_counts'], d['group_counts'] = counts(d['infos']), counts(d['groups'])
                d['info_attrs_changed'] = dict(sorted(collections.Counter(
                    a for v in d['infos'].values() for a in v.get('attrs_changed', [])).items()))
                d.update(format_diff(sm['empire'], sm['napoleon']))
            defs[p] = d
        elif p.endswith('.txt'):
            texts[p] = {g: text_summary(effx[g][p]['_b']) for g in ('empire', 'napoleon') if p in effx[g]}
    fmt_all = {'tags_new': sorted({t for d in defs.values() for t in d.get('tags_new', [])}),
               'tags_gone': sorted({t for d in defs.values() for t in d.get('tags_gone', [])}),
               'attrs_new': sorted({a for d in defs.values() for v in d.get('attrs_new', {}).values() for a in v}),
               'attrs_gone': sorted({a for d in defs.values() for v in d.get('attrs_gone', {}).values() for a in v})}
    # names that are new as attribute names anywhere (not just on one tag): new to the game's parser vocabulary
    vocab = {g: set() for g in ('empire', 'napoleon')}
    for d in defs.values():
        for g in vocab:
            if g in d and d[g].get('parse') == 'ok':
                vocab[g] |= {a for v in d[g]['attrs'].values() for a in v}
    fmt_all['attr_names_new_to_empire'] = sorted(vocab['napoleon'] - vocab['empire'])
    fmt_all['attr_names_gone'] = sorted(vocab['empire'] - vocab['napoleon'])

    # references
    def has(g):
        fs = games[g]['fs']
        cache = {}

        def f(ref):
            if ref not in cache:
                c = everything[g].get(ref)
                cache[ref] = sha(fs.read(c)) if c is not None else None
            return cache[ref]
        return f
    e_has, n_has = has('empire'), has('napoleon')
    refs, lacking = {}, {}
    for p in sorted(infos['napoleon']):
        for name, flat in infos['napoleon'][p].items():
            for r in info_refs(flat):
                if r not in refs:
                    fx = r.endswith(('.fx', '.fx_fragment'))
                    refs[r] = {'kind': 'fx' if fx else 'texture', 'empire': ref_status(r, e_has, n_has, shader_files), 'used_by': 0}
                    if not fx and refs[r]['empire'] in ('missing', 'absent_in_both'):
                        alt = os.path.splitext(r)[0] + ('.dds' if r.endswith('.tga') else '.tga')
                        refs[r]['other_ext'] = {'path': alt, 'empire': e_has(alt) is not None, 'napoleon': n_has(alt) is not None}
                refs[r]['used_by'] += 1
                if refs[r]['empire'] in ('missing', 'unknown'):
                    lacking.setdefault(p, {}).setdefault(name, []).append(r)
    group_lacking = {}
    for p, gs in groups['napoleon'].items():
        for gname, flat in gs.items():
            ents = {v for k, v in flat.items() if k.endswith('.effect')}
            miss = sorted({r for e in ents for r in lacking.get(p, {}).get(e, [])})
            if miss:
                group_lacking.setdefault(p, {})[gname] = miss

    # exe names
    fx_new = sorted(r for r, v in refs.items() if v['kind'] == 'fx' and v['empire'] == 'missing')
    txt_new = sorted(os.path.basename(p) for p, f in files.items() if f['status'] == 'new' and p.endswith('.txt'))
    probe = sorted(set(fmt_all['tags_new']) | set(fmt_all['attr_names_new_to_empire']) | set(fx_new) | set(txt_new)
                   | {os.path.splitext(t)[0] for t in txt_new})
    common = sorted((vocab['empire'] & vocab['napoleon'])
                    | {t for d in defs.values() for t in d.get('empire', {}).get('tags', {}) if t in d.get('napoleon', {}).get('tags', {})})
    exe_names = {'probe': {n: {g: name_counts(games[g]['exe'], n) for g in ('empire', 'napoleon')} for n in probe},
                 'controls': {n: {g: name_counts(games[g]['exe'], n) for g in ('empire', 'napoleon')} for n in common}}
    found = lambda d, g: sum(1 for v in d.values() if v[g]['ascii'] or v[g]['utf16'])
    exe_sum = {'probe_names': len(probe), 'probe_in_empire': found(exe_names['probe'], 'empire'),
               'probe_in_napoleon': found(exe_names['probe'], 'napoleon'), 'control_names': len(common),
               'control_in_empire': found(exe_names['controls'], 'empire'), 'control_in_napoleon': found(exe_names['controls'], 'napoleon')}

    # db
    db, rowsets = {}, {}
    for t in SCHEMA_TABLES:
        for g in ('empire', 'napoleon'):
            s, r = read_table(everything[g], games[g]['fs'], t, games[g]['schema'].get(t + '_tables', []))
            db.setdefault(t, {})[g] = s
            rowsets[(g, t)] = r
    for t in TABLES:
        er, nr = rowsets[('empire', t)], rowsets[('napoleon', t)]
        if er is not None and nr is not None:
            db[t]['keys'] = diff_rows(er, nr, db[t]['napoleon']['fields'], db[t]['empire']['fields'])
        else:
            hs = lambda g: [f.get('sha256') for f in db[t][g].get('files', [])]
            db[t]['keys'] = {'not_compared': 'a side did not decode; file hashes ' + ('identical' if hs('empire') == hs('napoleon') else 'differ')}
    db['projectiles'].pop('keys', None)

    # smoke
    def linked(g):
        out = collections.defaultdict(set)
        for t, fl in refs_by_table.items():
            rs = rowsets.get((g, t))
            for r in (rs or {}).values():
                for f in fl:
                    if r.get(f):
                        out[r[f]].add(f'{t}.{f}')
        return out
    n_link, e_link = linked('napoleon'), linked('empire')
    pe = db['particle_effects'].get('keys', {})
    pe_status = {k: s for s in ('identical', 'changed', 'new', 'gone') for k in pe.get(s, [])}

    def join(name, g='napoleon'):
        hits = []
        for p in sorted(set(infos[g]) | set(groups[g])):
            for tag, d, diff in ((GROUP, groups[g].get(p, {}), defs[p].get('groups', {})), (INFO, infos[g].get(p, {}), defs[p].get('infos', {}))):
                exact = name in d
                ci = None if exact else next((x for x in d if x.lower() == name.lower()), None)
                if exact or ci:
                    nm = name if exact else ci
                    miss = (group_lacking if tag == GROUP else lacking).get(p, {}).get(nm, [])
                    h = {'file': p, 'tag': tag, 'how': 'exact' if exact else 'case-insensitive', 'name': nm,
                         'verdict': diff.get(nm, {}).get('status', 'napoleon only file'), 'lacking_in_empire': sorted(set(miss))}
                    if h['verdict'] == 'changed':
                        h['add_only'] = diff[nm]['add_only']
                    if tag == GROUP:
                        ents = sorted({v for k, v in d[nm].items() if k.endswith('.effect')})
                        idiff = defs[p].get('infos', {})
                        h['entry_infos'] = dict(sorted(collections.Counter(
                            idiff.get(e, {}).get('status', 'no such info') + ('_add_only' if idiff.get(e, {}).get('add_only') else '')
                            for e in ents).items()))
                    hits.append(h)
        return hits
    primary = {k: {'from': sorted(v), 'particle_effects': pe_status.get(k, 'not a particle_effects key'),
                   'empire_rows_point_at_it': k in e_link, 'definitions': join(k)} for k, v in sorted(n_link.items())}
    how = collections.Counter()
    for v in primary.values():
        how[(v['definitions'][0]['tag'] + ' ' + v['definitions'][0]['how']) if v['definitions'] else 'no definition'] += 1
    secondary = {}
    for p in sorted(set(defs)):
        for tag, side in ((INFO, 'infos'), (GROUP, 'groups')):
            names = set((infos if tag == INFO else groups)['napoleon'].get(p, {})) | set((infos if tag == INFO else groups)['empire'].get(p, {}))
            for nm in sorted(n for n in names if SMOKE_RX.search(n)):
                st = defs[p].get(side, {}).get(nm, {}).get('status', 'napoleon only file' if 'empire' not in defs[p] else 'gone')
                miss = (group_lacking if tag == GROUP else lacking).get(p, {}).get(nm, [])
                secondary.setdefault(p, {}).setdefault(side, {})[nm] = {'verdict': st, 'lacking_in_empire': sorted(set(miss))}
    smoke = {'primary_rule': 'the particle_effects keys that Napoleon projectiles, projectiles_explosions and projectile_trails rows point at '
                             '(fields whose ref is particle_effects in discovery/db/tables.json), joined to XML info and group names',
             'ref_fields': refs_by_table, 'primary': primary, 'primary_join': dict(sorted(how.items())),
             'secondary_rule': f'info and group names matching the regex {SMOKE_RX.pattern!r} (case-insensitive)', 'secondary': secondary}

    rows = make_rows(files, defs, texts, refs, lacking, fmt_all, exe_sum, db, primary, how)
    tex = collections.Counter(f['status'] for p, f in files.items() if kind(p) in ('dds', 'tga'))
    detail = {'files': files, 'empire_shadowed': shadow['empire'], 'napoleon_shadowed': shadow['napoleon'],
              'empire_loose_skipped': loose['empire'], 'napoleon_loose_skipped': loose['napoleon'],
              'file_counts': {g: dict(sorted(collections.Counter(kind(p) for p in effx[g]).items())) for g in effx},
              'texture_counts': {s: tex[s] for s in ('identical', 'changed', 'new', 'gone')},
              'definitions': defs, 'text_files': texts, 'format': fmt_all,
              'references': {'refs': refs, 'lacking_by_info': lacking, 'lacking_by_group': group_lacking},
              'exe_names': {**exe_names, 'summary': exe_sum,
                            'method': 'substring counts of the name as ASCII and UTF-16LE in the whole exe file; _exact = NUL on both sides'},
              'db': db, 'smoke': smoke}
    return rows, detail


def _cnt(c):
    s = f"same {c['identical']}, changed {c['changed']}"
    if c['changed']:
        s += f" ({c['changed_add_only']} only add attributes)"
    return s + f", new {c['new']}, gone {c['gone']}"


def make_rows(files, defs, texts, refs, lacking, fmt, exe_sum, db, primary, how):
    rows = []
    for p, d in defs.items():
        st = files[p]['status']
        if 'infos' in d:
            n = f"infos {_cnt(d['info_counts'])}; groups {_cnt(d['group_counts'])}"
            e = f"{d['empire']['tags'].get(INFO, 0)} infos, {d['empire']['tags'].get(GROUP, 0)} groups"
        else:
            n, e = ('-', 'yes') if st == 'gone' else ('new file', '-')
        rows.append(row(f'effects {os.path.basename(p)}', e, n, VERDICT[st],
                        '' if st == 'identical' else 'per-name verdicts and changed attribute names in detail.definitions', 'detail.definitions'))
    for p, t in texts.items():
        st = files[p]['status']
        n = t.get('napoleon', {})
        rows.append(row(f'effects {os.path.basename(p)}', '-' if 'empire' not in t else 'yes',
                        f"{n.get('header', '')}, {n.get('records', 0)} records" if n else '-', VERDICT[st], n.get('format', ''), 'detail.text_files'))
    tc = collections.Counter(f['status'] for p, f in files.items() if kind(p) in ('dds', 'tga'))
    rows.append(row('effects textures', f"{tc['identical'] + tc['changed'] + tc['gone']} files",
                    f"same {tc['identical']}, changed {tc['changed']}, new {tc['new']}, gone {tc['gone']}",
                    'adapter' if tc['changed'] or tc['new'] or tc['gone'] else 'same', 'new textures ship in a pack', 'detail.files'))
    rows.append(row('effects definition format', 'EFFECTS_MANAGER XML',
                    f"new tags: {', '.join(fmt['tags_new']) or '-'}; {len(fmt['attr_names_new_to_empire'])} new attribute names; "
                    f"gone: {len(fmt['tags_gone'])} tags, {len(fmt['attr_names_gone'])} attribute names",
                    'new' if fmt['tags_new'] or fmt['attr_names_new_to_empire'] else 'same', 'names in detail.format', 'detail.format'))
    miss = sorted(r for r, v in refs.items() if v['empire'] in ('missing', 'unknown'))
    both = sum(1 for v in refs.values() if v['empire'] == 'absent_in_both')
    n_inf = sum(len(v) for v in lacking.values())
    rows.append(row('effects references Empire lacks', '-', f"{len(miss)} of {len(refs)}: {', '.join(os.path.basename(m) for m in miss)}"
                    if miss else f'0 of {len(refs)}', 'new' if miss else 'same',
                    f'{n_inf} Napoleon infos reference one; {both} more are absent in both games', 'detail.references'))
    rows.append(row('effects names in the exes', f"new names: {exe_sum['probe_in_empire']} of {exe_sum['probe_names']}; "
                    f"controls {exe_sum['control_in_empire']} of {exe_sum['control_names']}",
                    f"new names: {exe_sum['probe_in_napoleon']} of {exe_sum['probe_names']}",
                    'new' if exe_sum['probe_in_empire'] < exe_sum['probe_names'] else 'same',
                    'Empire.exe has no string for a name it lacks; whether it ignores the attribute is a runtime question', 'detail.exe_names'))
    for t in TABLES:
        d = db[t]
        side = lambda g: (f"v{d[g]['files'][0]['version']}, {d[g]['rows']} rows" if d[g].get('decoded') else
                          ('absent' if d[g].get('status') == 'absent' else 'not decoded'))
        k = d['keys']
        if 'not_compared' in k:
            rows.append(row(f'db {t}', side('empire'), side('napoleon'), 'adapter', k['not_compared'], 'detail.db'))
            continue
        same = not (k['changed'] or k['new'] or k['gone'] or k['fields_new'] or k['fields_gone'])
        note = f"keys same {len(k['identical'])}, changed {len(k['changed'])}, new {len(k['new'])}, gone {len(k['gone'])}"
        if k['fields_new'] or k['fields_gone']:
            note += f"; fields new {', '.join(k['fields_new']) or '-'}, gone {', '.join(k['fields_gone']) or '-'}"
        rows.append(row(f'db {t}', side('empire'), side('napoleon'), 'same' if same else 'adapter', note, 'detail.db'))
    ok = sum(1 for v in primary.values() if v['definitions'])
    rows.append(row('effects smoke subset (db-linked)', '-', f"{len(primary)} particle_effects keys, {ok} join an XML name",
                    'adapter', '; '.join(f'{k}: {v}' for k, v in sorted(how.items())), 'detail.smoke'))
    return rows


# ---- inputs and main ---------------------------------------------------------------------------------------------------

def trim_schema(src, out=EMPIRE_SCHEMA):
    b = open(src, 'rb').read()
    d = json.loads(b)
    doc = {'note': 'Trimmed by discovery/core/effects.py --trim-schema from empire-remastered rml_mod/tools/db/schema_emp.json '
                   '(RPFM schema_emp.ron converted there): only the tables the effects pass reads, every version, unchanged.',
           'source': {'line': d['source'], 'file': 'empire-remastered/rml_mod/tools/db/schema_emp.json', 'file_sha256': sha(b)},
           'tables': {t + '_tables': d['tables'][t + '_tables'] for t in SCHEMA_TABLES}}
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f'{out}: {len(doc["tables"])} tables from {src} ({doc["source"]["line"]})')
    return 0


def load_inputs(games_path):
    g = json.load(open(games_path, encoding='utf-8'))
    _, nap = load_schema()
    emp = json.load(open(EMPIRE_SCHEMA, encoding='utf-8'))['tables']
    out = {}
    for name, schema in (('empire', emp), ('napoleon', nap or {})):
        x = g[name]
        out[name] = {'fs': PackFS.from_games(g, name), 'exe': open(os.path.join(x['root'], x['exe']), 'rb').read(), 'schema': schema}
    shaders = json.load(open(SHADERS, encoding='utf-8'))['detail']['files']
    refs = particle_refs(json.load(open(DB_TABLES, encoding='utf-8')))
    return out, shaders, refs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--games', default=GAMES)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--check', action='store_true', help='rebuild in memory and compare with --out (rows and detail); exit 1 if it differs')
    ap.add_argument('--trim-schema', metavar='SCHEMA_EMP_JSON', help='write discovery/napoleon/empire_db_schema_effects.json from this file and stop')
    a = ap.parse_args(argv)
    if a.trim_schema:
        return trim_schema(a.trim_schema)
    rows, detail = build(*load_inputs(a.games))
    text = dumps('effects', rows, detail)
    if a.check:
        old = open(a.out, encoding='utf-8').read() if os.path.exists(a.out) else ''
        same = old == text
        print(f'effects --check: {"ok" if same else "DIFFERS"} - {len(rows)} rows, {len(detail["files"])} effects paths')
        return 0 if same else 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print(f'{a.out}: {len(rows)} rows, {len(detail["files"])} effects paths')
    return 0


if __name__ == '__main__':
    sys.exit(main())
