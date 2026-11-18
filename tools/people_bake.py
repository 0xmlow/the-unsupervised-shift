"""
tools/people_bake.py   (04:16, Nov 18)  the people, from Blender's own CC0 Human Base Meshes (blender.org, v1.4.1).

Run inside Blender with the bundle open:
  Blender -b human_base_meshes_bundle.blend --python tools/people_bake.py -- OUT.npz

Takes the realistic male and female base bodies (the subdivision cage, about 10,600 quads, a real face, ears,
hands with fingers) and for each variant:
  poses them  arms down from the A pose; 'phone' bends the right forearm up to the chest; 'walk' swings the legs
              and arms to a mid stride
  dresses them every vertex gets a role (skin, hair, hat, coat, legs, shoe, eye) from where it is on the body, and
              is pushed out along its normal by that garment's thickness, smoothed so the shells meet without cracks
  stores them  facing +x, origin between the feet, height 1.0, faces with a role each, in one npz.
build_block.person_geo scales a variant to the person's height and gives each role its material.
No person in it is anyone: two anonymous base bodies and a coat.
"""
import bpy, sys, math, numpy as np

OUT = sys.argv[sys.argv.index('--') + 1]
ROLES = ['skin', 'hair', 'hat', 'coat', 'legs', 'shoe', 'eye']
R = {k: i for i, k in enumerate(ROLES)}
THICK = {'skin': 0.0, 'eye': 0.0, 'hair': 0.013, 'hat': 0.026, 'coat': 0.04, 'legs': 0.015, 'shoe': 0.016}     # 04:20: looser, cloth hangs off a body

def ss(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def rot(P, pivot, axis, ang):
    """Rodrigues rotation of points P (n,3) about pivot, axis unit, ang (n,) radians."""
    k = np.asarray(axis, float); k /= np.linalg.norm(k); v = P - pivot; c = np.cos(ang)[:, None]; s = np.sin(ang)[:, None]
    return pivot + v * c + np.cross(k, v) * s + k * (v @ k)[:, None] * (1 - c)

def body(name):
    o = bpy.data.objects[name]; me = o.data
    V = np.array([tuple(v.co) for v in me.vertices], float)
    F = [tuple(p.vertices) for p in me.polygons]
    eyes = []
    for side in ('L', 'R'):
        e = bpy.data.objects.get(name + '.eye.' + side)
        if e is None: continue
        M = np.array(e.matrix_world); Mo = np.linalg.inv(np.array(o.matrix_world))
        EV = np.array([tuple(v.co) + (1.0,) for v in e.data.vertices]) @ (Mo @ M).T
        eyes.append((EV[:, :3], [tuple(p.vertices) for p in e.data.polygons]))
    return V, F, eyes

def edges_of(F, n):
    A = []; B = []
    for f in F:
        for i in range(len(f)): A.append(f[i]); B.append(f[(i + 1) % len(f)])
    return np.array(A + B), np.array(B + A)

def normals(V, F):
    N = np.zeros_like(V)
    for f in F:
        p = V[list(f)]; n = np.cross(p[1] - p[0], p[2] - p[0])
        if len(f) == 4: n = n + np.cross(p[2] - p[0], p[3] - p[0])
        N[list(f)] += n
    return N / np.maximum(1e-9, np.linalg.norm(N, axis=1))[:, None]

def make(name, pose, hem, head):
    V, F, eyes = body(name)
    z0 = V[:, 2].min(); H = V[:, 2].max() - z0
    head_pts = V[(V[:, 2] - z0) > 0.9 * H]; cx = head_pts[:, 0].mean()
    V = V - np.array([cx, 0, z0]); hy = (head_pts[:, 1].min() + head_pts[:, 1].max()) / 2      # face toward -y
    zn = V[:, 2] / H; ax = np.abs(V[:, 0]); side = np.sign(V[:, 0])
    # the arms: shoulder joint to fingertip, per side
    role = np.full(len(V), R['legs']); armt = np.full(len(V), -1.0); armw = np.zeros(len(V))
    S = {}; U = {}; L = {}
    for sg in (1, -1):
        sel = side == sg; tip = V[sel][np.argmax(ax[sel])]
        sh = np.array([sg * 0.105 * H, (V[sel & (np.abs(zn - 0.8) < 0.01), 1]).mean(), 0.812 * H])
        u = tip - sh; ln = np.linalg.norm(u); u /= ln; S[sg] = sh; U[sg] = u; L[sg] = ln
        p = V - sh; t = (p @ u) / ln
        # 04:18: a distance to the arm's axis left the outer deltoid behind (a ghost arm in the lineup). Split by a
        # line parallel to the arm instead: everything on the outer side of it, beyond the shoulder, is arm.
        nx, nz = -sg * u[2], sg * u[0]; so = p[:, 0] * nx + p[:, 2] * nz
        d = np.linalg.norm(p - np.outer(p @ u, u), axis=1)
        on = sel & (((so > -0.062 * H / 1.68) & (t > -0.12) & (np.abs(p[:, 1]) < 0.15)) | ((t > 0.62) & (d < 0.13))) & (ax > 0.08 * H)   # fingers curl in
        armt[on] = t[on]; armw[on] = ss(-0.10, 0.06, t[on])
    arm = armt > -0.5
    # roles
    torso_top = 0.848 - 0.01 * ss(-0.12, -0.02, V[:, 1] - hy)          # the collar sits a little lower at the front
    role[(zn < hem) & ~arm] = R['legs']
    role[(zn >= hem) & (zn < torso_top) & ~arm] = R['coat']
    role[arm & (armt < 0.735)] = R['coat']; role[arm & (armt >= 0.735)] = R['skin']
    role[zn < 0.062] = R['shoe']
    hd = (zn >= torso_top) & ~arm; role[hd] = R['skin']
    yb = V[:, 1] - hy
    if head == 'hat': cap = hd & ((zn > 0.948) | ((zn > 0.92) & (yb > 0.02)))
    else: cap = hd & ((zn > 0.953) | ((zn > 0.905) & (yb > 0.0)) | ((zn > 0.875) & (yb > 0.045)))
    role[cap] = R[head]
    # 04:18: cloth does not show muscles. Laplacian smoothing (it shrinks a little; the cloth offset makes up for it) of everything dressed, in the rest pose,
    # heavy on coats and shoes (no toes), light on trousers; skin and the borders with skin stay put.
    A, B = edges_of(F, len(V)); cnt = np.bincount(A, minlength=len(V))
    it = np.where(role == R['coat'], 40, np.where(role == R['shoe'], 45, np.where(role == R['legs'], 8, np.where(np.isin(role, [R['hair'], R['hat']]), 10, 0))))
    pin = np.zeros(len(V), bool); sk = role == R['skin']; pin[A[sk[B]]] = True; pin |= sk
    P = V.copy()
    for k in range(45):
        for lam in (0.6,):
            avg = np.stack([np.bincount(A, weights=P[B, c], minlength=len(V)) for c in range(3)], 1) / np.maximum(1, cnt)[:, None]
            mv = (~pin) & (it > k); P[mv] += lam * (avg[mv] - P[mv])
    V = P.copy()
    # pose: arms down (rotate about the forward axis through each shoulder)
    P = V.copy()
    for sg in (1, -1):
        m = arm & (side == sg); a = math.atan2(abs(U[sg][0]), -U[sg][2]); down = a - math.radians(6)   # leave 6 degrees so the sleeve clears the coat
        P[m] = rot(P[m], S[sg], (0, 1, 0), sg * down * armw[m])
    elbow = lambda sg: S[sg] + np.array([0, 0, -1]) * 0.42 * L[sg]
    if pose in ('stand', 'phone'):
        for sg in (1, -1):
            m = arm & (side == sg) & (armt > 0.3); w = ss(0.36, 0.48, armt[m])
            bend = math.radians(80) if (pose == 'phone' and sg == -1) else math.radians(9)
            P[m] = rot(P[m], elbow(sg), (1, 0, 0), -bend * w)          # forearm forward (toward -y) and up
    if pose == 'walk':
        legs = ~arm & (zn < 0.53); hip = 0.49 * H
        for sg in (1, -1):
            m = legs & (side == sg); w = ss(0.53, 0.45, zn[m]); ang = sg * math.radians(14) * w
            P[m] = rot(P[m], np.array([sg * 0.09 * H, 0, hip]), (1, 0, 0), ang)
            m2 = arm & (side == sg); P[m2] = rot(P[m2], S[sg], (1, 0, 0), -sg * math.radians(11) * armw[m2])
            m3 = arm & (side == sg) & (armt > 0.3); P[m3] = rot(P[m3], elbow(sg), (1, 0, 0), -math.radians(12) * ss(0.36, 0.48, armt[m3]))
        P[:, 2] -= P[:, 2].min()
    # dress: push out along the normals, garment thickness smoothed across the seams
    N = normals(P, F); off = np.array([THICK[ROLES[k]] for k in role]) * (H / 1.68)
    off = np.where(role == R['coat'], off * (0.7 + 0.3 * ss(0.6, 0.75, zn)) * np.where(arm, 0.75, 1.0), off)
    A, B = edges_of(F, len(P)); keep0 = (role == R['skin']) & (zn > 0.88) & (yb < -0.01)      # never move the face
    for _ in range(4):
        acc = np.bincount(A, weights=off[B], minlength=len(P)); cnt = np.bincount(A, minlength=len(P))
        off = np.where(keep0, 0.0, 0.5 * off + 0.5 * acc / np.maximum(1, cnt))
    P = P + N * off[:, None]
    # faces get the role most of their corners have; the eyes come along as 'eye'
    fr = []
    for f in F:
        rs = role[list(f)]; vals, cts = np.unique(rs, return_counts=True); r_ = vals[np.argmax(cts)]
        if r_ in (R['coat'], R['legs']) and not arm[list(f)].any():                 # 04:18: a straight hem, by the face's centre
            r_ = R['legs'] if zn[list(f)].mean() < hem else R['coat']
        fr.append(r_)
    hand = P[arm & (side == -1) & (armt > 0.86)].mean(0) if pose == 'phone' else P[arm & (side == -1) & (armt > 0.86)].mean(0)
    allP = [P]; allF = list(F); allR = list(fr); n = len(P)
    for EV, EF in eyes:
        EV = EV - np.array([cx, 0, z0])
        allP.append(EV); allF += [tuple(i + n for i in f) for f in EF]; allR += [R['eye']] * len(EF); n += len(EV)
    P = np.vstack(allP)
    P = np.stack([-P[:, 1], P[:, 0], P[:, 2]], 1) / H                    # face +x, height 1
    Fq = np.full((len(allF), 4), -1, np.int32)
    for i, f in enumerate(allF):
        if len(f) <= 4: Fq[i, :len(f)] = f
        else: Fq[i] = f[:4]
    hand = np.array([-hand[1], hand[0], hand[2]]) / H
    return P.astype(np.float32), Fq, np.array(allR, np.int8), hand.astype(np.float32)

out = {}; names = []
for sex, nm in (('m', 'GEO-body_male_realistic'), ('f', 'GEO-body_female_realistic')):
    for pose in ('stand', 'phone', 'walk'):
        for hem in (0.47, 0.30):
            for head in ('hair', 'hat'):
                key = '%s_%s_%s_%s' % (sex, pose, 'short' if hem > 0.4 else 'long', head)
                P, Fq, fr, hd = make(nm, pose, hem, head); out[key + '_h'] = hd; out[key + '_v'] = P; out[key + '_f'] = Fq; out[key + '_r'] = fr; names.append(key)
                print('variant', key, len(P), len(Fq))
np.savez_compressed(OUT, names=np.array(names), roles=np.array(ROLES), **out)
print('wrote', OUT)
