# Save editing tools (J14)

What a Napoleon save holds, field positions and recipes: `SAVE_FORMAT.md`. Every tool runs in Git Bash on the PC from the repo
checkout with `python3 -I`; saves never enter the repo (the manifest `napoleon/saves.json` names them by sha256).

| folder | what | warscape-core candidate |
|---|---|---|
| `core/` | `esf_dump.py` (offset reader: `tree`, `dump --path`, `lines`), `esf_edit.py` (byte-exact writer: `info`, `roundtrip`, `tree`, `dump`, `set`, `copy-item`, `remove-item`), `esf_diff.py` (node diff by record path), `esf_map.py` (generic map walker, `id` grep) | yes: game-agnostic ESF (ported from empire-remastered `rml_mod/tools/db/`) |
| `napoleon/` | `save_map.py` (factions, characters, forces, settlements, taxes, near), `noise.txt` (diff skip list), `recipes/` (`tax_rates.py`, `agent_into_settlement.py`, helpers in `_common.py`), `stage_save.py`, `load_save.sh`, `saves.json` | no: Napoleon paths and PC folders |

## Where saves live
- Liam's saves stay in `save_games\` untouched; `stage_save.py keep <name>` copies one, sha-checked, to `C:\napoleon_remastered_pc\saves\`.
  Those copies are read only: a recipe writes its output elsewhere (`_scratch\<you>\`).
- The game reads saves only from `save_games\`. `stage_save.py stage <file> zz_<name>` is the only writer there and refuses names
  without `zz_`; `stage_save.py clear` moves every `zz_` file to `<state>\_to_delete\saves_<utc>\` (nothing is deleted).
- The game itself writes `quick_save.save` (QuickSave) and its autosaves into `save_games\`; `load_save.sh --quicksave` keeps a copy.

## The method
1. Gate a new save: `esf_edit.py roundtrip FILE...` must print `OK` (sha-equal, no unknown tag); a failure names the first differing
   offset with its tag and record path.
2. Map a state from two saves one action apart: `esf_diff.py A B --skip @saves/napoleon/noise.txt`. Look up a field with
   `esf_dump.py dump FILE --path NAME/NAME` (prints `@N`), chase both ends of a link with `esf_map.py FILE id ID`.
3. Edit with a recipe (`IN OUT`), check it with `esf_diff.py IN OUT` (only the intended lines), then prove it in game.
4. Load test: with the game lock held and the proxy installed with `dev.ctl`, `dev.lua_bridge`, `dev.state_json` and `dev.skip_intro`:
   `saves/napoleon/load_save.sh <owner> OUT zz_<name> [--end-turn] [--quicksave] --log saves/runs/<run>/ladder.jsonl`.
   A recipe is PC-proven only after this (ladder A unchanged rewrite, B scalar, C structural plus EndTurn).

Costs: one save per process, about 15x its size in RAM while `esf_edit` holds the tree (30 MB -> about 470 MB, 2.2 s);
`esf_dump`, `esf_diff` and `esf_map` read by offset and stay small. Host tests: `tests/test_saves.py`.
