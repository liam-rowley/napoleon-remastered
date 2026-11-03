#!/bin/bash
# J24 map-size ladder (one sitting): the hardware-path rerun, then perf_baseline.py measure per step at 1080p and 4K on land_small,
# siege_small, hist_dresden: control (every key off), 8192 at quality 3, 8192 at quality 4 (watcher profile j8-shadow-q4), 4096 (its own kit).
# Run from the repo root after fitsweep2.sh. Never edit this file while it runs (bash reads it as it goes).
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'; J=core/harness/job.sh
K2=kit_20261103T035945Z_354011cb0fc6; K4=kit_20261103T032438Z_ab5896f8453d
OFF="gfx.shadow_map_large=0 gfx.shadow_far_cap=0 gfx.shadow_extrusion=0 gfx.shadow_crop_keep=0 gfx.shadow_fit_ortho=0 gfx.shadow_height_cutoff=0 gfx.shadow_hw_force=0 gfx.shadow_focus=0 gfx.shadow_near_scale=0"
M="python3 tools/perf_baseline.py measure --owner j24 --session 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 --backends dxvk --sizes 1920x1080,3840x2160 --scenarios land_small,siege_small,hist_dresden --repeats 2"
until grep -q 'sweep2 end' harness/runs/20261103_j24pc/logs/fitsweep2.log; do sleep 10; done
export EXTRA_OFF="gfx.shadow_focus=0 gfx.shadow_near_scale=0"
bash harness/runs/20261103_j24pc/fit.sh f_hw2 "gfx.shadow_hw_force=1" yaw
setk() { python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=0 $OFF "$@" 2>&1 | tail -1; }
echo "== control $(date -u +%H:%M:%SZ)"; setk; $M --run 20261103_j24ladder_ctl 2>&1 | tail -3
echo "== 8192 q3 $(date -u +%H:%M:%SZ)"; setk gfx.shadow_map_large=1; $M --run 20261103_j24ladder_8k 2>&1 | tail -3
echo "== 8192 q4 $(date -u +%H:%M:%SZ)"; setk gfx.shadow_map_large=1
$J lock j24 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 "J24 ladder q4" >/dev/null 2>&1; echo "profile j8-shadow-q4" | $J j24 - 120 2>&1 | tail -1
$M --run 20261103_j24ladder_8k_q4 2>&1 | tail -3
for t in $(seq 1 90); do $J status 2>/dev/null | grep -q '"profile_active":  null' && break; sleep 2; done
echo "== 4096 q3 $(date -u +%H:%M:%SZ)"
[ -d "/c/napoleon_remastered_pc/kits/$K4" ] || python3 core/proxy/tools/pc_deploy.py send --kit build/kits/$K4 --state "$S" 2>&1 | tail -1
python3 core/proxy/tools/pc_deploy.py install --kit "$S/kits/$K4" --game "$G" --state "$S" 2>&1 | tail -1
setk gfx.shadow_map_large=1; $M --run 20261103_j24ladder_4k 2>&1 | tail -3
echo "== back to $K2 $(date -u +%H:%M:%SZ)"
python3 core/proxy/tools/pc_deploy.py install --kit "$S/kits/$K2" --game "$G" --state "$S" 2>&1 | tail -1
setk
echo "== ladder end $(date -u +%H:%M:%SZ)"
