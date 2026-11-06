# J32 review

## Round 1 (2026-11-06, branch job/J32 at 8a1b978)

**Verdict: merge after fixes.**

S3's answer holds and I reproduced its key numbers from the full dumps. S4's verdicts may well be right, but the HUD's route A verdict skipped a check the brief requires, and the report does not say so. The tool the decision row names as the layout gate misses any move over 3 px. Neither needs new engine work. B1 needs no PC; B2 needs one short sitting, or an honest downgrade.

### Machines
- At the head `8a1b978` (base `bca3b99`, 6 commits behind main): `wsc gates` 13 ok, 2 warn, 0 failed. `wsc policy` refuses only for the missing review and the row status, as it should before a review. CI: 9 checks passed or skipped.
- **Against the latest main (`36923c6`).** CI runs on push only, so no check has seen the merged tree. Trial merge: clean, tree `a611dfc`, no file changed on both sides. `wsc gates` on that tree, as throwaway commit `2a8f24e`: 13 ok, 2 warn, 0 failed, 672 host tests passed, 37 skipped. The two warnings match the head's. This holds for main at `36923c6` only: round 2 must repeat it.
- Rule 79 does not apply: nothing outside `proxy/runs/` under `proxy/`, and no `harness/`, `core/`, `viewer/` or `uikit/` change. No UI baseline change.

### Blockers

**B1. `parity` calls a moved box rasterising once it moved 4 px or more, and that check is the proposed layout gate.** `tools/ui_hosttest.py:200` (`SEARCH = 2`), used at the tile search in `parity_images`.
- What fails: the report (line 27) says "the moved-tile check is the real layout gate", and the decision row sets `verified` to "no moved tile". Only shifts of up to 2 px per axis are tried, so a move is caught only if a 2 px shift removes 60 % of a tile's difference.
- How to see it: a 200 x 60 box on a flat 1920 x 1080 ground, moved diagonally by n px, through `parity_images`:

| n | kind | moved tiles | share beyond |
|---|---|---|---|
| 1, 2 | layout (whole-image offset) | 0 | 0 |
| 3 | layout | 16 | 0.07 % |
| 4 | **raster** | 0 | 0.10 % |
| 8 | **raster** | 0 | 0.19 % |
| 20 | **raster** | 0 | 0.46 % |

  From 4 px up the command exits 0 and the share is far under 2.3 %, so a box 20 px out of place passes `verified`. The tests stop at small shifts, so none shows this.
- A wider search alone is not enough. `count_off` (`tools/ui_hosttest.py:214`) leaves out pixels shifted off the image, so a shift gains from lost rows. With `SEARCH = 10`, the 4K board tile at 1504,2144 reports `layout`, shift 0,10: it is a one-pixel column differing in all 16 rows, and the "gain" is rows dropping off the bottom. Normalise for the pixels counted.
- Fix: catch moves well beyond 3 px (or say what bounds the gate and how larger moves are caught, for example comparing element boxes as `boxes.py` does), with tests at 4, 8 and 20 px and one at an image edge. Rerun the 12 cells and correct the report.
- **The S3 result is not affected:** I reran all 12 cells with `SEARCH = 10`. 11 report no moved tile, and the twelfth is the artefact above.

**B2. Route A's "takes no input" check was never run on the HUD or the front-end page, and the report does not say so.**
- The brief requires check (3) per kind. `hover()` (`proxy/runs/20261106_j32pc/s4.py:188`) is never called from `battle()` (`s4.py:245`), and `probes/fe_s4.lua` has no `MouseOver`. `s4.jsonl`'s 13 hover rows are all panel and popup.
- The HUD is the kind where this matters most: route A is its verdict, and an undrawn bar along the bottom of the screen that still takes clicks would eat orders on the battlefield. The report's table says "Works" (line 48), and open question 1 does not name this gap.
- `napoleon.ui.undraw_means` overclaims. It says all three means leave nothing under the hit test "on the panel, both popups and the page". In the log, all three were tested on the panel only, the popups with `SetVisible` only, and the page not at all. "Opacity still takes the pointer" was also seen on the panel only.
- Fix, either: one short sitting running `over` on `orders` hidden and visible (and on the page if it still matters), or say plainly that it is untested, list it as a deviation, and make it a condition on the HUD line of the decision row. In both cases, narrow the fact to what ran.

### Should-fix

**S1. The panel's unresolved fields are left out, though unresolved fields are why popups lost route B.** `route_b.json` gives `campaign.entity_lists` 11 parameter and 29 upvalue fields unresolved. The report (line 46) says "All 4 getters and 2 actions present", and `napoleon.ui.route_b.coverage` gives the popups' counts but not the panel's. Panel gets B with 40 unresolved, popups get A with 62 and 130. There may be a good reason (list entries carry the fields, or upvalues are view state), but it has to be stated, or the panel verdict is judged by a different rule from the popups'.

**S2. "20 rows" is 10.** Report line 48 and `napoleon.ui.route_a.hud`. Reassembling the `j32snap` lines from `build/j32/s4_battle_proxy.log`, `hud_hidden` against `hud_after_select`: 10 of 50 rows differ, by position and as sets. The likely source is a count of both sides of a diff. The substance holds: the engine does push state into the hidden bar.

**S3. The row-level S4 evidence is not on the branch.** `s4.jsonl` keeps only `snap` counts (`nodes=49 texts=5`), so "10 rows" and "0 of 137 rows changed" cannot be checked from the repo: they are in the `j32snap` lines of the job worktree's proxy logs. S2 could only be found from there. Commit those lines to the run folder (they are small). "137 rows" also reads 138 in the log.

**S4. The interim dp-ratio rule is too narrow.** Report line 27: "a 1440p render must use `--dp-ratio 1.3333334922790527`". That value is right for 1440p x 100 only. Simulating the three float32 steps, the error hits 1440p at 95, 100, 115 and 125 %, and 41 of the 108 combinations of 12 heights and 9 scales, including 900, 1050 and 1200 lines (1200 x 90 gives 1.0000001). 1080p and 4K are clean, and the proposed fix is exact at all 108. Say which cells need it, or how to get the value. Better, since this is a rule a later agent has to remember: until J35's fix, have whatever renders for `verified` compute the game's ratio itself.

**S5. Two report lines need their scope.** Line 16 "battle dumps are byte-identical" is true of the board and recipes only. Host test dumps differ on 73 to 87 % of the screen (the scene shows around its body), and are identical inside the compared rect. The S3 paragraph's SSE build needs the same care as the run README now has: `ui_host.cpp` stayed x87, so the build tested RmlUi's arithmetic, not `UiDpRatio`. Update `viewer.parity.numbers` ("same pixels across scenes and across x87 and SSE builds") to match.

Fixed by me, as a run-folder erratum (`7e48bce`): the README's builds row and its battle dump line. I left `report.md` alone: policy would count this session as an author of it.

### Later
- **The share depends on the area compared.** The board's share is of the whole screen, the host test's of a rect. J80 has to say which applies to a popup, or a small screen will read differently from a full one for the same defect.
- Report line 48 "no frame cost measured" should say measured, no saving: 4.18 open against 4.32 to 4.50 hidden, 2 runs each. "Within noise" (the fact) rests on those 4 numbers.
- The 07:36 launch failed once in `DllMain` before a retry, in the run README and not the report's "no crash or hang". It looks like the known launch flake, but the cause is not shown.
- `tools.ui_hosttest` `last_used` still says 2026-11-02.
- The `--no-gpg-sign` on a scratch commit was disclosed and never pushed. No action.

### Checked and sound
- **The x87 cause of the ratio.** I doubted it, since an SSE host should have changed the ratio. It did not because `ui_host.cpp` was not SSE: `ApplyScale` in both kit DLLs is `fild`, `fdiv dword [1080.0f]`, `fdiv dword [100.0f]`, while the scratch DLL's RmlUi really is SSE (850 `mulss` against 0). The three float32 steps give 1.33333349 for 1440p x 100.
- `board_1440_gameratio.png` against the game dump: 1.0384 %, max 99, no moved tile, as reported. `boxes/` has 507 lines per file. Threshold arithmetic is right (0.0181 + 25 % rounds to 0.023).
- Noise really is zero inside the compared areas: host test rects are identical across scenes and across x87 and SSE at all four cells, as are the board and recipes dumps.
- `recipes_table.json` matches the report's table for the rows I read. 27 new fact rows; 11 recipes named by the brief, each with a row.
- 28 ms is per fetch (`ccost` divides by n). 0.045 us and 0.07 us are from `clock 200000`, repeated at 08:18. Frame numbers match `s4.jsonl`. The unit popup route ran twice. Popups close through their own handlers while hidden.
- The channel not being prototyped is a named deviation, and open questions 1 to 6 are honest about what was not shown.
- Risk-first reading: I picked `parity` (it becomes a gate) and the route A evidence (it sets J35's design). No PC, install or persistent-data code changed.

### For the fix session
Rerun the merged-tree gates if main has moved. No rule changes here, so no other open branch is affected.
