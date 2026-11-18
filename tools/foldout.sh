#!/bin/bash
# tools/foldout.sh [step]   the second film: both sides of the street as flat elevations, north side on top,
# south side upside down underneath, the way the web page lays them out. Renders two frame sets and stacks them.
F="$(cd "$(dirname "$0")/.." && pwd)"; export TMPDIR="$F/_tmp/"; FF=/Users/degens/bin/ffmpeg; STEP=${1:-1}
"$F/shoot.sh" --film 0 480 $STEP --cam elevN --res 1920x528 --samples 32 --out "$F/film/frames_north" | tail -1
"$F/shoot.sh" --film 0 480 $STEP --cam elevS --res 1920x528 --samples 32 --out "$F/film/frames_south" | tail -1
FPS=$(python3 -c "print(24 / $STEP if $STEP <= 1 else 12)")
$FF -y -loglevel error -framerate $FPS -pattern_type glob -i "$F/film/frames_north/f_*.png" -framerate $FPS -pattern_type glob -i "$F/film/frames_south/f_*.png" -i "$F/sound/night_20s.wav" \
  -filter_complex "[1:v]hflip,vflip[s];[0:v]pad=1920:552:0:0:color=0x0D0D0D[n];[n][s]vstack,tpad=stop_mode=clone:stop_duration=2.5,format=yuv420p[v];[2:a]apad=pad_dur=2.6[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 16 -preset slow -c:a aac -b:a 192k -shortest -movflags +faststart "$F/the-unsupervised-shift_both-sides_20s.mp4" && echo "foldout mp4 written $(date +%H:%M:%S)"
