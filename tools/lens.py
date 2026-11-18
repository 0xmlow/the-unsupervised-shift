"""
tools/lens.py IN.png OUT.png [seed]   what a real camera adds to a clean render (21:05).
Highlight bloom (lamps, neon, lit windows spread a little into the dark), a slight colour fringe toward the edges,
a soft vignette, and fine luminance grain. The Blender render stays the source; this only makes a copy.
"""
import sys, numpy as np
from PIL import Image, ImageFilter
src, dst = sys.argv[1], sys.argv[2]; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 317
im = Image.open(src).convert('RGB'); a = np.asarray(im, dtype=np.float32) / 255.0; h, w, _ = a.shape
lin = a ** 2.2
# bloom: only what is near white spreads, at two radii
hi = np.clip((lin - 0.72) / 0.28, 0, 1) ** 2 * lin
def blur(x, r): return np.asarray(Image.fromarray(np.uint8(np.clip(x, 0, 1) ** (1 / 2.2) * 255)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0 ** 1
b1 = blur(hi, w * 0.006) ** 2.2; b2 = blur(hi, w * 0.03) ** 2.2
lin = lin + b1 * 0.22 + b2 * 0.07
# colour fringe: red a hair larger, blue a hair smaller, about the centre
def scale(ch, s):
    img = Image.fromarray(np.uint8(np.clip(ch, 0, 1) ** (1 / 2.2) * 255)); W, H = int(w * s), int(h * s)
    big = img.resize((W, H), Image.BICUBIC); x0, y0 = (W - w) // 2, (H - h) // 2
    if s >= 1: out = big.crop((x0, y0, x0 + w, y0 + h))
    else: out = Image.new('L', (w, h)); out.paste(big, (-x0, -y0)); out = Image.fromarray(np.where(np.asarray(out) == 0, np.asarray(img), np.asarray(out)).astype(np.uint8))
    return (np.asarray(out, dtype=np.float32) / 255.0) ** 2.2
lin[..., 0] = scale(lin[..., 0], 1.0012); lin[..., 2] = scale(lin[..., 2], 0.9988)
# vignette
yy, xx = np.mgrid[0:h, 0:w]; d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
lin *= (1 - 0.22 * np.clip(d, 0, 1) ** 2.2)[..., None]
out = np.clip(lin, 0, 1) ** (1 / 2.2)
# grain, stronger in the shadows, the same in every channel
rng = np.random.default_rng(seed); g = rng.normal(0, 1, (h, w)).astype(np.float32)
g = np.asarray(Image.fromarray(np.uint8(np.clip(g * 40 + 128, 0, 255))).filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32) / 40.0 - 3.2
lum = out.mean(-1, keepdims=True); out = out + g[..., None] * (0.012 + 0.018 * (1 - lum))
Image.fromarray(np.uint8(np.clip(out, 0, 1) * 255)).save(dst); print('lens', dst)
