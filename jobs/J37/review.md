## Round 1 (2026-11-05, branch job/J37 at 67aad7f)

**Verdict: merge after fixes.**

Machines: `wsc gates` failed on the branch (CI run 42087011111 and locally): `row shapes: engine_facts napoleon.fonts.getfont_rule: open, and neither its claim nor its notes name a jobs row or liam as owner`; the `test_discovery_repo` failure ("rows assets: 12295") is the same gate seen through the test. Fixed by me (below). `policy` refused only for the missing review and row, as expected before a verdict. No change to `core/`, `proxy/` or `harness/`: rule 79 does not apply. `jobs check` ok.
Risk-first read: `uiscale/core/fontcheck.py`, `licences.py`, `engine_text.py` (what J38 consumes), the licence data and the claim-to-evidence chain of the PC run.

### Fixed by the reviewer
- `registries/engine_facts/napoleon.fonts.getfont_rule.json`: named `liam` as owner in the notes; the `row shapes` gate is ok again (commit 67aad7f).

### Blockers
- none beyond the gate above.

### Should-fix (for the fix session)
1. **Brief deliverable 5 is incomplete.** Facts `napoleon.fonts.engine_text_slots`, `napoleon.fonts.subtitles` and `napoleon.fonts.licence` have no rows (`ls registries/engine_facts | grep napoleon.fonts`); the report says `engine_text_slots`, `loading_quote` and `subtitles` stay static_only but only `loading_quote` exists. Add them (open/static, with an owner and the reason they cannot be shot), and `napoleon.fonts.licence` (face, licence, date checked) from `font_licences.json`.
2. **Deliverable 4 evidence is by eye only.** The headline finding (campaign labels about 2x with the set, contradicting J66's "labels stayed 1x") rests on 1280 px copies with no measured height. Add a measured height from the committed shots, or make `factor_follows_install` say plainly that it is by eye and not measured.
3. **1080p front-end shot missing** (report, deviation 2): add a short extra cell, or an explicit `static_only` note in the run README.
4. **DLL id mismatch** (6e89faf06754 against the branch's a005f6cccc17): harmless if nothing J37 changes feeds the DLL, but the run README should say how that was checked (the `build_id` inputs unchanged between the two).

### Later
- A proxy pack-read log (open question 1) is the only route to the per-context `.cuf` readout; queue it as its own job (DLL, rule 79). Liam to decide.
- A full-size capture mode for `shot.sh` (open question 2) belongs in the core: warscape-core `docs/BACKLOG.md` via a core pull request.

Not legal advice applies to `font_licences.json`, as the report states.
