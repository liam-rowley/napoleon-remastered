# J7 review: Asset index, contact sheets, loc and db

2026-10-29. Independent review (Claude Code session 26c5a12d, Opus as D15 allows for independent checks) of `job/J7` at `a364a4a`,
against `jobs/J7/brief.md`, following `docs/REVIEW.md`.

**Verdict: merge.**

## What I ran
- `wsc gates` on the branch: 11 ok, 1 failed. The 5 errors were all `test_pc_deploy`, because a game was running on the PC (its
  `require_closed` calls the real `tasklist`). They are outside J7's diff. After my fixes, with the game closed: **12 ok, 0 failed**,
  110 host tests.
- **Determinism and counts, checked independently:** `wsc discovery all` from the install in a fresh worktree, with no hash cache,
  left `git status` clean. Every committed result reproduced byte for byte, and the printed counts match the report: 88,415 index
  rows, 12,295 registry rows (1 unclassified), 2,023/561 refs from 1,008 files, 306 of 310 db tables, 35,850 loc keys and 73 sheets.
- Sheets opened by eye, two that the builder did not name: `icon_01` and `event_picture_01`, plus the new `cursor_01`. The tiles
  decode, alpha shows on the checker and the labels are the id tails. `event_picture_01` shows real `#hash` ids
  (`war_declaration.tga#06ed32c`/`#c16ff11`), so the collision path is live in vanilla data.
- Content rule: sampled `assets.jsonl`, `index.tsv.gz`, `keys.tsv.gz`, `tables.json` and `loc/summary.json`. They hold only paths,
  sizes, hashes, keys, schemas and counts. No loc text and no row values are in them.

## Risk-first reading
I picked `discovery/core/packfs.py`, because every pass reads the game folder through it and a precedence mistake would poison
every result, and the write paths of `assets.py`, `sheets.py`, `loc.py`, `db.py` and `ron2json.py`, because of the read-only and
no-content rules. The adapter opens every file `'rb'`, reads by offset and applies a stable precedence over an explicit order,
and the loose override is a parameter. Every write goes to `/extract/` or to a committed `discovery/` file. The `.loc` and db
decoders enforce byte-exact. I skimmed the role rules, `imagehdr.py`, `tsvgz.py` and the verb.

## Findings

### Blocker
None.

### Should-fix (fixed on the branch, one commit each)
1. `discovery/core/assets.py:239`: on a re-run, hand-set `used_by`, `upscale_method` and `upscale_status` were carried over **by
   id**. An id changes to `<slug>#<sha1>` as soon as a new path collides on its slug, for example after a game update, and the
   hand-set fields were then dropped without warning. To see it fail: `Ids.test_hand_set_fields_survive_an_id_change` fails on the
   old code. Fixed by carrying them over by path, with that test added (`7441262`).
2. `discovery/core/sheets.py:29`: the brief asks for sheets for every UI role, but the 179 `cursor` rows (178 `.cur` and one `.ani`)
   had none, and the report did not name this as a deviation. Added `cur` and `ani` to the sheet formats and re-ran: 74 sheets,
   11,470 tiles. `ui/cursors/load.ani` is the one new failed tile, because Pillow has no `.ani` reader (`d641dfe`).
3. `registries/engine_facts.jsonl` `napoleon.db.decode` (and the report's Counts): "22 of them empty" is wrong. `tables.json` has
   **26** empty tables, and 25 of them have no schema definition: they count as decoded only because the 5-byte header is all the
   file holds, so they carry no fields, keys or refs. The fact is corrected (`a6d00c0`). The report is left as written.
4. `discovery/core/tsvgz.py:51`: added after the verdict, when the merge PR's CI `gates` failed. `problems()` re-deflated the rows
   and compared bytes, but the PC's CPython 3.15 uses zlib-ng and CI's 3.12 uses zlib, so the committed `.tsv.gz` files failed on
   CI only. The check now holds the gzip header (flags 0, mtime 0) and the inflated text, and a test covers a file written by
   another deflate (`cf607ed`, session 914dd587).

### Later (this repo)
- `discovery/core/db.py` `readme()`: the README's "Decoded byte-exact 306" should split out the 26 empty tables, and the 25 among
  them with no schema, so J10 does not expect fields for them.
- `discovery/core/db.py:79` `parse_header` reads the `mark` byte (the brief's u8 `1`) and never checks it. Byte-exact decoding
  covers this in practice. A check would give a clearer error on a non-db file.
- `napoleon.assets.pack_order` is `verified`, but its last clause ("the load order used is type then name") is the tool's choice,
  not an observed engine order. Its notes say this cannot matter in vanilla. Reword it to "assumed" when the fact is next touched.
- Evidence: the report gives no CI run id ("see the pull request checks"), and no pull request existed. The CI run on the merge
  pull request now stands as that evidence.
- `tests/test_pc_deploy.py`: five tests fail whenever any `Napoleon.exe` is running, because `require_closed` shells out to the real
  `tasklist`. This is not J7's code, but it makes `wsc gates` red during any game job. It needs a guard: an injectable process
  check in the tests.
- Empire repeat, as code: fetching a pinned raw GitHub file (the schema) took a refused guard bypass and then Liam's manual
  approval. A small sanctioned tool (`fetch_pinned.py <repo> <sha> <path>`: urllib into an empty folder, sha256 recorded,
  `-I`-only consumers) would let the next schema or data pin happen without that detour.

### Later (core)
None filed. `packfs.py`, `imagehdr.py`, `tsvgz.py`, the `.loc` codec, the db decoder and `ron2json.py` are core candidates (D10),
as the report says. Moving them is a warscape-core PR when a second game needs them.

## Brief compliance
Every deliverable (1 to 8) is present. The kill criteria were respected: `.loc` decoded on the first try, 4 of 310 db tables
(1.3 %) failed and none was reverse engineered past the cap, and the registry check at 12,295 rows takes 0.8 s. Nothing outside
scope. Deviations the report names: the schema file name and how it was fetched (MIT, pinned at `29024e92`), Opus instead of
Sonnet, `inherited_from` keys and refs, the per-role summary in `summary.json`, the sheet position rule in place of per-tile x/y,
and the bare-filename reference heuristic. All are reasonable. One deviation was missing from the report, the cursor sheets, and
it is fixed above.

This merge changes no rule that other open job branches must meet.
