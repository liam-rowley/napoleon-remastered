"""J50 crop sheet: vanilla vs probe, same boxes, 2x nearest; prints mean abs diff per box. usage: crops.py <rawdir> <out.jpg>"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
raw, out = sys.argv[1], sys.argv[2]
boxes = [('frontend logo', 's2r_frontend.jpg', 's2r3_frontend.jpg', (460, 70, 820, 170)),
         ('frontend steam', 's2r_frontend.jpg', 's2r3_frontend.jpg', (950, 650, 1070, 676)),
         ('frontend menu btn', 's2r_frontend.jpg', 's2r3_frontend.jpg', (520, 200, 760, 240)),
         ('campaign end turn', 's2r_campaign.jpg', 's2r3_campaign.jpg', (995, 655, 1065, 715))]
rows = []
for name, a, b, box in boxes:
    A = Image.open(os.path.join(raw, a)).convert('RGB').crop(box)
    B = Image.open(os.path.join(raw, b)).convert('RGB').crop(box)
    d = np.abs(np.asarray(A, np.int16) - np.asarray(B, np.int16)).mean()
    print('%-20s box %s mean abs diff %.2f' % (name, box, d))
    w, h = A.size
    k = 3 if w < 200 else 2
    A, B = A.resize((w * k, h * k), Image.NEAREST), B.resize((w * k, h * k), Image.NEAREST)
    row = Image.new('RGB', (A.width * 2 + 30, A.height + 22), 'white')
    row.paste(A, (0, 22)); row.paste(B, (A.width + 30, 22))
    ImageDraw.Draw(row).text((4, 4), '%s: vanilla (left) | J36 2.5x output (right), diff %.1f' % (name, d), fill='black')
    rows.append(row)
W = max(r.width for r in rows)
sheet = Image.new('RGB', (W, sum(r.height for r in rows)), 'white')
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height
sheet.save(out, quality=88)
print(out, sheet.size)
