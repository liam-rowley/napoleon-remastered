# J40 final build: console re-check (2026-11-01)

Core v0.5.0 (warscape-core #9: the three console fixes), DLL build `f3e33f228416` (logged by the running proxy and by `build_id.py`),
kit `kit_20261101T070023Z_d465747d7269`, watcher 1.2.0. One headless launch (1920x1080), owner `j40`, profile `dev-console`, `campaign:new:grand:britain`.

| step | raw | result |
|---|---|---|
| `console status` | `c_status.json` | slot `015570b0` holds the forwarder (`ours`), on |
| `console on` | `c_on.json` | ours, on |
| `console off` | `c_off.json` | **slot still ours (value unchanged), on false**: off no longer writes 0 (fix 1) |
| `console declare_war denmark` while off | `c_line_off.json` | refused "console is off" |
| `console on` | `c_on2.json` | ours, on |
| read-back, `declare_war denmark`, read-back | `rb0`, `c_war`, `rb1` | Denmark nil -> at war; path campaign, forwarded, 1 hit (record matched to its line, fix 2) |
| `_console` folder after the lines | (listing) | **empty** (fix 3) |
| `exit`, `profile restore`, uninstall | `exit.json` | clean exit, no dump, only the start-up crash-handler info lines in `proxy.log`; game folder identical to the pre-install snapshot (1564 files) |

Then the kit was installed again for the 20-pass acceptance run (`harness/runs/20261101_j40acc`).
