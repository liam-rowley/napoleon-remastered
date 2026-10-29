# J14 report: Save editing: ESF tools and Napoleon save format

Branch `job/J14`, 2026-10-29, session `23319d67-fff6-4f57-89c3-fc1b90999807`, one PC sitting: run `20261029_j14pc`
(`saves/runs/20261029_j14pc/`). Liam made three save pairs before the job started, so the mapping did not wait.

## What was built
| deliverable | state | where |
|---|---|---|
| 1 ESF reader, writer, diff, map walker with Empire's CLIs | done; 20 host tests on synthetic files (every tag, byte-exact round trip, `set`, `copy-item`, `remove-item` with offsets and counts rebuilt, unknown tag with its offset, unknown packed-array type) | `saves/core/esf_dump.py`, `esf_edit.py`, `esf_diff.py`, `esf_map.py`; `tests/test_saves.py` |
| 2 round-trip gate and manifest | 9 of 9 saves sha-equal, no unknown tag; **one turn only** (see Deviations) | `saves/napoleon/saves.json` |
| 3 save-format doc with paths per pair and the noise list | done for `agent` and `tax`; the third pair held no change | `saves/SAVE_FORMAT.md`, `saves/napoleon/noise.txt` |
| 4 map and recipes | `save_map.py` (factions, characters, forces, settlements, taxes, near); scalar `tax_rates.py`, structural `agent_into_settlement.py`, both with host tests | `saves/napoleon/` |
| 5 staging tool | `stage_save.py stage|clear|list|keep`: `zz_` names only, sha-checked copies, `clear` moves to `_to_delete`; host tests on temp folders | `saves/napoleon/stage_save.py` |
| 6 load ladder | A 2/2, B 2/2, C 2/2 loads; C's EndTurn survival open | `saves/napoleon/load_save.sh`, run folder |
| 7 registries | 10 `engine_facts` (`napoleon.save.*`, `napoleon.campaign.modal_stops_pump`), 3 `scenarios`, 13 `tools` rows | `registries/` |

Also: three campaign probes (`proxy/napoleon/lua/probes/campaign_turn.lua`, `campaign_quicksave.lua`, `campaign_end_turn.lua`) and
`saves/README.md`. Changes to Empire's tools, each a trap found here and fixed in code: `esf_edit set` takes the `@N` that
`esf_diff` prints (Empire counted values only); `esf_diff` no longer reports `nan -> nan`; `--skip @file`; a failed round trip names
offset, tag and record path; `load_save.sh` stops after 4 silent polls instead of waiting 15 minutes on a stalled Lua pump.

## Saves and round trip
All in `C:\napoleon_remastered_pc\saves\` (manifest has names, sha256, sizes). Every save: about 30 MB, parse + write 2.1-2.4 s,
peak working set 470-475 MB (15.6x the file), `OK`:
- Liam's six (`j14_agent-to-settlement_a|b`, `j14_taxes-changed_a|b`, `j14_building-queued-unit-recruited_a|b`), 1805 Winter;
- three the engine wrote in the ladder: `zz_j14_b_qs_...` (QuickSave), `zz_j14_c_autosave_164214` (EndTurn autosave), `zz_j14_c_qs_...`.

## Load ladder (run 20261029_j14pc)
Base `j14_taxes-changed_a`; each launch through the watcher (`dev.skip_intro=1`), `autostart campaign:zz_j14_<x>` by ctl.
- A (unchanged rewrite, sha-equal): 2 launches, loaded in 5.0 / 3.6 s at 1805 Winter on the player's turn.
- B (`tax_rates --lower 4 --upper 4`): 2 launches, 3.4 / 3.5 s; the engine's QuickSave reads `[4, 4, 25, 25]`.
- C (`agent_into_settlement`, the rake into Wales): 2 launches, 3.4 / 2.7 s; the EndTurn autosave and a QuickSave keep both ends.
  Launch 1 ended the turn: an AI diplomacy request during the AI turn and a turn-start event were modal (Liam dismissed both), and
  focus loss stopped the game too; the Lua pump stalled from 16:44:54 and the launch was killed through the watcher at 16:49:44.
  No crash and no hang dump in any launch.
- QuickSave: `CampaignUI.QuickSave()` writes `save_games\quick_save.save`; EndTurn writes `auto_save.save` when the turn is ended,
  before the AI pass. `campaign:<save>` autostart worked unchanged: `autostart.lua` needed no fix.

## Record paths mapped
- `agent-to-settlement` (12 lines with the noise skipped): `CHARACTER@7` (residence id), `@25` (in residence), `LOCOMOTABLE@0..3`
  (position = residence `@10,@11`), `@4,@5` facing, `@9` movement left, `LINE_OF_SIGHT@1,2`; settlement
  `SIEGEABLE_GARRISON_RESIDENCE@14` agent list. Id grep adds `ARMY@5` = residence id for garrisons.
- `taxes-changed` (11 lines): `GOVERNMENT/POSTS_ARRAY[p]/CHARACTER_POST/GOVERNORSHIP/GOVERNORSHIP_TAXES@0..3` (levels, rates =
  5 + 5 x level), derived `REGION@15` in the theatre's five regions, `REGION@19`, projected income.
- `building-queued-unit-recruited`: the two files differ only in the header timestamp; nothing to map.
- Across the whole save: FACTION fields must be read by value order (the player faction has an extra record in front); ids are
  per file (the engine renumbers on every write).

## Facts and scenarios added
`engine_facts`: `napoleon.save.format`, `.compression_checksum`, `.root`, `.location`, `.autostart_by_name`, `.edited_load`,
`.ids_per_file`, `.quicksave_name` (state verified, 2026-10-29, run 20261029_j14pc); `napoleon.save.endturn_survival` (open);
`napoleon.campaign.modal_stops_pump`.
`scenarios`: `campaign_britain_1805`, `campaign_britain_1805_tax44`, `campaign_britain_1805_rake_wales`.

## Evidence
Commits `f244d02`, `708059d`, `a7df189`, `af21f9a`, `a050662` and this report's commit. CI `gates`: 40913112561 and 40913775560
green; 40916117596 for `a050662`. Local `wsc gates`: 12 ok, 110 host tests. PC: kit `kit_20261029T163945Z_af21f9aa063d`
(DLL build `a7df189d1dc7`) installed, then uninstalled: game folder identical to the pre-install snapshot (1564 files); staged
`zz_` saves moved to `_to_delete\saves_20261029T165049Z`; lock released.

## Deviations from the brief, and why
- **Round-trip gate: one turn, not two.** All nine saves are 1805 Winter: the brief's second turn was to come from an EndTurn
  QuickSave, which the modals stopped. The byte-exact part holds on all nine, including three the engine wrote itself.
- **Ladder C: EndTurn survival not shown.** C loads twice and the link survives the engine's own writes, but no save after the AI
  pass exists. Re-running it unattended needs an always-active window (J13 already plans borderless plus swallowed deactivation, as
  Empire's `swallow_activation`) and a way to answer AI popups outside the Lua pump (J15). Liam asked for the window change during
  the sitting; it is J13's scope (a proxy DLL change), so it was not built here.
- **Two pairs mapped, not three:** the `building-queued-unit-recruited` pair holds identical state.
- The agent made no `campaign:new` saves of its own: Liam's six were already there, and a new campaign would have been a third turn
  of the same blocker.
- Extra: three Lua probes, `load_save.sh` (kept in the repo, not scratch: J4 needs the same sequence), and the fixes listed above.

## What moves to the core
`saves/core/` is game-agnostic ESF (no Napoleon paths): reader, writer, diff, generic map walker and their tests in
`tests/test_saves.py` (`Codec`, `Diff`). Candidate for J12 as a warscape-core library plus a `wsc save` verb. `stage_save.py` and
`load_save.sh` have Napoleon defaults (folders, probe paths) and would need an adapter first.

## Open questions
For J4:
- Ids are per file: generate scenarios by key (faction, region, type) and read every id from the save being edited.
- Which states need a pair Liam has not made yet: recruitment or building queues (a pair saved after the queue shows, or after an
  EndTurn), port, battle. A recipe for an army into a settlement can follow the agent one (`ARMY@5` plus residence `@12`).
- Should derived values be written too (`REGION@15` after a tax edit), or always left to the engine? The B load did not show
  whether the engine recomputes them on load.

For J15:
- Ending a turn unattended: the AI diplomacy request and turn-start events are modal and stop the campaign Lua pump (fact
  `napoleon.campaign.modal_stops_pump`). Can the console (or a hook outside Lua) answer or suppress them, or switch AI diplomacy
  off for test runs?

For Liam:
- `save_games\` now also holds the game's own `quick_save.save` and `auto_save.save` from the sitting; they are the game's files,
  left in place. Delete or keep as you like.
