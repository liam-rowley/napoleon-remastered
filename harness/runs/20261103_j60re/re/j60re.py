#!/usr/bin/env python3
"""J60 static RE helper on a copy of the stock Napoleon.exe: luaL_Reg tables, disassembly, callers, xrefs, strings, dwords.

purpose: the J60 ship-chain static RE (run harness/runs/20261103_j60re): dump a Lunar method table with names, disassemble (to ret or n
         instructions), list rel32 callers, string addresses with their references, dwords; built on discovery/core/x86re.py
usage: <re venv python> -I harness/runs/20261103_j60re/re/j60re.py <exe> regs lo hi | dis va [n] | d va [n] | callers va | xrefs va |
       str text | refs va | u32 va [n]   (several: <exe> multi "dis 611e90 40 ; regs 1451990 1451b00"; VAs in hex; venv: discovery/core/re_env.py)
when: re-checking a J60 RE claim (the README's tables name the commands that produced them)
not-a-verb: reads a copy of the exe (read only); writes nothing
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'discovery', 'core'))
import x86re  # noqa: E402

im = None


def num(s):
    return int(s, 16)


def isstr(v):
    s = im.section_of(v)
    if not s or s[0] != '.rdata':
        return None
    c = im.cstr(v)
    if c and 1 <= len(c) < 80 and all(32 <= ord(ch) < 127 for ch in c):
        return c
    return None


def istext(v):
    s = im.section_of(v)
    return bool(s) and s[0] == '.text'


def fmt(i):
    return '%08x  %-24s %s %s' % (i.address, i.bytes.hex(' '), i.mnemonic, i.op_str)


def run(a):
    c = a[0]
    if c == 'regs':
        x, hi = num(a[1]), num(a[2])
        while x < hi:
            n, f = im.u32(x), im.u32(x + 4)
            name = isstr(n)
            if name is not None and istext(f):
                print('  %08x %-40s %08x' % (x, name, f))
                x += 8
                continue
            x += 4
    elif c in ('dis', 'd'):
        for i in im.dis(num(a[1]), int(a[2]) if len(a) > 2 else 40, stop_ret=(c == 'd')):
            print(fmt(i))
    elif c == 'callers':
        print(' '.join('%08x' % x for x in im.callers(num(a[1]))))
    elif c == 'xrefs':
        for x in im.xrefs(num(a[1])):
            print(x)
    elif c == 'str':
        for x in im.find_str(a[1]):
            print('%08x' % x, 'refs:', ' '.join('%08x' % r for r in im.refs(x)))
    elif c == 'refs':
        for r in im.refs(num(a[1])):
            print('%08x %s' % (r, im.section_of(r)[0]))
    elif c == 'u32':
        n = int(a[2]) if len(a) > 2 else 1
        print(' '.join('%08x' % im.u32(num(a[1]) + 4 * k) for k in range(n)))
    else:
        sys.exit('unknown command ' + c)


def main():
    global im
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    im = x86re.Image(sys.argv[1])
    if sys.argv[2] == 'multi':
        for part in ' '.join(sys.argv[3:]).split(';'):
            if part.split():
                print('=====', part.strip())
                run(part.split())
    else:
        run(sys.argv[2:])


if __name__ == '__main__':
    main()
