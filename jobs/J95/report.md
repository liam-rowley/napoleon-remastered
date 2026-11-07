# J95 report: Discovery tools and facts: small fixes

Items 1 to 7 are in warscape-core draft pull request #185 (`job/W141`), waiting for a fresh review. Items 8 and 9 are on this branch. Item 10, the pin bump, is not done: no tag carries Part A yet.

## What was built
Part A, core pull request #185 (row W141, Semver patch; every item re-checked on the core's `main` first, none already fixed, none dropped). Per-item detail is in the core's `jobs/W141/report.md`.
1. `exe.py` `mask_for` and the `MIN_FIXED_BYTES` floor (6): fixed (`test_rel32_cut_by_the_window_edge_masks_the_bytes_present`, `test_address_like_dword_across_an_operand_end_stays_fixed`, `test_pattern_below_the_fixed_byte_floor_is_not_found`).
2. Unclosed files: fixed (no new test, as the brief says; `test_discovery_lua` passes under `python3 -W error::ResourceWarning`, 6 tests).
3. `db.py` mark byte and empty tables: fixed (`test_header_with_another_mark_byte_fails`, `test_readme_splits_out_the_empty_tables`).
4. `discovery check` reads `used_by`: fixed (class `UsedBy`).
5. `briefpaths.py` Registry gaps: fixed (`test_registry_gaps_exempt_only_the_bullets_own_path`).
6. `shader_catalog.py` import and `density --from-file`: fixed (class `ImportAndDensity`).
7. `discovery ui` fails loudly: fixed (class `MissingExtract`).

Part B, this branch:
8. Fact `napoleon.assets.pack_order`: the last clause now says assumed, in `claim` and `notes`; evidence, date and state kept.
9. Fact `napoleon.exe.window_imports`: evidence is `discovery/diff/exe.json`, the command is in `notes`, and the count is corrected to 19 named and 38 more (user32.dll 57 in `detail.napoleon_pe.imports`; the old text added up to 56).
10. Pin bump: not done. The newest tag is v0.49.0 and #185 is unmerged. Next step: review and merge #185, then a bump to the tag the release workflow cuts.

## Evidence
- Core: `python3 wsc.py gates` (full, Windows, 2026-11-07), 1606 host tests passed, 5 skipped; its one failure was `doc_paths` on an UPGRADING line, reworded, then `gates --fast` 15 ok. CI on #185 is the full check of the final tree.
- This repo, 2026-11-07: `python3 core/wsc.py reg check` ok, `jobs check` 110 rows ok, `gates` (full) 14 ok, 2 warn, 0 failed.
- The changed core code on this repo's committed files and the shipped packs, read-only (nothing launched, output in a scratch folder): `used_by` check 0 problems on `discovery/ui`; mark byte 1 on all 310 Napoleon and 286 Empire tables; empty tables 26 (1 with a schema, 25 without); 0 new found-path errors in the briefs with a Registry gaps section; `exe.py` function signatures unique 1159 to 1236, no signature that stayed unique changed its RVA, 19 lost `unique`.

## Deviations from the brief and why
1. **A core row the brief did not name.** The brief says one core pull request from the builder, but the core's `policy` takes code only on `job/W<n>` with its brief already on `main`, and no row existed. So this job added W141 (row and brief, core plan PR #183, merged on green CI) and built Part A on `job/W141`. It keeps D56's one pull request. Consequence: #185 is reviewed in the core's queue, separately from this job.
2. **`jobs next --id J95` refused to start:** `origin/job/J95` already existed at a1e917a4 with no commits of its own, and no session held it. I took the branch over by fast-forward; nothing was lost.
3. **Empty tables were never in "Not decoded"** (they are `decoded: true`), so nothing moved out of that list; the section and column were added. The audit's 26 and 25 hold.
4. `search` keeps `None` (`unsearchable`) when the longest fixed run is under 4 bytes; the floor's `[]` comes after that. `discovery ui` checks the extract on every step, not only `art` and `live`. `problems()` finds `assets.jsonl` beside the rows file to stay inside `discovery/`. The core's report has the reasons.
5. **`MIN_FIXED_BYTES` stays 6.** The registry's shortest anchors are 1 to 3 bytes, but they are read at a known RVA and never go through `search`.
6. A `docs/UPGRADING.md` section in the core, as the core's rules ask; the brief's scope line named only `discovery/`.

Usage: 100 tool calls; models: opus; 1 session, Part A and W141's row included, counted by hand, about, 2026-11-07

## Open questions
1. **What the bump does about `exe.json`.** `discovery render` does not re-run `exe.py`, so the committed `discovery/diff/exe.json` keeps the old classes until someone re-runs it, and 19 function signatures lose `unique` when they do. They are candidates, not sites, but J9 started from those hits. recommended: the bump job re-runs `exe.py` and checks no `engine_sites` row rests on one of the 19. default after: 2026-11-21.
