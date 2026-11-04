# J40: Campaign console: close the open checks

Phase 1, job 40. J15 built the campaign dev console and proved most of it, but stopped at its call cap with three checks open and three
review findings marked "later". This job closes them: why `transport_to_region` does not move an agent, what `declare_war` and
`add_trait` really do, one EndTurn that passes after console use and a save reload, and the three console robustness fixes. J4 (scenarios)
and later campaign jobs use the console for placement, so each open check ends as a verified fact or as a named list of commands that
hit but do nothing.

Model: Opus, reason: static reverse engineering of two engine functions (0xaa11e0, 0xa83f90) and a fix to the proxy code that writes
into engine memory (D15). Budget about 240 tool calls (200 for the work, 40 for the core round trip and the 20-pass run); at the cap,
stop, commit, report what is left. At most 1 subagent, only for
independent read-only work (for example, disassembling the move path while you build the read-back recipe). Waiting belongs to the
harness: `job.sh` blocks inside one call; never poll with repeated calls.

Since J12 (core v0.4.0) the console and dev-channel code, its host tests, the watcher kit and the ESF tools live in warscape-core
(`core/proxy/src`, `core/proxy/tests`, `core/harness`, `core/saves`), which this repo never edits. The console fixes (deliverable 4)
are therefore a warscape-core PR, a tag Liam cuts, and a pin bump on `job/J40`; the rest of the job stays in this repo.

## Start
- Starts only after J12 is merged (`core` at v0.4.0 or later on `main`). Follow `CLAUDE.md` (Jobs: branch `job/J40`; "The core").
  Core changes are made in a `warscape-core` clone beside this one (`/c/Users/liamr/repos/warscape-core`, `git pull` first), on the
  branch `napoleon-j40`; read its `CLAUDE.md` and `docs/CONSUMING.md`. Never edit inside `core/` here. Read:
  - `docs/DECISIONS.md` (D2, D15, D26-D28, D30, D32)
  - `jobs/J15/report.md` and `jobs/J15/review.md` (findings 4 to 7 are this job's), `proxy/runs/20261029_j15pc/README.md` and
    `proxy/runs/20261029_j15re/README.md`
  - `proxy/README.md` ("Runtime patch engine", "Dev control channel", console section), `harness/README.md`
  - `jobs/J14/report.md` (save read-back tools) and `saves/SAVE_FORMAT.md`
- Search before writing: `python3 core/wsc.py find console campaign save diplomacy trait modal endturn`. Extend what exists:
  in this repo `discovery/core/{re_env,x86re,console_cmds}.py`, `saves/napoleon/{save_map.py,stage_save.py,load_save.sh}`,
  `proxy/napoleon` (the adapter: console `engine_sites`, generated `console_table.h`) and the J15 Lua probes (`campaign_select`,
  `campaign_camera`); in the core (read here, change in warscape-core) `proxy/src/{console,dev}.cpp`, `proxy/tests/test_console.cpp`,
  `saves/{esf_diff,esf_map}.py`, `harness/shot.sh`. `python3 core/proxy/tools/layout.py` shows which copy the tools use.
- Facts to resolve: `napoleon.console.transport_to_region_no_move`, `napoleon.console.acting_commands` (both `open`) and
  `napoleon.campaign.modal_stops_pump` (recorded 2026-10-29, run 20261029_j14pc; this job handles it).
- Evidence in `empire-remastered` (read-only: never edit, commit or push there): how Empire's `transport_to_region` and AI-turn modals were
  handled. Port the method, not the addresses.

## Target facts
Recorded by J14 and J15. Check each again before relying on it:
- **Console route:** the verb runs a line through the engine's Lua `CliExecute`; our forwarder fills the `.bss` slot and builds a
  CampaignCLI with the exe's ctor on the live campaign context (chain `*(*0x15c4938 + 0x9fc)`). All eight addresses are `engine_sites` rows.
- **`transport_to_region <eur_key>`:** a campaign hit; region keys are db keys (`eur_scotland`, 159 in `regions`). The handler needs
  `campaign+0x54` (already non-zero live), `campaign+8`, then a region lookup in `[campaign+8]+0xf7c` (0xaa11e0) and the move (0xa83f90).
  The spy did not move in 5 tries.
- **Positions:** `PosX/PosY` from `RetrieveFactionAgentsList` is the unit `teleport_to` takes (12.20 fixed point, no scaling). This works
  and stays the placement route unless deliverable 1 finds a better one.
- **Modal:** a modal popup (AI diplomacy request in the AI turn, a turn-start event) stops frames and the campaign Lua update until it
  is closed; `ctl lua` times out meanwhile.
- **Saves:** `save_games` held `quick_save.save`, `auto_save.save` and six J14 saves before J15; J15's quick save overwrote
  `quick_save.save` and was never removed. Read `saves_before.txt` in the J15 `raw/e_save` for the exact list.

## Decisions already made for this job
- **Static first for deliverable 1.** Trace 0xaa11e0 and 0xa83f90 with the existing kit (`x86re.py`, capstone and pefile, outside the repo)
  before any new PC run. Say which function returns early, on which condition, and what state that condition reads.
- **A move is accepted in one of three outcomes**, in order of preference: the console moves an agent into a named region (record the
  working command line); or a precondition outside the console makes it work (name it, test it once, record it); or it cannot work in
  retail (stripped body, as J15 found for four handlers): record why, mark the command `parse_only` in the generated table, and
  say that `teleport_to` with `PosX/PosY` is the placement route for J4.
- **Read-back goes through existing tools.** Diplomacy state and character traits are read back through Lua (campaign
  `RetrieveFactionList`-style calls found with `python3 core/wsc.py find lua diplomacy trait`) or through a save read
  (`save_map.py`, `esf_diff.py` between a before and after save). Do not add a second reader. A command is `verified` only when the
  state changed and the change matches the command; a command whose state does not change is listed as "hits, does nothing".
- **The modal is handled in code, not by hand.** If a Lua or ctl route can close the AI diplomacy modal (a UI close call, a dismiss
  of the popup component), add it as a Lua probe in this repo and a test, and use it in the EndTurn proof. A new ctl verb is core code:
  take that route only if no Lua probe can do it, and then it goes into the same core PR as deliverable 4. If no route exists after a
  bounded search, do not hack engine memory: record the modal that blocked, the screenshot, and name the job that must own it.
- **Code fixes (J15 review later items 5 to 7), all in warscape-core `proxy/src` on branch `napoleon-j40`, with host tests in
  `proxy/tests` that fail first.** The core stays game-agnostic: comments and tests name no Napoleon address, path or fact (the
  test's "no game named in core" lint); the addresses below are the adapter's `engine_sites` rows, named here only to say what the fix
  must protect. The fixes:
  1. `console off` keeps the forwarder in the slot and sets the "not handled" state, so the executor can never see a null slot between
     its test (0xc5612b) and its call (0xc5613e). Only an empty-to-ours write touches the slot; `on` after `off` flips the state back.
  2. The verb matches the forwarder's record to its own command name (`fname == l.name`) before attributing a result; a mismatch is
     reported as "no record for this line", not as a result.
  3. Each generated `_console\<id>.lua` chunk (under the mod's lua folder, `napoleon_remastered\lua` for Napoleon) is deleted once
     `RunLua` returns, and also on the error path.
     The pre-install-snapshot comparison after uninstall must stay byte-exact.
- **Saves are protected in the run, not in prose.** Before the first launch of the sitting copy `save_games` listing and hashes to
  `_scratch\J40\`; at the end restore any overwritten file from J14's staged copies or the snapshot and remove J40 saves.
  Every save this job makes goes to `_scratch\J40\saves\` with a `j40_` name; the folder `save_games` must match the snapshot at
  the end (compare the listing and sha1s, record the result). Do not take J18's guard work: report the manual steps you needed.
- **Game start through the watcher only.** Every launch `dev.skip_intro=1`, headless as in J15, `dev.console=1` for the sitting. Use
  `saves/napoleon/load_save.sh` and the J15 profile `dev-console`; do not start `Napoleon.exe` yourself.
- **One core round trip, after the PC findings.** Run the PC sitting (deliverables 1 to 3 and 5) on the pinned core first: the
  read-back and the EndTurn proof need no code change. Then put everything the core needs into one warscape-core PR: the three
  fixes, plus a ctl verb or a new patch-engine site kind only if the sitting proved it is needed (anything else the core should
  have goes to its `docs/BACKLOG.md`). The PR carries `VERSION` at the next minor after the pinned tag (v0.5.0 if v0.4.0 is still the
  latest; check `git tag` in the clone) and is green in the core's CI. Open it, ask Liam to merge it and tag it, then commit, push,
  stop and end the turn. Do not wait or poll. Resume when Liam says it is tagged.
- **The pin bump, then the final build.** On `job/J40`: bump `core` and `wsc.toml` `[core] version` in one commit (`core_pin` gate),
  regenerate anything generated from the core, and run `wsc gates`. The bump changes the DLL build id, so rule 79 applies
  (`tools/pr_policy.py`): on the final build, a short console re-check on the PC (`console on`, `off`, `on`, one campaign line, the
  chunk folder empty after it, clean uninstall), then `python3 core/harness/acceptance.py run --passes 20 --run <date>_j40acc`, its
  ledger lines and evidence committed on the branch. Any later change to a DLL input (the adapter `proxy/napoleon` included, so a
  regenerated ini too) needs the 20 passes again: finish the adapter changes before the run.

## Deliverables
1. **`transport_to_region`.** The static trace, the answer, and one of the three outcomes above, recorded as an updated
   `napoleon.console.transport_to_region_no_move` fact (state `verified` with date and run id) plus a short section in the RE README.
   If the fix is a working command line or precondition, prove it once on the PC with a before and after `PosX/PosY` and the region of
   the agent.
2. **Read-back of `declare_war spain` and `add_trait C_Agent_Spy_Network 1`.** Before and after state of diplomacy (Britain and Spain) and
   of the target character's traits, through the route chosen above. Update `napoleon.console.acting_commands` to `verified`, or to
   a list of commands that hit but do nothing. If the status of other console commands changes (for example a command found to hit but
   have no effect), update `console_cmds.py` and regenerate the table; do not hand-edit generated files.
3. **EndTurn passes.** One EndTurn after console use and a save reload that finishes and returns control (next turn number read), with
   the AI diplomacy modal handled in code or the blocker recorded as above. Update `napoleon.campaign.modal_stops_pump` if the handling
   changes the claim.
4. **The three code fixes**, in warscape-core (branch `napoleon-j40`, one commit each), each with a host test, green in the core's CI;
   merged and tagged by Liam, then pinned here. Check the changes in `test_console.cpp`: the no-game-in-core lint still passes and the
   key-off path still does no engine read or write. Name the core PR, its tag and the pin-bump commit in the report.
5. **Saves left as found.** The `save_games` listing and sha1s equal the snapshot at the end; the run README states it.
6. **Registries:** facts updated or added with date and run id; any new tool has a header and registry row (`tools` gate); `wsc gates`
   and `python3 tools/pr_policy.py --branch job/J40 --base origin/main` pass before the pull request (rule 79: 20 passes on the final
   build).

## PC test
Headless, no Liam needed (J13). One sitting, `proxy/runs/<date>_j40pc/` with a README that lists every step and run folder, shots at 1280
px (`core/harness/shot.sh`), and the save-folder comparison, on the pinned core. Order: install, snapshot saves, (1) transport proof if
the static work found a way, (2) read-back before and after, (3) save, relaunch, EndTurn, (4) restore saves and uninstall; the folder
must be identical to the pre-install snapshot. Each launch: log, zero new dumps, clean exit. After the pin bump: the console re-check
and the 20-pass run on the final build (decision above), in `proxy/runs/<date>_j40final/` and `harness/runs/<date>_j40acc/`.

## Kill criteria
- The static trace of 0xaa11e0 and 0xa83f90 is not decided after about 60 calls: write down what is known, record outcome three
  (cannot, with the evidence so far) as an `open` fact with the next step named, and go on to deliverables 2 to 4.
- Any crash that appears only with the new code after 2 attempts: stop, collect the WER dumps, report; do not keep relaunching.
- A save in `save_games` that cannot be restored to its snapshot hash: stop using the campaign, report which file and why.
- The core PR is refused by the core's CI or by Liam: fix it on `napoleon-j40` once; if it is still refused, report the fixes as
  open, finish deliverables 1 to 3, 5 and 6 on the pinned core, and leave the pin as it is (no 20-pass run is needed then).
- The call cap: commit, report what is left.

## Finish
Write `jobs/J40/report.md`: what each deliverable found, the evidence (run ids, fact ids), the saves comparison, deviations from this
brief and why, open questions, and the core PR, tag and pin bump (or why there is none). Then `wsc reg set jobs J40 status=review report=jobs/J40/report.md`.
