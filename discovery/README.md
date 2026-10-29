# Discovery

The Empire to Napoleon diff (J6). Results: `diff/README.md` (generated) and `diff/<area>.json`, one per area, written through
`core/diffout.py` (fixed schema, sorted, no timestamps, so a re-run diffs cleanly). `core/` holds game-agnostic readers (core
candidates, D10). `napoleon/` holds the inputs: `games.json` (install paths, Empire's mod packs, pack load orders) and
`carry_over.json` (one verdict per Empire tool family).

## Re-run (on the PC, read only; the game folders are never written)

1. Extract the small files into the git-ignored `/extract/` (`proxy/tools/pack_list.py`; N and E are the two `data` folders):
   - Napoleon: `data.pack boot.pack --under ui --ext none --ext .luac`, `local_en.pack local_en_patch.pack --ext .cuf`,
     `data.pack boot.pack --under fx`, `data.pack --ext .lua`, each with `--extract extract/napoleon`.
   - Empire (`boot main patch patch2 patch3 patch4 patch5 patch_en local_en ui` .pack): `--ext .cuf`, `--under fx`,
     `--under ui --ext none --ext .luac`, each with `--extract extract/empire`.
2. Run `core/packs.py`, `core/layouts.py`, then `core/fonts.py` (it reads `layouts.json`), `core/lua_api.py`, `core/shaders.py`, `core/exe.py`.
3. `python3 core/wsc.py discovery render`, then `discovery check` (the tests gate fails a stale README).

Packs and the exe are read in place. Only the uied.templates file and the exes are read from the installs beyond pack indexes.

## Assets, db and loc (J7)

`core/packfs.py` is the read-only view of a game's packs plus loose `data\` files (pack order from `napoleon/games.json`, then
loose files); every J7 pass reads through it, by index offset, and writes nothing in the game folder. Results (generated READMEs
in each folder): `assets/` (`index.tsv.gz` of every copy, `refs.json`, `sheets.json`, `summary.json`; the UI-first rows are
`registries/assets.jsonl`, roles from `napoleon/asset_roles.json`), `db/tables.json` (schemas, keys and refs only) and
`loc/keys.tsv.gz` (keys only). Text, decoded db rows and contact sheets go under the git-ignored `/extract/napoleon/`.

Re-run on the PC: `python3 core/wsc.py discovery all` (assets, db, loc, sheets, then render), or one pass:
`discovery assets|db|loc|sheets`. The sheets need Pillow: `python3 -m pip install --user -r discovery/requirements.txt`; nothing
else needs a package. `discovery check` (tests gate) fails when a table is not deterministic, the registry is out of step with
the index, refs and rules, or a README is stale. The db schema is `napoleon/db_schema.json`, made by `core/ron2json.py` from a
pinned RPFM `schema_nap.ron` (run it with `python3 -I`: the download is untrusted data).
