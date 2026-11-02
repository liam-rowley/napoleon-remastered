# J34 run 20261102_j34: the component board at the four D19 corners, and the RCSS spike

Run on the PC (Windows, Docker Desktop for the wasm, Playwright Chromium with SwiftShader) on 2026-11-02, job branch `job/J34`. Commands:
`viewer/core/build.sh --docker all`, `python3 uikit/napoleon/gate.py --out uikit/napoleon/runs/20261102_j34`, `python3 uikit/napoleon/changes.py`.

## Viewer build

| File | sha256 | bytes |
|---|---|---|
| viewer.wasm | `2bdc8a112021772a4e4ad08004bb3e096707f9fcbff95625073f217f478b0f78` | 2122957 |
| viewer.js | `21876236ee8bad99f18159225bf1fb0478abda358fe9c549c9cc081c8288dcd2` | 97837 |

emsdk 4.0.10 image from `viewer/pins.json`, the J31 pins unchanged. J34 added three entry points in `viewer/core/src/viewer.cpp`: `viewer_key` (Tab,
Enter, Space, Escape, arrows), `viewer_overflow_json` (the gate's finder) and `class`, `focus` and `focus_visible` in `viewer_element_json`.

## Board renders (`board_<corner>.png`, the viewport as the player sees it; the page scrolls)

| Corner | Size | dp ratio (D19) | Findings | rgba_sha256 |
|---|---|---|---|---|
| 1080p_85 | 1920x1080 | 0.85 | 0 | `590db96cd44cf0a884c85a476c8f7c515f2d84c7719370e309e7c98f866f9b27` |
| 4k_125 | 3840x2160 | 2.5 | 0 | `b46f4d36ecb8bcb9381a7a64799e5c7d3987ad593c116665250dcf6a44870dac` |
| 21x9_100 | 3440x1440 | 1.3333 | 0 | `1d04e19f61fce24ae658b907a7e695cd21814fbd400ccd72c81a2ffb0dad1d69` |
| 16x10_100 | 1920x1200 | 1.1111 | 0 | `c4970549db45036b99608395d003f55d15aa7ffdf9dadb2d42f424a3d0957869` |

`uikit/napoleon/baseline.json` is the one source of the hashes. The renders are repeatable: `changes.py` run twice gives no change. Files total about 0.53 MB.

Board document load in the viewer (RML, 4 RCSS sheets, Lua, data model, first layout, headless SwiftShader): about 43 ms at every corner; wasm
instantiation 67 to 101 ms. Sheet sizes: base.rcss 920 bytes, library.rcss 12592 bytes, factions_synthetic.rcss 999 bytes.

## Spike (`spike/`)

`python3 uikit/napoleon/runs/20261102_j34/spike/run_spike.py` renders `spike/spike.rml` and prints one line per probe (`results.txt`, picture `spike.png`).
Answers are the `engine_facts` rows `viewer.rcss.*` (custom properties, faction route, library recipes, no text-shadow, shadow needs a background).
