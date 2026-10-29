# J14: Save editing: ESF tools and Napoleon save format

Phase 1. Port Empire's ESF save tools to Napoleon. Gate: a byte-exact round trip on several Napoleon saves with no unknown tag.
Map Napoleon's record paths from pairs of saves made one action apart, and write them into a save-format doc with edit recipes.
Prove in game, through J3's `campaign:<save>` autostart, that an unchanged rewrite, one scalar edit and one structural edit all
load, and that the structural edit survives an EndTurn. This feeds J4, which generates its mid- and late-game campaign scenarios
by editing saves instead of playing to them.

Model: Sonnet (the format and the method are known from Empire: this job is a port plus differential mapping, not reverse
engineering). Budget about 150 tool calls; at the cap, stop, commit, report what is left. At most 1 subagent, only for independent
work (for example, porting and testing the tools while you run the save-making sitting).

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J14`). Read `docs/DECISIONS.md`, `docs/plans/PLAN.md` section 5 (phase 1), `harness/README.md`,
  `proxy/README.md` "Dev control channel", and `jobs/J3/report.md` (autostart, ctl, the PC sittings).
- Check the tools registry first (`python3 core/wsc.py find save`, `... autostart`, `... deploy`). Build on:
  - `proxy/napoleon/lua/autostart.lua`: the `campaign:<save>` target calls `FrontEnd.LoadCampaign(<save>)` (key `target.save`).
    It is written but **untested** (J3 had no saves). This job is its first real test, so fix it here if it fails.
  - `harness/core/job.sh` (`launch`, `kill`, `profile`, `ctl <owner> "lua ..."`) and the J3 probes under `proxy/napoleon/lua/probes/`
  - the PC deploy tool (sha-checked copy) for getting files onto the PC
- Evidence in `empire-remastered` (read-only, `CLAUDE.md`):
  - method: `docs/plans/STATE_CONTROL.md` sections 2 and 4. Section 4 is the porting plan, and this brief follows it.
  - tools (stdlib, about 1,160 lines): `rml_mod/tools/db/esf_dump.py` (reader, tag table), `esf_edit.py` (byte-exact writer:
    `roundtrip`, `set`, `copy-item`, `remove-item`; end offsets, counts and the name table rebuilt), `esf_diff.py` (node diff by record
    path), `esf_map.py` (semantic summary), `test_esf_edit.py`
  - recipes: `rml_mod/tools/db/save_recipes/` (`_common.py` helpers, `test_save_recipes.py`)
  - format notes: `rml_mod/docs/db/SAVE_FORMAT.md` (Empire record paths: a model of what to write, not facts about Napoleon)

## Target facts (from Empire; every one is checked again on Napoleon)
- Empire saves are ESF: magic `0xABCE` (startpos `0xABCA`), u32 0, u32 timestamp, u32 offset of the name table, root node at 16.
  They are uncompressed and carry no checksum. The root record is `CAMPAIGN_SAVE_GAME` with a `BUILD` string.
- Node tags: 0x01-0x10 scalars, `0x40|t` packed arrays, 0x80 record, 0x81 record array (header of `esf_dump.py`).
- Empire's mapping model: ids are 32-bit handles; positions are 12.20 fixed point; a character's residence id links to the
  residence's agent list (both ends of every link must change together); AI records link to objects only by identical position;
  pending popups and events are **not** in saves.
- Parsing costs about 15x the file size in RAM (a 52 MB save took about 775 MB and 15 s).
- Napoleon (expected, **not checked**): saves in `%APPDATA%\The Creative Assembly\Napoleon\save_games\` (empty on 2026-10-29),
  probably `.napoleon_save`. The Lua API has `CampaignUI.QuickSave` and `CampaignUI.EndTurn`, both "same" as Empire in the static
  diff (`discovery/diff/lua_api.json`); neither has been called on Napoleon yet.

## Saves Liam makes (ask on day one; the tool port does not wait for them)
Each pair is two saves in the **same turn**, `j14_<pair>_a` before one action and `j14_<pair>_b` after it. Any campaign and faction
is fine, but keep it the same campaign for all pairs if possible. Ask for at least `agent`, `tax` and one more:

| pair | the one action between a and b | what it maps |
|---|---|---|
| `agent` | an agent (spy or diplomat) or a general moves **into a settlement** | residences, agent and garrison links |
| `tax` | one region's tax rate changes | a plain scalar |
| `recruit` | one unit queued for recruitment | recruitment queue records |
| `build` | one building queued | building slot records |
| `port` | an army boards a fleet, or a fleet enters a port | force links |
| `battle` | one battle auto-resolved and won | casualties, experience |

The agent makes the round-trip set itself through the watcher: autostart `campaign:new` (J3's keys), `CampaignUI.QuickSave` from
ctl, one EndTurn, then another QuickSave (plus any autosave the game writes). This gives at least 3 saves for the gate before Liam's
pairs arrive, and an EndTurn pair as a bonus.

## Decisions already made for this job
- **Where things live:**
  - The game-agnostic parser, writer, diff and generic map walker go in `saves/core/` (a warscape-core candidate, D10; flag it in
    the report).
  - Napoleon record paths, the semantic map and the recipes go in `saves/napoleon/`.
  - The format doc is `saves/SAVE_FORMAT.md` and `saves/README.md` covers the tools; both stay under the doc cap.
  - Keep Empire's CLIs (`info|roundtrip|tree|dump|set|copy-item|remove-item`, `--under`, `--skip`) so the method in
    STATE_CONTROL.md reads the same.
  - Drop the Empire-only parts (`slots`, Empire record names).
  - Every new file gets a tools row and a header.
- **No game content in the repo.** Saves are never committed.
  - Base saves (Liam's and the agent's) live on the PC in `C:\napoleon_remastered_pc\saves\` (outside the game and AppData folders,
    like D25's install state).
  - Commit a manifest, `saves/napoleon/saves.json`, with name, sha256, size, campaign, faction, turn, maker, date and the run id.
  - Edited saves are regenerated from a base save by a recipe, so they are never kept.
  - The doc may quote record paths, field positions and small numeric values. It does not quote names or text.
- **Liam's saves are read-only.** Copy them into `C:\napoleon_remastered_pc\saves\` with a sha check, and edit only copies.
  - The game reads saves only from `save_games\`. Stage a test save there under a `zz_j14_` prefix, with a sha-checked copy.
  - After the run, move every staged `zz_` file to `_to_delete` (nothing is ever deleted).
  - Nothing else in `save_games\` is touched. The watcher's profile restore does not cover that folder, so the staging tool is the
    only thing that writes there. It refuses names without the `zz_` prefix.
- **Game launches go only through the watcher** (`CLAUDE.md`), with `dev.skip_intro=1` on every test launch, and dev keys off at
  the end as J3 left them.
  - EndTurn and QuickSave are driven through `job.sh ctl ... "lua ..."` (add a small kit-synced probe script under
    `proxy/napoleon/lua/probes/` if needed).
  - The next turn is detected by the ctl result or the scene state, not by repeated agent calls.
- **Round-trip gate:** `roundtrip` writes every save back sha-equal, and a tree walk finds no unknown tag, on at least 3 Napoleon saves
  from at least 2 different turns.
  - A new magic or tag with a plain layout is added to the tag table, and Empire saves must still pass.
  - Run the Empire saves too if any are still on the PC. If none are, run the synthetic fixtures.
- **Mapping:** run `esf_diff` on each pair with the noise skipped (camera, AI interface, pathfinder, fog: find Napoleon's names). The
  lines that remain are the meaning. Write the meanings into `SAVE_FORMAT.md` as record path, field position, type, meaning, the
  pair that showed it, and links that must change together. Port `esf_map.py`'s summary (factions, characters, forces, residences,
  `near`) onto the paths you find.
- **Recipes:** at least one scalar recipe (for example `tax` or a unit's experience) and one structural recipe (for example an agent
  into a settlement: both ends of the link). Each recipe takes `IN OUT` and has a host test on a synthetic tree. A recipe counts
  as "PC-proven" only after its load test. Port more Empire recipes only where a pair mapped the paths.
- **Load ladder** (Empire's esfload), each step through `campaign:<save>` autostart with the scene checked:
  - A: an unchanged rewrite loads
  - B: the scalar edit loads, and the value shows in game (read it from Lua where an API exists, else from a QuickSave re-parsed)
  - C: the structural edit loads, survives one EndTurn (the AI pass) without a crash, and a QuickSave after it still has the edit
    (or shows what the engine rewrote)

  Each step runs 2 launches.
- **Registries:**
  - `engine_facts` rows `napoleon.save.<item>` (magic, compression, checksum, root record, file location and extension, autostart
    by save name, load of edited saves, EndTurn survival, the QuickSave file name). Each has evidence (the run id) and a date;
    inferences are `open`.
  - One `scenarios` row (`kind: campaign`) per load-proven base save. `save` gives the manifest name and sha; `launch` gives the
    autostart line. J3 could not add these.
  - Tools rows for the new files.
- **Not this job:** the campaign console (J15), the scenario library and generated mid- and late-game states (J4: it uses these
  recipes), startpos editing, and saves loadable with and without the mod (phase 6).

## Deliverables
1. `saves/core/` ESF reader, writer, diff and map walker, ported from Empire with the same CLIs. Host tests (stdlib, green in `wsc
   gates`) on synthetic ESF files cover every tag, round trip byte-exact, `set`, `copy-item` and `remove-item` with offsets and
   counts rebuilt, and an unknown tag that is reported with its offset.
2. The round-trip gate on at least 3 Napoleon saves, plus their manifest in `saves/napoleon/saves.json`.
3. `saves/SAVE_FORMAT.md`, with Napoleon record paths from every pair Liam made and the noise list for `esf_diff`.
4. `saves/napoleon/` map and recipes: at least one scalar and one structural recipe, each with host tests.
5. The staging tool (`zz_` only, sha-checked, moves files to `_to_delete`), with host tests on a temp folder.
6. Load ladder A, B and C run, with run ids, and `autostart.lua` fixed if `campaign:<save>` needed it.
7. `engine_facts`, `scenarios` and `tools` rows as above.

## Kill criteria
- A Napoleon save is compressed, encrypted or not ESF (unknown magic and no node layout at 16): stop the edit part. Record what
  the header shows as an `open` fact, then ask Liam.
- The round trip is not byte-exact after about 10 calls of fixing: stop. Report the first differing offset, its tag and its record
  path.
- An unknown tag whose layout is not obvious from its bytes after about 5 calls: stop. Report the offset and the surrounding bytes.
- Step A (unchanged rewrite) fails to load twice: stop the ladder. A hidden checksum or a name-dependent check is likely. Report
  the evidence and do not guess at a fix.
- `campaign:<save>` autostart fails and no fix in `autostart.lua` is found in about 8 calls: stop the ladder and report. Loading
  through the menu by hand is not a fallback, because the ladder must run unattended.
- Two game crashes in a row on edited saves: stop launching, keep the dumps, report.
- Liam's pairs have not arrived when the tools, round trip and ladder A are done: finish ladder B and C on the agent's own saves,
  mark the pair mapping not done, and report.
- Any write into the game folder, any write to `save_games\` without the `zz_` prefix, or a launch outside the watcher would be
  needed: stop and ask Liam.

## Finish
Write `jobs/J14/report.md`. Cover:
- what was built
- the saves used (manifest names, sizes, parse time and memory) and the round-trip result for each
- the load ladder with run ids, and the QuickSave and EndTurn behaviour
- the record paths mapped, by pair
- the facts and scenarios added (ids)
- evidence: commit and CI run ids
- deviations from this brief and why
- what moves to the core (the parser is game-agnostic)
- open questions, listed for J4 and J15 separately

Then `wsc reg set jobs J14 status=review report=jobs/J14/report.md`.
