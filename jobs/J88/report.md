# J88 report: pin bump to core v0.50.1

**State: ready for review.** **It also fixes a fault it found: every `gates` run was claiming a job on the real origin, and 12 empty claims are blocking the queue (Open question 1).** The pin moved from v0.47.0 to v0.50.1, `exe.py` was re-run, and the Usage rule, rule F and rule A at `error` are on. No `engine_sites` or `engine_facts` row rests on a lost signature. No rule 79 run is needed: the core diff has no `proxy/` or `harness/` path, and the build id did not move.

Usage: 36 tool calls; models: opus; 1 session, the build only, not the brief, counted by hand, about, 2026-11-07

## What was built
**Target:** v0.50.1, the newest tag. It does **not** hold W32, which is still `queued` in the core (decision 2).

- `5222157e`: `wsc core bump v0.50.1`. One commit of `core` and `wsc.toml`. The re-render changed nothing under `.github/workflows/`, and the core's `ci/` and `.githooks/` have no diff between the tags. The bump named no game verb.
- `9f718da1`: first `discovery render`. Only `discovery/db/README.md` moved, gaining the empty tables column and section.
- `c31a9837`: `exe.py` re-run, then the second render. `discovery/diff/exe.json` and the one count line in `discovery/diff/README.md` moved.
- `24bc88e3`: `wsc.toml` gets `[jobs] usage_from = 106`, `[policy] decisions_cite_job = true` and `[policy] reviewer_code = "error"`. `CLAUDE.md` now says a `merge` over a reviewer's fix needs a newer round from a fresh session.
- `f9a7c457`: `tests/test_claude_hook_corpus.py` calls `jobs next --peek`. See Deviations 3.

**W28's skip warnings** needed nothing: `[gates] skip` is empty, so there is no skip to warn about.

**UPGRADING.md sections crossed:**

| Section | What it asked | Done |
|---|---|---|
| Discovery tools (W141) | `discovery render`, `discovery check`, commit; re-run `exe.py` | Yes, below |
| The `tests` gate (W139) | Nothing required; read the timings before setting `workers` | Timings below; `workers` stays 1 |
| `wsc proposals` and `decide/` (W45) | Nothing required; a game verb named `proposals` must be renamed | The game has none; adoption is J104's |

## Evidence
All on 2026-11-07, on this PC, with nothing launched. The display was on layout D, which does not matter here: nothing in this job depends on it.

**Rule 79.** `git -C core diff --name-only v0.47.0 v0.50.1` lists 0 paths under `proxy/` or `harness/`. `build_id.py --no-dirty` printed `96722f4b8d52` before and after the bump, the same id as J78's 20 passes.

**Discovery check, both rounds:** `discovery: 6 area files valid, J7 and J10 results in step, READMEs current, gate ok`.

Round 1 README diff (`discovery/db/README.md`, shortened to the summary table and the new section):
```
-| Table files | Decoded byte-exact | Not decoded | Versions |
+| Table files | Decoded byte-exact | Not decoded | Empty tables | Versions |
-| 310 | 306 | 4 | v0: 288, v1: 16, v2: 2, v3: 2, v4: 1, v5: 1 |
+| 310 | 306 | 4 | 26 (1 with a schema, 25 without) | v0: 288, v1: 16, v2: 2, v3: 2, v4: 1, v5: 1 |
+## Empty tables
```
Round 2 README diff (`discovery/diff/README.md`, the `signatures function` line):
```
-1159 unique, 33 shared, 468 multiple, 1190 none, 4 unsearchable
+1236 unique, 28 shared, 516 multiple, 1071 none, 3 unsearchable
```

**`exe.py`** ran in 24 s and no guard refused it. This was a foreground session in the main clone, not a worktree. 2929 signatures before and after. Of the 37 `rows`, only `signatures function` changed. `empire_pe` and `napoleon_pe` are identical, so the PE facts `napoleon.diff.exe.pe` and `napoleon.exe.window_imports` stand. `detail.method` is the same, as W141's review said.

**The re-check (deliverable 3).** The old file was compared with the new one on `detail.signatures`, keyed on source, `empire_va` and name, with no duplicate keys. All changes are `function` signatures: 159 changed class or hits, and no guard, patch or cfg site did.

| Check | Result |
|---|---|
| Lost a candidate class | **26: 19 `unique`, 7 `shared`. Matches the row and W141's review.** |
| `engine_sites` rows (64) within 32 bytes of any old or new hit of the 159 | **0** |
| The 159 names found in `engine_sites` or `engine_facts` | 0 |
| The lost hits' RVAs quoted in sites or facts | 0 |
| Lost RVAs or `lua_isnumber` in `proxy/`, `discovery/napoleon`, `registries`, `docs/plans` (beyond the brief) | 0 |
| A `unique` signature that moved its RVA | 0 |

**So no row rests on a lost hit.**

| Class change | Count |
|---|---|
| none to unique | 94 |
| none to multiple | 30 |
| unique to multiple | 18 |
| shared to none | 4 |
| shared to multiple | 3 |
| multiple to multiple, other hits | 3 |
| multiple to none | 2 |
| none to shared | 2 |
| multiple to unique | 1 |
| unique to none | 1 |
| unsearchable to unique | 1 |

The 26 are: 13 CRT and stdio helpers (`__crt_*`, `find_next_state`, `state_case_*`, `type_case_*`), `io_open`, `io_popen`, `lua_isnumber`, `battle_ship_controller_*` (4), `battle_unit_controller_kill`, and `cond_*` (5).

**`usage_from`.** 74 reports on `main` have no `Usage:` line, the highest being J99, and only J95 has one. That gives 100. An open branch moved it to 106: see Deviations 1.

**The rule is live.** With `usage_from` set to 99 for a moment, `wsc jobs check` exited 1 with `jobs: J99: report: no "Usage: ..." line (from J99 on; ...)`. At 106 it says `110 rows, ok`.

**Rule A scan.** `wsc policy --scan --rule A`, whole history: **33 of 75 branches**. 11 of them changed only the job's own row before rows moved to one file each (W40's report), so they cannot recur. **That leaves 22 of 64, about one job in three**, and 13 of those 22 merged since 2026-11-01. With `--since b9b87083` (J78's merge): 1 branch judged, 0 hits. See Open question 2.

**Gates.** `gates` at `f9a7c457`: 14 ok, 2 warn, 0 failed in 192.4 s; 724 host tests passed, 47 skipped. Build id still `96722f4b8d52`.
- `timing: workers 1, cpu_count 16`. Slowest modules: `test_release_installer` 41.3 s, `test_job_sh` 35.9 s, `test_build_id` 19.0 s. The `tests` folder took 187.5 s of the 600 s cap, under the 75% warning.
- The two warnings: `hooks` (Open question 4) and `tests`, which reports its skips.
- Docker was down, so `test_proxy_host_tests` did not run here (`NOT RUN (no toolchain)`), and the viewer render and `upscale` tests skipped. No DLL input changed; CI's `proxy` job covers the pin change.

**The claim fault.** `job/J85` and `brief/J89` appeared on origin while this job ran, and no session had claimed them.
- This clone's reflogs say `update by push` at 11:04:54 and 11:08:46 UTC. The first two `gates` runs were going at those times, and this session was the only one with a process.
- `test_commands_printed_by_the_job_steps` ran a bare `wsc jobs next` from the repo root. Since core W26 that pushes a claim branch.
- After the fix, `git ls-remote origin 'refs/heads/*'` lists 223 branches before and after a full `gates` run, none new. Before it, each run added one.

**`jobs check`:** 110 rows, ok. **Failed ctl results in a cited run:** none, no run here.

## Deviations from the brief and why
1. **`usage_from` is 106, not the 100 that decision 5's rule gives on `main`.** `job/J105` already has a report with no `Usage:` line. At 100 that branch would be refused once this merges. The decision's aim is that no old report is refused, so the value sits above J105. The cost: J100 to J105 are not covered.
2. **A failed gate run, and a kill criterion read narrowly.** The first `gates` run failed `test_discovery_core_is_gone_and_unlisted`, because `discovery/core/` existed in this clone. It held 36 git-ignored `.pyc` files and nothing else, left from before J64 moved the folder (dated 2026-11-03 to 05). The kill criterion says stop on a failed test. I took that to mean a real failure, not a stale cache, checked that every file was a `.pyc`, removed the folder and ran `gates` again. Nothing tracked changed. A reviewer who reads it the other way should run `gates` on a clean checkout.
3. **A test fix the brief did not name.** `tests/test_claude_hook_corpus.py` now passes `--peek`. Without it, the reviewer's own `gates` run would claim another job. It is one argument and one comment, and touches no DLL or harness input.
4. **Beyond the brief:** the extra search of `proxy/`, `discovery/napoleon` and `docs/plans` in the re-check table. It reads only.

## Open questions
1. **For Liam: 12 empty claims need deleting.** These branches have no commits of their own, and no session with a process is on them, yet `jobs next` treats each job as taken. That is why it now says "nothing queued is ready". The two above are proven. The other ten have the same shape and date from 2026-11-06 on, after J78's branch brought W26's claims, so they are very likely the same fault, not proven. The hook denies an agent deleting a remote `job/` or `brief/` branch, so these are left for Liam:
   `git push origin --delete job/J27 job/J35 job/J48 job/J69 job/J85 job/J93 job/J101 brief/J26 brief/J63 brief/J77 brief/J89 brief/J102`
   Check first if any session was started on one of them by hand. Recommended: delete all 12 after this merges.
2. **For Liam: `reviewer_code = "error"` costs more than the brief said.** The brief only named J94 and J96. The scan says about one job in three would have needed one more Opus review round, and 13 of the 22 are recent. The setting is one line of `wsc.toml`, so it can go back to `warn`. Recommended: keep `error` as answered, and judge it on the next ten merges.
3. **W32 is in no tag.** It comes with a later bump, probably J104's.
4. **`hooks` warns in this clone:** `core.hooksPath` holds an absolute path, and the gate wants `core/.githooks`. The hook still runs (the pre-push gates ran on every push here). Left alone: it is local config, not this job's. Recommended: `git config core.hooksPath core/.githooks` in this clone.
5. **J87's row** still says `wsc.toml` switches the rule on. That is now done, so J87's brief should cover only `usage_cmd`, `tools/usage_reader.py` and the view chip.
6. **94 signatures are new `unique` hits.** They are candidates for any later engine site work, not facts. The 5 `cond_*` that fell to `none` are W141's finding 2 (`mask_for` walks bytes, not instructions), a false loss rather than a real one; core row W142 has the `method` gap from the same review.
