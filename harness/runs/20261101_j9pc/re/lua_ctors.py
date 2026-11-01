"""Lunar class constructors: the closure registered as both 'new' (methods table) and '__call' (metatable)."""
import sys, re, struct, json
sys.path.insert(0, __import__('os').path.dirname(__file__))
from lua_common import *
def ctors():
    out = []
    new = [v for v in im.find_str('new') if im.section_of(v)[0] == '.rdata']
    for nv in new:
        for r in im.refs(nv):
            if not im.in_text(r): continue
            w = im.bytes_at(r - 60, 60); m = None
            for mm in re.finditer(rb'\x6a\x00\x68(....)\x56\xe8', w, re.S): m = mm
            if not m: continue
            f = struct.unpack('<I', m.group(1))[0]
            w2 = im.bytes_at(r - 0x500, 0x500); own = None
            for mm in re.finditer(rb'\x68(....)\x56\xe8', w2, re.S):
                s = cs(struct.unpack('<I', mm.group(1))[0], 60)
                if s and ID.match(s) and not s.startswith('__') and s != 'new': own = s
            if im.in_text(f): out.append((own, f, r))
    return out
if __name__ == '__main__':
    for o, f, r in ctors(): print(o, hex(f), hex(r))
