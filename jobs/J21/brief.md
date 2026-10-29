# J21: Hotkeys registry and clash gate

Phase 1 tooling. Seed the `hotkeys` registry with every binding in Napoleon's vanilla key file, then add a repo test, run by the
`tests` gate, that fails on a clash or an OS combo. Needed before any mod hotkey (J15 console, J29 gestures, UI).

Model: Sonnet (Python parsing and host tests, no engine work, D15). Budget about 80 tool calls; at the cap, stop, commit, report what
is left. No subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J21`). Read `docs/DECISIONS.md` (D15, D21) and `docs/plans/PLAN.md` (phase 4 hazard).
- Read `core/schemas/hotkeys.schema.json` first. It is the contract and **you cannot change it** (`core/` is pinned). It already:
  - rejects `Alt+F4`, `Alt+Tab`, `Ctrl+Alt+Delete`, `Ctrl+Shift+Escape` as a binding
  - rejects a mod binding on F4 (Alt is held for the move gesture, so F4 becomes Alt+F4)
  - makes `(binding, context)` unique, with `global` clashing with every context (`x-unique`, `x-wildcard`)
  - fixes the binding form: modifiers in the order Ctrl+Alt+Shift, then one key
  - **cannot say** `Alt+Esc` or `Win+*`, and cannot see that Esc, Space, Delete or Insert fire with any modifier held (core backlog B3).
    Those two gaps are this job's repo test. It does not replace the schema's checks.
- Evidence: Empire's `docs/learnings/LEARNINGS_HARNESS.md` line on its key table (read-only; `--add-dir ../empire-remastered`).
  Empire facts are checked again on Napoleon before use.

## Target facts
Read from the PC 2026-10-29 in the planning chat; check them again yourself and record each in `engine_facts` with date and run id.
- `%APPDATA%\The Creative Assembly\Napoleon\custom_keys.keys.xml` exists: `<custom_keys version="32">`, one keyset `fps`, 108 `<func>`
  elements, categories `universal`, `campaign`, `battle`.
- A `func` has `name`, `hidden`, and one or more `<key modifier="X">K</key>` plus `<mapping mode="battle|campaign|all"
  component="..."/>`. Modifier values seen: `NONE`, `CTRL`, `ALT`, `SHIFT`, `ANY`, `ALLOW_SHIFT`. `ANY` and `ALLOW_SHIFT` mean the
  key fires with more than the stated modifier (check what `ALLOW_SHIFT` does in the localisation strings and Lua before encoding it).
- **That file is Liam's copy, not the defaults.** The defaults are in `data.pack` (or a `.pack` the game reads at start-up): find
  them with the J7 pack tools. If the defaults differ from Liam's file, the registry takes the **defaults**, and the report lists the
  differences. If the defaults cannot be found in 15 calls, seed from Liam's file, say so on every row's `source_ref` and in the report.
- Mouse bindings are not in the file (Empire: same). Record the ones you can prove (LeftDrag, RightDrag, wheel) from the localisation or
  the Lua; mark the rest as an open question rather than guessing.

## Decisions already made for this job
- **Importer:** one tool, `tools/verbs/hotkeys.py` as a `wsc` verb (`hotkeys import <file>`, `hotkeys check`), with a header and a
  `tools` row. It is idempotent: rerunning on the same file gives the same rows and the same order. It writes through the registry
  (`wsc reg add|set`), never by editing `registries/hotkeys.md`.
- **Row shape:** `id` = `vanilla.<keyset>.<func>.<n>` (n for the second key of a func), `binding` in the schema's canonical form,
  `action` = the func name, `description` = the loc string when found, else the func name, `context` = `battle`, `campaign` or `global`
  from the mapping mode (`all` is `global`), `source` = `vanilla`, `source_ref` = the file or pack it came from.
- **One func with several keys is several rows.** `usegroup0` has `Ctrl+0` and `0`, so two rows.
- **Clash rule (the repo test, over the whole registry):**
  1. Same canonical binding in the same context, or either side `global`: a clash (also what the gate already says; test it so the
     two cannot drift).
  2. **Bare-key rule:** a row whose modifier is `ANY` fires with every modifier. A mod binding on the same key in a clashing context,
     with any modifiers, is a clash. Esc, Space, Delete and Insert are `ANY` in Empire: take them from the file here, not a hardcoded list.
  3. **OS combos** always fail, mod or vanilla: `Alt+F4`, `Alt+Tab`, `Alt+Esc`, `Win+<anything>` (the grammar cannot spell `Win+`, so
     test the raw key string the importer sees and a `win` modifier in a mod row's `binding` text), `Ctrl+Alt+Delete`,
     `Ctrl+Shift+Escape`. Also `Alt+<any key>` held by the gesture: list the vanilla `ALT` rows, because J29 holds Alt during a drag.
  4. A vanilla row that hits an OS combo is not deleted. It is recorded with a `known_os_combo` list in the test (id, reason), and the
     test fails when that list is stale (an entry that no longer exists or no longer clashes).
- **Failing fixtures first.** Write the tests as small registries in a temp folder: one for each rule above, each must fail with a
  message naming both rows, and a clean one must pass. The real registry is then checked by one more test.
- **Where it runs:** `tests/test_hotkeys.py`, so the `tests` gate runs it. No change to `core/` and no new gate (core backlog B1).
- **Docs:** `registries/hotkeys.md` is regenerated, never edited. The importer's header says how to rerun it after a game update. One
  line in `docs/plans/PLAN.md` phase 4 is not needed: the schema description already points at the gate.

## Deliverables
1. `tools/verbs/hotkeys.py` (`import`, `check`) with header and tools row.
2. `registries/hotkeys.jsonl` seeded (about 108 funcs, so well over 108 rows) and the regenerated view.
3. `tests/test_hotkeys.py`: the fixtures above, the XML parser on a small fixture file (every modifier value, `mapping mode`, a func with
   two keys, a key the grammar cannot spell), and the real-registry check.
4. `engine_facts` rows for the file format and the default-vs-Liam difference, each with date and run id.
5. `python3 core/wsc.py gates` green, including `tests`.
6. A short list in the report of the free keys for mod use per context (a table the next jobs can read): no clash with any vanilla row,
   not F4, not an OS combo.

## Kill criteria
- The vanilla defaults need an unpack tool that does not exist yet and 15 calls do not find them: seed from Liam's file, record that,
  and go on. Do not build a pack reader.
- A clash rule needs a schema change in `core/`: do not change it. Put the rule in the test, file the schema gap as a note under the
  open questions, and stop adding rules.
- The key file's meaning of `ANY` or `ALLOW_SHIFT` cannot be proved in about 10 calls: encode both as "fires with any modifier" (the
  safe side: more clashes, not fewer), say so, and go on.
- Anything would need a change in `core/` or in `empire-remastered`: stop and ask Liam.

## Finish
Write `jobs/J21/report.md`. Cover:
- what was built and how to reseed after a game update
- the defaults-versus-Liam's-file result, and where the defaults came from
- evidence: commits, CI run ids, the test output
- the table of free keys per context
- deviations from this brief and why
- open questions (mouse bindings not proven, `ALLOW_SHIFT` meaning, B1 and B3 for the core)

Then `wsc reg set jobs J21 status=review report=jobs/J21/report.md`.
