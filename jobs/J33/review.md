## Round 1 (2026-11-02, branch job/J33 at 10d1db1)

**Verdict: merge.**

Reviewed against the brief: all deliverables are present (three direction files at 7.1 to 7.3 KB each, 18 previews at 2.28 MB, LANGUAGE.md at 10.2 KB, tokens.draft.json, D43 recorded in Liam's words, report). `wsc gates` is 10 ok, 2 warn (environment: hooks path, skipped numpy/capstone/wasm tests), 0 failed. CI on a5fe044: 8 of 8 passed or skipped. `pr_policy` refuses only for the missing review and the row not yet `done`, which this round fixes.

Checked: the 3 MB preview cap, the file-size caps, no loc text in the committed files (keys and ids only), the pick and D43 taken from Liam's chat words, the contrast ratios in LANGUAGE.md section 1 recomputed for the badge case, and the faction on-colour rule (dark `#0b0f16` or white, 4.75:1 at worst, as reported).

### Blocker
None.

### Should-fix (fixed by the reviewer, commit 10d1db1)
- `design/napoleon/LANGUAGE.md:103`: the number badge for a negative count said "`negative` fill with dark text". Dark `#0b0f16` on `#a3231a` is 2.57:1 (fails 4.5:1); white is 7.47:1. Changed to white text. See it fail: compute the ratio of the two colours.

### Later
- The previews still show C with the keyline faction rule (the report and LANGUAGE.md say so); J34 should treat LANGUAGE.md as the source on faction colour.
- Open questions in the report (RCSS `image-color` and box-shadow focus ring in the pinned 6.3, derived faction tokens via J35, engine-drawn face with J37, about 24 new sprites needing Liam's D14 acceptance) belong to J34, J35, J37 and Liam; none blocks this merge.
- Deviation noted and accepted: plain HTML artifact instead of a Design canvas (reported with a reason); `region_details` drawn as stacked panes because the atlas has no tab group.
- D43 numbering: renumber if another branch lands a D43 first.
