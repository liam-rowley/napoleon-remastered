#!/bin/bash
# J25 prototype driver: cas.sh <tag> "<keys>" [poses|yaw|both]   one launch on the installed prototype kit. poses: land_40 deploy and turned, land_small
# J24's p1..p6, siege_small s1 (a capture and a shot at each); yaw: the J8 sweep on land_small (a capture per yaw). Keys are set with the game closed,
# the dev.cascade_* keys are in the installed kit ini, which is what pc_deploy set checks. Run from the repo root.
# Never edit this file while it runs (J24 incident). Stops at a failed scene. Outputs under harness/runs/20261106_j25pc/raw/<tag>/.
set -u
TAG=$1; KEYS=$2; WHAT=${3:-poses}
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
S='C:\napoleon_remastered_pc'
J=core/harness/job.sh
O=j25
export WSC_SESSION_ID=96a223bd-8ffd-4e4f-946a-17aeee2548ad
OUT=harness/runs/20261106_j25pc/raw/$TAG; mkdir -p "$OUT"
echo "== $TAG keys: $KEYS ($WHAT) $(date -u +%H:%M:%SZ)"
python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=1 "dev.capture_dir=C:\\napoleon_remastered_pc\\captures" dev.skip_intro=1 $KEYS > "$OUT/set.txt" 2>&1 || { echo "set failed"; cat "$OUT/set.txt"; exit 2; }
$J lock $O $WSC_SESSION_ID "J25 $TAG" > "$OUT/lock.txt" 2>&1 || { echo "lock failed"; cat "$OUT/lock.txt"; exit 3; }
ctl() { python3 core/harness/ctl.py --owner $O --session $WSC_SESSION_ID --out "$OUT" "$@"; }
cap() { $J touch $O > /dev/null 2>&1; $J ctl $O "capture j25_${TAG}_$1 1" > "$OUT/$1_capture.txt" 2>&1 || echo "capture $1 failed: $(tail -c 200 "$OUT/$1_capture.txt")"; }
stop() { echo kill | $J $O - 120 > /dev/null 2>&1; echo "kill rc $?"; cp "$G/napoleon_remastered/logs/proxy.log" "$OUT/proxy.log" 2>/dev/null; grep -E '^(err|warn):' "$G/napoleon_remastered/dxvk/Napoleon_d3d9.log" | sort | uniq -c > "$OUT/dxvk_errors.txt" 2>&1; $J unlock $O > /dev/null 2>&1; echo "== $TAG end $1 $(date -u +%H:%M:%SZ)"; }
scene() { ctl scene "$1" > "$OUT/scene_$1.json" 2>&1; rc=$?; echo "scene $1 rc $rc"; if [ $rc -ne 0 ]; then tail -c 500 "$OUT/scene_$1.json"; echo; stop FAILED; exit 1; fi; }
pose() { ctl cam $2 > "$OUT/$1_cam.json" 2>&1; cap "$1"; ctl shot "j25_${TAG}_$1" > "$OUT/$1_shot.json" 2>&1; }

if [ "$WHAT" != yaw ]; then
  scene land_40
  pose l40_deploy "-0.08 61.39 451.38 179.91 -25"
  pose l40_turned "-0.08 61.39 451.38 -120.09 -25"
fi
scene land_small
if [ "$WHAT" != poses ]; then
  for y in 0 45 90 135 180 225 270 315; do ctl cam -0.08 59.02 446.14 $y -25 > "$OUT/y_${y}_cam.json" 2>&1; cap y_$y; done
fi
if [ "$WHAT" != yaw ]; then
  pose p1 "-0.08 18.2 285 0 -12"
  pose p2 "-0.08 18.2 300 90 -10"
  pose p3 "-0.08 18.2 285 45 -12"
  pose p4 "-0.08 18.2 340 180 -12"
  pose p5 "-0.08 59.02 446.14 180 -25"
  pose p6 "-0.08 59.31 525.65 180 -20"
  ctl perf 10 > "$OUT/perf_land.json" 2>&1
  scene siege_small
  cap s1; ctl shot "j25_${TAG}_s1" > "$OUT/s1_shot.json" 2>&1
fi
stop ok
