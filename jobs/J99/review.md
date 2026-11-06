# J99 review

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
