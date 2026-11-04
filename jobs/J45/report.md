# J45 report: Acceptance gate survives a rebase

Branch `job/J45`. Session `5839e2e0-e122-4218-8e4a-0fc4568f566c` (Claude Code on the PC). PC run: `harness/runs/20261031_j45pc/README.md`;
acceptance runs `harness/runs/20261031_j45acc` (failed attempt) and `harness/runs/20261031_j45acc2` (the gate run).

## The build id
- **Definition:** for each DLL input at a revision, its git object id (`git rev-parse <rev>:<path>`), paired with a fixed role name:
  `core` proxy/core, `adapter` proxy/napoleon, `build_sh` proxy/tools/build.sh, `fetch_lua` proxy/tools/fetch_lua.py, `build_id`
  proxy/tools/build_id.py. The id is the first 12 hex of sha256 over the `role oid` lines. `-dirty` is appended when an input differs from
  HEAD. `nogit` outside a checkout. An input that is not tracked raises an error naming it (no fallback to a commit hash).
- **Where:** `proxy/tools/build_id.py`, the one implementation. `build.sh` runs it (host route; `--docker` still gets it from the host
  through `WSP_BUILD_ID`; new `build.sh id` prints it). `tools/pr_policy.py` loads the same file (`dll_build_id`, committed content,
  no `-dirty`); if it cannot, the id is `nogit (<why>)`, which matches no ledger line, so rule 79 refuses and names it.
- **Example, same tree** (this branch's inputs): old formula `bb1adb9ef790` (and `775dfe9b6201` after the reword), new `41cde4716ac7`
  (before and after). Main's DLL under the old formula: `32c0b9a66de1`.
- The input list is the old one plus the id tool itself, as the brief says. The shallow-clone refusal in `build.sh` is gone, and so are
  the `proxy` job's `fetch-depth: 0` and its "full history" step. The `changes` and `policy` jobs keep `fetch-depth: 0`: they need
  merge bases.
- **History:** old ledger lines and `harness/acceptance/baseline.json` (`dc95ededfbe8`) keep their old ids. Neither `baseline_problems` nor
  rule 79 compares the baseline's id with the branch's (the baseline's `build_id` is only required to be present), so nothing needed to
  change. A pass counts only when its id equals the branch's new-format id, so no old line can count for a new branch.

## The tests and their failing fixtures
- `tests/test_build_id.py` (throwaway repos with the real `build_id.py` and `build.sh`): an amended commit keeps the id while the old formula
  moves; a branch rebased over a moved `main` (and a later report commit) keeps it; a change to each input changes it; an uncommitted
  input change gives `-dirty` (a non-input change does not); a `--depth 1` clone gives the same id as the full one; an untracked input is
  refused (and `pr_policy` gets `nogit (...)`); role names, not paths, are hashed; `build.sh id` equals `pr_policy.dll_build_id` equals
  `build_id`; neither file computes an id of its own.
- `tests/test_pr_policy.py` Rule79: 20 passes and then a reworded commit: passes; 20 passes and then an input change: refused (0
  consecutive).
- `tests/test_ctl.py` PcLaunch: a kit without the pack is refused before any launch call, and the refusal names the rule, the missing
  file, the kit id and the kit's reason; a missing rules file is refused; a kit with the pack launches as before.
- `tests/test_pc_deploy.py`: a kit whose sky step fails records `fixed_sky: {present: false, reason}` and carries it into `install.json`;
  a kit with the pack records `present`, its path and sha256.
- `tests/test_acceptance.py` RunPreflight (from the failed first attempt, below): a missing Pillow and a missing branch are refused before
  pass 1; the branch defaults to the checkout's.
- `python3 core/wsc.py gates`: 11 ok, 1 warn (the `hooks` warning: this worktree's `core.hooksPath` is the absolute path), 0 failed,
  348 host tests, including the Docker proxy build and its host tests (before the preflight commit; `test_acceptance` and
  `test_pr_policy` rerun after it).

## The fixed-sky guard
- `pc_deploy.py kit` writes `fixed_sky` into the manifest: `{"present": true, "path", "sha256"}` or `{"present": false, "reason"}` (no dev
  side, or the pack's builder failed). `install` copies it into `install.json`. The warning print stays for non-PC kits.
- `ctl.py` `Pc.launch` calls `file_rule_problems` first: when the launch keys set `dev.file_rules`, the rules file and every `add` rule's
  source must be in the installed kit's files and on disk. Otherwise it raises `Refused` (the verb answers `refused`, exit 2) before the
  VirtualStore move, the key edit and the launch job. On the PC (step a):
  `launch refused: rule "add data\zz_napoleon_remastered_fixed_sky.pack -> napoleon_remastered\packs\zz_napoleon_remastered_fixed_sky.pack"
  in napoleon_remastered\lua\fixed_sky_rules.txt: napoleon_remastered\packs\zz_napoleon_remastered_fixed_sky.pack is not in kit
  kit_20261031T115322Z_40377bbdba78 (the kit says: no fixed-sky pack, J45 step a: the game packs are treated as unreadable (a CI kit)):
  rebuild the kit where the pack builds (the PC)`
- An absolute `dev.file_rules` path (a developer's own file) is only checked for existence; its `add` sources are still checked against
  the kit.

## The PC run
Details: `harness/runs/20261031_j45pc/README.md`.
- a) The kit without the pack (`kit_20261031T115322Z_40377bbdba78`) was refused at launch; game `not_running`, no lock afterwards.
- b) Run `20261031_j45acc2`: 20 of 20 passes on build `41cde4716ac7`, watcher 1.1.0, kit `kit_20261031T115513Z_40377bbdba78`, branch
  `job/J45`, 11:57 to 13:18 UTC, **ledger lines 47 to 66**. Line 46 is the failed first attempt `20261031_j45acc`.
- c) Commit `bb1adb9` reworded (content unchanged; it is `775dfe9` now), pushed with `--force-with-lease`: `pr_policy.py` gives no rule
  79 error (rule 79 is active on main), `acceptance.py streak` still 20, `build_id.py` still `41cde4716ac7`. The incident J44 had,
  now passing.
- d) Uninstall: the game folder is identical to the pre-install snapshot (1564 files), the exe is vanilla, `save_games` is untouched
  (newest 2026-10-29) and the settings files were identical after every pass.

## What J12 can rely on
- A reword, rebase, cherry-pick, squash or `main` merge keeps the 20 passes **when the DLL inputs' content is unchanged** (proxy/core,
  proxy/napoleon, build.sh, fetch_lua.py, build_id.py) and the watcher version is the same.
- A change to any DLL input, whether made on the branch or brought in from `main`, gives a new id, and the branch needs a new 20-pass
  run. So does a new watcher version. `harness/` changes outside the watcher version do not change the id (rule 79 still requires the
  passes to be run for the branch being judged).
- J12 changes `headless.cpp` (proxy/core), so it needs a new run anyway. It can merge or rebase `main` along the way, but only the run
  after its last input change counts. The cheapest order is to merge `main` in first and run last.
- `CLAUDE.md` "Jobs" says this once. The "rebase on `main` before the pull request" lines live only in past briefs, which are records
  and stay as they are.

## Deviations
- **A third fix:** `acceptance.py run` now checks Pillow and the branch before pass 1 (`run_problems`, with tests). It defaults `--branch`
  to the checkout's branch. Not in the brief, but my first attempt spent a ledger line on exactly these two (wrong interpreter, no
  `--branch`), and "a learning becomes code first". It landed before the gate run, so the 20 passes cover it.
- **J18's kit was uninstalled** before the run, so the PC started from the vanilla snapshot. It was not reinstalled, so the PC is left
  with no kit.
- **The first attempt's line stays in the ledger** (line 46, failed, no branch), as J44's failed attempts did.
- The id tool's own file is a DLL input (the brief allowed it), so any edit to `build_id.py` is a new id.

## Open questions
- `python` on this PC's PATH is Python 3.14 without Pillow; `python3` is 3.15 with it. `wsc setup` could check that the interpreter
  agents use for `acceptance.py` has Pillow. The preflight now catches it either way.
- The `hooks` gate warns that this worktree's `core.hooksPath` is an absolute path rather than `core/.githooks`. That is a setup
  detail of `.claude/worktrees`, not this job.
- The kit id (`kit_<utc>_<HEAD short>`) still names HEAD at kit time, as before; only the DLL's id changed. Nothing compares it.
