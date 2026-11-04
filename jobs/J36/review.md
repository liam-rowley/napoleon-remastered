# J36 review

Reviewed 2026-10-31 on `job/J36` (head cd8911f, after the job chat's rebase) by an independent session that did not build it.

**Verdict: merge.**

## What I ran
- `python3 tools/pr_policy.py --branch job/J36 --base origin/main` on cd8911f: only the review and `done` lines remain, which this review resolves.
- `python3 -m unittest tests.test_upscale`: 18 run, OK, 9 skipped (no numpy or Pillow in this interpreter; the report's Open question 1). `tests.test_pc_deploy` runs.
- `wsc gates` (run in the background, 190 s): 12 ok, 319 host tests passed. That run overlapped my checkout switch, so treat it as indicative; CI on the rebased branch is the check.

## Blocker
None. My first read of 69b61c5 found a foreign J18 commit (7b8bd96, `proxy/tools/pc_deploy.py`) that made policy rule 79 refuse the branch; the job chat has since rebased it away (`origin/main..job/J36` is now 3 J36 commits, no `pc_deploy` change), so that blocker is resolved.

## Should-fix
1. **Brief PC test (d) not done: the game never loaded the packs.** The report says so openly and leaves `napoleon.ui_art.pack_loads` open; the kill criterion is neither hit nor cleared. Fine to merge the pipeline, but a follow-up job (proxy deployed via the J20 flow) must close it before packs are installed for real. Needs a `needs_brief` row.
2. **`upscale_status` words differ from the brief** (`todo`/`not_needed` plus text in `upscale_method`). Documented and justified by the core enum. Widening it is a warscape-core change (Later 1).
3. **Host tests half-skip in CI** (9 of 18 need numpy and Pillow). Add `pip install -r upscale/requirements.txt` to the gates workflow, or the determinism, alpha and mip tests never run where it counts.
4. **Not confirmed by me:** the model licences (CC BY 4.0, "read 2026-10-30") and the watcher job ids for install and uninstall. The run report records them; I did not re-open the release pages.

## Reviewed in depth
- `upscale/core/pack.py`, chosen because it writes the file that is later installed into the game folder. Two-phase `.building`, per-entry sha-check while copying, independent re-read (`check_pack`: type, index, end of data, per-entry sha) before rename, entries under a `ui_art_2x5\` prefix so no vanilla path is overridden (D2). No defect found.
- `registries/assets.jsonl` is rewritten wholesale (19k lines) because the new fields are added to every in-scope row. Expected; diff it by field, not by line.
- Skimmed `dds.py`, `resample.py`, `batch.py` and the CLI. The first-roles run (3484 done, verify clean, 207 of 207 byte-identical across two runs) is evidenced in `upscale/runs/2026-10-31_first_roles.md`.

## Later
1. warscape-core: widen the `upscale_status` enum to `pending|done|skipped:<reason>|failed:<reason>`; adopt `upscale/core/dds.py` as the shared DDS module (it duplicates Empire's).
2. Cursors (179 `.cur`, 1 `.ani`) stay out until Liam decides whether the RmlUi host draws its own.
3. Before a real install, add `ui_art_2x5_*.pack` to the games.json `mod_packs` skip list so J7's indexer does not index them as game packs (report Open question 6).
4. Liam picks the order of the remaining 5954 `todo` assets from the sheets. The look is his call; nothing here is claimed approved.
