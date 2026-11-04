"""j28_disp.py - list instructions with a given disp32 (movss/mov/lea/fld forms, any base reg) in an exe's .text. Read-only.
usage: j28_disp.py emp|nap disp [disp...]"""
import sys, re
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
P = {'emp': r'C:\Program Files (x86)\Steam\steamapps\common\Empire Total War\Empire.exe',
     'nap': r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe'}
im = x86re.Image(P[sys.argv[1]])
s = [x for x in im.sections if x[0] == '.text'][0]; t0 = s[1]; buf = im.bytes_at(t0, s[2])
for d in sys.argv[2:]:
    o = int(d, 16); db = o.to_bytes(4, 'little')
    out = []
    for m in re.finditer(re.escape(db), buf):
        va = t0 + m.start()
        # try decoding an instruction that ends with or contains this disp, starting 2..4 bytes before
        for back in (2, 3, 4):
            ins = list(im.md.disasm(im.bytes_at(va - back, 12), va - back))
            if ins and hex(o) in ins[0].op_str and '[' in ins[0].op_str and ins[0].size >= back + 4:
                out.append((ins[0].address, ins[0].mnemonic, ins[0].op_str)); break
    print('disp %s: %d' % (hex(o), len(out)))
    for a, mn, op in out[:int(sys.argv[0] and 400)]:
        print('  %08x %s %s' % (a, mn, op))
