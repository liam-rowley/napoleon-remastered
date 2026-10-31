#!/usr/bin/env python3
"""Which slow checks a diff needs: the one list of the `proxy`, `harness-windows` and `viewer` input files, for CI and for the local gates (J41).

purpose: print `proxy=true|false`, `harness=true|false` and `viewer=true|false` for the files changed since a base: CI's `changes` job writes them to $GITHUB_OUTPUT, and tests/test_proxy_host.py uses the proxy set to skip the proxy host tests when nothing they build from changed; an unknown base means everything changed
usage: python3 tools/changed_inputs.py --base <sha or ''>   (CI: base..HEAD) | python3 tools/changed_inputs.py --local   (merge-base with origin/main, plus staged, unstaged and untracked files); the changed files go to stderr, key=value lines to stdout
when: automatic (CI `changes` job, the `tests` gate through tests/test_proxy_host.py); by hand to see whether a branch will run the proxy, harness-windows or viewer job
not-a-verb: CI calls it before the core is checked out (the `changes` job has no submodule); a small file classifier, not a registry operation
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = r'^\.github/workflows/'
# proxy: proxy/ and the two registries proxy/tools/gen_tables.py reads; harness: harness/ and pc_deploy.py (the integration tests run
# `pc_deploy.py kit --what harness`); viewer: viewer/ and its test (J31). A workflow change runs all three. proxy/runs/ and viewer/runs/
# are committed run evidence, not build inputs (J42).
INPUTS = {
    'proxy': re.compile(rf'{WORKFLOWS}|^proxy/(?!runs/)|^registries/(engine_sites|config_keys)\.jsonl$'),
    'harness': re.compile(rf'{WORKFLOWS}|^harness/|^proxy/tools/pc_deploy\.py$'),
    'viewer': re.compile(rf'{WORKFLOWS}|^viewer/(?!runs/)|^tests/test_viewer\.py$'),
}


def classify(files):
    """{'proxy': bool, 'harness': bool, 'viewer': bool}; files None means the base is unknown: everything changed."""
    return {k: files is None or any(rx.search(f) for f in files) for k, rx in INPUTS.items()}


def _git(root, *args):
    """(returncode, stdout lines) of a git command in root; 127 when git cannot start."""
    try:
        r = subprocess.run(['git', '-c', 'core.quotepath=off', *args], cwd=root, capture_output=True, text=True, timeout=60)
        return r.returncode, [l for l in r.stdout.splitlines() if l.strip()]
    except (OSError, subprocess.SubprocessError):
        return 127, []


def known_commit(root, base, git=_git):
    return bool(base) and git(root, 'cat-file', '-e', f'{base}^{{commit}}')[0] == 0


def changed_files(root, base, git=_git):
    """Files changed from base to HEAD, or None when base is not a commit here (shallow clone, force push, first push)."""
    if not known_commit(root, base, git):
        return None
    rc, files = git(root, 'diff', '--name-only', base, 'HEAD')
    return files if rc == 0 else None


def local_base(root, git=_git):
    """The merge base with origin/main, or None (no origin/main, a shallow clone)."""
    rc, out = git(root, 'rev-parse', '--is-shallow-repository')
    if rc != 0 or out[:1] == ['true']:
        return None
    rc, out = git(root, 'merge-base', 'origin/main', 'HEAD')
    return out[0].strip() if rc == 0 and out else None


def local_changes(root, git=_git):
    """(base, files) for a local run: committed since the merge base with origin/main, plus staged, unstaged and untracked files, so
    an edit not yet committed still counts. files is None when the base is unknown."""
    base = local_base(root, git)
    files = changed_files(root, base, git)
    if files is None:
        return base, None
    for args in (('diff', '--name-only', 'HEAD'), ('ls-files', '--others', '--exclude-standard')):
        rc, more = git(root, *args)
        if rc != 0:
            return base, None
        files += more
    return base, sorted(set(files))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--base', help="the commit to diff HEAD against; '' or an unknown commit means everything changed")
    g.add_argument('--local', action='store_true', help='merge base with origin/main plus uncommitted and untracked files')
    a = ap.parse_args(argv)
    if a.local:
        base, files = local_changes(ROOT)
    else:
        base, files = a.base, changed_files(ROOT, a.base)
    if files is None:
        print(f"base unknown ('{base or ''}'): running everything", file=sys.stderr)
    else:
        print('\n'.join(files), file=sys.stderr)
    for k, v in classify(files).items():
        print(f'{k}={str(v).lower()}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
