#!/usr/bin/env python3
"""Font licence record for the release (J37 for J38): read a TTF's name table, and check the font_licences.json rows against the face and licence files.

purpose: read the licence facts of a TrueType face from its own name table (family, version, copyright, licence, licence URL, reserved font names) and check a font_licences.json: every row has every field, the pinned sha256 of the TTF (when the face is present) and of the licence text match the files
usage: python3 uiscale/core/licences.py read <face.ttf>   |   python3 uiscale/core/licences.py check [--data uiscale/napoleon/font_licences.json]   (also `python3 core/wsc.py uiscale licences [--check]`)
when: before a release build (J38's LICENSES.txt generator reads the json), after a face or licence change; the tests gate runs the check through tests/test_uiscale_engine_text.py
not-a-verb: a small library and CLI behind `wsc uiscale licences`, not a registry operation

Not legal advice: this records what the files say, so a human can check it.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, 'uiscale', 'napoleon', 'font_licences.json')
FIELDS = ('component', 'family', 'version', 'licence', 'spdx', 'copyright', 'reserved_font_name', 'rfn_meaning', 'source_url',
          'face_file', 'face_sha256', 'licence_file', 'licence_sha256', 'date_checked', 'shipped')
NAME_IDS = {0: 'copyright', 1: 'family', 5: 'version', 13: 'licence_text', 14: 'licence_url'}


def name_table(data):
    """{nameID: str} from a TTF/OTF name table (Windows Unicode BMP records first, then Mac Roman)"""
    num = struct.unpack_from('>H', data, 4)[0]
    tables = {}
    for i in range(num):
        tag, _, off, ln = struct.unpack_from('>4sIII', data, 12 + 16 * i)
        tables[tag] = (off, ln)
    off, _ = tables[b'name']
    _, count, soff = struct.unpack_from('>HHH', data, off)
    out, rank = {}, {}
    for i in range(count):
        pid, eid, lid, nid, ln, so = struct.unpack_from('>HHHHHH', data, off + 6 + 12 * i)
        raw = data[off + soff + so: off + soff + so + ln]
        if pid == 3 and eid in (0, 1):
            r, s = (0 if lid == 0x409 else 1), raw.decode('utf-16-be', 'replace')
        elif pid == 1 and eid == 0:
            r, s = 2, raw.decode('mac_roman', 'replace')
        else:
            continue
        if nid not in rank or r < rank[nid]:
            out[nid], rank[nid] = s, r
    return out


def read_face(path):
    """the licence facts a face states about itself"""
    with open(path, 'rb') as f:
        data = f.read()
    n = name_table(data)
    info = {k: n.get(i, '') for i, k in NAME_IDS.items()}
    info['reserved_font_names'] = re.findall(r'Reserved Font Names? [\'"“]([^\'"”]+)[\'"”]', info['copyright'])
    info['sha256'] = hashlib.sha256(data).hexdigest()
    info['bytes'] = len(data)
    return info


def sha_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def check(rows, root=REPO, face_paths=None):
    """problems [str] for the rows. A row's face_file may be absent (fetched by pin, not committed): its sha is checked only when a file is found
    at face_file or at one of face_paths; the licence file must be present."""
    problems = []
    for i, r in enumerate(rows):
        tag = r.get('component', f'row {i}')
        for k in FIELDS:
            if k not in r or r[k] in (None, ''):
                problems.append(f'{tag}: missing {k}')
        if problems and problems[-1].startswith(tag):
            continue
        lp = os.path.join(root, r['licence_file'])
        if not os.path.isfile(lp):
            problems.append(f'{tag}: licence file {r["licence_file"]} not found')
        elif sha_file(lp) != r['licence_sha256']:
            problems.append(f'{tag}: {r["licence_file"]} sha256 changed (pinned {r["licence_sha256"][:12]})')
        cands = [os.path.join(root, r['face_file'])] + list(face_paths or ())
        face = next((p for p in cands if os.path.isfile(p)), None)
        if face and sha_file(face) != r['face_sha256']:
            problems.append(f'{tag}: face {face} sha256 differs from the pin {r["face_sha256"][:12]}')
        elif face:
            info = read_face(face)
            if r['family'] not in info['family']:
                problems.append(f'{tag}: the face names its family {info["family"]!r}, not {r["family"]!r}')
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['read', 'check'])
    ap.add_argument('face', nargs='?')
    ap.add_argument('--data', default=DATA)
    a = ap.parse_args(argv)
    if a.action == 'read':
        print(json.dumps(read_face(a.face), indent=1, ensure_ascii=False))
        return 0
    with open(a.data, encoding='utf-8') as f:
        d = json.load(f)
    faces = []
    cfg = os.path.join(REPO, 'uiscale', 'napoleon', 'config.json')
    if os.path.exists(cfg):
        with open(cfg, encoding='utf-8') as f:
            faces = [p if os.path.isabs(p) else os.path.join(REPO, p) for p in json.load(f).get('font_faces', [])]
    probs = check(d['fonts'], face_paths=faces)
    for p in probs:
        print('licences: ' + p)
    print('licences: %d row(s), %s' % (len(d['fonts']), 'ok' if not probs else f'{len(probs)} problem(s)'))
    return 1 if probs else 0


if __name__ == '__main__':
    sys.exit(main())
