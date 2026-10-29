#!/usr/bin/env bash
# purpose: build the proxy d3d9.dll (mingw-w64 i686, the release route) and/or build and run the host tests (g++)
# usage: proxy/tools/build.sh [dll|tests|all|smoke|repro] [--adapter napoleon]   (smoke: run the built DLL under wine with a stand-in exe; repro: rebuild from a copy at another path, fail unless byte-identical)   (outputs in build/proxy/; needs g++-mingw-w64-i686 for dll)
# when: after any change under proxy/ (CI runs `all` on every push); the DLL in build/proxy/<adapter>/d3d9.dll is what proxy/tools/pc_deploy.py kits
# not-a-verb: a compiler driver for C++ sources, not a registry operation; CI and agents call it directly
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WHAT="${1:-all}"; ADAPTER="napoleon"
[[ "${2:-}" == "--adapter" ]] && ADAPTER="${3:?adapter name}"
OUT="$ROOT/build/proxy"; mkdir -p "$OUT/$ADAPTER" "$OUT/tests"
# Build id = the last commit that changed the DLL's inputs, not HEAD: a later report or run commit must not change the binary, or
# the DLL tested on the PC is never the head DLL (J1 review finding 2). -dirty when an input has local changes.
DLL_INPUTS=(proxy/core proxy/napoleon proxy/tools/build.sh proxy/tools/fetch_lua.py)
# The build id comes from the commit history: a shallow clone sees HEAD as the last commit touching the inputs and builds a DLL
# whose id is not the tested one (J1 deviation: CI run 40775169543). Refuse instead of building a wrong id.
if [[ "$(git -C "$ROOT" rev-parse --is-shallow-repository 2>/dev/null)" == true ]]; then
  echo "build.sh: $ROOT is a shallow clone: the build id would be wrong. Fetch the history first (git fetch --unshallow, or a bounded"
  echo "          git fetch --depth=1000 origin <branch>; CI: actions/checkout fetch-depth: 0)"; exit 4
fi
BUILD_ID="$(git -C "$ROOT" log -1 --format=%h --abbrev=12 -- "${DLL_INPUTS[@]}" 2>/dev/null || true)"; BUILD_ID="${BUILD_ID:-nogit}"
BUILD_ID="$BUILD_ID$(git -C "$ROOT" diff --quiet HEAD -- "${DLL_INPUTS[@]}" 2>/dev/null || echo -dirty)"

# One compile line for every build (dll and repro): $1 = source root, $2 = output DLL. Uses $CXX, $ADAPTER, $BUILD_ID.
LUA_SRC="$ROOT/build/lua/src"   # proxy/tools/fetch_lua.py: Lua 5.1.1, pinned, patched for the engine
build_dll() {
  local R="$1" O="$2" L="$2.lua"; mkdir -p "$L"
  local CC="${CXX/g++/gcc}"
  for c in lapi lcode ldebug ldo ldump lfunc lgc llex lmem lobject lopcodes lparser lstate lstring ltable ltm lundump lvm lzio lauxlib; do
    "$CC" -std=gnu99 -O2 -w -ffile-prefix-map="$ROOT/build/"= -c -o "$L/$c.o" "$LUA_SRC/$c.c"
  done
  # -win32 thread model (no winpthread DLL), static libgcc/libstdc++ (the DLL depends on system DLLs only), no PE timestamp and
  # relative file names (the same sources give the same bytes: the PC test binary is the CI binary). --disable-auto-image-base: mingw
  # ld otherwise hashes the OUTPUT PATH into the DLL's ImageBase, so the container, CI and a worktree gave three different DLLs for
  # one commit (review of J1, 2026-10-28). `build.sh repro` proves it stays fixed.
  "$CXX" -std=c++17 -O2 -s -shared -Wall -Wextra -Werror -DWSP_BUILD_ID="\"$BUILD_ID\"" -D_WIN32_WINNT=0x0601 -DUNICODE -D_UNICODE \
    -ffile-prefix-map="$R/"= -static-libgcc -static-libstdc++ -Wl,--no-insert-timestamp -Wl,--disable-auto-image-base -Wl,--enable-stdcall-fixup \
    -I"$LUA_SRC" -o "$O" "$R"/proxy/core/*.cpp "$R/proxy/$ADAPTER/adapter.cpp" "$L"/*.o "$R/proxy/core/d3d9.def" -ldbghelp -ladvapi32
}

python3 "$ROOT/proxy/tools/gen_tables.py" --adapter "proxy/$ADAPTER" --check
if [[ "$WHAT" == dll || "$WHAT" == all || "$WHAT" == repro ]]; then python3 "$ROOT/proxy/tools/fetch_lua.py" --out "$ROOT/build/lua" >/dev/null; fi

if [[ "$WHAT" == dll || "$WHAT" == all ]]; then
  CXX="$(command -v i686-w64-mingw32-g++-win32 || command -v i686-w64-mingw32-g++ || true)"
  [[ -n "$CXX" ]] || { echo "build.sh: no i686 mingw-w64 g++ (apt-get install g++-mingw-w64-i686)"; exit 2; }
  build_dll "$ROOT" "$OUT/$ADAPTER/d3d9.dll"
  echo "build.sh: $OUT/$ADAPTER/d3d9.dll build $BUILD_ID sha256 $(sha256sum "$OUT/$ADAPTER/d3d9.dll" | cut -c1-64)"
  if command -v i686-w64-mingw32-objdump >/dev/null; then
    DEPS="$(i686-w64-mingw32-objdump -p "$OUT/$ADAPTER/d3d9.dll" | awk '/DLL Name/{print tolower($3)}' | sort -u | tr '\n' ' ')"
    echo "build.sh: imports $DEPS"
    for d in $DEPS; do case "$d" in kernel32.dll|advapi32.dll|dbghelp.dll|msvcrt.dll|api-ms-win-*) ;; *) echo "build.sh: unexpected import $d"; exit 3;; esac; done
    EXP="$(i686-w64-mingw32-objdump -p "$OUT/$ADAPTER/d3d9.dll" | awk '/\[Ordinal\/Name Pointer\] Table/{f=1;next} f&&NF==0{f=0} f{print $NF}' | sort | tr '\n' ' ')"
    echo "build.sh: exports $EXP"
    for e in $(awk '/^EXPORTS/{f=1;next} f&&NF&&$1!~/^;/{print $1}' "$ROOT/proxy/core/d3d9.def"); do
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

if [[ "$WHAT" == repro ]]; then
  # The same commit must give the same bytes from any checkout path (container, CI runner, worktree): build again from a copy.
  [[ -f "$OUT/$ADAPTER/d3d9.dll" ]] || { echo "build.sh repro: build the dll first"; exit 2; }
  R="$(mktemp -d)/elsewhere_$RANDOM"; mkdir -p "$R"
  cp -a "$ROOT/proxy" "$R/proxy"; mkdir -p "$R/.git"   # no git in the copy: pass the same build id
  CXX="$(command -v i686-w64-mingw32-g++-win32 || command -v i686-w64-mingw32-g++)"
  build_dll "$R" "$R/other.dll"
  if cmp -s "$OUT/$ADAPTER/d3d9.dll" "$R/other.dll"; then echo "build.sh repro: identical from another path"; rm -rf "$(dirname "$R")"
  else echo "build.sh repro: FAILED: the DLL depends on the checkout path"; cmp -l "$OUT/$ADAPTER/d3d9.dll" "$R/other.dll" | head -5; exit 1; fi
fi

if [[ "$WHAT" == smoke ]]; then
  command -v wine >/dev/null || { echo "build.sh smoke: wine not installed (apt-get install wine wine32:i386)"; exit 2; }
  CXX="$(command -v i686-w64-mingw32-g++-win32 || command -v i686-w64-mingw32-g++)"
  G="$OUT/smoke/game"; rm -rf "$OUT/smoke"; mkdir -p "$G"
  "$CXX" -O1 -static -o "$G/Napoleon.exe" "$ROOT/proxy/tests/smoke_host.cpp"
  cp "$OUT/$ADAPTER/d3d9.dll" "$G/"
  run() { (cd "$G" && WINEDEBUG=-all WINEDLLOVERRIDES="d3d9=n,b;winedbg.exe=d" timeout 120 wine Napoleon.exe "$@") ; }
  check() { grep -q "$1" "$G/napoleon_remastered/logs/proxy.log" || { echo "build.sh smoke: '$1' not in the log"; cat "$G/napoleon_remastered/logs/proxy.log"; exit 1; }; }
  # 1) default config: the stand-in exe is not the pinned build -> MISMATCH, pass-through, notice, system fallback (no DXVK), clean detach
  run; check "exe_guard: MISMATCH"; check "PASS-THROUGH"; check "patch_engine: not run"; check "backend: dxvk unavailable"; check "process detach"
  [[ -f "$G/napoleon_remastered/EXE_MISMATCH.txt" ]] || { echo "build.sh smoke: no notice"; exit 1; }
  # 2) developer override + system backend + an unknown key: engine path on, patch engine runs (0 sites), notice removed, unknown key warned
  printf '[proxy]\r\nbackend=system\r\nexe_guard=0\r\nbogus=1\r\n' > "$G/napoleon_remastered.ini"
  run; check "OVERRIDE"; check "patch_engine: nothing to do - 0 sites"; check "unknown key proxy.bogus"; check "removed the stale"; check "process detach"
  [[ -f "$G/napoleon_remastered/logs/proxy.prev.log" ]] || { echo "build.sh smoke: previous log not kept"; exit 1; }
  # 3) forced mismatch wins over the override
  printf '[proxy]\r\nbackend=system\r\nexe_guard=0\r\nexe_guard_force_mismatch=1\r\n' > "$G/napoleon_remastered.ini"
  run; check "FORCED MISMATCH"; check "process detach"
  # 4) crash capture end to end: an access violation in the host -> our filter (still ours at the first create) -> a .dmp named in the log
  printf '[proxy]\r\nbackend=system\r\n' > "$G/napoleon_remastered.ini"
  run crash || true
  check "top-level filter at first Direct3DCreate9: still ours"; check "UNHANDLED exception 0xc0000005"; check "minidump (unhandled) written"
  dmp="$(grep -o 'minidump (unhandled) written: .*' "$G/napoleon_remastered/logs/proxy.log" | sed 's/.*\\//' | tr -d '\r')"
  [[ -s "$G/napoleon_remastered/dumps/$dmp" ]] || { echo "build.sh smoke: the dump the log names ($dmp) is missing or empty"; ls -la "$G/napoleon_remastered/dumps"; exit 1; }
  [[ "$(head -c4 "$G/napoleon_remastered/dumps/$dmp")" == MDMP ]] || { echo "build.sh smoke: $dmp is not a minidump (no MDMP signature)"; exit 1; }
  # 5) the host replaces the top-level filter (as a game may): logged as REPLACED; mode 2 still dumps the first-chance AV
  printf '[proxy]\r\nbackend=system\r\nminidump=2\r\n' > "$G/napoleon_remastered.ini"
  run replace crash || true
  check "top-level filter at first Direct3DCreate9: REPLACED by Napoleon.exe"; check "minidump (first-chance) written"
  echo "build.sh smoke: passed (5 launches under wine, 2 dumps)"
fi
