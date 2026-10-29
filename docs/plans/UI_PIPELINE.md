# UI pipeline: from concept to proven in game

Draft 2026-10-28, for Liam's review. Rests on D5-D9 (`docs/DECISIONS.md`): every screen is RmlUi, own design language, a scale
slider, Liam reviews by playing designs, agents own the source.

## 1. What changes from Empire, and why

Empire (2026-10-28): 72 screens in the registry, 9 in game, 2 gold standard, 6 audited, 13 mockups, 42 not started; the first
in-game panels were deleted on 2026-10-24 and are being rebuilt after the design language was reset. Eight statuses and six design
and build skills (about 120 KB of instructions). The causes, and the change for each:

| Empire | Napoleon |
|---|---|
| Boards are browser HTML/CSS; the game is RmlUi RML/RCSS. Every board is translated by hand, and parity is proven again afterwards. Much of the panel learnings is that gap (lint forcing an RCSS subset onto HTML, library CSS pasted into boards, renders without art misleading reviewers, board measurements drifting from the build). | **The design is the build source.** Screens are RML/RCSS from the start, rendered for review by the real RmlUi. Nothing is translated. |
| Visuals first, then fidelity, audit and a verify probe; each later stage can send the board back. | **Data contract first.** Values, interactions and engine questions are settled before any layout. |
| Panels built before the design language and library settled (the 2026-10-24 reset). | **Foundation first.** Design language, component library and panel host are locked before the first screen. |
| Host plumbing found panel by panel (native holes, `panel_manager` hiding popups, pulse gaps, warm-up copies, handlers lost after hide). | **One panel host**, proven on a screen, a popup and a HUD before the second screen; screens never touch plumbing. |
| Review by looking at static boards with scripted clicks. | **Review by playing** the real screen in a browser viewer, with real data and the real view logic. |

## 2. Stage 0: foundation (once, before any screen)

1. **Vanilla UI atlas** (discovery phase, mostly generated from layout dumps, the disassembled UI scripts and a live probe): every
   screen and popup, its elements, the data each element shows and where it comes from, every interaction and the handler behind it,
   its states and its art. It seeds the `ui_elements` registry. It also lists everything the engine draws outside the layout system
   (Empire's battle radar was not a UI component; unit banners, map labels and 3D previews need checking) and decides for each: rebuilt
   in RmlUi from engine data, an engine render target shown inside an RmlUi element, or left engine-drawn (then fonts follow Empire's
   `.cuf` route, D7).
2. **Design language** (D8). Exploration is free and cheap: two or three directions in Claude Design on the same three test screens
   with real data; never translated, only chosen from. The choice is then expressed as **tokens and a component library written in
   RCSS** and shown in the viewer with every state (hover, pressed, disabled, selected, focus-visible). Liam plays the component board
   and locks it.
3. **Panel host** (core RmlUi host plus the Napoleon adapter). One contract for every screen: open and close triggers (the vanilla
   entry points), keeping the vanilla screen's logic alive but never drawn versus calling getters directly (decided by the spike,
   per screen kind), the data feed (diffed updates, never full rebuilds: Empire's battle HUD received 10 updates a second with about
   0.2 % of fields changing), action dispatch to the engine, input routing (clicks not on RmlUi fall through to the 3D world),
   hotkeys (registered in the hotkeys registry), hide and restore, warm-up. **Gate:** one panel, one popup and the battle HUD run on
   it in game with no screen-specific plumbing.
4. **Review viewer** (core). RmlUi, FreeType and Lua 5.1 compiled to WebAssembly, hosted in a review page. It loads a screen's RML,
   RCSS, art and fonts, the screen's own Lua view code, and engine stubs generated from the screen's fixtures. **Playing the design runs
   the shipped view logic against captured data; only the engine is stubbed.** The same build in headless Chromium (Playwright,
   checked by the local setup, J20) renders PNGs for the gates. One renderer serves both review and checks.
5. **Scale model** (D5, D19). Every length in `dp`; reference 1 dp = 1 px at 1080p.
   Runtime dp ratio = (backbuffer height / 1080) × slider, so 100% gives the same physical layout at 1080p, 1440p and 4K. Slider
   85-125 % in 5 % steps, default 100 %. Minimum text 14 dp (about 12 px at 1080p × 85 %). Text is rasterised by FreeType at the
   final size, so it is crisp at every step. Art masters at 2.5× the reference (the largest dp in use, 4K × 125 %), with mipmaps
   for clean downscaling; vanilla art is ML-upscaled then resampled to the master size. Scale follows height, so wider screens get
   more horizontal room: the design gate renders the corners (1080p × 85 %, 4K × 125 %, a 21:9 and a 16:10 shape) and fails on
   clipping or overflow.
6. **Proving screens** (recommended, awaiting Liam's confirmation), in order: a small tabbed info panel (exact pick after the
   atlas) to run the whole loop once; a popup or tooltip (unit info) to prove layering, hover and open/close; the battle HUD
   (10 Hz updates, selection, cards, where Alt-drag lives). Then the HUDs, then the long tail of panels.

## 3. Per screen

Statuses in the `ui_elements` registry; the review page's titles are generated from it, one way only. Every status except
`locked` is set by a tool when its gate passes.

| Status | Work | Gate (machine-checked unless marked) |
|---|---|---|
| `atlas` | the vanilla inventory exists | screen present in the atlas with elements, data and interactions |
| `contract` | **data contract:** model schema with a source per field (getter, db or loc); fixtures captured from the live game (normal cases plus edges: empty lists, longest names, maximum values, negatives); every vanilla interaction marked kept, changed or dropped, with a reason; states; engine questions answered by probe | every field sourced and present in a fixture; every interaction classified; no `open` item in `engine_facts` for this screen |
| `design` | optional free concept sketch (only for genuinely new layouts; never translated), then RML and RCSS assembled from library components, bound to the contract's model, with the view logic in Lua | lint (tokens only, library classes or the screen's prefix, `dp` only, minimum text size, contrast); every fixture renders at slider 1.0, 1.5 and 2.0 with no overflow or clipping (detected by the renderer, not by eye); every kept or changed interaction bound |
| `locked` | Liam plays it in the viewer and locks it | **Liam** |
| `built` | the Lua feeder maps the contract to engine getters and actions; host tests against the stubs; deterministic pack; sha-checked install | host tests green; pack sha recorded; installed sha matches |
| `verified` | the harness opens the screen in game, takes a shot **and captures the live model data at the same moment**; the viewer renders that same data; the images are diffed; every interaction in the contract is walked | diff under the calibrated threshold; interaction walk passes; log clean; frame cost within the UI budget; checker is not the builder |

**Library and token changes:** any change re-renders every screen's fixtures and reports which screens changed. A locked screen
that changed is flagged "changed since lock" for Liam to play again; it is never silently demoted.

**Review loop:** one review page for all screens (D17). It lists screens by status with a fixture picker and a scale picker. Liam plays, then comments on the
page; agents pick up the comments, change the source and republish. Status changes only through the CLI, which regenerates the page.

**Skills:** three instead of Empire's six: `ui-contract`, `ui-screen` (design and wire) and `ui-verify` (the independent check).

## 4. Spikes before stage 0 is committed

| Spike | Question | Kill criterion (proposal) |
|---|---|---|
| S1 viewer build | Do RmlUi (the version the game will use), FreeType and Lua 5.1 build to WebAssembly? Likely in GitHub Actions (or Docker, as the proxy build does, D31), keeping Emscripten off the PC itself. Lua numbers set to match the game's (Empire's Lua was float32). | no working build in about 2 sessions: fall back to a native offline renderer for PNGs and keep HTML only for concepts |
| S2 hosting | Does a review artifact serve the wasm, fonts and art (types and size limits) and run interactively? | a hello-world screen does not run: host the viewer on GitHub Pages instead |
| S3 parity | How far apart are the viewer (WebGL) and the game (D3D9 render interface)? Layout is RmlUi's own, so only rasterising should differ. | a test document differs beyond antialiasing and filtering: find out why before any screen work |
| S4 host | Keep vanilla screens alive but undrawn, or call getters directly? Decide per screen kind (panel, popup, HUD, front end). | either route needs per-screen plumbing: stop and redesign the host |

## 5. Open questions for Liam

1. Confirm the proving screens (section 2.6).
