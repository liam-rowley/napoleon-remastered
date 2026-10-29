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
