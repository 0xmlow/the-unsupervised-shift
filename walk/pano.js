// THE UNSUPERVISED SHIFT, the walk for browsers without WebGL.
// The same block rendered in Cycles in 360 (tools/pano_render.py): every 8 metres along both sidewalks at five moments
// of the night. Drawn with plain canvas pixels, so it runs anywhere a page runs. The interface is ui.js (Nov 19).
const BASE = window.WALK_BASE || '', A = BASE + 'assets/', VQ = window.WALK_V ? '?v=' + window.WALK_V : '';
const $ = id => document.getElementById(id);
const P = await (await fetch(A + 'pano/panos.json' + VQ)).json();
const PHONE = matchMedia('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) < 600;
const D = await (await fetch(A + 'block.json' + VQ)).json().catch(() => null);
const T = s => { const [h, m, sec] = s.split(':').map(Number); return h * 60 + m + (sec || 0) / 60; };

const old = $('c'), cv = old.cloneNode(); old.replaceWith(cv); const ctx = cv.getContext('2d');
const V = window.WALK_V || '';
const { mountUI } = await import('./ui.js' + (V ? '?v=' + V : ''));
const MOM = P.moments.map(m => ({ k: m.k, t: T(m.t), label: { '0030': 'Half past midnight', '0240': 'The rain', '0317': 'The cat crosses', '0520': 'Kitchens', '0713': 'Sun in the slot' }[m.k] || m.l }));
const STATE = { '0030': 'Just after midnight. The block is still deciding.', '0240': 'Raining. Everyone has decided not to go out.', '0317': 'The quiet hours. The cat has right of way.',
  '0520': 'The early shift is up. The late shift is not down yet.', '0713': 'The sun is lined up with the street.' };
window.__uiP = () => U;
const nearestMoment = t => MOM.reduce((b, m) => Math.abs(m.t - t) < Math.abs(b.t - t) ? m : b, MOM[0]);
const U = await mountUI({
  end: 480, log: D ? D.log : [], canvas: () => cv,
  moments: MOM, onMoment: i => go(node, MOM[i].k),
  onScrub: (t, done) => { if (done) go(node, nearestMoment(t).k); },
  onStep: d => step(d), onCross: () => cross(),
  help: PHONE ? '' : '<b>drag</b> look · <b>click</b> step where you look<br><b>W S</b> step · <b>C</b> photo · <b>R</b> record<br>photographed in Cycles, in 360, every eight metres',
});
window.__ui = U;
let node = P.nodes[1], moment = '0317', yaw = Math.PI / 2, pitch = 0, src = null;
const imgs = new Map();           // compressed images only; the one we stand in is decoded to pixels
function image(dir, key) {
  const k = dir + key; if (imgs.has(k)) return imgs.get(k);
  const pr = new Promise((ok, no) => { const im = new Image(); im.decoding = 'async'; im.onload = () => ok(im); im.onerror = no; im.src = A + dir + '/' + key + '.jpg' + VQ; });
  imgs.set(k, pr); if (imgs.size > 40) imgs.delete(imgs.keys().next().value); return pr;
}
function pixels(im) {
  const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight; const x = c.getContext('2d'); x.drawImage(im, 0, 0);
  return { w: c.width, h: c.height, px: new Uint32Array(x.getImageData(0, 0, c.width, c.height).data.buffer) };
}
// the view: every screen pixel's longitude offset and row, rebuilt when the size or the pitch changes
let W = 0, H = 0, out = null, img = null, LON = null, ROW = null, lutKey = '', fast = false, idle = 0;
function size(f) {
  const s = f ? 0.5 : Math.min(devicePixelRatio || 1, 2), cap = 4.2e6;
  let w = Math.round(innerWidth * s), h = Math.round(innerHeight * s); const k = Math.min(1, Math.sqrt(cap / (w * h))); w = Math.round(w * k); h = Math.round(h * k);
  if (w !== W || h !== H) { W = w; H = h; cv.width = W; cv.height = H; img = ctx.createImageData(W, H); out = new Uint32Array(img.data.buffer); }
}
function lut() {
  const key = W + 'x' + H + ':' + pitch; if (key === lutKey) return; lutKey = key;
  const f = (W > H ? 74 : 64) * Math.PI / 180, fx = Math.tan(f / 2), fy = fx * H / W, cp = Math.cos(pitch), sp = Math.sin(pitch);
  LON = new Float32Array(W * H); ROW = new Float32Array(W * H);
  for (let j = 0; j < H; j++) { const y = (1 - (j + 0.5) / H * 2) * fy, yy = y * cp + sp, zz = -y * sp + cp;
    for (let i = 0; i < W; i++) { const x = ((i + 0.5) / W * 2 - 1) * fx, k = j * W + i, n = Math.hypot(x, yy, zz);
      LON[k] = Math.atan2(x, zz) / (2 * Math.PI); ROW[k] = 0.5 - Math.asin(yy / n) / Math.PI; } }
}
function draw() {
  if (!src) return; size(fast); lut();
  const sw = src.w, sh = src.h, px = src.px, y0 = yaw / (2 * Math.PI) + 0.5, n = W * H;
  if (fast) {
    for (let k = 0; k < n; k++) { let u = LON[k] + y0; u -= Math.floor(u); let r = (ROW[k] * sh) | 0; if (r >= sh) r = sh - 1; out[k] = px[r * sw + ((u * sw) | 0)]; }
  } else {
    for (let k = 0; k < n; k++) {
      let u = LON[k] + y0; u -= Math.floor(u); const fu = u * sw - 0.5, fv = ROW[k] * sh - 0.5;
      let x0 = Math.floor(fu), y = Math.floor(fv); const ax = fu - x0, ay = fv - y;
      if (x0 < 0) x0 += sw; const x1 = x0 + 1 === sw ? 0 : x0 + 1; const ya = y < 0 ? 0 : y >= sh ? sh - 1 : y, yb = y + 1 >= sh ? sh - 1 : y + 1 < 0 ? 0 : y + 1;
      const p00 = px[ya * sw + x0], p10 = px[ya * sw + x1], p01 = px[yb * sw + x0], p11 = px[yb * sw + x1];
      const w00 = (1 - ax) * (1 - ay), w10 = ax * (1 - ay), w01 = (1 - ax) * ay, w11 = ax * ay;
      const r = (p00 & 255) * w00 + (p10 & 255) * w10 + (p01 & 255) * w01 + (p11 & 255) * w11;
      const g = (p00 >> 8 & 255) * w00 + (p10 >> 8 & 255) * w10 + (p01 >> 8 & 255) * w01 + (p11 >> 8 & 255) * w11;
      const b = (p00 >> 16 & 255) * w00 + (p10 >> 16 & 255) * w10 + (p01 >> 16 & 255) * w01 + (p11 >> 16 & 255) * w11;
      out[k] = 0xff000000 | (b << 16) | (g << 8) | r;
    }
  }
  ctx.putImageData(img, 0, 0);
}
function sharpenSoon() { clearTimeout(idle); idle = setTimeout(() => { fast = false; draw(); }, 140); }
const resize = () => { fast = false; draw(); };
let goId = 0;
async function go(nd, k) {
  const id = ++goId, key = k + '_' + nd.id, m = P.moments.find(x => x.k === k);
  U.say('DEVELOPING');
  const small = await image('pano_s', key); if (id !== goId) return;
  node = nd; moment = k; src = pixels(small); fast = false; draw();
  U.setTime(T(m.t), { seconds: false }); U.setMoment(MOM.findIndex(x => x.k === k)); U.setState(STATE[k]);
  for (const n2 of P.nodes) if (Math.hypot(n2.x - nd.x, n2.y - nd.y) < 13) image('pano_s', k + '_' + n2.id);       // the next steps, ahead of time
  if (!PHONE) { const big = await image('pano', key).catch(() => null); if (big && id === goId) { src = pixels(big); draw(); } }
}
function step(dir) {       // the nearest node within 45 degrees of where you look (or behind you)
  const ly = yaw + (dir < 0 ? Math.PI : 0); let best = null, bd = 1e9;
  for (const n2 of P.nodes) { if (n2 === node) continue; const dx = n2.x - node.x, dy = n2.y - node.y, d = Math.hypot(dx, dy); if (d > 13) continue;
    let da = Math.atan2(dx, dy) - ly; da = Math.atan2(Math.sin(da), Math.cos(da)); if (Math.abs(da) < Math.PI / 4 && d < bd) { bd = d; best = n2; } }
  if (best) go(best, moment);
}
function cross() { const n2 = P.nodes.reduce((b, n) => (Math.sign(n.y) !== Math.sign(node.y) && (!b || Math.abs(n.x - node.x) < Math.abs(b.x - node.x))) ? n : b, null); if (n2) { yaw = Math.atan2(0, n2.y - node.y); go(n2, moment); } }
let drag = null, moved = 0;
cv.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY }; moved = 0; cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointermove', e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy);
  yaw -= dx * 0.004; pitch = Math.max(-0.9, Math.min(0.9, pitch + dy * 0.003)); drag = { x: e.clientX, y: e.clientY }; fast = true; draw(); sharpenSoon(); });
cv.addEventListener('pointerup', () => { if (drag && moved < 6) step(1); drag = null; });
addEventListener('keydown', e => { if (e.code === 'KeyW' || e.code === 'ArrowUp') step(1); else if (e.code === 'KeyS' || e.code === 'ArrowDown') step(-1);
  else if (e.code === 'KeyA' || e.code === 'ArrowLeft') { yaw -= 0.15; fast = true; draw(); sharpenSoon(); } else if (e.code === 'KeyD' || e.code === 'ArrowRight') { yaw += 0.15; fast = true; draw(); sharpenSoon(); } });
addEventListener('resize', resize);
cv.style.touchAction = 'none';
await go(node, moment);
$('loading') && ($('loading').classList.add('done'), setTimeout(() => $('loading') && $('loading').remove(), 900));
window.__pano = { go, step, get yaw() { return yaw; }, set yaw(v) { yaw = v; fast = false; draw(); }, P };
