"""
tools/web_bake.py   (Nov 18, for the walkable block)  Blender world -> what the three.js walk needs.

Run inside Blender (no file to open, it builds the block itself):
  Blender -b --factory-startup --python tools/web_bake.py -- OUT [--test] [--samples 96] [--density 24] [--states night,dawn]

What it writes into OUT:
  lm_<state>_<atlas>.exr   Cycles COMBINED bakes (colour x light, emission, no gloss) of the street at that state
  street.glb               one mesh per atlas, UV0 = the atlas, plus the glass and the gates, no images
  scene.json               atlases, states, panes (every window quad with its window), props, parked cars, movers, lamps
  props/<mesh>.glb         each CC0 prop once, decimated, with its own textures
  cars/<model>.glb         each car body once, decimated

The states: night = 03:17 (the cat crosses, lamps on, road wet), dawn = 07:13 (sun in the slot, lamps off).
The walk blends the two by the clock. Windows are not baked: their glow is set to zero for the bake and the walk
lights every window live from block.json. Nobody who moves is baked: movers, parked cars, trash and the people in
the shops are hidden for the bake and drawn live.
"""
import sys, os, json, math, time, runpy, re
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0]); os.makedirs(OUT, exist_ok=True)
TEST = '--test' in argv
def opt(k, d): return type(d)(argv[argv.index(k) + 1]) if k in argv else d
SAMPLES = opt('--samples', 16 if TEST else 96)
DENSITY = opt('--density', 24.0)
STATES = opt('--states', 'night,dawn').split(',')
ATLAS = 1024 if TEST else 4096
T_STATE = {'night': '03:17', 'dawn': '07:13'}
T0 = time.time()
def log(*a): print('[web %5.0fs]' % (time.time() - T0), *a, flush=True)

sys.argv = [os.path.join(HERE, 'build_block.py'), '--', '--norender', '--t', '03:17']
g = runpy.run_path(os.path.join(HERE, 'build_block.py'), run_name='bb')
K = g['K']; scene = bpy.context.scene
log('built')

# ------------------------------------------------------------------ who is what
STATIC = [o for o in g['STATIC'] if o.name in bpy.data.objects]
GATES = {k: [o for o in v] for k, v in g['GATES'].items()}
gate_objs = {o.name: k for k, v in GATES.items() for o in v}
dyn = set()
for m, e, objs, k in g['MOV']: dyn.update(o.name for o in objs); dyn.add(e.name)
for c, objs in g['PARKED']: dyn.update(o.name for o in objs)
for objs, x, a, b in g['PILES']: dyn.update(o.name for o in objs)
for objs, a, b in g['INSIDE']: dyn.update(o.name for o in objs)
for o in g['CATSIT'] + g['RAINOBJ']: dyn.add(o.name)
_st = g.get('STEAM')
for o in (_st if isinstance(_st, (list, tuple)) else [_st] if _st is not None else []): dyn.add(o.name)

# text objects become meshes so they can be baked
fonts = [o for o in scene.objects if o.type in ('FONT', 'CURVE') and not o.hide_render]
for o in fonts:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.transform(o.matrix_world); n = bpy.data.objects.new('txt ' + o.name, me); scene.collection.objects.link(n)
    for s in o.material_slots:
        if s.material and s.material.name not in [m.name for m in me.materials]: me.materials.append(s.material)
    o.hide_render = True
    if o.name in gate_objs: GATES[gate_objs[o.name]].append(n)
    else: STATIC.append(n)

def mat0(o): return o.material_slots[0].material if o.material_slots else None
def alpha_of(m):
    b = m.node_tree.nodes.get('Principled BSDF') if (m and m.use_nodes) else None
    if not b: return 1.0, 0.0, False
    return b.inputs['Alpha'].default_value, b.inputs['Transmission Weight'].default_value, b.inputs['Alpha'].is_linked
glass, see = [], []
bake = []
for o in STATIC:
    if o.type != 'MESH' or not o.data.polygons: continue
    a, tw, al = alpha_of(mat0(o))
    if a < 0.9 or tw > 0.3: glass.append(o)
    elif al: see.append(o)
    else: bake.append(o)
gate_list = [o for v in GATES.values() for o in v if o.type == 'MESH' and o.data.polygons]
statics = set(o.name for o in STATIC) | set(o.name for o in gate_list) | {'Panes'}
props = [o for o in scene.objects if o.type == 'MESH' and o.name not in statics and o.name not in dyn and not o.hide_render
         and not o.name.startswith(('cast_', 'car_', 'silhouette', 'txt '))]
log('bake %d, glass %d, see-through %d, gates %d, props %d' % (len(bake), len(glass), len(see), len(gate_list), len(props)))

# ------------------------------------------------------------------ near and far
NEAR = (-26.0, 122.0, -24.0, 24.0)
def near(c): return NEAR[0] < c.x < NEAR[1] and NEAR[2] < c.y < NEAR[3]
far = []
def cut_at_box(o):
    """Big planes (the road, the ground under the city) run far past the block: cut them at the box first."""
    if max((p.area for p in o.data.polygons), default=0) < 200: return
    bm = bmesh.new(); bm.from_mesh(o.data); mwi = o.matrix_world.inverted()
    for co, no in (((NEAR[0], 0, 0), (1, 0, 0)), ((NEAR[1], 0, 0), (1, 0, 0)), ((0, NEAR[2], 0), (0, 1, 0)), ((0, NEAR[3], 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=mwi @ Vector(co), plane_no=(mwi.to_3x3().transposed().inverted() @ Vector(no)).normalized(), clear_inner=False, clear_outer=False)
    bm.to_mesh(o.data); bm.free()
for o in list(bake):
    cut_at_box(o)
    me = o.data; mw = o.matrix_world
    fl = [not near(mw @ p.center) for p in me.polygons]
    if not any(fl): continue
    if all(fl): bake.remove(o); far.append(o); continue
    n = o.copy(); n.data = me.copy(); n.name = o.name + ' far'; scene.collection.objects.link(n)
    for ob, drop in ((o, True), (n, False)):
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
        kill = [f for f in bm.faces if (not near(mw @ f.calc_center_median())) == drop]
        bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(ob.data); bm.free()
    far.append(n)
log('near %d, far %d' % (len(bake), len(far)))

def area(o): return sum(p.area for p in o.data.polygons) * abs(o.matrix_world.determinant()) ** (2 / 3)
def dens(o):
    n = o.name.lower()
    if 'roof' in n or 'tar' in n: return DENSITY * 0.25
    if 'inside' in n: return DENSITY * 0.6
    return DENSITY
def pack(objs, dfun, tag, cap_px=ATLAS):
    cap = 0.6 * cap_px * cap_px
    objs = sorted(objs, key=lambda o: (round((o.matrix_world @ o.data.polygons[0].center).y / 12), (o.matrix_world @ o.data.polygons[0].center).x))
    out, cur, acc = [], [], 0.0
    for o in objs:
        px = area(o) * dfun(o) ** 2
        if cur and acc + px > cap: out.append(cur); cur, acc = [], 0.0
        cur.append(o); acc += px
    if cur: out.append(cur)
    return {'%s%d' % (tag, i): v for i, v in enumerate(out)}
ATL = {}
ATL.update(pack(bake, dens, 'n'))
ATL.update(pack(far, lambda o: 2.0, 'f', 2048 if not TEST else 512))
ATL['gates'] = gate_list
if TEST: ATL = {k: v for k, v in list(ATL.items())[:2]}
SIZE = {k: (ATLAS if k.startswith('n') else (2048 if not TEST else 512) if k.startswith('f') else (2048 if not TEST else 512)) for k in ATL}
log('atlases', {k: (len(v), round(sum(area(o) for o in v))) for k, v in ATL.items()})

# ------------------------------------------------------------------ unwrap
def unwrap(objs, size):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.data = o.data.copy() if o.data.users > 1 else o.data
        uv = o.data.uv_layers.get('lm') or o.data.uv_layers.new(name='lm'); o.data.uv_layers.active = uv; o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
    try: bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=4.0 / size)
    except TypeError: bpy.ops.uv.pack_islands(rotate=True, margin=4.0 / size)
    bpy.ops.object.mode_set(mode='OBJECT')
for k, objs in ATL.items():
    for o in objs:          # world space, no parents: the export and the bake both want it
        mw = o.matrix_world.copy(); o.parent = None; o.data = o.data.copy(); o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
    unwrap(objs, SIZE[k]); log('unwrapped', k)

# ------------------------------------------------------------------ bake
scene.render.engine = 'CYCLES'
try:
    pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'METAL'; pr.get_devices()
    for d in pr.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e: log('GPU setup failed', e)
scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = False
scene.render.bake.margin = 6; scene.render.bake.margin_type = 'EXTEND'
apply_time = g['apply_time']; GLOW = g['GLOW']; pme = g['pme']
def quiet():
    """Nothing that moves, no window glow, no rain."""
    for n in dyn:
        o = bpy.data.objects.get(n)
        if o: o.hide_render = True
    for o in scene.objects:
        if o.name.startswith(('silhouette', 'cast_', 'car_')) and o.name not in statics: o.hide_render = True
    GLOW.data.foreach_set('color', [0.0] * (len(GLOW.data) * 4)); pme.update()
def bake_atlas(state, k, objs):
    size = SIZE[k]; img = bpy.data.images.new('lm_%s_%s' % (state, k), size, size, float_buffer=True, alpha=False)
    img.colorspace_settings.name = 'Non-Color'; touched = []
    for m in {s.material for o in objs for s in o.material_slots if s.material}:
        if not m.use_nodes: m.use_nodes = True
        n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img
        for x in m.node_tree.nodes: x.select = False
        n.select = True; m.node_tree.nodes.active = n; touched.append((m, n))
    hidden = []
    for o in objs:
        if o.hide_render: o.hide_render = False; hidden.append(o)     # a gate that is up at this hour still gets its picture
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.data.uv_layers.active = o.data.uv_layers['lm']; o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    t = time.time()
    bpy.ops.object.bake(type='COMBINED', pass_filter={'EMIT', 'DIRECT', 'INDIRECT', 'DIFFUSE'}, use_clear=True, margin=6)
    for o in hidden: o.hide_render = True
    p = os.path.join(OUT, 'lm_%s_%s.exr' % (state, k))
    s = scene.render.image_settings; s.file_format = 'OPEN_EXR'; s.color_depth = '16'; s.exr_codec = 'ZIP'
    vs = scene.view_settings; keep = (vs.view_transform, vs.look, vs.exposure, vs.gamma)
    vs.view_transform, vs.look, vs.exposure, vs.gamma = 'Raw', 'None', 0.0, 1.0
    img.save_render(p, scene=scene); vs.view_transform, vs.look, vs.exposure, vs.gamma = keep
    for m, n in touched: m.node_tree.nodes.remove(n)
    bpy.data.images.remove(img); log('baked %s %s: %d objs %dpx %d spp %.0fs' % (state, k, len(objs), size, SAMPLES, time.time() - t))
EXPO = {}
for st in STATES:
    t = K.T(T_STATE[st]); apply_time(t); quiet()
    EXPO[st] = g['exposure_for'](t)
    for k, objs in ATL.items(): bake_atlas(st, k, objs)

# ------------------------------------------------------------------ the street GLB
bpy.ops.object.select_all(action='DESELECT')
keep = []
def one_mesh(name, objs, mname):
    objs = [o for o in objs if o.name in bpy.data.objects]
    if not objs: return None
    for o in objs:
        for uv in list(o.data.uv_layers):
            if uv.name != 'lm': o.data.uv_layers.remove(uv)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name
    m = bpy.data.materials.get(mname) or bpy.data.materials.new(mname)
    o.data.materials.clear(); o.data.materials.append(m); return o
for k, objs in ATL.items():
    if k == 'gates':
        for key, v in GATES.items():
            o = one_mesh('gate_' + key, [x for x in v if x in objs], 'atlas_gates')
            if o: keep.append(o)
    else:
        o = one_mesh('atlas_' + k, objs, 'atlas_' + k)
        if o: keep.append(o)
for i, o in enumerate(glass + see):
    mw = o.matrix_world.copy(); o.parent = None; o.data = o.data.copy(); o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
    m = mat0(o); o.name = ('glass_%d' if o in glass else 'see_%d') % i
    for uv in list(o.data.uv_layers): o.data.uv_layers.remove(uv)
    o.data.materials.clear(); o.data.materials.append(bpy.data.materials.new('glass' if o.name.startswith('glass') else 'chainlink')); keep.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in keep: o.hide_render = False; o.hide_set(False); o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'street.glb'), export_format='GLB', use_selection=True, export_image_format='NONE',
                          export_yup=True, export_apply=False, export_texcoords=True, export_normals=False, export_materials='EXPORT')
log('street.glb', len(keep), 'meshes')

# ------------------------------------------------------------------ data for the live parts
def yup(v): return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]
panes = []
for i, (w, static) in enumerate(g['PANES']):
    f = g['PANE_F'][i]; pts = [yup(g['PANE_V'][j]) for j in f]
    panes.append({'p': pts, 'w': (w['i'] if w is not None and 'i' in w else -1), 'c': [round(x, 3) for x in static] if static is not None else None})
def mat_list(m):
    loc, rot, sc = m.decompose(); return {'p': yup(loc), 'q': [round(rot.x, 4), round(rot.z, 4), round(-rot.y, 4), round(rot.w, 4)], 's': [round(sc.x, 4), round(sc.z, 4), round(sc.y, 4)]}
# props: one GLB per mesh, instances by transform
os.makedirs(os.path.join(OUT, 'props'), exist_ok=True)
pile_of = {o.name: i for i, (objs, x, a, b) in enumerate(g['PILES']) for o in objs}
groups = {}
for o in props + [o for objs, x, a, b in g['PILES'] for o in objs]:
    if o.type == 'MESH': groups.setdefault(o.data.name, []).append(o)
def export_one(o, path, budget):
    n = bpy.data.objects.new('x', o.data.copy()); scene.collection.objects.link(n)
    tris = sum(len(p.vertices) - 2 for p in n.data.polygons)
    if tris > budget:
        md = n.modifiers.new('d', 'DECIMATE'); md.ratio = budget / tris
        bpy.context.view_layer.objects.active = n; bpy.ops.object.modifier_apply(modifier='d')
    bpy.ops.object.select_all(action='DESELECT'); n.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_image_format='AUTO')
    bpy.data.objects.remove(n, do_unlink=True)
PROPS = []
for mn, obs in groups.items():
    safe = re.sub(r'[^a-z0-9_]+', '_', mn.lower()).strip('_')
    export_one(obs[0], os.path.join(OUT, 'props', safe + '.glb'), 3000 if len(obs) > 6 else 6000)
    PROPS.append({'mesh': safe, 'inst': [dict(mat_list(o.matrix_world), pile=pile_of.get(o.name, -1)) for o in obs]})
log('props', len(PROPS), 'meshes', sum(len(p['inst']) for p in PROPS), 'instances')
# cars: every Tripo body that appears, once; vehicles built from code, the cat and the rat, one GLB per mover
os.makedirs(os.path.join(OUT, 'cars'), exist_ok=True)
def model_key(o): return o.name.split(' ')[-1] if o.type == 'MESH' and o.name.split(' ')[-1].startswith('car_') else None
def export_group(objs, root_inv, path):
    tmp = []
    for o in objs:
        n = bpy.data.objects.new('v', o.data.copy()); n.data.transform(root_inv @ o.matrix_world); scene.collection.objects.link(n); tmp.append(n)
    bpy.ops.object.select_all(action='DESELECT')
    for n in tmp: n.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_image_format='AUTO')
    for n in tmp: bpy.data.objects.remove(n, do_unlink=True)
models = {}
PARKED = []
for c, objs in g['PARKED']:
    o = next((x for x in objs if model_key(x)), None)
    if o is None: continue
    models.setdefault(model_key(o), o); PARKED.append(dict(mat_list(o.matrix_world), model=model_key(o), arrive=c['arrive'], leave=c['leave']))
MOVERS = []
for mi, (m, e, objs, k) in enumerate(g['MOV']):
    rec = {'i': K.MOVERS.index(m), 'kind': k}
    meshes = [x for x in objs if x.type == 'MESH']
    car = next((x for x in meshes if model_key(x)), None)
    people = [x for x in meshes if x.name.startswith('cast ')]
    if people:
        rec['cast'] = people[0].name.split(' ')[1]
        ph = g['MOVPH'].get(mi)
        if ph: rec['stride'] = round(ph['stride'], 4)
        rec['local'] = mat_list(e.matrix_world.inverted() @ people[0].matrix_world)
    else:
        if car is not None:
            models.setdefault(model_key(car), car); rec['model'] = model_key(car); rec['local'] = mat_list(e.matrix_world.inverted() @ car.matrix_world)
        rest = [x for x in meshes if x is not car]
        if rest:
            export_group(rest, e.matrix_world.inverted(), os.path.join(OUT, 'cars', 'veh_%03d.glb' % mi)); rec['veh'] = 'veh_%03d' % mi
    MOVERS.append(rec)
for mn, o in models.items(): export_one(o, os.path.join(OUT, 'cars', mn + '.glb'), 14000)
# the people standing in lit windows: one GLB, shown while their window schedule says so
SIL = []
sil_objs = []
for objs, a_, b_ in g['INSIDE']:
    for o in objs:
        if o.type != 'MESH': continue
        n = bpy.data.objects.new('sil_%d' % len(SIL), o.data.copy()); n.data.transform(o.matrix_world); scene.collection.objects.link(n)
        tris = sum(len(p.vertices) - 2 for p in n.data.polygons)
        if tris > 800:
            md = n.modifiers.new('d', 'DECIMATE'); md.ratio = 800 / tris; bpy.context.view_layer.objects.active = n; bpy.ops.object.modifier_apply(modifier='d')
        n.data.materials.clear(); sil_objs.append(n); SIL.append({'name': n.name, 'a': a_, 'b': b_})
bpy.ops.object.select_all(action='DESELECT')
for n in sil_objs: n.select_set(True)
if sil_objs: bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'silhouettes.glb'), export_format='GLB', use_selection=True, export_yup=True, export_materials='NONE', export_normals=False)
log('cars', len(models), 'models,', len(PARKED), 'parked,', len(MOVERS), 'movers,', len(SIL), 'silhouettes')
data = {'states': {s: {'t': K.T(T_STATE[s]), 'exposure': EXPO[s]} for s in STATES},
        'atlases': {k: {'size': SIZE[k]} for k in ATL}, 'panes': panes, 'props': PROPS, 'parked': PARKED, 'movers': MOVERS, 'silhouettes': SIL,
        'near': NEAR}
json.dump(data, open(os.path.join(OUT, 'scene.json'), 'w'), separators=(',', ':'))
log('done')
