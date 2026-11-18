#!/bin/bash
# tools/queue.sh   the rest of the shift's GPU work, one Blender at a time (21:00).
# Takes turns with tools/checkpoint.sh through a lock file: it never starts while a checkpoint render runs, and holds
# /private/tmp/claude-501/unsupervised-shift/render.lock while it renders so the checkpoint waits for it.
F="$(cd "$(dirname "$0")/.." && pwd)"; L=/private/tmp/claude-501/unsupervised-shift; LOCK=$L/render.lock
export TMPDIR=$L/tmp/; cd /private/tmp; B=/Applications/Blender.app/Contents/MacOS/Blender
free_pct() { memory_pressure | awk -F": " '/free percentage/ {gsub("%","",$2); print int($2)}'; }
turn() { while pgrep -f "unsupervised-shift/hourly/hour_0" >/dev/null || [ "$(free_pct)" -lt 15 ]; do sleep 15; done; touch $LOCK; }
done_() { rm -f $LOCK; }
still() {   # still T CAM NAME
  [ -f "$F/stills/$3.png" ] && return; turn
  PYTHONDONTWRITEBYTECODE=1 $B --background --factory-startup --python "$F/build_block.py" -- --t $1 --cam $2 --res 1620x2025 --samples 160 --out $L/stills/$3.png 2>&1 | grep -E "^rendered|rror"
  cp $L/stills/$3.png "$F/stills/"; done_; echo "still $3 $(date +%H:%M:%S)"
}
mkdir -p $L/stills
still 03:17:27 canyon west-317th-street_0317_the-cat-crosses
still 04:40 witness west-317th-street_0440_the-witness
still 07:13 canyon west-317th-street_0713_sun-in-the-slot
# the canyon film's last 98 minutes, with the generator as filmed, eight frames a run
a=383
while [ $a -le 480 ]; do
  b=$((a + 7)); [ $b -gt 480 ] && b=480; turn
  PYTHONDONTWRITEBYTECODE=1 $B --background --factory-startup --python $L/v1/build_block.py -- --film $a $b 1 --cam canyon --res 1080x1350 --samples 40 --out $L/frames 2>&1 | grep -E "^rendered|rror"
  done_; a=$((b + 1))
done
echo "queue done $(date +%H:%M:%S)"
