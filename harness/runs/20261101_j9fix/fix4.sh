#!/bin/bash
# J9 fix round, attempt 4: the front-end page probe fixed (pages appear on their first TransitionTo; back to "main"), then a fleet:
# the coalition campaign as Britain through the proxy's autostart verb (campaign_britain_1805 has no autostart target).
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

echo "== frontend $(date -u +%H:%M:%SZ)"; restored
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 fix frontend and fleet" > /dev/null 2>&1
python3 core/harness/ctl.py --owner j9 --out $RAW scene land_small > $RAW/land4_scene.json 2>&1; echo "scene rc $? (sets the ctl keys)"
python3 core/harness/ctl.py --owner j9 --out $RAW reset > $RAW/reset4.json 2>&1; echo "reset rc $?"; sleep 5
L "$P/fe_pages.lua" fe_pages4; sleep 6
L "$API -- frontend_after_pages" api_frontend_after_pages4
finish frontend4
echo "== fleet $(date -u +%H:%M:%SZ)"
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 fix fleet" > /dev/null 2>&1
python3 core/harness/ctl.py --owner j9 --out $RAW scene land_small > $RAW/land5_scene.json 2>&1; echo "scene rc $?"
python3 core/harness/ctl.py --owner j9 --out $RAW reset > $RAW/reset5.json 2>&1; echo "reset rc $?"; sleep 5
$J ctl j9 "autostart campaign:new:mp_eur_napoleon:britain" > $RAW/autostart_britain.txt 2>&1; echo "autostart rc $?: $(tail -c 200 $RAW/autostart_britain.txt | tr -d '
')"
$J ctl j9 "waitfor campaign" > $RAW/waitfor_campaign4.txt 2>&1; echo "waitfor rc $?"; sleep 8
L "$P/camp_select.lua -- fleet" select_fleet4; sleep 6
L "$API -- campaign_fleet" api_campaign_fleet4; shot campaign_fleet
finish fleet
echo "== done $(date -u +%H:%M:%SZ)"
