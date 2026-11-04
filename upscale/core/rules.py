"""Size rule, skip rules, status words and the registry mapping of the UI art upscaler (J36). Standard library only.

purpose: decide an asset's target size (2.5x the vanilla pixels, integer-rounded) and whether to skip it, and map the tool's status words onto the assets registry fields
usage: library (upscale/core); python3 -c "import sys; sys.path.insert(0,'upscale/core'); import rules; print(rules.target_size(64, 48))"
when: planning a run (wsc upscale plan) or testing the size rule
not-a-verb: a library used by upscale/core/batch.py, not a registry operation
"""
import hashlib
import json
import re

MASTER_SCALE = 2.5        # D19: 1080p reference x 2.5 (4K x 125 %)
MIN_FACTOR = 2.0          # an asset that would end up under 2x is skipped
TINY_PX = 8               # below this on either axis the model is not run (Lanczos only, stated in the method)
NATIVE_CAP = 2048         # a longest side at or above this is already past a 4K display's need: skipped

PENDING, DONE = 'pending', 'done'


def skipped(reason):
    return 'skipped:' + reason


def failed(reason):
    return 'failed:' + reason[:120]


def target_size(w, h, scale=MASTER_SCALE):
    """(tw, th) = floor(x * scale + 0.5) on each axis (Python's round() is banker's: 2.5 -> 2)."""
    return int(w * scale + 0.5), int(h * scale + 0.5)


def decide(w, h, fmt, role_cfg, scale=MASTER_SCALE):
    """('run', (tw, th)) or ('skip', reason). fmt is the registry format word (tga, dds, jpg, cur, ani ...)."""
    if fmt not in ('tga', 'dds', 'jpg', 'jpeg', 'png'):
        return 'skip', 'not_an_image_file'
    if not w or not h:
        return 'skip', 'no_header'
    cap = role_cfg.get('native_cap', NATIVE_CAP)
    if max(w, h) >= cap:
        return 'skip', 'already_large'
    tw, th = target_size(w, h, scale)
    if tw < MIN_FACTOR * w or th < MIN_FACTOR * h:
        return 'skip', 'under_2x'
    return 'run', (tw, th)


def parse_format(s):
    """registry format 'dds dxt3 128x128 m1' / 'tga bgra8 512x256' -> (kind, sub, w, h, mips)"""
    p = s.split()
    kind = p[0] if p else ''
    sub, w, h, mips = '', 0, 0, 0
    for t in p[1:]:
        m = re.fullmatch(r'(\d+)x(\d+)', t)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
        elif re.fullmatch(r'm\d+', t):
            mips = int(t[1:])
        elif not sub:
            sub = t
    return kind, sub, w, h, mips


def registry_fields(status, method=''):
    """The assets schema (core) allows upscale_status todo | done | not_needed only: pending and failed:* are 'todo',
    skipped:* is 'not_needed'; the reason or the method goes in upscale_method."""
    if status == DONE:
        return {'upscale_status': 'done', 'upscale_method': method or 'done'}
    if status.startswith('skipped:'):
        return {'upscale_status': 'not_needed', 'upscale_method': status}
    if status.startswith('failed:'):
        return {'upscale_status': 'todo', 'upscale_method': status}
    return {'upscale_status': 'todo'}


def input_key(src_sha, cfg_sig):
    """the resume key: same input bytes, same model sha and settings -> the same output"""
    return hashlib.sha256((src_sha + '|' + cfg_sig).encode()).hexdigest()[:24]


def cfg_signature(settings):
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:16]
