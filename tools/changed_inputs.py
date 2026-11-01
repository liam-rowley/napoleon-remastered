#!/usr/bin/env python3
"""Which slow checks a diff needs: the one list of the `proxy`, `harness-windows` and `viewer` input files, for CI and for the local gates (J41), and each set's tree hash (J54).

purpose: print `proxy=true|false`, `harness=true|false` and `viewer=true|false` for the files changed since a base (an unknown base means everything changed), then `proxy_tree=`, `harness_tree=`, `viewer_tree=` (a hash of the set's files at HEAD: mode, object and path, plus the set's name and SALT; empty when it cannot be read) and `tree_salt=`: CI's `changes` job writes them to $GITHUB_OUTPUT and skips a slow job whose tree hash already has a pass marker (rule 79 for CI, J54); tests/test_proxy_host.py uses the proxy set to skip the proxy host tests when nothing they build from changed
usage: python3 tools/changed_inputs.py --base <sha or ''>   (CI: base..HEAD) | python3 tools/changed_inputs.py --local   (merge-base with origin/main, plus staged, unstaged and untracked files; the tree hashes are of HEAD); the changed files go to stderr, key=value lines to stdout
when: automatic (CI `changes` job, the `tests` gate through tests/test_proxy_host.py); by hand to see whether a branch will run the proxy, harness-windows or viewer job, or which tree hash its pass marker carries
not-a-verb: CI calls it before the core is checked out (the `changes` job has no submodule); a small file classifier, not a registry operation
"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = r'^\.github/workflows/'
# proxy: proxy/, the core pin (the proxy sources and tools live in core/ since J12) and the two registries gen_tables.py reads; harness:
# harness/, the core pin and pc_deploy.py (the integration tests run
# `pc_deploy.py kit --what harness`); viewer: viewer/ and its test (J31). A workflow change runs all three. proxy/runs/ and viewer/runs/
# are committed run evidence, not build inputs (J42).
# harness also runs the Python tests that run bash on Windows (J22): those tests, the finder in setup.py, and the hook they run.
INPUTS = {
    'proxy': re.compile(rf'{WORKFLOWS}|^proxy/(?!runs/)|^core$|^registries/(engine_sites|config_keys)\.jsonl$'),
    'harness': re.compile(rf'{WORKFLOWS}|^harness/|^core$'
                          r'|^tests/test_(job_sh|pc_deploy|claude_hook|setup|proxy_host)\.py$'
                          r'|^tools/verbs/setup\.py$|^tools/claude_hook\.py$|^\.claude/settings\.json$'),
    'viewer': re.compile(rf'{WORKFLOWS}|^viewer/(?!runs/)|^tests/test_viewer\.py$'),
}


# Bump SALT to invalidate every CI pass marker at once (gates.yml keys them `ci-pass-<SALT>-<set>-<tree hash>`), for example when a
# runner image change could break a job whose inputs did not change.
SALT = '1'


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


def tree_entries(root, ref='HEAD', git=_git):
    """[(path, 'mode object')] of every file and gitlink in ref's tree (`core` is a gitlink: its pinned commit, without the submodule),
    or None when the tree cannot be read."""
    rc, lines = git(root, 'ls-tree', '-r', '--full-tree', ref)
    if rc != 0 or not lines:
        return None
    out = []
    for line in lines:
        meta, sep, path = line.partition('\t')
        parts = meta.split()
        if not sep or len(parts) != 3:
            return None
        out.append((path, f'{parts[0]} {parts[2]}'))
    return out


def tree_hashes(entries, salt=SALT):
    """{set: sha256 hex} over the sorted (mode, object, path) entries whose path the set's regex matches, with the set's name and the
    salt; entries None (the tree could not be read) gives '' for every set, which CI treats as "no marker can match": the job runs."""
    out = {}
    for k, rx in INPUTS.items():
        if entries is None:
            out[k] = ''
            continue
        h = hashlib.sha256(f'ci-pass {salt} {k}\n'.encode())
        for path, meta in sorted(entries):
            if rx.search(path):
                h.update(f'{meta}\t{path}\n'.encode())
        out[k] = h.hexdigest()
    return out


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
    for k, v in tree_hashes(tree_entries(ROOT)).items():
        print(f'{k}_tree={v}')
    print(f'tree_salt={SALT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
