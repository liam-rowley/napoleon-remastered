#!/bin/bash
# J25 sitting d: real shadows on, the yaw sweeps at stock map size (control, then the three splits), the question 6 skip test last.
# Stops at the first launch that fails: the kill criterion is a crash twice for one cause, so nothing relaunches blindly. Never edit while it runs.
set -u
D=harness/runs/20261106_j25pc/cas.sh
SW='dev.cascade_dir=C:\napoleon_remastered_pc\_scratch\j25\swap'
ON="dev.cascade_proto=1 dev.cascade_count=1 dev.cascade_tint=0 $SW"
bash $D d_on "$ON dev.cascade_split=40 gfx.shadow_map_large=1" poses || exit 1
bash $D y_ctl "dev.cascade_proto=0 gfx.shadow_map_large=0" yaw || exit 1
bash $D y_s25 "$ON dev.cascade_split=25 gfx.shadow_map_large=0" yaw || exit 1
bash $D y_s40 "$ON dev.cascade_split=40 gfx.shadow_map_large=0" yaw || exit 1
bash $D y_s60 "$ON dev.cascade_split=60 gfx.shadow_map_large=0" yaw || exit 1
bash $D d_skip "$ON dev.cascade_split=40 gfx.shadow_map_large=1 dev.cascade_skip_ps=5c9bd7a4bb31b068" poses || exit 1
echo "== sitting d complete $(date -u +%H:%M:%SZ)"
