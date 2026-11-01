import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe')
for a in sys.argv[2:]:
    va = int(a, 16); print('==', hex(va))
    for ins in im.dis(va, int(sys.argv[1])):
        print('  %x  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret' and sys.argv[1].startswith('0'): break
