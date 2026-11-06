"""Resumable batch of the UI art upscaler (J36): plan, run, verify (needs numpy, Pillow; torch for real models).

purpose: turn a list of UI images into 2.5x master images (model x2, Lanczos to the exact size, alpha by Lanczos only, full mip chain), with a per-asset manifest, resume by input hash, a per-asset verify, an output size estimate for the free-disk guard, and a run log
usage: library (upscale/core), driven by `python3 core/wsc.py upscale plan|run|verify|sheets|pack`; run() takes items [{id, path, role, fmt, w, h}] and a read(item) -> bytes function
when: an upscale run on the PC; host tests with the 'lanczos' stand-in model
not-a-verb: a library used by tools/verbs/upscale.py, not a registry operation

Per asset: decode -> alpha class (none | binary | soft) -> dilate RGB under A = 0 -> model -> Lanczos to the target -> alpha by Lanczos (cut at 128 if binary)
-> DDS: full mip chain (RGB box in linear light, alpha plain box), vanilla header and format; TGA/JPG: same container, no mips (the UI host builds them).
Outputs sit under <work>/out/<vanilla path>; <work>/manifest.json holds every asset's status, hashes, method and timing; <work>/run.log gets one line per run (J96).
"""
import hashlib
import json
import os
import shutil
import sys
import time

import numpy as np

import dds
import imageio
import model as modelmod
import resample
import rules

MANIFEST_VERSION = 2
MIN_FREE_PCT = 20         # J51 review: run refuses when the work drive would keep less than this
PREMULT_TOL = 12          # of 255: DXT2 colour may sit this far above alpha: 4-bit alpha rounds by 8.5, 5:6:5 colour by 4 (J96: an honest alpha ramp fails at 8)
JPG_BYTES_PER_PX = 0.259  # J51 manifest: 665 JPG outputs, 63360947 bytes over 244675200 target pixels. TGA and DDS sizes are exact.
PNG_BYTES_PER_PX = 4      # no PNG in a J51 run: the raw size, an upper bound
DDS_RAW = {'bgra8': 'A8R8G8B8', 'bgr8': 'R8G8B8'}   # registry word -> dds.py format; anything unknown counts as 4 bytes a texel


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


def _visible_std(rgba):
    """std of RGB over the visible texels (A > 0), 0 when none: the flat-output check compares like with like"""
    v = rgba[rgba[..., 3] > 0][:, :3].astype(np.float32)
    return round(float(v.std()), 3) if v.size else 0.0


def process(src, target, mdl, cfg, encoder_path=None):
    """Source -> (output bytes, info). The whole image pipeline, no file access."""
    tw, th = target
    w, h = src.size
    rgba = src.rgba
    kind = src.alpha_kind()
    # a fully transparent image has no colour to spread: its RGB goes through as it is (nothing is visible either way)
    rgb = resample.dilate_rgb(rgba) if kind != 'none' and rgba[..., 3].any() else rgba[..., :3].astype(np.float32)
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


def run(items, read, work, cfg, pins, models_dir, role_cfgs, limit=0, device='cuda', log=print, encoder_path=None, model_override=None, force_disk=False):
    """Process items (resume by input hash and target size). Returns the manifest dict. model_override forces one model for all roles (host tests, sample runs);
    force_disk only goes into the run log: the guard itself is disk_refusal, before the run."""
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
        verdict, val = rules.decide(it['w'], it['h'], it['fmt'], rc, cfg.get('scale', rules.MASTER_SCALE))
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
            same_size = old and old.get('status') == rules.DONE and (old['out']['w'], old['out']['h']) == tuple(val)   # a size rule change is not in the key
            if same_size and old.get('key') == key and os.path.exists(op) and _sha(open(op, 'rb').read()) == old['out']['sha256']:
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
                        'std': _visible_std(src.rgba)},
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
    secs = time.time() - t0
    log('run: done %d (fresh %d), skipped %d, failed %d, %.1fs' % (done, fresh, skipped, failed, secs))
    append_run_log(work, items, done, fresh, skipped, failed, secs, force_disk)
    return man


def append_run_log(work, items, done, fresh, skipped, failed, seconds, force_disk):
    """one line per run in <work>/run.log, so a resume pass leaves its numbers too (J51 review)"""
    roles = ','.join(dict.fromkeys(it['role'] for it in items))
    with open(os.path.join(work, 'run.log'), 'a', encoding='utf-8', newline='\n') as f:
        f.write('%s roles=%s done=%d fresh=%d skipped=%d failed=%d seconds=%.1f force_disk=%d\n' % (
            time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), roles, done, fresh, skipped, failed, seconds, 1 if force_disk else 0))


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


def estimate_bytes(fmt, tw, th):
    """output bytes of one asset from its registry format and target: the exact DDS chain (the 4/3 mip factor, summed level by level) and TGA size, a measured ratio for JPG"""
    words = fmt.split()
    kind, sub = words[0], (words[1] if len(words) > 1 else '')
    if kind == 'dds':
        f = sub.upper() if rules.is_dxt(sub) else DDS_RAW.get(sub, 'A8R8G8B8')
        return 128 + dds.chain_size(f, tw, th, dds.full_mips(tw, th))
    if kind == 'tga':
        return 18 + tw * th * (3 if sub.startswith('bgr8') else 4)
    return int(tw * th * (PNG_BYTES_PER_PX if kind == 'png' else JPG_BYTES_PER_PX))


def plan(items, role_cfgs, cfg, work=None):
    """Decisions without running anything: {role: {run: n, skip:reason: n, bytes: n}} and the per-item list. bytes = estimated output size of the role;
    with work, a row's new_bytes leaves out what its output file there already holds (a resume or a rerun replaces that file)."""
    out, per = [], {}
    for it in sorted(items, key=lambda x: x['id']):
        v, val = rules.decide(it['w'], it['h'], it['fmt'], role_cfgs.get(it['role'], {}), cfg.get('scale', rules.MASTER_SCALE))
        key = 'run' if v == 'run' else 'skip:' + val
        role = per.setdefault(it['role'], {'bytes': 0})
        role[key] = role.get(key, 0) + 1
        est = estimate_bytes(it['fmt'], *val) if v == 'run' else 0
        role['bytes'] += est
        have = 0
        if est and work and os.path.exists(out_path(work, it['path'])):
            have = os.path.getsize(out_path(work, it['path']))
        out.append({'id': it['id'], 'decision': key, 'target': list(val) if v == 'run' else None, 'bytes': est, 'new_bytes': max(0, est - have)})
    return per, out


def disk_usage(path):
    """(total, used, free) of the drive holding path; the tests stub this"""
    return shutil.disk_usage(path)


def disk_after(rows, work):
    """the plan's rows against the work drive: bytes (all outputs), new_bytes (what the run adds), free, total, free_pct_after"""
    total, _, free = disk_usage(work)
    new = sum(r['new_bytes'] for r in rows)
    return {'bytes': sum(r['bytes'] for r in rows), 'new_bytes': new, 'free': free, 'total': total, 'free_pct_after': round(100.0 * (free - new) / total, 1)}


def disk_refusal(disk):
    """the one-line refusal when the run would leave the work drive under MIN_FREE_PCT free, else ''"""
    if disk['free_pct_after'] >= MIN_FREE_PCT:
        return ''
    return 'run: refused: the work drive would keep %.1f %% free, the floor is %d %% (free %.1f GB of %.1f GB, the run adds %.1f GB); --force-disk overrides' % (
        disk['free_pct_after'], MIN_FREE_PCT, disk['free'] / 1e9, disk['total'] / 1e9, disk['new_bytes'] / 1e9)


def verify_entry(e, work, tol=0.02):
    """Problems of one finished asset (empty = fine): exact size, mips, format, DXT2 premultiplied, alpha coverage at each mip, NaN or flat, sha."""
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
    want_size = rules.dxt_target_size(sw, sh, e['src']['fmt'])
    if (tw, th) != want_size:
        probs.append('manifest target %dx%d is not the size rule %s' % (tw, th, want_size))
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
            if d.fmt == 'DXT2':
                over = sum(dds.premultiplied_excess(d.levels[k], *d.dims(k), tol=PREMULT_TOL) for k in range(d.mips))
                if over:
                    probs.append('DXT2 not premultiplied: %d texels with colour above alpha + %d' % (over, PREMULT_TOL))
        else:
            src = imageio.load(data, os.path.splitext(e['path'])[1])
            if src.size != (tw, th):
                probs.append('size %dx%d, expected %dx%d' % (src.size[0], src.size[1], tw, th))
            levels = resample.mip_chain(src.rgba, dds.full_mips(tw, th)) if e['src']['alpha'] != 'none' else [src.rgba]
    except Exception as ex:
        return probs + ['unreadable: %s' % ex]
    l0 = levels[0]
    if _visible_std(l0) < 1.0 and e['src']['std'] >= 3.0:
        probs.append('flat output (source std %.1f)' % e['src']['std'])
    if e['src']['alpha'] != 'none':
        want = e['src']['cov']
        for k, lv in enumerate(levels):
            n = lv.shape[0] * lv.shape[1]
            t = tol + 1.5 / min(lv.shape[:2]) + (2.0 / np.sqrt(n) if k else 0)
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
