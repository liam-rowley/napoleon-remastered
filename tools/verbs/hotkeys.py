"""Seed the hotkeys registry from Napoleon's vanilla key file and check the whole registry for clashes the schema cannot see.

purpose: parse the vanilla key table (data.pack text\\default_keys.xml, or a custom_keys.keys.xml) into `vanilla.<keyset>.<func>.<n>` hotkeys rows through the registry, and check every row for clashes (same binding in a clashing context, a bare key that fires with any modifier, an OS combo)
usage: python3 core/wsc.py hotkeys import (--from-pack [<data dir>] | <keys.xml>) [--keyset fps] [--no-loc] [--dry-run]  |  python3 core/wsc.py hotkeys check
when: after a game update (reseed: `hotkeys import --from-pack`, then `reg render hotkeys` and review the diff of registries/hotkeys.jsonl); before adding any mod hotkey (`hotkeys check` is also run by tests/test_hotkeys.py in the `tests` gate)
verb: hotkeys

Reseed after a game update: `python3 core/wsc.py hotkeys import --from-pack` reads text\\default_keys.xml out of the Napoleon packs (the
J7 PackFS, precedence applied) and rewrites every `vanilla.*` row; mod rows are untouched. Rerunning on the same file gives the same
rows in the same order (the registry sorts by id). A row the grammar cannot spell, or that is an OS combo, stops the import (exit 1,
nothing written) and is listed: add its key to KEY_NAMES, or record it in tests/test_hotkeys.py KNOWN_OS_COMBO.

Encoding (checked on Napoleon 2026-10-29, see the engine_facts rows napoleon.hotkeys.*):
- context from the `<mappings>` mode (default file) or the func's own `<mapping mode>` (custom file): `battle`, `campaign`; a func in both,
  in `all`, or in none (voice_chat) is `global`. Land and naval formation keys share Alt+1..4 in `battle`, so a `battle_naval_*` func is
  context `battle_naval` and a `battle_land_*` one `battle_land`; a context is a prefix family (`battle` clashes with `battle_naval`).
- modifier `ANY` fires with every modifier held, `ALLOW_SHIFT` with the key alone or Shift added (the vanilla table itself binds
  Ctrl+S next to ALLOW_SHIFT S, Ctrl+A next to ALLOW_SHIFT A, so Ctrl does not reach it: engine_facts napoleon.hotkeys.modifiers). The
  row's binding is the bare key and `source_ref` ends in `modifier=ANY` / `modifier=ALLOW_SHIFT`, which the bare-key rule reads (the
  schema has no field for it).
- `all`-mode funcs are `global`, except `deselect_all`: it shares Return with the campaign `end_turn`, a vanilla double binding the
  schema would reject, so it is context `all_modes` (a wildcard like `global` in the test, not in the schema) and the pair is listed in
  tests/test_hotkeys.py KNOWN_VANILLA_CLASH.
"""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NAME = 'hotkeys'
HELP = 'seed the hotkeys registry from the vanilla key file (import) and check it for clashes (check)'

GAME_DATA = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\data'
KEYS_ENTRY = 'text\\default_keys.xml'
LOC_ENTRY = 'text\\localisation.loc'
LOC_PREFIX = 'shortcut_localisation_onscreen_'
MODS = {'NONE': '', 'CTRL': 'Ctrl', 'ALT': 'Alt', 'SHIFT': 'Shift'}
WILD = {'ANY', 'ALLOW_SHIFT'}   # fire with more than the bare key: ANY with every modifier, ALLOW_SHIFT with Shift added
CONTEXT_OVERRIDE = {'deselect_all': 'all_modes'}   # see the header
WILDCARD_CTX = ('global', 'all_modes')
# engine key name -> canonical key (schema grammar: [A-Z0-9], F1-F24 or a CamelCase name). Letters, digits and F-keys pass through.
KEY_NAMES = {
    'ESCAPE': 'Escape', 'RETURN': 'Return', 'SPACE': 'Space', 'DELETE': 'Delete', 'INSERT': 'Insert', 'BACK': 'Backspace',
    'HOME': 'Home', 'END': 'End', 'PAGE_UP': 'PageUp', 'PAGE_DOWN': 'PageDown', 'CAPITAL': 'CapsLock', 'TAB': 'Tab',
    'ADD': 'NumpadAdd', 'SUBTRACT': 'NumpadSubtract', 'MULTIPLY': 'NumpadMultiply', 'DIVIDE': 'NumpadDivide',
    'LBRACKET': 'LBracket', 'RBRACKET': 'RBracket', 'APOSTROPHE': 'Apostrophe', 'SEMICOLON': 'Semicolon', 'SLASH': 'Slash',
    'PERIOD': 'Period', 'COMMA': 'Comma', 'UP': 'Up', 'DOWN': 'Down', 'LEFT': 'Left', 'RIGHT': 'Right',
}
SPELL = re.compile(r'^([A-Z0-9]|F([1-9]|1[0-9]|2[0-4])|[A-Z][A-Za-z0-9]+)$')
# OS-level combos, key names normalised (Esc -> Escape): a binding in this set, or a `Win` modifier, always fails
OS_COMBOS = {'Alt+F4', 'Alt+Tab', 'Alt+Escape', 'Ctrl+Alt+Delete', 'Ctrl+Shift+Escape'}
KEY_ALIAS = {'Esc': 'Escape', 'Del': 'Delete', 'Ins': 'Insert', 'Enter': 'Return'}
WIN_RAW = re.compile(r'^(L|R)?(WIN|WINDOWS|LWINDOWS|RWINDOWS|APPS)$', re.I)


# ---- pure helpers (host tests: tests/test_hotkeys.py) --------------------------------------------------------------------------
def spell_key(raw):
    """Canonical key for an engine key name, or None when the grammar cannot spell it."""
    raw = (raw or '').strip()
    if len(raw) == 1 and raw.isalnum():
        return raw.upper()
    if re.fullmatch(r'F\d{1,2}', raw):
        k = raw
    elif raw.upper() in KEY_NAMES:
        k = KEY_NAMES[raw.upper()]
    elif re.fullmatch(r'NUMPAD\d', raw.upper()):
        k = 'Numpad' + raw[-1]
    else:
        return None
    return k if SPELL.match(k) else None


def context_of(modes, name=''):
    """`battle` / `campaign` / `global`, refined to battle_land / battle_naval from the func name."""
    modes = set(modes) - {''}
    if modes == {'battle'}:
        for fam in ('naval', 'land'):
            if name.startswith(f'battle_{fam}_'):
                return f'battle_{fam}'
        return 'battle'
    return 'campaign' if modes == {'campaign'} else 'global'


def parse_keys(text, keyset='fps', source_ref='keys.xml', loc=None):
    """(rows, problems) from a default_keys.xml (`<shortcuts>` + `<mappings>`) or a custom_keys.keys.xml (`<custom_keys>`, inline
    `<mapping>`). A problem is a string naming the func and why its key was not turned into a row; rows are in file order."""
    root = ET.fromstring(text)
    ks = next((k for k in root.iter('keyset') if k.get('name') == keyset), None)
    if ks is None:
        raise ValueError(f'no keyset {keyset!r} (have {[k.get("name") for k in root.iter("keyset")]})')
    modes = {}
    if root.find('mappings') is not None:
        for m in root.find('mappings'):
            for f in m:
                modes.setdefault(f.get('name'), set()).add(m.get('name'))
    rows, problems = [], []
    for f in ks.iter('func'):
        name = f.get('name')
        mode = modes.get(name, set()) | {m.get('mode') for m in f.findall('mapping')}
        ctx = CONTEXT_OVERRIDE.get(name) or context_of(mode, name)
        for n, k in enumerate(f.findall('key')):
            raw, mod = (k.text or '').strip(), (k.get('modifier') or 'NONE').upper()
            where = f'{name} key {n} ({mod} {raw})'
            if WIN_RAW.match(raw):
                problems.append(f'{where}: a Windows key is an OS combo')
                continue
            key = spell_key(raw)
            if key is None:
                problems.append(f'{where}: the schema grammar cannot spell {raw!r} (add it to KEY_NAMES in tools/verbs/hotkeys.py)')
                continue
            if mod not in MODS and mod not in WILD:
                problems.append(f'{where}: unknown modifier {mod!r}')
                continue
            binding = '+'.join(p for p in (MODS.get(mod, ''), key) if p)
            if binding in OS_COMBOS:
                problems.append(f'{where}: {binding} is an OS combo')
                continue
            ref = f'{source_ref}#{keyset}/{name}' + (f' modifier={mod}' if mod in WILD else '')
            desc = (loc or {}).get(LOC_PREFIX + name) or name
            rows.append({'id': f'vanilla.{keyset}.{name}.{n}', 'description': desc, 'binding': binding, 'action': name,
                         'context': ctx, 'source': 'vanilla', 'source_ref': ref})
    return rows, problems


ORDER = ['Ctrl', 'Alt', 'Shift']


def split(binding):
    """(modifiers in Ctrl, Alt, Shift order, then any others; key) of a binding or loose text such as `win+x` or `alt + esc`."""
    parts = [p.strip().capitalize() for p in binding.split('+')]
    key = KEY_ALIAS.get(parts[-1], parts[-1])
    mods = sorted(set(parts[:-1]), key=lambda m: (ORDER.index(m) if m in ORDER else len(ORDER), m))
    return mods, key


def os_combo(binding):
    mods, key = split(binding)
    if {'Win', 'Windows', 'Super', 'Meta'} & set(mods) or key in ('Win', 'Windows'):
        return True
    return '+'.join(mods + [key]) in OS_COMBOS


def ctx_clash(a, b):
    """Same context, either `global`, or one a `_`-prefix family of the other (battle / battle_naval)."""
    return a == b or a in WILDCARD_CTX or b in WILDCARD_CTX or a.startswith(b + '_') or b.startswith(a + '_')


def wild_of(row):
    m = re.search(r'modifier=(ANY|ALLOW_SHIFT)\b', row.get('source_ref', ''))
    return m.group(1) if m else None


def reaches(w, other_binding):
    """True when wildcard row `w` also fires for `other_binding` (same key): ANY with every modifier, ALLOW_SHIFT with Shift."""
    mods = split(other_binding)[0]
    return wild_of(w) == 'ANY' or (wild_of(w) == 'ALLOW_SHIFT' and mods == ['Shift'])


def find_problems(rows, known_os_combo=(), known_clash=()):
    """Every clash in the registry rows as a message naming both rows (or the one row, for an OS combo). `known_os_combo` is a list of
    (row id, reason): a vanilla row allowed to be an OS combo; `known_clash` is a list of (id, id, reason): a vanilla pair allowed to
    clash. A stale entry (no such row, or it no longer applies) is a problem."""
    out, known = [], dict(known_os_combo)
    byid = {r['id']: r for r in rows}
    for rid in known:
        r = byid.get(rid)
        if r is None:
            out.append(f'known_os_combo: {rid} is not in the registry (stale entry)')
        elif not os_combo(r['binding']):
            out.append(f'known_os_combo: {rid} ({r["binding"]}) is no longer an OS combo (stale entry)')
    for r in rows:
        if os_combo(r['binding']) and r['id'] not in known:
            out.append(f'OS combo: {r["id"]} binds {r["binding"]} ({r["context"]}); the OS takes it first')
    seen = set()
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if not ctx_clash(a['context'], b['context']):
                continue
            if split(a['binding'])[1] != split(b['binding'])[1]:
                continue
            if a['binding'] == b['binding']:
                msg = f'clash: {a["id"]} and {b["id"]} both bind {a["binding"]} ({a["context"]} / {b["context"]})'
            elif (wild_of(a) and reaches(a, b['binding'])) or (wild_of(b) and reaches(b, a['binding'])):
                w = a if wild_of(a) and reaches(a, b['binding']) else b
                o = b if w is a else a
                how = 'every modifier' if wild_of(w) == 'ANY' else 'Shift added'
                msg = (f'bare-key clash: {w["id"]} ({w["binding"]}, modifier {wild_of(w)}) fires with {how}, so it takes '
                       f'{o["id"]} ({o["binding"]}) ({w["context"]} / {o["context"]})')
            else:
                continue
            if frozenset((a['id'], b['id'])) in {frozenset((x, y)) for x, y, _ in known_clash}:
                seen.add(frozenset((a['id'], b['id'])))
            else:
                out.append(msg)
    for x, y, _ in known_clash:
        if frozenset((x, y)) not in seen:
            out.append(f'known_clash: {x} and {y} no longer clash or are not both in the registry (stale entry)')
    return out


def free_keys(rows, contexts=('battle', 'campaign', 'global'), mods=('', 'Ctrl+', 'Alt+', 'Shift+', 'Ctrl+Shift+')):
    """{context: [bindings]} that clash with no row, are not F4 and not an OS combo (letters, digits and F1-F12 only)."""
    keys = [chr(c) for c in range(65, 91)] + [str(d) for d in range(10)] + [f'F{n}' for n in range(1, 13)]
    out = {}
    for ctx in contexts:
        free = []
        for m in mods:
            for k in keys:
                if k == 'F4' or os_combo(m + k):
                    continue
                probe = {'id': 'probe', 'binding': m + k, 'context': ctx, 'source_ref': ''}
                if not any('probe' in p for p in find_problems(rows + [probe])):
                    free.append(m + k)
        out[ctx] = free
    return out


# ---- verb ------------------------------------------------------------------------------------------------------------------------
def load_loc(data_dir):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'discovery' / 'core'))
    from packfs import PackFS
    import loc
    games = json.loads((Path(__file__).resolve().parents[2] / 'discovery' / 'napoleon' / 'games.json').read_text(encoding='utf-8'))
    fs = PackFS(data_dir, pack_order=games['napoleon']['pack_order'])
    _, entries = loc.decode(fs.read(LOC_ENTRY))
    return {k: t for k, t, _ in entries}, fs


def add_arguments(p):
    sub = p.add_subparsers(dest='action', required=True)
    i = sub.add_parser('import', help='seed vanilla.* rows from a key file or the game packs')
    i.add_argument('file', nargs='?', help='a default_keys.xml or custom_keys.keys.xml')
    i.add_argument('--from-pack', nargs='?', const=GAME_DATA, metavar='DATA_DIR', help='read text\\default_keys.xml from the Napoleon packs')
    i.add_argument('--keyset', default='fps')
    i.add_argument('--no-loc', action='store_true', help='descriptions are the func names (no localisation lookup)')
    i.add_argument('--dry-run', action='store_true', help='parse and report, write nothing')
    sub.add_parser('check', help='check the registry for clashes, bare-key hits and OS combos')


def run(args, ctx):
    from warscape.registry import load_all
    reg = load_all(ctx)['hotkeys']
    if args.action == 'check':
        sys.path.insert(0, str(Path(ctx.root) / 'tests'))
        from test_hotkeys import KNOWN_OS_COMBO, KNOWN_VANILLA_CLASH
        probs = find_problems(reg.rows, KNOWN_OS_COMBO, KNOWN_VANILLA_CLASH)
        print('\n'.join(probs) or f'hotkeys: {len(reg.rows)} rows, no clash')
        return 1 if probs else 0
    if bool(args.file) == bool(args.from_pack):
        print('hotkeys import: give a key file or --from-pack')
        return 2
    loc = None
    if args.from_pack:
        try:
            loc, fs = load_loc(args.from_pack) if not args.no_loc else (None, None)
            if fs is None:
                sys.path.insert(0, str(Path(ctx.root) / 'discovery' / 'core'))
                from packfs import PackFS
                fs = PackFS(args.from_pack)
            text, src = fs.read(KEYS_ENTRY).decode('utf-8'), f'{fs.stat(KEYS_ENTRY).source}:{KEYS_ENTRY}'
        except (OSError, ValueError, KeyError) as e:
            print(f'hotkeys import: cannot read the packs at {args.from_pack}: {e}')
            return 1
    else:
        text, src = Path(args.file).read_text(encoding='utf-8-sig'), Path(args.file).name
        if not args.no_loc and Path(GAME_DATA).is_dir():
            try:
                loc = load_loc(GAME_DATA)[0]
            except (OSError, ValueError, KeyError) as e:
                print(f'hotkeys import: no localisation ({e}); descriptions are func names')
    rows, problems = parse_keys(text, args.keyset, src, loc)
    for p in problems:
        print(f'problem: {p}')
    if problems:
        print(f'hotkeys import: {len(problems)} problem(s); nothing written')
        return 1
    new = {r['id'] for r in rows}
    stale = [r['id'] for r in reg.rows if r['id'].startswith(f'vanilla.{args.keyset}.') and r['id'] not in new]
    print(f'hotkeys import: {len(rows)} rows from {src} (keyset {args.keyset}), {len(stale)} stale vanilla row(s) removed')
    if args.dry_run:
        return 0
    reg.rows = [r for r in reg.rows if r['id'] not in stale]
    for r in rows:
        reg.add(r, replace=True)
    reg.save()
    return subprocess.call([sys.executable, str(Path(ctx.root) / 'core' / 'wsc.py'), '--root', str(ctx.root), 'reg', 'render', 'hotkeys'])
