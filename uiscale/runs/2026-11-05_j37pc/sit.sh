#!/bin/bash
# J37 PC sitting: one resolution/pack matrix cell per call. Usage: sit.sh <label> <adapter.json>
#   label: v1080 | v4k | x2_4k.  The adapter (ctl.launch.size, dev.log_files=1, dev.file_rules) is a scratch copy of harness/napoleon/adapter.json.
# Scenes: land_small deploy + turned, naval_small deploy, siege_small deploy, front end, campaign_start (settle by the harness). One shot each,
# the file survey (files.log) and proxy.log copied after the last scene of each game launch; the game is killed at the end.
set -u
cd "$(dirname "$0")/../../.."
LABEL=$1; AD=$2
OWNER=j37
J=core/harness/job.sh
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
GB='/c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War'
SCR=$(bash $J scratch $OWNER)/$LABEL
OUT=uiscale/runs/2026-11-05_j37pc/raw/$LABEL
mkdir -p "$SCR/shots" "$OUT"
C() { python3 core/harness/ctl.py --adapter "$AD" --owner $OWNER --out "$SCR/shots" "$@" > "$OUT/ctl_$(echo "$*" | tr ' /:=' '____').json" 2>&1; echo "ctl $* rc $?: $(tail -c 160 "$OUT/ctl_$(echo "$*" | tr ' /:=' '____').json" | tr -d '\n' | cut -c1-160)"; }
grab() { cp "$GB/napoleon_remastered/logs/files.log" "$OUT/files_$1.log" 2>/dev/null; cp "$GB/napoleon_remastered/logs/proxy.log" "$OUT/proxy_$1.log" 2>/dev/null; }
echo "== $LABEL $(date -u +%H:%M:%SZ)"
C scene land_small
C cam land_small:deploy;  C shot land_deploy
C cam land_small:turned;  C shot land_turned
grab land
C scene naval_small;      C cam naval_small:deploy; C shot naval_deploy
C scene siege_small;      C cam siege_small:deploy; C shot siege_deploy
grab battles
C reset;                  C shot frontend
grab frontend
C scene campaign_start;   C shot campaign
grab campaign
C state
ls "$SCR/shots" > "$OUT/shots.txt"
cp "$SCR/shots/"* "$OUT/" 2>/dev/null
echo "== done $(date -u +%H:%M:%SZ)"
