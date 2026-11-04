"""J97: viewer/core/build.sh --prune [--dry-run] decides per napoleon-viewer-cmake volume, against a stub `docker` first on PATH.

The stub answers `info`, `volume ls -q`, `volume inspect` (the checkout label) and `volume rm` from a fixture folder and logs every call,
so no Docker is needed. The script runs from a temp git repo with one `git worktree add`, for the unlabelled-live case. Skips without bash.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'viewer' / 'core' / 'build.sh'
PREFIX = 'napoleon-viewer-cmake'

STUB = r'''#!/usr/bin/env bash
d="$STUB_DOCKER_DIR"
printf '%s\n' "$*" >> "$d/calls.log"
case "$1" in
  info) [[ -f "$d/down" ]] && exit 1; echo stub ;;
  volume)
    name="${@: -1}"
    case "$2" in
      ls) cat "$d/volumes" ;;
      inspect) [[ -f "$d/labels/$name" ]] && cat "$d/labels/$name" || echo "" ;;
      rm) grep -qx -- "$name" "$d/busy" 2>/dev/null && { echo "Error response from daemon: volume is in use" >&2; exit 1; }; echo "$name" ;;
      *) exit 1 ;;
    esac ;;
  *) exit 1 ;;
esac
'''


def find_bash():
    b = shutil.which('bash')
    if not b or 'system32' in b.lower():   # WSL's bash.exe is not Git Bash: it cannot see this PATH or these paths
        return None
    return b


BASH = find_bash()


@unittest.skipUnless(BASH, 'no bash (Git Bash or Linux) on PATH')
class Prune(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='j97_')))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / 'repo'
        (self.repo / 'viewer' / 'core').mkdir(parents=True)
        shutil.copyfile(BUILD, self.repo / 'viewer' / 'core' / 'build.sh')
        git = ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'core.autocrlf=false']
        subprocess.run(git + ['init', '-q', str(self.repo)], check=True)
        subprocess.run(git + ['-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(git + ['-C', str(self.repo), 'commit', '-qm', 'x'], check=True)
        self.wt = self.tmp / 'wt'
        subprocess.run(git + ['-C', str(self.repo), 'worktree', 'add', '-q', str(self.wt)], check=True)
        self.stub = self.tmp / 'stub'
        (self.stub / 'labels').mkdir(parents=True)
        (self.stub / 'docker').write_bytes(STUB.encode())
        (self.stub / 'docker').chmod(0o755)
        (self.stub / 'calls.log').write_text('')
        self.live_dir = self.tmp / 'live'
        self.live_dir.mkdir()

    def bash_path(self, p):
        return subprocess.run([BASH, '-c', 'cd "$1" && pwd', '_', str(p)], capture_output=True, text=True, check=True).stdout.strip()

    def vol(self, p):
        return f'{PREFIX}-' + hashlib.sha256(self.bash_path(p).encode()).hexdigest()[:12]

    def fixture(self, volumes, labels=None, busy=(), down=False):
        (self.stub / 'volumes').write_bytes(('\n'.join(volumes) + '\n').encode())
        for k, v in (labels or {}).items():
            (self.stub / 'labels' / k).write_bytes((v + '\n').encode())
        (self.stub / 'busy').write_bytes(('\n'.join(busy) + '\n').encode())
        if down:
            (self.stub / 'down').write_text('')

    def run_prune(self, *args):
        env = dict(os.environ, STUB_DOCKER_DIR=self.bash_path(self.stub))
        env['PATH'] = str(self.stub) + os.pathsep + env['PATH']
        r = subprocess.run([BASH, str(self.repo / 'viewer' / 'core' / 'build.sh'), '--prune', *args], env=env,
                           capture_output=True, text=True)
        calls = (self.stub / 'calls.log').read_text().splitlines()
        return r, calls

    def standard(self, busy=()):
        gone = self.tmp / 'gone'
        self.names = {
            'live_label': f'{PREFIX}-aaaaaaaaaaaa',
            'gone_label': f'{PREFIX}-bbbbbbbbbbbb',
            'live_hash': self.vol(self.wt),
            'dead_hash': f'{PREFIX}-cccccccccccc',
            'legacy': PREFIX,
            'other': 'someone-elses-volume',
        }
        n = self.names
        self.fixture(list(n.values()),
                     labels={n['live_label']: self.bash_path(self.live_dir), n['gone_label']: str(gone).replace('\\', '/')},
                     busy=busy)

    def line(self, out, name):
        return next(l for l in out.splitlines() if l.split(':')[0].split()[-1] == name)

    def test_decisions(self):
        self.standard()
        r, calls = self.run_prune()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        n = self.names
        self.assertTrue(self.line(r.stdout, n['live_label']).startswith('keep '), r.stdout)
        self.assertTrue(self.line(r.stdout, n['live_hash']).startswith('keep '), r.stdout)
        for k in ('gone_label', 'dead_hash', 'legacy'):
            self.assertTrue(self.line(r.stdout, n[k]).startswith('removed '), (k, r.stdout))
            self.assertIn(f'volume rm {n[k]}', calls)
        self.assertIn('kept 2, removed 3, skipped 0', r.stdout)
        self.assertEqual([c for c in calls if 'volume rm' in c], [f'volume rm {n[k]}' for k in ('gone_label', 'dead_hash', 'legacy')])

    def test_other_prefix_is_never_named(self):
        self.standard()
        _, calls = self.run_prune()
        self.assertTrue(calls)
        self.assertFalse([c for c in calls if self.names['other'] in c], calls)
        self.assertFalse([c for c in calls if c.split()[:2] != ['info'] and c.split()[:2] not in (['volume', 'ls'], ['volume', 'inspect'], ['volume', 'rm'])])
        self.assertFalse([c for c in calls if 'prune' in c], calls)

    def test_in_use_is_skipped(self):
        self.standard(busy=[f'{PREFIX}-cccccccccccc'])
        r, _ = self.run_prune()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('in use, skipped', self.line(r.stdout, f'{PREFIX}-cccccccccccc'))
        self.assertIn('kept 2, removed 2, skipped 1', r.stdout)

    def test_dry_run_removes_nothing(self):
        self.standard()
        r, calls = self.run_prune('--dry-run')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse([c for c in calls if 'volume rm' in c], calls)
        self.assertTrue(self.line(r.stdout, PREFIX).startswith('would remove '), r.stdout)
        self.assertIn('kept 2, would remove 3, skipped 0', r.stdout)

    def test_this_checkout_is_live(self):
        own = self.vol(self.repo)
        self.fixture([own])
        r, _ = self.run_prune('--dry-run')
        self.assertTrue(self.line(r.stdout, own).startswith('keep '), r.stdout)

    def test_docker_down_exits_2(self):
        self.fixture([PREFIX], down=True)
        r, calls = self.run_prune()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('start Docker Desktop', r.stdout)
        self.assertEqual(calls, ['info'])


if __name__ == '__main__':
    unittest.main()
