"""tools/cars_lineup.py CARS.blend OUT.png [names]: the baked cars in a row along y, seen from +x (their fronts) three quarters."""
import bpy, sys, math, mathutils
a = sys.argv[sys.argv.index('--') + 1:]; bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
with bpy.data.libraries.load(a[0]) as (src, dst): dst.objects = [n for n in src.objects if len(a) < 3 or n in a[2].split(',')]
for i, o in enumerate(dst.objects): sc.collection.objects.link(o); o.location = (0, i * 2.6, 0)
n = len(dst.objects); fl = bpy.data.meshes.new('f'); fl.from_pydata([(-8, -4, 0), (12, -4, 0), (12, n * 2.6 + 2, 0), (-8, n * 2.6 + 2, 0)], [], [(0, 1, 2, 3)]); sc.collection.objects.link(bpy.data.objects.new('f', fl))
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 28
cam.location = (11, -3.5, 3.2); d = mathutils.Vector((0, n * 1.3, 0.7)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sun = bpy.data.objects.new('s', bpy.data.lights.new('s', 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 3; sun.rotation_euler = (math.radians(45), 0, math.radians(60))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.45, 0.47, 0.52, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'GPU'; sc.render.resolution_x = 2200; sc.render.resolution_y = 900; sc.render.filepath = a[1]; bpy.ops.render.render(write_still=True)
