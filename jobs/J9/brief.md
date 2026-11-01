# J9: Engine API surface and engine sites

Phase 2, discovery. Three things in one job because they share the exe and one RE kit: (A) the engine's Lua API surface per screen and game
phase, as observed at runtime; (B) an index of the strings in `Napoleon.exe`; (C) the engine sites behind the sprite (imposter), LOD and
shadow settings, each proven with anchor bytes and a dated run id. J24 (shadow resolution and fit), J27 (imposter and LOD distances),
J10 (UI atlas) and J11 (the phase 2 gate) read this job's output and nothing else.

Model: Opus, reason: static reverse engineering of the exe (Lua registration tables, tweaker initialisers, sprite and shadow setup),
runtime patch proofs through the DLL and crash reading (D15). Effort high. Budget about 300 tool calls; at the cap, stop, commit, report
what is left. Subagents (D34) only for independent read-only work, for example the static name-to-address pass over the Lua registration
tables while the PC probe runs. Waiting belongs to the harness: `job.sh`, ctl requests and the acceptance runner block or run in the
background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J9`; "Exe stays vanilla", "The PC game folder is a deploy target"). Read `docs/DECISIONS.md` (D2, D15, D30),
  `docs/plans/PLAN.md` phase 2 and phase 3 items 2 and 3 (what the output feeds), `proxy/README.md` ("Dev control channel", the engine-sites
  paragraphs, "Adding a site"), `harness/README.md`, and the registry rows of J24, J27, J28 (their descriptions say what they need).
- Reports to read: `jobs/J6/report.md` "For J9" and `jobs/J6/review.md` ("For J9": `mask_for` over-masks and can turn a real match into `none`:
  treat `none` as "not found this way", and filter candidates by fixed-byte count, `32 - masked` in `detail.signatures`), `jobs/J7/report.md`
  ("For J9"), `jobs/J15/report.md` ("For J9": 12.20 fixed-point positions; `x86re.py` and `console_cmds.py` take an exe and an output path) and
  `jobs/J15/review.md` item 8, `jobs/J4/report.md` and `jobs/J44/report.md` (ctl verbs, the scenario table, settle, what pumps), `jobs/J12/report.md`
  (core paths). If `jobs/J8/report.md` is on `main` when you start, read it: J8 hands its engine addresses (blob shadows, the shadow pass) to
  this job as open facts with owner J9.
- Search before writing: `python3 core/wsc.py find lua api surface probe exe string x86re candidate sprite lod shadow`. Starting facts, all
  `open` in `registries/engine_facts/`: `napoleon.diff.lua_api.surface`, `napoleon.diff.exe.guard_candidates`, `.patch_candidates`,
  `.function_candidates`, `napoleon.files.loose_override`, `napoleon.files.loose_probe_dirs`. Tools: `discovery.core.exe` (the candidate
  search), `discovery.core.x86re` and `discovery.core.re_env` (the RE kit; run it from the pinned venv), `discovery.core.lua_api`,
  `discovery.core.console_cmds`, `discovery.core.tsvgz`. The proxy already checks every `engine_sites` row at start-up (11 verified rows, J15 and J43).
  Existing Lua probes to reuse: `proxy/napoleon/lua/probes/{env_dump,ui_tree,battleui_names,battle_api,campaign_keys}.lua`, `proxy/napoleon/lua/wrappers.txt`.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there). Port the method, then check every fact again on Napoleon:
  - `orchestrator/handoffs/2026-10-24_engine_api_brief.md` (the method for deliverable A and its output shape), `assets/extract/engine_api_*.jsonl`,
    `rml_mod/tools/controls/re/lua_api/engine_api_{runtime,events}.py`, `rml_mod/docs/atlas_live/engine_api/`, `rml_mod/docs/engine_api.json`
  - `docs/learnings/LEARNINGS_ENGINE.md`, the entry "Configurable sprites, animation, water, sky (gfxcfg ...)" and its updates (sprite page and frame
    time chosen by one switch on a getter of the object at a global; the tweaker initialiser pattern `mov dword [esp+0x18], <float>; push <name>;
    mov ecx, <TWEAKER>; call <ctor>`; building and rigid LOD ranges are db data, `warscape_rigid_lod_range`, naval `warscape_naval_lod`; the
    shadow NULL render target branch and the caps table; an anchor must never include an absolute address: ASLR relocates it)
  - `rml_mod/data/exe_patches.json`, `rml_mod/tools/gen_exe_patches.py`, `docs/graphics/GRAPHICS_NOTES.md` "Configurable graphics keys"
    and the imposter section, `docs/graphics/SHADOW_FIT_UNITS.md`
- Other jobs touching the same files: J8 (queued) changes the DLL (device-layer capture, `core` pin); rebase on `main` before the pull request.
  J16 (queued) also hooks the device. Do not edit `core/`; a core change (for example a `value_offset` field, `proxy/README.md` open question 1)
  is a warscape-core pull request, listed in the report, not done here.

## Decisions already made for this job
- **Settled by Liam 2026-11-01 (D38):** J9 stays one job: work in the priority order and stop at the cut line below; no J9a/J9b split.
- **Order of work** (so a cut by the budget costs the least): 0 the kit fix; 1 the string index (the base of every hunt); 2 shadow, sprite and LOD
  sites (what J24 and J27 are waiting on); 3 the API surface (J10); 4 the guard and function candidates; 5 the loose-override probe. Deliverables
  are numbered the same way. At the cap, finish the item in hand, commit, and write what is left as open facts.
- **Sites are proven by the exe, not by Empire's addresses.** An Empire signature hit is a candidate. A site is `verified` only when (a) static RE
  explains it (what the code does, from Napoleon's own strings and call chains), (b) its `anchor_bytes` (opcode bytes, never an absolute address)
  and `stock_bytes` match in the running process (the proxy's start-up check, logged in a run), and (c) for a `patch` row, one run with its key on
  shows the effect (a readback, a log line or a shot at a fixed pose) and one with it off shows stock. A row that fails (c) stays out of the
  registry and becomes an `open` fact with the evidence. Rows carry `exe=sha1:9aebcd2172f2878d781b079f7feb45b0e12e0250`, a `config_key`
  (default 0, release 0, a `config_keys` row, owner J24 for shadow, J27 for distances and sprites) and `verified` {date, run}.
- **J9 proves a site works at one non-stock value; J24 and J27 own the stepping**, their measurements and any proxy feature that writes a
  configured number rather than fixed `patch_bytes`. Say in the report what the site's value encoding is (float, imm32, imm8) and how many
  places must change together, so those jobs can size their work.
- **Per setting, name the route that governs it**, not only the exe site: an engine site, a db table (check `warscape_rigid_lod_range`,
  `warscape_naval_lod` and any LOD or imposter table in `discovery/napoleon/db_schema.json` and the decoded db), or a preference
  (`gfx_*` keys in the prefs file). The routes table in deliverable 2 is what J27 reads. Prefer the data route when both work (no exe write).
- **Runtime probes enumerate; they do not call.** `pairs()` over `_G`, each global table and each reachable object's metatable and `__index`,
  with no function calls except names classified probe-safe and kept in a committed list. Empire's gotchas are candidates to re-check on Napoleon,
  not facts: `string.sub` with a negative start, `string.find`, `gmatch` (Napoleon fact `napoleon.lua.string_find_stalls_pump`: one call stops the
  battle pump), and calls with no or wrong arguments that crashed Empire. A state that crashes the game twice is skipped and listed.
- Everything goes through the watcher and `ctl.py scene` (J44): fixed-sky pack and launch keys apply, DXVK backend, 1920x1080, profile restored
  byte for byte. Probes use `ctl lua <file>`; only the main menu pumps in the front end (`napoleon.lua.update_callbacks`), so other front-end
  screens need the `dev.lua_bridge` wrappers (`wrappers.txt`) or a `key`/`click` probe (allowed for probes only, rule 78 scans the presets).
- Out of scope: stepping values and tuning, shader replacement, the cascades spike (J25), any change to the render path, the console and
  camera features, the battle control route (J28), UI atlas content (J10).

## Deliverables
0. **The kit fix first** (J15 review 8): `discovery/core/x86re.py` `walk` drops an indirect `jmp` (register or memory tail call). Record it as an
   icall (or a separate `itail` list if that reads better, said in the header), with a host test on synthetic bytes (`jmp eax`, `jmp [mem]`,
   a jump table). Re-run `discovery/core/console_cmds.py` on the exe: if a handler's class changes, commit the TSV diff and say so; if none does, say that.
1. **The exe string index:** a registered tool (`discovery/core/exe_strings.py`, header and tools row; reuse `x86re.Image`) that lists every ASCII
   and UTF-16 string of `Napoleon.exe` with RVA, section, and the code sites that reference it (count and first few). Output under
   `discovery/napoleon/` (compressed with `discovery/core/tsvgz.py` if over about 3 MB; sorted, deterministic, `--check`). A `find` mode for the
   RE sessions after this one (and a line in the tool's `when:`). Whether `wsc find` should index it is a core question: put it in the report.
2. **Engine sites for sprite, LOD and shadow settings** (the PC proof is one sitting, see below):
   - Shadow, for J24: the light sweep (candidate `0xd27696`, from J6), the shadow map size and where it is created, the fit and bias constants, the
     NULL render target branch and the caps table for the shadow path, the receiving-side switch if one exists, and whatever J8 handed over (blob
     shadows: the engine switch and its address). Which of these an 8K map needs to change together.
   - Sprite (imposter), for J27: the page size, the per-quality switch, the frame time and the distance tweakers (large, sprite, no variant, shared pose),
     found from Napoleon's own tweaker strings (the candidates match several near-identical initialisers: use the string push, not Empire's window).
   - LOD: unit, building, tree, ship (mast, rope, knot, flag size) and grass distances (candidate grass grid `0x1019ad8`); `lod_distance_scaler`,
     `rigid_lod_distance_scaler`, `min_lod_range` and `max_lod_range` if they exist as strings here.
   - For each setting: `engine_sites` rows as above, `config_keys` rows, `engine_facts` rows (each proven with a date and run id, or open with owner and evidence), and one
     **routes table** (setting, governing route: site / db table / preference, stock value, value encoding, rows, proof run) in
     `discovery/napoleon/engine_sites_routes.md`, one owner for the topic. After the rows: `python3 core/proxy/tools/gen_tables.py`, rebuild, install, prove.
3. **The Lua API surface per screen and phase:** the committed raw probe output per state in the run folder, and a generated table
   `discovery/napoleon/engine_api.json` (+ a generator registered as a tool, `--check` rebuilding it from the committed raw output and the J6
   diff): per name its owner (global table, object type, component), kind (C function, Lua global, method, event or callback), the states where it
   exists, observed type and, for probe-safe getters, a sample; static argument count vs the one the vanilla scripts use, where they differ. States:
   front end (main menu and each screen reachable), campaign map (nothing selected; an army, a fleet, an agent, a settlement selected), the campaign
   panels reachable, battle deployment, land battle, siege, naval. Close the open questions of `napoleon.diff.lua_api.surface`: are the 28 new and
   8 gone CampaignUI names real at runtime, the 38 argument-count differences, the new component methods (`TriggerAnimation`, `ShaderTechniqueGet`,
   `SetZDepth`) and events (`OnDraw`, `OnPreDraw`, `OnAnimationFrameEnd`); drop the build-system names (`buildcommands`, `project`, ...) the static
   diff caught from a non-game script. Record the campaign root's update behaviour (`napoleon.lua.update_callbacks` says "campaign root not run yet").
   Stretch, if under budget: name-to-address for the C functions from the Lua registration tables (static), for J28 and later RE.
4. **Candidates:** the 6 guard-site candidates and the function candidates a consumer needs (J28's selection, positions and orders chain first
   if cheap): each either an `engine_sites` hook row (anchor bytes, run id) with a name from its callers, or left `open` with the reason. Close or
   narrow `napoleon.diff.exe.guard_candidates`, `.patch_candidates` and `.function_candidates` with what was done and what was not.
5. **The loose-override probe** (`napoleon.files.loose_override`): does a loose `data\` copy beat a pack entry? Put one harmless, visible loose
   copy of a known pack entry through `pc_deploy.py` (kit files, sha-checked, owned by the install record), check the result in a shot or a
   log, and uninstall; if `pc_deploy.py` cannot place a file there without a harness change, stop the probe, record why, and do not write into
   `data\` another way. Also answer, if the file-rule log shows it, whether the 4 tgas J7 could not parse (2 flag frames, 2 `rigidmodels` hints) are opened.

## PC test
All game launches through the watcher and `ctl.py`; Liam is not needed unless a step needs admin. One sitting, in this order: baseline idle
check (install with the new rows and every key off: start-up site check passes, a `land_small` shot matches the acceptance baseline); API probes
per state (front end, campaign, then the three battle kinds); site proofs, one launch per patch family with its key on and a stock launch, shots
at fixed `cam` poses (`land_small` deploy for shadow and sprite, `naval_small` for ships, a pose with trees and grass for LOD) and `perf` where
it shows cost; the loose probe; then the **20-pass acceptance run on the final DLL build** (the new rows change `proxy/napoleon/generated/`, so
rule 79 applies), in the background inside one call. Uninstall at the end and compare with the snapshot, as J44 step f. Run folder
`harness/runs/<date>_j9pc/` with a README: run ids, build, profile, one line per proof; raw probe output goes there if small, otherwise
`<state>\_scratch\J9\` with sha256 in the README. Make the DLL changes in as few builds as you can: every rebuild after the acceptance run restarts it.

## Kill criteria
- A setting family (sprite distance, a LOD tweaker, the shadow size) has no explained site after about 40 calls on it: write down what is known as
  an `open` fact with the strings and addresses tried, and go on to the next family. Do not guess a site into the registry.
- A site's anchor or stock bytes do not match in the running process, or a patch run crashes the game: stop writing that site, read the WER dump
  and the proxy log once, record it. A second crash in the same family stops that family. Do not relaunch in a loop.
- A runtime probe state crashes the game twice: skip the state, list it with the last name probed, finish the others.
- The 20-pass run fails twice for a cause in this job's code: stop and report; do not keep re-running. A failure from the PC or the display
  (J44 incidents) is the watcher's: report it with the ledger lines.
- Over about 300 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J9/report.md`: what was built (tools, rows, tables), the runs with ids, the routes table summary, the API surface counts per state and
the answers to the J6 questions, deviations from this brief and why, and open questions for J10, J24, J27, J28 and the core. Then
`wsc reg set jobs J9 status=review report=jobs/J9/report.md`.
