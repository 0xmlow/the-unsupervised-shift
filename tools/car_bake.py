"""
tools/car_bake.py   (05:57 Nov 18)  the cars on the block are real models now, not lofted procedural bodies.

MLow, just before 05:50: "fix the cars ... use real cc0 glbs and the mlow taxi cabs we made to replace the cars".
Sources, all read only:
  MOMLOW 2026-10-12/work/glb_raw/h_taxi*.glb          his MoMLOW cabs (Tripo): a sedan, an SUV, a minivan, a small van
  NEW YORKERS SITE/assets/movies/.../nyb_afterhours_cab.glb   the MLOW CAB CO. checker cab
  NEW YORKERS SITE/assets/movies/.../sedan.glb        a rusted 1970s sedan with broken glass (one, abandoned)
  NEW YORKERS SITE/assets/movies/.../nyb_clover_car.glb  Poly Haven's CC0 covered car, his "TOWED BY THE DEPT. OF THE COUNTED" tarp
Ordinary parked and passing cars are the same Tripo bodies repainted: the taxi yellow becomes an everyday colour, and the
dark taxi markings that sit inside the yellow (found by closing the yellow mask) are painted over, so no taxi livery
and no city logo remain on a private car. The cabs keep their yellow; since 06:10 their dark marks (the copy of the
city's "T" and the numbers) are painted out the same way, so a cab is a plain yellow car with its roof light.
Run:  Blender -b --factory-startup --python tools/car_bake.py -- OUT.blend
Objects: car_<model>_<paint>, facing +x, origin on the ground at the middle, real length, textures packed.
"""
import bpy, sys, os, math, numpy as np
from mathutils import Matrix, Vector
OUT = sys.argv[sys.argv.index('--') + 1]
M = '/Users/degens/Desktop/NEW YORKERS BY MLOW/MOMLOW 2026-10-12/work/glb_raw'
G = '/Users/degens/Desktop/NEW YORKERS BY MLOW/NEW YORKERS SITE/assets/movies/assets/glb'
# model: (file, real length m, yaw that turns its front to +x, paints)
PAINTS = dict(silver=(168, 170, 172), black=(24, 24, 27), white=(214, 214, 208), navy=(30, 42, 72), maroon=(92, 22, 28), grey=(92, 95, 98), green=(38, 62, 52), beige=(150, 138, 112))
SRC = dict(
    camry=(M + '/h_taxi_camry.glb', 4.88, None, ['taxi', 'silver', 'black', 'white', 'navy', 'maroon', 'grey']),
    escape=(M + '/h_taxi_escape.glb', 4.59, None, ['taxi', 'black', 'grey', 'white', 'green', 'silver']),
    sienna=(M + '/h_taxi_sienna.glb', 5.17, None, ['taxi', 'silver', 'white', 'navy', 'beige']),
    nv200=(M + '/h_taxi_nv200.glb', 4.69, None, ['taxi', 'white', 'grey']),
    hcab=(M + '/h_taxi.glb', 4.8, None, ['taxi', 'black', 'maroon']),
    checker=(G + '/nyb_afterhours_cab.glb', 5.0, None, ['own']),
    rusty=(G + '/sedan.glb', 5.25, None, ['own']),
    towed=(G + '/nyb_clover_car.glb', 4.5, None, ['own']),
)
YAW = {}          # filled from the front check: degrees about z after the long axis is laid along x
try:
    YAW.update(eval(open(os.path.join(os.path.dirname(OUT), 'yaw.txt')).read()))
except Exception: pass

def shift_max(a, r):
    out = a.copy()
    for d in range(1, r + 1):
        out[d:, :] = np.maximum(out[d:, :], a[:-d, :]); out[:-d, :] = np.maximum(out[:-d, :], a[d:, :])
    a2 = out.copy()
    for d in range(1, r + 1):
        out[:, d:] = np.maximum(out[:, d:], a2[:, :-d]); out[:, :-d] = np.maximum(out[:, :-d], a2[:, d:])
    return out

MASKS = os.path.join(os.path.dirname(OUT), 'masks')
def repaint(img, rgb, name, model=None):
    w, h = img.size; px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    c = px[..., :3]; mx = c.max(-1); mn = c.min(-1); sat = (mx - mn) / np.maximum(mx, 1e-4)
    hue = np.zeros_like(mx); r, g, b = c[..., 0], c[..., 1], c[..., 2]; d = np.maximum(mx - mn, 1e-4)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    yel = (hue > 22) & (hue < 62) & (sat > 0.3) & (mx > 0.25)
    closed = 1 - shift_max(1 - shift_max(yel.astype(np.float32), 9), 9)           # dilate then erode: fills the markings
    lum = c.mean(-1)
    paint = (closed > 0.5) | yel
    paint = paint | ((shift_max(paint.astype(np.float32), 2) > 0.5) & (lum > 0.16))   # 06:11: the soft edges of the marks too, not the dark grilles (13 px reached into them)
    mp = os.path.join(MASKS, '%s_mask.png' % model)
    if model and os.path.exists(mp):        # 06:13: tools/car_masks.py fills every hole in the yellow smaller than a window, whatever its size
        mi = bpy.data.images.load(mp); mm = np.empty(w * h * 4, np.float32); mi.pixels.foreach_get(mm); paint = mm.reshape(h, w, 4)[..., 0] > 0.5; bpy.data.images.remove(mi)
    ref = np.median(lum[yel]) if yel.any() else 0.5
    # 06:15: shading from a blurred luminance inside the paint (thin printed lines, darker yellow, were kept by per-pixel shading)
    wt = (yel & (lum > 0.8 * ref)).astype(np.float32)          # only clean body paint votes for the shading, never a mark
    def blur(a):
        for _ in range(3):
            acc = a.copy()
            for dd in (1, 2, 3, 4, 5, 6, 7, 8): acc[dd:] += a[:-dd]; acc[:-dd] += a[dd:]
            a = acc / 17; acc = a.copy()
            for dd in (1, 2, 3, 4, 5, 6, 7, 8): acc[:, dd:] += a[:, :-dd]; acc[:, :-dd] += a[:, dd:]
            a = acc / 17
        return a
    bw = blur(wt); bl = np.where(bw > 0.02, blur(lum * wt) / np.maximum(bw, 1e-4), ref)
    lum = np.where(wt > 0, lum, bl)
    shade = np.where(paint, (0.9 * bl + 0.1 * lum) / max(ref, 1e-3), 1.0).clip(0.6, 1.3)[..., None]
    tgt = np.median(c[yel], 0) if rgb is None else np.array(rgb, np.float32) / 255.0      # None: keep the cab's own yellow, only paint the marks out
    new = np.where(paint[..., None], (tgt * shade).clip(0, 1), c)
    out = bpy.data.images.new(name, w, h, alpha=True); px[..., :3] = new; out.pixels.foreach_set(px.ravel()); out.pack(); return out

bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; keep = []
for key, (f, L, _, paints) in SRC.items():
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f); new = [o for o in bpy.data.objects if o not in before]
    ms = [o for o in new if o.type == 'MESH' and len(o.data.materials)]; names = [o.name for o in new]
    for o in ms:
        mw = o.matrix_world.copy(); o.parent = None; o.data = o.data.copy(); o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
    vl = bpy.context.view_layer
    for o in vl.objects: o.select_set(o in ms)
    vl.objects.active = ms[0]
    if len(ms) > 1: bpy.ops.object.join()
    ob = vl.objects.active; me = ob.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    if (max(ys) - min(ys)) > (max(xs) - min(xs)): me.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))   # long axis along x
    me.transform(Matrix.Rotation(math.radians(YAW.get(key, 0)), 4, 'Z'))
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    s = L / (max(xs) - min(xs)); me.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs)))); me.transform(Matrix.Scale(s, 4))
    for p in me.polygons: p.use_smooth = True
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is not None and o != ob: bpy.data.objects.remove(o, do_unlink=True)
    for paint in paints:
        o = ob if paint == 'own' else bpy.data.objects.new('tmp', me.copy())
        if o is not ob: sc.collection.objects.link(o)
        if paint != 'own':      # 06:10: the cabs too, so the copy of the city's "T" mark comes off
            for i, m in enumerate(o.data.materials):
                m2 = m.copy(); o.data.materials[i] = m2
                for n in m2.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image and any(l.to_socket.name == 'Base Color' for l in n.outputs[0].links):
                        n.image = repaint(n.image, PAINTS.get(paint), 'car %s %s' % (key, paint), key)
        for m in o.data.materials:      # a clear coat on the body
            b = m.node_tree.nodes.get('Principled BSDF')
            if b and 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 0.6 if key not in ('rusty', 'towed') else 0.0; b.inputs['Coat Roughness'].default_value = 0.08
        o.name = 'car_%s_%s' % (key, paint); o.use_fake_user = True; keep.append(o)
        print('car', o.name, round(max(v.co.x for v in o.data.vertices) * 2, 2), round(max(v.co.z for v in o.data.vertices), 2))
for o in list(bpy.data.objects):
    if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True); print('wrote', OUT)
