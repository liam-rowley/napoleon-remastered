#!/usr/bin/env bash
# purpose: build the proxy d3d9.dll (mingw-w64 i686, the release route) and/or build and run the host tests (g++)
# usage: proxy/tools/build.sh [dll|tests|all] [--adapter napoleon]   (outputs in build/proxy/; needs g++-mingw-w64-i686 for dll)
# when: after any change under proxy/ (CI runs `all` on every push); the DLL in build/proxy/<adapter>/d3d9.dll is what proxy/tools/pc_deploy.py kits
# not-a-verb: a compiler driver for C++ sources, not a registry operation; CI and agents call it directly
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WHAT="${1:-all}"; ADAPTER="napoleon"
[[ "${2:-}" == "--adapter" ]] && ADAPTER="${3:?adapter name}"
OUT="$ROOT/build/proxy"; mkdir -p "$OUT/$ADAPTER" "$OUT/tests"
BUILD_ID="$(git -C "$ROOT" rev-parse --short=12 HEAD 2>/dev/null || echo nogit)$(git -C "$ROOT" diff --quiet -- proxy 2>/dev/null || echo -dirty)"

python3 "$ROOT/proxy/tools/gen_tables.py" --adapter "proxy/$ADAPTER" --check

if [[ "$WHAT" == dll || "$WHAT" == all ]]; then
  CXX="$(command -v i686-w64-mingw32-g++-win32 || command -v i686-w64-mingw32-g++ || true)"
  [[ -n "$CXX" ]] || { echo "build.sh: no i686 mingw-w64 g++ (apt-get install g++-mingw-w64-i686)"; exit 2; }
  SRC=("$ROOT"/proxy/core/*.cpp "$ROOT/proxy/$ADAPTER/adapter.cpp")
  # -win32 thread model (no winpthread DLL), static libgcc/libstdc++ (the DLL depends on system DLLs only), no PE timestamp and
  # relative file names (the same sources give the same bytes: the PC test binary is the CI binary).
  "$CXX" -std=c++17 -O2 -s -shared -Wall -Wextra -Werror -DWSP_BUILD_ID="\"$BUILD_ID\"" -D_WIN32_WINNT=0x0601 -DUNICODE -D_UNICODE \
    -ffile-prefix-map="$ROOT/"= -static-libgcc -static-libstdc++ -Wl,--no-insert-timestamp -Wl,--enable-stdcall-fixup \
    -o "$OUT/$ADAPTER/d3d9.dll" "${SRC[@]}" "$ROOT/proxy/core/d3d9.def" -ldbghelp
  echo "build.sh: $OUT/$ADAPTER/d3d9.dll build $BUILD_ID sha256 $(sha256sum "$OUT/$ADAPTER/d3d9.dll" | cut -c1-64)"
  if command -v i686-w64-mingw32-objdump >/dev/null; then
    DEPS="$(i686-w64-mingw32-objdump -p "$OUT/$ADAPTER/d3d9.dll" | awk '/DLL Name/{print tolower($3)}' | sort -u | tr '\n' ' ')"
    echo "build.sh: imports $DEPS"
    for d in $DEPS; do case "$d" in kernel32.dll|user32.dll|dbghelp.dll|msvcrt.dll|api-ms-win-*) ;; *) echo "build.sh: unexpected import $d"; exit 3;; esac; done
    EXP="$(i686-w64-mingw32-objdump -p "$OUT/$ADAPTER/d3d9.dll" | awk '/\[Ordinal\/Name Pointer\] Table/{f=1;next} f&&NF==0{exit} f{print $NF}' | sort | tr '\n' ' ')"
    echo "build.sh: exports $EXP"
    for e in $(awk '/^EXPORTS/{f=1;next} f&&NF{print $1}' "$ROOT/proxy/core/d3d9.def"); do
      [[ " $EXP " == *" $e "* ]] || { echo "build.sh: export $e missing (decorated?)"; exit 3; }
    done
  fi
fi

if [[ "$WHAT" == tests || "$WHAT" == all ]]; then
  fail=0
  for t in "$ROOT"/proxy/tests/test_*.cpp; do
    n="$(basename "$t" .cpp)"
    g++ -std=c++17 -O1 -Wall -Wextra -Werror -I"$ROOT/proxy" -o "$OUT/tests/$n" "$t"
    if "$OUT/tests/$n" --root "$ROOT"; then :; else echo "build.sh: $n FAILED"; fail=1; fi
  done
  [[ $fail == 0 ]] && echo "build.sh: host tests passed" || exit 1
fi
