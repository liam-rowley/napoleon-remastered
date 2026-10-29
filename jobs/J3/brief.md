# J3: dev control channel and load time

Phase 1, job 3: the dev side of the proxy that lets an agent drive Napoleon without a human: a timeline of every load phase,
intro skip, autostart into a named scene with the right map, a scene heartbeat, a checked request/result control channel, and a
warm reset that returns to a known state inside the same process. **Measure first, then cut**: every speed-up is reported against
a baseline measured in this job. The high-level control API (`scene`, `cam`, `shot`, `order`, ...) and the scenario library are J4's;
this job builds the channel and the few verbs J4 stands on.

Model: Opus, reason: DLL hooks, the engine's Lua and reverse engineering of Napoleon's front end (D15). Budget about 220 tool calls;
at the cap, stop, commit, report what is left. At most 2 subagents, only for independent cloud work (host tests, CI). Waiting
belongs to the harness: `job.sh` blocks inside one device call; the agent never polls with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J3`). Read `docs/DECISIONS.md` (D2, D3, D15, D22-D25), `docs/plans/PLAN.md` (sections 3, 4,
  phase 1), `proxy/README.md` (all of it: the pass-through contract, engine-site layout, build, PC install), `harness/README.md`, and
  the reports `jobs/J1/report.md` and `jobs/J2/report.md` (open questions and "Later": several land here, listed below).
- Search the registries before writing anything (`python3 core/wsc.py find hook log launch heartbeat`): extend `proxy/core`,
  `gen_tables.py`, `pc_deploy.py`, `harness/core/job.sh` and the watcher; do not write a second of any of them.
- Attach `liam-rowley/empire-remastered` (read only, never modified) as the evidence base. Port the design, re-check every fact on
  Napoleon: `rml_mod/src/devspeed.cpp` (header: intro skip at `BinkOpen`, file redirection rules, `state.json`, autostart, scene
  tracking), `rml_mod/src/overlay.cpp` (section "dev control channel", from line 558), `rml_mod/src/lua_bridge.cpp` (how the engine's
  Lua loads the DLL and the safety rules in its header), `rml_mod/src/lua_cmdq.h`, `rml_mod/dev/{autostart.lua, state_hook.lua,
  end_deployment.lua}`, `docs/learnings/LEARNINGS_ENGINE.md` ("Remote launch speed", "Engine scripting internals", "The engine finds
  packs by listing data\"), `docs/learnings/LEARNINGS_HARNESS.md` (search: autostart, `.sp_default`, "Soak mechanics", "measure battle
  load", "Most \"flanders40\"", "Map choice"). Do NOT port RmlUi, `headless.cpp`, the synthetic input layer, controls, screenshots,
  the console bridge, camera code or `hv.sh`.

## Target facts
From J1 and J2 (`registries/engine_facts.jsonl`); check again and record new ones with date and run id. `Napoleon.exe` pinned identity
(`napoleon.exe.identity`), ASLR base per boot (`napoleon.exe.observed_base`), no DRM stub, one `Direct3DCreate9` on the DllMain thread
(`napoleon.d3d9.proxy_load`), unattended launch route `exe` (`napoleon.launch.unattended_route`), settings files and baselines
(`napoleon.config.*`). No saves on the PC yet. The watcher is installed and live (`harness/runs/20261029_pctest/`).

## Decisions already made for this job
- **Where the code lives:** game-agnostic parts in `proxy/core/` (hook machinery, file-redirection rules, phase timeline, Lua bridge
  plumbing, control-channel protocol, state file) and the Napoleon specifics in `proxy/napoleon/` (movie names, scene classification,
  the autostart and reset Lua, scenario presets). Both stay core candidates for J12, so keep the split clean.
- **Dev only, behind the guard:** every new key defaults off and has release value off, with a `config_keys` row. Nothing new runs on a
  mismatched exe or with `proxy.enabled=0`: the pass-through contract in `proxy/README.md` is unchanged and its lint test covers the new
  code. With every dev key off the proxy must behave exactly as J1's.
- **Zero-touch:** nothing is written into `data\` or any game file. Loose Lua and presets reach the engine through the file-redirection
  rules (virtual `add` / `redirect`, Empire's design); proxy-owned output stays in `napoleon_remastered\` as today.
- **Hooks:** pick IAT patching or MinHook (BSD-2, source fetched by a committed tool pinned by version and sha256, never vendored as a
  binary), justify it in `proxy/README.md`, and log every hook installed. Engine-code hooks, if any, go through `engine_sites` with
  anchor bytes like any patch.
- **Control channel through the PC state folder, not the game folder (D25):** requests `C:\napoleon_remastered_pc\ctl\<id>.cmd`, results
  `<id>.done` (JSON written last: `ok|failed|timeout`, UTC times, the evidence: log lines and state at completion), ids never reused,
  same contract as the watcher's jobs. `job.sh` gains a `ctl` subcommand that submits and blocks inside one device call. The folder is a
  config key, so the uninstall stays byte-exact.
- **DXVK state cache:** DXVK 2.7 removed the state cache (its release notes: unused since `VK_EXT_graphics_pipeline_library` in 2.0),
  so with the pinned 3.1.1 there is nothing to warm and J1's `DXVK_STATE_CACHE_PATH` default is dead (remove it and say so). What is
  left of the row's "warm the DXVK state cache": measure the first and second launch after a driver-cache clear, find where the cost
  is (DXVK pipeline compiles, the NVIDIA driver's on-disk cache), and only build a warm step if the numbers show one is worth it.
- **Headless window placement is not in this job** (Liam 2026-10-29: a separate job). Until it exists, unattended runs open the game on
  Liam's monitor: tell him before each PC sitting.

## Deliverables
1. **Phase timeline.** One UTC millisecond timeline per launch, in the proxy log and as `napoleon_remastered\logs\timeline.json`:
   process start (from the OS), DllMain, `Direct3DCreate9`, device created, first `Present`, each movie opened and closed, front end
   first pump, autostart issued, loading started, scene ready (`frontend`, `campaign`, `battle_deploy`, `naval`), first `Present` after
   ready, exit. A committed tool turns timelines into a table (median and spread per phase, n per arm).
2. **Baseline before any cut:** at least 5 launches each of proxy on DXVK with no dev keys, to the front end and (driven by hand or
   by the plainest Lua route) into a land battle, a naval battle and a new campaign. Medians into `engine_facts`. Then set the targets
   (write them into the report and the measured `load_time_s` of the scenario rows used).
3. **File-redirection rules and a file-open survey** (`dev_log_files`): every distinct file opened and every movie open, so Napoleon's
   start-up movies, front-end scripts and battle preferences file are found, not assumed from Empire.
4. **Intro skip** (`dev_skip_intro`): Napoleon's start-up movies refused at open; the front-end background untouched. Measured.
5. **Minimal Lua bridge (no RmlUi):** the engine's Lua loads the proxy (first check Napoleon's Lua version and whether
   `package.loadlib` is reachable from UI scripts, as on Empire); a small global table (`log`, `dev_config`, `dev_state`, `poll`,
   command results) under Empire's safety rules: never raise a Lua error from C, never call back into Lua from C, one engine thread.
6. **Scene tracking and state file:** `napoleon_remastered\state.json` rewritten atomically about twice a second with launch id, frame
   count, scene (`intro|frontend|loading|campaign|battle_deploy|battle|naval`) and UTC time. Add it to the adapter's
   `heartbeat_files` so the watcher's "menu reached" (J2 report, deviation) is `scene == frontend`.
7. **Control channel** with checked results: `ping`, `state`, `log <text>`, `lua <file>` (its result returns the chunk's outcome, so no
   Empire-style `luamark`/`luawait` grep), `waitfor <scene>[|<scene>] [timeout_s]`, `autostart <target>`, `reset <target>`, `exit`.
   Unknown verbs fail with the reason. Host tests for the parser, the id rules and the scene state machine.
8. **Autostart** through the engine's own front-end Lua, never coordinate clicks: `frontend`; `campaign:new:<campaign>:<faction>`,
   `campaign:continue|<save>`; `battle:<preset>` for land and naval presets; a historical battle if it costs little. **The map is
   checked:** the result names the map the engine actually loaded and fails if it is not the preset's (Empire ran "Flanders" on
   Anatolia for days). If the custom-battle screens rewrite a preferences file, add it to the adapter's `config_files` so profiles
   restore it byte for byte.
9. **Warm reset** (`reset <target>`): from campaign or battle back to a known state inside the same process (the front end, then the
   target again) with checked state after. Measured against a relaunch; address space and commit logged after each cycle. Ten resets
   in a row without a crash, and growth per cycle reported. If a reset fails, the result says so and the watcher's relaunch is the
   fallback.
10. **Carried over:** `proxy.minidump` release value 2 (J1 open question 1); `build.sh` refuses a shallow clone (J1 deviation); rotation
    of second-process `proxy.p<pid>.log` files (J1 "Later"); the dead DXVK state-cache default (above).
11. **Registries:** `config_keys` rows for every new key, `tools` rows for every tool, `engine_facts` for every measured or found fact
    with run ids, `scenarios` rows only for the scenes used here (J4 fills the library).

## PC test
Through the watcher, unattended once Liam has said go (ask before each sitting: the game window shows on his monitor). Kits by
`pc_deploy.py`, sha-checked. a) dev keys off: identical to J1 behaviour (log, no dumps, uninstall byte-identical); b) the baseline
(deliverable 2); c) survey and intro skip, measured; d) every autostart target, map checked, 3 launches each; e) the control channel:
every verb, a bad verb, a timeout; f) 10 warm resets in one process, then a relaunch for comparison; g) cold and warm driver cache;
h) profile restore leaves every settings file byte-identical after battles. Results in a dated run report under `proxy/runs/` with
job ids, timelines and the summary table, and as `engine_facts` rows.

## Kill criteria
- The engine's Lua cannot be entered after 3 different approaches: stop that line and report; deliverables 1-4 and 6 (scene from the
  file survey and `Present` timing) still ship.
- Any start-up crash with dev keys on: read WER first (Empire lesson 23), stop, report with the dumps; do not keep relaunching.
- Warm reset crashes twice for the same cause, or grows the address space by more than 100 MB per cycle: stop, ship relaunch as the
  reset, report the numbers.
- Autostart lands on the wrong map and the selection cannot be fixed in 3 attempts: stop and report what the engine selected.

## Finish
Write `jobs/J3/report.md`: what exists, the baseline and the after table per phase with run ids, targets met or not, the control verbs
and their result format (one place: `proxy/README.md`, linked), deviations from this brief and why, what moves to the core in J12,
open questions. Then `wsc reg set jobs J3 status=review report=jobs/J3/report.md`.

## Open questions for Liam (raised while writing this brief)
1. **Headless as its own job** (your call 2026-10-29): it needs a `needs_brief` row on a `plan/` branch (a brief branch may change only
   its own row). Proposal: depends on J3, before J4, so the acceptance runs stay off your monitor; it also needs the 1080p and 1440p
   VDD modes from J2's open question 1.
2. The row still says "warm the DXVK state cache"; this brief replaces that with a measurement (above). Reword the row on the same
   `plan/` branch if you agree.
