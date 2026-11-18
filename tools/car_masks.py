"""
tools/car_masks.py OUTDIR [MAXAREA]   (06:12 Nov 18)  where to repaint each MoMLOW cab texture.

Run with the system python (numpy, scipy, PIL), not Blender's. For each cab GLB it reads the embedded texture, finds the
taxi yellow by hue, then marks as paint: the yellow itself, every hole in the yellow smaller than MAXAREA pixels (the
city "T", numbers, stripes: whole, whatever their size), and a 2 px rim round them that is not dark. Big holes (windows,
grilles, lamps) stay as they are. Writes OUTDIR/<model>_mask.png (white = paint) and <model>_check.png to look at.
tools/car_bake.py reads the masks.
"""
import sys, os, json, struct, io
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
OUT = sys.argv[1]; MAXA = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
M = '/Users/degens/Desktop/NEW YORKERS BY MLOW/MOMLOW 2026-10-12/work/glb_raw'
SRC = dict(camry='h_taxi_camry', escape='h_taxi_escape', sienna='h_taxi_sienna', nv200='h_taxi_nv200', hcab='h_taxi')
os.makedirs(OUT, exist_ok=True)

def glb_image(path):
    b = open(path, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; js = json.loads(b[20:20 + n]); o = 20 + n
    bl = struct.unpack('<I', b[o:o + 4])[0]; binc = b[o + 8:o + 8 + bl]
    img = js['images'][0]; bv = js['bufferViews'][img['bufferView']]; s = bv.get('byteOffset', 0)
    return Image.open(io.BytesIO(binc[s:s + bv['byteLength']])).convert('RGB')

for key, f in SRC.items():
    im = glb_image(os.path.join(M, f + '.glb')); c = np.asarray(im, np.float32) / 255
    mx = c.max(-1); mn = c.min(-1); sat = (mx - mn) / np.maximum(mx, 1e-4); d = np.maximum(mx - mn, 1e-4); r, g, b = c[..., 0], c[..., 1], c[..., 2]
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    yel = (hue > 22) & (hue < 62) & (sat > 0.3) & (mx > 0.25)
    holes = ndi.binary_fill_holes(yel) & ~yel; lab, n = ndi.label(holes); area = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    small = np.isin(lab, 1 + np.nonzero(area < MAXA)[0])
    paint = yel | small | ndi.binary_closing(yel, iterations=4)
    lum = c.mean(-1); paint |= ndi.binary_dilation(paint, iterations=2) & (lum > 0.16)
    Image.fromarray((paint * 255).astype(np.uint8)).save(os.path.join(OUT, key + '_mask.png'))
    chk = (c * 255).astype(np.uint8).copy(); chk[paint & ~yel] = (255, 0, 255); Image.fromarray(chk).save(os.path.join(OUT, key + '_check.png'))
    print(key, im.size, 'holes', n, 'filled', int((area < MAXA).sum()), 'largest kept', int(area[area >= MAXA].min()) if (area >= MAXA).any() else 0)
