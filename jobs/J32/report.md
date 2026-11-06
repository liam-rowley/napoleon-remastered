# J32 report: Viewer parity and panel-host route spikes (S3, S4)

S3: the viewer and the game differ only in rasterising, once one float step in the host's dp ratio is accounted for, and the proposed `verified` threshold is 2.3 % of pixels beyond 8 levels with no moved tile. S4: neither route needs per-screen plumbing for any kind, so J35 can be briefed: panel and front end on route B, popup and HUD on route A. Three small fixes are proposed for J35 and none is merged here. Run `proxy/runs/20261106_j32pc/`.

## What was built
- `tools/ui_hosttest.py parity` with `tests/test_ui_hosttest.py` (10 tests on synthetic pairs) and its tools row. It aligns the pair, counts pixels beyond a tolerance, and tests each 32 px tile for a shift that removes the difference, which is what separates moved content from edge blending.
- The run folder: drivers `s3.py`, `s4.py`, `viewer_cells.py`, `boxes.py`, `route_b.py`, `recipes_table.py`; the probes `probes/s4.lua` and `fe_s4.lua`; the recipe document `recipes/`.
- 27 new `engine_facts` rows and a note on `viewer.rcss.shadow_needs_background`. Result lines for S3 and S4 in `docs/plans/UI_PIPELINE.md`.
- No DLL input changed.

## S3 answer
**Rasterising only, after one explained layout cause.**
- **The one layout difference:** at 1440p one board button row sat 1 px off. D3D9 leaves the x87 in 24-bit precision, so `UiDpRatio` gives 1.33333349 where the correct value is 1.33333337. With the viewer at the game's value all 507 boxes match and no tile moves. At 1080p x 85 the boxes already match. My first explanation, x87 against SSE inside RmlUi, was wrong: a scratch SSE build gave byte-identical dumps.
- **A viewer bug, larger than any host difference:** the viewer's black shadows and filters come from `viewer_frame` calling `BeginFrame` before `Clear`. J34's limit on shadows was this bug, not RmlUi. **The game draws blurred, alpha and no-background shadows correctly, which answers J69's shadow question.**
- **What remains is filtering:** the host's mipmapped art, shadow rings that are crisp in game and soft in the viewer at fractional ratios, and curve edges.
- **Scene does not matter:** battle dumps are byte-identical to front-end dumps for these opaque documents. Parity for a document with transparent areas over a scene was not measured.

| cell | board | host test | recipes |
|---|---|---|---|
| 1080p x 100 | 0 | 0.553 % | 0.100 % |
| 1080p x 85 | 1.808 % | 0.578 % | 0.029 % |
| 1440p x 100 | 1.038 % | 0.409 % | 0.035 % |
| 4K x 125 | 0.395 % | 0 | 0.187 % |

Share of pixels more than 8 levels off, with the viewer fix and, for the 1440p board, the game's ratio. The pinned viewer's numbers are in the run README.

**Threshold for `verified`:** per-channel tolerance 8, share beyond it at most **0.023** (the largest seen, 0.0181, plus 25 %), and `kind` not `layout`. Measured noise is zero, so the margin only covers screens denser in rules and art than the board. The share cannot catch small layout errors on its own, so the moved-tile check is the real layout gate. Until the ratio fix lands, a 1440p render must use `--dp-ratio 1.3333334922790527`. The numbers assume the viewer fix.

**Recipes** (one `rmlui63.recipe.*` fact each):

| recipe | game against viewer |
|---|---|
| `image-color`, `var()` tint, gradients, layers, hairline at dp below 1 | same, within 1 level (`image-color` 10 at x 85) |
| `translateY` | same at whole pixels, edges up to 28 levels otherwise |
| `border-radius`, clip mask | same shape, curve edges up to 100 levels |
| blurred, alpha, no-background outer shadow | game right, viewer black until fixed |
| `filter: blur` | works, within 19 levels with the viewer fix |
| 4K x 125 text height miss | same pixels: it is FreeType and the font, not the host |
| `:focus-visible` | **not shown:** the host gives RmlUi no Tab key, so the live state cannot be reached yet |

## S4 answer
Lua alone can undraw a screen: `SetVisible(false)`, `PropagateVisibility(false)` and moving it off canvas all work. Opacity 0 does not, because the screen still takes the pointer. No DLL draw-skip is needed.

| kind | route A (alive, undrawn) | route B (direct) | verdict |
|---|---|---|---|
| Panel `campaign.entity_lists` | Works: text and state kept, tab handler ran hidden, no hit, about +0.1 ms p50 over closed. No outside data change was shown | All 4 getters and 2 actions present; 28 ms per full fetch, so feed on open and on events | **B** |
| Popup `event_message`, `common.unit_information` | Works: both hide, take no pointer, close through their own handler while hidden | 62 and 130 parameter fields unresolved; event popups are raised by the engine | **A** |
| HUD `battle.land_battle_orders` | Works: selecting infantry changed 20 rows of the hidden bar, no frame cost measured | No read getter exists, 25 actions | **A** for state, actions through `BattleUI` |
| Front end `frontend.single_player` | Hides, but nothing updates or acts on a page after the call | No engine call needed: root `LuaCall`s and loc text. The hidden main menu still pumps | **B**, sitting over the hidden main menu |

Mixed routes follow the brief's default. In each case the per-screen part is a list of ids, fields and actions, which is data. **The S4 kill criterion is not met.**

**Channel:** `package.loadlib` of a proxy export, the dev bridge's route, plus one wrapper in a pack. That is one piece of work for all screens. A C call costs about 0.05 us, so the getters dominate. The refresh trigger for the front end is the host's own action, since the pages hold nothing that changes. The safe route to the unit popup is in `napoleon.ui.unit_popup_route`.

## Proposals for J35 (none merged)
1. **Core, `UiDpRatio`:** `return (float)(backbufferHeight * percent) / 108000.0f;` exact in any x87 mode. It changes a DLL input, so rule 79 applies.
2. **Core, host file interface:** map `|` back to `:` so `<script src>` loads (`napoleon.ui.script_src_absolute_path`). Without it no screen with a script file works in game. Also a DLL input.
3. **Viewer, `viewer_frame`:** call `Clear` before `BeginFrame`. The board's pixels change at three corners, so the baseline needs a reviewed accept; lint rule 6 can then relax.

## Proposed decision row (unnumbered, for Liam)
**Panel-host routes (J32).** Panels and the front end are rebuilt on engine getters and actions (route B), fed on open and on events, never per frame; the front end sits over the hidden main menu. Popups and the battle HUD keep the vanilla screen alive and undrawn with `SetVisible(false)` (route A), with HUD actions going straight to `BattleUI`. One release channel serves all of them: a proxy export reached by `package.loadlib` from one packed wrapper. The `verified` gate uses tolerance 8, share at most 0.023, no moved tile. Reversible: yes, per kind.

## Evidence
- Run `20261106_j32pc`: `proxy/runs/20261106_j32pc/README.md` has every sitting, build and sha256. DLL `a005f6cccc17`, kit `kit_20261106T071945Z_b5a7ccec7f29`.
- PC end state, 2026-11-06 08:21 UTC: no lock, game not running, uninstall identical to the snapshot (1564 files), exe vanilla, prefs sha256 `83b9b32b...` unchanged. The scratch kit `kit_20261106T080617Z_af482d0562e0` is uninstalled and named in the run README. No crash or hang.

- Gates, 2026-11-06: `python3 core/wsc.py gates`: 13 ok, 2 warn (`ci_render`'s template note and tests skipped for optional dependencies), 0 failed. `tests.test_ui_hosttest`: 10 passed.

## Deviations from the brief and why
- **No channel prototype.** The dev bridge already proves the mechanism and gives the call cost, so the verdict did not need a new export. The export itself is unbuilt and its cost is an estimate from that bridge.
- **Added a third test document,** `recipes/`, because the board does not hold every recipe the brief names.
- **The cells used `ui scale` at run time** in S3, not a fresh launch per scale. `boxes.py` launched fresh at 85 % and agrees.
- **The box dumps ran on the scratch SSE DLL.** Its dumps are byte-identical to the acceptance DLL's, and its dp ratio was unchanged, so the result stands.
- **Local scratch commit.** The scratch repo under `build/j32/fp` took one local commit so the tracked-sources guard held, with `--no-gpg-sign`, which I had no need to pass. It was never pushed.
- **The viewer build came from CI** for the pinned numbers, and a temporary local edit of `viewer.cpp` made the scratch one; that edit was reverted and is not on the branch.
- **`proxy/runs/.../crops`** hold tiles only; full dumps stay on the PC, as J30's did.

## Open questions
1. **Input is only partly proved.** The pointer evidence is the engine's own hit test. No real click on a vanilla button was shown, because the engine's cursor stopped at x=1824 in the headless launch (`napoleon.ui.ctl_click_cursor_clamp`). Keys into a hidden screen were not tested.
2. **Panel data update.** The hidden panel's data changed through its handler, but no change from outside was shown; selecting an agent altered nothing in it. The HUD did show one. This does not touch the panel's verdict, which is route B.
3. **Popup flash.** An engine-raised popup is hidden only at the next Lua pump, so it may show for a moment. Not measured; J35 should.
4. **`Current_Selection_Halt`** returned cleanly but changed nothing visible in deployment, so an order through `BattleUI` with the bar hidden is not proved in a running battle.
5. **`:focus-visible`** waits on J35's key routing.
6. **Windowed modal pump gap** (`napoleon.campaign.modal_stops_pump`) was not retested; these sittings were headless. It affects route A's popup handlers.
7. **`RMLUI_ASSERT(num_allocated_objects == 0)`** is logged as an error at every exit with the host on. Harmless so far, but it should be looked at.
8. **`ui_elements` still says** `common.unit_information` has no safe route. That row is generated, so the next atlas run should pick up the new fact.
9. **Default still standing:** mixed routes are used, per the brief's default.

## Fix round 1
Everything below replaces the earlier sections where they differ. Those sections stay as written. Run ids: `20261106_j32pc`, sittings `battle2` (09:19 UTC) and `fe3` (09:31 UTC) on the acceptance kit `kit_20261106T071945Z_b5a7ccec7f29`.

**B1, moved boxes (aac278c).** Fixed. A tile now searches 32 px each way and compares shifts by rate, so rows falling off the image gain nothing. The tile must hold contrast in the viewer image, or a shift could only find flat ground. A tile with half its pixels over 64 levels off is `layout` at any distance, with shift `[]`. Tests at 3, 4, 8 and 20 px, along one axis, at three image edges, beyond the search, and for the 4K cut tile.
- The review's box, 200 x 60 on 1920 x 1080: `layout` at every n tried from 1 to 100. Real board content cut from the game dump and moved 4 to 60 px, two boxes: all `layout`.
- The 12 cells rerun (`parity_gate.jsonl`): shares unchanged, no moved tile, and the 4K artefact is gone. The 1440p board at the correct ratio still reports its button row, so the check did not go blind.
- **The gate's bound:** thin or faint content moved more than 32 px can pass, as can a thin mark only one image has. Those need element boxes (`boxes.py`). The 64-level limit is measured: real rasterising reaches 0.23 of a tile at 64 levels but 0.48 at 32, so a 32-level limit called the host test's art layout. That was tried and dropped.
- **One bug the new tests found:** `align` sampled every 4th row, so a rule on a sampled row gave a false whole-image offset. A chosen offset must now hold on every row.

**B2, route A input (80b98e34, 57ccf9aa; sittings `battle2`, `fe3`).** Run, not downgraded.
- **HUD:** 20 points of the bar answered with its own components while visible. Of the 6 kept, `SetVisible`, `PropagateVisibility` and move all read nil, opacity 0 all still answered, and all answered again once restored. Route A's verdict for the HUD stands, and the report's "Works" now has its input check.
- **Front end:** a page's hit test cannot be read, because no Lua runs there after the call. It is untested, and that does not touch the verdict, which is route B. I tested what route B depends on instead, the hidden main menu: its buttons leave the hit test, but `movie_bg` answers at all 4 points tried, not nil. **New for J35:** a rebuilt front end sits on a live background component. Whether it takes a click was not tested.
- `napoleon.ui.undraw_means` is narrowed to what ran, per means and per kind. It is still the hit test, not a real click, and keys were not tried: open question 1 stands.

**S1, panel fields (a977fd7).** All 40 are view state: 12 sort order, 12 tab bookkeeping, 15 template layout arguments and headers, 1 camera constant. None is engine data. On the popups 51 of the unit popup's 62 are details its caller hands it, and nearly all of `event_message`'s 130 are event details the engine passes to its handlers, which no getter returns. So one rule covers every kind: a field counts against route B when it is engine data with no getter. In `napoleon.ui.route_b.coverage`.

**S2, row count (24acccd).** 10 of 50 rows, in the report's terms too: read "10 rows" for "20 rows" in the S4 table.

**S3, row evidence (24acccd).** `j32snap.txt` in the run folder, 135 lines. "137 rows" is 138, corrected in `napoleon.ui.route_a.popup`.

**S4, dp ratio (cd8f8ff).** The rule is now code: `tools/ui_hosttest.py dp-ratio <height> <percent>` gives the game's value for any cell, and reproduces the review's 41 of 108. It replaces the report's one 1440p value. `viewer/core/render.py` still takes the ratio from its caller, so **J80 has to call this** until J35's fix lands. I did not change the viewer here, as that would bring rule 79 in.

**S5, scope (3fdc1a0).** "Byte-identical" holds for the board and recipes; the host test matches only inside the compared rect. The SSE build tested RmlUi's arithmetic, not `UiDpRatio`. `viewer.parity.numbers` says both.

**Later items.**
- `tools.ui_hosttest` `last_used` is updated.
- **Corrected:** the report's "no crash or hang" does not cover launches. One launch died in `DllMain` at 07:36 and another at 09:30 in this round, retried both times by `ctl.py`. The 09:30 one left a dump with code `c0000374`, the known `napoleon.proxy.init_heap_corruption`. The 07:36 cause is still not shown, though it has the same symptom.
- **Left for J80:** which area a share is of, for a popup. It is a gate design question.
- **Left:** "no frame cost measured" should read measured, no saving (4.18 open, 4.32 to 4.50 hidden, 2 runs each). The fact already says so.

**Merged tree.** See the last line of this section.

PC end state, 2026-11-06 09:37 UTC: no lock, nothing installed, game folder identical to the snapshot (1564 files), exe vanilla, prefs sha256 `83b9b32b...` restored byte-identical.
