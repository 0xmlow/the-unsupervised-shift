#!/bin/bash
# tools/shops.sh   one portrait of every shopfront, each at an hour that suits it
F="$(cd "$(dirname "$0")/.." && pwd)"; mkdir -p "$F/shops"
for spec in "grocery 03:30" "laundromat 00:40" "garage 07:40" "pizza 03:50" "diner 05:40" "bar 01:30" "flowers 06:35" "bakery 07:12" "locksmith 02:30" "pharmacy 07:50"; do set -- $spec
  "$F/shoot.sh" --t $2 --cam shop:$1 --res 1500x1000 --samples 64 --out "shops/$1_${2/:/}.png" | grep -E "rendered|rror|line"; done
