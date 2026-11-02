#!/bin/bash
# J10 live pass, sitting 2: the campaign (campaign_start, Austria) on the installed 20-pass build. The start-up mission popup is closed
# with the installed campaign_modal_close.lua (J9 fix round attempt 5); then the HUD, the probe-safe getters, an army, an agent and a
# settlement selected (J9 camp_select.lua, the settlement nil-guarded), and every panel the campaign root's menu functions open (J9
# camp_panel.lua; ShowPrestige needs menu arguments, so it is left out), each closed with PanelManager.CloseAllPanels. Per state: the
# component tree, the visible top level and one shot. Raw results go to the PC scratch folder and are copied into raw/ at the end.
set -u
cd /c/Users/liamr/repos/napoleon-remastered
J=core/harness/job.sh
RUN=harness/runs/20261102_j10pc
P=C:/Users/liamr/repos/napoleon-remastered/$RUN/probes
Q=C:/Users/liamr/repos/napoleon-remastered/harness/runs/20261101_j9fix/probes
MC=napoleon_remastered/lua/probes/campaign_modal_close.lua
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

echo "== sitting 2 $(date -u +%H:%M:%SZ)"; restored
bash $J lock j10 1bbe2745-8ed4-4d4c-9684-e1adf6bab382 "J10 live pass: campaign" > /dev/null 2>&1
C scene campaign_start; sleep 20
T camp_popup; S camp_popup
for t in 1 2 3 4; do L "$MC" modal_close_$t; sleep 4; done
T camp_hud; S camp_hud; L "$Q/getters.lua -- $Q/probe_safe_list.lua" getters_campaign
for k in army agent settlement; do
  L "$Q/camp_select.lua -- $k" "select_$k"; sleep 6
  T "camp_$k"; S "camp_$k"
done
for pair in lists:ToggleEntityLists gov:ShowGovernmentPopup diplomacy:ToggleDiplomacyPopup missions:ShowMissionsPopup technologies:ShowTechnologies buildings:ShowBuildingBrowser; do
  sc=${pair%%:*}; fn=${pair#*:}
  L "$Q/camp_panel.lua -- $fn" "panel_$sc"; sleep 5
  T "camp_$sc"; S "camp_$sc"
  L "$Q/camp_panel.lua -- close" "close_$sc"; sleep 3
done
finish sit2
echo "== done $(date -u +%H:%M:%SZ)"
