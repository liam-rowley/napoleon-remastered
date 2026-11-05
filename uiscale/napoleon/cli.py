#!/usr/bin/env python3
r"""Build Napoleon's UI scale stop-gap at a factor (J66, D40): every vanilla layout, uied.templates, the slot fonts and the UI art, as packs plus a templates file.

purpose: write ui_scale_<f>x.pack (layouts + art), ui_scale_<f>x_fonts.pack, uied.templates.ui_scale_<f>x and the proxy rules file that redirects the loose templates to it, each with a .json (entries, sha256, held back, method), into <work> (default <state folder>\uiscale\work: tools/pc_state.py, the adapter's state_dir or $NAPOLEON_STATE_DIR)
usage: python3 core/wsc.py uiscale build [--factor 2] [--work DIR] [--no-art] [--no-fonts] [--limit N] [--jobs N]   |   ... uiscale status [--work DIR]
when: before `python3 upscale/pc/play.py install --scale 2` (Liam's 4K play test) and before a J66/J67 PC run; re-running reuses the art cache and gives byte-identical packs
not-a-verb: the build behind tools/verbs/uiscale.py (runs in the art_build Python: numpy, Pillow, freetype-py, uharfbuzz)

Reads the game read-only through core/discovery/packfs.py (mod packs skipped, so an installed scale pack never feeds its own build) and
the J36 masters under <state folder>\upscale\work. Nothing here writes the game folder.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
for p in ('uiscale/core', 'core/discovery', 'upscale/core', 'tools'):
    sys.path.insert(0, os.path.join(REPO, p))
import packfs  # noqa: E402
import pc_state  # noqa: E402
import scale  # noqa: E402
import tpl  # noqa: E402
import uic  # noqa: E402

CONFIG = os.path.join(HERE, 'config.json')
GAMES = os.path.join(REPO, 'discovery', 'napoleon', 'games.json')


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def tag_of(f):
    return ('%g' % f).replace('.', '')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)


def rel_file(pack_path):
    """pack entry path -> a relative file path under a work subfolder (Windows-safe: the entry's own folders)"""
    return pack_path.replace('\\', os.sep)


# ------------------------------------------------------------------------------------------------------------ layouts
def vanilla_layouts(fs):
    out = []
    for c in fs.list(under='ui\\'):
        if '.' in c.path.rsplit('\\', 1)[-1]:
            continue
        b = fs.read(c)
        if b.startswith(b'Version'):
            out.append((c.path, b))
    return out


def referenced_textures(layouts, templates_bytes):
    """{lower path without data\\: count} of every texture a vanilla layout or template image def names (not embedded ones)"""
    refs, emb = {}, set()

    def add(p):
        p = p.lower().replace('/', '\\')
        if p.startswith('data\\'):
            p = p[5:]
        if ':' in p or not p:
            return   # authoring-machine absolute paths (c:\tw\..., x:\...) do not map to a pack entry
        refs[p] = refs.get(p, 0) + 1
    for path, b in layouts:
        for _, c in uic.walk(uic.parse(b, path)['root']):
            for im in c['images']:
                if im['path']:
                    add(im['path'])
    for r in tpl.split(templates_bytes):
        try:
            doc = tpl.parse_record(r)
        except Exception:  # noqa: BLE001 (the v4 records)
            continue

        def rec(c):
            for t in c.get('textures', []):
                emb.add(t['path'].lower())
            for ch in c['children']:
                rec(ch)
        for t in doc['textures']:
            emb.add(t['path'].lower())
        rec(doc['root'])
        for _, c in uic.walk(doc['root']):
            for im in c['images']:
                if im['path'] and im['path'].lower() not in emb:
                    add(im['path'])
    return refs


# ---------------------------------------------------------------------------------------------------------------- art
def art_task(task):
    """worker: (pack path, ext, vanilla bytes, master file or None, factor, out file) -> info (runs in a child process)"""
    import art   # numpy/Pillow only in the worker
    path, ext, vanilla, master, f, out = task
    if master:
        with open(master, 'rb') as fh:
            blob, info = art.from_master(fh.read(), vanilla, ext, f)
    else:
        blob, info = art.from_vanilla(vanilla, ext, f)
    write_file(out, blob)
    info.update(path=path, bytes=len(blob), sha256=sha(blob))
    return info


def build_art(cfg, fs, refs, f, work, upscale_work, limit=0, jobs=0, log=print):
    """returns (entries [(pack path, bytes, rel, sha)], held_back [{path, reason}], methods {method: n})"""
    import pack as upack
    man = load(os.path.join(upscale_work, 'manifest.json'))['entries']
    roles = set(cfg['art_roles'])
    keep_vanilla = [s.lower() for s in cfg['art_keep_vanilla']]
    cands = {}   # lower path -> (pack path, master file or None, role)
    for e in man.values():
        if e['status'] == 'done' and e['role'] in roles:
            cands[e['path'].lower()] = (e['path'], os.path.join(upscale_work, e['out']['file']), e['role'], e['out']['sha256'])
    for p in refs:
        if p not in cands:
            c = fs.stat(p)
            if c is not None:
                cands[p] = (c.path, None, 'referenced', None)
    sub = f'art_{tag_of(f)}x'
    idx_path = os.path.join(work, sub, 'index.json')
    idx = load(idx_path) if os.path.exists(idx_path) else {}
    held, tasks, done = [], [], {}
    for low in sorted(cands):
        ppath, master, role, msha = cands[low]
        if any(k in low for k in keep_vanilla):
            held.append({'path': ppath, 'reason': 'kept_vanilla'})
            continue
        c = fs.stat(low)
        if c is None:
            held.append({'path': ppath, 'reason': 'no_vanilla_copy'})
            continue
        ext = low.rsplit('.', 1)[-1]
        van = fs.read(c)
        key = sha(van) + (':' + msha if master else ':lanczos') + ':%g' % f
        out = os.path.join(work, sub, rel_file(ppath))
        prev = idx.get(ppath)
        if prev and prev.get('key') == key and os.path.exists(out):
            done[ppath] = prev
            continue
        tasks.append(((ppath, ext, van, master, f, out), key, role))
        if limit and len(tasks) >= limit:
            break
    log(f'art: {len(cands)} candidates, {len(done)} cached, {len(tasks)} to make, {len(held)} kept vanilla or missing')
    t0 = time.time()
    with cf.ProcessPoolExecutor(max_workers=jobs or max(1, (os.cpu_count() or 2) - 1)) as ex:
        futs = {ex.submit(art_task, t): (key, role) for t, key, role in tasks}
        for i, fu in enumerate(cf.as_completed(futs), 1):
            key, role = futs[fu]
            info = fu.result()
            info.update(key=key, role=role)
            done[info['path']] = info
            if i % 500 == 0:
                log(f'art: {i}/{len(tasks)} in {time.time() - t0:.0f} s')
                write_file(idx_path, json.dumps(done, indent=0, sort_keys=True).encode())
    write_file(idx_path, json.dumps(done, indent=0, sort_keys=True).encode())
    entries, methods = [], {}
    for ppath in sorted(done, key=str.lower):
        info = done[ppath]
        why = upack.held_back_reason({'w': info['w'], 'h': info['h'], 'fmt': info['fmt']})
        if why:
            held.append({'path': ppath, 'reason': why})
            continue
        entries.append((ppath, info['bytes'], os.path.join(sub, rel_file(ppath)), info['sha256']))
        methods[info['method']] = methods.get(info['method'], 0) + 1
    return entries, held, methods


# -------------------------------------------------------------------------------------------------------------- fonts
def build_fonts(cfg, fs, names, work, f, log=print):
    import cuf_encode
    face = next((p for p in (os.path.join(REPO, f) for f in cfg['font_faces']) if os.path.isfile(p)), None)
    if not face:
        raise SystemExit(f'uiscale: no Lora face at any of {cfg["font_faces"]}: vendor it at uiscale/fonts/Lora-Variable.ttf (D42)')
    log(f'font face: {face}')
    out = cuf_encode.render_set(sorted(names), lambda n: fs.read('font\\' + n), face)
    sub = f'fonts_{tag_of(f)}x'
    entries, notes = [], {}
    for n in sorted(out):
        data, note = out[n]
        write_file(os.path.join(work, sub, n), data)
        entries.append(('font\\' + n, len(data), os.path.join(sub, n), sha(data)))
        notes[n] = note
        log(f'font: {n} {note}')
    return entries, notes


# -------------------------------------------------------------------------------------------------------------- build
def build(factor=2.0, work=None, no_art=False, no_fonts=False, limit=0, jobs=0, log=print):
    import pack as upack
    cfg = load(CONFIG)
    games = load(GAMES)
    if factor not in cfg['factors']:
        raise SystemExit(f'uiscale: factor {factor:g} is not built here (config factors {cfg["factors"]}; 1.25x and 1.5x are J67)')
    skip = set(games['napoleon'].get('mod_packs', ()))
    fs = packfs.PackFS(os.path.join(games['napoleon']['root'], games['napoleon']['data']), games['napoleon']['pack_order'], skip=skip)
    stray = [n for n in fs.packs if n.lower().startswith(('ui_scale_', 'ui_art_'))]
    if stray:
        raise SystemExit(f'uiscale: mod pack(s) {stray} in data\\ are not in mod_packs: add them to discovery/napoleon/games.json')
    work = work or str(pc_state.uiscale_work(REPO))
    tag = tag_of(factor)
    os.makedirs(work, exist_ok=True)
    stats = {}
    # layouts
    lays = vanilla_layouts(fs)
    lay_entries = []
    for path, b in lays:
        out = scale.layout_bytes(b, path, factor, cfg['scale_root'], stats)
        rel = os.path.join(f'layouts_{tag}x', rel_file(path))
        write_file(os.path.join(work, rel), out)
        lay_entries.append((path, len(out), rel, sha(out)))
    log(f'layouts: {len(lay_entries)} scaled, {stats.get("keyframes", 0)} keyframes')
    # templates
    tpath = os.path.join(games['napoleon']['root'], cfg['templates_vanilla'])
    tvan = open(tpath, 'rb').read()
    tst = {}
    tout, trep = scale.scale_templates_file(tvan, factor, stats=tst)
    tname = cfg['templates_name'].format(tag=tag)
    write_file(os.path.join(work, tname), tout)
    tmeta = {'file': tname, 'factor': factor, 'vanilla_sha256': sha(tvan), 'sha256': sha(tout), 'bytes': len(tout),
             'scaled': len(trep['scaled']), 'passed': trep['passed'], 'upgraded_to_v33': trep['upgraded'], 'fonts': tst.get('fonts', {})}
    write_file(os.path.join(work, tname + '.json'), (json.dumps(tmeta, indent=1) + '\n').encode())
    log(f'templates: {len(trep["scaled"])} scaled, passed {trep["passed"]}, upgraded {trep["upgraded"]}, {len(tout) / 1e6:.1f} MB')
    rules = os.path.join(work, cfg['rules_name'].format(tag=tag))
    write_file(rules, ('# J66 UI scale %sx: the loose templates the engine opens (attribute check and CreateFileA) come from the scaled file\n'
                       'redirect %s -> %s\n' % (tag, cfg['templates_vanilla'].lower(), os.path.join(work, tname))).encode())
    # fonts
    fonts = dict(stats.get('fonts', {}))
    for k, v in tst.get('fonts', {}).items():
        fonts[k] = fonts.get(k, 0) + v
    names = sorted({scale.font_file(n) for n in fonts if scale.font_file(n)})
    log(f'fonts named by the scaled layouts and templates: {names}')
    metas = {}
    if not no_fonts:
        fent, notes = build_fonts(cfg, fs, names, work, factor, log)
        metas['fonts'] = upack.build(cfg['fonts_pack_name'].format(tag=tag), fent, work, work, log=log,
                                     extra={'factor': factor, 'method': 'Lora (uiscale/fonts) via uiscale/core/cuf_encode.py, Empire recipe',
                                            'notes': notes, 'slot_uses': fonts})
    # art + layouts pack
    held, methods, aent = [], {}, []
    if not no_art:
        refs = referenced_textures(lays, tvan)
        aent, held, methods = build_art(cfg, fs, refs, factor, work, str(pc_state.upscale_work(REPO)), limit, jobs, log)
    ents = sorted(lay_entries + aent, key=lambda e: e[0].lower())
    metas['pack'] = upack.build(cfg['pack_name'].format(tag=tag), ents, work, work, log=log,
                                extra={'factor': factor, 'layouts': len(lay_entries), 'art': len(aent), 'art_methods': methods,
                                       'held_back': held, 'scale_root': cfg['scale_root']})
    summary = {'factor': factor, 'packs': {k: {'pack': m['pack'], 'sha256': m['sha256'], 'bytes': m['bytes'], 'entries': m['entries']}
                                           for k, m in metas.items()},
               'templates': {'file': tname, 'sha256': tmeta['sha256'], 'bytes': len(tout)}, 'rules': os.path.basename(rules)}
    write_file(os.path.join(work, f'build_{tag}x.json'), (json.dumps(summary, indent=1) + '\n').encode())
    log(json.dumps(summary, indent=1))
    return summary


def status(work=None):
    cfg = load(CONFIG)
    work = work or str(pc_state.uiscale_work(REPO))
    for f in cfg['factors']:
        p = os.path.join(work, f'build_{tag_of(f)}x.json')
        print(open(p, encoding='utf-8').read() if os.path.exists(p) else f'uiscale: no {f:g}x build in {work}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['build', 'status'])
    ap.add_argument('--factor', type=float, default=2.0)
    ap.add_argument('--work')
    ap.add_argument('--no-art', action='store_true')
    ap.add_argument('--no-fonts', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='art: at most N new images (a smoke build)')
    ap.add_argument('--jobs', type=int, default=0, help='art worker processes (default: CPUs - 1)')
    a = ap.parse_args(argv)
    if a.action == 'status':
        return status(a.work)
    build(a.factor, a.work, a.no_art, a.no_fonts, a.limit, a.jobs)
    return 0


if __name__ == '__main__':
    sys.exit(main())
