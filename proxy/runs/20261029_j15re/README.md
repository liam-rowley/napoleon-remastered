# J15 static RE: the console route on Napoleon.exe (2026-10-29)

Exe sha1 `9aebcd21...` (pinned). Tools: `discovery/core/re_env.py` (pinned capstone 5.0.6 + pefile), `x86re.py`, `console_cmds.py`. VAs at
ImageBase 0x400000 (RVA = VA - 0x400000). Every address the proxy uses is an `engine_sites` row (verified on the PC, run `20261029_j15pc`).

| VA | what |
|---|---|
| 0x106c370 | `console_exec_string(ca_string*)`: stream over the line, then the executor 0x1055970 (callers: Lua `CliExecute` 0x105810c, `quit`, ...) |
| 0x1055970 | executor, per statement: system dict `*0x1767094` -> tweaks 0x106c980 -> `fopen(<name>)` relative to the working folder, recurse -> slot `*0x17670b0` `vfunc0(&name, &stream)` bool; `help` also calls `vfunc1()` |
| 0x17670b0 | external-handler slot (.bss): 4 reads, **0 writes** |
| 0x901260 / 0x104c2f0 | campaign / system command register (`name, handler, category, usage, help`); 199 campaign, 68 system |
| 0x9011f0 | CampaignCLI ctor `thiscall(void** ctx)` ret 4, 0x2c bytes, vtable 0x1361bc4, `this+0x28 = *ctx` |
| 0x925200 | `CampaignCLI::Execute` (vtable slot 7) `bool thiscall(name, stream)` ret 8: dict lookup, `handler(stream, &this->ctx)` |
| 0x8b7fe0 | builds Campaign CLI / Debug / camera CLIs and adds them to a manager (vtable 0x136a540 slot 55): never the slot |
| 0x15c4938 | campaign owner global (one writer, 0xa22460, from the owner's base ctor); `owner+0x9fc` = campaign context; `campaign+0x28 = owner+0xf4` (selection) |
| 0x8809f0 | teleport position: each float as 12.20 fixed point (x 2^20, sign-magnitude), no scaling |
| campaign+0x54 | byte tested first by 113 of 168 acting handlers (set in a live campaign) |

Tables: `campaign_commands.tsv` (status acts / no_op / parse_only / prints_only, static only), `system_commands.tsv`,
`campaign_vs_empire.tsv` (27 new, 0 gone, 10 status changes against Empire's 172).

## J40: `transport_to_region` traced (2026-10-31, run `proxy/runs/20261031_j40pc`)

| VA | what |
|---|---|
| 0xaafa30 | handler: key token (0x10f5d10); needs `campaign+0x54`, `campaign+8`, selection `campaign+0x28` and its `vfunc1` (the character); `region = 0xaa11e0(&key)` on `mgr = [campaign+8]+0xf7c`; if found, `0xa83f90(char, region)` |
| 0xaa11e0 | region lookup: walks `[[mgr+0x620]+0x134 .. +0x138]`, compares the key (UTF-16 compare 0x4f1f30) with the string at `[e+0x190]` (the region record, resolved from the key at `e+0x194` by 0xa6c840); null when nothing matches |
| 0xa83f90 | builds the order: `[mgr+0x630]` map (0xa86f80) by `char+0xcc` (filled for every map character at 0xa8e979), target spot = settlement (`region+0x12c` set) or region centre, a 0x148-byte order (ctor 0xbe3500, vtable 0x1383ef8: +0x10c entity, +0x110 region, +0x118 target), text "Transport character '..' to region '..' (hlci ..)", then the sink 0xa61af0 -> 0xcb2980 (registers the order as a live model object) |
| 0x1383ef8 slot 9 / 12 | 0xc5f850 done-check (entity region and spot equal the target); 0xc2fc20 execute: route 0xd7c390 and cost 0xa7c3a0 (budget FLT_MAX); failure ends the order silently (0xd095c0) |
| 0xaaf9c0 | `transport_to_hlci [hlci]`: the same order with a cell index (ctor 0xbe3610); its orders run at end of turn: cells 0, 1, 100, 1000 crashed the next EndTurn at Napoleon.exe+0x9611c9 (0xd61190, called from the character position code 0xc35b2d..0xc3afa0) |

No move in 10 tries (spy and general, neighbouring regions, across an EndTurn). Open: lookup null or route refused; a runtime read of
0xaa11e0's return decides it. `teleport_to` stays the placement route.
