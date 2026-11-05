"""This repo's discovery data against the core's discovery tools (J64): the committed results, registries and adapter files pass the core's checks.

The passes themselves are warscape-core's since v0.15.0 and their unit tests run in the core (`core/discovery/tests/`); what stays here are the tests that
read this repo's real data (the 88,415-row index, the committed diff files, the generated READMEs, the registries, the briefs), moved out of the old
tests/test_discovery*.py, test_engine_api.py and test_exe_strings.py. The effects pass is this repo's (discovery/napoleon/effects.py, tests/test_discovery_effects.py).
Everything reads committed files only; nothing here needs the game, Pillow or capstone.
"""
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'core' / 'discovery'))
sys.path.insert(0, str(ROOT / 'core'))

import assets  # noqa: E402
import briefpaths as bp  # noqa: E402
import diffout  # noqa: E402
import engine_api  # noqa: E402
import exe_strings  # noqa: E402
import tsvgz  # noqa: E402

LEGACY_BRIEFS = frozenset(json.loads((ROOT / 'jobs' / 'legacy.json').read_text(encoding='utf-8'))['brief_hooks'])   # exempt from the brief hooks only


def wsc(*args):
    return subprocess.run([sys.executable, str(ROOT / 'core' / 'wsc.py'), *args], cwd=str(ROOT), capture_output=True, text=True,
                          env=dict(os.environ, PYTHONIOENCODING='utf-8'))


class CoreVerb(unittest.TestCase):
    def test_discovery_check_passes_on_every_committed_result_and_readme(self):
        r = wsc('discovery', 'check')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('READMEs current', r.stdout)

    def test_the_gate_passes_on_the_real_registries_and_says_the_install_was_not_compared(self):
        r = wsc('discovery', 'gate')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(any(x.startswith('warn install not compared') for x in r.stdout.splitlines()), r.stdout)
        self.assertFalse(any(x.startswith('ok   install') for x in r.stdout.splitlines()))


class CommittedResults(unittest.TestCase):
    def test_committed_diff_files_pass_the_schema(self):
        d = ROOT / 'discovery' / 'diff'
        for f in sorted(d.glob('*.json')):
            with self.subTest(f=f.name):
                self.assertEqual(diffout.problems(json.loads(f.read_text(encoding='utf-8'))), [])

    def test_committed_registry_ids_are_unique(self):
        reg = assets.read_registry(str(ROOT / 'registries' / 'assets.jsonl'))
        self.assertEqual(len({r['id'] for r in reg}), len(reg))

    def test_probe_safe_list_is_current(self):
        self.assertEqual(engine_api.main(['probe-safe', '--check']), 0, 'discovery/napoleon/probe_safe.json is stale: rerun probe-safe')

    def test_engine_api_table_is_current(self):
        out = Path(engine_api.OUT)
        doc = json.loads(out.read_text(encoding='utf-8'))
        runs = [Path(engine_api.REPO) / r for r in doc['runs']]
        missing = [str(r) for r in runs if not (r / 'raw').is_dir()]
        if missing:
            self.skipTest(f'{missing} not present')
        args = ['build'] + [x for r in runs for x in ('--run', str(r))] + ['--check']
        self.assertEqual(engine_api.main(args), 0, 'discovery/napoleon/engine_api.json is stale: rebuild it')

    def test_committed_exe_strings_table_reads(self):
        table = Path(exe_strings.TABLE)
        self.assertTrue(table.exists(), 'discovery/napoleon/exe_strings.tsv.gz is committed')
        header, rows = tsvgz.read(table)
        self.assertEqual(header, exe_strings.HEADER)
        self.assertEqual(tsvgz.problems(str(table), exe_strings.HEADER), [])
        self.assertEqual(rows, sorted(rows), 'rows sorted (deterministic)')
        self.assertGreater(len(rows), 20000)


class Briefs(unittest.TestCase):
    # sha256 of '\n'.join(ids): the frozen set, checked in every clone, a depth-1 one included (J73)
    FROZEN_SHA256 = '059f0a5b218cb562aa7ed5fc4a3df45d57add323e312f8c8c98c502aab321a05'

    def test_the_legacy_set_still_hashes_to_its_constant(self):
        ids = json.loads((ROOT / 'jobs' / 'legacy.json').read_text(encoding='utf-8'))['brief_hooks']
        self.assertEqual(hashlib.sha256('\n'.join(ids).encode()).hexdigest(), self.FROZEN_SHA256)

    def test_the_legacy_set_is_every_brief_on_main_at_j11s_base(self):
        out = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'c674fb1', 'jobs'], capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest('J11 base commit not in this clone (the constant half above still runs)')
        on_main = {p.split('/')[1] for p in out.stdout.split() if p.endswith('/brief.md')}
        self.assertEqual(on_main | {'J24', 'J37'}, set(LEGACY_BRIEFS))   # J24 and J37 merged before J11 did

    def test_every_committed_brief_passes_the_found_path_rule_or_is_legacy(self):
        known = bp.load_known(ROOT)
        bad = []
        for p in sorted((ROOT / 'jobs').glob('*/brief.md')):
            if p.parent.name not in LEGACY_BRIEFS:
                bad += [f'{p.parent.name}: {e}' for e in bp.found_path_problems(p.read_text(encoding='utf-8'), known)]
        self.assertEqual(bad, [])

    def test_the_four_cases_the_rule_exists_for_fail_on_the_real_registries(self):
        known = bp.load_known(ROOT)
        unit = next(u for u in known.ui_ids if u.startswith('battle.'))
        path = next(k for k, v in known.ui_paths.items() if unit in v and ' ' in k)
        self.assertTrue(bp.found_path_problems(f'Open `{path}`.', known))
        self.assertEqual(bp.found_path_problems(f'Open `{unit}`.', known), [])


if __name__ == '__main__':
    unittest.main()
