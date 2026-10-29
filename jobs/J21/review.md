# J21 review: hotkeys registry and clash gate

2026-10-29. Independent review of `job/J21` at `b7707bc`, by a fresh session that did not build it (`docs/REVIEW.md`).

**Verdict: merge.**

Every deliverable is present. The registry is seeded from the pack defaults (`data.pack` `text\default_keys.xml`), with 128 rows for 108
funcs. The importer is idempotent, the clash rules each have a failing fixture that names both rows, the real registry is checked in the
`tests` gate, and the free-key table is derived by code. I fixed two gaps in the clash check (below). The deviations from the brief are
named and justified: the `battle_land`, `battle_naval` and `all_modes` contexts, the `ALLOW_SHIFT` reading, and mouse bindings left open.

## Machines

- `wsc gates`: 11 ok, 1 warn (`hooks`: this clone's absolute `core.hooksPath`, a local setup issue). That held before and after this review's
  commits; 167 host tests pass after them. PR #48 CI (`gates`) was green on `b7707bc`.
- The report's `test_pc_deploy` failure (the game was running) does not reproduce: `tests` passes.

## Claims against evidence (re-run, not read)

- **Idempotent:** `wsc hotkeys import --from-pack` on the branch rewrote `registries/hotkeys.jsonl` and `.md` byte for byte (empty `git status`).
- **Defaults vs Liam's file:** parsing `%APPDATA%\...\custom_keys.keys.xml` with `parse_keys` gives the same 128 ids, and the same binding,
  context and wildcard marker for every row as the registry (0 differences). Fact `napoleon.hotkeys.liam_vs_default` holds.
- **`ALLOW_SHIFT` is key plus Shift, not Ctrl:** every `ALLOW_SHIFT` key that shares a context with a vanilla `Ctrl+` row on the same key
  (S, A, W, Q, C: `quick_save`, `select_all`, `battle_both_withdraw`, `voice_chat`, `select_all_cavalry`) would be a vanilla double binding
  under the "any modifier" reading. The reading is sound from the table, but it is not tested in game (see should-fix 2).
- **Free keys:** `free_keys` re-derived for campaign, bare keys, and matched the report's table.

## Risk-first reading

`tools/verbs/hotkeys.py` `find_problems` / `os_combo` / `reaches`, because that is the gate every later mod hotkey (J29, UI, console)
relies on. A false "no clash" costs most. The XML parsing and the verb plumbing were skimmed.

## Findings

**blocker:** none.

**should-fix (fixed on the branch by this review, one commit each):**
1. `tools/verbs/hotkeys.py:183`, `:140`: the same-binding rule compared raw text, so two rows spelled `Esc` and `Escape` (or `alt+k` and
   `Alt+K`) in one context passed as no clash. Also, `os_combo` caught `Win+X` but not a bare `LWin`, `RWin` or `Apps` key. Fixed in `929d059`:
   bindings are compared in canonical form (`split`), and the key is tested against `WIN_RAW`. Two tests were added
   (`test_same_binding_spelled_two_ways_clashes`, plus `LWin`/`RWin`/`Apps` in `test_os_combos_always_fail`). Both failed before the fix and
   pass after it. The vanilla registry is still clean.
2. `registries/engine_facts.jsonl` `napoleon.hotkeys.modifiers` was `verified`, while its own claim says `ANY` is "not tested on Napoleon"
   and its notes say it "needs a PC run". Set to `open` in `ced1e5c`.
3. PR #48 conflicted with `main` (the generated `registries/engine_facts.md`). Merged `origin/main` into the branch in `0466ee5` and
   regenerated the views; gates pass.

**later:**
4. Mouse bindings (LeftDrag, RightDrag, wheel) and the in-game meaning of `ANY` and `ALLOW_SHIFT` are open. One PC probe could settle all
   three. This matters before J29 (Alt-drag gestures) relies on the registry; that job's brief should include the probe.
5. `tools/verbs/hotkeys.py:35`: the Napoleon `data` path is hard-coded in a `wsc` verb. It should come from the adapter
   (`discovery/napoleon/games.json`) before the verb moves to the core.
6. `tools/verbs/hotkeys.py:247`: `hotkeys check` imports `KNOWN_OS_COMBO` and `KNOWN_VANILLA_CLASH` from `tests/test_hotkeys.py`, so a tool
   depends on a test module. Move the two lists into a small data file that both read.
7. `split` uses `str.capitalize`, which turns `NumpadAdd` into `Numpadadd` in clash messages. Comparisons are unaffected (both sides get the
   same treatment), but the messages misspell the key.
8. Core (B3, already filed): the schema cannot spell `Alt+Esc`, `Win+*`, a modifier field, or parent/child contexts, so this test carries
   those rules until the schema does.

## Rule changes for other branches

None. Any open branch that adds a mod hotkey row now meets the canonical-binding comparison, which is stricter than before.
