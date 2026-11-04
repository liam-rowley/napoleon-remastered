# J12: Promote phase 1 core candidates to warscape-core

Phase 1, the promotion job (PLAN section 4, rules ledger row 76). The game-agnostic code built in phase 1 under `*/core/` moves to
`liam-rowley/warscape-core` and comes back as core v0.4.0. Napoleon keeps only its adapters. Before the move, this job fixes the open
review items that only a core consumer would hit, and proves them on the PC. The move itself changes nothing the game runs: the same
DLL, byte for byte, and the same watcher. Merging this job closes phase 1. J30, J38, J8 and J9 depend on it and cite core paths.

Model: Opus, reason: DLL fixes in the headless guard and a cross-repo move of the proxy, harness and build. Budget about 350 tool
calls; at the cap, stop, commit, push both repos, report what is left. At most 2 subagents, only for independent reading or the
core-side CI work. Waiting belongs to the harness: `acceptance.py run` and `job.sh` block inside one call. Never poll CI or a merge.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J12`). Read `docs/DECISIONS.md` (D2, D10, D15, D18, D29, D30-D33) and `docs/plans/PLAN.md`
  section 4.
- Read the core side: `core/CLAUDE.md`, `core/docs/CONSUMING.md` (upgrade steps), `core/docs/DECISIONS.md` (C1, C2, C8, C10) and
  `core/docs/BACKLOG.md` (B1, B9, B11, B12). Core changes are made in a `warscape-core` clone beside this one
  (`/c/Users/liamr/repos/warscape-core`, `git pull` first), on the branch `napoleon-j12`. Never edit inside `core/` here.
- Each phase 1 report has a "moves to the core" section. Read them, with the reviews they cite:
  - `jobs/J1/report.md` "What moves to warscape-core"
  - `jobs/J2/report.md` "What moves to the core later" and question 4; `jobs/J2/review.md` L1-L5 and L7
  - `jobs/J3/report.md` "What moves to the core in J12"; `jobs/J3/review.md` item 5
  - `jobs/J4/report.md` (ctl, acceptance, sync-lua)
  - `jobs/J13/report.md` "What moves to the core in J12" and question 1; `jobs/J13/review.md` "Should-fix" 1 and 2
  - `jobs/J15/review.md` item 9
  - `jobs/J44/report.md` (the J12 line)
  - `jobs/J45/report.md` (rule 79 and history edits)
  - `jobs/J41/report.md` question 1
  - `jobs/J14/review.md` (ESF tools)
- The row's description in `registries/jobs.jsonl` is the scope list. This brief orders that list and adds the decisions.
- Search before writing: `python3 core/wsc.py find core candidate adapter build id watcher kit`.
- **Other branches on the same files.** Check `git branch -r` at the start and again just before the move:
  - J22 (Windows host tests find Git Bash) changes `harness/core/{acceptance.py,ctl.py,shot.sh}` and `pc_deploy.py`. J12 depends
    on it, so merge `main` after J22 lands.
  - J16 (`job/J16`) changes `proxy/core` and is blocked on a visible PC sitting. If it is still open at the move, do not carry its
    changes. Name it in the report: once J12 merges, J16's `proxy/core` change becomes a warscape-core PR plus a pin bump.
  - J47 (VirtualStore) and J48 (watcher) have no branch yet. Their briefs will cite core paths.

## Decisions already made for this job
- **Scope: the phase 1 candidates only.** These move:
  - `proxy/core/*` and the game-agnostic `proxy/tests/*`
  - the generic proxy tools: `build.sh` with `repro` and `--disable-auto-image-base`, `build_id.py`, `gen_tables.py`,
    `fetch_dxvk.py`, `fetch_lua.py`, `pc_deploy.py` with `sync-lua`, `tools/wer/*`, `timeline_table.py`, `survey_table.py`,
    `pack_list.py`, `luac_list.py`
  - `build_dev_pack.py`, with game paths as input
  - the method of `build_fixed_sky_pack.py`. Its tables stay with the game.
  - all of `harness/core/` with its tests
  - `saves/core/` (the ESF tools)

  These stay as Napoleon's adapters: `proxy/napoleon/`, `harness/napoleon/`, `saves/napoleon/`, `exe_info.py`'s defaults, the
  registry contents, the fixed-sky tables and the scenario presets. `discovery/core` waits for the phase 2 promotion (after J11).
  `upscale/core` waits for its own promotion (after J50 and J51).
- **The game repo names its adapters in the core's terms, not by script location.** A core script must not find the game by its own
  path (`$ROOT/harness/napoleon`, `dirname $ROOT/ctl`, a hard-coded game path in `shot.sh`). It reads the game root and the
  adapter paths from the game repo's `wsc.toml`, or from the kit's ini on the PC. Use a `[harness]` and `[proxy]` section, or
  whatever the core's config already allows; check that the core tolerates new sections. If it does not, the extension is part of
  the core PR.
- **The move is a pure relocation.** Every content change happens on `job/J12` before the move:
  - the fixes below
  - the path wiring above
  - the game-name lint (J13's lint for `display_guard.h` and `headless.cpp`, extended to every moved file)

  The move commit then only changes where files live and how the build and the kit find them. In warscape-core the folders keep
  their content: `proxy/core/` becomes `proxy/src/`, then `proxy/tests/`, `proxy/tools/`, `harness/` (from `harness/core/`),
  `harness/tests/` and `saves/`. The `proxy/src` tree must stay byte-identical to the tree Napoleon built from. That keeps the
  git tree id, and so the DLL build id.
- **The build id follows the inputs into the submodule.** `build_id.py` keeps its role names. The `core` role reads the tree id
  through the gitlink: `git -C core rev-parse HEAD:proxy/src`. Any other input that moved is read the same way. A plain
  `git rev-parse HEAD:core/...` does not reach into a submodule.

  Proof that the move is pure:
  - `build.sh id` gives the same id before and after the move.
  - `build.sh repro` gives a byte-identical DLL before and after.
  - the watcher version is unchanged.

  With all three, rule 79's passes still count after the move (J45), so the 20-pass run happens once, before the move. If any DLL
  input or the watcher changes after the run, run again after the last change. Merge `main` in first, then run.
- **Core CI carries what it now owns.** warscape-core gets:
  - a proxy job: build plus host tests, against a minimal null adapter committed in the core for this purpose
  - a Windows job for the harness PowerShell tests
  - host tests for the moved Python tools

  Port the steps from Napoleon's `gates.yml`. Napoleon's CI still builds the real DLL from `core/proxy/src` plus
  `proxy/napoleon`. Its `changes` filter must treat a `core` gitlink change as a proxy and harness input change.
- **C2 and Pillow.** C2 (stdlib only) stays the rule for `warscape/`, the gates and the host tests. The core PR adds a proposed
  `C<n>` line: PC-side harness tools may import Pillow, checked before the first use (`acceptance.py run_problems` already does),
  and never imported by a gate or a host test without a skip. Liam's merge accepts it.
- **Registries.**
  - Core: rows for every moved tool (`wsc reg add tools <path>`, keeping the id with `--id` where the core's convention allows).
  - Napoleon: each moved tool's row is retired with `status=superseded:<core id>`.
  - `config_keys`, `engine_facts`, `engine_sites` and `scenarios` rows stay in Napoleon (PLAN section 4: registry contents are
    per game).
- **Rule 76 becomes code (ledger row 76, "CL").** Add a check to `wsc jobs check` (`tools/verbs/jobs.py`, with a test):
  - every `*/core/` folder in this repo is listed with the job that promotes it (a small table: in `wsc.toml` if the core allows it,
    else in `jobs.py`)
  - a folder whose promotion job is `done` must no longer exist
  - an unlisted `*/core/` folder fails

  Promotion rows that do not exist yet are named as `needs_brief` in the report, not added here.
- **Release and pin.**
  - Core release v0.4.0: `VERSION` says `0.4.0`. v0.3.0 is the J41 tests-gate release; its `VERSION` file still says `0.2.0`, so
    check what `core_pin` makes of that and say so in the report.
  - Napoleon bumps `core`, `wsc.toml` `[core] version` and the deletions of the local copies in one commit (core backlog B9).
  - Then the J41 item: `tests/test_proxy_host.py`'s no-toolchain case becomes a plain skip, and the default failure goes.
- **Liam merges and tags the core** (core `CLAUDE.md`). Open the core PR, ask Liam to merge it and tag v0.4.0, then stop and end
  the turn. Do not wait or poll. Resume when Liam says it is tagged.

## Deliverables
1. **Fixes before the move, each with a host test** (Napoleon, `job/J12`):
   a. J13 should-fix 1, `headless.cpp`: recognise the guard's own relocation by its target rect in `GuardProc`, not by thread id.
      Host test: a present from a worker thread while the virtual display moves.
   b. J13 should-fix 2: re-run the `SweepCb` window sweep from the guard thread every ~250 ms, outside `s_cs`. Host test: a window
      a DLL creates after start-up is hidden.
   c. `shot.sh` takes the game path from the adapter (J15 review 9). `job.sh ctl` reads `dev.ctl_dir` from the adapter or the
      kit ini (J3 review 5).
   d. The `job.sh` lock is an exclusive create (J2 L3).
   e. `update.ps1`: "0 files replaced" is its own outcome with no restart, and the manifest `kit_id` must match the folder
      (J2 L7, J2 question 4).
   f. Watcher script jobs propagate a failing exit code (J13 question 1).
   g. The VirtualStore guard lives in the watcher or launcher, not only in `ctl.py` (J44). Keep it compatible with what J47
      will need.
   h. J2 L1, L2, L4 and L5: decide each (fix, or a reasoned no) and say which in the report.
2. **The path wiring and game-name lint** from the decisions, so that no moved file names Napoleon, its paths or its adapter
   folder.
3. **PC proof, then the 20-pass run**, on the fixed, pre-move code (after merging `main`):
   - 1a: present from a worker thread (a dev key or test hook) and move the virtual display with `vdisplay_probe.ps1 -Origin`.
     The window ends `on_virtual` and uncloaked.
   - 1b: a DLL-created window after start-up is hidden, and the window probe shows zero ms on a real monitor.
   - Each of 1c-1g is exercised once through the watcher.
   - Then `acceptance.py run --passes 20`. Results go in a dated run README under `harness/runs/` and as `engine_facts` rows
     where a fact was learned.
4. **The core PR** (`warscape-core`, branch `napoleon-j12`):
   - the moved files, the null adapter and the CI jobs
   - the config extension, if one is needed
   - the tools rows, the Pillow `C<n>` line and `VERSION` 0.4.0
   - gates and every moved host test green in the core's CI
   - B-items this job makes obsolete removed from the backlog, and new ones it finds added
5. **The Napoleon switch** (after the tag), on `job/J12`:
   - the pin bump and the deletions in one commit
   - `build.sh`, `build_id.py`'s `core` role, `pc_deploy.py kit`, the CI and the tests repointed at `core/`
   - `CLAUDE.md`, `README.md`, `proxy/README.md` and `harness/README.md` fixed wherever they name a moved path (grep every
     living copy)
   - the superseded tools rows
   - the rule 76 check
   - the J41 skip
6. **Proof of a pure move:**
   - `build.sh id` and `build.sh repro` the same before and after the switch (both outputs in the report)
   - `pc_deploy.py kit` from the switched tree has the same file sha256s as the kit the 20 passes ran on
   - `pr_policy.py --branch job/J12 --base origin/main` shows no rule 79 error, and `acceptance.py streak` still gives 20
   - `wsc gates` green in both repos

## Kill criteria
- The DLL built from `core/proxy/src` differs from the pre-move DLL after 2 attempts to find the cause: stop. Report the diff
  (`build.sh repro` output, the build id inputs) and do not run the gate twice.
- The J13 fix 1 or 2 makes any headless launch show a frame on a real monitor (window probe), or the fix still fails after 3 PC
  attempts: stop, revert to the J13 behaviour and report. The move can go ahead without that fix only if Liam says so.
- The acceptance run fails a pass for a reason the fixes did not touch: stop after that pass. Report it with the pass JSON, and do
  not restart the 20 until the cause is understood.
- The core needs a design change beyond a config extension to host the adapters: stop before the move and report the proposal.

## Finish
Write `jobs/J12/report.md`. Cover:
- what moved, as a table of old path and core path, and what stayed
- the core PR and the tag, and the fixes with their run ids
- the 20-pass run, the build ids and the repro output
- the decisions on J2 L1, L2, L4 and L5
- deviations from this brief and why
- open job branches left on old paths (J16) and what each needs
- the promotion rows phase 2 and the upscale work still need
- open questions

Then `wsc reg set jobs J12 status=review report=jobs/J12/report.md`.
