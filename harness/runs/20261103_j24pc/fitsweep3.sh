#!/bin/bash
# J24 fit sweep, sitting 2 continued after f2_focus failed to launch (HEADLESS FAILED at DllMain, 04:10Z): retry focus once, then the rest.
export EXTRA_OFF="gfx.shadow_focus=0 gfx.shadow_near_scale=0"
F=harness/runs/20261103_j24pc/fit.sh
mv harness/runs/20261103_j24pc/raw/f2_focus harness/runs/20261103_j24pc/raw/f2_focus_fail1
bash $F f2_focus "gfx.shadow_focus=1"
bash $F f2_nears "gfx.shadow_near_scale=1"
bash $F f2_cutextr "gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1"
bash $F f2_cutextr_crop "gfx.shadow_height_cutoff=1 gfx.shadow_extrusion=1 gfx.shadow_crop_keep=1"
echo "== sweep2 end $(date -u +%H:%M:%SZ)" | tee -a harness/runs/20261103_j24pc/logs/fitsweep2.log
