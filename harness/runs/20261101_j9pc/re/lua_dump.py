import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe')
for a in sys.argv[2:]:
    va = int(a, 16)
    print('==', hex(va), 'refs', [hex(r) for r in im.refs(va)[:4]])
    for k in range(-int(sys.argv[1]), int(sys.argv[1]), 4):
        v = im.u32(va + k)
        s = ''
        if im.section_of(v)[0] in ('.rdata', '.data'):
            try: s = repr(im.cstr(v, 40))
            except Exception: pass
        print('  %x: %08x %s %s' % (va + k, v, 'T' if im.in_text(v) else ' ', s))
