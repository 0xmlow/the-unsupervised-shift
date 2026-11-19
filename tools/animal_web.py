"""tools/animal_web.py OUTDIR  (Nov 19) the cat and the rat for the walk, normalised exactly as build_block.glb_animal does
(+x forward, feet at 0, metres), exported as GLB so walk.js can load them in place of the old code-built shapes."""
import bpy, sys, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
SPEC = {'cat': ('assets/animals/cat_tabby_mlow_tripo.glb', 0.30, 'h'), 'rat': ('assets/animals/street_rat_polyhaven_cc0.glb', 0.24, 'l')}
for kind, (path, size, axis) in SPEC.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, path)); bpy.context.view_layer.update()
    ms = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in ms: o.data = o.data.copy(); o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix.Identity(4)
    for o in [o for o in bpy.data.objects if o.type != 'MESH']: bpy.data.objects.remove(o, do_unlink=True)
    if len(ms) > 1:
        for o in ms: o.select_set(True)
        bpy.context.view_layer.objects.active = ms[0]; bpy.ops.object.join()
    src = bpy.data.objects[0]
    def box():
        co = [v.co for v in src.data.vertices]; return Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co))), Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    lo, hi = box(); d = hi - lo
    if d.y > d.x * 1.3: src.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z')); lo, hi = box(); d = hi - lo
    k = size / (d.z if axis == 'h' else max(d.x, d.y))
    src.data.transform(Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))); src.data.transform(Matrix.Scale(k, 4))
    lo, hi = box(); print('ANIMAL', kind, tuple(round(v, 3) for v in (hi - lo)))
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, kind + '.glb'), export_format='GLB', export_yup=True)
