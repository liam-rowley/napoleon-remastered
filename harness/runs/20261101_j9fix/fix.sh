#!/bin/bash
# J9 fix round (review round 1, should-fix 2): the API states the first sitting did not cover. Three launches on the installed
# final build: campaign (getters, army / fleet / agent / settlement selected, five panels), front end (getters, the page transitions),
# land (getters). Probes run from this folder by absolute path (proxy/napoleon is a DLL input; a new probe there would void the 20 passes).
set -u
cd /c/Users/liamr/repos/napoleon-remastered
J=core/harness/job.sh
RAW=harness/runs/20261101_j9fix/raw
P=C:/Users/liamr/repos/napoleon-remastered/harness/runs/20261101_j9fix/probes
API=napoleon_remastered/lua/probes/api_surface.lua
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
restored() { for t in $(seq 1 60); do $J status 2>/dev/null | grep -q '"profile_active":  null' && return 0; sleep 2; done; echo "restore not seen"; }
L() { $J ctl j9 "lua $1" > $RAW/$2.txt 2>&1; echo "$2 rc $?: $(tail -c 240 $RAW/$2.txt | tr -d '\n' | cut -c1-240)"; }
shot() { python3 core/harness/ctl.py --owner j9 --out $RAW shot j9f_$1 > $RAW/j9f_$1_shot.json 2>&1; }
finish() { echo kill | $J j9 - 120 > /dev/null 2>&1; cp "$G/napoleon_remastered/logs/proxy.log" $RAW/j9f_$1_proxy.log; $J unlock j9 > /dev/null 2>&1; restored; }

echo "== campaign $(date -u +%H:%M:%SZ)"; restored
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 fix campaign" > /dev/null 2>&1
python3 core/harness/ctl.py --owner j9 --out $RAW scene campaign_start > $RAW/campaign_scene.json 2>&1; echo "scene rc $?"
L "$P/getters.lua -- $P/probe_safe_list.lua" getters_campaign
for k in army fleet agent settlement; do
  L "$P/camp_select.lua -- $k" select_$k; sleep 6
  L "$API -- campaign_$k" api_campaign_$k; shot campaign_$k
done
for sc in show_lists show_gov show_diplomacy show_missions show_technologies; do
  L "$P/camp_panel.lua -- $sc" panel_$sc; sleep 5
  L "$API -- campaign_$sc" api_campaign_$sc; shot campaign_$sc
done
finish campaign

echo "== frontend $(date -u +%H:%M:%SZ)"
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 fix frontend" > /dev/null 2>&1
echo "launch" | $J j9 - 300 2>&1 | tail -1
$J ctl j9 "waitfor frontend" > $RAW/frontend_waitfor.txt 2>&1; echo "waitfor rc $?"; sleep 5
L "$API -- frontend" api_frontend
L "$P/getters.lua -- $P/probe_safe_list.lua" getters_frontend
L "$P/fe_pages.lua" fe_pages; sleep 6
L "$API -- frontend_after_pages" api_frontend_after_pages; shot frontend_after_pages
finish frontend

echo "== land $(date -u +%H:%M:%SZ)"
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 fix land" > /dev/null 2>&1
python3 core/harness/ctl.py --owner j9 --out $RAW scene land_small > $RAW/land_scene.json 2>&1; echo "scene rc $?"
L "$P/getters.lua -- $P/probe_safe_list.lua" getters_land
finish land
echo "== done $(date -u +%H:%M:%SZ)"
