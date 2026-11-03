## Round 1 (2026-11-03, branch job/J46 at d422f8d)

**Verdict: merge.**

Reviewed cold from the brief, then the report, then the diff. Machines: `wsc gates` 13 ok, 1 warn (skipped tests: no numpy/Pillow/capstone/viewer wasm), 0 failed;
CI on d422f8d all 8 checks passed or skipped; `wsc policy` before this review only refuses for the missing review and row (expected).

### Checked
- Rule 79: `build_id.py` prints 7631068c014b; `acceptance.py streak --build 7631068c014b --watcher 1.2.0` prints 20 consecutive passes; the ledger has 20
  `j46acc` lines, each naming `harness/runs/20261102_j46acc/pass_NN.json`, all committed. The kit id is the merge commit 455d043 and the DLL inputs
  have not changed since (the id on HEAD is the same), so the passes stand. I did not re-run the passes on the PC.
- Brief against report: army route (`army=<n>` through `SetPerBattlePrefs`, read back, errors if it did not take, no memory write); land_40 and naval_large
  built; land_large not a separate row (cap 20, argued); siege-city fact; historical cause plus `type=napoleon` and `hist_lodi`; naval_storm measured; campaign
  mid/late not built on the stated kill criterion (127 s per end turn); no `core/` edits; campaign rows kept out of the acceptance order (D38); every
  commit carries the Claude-Session trailer. Deviations (naval_small/naval_storm pinned to 3 ships, a pass of about 8 min against about 7) are named in the report.
- Risk-first reading: `autostart.lua` (runs in the engine's Lua pump; no `string.find/sub/gmatch` added; a locked NHB_ icon errors instead of falling back;
  the army option is read back and errors on mismatch) and the `test_scenarios.py` army/preset agreement check. Both look sound.

### Findings
**Blockers:** none.

**Should-fix (fixed by me in 3d6ed72):**
1. `registries/scenarios.jsonl`: `land_small` and `naval_small` still carried the J44 load times (3.9 s and 3.5 s, run 20261030_j44pc) although J46 changed their
   armies (naval_small went from 10 to 3 ships) and the report's table and the baseline give 4.2 s and 3.7 s from run 20261102_j46m2. Updated both rows to
   the measured values with date and run; `tests/test_scenarios.py` passes. (Other unchanged rows keep J44's measurement, which is fine.)

**Later (not blocking):**
1. `proxy/napoleon/lua/autostart.lua` (the `army_units` block, near the `TotalUnits` call): the `while` loop sets `lc2 = nil` after one pass, so it reads one
   `army_box` at most; the `army_sides` read from `TeamSetups()` is the real per-side check. Remove the loop when the DLL inputs next change (touching
   the Lua now would change the build id and need a new 20-pass run).
2. A pass takes about 8 min of watcher time (20 passes about 2h40) against the brief's about 7; if more rows join the order, drop or split one.
3. Open questions for Liam, already in the report: two real saves for campaign_mid/campaign_late, the "scene stages the row's save" warscape-core backlog item,
   who left the stray `napoleon_remastered.ini` in the game folder.

No rule that other open job branches must meet changed with this merge. J23 and J28 can build on `land_40` and the `army=` preset key.
