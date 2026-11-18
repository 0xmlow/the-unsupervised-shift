"""tools/cast_lineup.py CAST.blend OUT.png [names]: the baked cast in a row, seen from +x (their front) and a little to the side."""
import bpy, sys, math
a = sys.argv[sys.argv.index('--') + 1:]; bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
with bpy.data.libraries.load(a[0]) as (src, dst): dst.objects = [n for n in src.objects if (len(a) < 3 or n in a[2].split(','))]
for i, o in enumerate(dst.objects):
    sc.collection.objects.link(o); s = 1.75 / o.dimensions.z; o.scale = (s, s, s); o.location = (0, i * 0.8, 0)
n = len(dst.objects); fl = bpy.data.meshes.new('f'); fl.from_pydata([(-6, -3, 0), (6, -3, 0), (6, n, 0), (-6, n, 0)], [], [(0, 1, 2, 3)]); sc.collection.objects.link(bpy.data.objects.new('f', fl))
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 30
cam.location = (7.5, n * 0.4 - 2.5, 1.6); import mathutils; d = mathutils.Vector((0, n * 0.4, 0.9)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sun = bpy.data.objects.new('s', bpy.data.lights.new('s', 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(70))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.4, 0.42, 0.48, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.device = 'GPU'; sc.render.resolution_x = 2200; sc.render.resolution_y = 700; sc.render.filepath = a[1]; bpy.ops.render.render(write_still=True)
