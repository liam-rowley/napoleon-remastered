#!/usr/bin/env python3
"""J24 run helper: one labelled JPEG contact sheet, rows = poses, columns = settings (each a raw/<tag>/ folder of ctl shots).

usage: python3 harness/runs/20261103_j24pc/sheet.py <out.jpg> <title> <pose,pose,...> <tag[:label]> [<tag[:label]> ...] [--crop]
  --crop: the centre-bottom third of each shot at full resolution instead of the whole frame scaled (shadow detail near the camera).
Shots are found as raw/<tag>/*_<pose>*.jpg|png (the ctl shot file); a missing one is drawn as a grey cell named "missing".
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if a != '--crop']
crop = '--crop' in sys.argv
out, title, poses, cols = args[0], args[1], args[2].split(','), args[3:]
W, H = 640, 360
font = ImageFont.load_default(size=18) if hasattr(ImageFont, 'load_default') else None


def find(tag, pose):
    d = HERE / 'raw' / tag
    for pat in (f'*_{pose}.jpg', f'*_{pose}.png', f'*{pose}*.jpg', f'*{pose}*.png'):
        hits = sorted(p for p in d.glob(pat) if 'cam' not in p.name)
        if hits:
            return hits[0]
    return None


sheet = Image.new('RGB', (W * len(cols), 40 + (H + 28) * len(poses)), (24, 24, 24))
dr = ImageDraw.Draw(sheet)
dr.text((8, 10), title, fill=(255, 255, 255), font=font)
for r, pose in enumerate(poses):
    for c, col in enumerate(cols):
        tag, _, label = col.partition(':')
        x, y = c * W, 40 + r * (H + 28)
        p = find(tag, pose)
        if p:
            im = Image.open(p).convert('RGB')
            if crop:
                w, h = im.size
                im = im.crop((w // 3, h // 2, w // 3 + w // 3, h // 2 + (w // 3) * H // W))
            im = im.resize((W, H), Image.LANCZOS)
            sheet.paste(im, (x, y + 28))
        else:
            dr.rectangle((x, y + 28, x + W - 1, y + 28 + H - 1), fill=(90, 90, 90))
        dr.text((x + 6, y + 4), f'{pose} | {label or tag}' + ('' if p else ' | missing'), fill=(255, 230, 120), font=font)
sheet.save(out, quality=82, optimize=True)
print(out, sheet.size, Path(out).stat().st_size // 1024, 'KB')
