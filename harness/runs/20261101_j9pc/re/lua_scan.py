"""J9: name -> address of Napoleon.exe's UI-facing Lua C functions and a static count of the Lua stack arguments each reads.

usage: <re venv python> -I lua_scan.py <out.json>     (read-only over the exe; prints a summary)

Bindings: registrar groups (push doc; push name; push func; mov ecx,<static>; call <registrar>) for CampaignUI / BattleUI /
FrontEnd; luaL_Reg tables (8-byte {name, func}) registered with luaL_register or a custom loop; Lunar classes (8-byte
{name, member func} or 24-byte {name, 0, member pointer(16)}) whose dispatch thunk names the class in its luaL_typerror call;
stack-built luaL_Reg arrays (mov [esp+x], name; mov [esp+x+4], func).

Argument model: the engine's bindings fetch an argument stream object with 0x1058750(L) and read with operator>> helpers that
read index -1 and pop it (lua_settop(L, -2)), so the number of arguments a function consumes = the pops along a path.
Plain lua_CFunctions read constant positive indices (lua_to*(L, n), luaL_check*(L, n)). Both are counted:
  pops_max/pops_min  = max/min over acyclic CFG paths of pop events (settop(L,-k) = k-1 pops, lua_remove = 1), callees summarised
                       recursively (depth 4, callees under 1500 insns); pops inside a loop of the binding = variadic
  idx_max            = highest positive constant stack index passed to an index-taking Lua API function (direct or in callees
                       that get the same lua_State as their first argument is not tracked: callees count only their pops)
"""
import sys, os, re, struct, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lua_common import im, T0, CODE, ID, LAPI, NAME, CFG, calls_with_args, imm, cs, s32, LAPI_RANGE

L = LAPI
IDX_FUNCS = {L[n] for n in ('lua_toboolean', 'lua_tolstring', 'lua_tonumber', 'lua_tointeger', 'lua_touserdata', 'lua_topointer',
                            'lua_type', 'lua_isnumber', 'lua_isuserdata', 'lua_getfield', 'lua_gettable', 'lua_pushvalue',
                            'lua_getmetatable', 'luaL_checkany', 'luaL_checkinteger', 'luaL_checklstring', 'luaL_checknumber',
                            'luaL_checktype', 'luaL_optinteger', 'luaL_typerror', 'luaL_argerror', 'lua_rawequal', 'lua_insert',
                            'luaL_getmetafield', 'luaL_callmeta')}
READER = 0x1058750          # argument stream fetch (reads the stream object stored in the registry)
REGISTRARS = {0x998c50: 'CampaignUI', 0x59eb40: 'BattleUI', 0x4587a0: 'FrontEnd'}

from lua_effect import READER
from lua_count import count, reader_cons, walk2
from lua_common import CFG


def analyse(f):
    r = count(f, depth=3, limit=8000, top=True)
    g = CFG(f, limit=8000)
    w = walk2(g, 4, top=True)
    ws = walk2(g, 4, top=True, strict=True)
    return dict(reads_max=w['max'], reads_min=w['min'], loop=w['loop'], gettop=w['gettop'] or r['gettop'], idx_max=max(w['idx'], r['idx']),
                ops=w['ops'], notes=sorted(w['notes']), n_insn=w['n'], raw_count_max=r['max'], raw_loop=r['loop'], strict_max=ws['max'], strict_min=ws['min'], strict_loop=ws['loop'],
                strict_notes=sorted(n for n in ws['notes'] if n.startswith('via_skipped') or n.startswith('reader_fetching')),
                strict_flags=sorted(n for n in ws['notes'] if n in ('var_index_read_in_loop', 'forwards_args')))
REGISTRARS = {0x998c50: 'CampaignUI', 0x59eb40: 'BattleUI', 0x4587a0: 'FrontEnd'}


# ------------------------------------------------------------------ enumeration
def registrar_rows():
    out = []
    pat = re.compile(rb'(?:\x68(....)|\x6a(.))\x68(....)\x68(....)\xb9(....)\xe8(....)', re.S)
    for m in pat.finditer(CODE):
        site = T0 + m.start() + (5 if m.group(1) is not None else 2)
        name, func, obj, rel = (struct.unpack('<I', m.group(k))[0] for k in (3, 4, 5, 6))
        doc = struct.unpack('<I', m.group(1))[0] if m.group(1) is not None else 0
        callsite = T0 + m.end() - 5
        tgt = (callsite + 5 + s32(rel)) & 0xffffffff
        if tgt not in REGISTRARS:
            continue
        n = cs(name, 120)
        if not n or not ID.match(n) or not im.in_text(func):
            continue
        out.append(dict(table=REGISTRARS[tgt], name=n, va=func, doc=cs(doc, 600) if doc else None, reg_site=callsite,
                        kind='c_function', registrar=tgt))
    return out


def scan_tables():
    """8-byte {name, func} and 24-byte {name, 0, func, 0, 0, 0} null-terminated tables in .rdata/.data."""
    res = []
    for sname, start, vsz, raw in im.sections:
        if sname not in ('.rdata', '.data'):
            continue
        i = 0
        while i + 8 <= raw:
            j = i; ents = []
            while j + 8 <= raw:
                a, f = im.u32(start + j), im.u32(start + j + 4)
                st = cs(a, 120) if a else None
                if st and ID.match(st) and im.in_text(f):
                    ents.append((st, f)); j += 8
                else:
                    break
            if len(ents) >= 2 and im.u32(start + j) == 0 and im.u32(start + j + 4) == 0:
                res.append((start + i, 8, ents)); i = j; continue
            j = i; ents = []
            while j + 24 <= raw:
                va = start + j
                a, z, f, z2, z3 = (im.u32(va + 4 * k) for k in range(5))
                st = cs(a, 120) if (a and z == 0 and z2 == 0 and z3 == 0) else None
                if st and ID.match(st) and im.in_text(f):
                    ents.append((st, f)); j += 24
                else:
                    break
            if len(ents) >= 2:
                res.append((start + i, 24, ents)); i = j; continue
            i += 4
    return res


def table_owner(tva):
    """(owner, how, thunk) from the code that references the table."""
    for r in im.refs(tva):
        if not im.in_text(r):
            continue
        win = im.bytes_at(r, 0x90)
        # Lunar: push 1; push <thunk>; push esi; call lua_pushcclosure  -> thunk names the class via luaL_typerror
        m = re.search(rb'\x6a\x01\x68(....)', win, re.S)
        if m:
            thunk = struct.unpack('<I', m.group(1))[0]
            if im.in_text(thunk):
                g = CFG(thunk, limit=400)
                for b in g.blocks.values():
                    for (i, t, args) in calls_with_args(b):
                        if t == L['luaL_typerror'] and len(args) >= 3 and args[2].startswith('0x'):
                            nm = cs(int(args[2], 16), 80)
                            if nm:
                                return nm, 'lunar', thunk
        # luaL_register / custom loop then lua_setfield(L, LUA_GLOBALSINDEX, "<name>")
        m = re.search(rb'\x68(....)\x68\xee\xd8\xff\xff', win, re.S)
        if m:
            nm = cs(struct.unpack('<I', m.group(1))[0], 80)
            if nm:
                return nm, 'luaL_register', None
    return None, 'unknown', None


def stack_regs():
    out = []
    pat = re.compile(rb'\xc7\x44\x24(.)(....)\xc7\x44\x24(.)(....)', re.S)
    for m in pat.finditer(CODE):
        o1, a, o2, f = m.group(1)[0], struct.unpack('<I', m.group(2))[0], m.group(3)[0], struct.unpack('<I', m.group(4))[0]
        if o2 != (o1 + 4) & 0xff or not im.in_text(f):
            continue
        nm = cs(a, 80)
        if not nm or not ID.match(nm):
            continue
        st = m.start(); w = CODE[st:st + 300]; owner = None
        for k in range(len(w) - 10):
            if w[k] == 0x68 and w[k + 5:k + 10] == b'\x68\xee\xd8\xff\xff':
                owner = cs(struct.unpack_from('<I', w, k + 1)[0], 80); break
        out.append(dict(name=nm, va=f, site=T0 + st, owner=owner))
    return out


def runtime_tables():
    """16-byte {name, 0, member func, adj} tables filled by a dynamic initializer: mov dword ptr [entry+8], func."""
    ents = {}
    for m in re.finditer(rb'\xc7\x05(....)(....)', CODE, re.S):
        addr, f = struct.unpack('<II', m.group(1) + m.group(2))
        if not im.in_text(f) or im.section_of(addr)[0] != '.data':
            continue
        nm = cs(im.u32(addr - 8), 120)
        if nm and ID.match(nm):
            ents[addr - 8] = (nm, f)
    tabs = []
    for e in sorted(ents):
        if tabs and e - tabs[-1][-1] == 16:
            tabs[-1].append(e)
        else:
            tabs.append([e])
    out = []
    for t in tabs:
        start = t[0]
        out.append((start, [ents[e] for e in t]))
    return out


STDLIB = {'package', 'table', 'io', 'os', 'string', 'math', 'debug', 'bit', 'coroutine', '_G'}
OTHER_AGENT = (0x1451400, 0x1452000)   # battle script luaL_Reg block (battle.unit etc.): mapped by another J9 agent


def main(out):
    tables = collections.OrderedDict()

    def add(tname, meta, row):
        t = tables.setdefault(tname, dict(meta, entries=[]))
        t['entries'].append(row)

    for r in registrar_rows():
        a = analyse(r['va'])
        add(r['table'], dict(table_va=None, kind='registrar', registrar='0x%x' % r['registrar']),
            dict(name=r['name'], va='0x%x' % r['va'], doc=r['doc'], reg_site='0x%x' % r['reg_site'], **a))
    for tva, stride, ents in scan_tables():
        if OTHER_AGENT[0] <= tva < OTHER_AGENT[1]:
            continue
        names = [e[0] for e in ents]
        if names[0] in ('assert', 'create', 'concat', 'close', 'clock', 'byte', 'abs', 'debug', 'loadlib', 'module', 'cast') \
                or names[:2] == ['package', 'table']:
            continue
        owner, how, thunk = table_owner(tva)
        tname = owner or ('table@0x%x' % tva)
        if tname in tables and tables[tname].get('table_va') not in (None, '0x%x' % tva):
            tname = '%s@0x%x' % (tname, tva)
        for nm, f in ents:
            a = analyse(f)
            add(tname, dict(table_va='0x%x' % tva, kind=how, stride=stride, thunk=('0x%x' % thunk) if thunk else None),
                dict(name=nm, va='0x%x' % f, **a))
    for tva, ents in runtime_tables():
        if len(ents) < 1:
            continue
        owner, how, thunk = table_owner(tva)
        tname = owner or ('rtable@0x%x' % tva)
        if tname in tables:
            tname = '%s@0x%x' % (tname, tva)
        for nm, f in ents:
            a = analyse(f)
            add(tname, dict(table_va='0x%x' % tva, kind=how + '+runtime_init', stride=16, thunk=('0x%x' % thunk) if thunk else None),
                dict(name=nm, va='0x%x' % f, **a))
    from lua_ctors import ctors
    for own, f, site in ctors():
        if not own or own.startswith('battle') or own in ('empire_battle', 'ui_component'):
            continue     # battle script classes: the other J9 agent's scope
        a = analyse(f)
        add(own, dict(table_va=None, kind='lunar'), dict(name='__call', va='0x%x' % f, reg_site='0x%x' % site,
                                                         note='constructor (new/__call): lua_remove(L,1) then T(L)', **a))
    for r in stack_regs():
        if r['owner'] in STDLIB:
            continue
        a = analyse(r['va'])
        add(r['owner'] or 'stack@0x%x' % r['site'], dict(table_va=None, kind='stack_luaL_Reg'),
            dict(name=r['name'], va='0x%x' % r['va'], reg_site='0x%x' % r['site'], **a))
    json.dump(dict(lua_core={k: '0x%x' % v for k, v in sorted(LAPI.items())}, tables=tables), open(out, 'w'), indent=1)
    for t, v in tables.items():
        print('%-28s %-14s %4d  %s' % (t, v.get('kind'), len(v['entries']), v.get('table_va')))


if __name__ == '__main__':
    main(sys.argv[1])
