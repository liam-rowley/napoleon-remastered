# J15 PC sitting: campaign console (2026-10-29)

Headless watcher launches (2560x1440 virtual display), every launch `dev.skip_intro=1`, `campaign:new:grand:britain` unless noted.
Kits `e44b447d4828` (probe only), `01d8682becbe` (a), `fd479b755538` (c), `1824949ac6ee` (gate build, d_gate). Raw ctl results and shots in `raw/`.

| step | run | result |
|---|---|---|
| no-DLL probe | `raw/d1_nodll` | `CliExecute` exists; `here_kitty_kitty` handled by the system dictionary; `teleport_to 0 0` and an unknown name reach the file stage (`files_console.tsv`): no campaign dictionary |
| a) key off | `raw/a_keyoff` | 7 sites stock at delta 0x620000, nothing installed; `console status` / `console teleport_to` refused `dev.console=0` |
| 6a P1 | `raw/c_console/status0.json` | chain ok (campaign context found), slot ours; own CampaignCLI built at first forward (`proxy.log`) |
| 6b verbs | `raw/c_console` | `here_kitty_kitty` path system; `j15_no_such_cmd` path unknown; `give_trait` refused no-op; `off` slot -> 0, line refused; `on` slot claimed again |
| 6c teleport | `raw/c_console/tp1-3, sel1-3` | `PosX/PosY` = target 3/3; camera does not follow (fact `napoleon.console.teleport_units`) |
| 6d transport | `raw/c_console/tr_*`, `raw/d_gate` | campaign hit, agent not moved (open fact) |
| 6e save/reload | `raw/e_save`, `raw/d_gate/e_reload_pos.json` | position kept after relaunch + `campaign:zz_j15_spy`; EndTurn reached the AI turn, stopped at a diplomacy modal |
| 6f | `raw/c_console/war.json, trait.json`, `f1/f2` shots | `declare_war spain`, `add_trait C_Agent_Spy_Network 1`: campaign hits, effect not read back |
| d) uninstall | this README | identical to the pre-install snapshot (1564 files); watcher restored every profile file (lock release) |

First try `raw/c_console_try1`: the base-vtable check refused a live campaign (fixed: the back-pointer is the identity) and names were read as
8-bit (they are UTF-16).
