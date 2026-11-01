# J30: RmlUi host in the proxy

Phase 5, foundation (`docs/plans/UI_PIPELINE.md` section 2.3, the part below the panel host). Put RmlUi inside the proxy DLL: a D3D9 render
interface (DXVK and system d3d9), FreeType fonts, a Lua 5.1 binding with the game's number type, input routing, and the D19 scale model.
The proof is one test document drawn over the front end, the campaign map and a battle, crisp at 1080p, 1440p and 4K, with its frame cost
measured. No screens, no panel host (J35), no parity verdict (J32), no tokens or library (J34), no game data feed.

Model: Opus, reason: DLL work in a 32-bit process across the D3D9 device, DXVK and the input path, an engine Lua state shared with a second
Lua user, and crash risk at start-up (D15). Budget about 300 tool calls; at the cap, stop, commit, report what is left. Subagents only for
independent read-only work (for example reading Empire's `input.cpp` and `overlay.cpp` against the core while you build). Waiting belongs
to the harness: `job.sh`, `ctl.py` and the acceptance runner block or run in the background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J30`; "The core": the host is made in a separate `warscape-core` clone beside this one, on a branch,
  as a pull request, and arrives here as a new tag and a pin bump, `core/docs/CONSUMING.md`). Read `docs/DECISIONS.md` (D2, D5, D6, D7, D15,
  D19, D22, D26, D31, D32, D37), `docs/plans/UI_PIPELINE.md` sections 2.3, 2.5 and 4 (S3 and S4 are J32's, not yours), and:
  - `jobs/J31/report.md` and `viewer/README.md`: the viewer you must stay in step with. `viewer/pins.json` is the one pin file (RmlUi 6.3
    `ba95ffe8`, FreeType 2.13.3, Lua 5.1.1 float, stb_image `f0569113`); `viewer/core/fetch_sources.py` fetches by pin (reuse it: one fetcher,
    one pin file); `viewer/core/src/lua51_compat.h` is what RmlUi's Lua bindings need on 5.1; `viewer/napoleon/hello/` is the test screen.
  - `jobs/J12/report.md` (the core layout, how a core change is made and proved pure), `jobs/J13/report.md` (the device, windows and input the
    headless layer already owns, and the tiny windowed helper device the battle loader creates), `jobs/J16/brief.md` (queued: device `Reset`
    and recreation; your resource release and rebuild must match what it finds, rebase on `main` before the pull request).
  - `proxy/README.md` ("Hooks", "Dev control channel", "Headless"), `harness/README.md` ("Control API and acceptance"), and in the core
    `proxy/src/{hooks,dev,headless,luabridge,devcore,runtime}.*`, `proxy/tools/{build.sh,build_id.py,fetch_lua.py,layout.py,pc_deploy.py}`.
- Search before writing: `python3 core/wsc.py find present vtable hook lua dinput window cursor scale rml viewer shot perf`. The one Present
  hook chain, the Lua core with the engine's `dummynode`, the ctl channel and the `[dev]` key pattern exist: extend them.
- Prior art in `empire-remastered` (read-only: never edit, commit or push there). Port the host design, then check every fact on Napoleon:
  `rml_mod/src/{rml_render_d3d9.h/.cpp (shader render interface with layers, filters, clip masks), rml_system.cpp, overlay.cpp (init on device
  creation, dp ratio, Reset handling, frame pass), input.cpp (WndProc subclass + DirectInput arbitration, engine pointer capture), hooks.cpp
  (Present ordering), lua_model.cpp}`, `rml_mod/src/CMakeLists.txt`, `rml_mod/docs/UI_PERF.md` (nested flex relayout cost: a trap for J34),
  `rml_mod/docs/PANEL_GUIDE.md` "RmlUi gotchas", `docs/learnings/LEARNINGS.md` section 6 (host-affecting lines only).
  **Do not port:** panel manager, warm copies, tip controller, native holes, `rml.*` panel Lua API, gestures, MinHook (D26: IAT and vtable
  hooks only), shader swap. Empire built RmlUi with Lua bindings off; this host turns them on (below).

## Decisions already made for this job
- **Split.** Game-agnostic code goes to warscape-core as a pull request with host tests, then a tag (Liam tags, as in J12) and the pin bump
  here: `proxy/src/ui_*.{h,cpp}` (context and lifecycle, render interface, system interface, input routing as pure decisions plus thin
  Win32 glue, scale model, Lua binding), the `ctl` verbs, the build changes (`build.sh`, `build_id.py`, the fetch step), the core's null
  game so the core's CI builds the host, and a section in the core proxy docs. This repo gets the adapter: config keys, the UI folder name,
  the test document (reuse `viewer/napoleon/hello`, plus a `hosttest` screen only if a probe needs one the viewer need not run), the
  kit's loose UI files, tools rows, `engine_facts`. A game name, path or address never enters the core (the core lint checks).
- **Versions are the viewer's** (D37): RmlUi 6.3, FreeType 2.13.3 (TTF only, no optional deps), Lua 5.1.1 with float32 numbers, stb_image.
  A pin change needs a reason in the report. Sources are fetched by pin, never committed; licences go in the report for J38 (FreeType FTL
  needs an acknowledgement).
- **Build route is D22/D31 unchanged:** mingw-w64 i686, static libgcc/libstdc++, system DLLs only (`build.sh` fails on any other import),
  byte-identical from another path (`build.sh --docker repro`). RmlUi and FreeType compile into the DLL; no precompiled header, no
  absolute paths. If a build step needs CMake, pin it inside the existing container image's apt set. MSVC is not a fallback for this job.
- **Release stays inert:** `ui.enabled` default 0, release 0 (J35 turns it on with the first screen). With it 0 nothing is hooked, loaded or
  allocated and the frame matches the baseline. A dev key names the test document to show at start. All keys are `config_keys` rows
  (`ui.enabled`, `ui.scale`, the test-document key), the shipped ini and the generated adapter tables updated (`gen_tables.py --check`).
- **Hooks:** draw from the existing Present chain (chain like `HeadlessPresent`, one hook per slot), inside the host's own Begin/EndScene,
  after saving and before restoring every piece of device state it touches (state block or explicit; the game's next draw must not notice).
  Hook `IDirect3DDevice9::Reset` [16] to release default-pool resources (layers, post buffers, stencil) before and rebuild after. Attach
  only to the main device (the helper devices of the loader and the Bink path are not the UI's); on a device destroyed and created again,
  release and re-init. Input: subclass the game window (a Win32 subclass, not a detour) and vtable-hook the DirectInput mouse device;
  record which path delivers Napoleon's clicks as an `engine_facts` row before relying on either.
- **Input routing (the contract J35 builds on):** the pointer belongs to RmlUi only while it is over an interactive element; every other
  mouse event, including the move that ends the hover and a press that began on the engine until all buttons are released (Empire's
  pointer-capture rule), reaches the engine unchanged. Wheel goes to RmlUi only over a scrollable element. Keyboard goes to RmlUi only
  while a text field has focus. The decision logic is pure and host-tested (a table of events, hover and capture states -> deliver to
  RmlUi / engine / both); `headless.*` synthetic-input filtering must still let synthetic input reach RmlUi.
- **Scale model (D19) as a pure function with host tests:** dp ratio = backbuffer height / 1080 x `ui.scale` / 100; `ui.scale` is 85-125 in
  steps of 5, default 100, out of range clamped and logged. Re-applied on backbuffer size change and by a ctl verb. Text is rasterised by
  FreeType at the final pixel size and texels map 1:1 to pixels (mind the D3D9 half-pixel offset); art textures get mipmaps and trilinear
  sampling so a 2.5x master downsamples cleanly. Decode PNG, JPEG and TGA with stb_image; DDS is not this job.
- **Lua:** the host runs RmlUi's own Lua bindings (as the viewer does, so a screen's view logic is the same in both) on the proxy's Lua 5.1.1
  float core (`fetch_lua.py`), with the 5-function compat header (carry a copy in the core with a test that it equals
  `viewer/core/src/lua51_compat.h` until the viewer is promoted). Open design point, yours to settle with evidence and record as an
  `engine_facts` row: the core's Lua patches (`g_engine_dummynode`, no GC step) assume the engine's state. Either the host state is created
  only after the sentinel has set the engine's `dummynode` (identity use only; check nothing writes it), or the host links a second copy of the
  core under renamed symbols. The test document must draw with no Lua at all (static RML plus C++-registered events), so the front end,
  where only the main menu pumps Lua, is covered whatever you choose. Whether screens use data models or fed C++ models is J35's call.
- **Lossless capture:** a ctl verb dumps the backbuffer (or a rect) to PNG from the DLL, because `shot.sh` output is lossy; this is the
  evidence J32 will reuse for parity. Keep the writer small (stb_image_write at the same stb commit, added to the pins with a reason).
- Out of scope: any real screen, tokens, component library, tooltips, hotkeys, the panel host's open/close contract, engine-drawn text
  (J37), art loading from packs (J50), promoting `viewer/core` (rule 76 lists it with this work and has no row: say so in the report and
  propose the row; do not move it here).

## Deliverables
1. The core: warscape-core pull request (host, render interface, input routing, scale model, Lua binding, ctl verbs, build and CI changes,
   null-game coverage, host tests, docs section), the tag, and the pin bump here with the adapter's keys. Core `VERSION` and the null game's
   build stay green; `core/proxy/tools/build.sh --docker all` and `repro` pass here after the bump; the DLL imports stay system-only; report
   the DLL size and CI build time before and after.
2. Host tests (C++, run by `build.sh all`): scale model table (1080/1440/2160 and odd heights x 85..125), input routing table, device
   resource lifecycle (release, Reset, recreate, destroyed device) as a state machine with a fake device, document load and event
   dispatch on a null render interface (Empire's `tips_rmlui_check` is the pattern), the float32 Lua number test (the viewer's:
   2550 x 0.319999992 floors to 816), the compat-header equality, and the config key tests.
3. The render interface ported from Empire with its advanced features (layers, filters, clip masks, gradients, box-shadow), shaders built
   per the route you choose (runtime compile through `d3dcompiler_47` loaded at run time, as Empire, or bytecode generated offline and
   committed with a `--check` tool): say which and why; a missing compiler must degrade to a logged "UI off", never a crash.
4. ctl verbs, registered and in the proxy README table, each with a checked result: `ui show|hide|reload <doc>`, `ui scale <percent>`,
   `ui click <x> <y> [button]` (synthetic, through the same routing), `ui dump <name> [rect]`, `ui state` (enabled, device and backbuffer
   size, dp ratio, documents, hovered element, routing counters since start: events delivered to RmlUi and to the engine, per type, and
   frame cost p50/p99/max for update and render over a window you name).
5. The test document through the viewer's files: it shows text at several sizes, a 1 dp rule and box pattern, a 2.5x art master scaled down,
   a hover and a click target (counter), a scrolling list, and a Lua-driven line when Lua is up. Loose UI files install by sha-checked copy
   into the mod folder through `pc_deploy.py` (extend the kit list; uninstall restores byte for byte).
6. Evidence on the PC (below), as a run folder `proxy/runs/<date>_j30pc/` with a README (run ids, build id, sizes, scale, backend), the
   dumps, crops, the cost table and `engine_facts` rows (verified with date and run id, or open with an owner) for: the main device and
   backbuffer; which input path carries clicks; whether the game's depth buffer has stencil; the Lua state decision; where Present runs
   (thread); video (Bink) and loading screens; anything the host had to save and restore.
7. Rule 79: the 20-pass acceptance run on the final DLL build id with the host enabled and no document shown (hooks installed, input routing
   live, nothing drawn), in the background (`core/harness/acceptance.py run --passes 20 --run <id>`). It proves the idle host stays inside the
   baseline thresholds. A pin bump alone would not need it (J58); this one changes the DLL.
8. `jobs/J30/report.md` (Finish), including the numbers J32 and J35 need: the Lua decision, the input path, the frame cost per
   resolution and scene, memory (address space and commit) with the host idle and with the document, and the open questions.

## PC test
All launches through the watcher and `ctl.py`/`job.sh ctl`; Liam is not needed unless a step needs admin. Headless sizes (J13) give 1920x1080,
2560x1440 and 3840x2160. Install the build with the keys on, then:
a) host enabled, no document, every scene of the acceptance order plus the front end: frame equals the baseline (thresholds as J44), `ui state`
   shows zero draws, the log has no error;
b) the test document over the front end (`scene` front end), the campaign map (`campaign_start`) and a battle (`land_small`), at each of the three
   sizes at `ui.scale` 100, and at 1080p/85 and 4K/125: a `ui dump` per cell, crops of the text and rules, and these checks from a committed
   script: the 1 dp rules are solid with no blended edge rows, box edges sit on whole pixels, and text height equals the specified size x dp
   ratio within 1 px (the crispness verdict is Liam's to look at, from the crops; the numbers are yours);
c) interaction in each of the three scenes: `ui click` on the target changes the counter and the engine's counter does not move; a click
   elsewhere moves the engine's and not RmlUi's; a press started on the engine and released over the document stays the engine's; the wheel
   scrolls only the list; the state resumes after `ui hide`, `ui reload` and a warm reset from the battle;
d) frame cost, with `ui.enabled` 0, 1 without a document, and 1 with it, per scene and size, 3 runs each, on DXVK; and the same at 1080p on the
   system d3d9 backend (the render interface must also work there; one front end and one battle suffice);
e) a document left open across a scene change (front end to battle and back) and across the loading screens: no crash, no stale resources
   in the log, no stray draw over a video;
f) the 20-pass acceptance run on the final build; uninstall and compare with the snapshot (J44 step f).

## Kill criteria
- RmlUi or FreeType does not build into the mingw DLL with system-only imports and a byte-identical `repro` after 3 attempts: stop, report
  the exact failure and propose a route (do not switch toolchain on your own).
- Any start-up crash or hang with `ui.enabled=1` and no document, twice: stop, collect WER dumps, report; do not keep relaunching.
- With the host idle, a scene's shot or load time falls outside the baseline thresholds: stop, fix or report; a host that changes what it
  measures is worthless.
- The Lua state cannot coexist with the engine's after about 30 calls on it (both routes tried): ship the Lua-free path and the host, mark the
  binding open with the evidence, and finish the other deliverables.
- The test document costs more than 2 ms p50 at 4K on DXVK after one profiling pass (a provisional figure, see Open questions): stop and
  report with a per-phase breakdown; do not optimise without Liam.
- The 20-pass run fails twice for a cause in the host: stop and report; do not keep re-running.

## Open questions
**Settled by Liam 2026-11-01 (D38):** the UI frame-cost budget is 1 ms p50 for this document at 4K and 0.1 ms for the idle host; 2 ms stays the hard stop. Report the measured numbers against it. Propose the `viewer/core` promotion row as below.
- The UI frame-cost budget is not set yet (UI_PIPELINE names one without a number). 1 ms p50 for this document at 4K and 0.1 ms for the idle
  host are proposals; report the measured numbers so Liam can set it. The 2 ms kill figure is the only hard stop here.
- `viewer/core` has no promotion row (rule 76, `PROMOTIONS` in `tools/verbs/jobs.py`); the host needs its fetcher and compat header. Propose
  the row in the report; if the core's CI cannot fetch sources without it, promote only `fetch_sources.py` and say so.

## Finish
Write `jobs/J30/report.md`: what was built (core PR and tag, tools, keys), the evidence with run ids, the Lua decision, the numbers for J32
and J35, deviations from this brief and why, and open questions. Then `wsc reg set jobs J30 status=review report=jobs/J30/report.md`.
