# Later triage, 2026-11-04 (J82)

Audit 2026-11-03 finding R4: the "Later" bullets in `jobs/*/review.md` were the only place many follow-ups lived. This record gives every one of them one fate. It is history once merged: it lists the reviews and never edits them. Built to the brief's defaults for its four open questions (J82 brief, "Open questions"); they are open for Liam, not answered by him.

## Counting rule and totals

Script: `_scratch/count.py` (git-ignored, not committed; its output was extracted to `_scratch/later/<job>.txt`). A **Later block** starts at a line that is a heading `##`, `###` or `####` beginning "Later" (also "Still open (later, ...)"), a bold line beginning `**Later` or `**later` (with or without a parenthesis, a colon or a trailing text), or a list item `- **later:**`. It ends at the next heading or the next bold-only line. **One bullet** is one top-level list item of the block (`-`, `*` or `1.`); nested bullets and continuation lines belong to their parent. A block with no list items counts as one bullet when it holds text, and as none when it says "none" (J6 and J7 "Later (core)"). Bullet ids are `J<n>-L<k>`, numbered through all of one review's blocks in file order.

**Total: 240 bullets in 54 reviews** (all 54 reviews on main have a Later block, so none is listed "none"). The audit counted 135 in 28 and the brief's heading-only scan 139 in 29: those counts read only the `###` Later headings, so they missed the bold-line blocks (about half of the reviews), the "Still open (later ...)" list, the second and third Later blocks of fix-round reviews (J1, J4, J6, J7, J9, J18, J22, J24, J52) and the inline `- **later:**` items. Per review: J1 9, J2 8, J3 5, J4 7, J5 6, J6 3, J7 6, J8 6, J9 7, J10 6, J11 4, J12 6, J13 6, J14 5, J15 5, J17 2, J18 8, J19 3, J20 3, J21 5, J22 5, J23 3, J24 7, J28 5, J30 3, J31 3, J33 4, J34 4, J36 4, J38 4, J39 6, J40 6, J41 5, J42 4, J43 5, J44 4, J45 3, J46 3, J49 4, J50 4, J51 4, J52 4, J53 4, J54 3, J55 4, J56 3, J57 3, J58 2, J62 3, J65 3, J66 4, J70 3, J71 2, J72 2.

## Summary of fates

| Fate | Bullets |
|---|---|
| already done (cited) | 106 |
| dropped (reason cited) | 53 |
| core BACKLOG line (B64 to B84, 19 lines hold the 31 bullets) | 31 |
| needs_brief row (J89 to J98) | 50 |
| **Total** | **240** |

Per destination: core B64 3; core B65 2; core B66 1; core B67 1; core B68 2; core B69 1; core B70 1; core B71 1; core B72 3; core B73 1; core B74 1; core B75 7; core B76 1; core B77 1; core B78 2; core B79 1; core B80 1; core B81 1; row J89 2; row J90 2; row J91 3; row J92 7; row J93 3; row J94 12; row J95 10; row J96 9; row J97 2.

Already done, by owner: the core at v0.22.0 (code that moved to warscape-core and was fixed there; arrives with row J64) and queued rows J59, J63, J64, J67, J68, J69, J73, J74, J75, J76, J77, J78, J83, J85, J87 and the J57 and J62 merges. A few "already done" cells are read from the tree by grep only and say so (the cell names the file and line); the core fixes are cited by file in warscape-core `main` (a6d4872, VERSION 0.22.0), not by commit sha, because napoleon pins v0.10.0 and the core history is not in this clone.

## Plan branch

`plan/later-triage-2026-11-04`, local worktree `nap-plan-later`, commit `8362716`, **not pushed** (D50: only Liam merges `plan/` branches). Ten `needs_brief` rows, ids J89 to J98 (the highest on main and on every open plan/brief branch was J88). `wsc jobs check` (98 rows, ok) and `wsc policy --branch plan/later-triage-2026-11-04 --base origin/main` (ok, 10 files changed) pass there. Each description lists its bullets by review.

| Row | Title | Phase | PC | Bullets |
|---|---|---|---|---|
| J89 | Lua probe follow-ups to J78 and stale proxy comments | 1 | yes | 2 |
| J90 | Console guard for transport_to_hlci and the diplomacy getter pump stall | 1 | yes | 2 |
| J91 | Napoleon harness adapter follow-ups | 1 | yes | 3 |
| J92 | Orders route follow-ups | 4 | yes | 7 |
| J93 | Liam decides: player install on the real folder | 5 | yes | 3 |
| J94 | Napoleon tools, tests and gates: small fixes | 1 | no | 12 |
| J95 | Discovery tools and facts: small fixes | 1 | no | 10 |
| J96 | Upscaler guards, DXT target checks and the uiscale probes | 5 | yes | 9 |
| J97 | Viewer housekeeping | 5 | no | 2 |
| J98 | Start-up soak after every DLL change (Empire learning 3) | 1 | yes | 0 |

J89, J90, J91 and J92 touch `proxy/` or `harness/` inputs and say "carries 20 passes". Rows marked "Liam decides:" in their description hold a scope call (J91 item 1, J93, J96 items 1 to 3), per the brief's default for open question 4. J90 is the only Opus row (crash bisecting, D15).

## Core branch

`plan/backlog-from-napoleon-later` in `warscape-core` (local worktree `wsc-plan-later`, cut from `origin/main` a6d4872, VERSION 0.22.0), commit `39339a8`, **not pushed**: B64 to B84 appended to `docs/BACKLOG.md`. `wsc policy --branch plan/backlog-from-napoleon-later --base origin/main` is ok (1 file changed) and `wsc gates --fast` passes (13 ok). `docs/BACKLOG.md` is 30,606 bytes against the 30 KB (30,720 byte) `doc_size` cap, so the next lines added there need the file split first; the lines were shortened to fit.

| Line | Change | Bullets |
|---|---|---|
| B64 | Capture hardening: the timeout path, unsynchronised globals and state-block hooks | J8-L1, J8-L2, J8-L3 |
| B65 | Headless: an explicit marker constant, and the guard thread's lock hold | J13-L1, J13-L2 |
| B66 | Console chunk files are deleted once `RunLua` returns | J15-L3 |
| B67 | `Test-Lib.ps1` `Invoke-Selected`: runner parameters leak into case bodies | J19-L1 |
| B68 | `wsc jobs check`: the report's `Model:` line against the row, and a brief that names `proxy/` or `harness/` code without an acceptance line | J19-L2, J22-L5 |
| B69 | `build.sh`: the mingw package versions are not pinned | J20-L2 |
| B70 | `ctl.py` `bash()` says when its finder fails | J22-L3 |
| B71 | Host check: every non-stdlib import in `tests/` is guarded or installed by the CI workflow | J24-L1 |
| B72 | `pc_deploy.py` and `ctl.py` small guards: the dev Lua docstring and the `lua` verb's path | J4-L1, J4-L3, J4-L6 |
| B73 | `ctl.py`: a unit that leaves its army during the settle is a structured failure | J28-L1 |
| B74 | Acceptance runner: a free-RAM floor, and `build.sh smoke` for a game without a `GestureAdapter` | J30-L2 |
| B75 | `wsc jobs view --serve` hardening | J39-L2, J39-L3, J39-L4, J39-L5, J39-L6, J52-L3, J56-L2 |
| B76 | `job.sh`: a failed script's exit code is told apart from `refused` | J2-L2 |
| B77 | A missing optional pack is recorded in the kit and refused at launch | J44-L1 |
| B78 | `pc_deploy.py status` names a kit left installed by a finished job; its tests need no live game | J50-L3, J57-L3 |
| B79 | The watcher and `job.sh lock` know a player's `play.json` | J53-L2 |
| B80 | `gen_tables.py` skips `config_keys` owners other than `proxy` | J23-L1 |
| B81 | The watcher holds the game only for the start and kill, not the whole job | J2-L4 |
| B83 | `%~dp0` in a watcher cmd job body is the `jobs` folder | Empire learning 1 (no bullet) |
| B84 | A host lint: no helper function named like a PowerShell alias | Empire learning 2 (no bullet) |

## Housekeeping (step 5, on `job/J82`, commit `0d8e053`)

- **a. `summary.json`.** `tools/perf_baseline.py:503` writes it into each run folder; `.gitignore` had no rule. Added `harness/runs/*/summary.json` under a comment naming J82. `git check-ignore -v harness/runs/20261101_j23x/summary.json` prints `.gitignore:32:harness/runs/*/summary.json`; `git ls-files harness/runs | grep -c summary.json` still gives 7 (six `summary.json` and J24's `ladder_ctl_summary.json`, which the rule does not match). Nothing was `git rm`-ed.

- **b. `ci_failures`.** `tools/ci_failures.py:28` named `python3 tools/pr_policy.py` (gone since J62). It now reads `python3 core/wsc.py policy --branch <kind>/<id> --base origin/main`, the line `docs/REVIEW.md` gives. `docs/CI_FAILURES.md` was regenerated with `--since 2026-10-29T00:00:00Z --until 2026-10-29T22:20:00Z` (the window on its line 3): `git diff --stat` is 7 insertions, 7 deletions, and every changed line is the guard cell of a policy row ("branch bug" row and 6 policy rows); nothing else moved. The per-run "Run python tools/pr_policy.py ..." cells quote the CI log and stay (6 rows, history). `python3 -m unittest tests.test_ci_failures`: 3 tests ok. `gh` was signed in; the fetch took about 3 minutes.

- **c. `test_ctl_without_an_ini_uses_the_registered_default`.** Cause found by reading `core/harness/job.sh` (lines 44 to 100) and probing its `ctl_dir` resolution on a copy that exits before any write: the resolution is correct and returns `/c/napoleon_remastered_pc/ctl`, the **real** control folder, because the repo's registered default for `dev.ctl_dir` is a real PC path. The old test body therefore wrote a `ping` request into the live state folder. On CI the folder does not exist (rc 1, "cannot write into"); on the PC it exists, and whatever answers requests there (a running game with `dev.ctl=1`) turns the expected 124 plus stderr into a plain answer with empty stderr. That matches all five reviews that explained it away (J49 report:50,72; J55 review:17,72; J65 report:41 and review:7; J71 review:11,21), each of which ran during or after a PC session. I did **not** run the old body: it would touch the real state folder (the brief's kill criterion), so the failing rc and stderr were not observed; the cause is established from the code and the J55 note, not from a reproduction. Fix, in `tests/test_job_sh.py` only: the test builds a temporary game root whose `registries/config_keys.jsonl` registers a temp `dev.ctl_dir`, and passes it through `WSP_GAME_ROOT` (which `core/proxy/tools/layout.py` `game_root` honours), so the test never reads or writes the real state on any machine; it now asserts rc 124 and the withdrawn `.cmd.expired` file on every OS. Green: the test passes alone (1 test, 1.5 s) and in the full gates run. A red-then-green on a changed environment was not made: the only environment that makes the old body fail is the real PC state, which the brief forbids touching. No core change or row is needed (no core code is at fault).

- **d. Gates on `job/J82`.** See the report: `python3 core/wsc.py gates`.

## The three Empire learnings

Evidence read in `../empire-remastered/docs/learnings/LEARNINGS_HARNESS.md` only (read-only, one call each, all located). Fate: the audit assigned `&` in save names to core W25.

| # | Learning | Source | Fate |
|---|---|---|---|
| E1 | `%~dp0` in a watcher cmd job is the `jobs\` folder; use absolute paths | LEARNINGS_HARNESS.md:89 | core BACKLOG line B83 |
| E2 | A PowerShell helper named like an alias (`Rd`) ran `Remove-Item` and deleted `game.lock`; aliases beat functions | LEARNINGS_HARNESS.md:114 | core BACKLOG line B84 |
| E3 | Start-up crashes are environment-bursty, so a many-launch soak with topology logged is the only proof | LEARNINGS_HARNESS.md:94 and 96 | needs_brief row J98 |
| (E4) | `&` in save names | audit | already done: core W25 (queued core row, cited by the brief) |

## Open questions

Each is the brief's default taken, open for Liam; none is Liam's answer.

1. One job for the whole triage (default taken; the call budget held: no reviews are untriaged).
2. Rows grouped by owning area: 10 rows, not 60.
3. The seven tracked `harness/runs/*/summary.json` stay tracked.
4. Scope calls are rows whose description starts "Liam decides:" (J93; J91 item 1 and J96 hold them inside).

Suggested decision for `docs/DECISIONS.md` (J82 may not edit it): "A Later bullet in a review is not a tracker; a reviewer files each as a row, a core BACKLOG line or a dated drop in the review itself, and `wsc jobs check` (core W32's later registry) refuses a review whose Later bullet has no fate." When core W32's `later` registry (with `trigger_paths`) reaches napoleon, move the rows marked as lines with a "next job that changes <file> anyway" trigger (B64 to B84 and rows J89 to J97) into it; J82 did not.

## Per-bullet table

Fates: `needs_brief row J<n>`, `core BACKLOG line B<n> <title>`, `already done`, `dropped`. The review stays the source: the third column paraphrases in under 25 words.

| Id | Review | Bullet | Fate | Evidence |
|---|---|---|---|---|
| J1-L1 | jobs/J1/review.md | patch_engine reprotect restores pages in wrong order (RWX left) | already done | core proxy/src/patch_engine.h:161-184 restores per site in reverse (core v0.22.0; arrives with row J64) |
| J1-L2 | jobs/J1/review.md | build.sh mislabels the DLL on a shallow clone | already done | core proxy/tools/build_id.py:12 hashes inputs, a shallow clone gives the same id |
| J1-L3 | jobs/J1/review.md | DXVK_STATE_CACHE_PATH already set on the PC; J3 needs to know who sets it | dropped | reason: J3 shipped (jobs/J3 on main); no row names the variable and the uninstall is byte-identical |
| J1-L4 | jobs/J1/review.md | vanilla game running at first install not detected; proxy.p<pid>.log never rotated | already done | core proxy/src/dllmain.cpp:39 PruneSecondLogs; require_closed in core pc_deploy.py:525 |
| J1-L5 | jobs/J1/review.md | housekeeping for Liam: delete merged branches and PC _to_delete | dropped | reason: branch hygiene for Liam; nothing to build |
| J1-L6 | jobs/J1/review.md | pc_deploy game-closed check misses vanilla game on first install | already done | core proxy/tools/pc_deploy.py:525 require_closed (tasklist layer, J57) |
| J1-L7 | jobs/J1/review.md | second-process logs proxy.p<pid>.log accumulate | already done | core proxy/src/dllmain.cpp:39,81 PruneSecondLogs |
| J1-L8 | jobs/J1/review.md | proxy README open question 2 stale (test d on DXVK menu) | dropped | reason: overtaken: the proxy README moved to the core (J12); the open-questions list there is the core's |
| J1-L9 | jobs/J1/review.md | carry build.sh repro and --disable-auto-image-base into the core | already done | J12 moved the proxy to the core; core proxy/tools/build.sh holds both |
| J2-L1 | jobs/J2/review.md | update.ps1 health check refuses while a zombie needs_reboot flag is set | already done | core harness/update.ps1:154-158 lets a flag present before and after pass |
| J2-L2 | jobs/J2/review.md | job.sh: failed script exit 2 equals refused | core BACKLOG line B76 `job.sh`: a failed script's exit code is told apart from `refused` | core harness/job.sh:107 still maps refused and script exit 2 together |
| J2-L3 | jobs/J2/review.md | job.sh lock check-then-write not atomic | already done | core harness/job.sh:123-125 exclusive create (noclobber); also B20 for the stale takeover |
| J2-L4 | jobs/J2/review.md | cmd/ps1 job touching the game holds holds_game for whole run, watchdog off | core BACKLOG line B81 The watcher holds the game only for the start and kill, not the whole job | core harness/watcher.ps1:956,1236 holds_game still per job |
| J2-L5 | jobs/J2/review.md | steam launch route returns success with no game process | already done | core harness/watcher.ps1:409-412 returns failure after steam_wait_s |
| J2-L6 | jobs/J2/review.md | update replacing 0 files still CONFIRMED | already done | core harness/update.ps1:112 NOTHING TO DO exit 4 |
| J2-L7 | jobs/J2/review.md | gate: every file a runs README names must exist | already done | warscape-core BACKLOG B13 |
| J2-L8 | jobs/J2/review.md | kit_id versus folder name in update | already done | core harness/update.ps1 reads the manifest kit_id (usage line 2, NOTHING TO DO path) |
| J3-L1 | jobs/J3/review.md | every kit ships the dev pack and dev Lua; a release kit should drop them | already done | row J74 (release fixes, dev.file_rules and kit contents) and row J83 |
| J3-L2 | jobs/J3/review.md | job.sh ctl ignores dev.ctl_dir | already done | core harness/job.sh:45-65 reads dev.ctl_dir from the mod ini then the registered default (J12 fix 1c) |
| J3-L3 | jobs/J3/review.md | mid-sitting Lua sync only in PC scratch j3run.sh; make it a verb | already done | pc_deploy.py sync-lua (J4, jobs/J4/review.md fix 4) |
| J3-L4 | jobs/J3/review.md | hooks.cpp header comment garbled | already done | core proxy/src/hooks.cpp:1-6 header rewritten |
| J3-L5 | jobs/J3/review.md | core_pin gate sees superproject status from a linked worktree | already done | this job's gates run from the linked worktree nap-job-J82 with core_pin ok (report evidence) |
| J4-L1 | jobs/J4/review.md | round 1 items: sync-lua docstring, ACC_EXEMPT substring, ctl lua path guard | core BACKLOG line B72 `pc_deploy.py` and `ctl.py` small guards: the dev Lua docstring and the `lua` verb's path | ACC_EXEMPT overtaken by row J75; sync-lua docstring and the ctl lua path guard are core line K9 |
| J4-L2 | jobs/J4/review.md | acceptance_active imports the checkout's acceptance.py, branch can switch rule 79 off | already done | core wsc policy replaces tools/pr_policy.py (J62); W23 judges with the base rules, carried by row J78 |
| J4-L3 | jobs/J4/review.md | pc_deploy docstring claims unowned files never touched | core BACKLOG line B72 `pc_deploy.py` and `ctl.py` small guards: the dev Lua docstring and the `lua` verb's path | core proxy/tools/pc_deploy.py: same docstring-versus-behaviour fix |
| J4-L4 | jobs/J4/review.md | ACC_EXEMPT matches by substring | already done | tools/pr_policy.py is gone (J62); row J75 owns the one rule 79 exemption |
| J4-L5 | jobs/J4/review.md | ledger self-attested, branch can add 20 pass lines | already done | row J75 (rule 79 evidence: unique evidence, append-only ledger) |
| J4-L6 | jobs/J4/review.md | scratch Lua written into game folder; guard ctl lua verb to the lua folder | core BACKLOG line B72 `pc_deploy.py` and `ctl.py` small guards: the dev Lua docstring and the `lua` verb's path | core harness/ctl.py lua verb; no guard seen |
| J4-L7 | jobs/J4/review.md | row 75 wsc jobs view PC state and usage source not done | already done | row J87 (usage lines) and jobs/J49 usage reader |
| J5-L1 | jobs/J5/review.md | builder/reviewer check compares Claude-Session trailers only | already done | warscape-core B10 and W12 (commit-msg hook), carried by row J78 |
| J5-L2 | jobs/J5/review.md | job rows compared at merge base but DECISIONS at base tip: wrong message | dropped | reason: overtaken: pr_policy.py gone (J62), core warscape/policy.py reads both at the base |
| J5-L3 | jobs/J5/review.md | test_repo_rules: any decision row quoting tests clears the skip | needs_brief row J94 | tests/test_repo_rules.py:130-131 still matches on backticked name only |
| J5-L4 | jobs/J5/review.md | core pin_problems precedence reads as a bug; tag the merge | already done | core warscape/gates.py:152 pin_check rewritten; tag v0.2.0 long since cut (core v0.22.0) |
| J5-L5 | jobs/J5/review.md | delete remote job/J3 | dropped | reason: branch hygiene; reports cite job branch shas (J56 review Later 3 keeps them on purpose) |
| J5-L6 | jobs/J5/review.md | confirm gates and policy are required checks on main | already done | docs/REVIEW.md names the required checks; row J78 runs wsc ci check-settings |
| J6-L1 | jobs/J6/review.md | exe.py mask_for over-masks across instruction boundaries; treat none as not found | needs_brief row J95 | discovery/core/exe.py:48 mask_for unchanged |
| J6-L2 | jobs/J6/review.md | Napoleon imports debug d3dx9d_40.dll, J8 should check | already done | recorded in discovery/diff/exe.json:86 and J8 shipped; no behaviour claim rests on it |
| J6-L3 | jobs/J6/review.md | unclosed open() in lua_api.py and test_discovery_lua.py | needs_brief row J95 | discovery/core/lua_api.py:36,112 and tests/test_discovery_lua.py:108 still use bare open |
| J7-L1 | jobs/J7/review.md | db readme should split out the 26 empty tables | needs_brief row J95 | discovery/core/db.py:224 README table has no empty-table column |
| J7-L2 | jobs/J7/review.md | parse_header never checks the mark byte | needs_brief row J95 | discovery/core/db.py:79 returns the mark and nothing checks it |
| J7-L3 | jobs/J7/review.md | pack_order fact verified but last clause is assumed | needs_brief row J95 | registries/engine_facts/napoleon.assets.pack_order.json claim still says verified |
| J7-L4 | jobs/J7/review.md | no CI run id in the report | dropped | reason: the merge pull request CI run is the evidence; nothing to build |
| J7-L5 | jobs/J7/review.md | test_pc_deploy fails whenever Napoleon.exe is running | already done | tests/test_pc_deploy.py:21-48 stubs the lowest layer (J57) |
| J7-L6 | jobs/J7/review.md | sanctioned fetch_pinned tool for a pinned raw GitHub file | already done | core proxy/tools/netfetch.py and fetch_lua.py/fetch_ui.py (B62 folds the retry in) |
| J8-L1 | jobs/J8/review.md | CaptureRun timeout path leaves kIdle with s_rec set | core BACKLOG line B64 Capture hardening: the timeout path, unsynchronised globals and state-block hooks | core proxy/src/capture.cpp CaptureRun, not in BACKLOG (B63 is the s_rec gate) |
| J8-L2 | jobs/J8/review.md | s_depth, s_buf, Line() unsynchronised globals in capture | core BACKLOG line B64 Capture hardening: the timeout path, unsynchronised globals and state-block hooks | same capture.cpp line as J8-L1 |
| J8-L3 | jobs/J8/review.md | hook CreateStateBlock and StateBlock Apply/Capture | core BACKLOG line B64 Capture hardening: the timeout path, unsynchronised globals and state-block hooks | core proxy/src/capture.cpp, no hook seen |
| J8-L4 | jobs/J8/review.md | engine facts carry evidence paths but no run field | dropped | reason: facts since carry run ids (J71 fact napoleon.vulkan.rt_32bit has run 20261103_j71pc); older rows are history |
| J8-L5 | jobs/J8/review.md | report Deviations omit two deviations | dropped | reason: report text is history and cannot be edited by a later job |
| J8-L6 | jobs/J8/review.md | wsc setup still checks harness/core/job.sh | already done | tools/verbs/setup.py checks core/harness (J12) ; no harness/core/job.sh path remains in tools |
| J9-L1 | jobs/J9/review.md | report Lua count 2,911 versus table 3,088 | dropped | reason: report is history; J10 counted from the table |
| J9-L2 | jobs/J9/review.md | probes calling state-changing functions not named a deviation | dropped | reason: report text is history; the README lists every call |
| J9-L3 | jobs/J9/review.md | fix probes live only in the run folder; move to proxy/napoleon/lua/probes and generate probe_safe_list.lua with --check | already done | row J78 moves the probes; the generated list and its --check go in ROW:probes |
| J9-L4 | jobs/J9/review.md | round 1 items 3 to 5: no-verify guard, B35-B39, weak anchors | already done | B39, B42, B43 in warscape-core BACKLOG; no-verify guard is row J76 (R11) |
| J9-L5 | jobs/J9/review.md | --no-verify commit 5eafc75; gate reading a run file still being written | already done | row J76 (R11, --no-verify) and core W9 flake rule via row J78 |
| J9-L6 | jobs/J9/review.md | core items filed as B35 to B39 | already done | warscape-core BACKLOG B38, B39, B42, B43 (B35 to B37 merged and removed) |
| J9-L7 | jobs/J9/review.md | weak anchors on 2 to 4 bytes; nothing to do now | dropped | reason: reviewer said nothing to do; anchors checked at fixed RVA behind exe guard |
| J10-L1 | jobs/J10/review.md | getters.lua runs dofile(nil) without its list, crashed game 3 times | needs_brief row J89 | J78 moves the probes but its description misses this guard |
| J10-L2 | jobs/J10/review.md | pid-file guard local; core one-driver-per-lock and ctl reset relaunch | dropped | reason: report question 3 was Liam's and the brief's defaults take no core change; B27/B30 cover the lock races |
| J10-L3 | jobs/J10/review.md | discovery check misses used_by in assets.jsonl | needs_brief row J95 | discovery/core/ui_atlas.py:1278 writes used_by, no check reads it |
| J10-L4 | jobs/J10/review.md | no row has a db: data field though art_keys has db rule for 9 roles | dropped | reason: the contract stage owns it (D39) and is not queued; no code to fix now |
| J10-L5 | jobs/J10/review.md | 92 rows have no data_fields; contract stage should read empty as none traced | dropped | reason: same contract-stage note as J10-L4 |
| J10-L6 | jobs/J10/review.md | 69 units static_only because they open on a click | dropped | reason: D39 leaves them to the contract stage |
| J11-L1 | jobs/J11/review.md | briefpaths skips prose under Registry gaps | needs_brief row J95 | discovery/core/briefpaths.py:192-200 skips the whole zone |
| J11-L2 | jobs/J11/review.md | four open facts owner liam and config_keys owner proxy | dropped | reason: owner field choices, neither blocks and no tracker needs them |
| J11-L3 | jobs/J11/review.md | first PC sitting runs wsc discovery gate --install once | already done | row J83 (release sitting on the PC) includes the PC runs; row J78 is a PC job too |
| J11-L4 | jobs/J11/review.md | J66 brief path uied.templates backslash fix | already done | J66 merged; uiscale/runs/2026-11-02_j66 shows the fixed path |
| J12-L1 | jobs/J12/review.md | B20 stale lock takeover not race-free | already done | warscape-core BACKLOG B20 |
| J12-L2 | jobs/J12/review.md | B21 ps1 LASTEXITCODE ends job with wrong code | already done | warscape-core BACKLOG B21 |
| J12-L3 | jobs/J12/review.md | B22 IsOwnMove compares physical pixels at scaled DPI | already done | warscape-core BACKLOG B22 |
| J12-L4 | jobs/J12/review.md | B23 headless_status.json not rewritten after relocation | already done | warscape-core BACKLOG B23 |
| J12-L5 | jobs/J12/review.md | B24 job.sh comment names old watcher path | already done | warscape-core BACKLOG B24 |
| J12-L6 | jobs/J12/review.md | SweepHides hides on either side larger (behaviour change, no action) | dropped | reason: review said no action now; passed 20 times |
| J13-L1 | jobs/J13/review.md | watcher finds headless marker only through a log format string | core BACKLOG line B65 Headless: an explicit marker constant, and the guard thread's lock hold | core harness/watcher.ps1:855-858 and proxy/src/headless.cpp |
| J13-L2 | jobs/J13/review.md | guard thread holds s_cs during monitor enumeration, frame spikes | core BACKLOG line B65 Headless: an explicit marker constant, and the guard thread's lock hold | core proxy/src/headless.cpp guard thread |
| J13-L3 | jobs/J13/review.md | audio muting in adapter prefs: Liam to confirm | needs_brief row J91 | harness/napoleon/adapter.json headless.prefs sound_master_*; Liam decides |
| J13-L4 | jobs/J13/review.md | kill criterion hit; orphan scratch loop lesson stays prose | dropped | reason: reviewer accepted; about scratch scripts, no repo code |
| J13-L5 | jobs/J13/review.md | ps1 job reports ok exit=0 when script exits non-zero | already done | core harness/watcher.ps1:1309-1311 appends exit $LASTEXITCODE (B21 refines) |
| J13-L6 | jobs/J13/review.md | evidence of fact window_imports points at report without the list | needs_brief row J95 | registries/engine_facts napoleon.exe.window_imports evidence |
| J14-L1 | jobs/J14/review.md | J4 brief must carry two unfinished J14 gates (save round trip, EndTurn survival) | already done | J4 merged; fact napoleon.save.endturn_survival is open and J60 (naval orders) plus J78 PC runs exercise it |
| J14-L2 | jobs/J14/review.md | C1 not unattended, Liam dismissed two modals | dropped | reason: report states it; the fact rests on that one sitting by design |
| J14-L3 | jobs/J14/review.md | load_save.sh stops after 4 silent polls, never run in game | needs_brief row J91 | harness/napoleon/load_save.sh poll limit still unproven |
| J14-L4 | jobs/J14/review.md | saves/core goes to warscape-core via J12 | already done | J12 moved saves/core into the core (core saves/) |
| J14-L5 | jobs/J14/review.md | game quick_save and auto_save left in save_games | dropped | reason: Liam's files to delete |
| J15-L1 | jobs/J15/review.md | console off writes 0 to the slot, race with CliExecute | already done | core proxy/src/console.cpp:134 off keeps the forwarder and refuses |
| J15-L2 | jobs/J15/review.md | dev.cpp attributes latest forwarder record without comparing names | already done | core proxy/src/dev.cpp:332-335 RecordIsForLine |
| J15-L3 | jobs/J15/review.md | console chunk files never deleted | core BACKLOG line B66 Console chunk files are deleted once `RunLua` returns | core proxy/src/dev.cpp:323-325 writes _console/<id>.lua, no delete seen |
| J15-L4 | jobs/J15/review.md | x86re walk drops an indirect jmp | already done | discovery/core/x86re.py:136 every indirect jmp is listed |
| J15-L5 | jobs/J15/review.md | shot.sh hard-codes the Napoleon game path | already done | core harness/shot.sh holds no game name (grep clean) |
| J17-L1 | jobs/J17/review.md | jobs row J12 description says cut v0.2.0 | already done | PR #25 plan/j12-tag-wording; J12 is done |
| J17-L2 | jobs/J17/review.md | commit core and wsc.toml together is prose | already done | warscape-core BACKLOG B9 |
| J18-L1 | jobs/J18/review.md | PC ini reads BAD after acceptance run; pass 1 after install fails settings_identical | already done | warscape-core BACKLOG B26 and B31 (acceptance reads the build id after launch) |
| J18-L2 | jobs/J18/review.md | wsc gates fails from PowerShell: WSL bash first on PATH | already done | tests/test_job_sh.py:19 bash_for_tests; core warscape/gitbash.py (B18, merged and removed) |
| J18-L3 | jobs/J18/review.md | round 1 items 4, 7, 8: hooks need repo folder, rescue branch, Script-RunsGit word match | already done | items 4 is B10/W12 (J78); item 8 is row J76 (git guards); item 7 is branch hygiene |
| J18-L4 | jobs/J18/review.md | hooks run only in a session started in the repo folder | already done | warscape-core BACKLOG B10 plus W12 via row J78; hook rows in J76 |
| J18-L5 | jobs/J18/review.md | PC runs an unmerged watcher 1.1.0 | dropped | reason: settled by the J18 merge, as the review said |
| J18-L6 | jobs/J18/review.md | report CI evidence: run 41146895956 cancelled | dropped | reason: report text is history; the review gives the counting run |
| J18-L7 | jobs/J18/review.md | origin/rescue/J18-7b8bd96 can be deleted | dropped | reason: branch hygiene, Liam's call |
| J18-L8 | jobs/J18/review.md | Script-RunsGit word match refuses echo "see git log" | already done | row J76 (agent hook hardening: per-segment git and game guards) |
| J19-L1 | jobs/J19/review.md | Test-Lib.ps1 Invoke-Selected parameters lack the tc prefix | core BACKLOG line B67 `Test-Lib.ps1` `Invoke-Selected`: runner parameters leak into case bodies | core harness/tests/Test-Lib.ps1 |
| J19-L2 | jobs/J19/review.md | gate: report Model line equals row model, deviation named | core BACKLOG line B68 `wsc jobs check`: the report's `Model:` line against the row, and a brief that names `proxy/` or `harness/` code without an acceptance line | jobs check in core warscape/jobq.py has no model comparison |
| J19-L3 | jobs/J19/review.md | watcher 1.0.1 not on PC yet | dropped | reason: overtaken: later PC jobs (J44, J46, J57) ran newer watcher versions |
| J20-L1 | jobs/J20/review.md | J19 report commit has no trailer; merge J19 first | dropped | reason: J19 and J20 are both done on main |
| J20-L2 | jobs/J20/review.md | build.sh apt-get takes mingw version of the day | core BACKLOG line B69 `build.sh`: the mingw package versions are not pinned | core proxy/tools/build.sh apt-get install without version pins |
| J20-L3 | jobs/J20/review.md | report open questions are Liam's; dev.skip_intro needs a needs_brief row | already done | jobs/J20 questions answered by later work; dev.skip_intro is a standing rule in ctl scenes (row J46 land_40) |
| J21-L1 | jobs/J21/review.md | mouse bindings and ANY/ALLOW_SHIFT meaning open; one PC probe | already done | row J29 (Alt-drag) brief includes the probe; fact facts open until then |
| J21-L2 | jobs/J21/review.md | hotkeys verb hard-codes the Napoleon data path | needs_brief row J94 | tools/verbs/hotkeys.py:33 GAME_DATA |
| J21-L3 | jobs/J21/review.md | hotkeys check imports lists from tests/test_hotkeys.py | needs_brief row J94 | tools/verbs/hotkeys.py:247 |
| J21-L4 | jobs/J21/review.md | split uses str.capitalize, misspells NumpadAdd in messages | needs_brief row J94 | tools/verbs/hotkeys.py:132 |
| J21-L5 | jobs/J21/review.md | schema cannot spell Alt+Esc etc. | already done | warscape-core BACKLOG B61 (context families); B3 merged and removed |
| J22-L1 | jobs/J22/review.md | round 1 later: ctl.bash fallback, BARE_BASH gaps, rule 79 brief check | needs_brief row J94 | BARE_BASH gaps are tests/test_repo_rules.py:56-60 (row J94); ctl.bash fallback is K7; the rule 79 brief check is K5 |
| J22-L2 | jobs/J22/review.md | first acceptance pass after fresh install fails settings_identical | already done | warscape-core BACKLOG B26 and B31 |
| J22-L3 | jobs/J22/review.md | ctl.bash silent fallback to plain bash | core BACKLOG line B70 `ctl.py` `bash()` says when its finder fails | core harness/ctl.py:48-60 still falls back without a line |
| J22-L4 | jobs/J22/review.md | BARE_BASH misses shutil.which argv and multi-line lists, skips .sh | needs_brief row J94 | tests/test_repo_rules.py:56-60 |
| J22-L5 | jobs/J22/review.md | jobs check should flag a brief naming harness/proxy code without acceptance line | core BACKLOG line B68 `wsc jobs check`: the report's `Model:` line against the row, and a brief that names `proxy/` or `harness/` code without an acceptance line | same jobs-check family as K5; napoleon row J73 adds rule 79 on every kind |
| J23-L1 | jobs/J23/review.md | gen_tables.py should skip non-proxy owners; dxvk_path description wrong | core BACKLOG line B80 `gen_tables.py` skips `config_keys` owners other than `proxy` | core proxy/tools/gen_tables.py owner filter; the registry description and adapter dxvk_conf path are fixed by row J94 |
| J23-L2 | jobs/J23/review.md | re-run measure --backends system after J16; J59 extends to J46 rows | already done | row J59 (performance baseline on J46 rows, budgets re-agreed) and row J61 |
| J23-L3 | jobs/J23/review.md | budgets stay PROPOSED until Liam agrees | already done | row J59 ends with Liam agreeing the budgets |
| J24-L1 | jobs/J24/review.md | host check: tests import only packages CI installs | core BACKLOG line B71 Host check: every non-stdlib import in `tests/` is guarded or installed by the CI workflow | core test runner; not in BACKLOG |
| J24-L2 | jobs/J24/review.md | shot_sheet tool row purpose loses closing quote | needs_brief row J94 | header-to-row extraction (core warscape/tools.py) strips trailing quote; tools/shot_sheet.py:4 |
| J24-L3 | jobs/J24/review.md | fix round says 10 tests, file has 9 | dropped | reason: report text is history |
| J24-L4 | jobs/J24/review.md | cut-off line question is Liam's; J59 re-measure 4K p50 | already done | decision D49 (all three shadow values approved) and row J59 |
| J24-L5 | jobs/J24/review.md | shader_catalog import fails on one missing capture; density breaks past 40 paths; never edit running .sh | needs_brief row J95 | shader_catalog/density are discovery/core (W4 has not moved them); the watcher half is core line K19 |
| J24-L6 | jobs/J24/review.md | proposed release turns height cutoff on, Liam's call | already done | decision D49 (Liam, 2026-11-04) and row J77 |
| J24-L7 | jobs/J24/review.md | at 4K release p50 +0.24 to +0.40 ms systematic; J59 re-measure | already done | row J59 |
| J28-L1 | jobs/J28/review.md | unit leaving its army in settle fails through an exception string, not structured | core BACKLOG line B73 `ctl.py`: a unit that leaves its army during the settle is a structured failure | core harness/ctl.py step read; B-lines W30 cover failed results in reports only |
| J28-L2 | jobs/J28/review.md | never-moved check proven only by host fixture; rerun g2 on siege_small | needs_brief row J92 | harness/runs/20261102_j28pc/README.md:52 |
| J28-L3 | jobs/J28/review.md | ctl.routes.orders land and siege repeat blocks verbatim | needs_brief row J92 | harness/napoleon/adapter.json ctl.routes.orders |
| J28-L4 | jobs/J28/review.md | wedge always fails here; J29 must not offer it | needs_brief row J92 | J29 brief writer needs the list; harness/napoleon/adapter.json routes |
| J28-L5 | jobs/J28/review.md | acceptance identity bug already core backlog B26 and B31 | already done | warscape-core BACKLOG B26, B31 |
| J30-L1 | jobs/J30/review.md | CI build time before and after not given | dropped | reason: report-evidence gap in a finished job; CI timing is visible in run history |
| J30-L2 | jobs/J30/review.md | acceptance runner free-RAM floor; build.sh smoke step 6 without GestureAdapter | core BACKLOG line B74 Acceptance runner: a free-RAM floor, and `build.sh smoke` for a game without a `GestureAdapter` | B57 is the hook gate, not smoke step 6 |
| J30-L3 | jobs/J30/review.md | viewer/core promotion row still only proposed | already done | row J63 (promote upscale/core and viewer/core) |
| J31-L1 | jobs/J31/review.md | per-checkout docker volumes accumulate; build.sh --prune | needs_brief row J97 | viewer/ build script (napoleon-viewer-cmake volumes) |
| J31-L2 | jobs/J31/review.md | S2 has no console or network capture inside the artifact | needs_brief row J97 | needs a signed-in browser session |
| J31-L3 | jobs/J31/review.md | J31 jobs row says the version J30 pins | dropped | reason: J31 is done; row text is history and edits to done rows are refused by policy |
| J33-L1 | jobs/J33/review.md | previews show C with keyline faction rule; J34 treats LANGUAGE.md as source | already done | J34 built the board (uikit/napoleon); row J69 refines it with Liam |
| J33-L2 | jobs/J33/review.md | open questions: RCSS image-color, derived tokens via J35, 24 sprites needing D14 acceptance | already done | row J35 (panel host) and row J69; sprites are Liam's |
| J33-L3 | jobs/J33/review.md | plain HTML artifact instead of Design canvas, accepted | dropped | reason: reviewer accepted |
| J33-L4 | jobs/J33/review.md | D43 numbering: renumber if another branch lands a D43 | dropped | reason: D43 landed in docs/DECISIONS.md; no collision |
| J34-L1 | jobs/J34/review.md | report written by orchestrating chat; review by different session | dropped | reason: not a defect; policy keys on session id and held |
| J34-L2 | jobs/J34/review.md | Liam locks the board, sprites, on-colour decision row | already done | row J69 (component board refinement with Liam) |
| J34-L3 | jobs/J34/review.md | promotion candidates to the core are a later brief | already done | row J63 (promotions) ; board maths are row J63's sibling and not yet briefed |
| J34-L4 | jobs/J34/review.md | no rule changed for open branches | dropped | reason: statement, no follow-up |
| J36-L1 | jobs/J36/review.md | core: widen upscale_status enum; adopt upscale/core/dds.py | already done | row J63 (promote upscale/core) |
| J36-L2 | jobs/J36/review.md | cursors stay out until Liam decides RmlUi host draws its own | needs_brief row J96 | Liam decides: cursors (179 .cur, 1 .ani) |
| J36-L3 | jobs/J36/review.md | add ui_art_2x5_*.pack to mod_packs skip list before real install | already done | discovery/napoleon/games.json:9-10 lists the ui_art_2x5 packs |
| J36-L4 | jobs/J36/review.md | Liam picks order of the remaining 5954 todo assets | needs_brief row J96 | Liam decides: the order |
| J38-L1 | jobs/J38/review.md | PC acceptance sitting steps b to f not done | already done | row J83 (0.1.0 release sitting on the PC) |
| J38-L2 | jobs/J38/review.md | installer tests skip on Linux CI; hook into harness-windows | already done | row J74 (installer tests in CI) |
| J38-L3 | jobs/J38/review.md | release/core promotion job not queued | needs_brief row J94 | PROMOTIONS entry None; a promotion row beside J63 |
| J38-L4 | jobs/J38/review.md | open owner questions: unofficial-mod statement, licence, player key, AV reaction | already done | row J83 collects them for Liam |
| J39-L1 | jobs/J39/review.md | plain jobs view fetches every job branch, slower | dropped | reason: builder kept it to show a correct Review button; --offline exists |
| J39-L2 | jobs/J39/review.md | ThreadingHTTPServer concurrent requests run git fetch at once | core BACKLOG line B75 `wsc jobs view --serve` hardening | core warscape/jobq.py:832-848 JobServer has a lock but fetch overlap remains |
| J39-L3 | jobs/J39/review.md | same-name guard counts only state working | core BACKLOG line B75 `wsc jobs view --serve` hardening | core warscape/jobq.py launch guard |
| J39-L4 | jobs/J39/review.md | start_session takes first 8-hex word of stdout | core BACKLOG line B75 `wsc jobs view --serve` hardening | core warscape/jobq.py launch regex |
| J39-L5 | jobs/J39/review.md | strip CLAUDE_CODE_* variables in _claude when serving from an agent | core BACKLOG line B75 `wsc jobs view --serve` hardening | no CLAUDE_CODE_ strip in core warscape/*.py |
| J39-L6 | jobs/J39/review.md | Stop button follow-up row | core BACKLOG line B75 `wsc jobs view --serve` hardening | jobs view Stop |
| J40-L1 | jobs/J40/review.md | transport_to_hlci bad cell index crashes next EndTurn, only prose stops it | needs_brief row J90 | discovery/core/console_cmds.py status; DLL input, carries 20 passes |
| J40-L2 | jobs/J40/review.md | transport_to_region open | already done | warscape-core BACKLOG B25 |
| J40-L3 | jobs/J40/review.md | acceptance identity on fresh install | already done | warscape-core BACKLOG B26, B31 |
| J40-L4 | jobs/J40/review.md | watcher kill returns before game is gone | already done | warscape-core BACKLOG B27 |
| J40-L5 | jobs/J40/review.md | save snapshot and restore were manual; J18 guard should own it | needs_brief row J91 | harness/ load_save.sh and profile restore per launch |
| J40-L6 | jobs/J40/review.md | one Lua call among five diplomacy getters stops the pump | needs_brief row J90 | bisect before any probe uses them |
| J41-L1 | jobs/J41/review.md | pin bump must not turn every run into a warn (skipTest routes) | already done | row J64 (pin bump to v0.22.0); tests/test_proxy_host.py:78 is its check |
| J41-L2 | jobs/J41/review.md | proxy/runs evidence counts as proxy input | already done | row J73 (derived proxy inputs) |
| J41-L3 | jobs/J41/review.md | Claude-Session hook does not run outside the repo folder | already done | warscape-core BACKLOG B10 and W12 via row J78 |
| J41-L4 | jobs/J41/review.md | setup.git_bash probes %LOCALAPPDATA%/Git | needs_brief row J94 | tools/verbs/setup.py:58 |
| J41-L5 | jobs/J41/review.md | pin_problems fails a shallow submodule with newer tag | already done | core warscape/gates.py:152-159 pin_check(shallow) |
| J42-L1 | jobs/J42/review.md | pull_request run no longer tests merge with main; merge queue if it bites | dropped | reason: reviewer: only if it bites; no occurrence recorded in docs/CI_FAILURES.md |
| J42-L2 | jobs/J42/review.md | 6 of 13 flaky rows say no in the second-run column | dropped | reason: the note column carries the reasoning, per the review |
| J42-L3 | jobs/J42/review.md | lost runner and shallow-tag reading stay open questions | already done | shallow reading fixed (J41-L5); the lost runner was a one-off |
| J42-L4 | jobs/J42/review.md | two notify checks cosmetic | dropped | reason: cosmetic |
| J43-L1 | jobs/J43/review.md | cam with dev.camera=0 fails; J44 scene must launch with dev.camera=1 | needs_brief row J92 | tests/test_ctl.py:310 ; verify scene sets it |
| J43-L2 | jobs/J43/review.md | siege falls back to land route with no scenario row | needs_brief row J92 | core harness/ctl.py current_kind |
| J43-L3 | jobs/J43/review.md | engine-Lua string lint covers tracked proxy/*.lua only | already done | warscape-core BACKLOG B14 |
| J43-L4 | jobs/J43/review.md | port memdump.ps1/memwrite.ps1 read half as watcher job type | needs_brief row J92 | scratch only (_scratch/j43); J60 naval orders may need the reads |
| J43-L5 | jobs/J43/review.md | route 2 and campaign camera setters untried | dropped | reason: review: recorded, nothing to do now; facts napoleon.battle.script_api_reachable stay open |
| J44-L1 | jobs/J44/review.md | fixed-sky pack build failure silent; ctl.py Pc.launch should refuse missing add source | core BACKLOG line B77 A missing optional pack is recorded in the kit and refused at launch | core proxy/tools/pc_deploy.py and harness/ctl.py |
| J44-L2 | jobs/J44/review.md | report says ledger lines 4 to 23, actually 5 to 24 | dropped | reason: report text is history |
| J44-L3 | jobs/J44/review.md | deliverable 2 gaps: large battles, siege city, campaign rows | needs_brief row J92 | scenario rows in registries/scenarios.jsonl; J8 and J23 must not assume them |
| J44-L4 | jobs/J44/review.md | commit hook only in repo-folder sessions; commit-msg hook in core | already done | warscape-core BACKLOG B10 and W12 via row J78 |
| J45-L1 | jobs/J45/review.md | file_rule_problems checks only add src -> dst form | dropped | reason: review: fine for the one rules file; extend if grammar grows |
| J45-L2 | jobs/J45/review.md | wsc setup check the Pillow interpreter for acceptance.py | needs_brief row J94 | preflight catches it at run time; setup check is optional |
| J45-L3 | jobs/J45/review.md | J12 should merge main first and run last | dropped | reason: J12 is done |
| J46-L1 | jobs/J46/review.md | autostart.lua while loop sets lc2 = nil, reads one army_box | already done | row J78 (names autostart.lua:139); line 137-139 still present |
| J46-L2 | jobs/J46/review.md | a pass takes about 8 min, 20 passes about 2h40 | already done | row J85 (unattended 20-pass acceptance) |
| J46-L3 | jobs/J46/review.md | two real saves for campaign rows; stage-the-save core backlog; stray ini | already done | warscape-core BACKLOG B51; campaign saves are Liam's (J44-L3 row) |
| J49-L1 | jobs/J49/review.md | per-card usage line needs a core hook card_extra | already done | warscape-core BACKLOG B50 |
| J49-L2 | jobs/J49/review.md | attribute counts a session for the first job only | dropped | reason: review: rare, no change needed |
| J49-L3 | jobs/J49/review.md | week cost not shown | already done | row J87 (usage lines on napoleon's reports) |
| J49-L4 | jobs/J49/review.md | report's test_job_sh failure not this branch's | already done | this job: test_ctl_without_an_ini isolated (commit 0d8e053) |
| J50-L1 | jobs/J50/review.md | re-probe dds_at_tga_paths with a DXT5 4-aligned TGA path | needs_brief row J96 | needs one PC launch (needs_pc) |
| J50-L2 | jobs/J50/review.md | UI DXT outputs at 2.5x not multiple of 4, may fail to draw | needs_brief row J96 | upscale/core/rules.py round-up rule |
| J50-L3 | jobs/J50/review.md | pc_deploy status should name a kit left installed by a finished job | core BACKLOG line B78 `pc_deploy.py status` names a kit left installed by a finished job; its tests need no live game | core proxy/tools/pc_deploy.py status |
| J50-L4 | jobs/J50/review.md | init heap corruption crash job and ctl.py shot at main menu need rows | already done | row J78 records whether napoleon.proxy.init_heap_corruption reproduces; ctl shot at main menu in ROW:harness |
| J51-L1 | jobs/J51/review.md | plan estimates no output bytes; run should refuse below 20 percent free | needs_brief row J96 | upscale/napoleon/cli.py plan prints no free-disk check |
| J51-L2 | jobs/J51/review.md | verify does not check premultiplied invariant for DXT2 | needs_brief row J96 | upscale/core/batch.py verify |
| J51-L3 | jobs/J51/review.md | native_cap tested on source size, 23 loading screens 4800 px wide | needs_brief row J96 | upscale/napoleon/config.json:27 native_cap 4096; Liam decides (D35) |
| J51-L4 | jobs/J51/review.md | run_j51.log holds only first pass; run should append a summary | needs_brief row J96 | upscale/core/batch.py run |
| J52-L1 | jobs/J52/review.md | branch_state treats bare row as head None | dropped | reason: review: only matters for a future caller; real snapshots carry shas |
| J52-L2 | jobs/J52/review.md | round 1 later items 3 and 4 still stand | already done | item 3 is J52-L3 (K12); item 4 is J52-L4 (done J57) |
| J52-L3 | jobs/J52/review.md | overlapping fetches of branch_rows between page GET and tick | core BACKLOG line B75 `wsc jobs view --serve` hardening | core warscape/jobq.py branch_rows |
| J52-L4 | jobs/J52/review.md | test_pc_deploy errors while Napoleon.exe is running | already done | tests/test_pc_deploy.py:21-48 (J57) |
| J53-L1 | jobs/J53/review.md | upscale/pc/play.py never run on real game folder | needs_brief row J93 | Liam decides: first install is the real test |
| J53-L2 | jobs/J53/review.md | watcher and job.sh lock unaware of play.json | core BACKLOG line B79 The watcher and `job.sh lock` know a player's `play.json` | core harness/job.sh and watcher.ps1; row play skips until it lands |
| J53-L3 | jobs/J53/review.md | uninstall does not refuse while an agent holds the game lock | needs_brief row J93 | upscale/pc/play.py uninstall |
| J53-L4 | jobs/J53/review.md | held-back loading screens and memory use unproven | needs_brief row J93 | Liam's play test settles it |
| J54-L1 | jobs/J54/review.md | gh pr ready then merge --auto can merge on a skipped policy | already done | J57 reordered the review steps (J57 review Later 1 shows a real non-skipped policy run) |
| J54-L2 | jobs/J54/review.md | a failed changes job skips slow jobs and counts as passed | already done | .github/workflows/gates.yml:6-7,155 J57 guards with !cancelled() and changes.result |
| J54-L3 | jobs/J54/review.md | test_pc_deploy fails locally whenever real game runs | already done | tests/test_pc_deploy.py:21-48 (J57) |
| J55-L1 | jobs/J55/review.md | branches cut before J55 need a transition merge; fold helper | dropped | reason: J8 the only branch and merged; no other pre-J55 branch exists |
| J55-L2 | jobs/J55/review.md | test_pc_deploy Deploy errors instead of skipping when game runs | already done | tests/test_pc_deploy.py:21-48 (J57) |
| J55-L3 | jobs/J55/review.md | test_ctl_without_an_ini fails locally with empty stderr | already done | this job: isolated test, commit 0d8e053 (record Housekeeping c) |
| J55-L4 | jobs/J55/review.md | open questions 2 to 4 stand | dropped | reason: review: none blocks; assets registry and row delete are B28 (done in core) |
| J56-L1 | jobs/J56/review.md | _blobs and for-each-ref calls ignore return code | already done | core warscape/jobq.py:510-514 checks returncode |
| J56-L2 | jobs/J56/review.md | glob fetch never prunes, offline lists a deleted job branch | core BACKLOG line B75 `wsc jobs view --serve` hardening | core warscape/jobq.py branch_rows fetch |
| J56-L3 | jobs/J56/review.md | 27 of 29 job branches belong to done jobs | dropped | reason: brief keeps them because reports cite shas |
| J57-L1 | jobs/J57/review.md | live evidence for problem 1 is this job's own merge | dropped | reason: evidence note; the merge happened |
| J57-L2 | jobs/J57/review.md | scratch/j57-changes-fail still on origin | dropped | reason: branch hygiene |
| J57-L3 | jobs/J57/review.md | core test_pc_deploy copy has same live-game dependency | core BACKLOG line B78 `pc_deploy.py status` names a kit left installed by a finished job; its tests need no live game | core line K15 asks the core copy of the Deploy test not to need a live game |
| J58-L1 | jobs/J58/review.md | pr_policy main() changed uses name-only, rename out of proxy/ shows new path | already done | tools/pr_policy.py is gone (J62); row J73 (rule 79 on every kind) owns changed-path derivation |
| J58-L2 | jobs/J58/review.md | note for J55: both edit acc lines, merge conflict | dropped | reason: both merged long ago |
| J62-L1 | jobs/J62/review.md | changes job time before and after not measured | dropped | reason: review: compare next time anyone looks; no regression seen in docs/CI_FAILURES.md |
| J62-L2 | jobs/J62/review.md | claude_hook trailer rule silently skips with no core checkout | dropped | reason: review: acceptable, wsc setup checks the submodule |
| J62-L3 | jobs/J62/review.md | restart jobs view --serve after merge; Liam's core repo settings | already done | row J78 runs wsc ci check-settings; the restart is operational |
| J65-L1 | jobs/J65/review.md | top-level rule misses over-broad pattern nested under unit container | dropped | reason: review: none exists today |
| J65-L2 | jobs/J65/review.md | discovery ui writes empty reach.json without error when extract missing | needs_brief row J95 | discovery/core/ui_atlas.py main |
| J65-L3 | jobs/J65/review.md | reviewer did not rerun discovery ui | dropped | reason: evidence note |
| J66-L1 | jobs/J66/review.md | campaign minimap content stays 1x inside 2x frame, missing from the list | already done | row J67 (remaining screens) and the fact napoleon.ui.scale_2x_packs |
| J66-L2 | jobs/J66/review.md | tooltips, settlement panel and unit-card row not seen in game | already done | row J67 (names tooltips) |
| J66-L3 | jobs/J66/review.md | build reads Lora face from empire-remastered until J68 vendors it | already done | row J68 (vendor the Lora face; removes the fallback) |
| J66-L4 | jobs/J66/review.md | template route-1 probe undecided; per-context font-size probe not done | needs_brief row J96 | uiscale probes need PC; put in the uiscale row |
| J70-L1 | jobs/J70/review.md | setup.py check_watcher ok line shows last line of multi-line JSON | needs_brief row J94 | tools/verbs/setup.py check_watcher |
| J70-L2 | jobs/J70/review.md | test_jobs_hooks.py uses pre-J12 proxy/core fixture paths | needs_brief row J94 | tests/test_jobs_hooks.py:38-44 |
| J70-L3 | jobs/J70/review.md | two stale comments adapter.json:82 and cam_read.lua:3 | needs_brief row J89 | proxy/napoleon/lua/ctl/cam_read.lua:3 still names harness/core/campose.py; DLL input |
| J71-L1 | jobs/J71/review.md | PLAN section 6 still says J71 and J72 queued | already done | docs/plans/PLAN.md has no such sentence now (grep clean) |
| J71-L2 | jobs/J71/review.md | test_ctl_without_an_ini fails on project PC; isolate | already done | this job: commit 0d8e053 |
| J72-L1 | jobs/J72/review.md | report by orchestrator and Opus run, stated, no action | dropped | reason: reviewer: no action |
| J72-L2 | jobs/J72/review.md | one mid-run tests failure attributed to running game without evidence | already done | tests/test_pc_deploy.py:21-48 (J57) removes the running-game dependence |
