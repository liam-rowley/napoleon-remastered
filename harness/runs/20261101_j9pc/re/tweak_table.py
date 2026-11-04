import sys, struct, pickle
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(sys.argv[1])
hits = pickle.load(open(sys.argv[2], 'rb'))
CT = {int(x,16) for x in sys.argv[3].split(',')}
rows = []
for at, name_va, obj, tgt in hits:
    if tgt not in CT: continue
    # walk back to the initialiser start: the int3/ret before
    st = at
    for back in range(1, 0x60):
        b = im.bytes_at(at-back, 1)[0]
        if b in (0xcc, 0xc3):
            st = at-back+1; break
    strs, imm, immat, immsz = [], None, None, None
    for i in im.md.disasm(im.bytes_at(st, at-st+15), st):
        if i.address > at: break
        if i.mnemonic == 'push' and i.op_str.startswith('0x'):
            v = int(i.op_str, 16)
            if im.section_of(v)[0] == '.rdata': strs.append(im.cstr(v, 120))
        if i.mnemonic == 'mov' and 'ptr [esp' in i.op_str and ', 0x' in i.op_str or (i.mnemonic=='mov' and 'ptr [esp' in i.op_str and i.op_str.endswith(', 0')):
            imm = int(i.op_str.split(',')[1], 16); immat = i.address; immsz = i.op_str.split()[0]
            immoff = i.size - {'dword':4,'word':2,'byte':1}[immsz]
    f = struct.unpack('<f', struct.pack('<I', imm))[0] if immsz == 'dword' and imm is not None else None
    rows.append((im.cstr(name_va,80), hex(tgt), hex(obj), immsz, hex(imm) if imm is not None else None,
                 (round(f,4) if f is not None else None), hex(immat+immoff-im.base) if immat else None, strs[0][:70] if strs else ''))
for r in sorted(rows): print('\t'.join(str(x) for x in r))
