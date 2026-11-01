# J9 review

## Round 1 (2026-11-01, branch job/J9 at ca33a65)

**Verdict: merge after fixes.**

Reviewer session `47985340-a559-4b5b-bf9c-6d1f70c95d84` (Opus, independent check: D15). Read the brief, the report, D2/D15/D30 and the diff
(415 files). Ran `wsc gates` and `tools/pr_policy.py` locally. Risk-first read: the 19 new `patch` rows in `registries/engine_sites.jsonl`
(they write engine memory at start-up) and their keys, then the proof logs and the 20-pass run.

### What holds (checked, not taken from the report)
- **Every new patch row matches the vanilla exe on disk**: anchor + stock bytes at each `rva`, read from `Napoleon.exe` with a PE section map,
  19 of 19 (shadow, sprite, unit LOD, ship, trees, grass). The written addresses in the proxy logs are `base + rva + len(anchor)`, and they agree
  with the descriptions (grass rows 3 and 4 of the 12-byte table at 0x1019ab4; `mov dl,1; mov ebx,0x800` for the shadow edge).
  `battle.selection_ctor`'s stock bytes hold a vtable address, which is fine: the start-up check takes the load delta off relocated dwords (`proxy/README.md:83`).
- **Start-up check and key isolation**: `raw/j9_mixc_stock_proxy.log` "45 sites: 45 ok, 0 bad, 0 to write, 26 hooks verified" on 46f52d356ce8;
  `raw/j9_mixc_on_proxy.log` and `raw/j9_land_shgr_proxy.log` write exactly their family's sites with the stated stock -> patch bytes.
- **Keys**: the 7 `gfx.*_proof` keys are default and release false in `config_keys.jsonl`, 0 in `napoleon_remastered.ini`, with owners J24 / J27.
- **Rule 79**: `build_id.py` on the branch head = `46f52d356ce8`, the build of `harness/runs/20261101_j9acc`; 20 pass files, every check `ok: true`.
  `main` has no commits the branch lacks, and the review fix below touches no DLL input.
- **J6 answers** in `engine_api.json` trace to the probe logs (for example all 28 new CampaignUI names in `j6["CampaignUI.*"].new.at_runtime`).
- Deliverables 0, 1, 2, 4 and 5 (stopped as the brief says) are present with tools rows, headers and tests.

### Blocker (fixed in this review)
1. **CI `gates` red on ca33a65**: `tests/test_engine_api.py` `test_table_current` failed ("engine_api.json is stale"), locally and in CI run
   41338153370. Cause: `discovery/core/engine_api.py` `build` put every `raw/*_proxy.log` of the run into `logs`, so each proof log added to the run
   after the table was built (the `mixa/b/c` and far-naval launches) made the committed table stale, though the data were identical. Fix `2e6a75d`:
   `logs` lists only the logs that carry probe lines (`_has_probe`), the table regenerated (only `logs` changed: 9 entries out, data unchanged),
   test `test_logs_without_probe_lines_are_not_listed`. See it fail: check out ca33a65 and run `python3 -m unittest tests.test_engine_api`.

### Should-fix (for the fix session)
2. **Deliverable 3 is short of the brief, and the report gives no reason** (`jobs/J9/report.md` "API probe scope"). The brief names these states:
   the front-end screens reachable from the main menu ("other front-end screens need the `dev.lua_bridge` wrappers or a `key`/`click` probe"),
   the campaign with an army, a fleet, an agent and a settlement selected, the reachable campaign panels, and samples for probe-safe getters
   (a committed probe-safe list). The run has the main menu only, nothing selected plus "the first character", no panels, no samples, and C and
   Lua functions not told apart. The report says the wrappers "were not used" but not why, and the call budget had been lifted by Liam to make the
   job thorough, so the budget is not the reason. REVIEW.md: a deviation is fine only when the report says why. Fix: run the missing states
   (the probe enumerates only, so each is one launch) and rebuild `engine_api.json`; or, for each state you cannot reach, record what you tried and
   why it failed. Getter samples need the committed probe-safe list the brief names. The kind (C vs Lua) can come from `lua_cfuncs.json`
   (986 names already carry a binding address) without a call.

### Later
3. **`--no-verify` commit `5eafc75`**: CLAUDE.md and the hook policy say never skip hooks without Liam's say-so; the report names it. The trigger,
   fast gates reading a run file a running driver was still writing, is worth a guard (the driver writes to `_scratch` and copies in at the end,
   or the gate skips files open for writing). For this repo.
4. **Core items from the report filed as warscape-core backlog rows B35 to B39** (branch `backlog/napoleon-j9-review`, commit c06f77f; the
   pull request still needs opening): profile-restore race in `pc_deploy.py set`, stale ctl requests, `engine_sites` `value_offset`, a kit role for loose
   `data\` files, a `wsc find` hook for the exe string index. Item 6 (the prefs overlay sets every occurrence) is already B30. Items 1 and 2 are
   traps that bit this job and are guarded only in the run-folder `proof.sh`, so another driver will hit them again until the core change lands.
5. **Weak anchors**: several rows anchor on 2 to 4 common bytes (`cc cc`, `c7 44 24 18`). They are checked at a fixed RVA behind the exe-identity
   guard, so they are correct today; if anchors are ever used to re-find a site after a game update, they will not be unique. Nothing to do now.
