"""Repo rules that were prose, as host tests (J5): run by the `tests` gate in CI and in a full `wsc gates`.

- harness/README.md: the harness is Windows PowerShell 5.1 and ASCII-only (PS 5.1 reads a BOM-less file as the ANSI code page, so
  one non-ASCII character in a .ps1 corrupts strings or breaks parsing); data files are UTF-8 without a BOM.
- proxy/README.md "DXVK": binaries are never committed (the build and kits are generated; .gitignore refuses *.dll).
- J5 rules for fixes: a gate is never silenced by `[gates] skip` or a new exemption glob without a dated decision naming it.
"""
import subprocess
import tomllib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tracked(*globs):
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z', '--', *globs], capture_output=True, check=True).stdout
    return [p for p in out.decode('utf-8', 'replace').split('\0') if p]


def text_problems(name, data, ascii_only):
    """Problems with one file's bytes: a UTF-8 BOM, a UTF-16 BOM, and (ascii_only) any byte above 0x7F with its line."""
    errs = []
    if data[:3] == b'\xef\xbb\xbf' or data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        errs.append(f'{name}: starts with a byte-order mark')
    if ascii_only:
        body = data[3:] if data[:3] == b'\xef\xbb\xbf' else data
        for i, line in enumerate(body.split(b'\n'), 1):
            if any(b > 0x7F for b in line):
                errs.append(f'{name}:{i}: non-ASCII byte (Windows PowerShell 5.1 reads this file as ANSI)')
                break
    return errs


# The engine replaces string.find and string.sub with its own C functions, and gmatch shares their pattern code: one plain
# ("camera"):find("me", 1, true) in a battle returned nil, nil and stopped the battle UI pump about a second later (J43, run
# harness/runs/20261030_j43pc, fact napoleon.lua.string_find_stalls_pump; empire-remastered PANEL_GUIDE gotcha 20). Engine Lua uses
# match, gsub, format, lower, upper, rep, reverse, byte, char, len only.
ENGINE_STRING_BANNED = re.compile(r'(?:\bstring\s*\.\s*|:\s*)(find|sub|gmatch)\s*\(')


def engine_lua_problems(name, text):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        code = line.split('--', 1)[0]
        m = ENGINE_STRING_BANNED.search(code)
        if m:
            out.append(f'{name}:{n}: {m.group(1)} in engine Lua stops the battle pump (use match/gsub): {line.strip()[:100]}')
    return out


class Fixtures(unittest.TestCase):
    def test_engine_lua_string_ban(self):
        bad = 'local a = s:find("x")\nlocal b = string.sub(s, 1, 2)\nfor w in string.gmatch(s, ".") do end\n'
        self.assertEqual(len(engine_lua_problems('f.lua', bad)), 3)
        ok = 'local a = s:match("x") -- not :find(\nlocal b = string.gsub(s, "a", "b")\nlocal c = finder(s)\n'
        self.assertEqual(engine_lua_problems('f.lua', ok), [])

    def test_silenced(self):
        self.assertEqual(silenced({'tools': {'exempt': ['tests/**']}}, ''), [])
        self.assertEqual(len(silenced({'gates': {'skip': ['tests']}, 'docs': {'exempt': ['x.md']}}, '')), 2)
        self.assertEqual(silenced({'gates': {'skip': ['tests']}}, '| D40 | 2026-11-01 | Liam | skip `tests` because ... | yes |'), [])

    def test_text_problems(self):
        self.assertEqual(text_problems('a.ps1', b'Write-Host "ok"\r\n', True), [])
        self.assertEqual(len(text_problems('a.ps1', b'\xef\xbb\xbfWrite-Host "ok"', True)), 1)
        self.assertIn(':2: non-ASCII', text_problems('a.ps1', 'x\n# café\n'.encode(), True)[0])
        self.assertEqual(text_problems('a.json', '{"n": "café"}'.encode(), False), [])


# Exemptions that predate J5, each with its reason; anything else in wsc.toml needs a docs/DECISIONS.md row that quotes it.
GRANDFATHERED = {('tools', 'exempt', 'tests/**'): 'host tests are not tools (core C8)',
                 ('tools', 'exempt', '**/runs/**'): 'dated run evidence, not tools'}


def silenced(cfg, decisions):
    """Entries of [gates] skip and the exempt globs of [tools] and [docs] that no decision row quotes and no grandfather covers."""
    out = []
    for sect, key in (('gates', 'skip'), ('tools', 'exempt'), ('docs', 'exempt')):
        for v in cfg.get(sect, {}).get(key, []):
            if (sect, key, v) not in GRANDFATHERED and f'`{v}`' not in decisions:
                out.append(f'wsc.toml [{sect}] {key} = {v!r} has no dated decision quoting it')
    return out


class ThisRepo(unittest.TestCase):
    def test_no_gate_silenced_without_a_decision(self):
        cfg = tomllib.loads((ROOT / 'wsc.toml').read_text(encoding='utf-8'))
        self.assertEqual(silenced(cfg, (ROOT / 'docs' / 'DECISIONS.md').read_text(encoding='utf-8')), [])

    def test_harness_sources_are_ascii_and_data_has_no_bom(self):
        errs = []
        for p in tracked('harness/*.ps1', 'harness/*.psm1', 'harness/*.cmd', 'harness/*.bat'):
            errs += text_problems(p, (ROOT / p).read_bytes(), True)
        for p in tracked('harness/*.json', 'harness/*.ini', 'harness/*.xml'):
            errs += text_problems(p, (ROOT / p).read_bytes(), False)
        self.assertEqual(errs, [])

    def test_engine_lua_uses_no_replaced_string_functions(self):
        errs = []
        for p in tracked('proxy/*.lua'):
            errs += engine_lua_problems(p, (ROOT / p).read_text(encoding='utf-8', errors='replace'))
        self.assertEqual(errs, [])

    def test_no_binaries_committed(self):
        self.assertEqual(tracked('*.dll', '*.exe', '*.pdb', '*.dmp'), [])


if __name__ == '__main__':
    unittest.main()
