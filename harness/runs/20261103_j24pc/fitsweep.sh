#!/bin/bash
# J24 fit sweep, sitting 1: one control at a time against stock, each one fit.sh launch (yaw sweep + shot poses + siege). Run from the repo root.
F=harness/runs/20261103_j24pc/fit.sh
bash $F f_stock ""
bash $F f_crop "gfx.shadow_crop_keep=1"
bash $F f_ortho "gfx.shadow_fit_ortho=1"
bash $F f_cutoff "gfx.shadow_height_cutoff=1"
bash $F f_extr "gfx.shadow_extrusion=1"
bash $F f_far "gfx.shadow_far_cap=1"
bash $F f_8k "gfx.shadow_map_large=1"
bash $F f_8k_crop "gfx.shadow_map_large=1 gfx.shadow_crop_keep=1"
bash $F f_hw "gfx.shadow_hw_force=1"
echo "== sweep end $(date -u +%H:%M:%SZ)"
