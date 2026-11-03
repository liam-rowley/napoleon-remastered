#!/usr/bin/env python3
r"""Build Napoleon's UI scale stop-gap at a factor (J66, J67, D40): every vanilla layout, the patched UI scripts, uied.templates, the slot fonts and the UI art, as packs plus a templates file; classify and check the Lua pixel constants; check a factor against a screen.

purpose: write ui_scale_<tag>x.pack (layouts, patched Lua scripts, art), ui_scale_<tag>x_fonts.pack, uied.templates.ui_scale_<tag>x and the proxy rules file that redirects the loose templates to it, each with a .json, into <work> (C:\napoleon_remastered_pc\uiscale\work); write uiscale/napoleon/lua_consts.json and lua_patches.txt (lua-consts); verify the patch list's asserts (lua-patches --check); report a factor's overflow at a screen size (check)
usage: python3 core/wsc.py uiscale build [--factor 1.25|1.5|2] [--work DIR] [--no-art] [--no-fonts] [--no-lua] [--limit N] [--jobs N]   |   ... uiscale status [--work DIR]   |   ... uiscale lua-consts [--scripts DIR] [--check]   |   ... uiscale lua-patches [--check] [--factor F] [--scripts DIR]   |   ... uiscale check --factor F --height H [--width W] [--scripts DIR]
when: before `python3 upscale/pc/play.py install --scale F` (Liam's play test) and before a J66/J67 PC run; lua-consts after a change to the classifier or its overrides, lua-patches --check after a game update; re-running gives byte-identical packs and lists
not-a-verb: the build behind tools/verbs/uiscale.py (build runs in the art_build Python: numpy, Pillow, freetype-py; lua-consts, lua-patches and check need only the standard library)

Reads the game read-only through discovery/core/packfs.py (mod packs skipped, so an installed scale pack never feeds its own build), or with
--scripts an extract folder (extract/napoleon, core/proxy/tools/pack_list.py --extract), and the J36 masters under
C:\napoleon_remastered_pc\upscale\work. Nothing here writes the game folder.
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
for p in ('uiscale/core', 'discovery/core', 'upscale/core'):
    sys.path.insert(0, os.path.join(REPO, p))
import packfs  # noqa: E402
import scale  # noqa: E402
import tpl  # noqa: E402
import uic  # noqa: E402

CONFIG = os.path.join(HERE, 'config.json')
GAMES = os.path.join(REPO, 'discovery', 'napoleon', 'games.json')
ASSETS = os.path.join(REPO, 'registries', 'assets.jsonl')
LUA_CONSTS = os.path.join(HERE, 'lua_consts.json')
LUA_PATCHES = os.path.join(HERE, 'lua_patches.txt')
LUA_OVERRIDES = os.path.join(HERE, 'lua_overrides.json')
LUA_EMPIRE = os.path.join(HERE, 'lua_empire_items.json')
FONT_SLOTS = os.path.join(HERE, 'font_slots.json')


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


# ---------------------------------------------------------------------------------------------------------------- Lua
def script_ids():
    """{pack entry path (lower case): asset id} of every compiled UI script in the assets registry"""
    out = {}
    with open(ASSETS, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r.get('format') == 'luac':
                out[r['path'].lower()] = r['id']
    return out


def game_fs(games=None):
    games = games or load(GAMES)
    skip = set(games['napoleon'].get('mod_packs', ()))
    return packfs.PackFS(os.path.join(games['napoleon']['root'], games['napoleon']['data']), games['napoleon']['pack_order'], skip=skip)


def lua_scripts(scripts_dir=None, fs=None):
    """{asset id: vanilla chunk bytes} of every UI script, from an extract folder (pack order applied) or the game's packs"""
    ids = script_ids()
    out = {}
    if scripts_dir:
        games = load(GAMES)
        order = games['napoleon']['pack_order']
        for stem in sorted(os.listdir(scripts_dir), key=lambda s: order.index(s) if s in order else -1):
            base = os.path.join(scripts_dir, stem)
            for d, _, files in os.walk(base):
                for fn in files:
                    if fn.lower().endswith('.luac'):
                        rel = os.path.relpath(os.path.join(d, fn), base).replace(os.sep, '\\').replace('/', '\\').lower()
                        if rel in ids:
                            with open(os.path.join(d, fn), 'rb') as f:
                                out[ids[rel]] = f.read()
    else:
        fs = fs or game_fs()
        for c in fs.list(under='ui\\'):
            p = c.path.lower()
            if p.endswith('.luac') and p in ids:
                out[ids[p]] = fs.read(c)
    return dict(sorted(out.items()))


def lua_paths():
    return {v: k for k, v in script_ids().items()}


LUA_HEADER = """# Napoleon UI scale: Lua pixel constants (J67). GENERATED by `python3 core/wsc.py uiscale lua-consts` from lua_consts.json
# (uiscale/core/lua_consts.py rules + lua_overrides.json): do not edit; change the overrides and regenerate.
# Syntax: uiscale/core/lua_patch.py. Every number is in vanilla pixels; the build writes px(v * factor), px(x) = floor(x + 0.5),
# and every item asserts the vanilla constant or instruction it changes. One list for every factor.
"""


def lua_consts_doc(scripts):
    import lua_consts
    ovd = load(LUA_OVERRIDES)
    ov = ovd['overrides']
    doc = lua_consts.classify(scripts, ov)
    for r in doc['rows']:                                    # whole scripts another job owns (J37: map and unit labels)
        why = ovd.get('exclude_scripts', {}).get(r['script'])
        if why and r['class'] != 'leave':
            r['class'], r['reason'], r['by'] = 'leave', why, 'exclude_scripts'
    emp = load(LUA_EMPIRE) if os.path.exists(LUA_EMPIRE) else {'items': []}
    rows = doc['rows']
    cross = []
    for it in emp['items']:
        hit = [r for r in rows if r['script'] == it['script'] and it['value'] is not None and abs(r['value'] - it['value']) < 1e-4]
        cross.append(dict(it, napoleon=sorted({r['class'] for r in hit}),
                          napoleon_rows=sorted({f"{r['func']}:{r['k']}@{r['pc']}" for r in hit})[:6]))
    counts = lua_consts.counts(doc)
    used = {(o['script'], o['func'], o['k'], o.get('pc')) for o in ov}
    hit = {(r['script'], r['func'], r['k'], r['pc']) for r in rows} | {(r['script'], r['func'], r['k'], None) for r in rows}
    stale = sorted('%s %s:%s@%s' % k for k in used - hit)
    if stale:
        raise SystemExit(f'uiscale: overrides that match no row (stale after a game update or a classifier change): {stale}')
    if any(r['class'] not in ('scale', 'set', 'leave', 'manual') for r in rows):
        raise SystemExit('uiscale: unclassified rows')
    sha = {sid: hashlib.sha256(b).hexdigest() for sid, b in scripts.items()}
    return {'note': 'Every numeric constant of the vanilla UI scripts that reaches a pixel-taking engine call or a position or size calculation '
                    '(uiscale/core/lua_consts.py), with its class (scale, set, leave with a reason, manual). GENERATED by '
                    '`python3 core/wsc.py uiscale lua-consts`; hand classes are in lua_overrides.json; the patch list is lua_patches.txt.',
            'scripts': len(scripts), 'scripts_with_rows': len({r['script'] for r in rows}), 'counts': counts,
            'script_sha256': {sid: sha[sid] for sid in sorted({r['script'] for r in rows})},
            'rows': rows, 'empire': cross}


def lua_consts_cmd(scripts_dir=None, check_only=False):
    import lua_patch
    scripts = lua_scripts(scripts_dir)
    if not scripts:
        print('uiscale: no UI scripts found (no game and no --scripts extract)')
        return 1
    doc = lua_consts_doc(scripts)
    jtext = json.dumps(doc, indent=0, sort_keys=False) + '\n'
    ptext = lua_patch.write_list(doc, scripts, LUA_HEADER)
    lua_patch.parse_list(ptext)
    for sid, items in lua_patch.parse_list(ptext):          # the list applies at every factor and changes nothing at 1.0
        for f in (1.0, 1.25, 1.5, 2.0):
            out, _ = lua_patch.apply(scripts[sid], items, f)
            if f == 1.0 and out != scripts[sid]:
                raise SystemExit(f'uiscale: {sid}: the list changes the script at factor 1.0')
    old_j = open(LUA_CONSTS, encoding='utf-8').read() if os.path.exists(LUA_CONSTS) else None
    old_p = open(LUA_PATCHES, encoding='utf-8').read() if os.path.exists(LUA_PATCHES) else None
    if check_only:
        same = old_j == jtext and old_p == ptext
        print(f'uiscale lua-consts: {"identical" if same else "DIFFERS"} ({doc["counts"]})')
        return 0 if same else 1
    with open(LUA_CONSTS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(jtext)
    with open(LUA_PATCHES, 'w', encoding='utf-8', newline='\n') as f:
        f.write(ptext)
    n = sum(len(i) for _, i in lua_patch.parse_list(ptext))
    print(f'uiscale lua-consts: {len(doc["rows"])} rows in {doc["scripts_with_rows"]} of {doc["scripts"]} scripts, {doc["counts"]}; '
          f'{n} patch items in {len(lua_patch.parse_list(ptext))} scripts -> {os.path.relpath(LUA_PATCHES, REPO)}')
    return 0


def lua_patches_cmd(check=False, factor=2.0, scripts_dir=None):
    import lua_patch
    entries = lua_patch.parse_list(open(LUA_PATCHES, encoding='utf-8').read())
    scripts = lua_scripts(scripts_dir)
    if check:
        bad = lua_patch.check(entries, scripts)
        for b in bad:
            print('uiscale lua-patches: ' + b)
        print(f'uiscale lua-patches --check: {len(entries)} scripts, {sum(len(i) for _, i in entries)} items, '
              f'{"every assert holds" if not bad else f"{len(bad)} FAILED"}')
        return 1 if bad else 0
    for sid, items in entries:
        _, log = lua_patch.apply(scripts[sid], items, factor)
        print(f'{sid}: ' + '; '.join(log))
    return 0


def lua_entries(scripts, factor, work, tag, log=print):
    """the patched scripts as pack entries (at each script's own pack path), written under work/lua_<tag>x"""
    import lua_patch
    paths = lua_paths()
    out = []
    for sid, items in lua_patch.parse_list(open(LUA_PATCHES, encoding='utf-8').read()):
        data, _ = lua_patch.apply(scripts[sid], items, factor)
        rel = os.path.join(f'lua_{tag}x', rel_file(paths[sid]))
        write_file(os.path.join(work, rel), data)
        out.append((paths[sid], len(data), rel, sha(data)))
    log(f'lua: {len(out)} scripts patched')
    return out


# -------------------------------------------------------------------------------------------------------------- check
def layouts_from(scripts_dir=None, fs=None):
    if scripts_dir:
        out = {}
        games = load(GAMES)
        order = games['napoleon']['pack_order']
        for stem in sorted(os.listdir(scripts_dir), key=lambda s: order.index(s) if s in order else -1):
            base = os.path.join(scripts_dir, stem, 'ui')
            for d, _, files in os.walk(base):
                for fn in files:
                    if '.' in fn:
                        continue
                    p = os.path.join(d, fn)
                    with open(p, 'rb') as f:
                        b = f.read()
                    if b.startswith(b'Version'):
                        out[os.path.relpath(p, os.path.join(scripts_dir, stem)).replace(os.sep, '\\').lower()] = b
        return sorted(out.items())
    return vanilla_layouts(fs or game_fs())


def check_cmd(factor, height, width=None, scripts_dir=None):
    import check
    width = width or int(round(height * 16 / 9))
    slots = {r['slot'] for r in load(FONT_SLOTS)['layouts'] if r['factor'] == factor}
    rep = check.check_layouts(layouts_from(scripts_dir), factor, width, height, slots or None)
    print(f'uiscale check: factor {factor:g} at {width}x{height}: {rep["layouts"]} layouts; '
          f'{len(rep["loses_content"])} lose content against 1080p {rep["loses_content"]}; {len(rep["bleed"])} bleed by at most '
          f'{check.BLEED} vanilla px {rep["bleed"]}; {len(rep["overflow"]) - len(rep["loses_content"]) - len(rep["bleed"])} overflow '
          f'1080p too (bleeds, scroll areas, parked parts); {len(rep["abutting"])} abutting pairs off; '
          f'fonts missing from the slot table: {rep["fonts_missing"] or "none"}')
    for o in rep['overflow']:
        print('  ', json.dumps(o))
    return 1 if rep['loses_content'] or rep['abutting'] or rep['fonts_missing'] else 0


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
    rows = {r['slot']: r for r in load(FONT_SLOTS)['layouts'] if r['factor'] == f}
    miss = sorted(set(names) - set(rows))
    if miss:
        raise SystemExit(f'uiscale: the scaled layouts name slot fonts {miss} that font_slots.json has no {f:g}x row for')
    out = cuf_encode.render_set(sorted(names), lambda n: fs.read('font\\' + n), face,
                                scale={n: rows[n]['render_scale'] for n in names},
                                spaced={n: rows[n]['spaced_h2'] for n in names if rows[n].get('spaced_h2')})
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
def build(factor=2.0, work=None, no_art=False, no_fonts=False, limit=0, jobs=0, log=print, no_lua=False):
    import pack as upack
    cfg = load(CONFIG)
    games = load(GAMES)
    if factor not in cfg['factors']:
        raise SystemExit(f'uiscale: factor {factor:g} is not built here (config factors {cfg["factors"]})')
    fs = game_fs(games)
    stray = [n for n in fs.packs if n.lower().startswith(('ui_scale_', 'ui_art_'))]
    if stray:
        raise SystemExit(f'uiscale: mod pack(s) {stray} in data\\ are not in mod_packs: add them to discovery/napoleon/games.json')
    work = work or cfg['work']
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
        aent, held, methods = build_art(cfg, fs, refs, factor, work, cfg['upscale_work'], limit, jobs, log)
    lent = [] if no_lua else lua_entries(lua_scripts(fs=fs), factor, work, tag, log)
    ents = sorted(lay_entries + aent + lent, key=lambda e: e[0].lower())
    metas['pack'] = upack.build(cfg['pack_name'].format(tag=tag), ents, work, work, log=log,
                                extra={'factor': factor, 'layouts': len(lay_entries), 'art': len(aent), 'lua': len(lent), 'art_methods': methods,
                                       'held_back': held, 'scale_root': cfg['scale_root']})
    summary = {'factor': factor, 'packs': {k: {'pack': m['pack'], 'sha256': m['sha256'], 'bytes': m['bytes'], 'entries': m['entries']}
                                           for k, m in metas.items()},
               'templates': {'file': tname, 'sha256': tmeta['sha256'], 'bytes': len(tout)}, 'rules': os.path.basename(rules)}
    write_file(os.path.join(work, f'build_{tag}x.json'), (json.dumps(summary, indent=1) + '\n').encode())
    log(json.dumps(summary, indent=1))
    return summary


def status(work=None):
    cfg = load(CONFIG)
    work = work or cfg['work']
    for f in cfg['factors']:
        p = os.path.join(work, f'build_{tag_of(f)}x.json')
        print(open(p, encoding='utf-8').read() if os.path.exists(p) else f'uiscale: no {f:g}x build in {work}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['build', 'status', 'lua-consts', 'lua-patches', 'check'])
    ap.add_argument('--factor', type=float, default=2.0)
    ap.add_argument('--no-lua', action='store_true', help='build: leave the UI scripts vanilla')
    ap.add_argument('--scripts', help='lua-consts, lua-patches, check: read an extract folder (extract/napoleon) instead of the game')
    ap.add_argument('--check', action='store_true', help='lua-consts: compare with the committed files; lua-patches: verify every assert')
    ap.add_argument('--height', type=int, help='check: screen height (2160, 1440)')
    ap.add_argument('--width', type=int, help='check: screen width (default 16:9 of the height)')
    ap.add_argument('--work')
    ap.add_argument('--no-art', action='store_true')
    ap.add_argument('--no-fonts', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='art: at most N new images (a smoke build)')
    ap.add_argument('--jobs', type=int, default=0, help='art worker processes (default: CPUs - 1)')
    a = ap.parse_args(argv)
    if a.action == 'status':
        return status(a.work)
    if a.action == 'lua-consts':
        return lua_consts_cmd(a.scripts, a.check)
    if a.action == 'lua-patches':
        return lua_patches_cmd(a.check, a.factor, a.scripts)
    if a.action == 'check':
        if not a.height:
            ap.error('check needs --height')
        return check_cmd(a.factor, a.height, a.width, a.scripts)
    build(a.factor, a.work, a.no_art, a.no_fonts, a.limit, a.jobs, no_lua=a.no_lua)
    return 0


if __name__ == '__main__':
    sys.exit(main())
