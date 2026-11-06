# J78 review

## Round 2 (2026-11-06, branch job/J78 at 1fa1687417f1970170f0cf75af88ad4cafcda83f)

**Verdict: merge.**

Fix round 1 answers both blockers and all four should-fix items of round 1, and what it says checks out against the logs and the tree. The 20 passes still count. Nothing below needs a code change, a PC run or a new build. No launch and no `job.sh` in this round; PC files were only read.

### Machines
- **Build id:** `build_id.py` says `96722f4b8d52` on this head, the id on all 20 ledger lines. `origin/main` is `888aa568`, the merge base, so this head is also the merge result: `git log HEAD..origin/main` and `git diff --stat HEAD...origin/main -- core proxy viewer/pins.json` are both empty.
- **CI on `1fa16874`, run 42301747954 (push):** `gates` success (684 host tests passed, 27 skipped), `harness-windows` success, `changes` success. `proxy` and `viewer` skipped: their inputs did not change, and the id is the one proxy passed for in run 42293279467.
- **`policy` in CI: skipped, the pull request is a draft. That is not a pass.** It has still judged nothing here; the real run is on the head this review pushes, after `gh pr ready`.
- **`policy` locally, before this round:** refused only for the old verdict and the row not being `done`. Rule 79 not named.
- **`wsc gates` locally:** 14 ok, 1 warn (`hooks`, this worktree's path form), 1 failed: `tests` timed out at 600 s, as the report says. The same discovery with no cap, on the same head: 724 tests, OK, 47 skipped, 545.1 s, exit 0. So no test fails, including the Windows ones CI skips (`Play`, `InstallPacks`). See later item 3 for the time.
- **Ledger:** the diff against `main` is 20 added lines, nothing removed; `harness/acceptance/baseline.json` and `shots/` unchanged. Nothing under `harness/acceptance/` moved in the fix round.

### Round 1's findings
1. **D46, answered.** `release/napoleon/release.json` and `release/README.md` are corrected, and no other "until a DLL job" sentence is left in `release/`. Deviations 8 and 9 name the missing D line and the missing release-ini launch; `release/napoleon/components.json` sets `proxy.file_rules`; `allowed_dev_keys` is `{}`, held by `tests/test_release.py`. The fact `napoleon.ui.templates_route` now says no Napoleon launch has used the key. J105 carries the D line and J106 the launch.
2. **Decisions recipe, answered, and now run for real.** The report says a real `policy` run was not done, so I did it on throwaway local branches, never pushed and since deleted, each judged with the step before as its base: step 1 ok (1 file), step 2 ok (67 files: `wsc.toml` and 66 rows, `--check` finds all 66), step 3 ok with the file and the key gone. Later item 2 is the one slip.
3. **W33 records 1, 2, 4, answered.** Record 1: `protections restored` at line 131 of both attempt logs and line 131 of the last launch's, no `left changed`. Record 2: the three lines quoted in the report match the log under `_to_delete\uninstall_20261106T210043Z` exactly, read today. Record 4: J101's table has M at 0/4 and D at 7.4% for that period, so "not W33's to claim" is the right reading, and it is marked as inferred.
4. **Display sizes, answered.** They match `attempts/pass_14/attempt_1/job_output.txt` lines 4 to 6.
5. **Deviation 2's reason, answered.** J108 owns it.
6. **`doc_paths`, answered.** The four paths are named, and J110 owns repointing them.

Round 1's other claims: 1.06 s and 0.94 s match the log (0.940 and 1.063 s after `init done`); 1/127 is J64's run, and J67 ran on D as J101 says.

### The points raised for this round
- **`play.py` left on `dev.file_rules` until J106: a fair answer.** The brief keeps that key for dev launches, while W33's report asks for the move, so the two disagree and the report says which it took and why. It costs nothing: `upscale/pc/play.py:251` is a kit install that normally sets `dev.skip_intro` too, so the dev side is on anyway, and since W33 its threads start at `Direct3DCreate9` either way. The audit's C4 risk was the release, and the shipped ini no longer sets a dev key. Moving Liam's only proven 2x route onto a key no Napoleon launch has used, in a round with no PC, would be the worse order. Later item 1 is the gap.
- **Report sections above "## Fix round 1": acceptable.** The procedure has a fix session append, not rewrite, and the section says at its top that it wins. I checked each false claim round 1 listed, and each has its correction there. The cost is that the top of the report still reads "ends the D46 stop-gap" and carries the two-pull-request recipe. J105's row already states three pull requests, so the recipe cannot mislead through the queue.
- **Local `tests` gate over the cap: not a blocker.** `gates` is the required check and is green on this head. Its local failure is time only, shown by the uncapped run above. J109 owns it; the cap is not edited.

### Blockers
None.

### Should-fix
None.

### Later
1. **"Revisit once J106 has passed" has no owner.** `jobs/J78/report.md`, Fix round 1, leaves `upscale/pc/play.py:251`, `tests/test_play.py` and `upscale/README.md` to J106, but `registries/jobs/J106.json` does not mention them, and this report stops being read at `done`. Fix: a `plan/` row edit adding the move to J106. It is outside this job's row, so not done here.
2. **Recipe step 2 lists its commands in an order that refuses.** `wsc reg migrate decisions` run first says `unknown registry decisions`; the `[registries]` line in `wsc.toml` has to come first. The error is clear and nothing is harmed. J105's brief should give the right order.
3. **J109's row is out of date, and the report overstates it the other way.** Its figures are 542 s and 577.7 s. Since then: 602.8 s (fix session) and 545.1 s (here), with a capped gate run timing out on the same head. So "no longer fits the cap at all" is too strong: the time swings by about 60 s around the cap. J109 should measure that spread first.
4. **"Must land before the next release" (J106) is prose.** Nothing stops `build_release.py --record` before J106 has passed. Worth pairing with J108's refusal.

### If this merges
It changes rules other branches meet: `commit_msg_hook`, W9's rule 79 and base-judged policy. `job/J78` is the only open pull request, so nothing is stranded today.

## Round 1 (2026-11-06, branch job/J78 at 4c3dbd7efc92fc811ca5e6256924015cce2d0968)

**Verdict: merge after fixes.**

The bump and the 20 passes hold up. Rule 79 is met and nothing below needs a new PC run or moves the build id: `release/`, `jobs/`, `harness/runs/*/README.md` and `registries/jobs/` are not DLL inputs (`build_id.py --inputs`). It cannot merge this round because the D46 ending is half done and left unreported, which needs changes outside the job folder, and because the decisions recipe as written would be refused by `policy`.

### Machines
- `wsc gates` on this head: 14 ok, 1 warn (`hooks`, this worktree's path form), **1 failed: `tests` hit the 600 s cap, with no test failing**. The same discovery run with no cap: 724 tests, OK, 48 skipped, 577.7 s. CI's `gates` is green on this head. See finding 9.
- `policy --branch job/J78 --base origin/main` (main's rules, core 0.30.0): refuses only for the missing review and the row not being `done`. Rule 79 is not named.
- Main's rules do not contain the new W9 checks, so I ran the branch's own `collect_acceptance` and `acceptance_problems` from `tools/gates/pipeline.py` against this head: no problems.
- `wsc ci check-settings`: 0 problems, 1 note (`viewer` is not required). Matches the report.
- CI on `4c3dbd7e`, run 42294648414 (push): `gates` and `changes` success. `proxy` and `harness-windows` skipped because their input trees passed in run 42293279467 on `0130c00c` (the `changes` log says so for `harness`; `proxy=false`), and that run shows both as success. **`policy` is skipped because the pull request is a draft. That is not a pass and it has not judged this branch in CI.** The real run comes with the merge order in a later round.
- `git log HEAD..origin/main` is empty at this review: main is `a1e917a4`, the merge base.

### Blockers
1. **The D46 ending is half done, and the report does not say so.** `jobs/J78/report.md:13` says the change "ends the D46 stop-gap". Core's `jobs/W33/report.md`, "What napoleon must do (J78)", lists what that takes, and these are missing and not named as deviations:
   - `release/napoleon/release.json:19` still says "(the UI scale stop-gap sets dev.file_rules until a DLL job gives it a player key)". W33 says to delete that sentence.
   - `release/README.md:52` still says "Today: `dev.file_rules` (D46)", which this branch makes false: `allowed_dev_keys` is now `{}`.
   - `upscale/pc/play.py:251` and `:267`, `upscale/README.md:48` and `:55`, `tests/test_play.py`: W33 says to move the same switch. Move them, or say why not. The brief keeps `dev.file_rules` for dev launches, so "play.py is a dev launch and stays" is a fair answer, but it has to be given.
   - The "D line that supersedes D46's exception": no room in `docs/DECISIONS.md`, so it must be named as waiting for the row files, beside the Opus row.
   - W33 record 3, a release-ini launch (no `dev:` line, no `thread:` line, `redirect: 1 rules from ... (proxy.file_rules)`, the 2x UI), was never run. Every J78 launch has `proxy.file_rules` empty and `dev.file_rules` set (`attempts/pass_14/attempt_1/proxy.log`), so the 20 passes say nothing about the shipped route on Napoleon. Core's smoke proves the mechanism on the stand-in (W33 launch 9). I rendered the player ini: `[proxy] file_rules=napoleon_remastered\ui\ui_scale_2x.rules`, no `[dev]` section, `value_problems` and `shipped_ini_problems` empty, so the move itself is right. What is missing is the in-game proof, and the report must say so. It needs a PC launch, so it needs a row that lands before the next release.

   Fix: delete or correct the first two, answer the third, name the fourth and fifth under Deviations.

2. **The decisions recipe fails at its first step (deliverable 6).** `jobs/J78/report.md`, "Decisions as one file per row", step 1 adds `registries/decisions/*` files and adds that glob to `meta` in the same pull request. A pull request is judged with its base's rules (`core/warscape/policy.py:357`), and the `meta` globs on this head do not match those files: `policy.allowed('registries/decisions/D1.json', meta)` is False, for `plan` too. So `meta/decisions-registry` is refused with "a meta/ branch may only touch repo infrastructure". The brief and core's `docs/CONSUMING_OPTIONS.md` have the same gap, so the builder copied it faithfully, but the report's line "Judged by main's `meta` globs" is the unchecked claim. Fix in the report: a first `meta/` pull request that only adds the glob to `plan` and `meta` in `wsc.toml`, then the two as written. That is three pull requests, all Liam's.

### Should-fix
3. **W33 records 1, 2 and 4 are missing from the report and the fact (`report.md`, Evidence).** The data is there. Record 1: `protections restored on 2 page(s)`, no `left changed` line (`attempts/pass_14/attempt_1/proxy.log:131`). Record 2: `thread: dev.state` and `thread: dev.ctl` at 20:57:09.075, after `Direct3DCreate9(` at 20:57:09.072, in the last launch's log under `_to_delete\uninstall_20261106T210043Z`. That log will go, so commit it or quote it. Record 4: the count against run 20261103_j30acc2 (10 retried exits in passes 1 to 16, and pass 17 failed on two in a row, per the fact). The report compares with J64 and J101 and not with this one.
4. **The display sizes are wrong in the report and in `harness/runs/20261106_j78pc/README.md:5`.** Both give DISPLAY1 2560x1440 and DISPLAY2 2048x1152. The display tool in the same run says DISPLAY1 3840x2160@240Hz and DISPLAY2 2560x1440@144Hz (`attempts/pass_14/attempt_1/job_output.txt`). DISPLAY2 at -2560,327 is only adjacent to 0,0 at 2560 wide, so the report's numbers look like scaled readings. The layout is still J101's M; only the sizes are wrong.
5. **The reason for deviation 2 does not hold.** "It would be a new change after the run" is not so: `release/` is not a DLL input, so attaching the map needs no new run. The deferral itself is fine (see point 3 below). State the real reason: no release is planned and how a builder fetches the CI artifact is a design question.
6. **"cleared by fixing, no skip" overstates `doc_paths` (`report.md:12`).** `wsc.toml` `[docs] path_ignore` also hides four paths that were this repo's and are gone: `tools/jobs_hooks.py`, `tools/pr_policy.py`, `docs/BACKLOG.md`, `uikit/napoleon/LOCK.json`. UPGRADING keeps that list for tokens that are not this repo's paths and says to repoint or mark the others. `docs/REVIEW.md` links the first one, and `tools/gates/pipeline.py` still names `UI_LOCK`. The brief allows `path_ignore` if needed, so say which entries are these. Repointing them can be a later row.

### Later
7. `core/harness/ctl.py:381` checks only `dev.file_rules` against the kit. A launch using `proxy.file_rules` gets no such guard. Core row.
8. `value_problems` does not hold `proxy.dxvk_wndproc_fix` to its release value when a component sets it (tried: no error). No component does. `required` in `release.json` would close it.
9. The local `tests` gate now sits at the 600 s cap: 542 s for the builder, 577.7 s uncapped here, and a timeout in `wsc gates`. Two of two full local sessions have hit it, so it will stop other agents. Do not edit the cap; a row should shorten or split the slow tests (`tests/test_proxy_host.py` is the report's suspect, unproved). The report's "724 host tests passed, 46 skipped" also reads wrong: 724 is the number run, skips included.

### The points raised for this review
1. **Two retried deaths: allowed, and counted correctly.** From `watcher.log`, 18:14 to 21:00 UTC: 122 launches started, 120 ok, 2 failed, at 19:59:50 and 20:36:09, both `HEADLESS FAILED ... last status: starting DllMain`. No other owner launched, no watchdog event. PC test step 5 and deliverable 5 name exactly this exception, so they govern the general "a crash" in the kill criteria. Core's `classify` makes a flake only when both attempts of a launch are lost; here each retry ran. `pass_14.json` indeed has no trace (no `retried_after`, no `attempts`) because `start()` drops the return value at `core/harness/acceptance.py:269`. Pass files hold 120 launches. Rule 79 counts passes and all 20 are `pass` with every step true on one build, one DLL sha and one watcher sha; `evidence_sha256` matches all 20 committed files and `watcher_sha` matches `core/harness/watcher.ps1`.
2. **`gen_tables --exe`: can merge without it.** The reason is evidence, not the denial. The run's exe has the pinned sha1 (`9aebcd21...`, re-read today), `engine_sites` did not change on this branch, and every launch checks each site against the live image (`exe_guard: match`, `patch_engine` lines). `--exe` reads the same rows against the same bytes and is weaker: it cannot see relocations. It was a brief item, the report names it, and nobody routed around the guard, including here. The exe check stays open and needs an owner: fold it into the next PC job, with a copy Liam allows.
3. **`d3d9.map`: can merge without it.** CI kept `proxy-map-96722f4b8d52` (artifact on run 42293279467), good for 90 days. The loss is only a release built with no map, and `build_release.py --record` is Liam's act. It needs a row, ideally one that makes the builder refuse a release without the map.
4. **Dev threads: the claim is right and narrower than it reads.** Both logs have one thread id, no `thread:` line, and end 7 ms and 6 ms after `init done`. `StartThread` refuses inside DllMain; `dev.state` and `dev.ctl` start only in `DevOnDirect3DCreate` (`core/proxy/src/dev.cpp:773`), and the backend never loaded. The other two proxy `CreateThread` sites are in headless, after `target_ok`; `headless_status.json` stayed at `starting`, so they had not run either. So no proxy thread existed: the sentence could be stronger than "dev threads". But the report stops short the other way: it does **not** clear the proxy. Its DllMain work ran on the dying thread, and non-proxy threads are unseen. "Counts against the leading suspect" is fair for threads, and it says nothing about init itself. The 0.94 s is one launch (0.937 s, the last launch's log), and `Direct3DCreate9(` itself logs at 1.06 s. This matches the two deaths only; J101 owns the cause.
5. **D46:** see blocker 1. The shipped ini is correct; the ending is not finished.
6. **Open questions:**
   - Q1 (attempts lost from pass files): true, no row in `warscape-core`: a new core `later` row.
   - Q2 (`discovery render` names): core W61 (`later`) already covers it: no new row, add `path_ignore`'s `discovery/core/**` to it.
   - Q3 (`doc_paths` crash): no row found: a new core `later` row. I did not reproduce it.
   - Also core: CONSUMING_OPTIONS's two-step move (blocker 2) and finding 7.
   - Q4 and the D46 line: the job row is the only place holding the Opus row, and it stops being live at `done`. Row edit: a `needs_brief` or `later` row for the decisions move, carrying the three `meta/` branches and both rows.
   - New game rows: the release-ini launch, the map on releases, `gen_tables --exe`. J74 is `done`, so these are new rows.
   - Q5: not checked here; stays with J64's question. Q6: fine, a later bump. Q7: the final head already skipped `harness-windows`, so a merge of this pull request answers it; the report's "can only be read on a docs-only pull request" is out of date. Q8: rechecked, empty. Q9: harmless, for Liam.
7. **Stated as checked, against the evidence:**
   - Holds: 2 of 122; dump names and byte sizes; the two WER dumps in `_scratch\j78`; the wndproc line, 4 slots; `build_source` proxy.log on pass 1, so 20 passes were enough; no failed ctl result in any pass file; game folder now has no DLL, ini or mod folder; exe sha1 vanilla; CI run 42293279467.
   - Does not hold: the display sizes (finding 4), "cleared by fixing" (6), the reason for deviation 2 (5), "ends the D46 stop-gap" (1), "Judged by main's `meta` globs" (2).
   - No committed evidence, taken on the report's word: the preflight CPU figure, the 9-key ini diff, the 1564-file snapshot compare. None of these decide anything here. The shot the report looked at is on the PC, and I opened it too: pass 18's `naval_small_deploy.jpg` is a normal naval deployment.
   - Not comparable as the brief asked: deliverable 5 names J64's 7 on 2026-11-04. The report uses J64's 1/127, the better figure on this layout, without saying why it swapped.

### If this merges
It changes rules other branches meet: `commit_msg_hook`, W9's rule 79 and base-judged policy. Only `job/J78` has an open pull request today.
