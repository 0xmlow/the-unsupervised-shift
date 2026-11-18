// tools/walkshot.mjs URL OUTDIR [W H] [views.json]   (Nov 18) photograph the walk in headless Chrome on the Mac's GPU.
// A view is {name, t: "03:17", x, y, yaw, pitch}. Prints the page's console errors and its renderer info.
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
const [url, out, wA, hA, viewsA] = process.argv.slice(2);
const W = +(wA || 1280), H = +(hA || 800);
const VIEWS = viewsA ? JSON.parse(readFileSync(viewsA, 'utf8')) : [
  { name: 'start_0317', t: '03:16:50', x: -4, y: 1.1, yaw: -1.5708, pitch: 0.02 },
  { name: 'canyon_0100', t: '01:00', x: 2, y: -6.5, yaw: -1.5708, pitch: 0.04 },
  { name: 'rain_0240', t: '02:40', x: 30, y: 6.8, yaw: -1.2, pitch: 0.05 },
  { name: 'deli_0400', t: '04:00', x: 7, y: 4.2, yaw: 0, pitch: 0.1 },
  { name: 'witness_0440', t: '04:40', x: 9, y: 1.6, yaw: 2.9, pitch: 0.12 },
  { name: 'dawn_0713', t: '07:13', x: -4, y: 1.1, yaw: -1.5708, pitch: 0.06 },
  { name: 'up_0520', t: '05:20', x: 48, y: -6, yaw: 0.0, pitch: 0.45 },
];
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PROFILE = join(out, '_chrome'); mkdirSync(out, { recursive: true });
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ['--headless=new', '--hide-scrollbars', '--mute-audio', `--remote-debugging-port=${port}`, `--user-data-dir=${PROFILE}`,
  `--window-size=${W},${H}`, '--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const done = c => { try { chrome.kill('SIGKILL'); } catch {} try { rmSync(PROFILE, { recursive: true, force: true }); } catch {} process.exit(c); };
let target; for (let i = 0; i < 100 && !target; i++) { try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t => t.type === 'page'); } catch {} if (!target) await sleep(150); }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
let id = 0; const wait = new Map(); const logs = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && wait.has(m.id)) { wait.get(m.id)(m); wait.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled' && /error|warn/.test(m.params.type)) logs.push(m.params.type + ': ' + m.params.args.map(a => a.value || a.description).join(' ').slice(0, 300));
  if (m.method === 'Runtime.exceptionThrown') logs.push('exception: ' + JSON.stringify(m.params.exceptionDetails).slice(0, 500)); };
const send = (method, params = {}) => new Promise(res => { const i = ++id; wait.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async x => (await send('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true })).result?.result?.value;
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate', { url });
const t0 = Date.now(); let ok = false;
for (let i = 0; i < 600; i++) { if (await ev('!!(window.__walk && document.getElementById("loading") == null)')) { ok = true; break; } await sleep(200); }
console.log('ready', ok, ((Date.now() - t0) / 1000).toFixed(1) + 's');
if (ok) {
  await sleep(1500);
  console.log('gl', await ev('(() => { const g = __walk.renderer.getContext(), d = g.getExtension("WEBGL_debug_renderer_info"); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : "?" })()'));
  for (const v of VIEWS) {
    await ev(`(() => { const [h,m,s] = "${v.t}".split(":").map(Number); __walk.t = h*60+m+(s||0)/60; __walk.setView(${v.x}, ${v.y}, ${v.yaw}, ${v.pitch}); })()`);
    for (let k = 0; k < 6; k++) { await ev('__walk.render()'); await sleep(250); }       // movers load on first sight
    const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 });
    writeFileSync(join(out, v.name + '.jpg'), Buffer.from(s.result.data, 'base64'));
    const info = await ev('JSON.stringify(__walk.renderer.info.render)');
    console.log('shot', v.name, info);
    if (v.eval) console.log('eval', v.name, await ev(v.eval));
    for (const [px, py] of (v.probe || [])) console.log('probe', px, py, await ev(`(() => { const T = __walk.THREE, r = new T.Raycaster(); r.setFromCamera({ x: ${px} / innerWidth * 2 - 1, y: 1 - ${py} / innerHeight * 2 }, __walk.camera);
      const vis = o => { while (o) { if (!o.visible) return false; o = o.parent; } return true; }; const h = r.intersectObjects(__walk.scene.children, true).find(x => x.object.isMesh && vis(x.object) && x.object.material.type !== 'ShaderMaterial' || (x.object.material.uniforms && x.object.material.uniforms.mapN)); if (!h) return 'nothing'; let o = h.object, n = []; while (o) { n.push(o.name); o = o.parent; }
      return JSON.stringify({ path: n.join(' < '), mat: h.object.material && (h.object.material.name || h.object.material.type), uv: h.uv, d: h.distance.toFixed(1), p: h.point }); })()`));
  }
}
console.log(logs.slice(0, 30).join('\n'));
done(0);
