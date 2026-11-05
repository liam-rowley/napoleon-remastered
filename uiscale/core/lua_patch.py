"""Apply a factor-neutral Lua patch list to compiled UI scripts: assert each vanilla constant or instruction, then scale it by the factor.

purpose: parse a patch list (Empire's ui_scale_mod syntax, every number in vanilla pixels, every item asserting what it changes), apply it to Lua 5.1 chunks at a factor with px(x) = floor(x + 0.5) on core/discovery/luachunk.py, re-parse every result, and check a list against a set of scripts; also writes a list from a lua_consts classification
usage: from lua_patch import parse_list, apply, check, write_list; out, log = apply(chunk_bytes, items, 1.5)   (library; `python3 core/wsc.py uiscale lua-patches [--check]` and `uiscale build` drive it)
when: J67 Lua part of the UI scale stop-gap: the build writes the patched scripts into ui_scale_<tag>x.pack; --check after a game update fails loudly on a changed instruction
not-a-verb: a library behind uiscale/napoleon/cli.py, ported from empire-remastered ui_scale_mod/tools/apply_patches.py and luapatch.py

List syntax: `script id | item, item, ...`, one line per script (`#` starts a comment line). pc and K are vanilla indices
(`python3 core/discovery/luachunk.py list <file>`), however many edits come before them on the line.
  func:K[v]                 scale numeric constant K, whose vanilla value must be v, to px(v * factor)
  func:K[v]=w               set it to px(w * factor) (w in vanilla pixels)
  func@pc[INSTR]=INSTR      replace the instruction at pc, which must be the vanilla INSTR
  func@pc[INSTR]+INSTR;...  insert instruction(s) before pc (jumps that targeted pc run the new code first)
INSTR is luachunk assembler syntax (R<n>, K<n>, #<number> a literal, '<string>', U<n>, ->N a vanilla pc); `$<number>` is a literal in
vanilla pixels, written as px(number * factor). Asserts are checked on the vanilla chunk before any edit, so they read as vanilla. At
factor 1.0 a list of scale items and `$` literals changes nothing (pinned by tests/test_uiscale_lua.py).
"""
import math
import re
import struct

import luachunk as L

BITRK = 256


def px(x):
    return int(math.floor(x + 0.5))


def split_outside_quotes(s, sep):
    out, cur, q, i = [], '', None, 0
    while i < len(s):
        ch = s[i]
        if q:
            cur += ch
            if ch == '\\':
                cur += s[i + 1]; i += 1
            elif ch == q:
                q = None
        elif ch in '\'"':
            q = ch; cur += ch
        elif ch == sep:
            out.append(cur); cur = ''
        else:
            cur += ch
        i += 1
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def parse_list(text):
    """[(script id, [item, ...])]; a script named twice is an error"""
    out, seen = [], set()
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '|' not in line:
            raise ValueError(f'line {n}: expected "script | items"')
        path, items = [x.strip() for x in line.split('|', 1)]
        if path.lower() in seen:
            raise ValueError(f'line {n}: {path} appears twice; put all its items on one line')
        seen.add(path.lower())
        its = split_outside_quotes(items, ',')
        for it in its:
            parse_item(it)
        out.append((path, its))
    return out


ITEM_K = re.compile(r'^(main(?:#\d+)*):(\d+)\[([-+0-9.eE]+)\](?:=([-+0-9.eE]+))?$')
ITEM_C = re.compile(r'^(main(?:#\d+)*)@(\d+)\[([^\]]+)\]([=+])(.+)$')


def parse_item(it):
    m = ITEM_K.match(it)
    if m:
        return {'kind': 'set' if m.group(4) is not None else 'scale', 'func': m.group(1), 'k': int(m.group(2)),
                'vanilla': float(m.group(3)), 'to': float(m.group(4)) if m.group(4) is not None else None}
    m = ITEM_C.match(it)
    if m:
        return {'kind': 'replace' if m.group(4) == '=' else 'insert', 'func': m.group(1), 'pc': int(m.group(2)),
                'expect': m.group(3).strip(), 'body': m.group(5).strip()}
    raise ValueError(f'patch item {it!r}: expected func:K[v], func:K[v]=w, func@pc[INSTR]=INSTR or func@pc[INSTR]+INSTR;...')


def scaled_text(text, factor):
    """`$28` -> `#<px(28 * factor)>` outside quotes"""
    out, q = [], None
    i = 0
    while i < len(text):
        ch = text[i]
        if q:
            out.append(ch)
            if ch == '\\':
                out.append(text[i + 1]); i += 1
            elif ch == q:
                q = None
            i += 1; continue
        if ch in '\'"':
            q = ch; out.append(ch); i += 1; continue
        if ch == '$':
            m = re.match(r'\$([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', text[i:])
            out.append('#%d' % px(float(m.group(1)) * factor)); i += len(m.group(0)); continue
        out.append(ch); i += 1
    return ''.join(out)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def assert_vanilla(ch, it):
    """the item's vanilla constant or instruction is what the list says, else ValueError (a game update or a wrong list)"""
    try:
        f = ch.func(it['func'])
    except (IndexError, ValueError):
        raise ValueError(f'{it["func"]}: no such function')
    if it['kind'] in ('scale', 'set'):
        if it['k'] >= len(f.k) or f.k[it['k']][0] != 'num':
            raise ValueError(f'{it["func"]}:K{it["k"]} is not a numeric constant')
        v = struct.unpack('<f', f.k[it['k']][1])[0]
        if v != f32(it['vanilla']):
            raise ValueError(f'{it["func"]}:K{it["k"]} is {v:g}, the list says {it["vanilla"]:g}')
        return
    pc = it['pc']
    if pc >= len(f.code):
        raise ValueError(f'{it["func"]}@{pc}: past the end ({len(f.code)} instructions)')
    try:
        want = L.asm(f, it['expect'], pc, add=False)
    except KeyError as e:
        raise ValueError(f'{it["func"]}@{pc}: expected {it["expect"]!r}: {e}')
    if want != f.code[pc]:
        raise ValueError(f'{it["func"]}@{pc}: expected {it["expect"]!r}, found {L.fmt(f, f.code[pc], pc)!r}')


def apply(data, items, factor):
    """(patched chunk bytes, log lines); raises ValueError when an assert fails"""
    its = [parse_item(i) if isinstance(i, str) else i for i in items]
    van = L.parse(data)
    for it in its:
        assert_vanilla(van, it)
    ch = L.parse(data)
    log, pcmaps = [], {}

    def pcmap(name):
        if name not in pcmaps:
            pcmaps[name] = list(range(len(ch.func(name).code) + 1))
        return pcmaps[name]

    for it in [i for i in its if i['kind'] in ('scale', 'set')]:
        f = ch.func(it['func']); old = f.kshow(it['k'])
        f.set_const(it['k'], float(px((it['vanilla'] if it['kind'] == 'scale' else it['to']) * factor)))
        log.append(f'{it["func"]}:K{it["k"]}: {old} -> {f.kshow(it["k"])}')
    for it in [i for i in its if i['kind'] in ('replace', 'insert')]:
        name = it['func']; f = ch.func(name); m = pcmap(name); cur = m[it['pc']]
        body = scaled_text(it['body'], factor)
        if it['kind'] == 'replace':
            old = L.fmt(f, f.code[cur], cur)
            f.replace(cur, L.asm(f, body, cur, target=lambda n: m[n]))
            log.append(f'{name}@{it["pc"]}: {old} -> {L.fmt(f, f.code[cur], cur)}')
        else:
            texts = split_outside_quotes(body, ';'); n_new = len(texts)
            words = [L.asm(f, t, cur + i, target=lambda n: m[n] + (n_new if m[n] >= cur else 0)) for i, t in enumerate(texts)]
            f.insert(cur, words)
            for i in range(len(m)):
                if m[i] >= cur:
                    m[i] += len(words)
            log.append(f'{name}@{it["pc"]}: +[' + '; '.join(L.fmt(f, w, cur + i) for i, w in enumerate(words)) + ']')
    out = ch.serialise()
    if L.parse(out).serialise() != out:
        raise ValueError('patched chunk does not round-trip')
    return out, log


def check(entries, scripts):
    """entries: parse_list output; scripts: {script id: bytes}. -> [problem text] (empty = every assert holds)"""
    bad = []
    for sid, items in entries:
        if sid not in scripts:
            bad.append(f'{sid}: no such script'); continue
        van = L.parse(scripts[sid])
        for it in items:
            try:
                assert_vanilla(van, parse_item(it))
            except ValueError as e:
                bad.append(f'{sid}: {e}')
    return bad


# ------------------------------------------------------------------------------------------------ list writer
def _num_text(v):
    return '%d' % v if v == int(v) else repr(v)


def _instr_with_dollar(f, pc, ki, value):
    """the instruction at pc as text, its operand that loads K<ki> written as a `$` literal"""
    d = L.dec(f.code[pc]); o = L.OPS[d['OP']]
    toks = L.fmt(f, f.code[pc], pc).split(' ')
    parts = L.LAYOUT[o].split()
    for n, part in enumerate(parts, 1):
        fld, kind = part.split(':')
        v = d['Bx'] if fld == 'X' else d.get(fld)
        if (kind == 'K' and v == ki) or (kind == 'RK' and v == ki + BITRK):
            toks[n] = '$' + _num_text(value)
    return ' '.join(toks)


def items_for(chunk, rows):
    """patch items for one script's classified rows (class scale or set): a whole constant when every use of it is in the rows,
    else one instruction item per use (the constant is shared with a use that must not scale)"""
    by_k = {}
    for r in rows:
        by_k.setdefault((r['func'], r['k']), []).append(r)
    items = []
    for (fn, ki), rs in sorted(by_k.items(), key=lambda x: (x[0][0].count('#'), x[0][0], x[0][1])):
        f = chunk.func(fn)
        from lua_consts import all_k_uses
        pcs = sorted(all_k_uses(f, ki))
        van = rs[0]['value']
        sets = {r.get('set') for r in rs}
        target = next(iter(sets)) if len(sets) == 1 else None
        if pcs == sorted(r['pc'] for r in rs) and len(sets) == 1:
            items.append(f'{fn}:{ki}[{_num_text(van)}]' + (f'={_num_text(target)}' if target is not None else ''))
        else:
            for r in sorted(rs, key=lambda r: r['pc']):
                to = r.get('set', van)
                items.append(f'{fn}@{r["pc"]}[{L.fmt(f, f.code[r["pc"]], r["pc"])}]={_instr_with_dollar(f, r["pc"], ki, to)}')
    return items


def write_list(doc, scripts, header):
    """lua_patches.txt text from a lua_consts document (rows of class scale or set)"""
    lines = [header.rstrip('\n')]
    per = {}
    for r in doc['rows']:
        if r['class'] in ('scale', 'set'):
            per.setdefault(r['script'], []).append(r)
    for sid in sorted(per):
        rows = per[sid]
        calls = sorted({c.split(' of ')[-1] for r in rows for c in r['call'].split('; ')})
        lines.append(f'# {sid}: {len(rows)} uses; {", ".join(calls)}')
        lines.append(f'{sid} | ' + ','.join(items_for(L.parse(scripts[sid]), rows)))
    return '\n'.join(lines) + '\n'
