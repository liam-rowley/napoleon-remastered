# J31 report: Review viewer build and hosting spikes (S1, S2)

Both spikes pass. The review viewer (RmlUi 6.3, FreeType 2.13.3, Lua 5.1.1 with float32 numbers) builds to WebAssembly in a pinned
container on the PC and in CI, byte-identical; the same build renders deterministic PNGs headless; and a private Claude Artifact hosts
it interactively. Evidence: `viewer/runs/20261031_j31/` (README there), CI run 41218079368 (commit 33efd77, every job green), artifact
https://claude.ai/artifact/EoCR1JcPZH7Rnix9JoKZea (private), `engine_facts` rows `viewer.*` and `rmlui63.lua51_api_gap`.

## What was built

- **Pins** (`viewer/pins.json`): RmlUi `6.3` at `ba95ffe8bfb6370efb2cdcca927eaad4710c5413` (Empire's version); FreeType `VER-2-13-3` at
  `42608f77f20749dd6ddc9e0536788eaad70ea4b5` (Empire's); Lua 5.1.1 tarball sha256 `c5daeed0...` (the same pin as `proxy/tools/fetch_lua.py`,
  checked by `tests/test_viewer.py`); stb_image.h at `f0569113...` sha256 `594c2fe3...` (Empire's commit; added for PNG art, see Deviations);
  `emscripten/emsdk:4.0.10@sha256:90b757eb...`. `viewer/core/fetch_sources.py` fetches each by commit or sha256 into `build/viewer/src`;
  nothing is vendored.
- **Build** (`viewer/core/build.sh --docker all`, `viewer/core/CMakeLists.txt`): emcmake in the pinned image, CMake tree in a named Docker
  volume (a Windows bind mount is slow), outputs `build/viewer/out/viewer.js` + `viewer.wasm` + `SHA256SUMS`, then the Node number test.
  No Dockerfile: the official image has everything (emcc, cmake, node, git, python), so the script runs it pinned by digest, the way
  `proxy/tools/build.sh` runs `ubuntu:24.04`. CI: job `viewer` in `.github/workflows/gates.yml` (triggered by `viewer/` changes through
  `tools/changed_inputs.py`, which gained a `viewer` set) runs the same command, the viewer tests and two renders, and keeps
  `viewer-wasm` as a workflow artifact.
- **wasm glue** (`viewer/core/src/viewer.cpp`): WebGL2 context, RmlUi's own GL3 renderer (GLES3 path), a PNG/JPEG texture loader
  (stb_image; the backend reads only TGA), Lua bindings, and C entry points for init, fonts, documents, resize and dp ratio, frame, mouse,
  touch scroll (`viewer_scroll_at`), a frozen clock, pixel readback, element boxes and state as JSON, and a Lua eval for tests.
  `viewer/core/src/lua51_compat.h` supplies the five Lua 5.2 names RmlUi 6.3's Lua bindings need (`engine_facts`
  `rmlui63.lua51_api_gap`), force-included so RmlUi stays unpatched.
- **Host page** (`viewer/core/web/index.html`, `viewer_host.js`): loads a screen from `screen/screen.json` into the wasm file system,
  runs frames, routes mouse, wheel and touch (drag scrolls, tap clicks), has the scale picker as plain inputs (width, height, slider %,
  explicit ratio; D19 ratio = height / 1080 x slider), and exposes `window.viewer` for the renderer and tests.
- **Hello-world** (`viewer/napoleon/hello/`): one RML document, RCSS in `dp`, IM FELL English (OFL 1.1, Igino Marini; `viewer/napoleon/fonts/`
  with `OFL.txt`, from google/fonts at `6c1dbe27`), a PNG emblem, a hover/press button, a scrolling list from a Lua data model, and Lua that
  reads the stubbed fixture and handles the click through one stubbed engine call (`stubs.lua`).
- **Headless renderer** (`viewer/core/render.py`, registered): stages the same site the artifact is published from, serves it locally,
  opens it in Playwright's Chromium (SwiftShader), and writes the PNG from the wasm's own readback. `--stage-only <dir>` builds the
  publish folder. Prints `rgba_sha256` (compare across hosts) and the PNG sha256.
- **Tests** (`tests/test_viewer.py`, run by the `tests` gate and CI's viewer job): pins exact and in step with the proxy, build script
  executable in git, font licence present; renders at 1080p x 1.0 and 4K x 125 % (dp ratio 2.5): size, non-blank, title text pixels inside
  the title's layout box and none beside the panel, the PNG emblem drawn; repeat renders identical; hover, press, click (Turn 1 -> 2 and
  the engine stub's message), wheel scroll, touch drag scroll and touch tap. Render tests skip with the reason when the build or
  Playwright is absent.

How to build: `viewer/README.md` (local Docker, CI, `gh run download <run> -n viewer-wasm` as the fallback).

## Proof

- **S1 build:** green on the third Docker build (the first two failed on RmlUi's Lua 5.2 calls; see `engine_facts`), well inside the
  60-call kill budget. Local and CI builds of commit 33efd77 are byte-identical: viewer.wasm `039ee66d3ff0...` (2118666 B), viewer.js
  `697673101181...` (97597 B). The touch-input build is 2118812 + 97679 B (`SHA256SUMS.local`).
- **Float32 Lua:** `viewer/core/tests/lua_numbers.mjs` runs Lua through the built viewer.wasm under Node: `sizeof(lua_Number)=4`,
  `math.floor(2550 * 0.319999992)` = 816 (doubles 815), `16777217 - 16777216` = 0, `string.format("%d", ...)` = 816, `tostring(1/3)` =
  `0.3333333`. Green locally and in CI.
- **Render determinism:** repeat runs on the PC give the same PNG (1080p `b60e23e2...`, 4K `21a5ad85...`). CI's renders of the same commit
  have 0 differing pixels from the PC's, but different PNG bytes: zlib differs between the hosts' Pythons. Hence `rgba_sha256` in
  `render.py` (1080p `389304b5...`, 4K `6e516e2a...`). No flags were loosened.
- **S2 hosting:** artifact version 1 was refused once for `emblem.tga` (the artifact serves web types only), so art moved to PNG through
  stb_image. Republished, the artifact's file listing shows `viewer.wasm` stored as `application/wasm` (2118666 B), the TTF as `font/ttf`,
  the PNG as `image/png`, RML, RCSS and Lua as `text/plain`, 2.43 MB in all (about 4 % of the 64 MB per publish, leaving about 61 MB for art
  and screens; each file far under the 15 MB/16 MB caps). Liam opened it on his phone: version 1 drew the screen (wasm instantiated, WebGL2,
  font, art, Lua all working) but would not scroll. A phone has no wheel, and the host listened only to mouse events. Version 2 adds touch
  (drag scrolls, tap clicks) and passed his check ("All good"). The local Playwright capture of the same site is in `browser_capture_local.txt`.

## Proposed decision for Liam

Review viewer route (UI_PIPELINE 2.4, S1 and S2): the viewer is RmlUi + FreeType + Lua 5.1.1 (float32) built to wasm with the
`emscripten/emsdk` image pinned by digest, through Docker Desktop on the PC and the same command in CI (no Emscripten on the PC); versions
are pinned in `viewer/pins.json` (RmlUi 6.3, FreeType 2.13.3, Lua 5.1.1, stb_image `f0569113`) and the in-game host (J30) builds from the
same pins; review pages are private Claude Artifacts published from `render.py --stage-only`; gates render through the same wasm and page
in headless Chromium and compare pixels (`rgba_sha256`). D-number left to the reviewer.

## Deviations

- **J31 pins the versions, not J30**, as the brief decided; J30 reads `viewer/pins.json`.
- **No `viewer/core/Dockerfile`.** The pinned official emsdk image already holds every tool, so `build.sh --docker` runs it directly (as
  the proxy does with `ubuntu:24.04`). A Dockerfile would add a second image to pin and build for nothing.
- **Lua bindings on in the viewer** (Empire ships them off). The viewer must run each screen's Lua view code, and RmlUi's Lua plugin is the
  route that reached "Lua running" within the spike. Whether the in-game host uses the same plugin or Empire's own Lua API is J30's call
  (open question below); the compat header is the cost of the plugin on 5.1.
- **stb_image added to the pins.** The artifact refuses `.tga`, and RmlUi's GL3 backend loads only TGA, so the viewer decodes PNG/JPEG
  (Empire's stb commit). Not a hosting variant: the wasm itself was never refused.
- **Touch input added after the phone check.** Not in the brief; review happens on a phone too (Liam over Remote Control).
- **S2 console and network capture inside the artifact** were not taken through Playwright: the artifact is private, the built-in browser
  pane was not signed in, and Claude in Chrome was not connected. The evidence is the artifact's stored file listing, Liam's check, and
  the Playwright capture of the identical site served locally.
- `tools/changed_inputs.py` and `tests/test_proxy_host.py` changed (a `viewer` input set) so CI runs the viewer job only when `viewer/`
  changes.
- The jobs registry row's summary says "the version J30 pins"; the brief overrides it (J31 pins).

## Open questions

**For J32 (parity):**
- The viewer draws with RmlUi's GL3 renderer, which has MSAA render layers (`RMLUI_NUM_MSAA_SAMPLES 2`); the game's D3D9 interface will
  differ in antialiasing and filtering. S3 should compare at the rasterising level only.
- Texture filtering and mipmaps: the GL3 backend generates no mipmaps; the 2.5x art masters (D19) need a decision in both renderers.

**For J34 (library board):**
- Every screen needs an RCSS base (RmlUi has no UA stylesheet: `display: block` for `div`, scrollbar parts). The hello-world's few lines
  should become a library base sheet.
- Art in review pages must be PNG or JPEG; DDS masters need a conversion step in staging.

**For J30 (host version):**
- Same RmlUi 6.3 commit as `viewer/pins.json`. Lua bindings: Empire built with them off. If the host turns them on to share the viewer's
  view code, it needs `viewer/core/src/lua51_compat.h` (or the same five functions), and it runs on the engine's own `lua_State` (the
  proxy's dummynode and GC patches in `fetch_lua.py`), unlike the viewer, which owns its state.
- Does the host use RmlUi's Lua data models (as the hello-world does) or feed models from C++? That decides what "the shipped view logic"
  is in the viewer.
