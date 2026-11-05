# J37 report: Engine-drawn text and fonts

## What was built
- Desk steps 1-3 (2026-11-03, `uiscale/runs/2026-11-03_j37_static/`): static RE of the engine font path, `uiscale/napoleon/engine_text.json` inventory with generator and `--check`, `check-fonts` slot check, per-factor fonts pack additions (`frontend_10..22`, `frontend_32` alias), `font_slots.json`, `font_licences.json` (Lora, OFL-1.1) with `licences --check`, host tests, README section.
- This session: merged `main` (conflicts in the uiscale verb, cli and tool rows resolved), fixed `check-fonts` default work dir (`pc_state`), full build and `check-fonts` ok, and the PC run `uiscale/runs/2026-11-05_j37pc/` (3 cells x 7 shots).

## Evidence
- Run `2026-11-05_j37pc` (README there): 1080p vanilla, 4K vanilla, 4K with the 2x set; game folder identical at the end; load 3.7-3.9 s against J66's 3.8 s.
- Fonts pack from the full build; `check-fonts 2x: 13 files ... ok`.
- Facts: `napoleon.fonts.file_survey_blind_to_cuf` (new, verified 2026-11-05, run 2026-11-05_j37pc), `napoleon.fonts.factor_follows_install` (new, verified by eye 2026-11-05, run 2026-11-05_j37pc), `getfont_rule` stays open with the new note.

## Deviations from the brief and why
- No crop pairs or measured glyph heights: the shot helper only writes 1280 px copies. Comparison is by eye (labels about 2x).
- No front-end shot at 1080p (setting not applied in the first cell); 4K cells have it.
- The `.cuf` per-context readout, `loading_quote`, `engine_text_slots` and `subtitles` facts remain static_only: the file survey does not log `.cuf` opens.
- DLL was a copy of the main checkout's build (id 6e89faf06754, not a005f6cccc17): rebuild blocked (network, no toolchain). Nothing J37 changes feeds the DLL.
- Committed raw data excludes the 20000-row survey logs (size); the claim they support is the fact row above.
- Not legal advice: `font_licences.json` records the OFL data for J38.

## Open questions
1. Is a proxy-side pack-read log (to see `.cuf` opens) wanted? It is a DLL change and needs its own job and rule-79 run.
2. Should a full-size capture variant of `shot.sh` (cropping at native 4K) be added to the core for the measured crop pairs?
3. The 1080p front-end shot and the measured heights could be added by a short follow-up sitting.

## Fix round 1
- Gate (row shapes, getfont_rule owner): fixed by the reviewer in 67aad7f; nothing left.
- Should-fix 1 (missing facts): added `napoleon.fonts.engine_text_slots` and `napoleon.fonts.subtitles` (open, static_only, owner liam, reason: no .cuf open is logged) and `napoleon.fonts.licence` (verified, from `font_licences.json`) (898a3d7). `loading_quote` already existed.
- Should-fix 2 (evidence by eye): not measured (shot helper writes 1280 px copies only); the `factor_follows_install` claim now says "by eye, not measured" and the run README says so (898a3d7).
- Should-fix 3 (1080p front end): marked static_only in the run README (898a3d7); no extra PC sitting.
- Should-fix 4 (DLL id): README now records that `build_id.py` gives a005f6cccc17 at both HEAD and origin/main, so the DLL inputs are unchanged (898a3d7).
- Later items (proxy pack-read log, full-size shot mode): left for Liam / a core PR, as the review says.
