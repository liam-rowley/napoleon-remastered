"""Resumable batch of the UI art upscaler (J36): plan, run, verify (needs numpy, Pillow; torch for real models).

purpose: turn a list of UI images into 2.5x master images (model x2, Lanczos to the exact size, alpha by Lanczos only, full mip chain), with a per-asset manifest, resume by input hash, and a per-asset verify
usage: library (upscale/core), driven by `python3 core/wsc.py upscale plan|run|verify|sheets|pack`; run() takes items [{id, path, role, fmt, w, h}] and a read(item) -> bytes function
when: an upscale run on the PC; host tests with the 'lanczos' stand-in model
not-a-verb: a library used by tools/verbs/upscale.py, not a registry operation

Per asset: decode -> alpha class (none | binary | soft) -> dilate RGB under A = 0 -> model -> Lanczos to the target -> alpha by Lanczos (cut at 128 if binary)
-> DDS: full mip chain (RGB box in linear light, alpha plain box), vanilla header and format; TGA/JPG: same container, no mips (the UI host builds them).
Outputs sit under <work>/out/<vanilla path>; <work>/manifest.json holds every asset's status, hashes, method and timing.
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

import dds
import imageio
import model as modelmod
import resample
import rules

MANIFEST_VERSION = 1


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def out_path(work, item_path):
    return os.path.join(work, 'out', *item_path.replace('/', '\\').split('\\'))


def settings_for(cfg, mdl):
    """everything that decides the output bytes besides the input; its signature is part of the resume key"""
    return {'scale': cfg.get('scale', rules.MASTER_SCALE), 'model': mdl.name, 'model_sha256': mdl.sha256, 'run': mdl.settings,
            'encoder': cfg.get('encoder', 'python'), 'jpg_quality': cfg.get('jpg_quality', 95), 'tiny_px': rules.TINY_PX, 'version': MANIFEST_VERSION}


def method_text(s, ran_model):
    if not ran_model:
        return 'lanczos->%sx (no model: side under %dpx)' % (s['scale'], rules.TINY_PX)
    r = s['run']
    return '%s(x2)+lanczos->%sx %s tile%s/ov%s' % (s['model'], s['scale'], r.get('precision', ''), r.get('tile', ''), r.get('overlap', ''))


def process(src, target, mdl, cfg, encoder_path=None):
    """Source -> (output bytes, info). The whole image pipeline, no file access."""
    tw, th = target
    w, h = src.size
    rgba = src.rgba
    kind = src.alpha_kind()
    rgb = resample.dilate_rgb(rgba) if kind != 'none' else rgba[..., :3].astype(np.float32)
    ran = min(w, h) >= rules.TINY_PX
    up = mdl.run(rgb) if ran else rgb
    rgb_t = resample.lanczos(up, tw, th)
    alpha = resample.resample_alpha(rgba[..., 3], tw, th, kind)
    out = resample.finish(rgb_t, alpha)
    info = {'alpha': kind, 'ran_model': ran}
    if src.kind == 'dds':
        n = dds.full_mips(tw, th)
        levels = resample.mip_chain(out, n)
        data = dds.encode_chain(levels, src.fmt, cfg.get('encoder', 'python'), texconv=encoder_path)
        tmpl = src.header
        try:
            dds.make_header(src.fmt, tw, th, n, tmpl)
        except ValueError:
            tmpl = None
        blob = dds.make_header(src.fmt, tw, th, n, tmpl) + b''.join(data)
        info.update(fmt=src.fmt, mips=n)
    elif src.kind == 'tga':
        blob = imageio.encode_tga(out, with_alpha=(src.fmt != 'bgr8'))
        info.update(fmt=src.fmt, mips=1)
    elif src.kind == 'png':
        blob = imageio.encode_png(out)
        info.update(fmt='rgba8', mips=1)
    else:
        blob = imageio.encode_jpg(out, cfg.get('jpg_quality', 95))
        info.update(fmt='ycc8', mips=1)
    return blob, info


def run(items, read, work, cfg, pins, models_dir, role_cfgs, limit=0, device='cuda', log=print, encoder_path=None, model_override=None):
    """Process items (resume by input hash). Returns the manifest dict. model_override forces one model for all roles (host tests, sample runs)."""
    os.makedirs(os.path.join(work, 'out'), exist_ok=True)
    man = load_manifest(work)
    run_cfg = cfg.get('run', {})
    models = {}
    done = skipped = failed = fresh = 0
    t0 = time.time()
    for i, it in enumerate(sorted(items, key=lambda x: x['id'])):
        if limit and fresh >= limit:
            break
        rc = role_cfgs.get(it['role'], {})
        verdict, val = rules.decide(it['w'], it['h'], it['fmt'].split()[0], rc, cfg.get('scale', rules.MASTER_SCALE))
        if verdict == 'skip':
            man['entries'][it['id']] = {'id': it['id'], 'path': it['path'], 'role': it['role'], 'status': rules.skipped(val)}
            skipped += 1
            continue
        name = model_override or rc.get('model', cfg.get('model', 'lanczos'))
        if name not in models:
            models[name] = modelmod.load(pins, name, models_dir, device, run_cfg.get('precision', 'fp16'), run_cfg.get('tile', 256), run_cfg.get('overlap', 16))
        mdl = models[name]
        s = settings_for(cfg, mdl)
        t1 = time.time()
        try:
            data = read(it)
            key = rules.input_key(_sha(data), rules.cfg_signature(s))
            old = man['entries'].get(it['id'])
            op = out_path(work, it['path'])
            if old and old.get('status') == rules.DONE and old.get('key') == key and os.path.exists(op) and _sha(open(op, 'rb').read()) == old['out']['sha256']:
                done += 1
                continue
            src = imageio.load(data, os.path.splitext(it['path'])[1])
            blob, info = process(src, val, mdl, cfg, encoder_path)
            os.makedirs(os.path.dirname(op), exist_ok=True)
            with open(op + '.tmp', 'wb') as f:
                f.write(blob)
            os.replace(op + '.tmp', op)
            a = src.rgba[..., 3]
            man['entries'][it['id']] = {
                'id': it['id'], 'path': it['path'], 'role': it['role'], 'status': rules.DONE, 'key': key,
                'method': method_text(s, info['ran_model']),
                'src': {'sha256': _sha(data), 'w': src.size[0], 'h': src.size[1], 'kind': src.kind, 'fmt': src.fmt, 'mips': src.mips,
                        'alpha': info['alpha'], 'cov': round(resample.alpha_mean(a), 6),
                        'std': round(float(src.rgba[..., :3].astype(np.float32).std()), 3)},
                'out': {'file': os.path.relpath(op, work).replace('\\', '/'), 'sha256': _sha(blob), 'bytes': len(blob),
                        'w': val[0], 'h': val[1], 'mips': info['mips'], 'fmt': info['fmt']},
                'seconds': round(time.time() - t1, 3)}
            done += 1
            fresh += 1
        except Exception as e:  # recorded, never silent: verify and the registry both show it
            man['entries'][it['id']] = {'id': it['id'], 'path': it['path'], 'role': it['role'], 'status': rules.failed('%s: %s' % (type(e).__name__, e))}
            failed += 1
        if (i + 1) % 200 == 0:
            save_manifest(work, man, cfg, models)
            log('%d/%d  fresh %d  skipped %d  failed %d  %.0fs' % (i + 1, len(items), fresh, skipped, failed, time.time() - t0))
    man['models'] = {n: m.sha256 for n, m in models.items()} or man.get('models', {})
    save_manifest(work, man, cfg, models)
    log('run: done %d (fresh %d), skipped %d, failed %d, %.1fs' % (done, fresh, skipped, failed, time.time() - t0))
    return man


def load_manifest(work):
    p = os.path.join(work, 'manifest.json')
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    return {'version': MANIFEST_VERSION, 'entries': {}, 'models': {}}


def save_manifest(work, man, cfg, models):
    man['version'] = MANIFEST_VERSION
    man['scale'] = cfg.get('scale', rules.MASTER_SCALE)
    if models:
        man['settings'] = {n: m.settings for n, m in models.items()}
    p = os.path.join(work, 'manifest.json')
    with open(p + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(man, f, indent=1, sort_keys=True, allow_nan=False)
        f.write('\n')
    os.replace(p + '.tmp', p)


def plan(items, role_cfgs, cfg):
    """Decisions without running anything: {role: {run: n, skip:reason: n}} and the per-item list."""
    out, per = [], {}
    for it in sorted(items, key=lambda x: x['id']):
        v, val = rules.decide(it['w'], it['h'], it['fmt'].split()[0], role_cfgs.get(it['role'], {}), cfg.get('scale', rules.MASTER_SCALE))
        key = 'run' if v == 'run' else 'skip:' + val
        per.setdefault(it['role'], {}).setdefault(key, 0)
        per[it['role']][key] += 1
        out.append({'id': it['id'], 'decision': key, 'target': list(val) if v == 'run' else None})
    return per, out


def verify_entry(e, work, tol=0.03):
    """Problems of one finished asset (empty = fine): exact size, mips, format, alpha coverage at each mip, NaN or flat, sha."""
    if e.get('status') != rules.DONE:
        return []
    probs = []
    p = os.path.join(work, e['out']['file'])
    if not os.path.exists(p):
        return ['output file missing']
    data = open(p, 'rb').read()
    if _sha(data) != e['out']['sha256']:
        probs.append('sha256 differs from the manifest')
    tw, th = e['out']['w'], e['out']['h']
    sw, sh = e['src']['w'], e['src']['h']
    if (tw, th) != rules.target_size(sw, sh):
        probs.append('manifest target %dx%d is not the size rule %s' % (tw, th, rules.target_size(sw, sh)))
    levels = []
    try:
        if e['src']['kind'] == 'dds':
            d = dds.read_dds(data)
            if (d.width, d.height) != (tw, th):
                probs.append('size %dx%d, expected %dx%d' % (d.width, d.height, tw, th))
            if d.mips != dds.full_mips(tw, th):
                probs.append('mip count %d, expected %d' % (d.mips, dds.full_mips(tw, th)))
            sfmt = e['src']['fmt']
            if d.fmt != sfmt and not (d.fmt == 'X8R8G8B8' and sfmt == 'A8R8G8B8'):
                probs.append('format %s, vanilla %s' % (d.fmt, sfmt))
            levels = [d.decode(k) for k in range(d.mips)]
        else:
            src = imageio.load(data, os.path.splitext(e['path'])[1])
            if src.size != (tw, th):
                probs.append('size %dx%d, expected %dx%d' % (src.size[0], src.size[1], tw, th))
            levels = resample.mip_chain(src.rgba, dds.full_mips(tw, th)) if e['src']['alpha'] != 'none' else [src.rgba]
    except Exception as ex:
        return probs + ['unreadable: %s' % ex]
    l0 = levels[0]
    if float(l0[..., :3].astype(np.float32).std()) < 1.0 and e['src']['std'] >= 3.0:
        probs.append('flat output (source std %.1f)' % e['src']['std'])
    if e['src']['alpha'] != 'none':
        want = e['src']['cov']
        for k, lv in enumerate(levels):
            n = lv.shape[0] * lv.shape[1]
            t = tol + (2.0 / np.sqrt(n) if k else 0)
            got = resample.alpha_mean(lv[..., 3])
            if abs(got - want) > t:
                probs.append('mean alpha at mip %d is %.3f, vanilla %.3f (tol %.3f)' % (k, got, want, t))
                break
        if e['src']['alpha'] == 'binary' and not np.isin(np.unique(l0[..., 3]), (0, 255)).all() and e['src']['kind'] != 'dds':
            probs.append('binary alpha is no longer binary')
    return probs


def verify(work, roles=None, log=print):
    man = load_manifest(work)
    bad, n = {}, 0
    for i, e in sorted(man['entries'].items()):
        if roles and e['role'] not in roles:
            continue
        if e['status'].startswith('failed:'):
            bad[i] = [e['status']]
        elif e['status'] == rules.DONE:
            n += 1
            pr = verify_entry(e, work)
            if pr:
                bad[i] = pr
    res = {'checked': n, 'failed': bad}
    with open(os.path.join(work, 'verify.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1, sort_keys=True)
    log('verify: %d checked, %d with problems' % (n, len(bad)))
    for i, pr in list(bad.items())[:30]:
        log('  %s: %s' % (i, '; '.join(pr)))
    return res
