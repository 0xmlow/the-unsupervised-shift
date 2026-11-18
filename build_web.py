"""
THE UNSUPERVISED SHIFT  ·  experiment 53 of 100  ·  build_web.py
Writes index.html: one file, no libraries, opens by double-click.

    python3 build_web.py

It embeds block.json (written by block.py) and every entry of NOTEBOOK.md, so run it again
after the notebook changes. The page draws both sides of West 317th Street as flat elevations,
north side upright, south side upside down, the roadway between them seen from above, and runs
the night from midnight to 8 a.m. on the same schedule the Blender renders use.
"""
import json, os, re, sys, base64, io
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import block as K
data = K.export()

from PIL import Image
FLOWERS = {}
for n in (1, 2, 3):
    im = Image.open(os.path.join(os.path.dirname(HERE), '_style', 'eye-flower-%d_384.png' % n)).convert('RGBA'); buf = io.BytesIO(); im.save(buf, 'WEBP', quality=86, method=6)
    FLOWERS[n] = 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()

notes = []
nb = open(os.path.join(HERE, 'NOTEBOOK.md')).read()
parts = re.split(r'^## ', nb, flags=re.M)[1:]
for p in parts:
    head, _, body = p.partition('\n')
    m = re.match(r'(\d\d:\d\d)\s+(?:\((\d\d:\d\d) on the block\)\s+)?(.*)', head.strip())
    if not m: continue
    real, blk, title = m.groups()
    if blk is None:
        h, mi = (int(v) for v in real.split(':')); el = max(0, (h * 60 + mi) - (12 * 60 + 5)); blk = '%02d:%02d' % (el // 60, el % 60)
    notes.append(dict(real=real, block=blk, title=title.strip(), body=body.strip(), mind='CHANGED MY MIND' in title.upper()))

HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Unsupervised Shift</title>
<style>
:root{--ink:#0D0D0D;--cloud:#F0F4F8;--blue:#2962FF;--cyan:#00E5FF;--pink:#FF2E63;--acid:#D7FF1F}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--ink);color:var(--cloud);font:13px/1.45 ui-monospace,Menlo,Consolas,monospace;overflow:hidden}
#c{position:fixed;inset:0;width:100%;height:100%;display:block;touch-action:none;cursor:crosshair}
#hud{position:fixed;left:16px;top:12px;pointer-events:none;text-shadow:0 1px 6px #000}
#clock{font-size:44px;font-weight:700;letter-spacing:1px;line-height:1}#sub{opacity:.75;margin-top:4px;max-width:60vw}
#log{position:fixed;left:16px;bottom:74px;max-width:min(680px,calc(100vw - 32px));pointer-events:none;background:rgba(13,13,13,.62);padding:6px 9px;border-radius:3px}
#log:empty{display:none}#log div{opacity:.35;transition:opacity .6s}#log div:last-child{opacity:1}#log .mind{color:var(--pink)}#log b{color:var(--acid);font-weight:400}
#bar{position:fixed;left:16px;bottom:14px;width:calc(100vw - 32px);height:50px;touch-action:none;cursor:ew-resize}
#ctl{position:fixed;right:16px;top:12px;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:50vw}
button{font:inherit;color:var(--cloud);background:rgba(13,13,13,.6);border:1px solid rgba(240,244,248,.35);padding:5px 9px;border-radius:3px;cursor:pointer}
button:hover,button.on{border-color:var(--acid);color:var(--acid)}
#tip{position:fixed;display:none;max-width:320px;background:rgba(13,13,13,.92);border:1px solid var(--cyan);padding:8px 10px;border-radius:3px;pointer-events:none;z-index:5}
#tip b{color:var(--cyan);font-weight:400}
#book{position:fixed;inset:0;display:none;background:rgba(13,13,13,.94);overflow:auto;padding:28px 18px 80px;z-index:10}
#book .in{max-width:760px;margin:0 auto}#book h1{font-size:20px;margin:0 0 4px}#book h2{font-size:14px;margin:26px 0 6px;color:var(--cyan);font-weight:400}
#book h2.mind{color:var(--pink)}#book p,#book li{color:#cfd6dd}#book .x{position:fixed;right:18px;top:14px}#book pre{white-space:pre-wrap;font:inherit;color:#cfd6dd;margin:0}
.clean #hud,.clean #log,.clean #bar,.clean #ctl{display:none}.film #ctl{display:none}
@media (max-width:640px){#clock{font-size:32px}#ctl{max-width:44vw}#sub{max-width:52vw;font-size:11px}}
</style></head><body>
<canvas id="c"></canvas>
<div id="hud"><div id="clock">00:00</div><div id="sub"></div></div>
<div id="ctl"><button id="play">pause</button><button data-s="1">1x</button><button data-s="4" class="on">4x</button><button data-s="16">16x</button><button data-s="60">60x</button><button id="nb">notebook</button></div>
<div id="log"></div><canvas id="bar"></canvas><div id="tip"></div>
<div id="book"><button class="x" id="bx">close</button><div class="in" id="bin"></div></div>
<script>
"use strict";
const D = /*DATA*/;
const NOTES = /*NOTES*/;
const FLOWERS = /*FLOWERS*/;
const q = new URLSearchParams(location.search);
if (q.has('clean')) document.body.classList.add('clean');
if (q.has('film')) document.body.classList.add('film');
const T = s => { const [h, m, sec] = s.split(':').map(Number); return h * 60 + m + (sec || 0) / 60; };
const hm = t => { t = Math.max(0, Math.round(t)); return String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0'); };
let t = q.has('t') ? T(q.get('t')) : 0, speed = q.has('speed') ? +q.get('speed') : 4, playing = !q.has('t') || q.has('speed'), hold = 0;
const END = 480, FAC = D.road + D.walk;

// ---------- the schedule, the same rules as block.py
const B = {}; D.buildings.forEach(b => B[b.id] = b);
function shopLevel(k, t) { for (const [a, b, lv] of D.shops[k].lights) if ((a <= t && t < b) || (t >= END && b >= END)) return lv; return 0; }
function gateDown(k, t) { return D.shops[k].gate.some(([a, b]) => (a <= t && t < b) || (t >= END && b >= END)); }
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
const wetness = t => t < D.rain[0] ? 0 : t < D.rain[1] ? Math.min(1, (t - D.rain[0]) / 14) : Math.max(0.3, 1 - (t - D.rain[1]) / 420);
const lampsOn = t => t < D.lamps_off;
const signal = t => { const s = (t * 60) % 90; return s < 32 ? 'G' : s < 35 ? 'Y' : 'R'; };
const sunEl = t => { const i = Math.min(479, Math.floor(t)), f = t - i; return D.sun[i][0] * (1 - f) + D.sun[i + 1][0] * f; };
function skyAt(t) { const i = Math.min(479, Math.floor(t)), f = t - i, a = D.sky[i], b = D.sky[i + 1]; return [0, 1].map(k => a[k].map((v, j) => v * (1 - f) + b[k][j] * f)); }
const smooth = (a, b, x) => { x = Math.min(1, Math.max(0, (x - a) / (b - a))); return x * x * (3 - 2 * x); };
const amb = t => 0.055 + 0.945 * smooth(-8, 7, sunEl(t));            // how much daylight is on the walls
const css = (c, k = 1) => 'rgb(' + c.map(v => Math.round(255 * Math.pow(Math.min(1, Math.max(0, v * k)), 1 / 2.2))).join(',') + ')';
const mix = (a, b, f) => a.map((v, i) => v + (b[i] - v) * f);
const LIT = []; for (let m = 0; m <= END; m++) LIT.push(D.windows.reduce((n, w) => n + (winLight(w, m) ? 1 : 0), 0));
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// ---------- layout
const cv = document.getElementById('c'), g = cv.getContext('2d'); let W, H, S, ox, baseN, baseS, pan = 0, dpr = 1;
const TOP = 30, MARG = 9;                     // metres of sky above each base line, metres of avenue at each end
function layout() {
  dpr = Math.min(2, window.devicePixelRatio || 1); W = innerWidth; H = innerHeight; cv.width = W * dpr; cv.height = H * dpr;
  const wide = D.L + 2 * MARG, tall = 2 * TOP + 2 * FAC;
  S = Math.min(W / wide, H / tall); if (W < H) S = H / tall;       // on a tall screen fill the height and let the street pan
  ox = (W - wide * S) / 2 + MARG * S; if (wide * S > W) ox = MARG * S - pan;
  baseN = H / 2 - FAC * S; baseS = H / 2 + FAC * S;
}
addEventListener('resize', layout); layout();
const X = x => ox + x * S, YP = y => H / 2 - y * S;                 // plan view: y = +9 is the north facade

// ---------- drawing
function facade(b, t, a) {
  // local frame: origin at the left end of the facade as you face it, u right, z up. Drawn with y = -z.
  const w = b.w, Hh = b.height, P = (u0, z0, u1, z1) => g.fillRect(u0 * S, -z1 * S, (u1 - u0) * S, (z1 - z0) * S);
  const wall = css(b.brick, a), trim = css(b.trim, a);
  if (b.kind === 'garden') {
    g.fillStyle = css([0.05, 0.04, 0.03], a * 2); P(0, 0, w, 0.12);
    g.strokeStyle = css([0.4, 0.42, 0.44], a); g.lineWidth = Math.max(0.5, S * 0.03); for (let k = 0; k <= 5; k++) { g.beginPath(); g.moveTo(k * w / 5 * S, 0); g.lineTo(k * w / 5 * S, -2.6 * S); g.stroke(); }
    g.beginPath(); g.moveTo(0, -2.5 * S); g.lineTo(w * S, -2.5 * S); g.stroke();
    g.globalAlpha = 0.25; for (let k = 0; k < w / 0.5; k++) { g.beginPath(); g.moveTo(k * 0.5 * S, 0); g.lineTo(k * 0.5 * S + 2.5 * S, -2.5 * S); g.moveTo(k * 0.5 * S, 0); g.lineTo(k * 0.5 * S - 2.5 * S, -2.5 * S); g.stroke(); } g.globalAlpha = 1;
    tree(w / 2, 11, 7, a, 0.12);
    if (lampsOn(t)) { g.fillStyle = '#ffd28a'; for (let k = 0; k < 15; k++) { const f = (k + 0.5) / 15; g.beginPath(); g.arc((0.3 + (w - 0.8) * f) * S, -(3.6 - 0.9 * Math.sin(Math.PI * f)) * S, Math.max(1, S * 0.07), 0, 7); g.fill(); } }
    g.fillStyle = css([0.03, 0.10, 0.05], a * 3); P(w / 2 - 1.6, 1.5, w / 2 + 1.6, 2.1); label('317TH STREET GARDEN', w / 2, 1.8, 0.24, '#D7FF1F'); return;
  }
  g.fillStyle = wall; P(0, 0, w, Hh);
  g.fillStyle = trim; P(0, Hh - 1.0, w, Hh - 0.25);                                  // cornice
  g.fillStyle = css(b.brick, a * 0.7); const r = rng(b.x0 * 7 + 3); const bu = 1.5 + r() * (w - 5); P(bu, Hh, bu + 2.4, Hh + 1.8);   // stair bulkhead
  if (b.floors >= 6 || b.id === 'N2' || b.id === 'S7') { const cu = bu > w / 2 ? w * 0.3 : w * 0.72; g.fillStyle = css([0.22, 0.13, 0.07], a); P(cu - 1.45, Hh + 2.2, cu + 1.45, Hh + 5.2);
    g.beginPath(); g.moveTo((cu - 1.55) * S, -(Hh + 5.2) * S); g.lineTo(cu * S, -(Hh + 6.1) * S); g.lineTo((cu + 1.55) * S, -(Hh + 5.2) * S); g.fill(); g.fillStyle = css([0.02, 0.02, 0.02], 1); P(cu - 1.15, Hh, cu - 1.05, Hh + 2.2); P(cu + 1.05, Hh, cu + 1.15, Hh + 2.2); }
  if (b.kind === 'garage') {
    const s = D.shops.garage, lv = shopLevel('garage', t), down = gateDown('garage', t);
    for (const [u0, u1] of [[0.4, 5.1], [5.5, 10.2]]) { g.fillStyle = down ? css([0.2, 0.205, 0.21], a * 1.4) : css(s.glow, 0.25 + 0.75 * lv); P(u0, 0.05, u1, 4.3); if (down) { g.fillStyle = 'rgba(0,0,0,.25)'; for (let k = 0; k < 26; k++) P(u0, 0.1 + k * 0.16, u1, 0.14 + k * 0.16); } }
    g.fillStyle = css(s.awning, Math.max(a, 0.35)); P(0.3, 4.45, w - 0.3, 5.45); label(s.name, w / 2, 5.0, 0.6, css(s.ink));
    g.fillStyle = lampsOn(t) ? '#e9edf0' : css([0.9, 0.9, 0.88], a); P(1, Hh + 2.2, w - 1, Hh + 6.2); ['ONE BLOCK.', 'EIGHT HOURS.', 'NO CHECK-INS.'].forEach((ln, i) => label(ln, w / 2, Hh + 5.35 - i * 1.15, 0.9, '#0D0D0D'));
    g.fillStyle = '#0D0D0D'; for (const u of [2, w / 2, w - 2]) P(u - 0.08, Hh, u + 0.08, Hh + 2.2); return;
  }
  // windows
  for (const wd of b._win) {
    const L = winLight(wd, t); const u0 = wd.u - wd.w / 2, u1 = wd.u + wd.w / 2;
    g.fillStyle = trim; P(u0 - 0.14, wd.z - 0.13, u1 + 0.14, wd.z); P(u0 - 0.1, wd.z + wd.h, u1 + 0.1, wd.z + wd.h + 0.24);
    if (L) { g.fillStyle = css(D.kind_rgb[L[0]], 0.35 + 0.75 * L[1]); P(u0, wd.z, u1, wd.z + wd.h); g.fillStyle = 'rgba(0,0,0,.18)'; P(u0, wd.z, u1, wd.z + wd.h * 0.3);
      const who = D.residents[wd.unit].who; if (SILH[who] === wd.room) { g.fillStyle = 'rgba(4,4,6,.92)'; const n = (who === 'The Old Couple' || who === 'The New Parents') ? 2 : 1;
        for (let q = 0; q < n; q++) { const ux = wd.u + (q - (n - 1) / 2) * 0.42 + ((wd.i * 7) % 5 - 2) * 0.05, hh = 0.7 - q * 0.08; P(ux - 0.19, wd.z + 0.06, ux + 0.19, wd.z + hh); g.beginPath(); g.arc(ux * S, -(wd.z + hh + 0.13) * S, 0.12 * S, 0, 7); g.fill(); } } }
    else { g.fillStyle = css(mix([0.012, 0.014, 0.018], SKYZ, 0.22), 1); P(u0, wd.z, u1, wd.z + wd.h); }
    g.fillStyle = L ? 'rgba(0,0,0,.45)' : css(b.trim, a * 0.6); P(u0, wd.z + wd.h / 2 - 0.03, u1, wd.z + wd.h / 2 + 0.03);
  }
  if (b.escape) { g.strokeStyle = '#050506'; g.lineWidth = Math.max(0.6, S * 0.05); const n = b.bays, pt = w / n, k0 = Math.max(0, Math.floor(n / 2) - 1), u0 = k0 * pt + 0.25, u1 = (k0 + 2) * pt - 0.25;
    for (let fl = 2; fl <= b.floors; fl++) { const z = D.ground_h + (fl - 2) * D.floor_h + 0.55; g.strokeRect(u0 * S, -(z + 0.95) * S, (u1 - u0) * S, 0.95 * S); g.beginPath(); g.moveTo(u0 * S, -(z + 0.5) * S); g.lineTo(u1 * S, -(z + 0.5) * S);
      if (fl < b.floors) { const a0 = fl % 2 ? u0 + 0.5 : u1 - 0.5, a1 = fl % 2 ? u1 - 0.5 : u0 + 0.5; g.moveTo(a0 * S, -z * S); g.lineTo(a1 * S, -(z + D.floor_h) * S); } g.stroke(); }
    g.beginPath(); g.moveTo((u1 - 0.55) * S, -(D.ground_h + 0.55) * S); g.lineTo((u1 - 0.55) * S, -(D.ground_h - 1.0) * S); g.stroke(); }
  if (b.kind === 'brownstone') {
    const pt = w / 3; g.fillStyle = css([0.07, 0.035, 0.025], a * 2); P(pt * 0.5 - 0.6, 1.6, pt * 0.5 + 0.6, 4.1); g.fillStyle = '#ffb066'; P(pt * 0.5 - 0.4, 3.8, pt * 0.5 + 0.4, 4.05);
    g.fillStyle = trim; for (let k = 0; k < 8; k++) P(pt * 0.5 - 0.8 - k * 0.0, 0, pt * 0.5 + 0.8, 1.6 - k * 0.18 > 0 ? 0.2 : 0); g.beginPath(); g.moveTo((pt * 0.5 - 0.9) * S, 0); g.lineTo((pt * 0.5 - 0.9) * S, -1.6 * S); g.lineTo((pt * 0.5 + 0.9) * S, -1.6 * S); g.lineTo((pt * 0.5 + 0.9) * S, 0); g.fill();
    g.fillStyle = 'rgba(0,0,0,.3)'; for (let k = 1; k < 8; k++) P(pt * 0.5 - 0.9, k * 0.2 - 0.02, pt * 0.5 + 0.9, k * 0.2); return;
  }
  if (b.kind === 'prewar') {
    g.fillStyle = trim; P(0, 0, w, D.ground_h + 0.1); g.fillStyle = '#ffc583'; P(w / 2 - 1.1, 0.2, w / 2 + 1.1, 3.0); g.fillStyle = 'rgba(0,0,0,.6)'; P(w / 2 - 0.03, 0.2, w / 2 + 0.03, 3.0);
    g.fillStyle = css(mix([0.012, 0.014, 0.018], SKYZ, 0.2)); for (let k = 0; k < b.bays; k++) { const u = (k + 0.5) * w / b.bays; if (Math.abs(u - w / 2) > 1.8) P(u - 0.65, 1.3, u + 0.65, 3.0); }
    g.fillStyle = css(b.side === 'N' ? [0.02, 0.05, 0.035] : [0.10, 0.02, 0.03], Math.max(a, 0.5) * 2.5); P(w / 2 - 1.3, 2.9, w / 2 + 1.3, 3.25);
    if (b.shed) { g.fillStyle = css([0.02, 0.07, 0.05], Math.max(a, 0.4) * 2.5); P(0.2, 2.75, w - 0.2, 4.1); g.fillStyle = css([0.32, 0.33, 0.34], a); for (let u = 0.3; u < w; u += 2.4) P(u, 0, u + 0.07, 2.75);
      g.fillStyle = '#ffd9a0'; for (let u = 1.5; u < w; u += 4.8) { g.beginPath(); g.arc(u * S, -2.6 * S, Math.max(1, S * 0.1), 0, 7); g.fill(); } label('POST NO BILLS', w * 0.25, 3.45, 0.22, 'rgba(240,244,248,.6)'); }
    return;
  }
  // tenement ground floor: the shop
  const k = b.shop, s = D.shops[k], lv = shopLevel(k, t), down = gateDown(k, t), u0 = 0.5, u1 = w - 2.4;
  g.fillStyle = css(b.trim, a); P(0, 3.05, w, D.ground_h);
  g.fillStyle = css(mix([0.02, 0.02, 0.025], s.glow, 0.1 + 0.9 * lv), 0.12 + 0.88 * lv); P(u0, 0.62, u1, 3.05);
  if (lv > 0.3 && !down) shopInside(k, u0, u1, lv);
  if (down) { g.fillStyle = css([0.2, 0.205, 0.21], a * 1.5); P(u0 - 0.05, 0.17, u1 + 0.05, 3.05); g.fillStyle = 'rgba(0,0,0,.28)'; for (let i = 0; i < 18; i++) P(u0 - 0.05, 0.2 + i * 0.16, u1 + 0.05, 0.24 + i * 0.16);
    const mc = mural(k, u1 - u0 + 0.1); if (mc) g.drawImage(mc, (u0 - 0.05) * S, -3.05 * S, (u1 - u0 + 0.1) * S, 2.88 * S); }
  const on = lv >= 0.5 || ['grocery', 'locksmith', 'pharmacy', 'diner', 'laundromat'].includes(k);
  const dark = ['pizza', 'diner', 'bar'].includes(k);
  g.fillStyle = dark ? '#060607' : css(s.awning, on ? 1 : Math.max(a, 0.3)); P(u0 - 0.1, 3.1, u1 + 0.1, 3.92);
  label(s.name, (u0 + u1) / 2, 3.5, Math.min(0.6, (u1 - u0) / (s.name.length * 0.42)), dark ? css(s.neon, on ? 1 : 0.25) : css(s.ink));
  if (dark && on) { g.fillStyle = css(s.neon); P(u0 - 0.1, 3.06, u1 + 0.1, 3.1); }
  g.fillStyle = css([0.07, 0.035, 0.025], a * 2); P(w - 1.95, 0.17, w - 0.6, 2.45); g.fillStyle = '#ffb872'; P(w - 1.8, 2.5, w - 0.75, 2.95);
}
// ---------- gate murals: his Open Eye Flowers in a field of his contour lines, drawn once per gate
const MURC = {}, FIMG = {};
for (const n of [1, 2, 3]) { const im = new Image(); im.onload = () => { for (const k in MURC) if (D.murals[k][0] === n) delete MURC[k]; }; im.src = FLOWERS[n]; FIMG[n] = im; }
function vnoise(x, y) { const h = (i, j) => { let s = Math.sin(i * 127.1 + j * 311.7) * 43758.5453; return s - Math.floor(s); }; const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
  return (h(i, j) * (1 - sx) + h(i + 1, j) * sx) * (1 - sy) + (h(i, j + 1) * (1 - sx) + h(i + 1, j + 1) * sx) * sy; }
const fbm = (x, y) => 0.5 * vnoise(x, y) + 0.3 * vnoise(x * 2.03, y * 2.03) + 0.2 * vnoise(x * 4.1, y * 4.1);
function mural(k, wm) {
  if (!D.murals[k]) return null; if (MURC[k]) return MURC[k]; const [n, at, size] = D.murals[k], hm_ = 2.88, PX = 48, cw = Math.round(wm * PX), ch = Math.round(hm_ * PX);
  const c = document.createElement('canvas'); c.width = cw; c.height = ch; const x = c.getContext('2d'), id = x.createImageData(cw, ch), cx = wm * at, cz = hm_ * 0.52;
  const pal = [[41, 98, 255], [0, 229, 255], [41, 98, 255], [111, 35, 168], [255, 46, 99]], cut = [0, 0.38, 0.62, 0.80, 0.92];
  for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) {
    const u = i / PX, z = (ch - j) / PX, d = Math.hypot(u - cx, z - cz), f = fbm(u * 0.32 + n * 3.1, z * 0.32 + n * 2.2) * 3 + Math.exp(-d / 1.6) * 4;
    const a1 = Math.abs((f * 9) % 1 - 0.5), a5 = Math.abs((f * 1.8) % 1 - 0.5), on = Math.max(Math.min(1, Math.max(0, (a1 - 0.44) / 0.06)), Math.min(1, Math.max(0, (a5 - 0.465) / 0.035)));
    const b = (f * 0.23) % 1; let p = 0; for (let q = 0; q < cut.length; q++) if (b >= cut[q]) p = q; const col = pal[p], o = (j * cw + i) * 4;
    id.data[o] = 2 + (col[0] - 2) * on; id.data[o + 1] = 8 + (col[1] - 8) * on; id.data[o + 2] = 40 + (col[2] - 40) * on; id.data[o + 3] = 255;
  }
  x.putImageData(id, 0, 0); const im = FIMG[n];
  if (im && im.complete && im.naturalWidth) { const s = (hm_ - 0.1) * size * PX; x.drawImage(im, cx * PX - s / 2, (hm_ - cz) * PX - s / 2, s, s); MURC[k] = c; }
  return c;
}
function shopInside(k, u0, u1, lv) {
  const P = (a, z0, b, z1) => g.fillRect(a * S, -z1 * S, (b - a) * S, (z1 - z0) * S), r = rng(k.length * 97 + 5), cols = ['#e53935', '#ffc107', '#2962FF', '#2e9c4f', '#ff7a1a', '#e8e6df', '#8a2be2', '#00a3b4', '#FF2E63'];
  if (k === 'grocery' || k === 'pharmacy') for (let lvl = 0; lvl < 5; lvl++) for (let u = u0 + 0.2; u < u1 - 0.3; u += 0.12 + r() * 0.2) { g.fillStyle = cols[Math.floor(r() * cols.length)]; P(u, 0.75 + lvl * 0.45, u + 0.1 + r() * 0.12, 0.95 + lvl * 0.45 + r() * 0.15); }
  if (k === 'laundromat') { for (let u = u0 + 0.3; u < u1 - 0.9; u += 0.85) for (let z = 0; z < 2; z++) { g.fillStyle = '#9aa0a6'; P(u, 0.7 + z * 1.05, u + 0.8, 1.7 + z * 1.05); g.fillStyle = '#111'; g.beginPath(); g.arc((u + 0.4) * S, -(1.2 + z * 1.05) * S, 0.27 * S, 0, 7); g.fill(); } }
  if (k === 'pizza' || k === 'bakery') { g.fillStyle = '#b9bbb9'; P(u0 + 0.5, 0.62, u1 - 0.9, 1.05); g.fillStyle = '#ff7a1a'; P(u0 + 0.9, 1.3, u0 + 2.7, 1.5); g.fillStyle = '#c98a45'; for (let u = u0 + 0.9; u < u1 - 1.2; u += 0.55) { g.beginPath(); g.ellipse(u * S, -1.12 * S, 0.22 * S, 0.07 * S, 0, 0, 7); g.fill(); } }
  if (k === 'diner') { g.fillStyle = '#FF2E63'; for (let u = u0 + 0.5; u < u1 - 1.8; u += 1.9) { P(u, 0.62, u + 0.12, 1.25); P(u + 1.63, 0.62, u + 1.75, 1.25); g.fillStyle = '#F0F4F8'; P(u + 0.55, 0.9, u + 1.2, 0.95); g.fillStyle = '#FF2E63'; } }
  if (k === 'bar') { g.fillStyle = '#2a0c06'; P(u0 + 0.9, 0.62, u0 + 1.6, 1.15); g.fillStyle = '#0a6b3a'; P(u1 - 3.2, 0.7, u1 - 2.0, 0.85); g.fillStyle = '#FF2E63'; P(u0 + 0.4, 2.5, u0 + 3.2, 2.56); }
  if (k === 'flowers') { for (let u = u0 + 0.4; u < u1 - 0.4; u += 0.42) { g.fillStyle = '#145a22'; P(u - 0.12, 0.8, u + 0.12, 1.5); g.fillStyle = ['#FF2E63', '#ffc107', '#F0F4F8', '#2962FF', '#ff7a1a', '#D7FF1F'][Math.floor(r() * 6)]; g.beginPath(); g.arc(u * S, -1.6 * S, 0.16 * S, 0, 7); g.fill(); } }
}
function label(s, u, z, size, col) { if (size * S < 3.2) return; g.fillStyle = col; g.font = '700 ' + (size * S) + 'px "DIN Condensed","Arial Narrow",Impact,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s, u * S, -z * S); }
function tree(u, h, seed, a, base) {
  const r = rng(seed * 131 + 7); g.strokeStyle = css([0.045, 0.038, 0.032], Math.max(a, 0.25) * 3); g.lineCap = 'round';
  (function grow(x, z, ang, len, wd, d) { const x2 = x + Math.sin(ang) * len, z2 = z + Math.cos(ang) * len; g.lineWidth = Math.max(0.5, wd * S); g.beginPath(); g.moveTo(x * S, -z * S); g.lineTo(x2 * S, -z2 * S); g.stroke();
    if (d >= 5) return; const n = d === 0 ? 3 : 2; for (let i = 0; i < n; i++) grow(x2, z2, ang * 0.6 + (r() - 0.5) * 1.5, len * (0.62 + r() * 0.18), wd * 0.62, d + 1); })(u, base || 0.16, (r() - 0.5) * 0.08, h * 0.34, h * 0.038, 0);
}
function carSide(c, u, kind) { // a parked or moving car seen from the side, at the kerb
  const d = { sedan: [4.6, 1.42], suv: [4.8, 1.75], van: [5.3, 2.15], hatch: [4.0, 1.5], cab: [4.7, 1.5], car: [4.6, 1.42] }[kind] || [4.6, 1.42];
  g.fillStyle = c; g.fillRect((u - d[0] / 2) * S, -0.95 * S, d[0] * S, 0.67 * S); g.fillRect((u - d[0] / 2 + d[0] * 0.25) * S, -d[1] * S, d[0] * 0.55 * S, (d[1] - 0.9) * S);
  g.fillStyle = '#050505'; for (const wx of [-d[0] / 2 + 0.85, d[0] / 2 - 0.85]) { g.beginPath(); g.arc((u + wx) * S, -0.33 * S, 0.33 * S, 0, 7); g.fill(); }
}
function person(col, umbrella, dogs, dir) {  // origin at the feet, 1.7 m tall
  g.fillStyle = '#0a0a0c'; g.fillRect(-0.1 * S, -0.85 * S, 0.2 * S, 0.85 * S); g.fillStyle = col; g.fillRect(-0.2 * S, -1.45 * S, 0.4 * S, 0.8 * S);
  g.fillStyle = '#8a6a55'; g.beginPath(); g.arc(0, -1.58 * S, 0.11 * S, 0, 7); g.fill();
  if (umbrella) { g.fillStyle = '#050505'; g.beginPath(); g.arc(0.1 * S, -1.95 * S, 0.6 * S, Math.PI, 0); g.fill(); }
  for (let k = 0; k < (dogs || 0); k++) { g.fillStyle = ['#8a643a', '#111', '#d9d5c8'][k % 3]; g.fillRect((dir * (0.8 + k * 0.55) - 0.25) * S, -0.5 * S, 0.5 * S, 0.25 * S); }
}
let SKYZ = [0, 0, 0];
const SILH = {'The Insomniac': 'kitchen', 'The Writer': 'living', 'The Student': 'bedroom', 'The Old Couple': 'kitchen', 'The Bartender': 'living', 'The New Parents': 'bedroom', 'The Early Riser': 'kitchen', 'The Saxophonist': 'living', 'The Night Shift': 'kitchen', 'The Nurse': 'kitchen', 'The Baker': 'kitchen', 'The Cab Driver': 'kitchen'};
const rainR = rng(317), DROPS = Array.from({ length: 260 }, () => [rainR(), rainR(), 0.6 + rainR() * 0.8]);

function draw() {
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  const [hz, zn] = skyAt(t), a = amb(t), el = sunEl(t), wet = wetness(t); SKYZ = zn;
  const k = el < -8 ? 2.6 : 2.6 - 2.05 * smooth(-8, 6, el);         // exposure, like the Blender camera
  // sky: zenith at the top and bottom edges, horizon where the buildings stand
  for (const [y0, y1] of [[0, baseN], [H, baseS]]) { const gr = g.createLinearGradient(0, y0, 0, y1); gr.addColorStop(0, css(zn, k)); gr.addColorStop(1, css(hz, k)); g.fillStyle = gr; g.fillRect(0, Math.min(y0, y1), W, Math.abs(y1 - y0)); }
  // the street from above
  g.fillStyle = css(mix([0.03, 0.03, 0.034], zn, 0.25 * wet), a * 6 * (1 + wet * 0.6)); g.fillRect(0, baseN, W, baseS - baseN);
  g.fillStyle = css([0.30, 0.295, 0.28], a * 1.6); g.fillRect(X(0), baseN, D.L * S, D.walk * S); g.fillRect(X(0), baseS - D.walk * S, D.L * S, D.walk * S);
  g.fillStyle = css([0.75, 0.75, 0.72], a * 1.5); for (const xc of [-2.4, D.L + 2.4]) for (let i = 0; i < 8; i++) g.fillRect(X(xc - 1.5), YP(-3.8 + i * 1.2) , 3 * S, 0.6 * S);
  // street lamp pools
  if (lampsOn(t)) for (const lp of D.lamps) { const sg = lp.side === 'N' ? 1 : -1, cx = X(lp.x), cy = YP(sg * (D.road - 1.85)), gr = g.createRadialGradient(cx, cy, 0, cx, cy, 13 * S); gr.addColorStop(0, 'rgba(255,205,150,.34)'); gr.addColorStop(1, 'rgba(255,205,150,0)'); g.fillStyle = gr; g.fillRect(cx - 13 * S, baseN, 26 * S, baseS - baseN); }
  // shop light spilling on the sidewalk
  for (const b of D.buildings) if (b.shop && b.kind === 'tenement') { const lv = shopLevel(b.shop, t); if (lv < 0.05 || gateDown(b.shop, t)) continue; const sg = b.side === 'N' ? 1 : -1, x0 = b.side === 'N' ? b.x0 + 0.5 : b.x0 + 2.4, wd = b.w - 2.9;
    const y0 = YP(sg * FAC), y1 = YP(sg * (FAC - 5)), gr = g.createLinearGradient(0, y0, 0, y1); const c = D.shops[b.shop].glow.map(v => Math.round(v * 255)); gr.addColorStop(0, `rgba(${c},${0.5 * lv})`); gr.addColorStop(1, `rgba(${c},0)`); g.fillStyle = gr; g.fillRect(X(x0), Math.min(y0, y1), wd * S, Math.abs(y1 - y0)); }
  // wet street: every lit shop and lamp drags a streak of its colour across the asphalt
  if (wet > 0.15) for (const b of D.buildings) { if (!b.shop || b.kind !== 'tenement') continue; const lv = shopLevel(b.shop, t); if (lv < 0.3) continue;
    const sg = b.side === 'N' ? 1 : -1, x0 = b.side === 'N' ? b.x0 + 0.5 : b.x0 + 2.4, c = (gateDown(b.shop, t) ? [0.5, 0.6, 0.9] : D.shops[b.shop].neon).map(v => Math.round(v * 255));
    const y0 = YP(sg * D.road), y1 = YP(-sg * D.road * 0.6), gr = g.createLinearGradient(0, y0, 0, y1); gr.addColorStop(0, `rgba(${c},${0.09 * wet * lv})`); gr.addColorStop(1, `rgba(${c},0)`);
    g.fillStyle = gr; for (let k = 0; k < 7; k++) { const xs = x0 + (b.w - 2.9) * (k + 0.5) / 7; for (const wd of [0.9, 0.5, 0.2]) g.fillRect(X(xs) - wd / 2 * S, Math.min(y0, y1), wd * S, Math.abs(y1 - y0)); } }   // three widths stacked instead of a blur filter, which stalled headless Chrome
  // trash, hydrants, tree pits, parked cars (plan)
  for (const p of D.piles) if (p.appear <= t && t < p.gone) { const sg = p.side === 'N' ? 1 : -1, r = rng(p.x * 13); g.fillStyle = '#050506'; for (let i = 0; i < p.n; i++) { g.beginPath(); g.arc(X(p.x + (r() - 0.5) * 2.6), YP(sg * (D.road + 0.75 + (r() - 0.5) * 0.5)), 0.36 * S, 0, 7); g.fill(); } }
  for (const tr of D.trees) { const sg = tr.side === 'N' ? 1 : -1; g.fillStyle = css([0.05, 0.04, 0.03], a * 4); g.fillRect(X(tr.x - 0.75), YP(sg * (D.road + 0.95)) - 0.6 * S, 1.5 * S, 1.2 * S); }
  for (const c of D.cars) { if ((c.arrive != null && t < c.arrive) || (c.leave != null && t >= c.leave)) continue; const sg = c.side === 'N' ? 1 : -1, ln = { sedan: 4.6, suv: 4.8, van: 5.3, hatch: 4.0 }[c.kind];
    g.fillStyle = css(c.col, a * 2.2 + 0.05); rr(X(c.x - ln / 2), YP(sg * (D.road - 1.05)) - 0.9 * S, ln * S, 1.8 * S, 0.35 * S); g.fillStyle = 'rgba(0,0,0,.55)'; g.fillRect(X(c.x - ln * 0.22), YP(sg * (D.road - 1.05)) - 0.75 * S, ln * 0.45 * S, 1.5 * S); }
  // signals at the west corner
  const ph = signal(t); g.fillStyle = { G: '#00ff73', Y: '#ffb000', R: '#ff2a1a' }[ph]; g.beginPath(); g.arc(X(-0.9), YP(-D.road - 0.7 + 4.2), Math.max(1.5, 0.22 * S), 0, 7); g.fill();
  // subway stair
  g.fillStyle = '#050505'; g.fillRect(X(90.6), YP(-6.4), 3.8 * S, 1.6 * S); g.fillStyle = '#19ff66'; for (const yy of [-6.33, -8.07]) { g.beginPath(); g.arc(X(90.9), YP(yy), Math.max(1.5, 0.2 * S), 0, 7); g.fill(); }
  // facades
  for (const b of D.buildings) { g.save(); if (b.side === 'N') g.translate(X(b.x0), baseN); else { g.translate(X(b.x0 + b.w), baseS); g.rotate(Math.PI); } facade(b, t, a * 3.2 * (k / 2.6) + 0.0); g.restore(); }
  // kerbside things in elevation: trees, lamps, parked cars, people
  for (const side of ['N', 'S']) {
    g.save(); if (side === 'N') g.translate(X(0), baseN); else { g.translate(X(D.L), baseS); g.rotate(Math.PI); }
    const U = x => side === 'N' ? x : D.L - x;
    for (const tr of D.trees) if (tr.side === side) tree(U(tr.x), tr.h, Math.round(tr.x * 10), a);
    for (const lp of D.lamps) if (lp.side === side) { g.fillStyle = css([0.32, 0.33, 0.34], a * 2); g.fillRect((U(lp.x) - 0.08) * S, -8.3 * S, 0.16 * S, 8.3 * S); g.fillRect((U(lp.x) - 0.5) * S, -8.66 * S, 1.0 * S, 0.14 * S); if (lampsOn(t)) { g.fillStyle = '#ffd9a8'; g.fillRect((U(lp.x) - 0.4) * S, -8.52 * S, 0.8 * S, Math.max(1.5, 0.1 * S)); } }
    for (const c of D.cars) if (c.side === side && !((c.arrive != null && t < c.arrive) || (c.leave != null && t >= c.leave))) carSide(css(c.col, a * 2.2 + 0.05), U(c.x), c.kind);
    g.restore();
  }
  // everyone who moves
  for (const m of D.movers) {
    if (m.kind === 'note') continue; const p = moverAt(m, t); if (!p) continue; const [x, y, hx, hy] = p, px = X(x), py = YP(y);
    if (m.kind === 'person') {
      g.fillStyle = css(m.col, 1.0); g.beginPath(); g.arc(px, py, Math.max(1.6, 0.3 * S), 0, 7); g.fill(); if (m.umbrella) { g.fillStyle = '#000'; g.beginPath(); g.arc(px, py, 0.6 * S, 0, 7); g.fill(); }
      if (m.dogs) for (let i = 0; i < m.dogs; i++) { g.fillStyle = ['#8a643a', '#222', '#d9d5c8'][i]; g.fillRect(px + (hx * (0.8 + i * 0.5)) * S - 1, py - (hy * (0.8 + i * 0.5) + (i - 1) * 0.3) * S - 1, Math.max(2, 0.4 * S), Math.max(2, 0.2 * S)); }
      if (Math.abs(y) > D.road) { g.save(); const side = y > 0 ? 'N' : 'S'; if (side === 'N') g.translate(px, baseN); else { g.translate(px, baseS); g.rotate(Math.PI); } person(css(m.col, 1.0), m.umbrella, m.dogs, side === 'N' ? Math.sign(hx) : -Math.sign(hx)); g.restore(); }
    } else if (m.kind === 'cat' || m.kind === 'rat') { g.fillStyle = m.kind === 'cat' ? '#e0822a' : '#3a322c'; g.beginPath(); g.arc(px, py, Math.max(1.4, (m.kind === 'cat' ? 0.22 : 0.1) * S), 0, 7); g.fill(); }
    else {
      const dims = { car: [4.6, 1.8], cab: [4.7, 1.85], van: [5.6, 2.05], boxtruck: [7.5, 2.4], garbage: [9.6, 2.5], sweeper: [5.2, 2.2], bus: [10.5, 2.5] }[m.kind];
      const gr = g.createRadialGradient(px - dims[0] / 2 * S, py, 0, px - dims[0] / 2 * S, py, 16 * S); gr.addColorStop(0, 'rgba(255,240,210,.5)'); gr.addColorStop(1, 'rgba(255,240,210,0)'); g.fillStyle = gr;
      g.beginPath(); g.moveTo(px - dims[0] / 2 * S, py); g.lineTo(px - (dims[0] / 2 + 16) * S, py - 5 * S); g.lineTo(px - (dims[0] / 2 + 16) * S, py + 5 * S); g.fill();
      g.fillStyle = css(m.col, 0.25 + a * 2); rr(px - dims[0] / 2 * S, py - dims[1] / 2 * S, dims[0] * S, dims[1] * S, 0.3 * S);
      g.fillStyle = '#ff2a1a'; g.fillRect(px + dims[0] / 2 * S - 1, py - dims[1] / 2 * S, 2, dims[1] * S);
      if (m.kind === 'garbage' || m.kind === 'sweeper') { g.fillStyle = Math.floor(t * 40) % 2 ? '#ffb000' : '#553a00'; g.beginPath(); g.arc(px, py, Math.max(1.5, 0.25 * S), 0, 7); g.fill(); }
      if (m.kind === 'bus') { g.fillStyle = Math.floor(t * 60) % 2 ? '#ff2a1a' : '#400'; g.fillRect(px - dims[0] / 2 * S, py - dims[1] / 2 * S, 3, 3); g.fillRect(px - dims[0] / 2 * S, py + dims[1] / 2 * S - 3, 3, 3); }
    }
  }
  // rain
  if (raining(t)) { g.strokeStyle = 'rgba(200,215,235,.35)'; g.lineWidth = 1; g.beginPath(); const ph2 = (performance.now() / 420) % 1;
    for (const [rx, ry, ln] of DROPS) { const x = rx * W, y = ((ry + ph2 * ln) % 1) * H; g.moveTo(x, y); g.lineTo(x - 3, y + 14 * ln); } g.stroke(); }
  // sun, low in the east, once it is up: a glow from the right-hand end of the street
  if (el > -1) { const f = smooth(-1, 3, el) * (1 - smooth(6, 14, el) * 0.6), gr = g.createRadialGradient(W + 40, H / 2, 0, W + 40, H / 2, W * 0.75); gr.addColorStop(0, `rgba(255,190,110,${0.55 * f})`); gr.addColorStop(1, 'rgba(255,190,110,0)'); g.fillStyle = gr; g.fillRect(0, baseN, W, baseS - baseN); }
}
function rr(x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.fill(); }
for (const b of D.buildings) b._win = D.windows.filter(w => w.b === b.id);

// ---------- timeline
const bar = document.getElementById('bar'), bg = bar.getContext('2d');
function drawBar() {
  const r = bar.getBoundingClientRect(), w = r.width, h = r.height; if (bar.width !== Math.round(w * dpr)) { bar.width = Math.round(w * dpr); bar.height = Math.round(h * dpr); } bg.setTransform(dpr, 0, 0, dpr, 0, 0); bg.clearRect(0, 0, w, h);
  const xx = m => m / END * w; bg.fillStyle = 'rgba(13,13,13,.55)'; bg.fillRect(0, 0, w, h);
  bg.fillStyle = 'rgba(41,98,255,.35)'; bg.fillRect(xx(D.rain[0]), 0, xx(D.rain[1]) - xx(D.rain[0]), h);
  const mx = Math.max(...LIT); bg.beginPath(); bg.moveTo(0, h - 14); for (let m = 0; m <= END; m++) bg.lineTo(xx(m), h - 14 - LIT[m] / mx * (h - 20)); bg.lineTo(w, h - 14); bg.fillStyle = 'rgba(255,170,90,.55)'; bg.fill();
  bg.fillStyle = '#F0F4F8'; bg.font = '10px ui-monospace,Menlo,monospace'; bg.textBaseline = 'bottom';
  for (let hr = 0; hr <= 8; hr++) { bg.fillRect(xx(hr * 60) - (hr === 8 ? 1 : 0), h - 14, 1, 6); bg.textAlign = hr === 0 ? 'left' : hr === 8 ? 'right' : 'center'; bg.fillText(hr === 0 ? '12 a.m.' : hr + ' a.m.', xx(hr * 60), h); }
  bg.fillStyle = '#D7FF1F'; bg.fillRect(xx(D.sunrise), 0, 1, h - 14);
  bg.fillStyle = '#FF2E63'; for (const n of NOTES) if (n.mind) bg.fillRect(xx(T(n.block)) - 1, 0, 3, 9);
  bg.fillStyle = '#00E5FF'; bg.fillRect(xx(Math.min(t, END)) - 1, 0, 2, h - 8);
}
let drag = false; const seek = e => { const r = bar.getBoundingClientRect(); t = Math.max(0, Math.min(END, (e.clientX - r.left) / r.width * END)); hold = 0; lastLog = -1; refreshLog(true); };
bar.addEventListener('pointerdown', e => { drag = true; bar.setPointerCapture(e.pointerId); seek(e); }); bar.addEventListener('pointermove', e => drag && seek(e)); bar.addEventListener('pointerup', () => drag = false);

// ---------- log, clock, notes
const logEl = document.getElementById('log'), clockEl = document.getElementById('clock'), subEl = document.getElementById('sub'); let lastLog = -1;
const ALL = D.log.map(([m, s]) => ({ m, s })).concat(NOTES.filter(n => n.mind).map(n => ({ m: T(n.block), s: 'Note left at ' + n.real + ' by whoever is building this: ' + n.title, mind: true }))).sort((a, b) => a.m - b.m);
function refreshLog(force) {
  let i = -1; for (let k = 0; k < ALL.length; k++) if (ALL[k].m <= t) i = k; if (i === lastLog && !force) return; lastLog = i;
  logEl.innerHTML = ''; for (let k = Math.max(0, i - 3); k <= i; k++) { const d = document.createElement('div'); if (ALL[k].mind) d.className = 'mind'; d.innerHTML = '<b>' + hm(ALL[k].m) + '</b>  ' + ALL[k].s.replace(/</g, '&lt;'); logEl.appendChild(d); }
}
function refreshHud() {
  clockEl.textContent = hm(Math.min(t, END)); const el = sunEl(Math.min(t, END));
  subEl.textContent = 'West 317th Street · ' + D.date + ' · ' + LIT[Math.min(END, Math.round(t))] + ' windows lit' + (raining(t) ? ' · rain' : '') + (el > -0.83 ? ' · sun ' + el.toFixed(0) + '° up' : '');
}
const book = document.getElementById('book'), bin = document.getElementById('bin');
function md(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`(.+?)`/g, '<code>$1</code>'); }
bin.innerHTML = '<h1>The notebook</h1><p>Written during the eight hours, in order, not edited afterwards. The time in brackets is the time on the block when each note was written: the shift and the night are the same length and run together.</p>' +
  NOTES.map(n => '<h2 class="' + (n.mind ? 'mind' : '') + '">' + n.real + ' (' + n.block + ' on the block) ' + md(n.title) + '</h2><pre>' + md(n.body) + '</pre>').join('');
document.getElementById('nb').onclick = () => { book.style.display = 'block'; }; document.getElementById('bx').onclick = () => { book.style.display = 'none'; };
const playB = document.getElementById('play'); playB.onclick = () => { playing = !playing; if (t >= END) { t = 0; playing = true; } playB.textContent = playing ? 'pause' : 'play'; };
document.querySelectorAll('[data-s]').forEach(b => b.onclick = () => { speed = +b.dataset.s; document.querySelectorAll('[data-s]').forEach(o => o.classList.toggle('on', o === b)); });
document.querySelectorAll('[data-s]').forEach(o => o.classList.toggle('on', +o.dataset.s === speed));
addEventListener('keydown', e => { if (e.key === ' ') { e.preventDefault(); playB.onclick(); } if (e.key === 'ArrowRight') t = Math.min(END, t + 1); if (e.key === 'ArrowLeft') t = Math.max(0, t - 1); if (e.key === 'Escape') book.style.display = 'none'; });

// ---------- who lives there
const tip = document.getElementById('tip'); let panDrag = null;
function hit(mx, my) {
  for (const b of D.buildings) { let u, z; if (b.side === 'N') { u = (mx - X(b.x0)) / S; z = (baseN - my) / S; } else { u = (X(b.x0 + b.w) - mx) / S; z = (my - baseS) / S; }
    if (u < 0 || u > b.w || z < 0 || z > b.height + 7) continue;
    for (const w of b._win) if (Math.abs(u - w.u) < w.w / 2 + 0.15 && z > w.z - 0.1 && z < w.z + w.h + 0.1) { const r = D.residents[w.unit], L = winLight(w, t); return '<b>' + b.name + ', apt ' + w.unit.split('-')[1] + '</b><br>' + r.who + '. ' + r.line + '<br><i>' + w.room + (L ? ', light on' : ', dark') + '</i>'; }
    if (b.shop && z < D.ground_h) { const s = D.shops[b.shop]; return '<b>' + s.name + '</b><br>' + s.note + '<br><i>' + (gateDown(b.shop, t) ? 'gate down' : shopLevel(b.shop, t) > 0.3 ? 'open' : 'dark') + '</i>'; }
    return '<b>' + b.name + '</b>'; }
  let best = null, bd = 1.2; for (const m of D.movers) { if (m.kind === 'note') continue; const p = moverAt(m, t); if (!p) continue; const d = Math.hypot((mx - X(p[0])) / S, (my - YP(p[1])) / S) - (m.kind === 'person' || m.kind === 'cat' || m.kind === 'rat' ? 0 : 2.5); if (d < bd) { bd = d; best = m; } }
  return best ? '<b>' + best.who + '</b>' + (best.line ? '<br>' + best.who + ' ' + best.line : '') : null;
}
cv.addEventListener('pointermove', e => { if (panDrag != null) { pan = Math.max(0, Math.min((D.L + 2 * MARG) * S - W, pan - (e.clientX - panDrag))); panDrag = e.clientX; layout(); return; }
  const h = hit(e.clientX, e.clientY); if (!h) { tip.style.display = 'none'; return; } tip.innerHTML = h; tip.style.display = 'block'; tip.style.left = Math.min(W - 330, e.clientX + 14) + 'px'; tip.style.top = Math.min(H - 110, e.clientY + 14) + 'px'; });
cv.addEventListener('pointerdown', e => { if ((D.L + 2 * MARG) * S > W) panDrag = e.clientX; }); addEventListener('pointerup', () => panDrag = null); cv.addEventListener('pointerleave', () => tip.style.display = 'none');

// ---------- run
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (playing && !drag) { if (t < END) t = Math.min(END, t + dt * speed); else { hold += dt; if (hold > 6 && !q.has('once')) { t = 0; hold = 0; lastLog = -1; } } }
  if ((D.L + 2 * MARG) * S > W && panDrag == null && playing) { const span = (D.L + 2 * MARG) * S - W; pan = span * (0.5 - 0.5 * Math.cos(now / 9000)); layout(); }
  draw(); drawBar(); refreshLog(); refreshHud(); requestAnimationFrame(frame);
}
refreshLog(true);
if (q.has('film')) {
  // ?film: no clock of its own. The recorder calls window.__rec(seconds); 24 block minutes pass per second, then the last minute holds.
  playing = false; const PER = +(q.get('film') || 24);
  window.__rec = async s => { t = Math.min(END, s * PER); lastLog = -1; if ((D.L + 2 * MARG) * S > W) { pan = ((D.L + 2 * MARG) * S - W) * (0.5 - 0.5 * Math.cos(s * 0.35)); layout(); }
    draw(); drawBar(); refreshLog(true); refreshHud(); };
  const ready = () => [1, 2, 3].every(n => FIMG[n].complete && FIMG[n].naturalWidth);
  (function wait() { if (ready()) { for (const k in MURC) delete MURC[k]; window.__rec(0); window.__recReady = true; } else setTimeout(wait, 50); })();
} else requestAnimationFrame(frame);
</script></body></html>
'''
out = HTML.replace('/*DATA*/', json.dumps(data, separators=(',', ':'))).replace('/*NOTES*/', json.dumps(notes)).replace('/*FLOWERS*/', json.dumps(FLOWERS))
open(os.path.join(HERE, 'index.html'), 'w').write(out)
print('index.html', len(out) // 1024, 'KB,', len(notes), 'notebook entries,', sum(n['mind'] for n in notes), 'changed-my-mind notes')
