#!/bin/bash
# J24 fit sweep, sitting 2: kit with the trapezoid focus and near-scale sites (build e876198be89a), the two new controls and combinations.
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'; K=kit_20261103T035945Z_354011cb0fc6
until grep -q 'sweep end' harness/runs/20261103_j24pc/logs/fitsweep.log; do sleep 10; done
python3 core/proxy/tools/pc_deploy.py send --kit build/kits/$K --state "$S" 2>&1 | tail -1
python3 core/proxy/tools/pc_deploy.py install --kit "$S/kits/$K" --game "$G" --state "$S" 2>&1 | tail -1
export EXTRA_OFF="gfx.shadow_focus=0 gfx.shadow_near_scale=0"
F=harness/runs/20261103_j24pc/fit.sh
bash $F f2_stock ""
bash $F f2_focus "gfx.shadow_focus=1"
bash $F f2_nears "gfx.shadow_near_scale=1"
bash $F f2_cutextr "gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1"
bash $F f2_cutextr_focus "gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1 gfx.shadow_focus=1"
echo "== sweep2 end $(date -u +%H:%M:%SZ)"
