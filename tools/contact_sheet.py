"""tools/contact_sheet.py   the eight hourly checkpoints in order, one row of canyon views over one row of web views, with the time each was made."""
import os, sys, time
from PIL import Image, ImageDraw, ImageFont
F = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 405, 506; pad = 18; top = 70
try: font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 17); big = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 26)
except Exception: font = big = ImageFont.load_default()
sheet = Image.new('RGB', (pad + 4 * (W + pad), top + 2 * (H + 44 + pad)), (13, 13, 13)); d = ImageDraw.Draw(sheet)
d.text((pad, 20), 'THE UNSUPERVISED SHIFT  ·  West 317th Street  ·  eight hourly checkpoints, 1 a.m. to 8 a.m.', fill=(240, 244, 248), font=big)
for n in range(1, 9):
    folder = os.path.join(F, 'hourly', 'hour_%02d' % n); p = os.path.join(folder, 'canyon_%dam.png' % n)
    x = pad + ((n - 1) % 4) * (W + pad); y = top + ((n - 1) // 4) * (H + 44 + pad)
    if os.path.exists(p):
        im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS); sheet.paste(im, (x, y))
        made = time.strftime('%H:%M', time.localtime(os.path.getmtime(p)))
        d.text((x, y + H + 6), '%d a.m. on the block' % n, fill=(215, 255, 31), font=font); d.text((x, y + H + 24), 'rendered %s' % made, fill=(160, 170, 180), font=font)
    else:
        d.rectangle((x, y, x + W, y + H), outline=(80, 80, 80)); d.text((x + 12, y + H // 2), 'hour %d: missing' % n, fill=(255, 46, 99), font=font)
out = os.path.join(F, 'contact_sheet.jpg'); sheet.save(out, quality=90); print(out, sheet.size)
