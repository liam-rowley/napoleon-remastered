"""j28_guard.py - for each J28 candidate VA print RVA, first 16 bytes, relocated dwords overlapping the first 16 bytes
(offset of each dword start), the first ret (with its imm) and the E8 caller count. Read-only."""
import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe')
rel = set(im.relocs())
for a in sys.argv[1:]:
    v = int(a, 16)
    r = [x - v for x in range(v - 3, v + 16) if x in rel]
    ret = next((i for i in im.dis(v, 400) if i.mnemonic.startswith('ret')), None)
    print('%08x rva %07x  %s  relocs@%s  first8:%s  %s  callers %d' % (
        v, v - 0x400000, im.bytes_at(v, 16).hex(' '), r, 'YES' if any(-3 <= x < 8 for x in r) else 'no',
        ('%s %s @%08x' % (ret.mnemonic, ret.op_str, ret.address)) if ret else '-', len(im.callers(v))))
