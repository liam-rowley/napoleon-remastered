"""Repo rules that were prose, as host tests (J5): run by the `tests` gate in CI and in a full `wsc gates`.

- harness/README.md: the harness is Windows PowerShell 5.1 and ASCII-only (PS 5.1 reads a BOM-less file as the ANSI code page, so
  one non-ASCII character in a .ps1 corrupts strings or breaks parsing); data files are UTF-8 without a BOM.
- proxy/README.md "DXVK": binaries are never committed (the build and kits are generated; .gitignore refuses *.dll).
- J5 rules for fixes: a gate is never silenced by `[gates] skip` or a new exemption glob without a dated decision naming it (J94: one
  docs/DECISIONS.md table row that names wsc.toml and quotes both the section and the value).
- J22: a test or tool never runs a bare `bash`: on Windows that can be the WSL launcher (other paths, other python3; J6 saw 10 test
  failures on the PC). It takes the path from tools/verbs/setup.py git_bash() (tests: bash_for_tests()).
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


# J22: an argv that starts with a literal bash (also when the list opens on the line before), a shell string handed to subprocess/os.system
# that starts with one, or a `shutil.which('bash')` (on Windows that finds the WSL launcher first; J94). Matched over the whole text with
# comments cut, so a list split over lines is seen. Python only: the shell scripts (harness/runs/**, saves/napoleon, viewer/core) hold no
# Python-style launch, and `bash -c` inside a shell script is fine (J94 checked 2026-11-04).
BARE_BASH = re.compile(r"""\[\s*['"](?:/usr/bin/|/bin/)?bash(?:\.exe)?['"]\s*[,\]]"""
                       r"""|\b(?:run|Popen|call|check_call|check_output|system)\(\s*f?['"]bash\s"""
                       r"""|\bshutil\s*\.\s*which\(\s*['"]bash(?:\.exe)?['"]\s*[,)]""")
BARE_BASH_GLOBS = ('tests/*.py', 'tools/*.py', 'tools/**/*.py', 'harness/*.py', 'harness/**/*.py', 'proxy/tools/*.py')
# file, or file::function, -> why a bare bash is right there (a Linux/CI-only file, a fixture, a check that only reports it); every entry
# needs a reason. The sanctioned way to get a bash is tools/verbs/setup.py git_bash() (tests: bash_for_tests()).
BARE_BASH_ALLOWED = {
    'tests/test_repo_rules.py': 'the BARE_BASH fixtures in Fixtures.test_bare_bash are strings, not calls',
    'tools/verbs/setup.py::check_git_bash': 'reports the bash on PATH beside git_bash() so setup can warn about the WSL launcher; never runs it',
}


def enclosing_def(text, offset):
    """Name of the last `def` that starts before `offset` (the function a hit sits in, near enough for an allow-list), or ''."""
    m = None
    for m in re.finditer(r'^[ \t]*(?:async[ \t]+)?def[ \t]+(\w+)', text[:offset], re.M):
        pass
    return m.group(1) if m else ''


def bare_bash_problems(name, text, allowed=None):
    allowed = BARE_BASH_ALLOWED if allowed is None else allowed
    lines = text.splitlines()
    code = '\n'.join(l.split('#', 1)[0] for l in lines)   # same line breaks, so an offset maps to its line
    out = []
    for m in BARE_BASH.finditer(code):
        if f'{name}::{enclosing_def(code, m.start())}' in allowed:
            continue
        n = code.count('\n', 0, m.start()) + 1
        out.append(f'{name}:{n}: bare bash (on Windows the WSL launcher): use setup.git_bash() or bash_for_tests(): {lines[n - 1].strip()[:100]}')
    return out


# J70: J12 moved proxy/core, harness/core and saves/core into the core, yet `wsc setup` kept running the old harness/core/job.sh (exit
# 127 with the watcher up). The moved folders are the tools/jobs_hooks.py PROMOTIONS keys whose job is J12; a tool naming one, as a
# slash path or a 'harness' / 'core' join, fails. jobs_hooks.py is the one exempt file: it names the old folders on purpose (rule 76,
# and fallbacks for a base before J12).
MOVED_GLOBS = ('tools/*.py', 'tools/**/*.py', 'tools/*.sh', 'tools/**/*.sh')
MOVED_ALLOWED = {
    'tools/jobs_hooks.py': 'PROMOTIONS (rule 76: the moved folder must stay gone) and the pre-J12 fallbacks for an older base',
}


def moved_folders():
    import importlib.util
    spec = importlib.util.spec_from_file_location('jobs_hooks_for_rules', ROOT / 'tools' / 'jobs_hooks.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return sorted(k for k, job in m.PROMOTIONS.items() if job == 'J12')


def moved_path_problems(name, text, folders):
    pats = []
    for f in folders:
        a, b = f.split('/')
        pats.append(re.compile(rf'(?<![\w.-]){re.escape(a)}[/\\]{re.escape(b)}\b'))
        pats.append(re.compile(rf'''['"]{re.escape(a)}['"]\s*/\s*['"]{re.escape(b)}['"]'''))
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in pats):
            out.append(f'{name}:{n}: a folder J12 moved into the core (use core/<area>/...): {line.strip()[:100]}')
    return out


class Fixtures(unittest.TestCase):
    def test_moved_paths(self):
        folders = ['harness/core', 'proxy/core', 'saves/core']
        for bad in ("run([bash, str(root / 'harness' / 'core' / 'job.sh')])", "p = 'harness/core/ctl.py'", 'x = "proxy/core/console.cpp"',
                    "ROOT / \"saves\" / \"core\"", "# see harness/core/campose.py"):
            self.assertEqual(len(moved_path_problems('f.py', bad, folders)), 1, bad)
        for ok in ("core_path(root, 'harness', 'job.sh')", "'core/harness/job.sh'", "ROOT / 'core' / 'proxy' / 'tools'",
                   "'uiscale/core'", "'harness/napoleon/adapter.json'"):
            self.assertEqual(moved_path_problems('f.py', ok, folders), [], ok)

    def test_bare_bash(self):
        for bad in ("subprocess.run(['bash', str(JOB)])", 'cmd = ["bash", "-c", x]', "p = Popen(['/usr/bin/bash'])",
                    "subprocess.run('bash -c true', shell=True)", "os.system(f'bash {x}')"):
            self.assertEqual(len(bare_bash_problems('f.py', bad)), 1, bad)
        for ok in ("subprocess.run([BASH, str(JOB)])", "which_of('bash')", "x = 'bash core/harness/job.sh'",
                   "subprocess.run(['bashful'])", "run([bash, 'x'])  # not ['bash', ...]"):
            self.assertEqual(bare_bash_problems('f.py', ok), [], ok)

    def test_bare_bash_j94_shapes(self):
        # shutil.which of bash, as an argv element or on its own (J94: it was an ok fixture before)
        for bad in ("subprocess.run([shutil.which('bash'), str(JOB)])", 'b = shutil.which("bash")', "shutil.which('bash.exe', path=p)"):
            self.assertEqual(len(bare_bash_problems('f.py', bad)), 1, bad)
        for ok in ("shutil.which('bashful')", "shutil.which('git')", "which('bash')  # an injected which, as git_bash() takes",
                   "# shutil.which('bash') in a comment"):
            self.assertEqual(bare_bash_problems('f.py', ok), [], ok)
        # an argv list whose 'bash' starts on the next line; the hit names the line of the list
        bad = "x = 1\nsubprocess.run([\n    'bash', str(JOB),\n])\n"
        self.assertEqual([p.split(':')[1] for p in bare_bash_problems('f.py', bad)], ['2'])
        for ok in ("subprocess.run([\n    BASH, str(JOB),\n])\n", "x = [\n    'bashrc',\n]\n", "x = [  # 'bash',\n    BASH]\n"):
            self.assertEqual(bare_bash_problems('f.py', ok), [], ok)
        # a file::function allow-list entry covers that function only
        two = "def check_git_bash(root, fix):\n    return shutil.which('bash')\n\n\ndef other():\n    return shutil.which('bash')\n"
        hits = bare_bash_problems('f.py', two, {'f.py::check_git_bash': 'reports it'})
        self.assertEqual([p.split(':')[1] for p in hits], ['6'])

    def test_engine_lua_string_ban(self):
        bad = 'local a = s:find("x")\nlocal b = string.sub(s, 1, 2)\nfor w in string.gmatch(s, ".") do end\n'
        self.assertEqual(len(engine_lua_problems('f.lua', bad)), 3)
        ok = 'local a = s:match("x") -- not :find(\nlocal b = string.gsub(s, "a", "b")\nlocal c = finder(s)\n'
        self.assertEqual(engine_lua_problems('f.lua', ok), [])

    def test_silenced(self):
        self.assertEqual(silenced({'tools': {'exempt': ['tests/**']}}, ''), [])
        self.assertEqual(len(silenced({'gates': {'skip': ['tests']}, 'docs': {'exempt': ['x.md']}}, '')), 2)
        skip = {'gates': {'skip': ['tests']}}
        # J94: a row that only quotes the value (any row about `tests`) no longer clears the skip
        self.assertEqual(len(silenced(skip, '| D40 | 2026-11-01 | Liam | skip `tests` because ... | yes |')), 1)
        # the section and the value in different rows do not clear it either
        self.assertEqual(len(silenced(skip, '| D40 | 2026-11-01 | Liam | `wsc.toml` `[gates] skip` is for ... | yes |\n'
                                            '| D41 | 2026-11-01 | Liam | `tests` is slow | yes |')), 1)
        self.assertEqual(len(silenced(skip, '| D40 | 2026-11-01 | Liam | wsc.toml `[docs] exempt` = `tests` | yes |')), 1)   # other section
        # one row naming wsc.toml, quoting the section and the value clears it
        self.assertEqual(silenced(skip, '| D40 | 2026-11-01 | Liam | wsc.toml `[gates] skip` = `tests` because ... | yes |'), [])
        self.assertEqual(silenced(skip, '| D40 | 2026-11-01 | Liam | `wsc.toml` `[gates]` skip `tests` because ... | yes |'), [])

    def test_text_problems(self):
        self.assertEqual(text_problems('a.ps1', b'Write-Host "ok"\r\n', True), [])
        self.assertEqual(len(text_problems('a.ps1', b'\xef\xbb\xbfWrite-Host "ok"', True)), 1)
        self.assertIn(':2: non-ASCII', text_problems('a.ps1', 'x\n# café\n'.encode(), True)[0])
        self.assertEqual(text_problems('a.json', '{"n": "café"}'.encode(), False), [])


# Exemptions that predate J5, each with its reason; anything else in wsc.toml needs a docs/DECISIONS.md row that quotes it.
GRANDFATHERED = {('tools', 'exempt', 'tests/**'): 'host tests are not tools (core C8)',
                 ('tools', 'exempt', '**/runs/**'): 'dated run evidence, not tools'}


def quoted_by_a_row(decisions, sect, v):
    """True when one decision table row (one `|` line) names wsc.toml, quotes the section (`` `[gates]` ``, `` `[gates] skip` ``, ...)
    and quotes the value (`` `tests` ``). A row that only mentions the value, such as any row about `tests`, is not enough (J94)."""
    sect_q = re.compile(r'`[^`\n]*\[' + re.escape(sect) + r'\][^`\n]*`')
    return any(l.lstrip().startswith('|') and 'wsc.toml' in l and sect_q.search(l) and f'`{v}`' in l for l in decisions.splitlines())


def silenced(cfg, decisions):
    """Entries of [gates] skip and the exempt globs of [tools] and [docs] that no decision row quotes and no grandfather covers."""
    out = []
    for sect, key in (('gates', 'skip'), ('tools', 'exempt'), ('docs', 'exempt')):
        for v in cfg.get(sect, {}).get(key, []):
            if (sect, key, v) not in GRANDFATHERED and not quoted_by_a_row(decisions, sect, v):
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

    def test_no_bare_bash_in_tests_and_tools(self):
        errs = []
        for p in sorted(set(tracked(*BARE_BASH_GLOBS))):
            if p not in BARE_BASH_ALLOWED:
                errs += bare_bash_problems(p, (ROOT / p).read_text(encoding='utf-8', errors='replace'))
        self.assertEqual(errs, [])
        self.assertTrue(all(BARE_BASH_ALLOWED.values()), 'every allow-list entry names its reason')

    def test_no_pre_j12_core_paths_in_tools(self):
        folders = moved_folders()
        self.assertEqual(folders, ['harness/core', 'proxy/core', 'saves/core'])
        errs = []
        for p in sorted(set(tracked(*MOVED_GLOBS))):
            if p not in MOVED_ALLOWED:
                errs += moved_path_problems(p, (ROOT / p).read_text(encoding='utf-8', errors='replace'), folders)
        self.assertEqual(errs, [])
        self.assertTrue(all(MOVED_ALLOWED.values()), 'every allow-list entry names its reason')

    def test_no_binaries_committed(self):
        self.assertEqual(tracked('*.dll', '*.exe', '*.pdb', '*.dmp'), [])


if __name__ == '__main__':
    unittest.main()
