#!/bin/bash
# J10 live pass, sitting 1 front end (re-run): sit1.sh reset to the front end after hist_dresden, and the warm reset from a historical
# battle stops at its post-battle screen (only ctl scene relaunches there), so its 13 pages ran inside the battle (page|true|false, Lua
# context battle). This sitting launches through land_small, warm-resets from that ordinary battle to the front end, checks the context
# is frontend, then walks the same pages. Only the main menu pumps Lua (J9), so fe_page.lua logs each page's tree and returns to main in
# one call; the shots then open each page and stay (shot.sh needs no Lua; ctl shot waits for a game scene), and a relaunch leaves it.
# Its trees (sit1fe_proxy.log) replace the same labels of sit1_proxy.log (ui_atlas parse_trees).
set -u
cd /c/Users/liamr/repos/napoleon-remastered
J=core/harness/job.sh
RUN=harness/runs/20261102_j10pc
P=C:/Users/liamr/repos/napoleon-remastered/$RUN/probes
Q=C:/Users/liamr/repos/napoleon-remastered/harness/runs/20261101_j9fix/probes
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
SCR=$(bash $J scratch j10)/20261102_j10pc/a3fe
RAW=$SCR/raw; SHOTS=$SCR/shots; mkdir -p "$RAW" "$SHOTS"
# One driver at a time (sit1.sh): a second driver refuses to start while the first is alive; stop a driver with kill on its pid.
PIDF=$(dirname "$SCR")/driver.pid
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "driver $(cat "$PIDF") is still running: kill it first"; exit 1; fi
echo $$ > "$PIDF"; trap 'rm -f "$PIDF"' EXIT
restored() { for t in $(seq 1 60); do bash $J status 2>/dev/null | grep -q '"profile_active":  null' && return 0; sleep 2; done; echo "restore not seen"; }
L() { bash $J ctl j10 "lua $1" > "$RAW/$2.txt" 2>&1; echo "$2 rc $?: $(tail -c 200 "$RAW/$2.txt" | tr -d '\n' | cut -c1-200)"; }
T() { L "$P/tree.lua -- $1 ${2:-*}" "tree_$1"; L "$Q/vis.lua" "vis_$1"; }
S() { bash core/harness/shot.sh j10 "$SHOTS/j10_$1.jpg" > "$RAW/shot_$1.txt" 2>&1; echo "shot $1 rc $?"; }
fe() { C scene land_small; C reset; sleep 8; C state; grep -Eq '"scene": *"frontend"' "$RAW/ctl_state.json"; }
C() { python3 core/harness/ctl.py --owner j10 "$@" > "$RAW/ctl_$(echo "$*" | tr ' /' '__').json" 2>&1; echo "ctl $* rc $?"; }
finish() { echo kill | bash $J j10 - 120 > /dev/null 2>&1; cp "$G/napoleon_remastered/logs/proxy.log" "$RAW/$1_proxy.log"; bash $J unlock j10 > /dev/null 2>&1; restored
  mkdir -p "$RUN/raw"; cp -r "$RAW/." "$RUN/raw/"; ls "$SHOTS" > "$RUN/raw/shots_$1.txt"; }

echo "== sitting 1 front end $(date -u +%H:%M:%SZ)"; restored
bash $J lock j10 1bbe2745-8ed4-4d4c-9684-e1adf6bab382 "J10 live pass: front end" > /dev/null 2>&1
if ! fe; then echo "not at the front end after the reset: stop"; finish sit1fe; exit 1; fi
T fe_main; S fe_main; L "$Q/getters.lua -- $Q/probe_safe_list.lua" getters_frontend
PAGES="single_player sp_battle1 sp_battle2 sp_battle2_scenario napoleon_battles sp_load_game sp_tutorials sp_episodic_campaign options credits player_stats load_replay grand_campaign"
for page in $PAGES; do L "$P/fe_page.lua -- $page" "page_$page"; sleep 2; done
L "$Q/vis.lua" vis_fe_after_pages
echo "== shots $(date -u +%H:%M:%SZ)"
for page in $PAGES; do
  L "$P/fe_page.lua -- $page stay" "stay_$page"; sleep 4; S "fe_$page"
  echo kill | bash $J j10 - 120 > /dev/null 2>&1
  fe || { echo "relaunch to the front end failed after $page: stop"; break; }
done
finish sit1fe
echo "== done $(date -u +%H:%M:%SZ)"
