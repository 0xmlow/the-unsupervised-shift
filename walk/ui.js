// THE UNSUPERVISED SHIFT, the walk's interface (Nov 19). One module for both walks: the 3D walk (walk.js) and the
// photographed walk for browsers without WebGL (pano.js). MLow's identity: ink ground, Cloud type, Evil Eye Blue and
// Cyan accents, Shock Pink only for recording, Playfair Display for display, Roboto Mono for labels, the real logo.
// Also: film grain over everything, a screenshot, and a recording of the visit.
const A = (window.WALK_BASE || '') + 'assets/';
const $ = id => document.getElementById(id);
const pad = n => String(n).padStart(2, '0');

const CSS = `
:root{--ink:#0D0D0D;--card:#141820;--div:#2A3040;--cloud:#F0F4F8;--slate:#8899AA;--blue:#2962FF;--cyan:#00E5FF;--pink:#FF2E63;--lb:#7EB8FF;
  --glass:rgba(13,16,24,.52);--line:rgba(240,244,248,.14);--display:"Playfair Display",Georgia,serif;--mono:"Roboto Mono",Consolas,ui-monospace,monospace;--body:Arial,Helvetica,sans-serif}
html,body{background:#02040C;color:var(--cloud);font:14px/1.45 var(--body)}
.u-glass{background:var(--glass);-webkit-backdrop-filter:blur(14px) saturate(140%);backdrop-filter:blur(14px) saturate(140%);border:1px solid var(--line)}
#u-grain{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;mix-blend-mode:overlay;opacity:.2;z-index:5}
#u-vig{position:fixed;inset:0;pointer-events:none;z-index:5;background:radial-gradient(120% 90% at 50% 46%,transparent 52%,rgba(2,4,12,.55) 100%)}
#u-top{position:fixed;left:20px;top:16px;z-index:8;pointer-events:none;text-shadow:0 2px 18px rgba(0,0,0,.65)}
#u-eye{font:500 10.5px/1 var(--mono);letter-spacing:.22em;color:var(--cyan);display:flex;align-items:center;gap:8px}
#u-eye i{width:7px;height:7px;border-radius:50%;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}
#u-clock{display:flex;align-items:flex-start;gap:2px;margin-top:8px;font-family:var(--display);font-weight:800;font-size:76px;line-height:.86;letter-spacing:-.01em;font-variant-numeric:lining-nums tabular-nums;font-feature-settings:"lnum","tnum"}
#u-clock .c{color:var(--blue);margin:0 2px;font-weight:600;animation:upulse 2s ease-in-out infinite;text-shadow:0 0 22px rgba(41,98,255,.7)}
@keyframes upulse{50%{opacity:.55}}
@keyframes ublink{50%{opacity:.25}}
#u-clock .s{font:500 15px/1 var(--mono);color:var(--cyan);margin:9px 0 0 8px;letter-spacing:.06em;font-variant-numeric:tabular-nums}
#u-clock .ap{display:block;font:italic 600 22px/1 var(--display);color:var(--cloud);opacity:.82;margin-top:10px}
#u-clock .side{display:flex;flex-direction:column}
#u-sub{margin-top:12px;font:400 10.5px/1.4 var(--mono);letter-spacing:.16em;color:var(--slate);text-transform:uppercase}
#u-sub b{color:var(--cloud);font-weight:500}
#u-state{margin-top:6px;font:italic 400 15px/1.3 var(--display);color:var(--lb);max-width:360px}
#u-right{position:fixed;right:16px;top:16px;z-index:8;display:flex;flex-direction:column;align-items:flex-end;gap:10px}
.u-row{display:flex;gap:8px;align-items:center}
.u-btn{font:500 11px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--cloud);height:38px;padding:0 16px;border-radius:999px;cursor:pointer;
  display:inline-flex;align-items:center;gap:9px;text-decoration:none;transition:border-color .2s,background .2s,box-shadow .2s,transform .15s;user-select:none;-webkit-user-select:none}
.u-btn:hover{border-color:rgba(41,98,255,.9);box-shadow:0 0 0 3px rgba(41,98,255,.18),0 8px 28px rgba(41,98,255,.25)}
.u-btn:active{transform:scale(.96)}
.u-btn.on{background:var(--blue);border-color:var(--blue);color:#fff;box-shadow:0 6px 24px rgba(41,98,255,.45)}
.u-ic{width:38px;padding:0;justify-content:center}
.u-ic svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.u-btn.rec{color:#fff;background:var(--pink);border-color:var(--pink);box-shadow:0 0 0 4px rgba(255,46,99,.25);animation:urec 1.4s ease-in-out infinite}
@keyframes urec{50%{box-shadow:0 0 0 9px rgba(255,46,99,0)}}
.u-seg{display:flex;padding:3px;border-radius:999px;gap:2px}
.u-seg button{font:500 10.5px/1 var(--mono);letter-spacing:.1em;color:var(--slate);background:none;border:0;height:30px;padding:0 12px;border-radius:999px;cursor:pointer;transition:color .2s,background .2s}
.u-seg button:hover{color:var(--cloud)}.u-seg button.on{background:rgba(240,244,248,.95);color:var(--ink)}
#u-ticker{position:fixed;left:20px;bottom:96px;z-index:8;width:min(520px,calc(100vw - 40px));pointer-events:none;display:flex;flex-direction:column;gap:8px}
.u-line{border-radius:14px;padding:12px 16px 13px 16px;border-left:2px solid var(--blue);animation:uin .55s cubic-bezier(.2,.8,.2,1)}
.u-line.old{opacity:.42;transform:scale(.985);transform-origin:left bottom;padding:8px 14px}
.u-line .t{font:500 10px/1 var(--mono);letter-spacing:.18em;color:var(--cyan);margin-bottom:6px}
.u-line.old .t{margin-bottom:4px}
.u-line .x{font:400 15px/1.42 var(--body);color:var(--cloud)}
.u-line.old .x{font-size:13px}
@keyframes uin{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
#u-time{position:fixed;left:20px;right:20px;bottom:18px;z-index:8;height:60px;border-radius:18px;padding:0 18px;display:flex;align-items:center;gap:16px}
#u-track{position:relative;flex:1;height:100%;cursor:pointer;touch-action:none}
#u-rail{position:absolute;left:0;right:0;top:30px;height:2px;border-radius:2px;background:linear-gradient(90deg,#0b1a44,#2962FF 55%,#7EB8FF 85%,#F6D9A8)}
#u-fill{position:absolute;left:0;top:29px;height:4px;border-radius:4px;background:var(--cyan);box-shadow:0 0 12px var(--cyan);opacity:.9}
#u-head{position:absolute;top:22px;width:18px;height:18px;margin-left:-9px;border-radius:50%;background:#fff;box-shadow:0 0 0 4px rgba(41,98,255,.55),0 0 22px rgba(0,229,255,.8)}
.u-tick{position:absolute;top:40px;font:400 9.5px/1 var(--mono);letter-spacing:.12em;color:var(--slate);transform:translateX(-50%);white-space:nowrap}
.u-tick:before{content:"";position:absolute;left:50%;top:-8px;width:1px;height:5px;background:rgba(240,244,248,.3)}
.u-mom{position:absolute;top:6px;transform:translateX(-50%);font:500 9.5px/1 var(--mono);letter-spacing:.1em;color:var(--cloud);white-space:nowrap;cursor:pointer;
  padding:4px 7px;border-radius:999px;opacity:.72;transition:opacity .2s,background .2s,color .2s}
.u-mom:after{content:"";position:absolute;left:50%;top:21px;width:7px;height:7px;margin-left:-3.5px;border-radius:50%;border:1.5px solid var(--cyan);background:#02040C}
.u-mom:hover,.u-mom.on{opacity:1;background:rgba(0,229,255,.14);color:var(--cyan)}
#u-steps{position:fixed;left:50%;bottom:96px;transform:translateX(-50%);z-index:8}
#u-tip{position:fixed;left:50%;top:calc(50% + 22px);transform:translateX(-50%);max-width:min(380px,86vw);border-radius:14px;padding:11px 14px;pointer-events:none;opacity:0;transition:opacity .25s;text-align:left;z-index:8}
#u-tip .t{font:500 10px/1 var(--mono);letter-spacing:.16em;color:var(--cyan);margin-bottom:6px;text-transform:uppercase}
#u-tip .x{font:italic 400 15px/1.35 var(--display)}
#u-cross{position:fixed;left:50%;top:50%;width:12px;height:12px;margin:-6px 0 0 -6px;border-radius:50%;border:1.5px solid rgba(240,244,248,.8);pointer-events:none;z-index:6;box-shadow:0 0 8px rgba(0,0,0,.6)}
#u-rec{position:fixed;left:50%;top:18px;transform:translateX(-50%);z-index:9;display:none;font:500 11px/1 var(--mono);letter-spacing:.16em;padding:10px 16px;border-radius:999px;color:#fff;background:rgba(255,46,99,.9);box-shadow:0 8px 30px rgba(255,46,99,.4)}
#u-rec i{display:inline-block;width:8px;height:8px;border-radius:50%;background:#fff;margin-right:9px;animation:ublink 1s steps(1) infinite}
#u-toast{position:fixed;left:50%;top:70px;transform:translateX(-50%) translateY(-8px);z-index:9;opacity:0;transition:all .3s;border-radius:999px;padding:10px 16px;font:500 11px/1 var(--mono);letter-spacing:.12em;pointer-events:none}
#u-toast.show{opacity:1;transform:translateX(-50%)}
#u-help{position:fixed;right:20px;bottom:124px;z-index:7;font:400 10px/1.7 var(--mono);letter-spacing:.1em;color:var(--slate);text-align:right;pointer-events:none;text-transform:uppercase}
#u-help b{color:var(--cloud);font-weight:500;border:1px solid var(--line);border-radius:4px;padding:1px 5px;margin:0 2px}
#loading{position:fixed;inset:0;z-index:30;background:radial-gradient(90% 70% at 50% 40%,#06163A 0%,#02040C 70%);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;transition:opacity .9s}
#loading.done{opacity:0;pointer-events:none}
#loading img{height:26px;opacity:.95}
#loading h1{margin:0;font:800 clamp(34px,6vw,64px)/1 var(--display);letter-spacing:-.01em;text-align:center}
#loading .k{font:500 10.5px/1 var(--mono);letter-spacing:.24em;color:var(--cyan)}
#loading p{margin:0;max-width:min(460px,84vw);text-align:center;color:var(--slate);font:400 13px/1.5 var(--body)}
#bar{width:min(300px,70vw);height:3px;border-radius:3px;background:rgba(240,244,248,.12);overflow:hidden}
#bar-in{height:100%;width:0;background:linear-gradient(90deg,var(--blue),var(--cyan));transition:width .3s}
#u-logo{position:fixed;right:22px;bottom:94px;height:16px;opacity:.75;z-index:7;pointer-events:none}
@media (max-width:760px){
  #u-top{left:14px;top:12px}#u-clock{font-size:50px}#u-clock .ap{font-size:16px}#u-clock .s{font-size:12px;margin-top:5px}#u-sub{font-size:9px;letter-spacing:.12em;max-width:52vw}#u-state{display:none}
  #u-right{right:10px;top:12px;gap:8px}.u-btn{height:34px}.u-ic{width:34px}#u-right .u-seg{display:none}#u-right .u-btn.txt{display:none}
  #u-ticker{left:12px;width:calc(100vw - 24px);bottom:84px}.u-line.old{display:none}.u-line .x{font-size:13.5px}
  #u-time{left:10px;right:10px;bottom:10px;height:56px;padding:0 12px}.u-tick.minor{display:none}.u-mom span{display:none}.u-mom{padding:4px}
  #u-steps{bottom:auto;top:calc(100% - 214px)}#u-help,#u-logo{display:none}}
`;

const ICON = {
  play: '<svg viewBox="0 0 24 24"><path d="M7 5l12 7-12 7z"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><path d="M8 5v14M16 5v14"/></svg>',
  shot: '<svg viewBox="0 0 24 24"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.6"/></svg>',
  rec: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="6" fill="currentColor"/></svg>',
  stop: '<svg viewBox="0 0 24 24"><rect x="7" y="7" width="10" height="10" rx="1.5" fill="currentColor"/></svg>',
  full: '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>',
  back: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>',
  fwd: '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7"/></svg>',
  cross: '<svg viewBox="0 0 24 24"><path d="M5 9h14l-3-3M19 15H5l3 3"/></svg>',
  out: '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/></svg>',
};

function el(tag, attrs = {}, html = '') { const e = document.createElement(tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (html) e.innerHTML = html; return e; }

function injectStyle() {
  if (document.getElementById('u-css')) return;
  for (const href of ['https://fonts.googleapis.com', 'https://fonts.gstatic.com']) document.head.appendChild(el('link', { rel: 'preconnect', href, crossorigin: '' }));
  document.head.appendChild(el('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,800;1,400;1,600&family=Roboto+Mono:wght@400;500&display=swap' }));
  document.head.appendChild(el('style', { id: 'u-css' }, CSS));
}
injectStyle();

export async function mountUI(o) {
  const END = o.end || 480;
  const body = document.body;
  // ---- grain and vignette
  const grain = el('canvas', { id: 'u-grain' }); body.appendChild(grain); body.appendChild(el('div', { id: 'u-vig' }));
  const tiles = [];
  for (let i = 0; i < 6; i++) { const c = document.createElement('canvas'); c.width = c.height = 220; const x = c.getContext('2d'), d = x.createImageData(220, 220);
    for (let k = 0; k < d.data.length; k += 4) { const g = 128 + (Math.random() + Math.random() + Math.random() - 1.5) * 95; d.data[k] = d.data[k + 1] = d.data[k + 2] = g; d.data[k + 3] = 255; }
    x.putImageData(d, 0, 0); tiles.push(c); }
  const gx = grain.getContext('2d'); let gi = 0, gLast = 0;
  function grainFrame(now) {
    if (now - gLast > 41) { gLast = now; const w = Math.ceil(innerWidth / 1.15), h = Math.ceil(innerHeight / 1.15);
      if (grain.width !== w || grain.height !== h) { grain.width = w; grain.height = h; }
      gx.save(); gx.fillStyle = gx.createPattern(tiles[gi = (gi + 1) % tiles.length], 'repeat'); gx.translate(Math.random() * 220 | 0, Math.random() * 220 | 0);
      gx.fillRect(-220, -220, w + 440, h + 440); gx.restore(); }
    requestAnimationFrame(grainFrame);
  }
  if (!new URLSearchParams(location.search).has('nograin')) requestAnimationFrame(grainFrame); else grain.style.display = 'none';

  // ---- top left: the clock
  const top = el('div', { id: 'u-top' }, `<div id="u-eye"><i></i>THE UNSUPERVISED SHIFT</div>
    <div id="u-clock"><span class="hh">03</span><span class="c">:</span><span class="mm">17</span><span class="side"><span class="s">:20</span><span class="ap">a.m.</span></span></div>
    <div id="u-sub"><b>West 317th Street</b> · Wed 18 Nov 2026</div><div id="u-state"></div>`);
  body.appendChild(top);
  const cH = top.querySelector('.hh'), cM = top.querySelector('.mm'), cS = top.querySelector('.s'), cA = top.querySelector('.ap');

  // ---- top right: controls
  const right = el('div', { id: 'u-right' }); body.appendChild(right);
  const row = el('div', { class: 'u-row' }); right.appendChild(row);
  const mk = (cls, html, title, on) => { const b = el('button', { class: 'u-btn u-glass ' + cls, title, 'aria-label': title }, html); b.onclick = on; row.appendChild(b); return b; };
  let playBtn = null;
  if (o.onPlay) playBtn = mk('u-ic', ICON.pause, 'Pause the clock (space)', () => o.onPlay());
  const shotBtn = mk('u-ic', ICON.shot, 'Screenshot (C)', () => screenshot());
  const recBtn = mk('u-ic', ICON.rec, 'Record the visit (R)', () => toggleRec());
  recBtn.style.color = 'var(--pink)';
  mk('u-ic', ICON.full, 'Full screen', () => { const d = document.documentElement; if (!document.fullscreenElement) (d.requestFullscreen || d.webkitRequestFullscreen || (() => {})).call(d); else document.exitFullscreen(); });
  const piece = el('a', { class: 'u-btn u-glass txt', href: o.piece || '/shift', target: '_top' }, 'The piece ' + ICON.out.replace('<svg', '<svg style="width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:1.8"'));
  row.appendChild(piece);
  let seg = null;
  if (o.speeds) { seg = el('div', { class: 'u-seg u-glass' }); right.appendChild(seg);
    for (const [s, l] of o.speeds) { const b = el('button', { 'data-s': s }, l); b.onclick = () => o.onSpeed(s); seg.appendChild(b); } }

  // ---- ticker
  const tick = el('div', { id: 'u-ticker' }); body.appendChild(tick);
  let LINES = o.log || [];
  try { const r = await fetch(A + 'ticker.json' + (window.WALK_V ? '?v=' + window.WALK_V : '')); if (r.ok) LINES = (await r.json()).lines; } catch (e) {}
  let shown = -2;
  function ticker(t) {
    let i = -1; for (let j = 0; j < LINES.length; j++) if (LINES[j][0] <= t) i = j;
    if (i === shown) return; const grew = i === shown + 1; shown = i;
    const fmt = m => { const h = Math.floor(m / 60), mm = Math.floor(m % 60), h12 = h % 12 || 12; return h12 + ':' + pad(mm) + (h < 12 ? ' A.M.' : ' P.M.'); };
    const show = LINES.slice(Math.max(0, i - 1), i + 1);
    tick.innerHTML = show.map(([m, s], k) => `<div class="u-line u-glass${k < show.length - 1 ? ' old' : ''}"${grew || k < show.length - 1 ? '' : ' style="animation:none"'}><div class="t">${fmt(m)}</div><div class="x">${s}</div></div>`).join('');
  }

  // ---- timeline
  const time = el('div', { id: 'u-time', class: 'u-glass' }, '<div id="u-track"><div id="u-rail"></div><div id="u-fill"></div><div id="u-head"></div></div>'); body.appendChild(time);
  const track = time.querySelector('#u-track'), fill = time.querySelector('#u-fill'), head = time.querySelector('#u-head');
  const pct = t => (100 * Math.max(0, Math.min(END, t)) / END) + '%';
  for (let h = 0; h <= 8; h++) { const d = el('div', { class: 'u-tick' + (h % 2 ? ' minor' : '') }, h === 0 ? '12 A.M.' : h + ' A.M.'); d.style.left = pct(h * 60); if (h === 8) d.style.transform = 'translateX(-100%)'; if (h === 0) d.style.transform = 'none'; track.appendChild(d); }
  const moms = (o.moments || []).map((m, i) => { const d = el('div', { class: 'u-mom' }, `<span>${m.label}</span>`); d.style.left = pct(m.t); d.title = m.label; if (m.t < 25) d.style.transform = 'translateX(-12px)';
    d.onclick = e => { e.stopPropagation(); o.onMoment(i); }; track.appendChild(d); return d; });
  let dragging = false;
  const tAt = e => { const r = track.getBoundingClientRect(); return END * Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); };
  track.addEventListener('pointerdown', e => { dragging = true; track.setPointerCapture(e.pointerId); o.onScrub && o.onScrub(tAt(e), false); });
  track.addEventListener('pointermove', e => { if (dragging && o.onScrub) o.onScrub(tAt(e), false); });
  track.addEventListener('pointerup', e => { if (dragging && o.onScrub) o.onScrub(tAt(e), true); dragging = false; });

  // ---- steps (photographed walk)
  if (o.onStep) { const st = el('div', { id: 'u-steps', class: 'u-row' }); body.appendChild(st);
    const b = (html, title, f) => { const x = el('button', { class: 'u-btn u-glass', title }, html); x.onclick = f; st.appendChild(x); };
    b(ICON.back + 'Back', 'Step back (S)', () => o.onStep(-1)); b(ICON.cross + 'Cross', 'Cross the street', () => o.onCross()); b('Forward' + ICON.fwd, 'Step forward (W)', () => o.onStep(1)); }
  if (o.crosshair) body.appendChild(el('div', { id: 'u-cross' }));
  const tip = el('div', { id: 'u-tip', class: 'u-glass' }); body.appendChild(tip);
  if (o.help) body.appendChild(el('div', { id: 'u-help' }, o.help));
  const logo = el('img', { id: 'u-logo', src: A + 'ui/logo_white.png', alt: 'MLow' }); body.appendChild(logo);
  const recPill = el('div', { id: 'u-rec' }, '<i></i><span>REC 0:00</span>'); body.appendChild(recPill);
  const toast = el('div', { id: 'u-toast', class: 'u-glass' }); body.appendChild(toast);
  let toastT = 0; const say = s => { toast.textContent = s; toast.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => toast.classList.remove('show'), 2200); };

  // ---- capture: the frame, the grain, the vignette, a caption and the logo
  const logoImg = new Image(); logoImg.src = A + 'ui/logo_white.png';
  let tNow = 0;
  const label = () => { const m = Math.floor(tNow), h = Math.floor(m / 60), h12 = h % 12 || 12; return 'WEST 317TH STREET  ·  ' + h12 + ':' + pad(m % 60) + (h < 12 ? ' A.M.' : ' P.M.') + '  ·  THE UNSUPERVISED SHIFT'; };
  function compose(ctx, W, H, caption) {
    const src = o.canvas(); ctx.drawImage(src, 0, 0, W, H);
    ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.2; ctx.drawImage(grain, 0, 0, W, H); ctx.restore();
    const g = ctx.createRadialGradient(W / 2, H * 0.46, Math.min(W, H) * 0.35, W / 2, H * 0.46, Math.hypot(W, H) * 0.62); g.addColorStop(0, 'rgba(2,4,12,0)'); g.addColorStop(1, 'rgba(2,4,12,.55)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    if (caption) { const s = Math.max(1, W / 1600), m = 34 * s;
      ctx.font = `500 ${Math.round(14 * s)}px "Roboto Mono", Consolas, monospace`; ctx.fillStyle = 'rgba(240,244,248,.9)'; ctx.textBaseline = 'alphabetic';
      if (ctx.letterSpacing !== undefined) ctx.letterSpacing = `${(2.2 * s).toFixed(1)}px`;
      ctx.fillText(label(), m, H - m);
      if (logoImg.complete && logoImg.naturalWidth) { const lh = 22 * s, lw = lh * logoImg.naturalWidth / logoImg.naturalHeight; ctx.globalAlpha = 0.85; ctx.drawImage(logoImg, W - m - lw, H - m - lh + 4 * s, lw, lh); ctx.globalAlpha = 1; } }
  }
  const stamp = () => { const m = Math.floor(tNow); return pad(Math.floor(m / 60)) + pad(m % 60); };
  function download(blob, name) { const a = el('a', { href: URL.createObjectURL(blob), download: name }); body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); }
  async function screenshot() {
    if (o.beforeCapture) await o.beforeCapture();
    const src = o.canvas(), W = src.width, H = src.height, c = document.createElement('canvas'); c.width = W; c.height = H;
    compose(c.getContext('2d'), W, H, true);
    c.toBlob(b => { download(b, `west-317th-street_${stamp()}.png`); say('SCREENSHOT SAVED'); }, 'image/png');
    shotBtn.classList.add('on'); setTimeout(() => shotBtn.classList.remove('on'), 300);
  }
  let rec = null;
  function toggleRec() {
    if (rec) { rec.stop(); return; }
    if (!window.MediaRecorder) { say('THIS BROWSER CANNOT RECORD'); return; }
    const src = o.canvas(), k = Math.min(1, 1920 / src.width), W = Math.round(src.width * k / 2) * 2, H = Math.round(src.height * k / 2) * 2;
    const c = document.createElement('canvas'); c.width = W; c.height = H; const ctx = c.getContext('2d');
    const type = ['video/mp4;codecs=avc1.640028', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm'].find(t => MediaRecorder.isTypeSupported(t)) || '';
    const stream = c.captureStream(30), mr = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 14e6 }), chunks = [], t0 = performance.now();
    let live = true; const loop = () => { if (!live) return; compose(ctx, W, H, true); const s = (performance.now() - t0) / 1000;
      recPill.querySelector('span').textContent = 'REC ' + Math.floor(s / 60) + ':' + pad(Math.floor(s % 60)); if (s > 120) mr.stop(); requestAnimationFrame(loop); };
    mr.ondataavailable = e => e.data.size && chunks.push(e.data);
    mr.onstop = () => { live = false; rec = null; recPill.style.display = 'none'; recBtn.classList.remove('rec'); recBtn.innerHTML = ICON.rec; recBtn.style.color = 'var(--pink)';
      const ext = (mr.mimeType || type).includes('mp4') ? 'mp4' : 'webm'; download(new Blob(chunks, { type: mr.mimeType || type }), `west-317th-street_visit_${stamp()}.${ext}`); say('VISIT SAVED'); };
    mr.start(500); rec = mr; recPill.style.display = 'block'; recBtn.classList.add('rec'); recBtn.innerHTML = ICON.stop; recBtn.style.color = ''; loop(); say('RECORDING · PRESS R TO STOP');
  }
  addEventListener('keydown', e => { if (e.target.tagName === 'INPUT') return; if (e.code === 'KeyC') screenshot(); else if (e.code === 'KeyR') toggleRec(); });

  return {
    setTime(t, opts = {}) {
      tNow = t; const m = Math.floor(t), sec = Math.floor((t - m) * 60), h = Math.floor(m / 60) % 24, h12 = h % 12 || 12;
      cH.textContent = h12 < 10 ? '0' + h12 : String(h12); cM.textContent = pad(m % 60); cS.textContent = opts.seconds === false ? '' : ':' + pad(sec); cA.textContent = h < 12 ? 'a.m.' : 'p.m.';
      if (!dragging || !o.onScrub) { fill.style.width = pct(t); head.style.left = pct(t); } else { fill.style.width = pct(t); head.style.left = pct(t); }
      ticker(t);
    },
    setState(s) { $('u-state').textContent = s || ''; },
    setPlaying(p) { if (playBtn) { playBtn.innerHTML = p ? ICON.pause : ICON.play; playBtn.classList.toggle('on', !p); } },
    setSpeed(s) { if (seg) seg.querySelectorAll('button').forEach(b => b.classList.toggle('on', +b.dataset.s === s)); },
    setMoment(i) { moms.forEach((d, k) => d.classList.toggle('on', k === i)); },
    setTip(who, line) { if (!who) { tip.style.opacity = 0; return; } tip.innerHTML = `<div class="t">${who}</div><div class="x">${line}</div>`; tip.style.opacity = 1; },
    say, refreshTicker() { shown = -2; },
    async frame() { if (o.beforeCapture) await o.beforeCapture(); const src = o.canvas(), c = document.createElement('canvas'); c.width = src.width; c.height = src.height; compose(c.getContext('2d'), c.width, c.height, true); return c.toDataURL('image/jpeg', 0.85); },
    recordTest(ms) { return new Promise(res => { toggleRec(); setTimeout(() => { const r = rec; r.addEventListener('stop', () => setTimeout(() => res(r.mimeType), 50)); r.stop(); }, ms); }); },
  };
}
