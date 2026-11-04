"""Write lua_cfuncs.md from lua_cfuncs.json (J9 UI-facing Lua C functions)."""
import json, os, collections
HERE = r'C:\napoleon_remastered_pc\_scratch\J9\re'
d = json.load(open(os.path.join(HERE, 'lua_cfuncs.json')))
T = d['tables']; V = d['validation']
L = []
w = L.append
w('# Napoleon.exe UI-facing Lua C functions: addresses and static argument counts (J9)')
w('')
w('Static read of `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, ImageBase 0x400000, 2026-11-01. Nothing was run, '
  'launched or edited. Machine-readable twin: `lua_cfuncs.json`. Regenerate (intermediates go to a temp folder `$LUA_TMP`): '
  '`<re venv python> -I py/lua_scan.py $LUA_TMP/lua_scan_raw.json`; from the napoleon-remastered checkout `python3 -I '
  'py/lua_vanilla_counts.py $LUA_TMP/lua_vanilla_counts.json` and `python3 -I py/lua_vanilla_all.py $LUA_TMP/lua_vanilla_all.json`; '
  'then `LUA_TMP=... python3 py/lua_final.py` and `python3 py/lua_md.py` (about 15 s in all). Every address is a candidate until '
  'an engine_sites row with anchor bytes is checked on the PC.')
w('')
w('## Method')
w('')
w('1. **Lua core.** I took masked byte signatures (relocated dwords and rel32 targets wildcarded) of Empire\'s known lapi/lauxlib '
  'functions (`empire-remastered/.../lua_api/lapi_map.py`) and searched Napoleon\'s .text: 39 of 39 hit uniquely. The whole block sits '
  'at Empire + 0xE1B70 and is linked in alphabetical order, so I named the other lapi/lauxlib functions from that order plus their '
  'callees (for example `lua_next` calls luaH_next, `lua_rawgeti` calls luaH_getnum, `lua_remove` follows `lua_rawseti`). `lua_core` '
  'in the JSON lists %d; the 39 signature hits are certain, the rest are named from layout and shape.' % len(d['lua_core']))
w('2. **Bindings.** CampaignUI / BattleUI / FrontEnd are static registrars: `push doc; push name; push func; mov ecx,<static>; '
  'call <registrar>` with registrar 0x998c50 = CampaignUI (339), 0x59eb40 = BattleUI (218), 0x4587a0 = FrontEnd (118), the same '
  'shape as Empire. The doc strings are copied into the JSON. Other tables: `luaL_Reg` arrays (Component at 0x13f1a38, filled by its '
  'own loop; UniChar, out, Keyboard via `luaL_register`); Lunar classes (8-byte {name, member fn}, 24-byte {name, 0, member '
  'pointer}, or 16-byte tables filled at start-up by `mov [entry+8], fn`), each named from the `luaL_typerror` class string in its '
  'dispatch thunk; Lunar constructors (the closure stored as both `new` and `__call`); stack-built arrays for DirectoryUtils and Localisation. '
  'I skipped the battle script classes (battle.unit etc., 0x1451400..0x1452000, ui_component, empire_battle), because another agent maps them. '
  'The Lunar thunk calls `lua_remove(L, 1)` before the method, so method counts exclude `self` and compare directly with J6\'s method signatures.')
w('3. **Argument model (important).** Engine bindings do not read `lua_to*(L, n)`. They fetch an argument stream with `0x1058750(L)` '
  'and read it with operator>> helpers. Each helper reads index **-1** and then pops it (`lua_settop(L,-2)`): 0x1055760 string, 0x1055840 bool, '
  '0x1055700 number (0x10556d0 = number to int), 0x44d320 / 0x10557e0 pointer, and 0x10558b0 opens a table on top. **Arguments are '
  'consumed from the last one backwards**. A binding that reads N values and is called with more than N reads the *trailing* '
  'arguments, which puts every value in the wrong slot, unless it branches on `lua_gettop` or on the type of the top value (both are '
  'flagged per entry). Called with fewer, it reads past the frame: the reader\'s type check fails and later reads are skipped.')
w('4. **Counting.** A reader op is a function that reads index -1 and pops without building a table. For each binding I walk its CFG '
  'once per acyclic path (back edges ignored) and track the Lua stack level: the counted value is the lowest level reached, so a '
  'getfield/read/pop field read nets 0. Callee contributions count only for wrappers of 80 instructions or fewer, or for callees '
  'that fetch the argument stream themselves. `static_args` is the maximum over paths. `static_args_min` is the minimum over paths '
  'that fetched the stream: a lower value there means optional arguments. It is **null** in these cases: a read sits inside a loop, '
  'the function forwards arguments with `lua_pcall` and a computed count, it reads by a computed index inside a loop, or most '
  'vanilla call sites disagree (see validation). Functions of four instructions or fewer that touch no argument are `stub` '
  '(count 0, extras ignored). Plain `lua_CFunction`s that read constant indices are reported as `index`.')
w('')
w('## Counts per table')
w('')
w('| table | kind | entries | with static count | null |')
w('|---|---|---:|---:|---:|')
tot = [0, 0]
for tn, t in T.items():
    n = len(t['entries']); k = sum(1 for e in t['entries'] if e['static_args'] is not None)
    tot[0] += n; tot[1] += k
    w('| %s | %s | %d | %d | %d |' % (tn, t['kind'], n, k, n - k))
w('| **total** | | **%d** | **%d** | **%d** |' % (tot[0], tot[1], tot[0] - tot[1]))
w('')
b = collections.Counter(e['basis'] for t in T.values() for e in t['entries'])
w('Basis: %s. "UIComponent" is the Lunar class behind `UIComponent(address)` objects (component methods). GAME is the campaign '
  'episodic-scripting class (not UI, included because it was met).' % ', '.join('%s %d' % kv for kv in b.most_common()))
w('')
w('## Validation against vanilla call sites')
w('')
w('I compared each static range [min if the binding checks gettop or the top type, else max .. max] with every non-open call site in '
  'Napoleon\'s vanilla `ui/*.luac`, using J6\'s inventory with open `f(...)` calls marked. For table functions the match is by '
  'Table.name; for methods, only by method names that are unique across the classes. **%d call sites fall inside the range and %d '
  'outside.** %d bindings had at least half of their call sites outside the range, so their count is withheld (null). Some are '
  'model misses: a value read through an indirect call, or a variadic reader such as `Component.CallByAddress`, `UIComponent:SequentialFind`, '
  '`UIComponent:SetGlobal` or `Component.SetProperty`. Others have one or two sites each and may be real script mistakes:'
  % (V['sites_ok'], V['sites_outside'], len(V['contradicted'])))
w('')
w('| binding | va | static range | vanilla counts outside | inside |')
w('|---|---|---|---|---:|')
for r in V['contradicted']:
    w('| %s | %s | %d..%d | %s | %d |' % (r['binding'], r['va'], r['static'][0], r['static'][1],
                                         ', '.join('%s x%d' % kv for kv in sorted(r['vanilla_outside'].items())), r['vanilla_inside']))
w('')
w('## J6\'s 38 argument-count drifts')
w('')
w('Vanilla counts were recomputed with J6\'s own inventory (`discovery/core/lua_api.py`). J6 recorded only the drift flag, not the '
  'counts. `...` means an open call (`f(x, g())` / `f(...)`), whose count cannot be known statically; J6 shows these as one `expr`. '
  'The Empire counts come from Empire\'s `engine_api.json`.')
w('')
w('| J6 name | binding (va) | static | gettop | Napoleon vanilla {count: sites} | Empire {count: sites} | verdict |')
w('|---|---|---|---|---|---|---|')
for r in d['j6_arg_drift']:
    if r['binding']:
        st = '-' if r['static_args'] is None and r['static_args_min'] is None else (
            'variadic' if r['static_args'] is None else ('%s' % r['static_args'] if r['static_args_min'] in (None, r['static_args'])
                                                         else '%s..%s' % (r['static_args_min'], r['static_args'])))
        w('| `%s` | %s (%s) | %s | %s | %s | %s | %s |' % (r['name'], r['binding'], r['va'], st, 'y' if r['checks_gettop'] else '',
                                                        r['vanilla_counts'], r['empire_counts'], r['verdict']))
for r in d['j6_arg_drift']:
    if not r['binding']:
        w('| `%s` | script global | - | | %s | %s | %s |' % (r['name'], r['vanilla_counts'], r['empire_counts'], r['verdict']))
w('')
w('**Summary:** 22 of the 38 are Lua functions defined in the vanilla scripts. The drift there is a script change, not an engine fact. '
  'Of the 16 engine functions, **11 are real engine signature changes** (Napoleon\'s exe reads what Napoleon\'s scripts pass): '
  'CampaignUI.InitialiseUnitDetails, CampaignUI.PromoteUnits, the ChatManager constructor, FrontEnd.CampaignDetails / GenerateRegionOwnershipMaps / '
  'MPHostCampaign / MPQuickBattleStart / RecruitableUnits / StartBattle, and UIMPInterface:AddAiBot / JoinTeam. Because of the '
  'last-argument-first stream, an Empire-shaped call to these reads the wrong slots. **5 are not real differences**: '
  'CampaignUI.TheatreList and SetImageRotation have optional arguments that both games\' counts fit; Component.CreateFromLayout has '
  'type-checked optional trailing arguments; LuaCall is a variadic forwarder; out.tom is a no-op stub. No vanilla Napoleon call to the 16 '
  'falls outside the exe\'s range.')
w('')
w('## Not found, and limits')
w('')
w('- **Script names the exe does not register.** These J6 table names are absent from Napoleon.exe\'s strings, so they are dead calls in vanilla scripts: '
  'CampaignUI CanDisembark, CanEmbark, EmbarkOrDisembark, ExecuteCaptives, HideBattleDetails, ImprisonCaptives, '
  'PreBattlePlayerSurrenderDecision; BattleUI CurrentSelectionBreakGroup/Group/Halt/Runs/Walks, Current_Selection_Start/Stop_Firing_At_Will, '
  'DestroyBattleChat, SelectUnitCard, Shot_Standard, UnitCardAddToGroup, UnitCardBeginsDrag, UnitCardGroupID, UnitCardUngroup, '
  'UnselectUnitCard; FrontEnd IsModifier, MPBaseInterface, MPHostLandBattle, MPHostNavalBattle, ModifierHeld, StartDefaultCampaign, '
  'StartDefaultFortBattle, StartDefaultLandBattle, StartDefaultSeaBattle. Component methods absent: IsVisible, SetPayRansom, BlockPlayerID, '
  'SetDetails, SetFromSetup, SyncProgress (close/read/seek/write are the io library\'s file methods).')
w('- **Model misses** (why some counts are null or withheld): reads through an indirect (virtual) call; values read with a computed index or '
  'with `lua_settop` to a computed level; table helpers above 80 instructions that do not fetch the stream themselves. The full walk, which '
  'counts all callees, is kept in `evidence` whenever it differs.')
w('- `lua_gettop` / top-type checks are flags, not proof of optional arguments. `static_args_min` is the path minimum and can include '
  'error paths.')
w('- Not in scope: battle script luaL_Reg tables and battle order functions (other J9 agent).')
w('- The runtime check would be the J9 api_surface probe: call each binding with N-1 / N / N+1 arguments on a scratch screen. Not done here (static only).')
open(os.path.join(HERE, 'lua_cfuncs.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(len(L), 'lines')
