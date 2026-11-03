#!/bin/bash
# J24 final sitting on the final build (75739186b92e, kit kit_20261103T063744Z_6bab276b0030): install, idle check (one acceptance pass
# with every shadow key off), the 20-pass acceptance run with the release values on, then perf at the release values against a
# same-sitting control (land_small, siege_small, hist_dresden, land_40 at 1080p and 4K). Run from the repo root; never edit while it runs.
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'; S='C:\napoleon_remastered_pc'; K=kit_20261103T063744Z_6bab276b0030
OFF="gfx.shadow_map_large=0 gfx.shadow_far_cap=0 gfx.shadow_extrusion=0 gfx.shadow_crop_keep=0 gfx.shadow_fit_ortho=0 gfx.shadow_height_cutoff=0 gfx.shadow_hw_force=0 gfx.shadow_focus=0 gfx.shadow_near_scale=0"
REL="gfx.shadow_map_large=1 gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1"
setk() { python3 core/proxy/tools/pc_deploy.py set --game "$G" --state "$S" dev.capture=0 $OFF "$@" 2>&1 | tail -1; grep -E '^shadow_' "$G/napoleon_remastered.ini" | tr '\n' ' '; echo; }
A="python3 core/harness/acceptance.py run --owner j24 --session 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 --branch job/J24"
M="python3 tools/perf_baseline.py measure --owner j24 --session 7463a92f-8bda-4a7f-a9ae-7f4b6fbe7a80 --backends dxvk --sizes 1920x1080,3840x2160 --scenarios land_small,siege_small,hist_dresden,land_40 --repeats 2"
python3 core/proxy/tools/pc_deploy.py send --kit build/kits/$K --state "$S" 2>&1 | tail -1
python3 core/proxy/tools/pc_deploy.py install --kit "$S/kits/$K" --game "$G" --state "$S" 2>&1 | tail -1
echo "== idle $(date -u +%H:%M:%SZ)"; setk; $A --passes 1 --run 20261103_j24idle 2>&1 | tail -4
echo "== acceptance $(date -u +%H:%M:%SZ)"; setk $REL; $A --passes 20 --run 20261103_j24acc 2>&1 | tail -6
echo "== perf control $(date -u +%H:%M:%SZ)"; setk; $M --run 20261103_j24rel_ctl 2>&1 | tail -2
echo "== perf release $(date -u +%H:%M:%SZ)"; setk $REL; $M --run 20261103_j24rel 2>&1 | tail -2
echo "== final end $(date -u +%H:%M:%SZ)"
