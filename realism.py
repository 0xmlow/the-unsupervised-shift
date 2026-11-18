"""
THE UNSUPERVISED SHIFT  ·  realism.py  (added 20:30, MLow asked for "much more realistic, much more detailed")
Imported by build_block.py. Three things the first pass did not have:

  1. Photographed surfaces. Poly Haven CC0 maps (assets/cc0/tex/<id>/diff, rough, disp) and Firefly textures
     (assets/firefly/*.jpg), box projected in world space because the block has no UVs. Each map is tinted to the
     colour block.py gives that building, so the colour plan of the street survives.
  2. Weather on the walls: rain streaks under every sill line, splash grime at the foot, soot at the cornice,
     and a bevel on every edge so boxes stop reading as boxes.
  3. Real props: CC0 GLBs (hydrant, cans, bags, AC units, boxes, crates, plants, utility boxes) imported once
     and placed as linked copies.

Nothing here decides where anything is. block.py still owns the block; this file only dresses it.
"""
import bpy, os, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
CC0 = os.path.join(HERE, 'assets', 'cc0'); FF = os.path.join(HERE, 'assets', 'firefly')
MEANS = json.load(open(os.path.join(CC0, 'means.json')))
for f in ('means.json',):
    p = os.path.join(FF, f)
    if os.path.exists(p): MEANS.update(json.load(open(p)))
ON = os.environ.get('REALISM', '1') != '0'

_IMG = {}
def image(path, data=False):
    if path not in _IMG:
        im = bpy.data.images.load(path, check_existing=True)
        im.colorspace_settings.name = 'Non-Color' if data else 'sRGB'; _IMG[path] = im
    return _IMG[path]

def _coords(nt, size, rot=0.0, offset=(0, 0, 0)):
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / size, 1 / size, 1 / size); mp.inputs['Rotation'].default_value = (0, 0, rot)
    mp.inputs['Location'].default_value = offset
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); return mp.outputs['Vector']

def _tex(nt, vec, path, data=False, blend=0.3):
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = image(path, data); tx.projection = 'BOX'; tx.projection_blend = blend
    tx.interpolation = 'Cubic' if not data else 'Linear'; nt.links.new(vec, tx.inputs['Vector']); return tx

def _math(nt, op, a, b=None, v=None):
    m = nt.nodes.new('ShaderNodeMath'); m.operation = op
    for i, x in enumerate((a, b)):
        if x is None: continue
        if isinstance(x, (int, float)): m.inputs[i].default_value = x
        else: nt.links.new(x, m.inputs[i])
    return m.outputs[0]

def _mix(nt, mode, a, b, fac=1.0):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = mode
    if isinstance(fac, (int, float)): m.inputs['Factor'].default_value = fac
    else: nt.links.new(fac, m.inputs['Factor'])
    for sock, x in ((6, a), (7, b)):
        if isinstance(x, tuple): m.inputs[sock].default_value = (*x, 1) if len(x) == 3 else x
        else: nt.links.new(x, m.inputs[sock])
    return m.outputs[2]

def _noise(nt, scale, detail=6, rough=0.6, vec=None, stretch=None):
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    if vec is not None or stretch is not None:
        tc = nt.nodes.new('ShaderNodeTexCoord'); src = tc.outputs['Object']
        if stretch is not None:
            vm = nt.nodes.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY'; vm.inputs[1].default_value = stretch; nt.links.new(src, vm.inputs[0]); src = vm.outputs[0]
        nt.links.new(src, n.inputs['Vector'])
    return n.outputs['Fac']

def _ramp(nt, x, a, b, lo, hi, smooth=True):
    r = nt.nodes.new('ShaderNodeMapRange'); r.clamp = True
    if smooth: r.interpolation_type = 'SMOOTHSTEP'
    r.inputs['From Min'].default_value = a; r.inputs['From Max'].default_value = b; r.inputs['To Min'].default_value = lo; r.inputs['To Max'].default_value = hi
    nt.links.new(x, r.inputs['Value']); return r.outputs['Result']

def _z(nt):
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sp.inputs[0]); return sp.outputs['Z']

def surface(m, tid, size, tint=None, bump=0.45, rough=None, rough_mul=1.0, weather=None, bevel=0.0, firefly=False, rot=0.0, offset=(0, 0, 0), keep_rough=False):
    """Replace a material's colour, roughness and relief with a photographed surface, box projected in world metres.
    tint: linear RGB the surface should average to (None keeps the photograph's own colour).
    weather: None, or dict(top=H, streaks=0..1, splash=0..1, soot=0..1) for a facade."""
    if not ON: return m
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; root = FF if firefly else os.path.join(CC0, 'tex', tid)
    path = (lambda k: os.path.join(FF, tid + ('' if k == 'diff' else '_' + k) + '.jpg')) if firefly else (lambda k: os.path.join(root, k + '.jpg'))
    vec = _coords(nt, size, rot, offset)
    col = _tex(nt, vec, path('diff')).outputs['Color']
    if tint is not None and tid in MEANS:
        mu = MEANS[tid]; ratio = tuple(max(0.05, min(6.0, t / max(1e-4, u))) for t, u in zip(tint, mu))
        col = _mix(nt, 'MULTIPLY', col, ratio)
    # large scale variation so no two bays look stamped from the same photograph
    var = _ramp(nt, _noise(nt, 0.08, 3, 0.5, vec=True), 0.3, 0.7, 0.82, 1.12)
    col = _mix(nt, 'MULTIPLY', col, _comb(nt, var))
    if weather:
        z = _z(nt)
        if weather.get('streaks'):
            st = _noise(nt, 1.0, 4, 0.5, stretch=(9.0, 9.0, 0.35))                        # long vertical runs of water
            stk = _ramp(nt, st, 0.48, 0.72, 1.0, 1.0 - 0.45 * weather['streaks'])
            col = _mix(nt, 'MULTIPLY', col, _comb(nt, stk))
        if weather.get('splash'):
            sp = _ramp(nt, z, 0.15, 1.3, 1.0 - 0.5 * weather['splash'], 1.0)
            col = _mix(nt, 'MULTIPLY', col, _comb(nt, sp))
        if weather.get('soot') and weather.get('top'):
            so = _ramp(nt, z, weather['top'] - 3.5, weather['top'], 1.0, 1.0 - 0.4 * weather['soot'])
            col = _mix(nt, 'MULTIPLY', col, _comb(nt, so))
    nt.links.new(col, b.inputs['Base Color'])
    if not keep_rough and os.path.exists(path('rough')):
        r = _tex(nt, vec, path('rough'), True).outputs['Color']
        rr = _math(nt, 'MULTIPLY', r, rough_mul); nt.links.new(rr, b.inputs['Roughness'])
    elif rough is not None and not keep_rough: b.inputs['Roughness'].default_value = rough
    # relief: displacement map through a bump, chained after any bump already on the material
    hp = path('disp') if os.path.exists(path('disp')) else None
    prev = b.inputs['Normal'].links[0].from_socket if b.inputs['Normal'].is_linked else None
    if bevel > 0:
        bv = nt.nodes.new('ShaderNodeBevel'); bv.inputs['Radius'].default_value = bevel; bv.samples = 4
        if prev is not None: nt.links.new(prev, bv.inputs['Normal'])
        prev = bv.outputs['Normal']
    if hp and bump > 0:
        h = _tex(nt, vec, hp, True).outputs['Color']
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = size * 0.012
        nt.links.new(h, bp.inputs['Height'])
        if prev is not None: nt.links.new(prev, bp.inputs['Normal'])
        prev = bp.outputs['Normal']
    if prev is not None: nt.links.new(prev, b.inputs['Normal'])
    return m

def _comb(nt, f):
    c = nt.nodes.new('ShaderNodeCombineXYZ')
    for k in ('X', 'Y', 'Z'): nt.links.new(f, c.inputs[k])
    return c.outputs[0]

def bevel_only(m, radius=0.01):
    """Round the edges of a flat material (sashes, steel, kerbs) without changing its colour."""
    if not ON: return m
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; bv = nt.nodes.new('ShaderNodeBevel'); bv.inputs['Radius'].default_value = radius; bv.samples = 4
    if b.inputs['Normal'].is_linked: nt.links.new(b.inputs['Normal'].links[0].from_socket, bv.inputs['Normal'])
    nt.links.new(bv.outputs['Normal'], b.inputs['Normal']); return m

# ------------------------------------------------------------------ props: CC0 GLBs, imported once, placed as linked copies
PROTO = {}; PLACED = []
PAIRS = {'fire_hydrant': 'left', 'metal_trash_can': 'right', 'exterior_aircon_unit': 'left'}     # which variant to keep
def proto(pid):
    """Import a Poly Haven glTF, join it into one mesh with its origin at the bottom centre, keep it out of the scene."""
    if pid in PROTO: return PROTO[pid]
    d = os.path.join(CC0, 'models', pid); f = [x for x in os.listdir(d) if x.endswith('.gltf') and not x.startswith('._')][0]
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(d, f))
    new = [o for o in bpy.data.objects if o not in before]; meshes = [o for o in new if o.type == 'MESH']; names = [o.name for o in new]
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.data = o.data.copy() if o.data.users > 1 else o.data; o.data.transform(mw); o.matrix_world.identity()
    vl = bpy.context.view_layer
    for o in vl.objects: o.select_set(False)
    for o in meshes: o.select_set(True)
    vl.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    ob = vl.objects.active
    if pid in PAIRS:      # Poly Haven ships some props as two variants side by side: keep the left one
        import bmesh
        bm = bmesh.new(); bm.from_mesh(ob.data); mid = (min(v.co.x for v in bm.verts) + max(v.co.x for v in bm.verts)) / 2
        keep_left = PAIRS[pid] == 'left'; bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.calc_center_median().x > mid) == keep_left], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(ob.data); bm.free()
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]; zs = [v.co.z for v in ob.data.vertices]
    cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    from mathutils import Matrix
    ob.data.transform(Matrix.Translation((-cx, -cy, -z0)))
    for p in ob.data.polygons: p.use_smooth = True
    dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - z0)
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is not None and o != ob: bpy.data.objects.remove(o, do_unlink=True)
    for c in list(ob.users_collection): c.objects.unlink(ob)
    PROTO[pid] = (ob.data, dims); return PROTO[pid]

def place(pid, loc, rotz=0.0, scale=1.0, fit=None, name=None):
    """A linked copy of a prop. fit=(axis, metres) scales it so that dimension matches."""
    if not ON: return None
    me, dims = proto(pid)
    if fit is not None: scale = fit[1] / max(1e-4, dims['xyz'.index(fit[0])])
    o = bpy.data.objects.new(name or pid, me); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, rotz); o.scale = (scale, scale, scale); PLACED.append(o); return o

def soften(objs, width=0.07, segs=3, names=('paint', 'Dark glass')):
    """Round the boxes a car is made of: a bevel modifier on its body and glass, smooth shaded."""
    if not ON: return
    for o in objs:
        if o.type == 'MESH' and o.data.materials and o.data.materials[0].name.startswith(names):
            md = o.modifiers.new('round', 'BEVEL'); md.width = width; md.segments = segs; md.use_clamp_overlap = True; md.limit_method = 'ANGLE'
            for p in o.data.polygons: p.use_smooth = True
            md.harden_normals = False

# how the CC0 window air conditioner sits (set from a lineup render at 20:45: which way its grille faces)
AC_ROT, AC_AXIS, AC_V, AC_DZ = 0.0, 'x', 0.42, -0.95      # a condenser on a bracket under the sill, grille to the street

def street_wear(m, road, length):
    """What traffic does to a street between two corners: dirt and leaves banked in both gutters, the wheel tracks
    polished a little lighter, an oil drip line down the middle of the lane. World y across the street, x along it."""
    if not ON: return
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    if not b.inputs['Base Color'].is_linked: return
    base = b.inputs['Base Color'].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sp.inputs[0])
    ay = _math(nt, 'ABSOLUTE', sp.outputs['Y'])
    wob = _math(nt, 'MULTIPLY', _noise(nt, 0.6, 4, 0.6, vec=True), 0.5)                      # the edges wander
    ayw = _math(nt, 'ADD', ay, wob)
    gutter = _ramp(nt, ayw, road - 0.15, road + 0.45, 1.0, 0.5)                                # dark band against each kerb
    track = _math(nt, 'SUBTRACT', 1.0, _math(nt, 'MULTIPLY', _math(nt, 'MAXIMUM', _ramp(nt, _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', ay, 1.05)), 0.0, 0.32, 1.0, 0.0), _ramp(nt, _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', ay, 2.65)), 0.0, 0.3, 1.0, 0.0)), -0.16))
    oil = _ramp(nt, _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', sp.outputs['Y'], 1.85)), 0.0, 0.35, 0.72, 1.0)   # the middle of the westbound lane
    f = _math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', gutter, track), oil)
    inx = _math(nt, 'MULTIPLY', _ramp(nt, sp.outputs['X'], -0.5, 0.5, 0.0, 1.0, False), _ramp(nt, sp.outputs['X'], length - 0.5, length + 0.5, 1.0, 0.0, False))
    fac = _math(nt, 'ADD', 1.0, _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', f, 1.0), inx))   # only between the corners
    col = _mix(nt, 'MULTIPLY', base, _comb(nt, fac)); nt.links.new(col, b.inputs['Base Color'])
    # leaves and litter in the gutter: speckle that only lives in the dark band
    sp2 = _noise(nt, 14.0, 2, 0.5, vec=True); leaf = _math(nt, 'MULTIPLY', _ramp(nt, sp2, 0.62, 0.7, 0.0, 1.0), _math(nt, 'SUBTRACT', 1.0, gutter))
    leaf = _math(nt, 'MULTIPLY', leaf, inx)
    col2 = _mix(nt, 'MIX', col, (0.09, 0.05, 0.02), leaf); nt.links.new(col2, b.inputs['Base Color'])

def blade(text_fn, F, u, v, z, words, plate_m, ink_m, size=0.13):
    """A street name sign: a green blade with white letters on both faces."""
    w = len(words) * size * 0.62 + 0.3
    F.box(plate_m, u - w / 2, v - 0.012, z - 0.11, u + w / 2, v + 0.012, z + 0.11)
    text_fn(words, F, u, v + 0.014, z, size, ink_m, extrude=0.002)
    G = F.at(u, v, 180); text_fn(words, G, 0, 0.014, z, size, ink_m, extrude=0.002)
