# Review of J44 (Scenario library and the 20-pass acceptance gate)

## Round 1 (2026-10-30, branch `job/J44` at c60c9af)

Reviewer: session `784213b1-ee70-4c06-8166-214f7cb242b4` (did not build the branch; builder `c641471b-06b1-4ab6-b2d5-27cc7b580b23`).

**Verdict: merge.**

The phase 1 gate holds up on the evidence. All 24 ledger lines name a run and a committed pass file. The last 20 are run
`20261030_j44acc3`, all `passed: true` with no failed step, and `acceptance.py streak --build dc95ededfbe8 --watcher 1.0.1` gives 20.
The DLL build id the passes ran on (`dc95ededfbe8`) differs from the branch's final id (`e1ebe9a561a6`) only because of the trailer
reword. `git diff dc95ededfbe8 HEAD -- proxy/core proxy/napoleon proxy/tools/build.sh proxy/tools/fetch_lua.py` is empty. Nothing
under `harness/` or `proxy/` changed after the gate commit `b0d37c6`, apart from the ledger. The main merge `8d03a16` brought in
briefs and job rows only. The baseline is measured (`acceptance.py measure`), and the `acceptance_active` and ledger-evidence fixes
are in, each with a failing fixture. Rule 79 is not active for this branch, because `main` has no baseline yet.

### Machines
- `python3 core/wsc.py gates`: 12 ok, 0 warn, 0 failed (292 host tests).
- `python3 tools/pr_policy.py --branch job/J44 --base origin/main`: before this review it refused only for the missing review and
  the J44 row's status.

### Risk-first reading
I picked these because a mistake in them costs the most:
- `tools/pr_policy.py` rule 79. It now governs every later proxy/harness merge.
- `harness/core/ctl.py` `Pc.launch` and `clear_virtualstore`. They write on the PC, under `%LOCALAPPDATA%\VirtualStore`.
- `harness/core/acceptance.py` `run_pass` and `PcEnv.settings`, for settings integrity.
- `proxy/core/dev.cpp` and `devcore.h` `PerfDeltaMs`, the DLL change.

What I found:
- The VirtualStore code moves files to `<state>/_to_delete` and never deletes. A cross-volume move raises and the launch fails
  closed.
- The settings are compared after `release()` has waited for the watcher's restore, as claimed.
- The exec of the base's `acceptance.py` is safe: the module imports only the standard library. A branch therefore cannot reach its
  own code through it.
- `PerfDeltaMs` is correct, and the reserve ×4 covers frame rates up to 4000 fps.

### Findings

**should-fix (fixed on the branch)**
1. `tools/pr_policy.py:141` (rule 79 streak). The streak did not check which branch a pass was run for. `harness/` is not in the
   build id (only the DLL inputs and the watcher version are), so a passing branch's 20 passes become a free pass for the next one.
   Picture branch X changing `harness/core/ctl.py`, running its 20 passes and merging. Branch Y then changes only
   `harness/core/acceptance.py`. Y has the same build id and watcher, the ledger tail is X's 20 committed passes, and rule 79 lets
   Y through with no run of its own.
   Fixed in commit "J44 review: rule 79 counts only passes run for the branch being judged": a line whose `branch` is not the judged
   branch ends the streak. The ledger already writes `branch` (`acceptance.py:135`).
   Test: `test_pr_policy.Rule79.test_failing_fixture_another_branchs_passes_do_not_count`, which uses a ledger of 20 passes from
   `job/J8` and lines with no branch.

**should-fix (follow-up job, not this branch)**
2. `proxy/tools/build.sh:27` and `tools/pr_policy.py:232`. The build id is the *commit hash* of the last change to the DLL inputs,
   so any reword, rebase or cherry-pick after the gate run invalidates the 20 passes even when the code is identical. That is exactly
   J44's incident. The briefs still tell branches to "rebase on `main` before the pull request" (J44's own brief, and the template
   the J4/J43 briefs use). A proxy branch that runs its 20 passes and then rebases will be refused by rule 79 and has to spend another
   ~80 minutes of PC time.
   - How to see it fail: `git commit --amend` any commit that touches `proxy/core`, then `git log -1 --format=%h -- proxy/core`
     shows a new id over the same tree.
   - Fix: derive the id from the inputs' tree hashes (for example `git rev-parse HEAD:proxy/core` and the others, hashed together)
     in both `build.sh` and `pr_policy.py`, with a test that a reword keeps the id.
   - This needs a `needs_brief` row on a `plan/` branch: it changes the DLL's embedded id and the ledger's meaning.
   - Until then, briefs for proxy/harness jobs should say: merge `main` in, never rebase, after the acceptance run.

**later**
3. `proxy/tools/pc_deploy.py:65-71`. When `build_fixed_sky_pack` fails, the kit is built without the sky pack and only prints a
   warning. `ctl.launch.keys` still points `dev.file_rules` at `fixed_sky_rules.txt`, which adds a pack that is not there. The first
   sign is then a `shot_match` failure on land (diff 9.6 to 11 against threshold 4), which looks like a lighting regression rather
   than a missing file.
   Guard: record `fixed_sky: absent` in the kit manifest and have `ctl.py` `Pc.launch` refuse when an `add` rule's source is not
   installed.
4. `jobs/J44/report.md`, "The 20 passes". The report says "ledger lines 4 to 23", but the passes are lines 5 to 24: lines 1 to 4
   are the two failed attempts.
5. Deliverable 2 gaps: land large, land 20 against 20, naval large, siege city, and campaign mid and late are not built, and
   `naval_storm` has no load time or poses. The report names each gap and its cause (`napoleon.custom_battle.armies` open; the
   custom siege list has no city; the recipes are not wired into `scene`). The cause for the land and naval large battles belongs to
   J28, and the campaign rows to whoever wires `load_save.sh` into `scene`. It is accepted as a stated deviation; J8 and J23 should
   not assume these rows exist.
6. The commit hook in `.claude/settings.json` only runs when the Claude Code session is started in the repo folder. This review
   session was started one level up (`repos/`) and its first commit went through without a trailer; I fixed that with `--amend`
   before the push. `pr_policy.py` still catches a missing trailer, so it is not a hole, but the hook alone does not stop it. A
   `commit-msg` git hook in `core/.githooks` would make it hold in every session. That is a core change: J12, or the warscape-core
   backlog.

### Effect on other branches
Merging this puts `baseline.json` and the ledger on `main`, so **rule 79 switches on**. Every later `job/` branch that changes
`proxy/` or `harness/` (not their runs, READMEs or acceptance files) needs 20 consecutive passes of its own. That means J16 and J18,
both queued; J22 if it touches `harness/`; and J8, J23 and J28 when they come. Each pass run costs about 80 minutes of watcher time,
and after finding 1 it counts only for the branch that ran it. Until finding 2 is fixed, those branches must not rebase after their
run.
