"""
THE UNSUPERVISED SHIFT  ·  experiment 53 of 100  ·  build_sound.py
The block's night as sound, synthesised from the same schedule as the pictures. No samples, no recordings:
every sound is noise or sine waves shaped in numpy.

    python3 build_sound.py 20      -> sound/night_20s.wav   (one block minute = 1/24 s, fits the film)
    python3 build_sound.py 240     -> sound/night_240s.wav  (one block minute = half a second, for listening)

Left ear is the north side of the street, right ear the south, as if you stood in the roadway facing east.
"""
import sys, os, math, wave
import numpy as np
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import block as K

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 240.0
SR = 44100; N = int(DUR * SR); SPM = DUR / 480.0            # seconds per block minute
rng = np.random.default_rng(K.SEED)
L = np.zeros(N); R = np.zeros(N)
tt = np.arange(N) / SR; bm = tt / SPM                       # block minute at every sample

def lowpass(x, fc):
    a = math.exp(-2 * math.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    # one-pole, vectorised with a cumulative trick is unstable for long arrays, so filter in the frequency domain instead
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), len(x))
def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = 1 / np.sqrt(1 + (f / hi) ** 6) * (1 - 1 / np.sqrt(1 + (f / max(lo, 1)) ** 6)); return np.fft.irfft(X * g, len(x))
def put(sig, at, pan=0.0, gain=1.0):
    """Mix sig in at time `at` seconds. pan -1 = left (north), +1 = right (south)."""
    i = int(at * SR)
    if i >= N or i + len(sig) <= 0: return
    if i < 0: sig = sig[-i:]; i = 0
    sig = sig[:N - i]; l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
    L[i:i + len(sig)] += sig * gain * l; R[i:i + len(sig)] += sig * gain * r
def env(n, a=0.1, r=0.3):
    e = np.ones(n); na = max(1, int(n * a)); nr = max(1, int(n * r)); e[:na] = np.linspace(0, 1, na) ** 2; e[-nr:] = np.linspace(1, 0, nr) ** 2; return e
def at(minute): return minute * SPM
def panx(y): return max(-1.0, min(1.0, -y / 9.0))           # north (+y) is left

# 1. the city: a low hum that thins out toward 4 a.m. and comes back
hum = lowpass(rng.standard_normal(N), 110) * 6.0 + lowpass(rng.standard_normal(N), 420) * 1.2
level = 0.045 + 0.10 * np.exp(-bm / 80.0) + 0.14 * np.clip((bm - 330) / 150.0, 0, 1) ** 1.5
L += hum * level; R += np.roll(hum, SR // 7) * level
for f0 in (59.0, 118.5):                                     # transformers and somebody's compressor
    L += 0.006 * np.sin(2 * math.pi * f0 * tt); R += 0.006 * np.sin(2 * math.pi * f0 * tt + 1.0)

# 2. rain: hiss while it falls, a drip for a while after
r0, r1 = at(K.RAIN[0]), at(K.RAIN[1]); n = int((r1 - r0) * SR) + SR
hiss = bandpass(rng.standard_normal(n), 1800, 9000) * env(n, 0.12, 0.2)
put(hiss, r0, -0.3, 0.16); put(bandpass(rng.standard_normal(n), 900, 5000) * env(n, 0.12, 0.2), r0, 0.3, 0.13)
for k in range(int(40 * max(1.0, DUR / 60))):
    t0 = r1 + rng.uniform(0, at(70)); m = int(0.05 * SR); f = rng.uniform(900, 2200)
    put(np.sin(2 * math.pi * f * np.arange(m) / SR * np.linspace(1, 0.6, m)) * np.exp(-np.arange(m) / (0.008 * SR)), t0, rng.uniform(-1, 1), 0.05)

# 3. everything on wheels
def whoosh(secs, lo, hi, rumble=0.0):
    m = max(int(secs * SR), 2000); x = bandpass(rng.standard_normal(m), lo, hi); e = np.exp(-((np.arange(m) / m - 0.5) / 0.22) ** 2)
    if rumble: x = x + lowpass(rng.standard_normal(m), 70) * rumble
    return x * e
for mv in K.MOVERS:
    k = mv['kind']
    if k in ('car', 'cab', 'van', 'boxtruck', 'bus', 'sweeper'):
        t0, t1 = mv['keys'][0][0], mv['keys'][-1][0]; secs = max(0.5, min(3.5, (t1 - t0) * SPM + 0.6))
        big = k in ('boxtruck', 'bus', 'sweeper'); wet = K.wetness((t0 + t1) / 2)
        put(whoosh(secs, 150 if big else 300, 2500 + 4500 * wet, 4.0 if big else 0.0), at(t0) - 0.2, panx(mv['keys'][0][2]) * 0.4, 0.10 if big else 0.07)
        if k == 'bus':                                       # air brakes
            m = int(0.35 * SR); put(bandpass(rng.standard_normal(m), 2500, 9000) * env(m, 0.02, 0.8), at(mv['keys'][1][0]), 0.5, 0.12)
    if k == 'garbage':                                       # brakes, hopper, brakes: one event per stop
        ks = mv['keys']
        for (ta, xa, _), (tb, xb, _) in zip(ks, ks[1:]):
            if xa == xb:
                m = int(max(0.25, (tb - ta) * SPM) * SR); p = (xa - 48) / 60.0
                whine = np.sin(2 * math.pi * np.cumsum(np.linspace(180, 420, m)) / SR) * 0.4 + lowpass(rng.standard_normal(m), 90) * 5
                put(whine * env(m, 0.1, 0.2), at(ta), p, 0.09)
                c = int(0.18 * SR); put(bandpass(rng.standard_normal(c), 300, 6000) * np.exp(-np.arange(c) / (0.03 * SR)), at(tb) - 0.1, p, 0.22)
                b = int(0.06 * SR); beep = np.sin(2 * math.pi * 1250 * np.arange(b) / SR) * env(b, 0.1, 0.1)
                for q in range(3): put(beep, at(ta) + q * 0.11, p, 0.03)

# 4. LAST CALL: the bass through the wall until the lights come up
bar_end = at(236); beat = 60.0 / 118
kick = np.sin(2 * math.pi * np.cumsum(np.linspace(95, 42, int(0.16 * SR))) / SR) * np.exp(-np.arange(int(0.16 * SR)) / (0.05 * SR))
tk = 0.0
while tk < bar_end:
    fade = min(1.0, (bar_end - tk) / max(0.5, at(15))); put(kick, tk, 0.75, 0.05 * fade); tk += beat
for mv in K.MOVERS:                                          # the door opening lets the room out
    if mv['who'] == 'Last call':
        m = int(0.4 * SR); put(bandpass(rng.standard_normal(m), 300, 2500) * env(m, 0.2, 0.5), at(mv['keys'][0][0]), 0.8, 0.05)

# 5. The Saxophonist, with a towel in the bell, until 00:3x
sax_end = at([b for a, b, kk in K.RESIDENTS['N3-3']['sched']['living']][0] - 25)
scale = [233.08, 261.63, 311.13, 349.23, 392.0, 466.16, 523.25]; tk = 0.2; sr2 = np.random.default_rng(K.SEED + 1)
while tk < sax_end:
    d = sr2.choice([0.18, 0.27, 0.4, 0.6]) * max(0.5, min(1.0, SPM * 4)); f = sr2.choice(scale); m = int(d * SR); x = np.arange(m) / SR
    vib = 1 + 0.006 * np.sin(2 * math.pi * 5.5 * x); tone = sum(np.sin(2 * math.pi * f * h * x * vib) / h ** 1.6 for h in (1, 2, 3, 4, 5))
    put(lowpass(tone, 900) * env(m, 0.15, 0.3), tk, -0.55, 0.02); tk += d * sr2.choice([1.0, 1.0, 1.5])

# 6. gates
for key, s in K.SHOPS.items():
    y = 1 if K.B[s['b']]['side'] == 'N' else -1
    for a, b in s['gate']:
        for edge in ([a] if a > 0 else []) + ([b] if b < 480 else []):
            m = int(0.5 * SR); rattle = bandpass(rng.standard_normal(m), 500, 5000) * (0.5 + 0.5 * np.sign(np.sin(2 * math.pi * 38 * np.arange(m) / SR))) * env(m, 0.05, 0.3)
            put(rattle, at(edge), panx(y * 9), 0.10)

# 7. the subway under the avenue, every so often
tk = at(7)
while tk < DUR:
    m = int(min(3.0, max(1.2, at(3))) * SR); put(lowpass(rng.standard_normal(m), 55) * env(m, 0.4, 0.5) * 9, tk, 0.6, 0.07); tk += at(rng.uniform(16, 26) if tk < at(300) else rng.uniform(6, 10))

# 8. birds, from first light
for k in range(int(260 * max(1.0, DUR / 60))):
    mnt = K.CIVIL_DAWN - 6 + rng.triangular(0, 55, 110)
    if mnt >= 480: continue
    m = int(rng.uniform(0.04, 0.11) * SR); f0 = rng.uniform(2600, 5200); x = np.arange(m) / SR
    chirp = np.sin(2 * math.pi * (f0 * x + rng.uniform(-9000, 14000) * x * x)) * env(m, 0.2, 0.4)
    for q in range(rng.integers(1, 4)): put(chirp, at(mnt) + q * 0.09, rng.uniform(-1, 1), rng.uniform(0.012, 0.035))

# 9. small things: the lamps going off, the hose, the school bus door, footsteps for the named ones
m = int(0.03 * SR); put(rng.standard_normal(m) * np.exp(-np.arange(m) / (0.004 * SR)), at(K.LAMPS_OFF), 0, 0.2)
h0, h1 = at(420), at(456); m = int((h1 - h0) * SR); put(bandpass(rng.standard_normal(m), 2500, 8000) * env(m, 0.05, 0.05), h0, -0.7, 0.012)

mix = np.stack([L, R], 1); mix = np.tanh(mix * 2.2) ; mix *= 0.89 / np.max(np.abs(mix))
fade = int(0.05 * SR); mix[:fade] *= np.linspace(0, 1, fade)[:, None]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
os.makedirs(os.path.join(HERE, 'sound'), exist_ok=True); out = os.path.join(HERE, 'sound', 'night_%ds.wav' % int(DUR))
with wave.open(out, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
print(out, '%.1f s' % DUR, 'peak', float(np.max(np.abs(mix))), 'rms', float(np.sqrt(np.mean(mix ** 2))))
