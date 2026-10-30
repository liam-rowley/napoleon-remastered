"""Print the upscale environment: GPU, torch, packages, model sha256 against the pins (J36).

purpose: check the GPU environment of the UI art upscaler and print GPU, torch, spandrel and every pinned model's sha256
usage: <work>\\art_build\\py\\python.exe upscale/pc/env_check.py --models <dir> --pins upscale/napoleon/models.json [--json out.json]   (or `wsc upscale env`)
when: after setup_env.cmd, before a run, and when a run behaves differently (driver update)
not-a-verb: runs inside the embeddable Python of art_build, which has no wsc; `wsc upscale env` starts it
"""
import argparse, hashlib, json, os, platform, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', required=True)
    ap.add_argument('--pins', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    r = {'python': platform.python_version(), 'ok': True, 'problems': []}
    for mod in ('numpy', 'PIL', 'spandrel', 'torch'):
        try:
            m = __import__(mod)
            r[mod] = getattr(m, '__version__', '?')
        except Exception as e:
            r[mod] = None
            r['problems'].append('%s: %s' % (mod, e))
    try:
        import torch
        r['cuda'] = bool(torch.cuda.is_available())
        if r['cuda']:
            p = torch.cuda.get_device_properties(0)
            r['gpu'] = '%s, %d MiB, sm_%d%d' % (p.name, p.total_memory >> 20, p.major, p.minor)
        else:
            r['problems'].append('torch.cuda.is_available() is False: the CPU path still works, slowly')
    except Exception:
        pass
    pins = json.load(open(a.pins, encoding='utf-8'))['models']
    r['models'] = {}
    for n, m in pins.items():
        p = os.path.join(a.models, m['file'])
        sha = None
        if os.path.exists(p):
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''):
                    h.update(b)
            sha = h.hexdigest()
        ok = sha == m['sha256']
        r['models'][n] = {'sha256': sha, 'pinned': m['sha256'], 'match': ok, 'licence': m['licence']}
        if not ok:
            r['problems'].append('model %s: sha256 %s, pinned %s' % (n, sha, m['sha256']))
    r['ok'] = not [x for x in r['problems'] if not x.startswith('torch.cuda')]
    for k in ('python', 'numpy', 'PIL', 'spandrel', 'torch', 'cuda', 'gpu'):
        print('%-9s %s' % (k, r.get(k)))
    for n, m in r['models'].items():
        print('model     %-20s %s %s' % (n, (m['sha256'] or 'MISSING')[:16], 'ok' if m['match'] else 'MISMATCH'))
    for x in r['problems']:
        print('problem  ', x)
    print('ENV', 'OK' if r['ok'] else 'FAILED')
    if a.json:
        json.dump(r, open(a.json, 'w'), indent=1)
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
