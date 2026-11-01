"""Find the Lua 5.1 C API functions in Napoleon.exe by masked byte signatures taken from Empire.exe at Empire's known LAPI addresses
(lapi_map.py, empire-remastered, read-only). Relocated dwords and rel32 call/jmp targets are wildcarded."""
import sys, re, struct, json
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
sys.path.insert(0, r'C:\Users\liamr\repos\empire-remastered\rml_mod\tools\controls\re\lua_api')
import x86re
from lapi_map import LAPI
nap = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe')
emp = x86re.Image(r'C:\Program Files (x86)\Steam\steamapps\common\Empire Total War\Empire.exe')
erel = set(emp.relocs())
T0, TSZ = nap.text[1], nap.text[2]
NT = bytes(nap.img[T0 - nap.base:T0 - nap.base + TSZ])

def sig(va, maxlen=64):
    pat = b''; n = 0
    for ins in emp.md.disasm(emp.bytes_at(va, 200), va):
        b = bytearray(ins.bytes)
        mask = [False] * len(b)
        for k in range(len(b) - 3):
            if ins.address + k in erel:
                for j in range(4): mask[k + j] = True
        if ins.mnemonic in ('call', 'jmp') or ins.mnemonic.startswith('j'):
            if b[0] in (0xe8, 0xe9): mask[1:5] = [True] * 4
            elif b[0] == 0x0f and len(b) == 6: mask[2:6] = [True] * 4
        for x, m in zip(b, mask):
            pat += b'.' if m else re.escape(bytes([x]))
        n += len(b)
        if ins.mnemonic in ('ret', 'retn') or n >= maxlen: break
    return pat, n

out = {}
for va, name in sorted(LAPI.items(), key=lambda x: x[1]):
    pat, n = sig(va)
    hits = [T0 + m.start() for m in re.finditer(pat, NT, re.S)]
    # function starts only (preceded by int3/ret padding or 16-aligned)
    hs = [h for h in hits if h % 16 == 0 or NT[h - T0 - 1] in (0xcc, 0xc3, 0x90)]
    out[name] = dict(empire=hex(va), siglen=n, hits=[hex(h) for h in hs[:6]], nhits=len(hs))
    print('%-22s emp %x len %3d hits %s' % (name, va, n, out[name]['hits'] if len(hs) < 6 else '%d' % len(hs)))
json.dump(out, open(sys.argv[1], 'w'), indent=1)
