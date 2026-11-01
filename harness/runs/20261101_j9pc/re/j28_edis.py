"""j28_edis.py - disassemble an exe (default Empire.exe, or --nap for Napoleon.exe) from bytes_at (section-aware). Read-only.
Usage: j28_edis.py [--nap] [-r] va[:n] ...   (-r stops at the first ret)"""
import sys
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re, capstone
NAP = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe'
EMP = r'C:\Program Files (x86)\Steam\steamapps\common\Empire Total War\Empire.exe'
nap = '--nap' in sys.argv
im = x86re.Image(NAP if nap else EMP)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
stop = '-r' in sys.argv
for a in [x for x in sys.argv[1:] if not x.startswith('-')]:
    va, _, n = a.partition(':'); va = int(va, 16); n = int(n) if n else 40
    print('=== %08x' % va)
    k = 0
    for i in md.disasm(im.bytes_at(va, n * 15), va):
        print('  %08x  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)); k += 1
        if k >= n or (stop and i.mnemonic in ('ret', 'retn')): break
