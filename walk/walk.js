// THE UNSUPERVISED SHIFT, the walk. West 317th Street, midnight to 8 a.m., on foot.
// The street is Cycles light baked twice in Blender (03:17 night, 07:13 dawn) and blended by the clock.
// Everything that changes is live from block.json, the same data the flat page and the renders use:
// every window, every shop, the lamps, the signal, the sky, the sun, the rain, and all 171 movers.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { clone as skClone } from 'three/addons/utils/SkeletonUtils.js';

const Q = new URLSearchParams(location.search);
const PHONE = matchMedia('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) < 600;
const BASE = window.WALK_BASE || ''; const A = BASE + 'assets/';
const $ = id => document.getElementById(id);
const END = 480, FAC = 9, ROAD = 5;
const T = s => { const [h, m, sec] = s.split(':').map(Number); return h * 60 + m + (sec || 0) / 60; };
const hm = t => { const m = Math.floor(t), s = Math.floor((t - m) * 60); return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0') + ':' + String(s).padStart(2, '0'); };
const lerp = (a, b, f) => a + (b - a) * f;
const smooth = (a, b, x) => { const f = Math.min(1, Math.max(0, (x - a) / (b - a))); return f * f * (3 - 2 * f); };
const v3 = (x, y, z) => new THREE.Vector3(x, z, -y);        // block coordinates (x along, y across, z up) to three

// ---------------------------------------------------------------- renderer
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas: $('c'), antialias: !PHONE, powerPreference: 'high-performance' }); }
catch (e) {        // no WebGL here: the photographed walk instead (pano.js), the same block in 360 at five moments
  document.querySelector('#loading p').textContent = 'No WebGL in this browser: loading the photographed walk.';
  try { await import('./pano.js'); } catch (e2) { document.querySelector('#loading p').innerHTML = 'This browser could not load the walk. <a href="/shift" target="_top" style="color:#D7FF1F">Watch the night on the flat page.</a>'; }
  throw e; }
renderer.setPixelRatio(Math.min(devicePixelRatio, PHONE ? 1.5 : 2));
renderer.toneMapping = THREE.AgXToneMapping; renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(PHONE ? 70 : 62, 1, 0.08, 2500);
function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();

const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
const load = url => new Promise((ok, no) => loader.load(url, ok, undefined, no));
const texLoader = new THREE.TextureLoader();
const tex = url => new Promise((ok, no) => texLoader.load(url, t => { t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; ok(t); }, undefined, no));
let loaded = 0, toLoad = 1;
const bump = () => { loaded++; $('bar-in').style.width = Math.min(100, 100 * loaded / toLoad) + '%'; };

// ---------------------------------------------------------------- the night, as data
const D = await (await fetch(A + 'block.json')).json();
const S = await (await fetch(A + 'scene.json')).json();
const shopLevel = (k, t) => { for (const [a, b, lv] of D.shops[k].lights) if ((a <= t && t < b) || (t >= END && b >= END)) return lv; return 0; };
const gateDown = (k, t) => D.shops[k].gate.some(([a, b]) => (a <= t && t < b) || (t >= END && b >= END));
function winLight(w, t) {
  const s = D.residents[w.unit].sched[w.room]; if (!s) return null;
  for (const [a, b, kind] of s) if ((a <= t && t < b) || (t >= END && b >= END)) {
    let lv = D.kind_lvl[kind]; if (kind === 'tv') lv *= 0.55 + 0.45 * (Math.sin(t * 37 + w.i * 1.7) * 0.5 + 0.5); return [kind, lv];
  } return null;
}
function moverAt(m, t) {
  const k = m.keys; if (t < k[0][0] || t > k[k.length - 1][0]) return null;
  for (let i = 0; i + 1 < k.length; i++) { const [t0, x0, y0] = k[i], [t1, x1, y1] = k[i + 1];
    if (t0 <= t && t <= t1) { const f = t1 === t0 ? 0 : (t - t0) / (t1 - t0), dx = x1 - x0, dy = y1 - y0, d = Math.hypot(dx, dy); return [x0 + dx * f, y0 + dy * f, d ? dx / d : 0, d ? dy / d : 0, d > 0]; } }
  return null;
}
const raining = t => D.rain[0] <= t && t < D.rain[1];
const lampsOn = t => t < D.lamps_off;
const carPresent = (c, t) => !((c.arrive != null && t < c.arrive) || (c.leave != null && t >= c.leave));
const signal = t => { const s = (t * 60) % 90; return s < 32 ? 'G' : s < 35 ? 'Y' : 'R'; };
const at = (arr, t) => { const i = Math.max(0, Math.min(arr.length - 2, Math.floor(t))), f = Math.min(1, Math.max(0, t - i)); return [arr[i], arr[i + 1], f]; };
function sunAt(t) { const [a, b, f] = at(D.sun, t); return [lerp(a[0], b[0], f), lerp(a[1], b[1], f)]; }
function skyAt(t) { const [a, b, f] = at(D.sky, t); return [0, 1].map(k => a[k].map((v, j) => lerp(v, b[k][j], f))); }
function sunVec(t) { const [el, az] = sunAt(t), th = (119 - az) * Math.PI / 180, e = el * Math.PI / 180; return v3(Math.cos(th) * Math.cos(e), Math.sin(th) * Math.cos(e), Math.sin(e)); }
function exposureAt(t) { const el = sunAt(t)[0]; if (el < -8) return 1.6; if (el > 6) return -0.85; let f = (el + 8) / 14; f = f * f * (3 - 2 * f); return 1.6 + (-0.85 - 1.6) * f; }
const dawnMix = t => smooth(372, 433, t);
const EXPO_OFF = Q.has('ev') ? +Q.get('ev') : -1.3;     // three's AgX has no Medium High Contrast look: a stop and a third under Blender's exposure matches the finals

// ---------------------------------------------------------------- the street: two baked states
const LMS = PHONE ? 'lm2k/' : 'lm/';
const atlasNames = Object.keys(S.atlases);
toLoad += 2 * atlasNames.length + 1;
const street = await load(A + 'street.glb'); bump();
const atlasMat = {};
const SCALE = S.scales;
await Promise.all(atlasNames.map(async k => {
  const [n, d] = await Promise.all([tex(A + LMS + 'night_' + k + '.jpg').then(t => (bump(), t)), tex(A + LMS + 'dawn_' + k + '.jpg').then(t => (bump(), t))]);
  atlasMat[k] = new THREE.ShaderMaterial({
    uniforms: { mapN: { value: n }, mapD: { value: d }, sN: { value: SCALE.night }, sD: { value: SCALE.dawn }, k: { value: 0 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform sampler2D mapN, mapD; uniform float sN, sD, k; varying vec2 vUv;
      void main(){ vec3 a = texture2D(mapN, vUv).rgb * sN; vec3 b = texture2D(mapD, vUv).rgb * sD; gl_FragColor = vec4(mix(a, b, k), 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
      }`, side: THREE.DoubleSide,
  });
}));
const GATES = {};
const glassMat = new THREE.MeshBasicMaterial({ color: 0x0a0d12, transparent: true, opacity: 0.28, depthWrite: false, side: THREE.DoubleSide });
const chainMat = new THREE.MeshBasicMaterial({ color: 0x4a4d50, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide });
const solids = [];
street.scene.traverse(o => {
  if (!o.isMesh) return;
  const mname = o.material.name || '', owner = (o.name || '') + ' ' + (o.parent ? o.parent.name : '');
  if (mname.startsWith('atlas_')) { o.material = atlasMat[mname.slice(6)]; solids.push(o); }
  else if (mname === 'glass') o.material = glassMat;
  else if (mname === 'chainlink') o.material = chainMat;
  const g = owner.match(/gate_([a-z]+)/); if (g) (GATES[g[1]] = GATES[g[1]] || []).push(o);
  o.matrixAutoUpdate = false; o.updateMatrix();
});
scene.add(street.scene);

// ---------------------------------------------------------------- windows: lit live
const paneGeo = new THREE.BufferGeometry(), PV = [], PI = [];
S.panes.forEach((p, i) => { const b = i * 4; p.p.forEach(q => PV.push(q[0], q[1], q[2])); PI.push(b, b + 1, b + 2, b, b + 2, b + 3); });
paneGeo.setAttribute('position', new THREE.Float32BufferAttribute(PV, 3)); paneGeo.setIndex(PI);
const paneCol = new THREE.Float32BufferAttribute(new Float32Array(S.panes.length * 12), 3); paneGeo.setAttribute('color', paneCol);
const panes = new THREE.Mesh(paneGeo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -1 }));
scene.add(panes);
const VR = S.panes.map((_, i) => 0.4 + 1.05 * ((Math.sin(i * 0.0137 + 3.17) * 43758.5453) % 1 + 1) % 1);
function paintWindows(t) {
  const [h] = skyAt(t), a = paneCol.array, dk = dawnMix(t);
  S.panes.forEach((p, i) => {
    let c;
    if (p.c) c = p.c;
    else { const w = D.windows[p.w], wl = w && winLight(w, t);
      if (wl) { const base = D.kind_rgb[wl[0]], k = wl[1] * 2.2 * VR[i]; c = [base[0] * k, base[1] * k, base[2] * k]; }
      else c = [0.012 + h[0] * 0.35 * dk, 0.014 + h[1] * 0.35 * dk, 0.018 + h[2] * 0.35 * dk]; }
    for (let v = 0; v < 4; v++) a.set(c, i * 12 + v * 3);
  });
  paneCol.needsUpdate = true;
}

// people standing in lit windows
const silMat = new THREE.MeshBasicMaterial({ color: 0x050403 });
const SIL = [];
load(A + 'silhouettes.glb').then(g => { g.scene.traverse(o => { if (o.isMesh) { o.material = silMat; const s = S.silhouettes.find(x => x.name === o.name || x.name === (o.parent && o.parent.name)); if (s) SIL.push([o, s]); } }); scene.add(g.scene); }).catch(() => {});

// ---------------------------------------------------------------- light for everything that is not baked
const hemi = new THREE.HemisphereLight(0x223040, 0x0a0806, 0.6); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffd0a0, 0); scene.add(sun); scene.add(sun.target);
const LAMPS = D.lamps.map(l => { const p = new THREE.PointLight(0xffc890, 0, 26, 1.6); p.position.copy(v3(l.x, (l.side === 'N' ? 1 : -1) * (FAC - 1.2), 6.4)); scene.add(p); return p; });
const SHOPL = PHONE ? [] : Object.entries(D.shops).map(([k, s]) => { const b = D.buildings.find(x => x.id === s.b); const sideN = b.side === 'N';
  const p = new THREE.PointLight(new THREE.Color(...s.glow), 0, 12, 1.8); p.position.copy(v3(b.x0 + b.w / 2, (sideN ? 1 : -1) * (FAC - 0.4), 2.4)); scene.add(p); return [k, p]; });

// the wet road: the bake is diffuse only, so the lamps, the neon and the sky on the wet asphalt are drawn live
const wetness = t => t < D.rain[0] ? 0 : t < D.rain[1] ? Math.min(1, (t - D.rain[0]) / 14) : Math.max(0.3, 1 - (t - D.rain[1]) / 420);
const SPEC = [...D.lamps.map(l => ({ p: v3(l.x, (l.side === 'N' ? 1 : -1) * (FAC - 2.6), 6.2), c: [1, 0.8, 0.55], lamp: true })),
  ...Object.entries(D.shops).map(([k, s]) => { const b = D.buildings.find(x => x.id === s.b); return { p: v3(b.x0 + b.w / 2, (b.side === 'N' ? 1 : -1) * (FAC - 0.2), 3.3), c: s.neon, shop: k }; })];
const wetMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, polygonOffset: true, polygonOffsetFactor: -2,
  uniforms: { lp: { value: SPEC.map(s => s.p) }, lc: { value: SPEC.map(() => new THREE.Vector3()) }, sky: { value: new THREE.Color() }, wet: { value: 0 } },
  vertexShader: 'varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
  fragmentShader: `uniform vec3 lp[${SPEC.length}]; uniform vec3 lc[${SPEC.length}]; uniform vec3 sky; uniform float wet; varying vec3 vW;
    void main(){ vec3 V = normalize(cameraPosition - vW); vec3 c = vec3(0.0);
      for (int i = 0; i < ${SPEC.length}; i++) { vec3 d = lp[i] - vW; vec3 L = normalize(d); vec3 H = normalize(L + V);
        float s = pow(max(H.y, 0.0), 420.0) * 1.4 + pow(max(H.y, 0.0), 60.0) * 0.012; c += lc[i] * s / (1.0 + dot(d, d) * 0.012); }
      float f = 0.01 + 0.22 * pow(1.0 - max(V.y, 0.0), 5.0); c += sky * f;
      gl_FragColor = vec4(c * wet, 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }` });
for (const [x0, x1, y0, y1, z] of [[-26, 122, -ROAD, ROAD, 0.012], [-24, -1.5, -22, 22, 0.012], [97.5, 120, -22, 22, 0.012], [-1.5, 97.5, ROAD, FAC, 0.172], [-1.5, 97.5, -FAC, -ROAD, 0.172]]) {
  const g = new THREE.PlaneGeometry(x1 - x0, y1 - y0); g.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(g, wetMat); m.position.copy(v3((x0 + x1) / 2, (y0 + y1) / 2, z)); m.renderOrder = 2; scene.add(m);
}

// sky: a dome with the horizon and zenith colours of the minute, and the sun's disc
const skyMat = new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false,
  uniforms: { h: { value: new THREE.Color() }, z: { value: new THREE.Color() }, sd: { value: new THREE.Vector3(0, 1, 0) }, sc: { value: new THREE.Color() }, su: { value: 0 } },
  vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); vec4 p = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * p; }',
  fragmentShader: `uniform vec3 h, z, sc, sd; uniform float su; varying vec3 vD;
    void main(){ float u = pow(clamp(vD.y / 0.55, 0.0, 1.0), 0.55); vec3 c = mix(h, z, u); float d = max(dot(normalize(vD), normalize(sd)), 0.0);
      c += sc * (pow(d, 2400.0) * 90.0 + pow(d, 12.0) * 1.2) * su; gl_FragColor = vec4(c, 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }` });
const skyDome = new THREE.Mesh(new THREE.SphereGeometry(1800, 32, 16), skyMat); scene.add(skyDome);

// ---------------------------------------------------------------- props, parked cars, trash
const dummy = new THREE.Object3D();
const cityMat = new THREE.MeshBasicMaterial({ color: 0x050608 });
const PILE_INST = [];          // [instancedMesh, index, pileNo, matrix]
toLoad += S.props.length;
await Promise.all(S.props.map(async p => {
  let g; try { g = await load(A + 'props/' + p.mesh + '.glb'); } catch (e) { bump(); return; } bump();
  g.scene.updateMatrixWorld(true);
  g.scene.traverse(o => {
    if (!o.isMesh) return;
    if (p.mesh.startsWith('city_')) o.material = cityMat;
    const im = new THREE.InstancedMesh(o.geometry, o.material, p.inst.length);
    p.inst.forEach((q, i) => { dummy.position.set(...q.p); dummy.quaternion.set(...q.q); dummy.scale.set(...q.s); dummy.updateMatrix();
      const m = dummy.matrix.clone().multiply(o.matrixWorld); im.setMatrixAt(i, m); if (q.pile >= 0) PILE_INST.push([im, i, q.pile, m]); });
    im.instanceMatrix.needsUpdate = true; im.frustumCulled = false; scene.add(im);
  });
}));
const ZERO = new THREE.Matrix4().makeScale(0, 0, 0);
const models = {};
const model = name => models[name] || (models[name] = load(A + 'cars/' + name + '.glb').then(g => g.scene).catch(() => null));
const PARKED = [];
toLoad += S.parked.length;
await Promise.all(S.parked.map(async (c, i) => { const m = await model(c.model); bump(); if (!m) return;
  const o = m.clone(); o.position.set(...c.p); o.quaternion.set(...c.q); o.scale.set(...c.s); scene.add(o); PARKED.push([o, c]); }));

// ---------------------------------------------------------------- the movers: everyone and everything on the block tonight
const CAST = {};
const castModel = name => CAST[name] || (CAST[name] = load(A + 'cast/' + name + '.glb').then(g => { g.scene.updateMatrixWorld(true);
  const bb = new THREE.Box3().setFromObject(g.scene); return { scene: g.scene, clips: g.animations, foot: bb.min.y, cx: (bb.min.x + bb.max.x) / 2, cz: (bb.min.z + bb.max.z) / 2 }; }).catch(() => null));
const FIX = { writer: Math.PI / 2 };
const MV = S.movers.map(r => ({ r, m: D.movers[r.i], obj: null, mixer: null, acts: null, cur: null, loading: false }));
async function make(mv) {
  mv.loading = true; const r = mv.r, root = new THREE.Group();
  if (r.cast) {
    const c = await castModel(r.cast); if (!c) return;
    const o = skClone(c.scene); o.position.set(-c.cx, -c.foot, -c.cz); const pivot = new THREE.Group(); pivot.add(o);
    pivot.scale.setScalar(r.local ? r.local.s[0] : 1); pivot.rotation.y = FIX[r.cast] || 0; root.add(pivot);
    o.traverse(x => { if (x.isMesh) { x.frustumCulled = false; } });
    mv.mixer = new THREE.AnimationMixer(o); mv.acts = {};
    for (const cl of c.clips) mv.acts[cl.name] = mv.mixer.clipAction(cl);
  } else {
    if (r.model) { const m = await model(r.model); if (m) { const o = m.clone(); o.position.set(...r.local.p); o.quaternion.set(...r.local.q); o.scale.set(...r.local.s); root.add(o); } }
    if (r.veh) { const v = await load(A + 'cars/' + r.veh + '.glb').catch(() => null); if (v) root.add(v.scene); }
  }
  root.visible = false; scene.add(root); mv.obj = root;
}
function play(mv, name) {
  if (!mv.acts || mv.cur === name) return; const a = mv.acts[name] || mv.acts.idle || Object.values(mv.acts)[0]; if (!a) return;
  if (mv.cur && mv.acts[mv.cur]) mv.acts[mv.cur].fadeOut(0.25); a.reset().fadeIn(0.25).play(); mv.cur = name;
}

// ---------------------------------------------------------------- rain
const RN = PHONE ? 1500 : 4000, rainGeo = new THREE.BufferGeometry(), RP = new Float32Array(RN * 6);
for (let i = 0; i < RN; i++) { const x = (Math.random() - 0.5) * 40, y = Math.random() * 18, z = (Math.random() - 0.5) * 40; RP.set([x, y, z, x + 0.02, y - 0.5, z], i * 6); }
rainGeo.setAttribute('position', new THREE.BufferAttribute(RP, 3));
const rain = new THREE.LineSegments(rainGeo, new THREE.LineBasicMaterial({ color: 0x8090a0, transparent: true, opacity: 0.35 })); rain.frustumCulled = false; scene.add(rain);

// ---------------------------------------------------------------- the clock
let t = Q.has('t') ? T(Q.get('t')) : T('03:16:30'), speed = Q.has('speed') ? +Q.get('speed') : 1, playing = true, lastPaint = -1;
const SPEEDS = [[1, 'real time'], [10, '10x'], [60, '1 min/s'], [240, '4 min/s']];
function applyTime() {
  const k = dawnMix(t), [h, z] = skyAt(t), [el] = sunAt(t), sv = sunVec(t);
  for (const m of Object.values(atlasMat)) m.uniforms.k.value = k;
  renderer.toneMappingExposure = Math.pow(2, exposureAt(t) + EXPO_OFF);
  skyMat.uniforms.h.value.setRGB(...h); skyMat.uniforms.z.value.setRGB(...z); skyMat.uniforms.sd.value.copy(sv);
  const up = Math.max(0, Math.min(1, (el + 1.2) / 1.6)); skyMat.uniforms.su.value = up;
  const sc = el > 0 ? Math.min(1, el / 14) : 0; skyMat.uniforms.sc.value.setRGB(1, lerp(0.42, 0.86, sc), lerp(0.16, 0.7, sc));
  hemi.color.setRGB(h[0] * 1.6 + 0.012, h[1] * 1.6 + 0.014, h[2] * 1.6 + 0.02); hemi.groundColor.setRGB(0.02, 0.016, 0.012); hemi.intensity = 0.8;
  sun.intensity = el > -0.8 ? Math.min(6, 0.4 + (el + 0.8) * 0.6) : 0; sun.color.setRGB(1, lerp(0.42, 0.86, sc), lerp(0.16, 0.7, sc));
  sun.position.copy(camera.position).addScaledVector(sv, 80); sun.target.position.copy(camera.position);
  const lo = lampsOn(t); for (const p of LAMPS) p.intensity = lo ? 28 : 0;
  for (const [k, p] of SHOPL) p.intensity = 14 * shopLevel(k, t);
  for (const [k, objs] of Object.entries(GATES)) { const d = gateDown(k, t); for (const o of objs) o.visible = d; }
  for (const [o, c] of PARKED) o.visible = carPresent(c, t);
  for (const [im, i, pile, m] of PILE_INST) { const p = D.piles[pile]; im.setMatrixAt(i, (p && p.appear <= t && t < p.gone) ? m : ZERO); im.instanceMatrix.needsUpdate = true; }
  for (const [o, s] of SIL) o.visible = s.a <= t && (t < s.b || (t >= END && s.b >= END));
  rain.visible = raining(t);
  wetMat.uniforms.wet.value = (0.25 + 0.75 * wetness(t)) * (1 - 0.85 * k);     // the streaks fade as the sun comes up
  wetMat.uniforms.sky.value.setRGB(...h);
  SPEC.forEach((s, i) => { const lv = s.lamp ? (lo ? 4 : 0) : (shopLevel(s.shop, t) >= 0.5 ? 0.45 : 0); wetMat.uniforms.lc.value[i].set(s.c[0] * lv, s.c[1] * lv, s.c[2] * lv); });
  cityMat.color.setRGB(0.006 + h[0] * 0.55, 0.007 + h[1] * 0.55, 0.01 + h[2] * 0.55);
  if (Math.abs(t - lastPaint) > 1 / 60) { paintWindows(t); lastPaint = t; }
}
const GROUND = 0.16;
function placeMovers(dt) {
  const camX = camera.position.x, camZ = camera.position.z;
  for (const mv of MV) {
    const p = moverAt(mv.m, t);
    if (!p) { if (mv.obj) mv.obj.visible = false; continue; }
    const [x, y, hx, hy, moving] = p, pos = v3(x, y, Math.abs(y) > ROAD ? GROUND : 0);
    const near = Math.hypot(pos.x - camX, pos.z - camZ) < (PHONE ? 70 : 140);
    if (!mv.obj) { if (!mv.loading && near) make(mv); continue; }
    mv.obj.visible = near; if (!near) continue;
    mv.obj.position.copy(pos);
    const k = mv.r.kind;
    if (k === 'person' || k === 'cat' || k === 'rat') { if (moving) mv.obj.rotation.y = Math.atan2(hx, -hy) + (mv.r.cast ? 0 : -Math.PI / 2); }
    if (mv.mixer) { play(mv, moving ? 'walk' : 'idle'); mv.mixer.timeScale = Math.min(4, speed); mv.mixer.update(dt); }
  }
}

// ---------------------------------------------------------------- walking
camera.rotation.order = 'YXZ';
let yaw = Q.has('yaw') ? +Q.get('yaw') : -Math.PI / 2, pitch = 0.04;
camera.position.copy(v3(Q.has('x') ? +Q.get('x') : -4, Q.has('y') ? +Q.get('y') : 1.1, 1.62));
const keys = {};
addEventListener('keydown', e => { keys[e.code] = true; if (e.code === 'Space') { playing = !playing; syncUI(); e.preventDefault(); } if (e.code === 'KeyN') $('nb').click(); });
addEventListener('keyup', e => { keys[e.code] = false; });
const cv = $('c');
cv.addEventListener('click', () => { if (!PHONE && document.pointerLockElement !== cv) { try { const p = cv.requestPointerLock(); if (p && p.catch) p.catch(() => {}); } catch (e) {} } });
addEventListener('mousemove', e => { if (document.pointerLockElement === cv) { yaw -= e.movementX * 0.0022; pitch = Math.max(-1.3, Math.min(1.3, pitch - e.movementY * 0.0022)); } });
// phone: left half walks, right half looks
const touch = { move: null, look: null, mx: 0, my: 0 };
cv.addEventListener('touchstart', e => { for (const tc of e.changedTouches) { if (tc.clientX < innerWidth * 0.42 && !touch.move) touch.move = { id: tc.identifier, x0: tc.clientX, y0: tc.clientY }; else if (!touch.look) touch.look = { id: tc.identifier, x: tc.clientX, y: tc.clientY }; } e.preventDefault(); }, { passive: false });
cv.addEventListener('touchmove', e => { for (const tc of e.changedTouches) {
  if (touch.move && tc.identifier === touch.move.id) { touch.mx = Math.max(-1, Math.min(1, (tc.clientX - touch.move.x0) / 60)); touch.my = Math.max(-1, Math.min(1, (tc.clientY - touch.move.y0) / 60)); $('stick').style.display = 'block'; $('stick').style.left = (touch.move.x0 - 40) + 'px'; $('stick').style.top = (touch.move.y0 - 40) + 'px'; }
  if (touch.look && tc.identifier === touch.look.id) { yaw -= (tc.clientX - touch.look.x) * 0.005; pitch = Math.max(-1.3, Math.min(1.3, pitch - (tc.clientY - touch.look.y) * 0.005)); touch.look.x = tc.clientX; touch.look.y = tc.clientY; } } e.preventDefault(); }, { passive: false });
cv.addEventListener('touchend', e => { for (const tc of e.changedTouches) { if (touch.move && tc.identifier === touch.move.id) { touch.move = null; touch.mx = touch.my = 0; $('stick').style.display = 'none'; } if (touch.look && tc.identifier === touch.look.id) touch.look = null; } });
function walkable(x, y) {           // block coordinates: the street, both sidewalks, and the two avenues at the ends
  if (x < -1.5 || x > 97.5) return x > -24 && x < 120 && Math.abs(y) < 22;
  return Math.abs(y) < FAC - 0.35;
}
function move(dt) {
  const run = keys.ShiftLeft || keys.ShiftRight ? 2.2 : 1;
  let f = (keys.KeyW || keys.ArrowUp ? 1 : 0) - (keys.KeyS || keys.ArrowDown ? 1 : 0) - touch.my, s = (keys.KeyD || keys.ArrowRight ? 1 : 0) - (keys.KeyA || keys.ArrowLeft ? 1 : 0) + touch.mx;
  if (keys.KeyQ) yaw += dt * 1.6; if (keys.KeyE) yaw -= dt * 1.6;
  const len = Math.hypot(f, s); if (len > 1) { f /= len; s /= len; }
  const v = 1.45 * run * dt, dx = (-Math.sin(yaw) * f + Math.cos(yaw) * s) * v, dz = (-Math.cos(yaw) * f - Math.sin(yaw) * s) * v;
  const p = camera.position, bx = p.x + dx, by = -(p.z + dz);
  if (walkable(bx, by)) { p.x += dx; p.z += dz; } else if (walkable(bx, -p.z)) p.x += dx; else if (walkable(p.x, by)) p.z += dz;
  const by2 = -p.z, gh = (Math.abs(by2) > ROAD && p.x > -1.5 && p.x < 97.5) ? GROUND : 0;
  p.y = lerp(p.y, gh + 1.62, Math.min(1, dt * 10));
  camera.rotation.set(pitch, yaw, 0);
}

// ---------------------------------------------------------------- who lives here: look at a lit window
const ray = new THREE.Raycaster(); ray.far = 45;
let lookTick = 0;
function lookAtWindow() {
  ray.setFromCamera({ x: 0, y: 0 }, camera); const h = ray.intersectObject(panes)[0];
  const tip = $('tip');
  if (!h) { tip.style.opacity = 0; return; }
  const p = S.panes[Math.floor(h.faceIndex / 2)], w = p && D.windows[p.w];
  if (!w) { tip.style.opacity = 0; return; }
  const r = D.residents[w.unit], wl = winLight(w, t);
  tip.innerHTML = `<b>${r.who}</b> · ${w.unit}, ${w.room}${wl ? '' : ' (dark)'}<br>${r.line}`; tip.style.opacity = 1;
}

// ---------------------------------------------------------------- the log and the controls
const LOG = D.log; let logShown = -1;
function showLog() {
  let i = -1; for (let j = 0; j < LOG.length; j++) if (LOG[j][0] <= t) i = j;
  if (i === logShown) return; logShown = i;
  $('log').innerHTML = LOG.slice(Math.max(0, i - 2), i + 1).map(([m, s]) => `<div><b>${hm(m).slice(0, 5)}</b> ${s}</div>`).join('');
}
function syncUI() {
  $('play').textContent = playing ? 'pause' : 'play';
  document.querySelectorAll('[data-s]').forEach(b => b.classList.toggle('on', +b.dataset.s === speed));
}
const ctl = $('ctl');
SPEEDS.forEach(([s, l]) => { const b = document.createElement('button'); b.dataset.s = s; b.textContent = l; b.onclick = () => { speed = s; syncUI(); }; ctl.insertBefore(b, $('nb')); });
$('play').onclick = () => { playing = !playing; syncUI(); };
const MOMENTS = [['00:00', 'midnight'], ['02:12', 'the rain'], ['03:16:30', 'the cat'], ['05:20', 'kitchens'], ['06:34', 'lamps off'], ['07:12:30', 'sun in the slot']];
for (const [s, l] of MOMENTS) { const b = document.createElement('button'); b.textContent = s.slice(0, 5) + ' ' + l; b.onclick = () => { t = T(s); lastPaint = -1; logShown = -2; }; $('moments').appendChild(b); }
const bar = $('scrub');
bar.addEventListener('input', () => { t = +bar.value; lastPaint = -1; });
syncUI();

// ---------------------------------------------------------------- go
$('loading').classList.add('done'); setTimeout(() => $('loading').remove(), 900);
let last = performance.now();
function frame(now) {
  const dt = Math.max(0, Math.min(0.1, (now - last) / 1000)); last = now;
  if (playing) { t += dt * speed / 60; if (t >= END) t = 0; }
  move(dt); applyTime(); placeMovers(dt * (playing ? 1 : 0));
  rain.position.set(camera.position.x, 0, camera.position.z);
  if (rain.visible) { const a = rain.geometry.attributes.position.array, fall = dt * 9 * Math.max(1, Math.min(4, speed / 10));
    for (let i = 0; i < a.length; i += 6) { a[i + 1] -= fall; a[i + 4] -= fall; if (a[i + 4] < 0) { a[i + 1] += 18; a[i + 4] += 18; } } rain.geometry.attributes.position.needsUpdate = true; }
  skyDome.position.copy(camera.position);
  if ((lookTick += dt) > 0.2) { lookTick = 0; lookAtWindow(); }
  $('clock').textContent = hm(t).slice(0, speed >= 60 ? 5 : 8); bar.value = t; showLog();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
// a 360 photograph of where you stand, for the no-WebGL version of the walk (tools/panos.mjs calls it headless)
async function pano(W = 2048) {
  const H = W / 2, rt = new THREE.WebGLCubeRenderTarget(1024, { type: THREE.HalfFloatType });
  const cc = new THREE.CubeCamera(0.08, 2500, rt); cc.position.copy(camera.position); scene.add(cc);
  applyTime(); placeMovers(0); skyDome.position.copy(camera.position); cc.update(renderer, scene); scene.remove(cc);
  const m = new THREE.ShaderMaterial({ uniforms: { cube: { value: rt.texture } }, depthTest: false,
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform samplerCube cube; varying vec2 vUv;
      void main(){ float lon = (vUv.x - 0.5) * 6.2831853, lat = (vUv.y - 0.5) * 3.1415927;
        vec3 d = vec3(sin(lon) * cos(lat), sin(lat), -cos(lon) * cos(lat)); gl_FragColor = vec4(textureCube(cube, d).rgb, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }` });
  const q = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), m), qs = new THREE.Scene(); qs.add(q);
  const keep = renderer.getSize(new THREE.Vector2()), pr = renderer.getPixelRatio();
  renderer.setPixelRatio(1); renderer.setSize(W, H, false); renderer.render(qs, new THREE.Camera());
  const url = renderer.domElement.toDataURL('image/jpeg', 0.72);
  renderer.setPixelRatio(pr); renderer.setSize(keep.x, keep.y, false); rt.dispose(); m.dispose();
  return url;
}
window.__walk = { THREE, MV, pano, get t() { return t; }, set t(v) { t = v; lastPaint = -1; }, camera, renderer, scene, render: () => { applyTime(); placeMovers(0); renderer.render(scene, camera); }, setView(x, y, yw, pt) { camera.position.copy(v3(x, y, 1.62 + ((Math.abs(y) > ROAD) ? GROUND : 0))); yaw = yw; pitch = pt || 0; camera.rotation.set(pitch, yaw, 0); } };
