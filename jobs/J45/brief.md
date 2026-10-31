# J45: Acceptance gate survives a rebase

Phase 1. J44's review findings 2 and 3. The DLL build id is the commit hash of the last change to the DLL inputs, so a reword,
rebase or cherry-pick after a 20-pass run gives a new id over identical code, and rule 79 then refuses the branch. J44 lost a whole
run this way. Separately, a kit built without the fixed-sky pack still launches with `dev.file_rules` pointing at that pack, and the
first symptom is a land `shot_match` failure that looks like a lighting regression. Both are fixed in one job so that one 20-pass run
covers both. J12 (the phase 1 promotion to warscape-core) waits on this job: it is a long proxy and harness job that has to merge
`main` in along the way and must not lose its acceptance run to history edits.

Model: Sonnet. Budget about 120 tool calls; at the cap, stop, commit, report what is left. No subagents. Waiting belongs to the
harness: `acceptance.py run` and `job.sh` block inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J45`). Read:
  - `docs/DECISIONS.md` (D2, D15, D30-D32)
  - `jobs/J44/report.md` and `jobs/J44/review.md` (findings 2 and 3), and `jobs/J1/review.md` finding 2 (why the id is not HEAD)
  - `proxy/tools/build.sh` lines 14-29 (the id today, the shallow-clone refusal, `WSP_BUILD_ID` for `--docker`, `repro`)
  - `tools/pr_policy.py` rule 79 (`acceptance_active`, the streak check, and the id at line ~232), `harness/core/acceptance.py`
    (`streak`, `ledger_line`, the baseline), `harness/core/ctl.py` `Pc.build_info` (the id read back from the DLL's load line) and
    `Pc.launch`
  - `proxy/tools/pc_deploy.py` `kit` (the fixed-sky block near line 178) and `proxy/README.md` "Fixed sky"
- Search before writing: `python3 core/wsc.py find build id acceptance ledger fixed sky file_rules`.
- Other jobs touching the same files: J16 (queued: `proxy/core`), J47 (VirtualStore, `ctl.py`), J48 (watcher). Keep the `ctl.py`
  change small and additive.

## Decisions already made for this job
- **The id is a content hash, not a commit hash.** Hash the git object ids of the DLL inputs at HEAD (`git rev-parse HEAD:<path>` for
  each input tree or blob), each paired with a fixed role name, into one 12-hex id. Use role names, not paths, so the id depends only on
  the inputs' content. `-dirty` stays when an input differs from HEAD. A shallow clone then computes the right id, so the shallow
  refusal in `build.sh` can go, along with any CI `fetch-depth: 0` that was only there for the id. Keep the latter if anything else
  needs history.
- **One implementation.** `build.sh` and `pr_policy.py` must not each compute the id in their own way. Put it in one place (for
  example a small `proxy/tools/build_id.py` with a header and a tools row, or `build.sh --print-id`) and have the other call it. Add a
  host test that both give the same id.
- **The DLL input list stays as it is** (`proxy/core`, `proxy/napoleon`, `proxy/tools/build.sh`, `proxy/tools/fetch_lua.py`), plus the
  id tool itself if it is a separate file. Don't widen or narrow what rule 79 covers in this job.
- **History stays as it is.** Old ledger lines and `harness/acceptance/baseline.json` keep their old-format ids as a record. Don't
  rewrite them. If `baseline_problems` or rule 79 compares the baseline's id with the branch's, say in the report how the new format
  is handled.
- **Rebase or merge.** Once the id follows content, a reword or rebase that leaves the inputs' content unchanged keeps the id. If
  `main` brings in changes to the DLL inputs, a new run is needed either way. Say this once, in `CLAUDE.md` "Jobs" (or wherever the
  rule 79 text for job branches lives), and drop "rebase on `main` before the pull request" from that place. Past briefs are records:
  leave them.
- **A missing file rule source is a refused launch.** `pc_deploy.py kit` records the fixed-sky pack in the kit manifest (present with
  sha256, or `absent` with the reason). `ctl.py` `Pc.launch` refuses before launching when a `dev.file_rules` file names an `add`
  source that the installed kit does not have, and gives the rule, the missing file and the kit id. The warning in `pc_deploy.py`
  stays for non-PC kits (CI), where the pack cannot be built.

## Deliverables
1. The content-hash build id in one implementation, used by `build.sh` (host and `--docker` routes) and `pr_policy.py` rule 79.
   `build.sh repro` is still byte-identical.
2. Host tests with failing fixtures:
   - In a throwaway repo, a reworded or amended commit and a rebased branch over the same inputs keep the id.
   - A change to any one input changes the id.
   - An uncommitted input change gives `-dirty`.
   - A shallow clone gives the same id as a full one.
   - `build.sh` and `pr_policy.py` agree.
3. Rule 79 on the new id: `test_pr_policy` cases for a branch whose last commit was reworded after its 20 passes (passes), and for one
   whose inputs changed after them (refused).
4. The fixed-sky guard: the manifest field, the `Pc.launch` refusal and `test_ctl` and `test_pc_deploy` cases (kit without the pack:
   refused with the reason; kit with it: launches as before).
5. The rebase/merge sentence in one place (see Decisions), and any doc that states the old id meaning (`proxy/README.md`, the
   `build.sh` comments, the tools rows) brought up to date.
6. Registries: a `tools` row for any new tool; `config_keys` unchanged unless a key changes.

## PC test
Unattended and headless through the watcher. Kits go over by `pc_deploy.py`, sha-checked.
- a) The guard: a kit built without the fixed-sky pack is refused at launch with the reason; nothing launches.
- b) Rule 79 needs 20 consecutive acceptance passes on this branch's final DLL and watcher:
  `python3 harness/core/acceptance.py run --passes 20 --run <run id>` (about 80 minutes). The ledger lines carry the new-format id.
- c) After the run, reword one commit that touches `proxy/` (no content change), push with `--force-with-lease`, and show that
  `tools/pr_policy.py --branch job/J45 --base origin/main` still says ok and `acceptance.py streak` still gives 20. This is the
  incident J44 had, now passing.
- d) Uninstall is byte-identical; `save_games` and every settings file are as found.
Results go in a dated run report under `harness/runs/` with job ids and the ledger range.

## Kill criteria
- **The id cannot be made content-only for some input** (for example a generated file that is not tracked) after about 20 calls:
  stop, report which input and why, and propose the narrowest fix. Don't fall back to commit hashes silently.
- **The 20-pass run fails twice for the same cause**: stop, read the evidence (`acceptance.py` stops at the first failure), and report.
  If the cause is outside this job's change (J16's crash, J47's VirtualStore), say so and don't fix it here.
- **Any write into the game folder outside a deploy, into `core/`, or into Liam's saves would be needed**: stop and ask Liam.

## Finish
Write `jobs/J45/report.md`. Cover:
- the id: its definition, where it is computed, and an example of an old and a new id for the same tree
- the tests and their failing fixtures
- the fixed-sky guard and its refusal text
- the PC run with run ids and the ledger range, and step c's reword evidence
- what J12 can now rely on: when a move keeps the id and when it needs a new run (J12 also changes `headless.cpp`, so it needs a new
  run anyway)
- deviations from this brief and why
- open questions

Then `wsc reg set jobs J45 status=review report=jobs/J45/report.md`.
