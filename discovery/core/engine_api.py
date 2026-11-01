#!/usr/bin/env python3
"""Build the engine Lua API surface table from the api_surface.lua probe lines of a run, and check it against J6's static diff.

purpose: read the "api <state> <owner> <name>:<type> ..." lines that proxy/<game>/lua/probes/api_surface.lua logs (in the run's committed proxy logs), merge them per name (owner, kind, the states where it exists, observed type) merge the static binding map discovery/napoleon/lua_cfuncs.json (address and argument counts per C function) and answer the open questions of J6's static Lua API diff (discovery/diff/lua_api.json: are its new and gone names there at runtime, which argument-count drifts are real); writes discovery/napoleon/engine_api.json
usage: python3 discovery/core/engine_api.py build --run harness/runs/<id> [--out discovery/napoleon/engine_api.json] [--check]
when: after a PC run of the api_surface probe (J9; again after a game update); --check in review rebuilds the table from the committed logs
not-a-verb: a discovery pass over committed run evidence, writing one discovery table; outside the wsc registry operations

Owners: `S` = the pumping script's own environment, `G` = the globals it falls back to (its metatable __index chain and _G: the engine
tables live there); `G.<table>` / `S.<table>` = one level into a table (CampaignUI, BattleUI, FrontEnd, ...); `<owner>#mt` and
`<owner>#index` = a table's or userdata's metatable and its __index table; `R.<key>` = a string-keyed table of the Lua registry (Lunar classes and their
method tables, no object needed). Kind: `event` for an On* name, `method` for a registry class entry, `function` for a function in a
global table, `global` otherwise. The probe calls nothing, so C and Lua functions are not told apart and there are no samples.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(REPO, 'discovery', 'napoleon', 'engine_api.json')
DIFF = os.path.join(REPO, 'discovery', 'diff', 'lua_api.json')
CFUNCS = os.path.join(REPO, 'discovery', 'napoleon', 'lua_cfuncs.json')   # J9 static RE: binding addresses and argument counts
LINE = re.compile(r'\] lua: api (\S+) (\S+) (.*)$')
END = re.compile(r'\] lua: api (\S+) __end total=(\d+)')
# names the static diff caught from a non-game (build-system) script; they are not engine API
BUILD_SYSTEM = {'buildcommands', 'project', 'solution', 'configuration', 'configurations', 'files', 'includedirs', 'links', 'kind',
                'language', 'location', 'targetdir', 'objdir', 'defines', 'flags', 'buildoptions', 'linkoptions', 'libdirs'}


def parse_logs(paths):
    """{state: {owner: {name: type}}}, {state: probe total}, [dropped blocks]. A probe run is one block of lines ended by its __end line;
    when a state has several blocks (a stale request from a killed client can run in the next launch, in another context: J9 chain 4),
    only the last complete block counts and the others are listed as dropped"""
    blocks = {}
    for p in sorted(paths):
        cur = {}
        with open(p, encoding='utf-8', errors='replace') as f:
            for line in f:
                m = END.search(line)
                if m:
                    state = m.group(1)
                    blocks.setdefault(state.split('@')[0], []).append((state, os.path.basename(p), int(m.group(2)), cur.pop(state, {})))
                    continue
                m = LINE.search(line)
                if not m:
                    continue
                state, owner, rest = m.groups()
                d = cur.setdefault(state, {}).setdefault(owner, {})
                for item in rest.split(' '):
                    name, _, typ = item.rpartition(':')
                    if name:
                        d[name] = typ
    seen, totals, dropped = {}, {}, []
    for state, bl in blocks.items():
        for label, log, total, owners in bl[:-1]:
            dropped.append({'state': label, 'log': log, 'probe_total': total})
        label, log, total, owners = bl[-1]
        seen[state], totals[state] = owners, total
    return seen, totals, dropped


def kind(owner, name, typ):
    if name.startswith('On') and name[2:3].isupper():
        return 'event'
    if owner.startswith('R.'):
        return 'method' if typ == 'function' else 'field'
    if owner[:2] in ('G.', 'S.') and typ == 'function':
        return 'function'
    return 'global'


def merge(seen):
    names = {}
    for state, owners in seen.items():
        for owner, d in owners.items():
            for name, typ in d.items():
                key = f'{owner}:{name}'
                e = names.setdefault(key, {'owner': owner, 'name': name, 'kind': kind(owner, name, typ), 'types': {}, 'states': []})
                e['types'][state] = typ
                if state not in e['states']:
                    e['states'].append(state)
    for e in names.values():
        e['states'].sort()
        types = set(e['types'].values())
        e['type'] = types.pop() if len(types) == 1 else 'varies'
        if e['type'] != 'varies':
            del e['types']
    return names


def j6_answers(names, diff_path=DIFF):
    """J6's static names (new / gone against Empire) against the runtime surface: which exist in any probed state"""
    if not os.path.exists(diff_path):
        return {}
    with open(diff_path, encoding='utf-8') as f:
        d = json.load(f)['detail']['names']
    runtime = {}
    for e in names.values():
        if e['owner'][:2] in ('G.', 'S.') and '#' not in e['owner']:
            runtime.setdefault(f"{e['owner'][2:]}.{e['name']}", e['states'])
    methods = {e['name'] for e in names.values() if e['owner'].startswith('R.') or '#' in e['owner']}
    out = {}
    for group in ('CampaignUI.*', 'BattleUI.*', 'FrontEnd.*'):
        g = d.get(group, {})
        res = {}
        for status in ('new', 'gone'):
            want = sorted(n for n, s in g.items() if s == status)
            res[status] = {'static': len(want), 'at_runtime': [n for n in want if n in runtime],
                           'not_at_runtime': [n for n in want if n not in runtime]}
        out[group] = res
    comp = d.get('component methods', {})
    new_methods = sorted(n.split('.')[-1] for n, s in comp.items() if s == 'new')
    out['component methods'] = {'new_static': len(new_methods), 'found': [m for m in new_methods if m in methods],
                                'not_found': [m for m in new_methods if m not in methods]}
    out['build_system_names_dropped'] = sorted(BUILD_SYSTEM)
    return out


def add_cfuncs(names, path=CFUNCS):
    """merge the static binding map (address, argument counts read by the C function) into the runtime names; J6's drift verdicts out"""
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        cf = json.load(f)
    by = {(t, e['name']): e for t, v in cf.get('tables', {}).items() for e in v.get('entries', [])}
    for e in names.values():
        table = e['owner'].split('.', 1)[1].split('#')[0] if '.' in e['owner'] else None
        hit = by.get((table, e['name']))
        if hit:
            for k in ('va', 'static_args', 'static_args_min', 'checks_gettop'):
                if hit.get(k) is not None:
                    e[k] = hit[k]
    return cf.get('j6_arg_drift', [])


def build(run):
    logs = glob.glob(os.path.join(run, 'raw', '*_proxy.log'))
    seen, totals, dropped = parse_logs(logs)
    names = merge(seen)
    drift = add_cfuncs(names)
    rows = sorted(names.values(), key=lambda e: (e['owner'], e['name']))
    per_state = {s: {'names': sum(len(d) for d in o.values()), 'probe_total': totals.get(s),
                     'owners': len(o)} for s, o in sorted(seen.items())}
    return {'generator': 'discovery/core/engine_api.py', 'run': run.replace('\\', '/'),
            'logs': sorted(os.path.relpath(p, REPO).replace('\\', '/') for p in logs),
            'states': per_state, 'dropped_blocks': dropped, 'j6': j6_answers(names), 'j6_arg_drift': drift, 'names': rows}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--run', required=True)
    b.add_argument('--out', default=OUT)
    b.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    doc = build(os.path.relpath(os.path.abspath(a.run), REPO))
    text = json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=False) + '\n'
    summary = ', '.join(f"{s} {v['names']}" for s, v in doc['states'].items())
    if a.check:
        with open(a.out, encoding='utf-8') if os.path.exists(a.out) else open(os.devnull, encoding='utf-8') as f:
            same = f.read() == text
        print(f'engine_api --check: {"ok" if same else "DIFFERS"} - {summary}')
        return 0 if same else 1
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print(f'wrote {a.out}: {len(doc["names"])} names; {summary}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
