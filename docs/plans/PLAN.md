# Plan

Draft 2026-10-28, for Liam's review. Decisions it rests on are in `docs/DECISIONS.md` (D-numbers below). The evidence behind most
choices is Empire's: `empire-remastered/docs/plans/PIPELINE_V2.md` (the "start again" plan written for this game),
`docs/learnings/RETRO_2026-10-23.md` and `docs/learnings/LEARNINGS*.md`. This doc says what we do differently, not why Empire did
what it did.

## 1. Goals (D1)

| Area | Goal |
|---|---|
| Controls | Alt+drag moves the selected units to the drawn position; Alt+Ctrl+drag rotates them. |
| UI | Every screen rebuilt in RmlUi (D6) in Napoleon's own design language (D8); a scale slider (D5); crisp from 1080p to 4K with no font aliasing; UI art upscaled to be 4K-suitable. |
| Visuals | Imposter (sprite) distance pushed right out; LOD distances pushed out for buildings, trees, ships and the rest; higher-resolution cascaded shadows with no slicing and no blob shadows (D12). |
| Performance | DXVK as the D3D9 backend. |
| Mod | No-touch: `Napoleon.exe` unmodified on disk; runtime patching from the proxy DLL is fine (D2). |

Facts about the target, read from the PC 2026-10-28: `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, PE timestamp
`0x645e917f`, **already large-address-aware** (so no header patch is needed for 4 GB), ASLR on (rebase every static address), NX on.
Vanilla install, no saves yet. The key file (`custom_keys.keys.xml`) binds Alt+1..9 (formations) and Alt+S / Alt+M, as Empire's did.

## 2. Scope

**Section 1 is the whole scope (D14); everything else is out.** The aim is a tight scope and a fast-ish release. For the avoidance
of doubt, out includes: lighting or shader remaster beyond what the shadow work needs, PBR or texture remaster beyond UI art,
upscalers (FSR, DLSS) and the 64-bit bridge, AMD and Intel GPUs (D13), languages other than English, compatibility with overhaul
mods, multiplayer-specific work. Empire's scope grew piece by piece; anything new enters only through a dated decision with its own
kill criterion.

## 3. How the pipeline changes from Empire

Empire's numbers: 1,374 registered tools, about 15 MB of markdown, learnings files of 140-190 KB, about 210 KB of rules and skills an
agent may need to load. Most harness learnings are workarounds every agent must remember (`wait 1600` after a full-res shot,
`waitfor` ignoring its timeout, keys lost during a shader compile, autostart ignoring the map). The changes:

1. **Learnings become code.** A gotcha is fixed in the tool, its default, a guard or a gate; prose is the last resort (`CLAUDE.md`).
2. **One registry framework.** Every registry is its rows (a JSONL file, or one file per row since J55) + a JSON Schema + a generated readable view + a `check` that runs in
   the gates, all behind one CLI with one `find` across every registry. Starting set:

   | Registry | Extra fields beyond id and description |
   |---|---|
   | tools | path, usage, **when to use**, status (`live`, `superseded:<id>`), last used |
   | scenarios | kind (land, siege, naval, campaign, historical), map, pinned time of day and weather, armies or save, camera poses by id, launch recipe, measured load time, good for |
   | assets | pack, path, format, size, hash, role, used by (screen, element), upscale method and status |
   | ui_elements | screen, vanilla source (layout, script), data fields with sources, interactions, **status** (UI_PIPELINE section 3), review link |
   | engine_sites | purpose, RVA, anchor bytes, stock bytes, patch or hook, config key, `verified` (date, run) |
   | config_keys | default, release value, owner, what it does |
   | hotkeys | binding, action, context, source (vanilla key file or mod): a gate fails on any clash |
   | engine_facts | claim, evidence (run id), date, state (`verified`, `open`, `refuted`): replaces prose engine learnings and VERIFY lists |

3. **One CLI, few tools.** Tools are verbs of one CLI wherever they can be; a new standalone tool says in its header why it isn't a
   verb. The tools registry flags tools unused for a set period for retirement.
4. **Doc budget enforced.** A gate fails any living doc over a size cap (proposal: 30 KB) and any undated "verified".
5. **Gates from the first commit.** CI on every push (registries `check`, schemas, strict JSON, Windows paths, doc budget, host
   tests); a pre-push hook for the fast set; PC jobs verify against a baseline file.
6. **Live state stays small (D16).** Empire's `ORCHESTRATOR.md` reached 86 KB of hand-kept prose. Here live state is a job queue
   file (one entry per job: brief, model, budget, PC needed, status, report link) plus a status page generated from it and the
   registries (what is waiting for Liam, PC state, what ran, usage this week). A dispatching chat reads and writes the queue; nobody
   hand-maintains a state document. History goes to dated reports.

## 4. Shared core (D10)

A separate repo, `liam-rowley/warscape-core` (D18; public, D29), that Napoleon pins by version.
Empire is not touched until a quiet time, when it moves onto the core.

| Core (shared) | Per-game adapter (here) |
|---|---|
| Registry framework, CLI, gates, CI templates | registry contents |
| Watcher, game lock, config profiles, headless display kit, PC sync with sha checks | paths, launch arguments |
| Proxy DLL skeleton: backend loading (system d3d9 or DXVK), log, crash capture, exe-identity guard, runtime patch engine, dev control channel | identity pin, engine sites, scene detection |
| Control API (scene, camera, shot, order, pause, speed) and contact sheets | scenario list, camera poses, openers |
| Pack reader, asset indexer, contact-sheet builder, texture upscaling pipeline | pack quirks, roles |
| RmlUi host, component library machinery, design tokens to RCSS, review viewer, fixture capture | design language, screens, data contracts |
| Frame-time and memory capture, A/B and regression diff | budgets, scenes |

Rule: a game repo never patches the core in place; it files a change against the core repo.

Promotion: core candidates are built in this repo under a `*/core/` folder next to their adapter, and move to the core once their
interface has settled, in one promotion job per phase that depends on that phase's gate (phase 1: J12, after the J4 acceptance gate).
Jobs that build heavily on a candidate depend on its promotion job, so their briefs cite core paths from the start.
Promotion rows (2026-11-01): phase 1 was J12; the job pipeline itself (`tools/verbs/jobs.py`, `tools/pr_policy.py`, the CI notifier
and workflows) is still game-side and moves in J62; `discovery/core` in J64 (after the discovery gate J11); `upscale/core` and
`viewer/core` in J63 (after S3 parity, J32). The RmlUi host and panel host (J30, J35) are core candidates from their briefs.

**Next games** (planning chat 2026-11-01, Liam's intent: back-port the core into Empire and start that game fresh; Shogun 2 later).
- Empire restarts as a new consumer repo: `identity.json` for the vanilla `Empire.exe`, `engine_sites` transcribed from
  `empire-remastered` `exe_patches.json` (J6: 23 of 23 guard sites and 33 of 52 patch anchors still hold), a `DevAdapter`, and the
  committed discovery and upscale tools re-run. It starts only after J62 (the pipeline in the core) and after J30 and J35 are
  promoted, so Empire's UI, the part that stalled it, is built once on the shared host; D11 (one game at a time) stands.
- Shogun 2 needs core work before an adapter: its players run the DX11 renderer and the proxy is `d3d9.dll` with
  `IDirect3DDevice9` hooks (core backlog B36, a renderer seam, to be designed when J30 builds the RmlUi render interface); the pack
  reader is PFH0 only (B37, Shogun 2 is PFH2 and PFH3); the ESF tools read ABCA and ABCE only (B38, Shogun 2 saves are ABCF); whether
  its UI still pumps Lua as Napoleon's does is the first probe, since the Lua bridge and dev channel ride on it.

## 5. Phases

**U** = unattended (agents and the PC), **L** = needs Liam. One game at a time (D11); within Napoleon, phases overlap once the
harness gate passes, limited by the two-agent rule and the single PC.

### Phase 1: core and harness (U; tooling first, D3)

- Registry framework, CLI and CI gates in the core; this repo wired to them.
- Proxy `d3d9.dll` skeleton: loads DXVK (pinned release) or the system d3d9, log, WER LocalDumps plus in-process minidump, the
  exe-identity guard (pinned to the sha above; falls back to plain pass-through on any mismatch), and the runtime patch engine
  reading the engine-sites registry.
- Watcher with per-job requests and ids, enforced game lock, hang watchdog, config profiles restored byte for byte, headless virtual
  display (ask early whether it can do 1080p and 1440p: Empire's could only do 4K).
- **Load time:** measure each phase first (process start, intro movies, front end, campaign or battle load, first frame), then cut:
  skip intros, autostart straight into a named scenario with the right map, warm the DXVK state cache, and above all a **warm
  reset** (stay in one process and go back to a known state between checks) instead of a relaunch. Targets set after measuring.
- **Scenario library** in the scenarios registry, each with generated launchers: small, large and 40-unit land battles; fort and
  city sieges; small, large and storm naval battles; Napoleon's historical battles (scripted, so repeatable); campaign saves at the
  start, mid-game and late-game of each campaign. Fixed sky and weather from day one (look for the data-driven randomness in the db
  tables first, as Empire's `battle_sky_types`).
- **Control API** with checked results: `scene <id>`, `cam <pose-id | x y z yaw pitch>`, `shot <name>`, `order ...`, `pause`,
  `speed`, `reset`. Each command waits for its own settle (render thread, shader compiles), checks its own result and fails loudly
  with evidence. `key`, `click` and `wait` remain underneath for probes only. Camera poses are stored by id, never as key-tap scripts.
- Frame-time and memory capture (p50, p99, address space, commit, VRAM) on any scenario and pose.
- **Gate:** an acceptance script runs launch, every scenario kind, a pose, a shot, a warm reset and a relaunch; it passes 20 times in
  a row, and again after every harness or DLL change.

### Phase 2: discovery (U)

Each pass is one agent step with a fixed output format and a committed tool, writing into the registries:
- Empire to Napoleon diff: pack format, layout and template versions, fonts, Lua API, shader set, exe. It lists what carries over
  through an adapter and what is new.
- Asset index and contact sheets (UI first), loc strings, db tables and their reference.
- Shader catalogue and frame anatomy: render targets, the shadow pass, what draws blob shadows and why, matrix registers.
- Engine API surface per screen and game phase, exe string index, the engine sites behind sprite, LOD and shadow settings.
- **Vanilla UI atlas:** every screen's elements, data, interactions, states and art (seeds the ui_elements registry; UI_PIPELINE
  section 2).
- **Gate:** every registry populated and current; briefs cite registry ids, never paths found by searching.

### Phase 3: performance and visuals (U, L to judge)

1. **Baseline:** vanilla D3D9 against stock DXVK across the scenario set (frame time, load time, memory). Every later change is
   reported against this, with a frame-time budget per feature agreed after the baseline.
2. **Shadows:** resolution and fit first (Empire did an 8K map plus a fit fix through runtime exe sites). Cascades are a larger
   change: the engine draws one shadow map, so cascades mean drawing the shadow pass once per cascade with its own light matrix
   (by replaying the pass's draws in the proxy, or by calling the engine's pass again through a runtime hook) and replacing the
   receiving shaders to pick and sample the right cascade. **Spike first**, from the frame anatomy. Kill criterion (proposal): if
   the shadow pass cannot be isolated, or the cascades cost more than the agreed budget in the 40-unit scene, stop and ask; the
   fallback is resolution, fit and filtering.
3. **Distances:** imposter and LOD distances from the engine sites, db tables or preferences that discovery found, pushed in steps,
   each step measured in the 40-unit battle and the largest siege. **Memory gate:** stop at a set headroom below the 4 GB address
   space (DXVK moves most GPU resources out of the process, which is why it comes first).

### Phase 4: controls (U, L to feel)

Go straight to the route that worked on Empire: selection from the engine's card manager, live unit state from memory reads,
orders through the engine's own command path. Skip the battle-script and posted-drag routes that failed there. Port the gesture
state machine and its host tests from Empire's `rml_mod/src/gesture_*.h`. Hazard carried over: Alt plus a remaster hotkey on F4 is
Alt+F4. **Gate:** the hotkeys registry has no clash; host tests green; Liam signs off the feel in a real battle.

### Phase 5: UI (L-heavy)

Foundation first (design language, component library, panel host, review viewer), then screens. The whole process is
`docs/plans/UI_PIPELINE.md`.

**Screen rows (planning step, 2026-11-01).** The queue ends at the three proving screens (J35); no row exists for the screens
themselves, and they are the largest unsized part of the project (Empire: 72 screens, 9 in game). Once J10's atlas lists them, a
`plan/` branch adds one row per screen group (battle HUD, campaign HUD, front end, campaign panels, battle popups and tooltips) in
priority order, each depending on J35, and proposes the release cut in section 6.

### Phase 6: release (designed in phase 1, built throughout)

Zero-touch install and byte-exact uninstall; the exe guard's pass-through as the Steam-update safety net; saves loadable both with
and without the mod; a player support bundle (logs, config, dumps, no personal data); `LICENSES.txt` (DXVK zlib, RmlUi MIT, fonts
OFL, …); versioned releases with generated release notes.

## 6. Open questions for Liam

1. Doc size cap: 30 KB per living doc (dated records exempt), or another number?
2. **Release cut** (2026-11-01). D6 (every screen RmlUi) and D14 (release fast-ish) pull apart on the screen long tail, where
   Empire stalled. Recommended: versioned releases as phase 6 already allows, v0.1 = DXVK, the J16 fix, controls (J29), shadows
   and distances (J24-J27), the upscaled art and the scale slider with the HUDs (J35 and the HUD rows); panels and the front end
   in v0.2 and later. Each version keeps the vanilla screens it has not replaced. Decide before the screen rows are written.
3. **J23 scope** (2026-11-01). The system d3d9 backend cannot launch headless or present through the hooked device (fact
   `napoleon.render.system_backend`, open), so J23 as briefed cannot measure its vanilla half. Recommended: J23 reports DXVK-only
   numbers now and J61 adds the vanilla half after J16; the alternative is J23 waiting on both. J23's `dxvk.conf` defaults should
   also settle the release values players feel: anisotropic filtering, the frame limiter and the present interval (D1 performance).
4. **J30 brief** (2026-11-01): amend it before it starts so the RmlUi render interface sits behind a backend seam (core backlog
   B36), the cheapest point to buy the D3D11 option Shogun 2 needs; or leave J30 as briefed and pay for the seam later.
5. The section 7 candidates: each needs a dated decision with its own kill criterion (D14), or a dated no.

## 7. Candidates outside D1 (not in scope until a dated decision, D14)

Found in the 2026-11-01 planning review; ordered by player value against cost. None is queued. Each would be a row of one or two
jobs on machinery that exists; the kill criterion is the proposal for its decision line.

| Candidate | Why players want it | Mechanism (exists) | Kill criterion |
|---|---|---|---|
| Borderless windowed, alt-tab safe, DPI-aware process | the first thing a 4K player with Windows scaling hits; alt-tab from exclusive fullscreen loses the device | `proxy/src/headless.cpp` already owns window placement and the device guard; a `display.mode` config key | any frame-time cost in the 40-unit scene, or a DXVK present path it cannot keep: stop |
| Skip intro and splash as a player option | seconds off every launch | `dev.skip_intro` exists (J3); a release key | none: a key flip and a release value |
| Shipped `dxvk.conf` release values | visibly better texture filtering, a frame limiter, vsync choice | J23 settles `dxvk.conf` defaults as `config_keys` | belongs to J23 (question 3), not a new job |
| Render-target resolution keys | water reflection and refraction are half-size and the campaign overlay is 2400x1350 (soft at 4K); the shadow map is the only target that does not scale with the backbuffer (J8) | the same patch-site route as the shadow map size (`shadow.map_size_q34`); one `engine_sites` row and key per target | VRAM or frame time over the J23 budget at 4K: keep the stock size |
| Camera feel: pan and zoom speed by height, height limits, free camera | the most-requested NTW mod category after UI | J43's camera route and `cam set`; J29's input hooks for the keys | no setter for the field in question through J43's route: stop |
| Mouse confined to the window for edge scrolling | the cursor escapes to a second monitor at the screen edge | `ClipCursor` in the proxy, released on alt-tab; a key | none: a key with a release value |
| Install option without the UI packs | most players run NTW3 or DarthMod, whose UI layouts a UI pack would override; not compatibility work (section 2 keeps that out), only packaging | J38's installer and J53's per-role packs; the inverse of J53's `--no-proxy` | none: a packaging choice in J38 |
