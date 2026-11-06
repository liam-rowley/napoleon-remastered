# Discovery

The Empire to Napoleon diff (J6). Results: `diff/README.md` (generated) and `diff/<area>.json`, one per area, written through
`core/discovery/diffout.py` (fixed schema, sorted, no timestamps, so a re-run diffs cleanly). The passes are warscape-core's since v0.15.0 (J64):
`core/discovery/*.py`, driven by the core verb `python3 core/wsc.py discovery ...` (`core/discovery/README.md`, `core/docs/CONSUMING.md` "Discovery").
This folder holds the results and the adapter, `napoleon/`: `games.json` (`target` and `reference` names, install paths, Empire's mod packs, pack load
orders; `wsc.toml` `[discovery] adapter`), `carry_over.json` (one verdict per Empire tool family), `gate.json` and the other inputs, and
`napoleon/effects.py`, the one pass the core does not have (below).

## Where things moved (J64)

| Old path | Now |
|---|---|
| `discovery/core/<module>.py` (31 modules) | `core/discovery/<module>.py` (the core's, pinned by `[core] version`) |
| `discovery/napoleon/effects.py` | `discovery/napoleon/effects.py` (this repo's: no core pass yet) |
| `core/warscape/verbs/discovery.py` (`wsc discovery`) | the core verb of the same name |
| `discovery/requirements.txt` | `core/discovery/requirements.txt` |
| `proxy/tools/exe_info.py` | `core/proxy/tools/exe_info.py` |
| `tests/test_discovery*.py`, `test_engine_api.py`, `test_exe_strings.py`, `test_x86re.py` | the core's `core/discovery/tests/` (logic); `tests/test_discovery_repo.py` (this repo's data) |

Tools-registry ids kept their `discovery.core.` prefix. Provenance strings the core's passes write into results (`generator: discovery/core/...`, the generated
READMEs) keep their old text so a re-run is byte for byte the same (core backlog B55).

## Re-run (on the PC, read only; the game folders are never written)

1. Extract the small files into the git-ignored `/extract/` (`core/proxy/tools/pack_list.py`; N and E are the two `data` folders):
   - Napoleon: `data.pack boot.pack --under ui --ext none --ext .luac`, `local_en.pack local_en_patch.pack --ext .cuf`,
     `data.pack boot.pack --under fx`, `data.pack --ext .lua`, each with `--extract extract/napoleon`.
   - Empire (`boot main patch patch2 patch3 patch4 patch5 patch_en local_en ui` .pack): `--ext .cuf`, `--under fx`,
     `--under ui --ext none --ext .luac`, each with `--extract extract/empire`.
2. Run `core/discovery/packs.py`, `layouts.py`, then `fonts.py` (it reads `layouts.json`), `lua_api.py`, `shaders.py`, `exe.py`,
   then `discovery/napoleon/effects.py` (J72: no extract needed, it reads both games' packs and exes in place through `packfs.PackFS`; it reads
   `diff/shaders.json` and `db/tables.json`, so run it after those; `--check` compares a rebuild with `diff/effects.json`). Empire's db
   tables decode with `napoleon/empire_db_schema_effects.json`, trimmed from empire-remastered's converted RPFM schema by `--trim-schema`.
3. `python3 core/wsc.py discovery render`, then `discovery check` (the tests gate fails a stale README).

**The effects pass is not in the core** (J72 landed after the core's copy, J64 open question 1): the core's `discovery render` does not know the `effects`
area, so `diff/README.md` has no effects rows; `diff/effects.json` and the facts `napoleon.diff.effects*` are untouched. A core row to promote the pass and the area
closes this.

Packs and the exe are read in place. Only the uied.templates file and the exes are read from the installs beyond pack indexes.

## Assets, db and loc (J7)

`core/discovery/packfs.py` is the read-only view of a game's packs plus loose `data\` files (pack order from `napoleon/games.json`, then
loose files); every J7 pass reads through it, by index offset, and writes nothing in the game folder. Results (generated READMEs
in each folder): `assets/` (`index.tsv.gz` of every copy, `refs.json`, `sheets.json`, `summary.json`; the UI-first rows are
`registries/assets.jsonl`, roles from `napoleon/asset_roles.json`), `db/tables.json` (schemas, keys and refs only) and
`loc/keys.tsv.gz` (keys only). Text, decoded db rows and contact sheets go under the git-ignored `/extract/napoleon/`.

Re-run on the PC: `python3 core/wsc.py discovery all` (assets, db, loc, sheets, ui, then render), or one pass:
`discovery assets|db|loc|sheets|ui`. The sheets need Pillow: `python3 -m pip install --user -r core/discovery/requirements.txt` (the pin is the core's); nothing
else needs a package, except the static x86 tools (`x86re`, `console_cmds`, `exe_strings build`) which need capstone and pefile in the RE environment
(`python3 core/discovery/re_env.py <dir outside the repo>`; `core/docs/CONSUMING.md`, "Discovery (optional extras)"). `discovery check` (tests gate) fails when a table
is not deterministic, the registry is out of step with the index, refs and rules, or a README is stale. The db schema is `napoleon/db_schema.json`, made by
`core/discovery/ron2json.py` from a pinned RPFM `schema_nap.ron` (run it with `python3 -I`: the download is untrusted data).
`discovery ui` needs the extract store and rewrites `ui/reach.json` and `ui/art_keys.json` from it; do not run it without the extract (it empties them).
