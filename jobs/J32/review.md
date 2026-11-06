# J32 review

## Round 2 (2026-11-06, branch job/J32 at ea7f8d4)

**Verdict: merge.**

Both blockers and all five should-fix items are answered, and the fixes hold when tried independently. One new finding: the report's 09:37 end state is wrong, because J32 left the stray ini in the game folder. It changes no J32 result and the brief's PC test still passes as worded, so it is a should-fix, corrected by erratum. Liam still has to clear the file (below).

### Machines
- At the head `ea7f8d4`: CI, 9 checks passed or skipped (`wsc jobs review`). `wsc policy` refused only for round 1's verdict and the row status, as it should before this review.
- **Against the latest main (`36923c6`, fetched again for this round).** Trial merge: clean, tree `c92f72f5`. `wsc gates` on it as throwaway commit `d99b40d3`, never pushed: 13 ok, 2 warn, 0 failed, 683 host tests passed, 37 skipped. The warnings are `ci_render`'s template note and the skipped tests, as in round 1. This holds for main at `36923c6` only.
- Rule 79 does not apply: no `proxy/` change outside `proxy/runs/`, no `harness/`, `core/`, `viewer/` or `uikit/` change. No UI baseline change.

### Round 1 findings
- **B1, fixed.** My own pairs through `parity_images` on 1920 x 1080: a 200 x 60 box reads `layout` at 1, 3, 4, 8, 20, 32, 33, 40 and 100 px. A text-like line reads `layout` up to 40 px, a 2 px rule up to 32 px, a 16 px icon up to 33 px. A blended edge stays `raster`. `parity_gate.jsonl` has 12 rows: 10 `raster`, 2 `same`, no moved tile.
- **B2, fixed by running it.** `s4.jsonl` from 09:19 UTC, tallied: 20 `hud_points`; of the 6 kept, `hud_vis`, `hud_pvis` and `hud_move` all nil; `hud_alpha` and `hud_restored` all answer. `main_vis` gives `movie_bg` at all 4 points. `napoleon.ui.undraw_means` and `napoleon.ui.route_a.hud` now say what ran. It is still the hit test, not a real click, and open question 1 says so.
- **S1, answered.** The rule and the 40 fields are in `napoleon.ui.route_b.coverage`. The counts add up, but `route_b.json` keeps counts only, so I did not reproduce the 12, 12, 15, 1 split.
- **S2, S3, S5, answered.** 10 of 50 rows and 138 rows are in the facts; `j32snap.txt` has its 135 lines; `viewer.parity.numbers` carries the scope.
- **S4, answered.** `ui_hosttest.py dp-ratio` gives 1.3333334922790527 at 1440 x 100, and off-by-one-step cells at 1440 x 95, 100, 115, 125, as round 1 found. The report rightly says J80 has to call it.
- **Later items:** the launch correction and `last_used` are done; the rest are named as left.

### Should-fix

**S6. The report's PC end state is wrong: J32 left `napoleon_remastered.ini` in the game folder.** `jobs/J32/report.md`, last line of Fix round 1, and the run README.
- **Which step wrote it.** `pc_deploy.py install` put the kit's ini down at 09:19:16 (10914 bytes, sha256 `1cfe08a3...`; `pre_install_20261106T091916Z.json` has no ini). The launch step of `s4.py battle2`, `ctl.py` through `pc_deploy.py set`, added the launch keys at 09:19:23 (10957 bytes, sha256 `aa3e7149...`), which is the file's date. The watcher's `headless` overlay at 09:19:27 saved that file as `mod_ini` in `_saved61106T091927Z_j32`, with the same date and sha.
- **Why nothing removed it.** The fix session ran the steps in the wrong order, in one command: `pc_deploy.py uninstall`, `status`, then `job.sh unlock`. The uninstall at 09:37:18 moved the ini out and said identical, while the profile was active. The lock came free afterwards, and at 09:37:21 the watcher restored the configs it had saved, ini included (`watcher.log`; `restored.json`, 0 mismatches). The restore is doing its job: it puts back what existed when the overlay was applied. An ini was there then, because the kit was installed first. Nothing ran after that to remove it. `play.py` refuses this order (J67), but this was `pc_deploy.py`, which does not (core W94, `needs_brief`). The first end state had it right: lock free 08:22:28, uninstall 08:22:44.
- **Why nobody saw it.** The session's `pc_deploy.py status` ran before the restore, and at core 0.30.0 that command does not look for the ini when nothing is installed. Its prefs read in the same command gave `b7c37858...`, the overlay, so it rechecked the prefs after the restore and not the folder. The report's "game folder identical" is a 09:37:18 reading stated as the state at 09:37 with no lock.
- **Why it is still there.** J96's install at 09:38:21 snapshotted it as vanilla (`pre_install_20261106T093821Z.json`, same sha, same mtime, the 155 extra bytes in that file) and backed it up, and J96's uninstall put it back with its date intact. J96's report is right that it is J32's.
- **Why not a blocker.** The brief's PC test passes as worded: no lock, game not running, `status` clean, exe vanilla, prefs unchanged. No J32 result rests on it.
- Fixed by me as a run-folder erratum. `report.md` stays as written, because policy would count this session as one of its authors: read this finding in place of its last line.

**S7. The gate's stated bound was too narrow.** `viewer.parity.numbers` said "thin or faint"; a solid 16 px icon and a text line at 100 px also read `raster`, because they fill under half a tile. Fixed by me in the fact. The same words remain in `tools/ui_hosttest.py:203` and the report. J80 should compare element boxes, as the fact says.

### Later
- **Three bites now (J43, J67, J32):** core W94 should stop waiting for a brief. Core W25's `status` stray line (0.33.0, through J78) would have shown this one.
- **For Liam:** the ini has to be moved out by hand or at J78's `--move-stray`. `play.py install` refuses until then, and any `pc_deploy.py install` snapshots it as vanilla: uninstalls will say identical with it present.
- `route_b.json` could keep the per-field split for S1.

### Checked and sound
- Risk-first reading: `tile_shift`, `align` and `parity_images`, since they become the gate, and the PC end state, since it touches the game folder. No install or persistent-data code changed on this branch.
- `dp-ratio`'s three float32 steps match round 1's reading of `ApplyScale`.

### For anyone merging
No rule changes here, so no other open branch is affected.

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
