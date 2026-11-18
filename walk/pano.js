// THE UNSUPERVISED SHIFT, the walk for browsers without WebGL.
// The same block, photographed from the real walk: 360 views every 8 metres along both sidewalks at five moments
// of the night (tools/panos.mjs). Drawn with plain canvas pixels, so it runs anywhere a page runs.
const BASE = window.WALK_BASE || '', A = BASE + 'assets/';
const $ = id => document.getElementById(id);
for (const id of ['help', 'moments', 'ctl', 'cross', 'scrub']) { const e = $(id); if (e) e.style.display = 'none'; }
const P = await (await fetch(A + 'pano/panos.json')).json();
const D = await (await fetch(A + 'block.json')).json().catch(() => null);
const T = s => { const [h, m, sec] = s.split(':').map(Number); return h * 60 + m + (sec || 0) / 60; };

const old = $('c'), cv = old.cloneNode(); old.replaceWith(cv); const ctx = cv.getContext('2d', { willReadFrequently: false });
const ui = document.createElement('div');
ui.innerHTML = `<style>@media (max-width:700px){#pnote{display:none}#pctl button,#pctl a.b{font-size:10px;padding:3px 5px}#pctl{max-width:58vw!important}#pbar button{font-size:11px;padding:6px 8px}#log{bottom:64px!important}}</style><div id="pnote" style="position:fixed;left:16px;right:16px;top:74px;max-width:520px;font-size:11px;opacity:.75;pointer-events:none">This browser has no WebGL, so this is the photographed walk: the block in 360 every eight metres, at five moments of the night. Drag to look. Click or tap to step where you look.</div>
<div id="pctl" style="position:fixed;right:12px;top:12px;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:62vw"></div>
<div id="pbar" style="position:fixed;left:50%;bottom:18px;transform:translateX(-50%);display:flex;gap:8px;white-space:nowrap"><button id="pback">step back</button><button id="pfwd">step forward</button><button id="pcross">cross the street</button></div>`;
document.body.appendChild(ui);
for (const m of P.moments) { const b = document.createElement('button'); b.textContent = m.t.slice(0, 5) + ' ' + m.l; b.dataset.k = m.k; b.onclick = () => go(node, m.k); $('pctl').appendChild(b); }
const a = document.createElement('a'); a.className = 'b'; a.href = '/shift'; a.target = '_top'; a.textContent = 'the piece'; $('pctl').appendChild(a);

let node = P.nodes[1], moment = '0317', yaw = Math.PI / 2, pitch = 0, src = null, SW = 0, SH = 0;
const cache = new Map();
function load(k, nd) {
  const key = k + '_' + nd.id; if (cache.has(key)) return cache.get(key);
  const pr = new Promise((ok, no) => { const im = new Image(); im.onload = () => {
    const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0);
    ok({ w: im.width, h: im.height, px: new Uint32Array(x.getImageData(0, 0, im.width, im.height).data.buffer) }); }; im.onerror = no; im.src = A + 'pano/' + key + '.jpg'; });
  cache.set(key, pr); if (cache.size > 24) cache.delete(cache.keys().next().value); return pr;
}
// the view: a lookup of every screen pixel's longitude offset and row, rebuilt when the size or the pitch changes
let W = 0, H = 0, out = null, img = null, LON = null, ROW = null, lutPitch = null;
function resize() {
  const s = Math.min(1, 900 / Math.max(innerWidth, innerHeight));         // a little under the screen: the CPU draws every pixel
  W = Math.round(innerWidth * s); H = Math.round(innerHeight * s); cv.width = W; cv.height = H; cv.style.imageRendering = 'auto';
  img = ctx.createImageData(W, H); out = new Uint32Array(img.data.buffer); lutPitch = null; draw();
}
function lut() {
  const f = (W > H ? 72 : 62) * Math.PI / 180, fx = Math.tan(f / 2), fy = fx * H / W, cp = Math.cos(pitch), sp = Math.sin(pitch);
  LON = new Float32Array(W * H); ROW = new Float32Array(W * H);
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const x = ((i + 0.5) / W * 2 - 1) * fx, y = (1 - (j + 0.5) / H * 2) * fy, z = 1;
    const yy = y * cp + z * sp, zz = -y * sp + z * cp, n = Math.hypot(x, yy, zz);
    const k = j * W + i; LON[k] = Math.atan2(x, zz) / (2 * Math.PI); ROW[k] = Math.asin(yy / n) / Math.PI;
  }
  lutPitch = pitch;
}
function draw() {
  if (!src || !W) return; if (lutPitch !== pitch) lut();
  const sw = src.w, sh = src.h, px = src.px, y0 = yaw / (2 * Math.PI);
  for (let k = 0, n = W * H; k < n; k++) {
    let u = LON[k] + y0 + 0.5; u -= Math.floor(u); const c = (u * sw) | 0, r = ((0.5 - ROW[k]) * sh) | 0;
    out[k] = px[(r < 0 ? 0 : r >= sh ? sh - 1 : r) * sw + c];
  }
  ctx.putImageData(img, 0, 0);
}
async function go(nd, k) {
  const s = await load(k, nd); node = nd; moment = k; src = s; draw();
  const m = P.moments.find(x => x.k === k); $('clock').textContent = m.t.slice(0, 5);
  document.querySelectorAll('#pctl button').forEach(b => b.classList.toggle('on', b.dataset.k === k));
  if (D) { const t = T(m.t); let i = -1; for (let j = 0; j < D.log.length; j++) if (D.log[j][0] <= t) i = j;
    $('log').innerHTML = D.log.slice(Math.max(0, i - 1), i + 1).map(([mm, s]) => `<div><b>${String(Math.floor(mm / 60)).padStart(2, '0')}:${String(Math.floor(mm % 60)).padStart(2, '0')}</b> ${s}</div>`).join(''); }
  for (const n2 of P.nodes) if (Math.hypot(n2.x - nd.x, n2.y - nd.y) < 13) load(k, n2);        // the next steps, ahead of time
}
function step(dir) {       // the nearest node within 45 degrees of where you look (or behind you)
  const ly = yaw + (dir < 0 ? Math.PI : 0); let best = null, bd = 1e9;
  for (const n2 of P.nodes) { if (n2 === node) continue; const dx = n2.x - node.x, dy = n2.y - node.y, d = Math.hypot(dx, dy); if (d > 13) continue;
    let da = Math.atan2(dx, dy) - ly; da = Math.atan2(Math.sin(da), Math.cos(da)); if (Math.abs(da) < Math.PI / 4 && d < bd) { bd = d; best = n2; } }
  if (best) go(best, moment);
}
function cross() { const n2 = P.nodes.reduce((b, n) => (Math.sign(n.y) !== Math.sign(node.y) && (!b || Math.abs(n.x - node.x) < Math.abs(b.x - node.x))) ? n : b, null); if (n2) { yaw = Math.atan2(0, n2.y - node.y); go(n2, moment); } }
$('pfwd').onclick = () => step(1); $('pback').onclick = () => step(-1); $('pcross').onclick = cross;
let drag = null, moved = 0;
cv.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY }; moved = 0; cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointermove', e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy);
  yaw -= dx * 0.005; pitch = Math.max(-0.9, Math.min(0.9, pitch + dy * 0.004)); drag = { x: e.clientX, y: e.clientY }; draw(); });
cv.addEventListener('pointerup', () => { if (drag && moved < 6) step(1); drag = null; });
addEventListener('keydown', e => { if (e.code === 'KeyW' || e.code === 'ArrowUp') step(1); else if (e.code === 'KeyS' || e.code === 'ArrowDown') step(-1);
  else if (e.code === 'KeyA' || e.code === 'ArrowLeft') { yaw -= 0.15; draw(); } else if (e.code === 'KeyD' || e.code === 'ArrowRight') { yaw += 0.15; draw(); } });
addEventListener('resize', resize);
cv.style.touchAction = 'none';
resize(); await go(node, moment);
$('loading') && ($('loading').classList.add('done'), setTimeout(() => $('loading') && $('loading').remove(), 900));
window.__pano = { go, step, get yaw() { return yaw; }, set yaw(v) { yaw = v; draw(); }, P };
