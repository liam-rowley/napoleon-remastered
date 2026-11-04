# J95: Discovery tools and facts: small fixes

Phase 1 sweep job: seven small, independent fixes to the discovery tools (`exe.py`, `lua_api.py`, `db.py`, `ui_atlas.py`, `briefpaths.py`,
`shader_catalog.py`) and two engine facts, all from the later-triage audit (`docs/audits/LATER_TRIAGE_2026-11-04.md`, J82; bullets J6 review Later 1 and 3,
J7 review Later 1, 2 and 3, J10 review Later 3, J11 review Later 1, J13 review Later 6, J24 review Later 5, J65 review Later 2). Python, registries and tests only:
no `proxy/` or `harness/` input changes, so rule 79 does not apply and no PC is needed.

Model: Opus, reason: D52 (builds run on Opus); the work itself is routine. Budget about 120 tool calls; at the cap, stop, commit, push, report what is left.
At most 1 subagent, none needed. Nothing here polls CI or a merge.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J95`, "Never change files inside `core/`"). Read `docs/DECISIONS.md` (D44 the pipeline lives in the core, D52) and
  `docs/audits/LATER_TRIAGE_2026-11-04.md` rows J6-L1, J6-L3, J7-L1 to L3, J10-L3, J11-L1, J13-L6, J24-L5, J65-L2.
- **This job starts after J64 has merged** (`depends_on: J64`). Reason, checked 2026-11-04 on main 0271d10: J64 deletes the whole `discovery/core/` folder (30 of its
  31 shared files differ from the core's copy) and moves Napoleon to the core's discovery code. A fix to `discovery/core/*.py` made before J64 would be deleted by it
  (delete/modify conflict) or kept on one side only, which J64 forbids. After J64 these tools are the core's files under `core/discovery/`, which a game job never edits.
  So the code items are **core changes**: made in a separate `warscape-core` clone beside this repo (CLAUDE.md, "The core"), one pull request there, tests in that repo's
  `discovery/tests/`. The two engine facts and the pin bump are the Napoleon half.
- **Re-check each item before touching it.** `git pull`, then run the grep in each item's "Applies" line against warscape-core `main` (the newest the fix can land on). If it
  has been fixed since (v0.30.0 was current when this was written), drop the item and say so in the report; do not re-fix.
- Look things up with `python3 core/wsc.py find <words>`.

## What exists (checked 2026-11-04: Napoleon `discovery/core/` on main 0271d10, warscape-core `discovery/` on main ea98a96, VERSION 0.30.0)
Every item below was present in both copies on that date, so none is dropped by this brief and none is already fixed. The audit already dropped the other bullets of the
same reviews (see its table). J10 Later 3 and J65 Later 2 live in `ui_atlas.py`, whose core copy matches the shapes quoted.

## Deliverables

### Part A: the core pull request (warscape-core `discovery/`, one PR, one test per item)
1. **`exe.py` `mask_for`** (J6 Later 1). Applies: `grep -n "def mask_for" discovery/exe.py` (line 48 in Napoleon's copy, 50 in the core's).
   Two faults: the second loop masks any 4 bytes whose value falls in the image, also across the instruction boundaries the first loop walked, so an address-like dword
   that straddles an operand boundary is over-masked; and a rel32 cut by the window edge (`i + 5 > len(window)`) is left unmasked, so its partial bytes must match.
   Fix: mask the rel32 bytes that are present when the window ends inside an operand, and mask address-like dwords only at positions that start inside no operand the first
   loop consumed. Then `search` treats a pattern with fewer than `MIN_FIXED_BYTES` fixed (True) bytes as **not found** (no hits); a named constant, default 6, with a comment
   saying why. Test: a window with a cut rel32, a window with an address-like dword across an operand boundary, and a pattern below the floor returns `[]`.
2. **Unclosed files** (J6 Later 3). Applies: `grep -n "open(" discovery/lua_api.py discovery/tests/test_discovery_lua.py` (Napoleon `lua_api.py:36, 112, 168`,
   `tests/test_discovery_lua.py:108`; the core's lines are one off). Use `with open(...) as fh:` or `Path.read_bytes` and `read_text` at each. No new test: run the
   discovery tests with `python3 -W error::ResourceWarning` for those modules and say so in the report.
3. **`db.py`** (J7 Later 1 and 2). Applies: `grep -n "def parse_header\|def readme\|'empty'" discovery/db.py` (Napoleon `db.py:79, 224`).
   (a) `parse_header` returns the mark byte and nothing checks it: raise `ValueError` (the type `decode_table` already turns into `status: failed`) when it is not 1, per the
   header layout in the module docstring. (b) The README renders one count table and a "Not decoded" list: add an **empty tables** column to the totals table (tables whose
   declared rows are 0, split by with and without a schema; the audit says 26 and 25, recount from `tables.json` and print what you find) and list the empty tables in their own
   short section instead of in "Not decoded". Tests: a header with mark byte 0 fails with the message; the README of a synthetic `tables.json` with one empty table with a schema and
   one without has the column and the section.
4. **`discovery check`: `used_by`** (J10 Later 3). Applies: `grep -n "used_by" discovery/ui_atlas.py discovery/gate.py` (Napoleon `ui_atlas.py:1278`, `write_used_by`; no check reads it).
   Add to `problems()` (what `wsc discovery check` calls) a check that every assets row with `used_by` lists only ids that exist in the `ui_elements` rows, and a row that
   `write_used_by` would now set differently is reported. It works on the committed files only, like `problems` today. Test: a synthetic registry pair with a dangling id fails, a matching pair passes.
5. **`briefpaths.py` Registry gaps** (J11 Later 1). Applies: `grep -n "in_gaps" discovery/briefpaths.py` (Napoleon `briefpaths.py:192-200`; the core's 194-198):
   `found_path_problems` skips every line under `## Registry gaps`. Fix: skip only the bullets and, inside a bullet, only its own `path:` field (the one `registry_gaps` parses);
   every other line and every other field of a bullet (the `reason:` text) goes through `token_problem` like the rest of the brief. Test: a brief with a clean bullet and a prose
   line naming a game-folder path under the heading reports exactly that line; a `reason:` field naming such a path is reported.
6. **`shader_catalog.py`** (J24 Later 5). Applies: `grep -n "def cmd_import\|density" discovery/shader_catalog.py` (Napoleon 369-396 and 731-737).
   (a) `import` with a named capture whose `frame.txt` is missing fails the whole import: skip it, collect the names, print one line listing the missing captures and how many were
   imported, exit 0 if at least one imported and non-zero if none did. (b) `density` takes capture paths as `nargs='+'`, which breaks past about 40 paths on a Windows command
   line: add `--from-file FILE` (one path per line, `-` for stdin) and keep the positional form. The third part of the audit's bullet (never edit a running `.sh`) is the watcher's,
   core line K19, not this job. Tests: a synthetic capture folder with one missing `frame.txt` (import skips, lists, exits 0); `--from-file` with 100 paths yields 100 results.
7. **`discovery ui` fails loudly** (J65 Later 2). Applies: `grep -n "extract\|reach.json\|art_keys" discovery/ui_atlas.py` (Napoleon 868 and 1300-1320): it writes empty `reach.json`
   and `art_keys.json` without an error when `extract/<target>` is missing. Fix: before the `art` and `live` steps, if the extract folder the step reads is absent or empty, exit
   non-zero with a message naming the folder and the command that builds it (use the verb the core README names) and write nothing. Test: the step against a temp tree
   without the extract exits non-zero, names the folder, creates neither file.

Part A ends with that repo's gates green and the PR queued as its rules require; a tag is cut by Liam (C27, W29). Do not wait for the tag.

### Part B: Napoleon (this repo, branch `job/J95`)
8. **Fact `napoleon.assets.pack_order`** (J7 Later 3), `registries/engine_facts/napoleon.assets.pack_order.json`: keep `verified` for what the pack headers show (no dependency list
   in all 11; the header types) and reword the last clause, "the load order used is type then name", as **assumed** (the game's own order is not read from the exe), with
   `python3 core/wsc.py reg set engine_facts napoleon.assets.pack_order claim=...`; say it in `notes` too; keep evidence, date and run.
9. **Fact `napoleon.exe.window_imports`** (J13 Later 6), `registries/engine_facts/napoleon.exe.window_imports.json`: `evidence` points at `jobs/J13/report.md`, which has no list.
   Point it at the committed output `discovery/diff/exe.json` (key `detail.napoleon_pe.imports`, user32.dll: 57 on 2026-11-04) and put the command in `notes`
   (`exe_info.py Napoleon.exe --imports user32.dll gdi32.dll dwmapi.dll shcore.dll`; find its path with `python3 core/wsc.py find exe_info`). The claim says 19 named
   calls "and 37 more" (56) against 57 in `exe.json`: recount from the committed output and correct the number.
10. **Pin bump**, only if a core tag carrying Part A exists when you finish: one commit moving the gitlink and `wsc.toml` `[core] version`, then `wsc discovery render`,
    `wsc discovery check` and the gates; commit regenerated outputs only where the render changes them (the db README gains the empty-table section). If there is no tag,
    say so: the bump is the next step and the report names the core PR number.

## Proof and what done looks like
- Core PR with one test per item 1 to 7 and its gates green; PR number (and the tag, if cut) in the report.
- Items 8 and 9 in the registry; `python3 core/wsc.py reg check`, `jobs check` and `gates` green on the branch.
- If the bump was done: the `discovery check` lines and the db README diff pasted in the report.
- The report lists per item "fixed (test name)", "already fixed (where)" or "dropped (why)".

## Out of scope
- Any file inside `core/` in this repo except the gitlink; `discovery/core/` (J64 deletes it); `empire-remastered`.
- The watcher half of J24 Later 5 (core line K19) and every other item of the later triage.
- New discovery features, the effects pass, anything in `proxy/` or `harness/`.

## Kill criteria
- J64 has not merged when you start: stop, change nothing, report.
- More than half of items 1 to 7 are already fixed in the core: do those that remain, then report; do not widen the scope.
- The core's gates fail twice in a row on a test you did not touch, after a rebase on its `main`: stop and report the failing id.
- A fix needs a change beyond `discovery/` in the core (shared helpers in `warscape/`): stop and file it as a core backlog line instead.
- The budget is reached: stop, commit, push, report what is left.

## Open questions (for Liam; each has a recommendation this brief follows)
1. **Core PR inside a game job.** The code items cannot be made here once J64 lands. Recommended (followed): one warscape-core PR from the builder, then a pin bump if a tag
   exists. Alternative: file them as core BACKLOG lines and shrink J95 to items 8 and 9.
2. **`MIN_FIXED_BYTES`.** Recommended 6; check it against the shortest anchor the engine-sites registry holds and change it only with a reason in the report.

## Finish
Write `jobs/J95/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): per item the outcome and test, the core PR number and tag,
the commands run (gates, `jobs check`, `reg check`), anything dropped and why. Then `wsc reg set jobs J95 status=review report=jobs/J95/report.md`.
