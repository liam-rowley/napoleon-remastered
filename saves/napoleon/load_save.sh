#!/usr/bin/env bash
# purpose: one load test of a save through the watcher: stage it as zz_<name>, launch, wait for the front end, autostart campaign:zz_<name>, read the turn, optionally end the turn (waiting for the next player turn) and quick save (copy kept under <state>/saves), kill; one JSON line per step
# usage: saves/napoleon/load_save.sh <owner> <save file> <zz_name> [--end-turn] [--quicksave] [--log FILE]   (game lock held by <owner>; proxy installed with dev.ctl, dev.lua_bridge, dev.state_json and dev.skip_intro on)
# when: load ladder A/B/C (J14) and any check that an edited save loads (J4 scenarios); waiting happens inside this one call
# not-a-verb: a PC sitting helper over job.sh and stage_save.py, run in Git Bash on the PC
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
JOB="bash $REPO/core/harness/job.sh"; STAGE="python3 -I $HERE/stage_save.py"
owner="${1:?owner}"; src="${2:?save file}"; name="${3:?zz_name}"; shift 3
END=0; QS=0; LOG=/dev/null
while [ $# -gt 0 ]; do case "$1" in --end-turn) END=1;; --quicksave) QS=1;; --log) LOG="$2"; shift;; *) echo "unknown $1" >&2; exit 64;; esac; shift; done
# One run per owner: a run left polling after its launch was killed by hand sent ctl into the next launch's game (run 20261029_j14pc C1/C2).
GUARD="${TMPDIR:-/tmp}/napoleon_load_save.$owner.pid"
if [ -f "$GUARD" ] && kill -0 "$(cat "$GUARD")" 2>/dev/null; then
  echo "load_save: another load_save.sh for '$owner' is still running (pid $(cat "$GUARD")): stop it before the next launch" >&2; exit 2
fi
echo $$ > "$GUARD"; trap '[ "$(cat "$GUARD" 2>/dev/null)" = $$ ] && rm -f "$GUARD"' EXIT
P=napoleon_remastered/lua/probes
SAVES="${APPDATA:?}/The Creative Assembly/Napoleon/save_games"
step() {   # step <label> <ctl line> <wait_s>: run one ctl request, log {step, rc, result} and echo a short line; returns the ctl exit code
  local out rc; $JOB touch >/dev/null 2>&1   # keep the game lock fresh (it expires after 20 min without a refresh)
  out="$($JOB ctl "$owner" "$2" "$3" 2>&1)"; rc=$?
  printf '%s' "$out" | python3 -c '
import json,sys
raw=sys.stdin.read(); label,rc,line=sys.argv[1],int(sys.argv[2]),sys.argv[3]
try: d=json.loads(raw)
except Exception: d={"status":"no-json","raw":raw[-400:]}
keep={k:d.get(k) for k in ("status","reason","scene","waited_s","load_s","total_s","lua","chunk") if d.get(k) not in (None,"")}
row={"step":label,"rc":rc,"request":line,**keep}
open(sys.argv[4],"a",encoding="utf-8").write(json.dumps(row)+"\n"); print(json.dumps(row)[:400])' "$1" "$rc" "$2" "$LOG"
  return $rc
}
chunk() { $JOB touch >/dev/null 2>&1; $JOB ctl "$owner" "lua $P/$1" 20 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("chunk",""))' 2>/dev/null; }
fail() { echo "{\"step\":\"$1\",\"rc\":1,\"status\":\"stopped\"}" | tee -a "$LOG"; echo kill | $JOB "$owner" - 150 >/dev/null 2>&1; exit 1; }

$STAGE stage "$src" "$name" || exit 1
echo launch | $JOB "$owner" - 120 >/dev/null 2>&1 || fail launch
step frontend "waitfor frontend 240" 260 || fail frontend
step autostart "autostart campaign:$name 420" 440 || fail autostart
step turn "lua $P/campaign_turn.lua" 60 || fail turn
if [ "$END" = 1 ]; then
  before="$(chunk campaign_turn.lua)"
  step end_turn "lua $P/campaign_end_turn.lua" 60 || fail end_turn
  t0=$(date +%s); now="$before"; IFS='|' read -r by bs _ <<< "$before"; moved=0; silent=0
  while [ $(( $(date +%s) - t0 )) -lt 900 ]; do   # the AI turn: poll the turn probe every 10 s, up to 15 min
    sleep 10; now="$(chunk campaign_turn.lua)"; IFS='|' read -r ny ns np _ <<< "$now"
    [ "$np" = true ] && [ "$ny|$ns" != "$by|$bs" ] && { moved=1; break; }   # year|season|players_turn|...
    # No answer = the campaign script is not pumping: a modal popup (AI diplomacy offer, turn-start event) or a minimised,
    # unfocused window stops frames and Lua (run 20261029_j14pc). Nothing in Lua can dismiss it, so stop instead of waiting.
    if [ -z "$now" ]; then silent=$((silent + 1)); else silent=0; fi
    [ "$silent" -ge 4 ] && { echo '{"step":"next_turn","status":"pump_stalled","reason":"no Lua pump for 4 polls: a modal popup or focus loss (SAVE_FORMAT.md Open)"}' | tee -a "$LOG"; fail next_turn; }
  done
  printf '{"step":"next_turn","from":"%s","to":"%s","waited_s":%d}\n' "$before" "$now" $(( $(date +%s) - t0 )) | tee -a "$LOG"
  [ "$moved" = 1 ] || fail next_turn
fi
if [ "$QS" = 1 ]; then
  mark="$(date +%s)"
  step quicksave "lua $P/campaign_quicksave.lua" 60 || fail quicksave
  qs=""; for i in $(seq 1 60); do   # the newest .save written after the request, once its size holds for 2 s
    sleep 2; f="$(cd "$SAVES" && ls -t -- *.save 2>/dev/null | head -1)"
    [ -n "$f" ] && [ "$(stat -c %Y "$SAVES/$f")" -ge "$mark" ] || continue
    s1=$(stat -c %s "$SAVES/$f"); sleep 2; [ "$s1" = "$(stat -c %s "$SAVES/$f")" ] && { qs="$f"; break; }
  done
  [ -n "$qs" ] || fail quicksave_file
  kept="$($STAGE keep "$qs" --as "${name}_qs_$(date -u +%Y%m%dT%H%M%SZ).save")"
  python3 -c 'import json,sys; print(json.dumps({"step": "quicksave_file", "file": sys.argv[1], "kept": sys.argv[2]}))' \
    "$qs" "$(printf '%s' "$kept" | head -1)" | tee -a "$LOG"   # json.dumps: the kept path has Windows backslashes
fi
echo kill | $JOB "$owner" - 150 >/dev/null 2>&1; echo "{\"step\":\"kill\",\"rc\":$?}" | tee -a "$LOG"
