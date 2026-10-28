#!/usr/bin/env bash
# purpose: agent helper for the device VM: submit a watcher job, block inside ONE call until its result (or a timeout), print the output, return the job's exit code (refused 2, no answer 124); also take, refresh and release the game lock
# usage: job.sh [--adapter FILE] <owner> <file|-> [timeout_s]  |  job.sh [--adapter FILE] lock <owner> <session> <purpose> [hang_s]  |  touch  |  unlock <owner> [--force]  |  status  |  root
# when: every time an agent runs something on the PC (launch, kill, profile, scripts): the watcher root comes from the adapter (device_mount + watcher_subdir), never a default path; waiting belongs here, not in repeated agent calls
# not-a-verb: runs in the device VM's bash (python3 and the PC's folders mounted), outside the repo checkout
# Body: a one-line control job (launch|kill|profile <name>|restore|update kit=<id>|restart|status|noop) or a cmd/ps1 script ('#ps1' first line or '#job type=ps1').
# launch/kill/profile get ' owner=<owner>' appended when missing; a script without a '#job owner=' line gets one. Mounts: $DEVICE_MOUNTS (default $HOME/mnt)/<adapter device_mount>.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ADAPTER="${HARNESS_ADAPTER:-}"
if [ "${1:-}" = "--adapter" ]; then ADAPTER="${2:?--adapter FILE}"; shift 2; fi
resolve_root() {
  if [ -n "${WATCHER_ROOT:-}" ]; then printf '%s' "$WATCHER_ROOT"; return 0; fi
  local a
  for a in "$ADAPTER" "$HERE/adapter.json" "$HERE/../napoleon/adapter.json"; do
    [ -n "$a" ] && [ -f "$a" ] && { ADAPTER="$a"; break; }
  done
  [ -f "$ADAPTER" ] || { echo "job.sh: no adapter.json found (use --adapter FILE, \$HARNESS_ADAPTER or \$WATCHER_ROOT)" >&2; return 64; }
  python3 - "$ADAPTER" "${DEVICE_MOUNTS:-$HOME/mnt}" <<'PY'
import json, sys
a = json.load(open(sys.argv[1], encoding='utf-8'))
print(sys.argv[2].rstrip('/') + '/' + a['device_mount'] + '/' + a['watcher_subdir'], end='')
PY
}
ROOT="$(resolve_root)" || exit 64
[ -d "$ROOT" ] || { echo "job.sh: watcher root $ROOT does not exist: is the PC folder connected (device mount) and the watcher installed?" >&2; exit 64; }
jget() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); print(d.get(sys.argv[2],""))' "$1" "$2"; }
utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
lock_owner() { [ -f "$ROOT/game.lock" ] && tr -d '\r' < "$ROOT/game.lock" | head -1 | sed -n 's/.*\bowner=\([^ ]*\).*/\1/p'; }
lock_age() { echo $(( $(date +%s) - $(stat -c %Y "$ROOT/game.lock") )); }
cmd="${1:-}"
case "$cmd" in
  root) printf '%s\n' "$ROOT"; exit 0;;
  status)
    [ -f "$ROOT/watcher.alive" ] || { echo "no watcher.alive in $ROOT: the watcher has never run here" >&2; exit 1; }
    age=$(( $(date +%s) - $(stat -c %Y "$ROOT/watcher.alive") ))
    for i in 1 2 3 4 5; do python3 -c 'import json,sys; json.load(open(sys.argv[1],encoding="utf-8"))' "$ROOT/watcher.status" 2>/dev/null && break; sleep 0.2; done   # the file is replaced every 2 s
    cat "$ROOT/watcher.status"; echo
    [ "$age" -lt 15 ] && exit 0
    echo "watcher heartbeat is ${age}s old: the watcher is not running (after a reboot Liam waits for the logon task, or double-clicks src\\watch.cmd)" >&2; exit 1;;
  lock)
    owner="${2:?lock <owner> <session> <purpose> [hang_s]}"; session="${3:?session}"; purpose="${4:?purpose}"; hang="${5:-}"
    if [ -f "$ROOT/game.lock" ]; then
      cur="$(lock_owner)"; age="$(lock_age)"
      if [ -n "$cur" ] && [ "$cur" != "$owner" ] && [ "$age" -lt 1200 ]; then echo "game.lock is held by '$cur' (refreshed ${age}s ago): refused" >&2; exit 2; fi
    fi
    line="owner=${owner//[$'\r\n']/_} session=${session//[$'\r\n']/_} purpose=${purpose//[$'\r\n']/ } started=$(utc)"
    [ -n "$hang" ] && line="$line hang_s=$hang"
    printf '%s\n' "$line" > "$ROOT/game.lock.tmp" && mv "$ROOT/game.lock.tmp" "$ROOT/game.lock" || exit 1
    echo "game.lock taken: $line  (refresh at least every 10 min with: job.sh touch; the watcher expires it after 20 min)"; exit 0;;
  touch)
    [ -f "$ROOT/game.lock" ] || { echo "no game.lock to refresh" >&2; exit 2; }
    touch "$ROOT/game.lock" && echo "game.lock refreshed"; exit 0;;
  unlock)
    owner="${2:?unlock <owner> [--force]}"
    [ -f "$ROOT/game.lock" ] || { echo "no game.lock held"; exit 0; }
    cur="$(lock_owner)"
    if [ "$cur" != "$owner" ] && [ "${3:-}" != "--force" ]; then echo "game.lock belongs to '$cur', not '$owner': refused (--force overrides)" >&2; exit 2; fi
    mkdir -p "$ROOT/_to_delete"
    mv "$ROOT/game.lock" "$ROOT/_to_delete/game.lock.released_${cur:-unknown}_$(date -u +%Y%m%dT%H%M%SZ)" && echo "game.lock released (the watcher restores an active profile by itself once the game is closed)"; exit 0;;
esac
owner="${1:-}"; file="${2:-}"; t="${3:-900}"
[ -n "$owner" ] && [ -n "$file" ] || { sed -n '2,4p' "$0"; exit 64; }
safe="$(printf '%s' "$owner" | tr -c 'A-Za-z0-9._-' '_')"
J="$ROOT/jobs"; mkdir -p "$J"
id="$safe-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM$RANDOM"
body="$(mktemp)"; trap 'rm -f "$body"' EXIT
if [ "$file" = "-" ]; then cat > "$body"; else cp "$file" "$body" || exit 1; fi
nonempty="$(grep -c '[^[:space:]]' "$body" || true)"
first="$(grep -m1 '[^[:space:]]' "$body" | tr -d '\r' | sed 's/^[[:space:]]*//')"
case "$first" in
  launch*|kill*|profile*)
    if [ "$nonempty" -eq 1 ] && ! printf '%s' "$first" | grep -q 'owner='; then printf '%s owner=%s\n' "$first" "$owner" > "$body"; fi;;
  *)
    if [ "$nonempty" -ne 1 ] || ! printf '%s' "$first" | grep -Eq '^(launch|kill|profile|restart|update|status|noop)\b'; then
      grep -q '^[[:space:]]*#job\b.*\bowner=' "$body" || { { printf '#job owner=%s\n' "$owner"; cat "$body"; } > "$body.new" && mv "$body.new" "$body"; }
    fi;;
esac
cp "$body" "$J/$id.tmp" && mv "$J/$id.tmp" "$J/$id.request" || { echo "job.sh: cannot submit into $J" >&2; exit 1; }
end=$(( $(date +%s) + t ))
while [ ! -f "$J/$id.done" ] && [ "$(date +%s)" -lt "$end" ]; do sleep 1; done
if [ ! -f "$J/$id.done" ]; then
  echo "job $id: no result after ${t}s. Check: job.sh status   (heartbeat, current_job, queue). The request stays queued." >&2
  exit 124
fi
sleep 0.2   # .done is written last and atomically; .out is already complete
[ -f "$J/$id.out" ] && cat "$J/$id.out"
s="$(jget "$J/$id.done" status)"; e="$(jget "$J/$id.done" exit)"; reason="$(jget "$J/$id.done" reason)"
echo "[job $id: $s exit=$e${reason:+ - $reason}]" >&2
case "$s" in
  ok) exit 0;;
  failed) if [ "$e" -ge 1 ] 2>/dev/null && [ "$e" -le 255 ]; then exit "$e"; else exit 1; fi;;
  refused) exit 2;;
  *) exit 124;;
esac
