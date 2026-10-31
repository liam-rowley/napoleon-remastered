#!/usr/bin/env bash
# J50 probe sequence: probe_run.sh <tag> [pack]   (pack = marker|real|dds; empty = no pack). Run from the worktree root.
tag=$1; pk=${2:-}
R=upscale/runs/2026-10-31_j50/raw
S=/c/napoleon_remastered_pc/_scratch/j50
st() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(sys.argv[2], d.get('status'), d.get('reason','')[:200])" "$1" "$2" 2>/dev/null || echo "$2 unreadable"; }
bash harness/core/job.sh touch >/dev/null
if [ -n "$pk" ]; then bash harness/core/job.sh J50 "$S/s2_${pk}_in.ps1" 300 | grep -E '"reason"|\[job'; fi
python3 harness/core/ctl.py --owner J50 --out $R scene land_small > $R/${tag}_land_scene.json 2>&1; st $R/${tag}_land_scene.json land_scene
python3 -c "import json;d=json.load(open('$R/${tag}_land_scene.json'));print('  launch', (d.get('path') or {}).get('launch',{}).get('retried_after'), d.get('evidence',{}).get('ctl',{}).get('launch_id'))"
python3 harness/core/ctl.py --owner J50 --out $R shot ${tag}_land > $R/${tag}_land_shot.json 2>&1; st $R/${tag}_land_shot.json land_shot
bash harness/core/job.sh ctl J50 'reset frontend 120' 150 > $R/${tag}_reset.json 2>&1; st $R/${tag}_reset.json reset_frontend
bash harness/core/shot.sh J50 $R/${tag}_frontend.jpg 2>&1 | tail -1
bash harness/core/job.sh touch >/dev/null
python3 harness/core/ctl.py --owner J50 --out $R scene campaign_start > $R/${tag}_campaign_scene.json 2>&1; st $R/${tag}_campaign_scene.json campaign_scene
python3 harness/core/ctl.py --owner J50 --out $R shot ${tag}_campaign > $R/${tag}_campaign_shot.json 2>&1; st $R/${tag}_campaign_shot.json campaign_shot
echo "kill owner=J50" | bash harness/core/job.sh J50 - 120 | tail -1
if [ -n "$pk" ]; then bash harness/core/job.sh J50 "$S/s2_${pk}_out.ps1" 300 | grep -E '"reason"|\[job'; fi
ls "/c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War/napoleon_remastered/dumps"
bash harness/core/job.sh touch
