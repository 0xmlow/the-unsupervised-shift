"""tools/people_lineup.py NPZ OUT.png : render a row of the baked people, three quarter view, to look at them."""
import bpy, sys, math, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]; D = np.load(a[0]); out = a[1]
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
def M(n, c, r=0.6):
    m = bpy.data.materials.new(n); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = c + (1,); b.inputs['Roughness'].default_value = r
    if n == 'skin': b.inputs['Subsurface Weight'].default_value = 0.15; b.inputs['Subsurface Radius'].default_value = (0.5, 0.2, 0.1)
    return m
mats = {'skin': M('skin', (0.55, 0.36, 0.26), 0.5), 'hair': M('hair', (0.02, 0.014, 0.01), 0.45), 'hat': M('hat', (0.05, 0.05, 0.06), 0.8), 'coat': M('coat', (0.16, 0.38, 1.0), 0.75),
        'legs': M('legs', (0.03, 0.03, 0.04), 0.8), 'shoe': M('shoe', (0.015, 0.015, 0.017), 0.35), 'eye': M('eye', (0.06, 0.045, 0.035), 0.08)}
roles = list(D['roles']); names = list(D['names']); pick = [n for n in names if n.endswith('hair') or 'long_hat' in n][:12] if len(a) < 3 else a[2].split(',')
for i, k in enumerate(pick):
    V = D[k + '_v'] * 1.75; F = D[k + '_f']; Rr = D[k + '_r']
    for ri, rn in enumerate(roles):
        sel = np.where(Rr == ri)[0]
        if not len(sel): continue
        fs = [tuple(int(x) for x in F[j] if x >= 0) for j in sel]; used = sorted({x for f in fs for x in f}); mp = {u: n for n, u in enumerate(used)}
        me = bpy.data.meshes.new(k + rn); me.from_pydata([tuple(V[u]) for u in used], [], [tuple(mp[x] for x in f) for f in fs]); me.materials.append(mats[rn])
        for p in me.polygons: p.use_smooth = True
        o = bpy.data.objects.new(k + rn, me); sc.collection.objects.link(o); o.location = (0, i * 0.9, 0)
    if 'long' in k:
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.21, radius2=0.17, depth=1.75 * 0.17, location=(0.0, i * 0.9, 1.75 * (0.30 + 0.085)))
        o = bpy.context.object; o.data.materials.append(mats['coat']); [setattr(p, 'use_smooth', True) for p in o.data.polygons]
fl = bpy.data.meshes.new('floor'); fl.from_pydata([(-5, -3, 0), (5, -3, 0), (5, 15, 0), (-5, 15, 0)], [], [(0, 1, 2, 3)]); fo = bpy.data.objects.new('floor', fl); sc.collection.objects.link(fo); fo.data.materials.append(M('floor', (0.3, 0.3, 0.3), 0.8))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; n = len(pick)
cam.location = (5.2, (n - 1) * 0.45 - 2.2, 1.5); cam.data.lens = 35
d = np.array([0, (n - 1) * 0.45, 0.9]) - np.array(cam.location); cam.rotation_euler = (math.atan2(math.hypot(d[0], d[1]), -d[2]), 0, math.atan2(d[1], d[0]) - math.pi / 2)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(60))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.35, 0.4, 0.5, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.device = 'GPU'; sc.render.resolution_x = 1800; sc.render.resolution_y = 700; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
