#!/bin/bash
# J9 proof launch: proof.sh <tag> <scene> "<key=val ...>" [cam "x y z yaw pitch"]...   (one launch; captures + perf + shot per pose)
set -u
cd /c/Users/liamr/repos/napoleon-remastered
TAG=$1; SCENE=$2; KEYS=$3; shift 3
PIDF=/c/napoleon_remastered_pc/_scratch/J9/proof.pid; echo $$ > $PIDF
mine() { [ "$(cat $PIDF 2>/dev/null)" = "$$" ] || { echo "another proof driver took over: $TAG stops"; exit 3; }; }
G='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
RAW=harness/runs/20261101_j9pc/raw
J=core/harness/job.sh
echo "== $TAG $SCENE keys: $KEYS  $(date -u +%H:%M:%SZ)"
for t in $(seq 1 60); do $J status 2>/dev/null | grep -q '"profile_active":  null' && break; sleep 2; done   # the previous launch's profile restore must land first
python3 core/proxy/tools/pc_deploy.py set --game "$G" --config-file napoleon_remastered.ini dev.capture=1 'dev.capture_dir=C:\napoleon_remastered_pc\captures' $KEYS 2>&1 | tail -1
for kv in $KEYS; do k=${kv#gfx.}; grep -q "^${k%%=*}=${kv#*=}" "$G/napoleon_remastered.ini" || echo "KEY NOT IN INI: $kv"; done
$J lock j9 4127895c-6413-43ca-81ff-480348089c8a "J9 proof $TAG" >/dev/null 2>&1
[ -n "${PROFILE:-}" ] && { echo "profile $PROFILE" | $J j9 - 120 2>&1 | tail -1; }
if [ "$SCENE" = frontend ]; then
  mine; echo "launch" | $J j9 - 300 2>&1 | tail -1
  $J ctl j9 "waitfor frontend" > $RAW/j9_${TAG}_waitfor.txt 2>&1; echo "waitfor rc $?"; sleep 5
  $J ctl j9 "lua napoleon_remastered/lua/probes/api_surface.lua -- frontend" > $RAW/j9_api_frontend.txt 2>&1; echo "api frontend rc $?: $(tail -c 160 $RAW/j9_api_frontend.txt | tr -d '
')"
  mine; echo kill | $J j9 - 120 > /dev/null 2>&1; echo "kill rc $?"
  cp "$G/napoleon_remastered/logs/proxy.log" $RAW/j9_${TAG}_proxy.log 2>/dev/null
  mine; $J unlock j9 >/dev/null 2>&1; exit 0
fi
mine; python3 core/harness/ctl.py --owner j9 --out $RAW scene $SCENE > $RAW/${TAG}_scene.json 2>&1; echo "scene rc $? $(python3 -c "import json,sys;d=json.load(open('$RAW/${TAG}_scene.json'));print(d['status'],d.get('reason','')[:200],'load',d.get('load_s') or d.get('settle',{}))" 2>&1 | cut -c1-300)"
i=0
cap() { # name
  $J ctl j9 "capture j9c_$1 1" > $RAW/j9c_$1_capture.txt 2>&1; echo "capture $1 rc $?: $(tail -c 300 $RAW/j9c_$1_capture.txt | tr '\n' ' ')"
  python3 core/harness/ctl.py --owner j9 --out $RAW shot j9_$1 > $RAW/j9_$1_shot.json 2>&1; echo "shot rc $?"
}
cap ${TAG}_a
api() { $J ctl j9 "lua napoleon_remastered/lua/probes/api_surface.lua -- $1" > $RAW/j9_api_$1.txt 2>&1; echo "api $1 rc $?: $(tail -c 200 $RAW/j9_api_$1.txt | tr '
' ' ')"; }
[ -n "${PROBE:-}" ] && api $PROBE
if [ -n "${SEL:-}" ]; then $J ctl j9 "lua napoleon_remastered/lua/probes/campaign_select.lua" > $RAW/j9_${TAG}_select.txt 2>&1; echo "select rc $?: $(tail -c 200 $RAW/j9_${TAG}_select.txt | tr -d '
')"; sleep 6; api ${PROBE}_selected; cap ${TAG}_sel; fi
while [ $# -ge 2 ] && [ "$1" = cam ]; do
  i=$((i+1)); python3 core/harness/ctl.py --owner j9 --out $RAW cam $2 > $RAW/j9_${TAG}_cam$i.json 2>&1; echo "cam $2 rc $?"
  cap ${TAG}_c$i; shift 2
done
if [ -n "${FRONT:-}" ]; then python3 core/harness/ctl.py --owner j9 --out $RAW reset > $RAW/j9_${TAG}_reset.json 2>&1; echo "reset rc $?"; api frontend; fi
python3 core/harness/ctl.py --owner j9 --out $RAW perf 10 > $RAW/j9_${TAG}_perf.json 2>&1; echo "perf rc $? $(python3 -c "import json;d=json.load(open('$RAW/j9_${TAG}_perf.json'));print(d.get('p50_ms'),d.get('build'))" 2>&1|cut -c1-200)"
$J ctl j9 "log" > $RAW/j9_${TAG}_ctllog.txt 2>&1
mine; echo kill | $J j9 - 120 > /dev/null 2>&1; echo "kill rc $?"
cp "$G/napoleon_remastered/logs/proxy.log" $RAW/j9_${TAG}_proxy.log 2>/dev/null
grep -E "patch_engine" $RAW/j9_${TAG}_proxy.log | grep -v "^\s*$" | tail -4 | cut -c1-200
mine; $J unlock j9 >/dev/null 2>&1
