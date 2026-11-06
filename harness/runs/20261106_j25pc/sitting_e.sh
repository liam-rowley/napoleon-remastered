#!/bin/bash
# J25 sitting e: the 2048 shot sets (control, cascade 0), then the cost blocks. Same kit for both arms, the prototype key off and on, set with the game closed.
# Arms interleave control, prototype, control, prototype (2 blocks of 2 repeats), all 1080p first, then all 4K, so the virtual display changes size once.
# Both arms run with J24's release values on, and neither with a capture or the draw counters. Stops at the first failure. Never edit while it runs.
set -u
D=harness/runs/20261106_j25pc/cas.sh
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'
SW='dev.cascade_dir=C:\napoleon_remastered_pc\_scratch\j25\swap'
ON="dev.cascade_proto=1 dev.cascade_count=1 dev.cascade_tint=0 dev.cascade_skip_ps= dev.cascade_split=40 $SW"
bash $D e_ctl2k "dev.cascade_proto=0 dev.cascade_skip_ps= gfx.shadow_map_large=0" poses || exit 1
bash $D e_on2k "$ON gfx.shadow_map_large=0" poses || exit 1
bash $D e_tint2k "dev.cascade_proto=1 dev.cascade_count=1 dev.cascade_tint=1 dev.cascade_skip_ps= dev.cascade_split=40 $SW gfx.shadow_map_large=0" poses || exit 1
M="python3 tools/perf_baseline.py measure --owner j25 --session 96a223bd-8ffd-4e4f-946a-17aeee2548ad --backends dxvk --repeats 2 --deploy-end-s 0"
setk() { python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=0 dev.cascade_count=0 dev.cascade_tint=0 dev.cascade_skip_ps= dev.cascade_split=40 gfx.shadow_map_large=1 "$SW" "$@" 2>&1 | tail -1; }
arm() {   # arm <id> <proto 0|1> <measure args...>
  id=$1; p=$2; shift 2
  echo "== arm $id proto=$p $(date -u +%H:%M:%SZ)"
  setk dev.cascade_proto=$p || exit 1
  $M --run 20261106_j25cost_$id "$@" 2>&1 | tail -2 | cut -c1-200
  rc=${PIPESTATUS[0]}; [ "$rc" = 0 ] || { echo "arm $id failed rc $rc"; exit 1; }
}
A1="--sizes 1920x1080 --scenarios land_40,hist_dresden"
A4="--sizes 3840x2160 --scenarios land_40"
arm 1080_ctl1 0 $A1; arm 1080_pro1 1 $A1; arm 1080_ctl2 0 $A1; arm 1080_pro2 1 $A1
arm 4k_ctl1 0 $A4; arm 4k_pro1 1 $A4; arm 4k_ctl2 0 $A4; arm 4k_pro2 1 $A4
echo "== sitting e complete $(date -u +%H:%M:%SZ)"
