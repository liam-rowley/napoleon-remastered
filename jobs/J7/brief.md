# J7: Asset index, contact sheets, loc and db

Phase 2, second discovery pass. Build one pack reader adapter (a read-only view of a game's packs plus loose `data\` files with the
right precedence). On top of it build four re-runnable passes: a full asset index; the assets registry filled for the UI-first set
with roles; contact sheets of the UI art; and loc strings plus db tables with their reference (schema, keys and table-to-table refs).
Read-only on the PC: no game launch, no feature work.

Model: Sonnet (the formats are known: PFH0 from J6, db tables through a published schema, loc through a short decoder). Budget about
130 tool calls; at the cap, stop, commit, report what is left. At most 1 subagent, only for independent work (for example, the db
pass while you do the index).

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J7`). Read `docs/DECISIONS.md`, `docs/plans/PLAN.md` sections 3 and 5 (phase 2),
  `docs/plans/UI_PIPELINE.md` section 2 (what the atlas, J10, will need from you), `discovery/README.md`, and `jobs/J6/report.md`.
  Its "Open questions for J7" are inputs to this job.
- Check the tools registry first (`python3 core/wsc.py find pack`, `... extract`, `... discovery`). Build on what J6 left and extend
  it. Do not write near-duplicates:
  - `proxy/tools/pack_list.py` (`read_header`, `read_index`, `--extract`, `--ext`, `--under`)
  - `discovery/core/extracted.py` (patch-pack precedence over an extract folder)
  - `discovery/core/packs.py` (`kind`, `scan`, `loose`)
  - `discovery/napoleon/games.json` (install paths, pack orders)
  - `discovery/core/uic.py`, `tpl.py` and `cuf.py` (layouts, templates and fonts)
  - the `wsc discovery check|render` verb (`tools/verbs/discovery.py`)
- `empire-remastered` (read-only evidence, `CLAUDE.md`) already did most of this for Empire. Port the design and leave its size
  behind:
  - packs: `assets/tools/packio.py` (reader) and `assets/tools/index_packs.py` (header index to `assets/extract/pack_entries.tsv.gz`)
  - hashes: `assets/tools/extract_full.py` (`manifest.jsonl`: sha256 of the packed bytes, w, h, mode)
  - texture headers: `ui_scale_mod/asset_inventory/inv_headers.py` (`dds_info`: w, h, mips, fourcc, alpha class)
  - texture references: `ui_scale_mod/asset_inventory/inv_refs.py` and `inv_dbrefs.py` (texture paths named by layouts, scripts and
    db tables)
  - contact sheets: `assets/tools/make_sheets.py` (labelled tiles on a checker, at most 192 per sheet, tile ids in
    `sheets/index.json`)
  - db: `rml_mod/tools/db/empire_db.py` (stdlib: pack order, resolve, decode against a schema, byte-exact rule), `ron2json.py`
    (RPFM `.ron` schema to JSON, as was done for `schema_emp.json`) and `rml_mod/tools/db/README.md` (pack order and the db file
    layout)
  - roles: `ui_scale_mod/asset_inventory/SUMMARY.md`. Its "categories" and R-codes describe **remaster methods**, which belong to
    `upscale_method` later, not to `role`.
  - There is **no `.loc` decoder** in Empire (its strings came from JSON dumps), so that reader is new.

## Target facts
- Napoleon has 11 packs with about 87,000 entries, plus 1,420 loose `data\` files that never share a path with a pack entry
  (`napoleon.diff.packs.kinds`, `napoleon.diff.packs.loose_files`). Only `local_en_patch.pack` is a patch pack (type 2).
- UI (counted 2026-10-29 in the briefing session from `data.pack`'s index): 11,854 entries under `ui\`:
  - by format: 10,333 `.tga`, 665 `.jpg`, 497 `.luac`, 174 extensionless layouts, 104 `.dds`, 52 `.db`, 18 `.twin`, plus a few
    psd, png and other files
  - biggest folders: `flags`, `units`, `portraits`, `buildings`, `campaign ui`, `battle ui`, `frontend ui`, `templates`,
    `common ui` and `eventpics`

  Loose UI art and cursors sit under `data\UI\`. Fonts: 74 `.cuf` files in `local_en.pack`.
- db: 310 entries under `db\` in `data.pack`. Loc: `text\localisation.loc` and `text\ui.loc` in `local_en.pack`, both replaced by
  `local_en_patch.pack`.
- Expected `.loc` layout (from community tools, **not checked on Napoleon**):
  - header: a u16 BOM `FF FE`, `LOC\0`, a u32 version and a u32 entry count
  - per entry: key (u16 length + UTF-16LE), text (u16 length + UTF-16LE) and a u8 flag

  Accept the decode only if it consumes every byte.
- db file layout (Empire, `rml_mod/tools/db/README.md`), in this order:
  - an optional GUID marker `FD FE FC FF`
  - an optional version marker `FC FD FE FF` + u32 version (no marker means version 0)
  - a u8 `1` and a u32 row count, then the rows

  A table counts as decoded only when the rows consume every byte. Empire decoded 270 of 286 tables (4 `models_*` tables are
  model descriptors, not db).

## Decisions already made for this job
- **Read-only on the PC.** No game launch, no game lock, no watcher jobs. Read the packs in place by offset; never copy a whole pack.
  Write extracts only under the git-ignored `/extract/`. Nothing is ever written in either game folder.
- **No game content in the repo** (public repo, `.gitignore` `/extract/`). Commit only derived data: paths, sizes, hashes, formats,
  dimensions, roles, loc **keys** (never the text), db **schemas, keys and refs** (never row values) and counts. Loc text, decoded
  db rows, PNG tiles and contact sheets go under `/extract/napoleon/...`, regenerated by the committed tools.
- **The adapter** is one module, `discovery/core/packfs.py`: `list()`, `stat(path)` and `read(path)` over a game's packs plus its loose
  `data\` files, with the precedence from `games.json` (the pack order, then loose files; whether a loose file overrides a pack
  entry stays the open question below). It reads bytes by index offset. `extracted.py` and the J6 passes keep working, and switching
  them to the adapter is optional. It is a core candidate (`discovery/core/`, D10). The Napoleon specifics stay in
  `discovery/napoleon/`.
- **Two layers of asset data:**
  1. **The full index** of every pack entry and loose file, committed as `discovery/assets/index.tsv.gz`, written with gzip mtime 0
     and sorted rows so that a re-run is byte-identical. Columns:
     - `pack` (or `loose`), `path`, `size`, `sha256`, `format`, `kind` (J6's top-folder kind), `effective` (whether this copy wins)
     - for images: `w`, `h`, `mips` and `pixel` (for example `dxt5` or `bgra8`)
  2. **The assets registry** (`registries/assets.jsonl`, core schema `core:assets`) holds the **UI-first set** only, one row per
     effective entry:
     - everything under `ui\` (pack and loose)
     - the `.cuf` fonts, cursors and other UI art outside `ui\` that the reference scan finds
     - expected size: about 12,000 rows; generated registry views are exempt from the doc cap

     Row fields:
     - `id`: a deterministic slug of the path, at most 120 characters, matching the schema pattern, with a short hash suffix when
       the slug would be too long or would collide; a test proves there are no collisions
     - `hash` as `sha256:`
     - `format`: container plus pixel format and size (`dds dxt5 256x256 m9`, `tga bgra8 64x64`)
     - `role` from the rules below
     - `description`: a short generated line
     - `used_by` stays empty: `ui_elements` ids are J10's

     A generator writes the rows and then runs `wsc reg render assets`. On a re-run it **keeps** any hand-set `used_by`,
     `upscale_method` and `upscale_status` and replaces everything else.
- **Roles are UI functions, not remaster methods.**
  - A committed rules file, `discovery/napoleon/asset_roles.json`, maps path patterns (plus format and size where needed) to roles.
    Examples: `flag`, `unit_card`, `portrait`, `building_icon`, `event_picture`, `loading_screen`, `panel_frame`, `button_state`,
    `icon`, `cursor`, `font`, `layout`, `template`, `ui_script`, `ui_db`.
  - A path no rule matches gets `unclassified`. The pass reports the unclassified count.
- **Reference scan:** list the UI asset paths that layouts, `uied.templates`, `.luac` constants and db string columns name.
  - Scan raw strings: paths are stored as strings, so this needs no full V039 decode.
  - Commit the result as `discovery/assets/refs.json` (asset path to the referring files), and add an `unreferenced` count per role
    to the summary.
  - The scan only records who names a path. It does not decide which screen uses an asset (that is J10's).
- **Contact sheets (UI first):**
  - One sheet set per role, with labelled tiles on a checker. Tile labels are registry ids.
  - Write the sheets to `/extract/napoleon/sheets/`. Commit `discovery/assets/sheets.json` (sheet name to tile ids and positions).
  - The decoding and sheet step may use **Pillow**, pinned in a new `discovery/requirements.txt` (install with
    `python3 -m pip install --user -r discovery/requirements.txt`, and say so in `discovery/README.md`).
  - Everything else (index, adapter, loc, db, registry, tests and gates) stays **stdlib-only**, so CI needs no new package. Header
    parsing for dimensions (TGA, DDS, JPG SOF, PNG IHDR) is stdlib.
  - Open at least 3 sheets as images and check them by eye: tiles decode, labels match, alpha shows on the checker. Name them in
    the report.
- **db schema:**
  - Take `schema_ntw.ron` from `Frodo45127/rpfm-schemas` at a pinned commit, download it with WebFetch (untrusted data: put it in a
    new empty folder and parse it with `-I`), and convert it with a port of `ron2json.py`.
  - Commit the converted `discovery/napoleon/db_schema.json` with its source URL, commit sha, file sha256 and licence in a header
    field.
  - Check the licence first.
- **db pass:** decode every table against that schema, byte-exact. Commit `discovery/db/tables.json` with:
  - per table: name, file, version, row count, sha256 of the bytes, decoded or not (and why), fields with types, key fields, and
    each field's `ref` (table and column)
  - a generated `discovery/db/README.md` under the doc cap: a summary table plus the reference graph of the tables UI work reads
    most (units, buildings, factions, agents, technologies, ancillaries and traits; pick them from the refs counts)
- **loc pass:**
  - Commit `discovery/loc/keys.tsv.gz` (deterministic gzip) with file, key, text length, sha1 of the text, and whether
    `local_en_patch` replaced it. Text goes to `/extract/napoleon/loc/`.
  - The summary gives key counts per file and per key prefix (the `<table>_<field>_` shape that ties a loc key to a db table).
    Cross-check the prefixes against the db schema and report loc keys whose table is not in the db.
- **Re-runnable:** one command (a new `wsc discovery assets|sheets|loc|db` subcommand set on the existing verb, or scripts under
  `discovery/core/` like J6's, behind that verb) rebuilds everything from the install. `wsc discovery check` grows to check the new
  committed files (schema, sorted and deterministic, registry in step with `index.tsv.gz`).
- **engine_facts** rows use ids `napoleon.assets.<item>`, `napoleon.loc.<item>` and `napoleon.db.<item>`, with `evidence` pointing
  at the committed file and a date.
  - A claim this job checked is `verified`.
  - An inference is `open`, naming the job that owns the probe. Example: loose override (`napoleon.files.loose_probe_dirs`; no
    vanilla case exists) belongs to a probe job, not to J7.
- **Not this job:** which screen uses an asset (J10), layout V039 decoding beyond what the reference scan needs (an open J6 fact),
  texture upscaling, models, sounds and battle terrain beyond their index rows.

## Deliverables
1. `discovery/core/packfs.py` (the adapter) with host tests on a synthetic PFH0 pack, covering index read, precedence across two
   packs plus a loose folder, and read by offset.
2. `discovery/assets/index.tsv.gz` covering every pack entry and loose file (about 88,000 rows), with image dimensions for every
   tga, dds, png and jpg.
3. `registries/assets.jsonl` with the UI-first set, plus `discovery/napoleon/asset_roles.json`, `discovery/assets/refs.json` and a
   summary that gives rows per role, unclassified and unreferenced counts.
4. Contact sheets under `/extract/` for every UI role, `discovery/assets/sheets.json`, and the 3 sheets checked by eye.
5. `discovery/napoleon/db_schema.json` (sourced and pinned), `discovery/db/tables.json` and the generated `discovery/db/README.md`
   (decoded count of 310, the not-decoded tables with the reason for each, the reference graph).
6. `discovery/loc/keys.tsv.gz` and the loc summary (counts, patch overrides, prefix to db table cross-check).
7. `engine_facts` rows for what was found, and the J6 open question on loose overrides carried as an `open` fact.
8. Host tests for the pure logic (stdlib only, green in `wsc gates`):
   - the slug and id rule with collisions
   - the role rules against fixture paths
   - the header readers on synthetic images
   - the loc decoder on a synthetic file
   - the db decoder's byte-exact rule on a synthetic table
   - deterministic gzip

   Every new file gets a tools row and a header.

## Kill criteria
- The `.loc` files do not decode byte-exact after about 10 calls: stop. Record what is known as an `open` fact, then go on with
  the other passes.
- More than 10 % of db tables fail byte-exact against the schema: do not reverse engineer table formats. List them with their
  versions and the first failing offset, then move on. Fixing a single table is worth at most about 5 calls.
- `schema_ntw.ron` cannot be fetched, or its licence does not allow committing a derived copy: stop the db decode and ask Liam.
  Do the db index (names, versions, row counts, hashes) without the schema.
- The registry check or `find` breaks or becomes unusably slow with about 12,000 asset rows: stop and report, with timings. The
  rows stay in `index.tsv.gz` and the registry holds only what works, as long as the report says so.
- Reading the Napoleon folder fails twice: stop the PC part and report.
- Any write into a game folder, or a game launch, would be needed: stop and ask Liam.

## Finish
Write `jobs/J7/report.md`. Cover:
- what was built
- counts: index rows, registry rows per role, unclassified and unreferenced; db decoded of 310; loc keys
- the sheets checked by eye
- the facts added (ids)
- evidence: commit and CI run ids
- deviations from this brief and why
- what moves to the core later
- open questions, listed for J10 (the atlas) and J9 separately

Then `wsc reg set jobs J7 status=review report=jobs/J7/report.md`.
