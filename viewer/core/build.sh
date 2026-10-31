#!/usr/bin/env bash
# purpose: build the review viewer (RmlUi + FreeType + float Lua 5.1.1) to build/viewer/out/viewer.js + viewer.wasm and run its Node tests
# usage: viewer/core/build.sh [--docker] [build|test|all]   (--docker: inside the emsdk image pinned in viewer/pins.json, the PC route (D30, D31); default all; prints the sha256 of both outputs)
# when: after any change under viewer/core/ or viewer/pins.json; on the PC always with --docker (no Emscripten on the PC); CI's viewer job runs `--docker all`
# not-a-verb: a build script with a container round trip, like proxy/tools/build.sh; not a registry operation
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKER=0; [[ "${1:-}" == "--docker" ]] && { DOCKER=1; shift; }
WHAT="${1:-all}"
OUT="$ROOT/build/viewer/out"

if [[ $DOCKER == 1 ]]; then
  docker info >/dev/null 2>&1 || { echo "build.sh --docker: Docker is not answering: start Docker Desktop (Linux containers); fallback: the CI artifact (viewer/README.md)"; exit 2; }
  IMAGE="$(python3 -c "import json,sys; p=json.load(open(sys.argv[1]))['emsdk_image']; print(p['image']+'@'+p['digest'])" "$ROOT/viewer/pins.json")"
  SRC="$ROOT"; command -v cygpath >/dev/null && SRC="$(cygpath -w "$ROOT")"   # Git Bash: docker wants C:\...
  echo "build.sh --docker: $WHAT in $IMAGE"
  # The CMake tree lives in a named volume (a Windows bind mount is slow for thousands of objects); /src is the same path in CI.
  # MSYS_NO_PATHCONV: Git Bash would rewrite /src and the -v arguments into Windows paths
  MSYS_NO_PATHCONV=1 docker run --rm -v "$SRC:/src" -v napoleon-viewer-cmake:/src/build/viewer/cmake -w /src "$IMAGE" \
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
