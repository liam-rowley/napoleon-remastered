# J15: Campaign dev console

Phase 1, job 15. The goal is to give agents Napoleon's campaign console: run campaign commands (`teleport_to`, `transport_to_region`,
`create_army`, ...) from the control channel and from dev Lua, with checked results. Mid-session movement and spawning then need no
save edit (J14) and no clicking. Empire proved the route (empire-remastered `docs/plans/STATE_CONTROL.md` section 3). This job finds
it again on `Napoleon.exe`. The method ports; no Empire address, size or command list does. Static reverse engineering comes first,
then a small dev-only DLL feature, then proof in game.

Model: Opus, reason: static reverse engineering of the exe's console executor and command dictionary, plus engine-memory writes from
the proxy DLL (D15). Budget about 200 tool calls; at the cap, stop, commit, report what is left. At most 1 subagent, only for
independent read-only work (for example, extracting the command table while you trace the executor). Waiting belongs to the harness:
`job.sh` blocks inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J15`). Read:
  - `docs/DECISIONS.md` (D2, D15, D25-D28, D30)
  - `proxy/README.md`, all of it: pass-through contract, exe-identity guard, "Runtime patch engine" (site byte layout, `kHook`),
    "Hooks", "Dev control channel"
  - `harness/README.md`
  - `jobs/J1/report.md`, `jobs/J3/report.md` and `jobs/J6/report.md`
- Search the registries before writing anything: `python3 core/wsc.py find console hook site lua save`. Extend what exists; do not
  write a second of any of these:
  - `proxy/core/{dev,devcore.h,luabridge,hooks}.cpp`
  - `patch_engine.h` and `tools/gen_tables.py`
  - `pc_deploy.py`
  - `harness/core/job.sh ctl`
  - `discovery/core/exe.py` (the signature search)
- Evidence in `empire-remastered`. It is read-only: never edit, commit or push there. Read:
  - `rml_mod/src/dev_console.{h,cpp}`: the route, gate, forwarder and refusals
  - `rml_mod/tests/dev_console_test.cpp`
  - `rml_mod/docs/runs/20261028_esfcon/`: README, `campaign_commands.tsv`, `PC_PLAN.md`
  - `docs/plans/STATE_CONTROL.md` sections 3 and 4 ("Console: the route ports, the addresses do not")
  - `orchestrator/reports/2026-10-28_{esfcon,dllw2,dllw3}.md`
  - `perf_mod/re/` (`re.sh`, `ghidra_scripts/`): how Empire ran Ghidra headless; port only what you use

## Target facts
Recorded by J1, J3 and J6. Check each again before relying on it:
- **Exe and guard:** `Napoleon.exe` is pinned (`napoleon.exe.identity`); ASLR is on, so rebase every RVA. The guard and the patch
  engine already refuse a mismatched exe, so Empire's "pin the guard before any experiment" step is done.
- **Lua:** Lua 5.1, entered through the virtual dev pack (`napoleon.lua.loadlib_bridge`). `ctl lua <file>` returns the chunk's
  results.
- **Lua API:** `CliExecute`, `CampaignUI.QuickSave`, `QuickLoad`, `CameraTarget`, `SetCameraTarget` and `SelectAndZoomToCharacter`
  exist in Napoleon (`discovery/diff/lua_api.json`).
- **Campaign start:** `campaign:new:<campaign>:<faction>` loads in about 17 s.
- **Campaign quit:** quitting a campaign to the menu does not work yet (`napoleon.campaign.quit_to_menu`), so a relaunch is the
  campaign reset.
- **Saves:** there are none on the PC (`save_games` is empty). `campaign:<save>` and `campaign:continue` are written but have never
  run.
- **J6 signature hits in `Napoleon.exe`** (`discovery/diff/exe.json` `detail.signatures`). They are candidates, not sites:
  - unique: `ccmd_teleport_to` at RVA `0x56caf0`, `console_exec_string` at RVA `0xc6c370`
  - no hit: `CampaignCLI_ctor`, `CampaignCLI_Execute`, `console_exec_stream`, `luaB_CliExecute`

## Decisions already made for this job
- **No DLL first.** Before any new DLL code, run system-dictionary commands through `CliExecute` from a `ctl lua` file. Use
  `here_kitty_kitty` (Empire: cat portraits) or a harmless tweak. Also run one campaign command (`teleport_to`) the same way. Record
  each as a fact. If Napoleon reaches the campaign dictionary with no DLL, there is no slot to fill: say so and skip deliverable 4.
- **Static RE tooling is local (D30) and fetched, never vendored.**
  - Ghidra, or capstone and pefile from pip, come from a committed tool pinned by version and sha256. Java 21 is installed.
  - The Ghidra project and any exports live outside the repo, under `C:\napoleon_remastered_pc\_scratch\J15\`.
  - What the repo keeps: the tool, its registry row, and the derived tables and annotations as text. J9 (engine API surface and
    engine sites) extends this kit later, so keep it general (exe path and output folder as arguments).
- **Finding the live CampaignCLI object, in this order of preference:**
  1. Read it at run time through a pointer chain from a global the exe writes (the campaign's CLI registration, or the campaign
     context). No engine code is changed.
  2. Construct our own CLI with the exe's ctor and the live campaign context.
  3. Only if neither works: detour the ctor. This must be an `engine_sites` `kHook` row (function-entry anchor, as `proxy/README.md`
     describes) installed by a small in-house detour in `proxy/core`. No MinHook or other third-party code (D26). Write a decision
     row "agent (J15), for Liam's review" that amends D26 for engine-code hooks.
- **Every address is an `engine_sites` row** with anchor bytes and `exe=sha1:<pin>`, generated into `tables.h`, checked by the
  patch-engine plan before use. This covers the executor, the CLI ctor, `Execute` and its vtable slot, and the string helpers.
- **The handler slot is probably in `.bss`** (no file bytes). If so, anchor it through the executor instruction that reads it: take
  the address from that instruction's operand at run time. Do not use a bare RVA. If `engine_sites` cannot express this, use the
  `value_offset` gap (`proxy/README.md` open question 1): say so and propose the core change; do not edit `core/`.
- **Never take a slot the engine filled.** Write the slot only if it holds 0. If retail writes it (Ghidra shows a write, or the PC
  sees a non-zero value), stop and report; chaining to the engine's handler is a decision for Liam.
- **Dev only, behind the guard.** One key, `dev.console`: default 0, release value 0, with a `config_keys` row. With the key off:
  - nothing is read or written in engine memory;
  - `console` lines are refused with the reason;
  - the proxy behaves exactly as at J3, and the pass-through lint covers the new code.
- **Code split:** game-agnostic in `proxy/core/` (forwarder, gate, refusal rules, ctl verb, the pure parts testable on the host).
  Napoleon specifics in `proxy/napoleon/` (sites, command table). Both are J12 core candidates.
- **Empire's lessons become code:**
  - Every forwarded line is logged, from the ctl verb and from Lua's `CliExecute` alike. In Empire, Lua calls left only counters.
  - The forwarder refuses unless the scene is `campaign` and the CLI's vtable is intact (stale object between campaigns).
  - The `console` verb refuses a command whose name matches a file the executor would open first. Find Napoleon's lookup order and
    folder statically, then check them against the file survey (`dev.log_files`).
  - The verb refuses a command marked no-op in the command table, naming it as no-op in retail.
  - The ctl result says which path ran: system, tweak, file, campaign hit, unknown to the campaign dictionary, or refused.

## Deliverables
1. **No-DLL probe.** For `CliExecute` from dev Lua: what runs (system, tweak, campaign) and what it returns. Each result is a fact
   with a run id.
2. **Static RE, written down.** The executor and its lookup order; the system and campaign dictionaries; the external handler slot
   and every read and write of it; the CLI ctor, `Execute` and its vtable slot; who builds the CLI and when. Write a short run
   README under `proxy/runs/<date>_j15re/` and record `engine_facts` rows (status `open` until the PC confirms them).
3. **Command table.** A re-runnable tool extracts every campaign command into a committed TSV, with these fields: name, usage,
   help, handler RVA, and status (`acts` / `parse_only` / `no_op`, plus `prints_only` where the output goes nowhere in retail).
   - The tool has a header and a `tools` row.
   - Compare with Empire's 172 commands and 33 no-ops: which commands are new, which are gone, which changed status.
4. **The forwarder and `dev.console`** as described under "Decisions already made". It is installed once per process before any
   campaign loads, and its install log line names every site and the slot.
   - Host tests cover: line parsing, the gate, the slot-claim rule, the file-name and no-op refusals, and the key-off behaviour.
5. **Control verb `console <line>|status|on|off`** with a checked result.
   - Result fields: `path`, `command`, `forwarded`, `hits`, `reason`; `status` adds the gate and slot state.
   - Its row goes in the `proxy/README.md` ctl table.
   - `job.sh ctl` needs no change. If it does, extend it; do not add a second submitter.
6. **Proof in game, campaign by campaign.** Use `campaign:new:<campaign>:<faction>` with intro skip. Every check below is a ctl
   result plus a before/after screenshot:
   - **a) P1:** the CLI exists at campaign load (or the route of preference 1 or 2 finds it).
   - **b) Verbs:** `console status`, a system command, an unknown command, a no-op command (refused), and `console off` then `on`.
   - **c) `teleport_to`** moves the selected agent, and **its map units are mapped.**
     - First read the conversion in the handler statically.
     - Then fit it against at least 3 teleports. Read positions after a settle: `CameraTarget` lies until the zoom has settled
       (Empire: wait at least 5 s after `SelectAndZoomToCharacter`).
     - The result is a formula or table in the facts. The verb accepts a target in the units agents can read back.
   - **d) `transport_to_region <region key>`** moves an agent into a named region. Find where Napoleon's region keys come from
     (Empire: db keys, not `RetrieveFactionRegionList`).
   - **e) Save and reload after console use.**
     - Teleport, then `CampaignUI.QuickSave`. Exit, relaunch, then `autostart campaign:<save>`.
     - Check that the agent is where the console put it, and that one `EndTurn` passes with no crash.
     - This is also the first run of J3's `campaign:<save>` target: fix it if it fails, and say so.
   - **f) Two acting commands from the table** beyond movement, chosen for J4's scenarios (for example `create_army` and
     `declare_war`). Each gets a result and a screenshot.
7. **Registries:**
   - `engine_sites` rows `verified` with run ids
   - a `config_keys` row for `dev.console`
   - `tools` rows for every new tool
   - `engine_facts` for every finding: the no-DLL result, P1, slot written or not, units, region keys, save/reload

## PC test
Run through the watcher, kits by `pc_deploy.py` sha-checked, every launch with `dev.skip_intro=1`. Headless (J13) does not exist yet:
tell Liam before each sitting, because the game window shows on his monitor.

Steps:
- a) `dev.console=0`: the J3 behaviour is unchanged, and `console` is refused with the reason.
- b) The no-DLL probe (deliverable 1).
- c) Deliverable 6 a-f.
- d) Uninstall is byte-identical, and every settings file is restored by the watcher.

**Saves:**
- Saves this job makes are kept. Copy them to `C:\napoleon_remastered_pc\_scratch\J15\saves\` with a `j15_` name.
- Remove them from `save_games` at the end, so Liam's folder holds only his saves.
- Record their sha1 in the report: they are the first saves on the PC, and J4 and J14 will want them.

Results go in a dated run report under `proxy/runs/` with job ids, ctl results and screenshots.

## Kill criteria
- **The executor or the handler slot is not found statically after about 40 calls:** stop the RE. Ship deliverables 1 and 3 (as far
  as the dictionary was found) and report what was traced.
- **Retail writes the handler slot, or the slot is non-zero on the PC:** do not overwrite it. Stop the DLL part and ask Liam.
- **No live CLI object by preference 1 or 2, and the ctor detour cannot pass the patch-engine checks in about 15 calls:** stop and
  report with the traces.
- **Any crash with `dev.console=1`:** read WER first. Two crashes for the same cause: stop, report with the dumps, and do not keep
  relaunching.
- **`teleport_to` units are not mapped after 3 methods** (static read, a fit against camera reads, a save read): stop that line. Make
  `transport_to_region` the placement route and record the units as an `open` fact.
- **The save/reload crashes or loses the moved agent twice:** stop and report. Console use then counts as unsafe before a save; say
  so in `proxy/README.md`.
- **Any write into the game folder, or into `core/`, would be needed:** stop and ask Liam.

## Finish
Write `jobs/J15/report.md`. Cover:
- what exists
- the RE findings, with links to the run README and the command table
- deliverable 6 a-f, each with its run id and screenshot
- the units mapping
- the saves made (names, sha1)
- deviations from this brief and why
- the decision rows proposed, if any
- what moves to the core in J12
- open questions, listed separately for J4, J9 and J14

Then `wsc reg set jobs J15 status=review report=jobs/J15/report.md`.
