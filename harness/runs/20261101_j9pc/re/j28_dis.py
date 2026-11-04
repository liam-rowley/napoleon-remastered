"""j28_dis.py - disassemble Napoleon.exe at VAs: j28_dis.py va[:n] ... Read-only."""
import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe')
stop = '-r' in sys.argv
for a in [x for x in sys.argv[1:] if x != '-r']:
    va, _, n = a.partition(':'); va = int(va, 16); n = int(n) if n else 40
    print('=== %08x' % va)
    for i in im.dis(va, n, stop_ret=stop):
        print('  %08x  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
