#!/bin/bash
# J9 fix round, attempt 5: the campaign panels again. In attempts 1-2 the campaign-start "Mission Issued" popup (modal) was up, so
# OnShortcut opened nothing (shots j9f_campaign_show_*.jpg). Close it first (campaign_modal_close.lua), then open each panel and
# record the visible top-level components (vis.lua) and a shot next to the surface probe.
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

MC=napoleon_remastered/lua/probes/campaign_modal_close.lua
echo "== campaign panels $(date -u +%H:%M:%SZ)"; restored
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 fix panels" > /dev/null 2>&1
python3 core/harness/ctl.py --owner j9 --out $RAW scene campaign_start > $RAW/campaign5_scene.json 2>&1; echo "scene rc $?"
L "$P/vis.lua" vis5_start
for t in 1 2 3; do L "$MC" modal_close5_$t; sleep 3; done
L "$P/vis.lua" vis5_after_close; shot campaign5_after_close
for sc in show_lists show_gov show_diplomacy show_missions show_technologies; do
  L "$P/camp_panel.lua -- $sc" panel5_$sc; sleep 5
  L "$P/vis.lua" vis5_$sc
  L "$API -- campaign_$sc" api_campaign_$sc; shot campaign5_$sc
  L "$P/camp_panel.lua -- $sc" panel5_${sc}_toggle; sleep 3   # the same hotkey again closes the panel before the next one
done
finish campaign5
echo "== done $(date -u +%H:%M:%SZ)"
