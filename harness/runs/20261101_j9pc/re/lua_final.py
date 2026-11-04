"""Build lua_cfuncs.json and lua_cfuncs.md from lua_scan_raw.json (py/lua_scan.py) and lua_vanilla_counts.json (py/lua_vanilla_counts.py)."""
import json, os, collections, re
HERE = r'C:\napoleon_remastered_pc\_scratch\J9\re'
TMP = os.environ.get('LUA_TMP', HERE)   # intermediates (lua_scan_raw.json, lua_vanilla_*.json) live outside the deliverable folder
raw = json.load(open(os.path.join(TMP, 'lua_scan_raw.json')))
van = json.load(open(os.path.join(TMP, 'lua_vanilla_counts.json')))['drift']

RENAME = {'table@0x13f1a38': 'Component'}
# by-hand reads (disassembly walked 2026-11-01), replace the automatic value
OVERRIDE = {
    ('Component', 'CreateFromLayout'): (7, 3, 'by hand: reads from the top, each optional slot type-checked: [dict table '
                                        '(lua_next walk, then lua_remove)], [array table], [number, number], then pointer, '
                                        'string, string; 3..7 args'),
    ('FrontEnd', 'StartBattle'): (5, 4, 'by hand: lua_gettop()==5 -> extra bool; bool; prefs table (0x455f00); players table '
                                  '(0x10558b0 open); setup pointer (0x44d320); 4 or 5 args'),
    ('ChatManager', '__call'): (3, 3, 'by hand: constructor thunk 0xdb5940 removes the class table, ctor 0xdb47c0 reads bool '
                                '(0x1055840), pointer, pointer (0x44d320 x2); the extra via 0xdb6780 in the full walk is a '
                                'false positive'),
    ('UIComponent', 'LuaCall'): (None, 1, 'by hand: reads the script function name at index 1, then forwards the remaining '
                                 'arguments to the component\'s script function (variadic)'),
}


def decide(tname, e):
    key = (tname, e['name'])
    if e.get('n_insn', 99) <= 4 and not e['ops'] and not e['idx_max'] and e['reads_max'] == 0 and e['strict_max'] == 0:
        return 0, 0, 'stub', 'tiny function or tail thunk (%d insns) that reads no Lua argument (tail target walked); extra arguments are ignored' % e['n_insn']
    if key in OVERRIDE:
        mx, mn, ev = OVERRIDE[key]
        return mx, mn, 'manual', ev
    fl = e.get('strict_flags', [])
    if 'forwards_args' in fl:
        return None, None, 'null', 'variadic: forwards its arguments to a Lua call (lua_pcall/lua_call with a computed count)'
    if 'var_index_read_in_loop' in fl and not e['ops']:
        return None, None, 'null', 'variadic: reads stack slots by a computed index inside a loop'
    if e['loop'] or e['strict_loop']:
        return None, None, 'null', 'reader call inside a loop (variadic or table walk); full walk max %s' % e['reads_max']
    if any(n.startswith('reader_fetching') for n in e['strict_notes']):
        ev0 = 'includes reads in callee(s) that fetch the argument stream themselves: ' + ','.join(
            n for n in e['strict_notes'] if n.startswith('reader_fetching'))
    else:
        ev0 = ''
    if e['reads_max'] != e['strict_max']:
        ev0 = (ev0 + '; ' if ev0 else '') + 'full walk (all callees) says %s, discounted: %s' % (
            e['reads_max'], ','.join(n for n in e['strict_notes'] if n.startswith('via_skipped')) or 'nested callee pops')
    mx, mn = e['strict_max'], e['strict_min']
    if e['idx_max'] > mx and not e['ops']:
        return e['idx_max'], e['idx_max'], 'index', 'constant stack index %d (lua_to*/luaL_check* style)' % e['idx_max']
    return mx, mn, 'auto', ev0


def evidence(e, how, ev):
    parts = []
    if ev:
        parts.append(ev)
    if e['ops']:
        c = collections.Counter(e['ops'])
        parts.append('reader calls: ' + ', '.join('%s x%d' % (k, n) if n > 1 else k for k, n in c.items()))
    if e['idx_max']:
        parts.append('direct index read %d' % e['idx_max'])
    fl = [n for n in e['notes'] if n in ('peeks_top_type', 'icall', 'truncated')]
    if fl:
        parts.append('flags: ' + ','.join(fl))
    return '; '.join(parts)


tables = collections.OrderedDict()
counts = {}
for tname, t in raw['tables'].items():
    tn = RENAME.get(tname, tname)
    ents = []
    for e in t['entries']:
        mx, mn, how, ev = decide(tn, e)
        ents.append(dict(name=e['name'], va=e['va'], static_args=mx, static_args_min=mn, checks_gettop=bool(e['gettop']),
                         peeks_top_type='peeks_top_type' in e['notes'], basis=how, evidence=evidence(e, how, ev),
                         **({'doc': e['doc']} if e.get('doc') else {})))
    tables[tn] = dict(table_va=t.get('table_va'), kind=('luaL_Reg (own registration loop at 0x1027200)' if tn == 'Component' else t.get('kind')), **({'registrar': t['registrar']} if t.get('registrar') else {}),
                      **({'thunk': t['thunk']} if t.get('thunk') else {}), entries=ents)
    counts[tn] = (len(ents), sum(1 for x in ents if x['static_args'] is not None))

# ------------------------------------------------------------------ validation against every vanilla call site
VAN_ALL = json.load(open(os.path.join(TMP, 'lua_vanilla_all.json')))


def site_counts(sigs):
    for sg, n in sigs.items():
        if '...' not in sg:
            yield (0 if sg == '()' else sg.count(',') + 1), n


def vrange(e):
    lo = e['static_args_min'] if (e['checks_gettop'] or e['peeks_top_type']) and e['static_args_min'] is not None else e['static_args']
    return min(lo, e['static_args']), e['static_args']


lunar_names = collections.defaultdict(list)
for tn, t in tables.items():
    if t['kind'] and 'lunar' in t['kind']:
        for e in t['entries']:
            lunar_names[e['name']].append(tn)
VALID = dict(sites_ok=0, sites_outside=0, contradicted=[], minority=[])
for tn, t in tables.items():
    for e in t['entries']:
        if e['static_args'] is None or e['basis'] in ('manual', 'stub'):
            continue
        if tn in ('CampaignUI', 'BattleUI', 'FrontEnd', 'Component', 'DirectoryUtils', 'Localisation', 'UniChar'):
            v = VAN_ALL['calls'].get('%s.%s' % (tn, e['name']))
        elif e['name'] in lunar_names and len(lunar_names[e['name']]) == 1:
            v = VAN_ALL['methods'].get(e['name'])
        else:
            v = None
        if not v:
            continue
        lo, hi = vrange(e)
        okn = badn = 0; outside = collections.Counter()
        for c, n in site_counts(v['sigs']):
            if lo <= c <= hi:
                okn += n
            else:
                badn += n; outside[c] += n
        VALID['sites_ok'] += okn; VALID['sites_outside'] += badn
        if not badn:
            continue
        row = dict(binding='%s.%s' % (tn, e['name']), va=e['va'], static=[lo, hi], vanilla_outside=dict(outside), vanilla_inside=okn)
        if badn >= okn:
            VALID['contradicted'].append(row)
            e['evidence'] = 'static walk said %s..%s but %d of %d vanilla call sites pass %s: count withheld; %s' % (
                lo, hi, badn, badn + okn, sorted(outside), e['evidence'])
            e['static_args'] = None; e['static_args_min'] = None; e['basis'] = 'null'
        else:
            VALID['minority'].append(row)
            e['evidence'] += '; vanilla call sites outside the range: %s (of %d)' % (dict(outside), badn + okn)
counts = {tn: (len(t['entries']), sum(1 for x in t['entries'] if x['static_args'] is not None)) for tn, t in tables.items()}

# ------------------------------------------------------------------ J6 drift
def sigcounts(sigs):
    if not sigs:
        return {}
    out = collections.Counter()
    for s, n in sigs.items():
        if s == '()':
            out['0'] += n
        elif '...' in s:
            k = s.count(',')
            out['%d+...' % k if k else '...'] += n
        else:
            out[str(s.count(',') + 1)] += n
    return dict(sorted(out.items()))


def find(tn, name):
    for e in tables.get(tn, {}).get('entries', []):
        if e['name'] == name:
            return e
    return None


ENGINE = {
    'calls:CampaignUI.InitialiseUnitDetails': ('CampaignUI', 'InitialiseUnitDetails'),
    'calls:CampaignUI.PromoteUnits': ('CampaignUI', 'PromoteUnits'),
    'calls:CampaignUI.TheatreList': ('CampaignUI', 'TheatreList'),
    'calls:ChatManager': ('ChatManager', '__call'),
    'calls:Component.CreateFromLayout': ('Component', 'CreateFromLayout'),
    'calls:FrontEnd.CampaignDetails': ('FrontEnd', 'CampaignDetails'),
    'calls:FrontEnd.GenerateRegionOwnershipMaps': ('FrontEnd', 'GenerateRegionOwnershipMaps'),
    'calls:FrontEnd.MPHostCampaign': ('FrontEnd', 'MPHostCampaign'),
    'calls:FrontEnd.MPQuickBattleStart': ('FrontEnd', 'MPQuickBattleStart'),
    'calls:FrontEnd.RecruitableUnits': ('FrontEnd', 'RecruitableUnits'),
    'calls:FrontEnd.StartBattle': ('FrontEnd', 'StartBattle'),
    'calls:out.tom': ('out', 'tom'),
    'methods:AddAiBot': ('UIMPInterface', 'AddAiBot'),
    'methods:JoinTeam': ('UIMPInterface', 'JoinTeam'),
    'methods:LuaCall': ('UIComponent', 'LuaCall'),
    'methods:SetImageRotation': ('UIComponent', 'SetImageRotation'),
}
VERDICT = {
    'calls:CampaignUI.InitialiseUnitDetails': 'real engine change: when lua_gettop()>1 it first reads four trailing strings (a nil is popped instead), then the unit pointer or id string, so 1 or 5 args; Napoleon vanilla uses 1 and 5, Empire used 1 and 4',
    'calls:CampaignUI.PromoteUnits': 'real engine change: reads two pointers (commander/force); Napoleon vanilla passes 2, Empire passed one table',
    'calls:CampaignUI.TheatreList': 'not a real difference: optional bool (read only if the top is a boolean); () and (bool) both fit',
    'calls:ChatManager': 'real engine change: the ChatManager constructor reads 3 (bool, pointer, pointer); Napoleon vanilla passes 3, Empire passed 2',
    'calls:Component.CreateFromLayout': 'not a real difference: 3 required + type-checked optional trailing (2 numbers, array table, dict table); every Napoleon and Empire shape fits 3..7 (the 1-arg rows are open f(...) calls)',
    'calls:FrontEnd.CampaignDetails': 'real engine change: reads key and a bool; Napoleon vanilla passes 2, Empire passed 1',
    'calls:FrontEnd.GenerateRegionOwnershipMaps': 'real engine change: 3..5 by lua_gettop (5th = int, 4th = optional second faction); Napoleon vanilla uses 3 and 5, Empire used 2 and 3',
    'calls:FrontEnd.MPHostCampaign': 'real engine change: fixed 5; Napoleon vanilla passes 5, Empire passed 4',
    'calls:FrontEnd.MPQuickBattleStart': 'real engine change: fixed 4 bools; Napoleon vanilla passes 4, Empire passed 1 (the exe doc string still describes one bool)',
    'calls:FrontEnd.RecruitableUnits': 'real engine change: fixed 7 (doc string lists 4); Napoleon vanilla passes 7, Empire passed 5',
    'calls:FrontEnd.StartBattle': 'real engine change: 4 or 5 (lua_gettop()==5 adds a bool); Napoleon vanilla uses 4 and 5, Empire used 3',
    'calls:out.tom': 'not a real difference: out.* (shane, dylan, tom, kostas, ting, design) all point at one stub 0x461180 that reads nothing',
    'methods:AddAiBot': 'real engine change: reads 2 (string + number); Napoleon vanilla passes 2 (one open call), Empire passed 1',
    'methods:JoinTeam': 'real engine change: reads 2 numbers; Napoleon vanilla passes 2, Empire passed 1',
    'methods:LuaCall': 'not a real difference: variadic forwarder (name at index 1, the rest passed to the script function); counts are per call site',
    'methods:SetImageRotation': 'not a real difference: 2 or 4 by lua_gettop()>2; both games use 2 and 4 (the Napoleon 1-arg row is an open f(...) call)',
}
drift = []
for k, v in van.items():
    nc = sigcounts(v['napoleon_sigs']); ec = sigcounts(v['empire_sigs'])
    if k in ENGINE:
        tn, nm = ENGINE[k]; e = find(tn, nm)
        drift.append(dict(name=k, binding='%s.%s' % (tn, nm), va=e['va'] if e else None,
                          static_args=e['static_args'] if e else None, static_args_min=e['static_args_min'] if e else None,
                          checks_gettop=e['checks_gettop'] if e else None, vanilla_counts=nc, empire_counts=ec, verdict=VERDICT[k]))
    else:
        nd = v.get('nap_defined_in') or []
        drift.append(dict(name=k, binding=None, va=None, static_args=None, vanilla_counts=nc, empire_counts=ec,
                          verdict='not an engine function: a Lua global defined in vanilla scripts (%s); the drift is a script-side signature change, no exe count applies' % (
                              ', '.join(x.split('/')[-1] for x in nd[:3]) + (' +%d' % (len(nd) - 3) if len(nd) > 3 else ''))))

out = dict(exe=dict(path=r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe',
                    sha1='9aebcd2172f2878d781b079f7feb45b0e12e0250', image_base='0x400000'),
           generated_by=r'C:\napoleon_remastered_pc\_scratch\J9\re\py\lua_scan.py + lua_final.py (static, 2026-11-01)',
           lua_core=raw['lua_core'], tables=tables, j6_arg_drift=drift, validation=VALID)
json.dump(out, open(os.path.join(HERE, 'lua_cfuncs.json'), 'w'), indent=1)
for tn, (n, k) in counts.items():
    print('%-28s %4d entries, %4d with a static count' % (tn, n, k))
print(sum(n for n, k in counts.values()), sum(k for n, k in counts.values()))
