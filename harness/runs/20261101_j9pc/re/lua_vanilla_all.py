"""Dump every call/method argument signature seen in Napoleon's vanilla ui/*.luac (J6 inventory, '...' = open argument list)."""
import json, os, sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import lua_api, api_inventory
from extracted import effective, load_games
_orig = api_inventory.argshape
api_inventory.argshape = lambda e: '...' if e == ('vararg',) else _orig(e)
games = load_games(None)
nap_files = effective(games, 'napoleon', exts={'.luac'}, under='ui' + lua_api.BACKSLASH)
nj, _, failed = lua_api.inventory(nap_files)
json.dump({'calls': {k: {'sigs': v['sigs'], 'scripts': v['scripts'][:5]} for k, v in nj['calls'].items()},
           'methods': {k: {'sigs': v['sigs'], 'scripts': v['scripts'][:5], 'receivers': v.get('receivers')} for k, v in nj['methods'].items()},
           'defined': sorted(nj['defined'])}, open(sys.argv[1], 'w'))
