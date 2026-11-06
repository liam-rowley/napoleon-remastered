# J78: Pin bump to the core's audit train 1

Phase 1 pipeline job, one `needs_pc` job. Audit 2026-11-03 carries P1, P2, C1, C3, C4, H2, H4, H5 and H10 to napoleon through one core pin bump. The row was
written for the first tag with W22, W23, W24, W9, W10, W25, W30 and W33; J64 has since pinned v0.30.0, and this brief is brought up to date for the
**newest core tag when the build starts** (v0.44.0 on 2026-11-06; W41 and W45 may add more: `git -C core fetch --tags`, take the newest, say which in the report).
That is about 14 versions past the pin, with DLL input changes in them (W24, W33, W35, W39) and a moved CI template (W23, W42), so this is **not** a small bump.
The bump also brings W39 (J16 waits on it), W42 faster CI, W43 row files and W44 `wsc audit`, and it carries the opt-in to decisions as one file per row,
which is urgent: `docs/DECISIONS.md` is within about 150 bytes of the `doc_size` cap (30 KB, `wsc.toml` `[docs] max_kb`), and the next decision row may not fit.

**Carries 20 passes (rule 79).** The core's `proxy/` and `harness/` change between the pins and the build id moves, so the final DLL build id and watcher
version need 20 consecutive acceptance passes (`docs/REVIEW.md` rule 79, `wsc.toml` gates via `tools/gates/pipeline.py`). `needs_pc: true`. The same
run covers the Lua changes (deliverable 4), which are DLL inputs too, and J89's, which rides this run: say in the report whether J89 was folded in.

Model: Opus, reason: a DLL-input pin bump across 14 core versions with a crash fact to re-test (D15, D52: DLL and crashes). The row says sonnet and is
corrected to opus by this brief (`wsc reg set jobs J78 model=opus`). Budget about 260 tool calls (J64, which crossed 8 versions on Sonnet, was briefed at 170 and its
re-scope and PC retries needed two further sessions; median plus a quarter for 14 versions and a decisions migration). The budget is not to be lifted in prose.
At most 2 subagents, only for independent host work, never for the PC run (D59: at most 4 sessions at once, a PC job counts as one, finished ones stopped).

## Start
- If this session's model is not Opus, stop and say so.
- `CLAUDE.md` (Jobs: branch `job/J78`); `docs/DECISIONS.md` (D2, D15, D52, D56, D59, D62); `docs/audits/AUDIT_2026-11-03.md` (the P, C, H and R rows named above);
  `docs/REVIEW.md` rule 79; **the reports of J64** (`jobs/J64/report.md`: its Deviations and Open questions are the state of the world, and its re-run recipe
  under Open questions 7 is the model for the PC part), J75 and J73 (the rule 79 reads in `tools/gates/pipeline.py`).
- `git fetch --tags` in `core/`, then `python3 core/wsc.py core bump vX.Y.Z` (from 0.36.0 on this is one commit of `core`, `wsc.toml` and the workflows, B9; a bump
  across it still needs the hand steps below). Read **every `docs/UPGRADING.md` section between v0.30.0 and the target** in a `warscape-core` clone beside this repo
  (`../warscape-core`, read only) and the core's `docs/CONSUMING.md` "Upgrading and releasing". What each one forces is under Target facts.
- Check each Target fact again before relying on it; record anything you prove as a registry row with its date and run id.

## Target facts
Read on 2026-11-06 from the core's `docs/UPGRADING.md`; check each again against the target tag.
- **0.24.0 commit-msg hook, `run_refs` gate (C23, W12).** Opt in: `[policy] commit_msg_hook = true` (the row asks for it). `run_refs_since` is already set by J64; leave it.
- **0.26.0 base-judged policy (W23, C24).** J64 did the steps (`pull_request_target`, the bootstrap `pull_request` trigger limited to `jobs/<id>/report.md`, extra steps from `env:`,
  the gate module reading the head by sha). **Check them again; do not assume.** This bump's own pull request is judged with `main`'s rules, so remove J64's bootstrap `pull_request` trigger
  from `ci/policy.yml.in` in this bump's first template change (`ci_render` warns until it is gone) and re-render.
- **0.27.0 build id (W24).** J64 did the toolchain apt step; check it still holds.
- **W36 (`[policy] bases`, `workflow_paths`).** Defaults apply; this job changes CI files, so **this brief names each**: `ci/gates.yml.in`, `.github/workflows/gates.yml`,
  `ci/policy.yml.in`, `.github/workflows/policy.yml`. A changed workflow path the brief does not name is a policy warning.
- **0.33.0 (W25, W10).** `pc_deploy` takes the lock through `job.sh`; watcher 1.5.0 and `exe_check` as a start-time setting. The watcher is **updated on the PC by Liam or the
  watcher's `update` job** (J64 open question 4: `watch.cmd` is not replaced by `update`; re-run `Install watcher.cmd` from the kit). Name the watcher version in the ledger.
- **0.34.0 DLL changes (W33, C29).** Add `proxy.file_rules` to `registries/config_keys` (text for the host tests: the core's null-game list; `gen_tables.py`).
  `dev.file_rules` stays for dev launches; a release that shipped file rules moves them to `proxy.file_rules` (J74 lists `dev.file_rules` as an allowed dev key, D46:
  update that allowance and its test). Dev threads now start at the first `Direct3DCreate9`, not DllMain.
- **0.36.0 gates (W28, C31).** Bump to 0.36.0 passes `[gates] skip` with `"<gate>:<decision id>"` only (none is set today); `verified_dates` rejects loose dates, `json` rejects
  duplicate keys, `doc_paths` fails on backticked paths missing from the repo (56 misses on napoleon on 2026-11-04: **count again**; fix in this branch or skip the gate
  under a decision row, recommended: fix, a skip needs its own row and `doc_size` is tight). `gen_tables.py` loads the game's whole `wsc.toml` with the new core.
  `gen_tables.py --exe` (W34) is new and cheap: run it on a staged copy of the exe and record the result (D2: never on the installed one).
- **0.38.0 crash maps (W35, C35).** A new build id again. Napoleon has no game verbs named `crash`, `agent-settings` or `audit` (`tools/verbs` holds hotkeys, setup, uiscale,
  upscale: check again). Add `{{wsc proxy_map step=dll}}` after the proxy build step (id `dll`) in `ci/gates.yml.in`, `wsc ci render`, attach `d3d9.map` and `d3d9.map.json`
  to each release, set `[agent_settings] safe` (`exact_only = true`).
- **0.40.0 (W39).** New key `proxy.dxvk_wndproc_fix` (bool, JSON `true`, owner `proxy`): add its `config_keys` row, then `gen_tables.py`. New DLL input. The proof is in-game: change the
  resolution with the key on and read `backend: wndproc guard on DXVK's imports: <n> slots`. That sitting is **J16's** (it waits on this bump); here, record that the log line
  appears in the acceptance launches (it proves the guard loads, nothing more). New tool `dump_read.py`: retire the game's own `tools` row if a copy exists.
- **W42 (faster CI), W43 (row files, `later` rows), W44 (`wsc audit`).** The UPGRADING notes say nothing is forced for W43 and W44. For W42 read the core's W42 report: Windows gates
  skip docs-only changes, the job limit is 20 minutes, the fetch cache key is narrower. `wsc ci render`, then confirm in the first pull request that a skipped `harness-windows` still
  counts as passed for the required checks (`wsc ci check-settings`).
- **Rule 79 inputs.** `python3 core/proxy/tools/build_id.py` names the DLL build; the ledger line names it and the watcher version. Pass 1's build id comes from the previous
  launch's log until W9's flake rule and preflight are in the pin: run 21 passes after a new DLL if the target still lacks it (J64 open question 3; check the target's docs).
- **Fact `napoleon.proxy.init_heap_corruption`** (c0000374 about 150 ms after process start, open since 2026-10-31). Read its row and J67's and J64's counts.

## Decisions already made for this job
- **Target:** the newest tag when the build starts; not a tag chosen to avoid a change. A newer tag appearing mid-job is **not** taken (new run, new budget): report it.
- **Decisions as one file per row: opted in after the bump, never in it.** The core's `docs/CONSUMING_OPTIONS.md` "Decisions as one file per row" moves in **two pull
  requests after this bump merges**, because a pull request is judged with its base's rules and the old rules refuse a head with registry decisions. This job does not do them
  (a `wsc.toml` change is `meta/` only and carries the policy keys): it **prepares** them. Deliverable 6 writes the recipe into the report. Branch kinds, for Liam:
  1. a `meta/decisions-registry` branch (Liam merges, D50): `wsc reg migrate decisions --from-md docs/DECISIONS.md` and `--check`, `wsc.toml`
     `[registries] decisions = "core:decisions"`, `[storage] dir = [..., "decisions"]`, `[policy] decisions = "registry:decisions"`, `decisions_retired = "docs/DECISIONS.md"`,
     and `"registries/decisions/*"` added to the `plan` and `meta` globs. Every row line of the Markdown file stays; its prose may change. From this merge `policy` refuses any
     change to the file's table on every branch: a branch cut before it cannot land a row (merge `main` first);
  2. a second `meta/` branch: delete `docs/DECISIONS.md` and the `decisions_retired` key.
  Old rows keep their numbers (D1 to the last); a new id is `D<yymmdd>-<4 hex>` from `wsc reg add decisions --mint who=... decision=... reversible=yes|no`.
  `CLAUDE.md`, `README.md` and the gates that name the file change in step 2 (grep for the old claim; one owner per topic).
- **If a decision must land before then:** a row is about 100 bytes in the table's shape (`| D66 | 2026-11-06 | Liam | text | yes |`). Keep it terse and under the cap (a `plan/` branch
  writes it; the cap is a hard CI failure). If it cannot fit, do not edit old rows (append only), and do not raise `max_kb`: say so in the report and put the full text in the plan
  doc that owns the topic with the row as a pointer. A skip `"doc_size:<id>"` needs a decision row first, so it is a `meta/` change of Liam's, last resort.
- **Rule 79 and history edits (J45):** a reword, rebase or merge of `main` after the 20 passes keeps them while the DLL inputs are unchanged; if `main` brings in a DLL-input
  change, the branch needs a new run.
- **Re-run against the latest `main` before every merge.** J64's traps, and a newer one: (1) the proxy CI job fetches Lua from lua.org and **times out on a cold cache**
  (`netfetch.retry` retries; a cold toolchain image also hit the 600 s tests cap once): re-run the job once, say so, never edit the cap; (2) a passing branch goes **stale against
  `main`** before the merge (J64 merged `main` twice, renumbering D rows when D57 to D59 landed): merge `origin/main`, re-check `git diff --stat HEAD...origin/main -- core proxy
  viewer/pins.json` (output there is a DLL input: stop and report, new run), re-run `gates` **on the merged head**; (3) core PR #135 passed alone and turned core `main`
  red when W44 merged first, so a green branch is not proof: re-run CI against the latest `main` after the last merge, and before the reviewer queues the merge.
- Opt in to W12's commit-msg hook (`[policy] commit_msg_hook = true`, `git config core.hooksPath core/.githooks` per clone); from this bump on `policy` judges with the base's rules (W23).

## Deliverables
1. **The bump.** `wsc core bump <tag>` (or the hand steps for 0.36.0), one pin commit (B9); then every forced step in Target facts, each its own commit with the tag section it answers
   in the message. Delete each verb the notes name (none expected). `wsc ci render`; `wsc gates` green; `wsc ci check-settings` run and its output in the report (row text).
2. **Config rows.** `proxy.file_rules` and `proxy.dxvk_wndproc_fix` (and any key a later tag added: the host tests name a missing one), then `gen_tables.py`; the player ini and
   `release/napoleon/release.json` decisions for each stated (J64 left `controls.gestures` out of the player ini as inert: same reasoning, shown).
3. **Gates and docs.** Clear or skip-with-a-decision the `doc_paths` misses; `verified_dates`; `json` duplicate keys; `[agent_settings] safe`; `[docs] path_ignore` if needed.
4. **R4's two Lua items.** The J9 probes move into `proxy/napoleon/lua/probes/` (J9-L3, J89 asks for the generated `probe_safe_list.lua` with a `--check` and the `getters.lua`
   `dofile(nil)` refusal: **in scope if the budget holds after the bump, else say what is left for J89**); J46's dead loop at `autostart.lua:139` is removed. DLL inputs: they belong
   to the build id the 20 passes name, so they land **before** the run, never after it.
5. **Heap corruption fact.** With W33 the dev threads start off DllMain: read `napoleon.proxy.init_heap_corruption`, then record in the fact's notes (date, run id) **how many
   start-up exits the 20-pass run retried** (the harness logs "retried N start-up exits"; count them per pass) and the display layout of the run. That is a count on the passes
   you run anyway: **no launches for it and no investigation**; the cause is J101's. Say whether the rate looks lower than J64's (7 on 2026-11-04) and J67's (6 of 18), and that
   it does not prove the fix: one display layout, a small sample.
6. **The decisions recipe.** In the report, a section "Decisions as one file per row" with the two `meta/` branches above, their commands and what each change judges, and the byte
   count of `docs/DECISIONS.md` at the end of this job against the cap. Do not open the branches.
7. **The 20 passes.** See PC test. Ledger lines and evidence files on the branch, a README in the run folder whose paths exist (`run_refs`).
8. **Report** (`jobs/J78/report.md`) with the headings in Finish and, under Deviations, **every `failed` ctl result in a cited run**.

## PC test
Rule 79's 20 passes, on the PC, one job at a time. **The PC is in use by J32 when this brief is written; the 20-pass run waits its turn** and must not start while a watcher job runs.
Preflight, in order, each result in the report:
1. `python3 core/proxy/tools/pc_deploy.py status`: the exe is the vanilla build (D2), no foreign files, nothing installed from another job. `bash core/harness/job.sh status`: the
   watcher version the target needs (update it first: see Target facts), `not_running`, no `game.lock`. The game is launched and killed **only through `job.sh`**.
2. **Quiet PC.** Ask whoever started you that nothing else runs for the whole run: no other sessions, no Docker work, J32 and J101 not running. Wait 5 minutes after an install.
3. **Display layout (changed 2026-11-05).** Windows lists the MSI as the primary display at 0,0 even while it is on another input, with the virtual display at 3839,2160. A
   foreign-window observer therefore needs `-X 3839 -Y 2160` (J64's `harness/runs/20261104_j64pc5/foreign_windows.ps1`, rect `-X -Y -W -H`). If that display drops off mid-run, the headless guard
   refuses with **exit 2160**: that is a flake, not a failure of the DLL; stop at the first such stop, keep the evidence, report it and say the layout. Anything else on the display:
   stop and ask Liam to move it, never move a window yourself.
4. Build `bash core/proxy/tools/build.sh --docker all` (retry once on a network fetch error); `build_id.py` names the id; `pc_deploy.py kit --what proxy`, `send`, `install`; then
   `python3 core/harness/acceptance.py run --passes 21 --run <date>_j78pc --owner j78 --session <session id>`, headless only, `dev.skip_intro` from the adapter. Same tolerance
   and baseline: never edit `harness/acceptance/baseline.json` or a limit (D56 prices a baseline edit at a 20-pass run). Pass 1 is the label pass: passes 2 to 21 are the 20 that count,
   unless the target's W9 flake rule says otherwise. Each pass about 7 to 8 minutes; keep the machine idle. Monitor on the run's output for `FAIL|stopped|Traceback|refused|exit=`.
5. First failure: stop, keep the evidence, no retry, except the tool's own `hist_nile` relaunch and a start-up exit the harness retries (count those: deliverable 5). `pc_deploy.py uninstall`,
   then `status` must say vanilla. Row `blocked` with the reason. Look at the shots and say so in the report.

## Out of scope
- The decisions migration itself (two `meta/` pull requests after this merges), `[policy] plan` narrowing (**J103**, `plan/ narrowed rules`; it waits for this bump because it needs the
  base-judged policy), J88's opt-ins (W27 review rules, W28 skip warnings, W31's `Usage:` rule: J87 wires the reader), J104's keys (`[jobs] max_sessions`, `[audit]`, `decide/` in the hook), the
  W41 and W45 keys beyond what the target tag forces.
- **J101 (start-up crash c0000374):** measuring rates by layout and DLL, dumps and the cause. This job only counts retried exits (deliverable 5) and does not touch the fact's `state`.
- J16's resolution-change proof, J89's work beyond what deliverable 4 says, any edit inside `core/` (a core need is a warscape-core W row), anything in `empire-remastered`.

## Open questions
1. **J88 after this bump.** J88's row (the process train: W26 to W35) is covered by this bump to the newest tag, so its only work left is the opt-ins. Recommended: Liam shrinks J88 to
   the opt-ins and keeps J104 after it; default after: 2026-11-10 (a plan/ row edit, not made here). Tag: taste.
2. **J89 folded in.** Recommended: do J89's three items here (one run covers them) if the budget holds at deliverable 4; otherwise leave them to J89, which rides this run's ledger. Default after: at pickup.
3. **Who runs the PC part.** Recommended: this session builds and runs the passes with Liam present for the watcher update (J64 open question 4); no other PC job runs meanwhile. Tag: risk.
4. **`doc_paths` misses:** fix in this branch (recommended) or skip under a decision row. Default after: at pickup. A skip needs a row and `doc_size` is tight: do not skip.
5. **Does the display layout need pinning?** Recommended: record it, do not pin it (J101 decides whether the MSI should stay on during PC jobs). Tag: risk.

## Kill criteria
- `core/` shows a local edit, or `wsc setup` says the core pin is not clean: stop and report.
- `python3 core/proxy/tools/build_id.py` after the last DLL-input commit differs from the id named in the ledger: stop, new run, report which input moved.
- `git diff --stat HEAD...origin/main -- core proxy viewer/pins.json` is not empty at a merge: stop and report (a DLL input; new run).
- The first failed acceptance pass, a `FAIL`, a crash, a hang or a refused launch other than exit 2160 (reported as a flake with the layout): stop, keep the run folder, report, no retry.
- `wsc gates` fails on a gate the notes say the bump forces and the fix is not in Target facts after 3 attempts: stop, report the gate and what was tried.
- Over about 260 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J78/report.md` with `## What was built` (target tag and what each UPGRADING section forced), `## Evidence` (run ids, build id, watcher version, the retried start-up exits per pass,
the display layout, CI run ids, `ci check-settings` output, the `DECISIONS.md` byte count), `## Deviations from the brief and why`, `## Open questions`, then `wsc jobs usage J78 --write`
where it applies. Then `wsc reg set jobs J78 status=review report=jobs/J78/report.md`. Never mark `done`, never merge, never `--no-verify`.

## Registry gaps
- path: harness/runs/20261104_j64pc5/foreign_windows.ps1; owner: J78; reason: a run-folder script of J64's, cited as the observer to reuse; promote it to a tool row if J78 reuses it.
