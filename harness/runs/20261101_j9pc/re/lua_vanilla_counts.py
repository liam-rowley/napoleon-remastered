"""Recompute J6's per-call argument signatures for the 38 drift names (Napoleon vanilla ui/*.luac and Empire engine_api.json)."""
import json, os, sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import lua_api
from extracted import effective, load_games
import api_inventory
_orig = api_inventory.argshape
api_inventory.argshape = lambda e: '...' if e == ('vararg',) else _orig(e)   # B=0 call: open argument list (count unknown)
games = load_games(None)
ej = json.load(open(os.path.join(games['empire']['repo'], *lua_api.ENGINE_API.split('/')), encoding='utf-8'))
nap_files = effective(games, 'napoleon', exts={'.luac'}, under='ui' + lua_api.BACKSLASH)
nj, _, failed = lua_api.inventory(nap_files)
drift = json.load(open(r'C:\Users\liamr\repos\napoleon-remastered\discovery\diff\lua_api.json'))['detail']['names']['call argument counts (shared names)']
out = {}
for k in drift:
    kind, name = k.split(':', 1)
    n = nj[kind].get(name, {}); e = ej[kind].get(name, {})
    out[k] = {'napoleon_sigs': n.get('sigs'), 'napoleon_scripts': sorted(n.get('scripts', []))[:12],
              'empire_sigs': e.get('sigs'), 'napoleon_examples': (n.get('examples') or [])[:6], 'napoleon_receivers': n.get('receivers'),
              'nap_defined_in': sorted(nj['defined'].get(name, [])) if isinstance(nj['defined'], dict) else (name in nj['defined']), 'emp_defined': (name in ej['defined']), 'empire_scripts': sorted(e.get('scripts', []))[:6]}
json.dump({'failed': failed, 'drift': out}, open(sys.argv[1], 'w'), indent=1)
print(len(out), 'failed', len(failed))
