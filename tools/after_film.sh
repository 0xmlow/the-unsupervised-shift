#!/bin/bash
# tools/after_film.sh   waits for the canyon film frames, encodes the MP4 with sound, then renders the ten shop portraits.
F="$(cd "$(dirname "$0")/.." && pwd)"; export TMPDIR="$F/_tmp/"; FF=/Users/degens/bin/ffmpeg
while pgrep -f "film 0 480 1 --cam canyon" > /dev/null; do sleep 20; done
n=$(ls "$F/film/frames" | grep -c "^f_"); echo "frames: $n"
cd "$F/film/frames" && $FF -y -loglevel error -framerate 24 -pattern_type glob -i 'f_*.png' -i "$F/sound/night_20s.wav" \
  -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=2.5,format=yuv420p[v];[1:a]apad=pad_dur=2.6[a]" -map "[v]" -map "[a]" -c:v libx264 -crf 16 -preset slow -c:a aac -b:a 192k -shortest -movflags +faststart \
  "$F/the-unsupervised-shift_one-night_20s.mp4" && echo "mp4 written"
cd "$F"
for spec in "grocery 03:30" "laundromat 00:40" "pizza 03:50" "diner 05:30" "bar 01:30" "flowers 06:35" "bakery 07:12" "locksmith 02:40" "pharmacy 07:50" "garage 07:40"; do set -- $spec
  "$F/shoot.sh" --t $2 --cam shop:$1 --res 1620x1080 --samples 96 --out "shops/${1}_${2/:/}.png" | grep -E "rendered|rror"; done
echo "after_film done $(date +%H:%M:%S)"
