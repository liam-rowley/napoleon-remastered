#!/bin/bash
# J10 live pass, sitting 1: battles and the front end on the installed 20-pass build (kit_20261101T205936Z_f08b12c3806a, DLL 46f52d356ce8).
# One launch: land_small (deployment, then running), naval_small (deployment, running), siege_small (deployment), hist_dresden (deployment),
# then a warm reset to the front end and every safe page there. Per state: the component tree (probes/tree.lua), the visible top level
# (J9 vis.lua), the probe-safe getters (J9 getters.lua) once per context, one shot. Probes only read; pages open the way their buttons do.
# Raw results go to the PC scratch folder while the game runs and are copied into raw/ at the end (J9 fix round lesson 3).
set -u
cd /c/Users/liamr/repos/napoleon-remastered
J=core/harness/job.sh
RUN=harness/runs/20261102_j10pc
P=C:/Users/liamr/repos/napoleon-remastered/$RUN/probes
Q=C:/Users/liamr/repos/napoleon-remastered/harness/runs/20261101_j9fix/probes
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
SCR=$(bash $J scratch j10)/20261102_j10pc/a3
RAW=$SCR/raw; SHOTS=$SCR/shots; mkdir -p "$RAW" "$SHOTS"
# One driver at a time: attempt 2 ran beside a still-live attempt 1 (TaskStop ended the tee, not the script) and its unguarded calls
# crashed the game twice. A second driver refuses to start while the first is alive; stop a driver with kill on the pid in driver.pid.
PIDF=$(dirname "$SCR")/driver.pid
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "driver $(cat "$PIDF") is still running: kill it first"; exit 1; fi
echo $$ > "$PIDF"; trap 'rm -f "$PIDF"' EXIT
restored() { for t in $(seq 1 60); do bash $J status 2>/dev/null | grep -q '"profile_active":  null' && return 0; sleep 2; done; echo "restore not seen"; }
L() { bash $J ctl j10 "lua $1" > "$RAW/$2.txt" 2>&1; echo "$2 rc $?: $(tail -c 200 "$RAW/$2.txt" | tr -d '\n' | cut -c1-200)"; }
T() { L "$P/tree.lua -- $1 ${2:-*}" "tree_$1"; L "$Q/vis.lua" "vis_$1"; }
S() { python3 core/harness/ctl.py --owner j10 --out "$SHOTS" shot "j10_$1" > "$RAW/shot_$1.json" 2>&1; echo "shot $1 rc $?"; }
C() { python3 core/harness/ctl.py --owner j10 "$@" > "$RAW/ctl_$(echo "$*" | tr ' /' '__').json" 2>&1; echo "ctl $* rc $?"; }
finish() { echo kill | bash $J j10 - 120 > /dev/null 2>&1; cp "$G/napoleon_remastered/logs/proxy.log" "$RAW/$1_proxy.log"; bash $J unlock j10 > /dev/null 2>&1; restored
  mkdir -p "$RUN/raw"; cp -r "$RAW/." "$RUN/raw/"; ls "$SHOTS" > "$RUN/raw/shots_$1.txt"; }

echo "== sitting 1 $(date -u +%H:%M:%SZ)"; restored
bash $J lock j10 1bbe2745-8ed4-4d4c-9684-e1adf6bab382 "J10 live pass: battles and front end" > /dev/null 2>&1
C scene land_small; T land_deploy; S land_deploy; L "$Q/getters.lua -- $Q/probe_safe_list.lua" getters_land
C scene land_small deploy=end; sleep 5; T land_running; S land_running
C scene naval_small; T naval_deploy; S naval_deploy; L "$Q/getters.lua -- $Q/probe_safe_list.lua" getters_naval
C scene naval_small deploy=end; sleep 5; T naval_running; S naval_running
C scene siege_small; T siege_deploy; S siege_deploy
C scene hist_dresden; T hist_deploy; S hist_deploy
echo "== front end $(date -u +%H:%M:%SZ)"
C reset; sleep 8; T fe_main; S fe_main; L "$Q/getters.lua -- $Q/probe_safe_list.lua" getters_frontend
for page in single_player sp_battle1 sp_battle2 sp_battle2_scenario napoleon_battles sp_load_game sp_tutorials sp_episodic_campaign options credits player_stats load_replay grand_campaign; do
  L "$P/fe_page.lua -- $page" "page_$page"; sleep 4
  T "fe_$page" "$page"; S "fe_$page"
  L "$P/fe_page.lua -- main" "back_$page"; sleep 3
done
finish sit1
echo "== done $(date -u +%H:%M:%SZ)"
