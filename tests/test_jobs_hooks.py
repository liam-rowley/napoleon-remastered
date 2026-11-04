"""Host tests for tools/jobs_hooks.py, napoleon's hook module for the core's job pipeline (napoleon J62): rule 76 (promotion folders), rule 75 (the PC line of
the page), rule 79 (acceptance passes, with the core-pin diff of J58), the legacy id sets (jobs/legacy.json) and the found-path brief hook.

Moved from tests/test_jobs.py and tests/test_pr_policy.py; the generic rules are tested in warscape-core (tests/test_jobs.py, test_policy.py, test_fixture_game.py).
"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('jobs_hooks', ROOT / 'tools' / 'jobs_hooks.py')
hk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hk)

ROW = {'id': 'J1', 'status': 'queued', 'brief': 'jobs/J1/brief.md'}
OTHER = {'id': 'J2', 'status': 'needs_brief'}


def row(jid='J1', **kw):
    r = {'id': jid, 'description': 'd', 'title': 't', 'phase': 1, 'status': 'needs_brief', 'model': 'opus', 'needs_pc': False,
         'depends_on': []}
    r.update(kw)
    return r


def files(**kw):
    return lambda p: kw.get(p)


class Promotions(unittest.TestCase):
    """Rule 76 (J12): core candidate folders and the jobs that promote them."""
    T = {'proxy/core': 'J12', 'discovery/core': None}

    def test_listed_folders_pass_while_the_job_is_open(self):
        self.assertEqual(hk.promotion_problems([row('J12', status='review')], {'proxy/core', 'proxy/core/x', 'discovery/core'}, self.T), [])

    def test_failing_fixture_a_folder_whose_promotion_is_done_must_be_gone(self):
        e = hk.promotion_problems([row('J12', status='done')], {'proxy/core'}, self.T)
        self.assertEqual(len(e), 1); self.assertIn('promotion job J12 is done', e[0])
        self.assertEqual(hk.promotion_problems([row('J12', status='done')], {'proxy/napoleon'}, self.T), [])   # gone: fine

    def test_failing_fixture_an_unlisted_core_folder_fails(self):
        e = hk.promotion_problems([row('J12')], {'audio/core/a'}, self.T)
        self.assertEqual(len(e), 1); self.assertIn('audio/core/ is a core candidate with no promotion job', e[0])

    def test_the_submodule_and_unknown_jobs(self):
        self.assertEqual(hk.promotion_problems([], {'core/proxy/src', 'core/warscape'}, self.T), [])   # the core itself is not a candidate
        self.assertIn('has no row', hk.promotion_problems([], {'proxy/core'}, self.T)[0])

    def test_the_repo_table_covers_every_core_folder_here(self):
        root = Path(__file__).resolve().parent.parent
        tracked = subprocess.run(['git', '-C', str(root), 'ls-files'], capture_output=True, text=True).stdout.split()
        rows = [json.loads(p.read_text(encoding='utf-8')) for p in (root / 'registries' / 'jobs').glob('*.json')]
        self.assertEqual(hk.promotion_problems(rows, {str(Path(f).parent.as_posix()) for f in tracked}), [])


class PcState(unittest.TestCase):
    """Rule 75 (J44): on the PC the view shows the lock holder, the watcher version, the installed kit, the last acceptance pass and a usage source."""
    def test_reads_the_state_folder_and_the_ledger(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            state, repo = d / 'state', d / 'repo'
            (state / 'watcher').mkdir(parents=True)
            (repo / 'harness' / 'napoleon').mkdir(parents=True)
            (repo / 'harness' / 'acceptance').mkdir(parents=True)
            (repo / 'harness' / 'napoleon' / 'adapter.json').write_text(json.dumps({'state_dir': str(state), 'watcher_subdir': 'watcher'}))
            (state / 'watcher' / 'game.lock').write_text('owner=j44 session=s purpose=p started=t\n')
            (state / 'watcher' / 'watcher.status').write_text(json.dumps({'version': '1.0.1', 'game_state': {'state': 'not_running'}}))
            (state / 'watcher' / 'watcher.alive').write_text('x')
            (state / 'install.json').write_text(json.dumps({'kit_id': 'kit_1', 'build_id': 'abc'}))
            (repo / 'harness' / 'acceptance' / 'ledger.jsonl').write_text(json.dumps({'pass': 3, 'result': 'pass', 'build_id': 'abc', 'watcher': '1.0.1', 'utc': 'u', 'run': 'r'}) + '\n')
            pc = hk.pc_state(repo, projects_dir=d / 'no-claude-projects')
            self.assertIn('owner=j44', pc['lock'])
            self.assertEqual((pc['watcher'], pc['kit'], pc['last_acceptance']['pass'], pc['last_acceptance']['result']), ('1.0.1', 'kit_1', 3, 'pass'))
            self.assertTrue(pc['usage'])
            block = hk.pc_block(pc)
            for want in ('owner=j44', '1.0.1', 'kit_1', 'pass 3 pass', 'usage source'):
                self.assertIn(want, block)

    def test_off_the_pc_there_is_no_block(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'harness' / 'napoleon').mkdir(parents=True)
            (Path(d) / 'harness' / 'napoleon' / 'adapter.json').write_text(json.dumps({'state_dir': str(Path(d) / 'nope')}))
            self.assertIsNone(hk.pc_state(d))
            self.assertEqual(hk.pc_block(None), '')


class Rule79(unittest.TestCase):
    """J4 rule 79: a job branch that changes proxy/ or harness/ needs 20 consecutive acceptance passes on its final build."""
    CHECKER = (ROOT / 'core' / 'harness' / 'acceptance.py').read_text(encoding='utf-8')

    @staticmethod
    def led(n, build='abc', watcher='1.0.1', fail_at=None, evidence=True, branch='job/J9'):
        return '\n'.join(json.dumps({'pass': i, 'build_id': build, 'watcher': watcher, 'branch': branch, 'result': 'fail' if i == fail_at else 'pass',
                                     **({'run': 'harness/runs/r', 'evidence': f'harness/runs/r/pass_{i:02d}.json'} if evidence else {})})
                         for i in range(1, n + 1)) + '\n'

    def acc(self, ledger, active=True, exists=lambda p: True):
        return {'active': active, 'ledger': ledger, 'build_id': 'abc', 'watcher': '1.0.1', 'branch': 'job/J9', 'exists': exists}

    @staticmethod
    def baseline():
        kinds = ('land', 'siege', 'naval', 'historical', 'campaign')
        steps = [{'scenario': f'{k}_x', 'kind': k, 'pose': 'wide', 'load_time_s': 20.0, 'load_tolerance_pct': 50, 'shot': f'{k}.jpg',
                  'shot_threshold': 4.0, 'deterministic': True} for k in kinds]
        return {'schema': 1, 'date': '2026-10-30', 'build_id': 'abc', 'fresh_boot': True, 'size': '1920x1080', 'exe_sha1': 'pin', 'steps': steps,
                'settings_files': ['prefs']}

    def test_failing_fixture_ledger_lines_without_committed_evidence_do_not_count(self):
        # J4 review 7: a hand-written line is a claim, not evidence; the run folder's pass file must be on the branch
        errs = hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20), exists=lambda p: p != 'harness/runs/r/pass_20.json'))
        self.assertEqual(len(errs), 1)
        self.assertIn('0 consecutive', errs[0])
        self.assertIn('not committed', errs[0])
        self.assertTrue(hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20, evidence=False))))

    def test_a_branch_weakening_its_own_checker_cannot_switch_the_rule_off(self):
        # J4 review round 2: the base's acceptance.py judges the baseline, not the branch's copy
        b = json.dumps(self.baseline())
        weak = self.CHECKER.replace('def baseline_problems(b):', 'def baseline_problems(b):\n    return ["always"]\n\ndef _old(b):')
        self.assertFalse(hk.acceptance_active('', b, weak))           # a weakened checker would say inactive...
        self.assertTrue(hk.acceptance_active('', b, self.CHECKER))    # ...but main() passes the base's text, which says active
        src = (ROOT / 'tools' / 'jobs_hooks.py').read_text(encoding='utf-8')
        self.assertIn('show_first(root, base, *ACC_CHECKERS)', src)   # the base's checker, in either layout (J12)
        self.assertNotIn("spec_from_file_location('acceptance'", src)

    def test_failing_fixture_another_branchs_passes_do_not_count(self):
        # J44 review: harness/ is not in the build id, so a harness-only branch on main's build would inherit the last merged branch's 20
        errs = hk.acceptance_problems(['harness/napoleon/adapter.json'], self.acc(self.led(20, branch='job/J8')))
        self.assertEqual(len(errs), 1)
        self.assertIn('another branch', errs[0])
        self.assertTrue(hk.acceptance_problems(['harness/napoleon/adapter.json'], self.acc(self.led(20, branch=None))))
        self.assertIn("'branch': facts['branch']", (ROOT / 'tools' / 'jobs_hooks.py').read_text(encoding='utf-8'))

    def test_exemptions_match_segments_not_substrings(self):
        self.assertFalse(hk.acc_exempt('proxy/core/README.md.bak'))
        self.assertFalse(hk.acc_exempt('proxy/core/reruns/x.cpp'))
        self.assertTrue(hk.acc_exempt('harness/runs/x/a.json'))

    def test_failing_fixture_a_code_change_without_20_passes_is_refused(self):
        errs = hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(19)))
        self.assertEqual(len(errs), 1)
        self.assertIn('19 consecutive', errs[0])

    def test_20_passes_on_this_build_pass(self):
        self.assertEqual(hk.acceptance_problems(['harness/napoleon/adapter.json'], self.acc(self.led(20))), [])

    def test_a_fail_resets_the_count(self):
        self.assertTrue(hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(25, fail_at=10))))   # 15 after the fail

    def test_another_build_or_watcher_does_not_count(self):
        self.assertTrue(hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20, build='old'))))
        self.assertTrue(hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20, watcher='0.9'))))

    def test_runs_docs_and_non_code_changes_are_exempt(self):
        for p in ('proxy/runs/x/README.md', 'harness/runs/y/raw/a.log', 'proxy/README.md', 'harness/acceptance/ledger.jsonl', 'docs/a.md', 'registries/x.jsonl'):
            self.assertEqual(hk.acceptance_problems([p], self.acc('')), [], p)

    def test_inactive_until_the_ledger_is_on_the_base(self):
        self.assertEqual(hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc('', active=False)), [])
        self.assertEqual(hk.acceptance_problems(['proxy/core/dev.cpp'], None), [])

    def test_a_ledger_without_a_valid_baseline_does_not_activate_it(self):
        # J4 review 1: the empty ledger alone switched the rule on, and nothing could satisfy it (no baseline, run not wired)
        self.assertFalse(hk.acceptance_active('', None, self.CHECKER))
        self.assertFalse(hk.acceptance_active('', '{"schema": 1}', self.CHECKER))
        self.assertFalse(hk.acceptance_active('', 'not json', self.CHECKER))
        self.assertFalse(hk.acceptance_active('', json.dumps(self.baseline()), None))
        self.assertEqual(hk.acceptance_problems(['proxy/core/dev.cpp'], self.acc('', active=hk.acceptance_active('', None, self.CHECKER))), [])

    def test_a_ledger_and_a_valid_baseline_activate_it(self):
        b = self.baseline()
        self.assertTrue(hk.acceptance_active('', json.dumps(b), self.CHECKER))
        self.assertFalse(hk.acceptance_active(None, json.dumps(b), self.CHECKER))

    def _repo_with_passes(self, d):
        """A fixture repo holding the DLL inputs (the real build_id.py), and 20 passes on its content id for job/J9."""
        g = lambda *a: subprocess.run(['git', *a], cwd=d, capture_output=True, text=True, check=True)
        g('init', '-q', '-b', 'job/J9'); g('config', 'user.email', 't@example.invalid'); g('config', 'user.name', 'test')
        for rel, data in (('proxy/core/a.cpp', b'int a;\n'), ('proxy/napoleon/adapter.cpp', b'int b;\n'), ('proxy/tools/build.sh', b'#!\n'),
                          ('proxy/tools/fetch_lua.py', b'#\n'), ('proxy/tools/fetch_ui.py', b'#\n'), ('viewer/pins.json', b'{}\n'),('proxy/tools/build_id.py', (ROOT / 'core/proxy/tools/build_id.py').read_bytes())):
            (Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(d) / rel).write_bytes(data)
        g('add', '-A'); g('commit', '-q', '-m', 'J9: proxy change')
        built = hk.dll_build_id(d)
        acc = lambda: dict(self.acc(self.led(20, build=built)), build_id=hk.dll_build_id(d))
        return g, acc

    def test_failing_fixture_a_reword_after_the_20_passes_still_passes(self):
        # J44 review 2: the id was the commit hash of the last input change, so this reword cost J44 a whole 20-pass run (J45)
        with tempfile.TemporaryDirectory() as d:
            g, acc = self._repo_with_passes(d)
            g('commit', '-q', '--amend', '-m', 'J9: proxy change (reworded, trailer added)')
            self.assertEqual(hk.acceptance_problems(['proxy/core/a.cpp'], acc()), [])

    def test_failing_fixture_an_input_change_after_the_20_passes_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            g, acc = self._repo_with_passes(d)
            (Path(d) / 'proxy/core/a.cpp').write_text('int a2;\n')
            g('commit', '-q', '-am', 'J9: one more proxy change')
            errs = hk.acceptance_problems(['proxy/core/a.cpp'], acc())
            self.assertEqual(len(errs), 1)
            self.assertIn('0 consecutive', errs[0])

    def test_check_wires_it_into_job_branches(self):
        ctx = types.SimpleNamespace(root=ROOT)
        errs = hk.policy_problems(ctx, {'kind': 'job', 'changed': ['proxy/core/dev.cpp'], 'acceptance': self.acc(self.led(3))})
        self.assertTrue(any('rule 79' in e for e in errs))
        self.assertEqual(hk.policy_problems(ctx, {'kind': 'brief', 'changed': ['proxy/core/dev.cpp'], 'acceptance': self.acc(self.led(3))}), [])


class CorePin(unittest.TestCase):
    """J58: a core pin bump counts for rule 79 only when the core's own proxy/ or harness/ changed between the two pins."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.core, self.game = Path(self.tmp.name) / 'core_src', Path(self.tmp.name) / 'game'
        for d in (self.core, self.game):
            d.mkdir()
            self.g(d, 'init', '-q', '-b', 'main'); self.g(d, 'config', 'user.email', 't@example.invalid'); self.g(d, 'config', 'user.name', 'test')
        self.write(self.core, {'proxy/src/a.cpp': 'int a;\n', 'harness/job.sh': '#!\n', 'docs/x.md': 'x\n', 'warscape/w.py': '#\n'})
        self.g(self.game, '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(self.core), 'core')
        self.g(self.game, 'commit', '-q', '-m', 'pin core')
        self.base_pin = self.g(self.game, 'rev-parse', 'HEAD:core')

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def g(d, *a):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *a], cwd=d, capture_output=True, text=True, check=True).stdout.strip()

    def write(self, repo, files):
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text, encoding='utf-8', newline='\n')
        self.g(repo, 'add', '-A'); self.g(repo, 'commit', '-q', '-m', 'core change')

    def bump(self, files):
        """A second core commit, pinned by a new game commit; returns rule 79's errors for the pin change on an empty ledger."""
        self.write(self.core, files)
        self.g(self.game / 'core', '-c', 'protocol.file.allow=always', 'fetch', '-q', 'origin', 'main')
        self.g(self.game / 'core', 'checkout', '-q', 'FETCH_HEAD')
        self.g(self.game, 'commit', '-q', '-am', 'bump core')
        diff = hk.core_pin_diff('HEAD~1', 'HEAD', self.game)
        acc = {'active': True, 'ledger': '', 'build_id': 'abc', 'watcher': '1.0.1', 'branch': 'job/J9', 'exists': lambda p: True, 'core_diff': diff}
        return diff, hk.acceptance_problems(['core'], acc)

    def test_a_bump_of_docs_and_python_only_needs_no_passes(self):
        diff, errs = self.bump({'docs/x.md': 'y\n', 'warscape/w.py': '# 2\n'})
        self.assertEqual(sorted(diff), ['docs/x.md', 'warscape/w.py'])
        self.assertEqual(errs, [])

    def test_failing_fixture_a_bump_that_changes_the_cores_proxy_is_refused(self):
        diff, errs = self.bump({'proxy/src/a.cpp': 'int a2;\n', 'docs/x.md': 'y\n'})
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('changes core/proxy/src/a.cpp but', errs[0])
        self.assertIn('0 consecutive', errs[0])

    def test_failing_fixture_a_bump_that_changes_the_cores_harness_is_refused(self):
        self.assertTrue(self.bump({'harness/job.sh': '#! 2\n'})[1])

    def test_failing_fixture_a_file_moved_out_of_the_cores_proxy_is_refused(self):
        (self.core / 'docs').joinpath('a.cpp').write_text('int a;\n', encoding='utf-8', newline='\n')
        (self.core / 'proxy/src/a.cpp').unlink()
        diff, errs = self.bump({})
        self.assertIn('proxy/src/a.cpp', diff)
        self.assertEqual(len(errs), 1, errs)

    def test_exempt_paths_inside_the_core_do_not_count(self):
        diff, errs = self.bump({'harness/runs/r/a.json': '{}\n', 'proxy/README.md': 'r\n', 'saves/esf.py': '#\n'})
        self.assertEqual(len(diff), 3)
        self.assertEqual(errs, [])

    def test_failing_fixture_a_base_pin_missing_from_the_core_fails_closed(self):
        missing = 'f' * 40
        self.g(self.game, 'update-index', '--cacheinfo', f'160000,{missing},core')
        self.g(self.game, 'commit', '-q', '-m', 'pin a commit the core checkout lacks')
        diff = hk.core_pin_diff('HEAD', 'HEAD~1', self.game)
        self.assertIsInstance(diff, str)
        self.assertIn(f'cannot compare core pins ffffffffffff..{self.base_pin[:12]}', diff)
        self.assertIn(f'git -C core fetch origin {missing}', diff)
        acc = {'active': True, 'ledger': '', 'build_id': 'abc', 'watcher': '1.0.1', 'branch': 'job/J9', 'exists': lambda p: True, 'core_diff': diff}
        errs = hk.acceptance_problems(['core'], acc)
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('cannot compare core pins', errs[0])
        self.assertTrue(hk.acceptance_problems(['core'], dict(acc, core_diff=None)))   # no diff computed counts too

    def test_a_branch_that_also_changes_this_repos_proxy_is_judged_as_before(self):
        acc = {'active': True, 'ledger': '', 'build_id': 'abc', 'watcher': '1.0.1', 'branch': 'job/J9', 'exists': lambda p: True, 'core_diff': ['docs/x.md']}
        errs = hk.acceptance_problems(['core', 'proxy/napoleon/adapter.cpp'], acc)
        self.assertEqual(len(errs), 1)
        self.assertIn('changes proxy/napoleon/adapter.cpp but', errs[0])

    def test_main_passes_the_merge_bases_pin_diff(self):
        self.assertIn("'core_diff': core_pin_diff(mb, 'HEAD', root) if 'core' in changed else None", (ROOT / 'tools' / 'jobs_hooks.py').read_text(encoding='utf-8'))


class LegacyData(unittest.TestCase):
    """jobs/legacy.json replaces the three frozen sets of tools/verbs/jobs.py (napoleon J62): same ids, same effect."""
    DATA = json.loads((ROOT / 'jobs' / 'legacy.json').read_text(encoding='utf-8'))

    def test_the_round_rules_set_is_every_review_on_main_at_j52s_base(self):
        out = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', '39eab5e', 'jobs'], capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest('J52 base commit not in this clone')
        on_main = {p.split('/')[1] for p in out.stdout.split() if p.endswith('/review.md')}
        self.assertEqual(on_main, set(self.DATA['round_rules']))

    def test_the_brief_hooks_set_is_every_brief_on_main_when_j11_cut_its_branch_plus_the_two_that_merged_first(self):
        out = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'c674fb1', 'jobs'], capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest('J11 base commit not in this clone')
        on_main = {p.split('/')[1] for p in out.stdout.split() if p.endswith('/brief.md')}
        self.assertEqual(on_main | {'J24', 'J37'}, set(self.DATA['brief_hooks']))

    def test_ids_are_unique_and_sorted_by_number(self):
        for k in ('round_rules', 'brief_hooks'):
            ids = self.DATA[k]
            self.assertEqual(len(ids), len(set(ids)), k)
            self.assertEqual(ids, sorted(ids, key=lambda j: int(j[1:])), k)


class FoundPathHook(unittest.TestCase):
    """The J11 hook: a brief that names a game-side path (not a registry id) fails; the shape of its message is the core's `<id>: brief: found path: ...`."""
    CTX = types.SimpleNamespace(root=ROOT)

    def test_a_found_path_is_refused_and_the_registry_id_passes(self):
        sys.path.insert(0, str(ROOT / 'discovery' / 'core'))
        import briefpaths
        known = briefpaths.load_known(ROOT)
        unit = next(u for u in known.ui_ids if u.startswith('battle.'))
        path = next(k for k, v in known.ui_paths.items() if unit in v and ' ' in k)
        bad = hk.brief_problems(self.CTX, 'J99', row('J99'), f'# J99: x\n\nOpen `{path}`.\n')
        self.assertTrue(bad and all(e.startswith('found path: ') for e in bad), bad)
        self.assertEqual(hk.brief_problems(self.CTX, 'J99', row('J99'), f'# J99: x\n\nOpen `{unit}`.\n'), [])

    def test_summary_counts_registry_gaps(self):
        read = lambda p: '## Registry gaps\n- path: ui/x.layout; owner: liam; reason: no row yet\n' if p == 'jobs/J99/brief.md' else None
        self.assertEqual(hk.summary(self.CTX, [row('J99')], read), '1 registry gaps in briefs')


class Queue(unittest.TestCase):
    def test_the_hook_runs_rule_76_on_the_tracked_files(self):
        ctx = types.SimpleNamespace(root=ROOT)
        self.assertEqual(hk.queue_problems(ctx, [row('J12', status='review')], ['proxy/core/a.py']), [])
        self.assertTrue(hk.queue_problems(ctx, [row('J12', status='done')], ['proxy/core/a.py']))

    def test_the_repo_table_covers_every_core_folder_here(self):
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True).stdout.split()
        rows = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'registries' / 'jobs').glob('*.json')]
        self.assertEqual(hk.promotion_problems(rows, {str(Path(f).parent.as_posix()) for f in tracked}), [])


if __name__ == '__main__':
    unittest.main()
