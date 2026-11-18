#!/bin/bash
# tools/queue2.sh   after tools/queue.sh: the canyon film again, this time with the realism layer (21:05).
# Every two block minutes, 810x1012, 32 samples, eight frames a run, same lock and memory gate as queue.sh.
F="$(cd "$(dirname "$0")/.." && pwd)"; L=/private/tmp/claude-501/unsupervised-shift; LOCK=$L/render.lock; OUT=$L/frames_v2
export TMPDIR=$L/tmp/; cd /private/tmp; B=/Applications/Blender.app/Contents/MacOS/Blender; mkdir -p $OUT
while pgrep -f "tools/queue.sh" >/dev/null; do sleep 20; done
cp "$F/build_block.py" "$F/realism.py" "$F/block.py" $L/v2/ 2>/dev/null || { mkdir -p $L/v2 && cp "$F/build_block.py" "$F/realism.py" "$F/block.py" $L/v2/; }
ln -sfn "$F/assets" $L/v2/assets; ln -sfn "$F/../_style" $L/_style 2>/dev/null
free_pct() { memory_pressure | awk -F": " '/free percentage/ {gsub("%","",$2); print int($2)}'; }
turn() { while pgrep -f "unsupervised-shift/hourly/hour_0" >/dev/null || [ "$(free_pct)" -lt 15 ]; do sleep 15; done; touch $LOCK; }
a=0
while [ $a -le 480 ]; do
  b=$((a + 14)); [ $b -gt 480 ] && b=480; turn
  PYTHONDONTWRITEBYTECODE=1 $B --background --factory-startup --python $L/v2/build_block.py -- --film $a $b 2 --cam canyon --res 810x1012 --samples 32 --out $OUT 2>&1 | grep -E "^rendered|rror"
  rm -f $LOCK; a=$((b + 2))
done
echo "film v2 done $(date +%H:%M:%S)"
