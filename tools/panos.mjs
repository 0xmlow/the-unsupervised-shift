// tools/panos.mjs URL OUTDIR [size]   (Nov 18) 360 photographs of the walk for browsers without WebGL.
// Runs the real walk in headless Chrome on the Mac's GPU, stands at every node at every moment, and saves
// OUTDIR/<moment>_<node>.jpg (equirectangular) plus OUTDIR/panos.json, which tools/../walk/pano.js reads.
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { join } from 'node:path';
const [url, out, sizeA] = process.argv.slice(2); const SIZE = +(sizeA || 2048);
const MOMENTS = [['0030', '00:30', 'half past midnight'], ['0240', '02:40', 'the rain'], ['0317', '03:17:20', 'the cat crosses'], ['0520', '05:20', 'kitchens'], ['0713', '07:13', 'sun in the slot']];
const NODES = [];
for (const [side, y] of [['s', -6.4], ['n', 6.4]]) for (let x = -4, i = 0; x <= 100; x += 8, i++) NODES.push({ id: side + String(i).padStart(2, '0'), x, y });
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PROFILE = join(out, '_chrome'); mkdirSync(out, { recursive: true });
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ['--headless=new', '--hide-scrollbars', '--mute-audio', `--remote-debugging-port=${port}`, `--user-data-dir=${PROFILE}`,
  '--window-size=1280,800', '--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const done = c => { try { chrome.kill('SIGKILL'); } catch {} try { rmSync(PROFILE, { recursive: true, force: true }); } catch {} process.exit(c); };
let target; for (let i = 0; i < 100 && !target; i++) { try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t => t.type === 'page'); } catch {} if (!target) await sleep(150); }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
let id = 0; const wait = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && wait.has(m.id)) { wait.get(m.id)(m); wait.delete(m.id); } if (m.method === 'Runtime.exceptionThrown') console.log('exception', JSON.stringify(m.params.exceptionDetails).slice(0, 300)); };
const send = (method, params = {}) => new Promise(res => { const i = ++id; wait.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async x => { const r = await send('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 300)); return r.result?.result?.value; };
await send('Page.enable'); await send('Runtime.enable'); await send('Page.navigate', { url });
for (let i = 0; i < 600; i++) { if (await ev('!!(window.__walk && document.getElementById("loading") == null)').catch(() => false)) break; await sleep(200); }
await ev(`document.getElementById('play').click()`);          // pause the clock: every photograph is one exact minute
const index = { moments: MOMENTS.map(([k, t, l]) => ({ k, t, l })), nodes: NODES, size: SIZE };
let n = 0; const t0 = Date.now();
for (const [k, t] of MOMENTS) {
  for (const nd of NODES) {
    const f = join(out, `${k}_${nd.id}.jpg`); if (existsSync(f)) continue;
    await ev(`(() => { const [h,m,s] = "${t}".split(":").map(Number); __walk.t = h*60+m+(s||0)/60; __walk.setView(${nd.x}, ${nd.y}, 0, 0); })()`);
    for (let r = 0; r < 4; r++) { await ev('__walk.render()'); await sleep(120); }        // movers near the node load on first sight
    const d = await ev(`__walk.pano(${SIZE})`);
    writeFileSync(f, Buffer.from(d.split(',')[1], 'base64')); n++;
    if (n % 10 === 0) console.log(n, 'panos', ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
}
writeFileSync(join(out, 'panos.json'), JSON.stringify(index));
console.log('done', n, 'new panos');
done(0);
