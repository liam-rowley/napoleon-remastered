"""J96 probe 5 reading: zoomed crops of the probe shots (left) beside J67's 2x shots of the same scene (right), in 1280x720 coordinates. usage: font_crops.py <shots dir> <out jpg>"""
import sys
from PIL import Image, ImageDraw

S, out = sys.argv[1:3]
J = 'uiscale/runs/2026-11-05_j67pc/raw/'
CROPS = [('frontend', J + 'x2_route/frontend.jpg', (520, 200, 760, 360), 'menu buttons'),
         ('frontend', J + 'x2_route/frontend.jpg', (860, 540, 1070, 680), 'new content box, version'),
         ('land4k', J + 'x2_route/land.jpg', (30, 25, 280, 120), 'advisor'),
         ('land4k', J + 'x2_route/land.jpg', (550, 80, 730, 110), 'Start Battle'),
         ('land4k', J + 'x2_route/land.jpg', (210, 650, 600, 720), 'unit card counts'),
         ('camp4k', J + 'x2_4k/camp_hud.jpg', (30, 25, 280, 120), 'campaign advisor'),
         ('camp4k', J + 'x2_4k/camp_hud.jpg', (980, 590, 1070, 700), 'date, treasury')]
Z = 2.2
rows = []
for n, base, box, label in CROPS:
    a = Image.open(S + '/' + n + '.jpg').convert('RGB').resize((1280, 720)).crop(box)
    b = Image.open(base).convert('RGB').resize((1280, 720)).crop(box)
    w, h = int(a.width * Z), int(a.height * Z)
    rows.append((a.resize((w, h), Image.LANCZOS), b.resize((w, h), Image.LANCZOS), label))
H = sum(r[0].height + 18 for r in rows)
W = 2 * max(r[0].width for r in rows) + 12
sh = Image.new('RGB', (W, H), (20, 20, 20))
d = ImageDraw.Draw(sh)
y = 0
for a, b, label in rows:
    d.text((4, y + 3), label + ' (left probe, right J67)', fill=(255, 255, 0))
    y += 18
    sh.paste(a, (0, y))
    sh.paste(b, (W // 2 + 6, y))
    y += a.height
sh.save(out, quality=90)
print(sh.size)
