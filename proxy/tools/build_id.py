#!/usr/bin/env python3
"""The proxy DLL's build id: a hash of the DLL inputs' content at a commit, the one implementation (J45).

purpose: print the 12-hex build id of the DLL inputs (their git object ids at a revision, each under a fixed role name), plus -dirty when an input differs from HEAD
usage: python3 proxy/tools/build_id.py [--root .] [--rev HEAD] [--no-dirty] [--inputs]   (--inputs: print each role, path and object id instead)
when: build.sh calls it for every DLL build; tools/pr_policy.py imports it for rule 79; run it by hand to see which id a DLL or a ledger line should carry
not-a-verb: a build helper shared by build.sh and the policy check, not a registry operation

Why content and not a commit: the id used to be the last commit that touched the inputs (J1 review finding 2: not HEAD, so a report
commit does not change the binary). A reword, rebase or cherry-pick then gave a new id over identical code and rule 79 refused a
branch whose 20 acceptance passes ran on that code (J44 review finding 2). Object ids follow content only, so the id survives any
history edit that leaves the inputs alone, and a shallow clone computes the same id as a full one. Role names, not paths, go into
the hash, so the id depends on nothing but the inputs' content. Old ledger lines keep their commit-hash ids as a record.
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The DLL inputs (rule 79's scope; unchanged by J45 apart from this file): role -> path. A change to any of them is a new DLL.
INPUTS = [('core', 'proxy/core'), ('adapter', 'proxy/napoleon'), ('build_sh', 'proxy/tools/build.sh'),
          ('fetch_lua', 'proxy/tools/fetch_lua.py'), ('build_id', 'proxy/tools/build_id.py')]


def _git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)


def object_ids(root=ROOT, rev='HEAD'):
    """[(role, path, object id)] at `rev`; raises ValueError naming an input that is not tracked there (never a silent fallback)."""
    out = []
    for role, path in INPUTS:
        p = _git(root, 'rev-parse', '--verify', '--quiet', f'{rev}:{path}')
        if p.returncode != 0 or not p.stdout.strip():
            raise ValueError(f'build_id: {path} ({role}) is not tracked at {rev}')
        out.append((role, path, p.stdout.strip()))
    return out


def content_id(oids):
    """12 hex of sha256 over 'role oid' lines in INPUTS order."""
    return hashlib.sha256(''.join(f'{role} {oid}\n' for role, _, oid in oids).encode()).hexdigest()[:12]


def build_id(root=ROOT, rev='HEAD', dirty=True):
    """The build id at `rev`; 'nogit' outside a git checkout; '-dirty' appended when `dirty` and an input differs from HEAD."""
    if _git(root, 'rev-parse', '--git-dir').returncode != 0:
        return 'nogit'
    bid = content_id(object_ids(root, rev))
    if dirty and _git(root, 'diff', '--quiet', 'HEAD', '--', *[p for _, p in INPUTS]).returncode != 0:
        bid += '-dirty'
    return bid


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=str(ROOT), help='the checkout (default: this repo)')
    ap.add_argument('--rev', default='HEAD', help='the revision whose inputs are hashed')
    ap.add_argument('--no-dirty', action='store_true', help='never append -dirty (the committed id only)')
    ap.add_argument('--inputs', action='store_true', help='print role, path and object id per input')
    a = ap.parse_args(argv)
    try:
        if a.inputs:
            for role, path, oid in object_ids(a.root, a.rev):
                print(f'{role}\t{path}\t{oid}')
        else:
            print(build_id(a.root, a.rev, dirty=not a.no_dirty))
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
