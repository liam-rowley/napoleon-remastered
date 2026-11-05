## Round 1 (2026-11-05, branch job/J67 at 55f1532)

**Verdict: merge.**

The work does what the brief asks at 4K, and the deviations that matter are named in the report. One report claim was false at 55f1532 and one brief item was missing without a word: both are fixed here (commits below). One item is left for Liam: the stale ini in the game folder, finding 1.

Session `34887eac-14e0-4f35-bf4e-6970232fbd94`. I did not build this branch. `report.md` is unchanged, because the policy check refuses a review from a session that wrote the report; where it is now out of date, this review says so.

### Machines
- `wsc gates` at the final head: 12 ok, 3 warn, 0 failed; 657 host tests pass, 36 skipped.
- CI at 55f1532: `gates` and `harness-windows` green; `proxy` skipped (no input changed); `policy` skipped while the pull request is a draft.
- Rule 79 does not apply: no change under `proxy/`, `harness/`, `core/` or `uikit/`. No baseline to accept.
- Art-build Python (the gates skip these without freetype): `tests/test_uiscale_fonts.py` 14 pass, including the golden 2x slots; `tests/test_uiscale.py` 19 pass.

### Claims checked against evidence
- `uiscale lua-patches --check`: 69 scripts, 204 items, every assert holds on the installed game. `uiscale lua-consts --check`: identical, 258 scale and 756 leave.
- 1.5 as the 1440p default: `uiscale check` gives 0 layouts that lose content and 6 that bleed 1 vanilla px, as the fact says.
- Pack shas for 1.5x match `build_15x.json`. Load `load_s` 3.8 in `raw/x2_route`.
- `wsp.vanilla` at 2x: `raw/x2_route/wsp_copy_battle.txt` reads `38:false|76:true`, so the patched copy runs.
- Crashes: `raw/*/dumps.txt` holds 15 dumps, all `c0000374`; 6 in `x2_pages`, as the report says.
- Shots opened: `x2_route/land.jpg` (radar group in the corner, Start Battle box right), `x2_4k/camp_settlement.jpg`, `x2_fix2/fe_sp_load_game.jpg`, `c15/frontend.jpg`, `h15b/land.jpg`, `h15b/camp_field.jpg`, `h125/camp_field.jpg`. All match the screen table, except the 1.25x minimap (finding 3).
- Doubtful `leave` rows, read in the disassembly: `popup_pre_battle` main#44 (1280 and 960 are `Max` floors that the 4K and 1440p screens already exceed), `lb_unit_id` (counts), `template.tech_entry` (halves). All correctly left.

### Risk-first reading
I read `lua_patch.py`, `check.py`, the `play.py` guards, `date_cell_pass` and the `cuf_encode` header change in depth, because they touch engine scripts, the install and the uninstall, and every later factor depends on them. `profile_active` matches the watcher: `_active.json` is removed once the restore succeeds, and a failed restore stays active, so the uninstall guard is sound. `lua_consts.py` beyond its rules, and the art path, are skimmed.

### Findings
**Blockers:** none left.

**Should-fix, open: for Liam**
1. **The game folder is not snapshot-identical, and the kill criterion was not followed.** `napoleon_remastered.ini` (10970 bytes) is still in the game folder, seen 2026-11-05. The brief says to stop at this point and not hand over the install command. The builder went on to the 1440p sittings with `--keep-ini`, and the report's commands mention `--keep-ini`. The report names all of this, the file has no effect without `d3d9.dll`, and both causes now have a `play.py` guard, so this does not hold the merge: nothing in the branch can remove the file. **Do not use `--keep-ini` for the play install. Remove the file first** (report, open question 1). I did not touch it.

**Should-fix, fixed here**

2. **`uiscale check` was red at every factor, and the report said green.** `uiscale/core/check.py`, `uiscale/core/scale.py` `date_cell_pass`. At 55f1532 it exits 1 with 2 abutting pairs off (`turn`, `save_date` in `sp_load_game` and `mp_load_game`), against the report's "0 abutting pairs off" and deliverable 3. Commit 7135278 moved the cell after the last check run. The move is deliberate and the Load Game shot is clean, so the check now allows exactly that shift, and the report's line holds again. `check.py` had no tests: it has them now, including green at all three factors when the game is present (e38c793).
3. **The template image-def and TGA pairing the brief asks of the check was missing, and the report does not say so.** Added, against the built templates file: 0 off at 2, 1.5 and 1.25 (e38c793). `wsc uiscale check` stays standard-library only.
4. **`--no-wrapped` was guarded by prose.** Without `--work` it wrote the default packs that `play.py` installs, with 2 scripts vanilla and no mark. The build now refuses that (83cc4b6).
5. **`release.json` said the Lua fixes were "not yet proven in game".** That was the desk phase's text; the README and facts say they are proven at 2x. Now says what ran and what was never seen (bb335ea).
6. **`napoleon.ui.scale_1_5x_packs` and `scale_1_25x_packs` claimed more than ran.** Their claims read as if the sets ran battles and campaigns; those shots are of `--no-wrapped` builds. The claims now say so (06d31f8).

**Later**

7. **1.25x minimap is 20% too large and cropped.** `uiscale/napoleon/lua_patches.txt:96`, `uiscale/core/lua_patch.py` `apply`. `template.map_image`'s x 2 is a multiplier, but every item is rounded to a whole number, so 1.25x writes 3, not 2.5. See it in `raw/h125/camp_field.jpg` against `h15b/camp_field.jpg`. The three uses agree, so hover stays right; 1.5x and 2x are exact. 1.25x is neither the default nor shipped. A fix needs an unrounded item and a PC launch to learn whether the engine takes 2.5, so it is recorded in `uiscale/README.md` rather than fixed here.
8. **Core row, not filed:** `pc_deploy uninstall` has the race `play.py` now guards (report, open question 4). It belongs in warscape-core `docs/BACKLOG.md` through a pull request. This session is confined to its worktree, so someone needs to file it.
9. **Never run, both named in the report:** the play condition (`dev.lua_bridge` off) as a launch at any factor, and the shipping 1.5x pack's battle root in a battle. Liam's first sessions at 4K and 1440p are the first real test of each.
10. **`‰` is wider than the cell width in the six 2x slot files** (for example 30 against `h9` 24 in `ingame_24.cuf`), so its right edge may be cut. No other glyph is. Those files are pinned by the golden shas, so a fix is a deliberate golden change; cosmetic.
11. **`uiscale check` runs in no CI gate:** the new test needs the game, so it skips on CI. Finding 2 got through this way. It does run in `wsc gates` on the PC.

### Other open branches
No rule changes here that another job branch must meet. J37's rows are already on this branch.
