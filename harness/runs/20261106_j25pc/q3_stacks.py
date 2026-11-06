#!/usr/bin/env python3
"""J25 question 3: the two logged call chains (raw/d_tint/proxy.log, `cascade: stack at`) resolved statically: each return address, the call before it, its function.

Run evidence (as J24's helpers), not a registered tool. usage: <re venv python> harness/runs/20261106_j25pc/q3_stacks.py <exe> <proxy.log>
The log prints runtime addresses (the header's ImageBase after relocation); the patch engine's `patch RVA x -> y` lines give the load delta. A stack scan
finds stale values too, so a line counts as a frame only when the bytes before it are a call. Functions start after int3 padding.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'core' / 'discovery'))
import x86re  # noqa: E402

im = x86re.Image(sys.argv[1])
log = open(sys.argv[2], encoding='latin1').read()
rva, rt = re.search(r'patch RVA 0x([0-9a-f]+) -> ([0-9a-f]+)', log).groups()
delta = int(rt, 16) - int(rva, 16) - im.base
print(f'load delta {delta:#x}')


def func_start(va):
    p = va
    while p > va - 0x4000:
        if im.bytes_at(p - 1, 1) == b'\xcc' and im.bytes_at(p, 1) != b'\xcc':
            return p
        p -= 1
    return None


def call_before(ret):
    for n in (2, 3, 5, 6, 7):
        ins = list(im.md.disasm(im.bytes_at(ret - n, n), ret - n))
        if len(ins) == 1 and ins[0].mnemonic == 'call' and ins[0].size == n:
            return f'{ins[0].mnemonic} {ins[0].op_str}'
    return None


for what, chain in re.findall(r'cascade: stack at ([a-z ]+): ([0-9a-f ]+)', log):
    print(f'== {what}')
    for a in chain.split():
        v = int(a, 16) - delta
        c = call_before(v)
        print(f'  {v:#x}  ' + (f'in {func_start(v):#x}: {c}' if c and func_start(v) else 'not a call site'))
