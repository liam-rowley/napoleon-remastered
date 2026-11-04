# J31 run evidence (2026-10-31)

PC: Docker Desktop 29.6.2, emsdk image pinned in viewer/pins.json; Python Playwright 1.64.1, Chromium 156.0.8078.4 (SwiftShader).
CI: run 41218079368 (commit 33efd77): every job green; artifact `viewer-wasm`.

| File | What |
|---|---|
| build1_local.log | first green Docker build (tail) and the Node float32 test (pre-PNG commit) |
| build3_local.log | build with stb_image and touch input (tail) and the float32 test |
| SHA256SUMS.local | viewer.js / viewer.wasm of the latest local build (touch input) |
| hello_1080p_r1.png, hello_4k_slider125.png | renders of the final build; renders_local.txt has their RGBA and PNG sha256 |
| browser_capture_local.txt | console and network capture of a headless render (Playwright): types served, load order, RmlUi log |

- Byte identity: commit 33efd77 built locally and in CI run 41218079368 gives the same viewer.wasm (039ee66d3ff0...) and viewer.js (697673101181...).
- Render identity: CI's renders of the same commit have 0 differing pixels from the PC's at 1080p x 1.0 and 4K at dp ratio 2.5; the PNG
  files differ (zlib builds), so renders are compared by `rgba_sha256`.
- Repeat runs on the PC: identical PNG sha256 (1080p b60e23e2..., 4K 21a5ad85...).
- S2: https://claude.ai/artifact/EoCR1JcPZH7Rnix9JoKZea (private). Version 1 refused emblem.tga (switched to PNG), then published; served types
  from the artifact's file listing: viewer.wasm application/wasm 2118666 B, font/ttf, image/png, text/plain for RML/RCSS/Lua, 2.43 MB in all.
  Liam's phone check: version 1 drew but did not scroll (no wheel on touch); version 2 (touch drag scrolls, tap clicks) all good.
  The built-in browser pane was not signed in and Claude in Chrome was not connected, so no in-artifact console capture.
