# J31 review

## Round 1 (2026-10-31, branch job/J31 at 1ccd2b9)

**Verdict: merge.**

Independent reviewer (did not build or fix this branch). Read the brief, the report, `docs/DECISIONS.md` and the full diff
(40 files). Machines: `wsc gates` 12 ok (389 host tests; render tests skip locally with no build, they run in CI's `viewer` job);
`pr_policy` refused only for the missing review and row, as expected before this round. CI on every pushed commit is green:
runs 41218079368 (33efd77), 41218866718 (fec72e3), 41219480738 (1ccd2b9, the reviewed head).

### Claims against evidence
- S1 build and byte identity: `viewer/runs/20261031_j31/build1_local.log`, `build3_local.log`, CI run 41218079368. The local
  `SHA256SUMS.local` is the later touch-input build, as the report says, not the 33efd77 hashes; consistent.
- Float32 Lua: `viewer/core/tests/lua_numbers.mjs` runs through the built wasm and fails a double build on the first cases;
  `build.sh all` runs it locally and in CI. `engine_facts` `viewer.lua.number_float32` carries the date and runs.
- Render determinism: `renders_local.txt` gives both sha256s; `test_deterministic` re-renders in CI. The rgba vs PNG-bytes split
  (zlib) is measured and explained, not loosened.
- S2: the artifact URL, stored types and sizes are in the run README and `engine_facts` `viewer.artifact.wasm`; the only
  in-artifact evidence is Liam's phone check, a named deviation (no signed-in browser). Acceptable for a spike; see later item 2.
- The five `engine_facts` rows the brief asks for are present (Lua number type, wasm size, artifact result, determinism, plus the
  RmlUi 5.1 API gap), each with date and run.

### The brief
Every deliverable is present. Deviations are all named with reasons: no Dockerfile (the pinned official image is the toolchain,
as the proxy runs `ubuntu:24.04`), Lua bindings on (needed to run screen Lua; J30 decides for the host), stb_image added to the
pins (the artifact refuses `.tga`), touch input added after the phone check. Nothing touches `core/`, `proxy/` sources or the PC
game folder; `tools/changed_inputs.py` and its test gained a `viewer` set, which is in scope (CI shape).

### Risk-first reading
Picked `viewer/core/build.sh` (runs Docker on the PC with a bind mount of the repo and a persistent volume),
`viewer/core/fetch_sources.py` (network fetches feeding the build) and the CI job. Fetches are pinned and checked (git commit
checked again after checkout; tarball and stb by sha256; tar extraction takes only `lua-5.1.1/src/*.c|h`, so no path escape).
`render.py` serves only on 127.0.0.1 on an ephemeral port. Two findings, fixed on the branch (below).

### Findings

**Blockers:** none.

**Should-fix (fixed on the branch by the reviewer, one commit each):**
1. `viewer/core/build.sh:19` (was `-v napoleon-viewer-cmake:...`): every checkout on the PC shared one named Docker volume for the
   CMake tree. Worktrees are the normal way jobs run here, so worktree B building after A reuses A's objects whenever B's sources are
   older on disk than A's objects (make compares mtimes), giving a wasm that is not built from B's sources; two builds at once also
   race on one tree. To see it: build in one worktree, edit `viewer.cpp` in an older checkout of another, build there: the object is
   not rebuilt. Fixed in e9a88df: the volume name carries a hash of the checkout path. CI is unaffected (fresh runner).
2. `viewer/core/fetch_sources.py:25` `LUACONF` is a copy of `proxy/tools/fetch_lua.py` `PATCHES['luaconf.h']`, and only the tarball
   pin was tested to agree. A change on one side would give the viewer different numbers from the in-game host with every gate
   green. Fixed in 6e5eb81: `tests/test_viewer.py` `test_lua_number_patches_match_proxy` asserts they are equal.

**Should-fix, for Liam (repository settings, not a branch change):**
3. `.github/workflows/gates.yml` job `viewer` is not a required check (`docs/REVIEW.md` lists `gates`, `proxy`, `harness-windows`,
   `policy`). A red viewer build or render test does not stop a merge; only the `notify` comment reports it. Add `viewer` to the
   required checks (skipped counts as passed, as for `proxy`), then add it to the list in `docs/REVIEW.md`.

**Later (this repo):**
1. Per-checkout volumes accumulate on the PC (`docker volume ls | grep napoleon-viewer-cmake-`); a `wsc` clean step or
   `build.sh --prune` can remove volumes whose checkout is gone. The old shared `napoleon-viewer-cmake` volume can be removed by hand.
2. S2 has no console or network capture from inside the artifact. When a session has a signed-in browser, capture it once
   (Playwright or the browser pane) and add it to the run folder; until then the evidence is the stored file listing and Liam's check.
3. The `jobs` row description still says "the version J30 pins"; the brief and `viewer/pins.json` say J31 pins. Fix the row text
   on the next `plan/` branch.

### Proposed decision (D37, for Liam)
**Review viewer route (J31, S1 and S2).** The review viewer is RmlUi 6.3 + FreeType 2.13.3 + Lua 5.1.1 (float32 numbers) built to
WebAssembly in the `emscripten/emsdk:4.0.10` image pinned by digest, on the PC through Docker Desktop and by the same command in CI;
no Emscripten on the PC. `viewer/pins.json` is the one pin file, and the in-game host (J30) builds from it. Review pages are private
Claude Artifacts staged by `viewer/core/render.py --stage-only`; art in them is PNG or JPEG. Gates render through the same wasm and
host page in headless Chromium and compare pixels by `rgba_sha256`. GitHub Pages stays unused.

### Rule change for other branches
None: the `viewer` CI input set only adds a job for branches that touch `viewer/` or `tests/test_viewer.py`.
