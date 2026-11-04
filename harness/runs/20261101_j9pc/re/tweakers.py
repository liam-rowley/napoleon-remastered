import sys, struct, re, collections
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
im = x86re.Image(sys.argv[1])
# find calls preceded within 3 insns by `mov ecx, imm32` and `push <str>` (name); collect ctor targets
t0, tsz = im.text[1], im.text[2]
data = im.img[t0-im.base:t0-im.base+tsz]
ctors = collections.Counter()
hits = []
for m in re.finditer(rb'\x68(....)\xb9(....)\xe8(....)', data, re.S):
    o = m.start()
    name_va = struct.unpack('<I', m.group(1))[0]
    obj = struct.unpack('<I', m.group(2))[0]
    tgt = t0 + o + 15 + struct.unpack('<i', m.group(3))[0]
    sec, _ = im.section_of(name_va)
    if sec != '.rdata': continue
    ctors[tgt] += 1
    hits.append((t0+o, name_va, obj, tgt))
for t, n in ctors.most_common(15):
    print(hex(t), n)
import pickle; pickle.dump(hits, open(sys.argv[2], 'wb'))
