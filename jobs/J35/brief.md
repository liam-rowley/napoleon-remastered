# J35: Panel host and its gate

Phase 5, foundation (`docs/plans/UI_PIPELINE.md` section 2.3). One contract for every screen: open and close from the vanilla entry points, the route per kind, a diffed data
feed, action dispatch, input routing, hotkeys through the registry, hide and restore, warm-up. Also the D17 review page and the scale slider. **Gate:** one panel, one popup and
the battle HUD run on it in game with no screen-specific plumbing. D66 accepts J32's routes on one condition: this job proves a real click on a vanilla button and an order through
the hidden bar in a running battle. So those two come first, before any host code, and a failure stops the job.

**Carries 20 passes (rule 79).** The job changes DLL inputs (the host, the core pin) and the UI baseline. Budget the run at about 8 minutes a pass, and a start-up flake restarts the
streak unless the pin holds the core's flake rule (W9, through J78).

Model: Opus, reason: DLL plumbing across screen kinds, input routing and engine Lua internals (D15, D52).
Budget about 400 tool calls, about 120 of them on the PC (J30 and J32 were each briefed at 300; this one has a core half, a PC proof and a 20-pass run, as J30 had, plus J32's
carried items). Subagents only for independent read-only work, at most 4 sessions (D59), and the PC job counts as one. Waiting belongs to the harness: one background call per sitting, never
repeated polling. Every test launch sets `dev.skip_intro=1`.

## Start
- If this session's model is not the row's, stop and say so.
- Follow `CLAUDE.md` (Jobs: branch `job/J35`). Check that J78 is `done` (see Decisions). Read `docs/DECISIONS.md` (D1, D2, D14, D17, D19, D38, D39, D55, D59, D66), `docs/plans/UI_PIPELINE.md`
  sections 2.3 to 2.6 and 3, `docs/REVIEW.md` (rule 79, UI baseline).
- **`jobs/J32/report.md` with its Fix round 1, and `jobs/J32/review.md` round 2, are the state of the world.** Where the fix round differs from the report, it wins; where S6 differs from the
  fix round's end state, S6 wins. Then `jobs/J30/report.md`, `jobs/J34/report.md` (open question 5), `core/docs/PROXY_UI.md`, `core/docs/CONSUMING.md`, `uikit/napoleon/README.md`, `viewer/README.md`.
- The run to reuse: `proxy/runs/20261106_j32pc/` (`README.md`, drivers `s4.py`, `route_b.py`, `boxes.py`, probes `probes/s4.lua`, `probes/fe_s4.lua`, `route_b.json`, `parity_gate.jsonl`).
- Empire, read-only and "port, don't copy": `empire-remastered` `docs/learnings/LEARNINGS.md` section 6, "RmlUi panels" (`--add-dir ../empire-remastered`). Take the failure list (native holes,
  `panel_manager` hiding popups, pulse gaps, warm-up copies, handlers lost after hide). Do not port its per-panel plumbing, its screen code or any address. Every Empire fact is checked again on Napoleon.
- Search first: `python3 core/wsc.py find <words>` for host, input, hotkey, route, panel, popup, tooltip, slider, loadlib, pack.

## Target facts
Check each again before relying on it.
- **Routes:** `napoleon.ui.route_a.panel`, `napoleon.ui.route_a.popup`, `napoleon.ui.route_a.hud`, `napoleon.ui.route_a.front_end`, `napoleon.ui.route_b.coverage`, `napoleon.ui.route_b.channel`,
  `napoleon.ui.undraw_means`, `napoleon.ui.unit_popup_route`.
- **Input:** `napoleon.ui.input_path`, `napoleon.ui.ctl_click_cursor_clamp`, `rmlui63.recipe.focus_visible`.
- **Pump and threads:** `napoleon.campaign.modal_stops_pump`, `napoleon.ui.frontend_credits_stops_pump`, `napoleon.lua.update_callbacks`, `napoleon.lua.loadlib_bridge`, `napoleon.lua.arg_stream`,
  `napoleon.ui.lua_state`, `napoleon.ui.host_lua_libs`, `napoleon.ui.present_thread`, `napoleon.ui.lua_pack_route`.
- **Screens:** `napoleon.ui.screen_routes`, `napoleon.ui.panel_registry`, `napoleon.ui.visible_not_inherited`, `napoleon.ui.hud_placeholder_attach`, `napoleon.ui.loading_and_video`, `napoleon.ui.saved_state`, `napoleon.ui.helper_device_rehook`.
- **The three fixes:** `napoleon.ui.dp_ratio_single_precision`, `napoleon.ui.script_src_absolute_path`, `viewer.clear_order_layers`.
- **Parity:** `viewer.parity.numbers`, and `tools.ui_hosttest` (`parity`, `dp-ratio`).
- **Crash:** `napoleon.proxy.init_heap_corruption` (J78 and J101 own it; here it is a launch risk to name, never to explain away).
- **Rows:** `ui_elements` `campaign.entity_lists`, `common.unit_information`, `campaign.event_message`, `battle.land_battle_orders`, `frontend.single_player`; `config_keys` `ui.scale`, `ui.show`, `ui.enabled`;
  the `hotkeys` registry; scenarios `hist_dresden`, `land_small`.
- **The three proving screens have no contract, design or lock.** Check their `status` in `ui_elements`. The gate therefore runs on proving documents, not on finished screens (Decisions).

## Decisions already made for this job
- **Routes (D66, final unless the proof fails).** Panel and front end on route B: rebuilt on engine getters and actions, fed on open and on events, never per frame; the front end sits over the hidden main
  menu. Popup and HUD on route A: the vanilla screen stays alive, undrawn with `SetVisible(false)`; HUD actions go straight to `BattleUI`. Opacity is never a route. One channel for all: a proxy
  export reached by `package.loadlib` from one packed wrapper.
- **J78 first; the row depends on it.** J35 needs from J78: (1) the pin, because this job's core work arrives on a newer tag and a bump from the old pin would repeat J78's migration; (2) the core's
  `status` stray line and `install --move-stray`, and the `uninstall` guard (W94) if the tag holds it, because J32 left a stray ini through exactly that gap; (3) W9's flake rule for the 20 passes, and W33's
  dev threads off `DllMain`. **J35 needs nothing from J78's row files.**
- **No new decision row.** `docs/DECISIONS.md` is at its size cap, and row files arrive only with the two `meta/` branches after J78 (`jobs/J78/brief.md`, "Decisions as one file per row"). D66 covers the routes
  and the threshold. Nothing here adds a line to that file. If the proof forces a route change, write `## Proposed decision row` in the report for Liam and stop (Kill criteria); do not number or add it.
- **Core and adapter split, as J30 and W2 did.** Game-agnostic host work (contract, channel, diff feed, key routing, the fixes) goes to warscape-core as a W row through the `warscape-core-change` skill and
  arrives with a tag; `core/` is never edited here. The route table, ids and actions are Napoleon's, and are data.
- **"No screen-specific plumbing" is a test, not a claim.** A host test fails if the host, the channel or the wrapper names a screen id, component path or engine action. Each proving screen differs from the next
  only in its data file, and adding the third changes no C++ and no wrapper line.
- **Proving documents, not screens.** Three small documents from `uikit/napoleon/` library classes, each bound to live data, under `viewer/napoleon/`. No contract, no lock, and every `ui_elements` status stays
  where it is. They prove the host and are replaced by the real screens later.
- **The parity gate as J32 left it, not retuned.** `tools/ui_hosttest.py parity`: tolerance 8, share at most 0.023, `kind` not `layout`, the 32 px tile search. Those numbers assume the viewer fix, so it lands first
  (deliverable 3). The gate's stated bound stands (review S7: thin marks, a solid 16 px icon and a text line can read `raster` when moved far): add the element boxes from `boxes.py` to every comparison.
- **J32 left three items "for J80", but J80 merged the day before, so they are ownerless and are J35's:** (1) whatever renders for parity calls `tools/ui_hosttest.py dp-ratio` for the game's value, and that tool
  changes with the fix, because it simulates the old three float steps; (2) which area a popup's share is of (open question 2); (3) the element-box comparison above.
- **D39's engine-drawn routes reviewed at this brief:** nothing in J32 changes them, so the atlas's defaults stand. None is on a proving screen. If one turns out to be, report it.
- **Release stays off.** `ui.*` stays out of the player ini, and the rule-79 run uses the idle host (`ui.enabled=1`, `ui.show` empty), as J30's did.
- **Budgets:** host cost as D38 (1 ms with a document, 0.1 ms idle). A route B full fetch cost 28 ms in J32, so a frame-rate feed is a defect.
- **Game only through `job.sh` and the watcher**, drivers with a pid file, and no clicks into destructive popups. PC experiments under `job.sh scratch J35`.

## Deliverables
1. **The D66 proof, first.** No DLL change, on the kit of the J78 pin, in the run folder. Each check is done visible, hidden, then restored, at the same points:
   - **Real click.** Counts only if the vanilla button's own handler ran and the game state changed; a hit test is not a click (J32 open question 1). A click reaches the engine through the window procedure
     (`napoleon.ui.input_path`). Use a button left of the clamp at x=1824, and find whether the clamp is headless only (`napoleon.ui.ctl_click_cursor_clamp`). Show it on the order bar, and on a popup with a safe handler
     (`napoleon.ui.unit_popup_route`). Hidden: the same click reaches no vanilla handler and falls through to the world.
   - **Order through the hidden bar.** In a running battle, past deployment, on a moving unit: an order through `BattleUI` with the bar hidden changes the unit in a way read back from the engine, with the same order
     with the bar visible as the control. `Current_Selection_Halt` in deployment is not evidence (J32 open question 4). Also show a move or halt and a stance change, not one action.
   - **Route A input checks (review B2, open question 1).** Repeat the hit test per kind, and add keys: a key sent with a route A screen hidden does not reach its handlers, and the vanilla hotkeys in the `hotkeys` registry
     for that context behave as with the screen visible. Narrow `napoleon.ui.undraw_means` to what ran.
   - **Front end.** Does `movie_bg` over the hidden main menu take a real click? Never enter the credits page (`napoleon.ui.frontend_credits_stops_pump`).
2. **The core row.** File the W row with the skill: contract, channel export, diff feed, input and key routing, assert fix, proposals 1 and 2. Bump the pin once the tag exists (rule 79 counts from the last DLL input).
3. **J32's three fixes.** Core `UiDpRatio` in integer maths as J32 proposes; the host file interface maps `|` back to `:` so `<script src>` loads; `viewer_frame` calls `Clear` before `BeginFrame`.
   Then update `tools/ui_hosttest.py dp-ratio` and its tests to the new formula, and `viewer.parity.numbers`. The viewer fix changes the board's pixels, so re-render the baseline; **the reviewer accepts it** (`Baseline accepted:`, `docs/REVIEW.md`), never the builder.
4. **The host contract.** Written in the doc that owns it (`core/docs/PROXY_UI.md`) and in code: open and close from the vanilla entry points, route per kind, data feed as diffs (never full rebuilds), action dispatch,
   hide and restore across loading, video, save and load, and device reset, warm-up, and teardown. State how a call crosses from the game's Lua to the host's on the render thread (`napoleon.ui.lua_state`, `napoleon.ui.present_thread`).
5. **Channel.** The proxy export and the one packed wrapper, behind `napoleon.ui.lua_pack_route`, with a deterministic pack and sha-checked install. Measure the real cost; J32's numbers are estimates from the dev bridge. Any engine address goes in `engine_sites` with anchor bytes (D2).
6. **Route data.** One data file per proving screen: `campaign.entity_lists` (panel), `common.unit_information` (popup) and `battle.land_battle_orders` (HUD, 10 Hz diffs, with the changed-field share measured), and the route for
   `campaign.event_message`, which is the engine-raised case. Add a `frontend.single_player` entry only as far as deliverable 1 and the contract need. Show an outside change reaching the panel through the event feed (J32 open question 2). Keep the per-field split in the evidence (review Later, `route_b.json`).
7. **Popup flash (J32 open question 3).** Count the presented frames an engine-raised popup is drawn before the hide, over at least 10 raises, with shots. Say what bounds it. If the count is above zero, propose a fix that needs no per-screen code.
8. **Windowed modal pump (J32 open question 6).** Retest `napoleon.campaign.modal_stops_pump` in a visible window, focused and unfocused, with route A's popup handlers running. If the pump stops, the hide of deliverable 7 does too: say what the player sees and fix it in the host.
9. **Key routing.** Keys to RmlUi by focus, the rest to the engine (DirectInput carries the keyboard), hotkeys registered in the `hotkeys` registry with no collision, and Tab so the live `:focus-visible` state is reached in game (J32 open question 5). Update `rmlui63.recipe.focus_visible`. Tooltip behaviour (delay, placement, the middle-click lock) is the host's (J34 open question 5).
10. **Exit assert (J32 open question 7).** Find what holds the objects behind `RMLUI_ASSERT(num_allocated_objects == 0)` and fix the teardown, or show with evidence why it is harmless and silence nothing until then.
11. **Scale slider.** D19 values: 85-125 % in 5 % steps, default 100 %, applied live, kept across a restart, all through `ui.scale`.
12. **D17 review page.** Generated from `ui_elements`, one way only: the screen list with statuses, the player, fixture and scale pickers, comments tagged by screen. Status changes only through the CLI, which regenerates the page. A private artifact. Do not duplicate J99's vanilla reference page. New tool: header and `tools` row.
13. **The gate.** Each proving document in game at 1080p x 100 and 1440p x 100, DXVK, with live data, opening and closing from its vanilla entry point: shots looked at and said to be, input walked, log clean, cost within budget. Parity against the viewer on the same data, per cell, with the game's ratio. **A transparent document over a scene was not measured by J32** and the HUD is one: compare inside its opaque parts and say which, and report the rest as a limit of the gate.
14. **Rule 79.** 20 consecutive passes on the final build id, evidence committed on the branch. Then update `docs/plans/UI_PIPELINE.md` (the J32 S4 line "the decision row waits on Liam" is out of date: D66), the facts and the rows the job changed.

## PC test
Preflight, each sitting:
1. `python3 core/proxy/tools/pc_deploy.py status`: exe vanilla, no foreign or stray files, nothing installed by another job. Stop if another job's kit is there. A stray mod ini is cleared with `install --move-stray`, and named in the report.
2. `core/harness/job.sh status`: watcher version, lock free. `python3 core/wsc.py find hist_dresden land_small` for the scenario rows.
3. The game is launched and killed only through `job.sh`; the hook denies anything else.

**End of each sitting, in this order (review S6):** free the lock, let the watcher restore finish, then `pc_deploy.py uninstall`, then `status`, and read the folder and the prefs **after** the restore. An end state is a reading with a time, taken last.

Evidence: `proxy/runs/<YYYYMMDD>_j35pc/README.md`, whose paths exist; rule 79 under `harness/runs/`. Every `failed` ctl result in a cited run is named under `## Deviations from the brief and why`, and so is every launch that died and was retried, with its dump code. "No crash" covers launches or says it does not. Every "verified" carries a date and run id.

## Out of scope
- Real screens: contracts, RML design, locks, `ui_elements` status moves, and the HUDs and panels after the gate (`napoleon-ui-contract`, `napoleon-ui-screen`, J69).
- The start-up crash (J101), retuning the parity numbers, lint rule 6, and CI wiring of the parity tool.
- Shipping the UI to players; anything outside D1 (D14); editing `core/`; a `docs/DECISIONS.md` line.
- J32 open question 8 (the generated `ui_elements` note on the unit popup waits for the next atlas run).

## Open questions
1. Where does the player reach the slider? recommended: a small host document opened by a registered hotkey, until a real options screen exists; default after: 2026-11-20; `taste`.
2. For a popup, what is the parity share a share of? recommended: the document root's box from `boxes.py`, with the whole-screen share reported beside it; default after: 2026-11-20.
3. How many flash frames may an engine-raised popup show? recommended: 0, and any other number goes to Liam with the shots; `taste`, never defaults.

## Kill criteria
- Deliverable 1, real click: the handler does not run with the screen visible after the windowed attempt, or a hidden route A screen still takes the click: stop, commit the run, report. No host code first.
- Deliverable 1, order: no action read back in a running battle with the bar hidden while the visible control works: stop and write `## Proposed decision row` for the HUD route. A scenario that cannot pass deployment after two sittings: stop and report.
- The host test finds a screen id in the host and no data route removes it, for any kind (the S4 criterion): stop and redesign with Liam.
- `pc_deploy.py status` reports a non-vanilla exe: stop and report.
- `tools/ui_hosttest.py parity` reads `layout`, or over 0.023, on a proving document after the three fixes: stop and find the cause. Do not change the numbers.
- D38's host budget is broken in a `ui state` reading with the document shown: stop the gate and report the cost.
- The streak needs a third run of 20: stop, commit the ledger, report.
- Over about 400 tool calls: stop, commit, report what is left.

## Finish
- `jobs/J35/report.md` with `## What was built`, `## Evidence`, `## Deviations from the brief and why` and `## Open questions`. It must also give: the D66 verdict in one line for each of the two conditions with its run id; an answer for each of J32's open questions 1 to 7; the flash count; the W row and tag; the pack sha; the final build id; whether a `## Proposed decision row` is needed.
- `python3 core/wsc.py jobs usage J35 --write` if the pinned core has the verb.
- `python3 core/wsc.py gates`, `python3 core/wsc.py policy --branch job/J35 --base origin/main`.
- `wsc reg set jobs J35 status=review report=jobs/J35/report.md`

## Registry gaps
