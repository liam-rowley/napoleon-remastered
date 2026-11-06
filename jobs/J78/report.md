# J78 report: pin bump to core v0.47.0

**State: ready for review. Rule 79's 20 passes are in.** Run 20261106_j78pc: 20 of 20 `pass` on build `96722f4b8d52`, watcher 1.5.0, no flake. **Two start-up crashes happened during it** (c0000374, both retried): see Evidence. The crash still reproduces on the W33 DLL.

Sessions: the build session stopped at the watcher update (head `6e96ce56`) with no report. This session (`02e3eff3-6149-4617-9501-5df0fb91a3cb`) ran the checks, the build, the passes and this report. The commits before `0130c00c` are the build session's; what is said about them here comes from their messages and diffs.

## What was built
**Target:** v0.47.0, the newest tag when the build started. v0.48.0 has appeared since (seen 2026-11-06 about 21:05 UTC) and was **not** taken, as the brief says: new run, new budget.

- `7aacb3ff` (deliverable 4, R4, J89): the J9 probes into `proxy/napoleon/lua/probes/`, the generated `probe_safe_list.lua` with a check, the `getters.lua` refusal of a missing list, J46's dead loop gone. **J89's three items are folded in.**
- `a77e66df`: the pin. Moved by hand, because the old pin has no `core bump` verb.
- `37bbf37e`: 0.24.0 `commit_msg_hook = true`; 0.26.0 the bootstrap `pull_request` trigger removed from `ci/policy.yml.in`; 0.36.0 `doc_paths` and `verified_dates` cleared by fixing, no skip; 0.38.0 `{{wsc proxy_map step=dll}}` in `ci/gates.yml.in` and `[agent_settings] safe` with `exact_only`; W18's headless doc.
- `d0c9438b`: 0.34.0 and 0.40.0, the `proxy.file_rules` and `proxy.dxvk_wndproc_fix` rows. `release/napoleon` now uses `proxy.file_rules`, which **ends the D46 stop-gap**: the shipped UI rules leave `dev.file_rules`.
- `4bb474f3`: W9 in the consumer's rule 79 (flakes, the watcher's bytes, one DLL, the evidence sha); `acceptance.max_flakes` 1.
- `6e96ce56`: discovery READMEs rendered, the new keys left out of the player ini (same reasoning as `controls.gestures` in J64: inert for a player), the acceptance fake gives a real shot.
- `0130c00c`, this session: the ledger lines and the run folder. Then fact `napoleon.proxy.init_heap_corruption` notes (deliverable 5, `state` untouched) and this report.
- No game `tools` row for `dump_read.py` needed retiring: `tools/` has no copy.

## Evidence
**Rule 79.** Build `96722f4b8d52` (`build_id.py` the same before the build, after it, and after the last commits), DLL sha256 `5dac94823fc5`, watcher 1.5.0 (installed by Liam, kit `harness_20261106T162932Z_6e96ce56fed1`), proxy kit `kit_20261106T180846Z_6e96ce56fed1`. 20 ledger lines, 18:22:25 to 20:57:28 UTC, all `pass`, no false step, no failed ctl result, passes about 8 minutes. `policy --branch job/J78 --base origin/main`, judged with main's rules (core 0.30.0), no longer names rule 79 once the ledger is committed. Pass 1's line names the real build, so 20 passes, not 21, were enough.

**Display layout**, same before and after: DISPLAY1 2560x1440 primary at 0,0 (the MSI), DISPLAY10 3840x2160 virtual at 3839,2160, DISPLAY2 2048x1152 at -2560,327. No change during the run: no exit 2160 and no display refusal.

**Start-up exits retried, per pass: pass 14: 1; pass 18: 1; the other 18 passes: 0.** That is 2 deaths in 122 launches (`watcher.log`, 18:14 to 20:58 UTC).

| Pass | Launch | pid | Time (UTC) | Dump |
|---|---|---|---|---|
| 14 | first of the pass | 5296 | 19:59:43 | `20261106T195943Z-p5296_c0000374.dmp`, 5.5 MB |
| 18 | `naval_small` relaunch | 19876 | 20:36:06 | `20261106T203606Z-p19876_c0000374.dmp`, 5.5 MB |

Both: c0000374 at ntdll+0xfd71f, last status `starting DllMain`, `ctl.py` retried and the retry ran. A retried exit is not a W9 flake (that needs two lost in a row), so no flake line was written and the streak stands. The brief allows these (PC test, step 5).

- **Against earlier counts:** 1.6% here. J101's table has 1.5% (2/133) for this layout since 2026-11-05 and 1.2% overall; J64's run on the old DLL had 1/127. J67's 6 of 18 is far higher but was on the other layout. **So there is no sign W33 lowered the rate.** It does not prove anything either way: one layout, a small sample.
- **New for J101:** both logs have one thread and end 6 to 7 ms after `init done`, before the first `Direct3DCreate9`, which a healthy launch of this build reaches about 0.94 s after `init done`. W33 starts the dev threads there, so **the proxy's dev threads cannot have caused these two**, which counts against the leading suspect. A thread that logs nothing is not excluded, and no dump was opened (J101 measures first). This is two deaths.
- **Dumps:** the in-process pair moved at uninstall to `C:\napoleon_remastered_pc\_to_delete\uninstall_20261106T210043Z\napoleon_remastered\dumps`. WER keeps only 5, so its full dumps of both are copied to `C:\napoleon_remastered_pc\_scratch\j78` (about 190 MB each). The dead launches' logs are in `harness/runs/20261106_j78pc/attempts/`.

**Wndproc guard (0.40.0):** `backend: wndproc guard on DXVK's imports: 4 slots` is in the last launch's `proxy.log`, read at 20:57 UTC. It proves the guard loads, nothing more; J16 has the resolution proof.

**Observer:** only `explorer` on the virtual display for the whole run. Its one `Empire.exe` line (18:07:29) is before the install: see Open questions 5. Shots: all `shot_match` steps passed; I looked at one, pass 18's `naval_small_deploy.jpg` from the retried launch, a normal naval deployment.

**Preflight:** exe vanilla, sha1 `9aebcd2172f2`; no foreign files; `not_running`; no lock; 5 minutes after the install, CPU about 3%. `pc_deploy status` showed `BAD napoleon_remastered.ini` after the run: the diff against the kit is exactly the 9 launch keys acceptance announced, so that is expected. After `uninstall`: game folder identical to the pre-install snapshot (1564 files), exe vanilla, no lock.

**Gates:** the first full run this session failed `tests` on the 600 s cap: `timed out`, no test failed (see Deviations). After the Docker build: 15 ok, 1 warn, 0 failed in 547.5 s, 724 host tests passed, 46 skipped (viewer render, numpy, Pillow, Playwright). `build.sh --docker all`: host tests passed, 17 core, 0 game, the first run on this core.

**`wsc ci check-settings`:** required checks gates, policy, proxy, harness-windows; `allow_auto_merge` true; 0 problems, 1 note (workflow job `viewer` is not a required check).

**`docs/DECISIONS.md`:** 30,703 bytes against the 30,720 cap: **17 bytes left**, not the 150 the brief had. No new row fits.

**CI:** run 42293279467 on `0130c00c` (the evidence commit): gates, proxy, harness-windows success; viewer skipped. Run 42252854783 on `6e96ce56` was cancelled by that push. The draft pull request and the final head's run come after this report: read them on the pull request.

## Deviations from the brief and why
1. **`gen_tables.py --exe` not run.** The copy of the exe to a staging folder was denied by the session's permissions, and I did not work around it. Still to do: stage a copy, then `python3 core/proxy/tools/gen_tables.py --check --exe <copy>`.
2. **`d3d9.map` is not attached to releases (0.38.0, part done).** CI keeps `proxy-map-<build id>` for 90 days, but `core/docs/PROXY_BUILD.md` leaves attaching it to the consumer's release builder and nothing in `release/` does. Not added here: it would be a new change after the run. No release is planned yet; it needs a row.
3. **20 passes, not the brief's 21:** W9's preflight is in the pin and pass 1 names the build (checked on its line).
4. **Gates order.** The first full run hit the cap, so the Docker build ran before the second gates run, not after. Docker came up during the first run and `tests/test_proxy_host.py` builds when Docker answers, so a cold image is the likely cause, as J64 saw; I did not prove it. Warm, `tests` took 542 s of 600 s, so the margin is thin. The cap was not edited.
5. **`core bump` by hand:** the old pin has no such verb.
6. **The observer ran through the PowerShell tool:** the session's isolation guard refused `powershell` under Bash. The script is read-only and has no git in it.
7. **Failed ctl results in the cited run:** none. The two failed `launch` jobs above are the only failed jobs.

## Open questions
1. **Core row: `acceptance.py` loses a retry on a pass's first launch.** `start('launch', ...)` drops the return value, so `pass_14.json` has no `retried_after` and looks clean, and `evidence.launches` lists survivors only (120, not 122). The count here comes from `watcher.log`. Anyone counting from pass files undercounts, J101 included. Recommended: a core row to record every launch attempt in the pass file.
2. **Core row: `wsc discovery render` still writes the old `discovery/core/` names,** so that prefix went into `[docs] path_ignore`.
3. **Core row: `doc_paths` crashes on a missing path inside the submodule.**
4. **For Liam, the new decision row:** the row's "Opus across the board, replacing D52" waits for the decision row files, the first new row after them. It cannot go in `docs/DECISIONS.md` (17 bytes left).
5. **`Empire.exe` in observer logs.** `tests/test_release_installer.py` `test_refuses_while_the_game_runs` runs a renamed `PING.EXE` called `Empire.exe`; that is this run's 18:07:29 line, during gates. It **may** also be J64's unexplained `Empire.exe` at about 19:21 (open question 1 there), if gates ran then. I did not check that.
6. **v0.48.0** is out: a later bump, not this job.
7. **W42:** whether a skipped `harness-windows` counts as passed can only be read on a docs-only pull request; this one is not. Still open.
8. **The branch against `main`:** checked at this report, `git log HEAD..origin/main` empty. The reviewer re-checks before queueing the merge (brief, traps 2 and 3). `core`, `proxy` or `viewer/pins.json` output there means a new run.
9. Worktree `.claude/worktrees/J78` carries a stale lock from pid 17704, a process that no longer exists. Harmless; `git worktree unlock` when it goes.

## Decisions as one file per row
Two pull requests **after this bump merges**, not opened here. A pull request is judged with its base's rules, and the old rules refuse a head with registry decisions, so neither can ride this bump. Both are `meta/`: Liam merges (D50).

**1. `meta/decisions-registry`.** Judged by main's `meta` globs and `policy`.
- `python3 core/wsc.py reg migrate decisions --from-md docs/DECISIONS.md`, then the same with `--check`.
- `wsc.toml`: `[registries] decisions = "core:decisions"`; `[storage] dir = [..., "decisions"]`; `[policy] decisions = "registry:decisions"`, `decisions_retired = "docs/DECISIONS.md"`; `"registries/decisions/*"` added to the `plan` and `meta` globs.
- Every row line of the Markdown file stays; its prose may change. From this merge `policy` refuses any change to the file's table on every branch, so a branch cut before it cannot land a row: merge `main` first.

**2. A second `meta/` branch.** Judged with the rules step 1 merged.
- Delete `docs/DECISIONS.md` and the `decisions_retired` key.
- `CLAUDE.md`, `README.md` and the gates that name the file change here: grep for the old claim.

Old rows keep their numbers; a new id is `D<yymmdd>-<4 hex>` from `python3 core/wsc.py reg add decisions --mint who=... decision=... reversible=yes|no`. Size today: 30,703 of 30,720 bytes.

## Fix round 1
Session `240bfc32-d735-4654-94bf-58d001513ec8`, from review round 1. No PC run, no launch, no `job.sh`. `build_id.py` said `96722f4b8d52` before, after every commit and after merging `main`. Earlier sections stay as written; **where this section differs, this section is right.**

### Blockers
**1. The D46 ending.** "Ends the D46 stop-gap" (What was built) overstated it. Corrected: the shipped ini no longer sets a dev key, and the ending is otherwise as follows.
- `release/napoleon/release.json` sentence deleted and `release/README.md` corrected: `99794157`. No test added: `value_problems` already fails a dev key in a component and a stale `allowed_dev_keys` entry.
- **`upscale/pc/play.py`, `tests/test_play.py`, `upscale/README.md`: not moved, on purpose.** W33 asked for the move; the brief keeps `dev.file_rules` for dev launches, and a play install is one (a kit install that also sets `dev.skip_intro`). No Napoleon launch has used `proxy.file_rules`, so moving it now would put Liam's only proven 2x route on an unproved one, and this round has no PC run. Those files stay true as they are. Revisit once J106 has passed.
- **New deviation 8: the D line that supersedes D46's exception is not written.** `docs/DECISIONS.md` has no room. It waits for the row files, beside the Opus row: J105.
- **New deviation 9: W33 record 3, the release-ini launch, was never run.** Every J78 launch had `proxy.file_rules` empty and `dev.file_rules` set, so **the 20 passes say nothing about the shipped route on Napoleon.** Core's smoke proves the mechanism on the stand-in only. It needs a PC launch before the next release: J106. Fact `napoleon.ui.templates_route` now says so (`c7ee5867`).

**2. The decisions recipe.** "Judged by main's `meta` globs" was unchecked and wrong. The corrected recipe is below and replaces "Decisions as one file per row".

### Should-fix
**3. W33 records 1, 2 and 4.**
- **Record 1, holds:** both dead launches and the last launch log `patch_engine: protections restored on 2 page(s): 0x00d27000=0x20 0x00d86000=0x20`, and none has a `left changed` line (`attempts/pass_14/attempt_1/proxy.log:131`, `attempts/pass_18/attempt_1/proxy.log:131`).
- **Record 2, holds, one launch:** quoted here because that log will go; the copy into the repo was denied this session, so it is not committed. Last launch of the run, `_to_delete\uninstall_20261106T210043Z\napoleon_remastered\logs\proxy.log`:
  ```
  177: 2026-11-06T20:57:09.072Z [INFO ] [t26084] Direct3DCreate9(sdk=32) -> 0c094800 [dxvk]
  192: 2026-11-06T20:57:09.075Z [INFO ] [t26084] thread: dev.state started (tid 21000)
  193: 2026-11-06T20:57:09.075Z [INFO ] [t26084] thread: dev.ctl started (tid 19620)
  ```
- **Record 4, against run 20261103_j30acc2:** 12 deaths at `starting DllMain` in 17 passes there (10 retried in passes 1 to 16, 2 in a row failing pass 17), 2 in 20 here, both before the first `Direct3DCreate9`. **This does not show W33 helped.** J101's table has layout M at 0 of 4 launches and D at 7.4% for the period holding j30acc2, so that run was almost surely on D (inferred; its pass files hold no layout or launch count), and this one was on M. Fact updated: `c7ee5867`.

**4. Display sizes.** Evidence's sizes were wrong. Right: DISPLAY1 3840x2160@240Hz, DISPLAY2 2560x1440@144Hz, DISPLAY10 3840x2160@60Hz, from the display tool in `attempts/pass_14/attempt_1/job_output.txt`. Still layout M. Run README fixed: `932a2773`.

**5. Deviation 2's reason.** "It would be a new change after the run" was wrong: `release/` is not a DLL input. The real reason: no release is planned, and how a builder fetches the CI artifact is a design question. J108.

**6. `doc_paths`.** "Cleared by fixing, no skip" overstated it. `[docs] path_ignore` also hides four paths that were this repo's and are gone: `tools/jobs_hooks.py`, `tools/pr_policy.py`, `docs/BACKLOG.md`, `uikit/napoleon/LOCK.json`. Left in place, repointing is J110.

### Other claims the review named
- **Dev threads (Evidence, point 4).** Corrected in the fact (`c7ee5867`) and the run README: no proxy thread of any kind existed in these two deaths, which is stronger than "dev threads". It also **does not clear the proxy**: its DllMain work ran on the dying thread, and non-proxy threads are unseen. "Counts against the leading suspect" holds for threads only and says nothing about init.
- **"About 0.94 s".** One launch, and that figure is the wndproc guard line. That launch logs `Direct3DCreate9(` 1.06 s after `init done`.
- **"724 host tests passed, 46 skipped".** 724 is the number run, skips included.
- **Deliverable 5's comparison.** The brief named J64's 7 on 2026-11-04; the report used 1/127 and did not say why. The reason: 1/127 is run 20261105_j64pc7 on J78's layout, and 2026-11-04 falls where J101 has M at 0 of 4, so the 7 is a D figure. Same conclusion either way.
- **Open question 7 (W42).** Out of date for the head the review read. This round changes `release/`, which starts `harness-windows`, so this head does not repeat that skip: read it on the pull request.
- **Open questions 1 to 4.** Their rows are filed separately on `plan/` branches, not here (Liam's instruction). J105 to J110 landed on `main` in #224, merged here at `26689fcb` (rows only).

### Left open
- `gen_tables --exe` (J107), `d3d9.map` on releases (J108), the `tests` gate at the cap (J109), all as above. Review findings 7 and 8 are later rows.
- No committed evidence for the preflight CPU figure, the 9-key ini diff or the 1564-file compare. Unchanged; the review says none decides anything.
- J105's row cites "Decisions as one file per row"; it should be read with the corrected recipe below.

### Decisions as one file per row, corrected: three `meta/` pull requests
All after this bump merges, all Liam's to merge (D50), in this order, each cut from `main` after the one before it merged. A pull request is judged with its base's rules, so the glob has to be on `main` before a row file can be added.

Checked 2026-11-06 on this branch, nothing committed: `policy.allowed` for each file list; `reg migrate` and `--check` (66 rows, every one found); `registries`, `doc_paths`, `doc_size` and `tools` gates after step 2; `doc_paths` and `tests.test_repo_rules` after step 3. The checks of step 3 are what added its last two bullets. Not checked: a real `policy` run on such a branch.

**1. `meta/decisions-glob`.** Only `wsc.toml`: add `"registries/decisions/*"` to the `plan` and `meta` globs.

**2. `meta/decisions-registry`.** Judged with the glob from step 1.
- `python3 core/wsc.py reg migrate decisions --from-md docs/DECISIONS.md`, then the same with `--check`.
- `wsc.toml`: `[registries] decisions = "core:decisions"`; `[storage] dir = [..., "decisions"]`; `[policy] decisions = "registry:decisions"`, `decisions_retired = "docs/DECISIONS.md"`.
- Every row line of the Markdown file stays; its prose may change. From this merge `policy` refuses any change to the file's table on every branch, so a branch cut before it cannot land a row: merge `main` first.

**3. `meta/decisions-retire`.** Judged with step 2's rules, which let the file go.
- Delete `docs/DECISIONS.md` and the `decisions_retired` key.
- Repoint `CLAUDE.md`, `README.md`, `docs/plans/PLAN.md` and `docs/plans/UI_PIPELINE.md`: `doc_paths` fails on each otherwise.
- `design/napoleon/LANGUAGE.md:3` names the file too and `design/` is outside the `meta` globs, so add `docs/DECISIONS.md` to `[docs] path_ignore` here, or add that file to the `meta` globs in step 1.
- `tests/test_repo_rules.py` `test_no_gate_silenced_without_a_decision` reads the file and errors without it: point it at the rows.

Old rows keep their numbers; a new id is `D<yymmdd>-<4 hex>` from `python3 core/wsc.py reg add decisions --mint who=... decision=... reversible=yes|no`. The first new rows are the Opus row and the D46 line (J105). Size today: 30,703 of 30,720 bytes.
