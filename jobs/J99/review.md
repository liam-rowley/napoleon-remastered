# J99 review

## Round 2 (2026-11-06, branch job/J99 at bdfb443)

**Verdict: merge.**

Both round 1 findings are fixed, and the published gallery matches the branch: I rebuilt it from `bdfb443` into my own folder, and `data.json` and all 17 sheets equal the published files byte for byte. There are no blockers and no should-fix items. Three later notes follow; none changes code on this branch.

### Machines
- **`wsc gates`:** 12 ok, 3 warn, 0 failed; 720 host tests passed, 47 skipped. The warnings are not this branch's: the hook path in my worktree, the known `ci_render` note, and the skips.
- **`wsc policy` before this review:** refused only for the verdict and the row, which this round supplies.
- **`tests/test_uikit_vanilla.py`:** 25 passed, none skipped, with the game present.
- **CI on `bdfb443`:** all 9 checks passed or were skipped (`wsc jobs review`). `gates` and `viewer` are green. `policy` is skipped while the pull request is a draft, so its real run comes on this commit.
- **Against the latest main:** `origin/main` is `50905a26`, fetched again before this verdict, and it is the branch's merge base, so the branch holds all of it. Pull request 222 reads MERGEABLE.
- **Rule 79** does not apply: no `proxy/` change and no core pin move, and `policy` raises nothing.
- **UI baseline:** `baseline.json` did not change in the fix round. Its blob at this head is still `741c65d58c538a2b782c65dd11617c22fc13b36f`, the sha round 1 accepted, so nothing new needs accepting.

### Round 1 findings
- **S1, fixed.** `inventory.py --check` is clean, and `components.json` sha256 starts d35057a7, as the report says. My own measurement: 780 kinds, 572 button families, 166 with one state, and all 2,015 `button_state` assets on a card.
  - No family's stem is a sibling plus an action or selection word. The 36 families holding both `up` and `down` are button states, such as `table_header` and `dropdown_button_*`, so the new split did not merge two directions into one card.
  - `button_advice` now shows `depress, inactive, normal, roll` on one card, and the art lines up with its labels in the 1x and 2x strips.
  - One small remainder is L6.
- **S2, fixed.** 372 button kinds name a surface: 369 with `ui_elements` plus the 3 the report names. `campaign.entity_lists` links to 24 kinds, and Type set to Button family shows 10, among them `button_advice`, `tab_c` and `table_header`. 52 surfaces list no kind, as reported.
- **Report counts:** every number in Fix round 1 that I checked holds. Fix round 1 corrects the old counts rather than editing the first section, which the fix steps require.

### The gallery against the branch
- **Rebuild:** `compose`, `strips` and `page` from `bdfb443` into my own folder: 348 files, 67.03 MB, and the same stats as the report. I did not rerun `twins`: the twin screen did not change, so I took `twins.json` from the fix round's staged folder and `twins.png` from the artifact.
- **Published, version 1793977554-b64b, 348 files:**
  - `data.json` equals my rebuild (sha256 4fc6dea1...).
  - All 16 `s1_`/`s2_` sheets equal my rebuild. `twins.png` also equals the staged copy, so that one is not independently rebuilt.
  - The page body in `index.html` contains `page.html` from the branch.
  - Five composites and two shots I downloaded equal my rebuild, among them `entity_lists`, `single_player` and `land_battle_orders`.
  - All 298 composites and 31 shots in my rebuild equal the fix round's staged set. The other 293 composites and 29 shots were not compared with the published copies one by one; they did not change in this round.
- **Data against `components.json`:** the same kind ids, and no difference in `surfaces`, `ui_elements`, `library` or `use_count`. No button has fewer cells than states, and no cell falls outside its sheet.
- **In a browser:** the Chrome extension was not connected, so I did not open the claude.ai page itself. I drove the published `index.html` over my byte-compared data and sheets in headless Chromium: no page errors and no failed requests, and the header reads 300 screens, 213 clean, 46 live, 780 kinds, 32 gaps, 737 uncertain.

### Risk-first reading
I picked `split_state` and `art_surfaces` in `inventory.py`, because J69 trusts these cards and a wrong split hides or merges art. `art_surfaces` only reads the atlas. Nothing in the fix round writes outside the repo or `--out`, and `gallery.py` changed by one constant.

### Later
- **L6.** `checkbox_inactive_empty` stays a one-state family beside `checkbox`, in `campaign_ui` and `spanish_skin`. It may be a checkbox state (inactive and unticked), so J69 should look for it there. `inactive_empty` is the only state-like tail I found left, and the report's "art with one file" is true of it literally.
- **L7.** `harness/runs/20261106_j99pc/README.md` still gives `components.json` sha256 as 9c7aafabedf00601. That is right for that run's first build, and Fix round 1 records the new hash, so anyone rebuilding should read the report.
- **L8.** Round 1's L2 stands: `wsc.toml` `harness` input still has no `runs/` exception. Round 1 did not file L1 with warscape-core, and neither did I; I did not check whether anyone else has.
- **For open branches.** Round 1's note stands: `vanilla_ref` is now a library screen, so a branch that changes library classes or tokens (J35, J69) must also get its corners accepted.

## Round 1 (2026-11-06, branch job/J99 at 9db7896)

**Verdict: merge after fixes.**

The gallery is real and its numbers hold: I rebuilt all 300 surfaces and every count and hash matched. Two should-fix items stand, both in how button kinds reach J69. S1 matters most: 484 of the 1,130 button "families" are one family's states split into separate kinds, so the Components view hides pressed and selected art from the card it belongs to. J69's sittings start from this page, and fixing it means rebuilding and republishing the page, so it is not a small reviewer fix.

Baseline accepted: 741c65d58c538a2b782c65dd11617c22fc13b36f

### Machines
- **`wsc gates`:** 12 ok, 3 warn, 0 failed; 715 host tests passed, 47 skipped. The warnings are not this branch's: the hook path in my worktree, the known `ci/policy.yml.in` note, and the skips.
- **`wsc policy`:** refused only for the three things this review supplies: the acceptance line, the verdict and the row.
- **`tests/test_uikit_vanilla.py`:** 20 passed, none skipped, with the game present.
- **CI on 9db7896:** run 42234487169 attempt 1 had `harness-windows` red, 28 passed and 6 failed. Attempt 2, same commit, was green (job 127957970665), and the other checks passed or skipped. `docs/CI_FAILURES.md` classes that as flaky. See L1.
- **Against the latest main (`50905a26`, fetched again before this verdict).** One commit behind, and it changes only `registries/jobs/J78.json`, which this branch does not touch. `git merge-tree` is clean, and the pull request reads MERGEABLE.
- **Rule 79** does not apply: no `proxy/` change and no core pin move. The only `harness/` file is the run README, and `policy` raises nothing.

### UI baseline
- `changes.py` with the build whose `viewer.wasm` equals `wasm_sha256`: 8 renders in 2 screens, none changed.
- I looked at all four `vanilla_ref` corners. Every cell shows the class and state `gallery.py twin_cells()` names, with no clipped control. Only the scroll sample clips, on purpose, at "Five". Text is test text (J7).
- No library class or token changed. `order-btn` draws on a black square, but the accepted board does the same (L4), so the twin is faithful.
- If a fix round changes `baseline.json`, round 2 must accept it again.

### Should-fix

**S1. Button families are split by state, so 43 % of the button kinds are not kinds.** `uikit/napoleon/vanilla/inventory.py:60` and `:209-212`.
- `SUFFIX` takes one trailing word and does not know `depress`, `unselected`, `unselect` or `select`. It also splits `x_down_off` into family `x_down`, state `off`.
- Measured on `components.json`: 663 of 1,130 families have one state. 484 are a sibling family's stem plus a state word: `down` 210, `depress` 133, `unselected` 123, `unselect` 9, `selected` 8, `select` 1. 257 of those are in use. A further 63 `_depress` families are compound states such as `button_group_selected_depress`, whose stem is not a family either.
- **How to see it.** `button:ui/campaign_ui/skins/button_advice` has `inactive, normal, roll`, and its pressed art sits alone in `button_advice_depress`. `button_left` and `button_left_down` show the same split.
- **What it costs.** The brief asks for one entry per kind with its states. The card shows a partial strip, the headline 1,130 and 1,338 are inflated, and the report does not say so. `test_every_button_state_asset_is_in_a_family` passes because it checks only that each asset landed somewhere.
- **Fix.** Teach the split these state words, including compounds. My word list is a measurement, so judge the real set from the file names. Add a test that no family's stem is another family's stem plus a state word. Rebuild `components.json`, `strips` and `page`, republish to the same URL, and correct the counts in the report.

**S2. A screen's "component kinds" link can never show a button.** `inventory.py:224` writes `'surfaces': []` for every button kind; `gallery.py:586-588` counts from `surfaces` and `page.html:199` filters on it.
- All 1,130 button kinds are therefore missing from every screen's count and filter, though the brief's card links to that screen's kinds. Set Type to "Button family" after following any card's link and the list is empty.
- The button cards do name screens, through `ui_elements`, so the data exists.
- **Fix** in the same rebuild: fill `surfaces` from the `ui_elements` the art is used by, or if that cannot be done, say on the link that buttons are left out.

### Later
- **L1, core.** The harness failure is a race, not this branch. "the proxy refusing" read `FakeGame.exe is not running after the start (exit code 2160...)` where the test wants the status detail, and five later cases failed after it (`zombie`, `profiles`, `auto-restore`, `hang watchdog`, `visible=1`). The cascade is my reading of the log order, not proven. Not filed: this belongs in warscape-core `docs/BACKLOG.md`.
- **L2.** `wsc.toml:104`: the harness input set has no `runs/` exception, unlike proxy and viewer, so a run README starts `harness-windows`. That is why this branch met the race at all.
- **L3.** `docs/REVIEW.md:23` links `tools/jobs_hooks.py`, which does not exist; the check is in `tools/gates/pipeline.py`.
- **L4.** `order-btn` has black corners outside its round plate in the viewer, on the board and here. I did not look for the cause. Liam will see it beside vanilla on the page, so J69 should know it is not a design choice.
- **L5.** The script behind `napoleon.ui.layout_flag_visible` was not committed, so its numbers cannot be rerun. See "Checked and sound" for what I could reproduce.
- **For open branches.** `vanilla_ref` is now a library screen, so a branch that changes library classes or tokens (J35, J69) must also get its corners accepted.

### Checked and sound
- **Risk-first reading:** `gallery.py` and `inventory.py`, because they read the packs and J69 trusts what they write. Nothing writes to the game folder or AppData: output goes to `--out`, and `twins` writes only the screen's RML. No install, save or engine code is on this branch.
- **Composites, rebuilt into my own folder:** 300 surfaces, 298 composited, 213 clean, 85 hatched, 380 hatched uses, 0 stand-ins, and the 2 unread records named. All 298 sha256 equal the builder's staged set; `entity_lists` and `single_player` equal the report.
- **Inventory:** `--check` clean. The table adds up: 1,338 kinds, 11 sure, 1,295 uncertain, 32 gaps.
- **Page:** the artifact lists 348 files, and the staged set is 348 files, 67.15 MB. `data.json` gives 46 live surfaces, all with shots; 1,336 strips, 1,254 with masters; 40 twin cells over 15 classes. I read the file listing and the staged data, and did not open the page in a browser.
- **J10 shots:** all 31 sha256 match `shots.json`, so skipping the sitting was within the brief.
- **Twin grid:** `twins.png` has eight 240 px columns, so the page's rects are right.
- **`entity_lists` by eye:** frame, gilt corners, tabs, header, dividers and scrollbar match `camp_lists`, as the report says. This is one of the ten; I did not repeat the others.
- **Visibility fact:** with my own path match over J10's trees, three panels give 792 components: 724 set and visible, 48 clear and hidden, 20 set and hidden. The 48 and 20 equal the README's. `land_deploy` did not match by path, so its 24 remain unchecked; they are exactly the gap to 747, 1 and 816.
- **Brief:** deliverables present, data rule kept (no composite or shot in git), and the eight deviations are named with reasons.
