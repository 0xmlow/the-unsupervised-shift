#!/bin/bash
# tools/chunks.sh GEN A B STEP CHUNK OUTDIR [extra args]   film frames in short fresh Blender runs.
# Added 20:50: three Cycles jobs on this 24 GB Mac stall each other (GPU memory cannot swap). Each chunk is a new
# process, so memory never builds up, and a chunk only starts when the Mac has room for it. Existing frames are skipped.
GEN=$1; A=$2; B=$3; STEP=$4; CH=$5; OUT=$6; shift 6
export TMPDIR=/private/tmp/claude-501/unsupervised-shift/tmp/; cd /private/tmp
free_pct() { memory_pressure | awk -F": " "/free percentage/ {gsub(\"%\",\"\",\$2); print int(\$2)}"; }
a=$A
while [ $(echo "$a <= $B" | bc) = 1 ]; do
  b=$(echo "$a + $STEP * ($CH - 1)" | bc); [ $(echo "$b > $B" | bc) = 1 ] && b=$B
  while [ "$(free_pct)" -lt 15 ]; do sleep 20; done
  PYTHONDONTWRITEBYTECODE=1 /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python "$GEN" -- --film $a $b $STEP --out "$OUT" "$@" 2>&1 | grep -E "^rendered|rror" 
  a=$(echo "$b + $STEP" | bc)
done
echo "chunks done $(date +%H:%M:%S)"
