"""J55: two job branches that each add a job row and change a different tool header merge with no conflict.

Built from this repo's real layout (wsc.toml, .gitattributes, schemas/, registries/ and two real tools) in a temporary repository, changed
through the real `wsc reg`, merged with plain `git merge`. `merge=union` must not be what makes it pass: the per-row files carry no
merge attribute at all.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ('tools/pr_policy.py', 'tools/changed_inputs.py')


class TwoJobsMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        for f in ('wsc.toml', '.gitattributes', '.gitignore', *TOOLS):
            (self.d / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / f, self.d / f)
        for d in ('schemas', 'registries'):
            shutil.copytree(ROOT / d, self.d / d)
        self.git('init', '-q', '-b', 'main')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'the real layout')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *a],
                              cwd=self.d, capture_output=True, text=True)

    def wsc(self, *a):
        p = subprocess.run([sys.executable, str(ROOT / 'core' / 'wsc.py'), '--root', str(self.d), *a], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def job(self, jid, tool):
        self.git('checkout', '-q', '-b', f'job/{jid}', 'main')
        row = {'id': jid, 'description': f'merge test row {jid}', 'title': f'Merge test {jid}', 'phase': 1, 'status': 'needs_brief',
               'model': 'sonnet', 'needs_pc': False, 'depends_on': []}
        self.wsc('reg', 'add', 'jobs', '--json', json.dumps(row))
        p = self.d / tool
        text = p.read_text(encoding='utf-8')
        new = re.sub(r'(?im)^(\W*purpose:\s*)', lambda m: f'{m.group(1)}({jid}) ', text, count=1)
        self.assertNotEqual(new, text, tool)
        p.write_text(new, encoding='utf-8', newline='\n')
        self.wsc('reg', 'add', 'tools', str(p))   # absolute: a relative path resolves against the shell's folder first
        self.git('add', '-A')
        self.assertEqual(self.git('commit', '-q', '-m', jid).returncode, 0)

    def test_two_branches_merge_with_no_conflict_and_no_union(self):
        self.job('J901', TOOLS[0])
        self.job('J902', TOOLS[1])
        changed = self.git('diff', '--name-only', 'main', 'job/J902').stdout.split()
        self.assertEqual(sorted(p for p in changed if p.startswith('registries/')), ['registries/jobs/J902.json', 'registries/tools/'
                         + next(f.name for f in (self.d / 'registries' / 'tools').glob('*.json') if 'changed_inputs' in f.read_text(encoding='utf-8'))])
        for p in changed:
            self.assertIn('merge: unspecified', self.git('check-attr', 'merge', '--', p).stdout, p)   # not merge=union
        self.git('checkout', '-q', 'job/J901')
        m = self.git('merge', '--no-edit', 'job/J902')
        self.assertEqual(m.returncode, 0, m.stdout + m.stderr)
        rows = {json.loads(f.read_text(encoding='utf-8'))['id'] for f in (self.d / 'registries' / 'jobs').glob('*.json')}
        self.assertTrue({'J901', 'J902'} <= rows)
        tools = [json.loads(f.read_text(encoding='utf-8')) for f in (self.d / 'registries' / 'tools').glob('*.json')]
        purposes = {t['path']: t['purpose'] for t in tools if t.get('path') in TOOLS}
        self.assertTrue(purposes[TOOLS[0]].startswith('(J901) ') and purposes[TOOLS[1]].startswith('(J902) '), purposes)
        self.assertFalse(list((self.d / 'registries').glob('*.md')))   # no committed view to conflict on


if __name__ == '__main__':
    unittest.main()
