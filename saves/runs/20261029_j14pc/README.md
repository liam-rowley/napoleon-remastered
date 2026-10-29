# Run 20261029_j14pc: J14 load ladder (2026-10-29, 16:39-16:51 UTC)

PC sitting through the watcher (owner `j14`): proxy kit `kit_20261029T163945Z_af21f9aa063d` (DLL build `a7df189d1dc7`) installed
with `dev.ctl=1 dev.lua_bridge=1 dev.state_json=1 dev.skip_intro=1 dev.timeline=1`; uninstalled at the end, game folder identical
to the pre-install snapshot (1564 files). Saves made by the recipes from Liam's `j14_taxes-changed_a` (1805 Winter) in
`C:\napoleon_remastered_pc\_scratch\j14\`, staged as `zz_j14_a|b|c` by `stage_save.py` and moved to `_to_delete\saves_20261029T165049Z`.
Every step: `ladder.jsonl` (one line per ctl step, from `saves/napoleon/load_save.sh`).

| launch | save | result |
|---|---|---|
| A1, A2 | unchanged rewrite (sha-equal to the base) | front end 3.6-9.0 s, `campaign:zz_j14_a` load 5.0 / 3.6 s, 1805 Winter, player's turn |
| B1 | `tax_rates --lower 4 --upper 4` | load 3.4 s; QuickSave -> `quick_save.save`, kept as `zz_j14_b_qs_20261029T164118Z.save`: taxes `[4, 4, 25, 25]`; region and diplomacy ids all new |
| B2 | same | load 3.5 s |
| C1 | `agent_into_settlement --region eur_wales --agent <the rake>` | load 3.4 s; EndTurn through `button_end_turn`; `auto_save.save` written at 16:42:14 (1805 Winter, rake in Wales, both ends, new ids); then an AI diplomacy modal and a turn-start event (Liam dismissed both) and focus loss stalled the Lua pump from 16:44:54 (frame counter frozen while a modal was up); killed through the watcher at 16:49:44 |
| C2 | same | load 2.7 s; QuickSave kept as `zz_j14_c_qs_20261029T165033Z.save`: rake in Wales, Wales lists it |

No crash, no hang dump. The game wrote `quick_save.save` and `auto_save.save` into `save_games\`; they were left there (not ours to move).
