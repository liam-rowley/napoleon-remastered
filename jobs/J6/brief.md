# J6: Empire to Napoleon diff

Phase 2, first discovery pass: diff Napoleon against Empire in six areas (packs, UI layouts and templates, fonts, Lua API, shaders, exe).
For each area, say what carries over from Empire's tooling as-is or through a small adapter, and what is new. Findings become
`engine_facts` rows with evidence. Each area gets one committed tool with a fixed output format. Read-only: no game launch, no feature work.

Model: Opus, reason: binary format reverse engineering (layout and template versions, fonts, PE and byte-signature matching) and an
independent re-check of Empire's engine claims on a different exe (D15). Budget about 150 tool calls; at the cap, stop, commit, report
what is left. At most 2 subagents, only for independent cloud work (for example, one ports the Lua API inventory while you do layouts).

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J6`). Read `docs/DECISIONS.md`, `docs/plans/PLAN.md` sections 3 and 5 (phase 2), and the
  reports of J2 (PC access: `job.sh`, kits, sha-checked copies) and J3 (the dev pack, Lua bridge and `wsp.vanilla`; these tell you how
  Napoleon's packs and Lua behave).
- Check the tools registry first (`python3 core/wsc.py find pack`, `... lua`, `... exe`). This repo already has `proxy/tools/pack_list.py`
  (PFH0 index and extract), `luac_list.py` (Lua 5.1 bytecode with the 4-byte float, `--calls`) and `exe_info.py` (PE identity). Extend
  these. Do not write near-duplicates.
- Attach `liam-rowley/empire-remastered` as read-only evidence (never modified). The Empire baselines are already in that repo, so
  most of the Empire side needs no PC:
  - packs: `assets/extract/pack_entries.tsv.gz` (header index of every Empire `data\*.pack`)
  - layouts: `ui_scale_mod/FORMAT.md` and `tools/uic.py` (layout codec, Version025-033, byte-exact round trip), `tools/tpl.py`
    (`uied.templates`), `assets/extract/layouts/*.json`
  - fonts: `ui_scale_mod/tools/cuf.py` (CUF0 bitmap fonts; all 43 vanilla files round-trip)
  - Lua: `ui_scale_mod/tools/api_inventory.py`, `luachunk.py` and `rml_mod/docs/engine_api.json` (Empire's engine API inventory)
  - shaders: `gfx_mod/shaders/catalog.json` (439 runtime shaders by hash). `docs/learnings/LEARNINGS_ENGINE.md` notes that Empire ships
    its effect sources as `data/main.pack` `fx\*.fx` (141 files).
  - exe: `rml_mod/src/exe_guard_sites.h` (Empire engine functions with their first 16 bytes), `rml_mod/data/exe_patches.json`
    (sprite, shadow, fit and grass patch sites), `perf_mod/re/annotations/{functions,labels}.jsonl` (named engine functions)
  Port these tools rather than copying them. Port a tool only when its area needs it, and give each ported tool a header and a tools row.

## Target facts
- Napoleon `data\` (read 2026-10-29 in the briefing chat): `battleterrain, boot, buildings, data, local_en, local_en_patch, media,
  rigidmodels, sound, variantmodels, variantmodels2` `.pack`, plus loose `data\UI\`, `campaign_maps\`, `campaigns\`,
  `all_scripted.lua` and `battle_scripted.lua`. Empire's pack set and names differ (for example, `main.pack`, `patch*.pack` and
  `ui.pack`). Do not assume a mapping between them: build it from the indexes.
- `Napoleon.exe` identity and Lua: the `engine_facts` rows `napoleon.exe.identity` and `napoleon.lua.loadlib_bridge`
  (Lua 5.1, 4-byte float).
- Empire is installed on the PC at `C:\Program Files (x86)\Steam\steamapps\common\Empire Total War`. Liam pre-granted folder access.
  Request it **read-only in practice**: read it only when a repo baseline is missing (for example, the `fx\*.fx` sources or the exe
  bytes). Never write there and never launch Empire (D11).

## Decisions already made for this job
- **Read-only on the PC.** No game launch, no game lock, no watcher jobs. Tools run on the device VM as single files copied under
  `C:\napoleon_remastered_pc\_scratch\j6\` (the pattern `exe_info.py` uses). Pass the multi-GB packs as paths; never stage them to the
  cloud. Stage only small extracts (layouts, templates, fonts, `.luac`, `.fx`) into the cloud, under the git-ignored `/extract/`.
- **No game files in the repo** (public repo, `.gitignore` `/extract/`). Commit only derived data: paths, sizes, hashes, versions,
  field tables, counts and API names.
- **Where things go:** the tools go in `discovery/core/` (game-agnostic readers that take the game as an input; core candidates, D10)
  and `discovery/napoleon/` (paths and quirks). Each pass writes `discovery/diff/<area>.json`: a fixed schema, deterministic, sorted,
  with no timestamps inside, so a re-run diffs cleanly. A `wsc` verb or a small generator renders the six files into one
  `discovery/diff/README.md`. Its top table has these columns: area, item, Empire, Napoleon, verdict, adapter note, evidence.
  The verdict is one of `same`, `adapter`, `new` or `gone`. Keep the README under the doc cap.
- **engine_facts** rows use ids `napoleon.diff.<area>.<item>`, with `evidence` pointing at the JSON or run folder, plus a date.
  An inference that the job did not check stays `open`. A byte-signature hit is **not** an engine site: `engine_sites` rows are J9's.
  Record the hits as `open` facts that J9 can verify.
- J7 owns the pack reader adapter and the asset index. J8 owns the runtime shader catalogue and frame anatomy. J9 owns engine sites
  and the per-screen API surface. J6 records what those jobs need to know about format and carry-over. It does not build their outputs.

## Deliverables
1. **Packs:** for every Napoleon pack, record the header (magic and version, pack type, flags), entry count, top-level folders and
   hash of the index. Compare against Empire's index: the format verdict, the folder-root overlap, and which Empire pack each content
   kind moved to. Also cover the loose `data\` files and folders: are they read in place of pack entries, per the
   `napoleon.files.loose_probe_dirs` fact?
2. **Layouts and templates:** for every UI layout file (packs and loose `data\UI\`), give its `Version0NN` and whether Empire's codec
   round-trips it byte for byte. Do the same for `uied.templates` record versions. For a version Empire never had, give the field
   differences found. Do not do a full decode beyond the kill criterion.
3. **Fonts:** every `.cuf` file (or whatever replaces it), its header and glyph count, and whether `cuf.py` round-trips it. Map the
   font names layouts reference to files, and compare that map with Empire's.
4. **Lua API:** run the ported API inventory over every compiled UI script in Napoleon. Then diff it against Empire's
   `engine_api.json`: engine globals, table APIs (for example `CampaignUI.*`), component methods and event names, each marked
   `same`, `new` or `gone`. Also cover the loose `*_scripted.lua` entry points.
5. **Shaders (static only):** the effect sources (or compiled shaders) Napoleon ships: list, sha256 and technique names. Diff them
   file by file against Empire's (from Empire's install if the repo has no copy): identical, changed (diff size) or new. Flag
   anything named shadow, imposter, sprite or LOD for J8.
6. **Exe:** a PE diff (sections, imports, size, LAA/ASLR/NX, strings count). Search Napoleon.exe for every Empire engine-function and
   patch-site signature in the Empire files above, masking relocated dwords. Record hits (unique, multiple or none) with their RVA
   as `open` facts, so J9 starts from candidates.
7. `discovery/diff/README.md` (generated) opens with a carry-over summary. For each Empire tool family above, give one of
   `as-is`, `adapter (what)` or `rewrite (why)`.
8. Host tests for each reader's pure logic (round-trip on synthetic inputs, signature masking, JSON schema), green in `wsc gates`.
   Tools rows and headers for every new file.

## Kill criteria
- One format (a layout or template version, or the font file) still fails to round-trip after about 15 calls: stop decoding it.
  Record what is known and what differs as an `open` fact, then move to the next area.
- Any area needs a game launch, a live probe or a debugger to answer: do not launch. Record the question as an `open` fact naming the
  job that owns it (J8 or J9).
- Device-VM file access to the Napoleon or Empire folder fails twice: stop the PC part, finish everything the repo baselines allow,
  and report what is missing.
- Any write into either game folder would be needed: stop and ask Liam.

## Finish
Write `jobs/J6/report.md`. Cover the carry-over table, the facts added (ids), the run ids, deviations from this brief and why, what
moves to the core later (`discovery/core/`), and open questions. List them for J7, J8 and J9 separately. Then
`wsc reg set jobs J6 status=review report=jobs/J6/report.md`.
