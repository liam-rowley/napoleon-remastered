# J88 review

## Round 1 (2026-11-07, branch job/J88 at 62ce169d)

**Verdict: merge.**

Every deliverable is present and I re-ran the results that matter. No blocker. **Do not run the delete command in the report as written: it names `job/J85`, which now holds real work (should-fix 1).**

I judged the work against the brief as it stood at `35b7c470`, because the copy on `main` has lost its deliverables (should-fix 2).

### What I ran
All on 2026-11-07 at `62ce169d`, in a fresh worktree, with nothing launched.

| Check | Result |
|---|---|
| `wsc gates`, full | 15 ok, 1 warn, 0 failed in 610.7 s; 724 host tests passed, 46 skipped |
| `wsc policy --branch job/J88 --base origin/main`, before the review | Refused only for the missing review and the row not being `done`, which this round supplies; two warnings for citing `job/J85` and `job/J105` |
| CI on pull request #235 at `62ce169d` | `gates` passed, `proxy` and `harness-windows` skipped (no input changed), `policy` skipped while a draft; mergeable |
| `wsc discovery check` | `discovery: 6 area files valid, J7 and J10 results in step, READMEs current, gate ok` |
| `wsc jobs check` | 110 rows, ok |
| `git -C core diff --name-only v0.47.0 v0.50.1` | No path under `proxy/` or `harness/` |
| `build_id.py --no-dirty` | `96722f4b8d52`, the same id as the last line of the acceptance ledger, so rule 79 needs no run |
| `exe.py` re-run to a scratch file | **Byte-identical to the committed `discovery/diff/exe.json`** |
| `wsc policy --scan --rule A` | 33 of 75 branches, as reported |
| Same scan with `--since 1673628d` (#225, close to J78's merge, not the report's `b9b87083`) | 1 branch judged, 0 hits, as reported |
| `git ls-remote origin 'refs/heads/*'` before and after my `gates` run | 225 and 225, so the `--peek` fix holds |

The `gates` run also covers the clean-checkout test that deviation 2 invited: `test_discovery_core_is_gone_and_unlisted` passes here. That deviation stands, since the stray folder was untracked and the report names what was removed.

### The re-check, repeated with my own script
`detail.signatures` on `main` against the branch, keyed on source, `empire_va` and name: 2929 keys on each side, none added or lost.

- **159** signatures changed class or hits, all `source: function`. The report's class table adds up to 159.
- **26** lost a candidate class: 19 `unique`, 7 `shared`. This matches the row and the report.
- **0** of the 159 have an old or new hit within 32 bytes of an `engine_sites` row. **This 0 is not an artefact of the test:** the same test over all new signatures finds 24 hits near sites, so the RVA forms do line up.
- **0** of the changed names appear in `engine_sites` or `engine_facts`, and none of the lost hits' RVAs are quoted there.
- No `unique` signature moved its RVA. Of the 37 `rows`, only `signatures function` changed. `empire_pe`, `napoleon_pe` and `detail.method` are identical.

The report does not mention that 403 signatures changed `masked` and 53 flipped `empire_unique`, some of them `cfg_site`. Neither is a class or hit change, so neither is in the brief's test. `men_inside_the_battle_bounds` shows the size of it: `masked` went from 4 to 5, and its hit `0x1dae50`, next to `guard.men_inside_battle_bounds`, did not move.

### Risk-first reading
I picked three things, because a mistake in any of them reaches past this branch.
1. **`wsc.toml` opt-ins.** Rule F (`core/warscape/policy.py:521`) applies only to `job` branches, and J105's decision rows go through `meta/`, so it does not refuse them. `job/J105` itself changes no decision file. Rule A at `error` has nothing to catch today: #235 is the only open job pull request.
2. **The claim fault.** The fix is complete for this repo: no other test or tool runs a bare `jobs next` or `jobs review`, and the core's tests use `--offline`. The reflogs show `job/J85` and `brief/J89` created by push 3 min 52 s apart, which fits the report's times.
3. **The 12 branches in Open question 1.** See should-fix 1.

### Findings

**Blockers:** none.

**Should-fix**
1. **`jobs/J88/report.md:104`: the delete command would destroy J85's work.** The list was right when written at 11:18 UTC. Since then `job/J85` has gained `1ec1b6b0` and `b637d0f7` from session `5589c70a`: `tools/acceptance_auto.py` and run `20261107_j85pc`. To see it: `git log origin/main..origin/job/J85`. The other 11 are still empty: their heads add nothing to `main`. The safe list is:
   `git push origin --delete job/J27 job/J35 job/J48 job/J69 job/J93 job/J101 brief/J26 brief/J63 brief/J77 brief/J89 brief/J102`
   I left the report as the builder wrote it. This section is the correction.
2. **`jobs/J88/brief.md` on `main`: #234 deleted 40 lines of the brief.** The commit replaced everything from the first text `## Open questions`, a backticked mention in `## Start`, through to the real heading. Target facts, Decisions, Deliverables and Out of scope are gone, and the `## Start` line is cut in half. To see it: `git diff 35b7c470 0b2972f5 -- jobs/J88/brief.md`. The builder evidently had the full text, because the report cites decisions 2 and 5 and deliverable 3. The report still does not name this, although the same session wrote #234. `wsc jobs check` passes the damaged brief. Restore it with a `plan/` branch; no other brief has the answer block. Recommended for the core: have `jobs check` require `## Deliverables` in a brief.

**Later**
1. **`wsc.toml:46`: the reason for 106 is wrong, though the deviation is named (`jobs/J88/report.md:97`).** The report says that at 100 `job/J105` "would be refused once this merges". `usage_problems` (`core/warscape/jobq.py:330`) only reads rows in `review`, `fix` or `done`, and J105 is `queued` with its report still in progress. At 100 its Finish step would simply have to write the line. Decision 5 said to compute the value on `main`, which gives 100, so J100 to J105 escape the rule for no gain. This is not worth an Opus round alone: J87 touches the same rule and can lower the value.
2. **The `tests` gate is close to its cap with Docker up.** My run took 580.8 s of the 600 s `timeout_s`, and `test_proxy_host` was 382.7 s of that. The report's 187.5 s is the same gate with that module not run, because Docker was down. It passed, but a fresh worktree on a busy PC can hit the cap with no failed test, as J78 did. My run shared the PC with an `exe.py` run and the policy scans, so this is an upper figure.
3. **For the core: nothing stops a claim from inside a gate.** `--peek` fixes the one caller, but a future test that runs a bare `jobs next` would take jobs again. A claim could refuse to push when it runs under `wsc gates`. This belongs in a `later` row in warscape-core, which I have not filed.
4. **`test_discovery_core_is_gone_and_unlisted` fails on ignored `.pyc` files** (`tests/test_jobs_hooks.py:84`). Any clone from before J64 can hit what deviation 2 hit. The test could ignore a folder that holds only `__pycache__`.
5. **`job/J85` carries its own copy of the `--peek` commit** (`5b8feaf2`, same change as `f9a7c457`). It should merge cleanly, but its branch will need `main` after this lands.

### Not checked
- The report's split of the 33 rule A branches into 11 row-only and 22 others.
- The removed `discovery/core/` folder held only `.pyc` files: it is gone, so only the report says so.
- The ten claims the report calls "very likely" the same fault. I confirmed they are empty, not how they were made.
- The `Usage:` line's 36 calls, counted by hand. J88 sits below `usage_from`.
- The usage rule refusing a report: I read the code and did not repeat the report's run at `usage_from = 99`.

### Effect on other branches
From this merge, a `merge` round whose own commits change code outside the job folder is refused, so a reviewer's fix now costs a fresh round. Rule F and the `Usage:` rule (from J106) also start. No open job branch fails any of these today. Any branch that started before this merge still has the bare `jobs next` test, so its full `gates` run can claim a job until it takes `main`.
