# J6 report: Empire to Napoleon diff

Built on branch `job/J6`, 2026-10-29, in a local Claude Code session on the PC (Opus 5.5; Lua API area by one Sonnet subagent).
Results: `discovery/diff/README.md` (generated), one `discovery/diff/<area>.json` per area, 16 `napoleon.diff.*` engine_facts rows.

## What was built
- `discovery/core/`: `diffout.py` (fixed diff schema and writer), `extracted.py` (one copy per entry with patch-pack precedence),
  and one pass per area: `packs.py`, `layouts.py`, `fonts.py`, `lua_api.py`, `shaders.py`, `exe.py`.
- Ported from empire-remastered (header added, otherwise as noted): `uic.py` (adds the Version039 spec, `state_ref`, the animation
  list), `tpl.py`, `cuf.py`, `api_inventory.py`, `luachunk.py`.
- `discovery/napoleon/`: `games.json` (install paths, Empire's mod packs, pack orders) and `carry_over.json`.
- Changed: `proxy/tools/pack_list.py` gains `read_header` (header fields and raw index, for the index hash) and `--ext`/`--under`
  filters (layouts have no extension, so `--grep` could not select them).
- `wsc discovery check|render` verb (`tools/verbs/discovery.py`), and `discovery/README.md` (inputs and re-run steps).
- Host tests: `tests/test_discovery.py` (schema, committed files valid, README current, pack kinds, a synthetic V039 layout
  with 0-2 animations round-tripping, font name rule, exe masking and search) and `tests/test_discovery_lua.py` (subagent, 6 tests).
  All 16 pass locally. Tools rows for every new file.

## Carry-over (from `discovery/napoleon/carry_over.json`)
| Empire tool family | Verdict |
|---|---|
| pack index reader | as-is (same PFH0; map content by top folder, not by pack name) |
| layout codec `uic.py` | adapter (V039: `state_ref`, animation list, longer transitions; V028-V033 unchanged) |
| `tpl.py` (uied.templates) | adapter (record versions v35, v39) |
| `cuf.py` fonts | as-is (74/74 round-trip, 73 byte-identical to Empire's) |
| Lua API inventory | as-is (497/497 scripts parse) |
| fx effect sources | adapter (per file: 71 identical, 61 changed, 4 new, 9 gone) |
| exe sites and signatures | rewrite (different build: 6/23 guard and 2/26 patch signatures hit uniquely) |

## Evidence
Every area file was produced by the tool next to it, from the Steam installs on this PC on 2026-10-29. Re-running all six passes
left the committed JSON unchanged (deterministic). CI gates on `job/J6`: runs 40892024184 and 40893792872 succeeded on earlier commits; the
final commit's run is on the branch. The facts' `evidence` is the area file (`discovery/diff/<area>.json`), not a `runs/` folder: nothing launched.

Facts added (all dated 2026-10-29): verified `napoleon.diff.packs.format`, `.packs.kinds`, `.packs.loose_files`,
`.layouts.versions`, `.layouts.template_records`, `.fonts.cuf`, `.lua_api.inventory`, `.shaders.fx`, `.exe.pe`. Open:
`.layouts.v039`, `.layouts.v039_transitions`, `.lua_api.surface`, `.shaders.j8_flags`, `.exe.guard_candidates`,
`.exe.patch_candidates`, `.exe.function_candidates`.

## Deviations from the brief and why
- **No device VM.** The session ran on the PC itself with the game folders attached, so the tools ran in place from the repo
  checkout instead of as single files under `C:\napoleon_remastered_pc\_scratch\j6\`. Still read only: no game launched, no lock, no
  watcher job; nothing written in either game folder. Extracts went to the git-ignored `/extract/` of the checkout.
- **Empire read from the install, not only the repo baselines.** Pack headers and indexes were read from Empire's packs (the TSV has
  no header fields or index bytes), and fonts, fx sources, layouts and `.luac` were extracted from them, so both sides of each diff
  went through the same reader. Empire.exe was read for the exe pass. Empire's mod packs (`games.json` `empire.mod_packs`) were left out.
- **Empire.exe on disk is not `exe_patches.json`'s `stock_sha1`** (on disk `2b8650bf…`, stock `74a79124…`). It is the build Empire
  pinned (`empire-remastered rml_mod/docs/exe_guard.md`: same TimeDateStamp 0x6421f11c); all 23 guard-site byte patterns sit at their
  VAs in it, and 33 of 52 patch anchors still hold their stock bytes. The patch windows therefore mask the value bytes. The exe diff
  row records the mismatch.
- **Exe signatures from Empire.exe bytes.** The patch tables have 3-4 byte anchors and the annotations have no bytes, so the
  signatures are Empire.exe windows (±16 bytes around patch anchors, the first 32 bytes of named functions) with rel32 operands and
  in-image absolute dwords masked. The 620 `dyninit_*` static initialisers were left out.
- **V039 decoding stopped at the kill criterion** (about 15 calls): 45 of 136 round-trip. What is known and the next difference are
  the two open `layouts` facts. The v35 template record was not decoded at all.
- The Lua API pass compares against Empire's `engine_api.json` (436 scripts) rather than re-running the inventory on Empire's 445
  extracted scripts: part of that diff may be the script set, not the engine (noted in the fact).
- Full `wsc gates` on this PC fails 3 tests in `test_job_sh` and `test_pc_deploy`. Those tests drive `job.sh` and the harness, which
  need a real `python3`, and on this PC `python3` is the Microsoft Store stub. The fast gates pass, the new tests pass, and CI is the authority.

## What moves to the core later
`diffout.py`, `extracted.py`, the pack header reader, `uic.py`/`tpl.py`/`cuf.py`, `api_inventory.py`/`luachunk.py` and the exe
masking and search are game-agnostic. `discovery/napoleon/*.json` and the Empire-specific signature sources stay per game.

## Open questions
**For J7 (pack reader adapter, asset index):**
- Content is laid out by top folder, not pack name. Use `packs.json` `detail.*_packs.*.kinds` and the pack load orders in `games.json`.
  Only `local_en_patch.pack` is a patch pack (type 2) in Napoleon.
- Loose `data\` files never share a path with a pack entry in vanilla. Is a loose override honoured? `napoleon.files.loose_probe_dirs`
  says the engine probes for them, but no vanilla case exists to prove it.
- `ui\templates` holds 456 extensionless layouts in data.pack. The asset roles for V039 layouts need `uic.py` to finish V039
  (`napoleon.diff.layouts.v039_transitions`).

**For J8 (shader catalogue, frame anatomy):**
- Read the flagged changed sources first (`napoleon.diff.shaders.j8_flags`): `sprite.fx` changed by 1,577 lines, `variantmesh.fx`,
  `imposter.fx`, `shadowmap.fx_fragment`. No source is named LOD.
- Napoleon ships no compiled shaders, so the runtime catalogue by hash has to be captured live, as on Empire.

**For J9 (engine API surface, engine sites):**
- Verify the 6 unique guard-site candidates and the 2 unique patch candidates (grass grid 0x1019ad8, shadow light sweep 0xd27696)
  with anchor bytes and a run id before any `engine_sites` row.
- Sprite, naval LOD and flag-size tweakers match several near-identical initialisers. Find them from Napoleon's own tweaker strings,
  not from Empire signatures.
- Are the 28 new and 8 gone CampaignUI names real at runtime? Check the 38 argument-count differences and the per-screen surface.
  The static diff includes build-system names (`buildcommands`, `project`, ...) from a non-game script; filter them.

**For Liam:**
- `python3` on this PC is the Microsoft Store alias. `job.sh` and three host tests need a real
  `python3` here. Turning off the alias (Settings > Apps > Advanced app settings > App execution aliases) and putting Python 3.14
  on PATH as `python3` would fix it.
