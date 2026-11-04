#!/usr/bin/env bash
# purpose: build the review viewer (RmlUi + FreeType + float Lua 5.1.1) to build/viewer/out/viewer.js + viewer.wasm and run its Node tests
# usage: viewer/core/build.sh [--docker] [build|test|all] | --prune [--dry-run]   (--docker: inside the emsdk image pinned in viewer/pins.json, the PC route (D30, D31); default all; prints the sha256 of both outputs; --prune: remove the per-checkout CMake volumes whose checkout is gone, J97)
# when: after any change under viewer/core/ or viewer/pins.json; on the PC always with --docker (no Emscripten on the PC); CI's viewer job runs `--docker all`; `--prune --dry-run`, then `--prune`, when worktrees have gone (viewer/README.md Housekeeping)
# not-a-verb: a build script with a container round trip, like core/proxy/tools/build.sh; not a registry operation
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKER=0; [[ "${1:-}" == "--docker" ]] && { DOCKER=1; shift; }
WHAT="${1:-all}"
OUT="$ROOT/build/viewer/out"
VOL_PREFIX="napoleon-viewer-cmake"
DOCKER_DOWN="Docker is not answering: start Docker Desktop (Linux containers)"

# The CMake volume of a checkout: the prefix and the first 12 hex of the sha256 of its path as `cd && pwd` prints it.
vol_name() { printf '%s-%s' "$VOL_PREFIX" "$(printf %s "$1" | sha256sum | cut -c1-12)"; }

# prune_decide NAME CHECKOUT_LABEL LIVE_VOLUME_NAMES...: prints "keep <why>" or "remove <why>" (J97). Plain inputs, no docker calls.
prune_decide() {
  local name="$1" label="$2" live; shift 2
  [[ "$label" == "<no value>" ]] && label=""
  if [[ "$name" == "$VOL_PREFIX" ]]; then echo "remove the old shared volume (one volume per checkout since the J31 review)"; return; fi
  if [[ -n "$label" ]]; then
    if [[ -d "$label" ]]; then echo "keep checkout $label exists"; else echo "remove checkout $label is gone"; fi
    return
  fi
  for live in "$@"; do
    [[ "$live" == "$name" ]] && { echo "keep unlabelled, the hash of a live checkout"; return; }
  done
  echo "remove unlabelled, no live checkout hashes to it"
}

# --prune [--dry-run]: only volumes named napoleon-viewer-cmake or napoleon-viewer-cmake-*; one `docker volume rm` per volume, never a bulk prune.
prune() {
  local dry=0 v label decision kept=0 removed=0 skipped=0 p err; local -a live=()
  [[ "${1:-}" == "--dry-run" ]] && dry=1
  docker info >/dev/null 2>&1 || { echo "build.sh --prune: $DOCKER_DOWN"; exit 2; }
  live+=("$(vol_name "$ROOT")")
  while IFS= read -r p; do
    [[ "$p" == worktree\ * ]] || continue
    p="${p#worktree }"
    [[ -d "$p" ]] && live+=("$(vol_name "$(cd "$p" && pwd)")")
  done < <(git -C "$ROOT" worktree list --porcelain 2>/dev/null | tr -d '\r' || true)
  while IFS= read -r v; do
    [[ "$v" == "$VOL_PREFIX" || "$v" == "$VOL_PREFIX"-* ]] || continue
    label=""
    [[ "$v" == "$VOL_PREFIX" ]] || label="$(docker volume inspect -f '{{ index .Labels "napoleon.viewer.checkout" }}' "$v" 2>/dev/null | tr -d '\r' || true)"
    decision="$(prune_decide "$v" "$label" "${live[@]}")"
    if [[ "$decision" == keep* ]]; then
      echo "keep $v: ${decision#keep }"; kept=$((kept+1))
    elif [[ $dry == 1 ]]; then
      echo "would remove $v: ${decision#remove }"; removed=$((removed+1))
    elif err="$(docker volume rm "$v" 2>&1 >/dev/null)"; then
      echo "removed $v: ${decision#remove }"; removed=$((removed+1))
    else
      echo "skip $v: in use, skipped (${err%%$'\n'*})"; skipped=$((skipped+1))
    fi
  done < <(docker volume ls -q | tr -d '\r')
  echo "build.sh --prune$([[ $dry == 1 ]] && echo ' --dry-run'): kept $kept, $([[ $dry == 1 ]] && echo 'would remove' || echo removed) $removed, skipped $skipped"
}

if [[ "$WHAT" == "--prune" ]]; then
  [[ $DOCKER == 1 ]] && { echo "build.sh: --prune runs on its own (no --docker)"; exit 2; }
  shift; prune "$@"; exit 0
fi

if [[ $DOCKER == 1 ]]; then
  docker info >/dev/null 2>&1 || { echo "build.sh --docker: $DOCKER_DOWN; fallback: the CI artifact (viewer/README.md)"; exit 2; }
  IMAGE="$(python3 -c "import json,sys; p=json.load(open(sys.argv[1]))['emsdk_image']; print(p['image']+'@'+p['digest'])" "$ROOT/viewer/pins.json")"
  SRC="$ROOT"; command -v cygpath >/dev/null && SRC="$(cygpath -w "$ROOT")"   # Git Bash: docker wants C:\...
  echo "build.sh --docker: $WHAT in $IMAGE"
  # The CMake tree lives in a named volume (a Windows bind mount is slow for thousands of objects); /src is the same path in CI.
  # One volume per checkout (J31 review): worktrees sharing one tree would reuse objects newer than their own sources, and race.
  VOL="$(vol_name "$ROOT")"
  # Labelled with the checkout so --prune can tell when it is gone (J97); `docker run -v` would make it unlabelled. MSYS_NO_PATHCONV keeps
  # the label the same string the hash is made from. Volumes made before J97 stay unlabelled and keep working.
  docker volume inspect "$VOL" >/dev/null 2>&1 || MSYS_NO_PATHCONV=1 docker volume create --label "napoleon.viewer.checkout=$ROOT"     --label "napoleon.viewer.hash=${VOL#"$VOL_PREFIX"-}" "$VOL" >/dev/null
  # MSYS_NO_PATHCONV: Git Bash would rewrite /src and the -v arguments into Windows paths
  MSYS_NO_PATHCONV=1 docker run --rm -v "$SRC:/src" -v "$VOL:/src/build/viewer/cmake" -w /src "$IMAGE" \
    bash viewer/core/build.sh "$WHAT"
  exit $?
fi

build() {
  command -v emcmake >/dev/null || { echo "build.sh: no emcmake: run with --docker (the pinned emsdk image)"; exit 2; }
  python3 "$ROOT/viewer/core/fetch_sources.py"
  emcmake cmake -S "$ROOT/viewer/core" -B "$ROOT/build/viewer/cmake" -DCMAKE_BUILD_TYPE=Release -Wno-dev >/dev/null
  cmake --build "$ROOT/build/viewer/cmake" --target viewer -j"$(nproc)"
  mkdir -p "$OUT"
  cp "$ROOT/build/viewer/cmake/viewer.js" "$ROOT/build/viewer/cmake/viewer.wasm" "$OUT/"
  (cd "$OUT" && sha256sum viewer.js viewer.wasm | tee SHA256SUMS && wc -c viewer.js viewer.wasm)
}

test_() {
  [[ -f "$OUT/viewer.wasm" ]] || { echo "build.sh test: no $OUT/viewer.wasm: run build first"; exit 2; }
  node "$ROOT/viewer/core/tests/lua_numbers.mjs" "$OUT/viewer.js"
}

case "$WHAT" in
  build) build ;;
  test) test_ ;;
  all) build; test_ ;;
  *) echo "build.sh: unknown target $WHAT (build|test|all)"; exit 2 ;;
esac
