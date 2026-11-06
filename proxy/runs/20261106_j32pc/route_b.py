#!/usr/bin/env python3
"""J32 S4 route B, offline: for the representative screens, which engine calls do the vanilla scripts make, and are they in the Lua API of that state?

usage: python3 proxy/runs/20261106_j32pc/route_b.py   (prints a table, writes route_b.json beside this file)
Reads discovery/ui/units.json.gz, discovery/napoleon/engine_api.json and registries/ui_elements.jsonl. A call is `ui` (the component tree, which a rebuilt screen does not need),
`read` or `act` by its name, and `missing` when the API of the screen's state does not list it.
"""
import gzip
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCREENS = {'panel': ('campaign.entity_lists', 'campaign_show_lists'), 'popup': ('common.unit_information', 'campaign'), 'popup_event': ('campaign.event_message', 'campaign'),
           'hud': ('battle.land_battle_orders', 'land'), 'front_end': ('frontend.single_player', 'frontend')}
READ = re.compile(r'^(Retrieve|Get|Is|Has|Can|Player|Current|Faction|Unit|Squad|Number|Num|Count|List|Query|Full|Initialise|Battle|Selected|Character|Region|Army)')
ACT = re.compile(r'^(Select|Set|Toggle|Start|Stop|Do|Move|Cancel|Show|Hide|Open|Close|Send|Enable|Disable|Add|Remove|Halt|Column|Single|Double|Triple|Crescent|Current_Selection)')


def main():
    units = json.load(gzip.open(ROOT / 'discovery/ui/units.json.gz'))
    units = units.get('units', units)
    api = json.loads((ROOT / 'discovery/napoleon/engine_api.json').read_text(encoding='utf-8'))
    rows = {}
    for line in (ROOT / 'registries/ui_elements.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r['id']] = r
    out = {}
    for kind, (uid, state) in SCREENS.items():
        u = units.get(uid)
        if u is None:
            out[kind] = {'unit': uid, 'absent': True}
            continue
        have = {f"{n['owner'][2:]}.{n['name']}" for n in api['names'] if state in n.get('states', []) and n['owner'].startswith('G.')}
        calls = Counter()
        lists = {'ui': [], 'read': [], 'act': [], 'other': [], 'missing': []}
        for name, n in u['engine_calls'].items():
            owner, _, short = name.partition('.')
            if owner in ('Component', 'UIComponent'):
                lists['ui'].append(name)
                continue
            k = 'act' if ACT.match(short) and not short.startswith('Current_Selection_Is') else 'read' if READ.match(short) else 'other'
            lists[k].append(name)
            if name not in have:
                lists['missing'].append(name)
        un = Counter(x['kind'] for x in u.get('unresolved', []))
        row = rows.get(uid, {})
        src = Counter((f.get('source') or '?').split(':')[0] for f in row.get('data_fields', []))
        ints = u.get('interactions', [])
        out[kind] = {'unit': uid, 'state': state, **{k: sorted(v) for k, v in lists.items()}, 'unresolved': dict(un), 'field_sources': dict(src), 'interactions': len(ints),
                     'interactions_engine': sum(1 for i in ints if '->' in i and re.search(r'(CampaignUI|BattleUI|FrontEnd)\.', i)),
                     'interactions_lua_only': sum(1 for i in ints if not re.search(r'(CampaignUI|BattleUI|FrontEnd)\.', i))}
        o = out[kind]
        print(f"{kind:12} {uid:32} ui {len(o['ui']):3} read {len(o['read']):3} act {len(o['act']):3} other {len(o['other']):3} missing {len(o['missing']):3} interactions {o['interactions']:3} "
              f"(engine {o['interactions_engine']}) fields {dict(src)} unresolved {dict(un)}")
        if o['missing']:
            print('   missing', o['missing'][:10])
        if o['other']:
            print('   other', o['other'][:12])
    (HERE / 'route_b.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
