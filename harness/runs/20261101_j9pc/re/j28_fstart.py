"""j28_fstart.py - guess the function start of each VA (last int3/ret padding boundary before it) and list E8 callers. Read-only."""
import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe')
for a in sys.argv[1:]:
    va = int(a, 16)
    b = im.bytes_at(va - 0x3000, 0x3000)
    # walk back to a 16-aligned address preceded by cc padding
    s = None
    for off in range(len(b) - 1, 0, -1):
        x = va - 0x3000 + off
        if x % 16 == 0 and b[off - 1] == 0xcc:
            s = x; break
    cs = im.callers(s) if s else []
    print('%08x -> start %08x  (%d E8 callers: %s)' % (va, s or 0, len(cs), ' '.join('%08x' % c for c in cs[:12])))
