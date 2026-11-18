"""
tools/cast_bake.py   (04:53 Nov 18)  the people on the block are MLow's own NEW YORKERS figures (flower heads, no faces).

MLow, just before 04:50: "these people are awful please replace with diff character glbs we have already made". The base-mesh
people are gone; these are the rigged ON LOCATION cast from 2026-10-28 (NEW YORKERS BY MLOW/UPGRADE ALL ROOMS
2026-10-28/rig/out), each posed from its own clip and frozen:
  walk  one frame a third of the way through the walk cycle (mid stride)
  idle  the first frame of the idle clip (standing, weight settled)
Run:  Blender -b --factory-startup --python tools/cast_bake.py -- RIG_OUT_DIR OUT.blend
Each object is named cast_<name>_<pose>, faces +x, origin between the feet, materials and textures packed.
"""
import bpy, sys, os, math
from mathutils import Matrix
a = sys.argv[sys.argv.index('--') + 1:]; SRC, OUT = a[0], a[1]
WALK = ['cabbie', 'workgirl', 'wiseguy', 'writer', 'oscar', 'hustler', 'editor', 'killer', 'annieh', 'loretta', 'gown', 'bartender', 'susan', 'actress', 'tough', 'discoking']
IDLE = WALK + ['clerk', 'blindwoman']
FIX = {'writer': 90}      # 04:57: writer's sculpt stands a quarter turn off the others (seen in the lineup)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; keep = []

def bake(name, pose):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, name + '.glb'))
    new = [o for o in bpy.data.objects if o not in before]; arm = next((o for o in new if o.type == 'ARMATURE'), None)
    meshes = [o for o in new if o.type == 'MESH' and len(o.data.materials)]      # not the importer's Icosphere bone shape
    if arm is not None:
        clip = 'walk' if pose.startswith('w') else pose; acts = [ac for ac in bpy.data.actions if clip in ac.name.lower()]
        if not acts: print('no clip', name, pose, [ac.name for ac in bpy.data.actions]); acts = [ac for ac in bpy.data.actions if 'idle' in ac.name.lower()]
        ac = acts[-1]; ad = arm.animation_data or arm.animation_data_create(); ad.action = ac
        if hasattr(ad, 'action_slot') and len(getattr(ac, 'slots', [])): ad.action_slot = ac.slots[0]
        f0, f1 = ac.frame_range; ph = 0.33 if pose == 'walk' else 0.0 if pose == 'idle' else int(pose[1:]) / 8.0
        fr = f0 + (f1 - f0) * ph; sc.frame_set(int(fr), subframe=fr % 1)
    dg = bpy.context.evaluated_depsgraph_get(); parts = []
    for o in meshes:
        ev = o.evaluated_get(dg); me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg); me.transform(o.matrix_world); parts.append(me)
    ob = bpy.data.objects.new('cast_%s_%s' % (name, pose), parts[0]); sc.collection.objects.link(ob)
    for me in parts[1:]:
        t = bpy.data.objects.new('tmp', me); sc.collection.objects.link(t)
    if len(parts) > 1:
        for o in bpy.context.view_layer.objects: o.select_set(o.name == ob.name or o.name.startswith('tmp'))
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.join()
    me = ob.data; me.transform(Matrix.Rotation(math.radians(90 + FIX.get(name, 0)), 4, 'Z'))          # the cast faces -y after import; the block wants +x
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    feet = [v.co for v in me.vertices if v.co.z < min(zs) + 0.12]
    cx = sum(c.x for c in feet) / len(feet); cy = sum(c.y for c in feet) / len(feet)
    me.transform(Matrix.Translation((-cx, -cy, -min(zs))))
    for p in me.polygons: p.use_smooth = True
    for o in new:
        if o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)
    for ac in list(bpy.data.actions): bpy.data.actions.remove(ac)
    keep.append(ob); print('cast', ob.name, len(me.vertices), round(max(zs) - min(zs), 2))

for n in WALK: bake(n, 'walk')
for n in IDLE: bake(n, 'idle')
for n in WALK:                      # 05:33: eight phases of the walk, so a person in the film steps instead of sliding
    for k in range(8): bake(n, 'w%d' % k)
for o in list(bpy.data.objects):
    if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
for o in keep: o.use_fake_user = True
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True); print('wrote', OUT)
