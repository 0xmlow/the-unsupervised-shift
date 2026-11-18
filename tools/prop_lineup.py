"""Render every CC0 prop from the front (-Y looking +Y) so its facing can be set. Not part of the build."""
import bpy, sys, os, math
sys.path.insert(0, sys.argv[sys.argv.index('--') + 1]); out = sys.argv[sys.argv.index('--') + 2]
bpy.ops.wm.read_factory_settings(use_empty=True)
import realism as R
ids = ['fire_hydrant', 'trashbag', 'metal_trash_can', 'exterior_aircon_unit', 'cardboard_box_01', 'plastic_crate_01', 'potted_plant_02', 'utility_box_01', 'power_box_01', 'street_lamp_01', 'street_rat', 'modular_street_seating']
x = 0.0; info = []
for i in ids:
    me, d = R.proto(i); s = 1.0 / max(d); o = R.place(i, (x, 0, 0), 0, s); info.append('%s %.2f x %.2f x %.2f' % (i, *d)); x += 1.3
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.device = 'GPU'
sc.render.resolution_x, sc.render.resolution_y = 1800, 300
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); cam.data.type = 'ORTHO'; cam.data.ortho_scale = x + 0.2
cam.location = (x / 2 - 0.65, -10, 0.5); cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.2
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3; sun.rotation_euler = (math.radians(50), math.radians(20), math.radians(-30)); sc.collection.objects.link(sun)
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('\n'.join(info))
