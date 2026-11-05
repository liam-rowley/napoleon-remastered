# J72: Effects per-file diff: Napoleon smoke and particle definitions against Empire

Phase 2, one measurement, no scope change. J6's pack diff counted the `effects` content kind (94 entries in Napoleon's data.pack against 74 in Empire's
main and patch packs, verdict "adapter: look it up in the other pack(s)", `discovery/diff/packs.json`) but never diffed it file by file, so the Empire
restart list's candidate "Napoleon's smoke and particle effects backported as a pack" (`docs/plans/PLAN.md` section 4; the moonshots record
`docs/plans/MOONSHOTS_2026-11-01.md`, "The Empire smoke backport is undetermined, not hard" and "Aside: backporting Napoleon's vanilla smoke") has no
evidence either way. This job adds an `effects` area to the J6 diff: every effects entry by name, size and identical/changed/new/gone, the effect
definition format and what changed in it, the textures and fx each Napoleon definition references and whether Empire has them, whether Empire's exe
knows the names Napoleon's definitions use, and the three effect db tables compared. Output: `discovery/diff/effects.json` with a `--check`, the fact
`napoleon.diff.effects`, and one feasibility paragraph in PLAN section 4. Nothing is backported, no game is launched, and nothing is written into either
game folder or into `empire-remastered` (D30: read-only evidence).

Model: Sonnet medium (D15). A static diff pass in the shape J6 already set (`discovery/core/shaders.py` is the model), XML and db reading with an
existing decoder, host tests: no reverse engineering beyond a byte search of the two exes, no shader, DLL or crash work, so nothing here earns Opus.
Budget about 70 tool calls; at the cap, stop, commit, report what is left. No subagents. No game launch and no watcher.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J72`). Read `jobs/J6/report.md`, `discovery/README.md`, `discovery/diff/README.md`, and these whole (they are
  the pattern to copy): `discovery/core/shaders.py`, `discovery/core/diffout.py`, `discovery/core/packfs.py` (header and `PackFS`),
  `discovery/core/extracted.py`, the header and `decode_table` of `discovery/core/db.py`, the `--check` of `discovery/core/exe_strings.py`, and
  `tools/verbs/discovery.py` (`AREAS`, `_load`, `render`). Inputs: `discovery/napoleon/games.json` (both installs, pack orders, each game's `mod_packs`).
- `python3 core/wsc.py find effects particle smoke projectile` before writing anything; extend, do not duplicate.
- **J64 ordering, check first.** J64 (queued) moves the whole of `discovery/core/` into warscape-core, and an `effects.py` added there after the move
  would fail rule 76. Run `git ls-remote --heads origin job/J64` and read `registries/jobs/J64.json`: if J64 is `done` or a `job/J64` branch exists, stop
  before writing code (kill criteria). Otherwise go ahead; J64 moves the whole folder, so it carries `effects.py` with it.
- Empire evidence, read-only (`--add-dir ../empire-remastered` if the session lacks it): `rml_mod/tools/db/schema_emp.json` (RPFM `schema_emp.ron`
  converted, its `source` line names the pin), and `docs/learnings/LEARNINGS_ENGINE.md`, the entries "Decision (Liam, 2026-10-22): particles and smoke
  stay vanilla for v1" and "Battle smoke and dust: the drawing PS is not identified" (2026-10-28). Their facts go into the feasibility paragraph.
- `needs_pc` is true: both installs' packs and exes are read in place, read-only, by index offset (`PackFS`). No lock is taken; nothing launches.

## What is there (brief writer's read-only look, 2026-11-03; orientation, not evidence: the tool reproduces or corrects it)
- **Entries.** Napoleon: 94 under `effects` in data.pack (3 XML definition files, 1 text file, 63 dds, 27 tga). Empire: 74 entries, 73 paths (main.pack
  73, patch.pack 1: the patch copy of the land-battle definition wins). Path sets: 21 Napoleon-only (20 textures and the unit-dust text file), none
  Empire-only.
- **Definition files are plain XML** (root `EFFECTS_MANAGER`, then `SCRIPTED_EFFECT_INFO_LIST`, `SCRIPTED_EFFECT_INFO` with attributes,
  `SCRIPTED_EFFECT_GROUP` and its entries, emission controls and modifiers). The naval file is byte-identical (829,306 bytes); the land file is
  1,445,077 bytes in Empire (patch) against 1,938,509 in Napoleon, about 229 against 283 `SCRIPTED_EFFECT_INFO` elements; the campaign file 44,386 against
  130,667. Napoleon adds one tag (`EFFECT_GROUP_AMBIENT_SETTINGS`) and about 16 attribute names (`ribbon_*`, `cell_count`, `cell_size`, `spawn_interval`,
  `wind_offset`, `quality_level`, `radial_blur_*`, ...); none was seen removed. Napoleon's land definitions name `ribbon.fx` (new in Napoleon: J6) beside
  `particle.fx` and `particle_distortion.fx`.
- **Empire's exe and the new names.** A byte search found none of the sampled new attribute names, the new tag, `ribbon.fx` or the unit-dust file name
  in Empire.exe (ASCII or UTF-16LE), and every one in Napoleon.exe (attribute names as UTF-16LE). Empire's parser therefore has no name for them;
  whether it ignores an unknown attribute or rejects the file is a runtime question this job does not answer.
- **db.** Both games have `particle_effects` (key only; Napoleon 104 rows), `projectiles_explosions` and `projectile_trails`; Empire's later patch packs
  override `projectiles_explosions` (patch, patch2). Empire's schema in `schema_emp.json` names them with a `_tables` suffix and lists several versions.

## Deliverables
1. **`discovery/core/effects.py`**, the `effects` area of the J6 diff, header in the tools format and a tools row (`python3 core/wsc.py reg add tools
   discovery/core/effects.py`). It reads both games through `PackFS` (each game's `pack_order`, its `mod_packs` skipped; Empire's loose `data` files are
   mod files: list any loose `effects` file under `detail.empire_loose_skipped`, never compare it) and writes through `diffout`:
   - `detail.files`: every effective `effects` path of either game with size, sha256, which pack it came from, and the verdict (`same` identical,
     `adapter` changed, `new`, `gone`), plus the shadowed copies (Empire's land file in main.pack under patch.pack).
   - `detail.definitions`, for each XML file in both games: parse result, root tag, element counts per tag, attribute names per tag; per
     `SCRIPTED_EFFECT_INFO` and `SCRIPTED_EFFECT_GROUP` name: identical, changed (with the names of the attributes whose values differ), new or gone;
     tags and attribute names new in Napoleon and gone from it. For the text file: its header line and record count; its format, if the header is
     enough to say. Values of the game data are not committed (names, counts and hashes only; values stay in the git-ignored extract).
   - `detail.references`: every texture path and fx name a Napoleon definition references (attribute values ending in `.dds`, `.tga`, `.fx` or
     `.fx_fragment`, normalised to lower case, leading backslash removed), and for each whether Empire has it: textures against Empire's effective
     files, fx against `discovery/diff/shaders.json` `detail.files` (identical, changed, new). Then the Napoleon effects (by name) that reference
     something Empire lacks.
   - `detail.exe_names`: for every Napoleon-only tag and attribute name, plus the fx and text file names referenced only by Napoleon, its count in
     Empire.exe and Napoleon.exe as ASCII and as UTF-16LE (the two exes from `games.json`, read in place).
   - `detail.db`: `particle_effects`, `projectiles_explosions` and `projectile_trails` in both games: pack and file the effective copy came from,
     version, row count, decoded or why not, field names, and keys identical / changed (row content hash differs) / new / gone. Napoleon decodes with
     `discovery/napoleon/db_schema.json`; Empire with a trimmed schema file the job commits, `discovery/napoleon/empire_db_schema_effects.json`
     (only the tables this pass reads, every version, with the `source` line of `schema_emp.json` and that file's sha256), so `--check` does not
     depend on `empire-remastered`. Reuse `db.py`'s `parse_header` and `decode_table`; do not write a second decoder.
   - `detail.smoke`: the subset Liam asked about. Primary: the `particle_effects` keys the gunpowder rows point at (in Napoleon's `projectiles`,
     `projectiles_explosions` and `projectile_trails`, the fields whose `ref` is `particle_effects`, per `discovery/db/tables.json`), and how those keys
     join to the XML (a key equal to an info or group name: say how many join and how). Secondary: definitions whose name matches a fixed, documented
     regex (smoke, musket, cannon, gun, volley, explosion, blast, fire, dust). Each with its definition verdict and its missing references.
   - `rows`: one per definition file, one per db table, one each for the textures (counts of same/changed/new/gone), the definition format (the new tag
     and attribute names), the missing references and the exe names. The README table lists every non-`same` row, so keep them few and readable.
   - `--check`: rebuild in memory and compare with the committed file (rows and detail), exit 1 on a difference, as `exe_strings.py --check` does.
     It reads the installs, so it runs on the PC only.
2. **Wiring.** `effects` joins `AREAS` in `tools/verbs/discovery.py`; `python3 core/wsc.py discovery render` regenerates `discovery/diff/README.md`;
   `discovery check` ok. Add the effects step to `discovery/README.md` "Re-run". Host tests (new `tests/test_discovery_effects.py`, on small synthetic
   XML, db bytes and fake exes, no game needed so they pass on CI): verdicts, the attribute and name diff, reference normalisation and lookup, the
   UTF-16LE count, deterministic output and the `--check` mismatch path.
3. **Fact `napoleon.diff.effects`** (`wsc reg add engine_facts ...`, state `verified`, evidence `discovery/diff/effects.json`, date): the counts
   (files same/changed/new/gone, definitions same/changed/new/gone per file, the new tag and attribute names, the missing references, the db result) and
   the exe-name result, in one claim of the `napoleon.diff.shaders.fx` kind. If the exe-name result is long, a second fact
   `napoleon.diff.effects.empire_exe_names` is fine.
4. **The feasibility paragraph**, one paragraph appended to the Empire restart list bullet in `docs/plans/PLAN.md` section 4 (dated, citing the fact):
   what carries over unchanged (identical files and definitions, textures Empire lacks and can be shipped in a pack), what Empire's exe has no names
   for, what that means for the backport's first proof (one volley captured with the J8 frame-capture tool on Empire, which stays an Empire-restart
   step: D11), and the Empire learning that its battle smoke draw was never identified, which weakens the fallback the bullet names (re-rendering
   smoke from Empire's own sprite draws). Recommend, do not decide: the backport stays a candidate for the Empire restart list. Fix the living copy in
   PLAN section 7's "Napoleon smoke backported to Empire" row ("the 94 vs 74 `effects` entries were never diffed per file") to name the fact. The
   moonshots record is a dated record: leave it unchanged.
5. `python3 core/wsc.py gates` green.

## Out of scope
- Building a backport pack, editing any game data, any Empire launch or capture (D11: one game at a time), any Napoleon launch.
- Any write into either game folder or `empire-remastered`; any change under `core/`, `proxy/` or `harness/` (no rule 79 inputs: say so in the report).
- Committing game data values (definition attribute values, db row values, textures): names, counts and hashes only.
- Downloading anything (an RPFM schema, a tool): Empire's schema comes from `empire-remastered` as above.

## Kill criteria
- J64 is `done`, or a `job/J64` branch exists, when you start: stop before writing code, change nothing, and report; the tool's home (here before J64, or
  warscape-core after) is the orchestrator's call.
- A definition file does not parse as XML in either game and its format cannot be decoded in about 15 calls: record it as undecoded with size and sha256
  only, mark the format open in the fact, finish the rest. The backport stays a candidate.
- An Empire table does not decode with any version of its schema (rows must consume every byte): record "not decoded" with the reason and compare the
  file hash only; do not hand-edit schema fields beyond about 10 calls.
- The work needs a write into a game folder or `empire-remastered`, a download, or a game launch: stop and report.
- Any tool call is refused by a deny rule or the hook: stop and report the call; do not retry another way.
- Over about 70 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J72/report.md` (headings `## What was built`, `## Evidence`, `## Deviations from the brief and why`, `## Open questions`): the tool, the
counts, the smoke subset and its missing references, the exe-name table, the db result, the PLAN paragraph as written, `effects.py --check` ok on the
PC, and the gates output. Then `wsc reg set jobs J72 status=review report=jobs/J72/report.md`.

## Open questions (recommendation taken; Liam may overrule before or during the build)
- **Order against J64.** Recommended: J72 runs and merges before J64 starts, so J64's whole-folder move carries `effects.py`; the orchestrator holds J64
  until then (J72 is the smaller job). The alternative, J72 after J64, makes the tool a warscape-core change (a `W` job) with the outputs here.
- **Empire db schema source.** Recommended: the trimmed committed copy from `empire-remastered`'s converted schema (pinned source line and sha256), not a
  fresh RPFM download (untrusted, and a download needs Liam's say-so).
- **What counts as "smoke".** Recommended: the db-linked set (effects the projectile, explosion and trail rows point at) as the answer, the name regex as
  a cross-check, both listed with their verdicts.
- **Runtime acceptance.** Whether Empire's exe ignores Napoleon's unknown attributes or rejects the file is not answerable without launching Empire.
  Recommended: leave it open in the fact and the PLAN paragraph as the first proof of the Empire restart, not a probe now (D11).
