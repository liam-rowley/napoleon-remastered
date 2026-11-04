#!/bin/bash
# J24: the 20-pass run on build 75739186b92e (kit kit_20261103T063744Z_6bab276b0030) with the release keys on, after the tests-gate fix.
# Up to three runs (acc3, acc4, acc5): a new run starts only when the previous one broke on the hist_nile headless-launch flake
# (HEADLESS FAILED: DllMain exit or no on_virtual); any other failure stops. Never edit while it runs.
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'; K=kit_20261103T063744Z_6bab276b0030
OFF="gfx.shadow_map_large=0 gfx.shadow_far_cap=0 gfx.shadow_extrusion=0 gfx.shadow_crop_keep=0 gfx.shadow_fit_ortho=0 gfx.shadow_height_cutoff=0 gfx.shadow_hw_force=0 gfx.shadow_focus=0 gfx.shadow_near_scale=0"
REL="gfx.shadow_map_large=1 gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1"
python3 core/proxy/tools/pc_deploy.py install --kit "$S/kits/$K" --game "$G" --state "$S" 2>&1 | tail -2
python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=0 $OFF $REL 2>&1 | tail -1
grep -E '^shadow_' "$G/napoleon_remastered.ini" | tr '\n' ' '; echo
for R in 20261103_j24acc3 20261103_j24acc4 20261103_j24acc5; do
  echo "== $R $(date -u +%H:%M:%SZ)"
  python3 core/harness/acceptance.py run --owner j24 --session 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 --branch job/J24 --passes 20 --run $R > harness/runs/20261103_j24pc/logs/$R.log 2>&1
  tail -3 harness/runs/20261103_j24pc/logs/$R.log | cut -c1-400
  grep -q 'stopped at the first failure' harness/runs/20261103_j24pc/logs/$R.log || { echo "== $R complete"; break; }
  grep 'stopped at the first failure' harness/runs/20261103_j24pc/logs/$R.log | grep -q 'HEADLESS FAILED' || { echo "== $R stopped on another cause"; break; }
done
echo "== final3 end $(date -u +%H:%M:%SZ)"
