#!/bin/bash
# J24 shots sitting (after ladder.sh): the fixed poses before and after, one launch per setting: stock, 8192, the proposed release
# (8192 + height cutoff 200 + extrusion -150) on build e876198be89a, then 4096 and 4096 + cutoff + extrusion on the 4096 kit.
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'
K4=kit_20261103T032438Z_ab5896f8453d
until grep -q 'ladder end' harness/runs/20261103_j24pc/logs/ladder.log; do sleep 10; done
export EXTRA_OFF="gfx.shadow_focus=0 gfx.shadow_near_scale=0"
F=harness/runs/20261103_j24pc/fit.sh
bash $F f3_stock "" shots
bash $F f3_8k "gfx.shadow_map_large=1" shots
bash $F f3_rel "gfx.shadow_map_large=1 gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1" both
python3 core/proxy/tools/pc_deploy.py install --kit "$S/kits/$K4" --game "$G" --state "$S" 2>&1 | tail -1
bash $F f3_4k "gfx.shadow_map_large=1" shots
bash $F f3_4k_rel "gfx.shadow_map_large=1 gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1" shots
echo "== shots end $(date -u +%H:%M:%SZ)"
