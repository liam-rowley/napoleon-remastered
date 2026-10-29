# Review of J14 (Save editing: ESF tools and Napoleon save format)

## Round 1 (2026-10-29, branch `job/J14` at 53c8c95)

Reviewer: a fresh Opus chat (session `4af3fc36-0ba5-4d39-b72a-e179b5ee11ae`) that built none of the branch (builder:
`23319d67-fff6-4f57-89c3-fc1b90999807`). Checked against `jobs/J14/brief.md` and `jobs/J14/report.md`.

**Verdict: merge.** The tools, the round trip, the manifest, the recipes, the staging tool and ladder A and B all hold up when
re-run independently on the PC's saves. The two unmet gate items are named in the report and blocked by work outside this job:
a second-turn round trip, and ladder C's survival of the AI pass. Both are already recorded as an `open` fact, and they move to
J4's brief (see Later). Three should-fix items were fixed on the branch.

### Machines
- `wsc gates`: 12 ok, 110 host tests (at 53c8c95, and again after the fixes). CI `gates` green on 708059d, af21f9a, a050662 and
  53c8c95 (run ids in the report match).

### Claims re-checked independently (2026-10-29, on the PC's files, this session)
- `saves/napoleon/saves.json`: all 9 sha256 values match the files in `C:\napoleon_remastered_pc\saves\`.
- `esf_edit.py roundtrip` prints `OK` on `j14_taxes-changed_b` (Liam's) and `zz_j14_c_autosave_164214` (written by the engine).
- Recipes are deterministic: `tax_rates.py --lower 4 --upper 4` on the base regenerates `_scratch\j14\j14_B_tax44.save`
  sha-equal (264be99c…); `agent_into_settlement.py --region eur_wales --agent 817597504` regenerates `j14_C_rake_wales.save`
  sha-equal (ebafe35d…); `j14_A_rewrite.save` equals the base (1252b955…).
- Ladder B in game: the engine's QuickSave `zz_j14_b_qs_…` reads `britain governor_europe [4, 4, 25, 25]`.
- Ladder C both ends: in the engine's autosave and QuickSave, Wales lists the rake (`agents [896852032]` in the QuickSave), and
  the rake's `residence` is Wales's id (741117584) with `in_residence` true.
- The watcher log matches the sitting: launches and kills of owner `j14` through 16:50:35, lock free at 16:50:51.

### Findings
**Blocker:** none.

**Should-fix (fixed on the branch, one commit each):**
1. `registries/scenarios.jsonl` rows `campaign_britain_1805_tax44` and `campaign_britain_1805_rake_wales` named the QuickSave files
   (`zz_j14_b_qs_…`, `zz_j14_c_qs_…`) as the save to load, and gave them load times. Those files were never loaded: the loads
   timed at 3.5 / 2.7 s were the recipe outputs `zz_j14_b` / `zz_j14_c`. Fixed in ffbd6fb: each row now names the base save plus
   the recipe, which is what was load-proven and fits the brief's "edited saves are regenerated, never kept".
2. `saves/napoleon/stage_save.py` `keep`: the docstring and README said kept saves are "read only from then on", but nothing
   enforced it, and the test named `..._read_only_...` never checked it. `--as ../x` also wrote outside `<state>\saves`. Fixed in
   7727b2f: the kept copy is set read-only on disk, a path in `--as` is refused, and the test checks both. (The 9 copies kept
   before this fix are still writable; run `attrib +R C:\napoleon_remastered_pc\saves\*.save` once if you want them read-only too.)
3. `saves/napoleon/load_save.sh`: C1's run was killed by hand at 16:49:44, but its `--end-turn` poll loop kept running for 921 s.
   During C2's launch (16:50:08-16:50:35) it sent `ctl lua campaign_turn.lua` requests into C2's game and kept refreshing the lock.
   At 16:57:37 it sent a `kill` that the watcher refused, because the lock was free by then
   (`watcher/jobs/j14-20261029T165736Z-2878814759.done`). That was after the report commit, so its two log lines
   (`{"step":"next_turn",...,"waited_s":921}`, `{"step":"next_turn","rc":1,"status":"stopped"}`) are only in the builder's
   uncommitted worktree copy of `ladder.jsonl`. Fixed in 36f6ca7: one run per owner (a pid file in `$TMPDIR`, stale when the pid
   is dead). A second run is refused with exit 2. Exercised on the host: a live holder is refused, a stale pid passes.

**Later:**
- **J4's brief must carry the two unfinished J14 gates:** a round trip on a save from a second turn, and ladder C's EndTurn
  survival (fact `napoleon.save.endturn_survival`, `open`). Both need J13's background-focus handling (its brief, lines 60-62) and an
  answer for the AI diplomacy modal (J15 or turning AI diplomacy off). `load_save.sh --end-turn` is ready for them.
- C1 was not unattended: Liam dismissed two modals by hand. The report says so; `napoleon.campaign.modal_stops_pump` rests on that
  one sitting.
- `load_save.sh`'s stop after 4 silent polls (lines 44-45) has not run in game yet (it came after C1). If the campaign Lua
  legitimately goes quiet during a long AI pass, it will stop a healthy run. J4 should note the first time it runs.
- `saves/core/` is game-agnostic. It goes to warscape-core through J12 as the report says; no core backlog entry is needed until then.
- The game's own `quick_save.save` and `auto_save.save` stay in `save_games\` (Liam's to delete).

### Merging
No rule changes for other open job branches.
