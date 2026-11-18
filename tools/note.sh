#!/bin/bash
# tools/note.sh "Title" < body     appends a notebook entry stamped with the real time and the block's time
F="$(cd "$(dirname "$0")/.." && pwd)"
now=$(date +%s); start=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-11-17 16:57:26" +%s); el=$(( now - start ))
bt=$(printf "%02d:%02d" $(( el / 3600 )) $(( (el % 3600) / 60 )))
{ printf "## %s  (%s on the block)  %s\n\n" "$(date +%H:%M)" "$bt" "$1"; cat; printf "\n"; } >> "$F/NOTEBOOK.md"
echo "noted $(date +%H:%M) / block $bt"
