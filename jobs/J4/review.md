# Review of J4 (Scenario library, control API, acceptance gate)

## Round 1 (2026-10-30, branch `job/J4` at 9c8ad61)

Reviewer: a fresh Opus chat (session `f21c7ea6-c674-4bc0-8831-11e84e73660b`) that built none of the branch (builder:
`70440f83-d867-4302-bed5-220da32255c0`).

**Verdict: merge after fixes.**

### Machines
- `wsc gates`: 11 ok, 1 warn (hooks path written absolute in this worktree, not a branch problem), 230 host tests passed.
- `pr_policy.py --branch job/J4 --base origin/main`: refused only for the missing review and the row not being `done` (expected before this review).
- CI `gates` on 9c8ad61: success (run 40977443713). No pull request exists yet.

### How to read this job
The report says plainly that the phase 1 gate is **not** passed: the battle-script route hit the kill criterion, so `cam`, `order`,
`pause`, `speed` are refused, no scenario was added, nothing is deterministic, no baseline exists and the ledger is empty. That is
honest and matches the evidence (`harness/runs/20261029_j4pc/README.md`). Liam's `plan/j4-followups` (2aaba51, no pull request yet)
re-scopes the rest as J43 (camera and speed route) and J44 (library, sky, 20-pass gate) and moves J8, J9, J12, J23 and J28 onto J44.
I review J4 as the layer that was built, on that basis. **It must not be marked `done` on `main` before `plan/j4-followups` lands**:
on today's `main`, J4 `done` would unblock J12, J8, J9, J23 and J28, all of which need the gate that does not exist.

### Blocker
1. **Rule 79 deadlocks every proxy/ and harness/ job once this merges.** `tools/pr_policy.py:101-120` (`acceptance_problems`) turns on
   as soon as `harness/acceptance/ledger.jsonl` exists on the base, and this branch commits it (empty). After the merge, any `job/`
   branch that changes `proxy/` or `harness/` needs 20 ledger passes on its build, but `acceptance.py run` stops after loading the
   baseline (report: "the PC binding is not wired"), no `baseline.json` exists, and the camera route the passes need is J43's
   own work. So nobody can satisfy it:
   - `job/J42` (in progress) changes `harness/core/watcher.ps1` and `harness/tests/*`: refused at its next policy run.
   - J43 (depends on J4) must change `proxy/` to find the camera route: refused before it can produce the route J44 needs.
   - See it fail: on `main` after the merge, `python3 tools/pr_policy.py --branch job/J42 --base origin/main` prints `rule 79: ... holds 0
     consecutive acceptance passes`.
   Fix (job chat): do not activate on the ledger's mere presence. Either leave the ledger uncommitted (J44 commits the first one), or
   make `active` require a valid committed `harness/acceptance/baseline.json` too, and add a `test_pr_policy.Rule79` case: ledger present,
   no baseline, proxy change, no error.

### Should-fix
2. **The kill criterion was applied beyond its reach** (named in the report as a deviation, but the reason given does not hold).
   The brief's criterion stops the camera, speed and order lines only and says to store poses as coordinates where possible.
   Deliverables 2 (rows with measured `load_time_s` at the default camera), 4 (sky pin data routes; determinism by shots on two
   launches at the default camera), 5 (`perf` on the PC) and PC test steps a, c, d, f did not need the camera and were not done. The
   criterion's own list also names "attaching a `.battle_script` to a custom battle preset", which the run report does not show tried,
   and deliverable 1 asked for siege, naval and the campaign camera calls (not probed). With J43/J44 now owning these, this is a scope
   record, not a reason to hold the merge: J43's brief should start with the untried preset `.battle_script` route and `BattleUI.*`.
3. **The pump stall is not isolated from this branch's DLL.** `ctl lua` stops 20-175 s after a battle loads (fact
   `napoleon.battle.script_api_reachable`); every probe ran with `dev.perf=1` and this branch's build 5c984fbabb49, and PC step a
   ("dev keys off: J3 behaviour unchanged") was not run. The recorder takes the dev lock on every Present when `dev.perf=1`
   (`proxy/core/dev.cpp:58-64`); unlikely to stop the Lua pump, but untested. J43 should reproduce the stall once on `main`'s DLL with
   `dev.perf=0` before chasing it.
4. **Most verbs have never run on the PC.** `scene`, `shot`, `reset`, `perf`, `state` (`harness/core/ctl.py`) and the proxy `perf` verb
   are tested only against fakes (report says so). The tools registry rows should say "untested on the PC" until J44 runs them, so a
   later job does not take them as working.

### Later
5. `proxy/tools/pc_deploy.py:533` docstring says files the install does not own are never touched; the code replaces any file at a
   dev Lua path. Harmless today (the whole mod folder is owned and removed by uninstall) but the claim is wrong: drop it or skip unowned files.
6. `tools/pr_policy.py:98` `ACC_EXEMPT` matches by substring: any path containing `README.md` or `/runs/` anywhere is exempt
   (e.g. `proxy/core/README.md.bak`). Match on the path's name or prefix instead.
7. The ledger is self-attested: rule 79 trusts hand-written JSON lines, and `harness/acceptance/` is exempt, so a branch can add 20
   pass lines without a run. When J44 wires `run`, have each line carry the run id and its evidence path and have the check verify the
   run folder exists.
8. The builder wrote a scratch Lua file into the game folder outside a deploy (report, Deviations). `sync-lua` now exists; a guard in
   the ctl `lua` verb refusing files outside `napoleon_remastered\lua` and `_scratch` would make the slip impossible.
9. Row 75 (`wsc jobs view` PC state, usage source) is not done and not in J43/J44's descriptions: add it to J44 or a meta row.

### What is sound
- `make_result` (`harness/core/ctl.py:40-51`) makes rule 77 structural: no verb can return ok without a check.
- The proxy change is small, behind `dev.perf` (default 0, release 0, config_keys row, shipped ini, pass-through lint), and
  `ParseCtl` bounds `perf` to 1-60 s; the buffer is reserved before capture so the Present path does not allocate.
- `sync-lua` stages under unique names, sha-checks before and after the move, records in `install.json`, and the test proves
  uninstall stays byte-exact.
- Engine facts carry the run folder; the refused routes point at the fact in `adapter.json` `ctl.routes`.

### For the job chat
Fix item 1 on this branch (and item 4's registry wording if cheap), push, and ask for round 2. Do not merge before
`plan/j4-followups` is on `main`.
