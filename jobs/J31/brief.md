# J31: Review viewer build and hosting spikes (S1, S2)

Phase 5, `docs/plans/UI_PIPELINE.md` section 4, spikes S1 and S2. Prove that the review viewer's engine (RmlUi, FreeType and Lua 5.1
with float32 numbers) builds to WebAssembly without Emscripten on the PC, that a hello-world screen runs interactively on the review
surface, and that the same build renders PNGs in headless Chromium. Output: a pinned build recipe, a working hello-world, and two
spike verdicts with evidence. No screens, no design language, no engine stubs beyond what hello-world needs.

Model: Sonnet. No reverse engineering is involved. Budget about 150 tool calls; at the cap, stop, commit, report what is left. At most
2 subagents, only for independent read-only work (for example, reading Empire's RmlUi and Lua build settings). Waiting belongs to the
harness: CI runs and `gh run watch` happen inside one call, never polled with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J31`). Read `docs/DECISIONS.md` (D7, D17, D19, D22, D30, D31) and `docs/plans/UI_PIPELINE.md`
  section 2 (review viewer, scale model) and section 4 (the spikes and their kill criteria, which are this job's).
- Search before writing: `python3 core/wsc.py find rmlui lua wasm viewer playwright docker`. Reuse the proxy's build pattern
  (`proxy/README.md` "Build", `proxy/build.sh --docker`, `.github/workflows/gates.yml`) for the container and CI shape; do not invent a
  second build system. `tools/verbs/setup.py` `check_playwright` already checks Python Playwright with Chromium: use it, do not add
  another browser dependency.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, not the numbers:
  `docs/plans/LEGAL_NOTES.md` (A1: RmlUi 6.3, MIT, FreeType font engine, Lua bindings off), `docs/learnings/LEARNINGS.md` (search
  "RmlUi 6.3", "stb", "Lua 5.1.1"), `docs/learnings/LEARNINGS_ENGINE.md` ("The repo's Lua 5.1 is float32 like the engine"),
  `docs/plans/REMASTER_ROADMAP.md` (Lua 5.1 statically linked, float32), and how Empire's boards were served, if a viewer exists
  there (search `ui_scale_mod/` and `rml_mod/` for "board").

## Target facts
Recorded from Empire and the UI plan; check each again and record the result as an `engine_facts` row with date and run id.
- RmlUi: Empire ships **6.3** (tag `6.3`), Core only, FreeType font engine, Lua bindings off (A1 in Empire's legal notes). Napoleon's
  host (J30) must use the same version the viewer uses.
- Lua: **5.1.x, numbers are float32** in the engine (Napoleon's compiled chunks use a 4-byte number, see `discovery/core/luachunk.py`).
  A viewer on doubles gives different results (Empire's example: 2550 x 0.319999992 = 816, not 815 on doubles).
- Build route: **no Emscripten on the PC** (D30, UI_PIPELINE S1). A container (`ubuntu:24.04` or the official `emscripten/emsdk` image,
  pinned by tag and digest) through Docker Desktop locally (D31), the same recipe on a GitHub Actions `ubuntu-24.04` runner.
- Review surface: a Claude **Artifact** (the D17 review page's home). Its published limits are in the Artifact tool's contract: 16 MB
  per page and per text file, 15 MB per binary file, 255 files and 64 MB per publish, standard web media types only, scripts only from a
  short CDN list with everything else inline or in `files`, private by default. Whether `application/wasm` is accepted, served with the
  right type and allowed to instantiate under the page's security policy is **the S2 question**: measure, do not assume.
- Fonts (D7): TTFs through FreeType. The hello-world uses one open-licence TTF committed with its licence file (name it in the report).

## Decisions already made for this job
- **J31 pins the versions**, not J30: J30 is not briefed and depends on J12 and J13. Pin RmlUi (default 6.3, the Empire version; change
  only with a reason in the report), FreeType, Lua 5.1.x (the exact patch level Empire links: check) and the toolchain image, each by
  tag and sha256 or commit sha, in one committed pin file under `viewer/`. J30 reads that file. A tool fetches the sources by pin; no
  vendored source trees in the repo.
- **Layout**: `viewer/core/` (game-agnostic: build recipe, Dockerfile, wasm glue, headless renderer, the hello-world host page) and
  `viewer/napoleon/` (only what is Napoleon's: font choice, hello-world RML and RCSS). `viewer/core/` is a core candidate.
- **Lua number type**: build Lua with `LUA_NUMBER` as `float` (with the matching number-format and integer-conversion settings), and
  prove it with a test the build runs, not by reading the config (for example, 2550 * 0.319999992 and 16777217 through the built Lua,
  compared with the expected float32 results). The test runs in Node or headless Chromium in CI.
- **One renderer for review and for gates** (UI_PIPELINE section 2): the PNG path in headless Chromium loads the same `.wasm` and the
  same JS glue as the review page, through Python Playwright, and takes the PNG from the canvas at a requested size and dp ratio (the
  D19 ratio = height / 1080 x slider is only an input here).
- **The hello-world** is one RML document with an RCSS stylesheet in `dp` units, one FreeType font, an image, a button with hover and
  pressed states, a scrolling list, and a Lua script that reads a data model and handles a click: enough to show layout, text, input and
  Lua running together. The data model and one engine call are stubbed in Lua inside the viewer.
- **Hosting order** (S2): try the Artifact route first (private artifact; `files` for wasm, font and image; the page loads them by
  relative path). If wasm does not instantiate or is refused, record the exact error and the setting that blocks it, then try one
  variant at most (for example the wasm embedded as base64 under the 16 MB page limit), then take the kill criterion (GitHub Pages).
- **Publish hello-world only.** The artifact holds the test screen, its title says it is a spike, and it stays private; sharing is
  Liam's call. Publishing and updating it is allowed in this job; deleting it is not (report its URL).
- No change to `core/`, `proxy/` or the PC game folder. The game is never launched: `needs_pc` is false.

## Deliverables
1. **Pin file and build recipe** (`viewer/pins.json`, `viewer/core/Dockerfile`, `viewer/core/build.sh --docker`): a local Docker build and
   a CI job produce `viewer.wasm` and `viewer.js`; record the sha256 of both builds (byte-identical is the aim; if not, say what differs
   and whether it matters). The CI job runs on every push that touches `viewer/` and keeps the outputs as workflow artifacts.
2. **Float32 Lua proof**: the number test above, green in CI, and an `engine_facts` row.
3. **Hello-world in the viewer** (`viewer/napoleon/hello/` and the host page in `viewer/core/web/`): loads RML, RCSS, font and image, runs
   the Lua script, handles hover, press, scroll and click, and has the scale picker as a plain input (ratio and size).
4. **Headless renderer** (`viewer/core/render.py`, a registered tool with the standard header): `render.py <rml> --size 1920x1080
   --dp-ratio 1.0 --out x.png`, deterministic (two runs give identical PNG sha256, or the difference is measured and explained: fonts,
   software rendering flags). A CI test renders hello-world at 1080p x 1.0 and 4K x 1.25 and checks it is non-blank, the expected size,
   and that text pixels sit where the layout puts them.
5. **S2 hosting result**: the Artifact route as above, with the verdict and evidence (the URL, what loaded, console and network lines
   captured through Playwright, file sizes against the limits, the wasm size). If it works, say how much of the 64 MB per publish the engine uses
   and what room is left for art. If it fails, build the GitHub Pages fallback as a workflow that publishes `viewer/`; do not enable Pages
   in the repository settings yourself: stop, ask Liam, and record his instruction.
6. **Spike verdicts** in `docs/plans/UI_PIPELINE.md` section 4 (a dated "S1: result" and "S2: result" line each, with run ids) and in
   `engine_facts`, plus a proposed decision for Liam (the route, the pinned versions, one renderer for review and gates; the D-number is
   left to the reviewer).
7. **Registries**: `tools` rows for every new tool (header format `core/warscape/tools.py`); `engine_facts` rows for the Lua number type,
   the wasm size, the artifact wasm result and the render determinism, each with a run id. `python3 core/wsc.py gates --fast` clean.

## PC test
None. Everything runs on Liam's PC through Docker Desktop and local Playwright (D30, D31) and in CI. Local results go in a dated run
folder `viewer/runs/<date>_j31/` with the build log tail, hashes, PNGs and the browser console and network capture.

## Kill criteria
- **S1: no working build in about 2 sessions** (UI_PIPELINE), counted here as about 60 tool calls of build work from the first Docker run.
  Stop and report which of RmlUi, FreeType or Lua fails to build to wasm, with the exact error and what was tried. Propose the plan's
  fallback (a native offline renderer for PNGs, HTML kept only for concepts); do not start it in this job.
- **Float32 Lua cannot be made to match the engine's numbers** after about 15 calls: do not ship a viewer on doubles quietly. Stop,
  record the difference as an open `engine_facts` row, and report; the viewer stays marked "not parity-safe".
- **S2: the hello-world does not run** on the Artifact route after the one variant above: take the plan's fallback (GitHub Pages
  workflow), record the verdict, and stop the Artifact work. Do not try the Artifact route a third way.
- **Headless renders are not repeatable** (the same input gives different pixels) after about 15 calls: record what varies (fonts, GPU,
  flags) and stop; do not loosen the check to hide it.
- **Anything would need a write into the game folder, `core/`, Liam's saves or the repository settings** (including enabling Pages):
  stop and ask Liam.

## Finish
Write `jobs/J31/report.md`. Cover:
- what was built, the pinned versions and their sources, and how to build locally and in CI
- the float32 Lua proof and the render determinism result
- the S1 and S2 verdicts with evidence (run folder, run ids, the artifact URL, sizes against the limits)
- the proposed decision for Liam
- deviations from this brief and why (including that J31, not J30, pins the versions)
- open questions, listed separately for J32 (parity), J34 (library board) and J30 (host version)

Then `wsc reg set jobs J31 status=review report=jobs/J31/report.md`.
