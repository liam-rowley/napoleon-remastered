#!/bin/bash
# J25 stock capture driver: cap.sh <tag>   one launch on the installed kit: land_40 at deploy and turned, land_small at the deploy pose and the
# yaw-0 sweep pose, siege_small at its deploy pose; a 2-frame capture and a shot at each. Keys are set with the game closed. Run from the repo root.
# Never edit this file while it runs (J24 incident: bash reads it as it goes). Outputs under harness/runs/20261106_j25pc/raw/<tag>/.
set -u
TAG=$1
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
S='C:\napoleon_remastered_pc'
J=core/harness/job.sh
O=j25
export WSC_SESSION_ID=96a223bd-8ffd-4e4f-946a-17aeee2548ad
OUT=harness/runs/20261106_j25pc/raw/$TAG; mkdir -p "$OUT"
echo "== $TAG $(date -u +%H:%M:%SZ)"
python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=1 "dev.capture_dir=C:\\napoleon_remastered_pc\\captures" dev.skip_intro=1 ${KEYS:-} > "$OUT/set.txt" 2>&1 || { echo "set failed"; cat "$OUT/set.txt"; exit 2; }
$J lock $O $WSC_SESSION_ID "J25 capture $TAG" > "$OUT/lock.txt" 2>&1 || { echo "lock failed"; cat "$OUT/lock.txt"; exit 3; }
ctl() { python3 core/harness/ctl.py --owner $O --session $WSC_SESSION_ID --out "$OUT" "$@"; }
cap() { $J touch $O > /dev/null 2>&1; $J ctl $O "capture j25_${TAG}_$1 2" > "$OUT/$1_capture.txt" 2>&1 || echo "capture $1 failed: $(tail -c 200 "$OUT/$1_capture.txt")"; }
stop() { echo kill | $J $O - 120 > /dev/null 2>&1; echo "kill rc $?"; cp "$G/napoleon_remastered/logs/proxy.log" "$OUT/proxy.log" 2>/dev/null; $J unlock $O > /dev/null 2>&1; echo "== $TAG end $1 $(date -u +%H:%M:%SZ)"; }
scene() { ctl scene "$1" > "$OUT/scene_$1.json" 2>&1; rc=$?; echo "scene $1 rc $rc"; if [ $rc -ne 0 ]; then tail -c 400 "$OUT/scene_$1.json"; stop FAILED; exit 1; fi; }

scene land_40
ctl cam -0.08 61.39 451.38 179.91 -25 > "$OUT/l40_deploy_cam.json" 2>&1; cap l40_deploy; ctl shot j25_${TAG}_l40_deploy > "$OUT/l40_deploy_shot.json" 2>&1
ctl cam -0.08 61.39 451.38 -120.09 -25 > "$OUT/l40_turned_cam.json" 2>&1; cap l40_turned; ctl shot j25_${TAG}_l40_turned > "$OUT/l40_turned_shot.json" 2>&1
scene land_small
ctl cam -0.08 59.02 446.14 180 -25 > "$OUT/ls_deploy_cam.json" 2>&1; cap ls_deploy; ctl shot j25_${TAG}_ls_deploy > "$OUT/ls_deploy_shot.json" 2>&1
ctl cam -0.08 59.02 446.14 0 -25 > "$OUT/ls_y0_cam.json" 2>&1; cap ls_y0
scene siege_small
cap s1; ctl shot j25_${TAG}_s1 > "$OUT/s1_shot.json" 2>&1
stop ok
