#!/bin/sh
# ./shoot.sh --t 03:17 --cam canyon --res 810x1012 --samples 48 --out stills/x.png
F="$(cd "$(dirname "$0")" && pwd)"; export TMPDIR="/private/tmp/claude-501/unsupervised-shift/tmp/"; mkdir -p "$TMPDIR"; cd "$F"
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python "$F/build_block.py" -- "$@" 2>&1 | grep -E "Error|Traceback|line [0-9]+|Exception|FAILED|not set|built:|rendered|saved|done|glare|font" | grep -v DeprecationWarning
