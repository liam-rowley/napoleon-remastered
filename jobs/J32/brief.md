# J32: Viewer parity and panel-host route spikes (S3, S4)

Phase 5, foundation (`docs/plans/UI_PIPELINE.md` section 4, spikes S3 and S4). Two questions must be answered before the panel host (J35)
is briefed. **S3:** how far apart are the review viewer (RmlUi 6.3 in WebGL, J31) and the game (the same RmlUi on J30's D3D9 render
interface)? Layout is RmlUi's own, so only rasterising should differ; anything else is explained before screen work, and the answer
becomes the threshold of the `verified` gate. **S4:** for each screen kind (panel, popup, HUD, front end), does a rebuilt screen keep the
vanilla screen alive but undrawn and borrow its logic, or call the engine directly? Stop and redesign if either route needs per-screen
plumbing. This job measures and proposes. It merges no DLL input and builds no screen.

Model: Opus, reason: an independent check across two renderers and the engine's Lua and draw internals (D15: DLL hooks, reverse engineering).
Budget about 300 tool calls; at the cap, stop, commit, report what is left. Subagents only for independent read-only work. Waiting belongs to
the harness: one background call per sitting, never repeated polling.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J32`). Read `docs/DECISIONS.md` (D2, D6, D9, D19, D37, D38, D39, D51), `docs/plans/UI_PIPELINE.md`
  sections 2.3 to 2.6, 3 (`verified`) and 4.
- The host: `jobs/J30/report.md`, `core/docs/PROXY_UI.md` (the `ui.*` keys, `ctl ui show|hide|dump|state|click`), `proxy/runs/20261103_j30pc/`
  (its `run.py`, checks and crops), `viewer/napoleon/hosttest/` and `tools/ui_hosttest.py` (the crispness checks). Facts
  `napoleon.ui.main_device`, `napoleon.ui.input_path`, `napoleon.ui.lua_state`, `napoleon.ui.present_thread`, `rmlui63.sub_pixel_rule`.
- The viewer: `jobs/J31/report.md`, `viewer/README.md`, `viewer/core/render.py`, `viewer/pins.json`. The library and board: `jobs/J34/report.md`
  (its RCSS feature table and the features J30 did not promise: `image-color`, `transform: translateY`, `border-radius`, blurred and alpha
  outer shadows), `uikit/napoleon/README.md`, `viewer/napoleon/board/`. Facts `viewer.rcss.*`.
- Vanilla screens: `discovery/ui/README.md`, `jobs/J10/report.md` and `harness/runs/20261102_j10pc/README.md` (states, drivers, probes, the
  three crash causes and the pid-file rule). Facts `napoleon.ui.screen_routes`, `napoleon.ui.panel_registry`, `napoleon.ui.visible_not_inherited`,
  `napoleon.ui.hud_placeholder_attach`, `napoleon.campaign.panel_routes`, `napoleon.campaign.modal_stops_pump`, `napoleon.lua.loadlib_bridge`,
  `napoleon.lua.update_callbacks`, `napoleon.lua.arg_stream`. `discovery/napoleon/engine_api.json` (getters per state).
- Search first: `python3 core/wsc.py find parity diff dump host route panel getter bridge`.

## Decisions already made for this job
- **No DLL input is merged** (rule 79 does not apply). Probes, drivers and test documents live in `proxy/runs/<YYYYMMDD>_j32pc/` (a runs folder,
  exempt). If a question can only be answered with a DLL change (a draw-skip detour, a new C function for a bridge), build it from a scratch
  branch into your PC scratch folder, run it there, and report the diff as a proposal for J35; never push it to `job/J32`.
- **The game only through `job.sh` and the watcher**, on the installed acceptance kit, headless unless a step needs a visible window. Drivers
  write a pid file and refuse to start beside another (J10's crash cause). Probes send no clicks into destructive popups.
- **S3 test documents.** `viewer/napoleon/hosttest/` (J30's) and the J34 board, staged into `ui.dir` the way `render.py --stage-only` stages
  them. Cells: 1080p x 100 %, 1080p x 85 %, 1440p x 100 %, 4K x 125 %, each rendered by the viewer headless at the game's back-buffer size and
  dp ratio, and in game with `ui.show` and `ctl ui dump`, over the front end and over a battle scene.
- **S3 comparison tool.** Extend `tools/ui_hosttest.py` with a `parity` subcommand (reuse, not a new tool): align the two PNGs, report the
  per-pixel difference, the share of pixels beyond a tolerance, and boxes whose edges moved (layout) as distinct from edge blending
  (rasterising), with crops of the worst areas. Tests in `tests/` on synthetic pairs.
- **S3 recipes checked by name.** Each J34 feature not on J30's list, plus `var()` faction tint, `:focus-visible`, gradients, clip masks, layers,
  the 1 dp rule at dp < 1 (`rmlui63.sub_pixel_rule`) and the 4K x 125 % text height miss: one `engine_facts` row each, saying whether the game
  draws it as the viewer does. In particular try a blurred outer box-shadow in game (the viewer paints it black:
  `viewer.rcss.shadow_needs_background`); the answer decides J69's shadow question.
- **S4 representative screens** (reached live in J10 unless noted). Panel: `campaign.entity_lists` (state `camp_lists`, `camp_panel.lua`).
  Popup: the campaign start popup of state `camp_popup`; also look for a safe route to `common.unit_information` (the proving popup, D51; the
  `UnitInfoPopup` id in `napoleon.ui.panel_registry`) and record it, or why none is safe. HUD: `battle.land_battle_orders` under
  `veneer_DY/orders` (state `hist_deploy`). Front end: `frontend.single_player` (`fe_page.lua`).
- **S4 route A, alive but undrawn.** Per kind: open the vanilla screen as the game does, stop it being drawn, and check that (1) its data still
  updates when the game changes (read its components' text and state from Lua before and after a change), (2) its handlers still work when
  called (`LuaCall`), (3) it takes no mouse or key input, (4) what it still costs per frame. Try Lua-only means first (root `SetVisible(false)`,
  given `napoleon.ui.visible_not_inherited`; moving it off the canvas; alpha), then a DLL draw-skip only as the scratch prototype above.
- **S4 route B, direct.** Per kind: can the screen's fields come from engine getters (`engine_api.json` for that state; the atlas unit's engine
  calls and unresolved fields) and its actions from engine calls, without the vanilla screen? The host's Lua is its own state
  (`napoleon.ui.lua_state`) and release has no dev bridge, so find the release-safe channel from the game's Lua to the host (for example a C
  function registered through `package.loadlib`, `napoleon.lua.loadlib_bridge`), measure its cost per update, and note the pump gaps
  (`napoleon.lua.update_callbacks`: the front end pumps only on the main menu; modal popups stop the campaign pump when windowed).
- **The verdict per kind** is the route that needs no per-screen plumbing (a per-screen list of fields and actions is data, not plumbing;
  per-screen C++, hooks or timing work is plumbing). Write it as a proposed decision row for Liam, unnumbered, in the report.

## Order of work
1. S3 offline: render both documents in the viewer at the four cells; extend `ui_hosttest.py parity`; tests.
2. S3 in game: one sitting over the front end and a battle; dumps; parity numbers; recipe facts.
3. S4 Lua-only probes for all four kinds in one or two sittings; route A checks; route B getter coverage from the registries, then the channel.
4. Any scratch DLL prototype that step 3 shows is needed, one sitting, reported as a proposal.
5. Facts, run README, proposed decision row, report.

## Deliverables
1. `proxy/runs/<YYYYMMDD>_j32pc/README.md`: every sitting, state, dump, sha256 and probe, and the PC end state.
2. `tools/ui_hosttest.py parity` with tests and its tools row updated.
3. `engine_facts` rows with run ids: one per recipe (S3), the parity numbers and the calibrated threshold proposed for the `verified` gate (J80 uses
   it), and per screen kind the route A and route B results (S4).
4. Report: the S3 answer (rasterising only, or what else and why), the threshold, the S4 table (kind, route A result, route B result, verdict),
   any DLL prototype as a proposal for J35, and the proposed decision row.

## PC test
After the last sitting: `job.sh status` shows no lock and the game not running, `pc_deploy.py status` is clean, the exe is vanilla and the
prefs sha256 is unchanged. Any scratch build is uninstalled and named in the run README.

## Kill criteria
- S3: a test document differs in layout (boxes moved, not edges blended) at any cell and the cause is not found after about 40 tool calls: stop
  S3, record the evidence as an open fact, and say in the report that screen work waits for it (UI_PIPELINE section 4).
- S4: both routes need per-screen plumbing for the same kind: stop, report the evidence, and propose the host redesign; J35 is not briefed on
  either route.
- Any probe crashes the game twice from the same call: stop that probe, record the dump ids and the call, move to the next kind.
- At about 270 tool calls with S4 unanswered for a kind: report that kind as open with what is known.

## Open questions
Written here so the builder does not stall; each has a default and goes in the report if it still stands.
- **Mixed routes?** Default: allowed, one route per kind, if each needs no per-screen plumbing.
- **Front end without a pump on its pages?** Default: route B with a host-driven refresh is acceptable for the front end if route A cannot
  update there; say what triggers the refresh.
- **Threshold for `verified`.** Default: the largest difference seen across the four cells on the two documents, plus a margin you justify,
  as a share of pixels beyond a per-channel tolerance.

## Finish
Write `jobs/J32/report.md`: the S3 answer and threshold, the recipe facts, the S4 table and verdicts, any DLL proposal for J35, the proposed
decision row, run ids, deviations from this brief and why, and the open questions that still stand. Run `python3 core/wsc.py jobs check` and
`python3 core/wsc.py gates` before pushing. Then `wsc reg set jobs J32 status=review report=jobs/J32/report.md`.
