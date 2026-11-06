"""J96 probe 1 reading: J50's all-cyan battle shot (every TGA of ui\\battle ui\\skins tinted) marks what those files draw; this sorts each of those pixels in a J96 shot
(aligned skins as DXT5 orange, unaligned skins as TGA cyan) against a vanilla shot of the same scene: cyan = a control TGA, orange = the DDS drawn, vanilla = the DDS ignored, other = blank.
usage: classify.py <all-cyan jpg> <j96 jpg> <vanilla jpg> <out png>"""
import sys
import numpy as np
from PIL import Image

allc, j96, van, out = sys.argv[1:5]
size = (1280, 720)
A, B, V = (np.asarray(Image.open(p).convert('RGB').resize(size)).astype(np.int16) for p in (allc, j96, van))


def cyan(x):
    return (x[..., 1] > 170) & (x[..., 2] > 170) & (x[..., 0] < 110)


def orange(x):
    return (x[..., 0] > 200) & (x[..., 1] > 80) & (x[..., 1] < 170) & (x[..., 2] < 80)


hud = cyan(A) & ~cyan(V)
near = np.abs(B - V).sum(-1) < 60
c, o = hud & cyan(B), hud & orange(B)
v = hud & near & ~c & ~o
other = hud & ~c & ~o & ~v
n = int(hud.sum())
print('pixels J50 drew cyan:', n)
for name, m in (('control cyan', c), ('orange (DDS drawn)', o), ('vanilla look (DDS ignored or not this file)', v), ('other (blank or changed)', other)):
    print('%-46s %7d %5.1f %%' % (name, int(m.sum()), 100.0 * m.sum() / max(1, n)))
print('orange anywhere in the shot:', int(orange(B).sum()))
vis = np.zeros(size[::-1] + (3,), np.uint8)
vis[c] = (0, 255, 255)
vis[o] = (255, 128, 0)
vis[v] = (0, 200, 0)
vis[other] = (255, 0, 0)
Image.fromarray(vis).save(out)
