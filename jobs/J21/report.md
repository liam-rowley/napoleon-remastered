# J21 report: Hotkeys registry and clash gate

2026-10-29, Sonnet, session da502b9f, about 55 tool calls. No game launch (host only), so there is no watcher run id; the evidence is the commands below.

## What exists
- `tools/verbs/hotkeys.py`: `wsc hotkeys import (--from-pack [DATA_DIR] | <keys.xml>)` and `wsc hotkeys check`, with a header and the `wsc.hotkeys` tools row.
  Import writes through `warscape.registry` (rows replaced by id, sorted, view rendered by `wsc reg render`), never by hand. Rerunning gives the
  same bytes (md5 of `registries/hotkeys.jsonl` unchanged on a second run).
- `registries/hotkeys.jsonl`: 128 `vanilla.fps.<func>.<n>` rows (108 funcs). 99 descriptions come from the localisation
  (`shortcut_localisation_onscreen_<func>`); the other 29 fall back to the func name. `registries/hotkeys.md` is regenerated.
- `tests/test_hotkeys.py` (21 tests, run by the `tests` gate): one failing fixture per rule (each message names both rows), a clean one, the
  parser on a fixture in both file layouts, and the real-registry check.
- `engine_facts`: `napoleon.hotkeys.key_file_format`, `.liam_vs_default`, `.modifiers`.
- Reseed after a game update: `python3 core/wsc.py hotkeys import --from-pack`, review `git diff registries/hotkeys.jsonl`, then `hotkeys check`.
  A key the grammar cannot spell, or an OS combo, stops the import with the func named and writes nothing.

## Defaults versus Liam's file
The defaults are in `data.pack` at `text\default_keys.xml` (found in the J7 asset index in 3 calls, read with PackFS). It holds keysets `fps`
and `total_war` (same funcs) and puts the modes in a `<mappings>` block. **Liam's `custom_keys.keys.xml` has no difference**: the same 108 funcs
and the same modifier and key for every func (0 differences). Only the layout differs (mapping inline, modifier explicit). The registry is
seeded from the pack, `source_ref` = `data.pack:text\default_keys.xml#fps/<func>`. The parser reads both layouts.

## Rules (repo test over the whole registry)
1. Same binding in a clashing context: equal, either side `global`/`all_modes`, or a `_`-prefix family (`battle` vs `battle_naval`).
2. Bare key: `ANY` takes every modifier on that key; `ALLOW_SHIFT` takes the key plus `Shift+` (not Ctrl, see Deviations). The marker lives in
   `source_ref` (`... modifier=ANY`), because the schema has no field for it.
3. OS combos fail, mod or vanilla: Alt+F4, Alt+Tab, Alt+Esc/Escape, Win+anything, Ctrl+Alt+Delete, Ctrl+Shift+Escape (and raw `LWIN` keys at import).
   `KNOWN_OS_COMBO` is empty (no vanilla row is one); it and `KNOWN_VANILLA_CLASH` fail when stale.
4. The vanilla `ALT` rows, for J29's Alt-held drag: Alt+S, Alt+M, Alt+1 to Alt+9 (land formations) and Alt+1 to Alt+4 (naval). A test pins the list.

## Free keys for mod use
No clash with any vanilla row, not F4, not an OS combo; letters, digits and F1-F12 only, from `hotkeys.free_keys`. Alt+ keys are free of vanilla,
but J29 holds Alt during a drag, so avoid them for anything that can fire mid-gesture.

| Context | Bare | Ctrl+ | Shift+ | Ctrl+Shift+ |
|---|---|---|---|---|
| battle | I K M O U Y F1 F2 F3 F8 | D E F G I J K L N O P R S U V X Y Z F1 F2 F3 F5-F12 | B F G H I J K M O P R T U Y 4 5 6 F1 F2 F3 F5-F8 | all |
| campaign | B C F H K N O P R U V Y 0-9 F1 F2 F3 F5-F8 | B C D E F G H I J K N O R U V W X Y Z 0-9 F1 F2 F3 F5-F12 | B C F G H I J K L M N O P R T U V Y 0-9 F1 F2 F3 F5-F8 | all |

`battle` means free of both `battle_land` and `battle_naval`. A `global` binding must be free in both rows. Re-derive with `hotkeys.free_keys`
after any change to the registry; do not copy this table.

## Evidence
- `python3 core/wsc.py hotkeys check` -> `hotkeys: 128 rows, no clash`. `python3 -m unittest tests.test_hotkeys` -> 21 tests OK.
- `wsc gates`: 11 of 12 ok. `tests` fails only in `test_pc_deploy` (5 errors, `pc_deploy: refusing: tasklist: Napoleon.exe is running`):
  Liam's game was running during my run; unrelated to this change. CI run id and commits: see the pull request.

## Deviations from the brief, and why
- Two extra context families. `battle_land` / `battle_naval`: land and naval formations both bind Alt+1 to Alt+4 in battle, which the schema's
  unique rule rejects. `all_modes` for `deselect_all`: it binds Return in mode `all` and `end_turn` binds Return in campaign, a vanilla double
  binding the schema rejects as `global` vs `campaign`. The test treats `all_modes` as a wildcard and lists the pair in `KNOWN_VANILLA_CLASH`.
  A func mapped in both battle and campaign (cam_up, rot_l, ...) is `global`, not two rows.
- `ALLOW_SHIFT` is not "any modifier": the table puts ALLOW_SHIFT S/A/Q/W/C next to Ctrl+S/A/Q/W/C in the same modes, so Ctrl does not reach
  it. Encoded as key plus Shift (not proved in game).
- Mouse bindings were not looked up (not in either file; I did not read the localisation or Lua for them within the budget). None guessed.
- The run id on the engine facts is the session id; no game run was made.

## Open questions
- Mouse bindings (LeftDrag, RightDrag, wheel) are unproven on Napoleon and the registry has none. Needs a localisation/Lua read or an in-game probe.
- `ANY` (Escape, Delete, Insert, Space) is Empire's finding, read as every modifier; `ALLOW_SHIFT` as key plus Shift. Both want an in-game check.
- Which of `deselect_all` (mode all) and `end_turn` (campaign) wins on Return is unknown.
- Core B3: the schema cannot say `Alt+Esc` or `Win+*`, has no `modifier` field, and has no parent/child context (`battle` vs `battle_naval`).
  B1: no game gates, so this test is the gate until the core grows them.
