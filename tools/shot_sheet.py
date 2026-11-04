#!/usr/bin/env python3
"""Labelled contact sheet of ctl shots (J24; needs Pillow): rows are poses, columns are settings, one JPEG for Liam to judge a look.

purpose: build one labelled JPEG contact sheet from ctl shot files, rows = poses, columns = settings (each setting a folder of shots), optionally a full-resolution crop of the near-camera region; a missing shot is a grey cell with "missing" in its label
usage: shot_sheet.py --shots DIR --out OUT.jpg --title T --poses p1,p2,... [--crop] TAG[:LABEL] [TAG[:LABEL] ...]   (shots are DIR/<TAG>/*_<pose>.jpg|png)
when: a before/after or ladder sitting of a graphics job (J24 shadows; J25, J26, J27 next) needs side-by-side shots per pose
not-a-verb: a run helper over shot files on disk, no registry or game state
"""
import argparse
import sys
from pathlib import Path

W, H, LABEL, TITLE = 640, 360, 28, 40


def find_shot(folder, pose):
    """The ctl shot of `pose` in `folder`: an exact `_<pose>` suffix first, then any name containing it; camera sidecars are skipped."""
    d = Path(folder)
    for pat in (f'*_{pose}.jpg', f'*_{pose}.png', f'*{pose}*.jpg', f'*{pose}*.png'):
        hits = sorted(p for p in d.glob(pat) if 'cam' not in p.name)
        if hits:
            return hits[0]
    return None


def near_crop(size):
    """The centre-bottom third of a frame at full resolution, in the sheet cell's aspect: where shadow detail near the camera is."""
    w, h = size
    return (w // 3, h // 2, w // 3 + w // 3, h // 2 + (w // 3) * H // W)


def build(shots, title, poses, cols, crop=False):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=18)
    sheet = Image.new('RGB', (W * len(cols), TITLE + (H + LABEL) * len(poses)), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    dr.text((8, 10), title, fill=(255, 255, 255), font=font)
    missing = []
    for r, pose in enumerate(poses):
        for c, col in enumerate(cols):
            tag, _, label = col.partition(':')
            x, y = c * W, TITLE + r * (H + LABEL)
            p = find_shot(Path(shots) / tag, pose)
            if p:
                im = Image.open(p).convert('RGB')
                if crop:
                    im = im.crop(near_crop(im.size))
                sheet.paste(im.resize((W, H), Image.LANCZOS), (x, y + LABEL))
            else:
                missing.append(f'{tag}/{pose}')
                dr.rectangle((x, y + LABEL, x + W - 1, y + LABEL + H - 1), fill=(90, 90, 90))
            dr.text((x + 6, y + 4), f'{pose} | {label or tag}' + ('' if p else ' | missing'), fill=(255, 230, 120), font=font)
    return sheet, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--shots', required=True, help='folder holding one subfolder of shots per setting tag')
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='')
    ap.add_argument('--poses', required=True, help='comma-separated pose names, one sheet row each')
    ap.add_argument('--crop', action='store_true', help='the near-camera third at full resolution instead of the whole frame scaled')
    ap.add_argument('cols', nargs='+', metavar='TAG[:LABEL]')
    a = ap.parse_args(argv)
    sheet, missing = build(a.shots, a.title, a.poses.split(','), a.cols, a.crop)
    sheet.save(a.out, quality=82, optimize=True)
    print(a.out, sheet.size, Path(a.out).stat().st_size // 1024, 'KB', f'missing: {", ".join(missing)}' if missing else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
