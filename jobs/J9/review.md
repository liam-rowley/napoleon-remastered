# J9 review

## Round 2 (2026-11-01, branch job/J9 at 4f10102)

**Verdict: merge.**

Reviewer session `b2eb304d-0129-4416-be7d-91133a0ea9e3` (Opus, independent check: D15; neither the builder nor the round 1 fixer). Read
the brief, round 1, the report's `## Fix round 1` and the fix diff `16d8c4a..4f10102` (178 files, 150 of them run evidence). Ran
`wsc gates`, `wsc jobs check` and `tools/pr_policy.py` locally. Risk-first read: the fix round's probes (`harness/runs/20261101_j9fix/probes/`),
the first J9 code that calls engine functions rather than only enumerating them, then the generator change in `discovery/core/engine_api.py`.

### What holds (checked, not taken from the report)
- **Round 1 answered.** Blocker 1 stays fixed (`2e6a75d`). Should-fix 2: `engine_api.json` has the 19 states the fix round names (campaign
  with an army, fleet, agent and settlement selected; six panel states; front end after the pages and after a warm reset), each traced to a
  committed `raw/*_proxy.log`; every log the run README cites is committed. Later items 3 to 5 are answered as the round asked.
- **Getter samples**: `discovery/napoleon/probe_safe.json` is generated and checked (`test_committed_list_current`), 45 getters (28 CampaignUI,
  10 BattleUI, 7 FrontEnd), the same 45 as the run's `probe_safe_list.lua`; every sample in the table traces to a `lua: sample` line
  (`j9f_campaign_crash_proxy.log` 28, `j9f_frontend_proxy.log` 7, `j9f_land_proxy.log` 17 = 10 battle + 7 front end after the reset), and
  they agree with each other (CampaignKey `mp_eur_napoleon` with PlayerFactionId `austria` from the same launch). No personal data: `LocalPlayerName` is empty.
- **The calling probes** are wrapped in `pcall`, use no string library call and nil-guard the address after the one crash (the crash is a
  fact, `napoleon.campaign.region_list_no_address`, with the minidump name and the faulting RVA). One crash in the state, under the brief's two.
- **Rule 79**: no DLL input changed in the fix round (no `proxy/`, `core/` or harness adapter file in the diff); `core/proxy/tools/build_id.py`
  on the head = `46f52d356ce8`, the build of `harness/runs/20261101_j9acc` (20 passes). `main` has no commit the branch lacks.
- **CI on 4f10102**: `gates` and `harness-windows` green, `proxy` skipped (no input changed). `policy` was red only because the newest verdict
  was round 1's `merge after fixes` and the row was `review`; this round's verdict and row answer both lines.

### Should-fix (fixed in this review)
1. **`campaign_show_prestige` is not the prestige panel, and the table did not say so** (`discovery/napoleon/engine_api.json` `states`).
   `ShowPrestige()` errored in `Huds.lua:51` (run README, fact `napoleon.campaign.panel_routes`), so that block is the surface with the technology
   and missions panels still up: its counts are identical to `campaign_show_technologies`. J10 reads this table per state and would take it for the
   prestige panel. Fix `618e55b`: `STATE_NOTES` in `discovery/core/engine_api.py` puts a `note` on that state's entry; table regenerated (only the
   note changed); test `test_state_note`. See it: `python3 -c "import json;print(json.load(open('discovery/napoleon/engine_api.json'))['states']['campaign_show_prestige'])"` on 4f10102 has no note.

### Later
2. **The report's Lua count is off**: `## Fix round 1` says "2,911 Lua functions of the script environments"; the table has 3,088 names with
   `impl: Lua` (235 on `S`, the rest on `S.<table>` and their `#index` tables, so one function can appear under several owners). Not a reviewer
   edit (a review session must not write report.md); J10 should count from the table, not the report.
3. **The probes that call are not named as a deviation.** The brief: probes call nothing "except names classified probe-safe and kept in a
   committed list". `camp_select.lua`, `camp_panel.lua` and `fe_pages.lua` call state-changing engine functions (SelectAndZoomTo*, the panel
   Show/Toggle functions, CloseAllPanels, TransitionTo) to reach the states round 1 asked for, and one of them crashed the game. They are the
   brief's "key/click probe" by another route and the README lists every call, so nothing to undo; the report's deviations should have said it.
4. **The fix probes live only in the run folder** ("they move there with the next DLL change"): a promise in prose. Whoever next changes
   `proxy/napoleon` (J10 or J24 are likely) should move `camp_select.lua`, `camp_panel.lua`, `fe_pages.lua`, `getters.lua` and `vis.lua` into
   `proxy/napoleon/lua/probes/`, and generate `probe_safe_list.lua` from `engine_api.py probe-safe --lua` with a `--check` in the tests,
   so the list the probe loads cannot drift from `probe_safe.json`.
5. **Round 1 items 3 to 5 stand** (the `--no-verify` trigger guard; warscape-core B35 to B39, whose pull request is still to open; weak anchors).

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
- **Start-up check and key isolation**: `raw/j9_mixc_stock_proxy.log` "45 sites: 45 ok, 0 bad, 0 to write" with all 26 hook rows passing on 46f52d356ce8 (2026-11-01, run 20261101_j9pc);
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
