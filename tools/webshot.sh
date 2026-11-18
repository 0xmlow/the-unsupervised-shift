#!/bin/bash
# tools/webshot.sh "t=03:17" out.png [width height]    screenshot of index.html in headless Chrome
F="$(cd "$(dirname "$0")/.." && pwd)"; export TMPDIR="/private/tmp/claude-501/unsupervised-shift/tmp/"
W=${3:-1440}; H=${4:-900}
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="/private/tmp/claude-501/unsupervised-shift/tmp/chrome" --window-size=$W,$H --virtual-time-budget=1500 \
  --screenshot="$2" "file://$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$F/index.html")?$1" 2>&1 | grep -iE "error|written" | head -5
