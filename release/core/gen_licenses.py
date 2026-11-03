#!/usr/bin/env python3
"""Generate LICENSES.txt from a licence data file and check it against the release components.

purpose: render LICENSES.txt (every shipped third-party component with its licence, copyright line, source URL, date checked and text; not-yet-shipped components listed apart) from release/napoleon/licenses.json, and fail a shipped component with no entry or an entry marked shipped with no component
usage: python3 release/core/gen_licenses.py [--data release/napoleon/licenses.json] [--components release/napoleon/components.json] [--out FILE] [--check]
when: build_release.py calls it for every release; the licence gate (tests/test_release.py) calls its checks; run it by hand after editing licenses.json to see the text
not-a-verb: a release-builder helper (release/core), not a registry operation; a core candidate with the rest of release/core (rule 76)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NOT_LEGAL_ADVICE = ('This file is a list of the third-party components in this release and the licences they come with. It is not legal advice, '
                    'and the licence texts below are copied from the sources named, on the dates given.')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def entry_text(e, root=ROOT):
    if e.get('text') is not None:
        return e['text']
    if e.get('text_file'):
        return (Path(root) / e['text_file']).read_text(encoding='utf-8')
    return None


def problems(data, components, root=ROOT):
    """Errors: a shipped component (named by a component row's licences) with no entry, a shipped entry no component names, an entry whose text
    does not match its pinned sha256, a duplicate id, a field missing."""
    errs, ids = [], {}
    for e in data['entries']:
        if e['id'] in ids:
            errs.append(f"licence entry {e['id']}: duplicate id")
        ids[e['id']] = e
        for k in ('name', 'licence', 'copyright', 'source_url', 'checked', 'shipped'):
            if k not in e:
                errs.append(f"licence entry {e['id']}: no `{k}`")
        if e.get('shipped') and entry_text(e, root) is None and 'creativecommons.org' not in e.get('checked_how', ''):
            errs.append(f"licence entry {e['id']}: shipped with no text (`text`, `text_file`, or a checked_how that points at the licence URL)")
        if e.get('text_sha256') and entry_text(e, root) is not None and hashlib.sha256(entry_text(e, root).encode('utf-8')).hexdigest() != e['text_sha256']:
            errs.append(f"licence entry {e['id']}: text sha256 differs from the pinned {e['text_sha256'][:12]}")
    named = {}
    for c in components['components']:
        for lid in c.get('licences', []):
            named.setdefault(lid, []).append(c['id'])
            if lid not in ids:
                errs.append(f"component {c['id']} ships {lid}, which has no entry in the licence data")
            elif not ids[lid].get('shipped'):
                errs.append(f"component {c['id']} ships {lid}, whose entry says shipped=false")
    for lid, e in ids.items():
        if e.get('shipped') and lid not in named:
            errs.append(f"licence entry {lid} is marked shipped but no component names it")
    return errs


def pending(data):
    """The two decisions Liam owns (open question 2): the lines that read 'pending' make the builder warn."""
    return [k for k in ('statement', 'own_code_licence') if str(data.get(k, 'pending')).strip().lower() == 'pending']


def render(data, root=ROOT):
    L = ['NAPOLEON REMASTERED - THIRD-PARTY LICENCES AND NOTICES', '', NOT_LEGAL_ADVICE, '']
    st = data.get('statement', 'pending')
    own = data.get('own_code_licence', 'pending')
    L += ['Napoleon Remastered is an unofficial, fan-made modification. Statement: ' + ('[pending: wording not decided yet]' if st == 'pending' else st),
          'The licence of Napoleon Remastered\'s own code: ' + ('[pending: not decided yet]' if own == 'pending' else own), '']
    shipped = [e for e in data['entries'] if e.get('shipped')]
    later = [e for e in data['entries'] if not e.get('shipped')]
    L += ['CONTENTS (components in this release)'] + [f"  {e['name']}  --  {e['licence']}" for e in shipped] + ['']
    for e in shipped:
        L += ['=' * 78, f"{e['name']}  --  {e['licence']}", f"Copyright : {e['copyright']}", f"Source    : {e['source_url']}",
              f"Checked   : {e['checked']} ({e.get('checked_how', '')})"]
        if e.get('credit_line'):
            L += ['CREDIT LINE (required):', '    ' + e['credit_line']]
        t = entry_text(e, root)
        if t is not None:
            L += ['', 'LICENCE TEXT:', '', t.rstrip('\n')]
        L += ['']
    if later:
        L += ['=' * 78, 'NOT IN THIS RELEASE (listed so the notice is ready when the component ships; each is checked again when it does)', '']
        for e in later:
            L += [f"  {e['name']}  --  {e['licence']}", f"    Copyright: {e['copyright']}", f"    Source   : {e['source_url']}  (checked {e['checked']})"]
        L += ['']
    return '\n'.join(L).replace('\r\n', '\n').replace('\n', '\r\n') + '\r\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--data', default=str(ROOT / 'release' / 'napoleon' / 'licenses.json'))
    ap.add_argument('--components', default=str(ROOT / 'release' / 'napoleon' / 'components.json'))
    ap.add_argument('--out')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data, comps = load(a.data), load(a.components)
    errs = problems(data, comps)
    for k in pending(data):
        print(f'gen_licenses: warning: {k} is still pending (Liam decides)')
    if errs:
        print('gen_licenses: INVALID\n  ' + '\n  '.join(errs))
        return 1
    text = render(data)
    if a.out:
        Path(a.out).write_bytes(text.encode('utf-8'))
        print(f'gen_licenses: wrote {a.out} ({len(text)} chars)')
    elif not a.check:
        sys.stdout.write(text)
    else:
        print('gen_licenses: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
