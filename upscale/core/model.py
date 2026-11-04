"""Model runner of the UI art upscaler (J36): pinned models, a tiled fp16 GPU path and a deterministic CPU stand-in (numpy, Pillow; torch and spandrel only for real models).

purpose: run a pinned 2x model over an RGB image in overlapping tiles; verify the model file against its pinned sha256; offer a 'lanczos' stand-in with the same interface for host tests and CPU-only machines
usage: library (upscale/core); python3 upscale/core/model.py fetch <models.json> <dir>   (downloads the pinned files and checks sha256)
when: batch.py needs an upscaler; setting up the PC environment (fetch)
not-a-verb: a library used by upscale/core/batch.py, not a registry operation
"""
import hashlib
import json
import os
import sys
import urllib.request

import numpy as np


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fetch(models_json, dest):
    """Download every pinned model into dest (a file whose sha256 already matches is kept); a mismatch deletes the file and raises."""
    pins = json.load(open(models_json, encoding='utf-8'))['models']
    os.makedirs(dest, exist_ok=True)
    for name, m in pins.items():
        p = os.path.join(dest, m['file'])
        if not (os.path.exists(p) and sha256_file(p) == m['sha256']):
            urllib.request.urlretrieve(m['url'], p + '.part')
            os.replace(p + '.part', p)
        if sha256_file(p) != m['sha256']:
            os.remove(p)
            raise RuntimeError('%s: sha256 differs from the pin %s' % (name, m['sha256']))
        print('ok', name, m['sha256'][:12], m.get('licence', ''))


class Lanczos2x:
    """Stand-in 'model': Lanczos x2. Deterministic, CPU, no dependencies beyond numpy and Pillow."""
    name, scale, sha256 = 'lanczos', 2, 'none'
    settings = {'device': 'cpu', 'precision': 'fp32', 'tile': 0, 'overlap': 0}

    def run(self, rgb):
        import resample   # lazy: `model.py fetch` runs in an embeddable Python that has no script directory on sys.path
        h, w = rgb.shape[:2]
        return resample.lanczos(rgb.astype(np.float32), w * 2, h * 2)


class TorchModel:
    """A spandrel-loaded .pth run in tiles. Each tile core gets `overlap` texels of real context on every side (reflect padding at
    the image border) and the context is cropped from the result, so there is no blending. cudnn is pinned deterministic, so the
    same input, model sha and settings give the same bytes on the same GPU and driver."""
    def __init__(self, name, path, sha256, device='cuda', precision='fp16', tile=256, overlap=16):
        import torch
        from spandrel import ModelLoader
        if sha256_file(path) != sha256:
            raise RuntimeError('%s: file sha256 differs from the pin' % path)
        self.torch = torch
        self.name, self.sha256 = name, sha256
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        self.device = torch.device(device if (device != 'cuda' or torch.cuda.is_available()) else 'cpu')
        self.dtype = torch.float16 if (precision == 'fp16' and self.device.type == 'cuda') else torch.float32
        d = ModelLoader().load_from_file(path)
        self.scale = int(d.scale)
        self.net = d.model.to(self.device).eval().to(self.dtype)
        self.tile, self.overlap = tile, overlap
        self.settings = {'device': self.device.type, 'precision': 'fp16' if self.dtype == torch.float16 else 'fp32',
                         'tile': tile, 'overlap': overlap, 'torch': torch.__version__}

    def _run(self, a):
        t = self.torch.from_numpy(np.ascontiguousarray(a.transpose(2, 0, 1)) / 255.0).unsqueeze(0).to(self.device, self.dtype)
        with self.torch.no_grad():
            o = self.net(t)
        return o.squeeze(0).float().clamp(0, 1).cpu().numpy().transpose(1, 2, 0) * 255.0

    def run(self, rgb):
        h, w = rgb.shape[:2]
        s, T, ov = self.scale, self.tile, self.overlap
        out = np.zeros((h * s, w * s, 3), np.float32)
        mode = 'reflect' if min(h, w) > ov else 'edge'
        pad = np.pad(rgb.astype(np.float32), ((ov, ov), (ov, ov), (0, 0)), mode=mode)
        for y in range(0, h, T):
            for x in range(0, w, T):
                th, tw = min(T, h - y), min(T, w - x)
                r = self._run(pad[y:y + th + 2 * ov, x:x + tw + 2 * ov])
                out[y * s:(y + th) * s, x * s:(x + tw) * s] = r[ov * s:(ov + th) * s, ov * s:(ov + tw) * s]
        return out


def load(pins, name, models_dir, device='cuda', precision='fp16', tile=256, overlap=16):
    if name == 'lanczos':
        return Lanczos2x()
    m = pins[name]
    return TorchModel(name, os.path.join(models_dir, m['file']), m['sha256'], device, precision, tile, overlap)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'fetch':
        fetch(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
