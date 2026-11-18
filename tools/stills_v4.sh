#!/bin/bash
# 04:26 Nov 18: the three finals with the CC0 base-mesh people, the patchy wet road, half the neon spill, the slatted mural, the new cat. The previous finals are kept as _v3.
F="/Volumes/mlow2026/100 ART EXPERIMENTS 2026-11-17/53-the-unsupervised-shift"; L=/private/tmp/claude-501/unsupervised-shift; B=/Applications/Blender.app/Contents/MacOS/Blender
mkdir -p $L/stills4; touch $L/render.lock
one() {
  [ -f "$F/stills/$3_v3.png" ] || cp "$F/stills/$3.png" "$F/stills/$3_v3.png"
  [ -f "$F/stills/$3_lens.png" ] && [ ! -f "$F/stills/$3_lens_v3.png" ] && cp "$F/stills/$3_lens.png" "$F/stills/$3_lens_v3.png"
  PYTHONDONTWRITEBYTECODE=1 $B --background --factory-startup --python "$F/build_block.py" -- --t $1 --cam $2 --res 1620x2025 --samples 160 --out $L/stills4/$3.png 2>&1 | grep -E "^rendered|rror"
  python3 "$F/tools/lens.py" $L/stills4/$3.png $L/stills4/$3_lens.png
  cp $L/stills4/$3.png $L/stills4/$3_lens.png "$F/stills/"; echo "still $3 $(date +%H:%M:%S)"
}
one 07:13 canyon west-317th-street_0713_sun-in-the-slot
one 03:17:27 canyon west-317th-street_0317_the-cat-crosses
one 04:40 witness west-317th-street_0440_the-witness
rm -f $L/render.lock; echo "all done $(date +%H:%M:%S)"
