#!/bin/bash
# J96 PC sitting. Usage: sit.sh <label> <adapter.json> <pack names, comma list or -> <parts>...   parts: land front camp army
# The lock and the kit come first (job.sh lock j96 ...). Packs go in before the launch and out after the kill; shots go to raw/<label>.
# grab.ps1, started beside this, catches the loading screens: a shot through the watcher takes about 3 s, longer than the load.
set -u
cd "$(dirname "$0")/../../.."
LABEL=$1; AD=$2; PK=$3; shift 3
OWNER=j96
J=core/harness/job.sh
HERE=$(pwd -W)
Q=$HERE/harness/runs/20261101_j9fix/probes
GB='/c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War'
GW='C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
SW='C:\napoleon_remastered_pc\_scratch\j96'
SCR=$(bash $J scratch $OWNER)
OUT=uiscale/runs/2026-11-06_j96/raw/$LABEL
mkdir -p "$SCR/shots_$LABEL" "$OUT"
SH=$SCR/shots_$LABEL
n() { echo "$*" | tr ' /:=' '____' | cut -c1-60; }
C() { python3 core/harness/ctl.py --adapter "$AD" --owner $OWNER --out "$SH" "$@" > "$OUT/ctl_$(n "$*").json" 2>&1; echo "ctl $* rc $?: $(tail -c 150 "$OUT/ctl_$(n "$*").json" | tr -d '\n' | cut -c1-150)"; }
L() { bash $J --adapter "$AD" ctl $OWNER "lua $1" > "$OUT/$2.txt" 2>&1; echo "$2 rc $?: $(tail -c 170 "$OUT/$2.txt" | tr -d '\n' | cut -c1-170)"; }
F() { bash core/harness/shot.sh $OWNER "$SH/$1.jpg" > "$OUT/shot_$1.txt" 2>&1; echo "shot $1 rc $?"; }
packs() {
  [ "$PK" = "-" ] && return 0
  local f="$SCR/pk_$1_$LABEL.ps1" list=""
  for p in ${PK//,/ }; do
    if [ "$1" = in ]; then list="$list,'$SW\\packs\\$p.pack'"; else list="$list,'$p.pack'"; fi
  done
  list=${list#,}
  { echo '#ps1'; echo "#job owner=$OWNER timeout=900 type=ps1"
    if [ "$1" = in ]; then echo "& '$SW\\install_packs.ps1' -Mode install -Game '$GW' -Packs @($list) -Trash '$SW\\trash'"
    else echo "& '$SW\\install_packs.ps1' -Mode uninstall -Game '$GW' -Names @($list) -Trash '$SW\\trash'"; fi
    echo 'exit $LASTEXITCODE'; } > "$f"
  bash $J $OWNER "$f" 900 | tail -2 | cut -c1-200
}
endgame() { echo kill | bash $J --adapter "$AD" $OWNER - 120 > /dev/null 2>&1; }

bash $J touch $OWNER > /dev/null 2>&1
packs in
for part in "$@"; do
  bash $J touch $OWNER > /dev/null 2>&1; echo "== $part $(date -u +%H:%M:%SZ)"
  case $part in
  land)  C scene land_small; C shot land; F land4k ;;
  front) C scene land_small; C reset; sleep 8; C state; F frontend ;;
  camp)  C scene campaign_start; sleep 20; C shot camp; F camp4k ;;
  army)  L "$Q/camp_select.lua -- army" select_army; sleep 6; C shot camp_army ;;
  field) L "$HERE/uiscale/runs/2026-11-05_j67pc/probes/camp_field.lua" select_field; sleep 6; C shot camp_field ;;
  *) echo "unknown part $part" ;;
  esac
done
cp "$GB/napoleon_remastered/logs/proxy.log" "$OUT/proxy.log" 2>/dev/null
endgame
packs out
ls "$SH" > "$OUT/shots.txt"
ls "$GB/napoleon_remastered/dumps" 2>/dev/null | head -5
ls "$APPDATA/The Creative Assembly/Napoleon/ui_cache" 2>/dev/null | wc -l
echo "== done $(date -u +%H:%M:%SZ)"
