"""j28_regs.py - dump luaL_Reg-like tables (name ptr, func ptr) in a .data range of Napoleon.exe. Read-only."""
import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
EXE = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe'
im = x86re.Image(EXE)
lo = int(sys.argv[1], 16); hi = int(sys.argv[2], 16)
def isstr(v):
    try:
        s = im.section_of(v)
    except Exception:
        return None
    if not s or s[0] not in ('.rdata',): return None
    try:
        c = im.cstr(v)
    except Exception:
        return None
    if c and 1 <= len(c) < 64 and all(32 <= ord(ch) < 127 for ch in c): return c
    return None
def istext(v):
    try: s = im.section_of(v)
    except Exception: return False
    return bool(s) and s[0]=='.text'
a = lo
run = []
while a < hi:
    n, f = im.u32(a), im.u32(a+4)
    c = isstr(n)
    if c is not None and istext(f):
        run.append((a, c, f)); a += 8; continue
    if run:
        if len(run) >= 2:
            print('--- table at %08x (%d entries) end word %08x %08x' % (run[0][0], len(run), n, f))
            for (x, c2, f2) in run: print('  %08x %-32s %08x' % (x, c2, f2))
        run = []
    a += 4
