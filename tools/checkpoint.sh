#!/bin/bash
# tools/checkpoint.sh N [wait]   hourly checkpoint N (1..8): the block at N a.m., rendered with the generator as it stands right now.
# Renders to the Mac's internal disk first and copies the finished set to the drive (the drive dropped once under load).
F="$(cd "$(dirname "$0")/.." && pwd)"; N=$1; D="$F/hourly/hour_0$N"; L="/private/tmp/claude-501/unsupervised-shift/hourly/hour_0$N"; mkdir -p "$D" "$L"
export TMPDIR="/private/tmp/claude-501/unsupervised-shift/tmp/"
if [ "$2" = "wait" ]; then
  target=$(( $(date -j -f "%Y-%m-%d %H:%M:%S" "2026-11-17 16:57:26" +%s) + N * 3600 )); now=$(date +%s); [ $target -gt $now ] && sleep $(( target - now ))
fi
# 21:05: wait while tools/queue.sh holds the render lock, so two of my Cycles jobs never run at once
while [ -f /private/tmp/claude-501/unsupervised-shift/render.lock ]; do sleep 10; done
T=$(printf "%02d:00" $N); echo "checkpoint $N started $(date +%H:%M:%S)"
cd "$F" && PYTHONDONTWRITEBYTECODE=1 python3 block.py > /dev/null && PYTHONDONTWRITEBYTECODE=1 python3 build_web.py > /dev/null
"$F/shoot.sh" --t $T --cam canyon --res 810x1012 --samples 48 --out "$L/canyon_${N}am.png" | grep -E "rendered|rror"
"$F/shoot.sh" --t $T --cam elevN --res 2400x660 --samples 32 --out "$L/north_side_${N}am.png" | grep -E "rendered|rror"
"$F/shoot.sh" --t $T --cam elevS --res 2400x660 --samples 32 --out "$L/south_side_${N}am.png" | grep -E "rendered|rror"
"$F/tools/webshot.sh" "t=$T" "$L/web_${N}am.png" | grep written
/Users/degens/bin/ffmpeg -y -loglevel error -i "$L/canyon_${N}am.png" -q:v 3 "$L/checkpoint.jpg"
cp "$L"/* "$D/"; cp "$F/build_block.py" "$D/build_block_at_hour_$N.py"; cp "$F/block.py" "$D/block_at_hour_$N.py"
echo "checkpoint $N done at $(date +%H:%M:%S)"
