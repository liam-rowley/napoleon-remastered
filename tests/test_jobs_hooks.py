"""Host tests for tools/gates/pipeline.py, napoleon's gate module for the core's job pipeline (napoleon J62): rule 76 (promotion folders), rule 75 (the PC line of
the page), rule 79 (acceptance passes, with the core-pin diff of J58), the legacy id sets (jobs/legacy.json) and the found-path brief hook.

Moved from tests/test_jobs.py and tests/test_pr_policy.py; the generic rules are tested in warscape-core (tests/test_jobs.py, test_policy.py, test_fixture_game.py).
"""
import hashlib
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
_spec = importlib.util.spec_from_file_location('jobs_hooks', ROOT / 'tools' / 'gates' / 'pipeline.py')
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
    """Rule 76 (J12): core candidate folders and the jobs that promote them. `T` is a fixture table with neutral folder names (J94: it
    named proxy/core and discovery/core, which read like the real table from before J12 moved the proxy into the core)."""
    T = {'area_a/core': 'J12', 'area_b/core': None}

    def test_listed_folders_pass_while_the_job_is_open(self):
        self.assertEqual(hk.promotion_problems([row('J12', status='review')], {'area_a/core', 'area_a/core/x', 'area_b/core'}, self.T), [])

    def test_failing_fixture_a_folder_whose_promotion_is_done_must_be_gone(self):
        e = hk.promotion_problems([row('J12', status='done')], {'area_a/core'}, self.T)
        self.assertEqual(len(e), 1); self.assertIn('promotion job J12 is done', e[0])
        self.assertEqual(hk.promotion_problems([row('J12', status='done')], {'area_a/napoleon'}, self.T), [])   # gone: fine

    def test_failing_fixture_an_unlisted_core_folder_fails(self):
        e = hk.promotion_problems([row('J12')], {'audio/core/a'}, self.T)
        self.assertEqual(len(e), 1); self.assertIn('audio/core/ is a core candidate with no promotion job', e[0])

    def test_the_submodule_and_unknown_jobs(self):
        self.assertEqual(hk.promotion_problems([], {'core/proxy/src', 'core/warscape'}, self.T), [])   # the core itself is not a candidate
        self.assertIn('has no row', hk.promotion_problems([], {'area_a/core'}, self.T)[0])

    def test_the_real_table_names_no_folder_that_is_gone(self):
        # J94 (J70 Later 2): an entry whose promotion is not done must name a folder that still has tracked files; a done one is the
        # record that its folder stays gone (rule 76 fails it if it comes back), so it is the one kind of entry allowed to be absent
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True, check=True).stdout.split()
        have = {'/'.join(f.split('/')[:2]) for f in tracked}
        rows = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'registries' / 'jobs').glob('*.json')}
        in_flight = {'discovery/core': 'J64'}   # J64 removes this folder itself and its row is `done` only at its merge; harmless after that
        stale = [f'{d} ({j or "no row"})' for d, j in hk.PROMOTIONS.items()
                 if d not in have and not (j and rows.get(j, {}).get('status') == 'done') and in_flight.get(d) != j]
        self.assertEqual(stale, [], 'PROMOTIONS entries for folders that no longer exist and whose promotion is not done')

    def test_the_repo_table_covers_every_core_folder_here(self):
        root = Path(__file__).resolve().parent.parent
        tracked = subprocess.run(['git', '-C', str(root), 'ls-files'], capture_output=True, text=True).stdout.split()
        rows = [json.loads(p.read_text(encoding='utf-8')) for p in (root / 'registries' / 'jobs').glob('*.json')]
        self.assertEqual(hk.promotion_problems(rows, {str(Path(f).parent.as_posix()) for f in tracked}), [])

    def test_promotions_name_rows_that_exist(self):
        rows = {p.stem for p in (ROOT / 'registries' / 'jobs').glob('*.json')}
        for folder, jid in (('upscale/core', 'J63'), ('viewer/core', 'J63'), ('release/core', 'J100')):
            self.assertEqual(hk.PROMOTIONS[folder], jid, folder)
            self.assertIn(jid, rows, folder)

    def test_discovery_core_is_gone_and_unlisted(self):
        # J64: the folder moved to the core (v0.15.0); rule 76 has nothing to list, and a new discovery/core would fail as an unlisted candidate
        self.assertEqual(hk.PROMOTIONS['discovery/core'], 'J64')
        self.assertFalse((ROOT / 'discovery' / 'core').exists())
        self.assertEqual(hk.promotion_problems([row('J64', status='review')], {'discovery/core'}), [])
        self.assertTrue(hk.promotion_problems([row('J64', status='done')], {'discovery/core'}))


class MetaGlobs(unittest.TestCase):
    """J73 (audit P3): `meta/` may not carry the core pin or the registries that feed the DLL tables; the globs match the way the core's `policy.allowed` does."""
    sys.path.insert(0, str(ROOT / 'core'))
    from warscape import policy as _policy
    from warscape.repo import load_config as _load_config
    POLICY = _load_config(ROOT)['policy']

    @staticmethod
    def segment_match(path, glob):
        """`*` and `?` stay inside one path segment, `**` is zero or more whole segments."""
        import fnmatch

        def go(ps, gs):
            if not gs:
                return not ps
            if gs[0] == '**':
                return any(go(ps[i:], gs[1:]) for i in range(len(ps) + 1))
            return bool(ps) and fnmatch.fnmatchcase(ps[0], gs[0]) and go(ps[1:], gs[1:])
        return go(path.split('/'), glob.split('/'))

    def test_the_pin_and_the_registries_are_not_meta_or_plan(self):
        for kind in ('plan', 'meta'):
            self.assertNotIn('core', self.POLICY[kind])
            self.assertNotIn('registries/*', self.POLICY[kind])
            self.assertFalse(self._policy.allowed('core', self.POLICY[kind]), kind)
            self.assertFalse(self._policy.allowed('registries/engine_sites.jsonl', self.POLICY[kind]), kind)
            self.assertFalse(self._policy.allowed('registries/engine_facts/x.json', self.POLICY[kind]), kind)
            self.assertTrue(self._policy.allowed('registries/jobs/J73.json', self.POLICY[kind]), kind)

    def test_the_globs_of_each_kind_match_no_more_than_a_segment_wise_match(self):
        # per kind, not per glob: `docs/*` crosses `/` under fnmatch but `docs/**` is listed beside it
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True, check=True).stdout.splitlines()
        for kind in ('plan', 'meta'):
            fn = {p for p in tracked if self._policy.allowed(p, self.POLICY[kind])}
            seg = {p for p in tracked if any(self.segment_match(p, g) for g in self.POLICY[kind])}
            self.assertEqual(fn, seg, f'[policy] {kind} globs match {sorted(fn - seg)[:3]} under fnmatch but not per segment')


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
        src = (ROOT / 'tools' / 'gates' / 'pipeline.py').read_text(encoding='utf-8')
        self.assertIn('show_first(repo, base, *ACC_CHECKERS)', src)   # the base's checker, in either layout (J12), read at the clone (W23)
        self.assertNotIn("spec_from_file_location('acceptance'", src)

    def test_failing_fixture_another_branchs_passes_do_not_count(self):
        # J44 review: harness/ is not in the build id, so a harness-only branch on main's build would inherit the last merged branch's 20
        errs = hk.acceptance_problems(['harness/napoleon/adapter.json'], self.acc(self.led(20, branch='job/J8')))
        self.assertEqual(len(errs), 1)
        self.assertIn('another branch', errs[0])
        self.assertTrue(hk.acceptance_problems(['harness/napoleon/adapter.json'], self.acc(self.led(20, branch=None))))
        self.assertIn("'branch': facts['branch']", (ROOT / 'tools' / 'gates' / 'pipeline.py').read_text(encoding='utf-8'))

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
                          ('proxy/tools/fetch_lua.py', b'#\n'), ('proxy/tools/fetch_ui.py', b'#\n'), ('viewer/pins.json', b'{}\n'),
                          ('proxy/tools/toolchain.py', b'#\n'),   # a DLL input since core 0.27.0 (W24)
                          ('proxy/tools/build_id.py', (ROOT / 'core/proxy/tools/build_id.py').read_bytes())):
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
        errs = hk.policy_rule(ctx, {'kind': 'job', 'changed': ['proxy/core/dev.cpp'], 'acceptance': self.acc(self.led(3))})
        self.assertTrue(any('rule 79' in e for e in errs))

    def test_failing_fixture_rule_79_runs_on_every_branch_kind(self):
        # J73 (audit P3): the hook runs for every kind; a meta/ or brief/ branch cannot move proxy/ or harness/ without passes
        ctx = types.SimpleNamespace(root=ROOT)
        for kind in ('brief', 'plan', 'meta', '', 'job'):
            with self.subTest(kind=kind):
                errs = hk.policy_rule(ctx, {'kind': kind, 'changed': ['proxy/napoleon/adapter.cpp'], 'acceptance': self.acc(self.led(3))})
                self.assertTrue(any('rule 79' in e for e in errs), errs)
                self.assertEqual(hk.policy_rule(ctx, {'kind': kind, 'changed': ['docs/x.md'], 'acceptance': self.acc(self.led(3))}), [])
                pin = lambda diff: hk.policy_rule(ctx, {'kind': kind, 'changed': ['core'], 'acceptance': dict(self.acc(self.led(3)), core_diff=diff)})
                self.assertTrue(any('rule 79' in e for e in pin(['proxy/src/a.cpp'])))
                self.assertEqual(pin(['docs/x.md']), [])

    def test_docs_only_branches_skip_the_git_reads_and_the_shortcut_equals_the_full_path(self):
        ctx = types.SimpleNamespace(root=ROOT)

        def boom(*a, **k):
            raise AssertionError('collect_acceptance ran for a change rule 79 does not count')
        real = hk.collect_acceptance
        hk.collect_acceptance = boom
        try:
            for kind in ('brief', 'plan', 'meta', '', 'job'):
                self.assertEqual(hk.policy_rule(ctx, {'kind': kind, 'changed': ['docs/x.md', 'jobs/J9/brief.md', 'harness/runs/r/a.json']}), [])
        finally:
            hk.collect_acceptance = real
        # equal in effect: acceptance_problems gives [] for exactly these inputs, whatever the ledger holds
        for changed in (['docs/x.md'], ['harness/runs/r/a.json', 'proxy/README.md']):
            self.assertEqual(hk.acceptance_problems(changed, self.acc('')), [])
        # a counted path still reaches the git reads
        seen = []
        hk.collect_acceptance = lambda root, facts: seen.append(facts['changed']) or None
        try:
            hk.policy_rule(ctx, {'kind': 'meta', 'changed': ['proxy/napoleon/a.cpp']})
            hk.policy_rule(ctx, {'kind': 'meta', 'changed': ['core']})
        finally:
            hk.collect_acceptance = real
        self.assertEqual(seen, [['proxy/napoleon/a.cpp'], ['core']])


class Rule79Evidence(unittest.TestCase):
    """J75 (audit H3): each counted line's evidence is unique and agrees with it, the ledger diff is append-only, base pass files are
    immutable, only ledger.jsonl is exempt, and once the pinned core names them (core W9) the shas must be on the lines and files."""
    SHAS = ('shot_sha256', 'kit_sha256', 'dll_sha256', 'watcher_sha256')
    C = ['proxy/core/dev.cpp']

    @staticmethod
    def valid(n, run='harness/runs/r', start=1, shas=()):
        """n lines and their pass files, all agreeing: (lines, files)."""
        lines, files = [], {}
        for i in range(start, start + n):
            ev, steps = f'{run}/pass_{i:02d}.json', {'exe_sha1': True, 'land:load': True}
            sh = {k: hashlib.sha256(f'{k}{i if k.startswith("shot") else 0}'.encode()).hexdigest() for k in shas}
            lines.append({'pass': i, 'build_id': 'abc', 'watcher': '1.0.1', 'kit': 'k', 'branch': 'job/J9', 'run': run, 'evidence': ev,
                          'result': 'pass', 'steps': steps, **sh})
            files[ev] = {'pass': i, 'build_id': 'abc', 'watcher': '1.0.1', 'kit': 'k', 'passed': True,
                         'steps': {k: {'ok': v} for k, v in steps.items()}, **sh}
        return lines, files

    @staticmethod
    def acc(lines, files, **kw):
        text = {p: (f if isinstance(f, str) else json.dumps(f)) for p, f in files.items()}
        return {'active': True, 'ledger': ''.join(json.dumps(l) + '\n' for l in lines), 'build_id': 'abc', 'watcher': '1.0.1', 'branch': 'job/J9',
                'exists': lambda p: p in text, 'read': lambda p: text.get(p), **kw}

    def test_failing_fixture_only_the_ledger_is_exempt(self):
        self.assertFalse(hk.acc_exempt('harness/acceptance/baseline.json'))
        self.assertFalse(hk.acc_exempt('harness/acceptance/shots/x.png'))
        self.assertTrue(hk.acc_exempt('harness/acceptance/ledger.jsonl'))
        self.assertTrue(hk.acc_exempt('harness/acceptance/README.md'))
        errs = hk.acceptance_problems(['harness/acceptance/baseline.json'], self.acc([], {}))
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('changes harness/acceptance/baseline.json but', errs[0])

    def test_failing_fixture_twenty_copies_of_one_line_are_one_pass(self):
        lines, files = self.valid(1)
        errs = hk.acceptance_problems(self.C, self.acc(lines * 20, files))
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('1 consecutive', errs[0])
        self.assertIn('harness/runs/r/pass_01.json', errs[0])
        self.assertIn('already counted', errs[0])
        self.assertEqual(hk.acceptance_problems(self.C, self.acc(*self.valid(20))), [])

    def test_failing_fixture_evidence_that_disagrees_with_its_line_ends_the_streak(self):
        cases = {'build_id': lambda l, f: f.update(build_id='old'), 'watcher': lambda l, f: f.update(watcher='0.9'),
                 'pass': lambda l, f: f.update({'pass': 3}), 'passed': lambda l, f: f.update(passed=False),
                 'steps': lambda l, f: f['steps']['land:load'].update(ok=False), 'step names': lambda l, f: f['steps'].pop('land:load'),
                 'run': lambda l, f: l.update(run='harness/runs/q')}
        for name, spoil in cases.items():
            with self.subTest(field=name):
                lines, files = self.valid(20)
                spoil(lines[10], files[lines[10]['evidence']])
                errs = hk.acceptance_problems(self.C, self.acc(lines, files))
                self.assertEqual(len(errs), 1, errs)
                self.assertIn('9 consecutive', errs[0])
                self.assertIn('pass 11 of harness/runs/', errs[0])
                self.assertIn('harness/runs/r/pass_11.json', errs[0])

    def test_failing_fixture_unparsable_evidence_and_a_repeated_pass_number_end_the_streak(self):
        lines, files = self.valid(20)
        files['harness/runs/r/pass_11.json'] = 'not json {'
        errs = hk.acceptance_problems(self.C, self.acc(lines, files))
        self.assertIn('9 consecutive', errs[0])
        self.assertIn('not JSON', errs[0])
        lines, files = self.valid(20)
        lines[10] = dict(lines[9], evidence='harness/runs/r/pass_10b.json')      # a pasted line repeats a number, with a copied file
        files['harness/runs/r/pass_10b.json'] = files['harness/runs/r/pass_10.json']
        errs = hk.acceptance_problems(self.C, self.acc(lines, files))
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('9 consecutive', errs[0])
        self.assertIn('pass 10 of harness/runs/r', errs[0])
        # two runs in one streak: the numbers restart with the new run
        a, fa = self.valid(5, run='harness/runs/a')
        b, fb = self.valid(15, run='harness/runs/b')
        self.assertEqual(hk.acceptance_problems(self.C, self.acc(a + b, {**fa, **fb})), [])

    def test_failing_fixture_the_ledger_diff_is_append_only(self):
        a, b, c = (json.dumps({'pass': i, 'run': 'harness/runs/r', 'result': 'pass'}) for i in (1, 2, 3))
        b2 = b.replace('pass"}', 'pass", "x": 1}')
        led = lambda *ls: ''.join(l + '\n' for l in ls)
        check = lambda base, branch, changed=('docs/x.md',): hk.acceptance_problems(list(changed), dict(self.acc([], {}), ledger=branch, base_ledger=base))
        self.assertEqual(check(led(a, b), led(a, b, c)), [])
        self.assertEqual(check(led(a, b), led(a, b)), [])
        self.assertEqual(check(led(a, b), led(a, b).rstrip('\n')), [])
        self.assertEqual(check(None, led(a)), [])                                   # a ledger new at the base
        for branch in (led(a, b2), led(b), led(a), led(b, a, c)):
            with self.subTest(branch=branch):
                errs = check(led(a, b), branch, changed=('harness/acceptance/ledger.jsonl',))   # rewriting the ledger alone is the attack
                self.assertEqual(len(errs), 1, errs)
                self.assertTrue(errs[0].startswith('rule 79: harness/acceptance/ledger.jsonl is not append-only'), errs[0])
        self.assertIn('pass 2 of harness/runs/r', check(led(a, b), led(a, b2))[0])

    def test_failing_fixture_shas_are_required_once_the_core_names_them(self):
        lines, files = self.valid(20, shas=self.SHAS)
        self.assertEqual(hk.acceptance_problems(self.C, self.acc(lines, files, sha_fields=self.SHAS)), [])
        spoils = {'missing': lambda l, f: l.pop('dll_sha256'), 'differs': lambda l, f: f.update(kit_sha256='0' * 64),
                  'not hex': lambda l, f: (l.update(watcher_sha256='zz'), f.update(watcher_sha256='zz')),
                  'shared shot': lambda l, f: (l.update(shot_sha256=lines[11]['shot_sha256']), f.update(shot_sha256=lines[11]['shot_sha256']))}
        for name, spoil in spoils.items():
            with self.subTest(case=name):
                lines, files = self.valid(20, shas=self.SHAS)
                spoil(lines[10], files[lines[10]['evidence']])
                errs = hk.acceptance_problems(self.C, self.acc(lines, files, sha_fields=self.SHAS))
                self.assertEqual(len(errs), 1, errs)
                self.assertIn('9 consecutive', errs[0])
                self.assertIn('pass 11 of harness/runs/r', errs[0])
                self.assertEqual(hk.acceptance_problems(self.C, self.acc(lines, files, sha_fields=None)), [])   # off: Decisions 1-4 only
        self.assertIsNone(hk.acc_sha_fields(src='NEEDED = 20\n'))
        self.assertIsNone(hk.acc_sha_fields(src=None))
        self.assertEqual(hk.acc_sha_fields(src="X = 1\nLEDGER_SHA_FIELDS = ('shot_sha256', 'kit_sha256')\n"), ('shot_sha256', 'kit_sha256'))


class Rule79Repo(unittest.TestCase):
    """J75 Decisions 3-5 through collect_acceptance, on a throwaway repo: pass files at the base are immutable, and the new keys are read from git."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.g('init', '-q', '-b', 'main'); self.g('config', 'user.email', 't@example.invalid'); self.g('config', 'user.name', 'test')
        lines, files = Rule79Evidence.valid(20)
        self.write({'harness/core/watcher.ps1': "$Version = '1.0.1'\n", 'harness/acceptance/ledger.jsonl': json.dumps(lines[0]) + '\n',
                    'harness/runs/r/pass_01.json': json.dumps(files['harness/runs/r/pass_01.json'])})
        self.base = self.g('rev-parse', 'HEAD')
        self.g('checkout', '-q', '-b', 'job/J9')
        self.lines, self.files = lines, files
        self.real = hk.dll_build_id
        hk.dll_build_id = lambda root, rev='HEAD', tool_root=None: 'abc'   # the fixture has no build id tool

    def tearDown(self):
        hk.dll_build_id = self.real
        self.tmp.cleanup()

    def g(self, *a):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *a], cwd=self.d, capture_output=True, text=True, check=True).stdout.strip()

    def write(self, files, rm=()):
        for rel, text in files.items():
            (self.d / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.d / rel).write_text(text, encoding='utf-8', newline='\n')
        for rel in rm:
            (self.d / rel).unlink()
        self.g('add', '-A'); self.g('commit', '-q', '-m', 'change')

    def problems(self, changed):
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.d, capture_output=True, text=True, check=True).stdout.strip()
        acc = hk.collect_acceptance(self.d, {'base': 'main', 'merge_base': self.base, 'head': head, 'repo': str(self.d), 'changed': changed, 'branch': 'job/J9'})
        return acc, hk.acceptance_problems(changed, dict(acc, active=True))

    def test_failing_fixture_a_base_pass_file_is_immutable(self):
        self.write({'harness/runs/r/pass_01.json': '{"pass": 1, "passed": true}\n'})
        errs = self.problems(['harness/runs/r/pass_01.json'])[1]
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('harness/runs/r/pass_01.json is modified', errs[0])
        self.g('reset', '-q', '--hard', self.base)
        self.write({}, rm=['harness/runs/r/pass_01.json'])
        self.assertIn('is deleted', self.problems(['harness/runs/r/pass_01.json'])[1][0])
        self.g('reset', '-q', '--hard', self.base)
        self.write({'harness/runs/r/pass_02.json': json.dumps(self.files['harness/runs/r/pass_02.json'])})
        self.assertEqual(self.problems(['harness/runs/r/pass_02.json'])[1], [])

    def test_failing_fixture_collect_reads_content_the_base_ledger_and_the_sha_fields(self):
        self.write({'harness/acceptance/ledger.jsonl': ''.join(json.dumps(l) + '\n' for l in self.lines),
                    **{p: json.dumps(f) for p, f in self.files.items()}})
        acc, errs = self.problems(['proxy/core/dev.cpp', 'harness/acceptance/ledger.jsonl'])
        self.assertEqual(errs, [])
        self.assertEqual(acc['base_ledger'], json.dumps(self.lines[0]) + '\n')
        self.assertEqual(json.loads(acc['read']('harness/runs/r/pass_07.json'))['pass'], 7)
        self.assertIsNone(acc['read']('harness/runs/r/pass_99.json'))
        self.assertIsNone(acc['sha_fields'])
        self.write({'harness/core/acceptance.py': "LEDGER_SHA_FIELDS = ('shot_sha256',)\n"})
        acc, errs = self.problems(['proxy/core/dev.cpp'])
        self.assertEqual(acc['sha_fields'], ('shot_sha256',))
        self.assertIn('shot_sha256', errs[0])
        # rewriting the base's line on the branch is refused even when nothing else counts
        self.write({'harness/acceptance/ledger.jsonl': ''.join(json.dumps(dict(l, kit='k2')) + '\n' for l in self.lines)})
        self.assertIn('not append-only', self.problems(['harness/acceptance/ledger.jsonl'])[1][0])


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

    def test_collect_acceptance_reads_the_pin_diff_from_the_merge_base(self):
        self.bump({'proxy/src/a.cpp': 'int a2;\n'})
        mb = self.g(self.game, 'rev-parse', 'HEAD~1')
        head = self.g(self.game, 'rev-parse', 'HEAD')
        # core W23 (0.26.0): the facts carry the clone and the shas; the rules' folder (here a stand-in) is never a git cwd
        facts = {'base': mb, 'merge_base': mb, 'head': head, 'repo': str(self.game), 'changed': ['core'], 'branch': 'job/J9'}
        real = hk.dll_build_id
        seen = []
        hk.dll_build_id = lambda root, rev='HEAD', tool_root=None: seen.append((rev, tool_root)) or 'abc'   # the fixture core has no build id tool
        try:
            got = hk.collect_acceptance('rules-folder', facts)
            self.assertEqual(got['core_diff'], hk.core_pin_diff(mb, head, self.game))
            self.assertEqual(got['core_diff'], ['proxy/src/a.cpp'])
            self.assertEqual(seen[-1], (head, 'rules-folder'))   # the base's build id tool over the head's blobs
            self.assertIsNone(hk.collect_acceptance('rules-folder', dict(facts, changed=['docs/x.md']))['core_diff'])
            # the wrong base (the head itself) would give an empty diff: the merge base is what is read
            self.assertNotEqual(got['core_diff'], hk.core_pin_diff(head, head, self.game))
            # a pull_request_target run checks out the base: HEAD is the base there, and the head is still read by its sha
            self.g(self.game, 'checkout', '-q', '--detach', mb)
            self.assertEqual(hk.collect_acceptance('rules-folder', facts)['core_diff'], ['proxy/src/a.cpp'])
        finally:
            hk.dll_build_id = real


class LegacyData(unittest.TestCase):
    """jobs/legacy.json replaces the three frozen sets of tools/verbs/jobs.py (napoleon J62): same ids, same effect."""
    DATA = json.loads((ROOT / 'jobs' / 'legacy.json').read_text(encoding='utf-8'))

    # sha256 of '\n'.join(ids) (sorted by number): the frozen sets, checked in every clone, a depth-1 one included (J73)
    FROZEN = {'round_rules': '5b4755b405b52fc62abdd27d9155a0d0f42641a6dacec5af1b8eee98a41ba8ff',
              'brief_hooks': '059f0a5b218cb562aa7ed5fc4a3df45d57add323e312f8c8c98c502aab321a05'}

    def test_the_frozen_sets_still_hash_to_their_constants(self):
        import hashlib
        for k, want in self.FROZEN.items():
            self.assertEqual(hashlib.sha256('\n'.join(self.DATA[k]).encode()).hexdigest(), want, f'{k}: jobs/legacy.json changed; the sets are frozen')

    def test_the_round_rules_set_is_every_review_on_main_at_j52s_base(self):
        out = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', '39eab5e', 'jobs'], capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest('J52 base commit not in this clone (the constant half above still runs)')
        on_main = {p.split('/')[1] for p in out.stdout.split() if p.endswith('/review.md')}
        self.assertEqual(on_main, set(self.DATA['round_rules']))

    def test_the_brief_hooks_set_is_every_brief_on_main_when_j11_cut_its_branch_plus_the_two_that_merged_first(self):
        out = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'c674fb1', 'jobs'], capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest('J11 base commit not in this clone (the constant half above still runs)')
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
        sys.path.insert(0, str(ROOT / 'core' / 'discovery'))
        import briefpaths
        known = briefpaths.load_known(ROOT)
        unit = next(u for u in known.ui_ids if u.startswith('battle.'))
        path = next(k for k, v in known.ui_paths.items() if unit in v and ' ' in k)
        bad = hk.brief_rule(self.CTX, 'J99', row('J99'), f'# J99: x\n\nOpen `{path}`.\n')
        self.assertTrue(bad and all(e.startswith('found path: ') for e in bad), bad)
        self.assertEqual(hk.brief_rule(self.CTX, 'J99', row('J99'), f'# J99: x\n\nOpen `{unit}`.\n'), [])

    def test_summary_counts_registry_gaps(self):
        read = lambda p: '## Registry gaps\n- path: ui/x.layout; owner: liam; reason: no row yet\n' if p == 'jobs/J99/brief.md' else None
        self.assertEqual(hk.gap_summary(self.CTX, [row('J99')], read), '1 registry gaps in briefs')


class Queue(unittest.TestCase):
    def test_the_hook_runs_rule_76_on_the_tracked_files(self):
        ctx = types.SimpleNamespace(root=ROOT)
        self.assertEqual(hk.queue_rule(ctx, [row('J12', status='review')], ['proxy/core/a.py']), [])
        self.assertTrue(hk.queue_rule(ctx, [row('J12', status='done')], ['proxy/core/a.py']))

    def test_the_repo_table_covers_every_core_folder_here(self):
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True).stdout.split()
        rows = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'registries' / 'jobs').glob('*.json')]
        self.assertEqual(hk.promotion_problems(rows, {str(Path(f).parent.as_posix()) for f in tracked}), [])


if __name__ == '__main__':
    unittest.main()
