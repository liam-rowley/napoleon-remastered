"""Pack builder of the UI art upscaler (J36): a movie-type PFH0 pack from the verified outputs, sha-checked while copying and again after.

purpose: build <name>.pack (PFH0, type 4) from the manifest's finished assets under an entry prefix, writing <name>.pack.building first and renaming only after an independent re-read passes; write <name>.pack.json (entries, sha256, model credits)
usage: library (upscale/core), driven by `python3 core/wsc.py upscale pack`; python3 upscale/core/pack.py check <file.pack> <file.pack.json>
when: after `wsc upscale verify` is clean for the roles to pack
not-a-verb: a library used by tools/verbs/upscale.py, not a registry operation

Ported from empire-remastered art_mod/tools/build_texture_pack.py (read-only evidence): two-phase write, per-entry sha256 check against the
manifest while copying, independent re-read before the rename. The pack never replaces a vanilla pack (D2) and entries sit under a
prefix (default ui_art_2x5\\), so no vanilla path is overridden. Standard library only.
"""
import hashlib
import json
import os
import struct
import sys
import time

PTYPE_MOVIE = 4


def plan(man, work, roles, prefix, only_ok=None):
    """sorted [(entry path, bytes, file, sha256)] for the done assets of `roles` (None = all); only_ok = ids that verified clean"""
    out = []
    for i, e in sorted(man['entries'].items()):
        if e['status'] != 'done' or (roles and e['role'] not in roles) or (only_ok is not None and i not in only_ok):
            continue
        out.append((prefix + e['path'], e['out']['bytes'], e['out']['file'], e['out']['sha256']))
    return sorted(out)


def index_bytes(entries):
    return b''.join(struct.pack('<I', size) + name.encode('latin1') + b'\0' for name, size, _, _ in entries)


def read_pack(path):
    """independent re-read: (type, [(name, size, offset)])"""
    with open(path, 'rb') as f:
        hd = f.read(24)
        if hd[:4] != b'PFH0':
            raise ValueError('%s: not PFH0' % path)
        ptype, _, prs, n, isz = struct.unpack_from('<5I', hd, 4)
        f.read(prs)
        idx = f.read(isz)
    out, pos, off = [], 0, 24 + prs + isz
    for _ in range(n):
        size, = struct.unpack_from('<I', idx, pos)
        e = idx.index(b'\0', pos + 4)
        out.append((idx[pos + 4:e].decode('latin1'), size, off))
        pos = e + 1
        off += size
    if pos != isz:
        raise ValueError('%s: index size mismatch' % path)
    return ptype, out


def check_pack(path, entries):
    """re-read `path` and compare it to the plan: type, index, end of data, per-entry sha256. Returns the file sha256."""
    ptype, idx = read_pack(path)
    if ptype != PTYPE_MOVIE:
        raise ValueError('pack type %d, expected %d' % (ptype, PTYPE_MOVIE))
    if [(n, s) for n, s, _ in idx] != [(e[0], e[1]) for e in entries]:
        raise ValueError('index differs from the plan')
    end = idx[-1][2] + idx[-1][1] if idx else 24
    if os.path.getsize(path) != end:
        raise ValueError('file size %d, end of data %d' % (os.path.getsize(path), end))
    with open(path, 'rb') as f:
        for (name, size, off), e in zip(idx, entries):
            f.seek(off)
            if hashlib.sha256(f.read(size)).hexdigest() != e[3]:
                raise ValueError('%s: data sha256 differs from the manifest' % name)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def build(name, entries, work, out_dir, credits=(), force=False, log=print):
    """Build <out_dir>/<name>.pack. Returns {'pack','sha256','entries','bytes'}; a finished pack with the same plan is kept."""
    os.makedirs(out_dir, exist_ok=True)
    final = os.path.join(out_dir, name + '.pack')
    building = final + '.building'
    sig = hashlib.sha256(json.dumps(entries).encode()).hexdigest()
    meta = final + '.json'
    if os.path.exists(final) and os.path.exists(meta) and not force:
        m = json.load(open(meta, encoding='utf-8'))
        if m.get('plan') == sig:
            log('%s: already built (%d entries)' % (name, len(entries)))
            return m
    index = index_bytes(entries)
    with open(building, 'wb') as w:
        w.write(b'PFH0' + struct.pack('<5I', PTYPE_MOVIE, 0, 0, len(entries), len(index)) + index)
        for pname, size, rel, sha in entries:
            with open(os.path.join(work, rel), 'rb') as f:
                d = f.read()
            if len(d) != size or hashlib.sha256(d).hexdigest() != sha:
                raise RuntimeError('%s changed since the run (size or sha256 vs the manifest): re-run' % rel)
            w.write(d)
        w.flush()
        os.fsync(w.fileno())
    sha = check_pack(building, entries)
    os.replace(building, final)
    m = {'pack': name + '.pack', 'type': 'movie (4)', 'sha256': sha, 'bytes': os.path.getsize(final), 'entries': len(entries), 'plan': sig,
         'built_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'credits': list(credits),
         'files': [{'path': e[0], 'bytes': e[1], 'sha256': e[3]} for e in entries]}
    with open(meta, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(m, f, indent=1)
    log('%s: %d entries, %.1f MB, sha256 %s' % (name, len(entries), m['bytes'] / 1e6, sha[:16]))
    return m


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'check':
        m = json.load(open(sys.argv[3], encoding='utf-8'))
        ents = [(f['path'], f['bytes'], None, f['sha256']) for f in m['files']]
        print('ok', check_pack(sys.argv[2], ents))
    else:
        print(__doc__)
