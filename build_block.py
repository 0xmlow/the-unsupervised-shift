"""
THE UNSUPERVISED SHIFT  ·  experiment 53 of 100  ·  build_block.py
Builds West 317th Street in Blender from block.py and renders it at any minute of its night.

  Blender --background --factory-startup --python build_block.py -- --t 03:17 --cam canyon --res 810x1012 --samples 48 --out stills/x.png
  ... -- --film 0 480 1 --out film/frames --res 810x1012 --samples 32        one frame per block minute
  ... -- --t 04:10 --save block.blend                                         also save the scene

Cameras: canyon (street level, looking east), axo (the whole block from above), elevN, elevS (flat elevations).
Nothing is loaded from disk except block.py. Every surface is a procedural material or a flat colour.
"""
import bpy, bmesh, sys, os, math, random, argparse, time
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import block as K
import realism as R        # photographed surfaces, weather on the walls, CC0 props (20:30; REALISM=0 turns it off)

ap = argparse.ArgumentParser()
ap.add_argument('--t', default='03:17'); ap.add_argument('--cam', default='canyon'); ap.add_argument('--res', default='810x1012')
ap.add_argument('--samples', type=int, default=48); ap.add_argument('--out', default=os.path.join(HERE, 'stills', 'test.png'))
ap.add_argument('--film', nargs=3, type=float, default=None); ap.add_argument('--save', default=None); ap.add_argument('--cpu', action='store_true')
ap.add_argument('--exposure', type=float, default=None); ap.add_argument('--norender', action='store_true')
A = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
T0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
rnd = random.Random(K.SEED)
FAC, L, DEPTH, SK = K.FAC, K.L, 14.0, 0.22
CTRL = {}          # name -> (socket) for values that change with the hour

# ------------------------------------------------------------------ materials
MATS = {}
def mat(name, color=(0.5, 0.5, 0.5), rough=0.6, metal=0.0, emit=None, es=1.0, alpha=None):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit is not None: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    if alpha is not None: b.inputs['Alpha'].default_value = alpha
    MATS[name] = m; return m
def bsdf(m): return m.node_tree.nodes['Principled BSDF']
def ctrl_emit(name, m): CTRL[name] = bsdf(m).inputs['Emission Strength']

def brickify(m, c1, c2, mortar, scale=5.0):
    nt = m.node_tree; b = bsdf(m)
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); addn = nt.nodes.new('ShaderNodeMath'); comb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs[0]); nt.links.new(sep.outputs['X'], addn.inputs[0]); nt.links.new(sep.outputs['Y'], addn.inputs[1])
    nt.links.new(addn.outputs[0], comb.inputs['X']); nt.links.new(sep.outputs['Z'], comb.inputs['Y'])
    br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = scale; br.inputs['Brick Width'].default_value = 1.0; br.inputs['Row Height'].default_value = 0.34
    br.inputs['Mortar Size'].default_value = 0.022; br.inputs['Color1'].default_value = (*c1, 1); br.inputs['Color2'].default_value = (*c2, 1); br.inputs['Mortar'].default_value = (*mortar, 1)
    nt.links.new(comb.outputs[0], br.inputs['Vector'])
    grime = nt.nodes.new('ShaderNodeTexNoise'); grime.inputs['Scale'].default_value = 0.35; grime.inputs['Detail'].default_value = 7; grime.inputs['Roughness'].default_value = 0.65
    nt.links.new(geo.outputs['Position'], grime.inputs['Vector'])
    gr = nt.nodes.new('ShaderNodeMapRange'); gr.inputs['From Min'].default_value = 0.3; gr.inputs['From Max'].default_value = 0.7; gr.inputs['To Min'].default_value = 0.45; gr.inputs['To Max'].default_value = 1.0
    nt.links.new(grime.outputs['Fac'], gr.inputs['Value'])
    dark = nt.nodes.new('ShaderNodeMixRGB'); dark.blend_type = 'MULTIPLY'; dark.inputs['Fac'].default_value = 1.0
    nt.links.new(br.outputs['Color'], dark.inputs['Color1']); nt.links.new(gr.outputs['Result'], dark.inputs['Color2']); nt.links.new(dark.outputs['Color'], b.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5; bp.inputs['Distance'].default_value = 0.01; bp.invert = True
    nt.links.new(br.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
def stoneify(m, col, scale=0.8):
    nt = m.node_tree; b = bsdf(m); geo = nt.nodes.new('ShaderNodeNewGeometry')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = 0.7
    nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.25; mr.inputs['From Max'].default_value = 0.75; mr.inputs['To Min'].default_value = 0.55; mr.inputs['To Max'].default_value = 1.1
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1.0; mx.inputs['Color1'].default_value = (*col, 1)
    nt.links.new(mr.outputs['Result'], mx.inputs['Color2']); nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])

WET = []   # roughness map-range nodes that follow the rain
def wetify(m, dry=0.75, scale=0.55, bump=0.12):
    """Asphalt and paving: a noise decides where the puddles are, CTRL['wet'] decides how much water there is."""
    nt = m.node_tree; b = bsdf(m); geo = nt.nodes.new('ShaderNodeNewGeometry')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 9; nz.inputs['Roughness'].default_value = 0.62; nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    wetv = nt.nodes.new('ShaderNodeValue'); wetv.outputs[0].default_value = 0.0; WET.append(wetv.outputs[0])
    # puddle mask: threshold falls as wetness rises
    thr = nt.nodes.new('ShaderNodeMapRange'); thr.inputs['From Min'].default_value = 0; thr.inputs['From Max'].default_value = 1; thr.inputs['To Min'].default_value = 0.84 if R.ON else 0.80; thr.inputs['To Max'].default_value = 0.62 if R.ON else 0.56   # 05:57: fewer puddles out in the lanes (Astra, third pass)
    nt.links.new(wetv.outputs[0], thr.inputs['Value'])
    sub = nt.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; nt.links.new(nz.outputs['Fac'], sub.inputs[0]); nt.links.new(thr.outputs['Result'], sub.inputs[1])
    # 04:22 Nov 18, from Astra's critique: the road was one even coat of gloss. A large mask (patches 5 to 15 m) dries
    # some stretches before others, and water collects in the last metre before each kerb.
    lg = nt.nodes.new('ShaderNodeTexNoise'); lg.inputs['Scale'].default_value = scale * 0.12; lg.inputs['Detail'].default_value = 2; nt.links.new(geo.outputs['Position'], lg.inputs['Vector'])
    L_ = nt.nodes.new('ShaderNodeMapRange'); L_.inputs['From Min'].default_value = 0.38; L_.inputs['From Max'].default_value = 0.62; L_.interpolation_type = 'SMOOTHSTEP'; nt.links.new(lg.outputs['Fac'], L_.inputs['Value'])
    sxyz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sxyz.inputs[0])
    ay = nt.nodes.new('ShaderNodeMath'); ay.operation = 'ABSOLUTE'; nt.links.new(sxyz.outputs['Y'], ay.inputs[0])
    gu = nt.nodes.new('ShaderNodeMapRange'); gu.inputs['From Min'].default_value = K.ROAD - 1.0; gu.inputs['From Max'].default_value = K.ROAD - 0.15; gu.interpolation_type = 'SMOOTHSTEP'; nt.links.new(ay.outputs[0], gu.inputs['Value'])
    gu2 = nt.nodes.new('ShaderNodeMapRange'); gu2.inputs['From Min'].default_value = K.ROAD + 0.05; gu2.inputs['From Max'].default_value = K.ROAD + 0.25; gu2.inputs['To Min'].default_value = 1.0; gu2.inputs['To Max'].default_value = 0.0; nt.links.new(ay.outputs[0], gu2.inputs['Value'])
    gm = nt.nodes.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; nt.links.new(gu.outputs['Result'], gm.inputs[0]); nt.links.new(gu2.outputs['Result'], gm.inputs[1])
    bias = nt.nodes.new('ShaderNodeMath'); bias.operation = 'MULTIPLY_ADD'; nt.links.new(L_.outputs['Result'], bias.inputs[0]); bias.inputs[1].default_value = 0.12; bias.inputs[2].default_value = -0.07
    bias2 = nt.nodes.new('ShaderNodeMath'); bias2.operation = 'MULTIPLY_ADD'; nt.links.new(gm.outputs[0], bias2.inputs[0]); bias2.inputs[1].default_value = 0.17; nt.links.new(bias.outputs[0], bias2.inputs[2])
    sub2 = nt.nodes.new('ShaderNodeMath'); sub2.operation = 'ADD'; nt.links.new(sub.outputs[0], sub2.inputs[0]); nt.links.new(bias2.outputs[0], sub2.inputs[1]); sub = sub2
    pud = nt.nodes.new('ShaderNodeMapRange'); pud.inputs['From Min'].default_value = 0.0; pud.inputs['From Max'].default_value = 0.16; pud.interpolation_type = 'SMOOTHSTEP'; nt.links.new(sub.outputs[0], pud.inputs['Value'])
    # overall damp sheen
    dT = nt.nodes.new('ShaderNodeMapRange'); dT.inputs['To Min'].default_value = 0.55; dT.inputs['To Max'].default_value = 0.35; nt.links.new(L_.outputs['Result'], dT.inputs['Value'])   # damp 0.24 to 0.5, by patch
    damp = nt.nodes.new('ShaderNodeMapRange'); damp.inputs['From Min'].default_value = 0; damp.inputs['From Max'].default_value = 1; damp.inputs['To Min'].default_value = dry; nt.links.new(dT.outputs['Result'], damp.inputs['To Max'])
    nt.links.new(wetv.outputs[0], damp.inputs['Value'])
    mix = nt.nodes.new('ShaderNodeMapRange'); mix.inputs['From Min'].default_value = 0; mix.inputs['From Max'].default_value = 1; mix.inputs['To Max'].default_value = 0.05
    nt.links.new(pud.outputs['Result'], mix.inputs['Value']); nt.links.new(damp.outputs['Result'], mix.inputs['To Min']); nt.links.new(mix.outputs['Result'], b.inputs['Roughness'])
    fine = nt.nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 55; nt.links.new(geo.outputs['Position'], fine.inputs['Vector'])
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(pud.outputs['Result'], inv.inputs[1])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; nt.links.new(fine.outputs['Fac'], mul.inputs[0]); nt.links.new(inv.outputs[0], mul.inputs[1])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.02
    nt.links.new(mul.outputs[0], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return pud

# ------------------------------------------------------------------ geometry accumulator
class Geo:
    """Collects boxes, quads and tubes per material, then writes one mesh per material."""
    def __init__(s): s.v = {}; s.f = {}
    def _b(s, m):
        k = m.name
        if k not in s.v: s.v[k] = []; s.f[k] = []
        return s.v[k], s.f[k]
    def box(s, m, x0, y0, z0, x1, y1, z1):
        vs, fs = s._b(m); n = len(vs)
        vs += [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        fs += [(n + a, n + b, n + c, n + d) for a, b, c, d in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
    def quad(s, m, p0, p1, p2, p3):
        vs, fs = s._b(m); n = len(vs); vs += [p0, p1, p2, p3]; fs.append((n, n + 1, n + 2, n + 3))
    def hexa(s, m, pts):
        """8 points: bottom ring 0..3, top ring 4..7 (same winding)."""
        vs, fs = s._b(m); n = len(vs); vs += list(pts)
        fs += [(n + a, n + b, n + c, n + d) for a, b, c, d in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    def tube(s, m, p0, p1, r0, r1=None, n=6, caps=True):
        """A cylinder or cone between two points."""
        r1 = r0 if r1 is None else r1; p0 = Vector(p0); p1 = Vector(p1); ax = p1 - p0
        if ax.length < 1e-6: return
        ax.normalize(); a = ax.orthogonal().normalized(); b = ax.cross(a)
        vs, fs = s._b(m); k = len(vs)
        for i in range(n):
            th = 2 * math.pi * i / n; d = a * math.cos(th) + b * math.sin(th)
            vs.append(tuple(p0 + d * r0)); vs.append(tuple(p1 + d * r1))
        for i in range(n):
            i2 = (i + 1) % n; fs.append((k + 2 * i, k + 2 * i2, k + 2 * i2 + 1, k + 2 * i + 1))
        if caps:
            fs.append(tuple(k + 2 * i for i in range(n))); fs.append(tuple(k + 2 * i + 1 for i in range(n)))
    def cyl(s, m, x, y, z0, z1, r, n=12, r1=None): s.tube(m, (x, y, z0), (x, y, z1), r, r1, n)
    def blob(s, m, x, y, z, rx, ry, rz, n=8, rings=5, jit=0.0, rr=None):
        vs, fs = s._b(m); k = len(vs); rr = rr or rnd
        for i in range(rings + 1):
            ph = math.pi * i / rings
            for q in range(n):
                th = 2 * math.pi * q / n; jj = 1 + (rr.uniform(-jit, jit) if jit else 0)
                vs.append((x + rx * jj * math.sin(ph) * math.cos(th), y + ry * jj * math.sin(ph) * math.sin(th), z + rz * math.cos(ph)))
        for i in range(rings):
            for q in range(n):
                q2 = (q + 1) % n; fs.append((k + i * n + q, k + i * n + q2, k + (i + 1) * n + q2, k + (i + 1) * n + q))
    def beam(s, m, p0, p1, wdt, th):
        """A rectangular bar from p0 to p1, wdt wide (horizontal), th thick."""
        p0 = Vector(p0); p1 = Vector(p1); ax = (p1 - p0).normalized(); side = ax.cross(Vector((0, 0, 1)))
        if side.length < 1e-6: side = Vector((1, 0, 0))
        side.normalize(); up = side.cross(ax).normalized(); a = side * wdt / 2; b = up * th / 2
        s.hexa(m, [tuple(p0 - a - b), tuple(p0 + a - b), tuple(p0 + a + b), tuple(p0 - a + b), tuple(p1 - a - b), tuple(p1 + a - b), tuple(p1 + a + b), tuple(p1 - a + b)])
    def mesh(s, m, verts, faces):
        """Append a whole mesh: verts a list of (x, y, z), faces tuples of indices into it."""
        vs, fs = s._b(m); n = len(vs); vs += verts; fs += [tuple(i + n for i in f) for f in faces]
    def merge(s, other, loc=(0, 0, 0), rotz=0.0, scale=1.0):
        c, sn = math.cos(rotz), math.sin(rotz)
        for k in other.v:
            if k not in s.v: s.v[k] = []; s.f[k] = []
            n = len(s.v[k]); s.v[k] += [(loc[0] + (x * c - y * sn) * scale, loc[1] + (x * sn + y * c) * scale, loc[2] + z * scale) for x, y, z in other.v[k]]
            s.f[k] += [tuple(i + n for i in f) for f in other.f[k]]
    def flush(s, prefix, parent=None, smooth=()):
        objs = []
        for k in s.v:
            me = bpy.data.meshes.new(prefix + ' ' + k); me.from_pydata(s.v[k], [], s.f[k])
            bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
            me.materials.append(bpy.data.materials[k])
            if k in smooth:
                for p in me.polygons: p.use_smooth = True
            o = bpy.data.objects.new(prefix + ' ' + k, me); scene.collection.objects.link(o)
            if parent is not None: o.parent = parent
            objs.append(o)
        s.v = {}; s.f = {}; return objs
G = Geo()

class Frame:
    """A wall. u runs along it left to right as you face it, v comes out of it toward you, z is up."""
    def __init__(s, ox, oy, ux, uy, vx, vy, length): s.o = (ox, oy); s.u = (ux, uy); s.v = (vx, vy); s.len = length
    def p(s, u, v, z): return (s.o[0] + s.u[0] * u + s.v[0] * v, s.o[1] + s.u[1] * u + s.v[1] * v, z)
    def box(s, m, u0, v0, z0, u1, v1, z1, g=None):
        a = s.p(u0, v0, z0); b = s.p(u1, v1, z1); (g or G).box(m, min(a[0], b[0]), min(a[1], b[1]), min(z0, z1), max(a[0], b[0]), max(a[1], b[1]), max(z0, z1))
    def quad(s, m, u0, z0, u1, z1, v, g=None): (g or G).quad(m, s.p(u0, v, z0), s.p(u1, v, z0), s.p(u1, v, z1), s.p(u0, v, z1))
    def rotz(s): return math.atan2(s.u[1], s.u[0])       # rotation that makes local +x run along u
    def at(s, u, v, deg, length=1.0):
        """A wall standing inside this one's space: origin at (u, v), turned deg degrees. 0 faces the same way, 90 faces -u, -90 faces +u."""
        a = math.radians(deg); c, sn = math.cos(a), math.sin(a); o = s.p(u, v, 0)
        return Frame(o[0], o[1], c * s.u[0] + sn * s.v[0], c * s.u[1] + sn * s.v[1], -sn * s.u[0] + c * s.v[0], -sn * s.u[1] + c * s.v[1], length)
    def heading(s, du, dv): return math.atan2(s.u[1] * du + s.v[1] * dv, s.u[0] * du + s.v[0] * dv)
def street_frame(b):
    if b['side'] == 'N': return Frame(b['x0'], FAC, 1, 0, 0, -1, b['w'])
    return Frame(b['x0'] + b['w'], -FAC, -1, 0, 0, 1, b['w'])
def avenue_frame(b):
    """The side wall of a corner building on the avenue, or None."""
    if b['x0'] == 0:
        return Frame(0, FAC + DEPTH, 0, -1, -1, 0, DEPTH) if b['side'] == 'N' else Frame(0, -FAC, 0, -1, -1, 0, DEPTH)
    if b['x0'] + b['w'] == L:
        return Frame(L, FAC, 0, 1, 1, 0, DEPTH) if b['side'] == 'N' else Frame(L, -FAC - DEPTH, 0, 1, 1, 0, DEPTH)
    return None

# ------------------------------------------------------------------ text
FONT = None
for fp in ('/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf', '/System/Library/Fonts/Supplemental/Impact.ttf', '/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf'):
    if os.path.exists(fp):
        try: FONT = bpy.data.fonts.load(fp); break
        except Exception as ex: print('font', fp, ex)
def text(body, F, u, v, z, size, m, align='CENTER', extrude=0.01, parent=None, spacing=1.0):
    cu = bpy.data.curves.new('txt ' + body[:12], 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'; cu.space_character = spacing
    if FONT: cu.font = FONT
    cu.materials.append(m); o = bpy.data.objects.new('txt ' + body[:12], cu); scene.collection.objects.link(o)
    o.location = F.p(u, v, z); o.rotation_euler = (math.radians(90), 0, F.rotz())
    if parent is not None: o.parent = parent
    return o

# ------------------------------------------------------------------ shared materials
ASPH = mat('Asphalt', (0.022, 0.022, 0.025), 0.75); wetify(ASPH, dry=0.8, scale=1.5)
CONC = mat('Sidewalk', (0.30, 0.295, 0.28), 0.85); wetify(CONC, dry=0.9, scale=0.9, bump=0.05)
KERB = mat('Kerb', (0.36, 0.36, 0.35), 0.7)
PAINT = mat('Road paint', (0.75, 0.75, 0.72), 0.6)
TAR = mat('Roof tar', (0.035, 0.035, 0.038), 0.9)
IRON = mat('Iron', (0.012, 0.012, 0.014), 0.55, 0.6)
STEEL = mat('Galvanised', (0.32, 0.33, 0.34), 0.45, 0.8)
GATE = mat('Roll gate', (0.20, 0.205, 0.21), 0.5, 0.7)
SASH = mat('Sash', (0.50, 0.49, 0.46), 0.6)
DOOR = mat('Door', (0.07, 0.035, 0.025), 0.4)
GLASS = mat('Shop glass', (0.0, 0.0, 0.0), 0.03, alpha=0.14)
DARKGLASS = mat('Dark glass', (0.01, 0.012, 0.016), 0.04)
CARGLASS = mat('Car glass', (0.28, 0.31, 0.32), 0.02)
if R.ON:
    _b = CARGLASS.node_tree.nodes['Principled BSDF']; _b.inputs['Transmission Weight'].default_value = 0.92; _b.inputs['IOR'].default_value = 1.45
CABIN = mat('car cabin', (0.018, 0.018, 0.02), 0.8); SEAT = mat('car seat', (0.035, 0.032, 0.03), 0.75)
INWALL = mat('Inside wall', (0.72, 0.70, 0.64), 0.8)
INFLOOR = mat('Inside floor', (0.42, 0.40, 0.36), 0.35)
WOOD = mat('Wood', (0.22, 0.13, 0.07), 0.6)
RUBBER = mat('Rubber', (0.01, 0.01, 0.01), 0.8)
BAG = mat('Trash bag', (0.006, 0.006, 0.007), 0.28)
BARK = mat('Bark', (0.045, 0.038, 0.032), 0.9)
SOIL = mat('Soil', (0.05, 0.04, 0.03), 0.95)
SKIN = [mat('Skin %d' % i, c, 0.6) for i, c in enumerate([(0.55, 0.36, 0.26), (0.30, 0.18, 0.12), (0.72, 0.52, 0.40), (0.16, 0.10, 0.07), (0.62, 0.44, 0.30)])]
def colmat(prefix, c, rough=0.55, metal=0.0): return mat('%s %.2f %.2f %.2f' % (prefix, c[0], c[1], c[2]), c, rough, metal)
# realism: the street and its hardware get photographed surfaces (Poly Haven CC0, Firefly), metres in world space
R.surface(ASPH, 'ff_asphalt' if os.path.exists(os.path.join(R.FF, 'ff_asphalt.jpg')) else 'asphalt_02', 4.0, tint=(0.030, 0.030, 0.033), bump=0.25, keep_rough=True, firefly=os.path.exists(os.path.join(R.FF, 'ff_asphalt.jpg')))
R.surface(CONC, 'concrete_pavement_02', 6.0, tint=(0.25, 0.245, 0.235), bump=0.6, keep_rough=True)
R.surface(KERB, 'dirty_concrete', 1.4, tint=(0.17, 0.17, 0.165), bump=0.5, bevel=0.02)
R.surface(PAINT, 'concrete_pavement_02', 2.2, tint=(0.62, 0.62, 0.59), bump=0.12)       # road paint (00:15: was dirty_concrete, which read as grey speckle)
def worn_paint(m):
    """05:57 (Astra, third pass: the crosswalk looked freshly painted and varnished): matte thermoplastic, worn through to
    the asphalt in the wheel paths and in patches, and only glossy while the street is wet."""
    if not R.ON: return
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; geo = nt.nodes.new('ShaderNodeNewGeometry'); sx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sx.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; nz.inputs['Detail'].default_value = 10; nz.inputs['Roughness'].default_value = 0.7; nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    pm = nt.nodes.new('ShaderNodeMapRange'); pm.inputs['From Min'].default_value = 0.52; pm.inputs['From Max'].default_value = 0.6; nt.links.new(nz.outputs['Fac'], pm.inputs['Value'])
    ay = nt.nodes.new('ShaderNodeMath'); ay.operation = 'ABSOLUTE'; nt.links.new(sx.outputs['Y'], ay.inputs[0])
    tracks = []
    for yc in (1.05, 2.65):
        d = nt.nodes.new('ShaderNodeMath'); d.operation = 'SUBTRACT'; nt.links.new(ay.outputs[0], d.inputs[0]); d.inputs[1].default_value = yc
        da = nt.nodes.new('ShaderNodeMath'); da.operation = 'ABSOLUTE'; nt.links.new(d.outputs[0], da.inputs[0])
        tr = nt.nodes.new('ShaderNodeMapRange'); tr.inputs['From Min'].default_value = 0.0; tr.inputs['From Max'].default_value = 0.35; tr.inputs['To Min'].default_value = 0.55; tr.inputs['To Max'].default_value = 0.0; nt.links.new(da.outputs[0], tr.inputs['Value']); tracks.append(tr)
    t2 = nt.nodes.new('ShaderNodeMath'); t2.operation = 'MAXIMUM'; nt.links.new(tracks[0].outputs[0], t2.inputs[0]); nt.links.new(tracks[1].outputs[0], t2.inputs[1])
    wn = nt.nodes.new('ShaderNodeMath'); wn.operation = 'MULTIPLY'; nt.links.new(t2.outputs[0], wn.inputs[0]); nt.links.new(nz.outputs['Fac'], wn.inputs[1])
    worn = nt.nodes.new('ShaderNodeMath'); worn.operation = 'MAXIMUM'; worn.use_clamp = True; nt.links.new(pm.outputs['Result'], worn.inputs[0]); nt.links.new(wn.outputs[0], worn.inputs[1])
    base = b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].is_linked else None
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.inputs['Color2'].default_value = (0.03, 0.03, 0.033, 1); nt.links.new(worn.outputs[0], mx.inputs['Fac'])
    if base is not None: nt.links.new(base, mx.inputs['Color1'])
    else: mx.inputs['Color1'].default_value = b.inputs['Base Color'].default_value
    nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
    wv = nt.nodes.new('ShaderNodeValue'); WET.append(wv.outputs[0]); rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.8; rr.inputs['To Max'].default_value = 0.3
    nt.links.new(wv.outputs[0], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    if b.inputs['Normal'].is_linked:
        bp = b.inputs['Normal'].links[0].from_node
        if bp.type == 'BUMP': bp.inputs['Strength'].default_value = 0.05
worn_paint(PAINT)
R.street_wear(ASPH, K.ROAD, L)
R.surface(TAR, 'worn_asphalt', 2.5, tint=(0.035, 0.035, 0.038), bump=0.3)
R.surface(GATE, 'painted_metal_shutter', 1.6, tint=(0.20, 0.205, 0.21), bump=0.8, rough_mul=0.9)
# bevels on SASH, STEEL, DOOR and IRON were tried 20:50 and dropped: thousands of fire escape bars made a still take 209 s

# window panes: one mesh, emission driven by a per-corner colour attribute rewritten for every minute
PANE = bpy.data.materials.new('Pane'); PANE.use_nodes = True
def _pane():
    nt = PANE.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.012, 0.014, 0.018, 1); b.inputs['Roughness'].default_value = 0.06
    glow = nt.nodes.new('ShaderNodeAttribute'); glow.attribute_name = 'glow'; wuv = nt.nodes.new('ShaderNodeAttribute'); wuv.attribute_name = 'wuv'
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(wuv.outputs['Vector'], sep.inputs[0])
    # curtains: a soft vertical pleat pattern, different per window (seed in the blue channel)
    wave = nt.nodes.new('ShaderNodeMath'); wave.operation = 'MULTIPLY_ADD'; wave.inputs[1].default_value = 38.0; nt.links.new(sep.outputs['X'], wave.inputs[0]); nt.links.new(sep.outputs['Z'], wave.inputs[2])
    sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'; nt.links.new(wave.outputs[0], sn.inputs[0])
    pleat = nt.nodes.new('ShaderNodeMapRange'); pleat.inputs['From Min'].default_value = -1; pleat.inputs['From Max'].default_value = 1; pleat.inputs['To Min'].default_value = 0.62; pleat.inputs['To Max'].default_value = 1.0
    nt.links.new(sn.outputs[0], pleat.inputs['Value'])
    # brighter toward the top of the window where the ceiling is, darker at the sill
    vg = nt.nodes.new('ShaderNodeMapRange'); vg.inputs['From Min'].default_value = 0; vg.inputs['From Max'].default_value = 1; vg.inputs['To Min'].default_value = 0.45; vg.inputs['To Max'].default_value = 1.15
    nt.links.new(sep.outputs['Y'], vg.inputs['Value'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(pleat.outputs['Result'], m1.inputs[0]); nt.links.new(vg.outputs['Result'], m1.inputs[1])
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1.0
    nt.links.new(glow.outputs['Color'], mx.inputs['Color1']); nt.links.new(m1.outputs[0], mx.inputs['Color2'])
    nt.links.new(mx.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.0
    if R.ON:
        dim = nt.nodes.new('ShaderNodeMath'); dim.operation = 'MULTIPLY'; dim.inputs[1].default_value = 0.07; nt.links.new(m1.outputs[0], dim.inputs[0])
        tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1.0; tint.inputs[7].default_value = (0.9, 0.82, 0.7, 1)
        nt.links.new(dim.outputs[0], tint.inputs[6]); nt.links.new(tint.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.12
_pane()
ACM = mat('AC unit', (0.42, 0.42, 0.40), 0.6); SHADE = mat('Silhouette', (0.004, 0.004, 0.005), 0.9); SILH_T = []; INSIDE = []
SILH = {'The Insomniac': 'kitchen', 'The Writer': 'living', 'The Student': 'bedroom', 'The Old Couple': 'kitchen', 'The Bartender': 'living', 'The New Parents': 'bedroom', 'The Early Riser': 'kitchen', 'The Saxophonist': 'living', 'The Night Shift': 'kitchen', 'The Nurse': 'kitchen', 'The Baker': 'kitchen', 'The Cab Driver': 'kitchen'}
PANES = []     # (window dict or pseudo window, static glow or None)
PANE_V = []; PANE_F = []; PANE_UV = []
def pane(F, u0, z0, u1, z1, v, w, static=None):
    n = len(PANE_V); PANE_V.extend([F.p(u0, v, z0), F.p(u1, v, z0), F.p(u1, v, z1), F.p(u0, v, z1)]); PANE_F.append((n, n + 1, n + 2, n + 3))
    sd = rnd.uniform(0, 6.28); PANE_UV.extend([(0, 0, sd, 1), (1, 0, sd, 1), (1, 1, sd, 1), (0, 1, sd, 1)]); PANES.append((w, static))

# 04:59 Nov 18, MLow: "fix the facades too" (Astra, both passes: the street looks assembled from one kit). Every
# building now draws its own sills, lintels, sash, frame colour, recess depth and cornice from its id; a fifth of its
# windows are mismatched replacements; and a history layer adds belt courses, a downspout, cables and repointed patches.
FSTY = {}
FRAMES = None
def fstyle(bid):
    global FRAMES
    if FRAMES is None:
        FRAMES = dict(grey=SASH, white=mat('sash white', (0.80, 0.80, 0.77), 0.45), bronze=mat('sash bronze', (0.05, 0.04, 0.03), 0.35, 0.6),
                      green=mat('sash green', (0.04, 0.13, 0.08), 0.5), black=mat('sash black', (0.015, 0.015, 0.017), 0.4), vinyl=mat('sash vinyl', (0.86, 0.85, 0.80), 0.3))
    if bid in FSTY: return FSTY[bid]
    r = random.Random(sum(ord(c) * (i + 7) for i, c in enumerate(bid or 'x')) * 31 + K.SEED)
    st = dict(sill=r.choice(['stone', 'stone', 'brick', 'deep']), lintel=r.choice(['flat', 'arch', 'hood', 'key', 'arch']),
              sash=r.choice(['11', '66', '22', '11']), frame=FRAMES[r.choice(['grey', 'white', 'bronze', 'green', 'black'])],
              pv=r.choice([0.03, 0.03, 0.08]), cornice=r.choice(['bracket', 'metal', 'parapet', 'metal']),
              metal=r.choice([(0.05, 0.08, 0.06), (0.55, 0.52, 0.45), (0.035, 0.035, 0.04), (0.32, 0.13, 0.08), (0.42, 0.44, 0.45)]),
              belt=r.random() < 0.55, pipe=r.random() < 0.8, cables=r.random() < 0.65, patches=r.randint(1, 4), seed=r.random())
    FSTY[bid] = st; return st
def window(F, w, trim, sash=SASH, static=None):
    """One window: the pane sits at the back of a reveal, with a sill, a lintel and a sash, each in its building's style."""
    u0, u1, z0, z1 = w['u'] - w['w'] / 2, w['u'] + w['w'] / 2, w['z'], w['z'] + w['h']
    st = fstyle(w.get('b')) if (R.ON and w.get('b')) else None
    if st is None:
        pane(F, u0, z0, u1, z1, 0.03, w, static)
        F.box(trim, u0 - 0.14, SK, z0 - 0.13, u1 + 0.14, SK + 0.10, z0)
        F.box(trim, u0 - 0.10, SK, z1, u1 + 0.10, SK + 0.05, z1 + 0.24)
        for a, b_ in ((u0, u0 + 0.05), (u1 - 0.05, u1)): F.box(sash, a, 0.03, z0, b_, 0.09, z1)
        for a, b_ in ((z0, z0 + 0.06), (z1 - 0.06, z1), ((z0 + z1) / 2 - 0.03, (z0 + z1) / 2 + 0.03)): F.box(sash, u0, 0.03, a, u1, 0.09, b_)
    else:
        pv = st['pv']; wall = bmats(K.B[w['b']])[0]; mid = (u0 + u1) / 2
        rw = random.Random(int(w['u'] * 100) * 7 + int(w['z'] * 100) + int(st['seed'] * 1e6))
        repl = rw.random() < 0.2; fm = FRAMES['vinyl'] if repl else st['frame']; ft = 0.075 if repl else 0.05
        pane(F, u0, z0, u1, z1, pv, w, static)
        if st['sill'] == 'brick': F.box(wall, u0 - 0.07, SK, z0 - 0.11, u1 + 0.07, SK + 0.05, z0)                    # a rowlock of brick on edge
        elif st['sill'] == 'deep': F.box(trim, u0 - 0.17, SK, z0 - 0.16, u1 + 0.17, SK + 0.13, z0); F.box(trim, u0 - 0.12, SK, z0 - 0.26, u1 + 0.12, SK + 0.06, z0 - 0.16)
        else: F.box(trim, u0 - 0.14, SK, z0 - 0.13, u1 + 0.14, SK + 0.10, z0)
        if st['lintel'] == 'arch':          # a segmental arch of brick soldiers, standing a little proud of the wall
            n = 11
            for k in range(n):
                a_ = u0 - 0.08 + (u1 - u0 + 0.16) * k / n; b2 = a_ + (u1 - u0 + 0.16) / n - 0.008; x_ = (k + 0.5) / n * 2 - 1; zr = z1 + 0.02 + 0.13 * (1 - x_ * x_)
                F.box(wall, a_, SK, zr - 0.04, b2, SK + 0.025, zr + 0.2)
        elif st['lintel'] == 'hood':        # a projecting hood on two small brackets
            F.box(trim, u0 - 0.2, SK, z1 + 0.04, u1 + 0.2, SK + 0.14, z1 + 0.32); F.box(trim, u0 - 0.24, SK, z1 + 0.28, u1 + 0.24, SK + 0.18, z1 + 0.36)
            for a_ in (u0 - 0.19, u1 + 0.09): F.box(trim, a_, SK, z1 - 0.22, a_ + 0.1, SK + 0.1, z1 + 0.04)
        elif st['lintel'] == 'key':
            F.box(trim, u0 - 0.10, SK, z1, u1 + 0.10, SK + 0.05, z1 + 0.24); F.box(trim, mid - 0.09, SK, z1 - 0.02, mid + 0.09, SK + 0.09, z1 + 0.34)
        else: F.box(trim, u0 - 0.10, SK, z1, u1 + 0.10, SK + 0.05, z1 + 0.24)
        for a, b_ in ((u0, u0 + ft), (u1 - ft, u1)): F.box(fm, a, pv, z0, b_, pv + 0.06, z1)
        zm = (z0 + z1) / 2 + (0.0 if not repl else 0.08)
        for a, b_ in ((z0, z0 + ft + 0.01), (z1 - ft, z1), (zm - 0.03, zm + 0.03)): F.box(fm, u0, pv, a, u1, pv + 0.06, b_)
        if not repl and st['sash'] in ('66', '22'):      # muntins: six lights or two in each sash
            cols = 3 if st['sash'] == '66' else 2
            for half in ((z0 + ft, zm - 0.03), (zm + 0.03, z1 - ft)):
                for q in range(1, cols): uu = u0 + (u1 - u0) * q / cols; F.box(fm, uu - 0.012, pv + 0.01, half[0], uu + 0.012, pv + 0.05, half[1])
                if st['sash'] == '66': zz = (half[0] + half[1]) / 2; F.box(fm, u0, pv + 0.01, zz - 0.012, u1, pv + 0.05, zz + 0.012)
        if pv > 0.05: F.box(wall, u0, 0, z0, u1, pv, z0 + 0.001)         # the reveal floor when the window sits shallow
    if 'unit' not in w: return
    if w.get('fl', 0) >= 2 and rnd.random() < 0.13:                       # an air conditioner nobody took out for the winter
        if R.ON: R.place('exterior_aircon_unit', F.p((u0 + u1) / 2, R.AC_V, z0 + R.AC_DZ), rotz=F.rotz() + R.AC_ROT, fit=(R.AC_AXIS, min(0.95, u1 - u0)), name='ac'); F.box(IRON, u0 + 0.1, 0.0, z0 + R.AC_DZ - 0.05, u1 - 0.1, 0.62, z0 + R.AC_DZ)
        else: F.box(ACM, u0 + 0.12, 0.05, z0 + 0.06, u1 - 0.12, 0.52, z0 + 0.5); F.box(SASH, u0 + 0.16, 0.52, z0 + 0.12, u1 - 0.16, 0.53, z0 + 0.44)
    res = K.RESIDENTS.get(w['unit'])
    if res and res['who'] in SILH and SILH[res['who']] == w['room'] and w.get('i', 0) < 1000:
        g = Geo(); uu = (u0 + u1) / 2 + rnd.uniform(-0.2, 0.2); n = 2 if res['who'] in ('The Old Couple', 'The New Parents') else 1
        for q in range(n):
            ux = uu + (q - (n - 1) / 2) * 0.42; hh = rnd.uniform(0.62, 0.8) - q * 0.08
            if R.ON:      # 04:21 Nov 18: Astra read the box-and-ball shadows as placeholders. A real outline, squashed onto the blind.
                hb = 1.62 + 0.1 * q; top = z0 + hh + 0.255; zf = top - hb; bg = Geo()
                body_geo(bg, ('f' if (q + len(INSIDE)) % 2 else 'm') + '_phone_short_hair', hb, 1.0, {k_: SHADE for k_ in ('skin', 'hair', 'coat', 'legs', 'eye')}, flat=0.05, zmin=(z0 + 0.06) - zf)   # 04:30: an arm up, not a cut-out
                g.merge(bg, F.p(ux, 0.047, zf), F.heading(0, 1))
            else:
                F.box(SHADE, ux - 0.2, 0.04, z0 + 0.06, ux + 0.2, 0.055, z0 + hh, g); c = F.p(ux, 0.047, z0 + hh + 0.13); g.blob(SHADE, c[0], c[1], c[2], 0.105, 0.02 if abs(F.u[0]) > 0.5 else 0.105, 0.125, 8, 5)
            if abs(F.u[0]) < 0.5: pass
        INSIDE.append((g.flush('silhouette %s' % w['unit']), min(a for a, b_, k in res['sched'][w['room']]), max(b_ for a, b_, k in res['sched'][w['room']])))
        SILH_T.append((g, w))

def skin(F, wall, ws, z_from, z_to, trim):
    """The outer 22 cm of a wall, built around its windows so every window is a real recess."""
    rows = {}
    for w in ws: rows.setdefault(round(w['z'], 2), []).append(w)
    z = z_from
    for zs in sorted(rows):
        row = sorted(rows[zs], key=lambda w: w['u']); top = max(w['z'] + w['h'] for w in row)
        F.box(wall, 0, 0, z, F.len, SK, zs)
        u = 0.0
        for w in row:
            F.box(wall, u, 0, zs, w['u'] - w['w'] / 2, SK, top)
            if w['z'] + w['h'] < top: F.box(wall, w['u'] - w['w'] / 2, 0, w['z'] + w['h'], w['u'] + w['w'] / 2, SK, top)
            u = w['u'] + w['w'] / 2; window(F, w, trim, static=w.get('static'))
        F.box(wall, u, 0, zs, F.len, SK, top); z = top
    F.box(wall, 0, 0, z, F.len, SK, z_to)

# ------------------------------------------------------------------ ground
def ground():
    G.box(TAR, -200, -160, -0.6, 300, 160, -0.31)
    G.box(ASPH, -200, -K.ROAD, -0.3, 300, K.ROAD, 0.0)                         # 317th Street, continuing both ways
    for x0, x1 in ((-22, 0), (L, L + 22)): G.box(ASPH, x0, -160, -0.3, x1, 160, 0.001)    # the two avenues
    for sgn in (1, -1):
        y0, y1 = sorted((sgn * K.ROAD, sgn * FAC))
        # sidewalk, with a hole for the subway stair on the south side at the east corner
        if sgn == -1:
            G.box(CONC, 0, y0, 0, 90.6, y1, 0.16); G.box(CONC, 94.4, y0, 0, L, y1, 0.16); G.box(CONC, 90.6, y0, 0, 94.4, -8.0, 0.16); G.box(CONC, 90.6, -6.4, 0, 94.4, y1, 0.16)
        else: G.box(CONC, 0, y0, 0, L, y1, 0.16)
        G.box(KERB, 0, sgn * K.ROAD - 0.08, 0, L, sgn * K.ROAD + 0.08, 0.165)
        for x0, x1 in ((-200, -22), (L + 22, 300)):                            # neighbouring blocks
            G.box(CONC, x0, y0, 0, x1, y1, 0.16); G.box(KERB, x0, sgn * K.ROAD - 0.08, 0, x1, sgn * K.ROAD + 0.08, 0.165)
        # avenue sidewalks beside the corner buildings
        for x0, x1 in ((-4, 0), (L, L + 4), (-22, -18), (L + 18, L + 22)):
            G.box(CONC, x0, sgn * K.ROAD, 0, x1, sgn * 160, 0.16)
    # crosswalks at both ends, and a stop line
    for xc in (-2.4, L + 2.4):
        for k in range(8): G.box(PAINT, xc - 1.5, -4.4 + k * 1.2, 0.0, xc + 1.5, -3.8 + k * 1.2, 0.006)
    for yc in (-K.ROAD - 2.2, K.ROAD + 2.2):
        for xa in (-20, L + 2):
            for k in range(15): G.box(PAINT, xa + 0.3 + k * 1.2, yc - 1.5, 0.0, xa + 0.9 + k * 1.2, yc + 1.5, 0.006)
    G.box(PAINT, 0.6, -K.ROAD + 0.3, 0.0, 0.9, K.ROAD - 0.3, 0.006)
    pm = [mat('Patch %d' % i, c, 0.7) for i, c in enumerate([(0.012, 0.012, 0.014), (0.035, 0.035, 0.038), (0.018, 0.017, 0.016)])]
    for p_ in pm: wetify(p_, dry=0.7, scale=1.5)
    rr_ = random.Random(K.SEED + 4)
    for k in range(0):       # road patches removed at 18:40: they read as rectangles laid on the street
        x = rr_.uniform(-18, 110); y = rr_.uniform(-4.2, 4.2); w_ = rr_.uniform(0.8, 5.5); d_ = rr_.uniform(0.5, 1.6); G.box(pm[k % 3], x, y, 0.0, x + w_, min(4.6, y + d_), 0.0015)
    for x, y in ((6.5, -1.6), (33.0, -2.2), (84.0, 1.5)): G.cyl(MATS['Manhole'] if 'Manhole' in MATS else mat('Manhole', (0.05, 0.05, 0.052), 0.4, 0.8), x, y, 0.0, 0.012, 0.42, 20)
    for x in (22.0, 48.0, 71.0): G.cyl(mat('Manhole', (0.05, 0.05, 0.052), 0.4, 0.8), x, 0.7, 0.0, 0.012, 0.42, 20)
    if R.ON:     # 04:30 Nov 18 (Astra, second pass: a manhole read as a dark disk): a cast waffle face, a frame, a square of patched asphalt
        mh = MATS['Manhole']; nt = mh.node_tree; b = nt.nodes['Principled BSDF']; tc = nt.nodes.new('ShaderNodeTexCoord'); sx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sx.inputs[0])
        bk = nt.nodes.new('ShaderNodeTexBrick'); bk.inputs['Scale'].default_value = 14.0; bk.inputs['Mortar Size'].default_value = 0.012; bk.offset = 0.0; bk.inputs['Brick Width'].default_value = 0.5; bk.inputs['Row Height'].default_value = 0.5
        nt.links.new(tc.outputs['Object'], bk.inputs['Vector']); bp_ = nt.nodes.new('ShaderNodeBump'); bp_.inputs['Strength'].default_value = 0.6; bp_.invert = True
        nt.links.new(bk.outputs['Fac'], bp_.inputs['Height']); nt.links.new(bp_.outputs['Normal'], b.inputs['Normal']); b.inputs['Roughness'].default_value = 0.55
        fr = mat('manhole frame', (0.16, 0.15, 0.14), 0.45, 0.7); pa = mat('asphalt patch', (0.016, 0.016, 0.018), 0.88)
        for x, y in ((6.5, -1.6), (33.0, -2.2), (84.0, 1.5), (22.0, 0.7), (48.0, 0.7), (71.0, 0.7)):
            G.cyl(fr, x, y, 0.0, 0.009, 0.47, 24); G.box(pa, x - 0.8, y - 0.78, 0.0, x + 0.76, y + 0.8, 0.003)
    # avenue lane lines
    for xa in (-11, L + 11):
        for k in range(-20, 21):
            if abs(k * 8) > 9: G.box(PAINT, xa - 0.07, k * 8 - 1.5, 0.0, xa + 0.07, k * 8 + 1.5, 0.006)

# ------------------------------------------------------------------ buildings
def bmats(b):
    i = b['id']
    if ('wall ' + i) not in MATS:
        m = mat('wall ' + i, b['brick'], 0.85); H_ = K.height(b) if b['kind'] != 'garden' else 4.0
        if R.ON:
            # photographed brick or stone, tinted to this building's colour, weathered by its own height
            tid, size = {'brownstone': ('red_sandstone_wall', 2.0), 'prewar': ('yellow_brick', 2.0), 'garage': ('dirty_concrete', 2.5)}.get(b['kind'], ('red_bricks_04' if sum(map(ord, i)) % 2 else 'red_brick_03', 2.5 if sum(map(ord, i)) % 2 else 1.0))
            R.surface(m, tid, size, tint=b['brick'], bump=0.7, weather=dict(top=H_, streaks=0.8, splash=0.6, soot=0.7), offset=(sum(map(ord, i)) * 0.37, 0, 0))
            t = mat('trim ' + i, b['trim'], 0.7); R.surface(t, 'dirty_concrete', 1.2, tint=b['trim'], bump=0.4, bevel=0.015, weather=dict(top=H_, streaks=0.6, soot=0.5))
            return MATS['wall ' + i], MATS['trim ' + i]
        if b['kind'] == 'brownstone': stoneify(m, b['brick'])
        elif b['kind'] == 'garage': stoneify(m, b['brick'], 0.3)
        else:
            c = b['brick']; brickify(m, c, tuple(v * 0.72 for v in c), tuple(min(1, v * 0.9 + 0.08) for v in c))
        t = mat('trim ' + i, b['trim'], 0.7); stoneify(t, b['trim'], 2.0)
    return MATS['wall ' + i], MATS['trim ' + i]

def shell(b, F, z0):
    """Massing above z0, parapet and roof."""
    wall, trim = bmats(b); H = K.height(b); w = b['w']
    F.box(wall, 0, -DEPTH, z0, w, 0, H - 0.8)
    F.box(wall, 0, -0.3, H - 0.8, w, 0, H); F.box(wall, 0, -DEPTH, H - 0.8, w, -DEPTH + 0.3, H); F.box(wall, 0, -DEPTH, H - 0.8, 0.3, 0, H); F.box(wall, w - 0.3, -DEPTH, H - 0.8, w, 0, H)
    F.box(TAR, 0.3, -DEPTH + 0.3, H - 0.82, w - 0.3, -0.3, H - 0.78)
    return wall, trim, H

def roof_stuff(b, F, H, tank=False):
    w = b['w']; r = random.Random(K.SEED + hash(b['id']) % 1000)
    u = r.uniform(1.5, w - 3.5); F.box(bmats(b)[0], u, -9.5, H - 0.8, u + 2.4, -6.0, H + 1.7); F.box(TAR, u - 0.1, -9.6, H + 1.7, u + 2.5, -5.9, H + 1.8)   # stair bulkhead
    F.box(DOOR, u + 0.7, -6.0, H - 0.78, u + 1.6, -5.96, H + 1.2)
    for k in range(r.randint(1, 3)):
        cu = r.uniform(0.8, w - 0.8); cv = r.uniform(-12.5, -3); F.box(bmats(b)[0], cu - 0.3, cv - 0.3, H - 0.8, cu + 0.3, cv + 0.3, H + 0.9)
    if tank:
        cu, cv = (w * 0.3 if u > w / 2 else w * 0.72), -4.2; c = F.p(cu, cv, 0); base = H + 2.2
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)): G.box(IRON, c[0] + dx * 1.1 - 0.06, c[1] + dy * 1.1 - 0.06, H - 0.8, c[0] + dx * 1.1 + 0.06, c[1] + dy * 1.1 + 0.06, base)
        G.box(IRON, c[0] - 1.4, c[1] - 1.4, base - 0.12, c[0] + 1.4, c[1] + 1.4, base)
        G.cyl(WOOD, c[0], c[1], base, base + 3.0, 1.45, 18); G.cyl(TAR, c[0], c[1], base + 3.0, base + 3.9, 1.55, 18, r1=0.05)
        for zz in (0.5, 1.5, 2.5): G.cyl(IRON, c[0], c[1], base + zz, base + zz + 0.05, 1.47, 18)

def cornice(b, F, trim, H, deep=0.5):
    w = b['w']
    st = fstyle(b['id']) if R.ON else None
    if st and st['cornice'] == 'parapet':        # no cornice left: a stone coping and a plain band, as on a building stripped in the 1950s
        F.box(trim, 0, SK, H - 0.32, w, SK + 0.07, H - 0.22); F.box(trim, 0, SK, H - 1.05, w, SK + 0.03, H - 0.9); return
    if st and st['cornice'] == 'metal':          # pressed and painted sheet metal: a deep frieze, a row of dentils, modillions, a crown
        mm = mat('cornice metal ' + b['id'], st['metal'], 0.42, 0.25)
        F.box(mm, 0, SK, H - 1.45, w, SK + 0.22, H - 0.62); F.box(mm, 0, SK, H - 1.55, w, SK + 0.3, H - 1.45)
        for k in range(int(w / 0.16)): u = 0.05 + k * 0.16; F.box(mm, u, SK, H - 0.72, u + 0.08, SK + 0.32, H - 0.62)
        F.box(mm, 0, SK, H - 0.62, w, SK + 0.5, H - 0.5); F.box(mm, 0, SK, H - 0.5, w, SK + 0.72, H - 0.3); F.box(mm, 0, SK, H - 0.3, w, SK + 0.62, H - 0.24)
        n = max(3, int(w / 1.6))
        for k in range(n + 1): u = 0.1 + (w - 0.35) * k / n; F.box(mm, u, SK, H - 1.55, u + 0.16, SK + 0.62, H - 0.5); F.box(mm, u - 0.03, SK + 0.3, H - 1.6, u + 0.19, SK + 0.5, H - 1.45)
        return
    F.box(trim, 0, SK, H - 1.0, w, SK + deep * 0.6, H - 0.45); F.box(trim, 0, SK, H - 0.45, w, SK + deep, H - 0.25)
    n = max(3, int(w / 1.1))
    for k in range(n + 1):
        u = 0.1 + (w - 0.3) * k / n; F.box(trim, u, SK, H - 1.35, u + 0.12, SK + deep * 0.8, H - 0.45)

GALV = None
def facade_history(b, F, ws, H, z_from):
    """What a hundred years leave on a front: a belt course, a downspout, cables looped between hooks, repointed patches."""
    global GALV
    if not R.ON: return
    st = fstyle(b['id']); w = b['w']; r = random.Random(int(st['seed'] * 1e7)); wall, trim = bmats(b)
    if GALV is None: GALV = mat('galvanized', (0.42, 0.43, 0.44), 0.5, 0.7)
    rows = sorted({round(x['z'], 2) for x in ws})
    if st['belt'] and rows:
        for zr in rows[:1] + rows[-1:]: F.box(trim, 0, SK, zr - 0.38, w, SK + 0.06, zr - 0.22)
    if st['pipe']:                           # a leader from the roof to the pavement, strapped every 2 m
        u = 0.18 if r.random() < 0.5 else w - 0.18; v = SK + 0.07
        G.tube(GALV, F.p(u, v, 0.35), F.p(u, v, H - 0.6), 0.045, n=10); F.box(GALV, u - 0.14, SK, H - 0.75, u + 0.14, SK + 0.2, H - 0.45)
        G.tube(GALV, F.p(u, v, 0.35), F.p(u, v + 0.25, 0.18), 0.045, n=10)
        z = 1.0
        while z < H - 1: F.box(IRON, u - 0.06, SK, z, u + 0.06, v + 0.05, z + 0.03); z += 2.0
    if st['cables']:                          # cable TV and phone lines, looped between hooks above the shop, one dropping to a window
        CB = mat('cable', (0.01, 0.01, 0.011), 0.5); zc = z_from + r.uniform(0.25, 0.6)
        for line in range(r.randint(1, 3)):
            zl = zc + line * 0.09; hooks = [0.0] + sorted(r.uniform(1, w - 1) for _ in range(int(w / 3.5))) + [w]
            for a_, c_ in zip(hooks, hooks[1:]):
                n = 6; pts = [F.p(a_ + (c_ - a_) * q / n, SK + 0.04, zl - 0.12 * (c_ - a_) / 4 * math.sin(math.pi * q / n)) for q in range(n + 1)]
                for p0, p1 in zip(pts, pts[1:]): G.tube(CB, p0, p1, 0.007, n=4, caps=False)
        if ws:
            tw = r.choice(ws); u = tw['u'] + tw['w'] / 2 + 0.12
            G.tube(CB, F.p(u, SK + 0.04, zc), F.p(u, SK + 0.04, tw['z'] + 0.3), 0.007, n=4, caps=False)
    if True:                                  # repointed and replaced brick, a little fresher than the wall around it
        pm = MATS.get('patch ' + b['id'])
        if pm is None:
            pm = mat('patch ' + b['id'], b['brick'], 0.85); tid = 'red_bricks_04' if sum(map(ord, b['id'])) % 2 else 'red_brick_03'
            if b['kind'] == 'prewar': tid = 'yellow_brick'
            R.surface(pm, tid, 2.5, tint=tuple(min(1, v * 1.18 + 0.02) for v in b['brick']), bump=0.6, offset=(r.uniform(0, 9), 0, r.uniform(0, 9)))
        for _ in range(st['patches']):
            for tries in range(12):
                pw, ph = r.uniform(0.7, 2.2), r.uniform(0.4, 1.4); pu, pz = r.uniform(0.2, w - pw - 0.2), r.uniform(z_from + 0.3, H - 2.0 - ph)
                if all(pu + pw < x['u'] - x['w'] / 2 - 0.3 or pu > x['u'] + x['w'] / 2 + 0.3 or pz + ph < x['z'] - 0.4 or pz > x['z'] + x['h'] + 0.45 for x in ws):
                    F.box(pm, pu, SK, pz, pu + pw, SK + 0.004, pz + ph); break

FEPAINT = {}
def fire_escape2(b, F, ws, u0, u1, out, floors):
    """05:30 Nov 18 (Astra, second pass, and MLow: "fix the fire escapes too"): built the way they are. A platform is an
    angle iron frame round a slatted deck, carried on wall anchors and diagonal brackets; the railing is a round top rail,
    a mid rail and round balusters; the stair has channel stringers, open treads and its own handrail; the drop ladder
    has round rungs. Painted per building, the paint worn back to rust at the edges."""
    key = fstyle(b['id'])['seed']
    pc = [(0.012, 0.012, 0.014), (0.02, 0.05, 0.03), (0.06, 0.02, 0.015), (0.03, 0.03, 0.035)][int(key * 4) % 4]
    if b['id'] not in FEPAINT:
        m = mat('fire escape ' + b['id'], pc, 0.5, 0.35); nt = m.node_tree; bb = nt.nodes['Principled BSDF']; tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 8; nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = nt.nodes.new('ShaderNodeMapRange'); rp.inputs['From Min'].default_value = 0.58; rp.inputs['From Max'].default_value = 0.7; nt.links.new(nz.outputs['Fac'], rp.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMixRGB'); mx.inputs['Color1'].default_value = (*pc, 1); mx.inputs['Color2'].default_value = (0.16, 0.06, 0.025, 1); nt.links.new(rp.outputs['Result'], mx.inputs['Fac']); nt.links.new(mx.outputs['Color'], bb.inputs['Base Color'])
        rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.45; rr.inputs['To Max'].default_value = 0.9; nt.links.new(rp.outputs['Result'], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], bb.inputs['Roughness'])
        FEPAINT[b['id']] = m
    FE = FEPAINT[b['id']]; v0 = SK; v1 = SK + out
    def T(a, c, r=0.012, n=6): G.tube(FE, F.p(*a), F.p(*c), r, n=n, caps=False)
    for i, fl in enumerate(floors):
        z = K.GROUND_H + (fl - 2) * K.FLOOR_H + 0.55
        for k in range(int((u1 - u0) / 0.075)): F.box(FE, u0 + 0.04 + k * 0.075, v0, z, u0 + 0.04 + k * 0.075 + 0.045, v1 - 0.03, z + 0.012)   # bar grating
        for a_, c_ in (((u0, v1 - 0.05), (u1, v1)), ((u0, v0), (u1, v0 + 0.05))):                  # angle iron front and back: a flange and a leg
            F.box(FE, a_[0], a_[1], z - 0.06, c_[0], c_[1], z + 0.012); F.box(FE, a_[0], a_[1], z - 0.06, c_[0], a_[1] + 0.008, z)
        for uu in (u0, u1 - 0.05): F.box(FE, uu, v0, z - 0.06, uu + 0.05, v1, z + 0.012)
        for uu in (u0 + 0.12, (u0 + u1) / 2, u1 - 0.12):                                            # wall anchors and diagonal brackets
            F.box(FE, uu - 0.07, v0 - 0.005, z - 0.65, uu + 0.07, v0 + 0.012, z - 0.05)
            T((uu, v0 + 0.02, z - 0.6), (uu, v1 - 0.12, z - 0.07), 0.016); T((uu, v0, z - 0.03), (uu, v1 - 0.03, z - 0.03), 0.012)
        for uu, vv in ((u0 + 0.02, v1 - 0.02), (u1 - 0.02, v1 - 0.02), (u0 + 0.02, v0 + 0.05), (u1 - 0.02, v0 + 0.05)): T((uu, vv, z), (uu, vv, z + 1.02), 0.018, 8)   # corner posts
        T((u0 + 0.02, v1 - 0.02, z + 1.0), (u1 - 0.02, v1 - 0.02, z + 1.0), 0.022, 8)                # top rail, round
        T((u0 + 0.02, v1 - 0.02, z + 0.5), (u1 - 0.02, v1 - 0.02, z + 0.5), 0.012)
        for uu in (u0 + 0.02, u1 - 0.02):
            T((uu, v0 + 0.05, z + 1.0), (uu, v1 - 0.02, z + 1.0), 0.02, 8); T((uu, v0 + 0.05, z + 0.5), (uu, v1 - 0.02, z + 0.5), 0.012)
            for k in range(1, 9): vv = v0 + 0.05 + (out - 0.07) * k / 9; T((uu, vv, z), (uu, vv, z + 1.0), 0.008, 5)
        for k in range(1, int((u1 - u0) / 0.115)): uu = u0 + k * 0.115; T((uu, v1 - 0.02, z), (uu, v1 - 0.02, z + 1.0), 0.008, 5)
        if i + 1 < len(floors):                                                                      # stair up: stringers, treads, a handrail
            a, c = u0 + 0.5, u1 - 0.5
            if i % 2: a, c = c, a
            for vv in (v0 + 0.22, v0 + 0.78): G.beam(FE, F.p(a, vv, z + 0.02), F.p(c, vv, z + K.FLOOR_H + 0.02), 0.025, 0.16)
            for q in range(1, 13):
                f = q / 13.0; zz = z + K.FLOOR_H * f; uu = a + (c - a) * f
                F.box(FE, min(uu, uu + (c - a) / 26) , v0 + 0.24, zz, max(uu, uu + (c - a) / 26), v0 + 0.76, zz + 0.015)
            T((a, v0 + 0.8, z + 0.9), (c, v0 + 0.8, z + K.FLOOR_H + 0.9), 0.016, 8)
            for f in (0.15, 0.5, 0.85): uu = a + (c - a) * f; zz = z + K.FLOOR_H * f; T((uu, v0 + 0.8, zz + 0.02), (uu, v0 + 0.8, zz + 0.9), 0.01)
    z = K.GROUND_H + (floors[0] - 2) * K.FLOOR_H + 0.55                                              # the drop ladder, hung on its hooks
    for uu in (u1 - 0.75, u1 - 0.33): T((uu, v1 + 0.04, z - 1.7), (uu, v1 + 0.04, z + 1.0), 0.016, 6)
    for k in range(10): zz = z - 1.55 + k * 0.27; T((u1 - 0.75, v1 + 0.04, zz), (u1 - 0.33, v1 + 0.04, zz), 0.011, 6)
    for uu in (u1 - 0.75, u1 - 0.33): T((uu, v1 - 0.02, z + 1.0), (uu, v1 + 0.06, z + 1.08), 0.012)

def fire_escape(b, F, ws):
    """Iron balconies on the middle bays, a stair between each, a drop ladder at the bottom."""
    n = K.bays(b); pitch = b['w'] / n; k0 = max(0, n // 2 - 1); u0 = k0 * pitch + 0.25; u1 = (k0 + 2) * pitch - 0.25; out = 1.15
    floors = sorted({w['fl'] for w in ws})
    if R.ON: return fire_escape2(b, F, ws, u0, u1, out, floors)
    for i, fl in enumerate(floors):
        z = K.GROUND_H + (fl - 2) * K.FLOOR_H + 0.55
        for k in range(int((u1 - u0) / 0.16) + 1): F.box(IRON, u0 + k * 0.16, SK, z, u0 + k * 0.16 + 0.04, SK + out, z + 0.03)        # slatted floor
        F.box(IRON, u0, SK + out - 0.04, z, u1, SK + out, z + 0.06); F.box(IRON, u0, SK, z - 0.02, u0 + 0.05, SK + out, z + 0.06); F.box(IRON, u1 - 0.05, SK, z - 0.02, u1, SK + out, z + 0.06)
        for zz in (0.5, 0.95): F.box(IRON, u0, SK + out - 0.03, z + zz, u1, SK + out, z + zz + 0.035); F.box(IRON, u0, SK, z + zz, u0 + 0.03, SK + out, z + zz + 0.035); F.box(IRON, u1 - 0.03, SK, z + zz, u1, SK + out, z + zz + 0.035)
        for k in range(int((u1 - u0) / 0.14) + 1): F.box(IRON, u0 + k * 0.14, SK + out - 0.025, z, u0 + k * 0.14 + 0.02, SK + out, z + 0.95)
        for uu in (u0, u1 - 0.03):
            for k in range(8): F.box(IRON, uu, SK + k * 0.15, z, uu + 0.02, SK + k * 0.15 + 0.02, z + 0.95)
        for uu in (u0 + 0.1, u1 - 0.14): G.beam(IRON, F.p(uu, SK + out - 0.1, z - 0.02), F.p(uu, SK, z - 0.75), 0.04, 0.04)          # brackets
        if i + 1 < len(floors):                                                                                                    # stair up
            a, c = u0 + 0.5, u1 - 0.5
            if i % 2: a, c = c, a
            for vv in (SK + 0.25, SK + 0.75): G.beam(IRON, F.p(a, vv, z + 0.03), F.p(c, vv, z + K.FLOOR_H + 0.03), 0.03, 0.10)
            for q in range(1, 12):
                f = q / 12.0; G.beam(IRON, F.p(a + (c - a) * f, SK + 0.25, z + K.FLOOR_H * f + 0.03), F.p(a + (c - a) * f, SK + 0.75, z + K.FLOOR_H * f + 0.03), 0.16, 0.02)
    z = K.GROUND_H + (floors[0] - 2) * K.FLOOR_H + 0.55
    for uu in (u1 - 0.75, u1 - 0.35): F.box(IRON, uu, SK + out + 0.02, z - 1.6, uu + 0.03, SK + out + 0.05, z + 1.0)
    for k in range(9): F.box(IRON, u1 - 0.75, SK + out + 0.02, z - 1.5 + k * 0.28, u1 - 0.35, SK + out + 0.045, z - 1.48 + k * 0.28)

def avenue_windows(b):
    """Windows on the avenue side of a corner building. They belong to the corner apartment on each floor."""
    out = []; per = 2
    west = b['x0'] == 0; end_apt = 'A' if (b['side'] == 'N') == west else 'AB'[per - 1]
    for fl in range(1, b['floors']):
        z = K.GROUND_H + (fl - 1) * K.FLOOR_H + 0.85
        for k in range(5):
            out.append(dict(b=b['id'], fl=fl + 1, u=(k + 0.5) * DEPTH / 5, z=z, w=1.1, h=1.8, unit='%s-%d%s' % (b['id'], fl + 1, end_apt), room=('living', 'kitchen', 'bedroom', 'bedroom', 'kitchen')[k], i=1000 + k))
    return out


# ------------------------------------------------------------------ gate murals: MLow's Open Eye Flowers (his PNGs, from _style on this drive)
STYLE = os.path.join(os.path.dirname(HERE), '_style')
MURALS = K.MURALS     # which flower, where along the gate, how big (block.py)
NAVY = (0.0018, 0.0080, 0.0395)
def plane_uv(name, pts, uvs, m):
    me = bpy.data.meshes.new(name); me.from_pydata(pts, [], [(0, 1, 2, 3)]); uv = me.uv_layers.new(name='UVMap')
    for i, l in enumerate(me.loops): uv.data[i].uv = uvs[l.vertex_index]
    me.materials.append(m); o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); return o
def slatted_uv(name, F, u0, u1, z0, z1, v, m, uvf):
    """04:23 Nov 18 (Astra: the mural read as a graphic on a flat wall): a plane that follows the roll gate's slats,
    a rounded rib every 0.08 m with a groove at each joint, so the painting bends over the gate like real paint."""
    prof = [(0.0, 0.0), (0.008, 0.005), (0.025, 0.010), (0.055, 0.010), (0.072, 0.005), (0.08, 0.0)]
    zs = []; z = z0
    while z < z1 - 1e-6:
        for dz, dv in prof[:-1]:
            if z + dz < z1: zs.append((z + dz, dv))
        z += 0.08
    zs.append((z1, 0.0)); vs = []; fs = []; uvs = []
    for i, (zz, dv) in enumerate(zs):
        for uu in (u0, u1): vs.append(F.p(uu, v + dv, zz)); uvs.append(uvf(uu, zz))
        if i: fs.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); uv = me.uv_layers.new(name='UVMap')
    for l in me.loops: uv.data[l.index].uv = uvs[l.vertex_index]
    for p_ in me.polygons: p_.use_smooth = True
    me.materials.append(m); o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); return o
def contour_mat(name, cx, cz, r=1.6, n_lines=9.0, seed=0.0):
    """His liquid contour field on navy: lines crowd toward (cx, cz), the flower. UV is metres on the gate."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.55
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    off = nt.nodes.new('ShaderNodeVectorMath'); off.operation = 'ADD'; off.inputs[1].default_value = (seed, seed * 0.7, 0); nt.links.new(uv.outputs['UV'], off.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.32; nz.inputs['Detail'].default_value = 3; nz.inputs['Distortion'].default_value = 0.4; nt.links.new(off.outputs[0], nz.inputs['Vector'])
    d = nt.nodes.new('ShaderNodeVectorMath'); d.operation = 'DISTANCE'; d.inputs[1].default_value = (cx, cz, 0); nt.links.new(uv.outputs['UV'], d.inputs[0])
    e1 = nt.nodes.new('ShaderNodeMath'); e1.operation = 'MULTIPLY'; e1.inputs[1].default_value = -1.0 / r; nt.links.new(d.outputs['Value'], e1.inputs[0])
    e2 = nt.nodes.new('ShaderNodeMath'); e2.operation = 'EXPONENT'; nt.links.new(e1.outputs[0], e2.inputs[0])
    f1 = nt.nodes.new('ShaderNodeMath'); f1.operation = 'MULTIPLY_ADD'; f1.inputs[1].default_value = 3.0; nt.links.new(nz.outputs['Fac'], f1.inputs[0])
    f2 = nt.nodes.new('ShaderNodeMath'); f2.operation = 'MULTIPLY'; f2.inputs[1].default_value = 4.0; nt.links.new(e2.outputs[0], f2.inputs[0]); nt.links.new(f2.outputs[0], f1.inputs[2])
    fN = nt.nodes.new('ShaderNodeMath'); fN.operation = 'MULTIPLY'; fN.inputs[1].default_value = n_lines; nt.links.new(f1.outputs[0], fN.inputs[0])
    fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'; nt.links.new(fN.outputs[0], fr.inputs[0])
    ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'SUBTRACT'; ab.inputs[1].default_value = 0.5; nt.links.new(fr.outputs[0], ab.inputs[0])
    ab2 = nt.nodes.new('ShaderNodeMath'); ab2.operation = 'ABSOLUTE'; nt.links.new(ab.outputs[0], ab2.inputs[0])
    edge = nt.nodes.new('ShaderNodeMapRange'); edge.inputs['From Min'].default_value = 0.458; edge.inputs['From Max'].default_value = 0.5; nt.links.new(ab2.outputs[0], edge.inputs['Value'])   # 1 on a line, 0 between
    # every fifth line heavier: a slower set of bands with a wider edge
    f5 = nt.nodes.new('ShaderNodeMath'); f5.operation = 'MULTIPLY'; f5.inputs[1].default_value = 0.2; nt.links.new(fN.outputs[0], f5.inputs[0])
    fr5 = nt.nodes.new('ShaderNodeMath'); fr5.operation = 'FRACT'; nt.links.new(f5.outputs[0], fr5.inputs[0])
    a5 = nt.nodes.new('ShaderNodeMath'); a5.operation = 'SUBTRACT'; a5.inputs[1].default_value = 0.5; nt.links.new(fr5.outputs[0], a5.inputs[0])
    a52 = nt.nodes.new('ShaderNodeMath'); a52.operation = 'ABSOLUTE'; nt.links.new(a5.outputs[0], a52.inputs[0])
    e5 = nt.nodes.new('ShaderNodeMapRange'); e5.inputs['From Min'].default_value = 0.47; e5.inputs['From Max'].default_value = 0.5; nt.links.new(a52.outputs[0], e5.inputs['Value'])
    ln = nt.nodes.new('ShaderNodeMath'); ln.operation = 'MAXIMUM'; nt.links.new(edge.outputs['Result'], ln.inputs[0]); nt.links.new(e5.outputs['Result'], ln.inputs[1])
    band = nt.nodes.new('ShaderNodeMath'); band.operation = 'MULTIPLY'; band.inputs[1].default_value = 0.23; nt.links.new(f1.outputs[0], band.inputs[0])
    bf = nt.nodes.new('ShaderNodeMath'); bf.operation = 'FRACT'; nt.links.new(band.outputs[0], bf.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); nt.links.new(bf.outputs[0], ramp.inputs['Fac']); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    stops = [(0.0, K.BLUE), (0.38, K.CYAN), (0.62, K.BLUE), (0.80, (0.157, 0.016, 0.39)), (0.92, K.PINK)]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1); cr.elements[1].position, cr.elements[1].color = stops[1][0], (*stops[1][1], 1)
    for p_, c_ in stops[2:]: el = cr.elements.new(p_); el.color = (*c_, 1)
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.inputs['Color1'].default_value = (*NAVY, 1); nt.links.new(ln.outputs[0], mx.inputs['Fac']); nt.links.new(ramp.outputs['Color'], mx.inputs['Color2'])
    nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
    em = nt.nodes.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 0.1 if R.ON else 0.3;   # 04:30: paint, not a sign (Astra)
    nt.links.new(ln.outputs[0], em.inputs[0])
    nt.links.new(ramp.outputs['Color'], b.inputs['Emission Color']); nt.links.new(em.outputs[0], b.inputs['Emission Strength'])
    return m
def flower_mat(n):
    nm = 'Open Eye Flower %d' % n
    if nm in MATS: return MATS[nm]
    m = bpy.data.materials.new(nm); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.5
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(STYLE, 'eye-flower-%d_1024.png' % n), check_existing=True); tx.extension = 'CLIP'
    nt.links.new(tx.outputs['Color'], b.inputs['Base Color']); nt.links.new(tx.outputs['Alpha'], b.inputs['Alpha'])
    nt.links.new(tx.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 0.04 if R.ON else 0.12
    MATS[nm] = m; return m
def gate_mural(F, u0, u1, z0, z1, key):
    n, at, size = MURALS[key]; w, h = u1 - u0, z1 - z0; cx, cz = w * at, h * 0.52; s = (h - 0.1) * size
    bg = slatted_uv('mural ' + key, F, u0, u1, z0, z1, 0.186, contour_mat('contours ' + key, cx, cz, seed=n * 3.1), lambda uu, zz: (uu - u0, zz - z0))
    a, c = cx - s / 2, cx + s / 2; zb, zt = z0 + cz - s / 2, z0 + cz + s / 2
    fl = slatted_uv('flower ' + key, F, u0 + a, u0 + c, max(z0, zb), min(z1, zt), 0.1875, flower_mat(n), lambda uu, zz: ((uu - u0 - a) / s, (zz - zb) / s))
    return [bg, fl]

SHOPLIGHT = {}
def shop_materials(key):
    s = K.SHOPS[key]
    gl = tuple(0.5 * a + 0.5 * b for a, b in zip(s['glow'], (1.0, 0.84, 0.64))) if R.ON else s['glow']     # 04:23: rooms lit warm white (about 3200 K), the colour stays on the signs
    m = mat('shoplight ' + key, (1, 1, 1), 0.5, emit=gl, es=0.0); ctrl_emit('shop ' + key, m)
    sg = mat('sign ' + key, s['awning'], 0.5, emit=s['awning'], es=0.0); ctrl_emit('sign ' + key, sg)
    nn = mat('neon ' + key, s['neon'], 0.5, emit=s['neon'], es=0.0); ctrl_emit('neon ' + key, nn)
    ink = mat('ink ' + key, s['ink'], 0.6); aw = mat('awning ' + key, s['awning'], 0.7)
    return m, sg, nn, ink, aw
GATES = {}; SHOPCAV = {}
SIGN_STYLE = dict(grocery='awning', laundromat='box', garage='paint', pizza='neon', diner='neon', bar='neon', flowers='awning', bakery='box', locksmith='box', pharmacy='box')

def shopfront(b, F, wall, trim, FA=None):
    """Ground floor of a tenement: shop cavity, glass, sign, roll gate, and the apartment door at the right hand end."""
    key = b['shop']; s = K.SHOPS[key]; w = b['w']; light, sign, neon, ink, awn = shop_materials(key)
    door_w = 1.5; shop_u0, shop_u1 = 0.5, w - door_w - 0.9
    # structure around the cavity
    F.box(wall, 0, -DEPTH, 0, w, -6.2, K.GROUND_H)                                   # back of the ground floor
    if FA is None or FA.o[0] != F.p(0, 0, 0)[0] or True:
        pass
    corner_left = FA is not None and abs(F.p(0, 0, 0)[0] - FA.o[0]) < 0.01 and abs(F.p(0, 0, 0)[0] - (0 if b['x0'] == 0 else L)) < 0.01
    corner_right = FA is not None and not corner_left
    if not corner_left: F.box(wall, 0, -6.2, 0, 0.3, 0, K.GROUND_H)
    if not corner_right: F.box(wall, w - 0.3, -6.2, 0, w, 0, K.GROUND_H)
    F.box(wall, shop_u1, -6.2, 0, shop_u1 + 0.3, SK, K.GROUND_H)                     # wall between shop and stair hall
    F.box(wall, 0, 0, 0, shop_u0, SK, K.GROUND_H); F.box(wall, w - 0.45, 0, 0, w, SK, K.GROUND_H)
    F.box(trim, 0, 0, 3.05, w, SK + 0.06, K.GROUND_H)                                # fascia
    F.box(trim, shop_u0, 0, 0.16, shop_u1, SK - 0.05, 0.62)                          # bulkhead under the glass
    # interior
    F.box(INFLOOR, 0.3, -6.2, 0.0, shop_u1, 0, 0.17); F.box(INWALL, 0.3, -6.2, 0.17, shop_u1, -6.1, 3.3); F.box(INWALL, 0.3, -6.2, 3.3, shop_u1, 0, 3.4)
    F.box(INWALL, shop_u1 - 0.02, -6.1, 0.17, shop_u1, 0, 3.3)
    if not corner_left: F.box(INWALL, 0.3, -6.1, 0.17, 0.32, 0, 3.3)
    nrow = max(1, int((shop_u1 - shop_u0) / 2.2))
    for k in range(nrow):
        uu = shop_u0 + (shop_u1 - shop_u0) * (k + 0.5) / nrow
        for vv in (-1.6, -3.4, -5.0): F.box(light, uu - 0.6, vv - 0.07, 3.24, uu + 0.6, vv + 0.07, 3.3)
    # glass and door
    du = shop_u1 - 1.3                                                               # shop door at the right of the glass
    F.box(GLASS, shop_u0, 0.06, 0.62, du, 0.08, 3.05); F.box(GLASS, du + 0.05, 0.02, 0.2, shop_u1 - 0.05, 0.04, 2.3); F.box(GLASS, du, 0.06, 2.4, shop_u1, 0.08, 3.05)
    for a in (shop_u0, du - 0.03, du + 0.0, shop_u1 - 0.05): F.box(STEEL, a, 0.03, 0.17, a + 0.05, 0.12, 3.05)
    F.box(STEEL, shop_u0, 0.03, 2.3, shop_u1, 0.12, 2.4); F.box(STEEL, du + 0.15, 0.12, 1.0, shop_u1 - 0.15, 0.16, 1.06)
    # residential door and its light
    F.box(DOOR, w - door_w - 0.45, 0.02, 0.17, w - 0.6, 0.08, 2.45); F.box(trim, w - door_w - 0.6, 0, 2.45, w - 0.45, SK, 3.05)
    hall = mat('hall light', (1, 1, 1), emit=(1.0, 0.72, 0.42), es=2.2); F.box(hall, w - door_w - 0.3, 0.03, 2.5, w - 0.75, 0.05, 2.95)
    F.box(wall, w - door_w - 0.9, 0, 0, w - door_w - 0.45, SK, K.GROUND_H); F.box(wall, w - 0.6, 0, 0, w - 0.45, SK, 3.05)
    # sign
    style = SIGN_STYLE[key]; mid = (shop_u0 + shop_u1) / 2; span = shop_u1 - shop_u0
    size = min(0.62, span / (len(s['name']) * 0.36))
    if style == 'awning':
        G.quad(awn, F.p(shop_u0 - 0.2, SK, 3.75), F.p(shop_u1 + 0.2, SK, 3.75), F.p(shop_u1 + 0.2, 1.5, 3.0), F.p(shop_u0 - 0.2, 1.5, 3.0))
        G.quad(awn, F.p(shop_u0 - 0.2, 1.5, 3.0), F.p(shop_u1 + 0.2, 1.5, 3.0), F.p(shop_u1 + 0.2, 1.5, 2.55), F.p(shop_u0 - 0.2, 1.5, 2.55))
        for uu in (shop_u0 - 0.2, shop_u1 + 0.2): G.quad(awn, F.p(uu, SK, 3.75), F.p(uu, 1.5, 3.0), F.p(uu, 1.5, 2.55), F.p(uu, SK, 2.55))
        text(s['name'], F, mid, 1.52, 2.78, min(0.36, size), ink)
        F.box(neon, shop_u0, 0.1, 2.95, du, 0.13, 3.0)                               # one tube of neon inside the top of the window
    elif style == 'box':
        F.box(sign, shop_u0 - 0.1, SK, 3.1, shop_u1 + 0.1, SK + 0.22, 3.92); text(s['name'], F, mid, SK + 0.235, 3.51, size, ink)
    elif style == 'neon':
        F.box(mat('fascia dark', (0.015, 0.015, 0.017), 0.4), shop_u0 - 0.1, SK, 3.1, shop_u1 + 0.1, SK + 0.12, 3.92); text(s['name'], F, mid, SK + 0.14, 3.51, size, neon, extrude=0.03)
        F.box(neon, shop_u0 - 0.1, SK + 0.12, 3.08, shop_u1 + 0.1, SK + 0.16, 3.12)
    else:
        text(s['name'], F, mid, SK + 0.07, 3.5, size, ink)
    text(s['sub'], F, mid, 0.085, 0.42, min(0.13, span / (len(s['sub']) * 0.075)), ink if style != 'neon' else mat('sub ' + key, K.CLOUD, 0.6), extrude=0.002)
    # roll gate
    if s['gate']:
        g = Geo(); F.box(GATE, shop_u0 - 0.05, 0.13, 0.17, shop_u1 + 0.05, 0.17, 3.05, g)
        for k in range(36): F.box(GATE, shop_u0 - 0.05, 0.17, 0.2 + k * 0.08, shop_u1 + 0.05, 0.185, 0.24 + k * 0.08, g)
        GATES[key] = g.flush('gate ' + key)
        if key in MURALS: GATES[key] += gate_mural(F, shop_u0 - 0.05, shop_u1 + 0.05, 0.17, 3.05, key)
    # corner: the shop turns the corner onto the avenue
    if FA is not None:
        a0, a1 = (0.5, 5.8) if FA.p(0, 0, 0)[1] in (FAC, -FAC) else (DEPTH - 5.8, DEPTH - 0.5)
        FA.box(wall, 0, 0, 0, min(a0, DEPTH - a1 + 0.0) if a0 < 1 else a0, SK, K.GROUND_H) if a0 < 1 else FA.box(wall, 0, 0, 0, a0, SK, K.GROUND_H)
        if a0 < 1: FA.box(wall, a1, 0, 0, DEPTH, SK, K.GROUND_H); FA.box(wall, a1, -0.3, 0, DEPTH, 0, K.GROUND_H)
        else: FA.box(wall, 0, -0.3, 0, a0, 0, K.GROUND_H); FA.box(wall, a1, 0, 0, DEPTH, SK, K.GROUND_H)
        FA.box(trim, 0, 0, 3.05, DEPTH, SK + 0.06, K.GROUND_H); FA.box(trim, a0, 0, 0.16, a1, SK - 0.05, 0.62)
        FA.box(GLASS, a0, 0.06, 0.62, a1, 0.08, 3.05)
        for k in range(4): aa = a0 + (a1 - a0) * k / 3; FA.box(STEEL, aa - 0.025, 0.03, 0.17, aa + 0.025, 0.12, 3.05)
        if style in ('neon', 'box'):
            FA.box(sign if style == 'box' else mat('fascia dark', (0.015, 0.015, 0.017), 0.4), a0 - 0.1, SK, 3.1, a1 + 0.1, SK + (0.22 if style == 'box' else 0.12), 3.92)
            text(s['name'], FA, (a0 + a1) / 2, SK + 0.235, 3.51, min(size, 0.5), ink if style == 'box' else neon, extrude=0.01 if style == 'box' else 0.03)
        else:
            G.quad(awn, FA.p(a0 - 0.2, SK, 3.75), FA.p(a1 + 0.2, SK, 3.75), FA.p(a1 + 0.2, 1.5, 3.0), FA.p(a0 - 0.2, 1.5, 3.0))
            G.quad(awn, FA.p(a0 - 0.2, 1.5, 3.0), FA.p(a1 + 0.2, 1.5, 3.0), FA.p(a1 + 0.2, 1.5, 2.55), FA.p(a0 - 0.2, 1.5, 2.55))
            text(s['name'], FA, (a0 + a1) / 2, 1.52, 2.78, min(0.36, size), ink)
        if s['gate']:
            g = Geo(); FA.box(GATE, a0 - 0.05, 0.13, 0.17, a1 + 0.05, 0.17, 3.05, g)
            for k in range(36): FA.box(GATE, a0 - 0.05, 0.17, 0.2 + k * 0.08, a1 + 0.05, 0.185, 0.24 + k * 0.08, g)
            GATES[key] += g.flush('gate ave ' + key)
    SHOPCAV[key] = (F, 0.3, shop_u1)
    return shop_u0, shop_u1

def tenement(b):
    F = street_frame(b); FA = avenue_frame(b); ws = [w for w in K.WINDOWS if w['b'] == b['id']]
    wall, trim, H = shell(b, F, K.GROUND_H)
    skin(F, wall, ws, K.GROUND_H, H - 0.8, trim); cornice(b, F, trim, H); facade_history(b, F, ws, H, K.GROUND_H)
    if FA is not None:
        skin(FA, wall, avenue_windows(b), K.GROUND_H, H - 0.8, trim)
        FA.box(trim, 0, SK, H - 1.0, DEPTH, SK + 0.3, H - 0.45); FA.box(trim, 0, SK, H - 0.45, DEPTH, SK + 0.5, H - 0.25)
    gwall = wall
    if R.ON:     # the ground floor: the same brick, buffed in patches where graffiti was painted over (Firefly)
        gwall = mat('ground wall ' + b['id'], b['brick'], 0.85); R.surface(gwall, 'ff_brick', 2.6, tint=tuple(v * 0.9 for v in b['brick']), bump=0.6, firefly=True, weather=dict(splash=0.7), offset=(b['x0'] * 0.31, 0, 0))
    shopfront(b, F, gwall, trim, FA)
    if b['escape']: fire_escape(b, F, ws)
    roof_stuff(b, F, H, tank=b['floors'] >= 6 or b['id'] in ('N2', 'S7'))

def brownstone(b):
    F = street_frame(b); ws = [w for w in K.WINDOWS if w['b'] == b['id']]; w = b['w']; pitch = w / 3
    wall, trim, H = shell(b, F, 0); skin(F, wall, ws, 0, H - 0.8, trim); cornice(b, F, trim, H, deep=0.7)
    # the door on the parlour floor and the stoop that reaches it
    zf = 1.6; F.box(DOOR, pitch * 0.5 - 0.6, SK - 0.08, zf, pitch * 0.5 + 0.6, SK - 0.02, zf + 2.5); F.box(trim, pitch * 0.5 - 0.85, SK, zf + 2.5, pitch * 0.5 + 0.85, SK + 0.3, zf + 2.9)
    for uu in (pitch * 0.5 - 0.85, pitch * 0.5 + 0.65): F.box(trim, uu, SK, zf, uu + 0.2, SK + 0.12, zf + 2.5)
    lamp = mat('stoop light', (1, 1, 1), emit=(1.0, 0.7, 0.4), es=6.0); F.box(lamp, pitch * 0.5 - 0.4, SK - 0.02, zf + 2.2, pitch * 0.5 + 0.4, SK, zf + 2.45)
    steps = 8
    for k in range(steps):
        z1 = zf - k * (zf - 0.16) / steps; F.box(trim, pitch * 0.5 - 0.8, SK + 0.5 + k * 0.3, 0.16, pitch * 0.5 + 0.8, SK + 0.5 + (k + 1) * 0.3, z1)
    F.box(trim, pitch * 0.5 - 0.8, SK, 0.16, pitch * 0.5 + 0.8, SK + 0.5, zf)
    for uu in (pitch * 0.5 - 1.0, pitch * 0.5 + 0.8):
        F.box(trim, uu, SK, 0.16, uu + 0.2, SK + 3.2, 0.55)
        G.beam(IRON, F.p(uu + 0.1, SK + 0.5, zf + 0.9), F.p(uu + 0.1, SK + 3.0, 1.2), 0.04, 0.04)
        for k in range(9): vv = SK + 0.5 + k * 0.31; F.box(IRON, uu + 0.09, vv, 0.55, uu + 0.11, vv + 0.02, zf + 0.9 - (k * 0.31) * (zf - 0.3) / 2.5)
        F.box(trim, uu - 0.05, SK + 3.0, 0.16, uu + 0.25, SK + 3.3, 1.3)
    # areaway fence in front of the basement windows
    for k in range(int((w - pitch - 0.4) / 0.14)): F.box(IRON, pitch + 0.3 + k * 0.14, 1.9, 0.16, pitch + 0.32 + k * 0.14, 1.92, 1.1)
    F.box(IRON, pitch + 0.3, 1.9, 1.05, w - 0.1, 1.93, 1.1); F.box(IRON, pitch + 0.3, 1.9, 0.3, w - 0.1, 1.93, 0.34)
    if R.ON: R.place('potted_plant_02', F.p(pitch * 0.5 - 1.35, SK + 3.25, 0.16), fit=('z', 0.75)); R.place('potted_plant_02', F.p(pitch * 0.5 + 1.35, SK + 3.25, 0.16), rotz=1.3, fit=('z', 0.7))
    roof_stuff(b, F, H)

def prewar(b):
    F = street_frame(b); ws = [w for w in K.WINDOWS if w['b'] == b['id']]; w = b['w']
    wall, trim, H = shell(b, F, 0)
    # ground floor: limestone base, dark windows with bars, and a lit lobby in the middle
    gw = []; n = K.bays(b); pitch = w / n
    for k in range(n):
        if abs((k + 0.5) * pitch - w / 2) > 1.8: gw.append(dict(u=(k + 0.5) * pitch, z=1.3, w=1.3, h=1.7, static=(0, 0, 0)))
    skin(F, trim, gw, 0, K.GROUND_H, trim); skin(F, wall, ws, K.GROUND_H, H - 0.8, trim); cornice(b, F, trim, H, deep=0.6); facade_history(b, F, ws, H, K.GROUND_H)
    F.box(trim, 0, SK, K.GROUND_H - 0.25, w, SK + 0.2, K.GROUND_H + 0.1)
    for g in gw:
        for k in range(8): F.box(IRON, g['u'] - 0.6 + k * 0.17, SK - 0.03, g['z'], g['u'] - 0.58 + k * 0.17, SK - 0.01, g['z'] + g['h'])
    lob = mat('lobby light', (1, 1, 1), emit=(1.0, 0.78, 0.5), es=5.0)
    F.box(lob, w / 2 - 1.1, SK - 0.05, 0.2, w / 2 + 1.1, SK - 0.03, 3.0); F.box(trim, w / 2 - 1.5, SK, 0.16, w / 2 - 1.1, SK + 0.25, 3.5); F.box(trim, w / 2 + 1.1, SK, 0.16, w / 2 + 1.5, SK + 0.25, 3.5); F.box(trim, w / 2 - 1.5, SK, 3.0, w / 2 + 1.5, SK + 0.3, 3.5)
    for uu in (w / 2 - 0.02, w / 2 - 1.1, w / 2 + 1.06): F.box(IRON, uu, SK - 0.03, 0.2, uu + 0.04, SK + 0.02, 3.0)
    F.box(IRON, w / 2 - 1.1, SK - 0.03, 2.3, w / 2 + 1.1, SK + 0.02, 2.36)
    # canopy to the kerb
    cm = colmat('canopy', (0.02, 0.05, 0.035) if b['side'] == 'N' else (0.10, 0.02, 0.03), 0.7)
    F.box(cm, w / 2 - 1.3, SK, 2.9, w / 2 + 1.3, 3.7, 3.25)
    for uu in (w / 2 - 1.25, w / 2 + 1.2): F.box(STEEL, uu, 3.6, 0.16, uu + 0.05, 3.65, 2.9)
    text(b['name'].split(',')[0].upper(), F, w / 2, 3.71, 3.07, 0.2, mat('canopy ink', K.CLOUD, 0.6), extrude=0.003)
    # sidewalk shed
    if b.get('shed'):
        ply = colmat('shed', (0.02, 0.07, 0.05), 0.7)
        if R.ON and 'ff posters' not in MATS:     # the plywood under the shed: torn wheatpaste, years deep (Firefly)
            MATS['ff posters'] = mat('ff posters', (0.5, 0.5, 0.5), 0.8); R.surface(MATS['ff posters'], 'ff_posters', 2.4, tint=(0.30, 0.28, 0.30), bump=0.5, firefly=True)
        if R.ON: ply = MATS['ff posters']
        F.box(ply, 0.2, 0.5, 2.75, w - 0.2, 3.85, 2.9); F.box(ply, 0.2, 3.8, 2.9, w - 0.2, 3.85, 4.1); F.box(ply, 0.2, 0.5, 2.9, 0.25, 3.85, 4.1); F.box(ply, w - 0.25, 0.5, 2.9, w - 0.2, 3.85, 4.1)
        bulb = mat('shed bulb', (1, 1, 1), emit=(1.0, 0.85, 0.6), es=14.0)
        for k in range(int((w - 0.4) / 2.4) + 1):
            uu = 0.3 + k * 2.4
            for vv in (0.6, 3.7):
                F.box(STEEL, uu, vv, 0.16, uu + 0.06, vv + 0.06, 2.75)
            G.beam(STEEL, F.p(uu + 0.03, 0.63, 0.5), F.p(uu + 0.03, 3.73, 2.6), 0.04, 0.04)
            if k % 2 == 0:
                c = F.p(uu + 1.2, 2.1, 2.62); G.blob(bulb, c[0], c[1], c[2], 0.08, 0.08, 0.1, 6, 4)
                li = bpy.data.lights.new('shed', 'POINT'); li.energy = 28; li.color = (1.0, 0.85, 0.6); li.shadow_soft_size = 0.08
                o = bpy.data.objects.new('shed', li); scene.collection.objects.link(o); o.location = (c[0], c[1], c[2] - 0.15)
        text('POST NO BILLS', F, w * 0.25, 3.86, 3.5, 0.22, mat('stencil', (0.7, 0.7, 0.66), 0.7), extrude=0.002)
    roof_stuff(b, F, H, tank=True)

def garage(b):
    F = street_frame(b); w = b['w']; key = 'garage'; s = K.SHOPS[key]; light, sign, neon, ink, awn = shop_materials(key)
    wall, trim = bmats(b); H = K.height(b)
    F.box(wall, 0, -DEPTH, 0, w, -9, H); F.box(wall, 0, -9, 4.3, w, 0, H); F.box(wall, 0, -9, 0, 0.4, 0, 4.3); F.box(wall, w - 0.4, -9, 0, w, 0, 4.3)
    F.box(wall, 5.1, -0.4, 0, 5.5, 0, 4.3); F.box(wall, 10.2, -0.4, 0, 10.5, 0, 4.3); F.box(wall, 10.5, -0.4, 2.3, w - 0.4, 0, 4.3)
    F.box(TAR, 0, -DEPTH, H, w, 0, H + 0.02); F.box(trim, 0, 0, H - 0.5, w, 0.15, H + 0.3)
    F.box(INFLOOR, 0.4, -9, 0, w - 0.4, 0, 0.05); F.box(INWALL, 0.4, -9, 0.05, w - 0.4, -8.9, 4.2); F.box(INWALL, 0.4, -9, 4.2, w - 0.4, 0, 4.3)
    for uu in (2.7, 7.8):
        for vv in (-2.5, -6.0): F.box(light, uu - 0.8, vv - 0.08, 4.12, uu + 0.8, vv + 0.08, 4.2)
    F.box(DOOR, 10.6, -0.1, 0.05, w - 0.5, -0.04, 2.3)
    g = Geo()
    for a, c in ((0.4, 5.1), (5.5, 10.2)):
        F.box(GATE, a, -0.2, 0.05, c, -0.15, 4.3, g)
        for k in range(52): F.box(GATE, a, -0.15, 0.08 + k * 0.08, c, -0.135, 0.12 + k * 0.08, g)
    GATES[key] = g.flush('gate garage')
    F.box(awn, 0.3, 0.0, 4.45, w - 0.3, 0.06, 5.45); text(s['name'], F, w / 2, 0.07, 5.05, 0.62, ink); text(s['sub'], F, w / 2, 0.07, 4.62, 0.2, ink, extrude=0.003)
    # tyres stacked inside, a car on stands
    for k in range(5):
        for q in range(4): c = F.p(1.0 + k * 0.75, -8.3, 0); G.cyl(RUBBER, c[0], c[1], 0.05 + q * 0.24, 0.27 + q * 0.24, 0.33, 12)
    gc = Geo(); car_geo(gc, 'sedan', (0.30, 0.05, 0.05)); c_ = F.p(2.75, -4.5, 0.55); G.merge(gc, c_, math.radians(90))
    for dx in (-0.6, 0.6):
        for dy in (-1.5, 1.5): G.cyl(STEEL, c_[0] + dx, c_[1] + dy, 0.05, 0.85, 0.05, 6)
    # billboard on the roof: the brief
    bb = mat('billboard', (0.9, 0.9, 0.88), 0.7, emit=K.CLOUD, es=0.0); ctrl_emit('billboard', bb)
    F.box(bb, 1.0, -1.0, H + 2.2, w - 1.0, -0.9, H + 6.2); F.box(IRON, 0.9, -1.1, H + 2.1, w - 0.9, -1.0, H + 6.3)
    for uu in (2.0, w / 2, w - 2.0): F.box(IRON, uu - 0.08, -1.3, H, uu + 0.08, -1.1, H + 6.3); G.beam(IRON, F.p(uu, -1.2, H + 5.0), F.p(uu, -5.0, H), 0.1, 0.1)
    bi = mat('billboard ink', K.INK, 0.7)
    for i, line in enumerate(('ONE BLOCK.', 'EIGHT HOURS.', 'NO CHECK-INS.')): text(line, F, w / 2, -0.88, H + 5.35 - i * 1.15, 0.95, bi, extrude=0.004)
    text('YOUR AD HERE  ·  317-555-0153', F, w / 2, -0.88, H + 2.5, 0.22, mat('billboard pink', K.PINK, 0.6), extrude=0.004)

def garden(b):
    F = street_frame(b); w = b['w']
    F.box(SOIL, 0, -DEPTH, 0, w, 0, 0.12)
    fence = bpy.data.materials.new('Chain link'); fence.use_nodes = True; nt = fence.node_tree; bs = nt.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (0.25, 0.26, 0.27, 1); bs.inputs['Metallic'].default_value = 0.8; bs.inputs['Roughness'].default_value = 0.4
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sp.inputs[0])
    def saw(sock_a, sock_b, sign):
        m = nt.nodes.new('ShaderNodeMath'); m.operation = 'ADD' if sign > 0 else 'SUBTRACT'; nt.links.new(sock_a, m.inputs[0]); nt.links.new(sock_b, m.inputs[1])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'PINGPONG'; fr.inputs[1].default_value = 0.035; nt.links.new(m.outputs[0], fr.inputs[0])
        lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.006; nt.links.new(fr.outputs[0], lt.inputs[0]); return lt
    a = saw(sp.outputs['X'], sp.outputs['Z'], 1); c = saw(sp.outputs['X'], sp.outputs['Z'], -1)
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; nt.links.new(a.outputs[0], mx.inputs[0]); nt.links.new(c.outputs[0], mx.inputs[1]); nt.links.new(mx.outputs[0], bs.inputs['Alpha'])
    MATS['Chain link'] = fence
    F.quad(fence, 0.1, 0.12, w - 0.1, 2.5, 0.05)
    for k in range(6): uu = 0.1 + (w - 0.2) * k / 5; F.box(STEEL, uu - 0.03, 0.02, 0.12, uu + 0.03, 0.08, 2.6)
    F.box(STEEL, 0.1, 0.03, 2.5, w - 0.1, 0.07, 2.55)
    bed = colmat('bed', (0.16, 0.10, 0.05), 0.8); green = colmat('kale', (0.03, 0.09, 0.03), 0.8)
    for i in range(3):
        for q in range(2):
            u0 = 0.9 + i * 3.6; v0 = -3.2 - q * 3.6; F.box(bed, u0, v0 - 2.2, 0.12, u0 + 2.6, v0, 0.5); F.box(SOIL, u0 + 0.08, v0 - 2.12, 0.5, u0 + 2.52, v0 - 0.08, 0.52)
            for k in range(7): c_ = F.p(u0 + 0.3 + rnd.uniform(0, 2.0), v0 - 0.3 - rnd.uniform(0, 1.6), 0); G.blob(green, c_[0], c_[1], 0.62, 0.16, 0.16, 0.14, 6, 4, 0.2)
    shed = colmat('garden shed', K.BLUE, 0.7); F.box(shed, w - 3.2, -12.5, 0.12, w - 0.6, -10.0, 2.4); F.box(TAR, w - 3.4, -12.7, 2.4, w - 0.4, -9.8, 2.5)
    F.box(WOOD, 1.0, -11.5, 0.5, 2.8, -11.0, 0.56); F.box(WOOD, 1.0, -11.6, 0.12, 1.1, -10.9, 0.5); F.box(WOOD, 2.7, -11.6, 0.12, 2.8, -10.9, 0.5)
    # string lights across the lot
    sl = mat('string light', (1, 1, 1), emit=(1.0, 0.8, 0.5), es=0.0); ctrl_emit('string', sl)
    for (ua, va), (ub, vb) in (((0.3, -0.5), (w - 0.5, -9.5)), ((w - 0.3, -0.5), (0.5, -9.5))):
        for k in range(15):
            f = (k + 0.5) / 15; sag = 0.9 * math.sin(math.pi * f); c_ = F.p(ua + (ub - ua) * f, va + (vb - va) * f, 0); G.blob(sl, c_[0], c_[1], 3.6 - sag, 0.05, 0.05, 0.07, 6, 3)
        G.beam(IRON, F.p(ua, va, 3.6), F.p(ub, vb, 3.6), 0.01, 0.01)
    for (ua, va) in ((0.3, -0.5), (w - 0.5, -9.5), (w - 0.3, -0.5), (0.5, -9.5)): F.box(WOOD, ua - 0.05, va - 0.05, 0.12, ua + 0.05, va + 0.05, 3.65)
    c_ = F.p(w / 2, -6, 0); tree(c_[0], c_[1], 11.0, seed=7, base=0.12)
    sgn = colmat('garden sign', (0.03, 0.10, 0.05), 0.7); F.box(sgn, w / 2 - 1.6, 0.08, 1.5, w / 2 + 1.6, 0.11, 2.1); text('317TH STREET GARDEN', F, w / 2, 0.115, 1.88, 0.22, mat('garden ink', K.ACID, 0.6), extrude=0.003)
    text('OPEN SAT + SUN  ·  ALL WELCOME', F, w / 2, 0.115, 1.63, 0.11, mat('canopy ink', K.CLOUD, 0.6), extrude=0.003)
    # ghost sign on the party wall of 304: an old painted advertisement nobody has painted over
    gh = mat('ghost', (0.42, 0.37, 0.30), 0.9); FW = Frame(22.0, -FAC - 12, 0, 1, 1, 0, 12)
    for i, line in enumerate(('ICE', 'COAL', 'WOOD')): text(line, FW, 6.0, 0.01, 10.6 - i * 1.5, 1.25, gh, extrude=0.001)
    text('DELIVERED TO YOUR DOOR', FW, 6.0, 0.01, 6.3, 0.42, gh, extrude=0.001)

def tree(x, y, h, seed=0, base=0.16):
    r = random.Random(K.SEED * 31 + seed)
    def grow(p, d, length, rad, depth):
        q = p + d * length; G.tube(BARK, tuple(p), tuple(q), rad, rad * 0.72, 5 if depth < 2 else 4, caps=False)
        if depth >= 5 or rad < 0.012: return
        for k in range(2 if depth else 3) if depth < 4 else range(2):
            ax = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.15, 0.5))).normalized()
            nd = (d + ax * r.uniform(0.45, 0.85)).normalized(); nd.z = abs(nd.z) * 0.8 + 0.2; nd.normalize()
            grow(q, nd, length * r.uniform(0.62, 0.8), rad * 0.62, depth + 1)
    grow(Vector((x, y, base)), Vector((r.uniform(-0.04, 0.04), r.uniform(-0.04, 0.04), 1)).normalized(), h * 0.34, h * 0.019, 0)

# ------------------------------------------------------------------ street furniture
LAMP_LIGHTS = []
def street_lamps():
    lens = mat('lamp lens', (1, 1, 1), emit=(1.0, 0.80, 0.58), es=0.0); ctrl_emit('lamp', lens)
    for lp in K.LAMPS:
        s = 1 if lp['side'] == 'N' else -1; x = lp['x']; y = s * (K.ROAD + 0.55)
        G.cyl(STEEL, x, y, 0.16, 8.2, 0.10, 8, r1=0.07); G.cyl(STEEL, x, y, 0.16, 0.8, 0.16, 8)
        G.beam(STEEL, (x, y, 8.1), (x, y - s * 2.4, 8.6), 0.07, 0.07); G.box(STEEL, x - 0.16, y - s * 2.4 - 0.45, 8.52, x + 0.16, y - s * 2.4 + 0.45, 8.66)
        G.box(lens, x - 0.12, y - s * 2.4 - 0.35, 8.50, x + 0.12, y - s * 2.4 + 0.35, 8.52)
        li = bpy.data.lights.new('street lamp', 'SPOT'); li.spot_size = math.radians(150); li.spot_blend = 0.6; li.color = (1.0, 0.80, 0.58); li.shadow_soft_size = 0.25
        o = bpy.data.objects.new('street lamp', li); scene.collection.objects.link(o); o.location = (x, y - s * 2.4, 8.45); LAMP_LIGHTS.append(li)

SIG = {}
def signals():
    housing = mat('Signal housing', (0.02, 0.02, 0.02), 0.5)
    for nm, c in (('R', (1.0, 0.02, 0.01)), ('Y', (1.0, 0.55, 0.0)), ('G', (0.0, 1.0, 0.45))):
        for grp in ('st', 'av'):
            m = mat('sig %s %s' % (grp, nm), (0.02, 0.02, 0.02), 0.3, emit=c, es=0.0); SIG[(grp, nm)] = bsdf(m).inputs['Emission Strength']
    def head(x, y, z, face, grp):      # face = unit vector the lenses look along
        fx, fy = face; px, py = -fy, fx
        G.box(housing, x - abs(px) * 0.17 - abs(fx) * 0.1, y - abs(py) * 0.17 - abs(fy) * 0.1, z, x + abs(px) * 0.17 + abs(fx) * 0.1, y + abs(py) * 0.17 + abs(fy) * 0.1, z + 1.05)
        for k, nm in enumerate('GYR'):
            c = (x + fx * 0.105, y + fy * 0.105, z + 0.18 + k * 0.34); G.tube(MATS['sig %s %s' % (grp, nm)], c, (c[0] + fx * 0.01, c[1] + fy * 0.01, c[2]), 0.105, n=14)
    if R.ON:     # green street name blades on both signal poles, the way every corner here has them
        plate = mat('street sign', (0.0, 0.12, 0.05), 0.4, 0.2); ink = mat('street sign ink', (0.85, 0.87, 0.85), 0.5)
        for (x, y, arm) in ((-0.9, -K.ROAD - 0.7, 1), (L + 0.9, K.ROAD + 0.7, -1)):
            R.blade(text, Frame(x, y, 1, 0, 0, -1, 1), 0, 0, 3.55, 'W 317 ST', plate, ink)       # along the street, read from the avenue
            R.blade(text, Frame(x, y, 0, 1, 1, 0, 1), 0, 0, 3.85, 'MERIDIAN AV', plate, ink)      # along the avenue, read from the street
    # traffic on 317th runs west and stops at the west corner; avenue heads face north and south
    for (x, y, arm) in ((-0.9, -K.ROAD - 0.7, 1), (L + 0.9, K.ROAD + 0.7, -1)):
        G.cyl(STEEL, x, y, 0.16, 6.2, 0.11, 8); G.beam(STEEL, (x, y, 6.0), (x, y + arm * 4.6, 6.3), 0.09, 0.09)
        head(x, y + arm * 4.2, 5.2, (1, 0), 'st'); head(x, y + arm * 0.1, 3.0, (1, 0), 'st')
        head(x - 0.0, y, 4.3, (0, arm), 'av'); head(x, y, 4.3, (0, -arm), 'av')

def hydrant(x, side):
    s = 1 if side == 'N' else -1; y = s * (K.ROAD + 0.6); hm_ = colmat('hydrant', (0.45, 0.04, 0.03), 0.4)
    if R.ON: R.place('fire_hydrant', (x, y, 0.16), rotz=math.radians(90 if s > 0 else -90), fit=('z', 0.82)); return
    G.cyl(hm_, x, y, 0.16, 0.75, 0.11, 10); G.cyl(hm_, x, y, 0.75, 0.9, 0.12, 10, r1=0.04); G.tube(hm_, (x - 0.2, y, 0.6), (x + 0.2, y, 0.6), 0.055, n=8); G.tube(hm_, (x, y, 0.6), (x, y - s * 0.2, 0.6), 0.07, n=8)

PILES = []     # (objects, x, appear_minute, gone_minute)
def trash_piles():
    spots = K.PILES
    r = random.Random(K.SEED + 9)
    for x, side, n, appear in spots:
        s = 1 if side == 'N' else -1; g = Geo()
        extra = []
        for k in range(n):
            bx, by, bz = x + r.uniform(-1.3, 1.3), s * (K.ROAD + 0.75 + r.uniform(-0.25, 0.3)), 0.16 + (0.38 if k % 4 == 3 else 0)
            if R.ON: extra.append(R.place('trashbag', (bx, by, bz), rotz=r.uniform(0, 6.28), fit=('z', r.uniform(0.55, 0.75)), name='bag')); continue
            g.blob(BAG, bx, by, bz + 0.26, r.uniform(0.3, 0.42), r.uniform(0.28, 0.4), r.uniform(0.26, 0.36), 7, 5, 0.18, r)
        if n > 8:
            if R.ON: extra.append(R.place('metal_trash_can', (x + 1.75, s * (K.ROAD + 0.75), 0.16), rotz=r.uniform(0, 6.28), fit=('z', 0.78)))
            else: g.box(colmat('recycling', (0.08, 0.2, 0.6), 0.5), x + 1.5, s * (K.ROAD + 0.5), 0.16, x + 2.0, s * (K.ROAD + 1.0), 0.75)
        PILES.append((g.flush('pile %d' % len(PILES), smooth=('Trash bag',)) + extra, x, appear, K.pile_gone(x)))

def subway():
    green = colmat('subway green', (0.02, 0.10, 0.06), 0.45, 0.3); x0, x1, y0, y1 = 90.6, 94.4, -8.0, -6.4
    G.box(mat('stair void', (0.01, 0.01, 0.01), 0.9), x0, y0, -3.2, x1, y1, -3.15)
    sub = mat('subway light', (1, 1, 1), emit=(1.0, 0.92, 0.75), es=6.0); G.box(sub, x0 + 0.05, y0 + 0.02, -2.6, x0 + 0.08, y1 - 0.02, -0.4)
    for k in range(12): G.box(CONC, x0 + 0.3 + k * 0.29, y0, -3.2, x0 + 0.3 + (k + 1) * 0.29, y1, -0.1 - k * 0.26)
    G.box(CONC, x0 - 0.0, y0 - 0.12, -3.2, x1, y0, 0.16); G.box(CONC, x0, y1, -3.2, x1, y1 + 0.12, 0.16); G.box(CONC, x1, y0 - 0.12, -3.2, x1 + 0.12, y1 + 0.12, 0.16)
    for (a, b_, c, d) in ((x0 + 0.3, y0 - 0.1, x1 + 0.1, y0 - 0.04), (x0 + 0.3, y1 + 0.04, x1 + 0.1, y1 + 0.1), (x1 + 0.04, y0 - 0.1, x1 + 0.1, y1 + 0.1)):
        G.box(green, a, b_, 1.05, c, d, 1.12); G.box(green, a, b_, 0.16, c, d, 0.3)
        nb = int(max(c - a, d - b_) / 0.13)
        for k in range(nb + 1):
            if c - a > d - b_: G.box(green, a + k * 0.13, b_, 0.3, a + k * 0.13 + 0.025, d, 1.05)
            else: G.box(green, a, b_ + k * 0.13, 0.3, c, b_ + k * 0.13 + 0.025, 1.05)
    globe = mat('subway globe', (0.1, 1, 0.4), 0.3, emit=(0.05, 1.0, 0.35), es=5.0)
    for yy in (y0 - 0.07, y1 + 0.07):
        G.cyl(green, x0 + 0.3, yy, 0.16, 2.7, 0.05, 8); G.blob(globe, x0 + 0.3, yy, 2.9, 0.2, 0.2, 0.2, 10, 6)
    F = Frame(x1 + 0.12, y0 - 0.1, 0, 1, 1, 0, 1.8); G.box(mat('station sign', (0.01, 0.01, 0.012), 0.5), x1 + 0.1, y0 - 0.1, 1.2, x1 + 0.13, y1 + 0.1, 1.75)
    text('317 ST', F, 0.9, 0.02, 1.52, 0.3, mat('canopy ink', K.CLOUD, 0.6), extrude=0.003); text('UPTOWN & DOWNTOWN', F, 0.9, 0.02, 1.3, 0.09, mat('canopy ink', K.CLOUD, 0.6), extrude=0.003)

def odds_and_ends():
    mb = colmat('mailbox', (0.03, 0.07, 0.25), 0.4)
    G.box(mb, 12.0, K.ROAD + 0.5, 0.3, 12.55, K.ROAD + 1.1, 1.15); G.tube(mb, (12.0, K.ROAD + 0.8, 1.15), (12.55, K.ROAD + 0.8, 1.15), 0.3, n=10)
    for dx, dy in ((0.05, 0.05), (0.45, 0.05), (0.05, 0.5), (0.45, 0.5)): G.box(mb, 12.0 + dx, K.ROAD + 0.5 + dy, 0.16, 12.05 + dx, K.ROAD + 0.55 + dy, 0.3)
    # parking signs and tree guards
    for x, s in ((16, 1), (34, 1), (60, 1), (82, 1), (12, -1), (36, -1), (60, -1), (80, -1)):
        y = s * (K.ROAD + 0.45); G.cyl(STEEL, x, y, 0.16, 2.9, 0.025, 6); G.box(colmat('parking sign', (0.75, 0.75, 0.72), 0.5), x - 0.15, y - 0.01, 2.2, x + 0.15, y + 0.01, 2.8)
        G.box(colmat('parking red', (0.6, 0.03, 0.03), 0.5), x - 0.13, y - s * 0.012, 2.55, x + 0.13, y - s * 0.011, 2.78)
    for tr in K.TREES:
        s = 1 if tr['side'] == 'N' else -1; y = s * (K.ROAD + 0.95); x = tr['x']
        G.box(SOIL, x - 0.75, y - 0.6, 0.16, x + 0.75, y + 0.6, 0.175); tree(x, y, tr['h'], seed=int(x * 10))
        for a, b_, c, d in ((x - 0.78, y - 0.63, x + 0.78, y - 0.6), (x - 0.78, y + 0.6, x + 0.78, y + 0.63), (x - 0.78, y - 0.63, x - 0.75, y + 0.63), (x + 0.75, y - 0.63, x + 0.78, y + 0.63)): G.box(IRON, a, b_, 0.42, c, d, 0.45);
        for cx, cy in ((x - 0.765, y - 0.615), (x + 0.765, y - 0.615), (x - 0.765, y + 0.615), (x + 0.765, y + 0.615)): G.box(IRON, cx - 0.015, cy - 0.015, 0.16, cx + 0.015, cy + 0.015, 0.45)
    # bike rack and one locked frame with no wheels
    for k in range(3):
        x = 68.0 + k * 0.9; y = -K.ROAD - 0.7
        for dx in (-0.25, 0.25): G.cyl(STEEL, x + dx, y, 0.16, 0.9, 0.025, 6)
        G.tube(STEEL, (x - 0.25, y, 0.9), (x + 0.25, y, 0.9), 0.025, n=6)
    # steam stack over the manhole at mid block
    st = colmat('stack orange', (0.9, 0.25, 0.02), 0.6); wt = colmat('stack white', (0.85, 0.85, 0.82), 0.6)
    for k in range(6): G.cyl(st if k % 2 == 0 else wt, 48.0, 0.7, 0.012 + k * 0.5, 0.012 + (k + 1) * 0.5, 0.26 - 0.0 * k, 12)
    if R.ON:     # CC0 street hardware: corner cans, the signal controller cabinets, cartons waiting by the grocery
        rr = random.Random(K.SEED + 21)
        for x, s in ((1.2, 1), (1.2, -1), (L - 1.2, 1), (L - 1.2, -1), (47.0, 1)): R.place('metal_trash_can', (x, s * (K.ROAD + 0.75), 0.16), rotz=rr.uniform(0, 6.28), fit=('z', 0.8))
        R.place('utility_box_01', (-2.2, -K.ROAD - 1.5, 0.16), rotz=math.radians(90), fit=('z', 1.25)); R.place('utility_box_01', (L + 2.2, K.ROAD + 1.5, 0.16), rotz=math.radians(-90), fit=('z', 1.25))
        if 'grocery' in SHOPCAV:
            F_, a_, b__ = SHOPCAV['grocery']
            for k in range(5): R.place('cardboard_box_01', F_.p(b__ - 0.6 - (k % 3) * 0.45, 0.65 + (k // 3) * 0.05, 0.16 + (k // 3) * 0.34), rotz=F_.rotz() + rr.uniform(-0.2, 0.2), fit=('z', 0.34))

STEAMOFF = []
def steam(x, y, z0, h=7.0, wdt=1.7, dens=0.5):
    me = bpy.data.meshes.new('Steam'); me.from_pydata([(a, b_, c) for a in (x - wdt, x + wdt) for b_ in (y - wdt, y + wdt) for c in (z0, z0 + h)], [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    o = bpy.data.objects.new('Steam', me); scene.collection.objects.link(o)
    m = bpy.data.materials.new('Steam'); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    vol = nt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Color'].default_value = (0.9, 0.9, 0.9, 1); vol.inputs['Anisotropy'].default_value = 0.3
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sp.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.9; nz.inputs['Detail'].default_value = 5
    so = nt.nodes.new('ShaderNodeVectorMath'); so.operation = 'ADD'; STEAMOFF.append(so.inputs[1]); nt.links.new(geo.outputs['Position'], so.inputs[0]); nt.links.new(so.outputs[0], nz.inputs['Vector'])
    ex = nt.nodes.new('ShaderNodeMath'); ex.operation = 'SUBTRACT'; ex.inputs[1].default_value = x; nt.links.new(sp.outputs['X'], ex.inputs[0])
    ey = nt.nodes.new('ShaderNodeMath'); ey.operation = 'SUBTRACT'; ey.inputs[1].default_value = y; nt.links.new(sp.outputs['Y'], ey.inputs[0])
    cb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(ex.outputs[0], cb.inputs['X']); nt.links.new(ey.outputs[0], cb.inputs['Y'])
    d2 = nt.nodes.new('ShaderNodeVectorMath'); d2.operation = 'LENGTH'; nt.links.new(cb.outputs[0], d2.inputs[0])
    rad = nt.nodes.new('ShaderNodeMapRange'); rad.inputs['From Min'].default_value = z0; rad.inputs['From Max'].default_value = z0 + h; rad.inputs['To Min'].default_value = 0.3; rad.inputs['To Max'].default_value = wdt; nt.links.new(sp.outputs['Z'], rad.inputs['Value'])
    fall = nt.nodes.new('ShaderNodeMath'); fall.operation = 'DIVIDE'; nt.links.new(d2.outputs['Value'], fall.inputs[0]); nt.links.new(rad.outputs['Result'], fall.inputs[1])
    inv = nt.nodes.new('ShaderNodeMapRange'); inv.inputs['From Min'].default_value = 0.2; inv.inputs['From Max'].default_value = 1.0; inv.inputs['To Min'].default_value = 1.0; inv.inputs['To Max'].default_value = 0.0; nt.links.new(fall.outputs[0], inv.inputs['Value'])
    fade = nt.nodes.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = z0; fade.inputs['From Max'].default_value = z0 + h; fade.inputs['To Min'].default_value = dens; fade.inputs['To Max'].default_value = 0.0; nt.links.new(sp.outputs['Z'], fade.inputs['Value'])
    thr = nt.nodes.new('ShaderNodeMapRange'); thr.inputs['From Min'].default_value = 0.35; thr.inputs['From Max'].default_value = 0.7; nt.links.new(nz.outputs['Fac'], thr.inputs['Value'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(inv.outputs['Result'], m1.inputs[0]); nt.links.new(fade.outputs['Result'], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(thr.outputs['Result'], m2.inputs[1])
    nt.links.new(m2.outputs[0], vol.inputs['Density']); nt.links.new(vol.outputs['Volume'], nt.nodes['Material Output'].inputs['Volume'])
    me.materials.append(m); return o

# ------------------------------------------------------------------ the rest of the city
CITY = []; CG = Geo()
def city():
    """Blocks across the avenues and a skyline behind, with windows that are only a texture."""
    cm = bpy.data.materials.new('City'); cm.use_nodes = True; nt = cm.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.8
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sp.inputs[0])
    hz = nt.nodes.new('ShaderNodeMath'); hz.operation = 'ADD'; nt.links.new(sp.outputs['X'], hz.inputs[0]); nt.links.new(sp.outputs['Y'], hz.inputs[1])
    def cell(sock, size):
        d = nt.nodes.new('ShaderNodeMath'); d.operation = 'DIVIDE'; d.inputs[1].default_value = size; nt.links.new(sock, d.inputs[0])
        fl = nt.nodes.new('ShaderNodeMath'); fl.operation = 'FLOOR'; nt.links.new(d.outputs[0], fl.inputs[0])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'; nt.links.new(d.outputs[0], fr.inputs[0]); return fl, fr
    cu, fu = cell(hz.outputs[0], 2.1); cv, fv = cell(sp.outputs['Z'], 3.2)
    cc = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(cu.outputs[0], cc.inputs['X']); nt.links.new(cv.outputs[0], cc.inputs['Y'])
    wn = nt.nodes.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '2D'; nt.links.new(cc.outputs[0], wn.inputs['Vector'])
    def band(sock, lo, hi):
        a = nt.nodes.new('ShaderNodeMath'); a.operation = 'GREATER_THAN'; a.inputs[1].default_value = lo; nt.links.new(sock, a.inputs[0])
        c = nt.nodes.new('ShaderNodeMath'); c.operation = 'LESS_THAN'; c.inputs[1].default_value = hi; nt.links.new(sock, c.inputs[0])
        m = nt.nodes.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; nt.links.new(a.outputs[0], m.inputs[0]); nt.links.new(c.outputs[0], m.inputs[1]); return m
    wu = band(fu.outputs[0], 0.32, 0.70); wv = band(fv.outputs[0], 0.34, 0.80)
    isw = nt.nodes.new('ShaderNodeMath'); isw.operation = 'MULTIPLY'; nt.links.new(wu.outputs[0], isw.inputs[0]); nt.links.new(wv.outputs[0], isw.inputs[1])
    litv = nt.nodes.new('ShaderNodeValue'); litv.outputs[0].default_value = 0.1; CTRL['city'] = litv.outputs[0]
    on = nt.nodes.new('ShaderNodeMath'); on.operation = 'LESS_THAN'; nt.links.new(wn.outputs['Value'], on.inputs[0]); nt.links.new(litv.outputs[0], on.inputs[1])
    em = nt.nodes.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; nt.links.new(isw.outputs[0], em.inputs[0]); nt.links.new(on.outputs[0], em.inputs[1])
    col = nt.nodes.new('ShaderNodeMixRGB'); col.inputs['Color1'].default_value = (1.0, 0.55, 0.25, 1); col.inputs['Color2'].default_value = (1.0, 0.8, 0.6, 1); nt.links.new(wn.outputs['Color'], col.inputs['Fac'])
    nt.links.new(col.outputs['Color'], b.inputs['Emission Color'])
    es = nt.nodes.new('ShaderNodeMath'); es.operation = 'MULTIPLY'; es.inputs[1].default_value = 0.9; nt.links.new(em.outputs[0], es.inputs[0]); nt.links.new(es.outputs[0], b.inputs['Emission Strength'])
    base = nt.nodes.new('ShaderNodeMixRGB'); base.inputs['Color1'].default_value = (0.10, 0.07, 0.06, 1); base.inputs['Color2'].default_value = (0.012, 0.014, 0.02, 1); nt.links.new(isw.outputs[0], base.inputs['Fac'])
    tint = nt.nodes.new('ShaderNodeTexWhiteNoise'); tint.noise_dimensions = '1D'; obj = nt.nodes.new('ShaderNodeObjectInfo')
    nt.links.new(base.outputs['Color'], b.inputs['Base Color'])
    rg = nt.nodes.new('ShaderNodeMapRange'); rg.inputs['To Min'].default_value = 0.85; rg.inputs['To Max'].default_value = 0.08; nt.links.new(isw.outputs[0], rg.inputs['Value']); nt.links.new(rg.outputs['Result'], b.inputs['Roughness'])
    MATS['City'] = cm; r = random.Random(K.SEED + 5)
    def row(x0, x1, ya, yb, hmin, hmax):
        x = x0
        while x < x1 - 4:
            w = min(r.uniform(7, 22), x1 - x); h = r.uniform(hmin, hmax); CG.box(cm, x, min(ya, yb), 0, x + w - 0.05, max(ya, yb), h); CG.box(TAR, x, min(ya, yb), h, x + w - 0.05, max(ya, yb), h + 0.05); x += w
    for sgn in (1, -1):
        row(-200, -22, sgn * FAC, sgn * (FAC + DEPTH), 13, 24); row(L + 22, 300, sgn * FAC, sgn * (FAC + DEPTH), 13, 26)       # 317th continues
        row(-200, 300, sgn * (FAC + DEPTH + 9), sgn * (FAC + 2 * DEPTH + 9), 14, 30)                                             # the backs of the next street
        row(-220, 320, sgn * 72, sgn * 100, 20, 70); row(-240, 340, sgn * 130, sgn * 170, 30, 130)                             # farther off
        for xa, xb in ((-22, 0), (L, L + 22)):                                                                                   # along the avenues
            pass
    for y0 in (FAC + DEPTH + 9 + DEPTH + 18,):
        pass
    CG.box(TAR, -900, -900, -0.6, 1200, 900, -0.31)      # the ground the rest of the city stands on
    CITY.extend(CG.flush('city'))

# ------------------------------------------------------------------ vehicles and people
# 23:45: modelled cars. MLow at 23:39: "fix the cars". The boxes with rounded corners read as toys in every still.
# A body lofted through rounded sections along its length (hood falling to the nose, a raked windshield, a roof, a deck),
# a glass house with painted pillars and roof, black wheel arches, tyres with rims, bumpers, mirrors, lamps.
CARPROF = dict(   # length, width, nose top, belt, roof, windshield base, roof start, roof end, rear glass base, tail top (u: 0 front .. 1 rear)
    sedan=(4.70, 1.82, 0.80, 0.98, 1.44, 0.30, 0.46, 0.71, 0.83, 0.96), car=(4.70, 1.82, 0.80, 0.98, 1.44, 0.30, 0.46, 0.71, 0.83, 0.96),
    cab=(4.80, 1.84, 0.80, 0.98, 1.48, 0.30, 0.45, 0.72, 0.84, 0.96), suv=(4.80, 1.92, 0.98, 1.12, 1.76, 0.27, 0.39, 0.92, 0.965, 1.10),
    van=(5.20, 2.00, 1.02, 1.16, 2.08, 0.16, 0.27, 0.985, 0.995, 1.14), hatch=(4.10, 1.76, 0.80, 0.98, 1.50, 0.29, 0.44, 0.86, 0.95, 0.99))
RIM = mat('Rim', (0.42, 0.43, 0.45), 0.3, 0.9); WELL = mat('Wheel well', (0.004, 0.004, 0.005), 0.9); TRIM = mat('Car trim', (0.015, 0.015, 0.017), 0.55)
def _sup(c, sn, p=4.0): return math.copysign(abs(c) ** (2 / p), c), math.copysign(abs(sn) ** (2 / p), sn)
def ringloft(g, m, rings):
    vs, fs = g._b(m); k = len(vs); n = len(rings[0])
    for r_ in rings: vs.extend(r_)
    for i in range(len(rings) - 1):
        for q in range(n): q2 = (q + 1) % n; fs.append((k + i * n + q, k + i * n + q2, k + (i + 1) * n + q2, k + (i + 1) * n + q))
    fs.append(tuple(k + q for q in range(n))[::-1]); fs.append(tuple(k + (len(rings) - 1) * n + q for q in range(n)))
def car_geo2(g, kind, col, lights=None):
    ln, wd, nose, belt, roof, uc, ur0, ur1, ud, tail = CARPROF[kind]; hx, hy = ln / 2, wd / 2
    body = colmat('paint', col, 0.25, 0.3); bb = bsdf(body)
    if 'Coat Weight' in bb.inputs: bb.inputs['Coat Weight'].default_value = 1.0; bb.inputs['Coat Roughness'].default_value = 0.04
    X = lambda u: -hx + u * ln
    def top(u):      # the top of the lower body: hood, belt, deck
        if u < uc: a = u / uc; return nose + (belt - nose) * (1 - (1 - a) ** 2)
        if u > ud: a = (u - ud) / (1 - ud); return belt + (tail - belt) * a
        return belt
    def bot(u): e = min(u, 1 - u); return 0.30 + (0.10 * (1 - e / 0.08) ** 2 if e < 0.08 else 0.0)
    def half(u): e = abs(2 * u - 1); return hy * (1 - 0.07 * e ** 8)
    N = 18; us = [0.0, 0.012, 0.03, 0.06] + [0.06 + i * 0.88 / 22 for i in range(1, 22)] + [0.94, 0.97, 0.988, 1.0]
    rings = []
    for u in us:
        e = min(u, 1 - u); sq = 1.0 if e > 0.03 else (0.86 + 0.14 * (e / 0.03) ** 0.5)       # the nose and tail round off in plan and section
        b, t, w = bot(u), top(u), half(u) * sq; zc = (b + t) / 2; hz = (t - b) / 2 * (sq if e < 0.03 else 1)
        ring = []
        for q in range(N):
            th = 2 * math.pi * q / N; cy, sz = _sup(math.cos(th), math.sin(th), 4.5); yy = w * cy * (1 - 0.05 * max(0, sz)); ring.append((X(u), yy, zc + hz * sz))
        rings.append(ring)
    ringloft(g, body, rings)
    # the glass house
    def rz(u):
        if u <= ur0: return top(u) + (roof - top(u)) * ((u - uc) / (ur0 - uc)) ** 0.9
        if u >= ur1: return top(u) + (roof - top(u)) * ((ud - u) / (ud - ur1)) ** 0.8
        return roof + 0.02 * math.sin(math.pi * (u - ur0) / (ur1 - ur0))
    gl = []; gus = [uc + (ud - uc) * i / 20 for i in range(21)]
    for i, u in enumerate(gus):
        zb = top(u) - 0.02; zt = max(rz(u), zb + 0.015) if 0 < i < 20 else zb + 0.015; wb = half(u) * 0.95; wt = wb * 0.78; ring = []
        for q in range(12):
            th = 2 * math.pi * q / 12; cy, sz = _sup(math.cos(th), math.sin(th), 6); f = (sz + 1) / 2; ring.append((X(u), cy * (wb + (wt - wb) * f), zb + (zt - zb) * f))
        gl.append(ring)
    if R.ON:      # 05:35 (Astra, both passes: opaque glass, no interiors): tinted glass you can see into, and a cabin behind it
        ringloft(g, CARGLASS, gl); bt = top((uc + ud) / 2)
        cu = lambda f: X(ur0 + (ur1 - ur0) * f)
        g.box(CABIN, X(uc + 0.02), -hy * 0.85, bt - 0.04, X(ud - 0.02), hy * 0.85, bt - 0.005)                       # the floor of the cabin, dark
        g.box(CABIN, X(uc) + 0.02, -hy * 0.82, bt - 0.02, X(uc) + 0.32, hy * 0.82, bt + 0.09)                     # dashboard under the windshield
        rows = (0.18, 0.72) if kind not in ('van',) else (0.18,)
        for f in rows:
            for sy in (-0.42, 0.42):
                xb = cu(f); g.box(SEAT, xb, sy * hy - 0.24, bt - 0.03, xb + 0.12, sy * hy + 0.24, bt + 0.36)                # seat back, raked a little by the headrest
                g.box(SEAT, xb + 0.02, sy * hy - 0.12, bt + 0.4, xb + 0.11, sy * hy + 0.12, bt + 0.56)
        wx = X(uc) + 0.42; wy = -0.42 * hy
        for q in range(12): a0 = 2 * math.pi * q / 12; a1 = 2 * math.pi * (q + 1) / 12; g.tube(CABIN, (wx + 0.04 * math.sin(a0), wy + 0.18 * math.cos(a0), bt + 0.14 + 0.18 * math.sin(a0)), (wx + 0.04 * math.sin(a1), wy + 0.18 * math.cos(a1), bt + 0.14 + 0.18 * math.sin(a1)), 0.015, n=5, caps=False)
    else: ringloft(g, DARKGLASS, gl)
    # painted roof and pillars
    rr = []
    for u in [ur0 - 0.015 + (ur1 - ur0 + 0.03) * i / 12 for i in range(13)]:
        zt = rz(min(max(u, ur0), ur1)) + 0.012; w = half(u) * 0.95 * 0.79; rr.append([(X(u), w * c_, zt + dz) for c_, dz in ((-1, -0.05), (1, -0.05), (1, 0.0), (-1, 0.0))])
    ringloft(g, body, rr)
    pil = [uc, (ur0 + ur1) / 2 if kind not in ('van', 'suv') else ur0 + (ur1 - ur0) * 0.42, ud] + ([ur0 + (ur1 - ur0) * 0.78] if kind in ('suv', 'van') else [])
    for j, u in enumerate(pil):
        ut = ur0 if j == 0 else (ur1 if j == 2 else u)
        for sgn in (-1, 1):
            g.beam(body, (X(u), sgn * half(u) * 0.955, top(u) - 0.02), (X(ut), sgn * half(ut) * 0.95 * 0.79, rz(ut) + 0.005), 0.10 if j != 2 else 0.22, 0.05)
    # wheels, arches, rims
    for u in (0.17 if kind != 'van' else 0.15, 0.80 if kind != 'van' else 0.82):
        wx = X(u); w = half(u)
        for sgn in (-1, 1):
            g.tube(WELL, (wx, sgn * (w - 0.3), 0.34), (wx, sgn * (w + 0.004), 0.34), 0.41, n=24)
            g.tube(RUBBER, (wx, sgn * (w - 0.25), 0.33), (wx, sgn * (w - 0.03), 0.33), 0.33, n=24)
            g.tube(RIM, (wx, sgn * (w - 0.04), 0.33), (wx, sgn * (w - 0.015), 0.33), 0.205, 0.19, n=20)
            g.tube(TRIM, (wx, sgn * (w - 0.02), 0.33), (wx, sgn * (w - 0.008), 0.33), 0.05, n=10)
    # bumpers, sills, grille, mirrors, lamps
    for x0, x1 in ((-hx - 0.03, -hx + 0.25), (hx - 0.25, hx + 0.03)):
        g.box(TRIM, x0, -hy * 0.9, 0.30, x1, hy * 0.9, 0.46)
    for sgn in (-1, 1): g.box(TRIM, X(0.2), sgn * hy * 0.985 - 0.02, 0.30, X(0.78), sgn * hy * 0.985 + 0.01, 0.37)
    g.box(TRIM, -hx - 0.01, -hy * 0.42, nose - 0.30, -hx + 0.05, hy * 0.42, nose - 0.10)
    for sgn in (-1, 1): g.blob(body, X(uc) + 0.08, sgn * (hy + 0.08), belt + 0.08, 0.07, 0.09, 0.06, 8, 4)
    hl = lights[0] if lights else mat('headlamp off', (0.6, 0.6, 0.62), 0.2); tl = lights[1] if lights else mat('tail off', (0.25, 0.01, 0.01), 0.3)
    for sgn in (-1, 1):
        g.blob(hl, -hx + 0.06, sgn * (hy - 0.33), nose - 0.08, 0.06, 0.22, 0.055, 10, 4)
        g.blob(tl, hx - 0.04, sgn * (hy - 0.24), tail - 0.12, 0.05, 0.2, 0.065, 10, 4)
    g.box(mat('plate', (0.75, 0.74, 0.68), 0.5), hx + 0.025, -0.26, 0.48, hx + 0.035, 0.26, 0.63)
    if kind == 'cab':
        g.box(mat('cab light', (1, 1, 1), emit=(1.0, 0.85, 0.4), es=6.0), -0.25, -0.33, roof + 0.03, 0.25, 0.33, roof + 0.2)
    return ln

def car_geo(g, kind, col, lights=None):
    if R.ON and kind in CARPROF: return car_geo2(g, kind, col, lights)
    return car_geo0(g, kind, col, lights)
def car_geo0(g, kind, col, lights=None):
    """A car pointing along -x (westbound), centred on the origin, wheels on z = 0."""
    dims = dict(sedan=(4.6, 1.8, 0.62, 1.42, 0.50), suv=(4.8, 1.92, 0.85, 1.75, 0.34), van=(5.3, 2.0, 1.0, 2.15, 0.12), hatch=(4.0, 1.75, 0.68, 1.5, 0.30), cab=(4.7, 1.85, 0.66, 1.5, 0.42), car=(4.6, 1.8, 0.62, 1.42, 0.50))[kind]
    ln, wd, belt, top, slope = dims; body = colmat('paint', col, 0.25, 0.3); hx, hy = ln / 2, wd / 2
    g.box(body, -hx, -hy, 0.28, hx, hy, belt + 0.28)
    fx0 = -hx + ln * (0.30 if kind != 'van' else 0.14); fx1 = hx - ln * (0.16 if kind in ('sedan', 'cab', 'car') else 0.04); s = slope
    g.hexa(DARKGLASS, [(fx0, -hy + 0.04, belt + 0.28), (fx1, -hy + 0.04, belt + 0.28), (fx1, hy - 0.04, belt + 0.28), (fx0, hy - 0.04, belt + 0.28),
                       (fx0 + s, -hy + 0.16, top), (fx1 - s * 0.8, -hy + 0.16, top), (fx1 - s * 0.8, hy - 0.16, top), (fx0 + s, hy - 0.16, top)])
    g.box(body, fx0 + s - 0.02, -hy + 0.14, top - 0.02, fx1 - s * 0.8 + 0.02, hy - 0.14, top + 0.03)
    for wx in (-hx + 0.85, hx - 0.85):
        for wy in (-hy + 0.02, hy - 0.02): g.tube(RUBBER, (wx, wy - 0.1, 0.33), (wx, wy + 0.1, 0.33), 0.33, n=12)
    hl = lights[0] if lights else mat('headlamp off', (0.6, 0.6, 0.62), 0.2); tl = lights[1] if lights else mat('tail off', (0.25, 0.01, 0.01), 0.3)
    for wy in (-hy + 0.3, hy - 0.3):
        g.box(hl, -hx - 0.02, wy - 0.2, belt - 0.05, -hx, wy + 0.2, belt + 0.12); g.box(tl, hx, wy - 0.22, belt, hx + 0.02, wy + 0.22, belt + 0.14)
    if kind == 'cab':
        g.box(mat('cab light', (1, 1, 1), emit=(1.0, 0.85, 0.4), es=6.0), -0.25, -0.35, top + 0.03, 0.25, 0.35, top + 0.16)
    return ln

def truck_geo(g, kind, col, lights):
    body = colmat('paint', col, 0.35, 0.1); dark = colmat('paint', (0.03, 0.03, 0.035), 0.5)
    spec = dict(boxtruck=(7.5, 2.4, 3.4), garbage=(8.6, 2.5, 3.5), sweeper=(5.2, 2.2, 2.7), bus=(10.5, 2.5, 3.1), van=(5.6, 2.05, 2.3))[kind]
    ln, wd, top = spec; hx, hy = ln / 2, wd / 2
    if kind == 'bus':
        g.box(body, -hx, -hy, 0.45, hx, hy, top); g.box(dark, -hx + 0.3, -hy - 0.01, 1.75, hx - 0.3, hy + 0.01, 2.55); g.box(dark, -hx - 0.01, -hy + 0.15, 1.6, -hx, hy - 0.15, 2.6)
        for zz in (1.05, 1.45): g.box(dark, -hx, -hy - 0.012, zz, hx, hy + 0.012, zz + 0.07)
        fl = mat('bus flasher', (0.3, 0, 0), emit=(1.0, 0.05, 0.02), es=0.0); CTRL['flasher'] = bsdf(fl).inputs['Emission Strength']
        for wy in (-hy + 0.25, hy - 0.25): g.box(fl, -hx - 0.02, wy - 0.12, top - 0.35, -hx, wy + 0.12, top - 0.12); g.box(fl, hx, wy - 0.12, top - 0.35, hx + 0.02, wy + 0.12, top - 0.12)
    else:
        cab_l = 2.0 if kind != 'van' else 1.6
        g.box(body if kind != 'boxtruck' else colmat('paint', (0.75, 0.05, 0.03), 0.35), -hx, -hy + 0.1, 0.5, -hx + cab_l, hy - 0.1, 2.5 if kind != 'van' else top)
        g.box(DARKGLASS, -hx - 0.01, -hy + 0.22, 1.5, -hx + 0.02, hy - 0.22, 2.3 if kind != 'van' else top - 0.25)
        g.box(body, -hx + cab_l + (0.15 if kind != 'van' else 0), -hy, 0.75 if kind != 'van' else 0.5, hx, hy, top)
        if kind == 'garbage':
            g.hexa(body, [(hx, -hy, 0.75), (hx + 1.3, -hy, 0.9), (hx + 1.3, hy, 0.9), (hx, hy, 0.75), (hx, -hy, top), (hx + 0.7, -hy, top - 0.2), (hx + 0.7, hy, top - 0.2), (hx, hy, top)])
            g.box(dark, hx + 0.2, -hy + 0.15, 0.95, hx + 1.32, hy - 0.15, 1.9)
            bc = mat('beacon', (0.3, 0.15, 0), emit=(1.0, 0.5, 0.0), es=0.0); CTRL['beacon'] = bsdf(bc).inputs['Emission Strength']
            g.cyl(bc, -hx + 1.0, 0, 2.5, 2.68, 0.12, 8); g.cyl(bc, hx + 0.3, 0, top - 0.02, top + 0.16, 0.12, 8)
            g.box(colmat('paint', K.BLUE, 0.4), -hx + cab_l + 0.16, -hy - 0.01, 1.4, hx - 0.2, hy + 0.01, 1.9)
        if kind == 'sweeper':
            for wy in (-hy - 0.1, hy + 0.1): g.cyl(dark, -hx + 1.2, wy, 0.02, 0.2, 0.55, 12)
            bc = mat('beacon2', (0.3, 0.15, 0), emit=(1.0, 0.5, 0.0), es=8.0); g.cyl(bc, -hx + 1.0, 0, 2.5, 2.68, 0.12, 8)
    for wx in (-hx + 1.1, hx - 1.4) + ((hx - 2.5,) if ln > 7 else ()):
        for wy in (-hy + 0.05, hy - 0.05): g.tube(RUBBER, (wx, wy - 0.14, 0.48), (wx, wy + 0.14, 0.48), 0.48, n=12)
    for wy in (-hy + 0.35, hy - 0.35):
        g.box(lights[0], -hx - 0.02, wy - 0.18, 0.75, -hx, wy + 0.18, 0.98); g.box(lights[1], hx + (1.3 if kind == 'garbage' else 0), wy - 0.15, 0.95, hx + (1.33 if kind == 'garbage' else 0.02), wy + 0.15, 1.12)
    return ln

HAIR = [mat('Hair %d' % i, c, 0.55) for i, c in enumerate([(0.012, 0.009, 0.007), (0.035, 0.02, 0.01), (0.09, 0.06, 0.035), (0.25, 0.24, 0.23)])]
def loft(g, m, rings, n=14):
    """A closed body through ellipse rings (z, half depth along x, half width along y), bottom to top."""
    vs, fs = g._b(m); k = len(vs)
    for z, rx, ry in rings:
        for q in range(n): th = 2 * math.pi * q / n; vs.append((rx * math.cos(th), ry * math.sin(th), z))
    for i in range(len(rings) - 1):
        for q in range(n): q2 = (q + 1) % n; fs.append((k + i * n + q, k + i * n + q2, k + (i + 1) * n + q2, k + (i + 1) * n + q))
    fs.append(tuple(k + q for q in range(n))[::-1]); fs.append(tuple(k + (len(rings) - 1) * n + q for q in range(n)))
# 04:20 Nov 18: the people are Blender's CC0 Human Base Meshes (blender.org), posed and dressed by tools/people_bake.py
PEOPLE = {}
EYE = None
def people_lib():
    global EYE
    if not PEOPLE:
        import numpy as np
        D = np.load(os.path.join(HERE, 'assets', 'cc0', 'people', 'people.npz'))
        for k in D.files: PEOPLE[k] = D[k]
        EYE = mat('Eye', (0.05, 0.04, 0.03), 0.08)
    return PEOPLE
PHONE = []
# 04:58 Nov 18: the cast, baked by tools/cast_bake.py from the rigged ON LOCATION figures of 2026-10-28
CAST_WALK = ['cabbie', 'workgirl', 'wiseguy', 'writer', 'hustler', 'editor', 'killer', 'annieh', 'loretta', 'gown', 'bartender', 'susan', 'actress', 'discoking']   # oscar stoops mid stride; tough's bat reads wrong walking the street at 3 a.m. (05:33)
CAST_IDLE = CAST_WALK + ['oscar', 'clerk', 'blindwoman', 'tough']
CAST = {}; CAST_PENDING = []; CAST_SET = {}; MOVPH = {}
def cast_lib():
    if not CAST:
        with bpy.data.libraries.load(os.path.join(HERE, 'assets', 'cast', 'cast.blend')) as (src, dst): dst.objects = list(src.objects)
        for o in dst.objects: CAST[o.name] = o
    return CAST
def body_geo(g, key, h, wide, mats, flat=None, zmin=None):
    """One baked person scaled to height h; mats maps role name to material. flat squashes depth (a shadow on a blind)."""
    D = people_lib(); V = D[key + '_v'] * h; F = D[key + '_f']; Rr = D[key + '_r']; roles = list(D['roles'])
    V = V.copy(); V[:, 1] *= wide; V[:, 0] *= wide ** 0.5
    if flat is not None: V[:, 0] = V[:, 0] * flat
    if zmin is not None: V[:, 2] = V[:, 2].clip(zmin, None)
    for ri, rn in enumerate(roles):
        m = mats.get(rn)
        if m is None: continue
        sel = (Rr == ri)
        if zmin is not None: sel &= (V[F[:, 0], 2] > zmin + 1e-4) | (V[F[:, 2], 2] > zmin + 1e-4)
        idx = sel.nonzero()[0]
        if not len(idx): continue
        Fs = F[idx]; used = sorted(set(int(x) for x in Fs.ravel() if x >= 0)); mp = {u: i for i, u in enumerate(used)}
        g.mesh(m, [tuple(float(c) for c in V[u]) for u in used], [tuple(mp[int(x)] for x in f if x >= 0) for f in Fs])
    return V
def person_geo(g, col, r, umbrella=False, dogs=0, walk=False):
    """Someone 1.6 to 1.85 m tall, facing +x, origin between the feet."""
    h = r.uniform(1.58, 1.86); coat = colmat('coat', col, 0.7); legs = colmat('coat', (0.03, 0.03, 0.04), 0.7) if r.random() < 0.7 else colmat('coat', (0.10, 0.12, 0.2), 0.7)
    sk = r.choice(SKIN); st = r.uniform(0.12, 0.3)
    if R.ON:     # 04:58 Nov 18, MLow: "these people are awful". The people are his NEW YORKERS cast now (flower heads, no faces).
        long = r.random() < 0.5; hat = r.random() < 0.45; hat_c = coat if (r.random() < 0.5 if hat else False) else legs   # same draws as before, so the rest of the night is unchanged
        rv = random.Random(int(h * 1e6) + int(st * 1e5))
        name = rv.choice(CAST_WALK) if walk else rv.choice(CAST_IDLE)
        s_ = h * 1.06 / 1.88; lib = cast_lib()
        def one(tag):
            o = bpy.data.objects.new('cast %s %s' % (name, tag), lib['cast_%s_%s' % (name, tag)].data); scene.collection.objects.link(o); o.scale = (s_, s_, s_); CAST_PENDING.append(o); return o
        if walk:      # 05:35: the eight phases of his walk, and his idle for when he stops; apply_time shows one
            CAST_SET.clear(); CAST_SET.update(idle=one('idle'), phases=[one('w%d' % k) for k in range(8)], stride=0.95 * s_ * 1.88 / 1.75)
        else: one('idle')
    elif False:     # 04:20 Nov 18: the CC0 base-mesh bodies (tools/people_bake.py). MLow did not like them; kept for the record.
        long = r.random() < 0.5; hat = r.random() < 0.45; hat_c = coat if (r.random() < 0.5 if hat else False) else legs
        shoe = colmat('coat', (0.015, 0.015, 0.017), 0.35)
        rv = random.Random(int(h * 1e6) + int(st * 1e5)); sex = 'f' if rv.random() < 0.5 else 'm'
        pose = 'walk' if walk else ('phone' if rv.random() < 0.3 else 'stand')
        key = '%s_%s_%s_%s' % (sex, pose, 'long' if long else 'short', 'hat' if hat else 'hair')
        hair = HAIR[int(h * 1000) % len(HAIR)]; wide = rv.uniform(0.95, 1.12)
        people_lib(); body_geo(g, key, h, wide, {'skin': sk, 'hair': hair, 'hat': hat_c, 'coat': coat, 'legs': legs, 'shoe': shoe, 'eye': EYE})
        if long:      # the skirt of a long coat, hung from the hips to the knee
            s_ = h / 1.75; loft(g, coat, [(0.31 * h, 0.16 * s_ * wide ** 0.5, 0.215 * s_ * wide), (0.41 * h, 0.14 * s_ * wide ** 0.5, 0.2 * s_ * wide), (0.52 * h, 0.115 * s_ * wide ** 0.5, 0.175 * s_ * wide)], n=20)
        if pose == 'phone':
            hp = PEOPLE[key + '_h'] * h; hp = (hp[0] * wide ** 0.5 + 0.03, hp[1] * wide, hp[2] + 0.02)
            if not PHONE: PHONE.append(mat('phone screen', (0.02, 0.02, 0.03), 0.2, emit=(0.75, 0.85, 1.0), es=1.6))
            g.box(PHONE[0], hp[0] - 0.006, hp[1] - 0.035, hp[2] - 0.07, hp[0] + 0.006, hp[1] + 0.035, hp[2] + 0.07)
    elif False:
        long = r.random() < 0.5; hat = r.random() < 0.45; hat_c = coat if (r.random() < 0.5 if hat else False) else legs
        shoe = colmat('coat', (0.015, 0.015, 0.017), 0.5); zh = h * 0.5; zc = h * (0.36 if long else 0.47)
        for sy, sx in ((0.1, st), (-0.1, -st)):
            g.tube(legs, (sx * 0.9, sy, 0.07), (sx * 0.15, sy * 0.9, zh), 0.06, 0.085, n=10); g.blob(shoe, sx * 0.9 + 0.06, sy, 0.05, 0.13, 0.055, 0.05, 8, 4)
        g.tube(coat, (0.0, 0.0, zc), (0.0, 0.0, zh + 0.02), 0.2 if long else 0.17, 0.165, n=14)                       # coat skirt, flaring a little
        loft(g, coat, [(zh - 0.02, 0.105, 0.17), (h * 0.6, 0.1, 0.16), (h * 0.7, 0.115, 0.185), (h * 0.78, 0.105, 0.2), (h * 0.815, 0.07, 0.15), (h * 0.83, 0.05, 0.07)])   # hips, waist, chest, shoulders
        for sy, sw in ((-1, st), (1, -st)):
            g.tube(coat, (0.0, sy * 0.2, h * 0.79), (sw * 0.75, sy * 0.25, h * 0.5), 0.058, 0.047, n=10); c_ = (sw * 0.78, sy * 0.25, h * 0.47); g.blob(sk, c_[0], c_[1], c_[2], 0.04, 0.035, 0.05, 6, 4)
        g.tube(sk, (0.01, 0, h * 0.82), (0.02, 0, h * 0.88), 0.05, 0.048, n=8)
        g.blob(sk, 0.025, 0, h * 0.935, 0.098, 0.085, 0.118, 12, 8)
        if hat: g.blob(hat_c, 0.01, 0, h * 0.965, 0.108, 0.098, 0.085, 12, 6)
        else: g.blob(HAIR[int(h * 1000) % len(HAIR)], -0.018, 0, h * 0.95, 0.102, 0.092, 0.103, 12, 6)                 # hair, back and top of the head
    else:
      g.hexa(legs, [(-0.08 + st, 0.03, 0), (0.06 + st, 0.03, 0), (0.06 + st, 0.17, 0), (-0.08 + st, 0.17, 0), (-0.07, 0.03, h * 0.5), (0.07, 0.03, h * 0.5), (0.07, 0.17, h * 0.5), (-0.07, 0.17, h * 0.5)])
      g.hexa(legs, [(-0.08 - st, -0.17, 0), (0.06 - st, -0.17, 0), (0.06 - st, -0.03, 0), (-0.08 - st, -0.03, 0), (-0.07, -0.17, h * 0.5), (0.07, -0.17, h * 0.5), (0.07, -0.03, h * 0.5), (-0.07, -0.03, h * 0.5)])
      long = r.random() < 0.5
      g.hexa(coat, [(-0.13, -0.22, h * (0.36 if long else 0.47)), (0.13, -0.22, h * (0.36 if long else 0.47)), (0.13, 0.22, h * (0.36 if long else 0.47)), (-0.13, 0.22, h * (0.36 if long else 0.47)),
                    (-0.11, -0.2, h * 0.84), (0.12, -0.2, h * 0.84), (0.12, 0.2, h * 0.84), (-0.11, 0.2, h * 0.84)])
      for sy, sw in ((-1, st), (1, -st)):
          g.beam(coat, (0.0, sy * 0.25, h * 0.82), (sw * 0.8, sy * 0.27, h * 0.5), 0.09, 0.1)
      g.blob(sk, 0.02, 0, h * 0.93, 0.095, 0.085, 0.115, 8, 5)
      if r.random() < 0.45: g.blob(coat if r.random() < 0.5 else legs, 0.0, 0, h * 0.955, 0.105, 0.095, 0.1, 8, 4)          # a hat or a hood
    if umbrella:
        g.tube(IRON, (0.15, 0.2, h * 0.6), (0.15, 0.2, h + 0.35), 0.012, n=5); g.cyl(colmat('coat', (0.02, 0.02, 0.025), 0.4), 0.15, 0.2, h + 0.2, h + 0.48, 0.62, 10, r1=0.03)
    for k in range(dogs):
        dx = 0.9 + k * 0.55; dy = (-0.5, 0.45, 0.0)[k % 3]; dc = colmat('coat', [(0.5, 0.36, 0.2), (0.05, 0.05, 0.05), (0.8, 0.78, 0.7)][k % 3], 0.8); sz = (1.0, 0.6, 0.8)[k % 3]
        g.box(dc, dx - 0.3 * sz, dy - 0.1 * sz, 0.3 * sz, dx + 0.3 * sz, dy + 0.1 * sz, 0.55 * sz); g.box(dc, dx + 0.25 * sz, dy - 0.09 * sz, 0.5 * sz, dx + 0.5 * sz, dy + 0.09 * sz, 0.75 * sz)
        for lx in (-0.25, 0.22): g.box(dc, dx + lx * sz, dy - 0.08 * sz, 0, dx + lx * sz + 0.06, dy + 0.08 * sz, 0.3 * sz)
        g.beam(IRON, (0.1, 0.25, h * 0.5), (dx, dy, 0.55 * sz), 0.008, 0.008)


# 23:40 Nov 19, MLow: "the cats and dogs need to look more realistic so find better cc0 glbs". No realistic CC0 cat or
# dog exists on Poly Haven or Sketchfab (checked: statues, skulls, catfish). The cat is MLow's own orange tabby (Tripo,
# made for ONLY IN NEW YORK), the rat is Poly Haven's street_rat (CC0, Sean Buckley). Both face +x like the old shapes.
ANIMAL_GLB = {'cat': ('assets/animals/cat_tabby_mlow_tripo.glb', 0.30, 'h'), 'rat': ('assets/animals/street_rat_polyhaven_cc0.glb', 0.24, 'l')}
_ANIMAL_SRC = {}
def glb_animal(kind, name):
    path, size, axis = ANIMAL_GLB[kind]; path = os.path.join(HERE, path)
    if not os.path.exists(path): return None
    if kind not in _ANIMAL_SRC:
        before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path); new = [o for o in bpy.data.objects if o not in before]
        ms = [o for o in new if o.type == 'MESH']; bpy.context.view_layer.update()
        for o in ms: o.data = o.data.copy(); o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix.Identity(4)
        if len(ms) > 1:
            bpy.ops.object.select_all(action='DESELECT')
            for o in ms: o.select_set(True)
            bpy.context.view_layer.objects.active = ms[0]; bpy.ops.object.join()
        src = ms[0]
        for o in new:
            if o is not src and o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)
        co = [v.co for v in src.data.vertices]; lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co))); hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
        d = hi - lo
        if d.y > d.x * 1.3: src.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z')); co = [v.co for v in src.data.vertices]; lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co))); hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co))); d = hi - lo
        k = size / (d.z if axis == 'h' else max(d.x, d.y))
        src.data.transform(Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
        src.data.transform(Matrix.Scale(k, 4))
        for p_ in src.data.polygons: p_.use_smooth = True
        if src.name in scene.collection.objects: scene.collection.objects.unlink(src)
        for c in list(src.users_collection): c.objects.unlink(src)
        _ANIMAL_SRC[kind] = src
    o = _ANIMAL_SRC[kind].copy(); o.name = name; scene.collection.objects.link(o); return o

def cat_geo(g):
    c = colmat('cat', (0.75, 0.38, 0.08), 0.8)
    if R.ON:     # 04:24 Nov 18 (Astra: the cat was an ambiguous prop): a body you can read, 0.26 m at the shoulder, mid stride
        for (x, z, rx, ry, rz) in ((-0.1, 0.2, 0.15, 0.075, 0.075), (0.07, 0.215, 0.12, 0.07, 0.08)): g.blob(c, x, 0, z, rx, ry, rz, 12, 7)   # haunch and chest
        g.blob(c, 0.235, 0, 0.29, 0.06, 0.052, 0.052, 12, 7); g.blob(c, 0.285, 0, 0.278, 0.03, 0.028, 0.024, 8, 5)                                 # head and muzzle
        for sy in (-0.028, 0.028): g.tube(c, (0.225, sy, 0.325), (0.215, sy * 1.25, 0.37), 0.02, 0.002, n=6)                                     # ears
        for (x0, y0, x1) in ((0.11, -0.035, 0.18), (0.09, 0.035, 0.02), (-0.15, -0.035, -0.22), (-0.13, 0.035, -0.06)):                          # legs: front left forward, rear right back
            g.tube(c, (x0, y0, 0.2), (x1, y0, 0.012), 0.024, 0.015, n=8); g.blob(c, x1 + 0.012, y0, 0.012, 0.022, 0.016, 0.012, 6, 4)
        pts = [(-0.23, 0, 0.23), (-0.33, 0, 0.26), (-0.39, 0, 0.33), (-0.4, 0.02, 0.41)]
        for a_, b_ in zip(pts, pts[1:]): g.tube(c, a_, b_, 0.017, 0.014, n=8)
        return
    g.box(c, -0.2, -0.07, 0.14, 0.2, 0.07, 0.3); g.box(c, 0.16, -0.065, 0.26, 0.32, 0.065, 0.4); g.beam(c, (-0.2, 0, 0.28), (-0.38, 0, 0.5), 0.035, 0.035)
    for lx in (-0.17, 0.13): g.box(c, lx, -0.06, 0, lx + 0.05, 0.06, 0.15)
    for sy in (-0.045, 0.045): g.box(c, 0.2, sy - 0.02, 0.4, 0.24, sy + 0.02, 0.45)
def rat_geo(g):
    c = colmat('rat', (0.09, 0.075, 0.065), 0.8); g.blob(c, 0, 0, 0.05, 0.11, 0.04, 0.045, 6, 4); g.beam(c, (-0.1, 0, 0.03), (-0.26, 0, 0.02), 0.012, 0.012)

MOV = []       # (mover dict, empty, [lights])
def movers():
    hl_on = mat('headlamp on', (1, 1, 1), emit=(1.0, 0.95, 0.85), es=40.0); tl_on = mat('tail on', (0.3, 0, 0), emit=(1.0, 0.03, 0.02), es=6.0)
    r = random.Random(K.SEED + 3)
    for i, m in enumerate(K.MOVERS):
        if m['kind'] == 'note': continue
        e = bpy.data.objects.new('mover %03d %s' % (i, m['who']), None); scene.collection.objects.link(e); g = Geo(); lights = []
        k = m['kind']
        if k == 'person': person_geo(g, m['col'], r, m.get('umbrella', False), m.get('dogs', 0), walk=True)
        elif k in ('cat', 'rat'):
            ao = glb_animal(k, 'mover %d %s' % (i, k)) if R.ON else None
            if ao: CAST_PENDING.append(ao)
            elif k == 'cat': cat_geo(g)
            else: rat_geo(g)
        else:
            if R.ON and k in ('car', 'cab'):      # 05:58: a model, with lamps you can see lit
                o, ln = glb_car('car', m['col'], K.SEED + 900 + i, taxi=(k == 'cab'), name='mover %d' % i); CAST_PENDING.append(o); hx_ = ln / 2
                for wy in (-0.62, 0.62):
                    g.box(hl_on, -hx_ - 0.03, wy - 0.13, 0.66, -hx_ + 0.02, wy + 0.13, 0.78); g.box(tl_on, hx_ - 0.02, wy - 0.12, 0.8, hx_ + 0.03, wy + 0.12, 0.92)
            else: ln = car_geo(g, k, m['col'], (hl_on, tl_on)) if k in ('car', 'cab') else truck_geo(g, k, m['col'], (hl_on, tl_on))
            for wy in (-0.6, 0.6):
                li = bpy.data.lights.new('headlight', 'SPOT'); li.energy = 900; li.spot_size = math.radians(50); li.spot_blend = 0.5; li.color = (1.0, 0.95, 0.85); li.shadow_soft_size = 0.06
                o = bpy.data.objects.new('headlight', li); scene.collection.objects.link(o); o.parent = e; o.location = (-ln / 2 - 0.05, wy, 0.75); o.rotation_euler = (0, math.radians(-84), 0); lights.append(o)
        if m.get('small'): e.scale = (0.72, 0.72, 0.72)
        objs = g.flush('mv%03d' % i, parent=e)
        for o in CAST_PENDING: o.parent = e; objs.append(o)
        if CAST_SET: MOVPH[len(MOV)] = dict(CAST_SET); CAST_SET.clear()
        CAST_PENDING.clear(); MOV.append((m, e, objs + lights, k))
        if k == 'person' and R.ON:
            for o in objs:
                for p_ in o.data.polygons: p_.use_smooth = True
        if k in ('car', 'cab'): R.soften(objs)
        elif k not in ('person', 'cat', 'rat'): R.soften(objs, 0.05, 2)

PARKED = []
COVERED = [i for i, c in enumerate(K.CARS) if c['side'] == 'S' and c['leave'] is None and c['arrive'] is None][2]
# 05:58 Nov 18, MLow: "fix the cars ... use real cc0 glbs and the mlow taxi cabs we made". Every car is a model now
# (tools/car_bake.py -> assets/cars/cars.blend): his MoMLOW cabs in their yellow and the MLOW CAB CO. checker as the
# taxis, the same bodies repainted as private cars, Poly Haven's CC0 covered car, his towed tarp car and one rusted wreck.
CARLIB = {}
CARMODELS = dict(sedan=['camry', 'hcab'], car=['camry', 'hcab', 'escape', 'camry'], hatch=['camry'], suv=['escape'], van=['sienna', 'nv200'])
PAINTLIN = dict(silver=(0.40, 0.41, 0.42), black=(0.01, 0.01, 0.012), white=(0.68, 0.68, 0.64), navy=(0.013, 0.023, 0.065), maroon=(0.105, 0.008, 0.012),
                grey=(0.105, 0.112, 0.118), green=(0.02, 0.048, 0.034), beige=(0.30, 0.25, 0.16))
def car_lib():
    if not CARLIB:
        with bpy.data.libraries.load(os.path.join(HERE, 'assets', 'cars', 'cars.blend')) as (src, dst): dst.objects = list(src.objects)
        for o in dst.objects: CARLIB[o.name] = o
    return CARLIB
def glb_car(kind, col, seed, taxi=False, name='car'):
    """A car model pointing along -x like the procedural ones, centred, wheels on z = 0. Returns (object, length)."""
    lib = car_lib(); r = random.Random(seed)
    if taxi: key = 'car_checker_own' if r.random() < 0.34 else 'car_%s_taxi' % r.choice(['camry', 'escape', 'sienna', 'nv200', 'hcab', 'camry'])
    elif kind in ('rusty', 'towed'): key = 'car_%s_own' % kind
    else:
        model = r.choice(CARMODELS.get(kind, ['camry'])); paints = [n.split('_')[2] for n in lib if n.startswith('car_%s_' % model) and not n.endswith(('_taxi', '_own'))]
        key = 'car_%s_%s' % (model, min(paints, key=lambda pn: sum((a - b) ** 2 for a, b in zip(PAINTLIN[pn], col)) + r.uniform(0, 0.004)))
    src = lib[key]; o = bpy.data.objects.new(name + ' ' + key, src.data); scene.collection.objects.link(o); o.rotation_euler = (0, 0, math.pi)
    return o, src.dimensions.x
_STILL = [i for i, c in enumerate(K.CARS) if c['leave'] is None and c['arrive'] is None and i != COVERED]
RUSTY = [i for i in _STILL if K.CARS[i]['side'] == 'N'][1]; TOWED = [i for i in _STILL if K.CARS[i]['side'] == 'S'][-1]   # the wreck and the towed car never move
def parked_cars():
    for i, c in enumerate(K.CARS):
        if R.ON and i != COVERED:
            e = bpy.data.objects.new('parked %d' % i, None); scene.collection.objects.link(e)
            s_ = 1 if c['side'] == 'N' else -1; rr = random.Random(K.SEED + 400 + i)
            e.location = (c['x'], s_ * (K.ROAD - 1.0 - rr.uniform(0.0, 0.22)), 0.0); e.rotation_euler = (0, 0, rr.uniform(-0.035, 0.035))   # never quite square to the kerb
            special = ('rusty' if i == RUSTY else 'towed' if i == TOWED else None) if (c['leave'] is None and c['arrive'] is None) else None
            o, ln = glb_car(special or c['kind'], c['col'], K.SEED + 500 + i, name='parked %d' % i); o.parent = e; PARKED.append((c, [o])); continue
        if R.ON and i == COVERED:      # 23:50: one car on the block lives under a tarp (Poly Haven covered_car, CC0)
            sgn = 1 if c['side'] == 'N' else -1; o = R.place('covered_car', (c['x'], sgn * (K.ROAD - 1.05), 0.0), rotz=math.pi / 2, fit=('y', 4.5), name='parked %d covered' % i)
            if o is not None: PARKED.append((c, [o])); continue
        g = Geo(); car_geo(g, c['kind'], c['col']); e = bpy.data.objects.new('parked %d' % i, None); scene.collection.objects.link(e)
        s = 1 if c['side'] == 'N' else -1; e.location = (c['x'], s * (K.ROAD - 1.05), 0.0); objs = g.flush('parked%d' % i, parent=e); PARKED.append((c, objs)); R.soften(objs)

CATSIT = []
def cat_in_window():
    g = Geo(); c = colmat('cat', (0.75, 0.38, 0.08), 0.8); F = street_frame(K.B['N1'])
    p = F.p(2.2, -0.35, 0.64); ao = glb_animal('cat', 'cat in window glb') if R.ON else None
    if ao:          # sits on the crate looking out at the street
        ao.location = p; CATSIT.append(ao)
        fwd = Vector(F.p(2.2, -1.35, 0.64)) - Vector(p); ao.rotation_euler = (0, 0, math.atan2(fwd.y, fwd.x))
    else:
        g.blob(c, p[0], p[1], p[2] + 0.16, 0.13, 0.2, 0.17, 8, 5); g.blob(c, p[0], p[1] - 0.16, p[2] + 0.36, 0.085, 0.085, 0.08, 8, 5)
        for dx in (-0.045, 0.045): g.box(c, p[0] + dx - 0.02, p[1] - 0.19, p[2] + 0.42, p[0] + dx + 0.02, p[1] - 0.15, p[2] + 0.48)
    F.box(colmat('crate', (0.75, 0.1, 0.05), 0.6), 1.8, -0.7, 0.17, 2.6, -0.1, 0.64, g)
    CATSIT.extend(g.flush('cat in window'))

# ------------------------------------------------------------------ rain
RAINOBJ = []
def rain(cam_loc):
    m = bpy.data.materials.new('Rain'); m.use_nodes = True; b = bsdf(m); b.inputs['Base Color'].default_value = (0.8, 0.85, 0.9, 1); b.inputs['Alpha'].default_value = 0.13; b.inputs['Roughness'].default_value = 0.1
    b.inputs['Emission Color'].default_value = (0.8, 0.85, 1.0, 1); b.inputs['Emission Strength'].default_value = 0.05; MATS['Rain'] = m
    g = Geo(); r = random.Random(K.SEED + 11)
    for k in range(5200):
        x = cam_loc[0] + r.uniform(1.5, 70) ** 1.0; y = r.uniform(-9, 9); z = r.uniform(0.2, 16); ln = r.uniform(0.5, 1.1); wd = 0.004 + 0.0006 * (x - cam_loc[0])
        g.quad(m, (x, y - wd, z), (x, y + wd, z), (x + 0.06 * ln, y + wd, z + ln), (x + 0.06 * ln, y - wd, z + ln))
    RAINOBJ.extend(g.flush('rain'))


# ------------------------------------------------------------------ what is inside the shops
PACK = [colmat('pack', tuple(0.55 * v + 0.45 * sum(c) / 3 for v in c) if R.ON else c, 0.45) for c in [(0.9, 0.1, 0.1), (1.0, 0.75, 0.05), (0.1, 0.35, 0.9), (0.1, 0.6, 0.25), (0.95, 0.4, 0.05), (0.9, 0.9, 0.85), (0.5, 0.1, 0.6), (0.05, 0.6, 0.7), (0.95, 0.3, 0.5)]]
SHELF = mat('Shelf', (0.78, 0.78, 0.76), 0.5)
PETAL = [colmat('petal', c, 0.6) for c in [K.PINK, (1.0, 0.75, 0.0), (0.95, 0.95, 0.9), K.BLUE, (1.0, 0.35, 0.05), K.ACID, (0.6, 0.15, 0.8)]]
STEM = colmat('stem', (0.05, 0.3, 0.08), 0.7); BUCKET = colmat('bucket', (0.02, 0.02, 0.02), 0.5)
# INSIDE (defined above): (objects, t0, t1), people and things that are only there for part of the night
pr = random.Random(K.SEED + 21)
GOODS = None
def goods():
    """06:16 Nov 18 (MLow: keep editing; the shelves were pastel blocks): package colours as they are on a real shelf,
    deep and printed, and the labels that break each one up."""
    global GOODS
    if GOODS is None:
        cols = [(0.55, 0.05, 0.04), (0.75, 0.32, 0.03), (0.85, 0.62, 0.05), (0.04, 0.10, 0.32), (0.05, 0.28, 0.10), (0.25, 0.12, 0.05), (0.80, 0.78, 0.72),
                (0.03, 0.03, 0.035), (0.30, 0.06, 0.32), (0.02, 0.35, 0.45), (0.72, 0.20, 0.30), (0.45, 0.42, 0.10)]
        GOODS = dict(body=[colmat('goods', c, 0.4) for c in cols], label=[colmat('label', c, 0.55) for c in [(0.88, 0.86, 0.8), (0.95, 0.85, 0.3), (0.9, 0.9, 0.9), (0.05, 0.05, 0.06), (0.8, 0.1, 0.08)]],
                     glass=colmat('jar glass', (0.55, 0.35, 0.12), 0.08), lid=colmat('lid', (0.6, 0.6, 0.62), 0.3, 0.8), foil=colmat('chip bag', (0.85, 0.6, 0.05), 0.2, 0.5),
                     strip=mat('price strip', (0.92, 0.92, 0.9), 0.5))
    return GOODS
def stock(F, u, z, depth, wdt, h, pk):
    """One facing of goods on a shelf at height z, from u for wdt metres."""
    Gd = goods(); kind = pr.random(); body = pk if pk not in PACK else pr.choice(Gd['body']); lab = pr.choice(Gd['label'])
    if kind < 0.3:                                     # boxes, two or three deep, each with a printed panel on its face
        for q in range(max(1, int(wdt / 0.085))):
            a = u + q * 0.085; hh = h * pr.uniform(0.9, 1.0); F.box(body, a, depth - 0.24, z, a + 0.075, depth - 0.02, z + hh)
            F.box(lab, a + 0.008, depth - 0.019, z + hh * 0.35, a + 0.067, depth - 0.016, z + hh * 0.8)
    elif kind < 0.55:                                  # cans stacked two high, a paper label round the middle
        rr_ = pr.uniform(0.032, 0.042); hh = min(h * 0.5, 0.13)
        for q in range(max(1, int(wdt / (2 * rr_ + 0.006)))):
            for st in range(2):
                if pr.random() < 0.08: continue
                c_ = F.p(u + rr_ + q * (2 * rr_ + 0.006), depth - 0.06, 0); zz = z + st * hh
                G.cyl(Gd['lid'], c_[0], c_[1], zz, zz + hh, rr_, 12); G.cyl(body, c_[0], c_[1], zz + hh * 0.12, zz + hh * 0.88, rr_ * 1.02, 12)
    elif kind < 0.7:                                   # jars with lids
        for q in range(max(1, int(wdt / 0.085))):
            c_ = F.p(u + 0.04 + q * 0.085, depth - 0.06, 0); G.cyl(Gd['glass'] if pr.random() < 0.5 else body, c_[0], c_[1], z, z + 0.12, 0.038, 12)
            G.cyl(Gd['lid'], c_[0], c_[1], z + 0.12, z + 0.145, 0.036, 12); G.cyl(lab, c_[0], c_[1], z + 0.03, z + 0.09, 0.039, 12)
    elif kind < 0.85:                                  # bottles
        rr_ = min(0.04, wdt / 4)
        for q in range(max(1, int(wdt / (2 * rr_ + 0.01)))):
            if pr.random() < 0.12: continue
            c_ = F.p(u + rr_ + q * (2 * rr_ + 0.01), depth - 0.08, 0); G.cyl(body, c_[0], c_[1], z, z + h * 0.7, rr_, 12)
            G.cyl(body, c_[0], c_[1], z + h * 0.7, z + h * 0.95, rr_ * 0.4, 10, r1=rr_ * 0.32); G.cyl(lab, c_[0], c_[1], z + h * 0.2, z + h * 0.5, rr_ * 1.02, 12)
    else:                                              # chip bags, puffed and leaning
        for q in range(max(1, int(wdt / 0.11))):
            c_ = F.p(u + 0.055 + q * 0.11, depth - 0.07, 0); G.blob(pr.choice([Gd['foil'], body]), c_[0], c_[1], z + 0.13, 0.05, 0.035, 0.13, 10, 6, jit=0.06, rr=pr)
def shelves(F, length, depth=0.38, levels=5, z0=0.4, dz=0.48, packs=PACK, fill=1.0):
    """A run of shelves standing at F's origin, facing out along +v."""
    F.box(SHELF, 0, -0.03, 0.17, length, 0, z0 + levels * dz)
    if R.ON:
        for lv in range(levels):
            z = z0 + lv * dz; F.box(SHELF, 0, 0, z - 0.03, length, depth, z); F.box(goods()['strip'], 0, depth, z - 0.06, length, depth + 0.008, z)
            u = 0.03
            while u < length - 0.1:
                wdt = pr.uniform(0.15, 0.4); h = pr.uniform(0.2, min(0.36, dz - 0.08))
                if pr.random() < fill * 0.95: stock(F, u, z, depth, min(wdt, length - 0.05 - u), h, pr.choice(packs))
                u += wdt + pr.uniform(0.01, 0.04)
        return
    for lv in range(levels):
        z = z0 + lv * dz; F.box(SHELF, 0, 0, z - 0.03, length, depth, z); u = 0.03
        while u < length - 0.1:
            wdt = pr.uniform(0.09, 0.24); h = pr.uniform(0.16, 0.38)
            if pr.random() < fill:
                pk = pr.choice(packs)
                if R.ON and pr.random() < 0.45:     # 04:24 (Astra: grids of coloured blocks): a row of bottles or cans, some stock missing
                    rr_ = min(0.045, wdt / 4); n_ = max(1, int(wdt / (2 * rr_ + 0.01)))
                    for q in range(n_):
                        if pr.random() < 0.85:
                            c_ = F.p(u + rr_ + q * (2 * rr_ + 0.01), depth - 0.1, 0); G.cyl(pk, c_[0], c_[1], z, z + h * 0.8, rr_, 10)
                            G.cyl(pk, c_[0], c_[1], z + h * 0.8, z + h, rr_ * 0.4, 8, r1=rr_ * 0.35)
                else: F.box(pk, u, depth - 0.2 - pr.uniform(0, 0.08), z, u + wdt, depth - 0.02 - pr.uniform(0, 0.05), z + h)
            u += wdt + pr.uniform(0.005, 0.03)
KRAFT = mat('kraft paper', (0.50, 0.38, 0.24), 0.8); CELLO = mat('cellophane', (0.9, 0.92, 0.95), 0.05)
def bouquet(g, x, y, z, m, n=9, spread=0.14):
    if R.ON:     # 06:00 Nov 18 (MLow: the deli): bunches in kraft paper in a bucket, stems you can see, heads with layered petals
        g.cyl(BUCKET, x, y, z, z + 0.36, 0.15, 16); g.cyl(STEEL, x, y, z + 0.33, z + 0.36, 0.155, 16)
        for q in range(max(2, n // 4)):
            a = 2 * math.pi * q / max(2, n // 4) + pr.uniform(-0.3, 0.3); cx, cy = x + 0.06 * math.cos(a), y + 0.06 * math.sin(a)
            g.tube(KRAFT, (cx, cy, z + 0.25), (cx + 0.05 * math.cos(a), cy + 0.05 * math.sin(a), z + 0.58), 0.035, 0.085, n=10, caps=False)
            for k in range(6):
                b2 = a + pr.uniform(-0.6, 0.6); rr = pr.uniform(0.01, 0.07); hx_, hy_ = cx + rr * math.cos(b2), cy + rr * math.sin(b2); hz = z + 0.6 + pr.uniform(0, 0.14)
                g.tube(STEM, (cx, cy, z + 0.3), (hx_, hy_, hz), 0.004, n=4, caps=False)
                g.blob(m, hx_, hy_, hz, 0.032, 0.032, 0.022, 10, 4, jit=0.12, rr=pr); g.blob(m, hx_, hy_, hz + 0.012, 0.022, 0.022, 0.018, 8, 4, jit=0.15, rr=pr)
                if k % 2: g.blob(STEM, hx_ + 0.03, hy_, hz - 0.05, 0.035, 0.012, 0.006, 6, 3)
        return
    g.cyl(BUCKET, x, y, z, z + 0.36, 0.15, 10); g.blob(STEM, x, y, z + 0.46, 0.15, 0.15, 0.16, 6, 4)
    for q in range(n):
        a = pr.uniform(0, 6.28); rr = pr.uniform(0, spread); g.blob(m, x + rr * math.cos(a), y + rr * math.sin(a), z + 0.56 + pr.uniform(0, 0.09), 0.05, 0.05, 0.05, 5, 3)
def stool(F, u, v, seat):
    c = F.p(u, v, 0); G.cyl(STEEL, c[0], c[1], 0.17, 0.75, 0.03, 6); G.cyl(seat, c[0], c[1], 0.75, 0.82, 0.19, 10); G.cyl(STEEL, c[0], c[1], 0.17, 0.2, 0.2, 10)
def figure(F, u, v, face_du, face_dv, col, t0=0, t1=480, z=0.17, seed=0):
    g = Geo(); person_geo(g, col, random.Random(K.SEED + 100 + seed + len(INSIDE))); gg = Geo(); c = F.p(u, v, z); gg.merge(g, c, F.heading(face_du, face_dv))
    objs = gg.flush('inside %d' % len(INSIDE))
    for o in CAST_PENDING: o.location = c; o.rotation_euler = (0, 0, F.heading(face_du, face_dv)); objs.append(o)
    CAST_PENDING.clear()
    if R.ON:
        for o in objs:
            for p_ in o.data.polygons: p_.use_smooth = True      # 00:00: the people in the shops were faceted
    INSIDE.append((objs, t0, t1))
def pendant(F, u, v, light, z=2.35):
    c = F.p(u, v, 0); G.tube(IRON, (c[0], c[1], z + 0.2), (c[0], c[1], 3.3), 0.008, n=4); G.cyl(IRON, c[0], c[1], z + 0.02, z + 0.22, 0.2, 10, r1=0.05); G.cyl(light, c[0], c[1], z, z + 0.02, 0.17, 10)

FRUIT = ['food_apple_01', 'food_lime_01', 'lemon', 'yellow_onion', 'food_avocado_01', 'food_pears_asian_01', 'sweet_potato', 'food_apple_01']
def fruit_pile(pid, F, ua, ub, va, vb, z, r):
    """A crate heaped with one kind of CC0 fruit: a packed layer, then a smaller layer on top, each piece turned at random."""
    me, d = R.proto(pid); dx = max(d[0], d[1]) * 0.86; dz = d[2] * 0.7
    for layer in range(4):
        inset = layer * dx * 0.45; nu = int((ub - ua - 2 * inset) / dx); nv = int((vb - va - 2 * inset) / dx)
        for i in range(max(0, nu)):
            for j in range(max(0, nv)):
                if layer and r.random() < 0.25: continue
                uu = ua + inset + dx * (i + 0.5) + r.uniform(-0.01, 0.01); vv = va + inset + dx * (j + 0.5) + r.uniform(-0.01, 0.01)
                o = R.place(pid, F.p(uu, vv, z + layer * dz), rotz=r.uniform(0, 6.28), scale=r.uniform(0.92, 1.08)); o.rotation_euler = (r.uniform(-0.4, 0.4), r.uniform(-0.4, 0.4), o.rotation_euler[2])
def deli(F, u0, u1, sign):
    """06:00 Nov 18, MLow: "i also want the deli to look more realistic with better looking low poly food". A fruit stand on
    the pavement in crates on green turf, Poly Haven's CC0 fruit and bread; a glass deli case with cold cuts and a slicer
    and a menu board; bottles and cans in the drinks fridge; bananas and a basket of rolls by the register; vinyl tile."""
    if not R.ON: return
    r = random.Random(K.SEED + 717); wd = u1 - u0
    TURF = mat('fruit stand turf', (0.012, 0.075, 0.018), 1.0); CRATE = mat('crate wood', (0.38, 0.27, 0.15), 0.8)
    # the fruit stand: three tiers stepping up toward the window, eight crates a tier
    s0 = u0 + 3.7; n = min(8, int((wd - 4.6) / 0.53))
    for tier in range(3):
        v0 = 1.25 - tier * 0.36; zt = 0.55 + tier * 0.2
        F.box(WOOD, s0 - 0.05, v0 - 0.36, 0.16, s0 + n * 0.53 + 0.02, v0, zt - 0.02); F.box(TURF, s0 - 0.07, v0 - 0.37, zt - 0.02, s0 + n * 0.53 + 0.04, v0 + 0.03, zt)
        if tier == 0: F.box(TURF, s0 - 0.07, v0, 0.2, s0 + n * 0.53 + 0.04, v0 + 0.03, zt)         # the turf hangs down the front
        for k in range(n):
            ua, ub = s0 + k * 0.53, s0 + k * 0.53 + 0.5; va, vb = v0 - 0.34, v0 - 0.02
            for a_, b_ in ((ua, ua + 0.02), (ub - 0.02, ub)): F.box(CRATE, a_, va, zt, b_, vb, zt + 0.08)
            for a_, b_ in ((va, va + 0.02), (vb - 0.02, vb)): F.box(CRATE, ua, a_, zt, ub, b_, zt + 0.08)
            F.box(CRATE, ua, va, zt, ub, vb, zt + 0.015)
            fruit_pile(FRUIT[(k + tier * 3) % len(FRUIT)], F, ua + 0.02, ub - 0.02, va + 0.02, vb - 0.02, zt + 0.015, r)
            if k % 3 == 1: F.box(mat('price card', (0.9, 0.9, 0.86), 0.7), (ua + ub) / 2 - 0.06, vb + 0.005, zt + 0.02, (ua + ub) / 2 + 0.06, vb + 0.01, zt + 0.1)
    for k in range(3): R.place('bananas', F.p(s0 + 0.6 + k * 1.4, 1.25 - 2 * 0.36 - 0.17, 0.95 + 0.02), rotz=F.rotz() + r.uniform(-0.3, 0.3), fit=('x', 0.32))
    # vinyl tile on the shop floor
    tile = mat('vinyl tile', (0.6, 0.58, 0.54), 0.35); nt = tile.node_tree; b = nt.nodes['Principled BSDF']; geo = nt.nodes.new('ShaderNodeNewGeometry')
    ck = nt.nodes.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 1.0 / 0.3 / 2 * 2; ck.inputs['Color1'].default_value = (0.58, 0.56, 0.51, 1); ck.inputs['Color2'].default_value = (0.3, 0.3, 0.29, 1)
    sc_ = nt.nodes.new('ShaderNodeVectorMath'); sc_.operation = 'SCALE'; sc_.inputs['Scale'].default_value = 1.0 / 0.6; nt.links.new(geo.outputs['Position'], sc_.inputs[0]); nt.links.new(sc_.outputs[0], ck.inputs['Vector']); nt.links.new(ck.outputs['Color'], b.inputs['Base Color'])
    F.box(tile, u0, -6.08, 0.17, u1, -0.05, 0.176)
    # the deli case at the back right, the slicer, the menu board
    ca, cb = u0 + wd * 0.56, u1 - 0.8; v1 = -4.15
    F.box(STEEL, ca, v1 - 0.85, 0.17, cb, v1, 0.78); F.box(mat('case light', (1, 1, 1), emit=(1.0, 0.95, 0.85), es=4.0), ca + 0.05, v1 - 0.8, 1.2, cb - 0.05, v1 - 0.6, 1.22)
    CG = MATS.get('Car glass') or DARKGLASS
    F.box(CG, ca, v1 - 0.02, 0.78, cb, v1, 1.22); F.box(CG, ca, v1 - 0.85, 1.22, cb, v1, 1.24)
    for a_ in (ca, cb - 0.02): F.box(STEEL, a_, v1 - 0.85, 0.78, a_ + 0.02, v1, 1.24)
    meats = [colmat('ham', (0.78, 0.42, 0.40), 0.5), colmat('salami', (0.45, 0.10, 0.08), 0.55), colmat('turkey', (0.85, 0.75, 0.62), 0.5), colmat('cheese', (0.95, 0.78, 0.25), 0.45), colmat('bologna', (0.80, 0.5, 0.48), 0.5), colmat('provolone', (0.93, 0.86, 0.6), 0.5)]
    uu = ca + 0.15
    while uu < cb - 0.4:
        m_ = r.choice(meats); ln = r.uniform(0.18, 0.32); rad = r.uniform(0.045, 0.075); c1 = F.p(uu, v1 - 0.3, 0.8 + rad); c2 = F.p(uu + ln, v1 - 0.3, 0.8 + rad); G.tube(m_, c1, c2, rad, n=16)
        G.tube(mat('meat face', (0.9, 0.55, 0.5), 0.4), c2, F.p(uu + ln + 0.004, v1 - 0.3, 0.8 + rad), rad * 0.98, n=16)
        uu += ln + 0.08
    F.box(mat('salad tray', (0.92, 0.92, 0.9), 0.3), ca + 0.2, v1 - 0.65, 0.79, cb - 0.2, v1 - 0.45, 0.83)
    for k in range(int((cb - ca - 0.4) / 0.35)): F.box(r.choice([colmat('salad', (0.55, 0.65, 0.2), 0.6), colmat('salad', (0.9, 0.85, 0.65), 0.6), colmat('salad', (0.8, 0.3, 0.15), 0.6)]), ca + 0.25 + k * 0.35, v1 - 0.64, 0.83, ca + 0.55 + k * 0.35, v1 - 0.46, 0.86)
    sl = F.p(cb - 0.5, v1 - 1.1, 0); G.box(STEEL, sl[0] - 0.25, sl[1] - 0.2, 1.24, sl[0] + 0.25, sl[1] + 0.2, 1.32); G.tube(STEEL, F.p(cb - 0.5, v1 - 1.1, 1.48), F.p(cb - 0.5, v1 - 1.0, 1.48), 0.15, n=20)
    board = mat('menu board', (0.02, 0.02, 0.025), 0.6); F.box(board, ca - 0.2, -5.62, 2.85, cb + 0.2, -5.58, 3.65)
    ink = mat('menu chalk', (0.93, 0.92, 0.86), 0.7, emit=(0.9, 0.9, 0.85), es=0.4)
    for q, line in enumerate(['BACON EGG & CHEESE   4.50', 'CHOPPED CHEESE HERO   9.75', 'TURKEY CLUB   10.50', 'COFFEE ANY SIZE   1.75']):
        text(line, F, (ca + cb) / 2, -5.57, 3.48 - q * 0.19, 0.13, ink, extrude=0.001)
    # bottles and cans in the drinks fridge, behind clear doors
    bot = [colmat('soda', (0.35, 0.08, 0.02), 0.1), colmat('water', (0.65, 0.8, 0.95), 0.05), colmat('lime soda', (0.25, 0.55, 0.15), 0.1), colmat('juice', (0.95, 0.5, 0.08), 0.15), colmat('cola', (0.05, 0.02, 0.015), 0.1), colmat('can', (0.75, 0.76, 0.78), 0.25)]
    for lv in range(4):
        z = 0.42 + lv * 0.42; F.box(STEEL, u0 + 0.03, -5.9, z - 0.02, u0 + 0.3, -1.4, z)
        vv = -5.85
        while vv < -1.5:
            m_ = bot[int((vv + 6) / 0.6) % len(bot)]; rad = 0.033 if m_.name.startswith('can') is False else 0.03; c_ = F.p(u0 + 0.16, vv, z)
            G.cyl(m_, c_[0], c_[1], z, z + 0.22, rad, 12); G.cyl(m_, c_[0], c_[1], z + 0.22, z + 0.29, rad * 0.35, 8, r1=rad * 0.3)
            vv += 0.075
    for k in range(4):                     # door frames on the fridge
        F.box(STEEL, u0 + 0.015, -5.9 + k * 1.125, 0.34, u0 + 0.03, -5.86 + k * 1.125, 2.1)
    # by the register: bananas, a basket of rolls and croissants, a coffee machine
    R.place('bananas', F.p(u1 - 3.05, -1.15, 1.1), rotz=F.rotz() + 0.4, fit=('x', 0.3))
    bk = F.p(u1 - 2.55, -1.15, 1.1); G.cyl(mat('wicker', (0.5, 0.35, 0.18), 0.85), bk[0], bk[1], 1.1, 1.2, 0.17, 16)
    for q in range(3): R.place('croissant', F.p(u1 - 2.62 + q * 0.07, -1.18 + (q % 2) * 0.06, 1.2), rotz=r.uniform(0, 6.28), scale=0.9)
    R.place('hamburger_buns', F.p(u1 - 2.5, -1.08, 1.2), rotz=F.rotz(), scale=0.6)
    F.box(colmat('coffee machine', (0.06, 0.06, 0.065), 0.3, 0.6), u1 - 1.45, -1.45, 1.1, u1 - 1.0, -1.0, 1.75)
    for q in range(4):                     # a candy rack on the customer side of the counter
        z = 0.3 + q * 0.2; F.box(STEEL, u1 - 3.1, -0.78, z, u1 - 1.7, -0.6, z + 0.01)
        for k in range(10): F.box(r.choice(PACK), u1 - 3.08 + k * 0.135, -0.77, z + 0.01, u1 - 2.97 + k * 0.135, -0.62, z + 0.13)

def props(key, F, u0, u1):
    """Fill the shop cavity. u0..u1 is the clear width, v runs from -6.1 at the back wall to 0 at the glass."""
    s = K.SHOPS[key]; light = MATS['shoplight ' + key]; neon = MATS['neon ' + key]; sign = MATS['sign ' + key]; wd = u1 - u0
    ember = mat('ember ' + key, (0.1, 0.02, 0), emit=(1.0, 0.35, 0.05), es=0.0); CTRL['ember ' + key] = bsdf(ember).inputs['Emission Strength']
    if key == 'grocery':
        shelves(F.at(u0 + 0.1, -6.05, 0), wd - 0.4); shelves(F.at(u1 - 0.05, -5.6, 90), 4.2); shelves(F.at(u0 + wd * 0.42, -1.5, -90), 3.4, levels=3); shelves(F.at(u0 + wd * 0.42 - 0.06, -4.9, 90), 3.4, levels=3)
        F.box(neon, u0 + 0.06, -5.9, 0.3, u0 + 0.09, -1.4, 0.34); F.box(neon, u0 + 0.06, -5.9, 2.1, u0 + 0.09, -1.4, 2.14)                                # the drinks fridge
        F.box(MATS['Car glass'] if R.ON else DARKGLASS, u0 + 0.05, -5.9, 0.34, u0 + 0.07, -1.4, 2.1); fr = mat('fridge glow', (1, 1, 1), emit=(0.7, 0.95, 1.0), es=3.0); F.box(fr, u0 + 0.02, -5.9, 0.34, u0 + 0.04, -1.4, 2.1)
        if not R.ON:
            for k in range(22): F.box(pr.choice(PACK), u0 + 0.075, -5.8 + k * 0.2, 0.5 + (k % 4) * 0.4, u0 + 0.16, -5.68 + k * 0.2, 0.74 + (k % 4) * 0.4)
        else: deli(F, u0, u1, sign)
        F.box(WOOD, u1 - 3.2, -1.5, 0.17, u1 - 1.5, -0.8, 1.1); F.box(DARKGLASS, u1 - 3.1, -1.45, 1.1, u1 - 1.6, -0.85, 1.5); F.box(colmat('register', (0.1, 0.1, 0.1), 0.4), u1 - 2.0, -1.35, 1.1, u1 - 1.65, -1.0, 1.45)
        F.box(sign, u1 - 3.2, -1.52, 2.5, u1 - 1.5, -1.5, 3.0)                                                                                               # the lotto and cigarette board
        figure(F, u1 - 2.4, -1.9, 0, 1, (0.161, 0.384, 1.0), seed=1)                                                                                          # the clerk, all night
        cards = [colmat('card', c, 0.7) for c in [(1.0, 0.85, 0.05), (0.9, 0.9, 0.86), K.PINK, K.ACID]]
        for k in range(7): uu = u0 + 0.5 + k * 0.62; F.box(cards[k % 4], uu, 0.02, 2.3 + (k % 2) * 0.1, uu + 0.5, 0.03, 2.62 + (k % 2) * 0.1)
        g = G
        for row in range(2):                                                                                                                                 # flowers on the sidewalk
            for k in range(6):
                c = F.p(u0 + 0.6 + k * 0.45 + row * 0.2, 0.45 + row * 0.42, 0); top = 0.16 + (0.22 if row == 0 else 0)
                if row == 0: g.box(colmat('crate', (0.75, 0.1, 0.05), 0.6), c[0] - 0.2, c[1] - 0.2, 0.16, c[0] + 0.2, c[1] + 0.2, 0.38)
                bouquet(g, c[0], c[1], top, PETAL[(k + row * 3) % len(PETAL)])
        c = F.p(u1 + 0.75, 0.6, 0); G.box(colmat('ice box', (0.85, 0.87, 0.9), 0.3), c[0] - 0.6, c[1] - 0.35, 0.16, c[0] + 0.6, c[1] + 0.35, 1.2)
        text('ICE', F, u1 + 0.75, 0.97, 0.85, 0.3, colmat('ice ink', K.BLUE, 0.5), extrude=0.004)
    elif key == 'laundromat':
        white = colmat('appliance', (0.85, 0.86, 0.87), 0.3)
        n = int((wd - 0.6) / 0.85)
        for k in range(n):                                                                                                                                    # dryers, stacked two high along the back wall
            uu = u0 + 0.3 + k * 0.85
            for q in range(2):
                F.box(STEEL, uu, -6.05, 0.2 + q * 1.05, uu + 0.8, -5.3, 1.2 + q * 1.05); c = F.p(uu + 0.4, -5.29, 0.7 + q * 1.05); c2 = F.p(uu + 0.4, -5.27, 0.7 + q * 1.05)
                G.tube(DARKGLASS, c, c2, 0.27, n=14); G.tube(white, F.p(uu + 0.4, -5.295, 0.7 + q * 1.05), c2, 0.31, n=14)
        for k in range(int(3.6 / 0.72)):                                                                                                                      # washers, back to back in an island
            vv = -4.4 + k * 0.72
            for sgn, a in ((1, -90), (-1, 90)):
                uu = u0 + wd * 0.5; F.box(white, uu - 0.66 if sgn > 0 else uu, vv, 0.17, uu if sgn > 0 else uu + 0.66, vv + 0.68, 1.1)
                c = F.p(uu - 0.665 * sgn, vv + 0.34, 0.6); c2 = F.p(uu - 0.69 * sgn, vv + 0.34, 0.6); G.tube(DARKGLASS, c, c2, 0.21, n=12)
        F.box(colmat('table', K.CLOUD, 0.4), u0 + 0.4, -3.2, 0.9, u0 + 1.3, -0.9, 0.95)
        for vv in (-3.1, -1.0): F.box(STEEL, u0 + 0.45, vv, 0.17, u0 + 0.5, vv + 0.05, 0.9); F.box(STEEL, u0 + 1.2, vv, 0.17, u0 + 1.25, vv + 0.05, 0.9)
        seat = colmat('seat', K.BLUE, 0.4)
        for k in range(4): F.box(seat, u1 - 0.75, -4.6 + k * 0.62, 0.55, u1 - 0.25, -4.1 + k * 0.62, 0.6); F.box(seat, u1 - 0.3, -4.6 + k * 0.62, 0.6, u1 - 0.25, -4.1 + k * 0.62, 1.0); F.box(STEEL, u1 - 0.7, -4.4 + k * 0.62, 0.17, u1 - 0.66, -4.36 + k * 0.62, 0.55)
        c = F.p(u0 + 2.0, -1.6, 0); G.box(STEEL, c[0] - 0.4, c[1] - 0.3, 0.3, c[0] + 0.4, c[1] + 0.3, 0.34); G.blob(colmat('laundry', (0.8, 0.8, 0.85), 0.9), c[0], c[1], 0.62, 0.36, 0.27, 0.25, 8, 5, 0.2)
        figure(F, u0 + 1.6, -2.0, -1, 0, (0.60, 0.58, 0.52), 0, 62, seed=2)                                                                                   # the last customer, folding until 1:02
        text('NO DYEING  ·  CHECK YOUR POCKETS', F.at(u0 + 0.3, -6.04, 0), wd / 2 - 0.3, 0.02, 2.75, 0.14, colmat('ice ink', K.BLUE, 0.5), extrude=0.002)
    elif key in ('pizza', 'bakery'):
        F.box(colmat('counter', (0.75, 0.75, 0.73), 0.3, 0.6), u0 + 0.5, -3.3, 0.17, u1 - 0.9, -2.6, 1.05); F.box(GLASS, u0 + 0.6, -3.25, 1.05, u1 - 1.0, -2.65, 1.45)
        crust = colmat('crust', (0.72, 0.5, 0.25), 0.8); sauce = colmat('sauce', (0.65, 0.12, 0.05), 0.7)
        if key == 'pizza':
            for k in range(int((wd - 1.8) / 0.62)):
                c = F.p(u0 + 0.95 + k * 0.62, -2.95, 0); G.cyl(crust, c[0], c[1], 1.07, 1.09, 0.27, 14); G.cyl(sauce if k % 2 else colmat('cheese', (0.9, 0.75, 0.4), 0.7), c[0], c[1], 1.09, 1.1, 0.23, 14)
            F.box(colmat('oven', (0.08, 0.08, 0.085), 0.4, 0.5), u0 + 0.6, -6.05, 0.17, u0 + 3.0, -5.1, 2.0); F.box(ember, u0 + 0.9, -5.09, 1.05, u0 + 2.7, -5.07, 1.3); F.box(ember, u0 + 0.9, -5.09, 1.5, u0 + 2.7, -5.07, 1.75)
            F.box(sign, u0 + 0.5, -6.05, 2.35, u1 - 0.4, -6.0, 3.05); mi = colmat('menu ink', K.INK, 0.6); FB = F.at(u0 + 0.5, -5.99, 0)
            for i, line in enumerate(('PLAIN  3.50     PEPPERONI  4.25     WHITE  4.50', 'GRANDMA  4.75     KNOTS (6)  5.00     CALZONE  9.00')): text(line, FB, (wd - 0.9) / 2, 0.01, 2.85 - i * 0.32, 0.16, mi, extrude=0.002)
            for k in range(3): stool(F, u0 + 0.9 + k * 0.8, -0.7, colmat('seat', K.PINK, 0.4))
            F.box(WOOD, u0 + 0.5, -0.5, 1.0, u0 + 3.0, -0.2, 1.05)
            figure(F, u0 + wd * 0.5, -3.9, 0, 1, (0.92, 0.92, 0.9), 0, 259, seed=3); figure(F, u0 + wd * 0.6, -1.9, 0, -1, (0.10, 0.12, 0.20), 0, 55, seed=4); figure(F, u0 + 1.3, -0.95, 0, 1, (0.30, 0.08, 0.06), 100, 131, seed=5)
            figure(F, u0 + wd * 0.45, -2.0, 0, -1, (0.05, 0.05, 0.06), 205, 241, seed=6); figure(F, u0 + wd * 0.7, -1.8, -1, -1, (0.843, 1.0, 0.122), 221, 243, seed=7)
        else:
            loaf = colmat('loaf', (0.62, 0.38, 0.16), 0.8)
            for k in range(3):                                                                                                                                # bread racks along the back wall
                uu = u0 + 0.5 + k * 1.5
                for lv in range(6):
                    z = 0.4 + lv * 0.36; F.box(STEEL, uu, -6.0, z, uu + 1.3, -5.45, z + 0.02)
                    for q in range(4): c = F.p(uu + 0.2 + q * 0.3, -5.72, z + 0.1); G.blob(loaf, c[0], c[1], c[2], 0.12, 0.22, 0.09, 6, 4)
                for a in (uu, uu + 1.28): F.box(STEEL, a, -6.0, 0.17, a + 0.02, -5.45, 2.4)
            F.box(colmat('oven', (0.08, 0.08, 0.085), 0.4, 0.5), u1 - 2.1, -6.05, 0.17, u1 - 0.1, -5.0, 2.2); F.box(ember, u1 - 1.9, -4.99, 0.9, u1 - 0.3, -4.97, 1.15); F.box(ember, u1 - 1.9, -4.99, 1.4, u1 - 0.3, -4.97, 1.65)
            for k in range(int((wd - 1.8) / 0.5)): c = F.p(u0 + 0.9 + k * 0.5, -2.95, 1.13); G.blob(loaf if k % 3 else crust, c[0], c[1], c[2], 0.18, 0.12, 0.07, 6, 4)
            for k in range(4): c = F.p(u0 + 0.9 + k * 0.7, -0.5, 0); G.cyl(colmat('basket', (0.5, 0.33, 0.15), 0.9), c[0], c[1], 0.62, 0.9, 0.26, 10, r1=0.3); G.blob(loaf, c[0], c[1], 0.92, 0.2, 0.2, 0.1, 6, 4, 0.2)
            figure(F, u0 + wd * 0.7, -4.3, 1, -1, (0.92, 0.92, 0.9), 198, 480, seed=8); figure(F, u0 + wd * 0.4, -3.8, 0, 1, (0.92, 0.92, 0.9), 356, 480, seed=9)
            for k, tt in enumerate((412, 425, 437, 449, 458, 466)): figure(F, u0 + 1.0 + (k % 4) * 0.75, -1.9 - (k // 4) * 0.7, 0, -1, pr.choice(K.COAT), tt, 480, seed=10 + k)
    elif key == 'diner':
        seat = colmat('seat', K.PINK, 0.35); top = colmat('table', K.CLOUD, 0.3)
        for k in range(int((wd - 1.2) / 1.9)):                                                                                                                # booths in the window
            uu = u0 + 0.5 + k * 1.9
            for a in (uu, uu + 1.25): F.box(seat, a, -1.7, 0.17, a + 0.5, -0.35, 0.62); F.box(seat, a if a == uu else a + 0.38, -1.7, 0.62, a + 0.12 if a == uu else a + 0.5, -0.35, 1.25)
            F.box(top, uu + 0.55, -1.6, 0.9, uu + 1.2, -0.4, 0.94); c = F.p(uu + 0.87, -1.0, 0); G.cyl(STEEL, c[0], c[1], 0.17, 0.9, 0.04, 6); pendant(F, uu + 0.87, -1.0, light, 2.2)
        F.box(colmat('counter', (0.75, 0.75, 0.73), 0.3, 0.6), u0 + 0.6, -4.2, 0.17, u1 - 0.8, -3.6, 1.08); F.box(top, u0 + 0.55, -4.25, 1.08, u1 - 0.75, -3.5, 1.12)
        for k in range(int((wd - 1.6) / 0.7)): stool(F, u0 + 0.95 + k * 0.7, -3.1, seat)
        F.box(STEEL, u0 + 0.5, -6.05, 0.17, u1 - 0.5, -5.4, 1.0); F.box(STEEL, u0 + 0.5, -6.05, 1.9, u1 - 0.5, -5.6, 2.3); F.box(neon, u0 + 0.5, -5.58, 2.28, u1 - 0.5, -5.56, 2.32)
        F.box(ember, u0 + 1.0, -5.5, 1.0, u0 + 2.6, -5.48, 1.03)
        text('EGGS ANY STYLE  ·  PANCAKES  ·  COFFEE', F.at(u0 + 0.5, -6.04, 0), (wd - 1.0) / 2, 0.02, 2.75, 0.2, colmat('menu ink', K.INK, 0.6), extrude=0.002)
        figure(F, u0 + wd * 0.5, -4.8, 0, 1, (0.92, 0.92, 0.9), 284, 480, seed=20)
        for k, (tt, uu, vv) in enumerate(((303, 1.3, -3.1), (322, 3.4, -3.1), (351, 2.0, -3.1), (378, 4.8, -3.1), (396, 1.0, -1.0), (414, 2.9, -1.0), (431, 6.1, -3.1), (447, 4.8, -1.0))):
            if uu < wd - 0.8: figure(F, u0 + uu, vv, 0, -1 if vv < -2 else 1, pr.choice(K.COAT), tt, 480 if k % 3 else tt + 55, z=0.17, seed=30 + k)
    elif key == 'bar':
        bw = colmat('bar wood', (0.12, 0.05, 0.03), 0.3)
        F.box(bw, u0 + 0.9, -5.6, 0.17, u0 + 1.5, -1.2, 1.1); F.box(bw, u0 + 0.85, -5.65, 1.1, u0 + 1.6, -1.15, 1.15)
        F.box(bw, u0 + 0.03, -5.8, 0.9, u0 + 0.35, -1.0, 0.95); F.box(neon, u0 + 0.05, -5.8, 2.05, u0 + 0.08, -1.0, 2.09); F.box(neon, u0 + 0.05, -5.8, 1.45, u0 + 0.08, -1.0, 1.49)
        for lv in range(2):
            F.box(bw, u0 + 0.03, -5.8, 1.5 + lv * 0.6, u0 + 0.3, -1.0, 1.53 + lv * 0.6)
            for k in range(30): c = F.p(u0 + 0.18, -5.7 + k * 0.155, 0); G.cyl(pr.choice(PACK[:8]), c[0], c[1], 1.53 + lv * 0.6, 1.53 + lv * 0.6 + pr.uniform(0.22, 0.34), 0.04, 6, r1=0.015)
        seat = colmat('seat', (0.25, 0.02, 0.03), 0.4)
        for k in range(6): stool(F, u0 + 2.0, -5.2 + k * 0.72, seat)
        felt = colmat('felt', (0.02, 0.25, 0.12), 0.9); F.box(bw, u1 - 3.3, -4.6, 0.17, u1 - 1.9, -2.0, 0.8); F.box(felt, u1 - 3.2, -4.5, 0.8, u1 - 2.0, -2.1, 0.83)
        for k in range(5): c = F.p(u1 - 2.6 + pr.uniform(-0.4, 0.4), -3.3 + pr.uniform(-0.9, 0.9), 0.86); G.blob(pr.choice(PACK), c[0], c[1], c[2], 0.03, 0.03, 0.03, 6, 4)
        pendant(F, u1 - 2.6, -3.3, light, 1.9); pendant(F, u0 + 1.2, -2.2, light, 2.3); pendant(F, u0 + 1.2, -4.4, light, 2.3)
        text('COLD BEER', F, u0 + 1.9, 0.0, 2.55, 0.3, neon, extrude=0.03); text('POOL', F, u1 - 2.4, 0.0, 2.55, 0.3, MATS['neon grocery'] if 'neon grocery' in MATS else neon, extrude=0.03)
        figure(F, u0 + 0.6, -3.0, 1, 0, (0.05, 0.05, 0.06), 0, 262, seed=40)                                                                                 # the bartender
        for k, (uu, vv, du, dv, t1) in enumerate(((2.05, -4.5, -1, 0, 236), (2.05, -3.75, -1, 0, 241), (2.3, -2.3, -1, 0.3, 246), (wd - 3.6, -3.0, 1, 0, 249), (wd - 1.5, -3.6, -1, 0, 249), (2.05, -1.6, -1, 0, 251), (3.2, -1.2, 0, 1, 255))):
            figure(F, u0 + uu, vv, du, dv, pr.choice(K.COAT), 0 if k != 3 else 40, t1, seed=41 + k)
    elif key == 'flowers':
        for tier in range(3):
            F.box(WOOD, u0 + 0.3, -5.9 + tier * 0.5, 0.17, u1 - 0.3, -5.4 + tier * 0.5, 1.3 - tier * 0.4)
            for k in range(int((wd - 0.8) / 0.42)): c = F.p(u0 + 0.55 + k * 0.42, -5.65 + tier * 0.5, 0); bouquet(G, c[0], c[1], 1.3 - tier * 0.4, pr.choice(PETAL))
        green = colmat('kale', (0.03, 0.09, 0.03), 0.8)
        for k in range(5): c = F.p(u0 + 0.7 + k * 0.9, -1.0, 0); G.cyl(colmat('pot', (0.5, 0.2, 0.1), 0.8), c[0], c[1], 0.17, 0.5, 0.2, 10, r1=0.25); G.blob(green, c[0], c[1], 0.95, 0.35, 0.35, 0.5, 7, 5, 0.25)
        F.box(WOOD, u1 - 2.2, -3.2, 0.17, u1 - 0.6, -2.6, 1.0)
        figure(F, u1 - 1.4, -3.7, 0, 1, (0.08, 0.20, 0.14), 312, 480, seed=50)
        # buckets go out on the sidewalk once the van has come
        g = Geo()
        for k in range(8):
            c = F.p(u0 + 0.5 + k * 0.48, 0.5 + (k % 2) * 0.35, 0); bouquet(g, c[0], c[1], 0.16, PETAL[k % len(PETAL)], 11, 0.16)
        INSIDE.append((g.flush('flower buckets out'), 350, 481))
    elif key == 'pharmacy':
        for k in range(3): shelves(F.at(u0 + 1.2 + k * 2.4, -1.4, -90), 3.6, levels=4, packs=[PACK[5], PACK[2], PACK[7], PACK[5]])
        shelves(F.at(u0 + 0.1, -6.05, 0), wd - 0.4, packs=[PACK[5], PACK[2], PACK[7], PACK[5], PACK[0]])
        F.box(sign, u0 + 1.0, -5.6, 2.5, u1 - 1.0, -5.55, 3.0); text('PRESCRIPTIONS', F.at(u0 + 1.0, -5.54, 0), (wd - 2.0) / 2, 0.01, 2.75, 0.3, colmat('ice ink', K.BLUE, 0.5), extrude=0.002)
        figure(F, u0 + wd * 0.6, -1.2, 0, -1, (0.92, 0.92, 0.9), 462, 480, seed=60)
    elif key == 'locksmith':
        brass = colmat('brass', (0.7, 0.5, 0.15), 0.3, 0.9); F.box(WOOD, u0 + 0.3, -2.4, 0.17, u1 - 0.3, -1.8, 1.05)
        for k in range(160): uu = u0 + 0.4 + (k % 32) * (wd - 0.8) / 32; z = 1.3 + (k // 32) * 0.3; F.box(brass, uu, -6.08, z, uu + 0.03, -6.06, z + 0.12)

# ------------------------------------------------------------------ build
ground()
for b in K.BUILDINGS: {'tenement': tenement, 'brownstone': brownstone, 'prewar': prewar, 'garage': garage, 'garden': garden}[b['kind']](b)
for key, (F_, a_, b__) in SHOPCAV.items(): props(key, F_, a_, b__)
street_lamps(); signals(); subway(); odds_and_ends(); trash_piles(); city()
for h in K.HYDRANTS: hydrant(h['x'], h['side'])
STATIC = G.flush('block', smooth=('Bark',))
STEAM = steam(48.0, 0.7, 3.0)     # a second plume near the west corner was tried 12:36 to 18:44 and removed: it darkened a square of road under it
parked_cars(); movers(); cat_in_window()
# window panes
pme = bpy.data.meshes.new('Panes'); pme.from_pydata(PANE_V, [], PANE_F); pme.materials.append(PANE)
pobj = bpy.data.objects.new('Panes', pme); scene.collection.objects.link(pobj)
GLOW = pme.color_attributes.new('glow', 'FLOAT_COLOR', 'CORNER'); WUV = pme.color_attributes.new('wuv', 'FLOAT_COLOR', 'CORNER')
WUV.data.foreach_set('color', [c for uv in PANE_UV for c in uv])
print('built: %d panes, %d objects, %.1fs' % (len(PANES), len(bpy.data.objects), time.time() - T0))

# ------------------------------------------------------------------ world and sun
world = bpy.data.worlds.new('Sky'); scene.world = world; world.use_nodes = True
def _world():
    nt = world.node_tree; bg = nt.nodes['Background']; geo = nt.nodes.new('ShaderNodeNewGeometry'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Incoming'], sp.inputs[0])
    up = nt.nodes.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = -0.02; up.inputs['From Max'].default_value = -0.55; nt.links.new(sp.outputs['Z'], up.inputs['Value'])     # incoming points at the camera, so up is -z
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.55; nt.links.new(up.outputs['Result'], pw.inputs[0])
    hz = nt.nodes.new('ShaderNodeRGB'); zn = nt.nodes.new('ShaderNodeRGB'); gl = nt.nodes.new('ShaderNodeRGB'); CTRL['sky_h'] = hz.outputs[0]; CTRL['sky_z'] = zn.outputs[0]; CTRL['sky_g'] = gl.outputs[0]
    mx = nt.nodes.new('ShaderNodeMixRGB'); nt.links.new(pw.outputs[0], mx.inputs['Fac']); nt.links.new(hz.outputs[0], mx.inputs['Color1']); nt.links.new(zn.outputs[0], mx.inputs['Color2'])
    # glow toward the sun's azimuth, strongest at the horizon
    sv = nt.nodes.new('ShaderNodeCombineXYZ'); CTRL['sunvec'] = sv
    dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; nt.links.new(geo.outputs['Incoming'], dot.inputs[0]); nt.links.new(sv.outputs[0], dot.inputs[1])
    dm = nt.nodes.new('ShaderNodeMapRange'); dm.inputs['From Min'].default_value = -0.35; dm.inputs['From Max'].default_value = -1.0; nt.links.new(dot.outputs['Value'], dm.inputs['Value'])
    dp = nt.nodes.new('ShaderNodeMath'); dp.operation = 'POWER'; dp.inputs[1].default_value = 2.2; nt.links.new(dm.outputs['Result'], dp.inputs[0])
    add = nt.nodes.new('ShaderNodeMixRGB'); add.blend_type = 'ADD'; nt.links.new(dp.outputs[0], add.inputs['Fac']); nt.links.new(mx.outputs['Color'], add.inputs['Color1']); nt.links.new(gl.outputs[0], add.inputs['Color2'])
    s3 = nt.nodes.new('ShaderNodeCombineXYZ'); CTRL['sun3'] = s3
    d3 = nt.nodes.new('ShaderNodeVectorMath'); d3.operation = 'DOT_PRODUCT'; nt.links.new(geo.outputs['Incoming'], d3.inputs[0]); nt.links.new(s3.outputs[0], d3.inputs[1])
    disk = nt.nodes.new('ShaderNodeMapRange'); disk.inputs['From Min'].default_value = -0.99985; disk.inputs['From Max'].default_value = -0.99995; nt.links.new(d3.outputs['Value'], disk.inputs['Value'])
    halo = nt.nodes.new('ShaderNodeMapRange'); halo.inputs['From Min'].default_value = -0.93; halo.inputs['From Max'].default_value = -1.0; nt.links.new(d3.outputs['Value'], halo.inputs['Value'])
    hp = nt.nodes.new('ShaderNodeMath'); hp.operation = 'POWER'; hp.inputs[1].default_value = 6.0; nt.links.new(halo.outputs['Result'], hp.inputs[0])
    dv = nt.nodes.new('ShaderNodeValue'); CTRL['sun_disk'] = dv.outputs[0]; hv = nt.nodes.new('ShaderNodeValue'); CTRL['sun_halo'] = hv.outputs[0]; sc = nt.nodes.new('ShaderNodeRGB'); CTRL['sun_col'] = sc.outputs[0]
    a1 = nt.nodes.new('ShaderNodeMath'); a1.operation = 'MULTIPLY'; nt.links.new(disk.outputs['Result'], a1.inputs[0]); nt.links.new(dv.outputs[0], a1.inputs[1])
    a2 = nt.nodes.new('ShaderNodeMath'); a2.operation = 'MULTIPLY'; nt.links.new(hp.outputs[0], a2.inputs[0]); nt.links.new(hv.outputs[0], a2.inputs[1])
    a3 = nt.nodes.new('ShaderNodeMath'); a3.operation = 'ADD'; nt.links.new(a1.outputs[0], a3.inputs[0]); nt.links.new(a2.outputs[0], a3.inputs[1])
    sm = nt.nodes.new('ShaderNodeMixRGB'); sm.blend_type = 'MULTIPLY'; sm.inputs['Fac'].default_value = 1.0; nt.links.new(sc.outputs[0], sm.inputs['Color1']); nt.links.new(a3.outputs[0], sm.inputs['Color2'])
    fin = nt.nodes.new('ShaderNodeMixRGB'); fin.blend_type = 'ADD'; fin.inputs['Fac'].default_value = 1.0; nt.links.new(add.outputs['Color'], fin.inputs['Color1']); nt.links.new(sm.outputs['Color'], fin.inputs['Color2'])
    # low cloud: the sky is never one flat colour over a city
    cn = nt.nodes.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 2.2; cn.inputs['Detail'].default_value = 5; cn.inputs['Roughness'].default_value = 0.6; co = nt.nodes.new('ShaderNodeVectorMath'); co.operation = 'ADD'; CTRL['cloud_off'] = co.inputs[1]; nt.links.new(geo.outputs['Incoming'], co.inputs[0]); nt.links.new(co.outputs[0], cn.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.3; cr.inputs['From Max'].default_value = 0.7; cr.inputs['To Min'].default_value = 0.72; cr.inputs['To Max'].default_value = 1.35; nt.links.new(cn.outputs['Fac'], cr.inputs['Value'])
    cl = nt.nodes.new('ShaderNodeMixRGB'); cl.blend_type = 'MULTIPLY'; cl.inputs['Fac'].default_value = 1.0; nt.links.new(fin.outputs['Color'], cl.inputs['Color1']); nt.links.new(cr.outputs['Result'], cl.inputs['Color2'])
    nt.links.new(cl.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    if R.ON:     # 04:30 (Astra, second pass: the night facades sink to black): the sky lights the street half a stop more than it shows itself to the camera
        lp = nt.nodes.new('ShaderNodeLightPath'); fill = nt.nodes.new('ShaderNodeMapRange'); fill.inputs['To Min'].default_value = 1.4; fill.inputs['To Max'].default_value = 1.0
        nt.links.new(lp.outputs['Is Camera Ray'], fill.inputs['Value']); nt.links.new(fill.outputs['Result'], bg.inputs['Strength'])
_world()
sunl = bpy.data.lights.new('Sun', 'SUN'); sunl.angle = math.radians(0.53 if R.ON else 1.2); suno = bpy.data.objects.new('Sun', sunl); scene.collection.objects.link(suno)

# ------------------------------------------------------------------ cameras
def camera(name, loc, aim, lens=None, ortho=None, shift_y=0.0, clip=(0.1, 1500)):
    cd = bpy.data.cameras.new(name); o = bpy.data.objects.new(name, cd); scene.collection.objects.link(o); o.location = loc
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else: cd.lens = lens
    cd.shift_y = shift_y; cd.clip_start, cd.clip_end = clip
    e = bpy.data.objects.new(name + ' aim', None); scene.collection.objects.link(e); e.location = aim
    c = o.constraints.new('TRACK_TO'); c.target = e; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'; return o
CAMS = dict(
    canyon=camera('canyon', (-12.5, 1.1, 1.66), (96, 0.4, 1.66), lens=22, shift_y=0.21),
    axo=camera('axo', (-44, -54, 152), (46, 0, 5), ortho=122),
    elevN=camera('elevN', (48, -60, 12.5), (48, 0, 12.5), ortho=100, clip=(57.5, 400)),
    elevS=camera('elevS', (48, 60, 12.5), (48, 0, 12.5), ortho=100, clip=(57.5, 400)),
    high=camera('high', (-10, -3.5, 16), (70, 3, 6), lens=20, shift_y=0.0),
    witness=camera('witness', (9.0, 1.6, 1.45), (5.15, -9.0, 2.5), lens=20, shift_y=0.12),     # 04:25: turned a little so the clipped car is only a sliver; further (4.7) cut the window figure off (04:32)
    cars=camera('cars', (27.5, 1.2, 1.35), (34.0, -K.ROAD + 0.6, 0.7), lens=28),     # 23:55: a look at the parked cars
    smokers=camera('smokers', (14.6, -5.6, 1.6), (10.4, -7.8, 1.25), lens=30),      # a close look at people (the two smokers, 00:11 to 00:20)
)
rain(CAMS['canyon'].location)

# ------------------------------------------------------------------ the hour
SIGN_ALWAYS = {'grocery', 'locksmith', 'pharmacy', 'diner', 'laundromat'}
def apply_time(t):
    # windows
    cols = []
    for w, static in PANES:
        if static is not None: c = static
        else:
            wl = K.window_light(w, t)
            if wl:
                k, lv = wl; base = K.KIND_RGB[k]; vr = 0.4 + 1.05 * ((math.sin(len(cols) * 0.0137 + 3.17) * 43758.5453) % 1.0) if R.ON else 1.0   # 04:23: no two rooms equally bright
                c = tuple(v * lv * 2.2 * vr for v in base)
            else: c = (0, 0, 0)
        cols.extend((c[0], c[1], c[2], 1.0) * 4)
    GLOW.data.foreach_set('color', cols); pme.update()
    # shops, signs, gates
    for key, s in K.SHOPS.items():
        lv = K.shop_level(key, t); CTRL['shop ' + key].default_value = 7.0 * lv
        on = lv >= 0.5 or key in SIGN_ALWAYS
        CTRL['sign ' + key].default_value = 2.2 if on else 0.0; CTRL['neon ' + key].default_value = (4.5 if R.ON else 9.0) if on else 0.0   # 04:23: half the coloured spill (Astra)
        if key in GATES:
            down = K.gate_down(key, t)
            for o in GATES[key]: o.hide_render = not down
    for key in K.SHOPS:
        if ('ember ' + key) in CTRL: CTRL['ember ' + key].default_value = 12.0 if K.shop_level(key, t) >= 0.5 else 0.0
    for objs, a_, b__ in INSIDE:
        for o in objs: o.hide_render = not (a_ <= t < b__ or (t >= 480 and b__ >= 480))
    # street lamps, garden lights, billboard
    lamp = K.lamps_on(t); CTRL['lamp'].default_value = 28.0 if lamp else 0.0
    for li in LAMP_LIGHTS: li.energy = 2600 if lamp else 0.0
    CTRL['string'].default_value = 7.0 if lamp else 0.0; CTRL['billboard'].default_value = 0.9 if lamp else 0.0
    # signals
    ph = K.signal(t)
    for nm in 'RYG':
        SIG[('st', nm)].default_value = 14.0 if nm == ph else 0.0
        SIG[('av', nm)].default_value = 14.0 if nm == {'G': 'R', 'Y': 'R', 'R': 'G'}[ph] else 0.0
    # sky and sun
    h, z, _ = K.sky(t); el, az = K.sun(t); sv = K.sun_vector(t)
    CTRL['sky_h'].default_value = (*K.lerp(h, z, 0.55), 1); CTRL['sky_z'].default_value = (*z, 1); CTRL['sky_g'].default_value = (*[max(0.0, a - b_ * 0.55) for a, b_ in zip(h, z)], 1)
    n = CTRL['sunvec']; n.inputs[0].default_value, n.inputs[1].default_value, n.inputs[2].default_value = sv[0], sv[1], 0.0
    sunl.energy = K.sun_strength(t); sunl.color = K.sun_colour(t); suno.rotation_euler = Vector(sv).to_track_quat('Z', 'Y').to_euler()
    n3 = CTRL['sun3']; n3.inputs[0].default_value, n3.inputs[1].default_value, n3.inputs[2].default_value = sv
    up = max(0.0, min(1.0, (el + 1.2) / 1.6)); CTRL['sun_disk'].default_value = 900.0 * up; CTRL['sun_halo'].default_value = 14.0 * up; CTRL['sun_col'].default_value = (*K.sun_colour(t), 1)
    # the rest of the city: fewer windows lit as the night goes on, more toward morning
    CTRL['city'].default_value = 0.035 + 0.11 * math.exp(-t / 80.0) + 0.10 * max(0.0, (t - 330) / 150.0)
    # weather
    wv = K.wetness(t)
    for sck in WET: sck.default_value = wv
    rr2 = random.Random(int(t * 60))
    for o in RAINOBJ: o.hide_render = not K.raining(t); o.location = (rr2.uniform(0, 3), rr2.uniform(-1, 1), rr2.uniform(-1.5, 1.5))
    CTRL['cloud_off'].default_value = (t * 0.006, t * 0.002, 0.0)
    for sck in STEAMOFF: sck.default_value = (t * 0.37 % 50, 0.0, -t * 1.3 % 97)
    # cars, trash, the cat
    for c, objs in PARKED:
        for o in objs: o.hide_render = not K.car_present(c, t)
    for objs, x, appear, gone in PILES:
        for o in objs: o.hide_render = not (appear <= t < gone)
    cat_out = any(m['kind'] == 'cat' and m['keys'][0][0] <= t <= m['keys'][-1][0] for m in K.MOVERS) or (258 <= t < 263)
    for o in CATSIT: o.hide_render = cat_out
    # everyone who moves
    for mi, (m, e, objs, k) in enumerate(MOV):
        p = K.mover_at(m, t)
        for o in objs: o.hide_render = p is None
        if p is None: continue
        x, y, hx, hy, moving = p; e.location = (x, y, 0.16 if abs(y) > K.ROAD else 0.0)
        cs = MOVPH.get(mi)
        if cs:        # one pose at a time: the walk phase his distance along the street gives, or his idle when he stands
            ph = int(((x * hx + y * hy) / max(0.5, cs['stride'])) % 1.0 * 8) % 8 if moving else -1
            cs['idle'].hide_render = moving
            for q, o in enumerate(cs['phases']): o.hide_render = (q != ph)
        if k in ('person', 'cat', 'rat'):
            if moving: e.rotation_euler = (0, 0, math.atan2(hy, hx))
        else: e.rotation_euler = (0, 0, 0)
    if 'flasher' in CTRL: CTRL['flasher'].default_value = 20.0 if int(t * 60) % 2 == 0 else 0.0
    if 'beacon' in CTRL: CTRL['beacon'].default_value = 12.0
    bpy.context.view_layer.update()

# ------------------------------------------------------------------ render
r = scene.render; r.engine = 'CYCLES'; scene.cycles.use_denoising = True; r.image_settings.file_format = 'PNG'
if not A.cpu:
    try:
        pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'METAL'; pr.get_devices()
        for d in pr.devices: d.use = True
        scene.cycles.device = 'GPU'
    except Exception as ex: print('GPU not set:', ex)
try: scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception as ex: print('look not set:', ex)
scene.cycles.max_bounces = 6; scene.cycles.volume_bounces = 1; scene.cycles.caustics_reflective = False; scene.cycles.caustics_refractive = False
scene.cycles.sample_clamp_indirect = 6.0; scene.cycles.use_light_tree = True
try:
    tree = bpy.data.node_groups.new('Bloom', 'CompositorNodeTree'); scene.compositing_node_group = tree
    tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = tree.nodes.new('CompositorNodeRLayers'); gl = tree.nodes.new('CompositorNodeGlare'); out = tree.nodes.new('NodeGroupOutput')
    for nm, val in (('Type', 'Bloom'), ('Threshold', 1.5), ('Strength', 0.3), ('Size', 0.4)):
        try: gl.inputs[nm].default_value = val
        except Exception as ex: print('glare input', nm, ex)
    tree.links.new(rl.outputs['Image'], gl.inputs['Image']); tree.links.new(gl.outputs['Image'], out.inputs['Image'])
except Exception as ex: print('BLOOM FAILED:', ex)

def exposure_for(t):
    """The camera opens up at night and stops down as the sun comes up, the way a person's eye would."""
    el = K.sun(t)[0]
    if el < -8: return 1.6
    if el > 6: return -0.85
    f = (el + 8) / 14.0; f = f * f * (3 - 2 * f); return 1.6 + (-0.85 - 1.6) * f

def shop_camera(key):
    """A camera standing at the kerb facing one shopfront."""
    b = K.B[K.SHOPS[key]['b']]; F = street_frame(b); mid = (b['w'] - 1.9) / 2 if b['kind'] == 'tenement' else b['w'] / 2
    return camera('shop ' + key, F.p(mid, 3.75, 1.5), F.p(mid, 0, 2.0), lens=15 if b['kind'] == 'tenement' else 12)
def setup(cam, res, samples):
    if cam.startswith('shop:'): CAMS[cam] = shop_camera(cam[5:])
    scene.camera = CAMS[cam]
    for o in CITY: o.hide_render = cam in ('axo', 'elevN', 'elevS')
    rx, ry = (int(v) for v in res.split('x')); r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100; scene.cycles.samples = samples
def shoot(t, path):
    apply_time(t); scene.view_settings.exposure = A.exposure if A.exposure is not None else exposure_for(t)
    r.filepath = path; t1 = time.time(); bpy.ops.render.render(write_still=True); print('rendered %s  t=%s  %.1fs' % (os.path.basename(path), K.hm(t), time.time() - t1)); sys.stdout.flush()

setup(A.cam, A.res, A.samples)
if A.save:
    apply_time(K.T(A.t)); bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(A.save)); print('saved', A.save)
if A.film:
    r.use_persistent_data = True; a, b_, step = A.film; os.makedirs(A.out, exist_ok=True); t = a
    while t <= b_ + 1e-6:
        p = os.path.join(A.out, 'f_%05d.png' % int(round(t * 60)))
        if not os.path.exists(p): shoot(t, p)
        t += step
elif not A.norender:
    shoot(K.T(A.t), os.path.abspath(A.out))
print('done %.1fs' % (time.time() - T0))
