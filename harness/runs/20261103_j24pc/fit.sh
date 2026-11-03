#!/bin/bash
# J24 fit driver: fit.sh <tag> "<key=val ...>" [yaw|shots|both]   one launch: land_small, the J8 yaw sweep (capture per yaw), the shot poses
# (capture + shot each), then siege_small at its own deploy pose (capture + shot); keys set with the game closed; PROFILE=<name> applies a
# watcher profile first (j8-shadow-q4 for quality 4). Run from the repo root; outputs under harness/runs/20261103_j24pc/raw/<tag>/.
set -u
TAG=$1; KEYS=$2; WHAT=${3:-both}
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
S='C:\napoleon_remastered_pc'
J=core/harness/job.sh
O=j24
OUT=harness/runs/20261103_j24pc/raw/$TAG; mkdir -p $OUT
ALL="gfx.shadow_map_large=0 gfx.shadow_far_cap=0 gfx.shadow_extrusion=0 gfx.shadow_crop_keep=0 gfx.shadow_fit_ortho=0 gfx.shadow_height_cutoff=0 gfx.shadow_hw_force=0 ${EXTRA_OFF:-}"
echo "== $TAG keys: $KEYS ($WHAT) $(date -u +%H:%M:%SZ)"
for t in $(seq 1 60); do $J status 2>/dev/null | grep -q '"profile_active":  null' && break; sleep 2; done
python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=1 "dev.capture_dir=C:\\napoleon_remastered_pc\\captures" $ALL $KEYS > $OUT/set.txt 2>&1 || { echo "set failed"; cat $OUT/set.txt; exit 2; }
grep -E '^shadow_' "$G/napoleon_remastered.ini" | tr '\n' ' ' > $OUT/keys.txt; echo "ini: $(cat $OUT/keys.txt)"
$J lock $O 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 "J24 fit $TAG" >/dev/null 2>&1
[ -n "${PROFILE:-}" ] && { echo "profile $PROFILE" | $J $O - 120 2>&1 | tail -1; }
ctl() { python3 core/harness/ctl.py --owner $O --out $OUT "$@"; }
cap() { $J touch >/dev/null 2>&1; $J ctl $O "capture j24_${TAG}_$1 1" > $OUT/$1_capture.txt 2>&1 || echo "capture $1 failed: $(tail -c 200 $OUT/$1_capture.txt)"; }
ctl scene land_small > $OUT/scene_land.json 2>&1; rc=$?; echo "scene land rc $rc"
if [ $rc -ne 0 ]; then   # no scene: stop this launch here (a failed launch must not burn 170 s per capture)
  echo kill | $J $O - 120 > /dev/null 2>&1; cp "$G/napoleon_remastered/logs/proxy.log" $OUT/proxy.log 2>/dev/null; $J unlock $O >/dev/null 2>&1
  echo "== $TAG FAILED (scene) $(date -u +%H:%M:%SZ)"; exit 1
fi
if [ "$WHAT" != shots ]; then
  for y in 0 45 90 135 180 225 270 315; do ctl cam -0.08 59.02 446.14 $y -25 > $OUT/y_${y}_cam.json 2>&1; cap y_$y; done
fi
if [ "$WHAT" != yaw ]; then
  i=0
  IFS=';' read -ra PL <<< "${POSES:--0.08 18.2 285 0 -12;-0.08 18.2 300 90 -10;-0.08 18.2 285 45 -12;-0.08 18.2 340 180 -12;-0.08 59.02 446.14 180 -25;-0.08 59.31 525.65 180 -20}"
  for p in "${PL[@]}"; do
    i=$((i+1)); ctl cam $p > $OUT/p${i}_cam.json 2>&1; cap p$i; ctl shot j24_${TAG}_p$i > $OUT/p${i}_shot.json 2>&1
  done
  ctl perf 10 > $OUT/perf_land.json 2>&1
  ctl scene siege_small > $OUT/scene_siege.json 2>&1; echo "scene siege rc $?"
  cap s1; ctl shot j24_${TAG}_s1 > $OUT/s1_shot.json 2>&1
fi
echo kill | $J $O - 120 > /dev/null 2>&1; echo "kill rc $?"
cp "$G/napoleon_remastered/logs/proxy.log" $OUT/proxy.log 2>/dev/null
grep -E 'shadow\.' $OUT/proxy.log | cut -c1-160 > $OUT/sites.txt; echo "sites: $(grep -c 'key off' $OUT/sites.txt) key off of $(wc -l < $OUT/sites.txt)"
$J unlock $O >/dev/null 2>&1
echo "== $TAG done $(date -u +%H:%M:%SZ)"
