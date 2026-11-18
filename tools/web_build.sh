#!/bin/bash
# tools/web_build.sh BAKE_DIR SITE_DIR   (Nov 18, for the walkable block)
# The bake (tools/web_bake.py) -> the walk's assets: encoded lightmaps (4096 and 2048 for phones), lean GLBs, the cast,
# block.json and scene.json with the scales. SITE_DIR already holds index.html, walk.js and vendor/.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"; BAKE="$1"; SITE="$2"; A="$SITE/assets"
B=/Applications/Blender.app/Contents/MacOS/Blender
G=/Volumes/mlow2026/Claude/Projects/ARCHITECT/mlow-airport-v3/web/tools/node_modules/.bin/gltf-transform
CAST="/Users/degens/Desktop/NEW YORKERS BY MLOW/UPGRADE ALL ROOMS 2026-10-28/rig/out"
mkdir -p "$A/lm" "$A/lm2k" "$A/props" "$A/cars" "$A/cast"
"$B" -b --factory-startup --python "$HERE/tools/web_encode.py" -- "$BAKE" "$BAKE/enc" 2>&1 | grep -E "SCALE|ENCODED|Error|Traceback" || true
python3 - "$BAKE/enc" "$A" <<'PY'
import sys, os, glob
from PIL import Image
src, a = sys.argv[1:]
for p in sorted(glob.glob(os.path.join(src, 'png', '*.png'))):
    n = os.path.basename(p)[:-4]; im = Image.open(p).convert('RGB')
    im.save(os.path.join(a, 'lm', n + '.jpg'), quality=86, subsampling=0, optimize=True)
    im.resize((max(256, im.width // 2), max(256, im.height // 2)), Image.LANCZOS).save(os.path.join(a, 'lm2k', n + '.jpg'), quality=84, optimize=True)
    print('jpg', n, im.size)
PY
python3 - "$BAKE/scene.json" "$BAKE/enc/scales.json" "$A/scene.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s['scales'] = json.load(open(sys.argv[2])); json.dump(s, open(sys.argv[3], 'w'), separators=(',', ':'))
PY
cp "$HERE/block.json" "$A/block.json"
"$G" meshopt "$BAKE/street.glb" "$A/street.glb" --level medium >/dev/null
[ -f "$BAKE/silhouettes.glb" ] && "$G" meshopt "$BAKE/silhouettes.glb" "$A/silhouettes.glb" --level medium >/dev/null
lean() { "$G" resize "$1" /tmp/claude-501/_l1.glb --width "$3" --height "$3" >/dev/null && "$G" webp /tmp/claude-501/_l1.glb /tmp/claude-501/_l2.glb --quality 82 >/dev/null && "$G" meshopt /tmp/claude-501/_l2.glb "$2" --level medium >/dev/null; }
# props: the more copies on the street, the fewer triangles each (1,232 copies drew 3.7 million triangles a frame)
python3 - "$BAKE" > /tmp/claude-501/_ratios.txt <<'PY'
import json, struct, sys, os
b = sys.argv[1]; s = json.load(open(os.path.join(b, 'scene.json')))
for p in s['props']:
    f = os.path.join(b, 'props', p['mesh'] + '.glb'); d = open(f, 'rb').read(); n = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + n])
    tris = sum(j['accessors'][pr['indices']]['count'] // 3 for m in j['meshes'] for pr in m['primitives'] if 'indices' in pr)
    k = len(p['inst']); target = 350 if k > 40 else 900 if k > 8 else 2500
    print(p['mesh'], min(1.0, round(target / max(1, tris), 4)))
PY
while read m r; do
  f="$BAKE/props/$m.glb"
  if [ "$r" != "1.0" ]; then "$G" simplify "$f" /tmp/claude-501/_s.glb --ratio "$r" --error 0.02 >/dev/null; lean /tmp/claude-501/_s.glb "$A/props/$m.glb" 512; else lean "$f" "$A/props/$m.glb" 1024; fi
done < /tmp/claude-501/_ratios.txt
for f in "$BAKE"/cars/*.glb; do lean "$f" "$A/cars/$(basename "$f")" 1024; done
python3 - "$A/scene.json" "$CAST" "$A/cast" <<'PY'
import json, sys, shutil, os
s, src, dst = sys.argv[1:]; names = {m['cast'] for m in json.load(open(s))['movers'] if m.get('cast')}
for n in sorted(names): shutil.copy2(os.path.join(src, n + '.glb'), os.path.join(dst, n + '.glb'))
print('cast', len(names), sorted(names))
PY
rm -f /tmp/claude-501/_l1.glb /tmp/claude-501/_l2.glb
du -sh "$A"/* | sort -h; du -sh "$A"
