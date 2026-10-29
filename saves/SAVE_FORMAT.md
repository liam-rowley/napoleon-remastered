# Napoleon save format (ESF) and edit recipes

Owner of what a Napoleon campaign save holds and how to edit it. Tools: `saves/README.md`. Method and Empire background:
empire-remastered `docs/plans/STATE_CONTROL.md` sections 2 and 4. Facts with evidence: the `engine_facts` rows `napoleon.save.*`.
Mapped by J14 on 2026-10-29 from Liam's pairs (one campaign: grand campaign, Britain, 1805 Winter) and the load ladder of run
`20261029_j14pc` (`saves/runs/20261029_j14pc/`). This doc quotes record paths, positions and small numbers, never names or text.

## File
Facts from run 20261029_j14pc, 2026-10-29:

| item | Napoleon |
|---|---|
| location | `%APPDATA%\The Creative Assembly\Napoleon\save_games\<name>.save` (extension `.save`, not `.napoleon_save`) |
| header | u32 magic `0xABCE`, u32 0, u32 timestamp, u32 offset of the name table; root record at 16; nothing after the name table |
| compression, checksum | none: an edited save loads (ladder B and C) and an unchanged rewrite is sha-equal |
| root | `CAMPAIGN_SAVE_GAME v5`: `BUILD`, `SAVE_GAME_HEADER`, `CAMPAIGN_ENV` (`CAMPAIGN_SETUP`, `CAMPAIGN_CAMERA_MANAGER`, `CAMPAIGN_MODEL v10`) |
| size, nodes | about 30 MB, 3.4 M nodes, 627 names; parse + write about 2.2 s, peak about 470 MB (15.6x the file) |
| tags | the Empire set; Napoleon saves use 0x01, 0x04, 0x06, 0x07, 0x08, 0x0a, 0x0c, 0x0d, 0x0e, 0x0f, 0x10 and packed arrays 0x41, 0x44, 0x46, 0x47, 0x48, 0x4a; no unknown tag |
| quick save | `CampaignUI.QuickSave()` writes `save_games\quick_save.save` (overwritten each time) |
| autostart | `campaign:<file name without .save>` (`FrontEnd.LoadCampaign`); a test save is staged as `zz_<name>.save` |

`CAMPAIGN_MODEL` children: `CAMPAIGN_MAP_DATA`, `RandSeed`, `CAMPAIGN_CALENDAR` (`@0` 24, `DATE` year, `@3`), `WORLD`
(`FACTION_ARRAY[41]`, `REBEL_FACTION`, `REGION_MANAGER`, `SPYING_ARRAY`), `LOCOMOTION_MANAGER`, `PENDING_BATTLE`,
`HISTORICAL_EVENT_MANAGER`, `HISTORICAL_CHARACTER_MANAGER`, `CAI_INTERFACE`, `CAMPAIGN_TRADE_MANAGER`, `MARKER_MANAGER`,
`PORTRAIT_ALLOCATOR`, `CAMPAIGN_PATHFINDER`, `EPISODIC_RESTRICTIONS`.

## Ids
Ids are 32-bit handles valid **inside one file only**: a save the engine writes after a load gives regions, diplomacy relationships
and other records new ids (ladder B quick save against its source, run 20261029_j14pc). So a recipe finds records by key (faction,
region, character type) and reads every id it writes from the same file; ids never travel between saves. Positions are 12.20 fixed
point (map units = value / 2^20); `LINE_OF_SIGHT` boxes are f32 pairs on a 1.25 grid.

## Noise for esf_diff
`saves/napoleon/noise.txt` (`--skip @saves/napoleon/noise.txt`): `CAI_INTERFACE` (about 20,000 lines for one agent move),
`CAMPAIGN_PATHFINDER` (obstacle boundaries follow a character's footprint), `QUAD_TREE_BIT_ARRAY` (fog bits). With it the agent
pair is 12 lines and the tax pair 11. `REGION@42` holds nan, which the differ treats as unchanged.

## Field positions
`@N` is the child position over all children (records too), as `esf_diff`, `esf_dump dump` and `esf_edit set` print it.
Paths below start at `CAMPAIGN_SAVE_GAME/CAMPAIGN_ENV/CAMPAIGN_MODEL/WORLD`. Seen in run 20261029_j14pc on 41 factions,
539 characters, 87 forces and 72 settlements:

| record | position | type | meaning | evidence |
|---|---|---|---|---|
| `FACTION_ARRAY[i]/FACTION` | 1st, 2nd, 3rd value | u32, utf16, utf16 | faction id, key, name; **read by value order**: the player faction has an extra `CAMPAIGN_PLAYER_SETUP` record in front, so its `@N` are one higher | all factions |
| `FACTION` | `@1` (player) | rec | `CAMPAIGN_PLAYER_SETUP`, holds the faction key at its `@2` | `FACTION_ARRAY[0]` is the player |
| `.../CHARACTER_ARRAY[j]/CHARACTER` | `@2` | u32 | character id (also `CHARACTER_DETAILS@10`) | agent pair |
| `CHARACTER` | `@3` | utf16 | type: `General`, `colonel`, `admiral`, `captain`, `minister`, `gentleman`, `rake`, `assassin`, `Eastern_Scholar` | all characters |
| `CHARACTER` | `@7` | u32 | residence id it sits in, 0 = field | agent pair |
| `CHARACTER` | `@25` | bool | set when it enters a residence (Empire's `@24`) | agent pair |
| `CHARACTER/LOCOMOTABLE` | `@0,@1` / `@2,@3` | i32 | position / destination (equal when idle), fixed point | agent pair |
| `LOCOMOTABLE` | `@4,@5` | f32 | facing angle | agent pair |
| `LOCOMOTABLE` | `@8` / `@9` | i32 | movement points: maximum / left (29 -> 18 on the move) | agent pair |
| `CHARACTER/LINE_OF_SIGHT` | `@1`, `@2` | xy | sight box corners | agent pair |
| `.../ARMY_ARRAY[k]/ARMY` | `@5` | u32 | residence id of the settlement it garrisons (0 or absent in the field); `NAVY` items share the array | id grep |
| `ARMY/MILITARY_FORCE` | `@0`, `@1` | u32 | force id, commander character id | map |
| `REGION_MANAGER/REGIONS_ARRAY[r]/REGION` | `@0` / `@4` | utf16 / u32 | region key / region id | map |
| `REGION` | `@15` | i32 | moves with the theatre's taxes (-1 -> -26 in the five governed regions): public order from taxes, by the look of it | tax pair |
| `REGION` | `@19` | bool | flipped in the capital's region on the tax change (meaning open) | tax pair |
| `REGION/SETTLEMENT` | `@3` / `@4` | ascii / u32 | settlement key / its residence id | map |
| `SETTLEMENT/SIEGEABLE_GARRISON_RESIDENCE` | `@1` | u32 | residence id | agent pair |
| residence | `@10,@11` | i32 | position, fixed point (an agent inside stands exactly here) | agent pair |
| residence | `@12` | u32 | garrisoned force id | map |
| residence | `@14` | u32 array | ids of the agents inside | agent pair |
| residence `/GARRISON_RESIDENCE` | `@0` | u32 | owner faction id | map |
| `FACTION/GOVERNMENT` | `@1`, `@2` | utf16, i32 | government key, a percentage (49; Empire: popularity) | map |
| `GOVERNMENT/POSTS_ARRAY[p]/CHARACTER_POST` | `@1` | utf16 | post key; `governor_<theatre>` posts carry a `GOVERNORSHIP` | tax pair |
| `CHARACTER_POST/GOVERNORSHIP` | `@2` | u32 array | region ids of the theatre | tax pair |
| `GOVERNORSHIP/GOVERNORSHIP_TAXES` | `@0`, `@1` | u32 | tax level, lower and upper class (0-4) | tax pair |
| `GOVERNORSHIP_TAXES` | `@2`, `@3` | u32 | tax rate %, lower and upper class: 5 + 5 x level | tax pair, both saves |
| `FACTION_ECONOMICS/history[0]/ECONOMICS_DATA` | `@1` | i32 array | projected income figures (moved with taxes) | tax pair |

## Pairs
Liam's pairs, 2026-10-29 (all one turn, 1805 Winter):

| pair | the action | lines (noise skipped) | what it showed |
|---|---|---|---|
| `agent-to-settlement` | a gentleman walks into London | 12 | `CHARACTER@7` 0 -> residence id, `@25` -> True, `LOCOMOTABLE` to the residence position, movement points spent, facing, `LINE_OF_SIGHT` box; the residence's `@14` gains the character id |
| `taxes-changed` | Europe theatre taxes: lower 2 -> 4, upper 2 -> 0 | 11 | `GOVERNORSHIP_TAXES@0..3`, then derived: `REGION@15` in the five governed regions, `REGION@19` in one, projected income |
| `building-queued-unit-recruited` | a building queued and a unit recruited | 0 | the two files differ only in the header timestamp: the save after the action holds the same state; not mapped (open) |

## Links that change together
- Agent in a settlement: `CHARACTER@7` = residence `@1`, and the residence `@14` lists `CHARACTER@2`; `@25` True; the character
  stands at residence `@10,@11`. Moving it out again is the reverse on both ends.
- Army in a settlement: `ARMY@5` = residence `@1`, and residence `@12` = that army's `MILITARY_FORCE@0` (seen, not edited yet).
- Theatre taxes: level and rate together (`rate = 5 + 5 x level`); the region and income values follow from the engine.

## Recipes
`saves/napoleon/recipes/` (each `IN OUT`, never over its input; host tests in `tests/test_saves.py`). Status from the load ladder:

| recipe | kind | what it writes | status |
|---|---|---|---|
| `tax_rates.py` | scalar | `GOVERNORSHIP_TAXES@0..3` of one governorship | PC-proven 2026-10-29, run 20261029_j14pc (ladder B, 2 launches; the quick save holds the edit) |
| `agent_into_settlement.py` | structural | `CHARACTER@7`, `@25`, `LOCOMOTABLE@0..3`, `LINE_OF_SIGHT@1,2` and residence `@14` | loads, PC-proven 2026-10-29, run 20261029_j14pc (ladder C, 2 launches); survival of an EndTurn open |

Replaying each pair with its recipe on the `_a` save leaves only what the engine derives: for taxes the region and income values,
for the agent the facing, the spent movement points and the engine's own sight box.

## Load ladder (run 20261029_j14pc, 2026-10-29)
Base: Liam's `j14_taxes-changed_a` (1805 Winter); `saves/napoleon/load_save.sh`, every launch through the watcher with
`dev.skip_intro=1`; results per step in `saves/runs/20261029_j14pc/ladder.jsonl`.

| step | save | launches | result |
|---|---|---|---|
| A | unchanged rewrite (sha-equal to the base) | 2 | both load in 3.6-5.0 s into `campaign`, 1805 Winter, player's turn |
| B | `tax_rates --lower 4 --upper 4` | 2 | both load; the quick save after the load reads `[4, 4, 25, 25]` |
| C | `agent_into_settlement --region eur_wales` (the rake) | 2 | both load (2.7-3.4 s); the engine's autosave at EndTurn and a quick save after a reload keep both ends of the link (new ids); **EndTurn survival open**: modals during the AI turn and focus loss stalled the Lua pump, launch 1 killed by hand |
| C (QuickSave after the AI pass) | | 0 | not reached; re-run `load_save.sh ... --end-turn --quicksave` once J13 (always-active window) and a popup answer (J15) exist |

## Open
- **EndTurn unattended** (run 20261029_j14pc, ladder C launch 1): an AI diplomacy request during the AI turn and a turn-start event
  are modal; while one is open the game draws no frames and the campaign script does not pump, so no Lua probe can answer or
  dismiss it. A minimised, unfocused window stops the pump too. `load_save.sh --end-turn` now stops after 4 silent polls. Needs an
  always-active window (J13) and a way to answer popups outside the pump (J15). The autosave is written at EndTurn, before the AI.
- Saves of a second turn: every save so far is 1805 Winter; the first EndTurn that completes gives the other turn.
- What `REGION@15` and `@19` are exactly (public order from taxes is the reading); whether the engine recomputes them on load.
- Recruitment and building queues: the pair showed nothing; a new pair saved after the queue is visibly placed (or one EndTurn
  later) is needed.
- Ports, battles, diplomacy: no pairs yet (`port`, `battle` in the J14 brief).
