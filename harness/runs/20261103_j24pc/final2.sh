#!/bin/bash
# J24: the 20-pass run again after final.sh (its pass 10 failed at a launch: HEADLESS FAILED at DllMain twice in ctl.py's retry, the
# pre-existing launch flake also seen with every key off and in J8, J23, J44 and J46 runs). Release values on, same build 75739186b92e.
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'
OFF="gfx.shadow_map_large=0 gfx.shadow_far_cap=0 gfx.shadow_extrusion=0 gfx.shadow_crop_keep=0 gfx.shadow_fit_ortho=0 gfx.shadow_height_cutoff=0 gfx.shadow_hw_force=0 gfx.shadow_focus=0 gfx.shadow_near_scale=0"
REL="gfx.shadow_map_large=1 gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1"
until grep -q '== final end' harness/runs/20261103_j24pc/logs/final.log; do sleep 10; done
python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=0 $OFF $REL 2>&1 | tail -1
grep -E '^shadow_' "$G/napoleon_remastered.ini" | tr '\n' ' '; echo
echo "== acceptance2 $(date -u +%H:%M:%SZ)"
python3 core/harness/acceptance.py run --owner j24 --session 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 --branch job/J24 --passes 20 --run 20261103_j24acc2 2>&1 | tail -6
echo "== final2 end $(date -u +%H:%M:%SZ)"
