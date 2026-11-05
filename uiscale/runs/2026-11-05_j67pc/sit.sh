#!/bin/bash
# J67 PC sitting. Usage: sit.sh <label> <adapter.json> <part>...   parts: route battles frontend pages campaign
# One driver at a time. Raw results go to raw/<label>; shots are the harness's 1280-wide JPGs. The play install and the lock come first
# (play.py refuses an agent's lock, so: install, then `job.sh lock j67 ...`); the game is killed at the end of the call.
set -u
cd "$(dirname "$0")/../../.."
LABEL=$1; AD=$2; shift 2
OWNER=j67
J=core/harness/job.sh
HERE=$(pwd -W)
RUNP=$HERE/uiscale/runs/2026-11-05_j67pc/probes
P=$HERE/harness/runs/20261102_j10pc/probes
Q=$HERE/harness/runs/20261101_j9fix/probes
MC=napoleon_remastered/lua/probes/campaign_modal_close.lua
GB='/c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War'
SCR=$(bash $J scratch $OWNER)/$LABEL
OUT=uiscale/runs/2026-11-05_j67pc/raw/$LABEL
mkdir -p "$SCR/shots" "$OUT"
PIDF=$(dirname "$SCR")/driver.pid
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "driver $(cat "$PIDF") is still running: kill it first"; exit 1; fi
echo $$ > "$PIDF"; trap 'rm -f "$PIDF"' EXIT
n() { echo "$*" | tr ' /:=' '____' | cut -c1-60; }
C() { python3 core/harness/ctl.py --adapter "$AD" --owner $OWNER --out "$SCR/shots" "$@" > "$OUT/ctl_$(n "$*").json" 2>&1; echo "ctl $* rc $?: $(tail -c 150 "$OUT/ctl_$(n "$*").json" | tr -d '\n' | cut -c1-150)"; }
L() { bash $J --adapter "$AD" ctl $OWNER "lua $1" > "$OUT/$2.txt" 2>&1; echo "$2 rc $?: $(tail -c 170 "$OUT/$2.txt" | tr -d '\n' | cut -c1-170)"; }
F() { bash core/harness/shot.sh $OWNER "$SCR/shots/$1.jpg" > "$OUT/shot_$1.txt" 2>&1; echo "shot $1 rc $?"; }
grab() { cp "$GB/napoleon_remastered/logs/proxy.log" "$OUT/proxy_$1.log" 2>/dev/null; }
fe() { bash $J touch $OWNER > /dev/null 2>&1; C scene land_small; C reset; sleep 8; C state; grep -Eq '"scene": *"frontend"' "$OUT/ctl_state.json"; }
endgame() { echo kill | bash $J --adapter "$AD" $OWNER - 120 > /dev/null 2>&1; }

for part in "$@"; do
  bash $J touch $OWNER > /dev/null 2>&1; echo "== $part $(date -u +%H:%M:%SZ)"
  case $part in
  route)
    C scene land_small; C shot land; L "$RUNP/wsp_copy.lua" wsp_copy_battle; grab route
    C reset; sleep 8; C state; F frontend ;;
  battles)
    C scene land_small; C cam land_small:deploy; C shot land_deploy
    C scene naval_small; C cam naval_small:deploy; C shot naval_deploy
    C scene siege_small; C cam siege_small:deploy; C shot siege_deploy; grab battles ;;
  frontend)
    fe && { F fe_main; L "$Q/vis.lua" vis_fe; grab frontend; } ;;
  pages)
    for page in ${PAGES:-single_player sp_battle1 sp_battle2 napoleon_battles sp_load_game sp_tutorials sp_episodic_campaign options credits player_stats load_replay grand_campaign}; do
      fe || { echo "no front end before $page: stop"; break; }
      L "$P/fe_page.lua -- $page stay" "stay_$page"; sleep 4; F "fe_$page"; endgame
    done ;;
  campaign)
    C scene campaign_start; sleep 20; C shot camp_popup
    for t in 1 2 3 4; do L "$MC" modal_close_$t; sleep 4; done
    C shot camp_hud
    for k in army agent settlement; do L "$Q/camp_select.lua -- $k" "select_$k"; sleep 6; C shot "camp_$k"; done
    for pair in lists:ToggleEntityLists gov:ShowGovernmentPopup diplomacy:ToggleDiplomacyPopup missions:ShowMissionsPopup technologies:ShowTechnologies buildings:ShowBuildingBrowser; do
      sc=${pair%%:*}; fn=${pair#*:}
      L "$Q/camp_panel.lua -- $fn" "panel_$sc"; sleep 5; C shot "camp_$sc"; L "$Q/camp_panel.lua -- close" "close_$sc"; sleep 3
    done
    grab campaign ;;
  army)
    C scene campaign_start; sleep 20
    L "$Q/vis.lua" vis_popup; L "$P/tree.lua -- camp_popup *" tree_popup; grab popup
    L "$RUNP/camp_field.lua" select_field; sleep 6; C shot camp_field; L "$Q/vis.lua" vis_field ;;
  *) echo "unknown part $part" ;;
  esac
done
endgame
ls "$SCR/shots" > "$OUT/shots.txt"
cp "$SCR/shots/"* "$OUT/" 2>/dev/null
ls "$GB/napoleon_remastered/dumps" 2>/dev/null | head -5
echo "== done $(date -u +%H:%M:%SZ)"
