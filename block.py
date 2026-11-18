"""
THE UNSUPERVISED SHIFT  ·  experiment 53 of 100  ·  block.py
West 317th Street, one invented New York block, midnight to 8 a.m., as data.

This file is the source of truth. It has no Blender in it. build_block.py (Blender) and
build_web.py (the web page) both read it. Run it directly to write block.json,
RESIDENTS.md and NIGHT_LOG.md:

    python3 block.py

Units are metres and minutes after midnight. x runs west to east along the street (0..96),
y runs south to north, the roadway is y -5..5, sidewalks are 4 m, facades stand at y = +9
(north side, facing south) and y = -9 (south side, facing north). Seed 317.
"""
import math, random, json, os

SEED = 317
L = 96.0            # corner to corner
ROAD = 5.0          # half width of roadway
WALK = 4.0          # sidewalk width
FAC = ROAD + WALK   # facade line, 9 m from the centre line
GROUND_H = 4.0      # shop floor height
FLOOR_H = 3.2       # upper floor height
NIGHT_END = 480     # 8:00 a.m.
DATE = "Wednesday, November 18, 2026"

def hm(t):
    t = int(round(t)); return "%02d:%02d" % (t // 60, t % 60)
def T(s):
    p = [float(v) for v in s.split(":")]; return p[0] * 60 + p[1] + (p[2] / 60.0 if len(p) > 2 else 0.0)

# ------------------------------------------------------------------ lots
# kind: tenement | brownstone | prewar | garage | garden
# brick: facade colour (linear-ish rgb 0..1), trim: lintels, sills, cornice
BUILDINGS = [
 # north side, west to east
 dict(id="N1", side="N", x0=0.0,  w=14.0, floors=5, kind="tenement",   brick=(0.33, 0.085, 0.055), trim=(0.30, 0.27, 0.23), escape=True,  name="301 W 317th", shop="grocery"),
 dict(id="N2", side="N", x0=14.0, w=10.0, floors=5, kind="tenement",   brick=(0.42, 0.30, 0.17),   trim=(0.34, 0.30, 0.25), escape=True,  name="305 W 317th", shop="laundromat"),
 dict(id="N3", side="N", x0=24.0, w=6.5,  floors=4, kind="brownstone", brick=(0.17, 0.095, 0.065), trim=(0.20, 0.12, 0.085), escape=False, name="309 W 317th", shop=None),
 dict(id="N4", side="N", x0=30.5, w=6.5,  floors=4, kind="brownstone", brick=(0.50, 0.52, 0.54),   trim=(0.62, 0.64, 0.66), escape=False, name="311 W 317th", shop=None),
 dict(id="N5", side="N", x0=37.0, w=6.5,  floors=4, kind="brownstone", brick=(0.11, 0.07, 0.055),  trim=(0.15, 0.10, 0.08), escape=False, name="313 W 317th", shop=None),
 dict(id="N6", side="N", x0=43.5, w=18.0, floors=6, kind="prewar",     brick=(0.36, 0.27, 0.17),   trim=(0.52, 0.48, 0.40), escape=False, name="The Meridian Arms, 317 W 317th", shop=None, shed=True),
 dict(id="N7", side="N", x0=61.5, w=12.0, floors=1, kind="garage",     brick=(0.30, 0.30, 0.31),   trim=(0.20, 0.20, 0.21), escape=False, name="325 W 317th", shop="garage"),
 dict(id="N8", side="N", x0=73.5, w=10.0, floors=5, kind="tenement",   brick=(0.27, 0.075, 0.06),  trim=(0.33, 0.30, 0.26), escape=True,  name="331 W 317th", shop="pizza"),
 dict(id="N9", side="N", x0=83.5, w=12.5, floors=6, kind="tenement",   brick=(0.40, 0.33, 0.24),   trim=(0.30, 0.27, 0.23), escape=True,  name="335 W 317th", shop="diner"),
 # south side, west to east
 dict(id="S1", side="S", x0=0.0,  w=13.0, floors=5, kind="tenement",   brick=(0.24, 0.07, 0.05),   trim=(0.28, 0.25, 0.21), escape=True,  name="300 W 317th", shop="bar"),
 dict(id="S2", side="S", x0=13.0, w=9.0,  floors=4, kind="tenement",   brick=(0.44, 0.38, 0.30),   trim=(0.30, 0.27, 0.22), escape=True,  name="304 W 317th", shop="flowers"),
 dict(id="S3", side="S", x0=22.0, w=12.0, floors=0, kind="garden",     brick=(0.2, 0.2, 0.2),      trim=(0.2, 0.2, 0.2),    escape=False, name="317th Street Garden", shop=None),
 dict(id="S4", side="S", x0=34.0, w=6.5,  floors=4, kind="brownstone", brick=(0.19, 0.10, 0.07),   trim=(0.22, 0.13, 0.09), escape=False, name="312 W 317th", shop=None),
 dict(id="S5", side="S", x0=40.5, w=6.5,  floors=4, kind="brownstone", brick=(0.36, 0.13, 0.09),   trim=(0.45, 0.42, 0.37), escape=False, name="314 W 317th", shop=None),
 dict(id="S6", side="S", x0=47.0, w=16.0, floors=6, kind="prewar",     brick=(0.30, 0.10, 0.07),   trim=(0.50, 0.46, 0.38), escape=False, name="Halcyon Court, 318 W 317th", shop=None),
 dict(id="S7", side="S", x0=63.0, w=10.0, floors=5, kind="tenement",   brick=(0.46, 0.36, 0.22),   trim=(0.32, 0.29, 0.24), escape=True,  name="326 W 317th", shop="bakery"),
 dict(id="S8", side="S", x0=73.0, w=9.0,  floors=4, kind="tenement",   brick=(0.20, 0.20, 0.22),   trim=(0.30, 0.30, 0.31), escape=True,  name="330 W 317th", shop="locksmith"),
 dict(id="S9", side="S", x0=82.0, w=14.0, floors=5, kind="tenement",   brick=(0.31, 0.09, 0.06),   trim=(0.31, 0.28, 0.24), escape=True,  name="334 W 317th", shop="pharmacy"),
]
B = {b["id"]: b for b in BUILDINGS}

def height(b):
    if b["kind"] == "garden": return 0.0
    if b["kind"] == "garage": return 6.0
    if b["kind"] == "brownstone": return 1.6 + b["floors"] * FLOOR_H + 0.9      # raised parlour floor over an English basement
    return GROUND_H + (b["floors"] - 1) * FLOOR_H + 1.0                          # parapet

# ------------------------------------------------------------------ shops
# lights: list of (t0, t1, level 0..1). gate: list of (t0, t1) when the roll gate is DOWN.
# sign is the lit sign or awning lettering; neon is one accent colour from the house palette.
INK = (0.05, 0.05, 0.05); CLOUD = (0.94, 0.957, 0.973); BLUE = (0.161, 0.384, 1.0)
CYAN = (0.0, 0.898, 1.0); PINK = (1.0, 0.18, 0.388); ACID = (0.843, 1.0, 0.122)
SHOPS = {
 "grocery":    dict(b="N1", name="BLUE EYE GROCERY", sub="OPEN 24 HOURS  ·  COFFEE  ·  ATM  ·  FLOWERS", awning=BLUE, ink=CLOUD, neon=CYAN, glow=(0.85, 1.0, 0.9),
                    lights=[(0, 480, 1.0)], gate=[], note="Never closes. The cat is on the payroll."),
 "laundromat": dict(b="N2", name="SOFT WATER LAUNDROMAT", sub="WASH  ·  DRY  ·  FOLD  ·  LAST WASH 12:30", awning=CLOUD, ink=BLUE, neon=BLUE, glow=(0.8, 0.9, 1.0),
                    lights=[(0, 62, 1.0), (62, 345, 0.12), (345, 480, 1.0)], gate=[], note="Lights drop at 1:02 when the last dryer stops. Back up at 5:45."),
 "garage":     dict(b="N7", name="317 FLAT FIX", sub="TIRES  ·  BRAKES  ·  INSPECTION", awning=ACID, ink=INK, neon=ACID, glow=(1.0, 0.95, 0.8),
                    lights=[(0, 440, 0.0), (440, 480, 1.0)], gate=[(0, 438)], note="Gates up at 7:18."),
 "pizza":      dict(b="N8", name="LATE SLICE", sub="PIZZA  ·  CALZONE  ·  GARLIC KNOTS", awning=PINK, ink=CLOUD, neon=PINK, glow=(1.0, 0.85, 0.65),
                    lights=[(0, 242, 1.0), (242, 262, 0.35), (262, 480, 0.0)], gate=[(263, 480)], note="Last slice 4:00. Mop until 4:20. Gate down 4:23."),
 "diner":      dict(b="N9", name="CLOUD DINER", sub="BREAKFAST ALL DAY", awning=CLOUD, ink=INK, neon=CYAN, glow=(1.0, 0.93, 0.8),
                    lights=[(0, 285, 0.06), (285, 480, 1.0)], gate=[], note="Grill on at 4:45. Doors at 5:00."),
 "bar":        dict(b="S1", name="LAST CALL", sub="BEER  ·  SHOT  ·  POOL", awning=INK, ink=PINK, neon=PINK, glow=(1.0, 0.45, 0.35),
                    lights=[(0, 236, 0.8), (236, 258, 1.0), (258, 480, 0.0)], gate=[(262, 480)], note="Last call 3:40. House lights up 3:56. Out by 4:18."),
 "flowers":    dict(b="S2", name="PETAL & STEM", sub="FLOWERS  ·  PLANTS", awning=ACID, ink=INK, neon=ACID, glow=(0.95, 1.0, 0.85),
                    lights=[(0, 312, 0.05), (312, 480, 0.9)], gate=[(0, 312), ], note="Market van at 5:10. Buckets out by 6:30."),
 "bakery":     dict(b="S7", name="FIRST LIGHT BAKERY", sub="BREAD  ·  ROLLS  ·  COFFEE", awning=CLOUD, ink=PINK, neon=PINK, glow=(1.0, 0.82, 0.55),
                    lights=[(0, 198, 0.0), (198, 360, 0.55), (360, 480, 1.0)], gate=[(0, 358)], note="Ovens at 3:18. Gate up 5:58. Line by 7."),
 "locksmith":  dict(b="S8", name="KEYS 24 HR", sub="LOCKS  ·  KEYS  ·  SAFES", awning=INK, ink=ACID, neon=ACID, glow=(0.9, 1.0, 0.7),
                    lights=[(0, 480, 0.25)], gate=[(0, 480)], note="The sign says 24 hours. The gate says call the number."),
 "pharmacy":   dict(b="S9", name="CORNER RX", sub="PHARMACY  ·  PHOTO  ·  NOTARY", awning=CLOUD, ink=BLUE, neon=BLUE, glow=(0.85, 0.95, 1.0),
                    lights=[(0, 465, 0.08), (465, 480, 1.0)], gate=[(0, 462)], note="Opens at 8. Staff in at 7:42."),
}
# Gates that carry MLow's Open Eye Flowers: (which of his flowers, where along the gate 0..1, size as a share of gate height)
MURALS = {"bar": (1, 0.60, 1.0), "bakery": (2, 0.30, 0.82), "locksmith": (3, 0.70, 0.8)}
def shop_level(key, t):
    for a, b_, lv in SHOPS[key]["lights"]:
        if a <= t < b_ or (t >= NIGHT_END and b_ >= NIGHT_END): return lv
    return 0.0
def gate_down(key, t):
    return any(a <= t < b_ or (t >= NIGHT_END and b_ >= NIGHT_END) for a, b_ in SHOPS[key]["gate"])

# ------------------------------------------------------------------ windows and apartments
def bays(b):
    if b["kind"] == "brownstone": return 3
    if b["kind"] in ("garage", "garden"): return 0
    return max(3, int(round(b["w"] / 2.75)))

def windows(b):
    """Every street-facing apartment window: u is metres along the facade from its left end
    as you face it, z is the sill height. Brownstones keep a basement window and a parlour floor."""
    out = []; n = bays(b)
    if n == 0: return out
    pitch = b["w"] / n
    if b["kind"] == "brownstone":
        # bay 0 is the door bay on the parlour floor (the stoop lands there)
        for fl in range(b["floors"]):
            z = 1.6 + fl * FLOOR_H + 0.75
            for k in range(n):
                if fl == 0 and k == 0: continue
                out.append(dict(b=b["id"], fl=fl + 1, bay=k, u=(k + 0.5) * pitch, z=z, w=1.05, h=2.1 if fl == 0 else 1.75, unit="%s-%d" % (b["id"], fl + 1), room=("living", "living", "bedroom")[k]))
        out.append(dict(b=b["id"], fl=0, bay=1, u=1.5 * pitch, z=0.25, w=1.05, h=1.0, unit="%s-0" % b["id"], room="living"))
        out.append(dict(b=b["id"], fl=0, bay=2, u=2.5 * pitch, z=0.25, w=1.05, h=1.0, unit="%s-0" % b["id"], room="bedroom"))
        return out
    per = 2 if b["kind"] == "tenement" else 3                 # apartments per floor on the street side
    for fl in range(1, b["floors"]):
        z = GROUND_H + (fl - 1) * FLOOR_H + 0.85
        for k in range(n):
            apt = min(per - 1, k * per // n)
            first = (k == 0) or (min(per - 1, (k - 1) * per // n) != apt)
            room = "living" if first else ("bedroom" if (k + fl) % 2 else "kitchen")
            out.append(dict(b=b["id"], fl=fl + 1, bay=k, u=(k + 0.5) * pitch, z=z, w=1.1 if b["kind"] == "tenement" else 1.3, h=1.8,
                            unit="%s-%d%s" % (b["id"], fl + 1, "ABC"[apt]), room=room))
    return out

WINDOWS = [w for b in BUILDINGS for w in windows(b)]
for i, w in enumerate(WINDOWS): w["i"] = i
UNITS = {}
for w in WINDOWS: UNITS.setdefault(w["unit"], []).append(w)

# ------------------------------------------------------------------ residents
# Each archetype returns light intervals per room: (t0, t1, kind). kind is warm | cool | tv | dim | pink | blue.
# j() is a seeded jitter so two Students on the block do not keep the same hours.
rnd = random.Random(SEED)
def j(a, spread=12): return a + rnd.uniform(-spread, spread)

def A_asleep():      return dict(), "Asleep by 11. The windows stay dark until the alarm, which is after 8."
def A_owl():
    e = j(95, 40);   return dict(living=[(0, e, "warm")], bedroom=[(e - 3, e + j(18, 6), "dim")]), "Up late. Living room until %s, then the bedroom lamp for a while." % hm(e)
def A_tv():
    e = j(150, 60);  return dict(living=[(0, e, "tv")]), "Fell asleep in front of the television. It turns itself off at %s." % hm(e)
def A_insomniac():
    a = j(175, 30); b_ = a + j(55, 15); return dict(kitchen=[(a, b_, "cool")], living=[(a + 4, b_ - 6, "dim")], bedroom=[(a - 2, a + 1, "dim")]), "Wakes at %s, gives up, stands in the kitchen until %s." % (hm(a), hm(b_))
def A_parents():
    a = j(110, 25); c = j(275, 20); return dict(bedroom=[(a, a + 22, "dim"), (c, c + 31, "dim")], kitchen=[(a + 3, a + 9, "cool"), (c + 2, c + 8, "cool")], living=[(j(430, 10), 480, "warm")]), "New parents. Feeds at %s and %s. Nobody has slept." % (hm(a), hm(c))
def A_student():
    e = j(215, 35);  return dict(bedroom=[(0, e, "cool")]), "The Student. Desk lamp and a screen until %s. The paper is due at 9." % hm(e)
def A_nightshift():
    a = j(52, 10);   return dict(living=[(a, a + 38, "warm")], kitchen=[(a + 2, a + 20, "cool")], bedroom=[(a + 36, a + 50, "dim")]), "The Night Shift. Home at %s, eats standing up, bed by %s." % (hm(a), hm(a + 50))
def A_bartender():
    a = j(278, 8);   return dict(living=[(a, a + 44, "warm")], kitchen=[(a + 1, a + 12, "cool")]), "The Bartender. Counts out at LAST CALL, home at %s, cannot sleep until it is light." % hm(a)
def A_baker():
    a = j(170, 8);   return dict(bedroom=[(a, a + 9, "dim")], kitchen=[(a + 5, a + 21, "cool")]), "The Baker. Alarm at %s, out the door at %s, ovens on by 3:18." % (hm(a), hm(a + 21))
def A_nurse():
    a = j(318, 10);  return dict(bedroom=[(a, a + 12, "dim")], kitchen=[(a + 8, a + 34, "cool")], living=[(a + 20, a + 40, "warm")]), "The Nurse. Up at %s for the 7 o'clock handover." % hm(a)
def A_early():
    a = j(352, 22);  return dict(bedroom=[(a, a + 15, "dim")], kitchen=[(a + 10, 480, "warm")], living=[(a + 30, 480, "warm")]), "Early riser. Lights from %s. Coffee, radio, window." % hm(a)
def A_runner():
    a = j(330, 10);  return dict(bedroom=[(a, a + 14, "dim")], living=[(a + 10, a + 22, "warm"), (a + 75, a + 110, "warm")]), "The Runner. Up at %s, out at %s, back an hour later." % (hm(a), hm(a + 22))
def A_school():
    a = j(395, 14);  return dict(bedroom=[(a, a + 30, "warm")], kitchen=[(a + 4, 478, "warm")], living=[(a + 12, 474, "warm")]), "School morning. Everyone up at %s, out by 8." % hm(a)
def A_dj():
    a = j(205, 15);  return dict(living=[(0, 28, "pink"), (a, a + 70, "pink")], bedroom=[(a + 66, a + 80, "dim")]), "The DJ. Leaves at 12:28 with two bags, back at %s, still hearing it." % hm(a)
def A_gamer():
    e = j(290, 40);  return dict(bedroom=[(0, e, "blue")]), "The Gamer. Blue light until %s. Headphones, so nobody knows." % hm(e)
def A_oldcouple():
    a = j(300, 15);  return dict(kitchen=[(a, 480, "warm")], living=[(a + 25, 480, "warm")], bedroom=[(a - 250, a - 244, "dim")]), "Fifty one years in the same apartment. Kitchen light at %s, same as every day." % hm(a)
def A_super():
    return dict(living=[(298, 325, "warm"), (410, 422, "warm")], bedroom=[(294, 300, "dim")]), "The Super. Up at 4:54. Bags to the kerb at 5:15, hose at 7:00."
def A_empty():       return dict(), "Empty since September. A sign in the window gives a number."
def A_plant():       return dict(living=[(0, 480, "pink")]), "Nobody is awake. The grow light for the plants runs all night."
def A_sax():
    e = j(34, 8);    return dict(living=[(0, e + 25, "warm")], bedroom=[(e + 22, e + 40, "dim")]), "The Saxophonist. Practises with a towel in the bell until %s." % hm(e)
def A_cabbie():
    a = j(232, 12);  return dict(kitchen=[(a, a + 26, "cool")], bedroom=[(a - 6, a + 2, "dim")]), "The Cab Driver. Up at %s for the airport runs." % hm(a)
def A_writer():
    a = j(128, 20); b_ = j(318, 25); return dict(living=[(0, a, "dim"), (b_, b_ + 50, "dim")]), "The Writer. One lamp until %s. Then again at %s, because of one sentence." % (hm(a), hm(b_))
def A_lightsleeper():
    return dict(bedroom=[(338, 351, "dim")]), "The Light Sleeper. The garbage truck wakes them at 5:38. Every Wednesday."

ARCH = [("Asleep", A_asleep, 22), ("The Night Owl", A_owl, 9), ("The Television", A_tv, 7), ("The Insomniac", A_insomniac, 5), ("The New Parents", A_parents, 3),
        ("The Student", A_student, 4), ("The Night Shift", A_nightshift, 3), ("The Nurse", A_nurse, 3), ("The Early Riser", A_early, 9), ("The Runner", A_runner, 3),
        ("School Morning", A_school, 7), ("The Gamer", A_gamer, 3), ("The Old Couple", A_oldcouple, 3), ("Empty", A_empty, 3), ("The Grow Light", A_plant, 2),
        ("The Cab Driver", A_cabbie, 2), ("The Writer", A_writer, 2), ("The Light Sleeper", A_lightsleeper, 4)]
# people who must exist exactly once because the street needs them
FIXED = {"S1-3A": ("The Bartender", A_bartender), "S7-2A": ("The Baker", A_baker), "N6-2A": ("The Super", A_super),
         "N3-3": ("The Saxophonist", A_sax), "N9-4B": ("The DJ", A_dj), "S6-5B": ("The Night Shift", A_nightshift), "N5-0": ("The Old Couple", A_oldcouple)}

RESIDENTS = {}
_bag = [a for a in ARCH for _ in range(a[2])]
for unit in sorted(UNITS):
    if unit in FIXED: name, fn = FIXED[unit]
    else: name, fn, _ = rnd.choice(_bag)
    sched, line = fn()
    RESIDENTS[unit] = dict(unit=unit, who=name, line=line, sched=sched)

KIND_RGB = dict(warm=(1.0, 0.62, 0.30), cool=(0.80, 0.92, 1.0), tv=(0.45, 0.60, 1.0), dim=(1.0, 0.50, 0.20), pink=(1.0, 0.18, 0.388), blue=(0.161, 0.384, 1.0))
KIND_LVL = dict(warm=1.0, cool=0.9, tv=0.45, dim=0.35, pink=0.7, blue=0.5)

def window_light(w, t):
    """(kind, level) of one window at minute t, or None when dark."""
    sched = RESIDENTS[w["unit"]]["sched"].get(w["room"], ())
    for a, b_, kind in sched:
        if a <= t < b_ or (t >= NIGHT_END and b_ >= NIGHT_END):
            lvl = KIND_LVL[kind]
            if kind == "tv":                    # television flicker: deterministic, changes every few seconds
                lvl *= 0.55 + 0.45 * (math.sin(t * 37.0 + w["i"] * 1.7) * 0.5 + 0.5)
            return kind, lvl
    return None

# ------------------------------------------------------------------ weather and sky
RAIN = (132, 184)       # 2:12 to 3:04
def raining(t): return RAIN[0] <= t < RAIN[1]
def wetness(t):
    """0 dry .. 1 soaked. Dry at midnight, soaks during the rain, dries slowly, never fully before 8."""
    if t < RAIN[0]: return 0.0
    if t < RAIN[1]: return min(1.0, (t - RAIN[0]) / 14.0)
    return max(0.3, 1.0 - (t - RAIN[1]) / 420.0)

LAT, LON, TZ_MERIDIAN = 40.757, -73.99, -75.0
DOY = 322               # Nov 18
STREET_AZ = 119.0       # compass bearing of the street's east end
def sun(t):
    """Solar elevation and azimuth in degrees at minute t (EST), from the usual textbook approximation."""
    g = 2 * math.pi / 365.0 * (DOY - 1)
    decl = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    solar = t + eot + 4.0 * (LON - TZ_MERIDIAN)
    H = math.radians((solar - 720.0) / 4.0); lat = math.radians(LAT)
    el = math.asin(math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(H))
    az = math.degrees(math.atan2(math.sin(H), math.cos(H) * math.sin(lat) - math.tan(decl) * math.cos(lat))) + 180.0
    return math.degrees(el), az % 360.0
def sun_vector(t):
    """Unit vector pointing AT the sun in block coordinates."""
    el, az = sun(t); th = math.radians(STREET_AZ - az); e = math.radians(el)
    return (math.cos(th) * math.cos(e), math.sin(th) * math.cos(e), math.sin(e))
def _find(el_target):
    for t in range(240, 600):
        if sun(t)[0] >= el_target: return t
    return None
CIVIL_DAWN = _find(-6.0); SUNRISE = _find(-0.833); LAMPS_OFF = _find(-3.0)

def lerp(a, b_, f): return tuple(x + (y - x) * f for x, y in zip(a, b_))
def sky(t):
    """Horizon colour, zenith colour and strength for the world, from the sun's elevation.
    Night in the city is never black: a dull orange-violet glow sits on the horizon."""
    el = sun(t)[0]
    keys = [(-90, (0.060, 0.032, 0.030), (0.010, 0.011, 0.022), 1.0),
            (-12, (0.060, 0.032, 0.030), (0.010, 0.011, 0.022), 1.0),
            (-8,  (0.070, 0.040, 0.046), (0.013, 0.017, 0.040), 1.0),
            (-4,  (0.50, 0.20, 0.16),    (0.045, 0.075, 0.20),  1.0),
            (-1,  (1.6, 0.62, 0.30),     (0.16, 0.26, 0.55),    1.0),
            (3,   (2.6, 1.5, 0.85),      (0.30, 0.50, 0.95),    1.0),
            (12,  (2.2, 2.2, 2.2),       (0.35, 0.62, 1.25),    1.0),
            (90,  (2.2, 2.2, 2.2),       (0.35, 0.62, 1.25),    1.0)]
    for (e0, h0, z0, s0), (e1, h1, z1, s1) in zip(keys, keys[1:]):
        if e0 <= el <= e1:
            f = (el - e0) / (e1 - e0); f = f * f * (3 - 2 * f)
            return lerp(h0, h1, f), lerp(z0, z1, f), s0 + (s1 - s0) * f
    return keys[0][1], keys[0][2], 1.0
def sun_strength(t):
    el = sun(t)[0]
    if el <= -0.8: return 0.0
    return min(9.0, 0.4 + (el + 0.8) * 0.9)
def sun_colour(t):
    el = max(0.0, sun(t)[0]); f = min(1.0, el / 14.0)
    return lerp((1.0, 0.42, 0.16), (1.0, 0.86, 0.70), f)
def lamps_on(t): return t < LAMPS_OFF

# ------------------------------------------------------------------ street furniture (static)
LAMPS = [dict(x=x, side=s) for x, s in ((8, "N"), (40, "N"), (72, "N"), (24, "S"), (56, "S"), (88, "S"))]
TREES = [dict(x=x, side=s, h=h) for x, s, h in ((27.2, "N", 8.5), (33.8, "N", 7.2), (40.3, "N", 9.0), (52.0, "N", 7.8), (37.2, "S", 8.2), (43.8, "S", 9.4), (58.5, "S", 7.0), (28.0, "S", 10.5))]
HYDRANTS = [dict(x=19.5, side="N"), dict(x=66.0, side="S")]
# parked cars: slot centre x, side, colour, and the minute it leaves or arrives (None = all night)
CARS = []
_car_cols = [(0.02, 0.02, 0.025), (0.55, 0.57, 0.60), (0.75, 0.76, 0.78), (0.10, 0.12, 0.20), (0.30, 0.05, 0.05), (0.06, 0.16, 0.12), (0.62, 0.60, 0.52), (0.92, 0.92, 0.90)]
_r2 = random.Random(SEED + 1)
for side in "NS":
    x = 13.0
    while x < 86:
        if not (side == "N" and 17.5 < x < 22.5) and not (side == "S" and 63.5 < x < 69) and _r2.random() < 0.82:     # hydrants stay clear
            CARS.append(dict(x=x, side=side, col=_r2.choice(_car_cols), kind=_r2.choice(["sedan", "sedan", "suv", "van", "hatch"]), leave=None, arrive=None))
        x += _r2.uniform(5.6, 6.6)
for c, tt in zip([c for c in CARS if c["side"] == "N"][2::3], (351, 402, 446)): c["leave"] = tt
for c, tt in zip([c for c in CARS if c["side"] == "S"][1::3], (327, 418, 461)): c["leave"] = tt
[c for c in CARS if c["side"] == "S"][-1]["arrive"] = 74          # someone gets home at 1:14 and finds the last spot

# trash at the kerb: (x, side, bags, minute it appears). Each pile is gone when the garbage truck reaches it.
PILES = [(86, "N", 9, 0), (76, "N", 12, 0), (62, "S", 7, 0), (52, "N", 14, 318), (52.5, "S", 8, 0), (38, "N", 5, 0), (38.5, "S", 6, 0), (26, "N", 5, 0),
         (16, "N", 8, 0), (16.5, "S", 6, 0), (5, "S", 10, 0), (4.5, "N", 6, 0), (75.5, "S", 5, 0), (87, "S", 7, 0)]
def pile_gone(x):
    truck = [m for m in MOVERS if m["who"] == "The garbage truck"][0]
    for (t0, x0, _), (t1, x1, _) in zip(truck["keys"], truck["keys"][1:]):
        if x1 <= x <= x0 and x0 != x1: return t0 + (x0 - x) / (x0 - x1) * (t1 - t0) + 0.6
    return 345.0

def car_present(c, t):
    if c["arrive"] is not None and t < c["arrive"]: return False
    if c["leave"] is not None and t >= c["leave"]: return False
    return True

# ------------------------------------------------------------------ the night: everyone and everything that moves
# A mover has a kind, a name, a line for the log, and a path of (minute, x, y) keys. Between keys it moves in a
# straight line. Outside its first and last key it is not on the block.
NS, SS = 7.0, -7.0        # sidewalk centre lines
WEST, EAST = -14.0, 110.0 # off the ends of the block
MOVERS = []
def door(bid, frac=0.5):
    b = B[bid]; return b["x0"] + b["w"] * (frac if b["side"] == "N" else 1 - frac)
def side_y(bid, off=0.0): return (FAC - 0.6 - off) if B[bid]["side"] == "N" else -(FAC - 0.6 - off)
def mv(kind, who, line, keys, col=None, **kw):
    MOVERS.append(dict(kind=kind, who=who, line=line, keys=[(float(a), float(b_), float(c)) for a, b_, c in keys], col=col, **kw))
def walk(who, line, t0, pts, speed=78.0, kind="person", col=None, pause=None, **kw):
    """Walk through pts at speed (metres per minute). pause = {index: minutes} to stand at a point."""
    keys = [(t0, pts[0][0], pts[0][1])]; t = t0
    for i in range(1, len(pts)):
        d = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); t += d / speed
        keys.append((t, pts[i][0], pts[i][1]))
        if pause and i in pause: t += pause[i]; keys.append((t, pts[i][0], pts[i][1]))
    mv(kind, who, line, keys, col, **kw); return t
def drive(who, line, t0, stops=(), kind="car", col=None, y=0.0, speed=420.0, **kw):
    """Westbound through the block. stops = [(x, minutes)]."""
    keys = [(t0, EAST, y)]; t = t0; x = EAST
    for sx, mins in sorted(stops, reverse=True):
        t += (x - sx) / speed; keys.append((t, sx, y)); t += mins; keys.append((t, sx, y)); x = sx
    t += (x - WEST) / speed; keys.append((t, WEST, y))
    mv(kind, who, line, keys, col, **kw); return t

r3 = random.Random(SEED + 2)
COAT = [(0.05, 0.05, 0.06), (0.10, 0.12, 0.20), (0.30, 0.08, 0.06), (0.35, 0.33, 0.28), (0.08, 0.20, 0.14), (0.60, 0.58, 0.52), (0.161, 0.384, 1.0), (1.0, 0.18, 0.388), (0.843, 1.0, 0.122)]

# --- the named ones
walk("The Saxophonist's neighbour", "comes out on the stoop of 309 to see where the music is coming from, and goes back in.", 9, [(door("N3", 0.2), 8.2), (door("N3", 0.2), 6.6), (door("N3", 0.2), 8.2)], speed=20, pause={1: 3}, col=COAT[3])
walk("The DJ", "leaves 335 with two record bags and heads for the subway.", 28, [(door("N9"), 8.2), (door("N9"), 5.2), (92.5, -5.2), (92.5, -7.6)], col=COAT[7])
walk("The Night Shift", "comes up the subway stairs and walks home to Halcyon Court.", 44, [(92.5, -7.6), (92.5, SS), (door("S6"), SS), (door("S6"), -8.4)], col=COAT[1])
drive("A yellow cab", "drops someone at 304 and waits until the door closes.", 71, stops=[(door("S2"), 1.6)], kind="cab", col=(0.95, 0.66, 0.05), y=-1.2)
walk("The Rat", "crosses from the garden to the bags outside LATE SLICE. Nobody sees.", 125, [(30, -8.6), (34, -5.1), (71, 5.1), (76, 6.0)], speed=140, kind="rat")
walk("The Umbrella", "somebody under an umbrella, fast, east to west, north side.", 141, [(EAST, NS), (WEST, NS)], speed=95, col=COAT[0], umbrella=True)
walk("The Umbrella", "a second umbrella, slower, stops under the shed at The Meridian Arms to wait it out.", 149, [(EAST, NS - 0.4), (54, NS - 0.4), (54, NS - 0.4), (WEST, NS - 0.4)], speed=70, col=COAT[5], umbrella=True, pause={1: 31})
walk("The Baker", "locks the door of 326, walks eleven steps, unlocks the bakery from inside the gate.", 191, [(door("S7", 0.15), -8.4), (door("S7", 0.15), SS), (door("S7", 0.7), SS), (door("S7", 0.7), -8.4)], speed=40, col=COAT[5])
walk("The Bodega Cat", "leaves the window of BLUE EYE GROCERY, crosses the street without looking, sits on the garden wall.", 197, [(6.0, 8.3), (3.5, 5.2), (5.5, -5.2), (24.0, -7.4), (25.5, -8.3), (25.5, -8.3)], speed=24, kind="cat", pause={5: 58})
walk("The Bodega Cat", "walks back. The door is propped. Breakfast.", 263, [(25.5, -8.3), (22.0, -5.2), (8.0, 5.2), (6.0, 8.3)], speed=38, kind="cat")
# last call
for k in range(7):
    t0 = 236 + k * 5 + r3.uniform(0, 3); dest = r3.choice([(WEST, SS), (WEST, SS), (EAST, SS), (92.5, -7.6)])
    walk("Last call", ("two people leave LAST CALL and argue about which way the train is." if k == 2 else "someone leaves LAST CALL."), t0,
         [(door("S1", 0.3), -8.3), (door("S1", 0.3), SS + r3.uniform(-0.6, 0.6)), (dest[0], dest[1] + r3.uniform(-0.5, 0.5))], speed=r3.uniform(55, 80), col=r3.choice(COAT), pause={1: r3.uniform(0.5, 6)})
walk("The Bartender", "pulls the gate at LAST CALL, checks it twice, goes upstairs.", 262, [(door("S1", 0.3), -8.3), (door("S1", 0.3), SS), (door("S1", 0.85), SS), (door("S1", 0.85), -8.4)], speed=30, col=COAT[0], pause={1: 3.5})
walk("The Pizza Man", "drags the mats in, pulls the gate at LATE SLICE, lights a cigarette, walks east.", 259, [(door("N8"), 8.3), (door("N8"), NS), (door("N8"), NS), (EAST, NS)], speed=45, col=COAT[2], pause={1: 4, 2: 5})
walk("The Cab Driver", "walks to the avenue to pick up the cab.", 258, [(door("N2", 0.85), 8.3), (door("N2", 0.85), NS), (WEST, NS)], col=COAT[3])
drive("The bread flour truck", "backs up to FIRST LIGHT BAKERY. Twelve sacks.", 268, stops=[(door("S7", 0.6), 11)], kind="boxtruck", col=(0.85, 0.85, 0.82), y=-1.4)
walk("The Line Cook", "opens CLOUD DINER from the inside. The grill goes on.", 281, [(EAST, NS), (door("N9", 0.7), NS), (door("N9", 0.7), 8.3)], col=COAT[0])
drive("The newspaper van", "slows, throws three bundles at the door of BLUE EYE GROCERY, does not stop.", 296, stops=[(9, 0.4)], kind="van", col=(0.15, 0.15, 0.17), y=1.2)
walk("The Super", "brings the bags up from the cellar of The Meridian Arms and builds the pile at the kerb. Fourteen bags.", 315, [(door("N6", 0.12), 8.4), (door("N6", 0.12), 5.6), (door("N6", 0.12), 8.4), (door("N6", 0.12), 5.6), (door("N6", 0.12), 8.4)], speed=18, col=COAT[4], pause={1: 2, 3: 3})
drive("The flower market van", "double parks at PETAL & STEM. Buckets, boxes, one small tree.", 310, stops=[(door("S2"), 9)], kind="van", col=(0.90, 0.90, 0.88), y=-1.4)
drive("The garbage truck", "works the block west, both sides, stopping at every pile. Brakes, hopper, brakes.", 335, stops=[(86, 2.0), (76, 2.5), (62, 1.5), (52, 3.5), (38, 2.0), (26, 1.5), (16, 2.5), (5, 2.0)], kind="garbage", col=(0.93, 0.93, 0.90), y=0.6, speed=160)
walk("The Nurse", "leaves for the 7 o'clock handover.", 356, [(door("S9", 0.2), -8.4), (door("S9", 0.2), SS), (92.5, SS), (92.5, -7.6)], col=COAT[6])
walk("The Runner", "out of Halcyon Court, checks a watch, goes west.", 352, [(door("S6"), -8.4), (door("S6"), -5.6), (WEST, -5.6)], speed=190, col=COAT[8])
walk("The Runner", "comes back the other way, slower.", 428, [(WEST, -5.6), (door("S6"), -5.6), (door("S6"), -8.4)], speed=150, col=COAT[8])
walk("The Dog Walker", "three dogs, one of them in charge. Stops at every tree on the north side.", 392, [(WEST, NS - 1.4), (27.2, NS - 1.4), (33.8, NS - 1.4), (40.3, NS - 1.4), (52.0, NS - 1.4), (EAST, NS - 1.4)], speed=60, col=COAT[1], dogs=3, pause={1: 1.2, 2: 0.8, 3: 1.5, 4: 1.0})
walk("The Super", "hoses the sidewalk in front of The Meridian Arms, east to west, the way it has always been done.", 420, [(door("N6", 0.95), 6.8), (door("N6", 0.05), 6.8), (door("N6", 0.12), 8.4)], speed=1.1, col=COAT[4], hose=True)
drive("The street sweeper", "comes through with its brushes down. Two cars have not moved.", 452, stops=[(60, 0.3)], kind="sweeper", col=(0.92, 0.92, 0.9), y=2.4, speed=180)
drive("The school bus", "stops at Halcyon Court. Lights flash. Four children.", 458, stops=[(door("S6"), 2.2)], kind="bus", col=(0.95, 0.62, 0.04), y=-1.0, speed=300)
walk("The Mechanic", "rolls up both gates at 317 FLAT FIX and drags the tire rack out.", 436, [(WEST, NS), (door("N7", 0.3), NS), (door("N7", 0.3), 8.3)], col=COAT[0])
walk("The Pharmacist", "arrives at CORNER RX with coffee from the diner.", 458, [(door("N9", 0.7), 8.3), (door("N9", 0.7), 5.2), (door("S9", 0.6), -5.2), (door("S9", 0.6), -8.3)], col=COAT[5])
# the bakery line, 6:55 on
for k in range(6):
    t0 = 404 + k * 9 + r3.uniform(0, 5); frm = r3.choice([(WEST, SS), (EAST, SS), (92.5, -7.6)])
    walk("Bakery line", "someone joins the line at FIRST LIGHT BAKERY.", t0, [frm, (door("S7", 0.7) + 1.0 + (k % 4) * 0.8, -7.9), (door("S7", 0.7), -8.4)], col=r3.choice(COAT), pause={1: r3.uniform(3, 7)})
# --- the unnamed ones: background foot traffic and cars, thin in the middle of the night, thick by 8
def density(t):    # people per minute crossing the block
    return 0.30 * math.exp(-t / 70.0) + 0.012 + 0.55 * max(0.0, (t - 330) / 150.0) ** 2
t = 2.0
while t < NIGHT_END:
    t += r3.expovariate(density(t))
    if t >= NIGHT_END: break
    side = r3.choice((NS, SS)) + r3.uniform(-1.2, 1.2); east = r3.random() < 0.5
    walk("Passer-by", None, t, [(WEST, side), (EAST, side)] if east else [(EAST, side), (WEST, side)], speed=r3.uniform(62, 96), col=r3.choice(COAT))
def cars_per_min(t): return 0.22 * math.exp(-t / 90.0) + 0.03 + 0.5 * max(0.0, (t - 320) / 160.0) ** 2
t = 1.0
while t < NIGHT_END:
    t += r3.expovariate(cars_per_min(t))
    if t >= NIGHT_END: break
    cab = r3.random() < (0.5 if t < 300 else 0.25)
    drive("A yellow cab" if cab else "A car", None, t, kind="cab" if cab else "car", col=(0.95, 0.66, 0.05) if cab else r3.choice(_car_cols), y=r3.uniform(-0.6, 0.6), speed=r3.uniform(380, 520))
# parked cars that leave become a driver walking out and a car pulling away (the car object itself is in CARS)
for c in CARS:
    if c["leave"] is not None:
        y = 3.9 if c["side"] == "N" else -3.9
        mv("note", "A parked car", "pulls out from the %s side. The spot is taken in four minutes." % ("north" if c["side"] == "N" else "south"), [(c["leave"], c["x"], y), (c["leave"] + 0.3, c["x"], y)])
# --- people who stand still for a while (added at 17:25 on the day of the shift, after the film had started: they are not in the film)
def stand(who, line, t0, mins, x, y, col, **kw): mv("person", who, line, [(t0, x, y), (t0 + mins, x + 0.01, y)], col, **kw)
for k, (t0, mins) in enumerate(((11, 9), (64, 11), (119, 8), (187, 7))):
    stand("Two smokers", "stand outside LAST CALL. One of them is telling the long version." if k == 0 else None, t0, mins, door("S1", 0.3) + 0.9, -7.6, COAT[0])
    stand("Two smokers", None, t0 + 0.4, mins - 0.8, door("S1", 0.3) + 1.6, -7.9, COAT[2])
stand("Someone on the stoop of 312", "sits on the stoop with a phone, saying yes, no, yes.", 50, 36, door("S4", 0.2) + 0.3, -6.3, COAT[6])
stand("A delivery rider", "waits outside LATE SLICE with the engine of the bike still ticking.", 101, 11, door("N8") - 1.2, 6.1, COAT[8])
stand("Someone with a suitcase", "waits outside The Meridian Arms for a car to the airport. It comes.", 352, 9, door("N6") + 1.5, 5.9, COAT[5])
stand("The Line Cook", "stands outside CLOUD DINER for exactly one cigarette.", 381, 6, door("N9", 0.7) + 1.4, 7.4, COAT[0])
for k in range(4):
    stand("Four children", "wait for the bus outside Halcyon Court. One has forgotten something." if k == 0 else None, 446 + k * 1.5, 14.2 - k * 1.5, door("S6") - 1.2 + k * 0.7, -6.0 - (k % 2) * 0.5, COAT[(k * 2 + 6) % 9], small=True)
stand("A parent", None, 446, 14.6, door("S6") + 1.9, -6.4, COAT[3])
MOVERS.sort(key=lambda m: m["keys"][0][0])

def mover_at(m, t):
    """(x, y, heading_x, heading_y, moving) or None if this mover is not on the block at minute t."""
    k = m["keys"]
    if t < k[0][0] or t > k[-1][0]: return None
    for (t0, x0, y0), (t1, x1, y1) in zip(k, k[1:]):
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            dx, dy = x1 - x0, y1 - y0; d = math.hypot(dx, dy)
            return (x0 + dx * f, y0 + dy * f, (dx / d if d else 0.0), (dy / d if d else 0.0), d > 0)
    return None

# ------------------------------------------------------------------ signals
def signal(t):
    """The light facing traffic on 317th at the west corner: 'G', 'Y' or 'R'. 90 second cycle."""
    s = (t * 60.0) % 90.0
    return "G" if s < 32 else ("Y" if s < 35 else "R")

# ------------------------------------------------------------------ the log
def night_log():
    rows = []
    for m in MOVERS:
        if m["line"]: rows.append((m["keys"][0][0], "%s %s" % (m["who"], m["line"])))
    for key, s in SHOPS.items():
        prev = shop_level(key, 0)
        for a, b_, lv in s["lights"][1:]:
            rows.append((a, "%s: %s" % (s["name"], "lights out." if lv == 0 else ("lights down." if lv < prev else "lights on."))) ); prev = lv
        for a, b_ in s["gate"]:
            if a > 0: rows.append((a, "%s: the gate comes down." % s["name"]))
            if b_ < NIGHT_END: rows.append((b_, "%s: the gate goes up." % s["name"]))
    rows.append((RAIN[0], "It starts to rain.")); rows.append((RAIN[1], "The rain stops. The street keeps it."))
    rows.append((CIVIL_DAWN, "First grey in the east. The sky is a colour again.")); rows.append((LAMPS_OFF, "The street lights go off, all six at once."))
    rows.append((SUNRISE, "Sunrise, somewhere behind the avenue.")); rows.append((NIGHT_END, "Eight o'clock. The sun is %.0f degrees up and almost straight down the street." % sun(NIGHT_END)[0]))
    for u, r in RESIDENTS.items():
        ons = sorted(a for room in r["sched"].values() for a, b_, k in room if a > 0)
        if ons and r["who"] not in ("Asleep",): rows.append((ons[0], "%s, %s: a light goes on." % (r["who"], u.replace("-", " apt "))))
    rows.sort(key=lambda r: r[0]); return rows

def lit_count(t): return sum(1 for w in WINDOWS if window_light(w, t))

def export():
    here = os.path.dirname(os.path.abspath(__file__))
    data = dict(seed=SEED, date=DATE, L=L, road=ROAD, walk=WALK, ground_h=GROUND_H, floor_h=FLOOR_H,
                buildings=[dict(b, height=height(b), bays=bays(b)) for b in BUILDINGS], shops=SHOPS, windows=WINDOWS,
                residents=RESIDENTS, kind_rgb=KIND_RGB, kind_lvl=KIND_LVL, rain=RAIN, lamps=LAMPS, trees=TREES, murals=MURALS, piles=[dict(x=x, side=s, n=n, appear=a, gone=round(pile_gone(x), 2)) for x, s, n, a in PILES], hydrants=HYDRANTS, cars=CARS,
                movers=MOVERS, civil_dawn=CIVIL_DAWN, sunrise=SUNRISE, lamps_off=LAMPS_OFF,
                sun=[[round(v, 2) for v in sun(t)] for t in range(0, 481)], sky=[[[round(c, 4) for c in col] for col in sky(t)[:2]] for t in range(0, 481)],
                log=[[round(t, 2), s] for t, s in night_log()])
    json.dump(data, open(os.path.join(here, "block.json"), "w"), separators=(",", ":"))
    with open(os.path.join(here, "RESIDENTS.md"), "w") as f:
        f.write("# West 317th Street: who lives behind each window\n\nWritten by `block.py`, seed 317. %d street-facing windows, %d apartments. Nobody here is a real person.\n\n" % (len(WINDOWS), len(UNITS)))
        for b in BUILDINGS:
            us = sorted(u for u in UNITS if u.startswith(b["id"] + "-"))
            f.write("## %s  (%s, %s side)\n\n" % (b["name"], b["id"], "north" if b["side"] == "N" else "south"))
            if b["shop"]: s = SHOPS[b["shop"]]; f.write("Ground floor: **%s**. %s\n\n" % (s["name"], s["note"]))
            if not us: f.write("No apartments.\n\n"); continue
            for u in us: r = RESIDENTS[u]; f.write("- **%s** · %s · %d window%s. %s\n" % (u.split("-")[1], r["who"], len(UNITS[u]), "" if len(UNITS[u]) == 1 else "s", r["line"]))
            f.write("\n")
    with open(os.path.join(here, "NIGHT_LOG.md"), "w") as f:
        f.write("# West 317th Street, %s, midnight to 8 a.m.\n\nWritten by `block.py`. Every line is something the generator schedules; the renders and the web page read the same schedule.\n\n" % DATE)
        f.write("Rain %s to %s. First light %s. Street lights off %s. Sunrise %s.\n\n" % (hm(RAIN[0]), hm(RAIN[1]), hm(CIVIL_DAWN), hm(LAMPS_OFF), hm(SUNRISE)))
        hour = -1
        for t, s in night_log():
            if int(t // 60) != hour and t < 480: hour = int(t // 60); f.write("\n## %d a.m.  (%d windows lit on the hour)\n\n" % (hour if hour else 12, lit_count(hour * 60)))
            f.write("- %s  %s\n" % (hm(t), s))
    return data

if __name__ == "__main__":
    d = export()
    print("windows", len(WINDOWS), "apartments", len(UNITS), "movers", len(MOVERS), "log lines", len(d["log"]))
    print("civil dawn", hm(CIVIL_DAWN), "lamps off", hm(LAMPS_OFF), "sunrise", hm(SUNRISE), "sun at 8:00", [round(v, 1) for v in sun(480)])
    print("lit windows by hour", [lit_count(h * 60) for h in range(9)])
