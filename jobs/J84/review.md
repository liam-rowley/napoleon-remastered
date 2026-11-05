## Round 1 (2026-11-05, branch job/J84 at 946fb80)

**Verdict: merge.**

The hook change is correct and does what D62 asks. `meta/` stays denied, `plan/` is allowed, and the rest of the merge guard is untouched. The two should-fix items are fixed on the branch (130a12b, 0cdc077). The later items need nothing from this job, but L1 and L2 need Liam or the core.

### Machines
Run on the branch commit, in a worktree on a local branch `review/J84` (`job/J84` is checked out in the builder's locked worktree `J84`).
- `wsc gates` at 946fb80: 12 ok, 3 warn, 0 failed. The warnings: `hooks` (this worktree's `core.hooksPath` is an absolute path), `ci_render` (the known W23 trigger note) and the skipped-test summary of this machine.
- `wsc policy --branch job/J84 --base origin/main` at 946fb80: refused only for the missing review and the row not yet `done`, which this round supplies.
- `tests.test_claude_hook_corpus` and `tests.test_claude_hook`: 30 tests ok. With `tests.test_jobs_hooks` after the fixes: 90 tests ok.
- CI on 946fb80: `gates` and `harness-windows` success; `proxy` skipped; `policy` skipped because the pull request is a draft.

### Checked in depth: `merge_reason` (`tools/claude_hook.py`)
Picked because a mistake here lets an agent merge a `meta/` branch, the one thing D62 keeps for Liam.
- `branch.startswith('meta/')` is equivalent to the old regex for `meta/`. The normalisation above it is unchanged.
- `decide()` on 28 spellings, each as Bash and as PowerShell: `meta/` denied bare, quoted, as `origin/`, `refs/heads/`, `refs/remotes/origin/` and `owner:` forms, behind `-R`, `--repo=`, `--subject`, `-t`, `GH_REPO=`, `env`, `cmd /c` and `xargs`.
- `decide()` with the real `pr_head` against real pull requests: #205 and #204 (`plan/`) allowed, #47 (`meta/relax-agent-cap`) denied, 999999 (no such pull request) denied. `decide()` only classifies, so nothing was merged.
- "Green CI" is enforced on GitHub, not only by convention: ruleset 26078850 on `main` requires `gates`, `policy`, `proxy` and `harness-windows`, squash only, and `bypass_actors` is empty, so `gh pr merge --admin` on a `plan/` branch cannot skip the checks.

### Brief
All five deliverables are present and nothing is out of scope. The narrowed rules are left to J103. `README.md` and `docs/plans/PLAN.md` hold no living copy of the old claim, as the report says; `docs/audits/` mentions it only as dated history.

### Findings

**Blockers:** none.

**Should-fix (both fixed in this round):**
- S1, `tests/test_claude_hook_corpus.py:39`: the corpus stopped covering a URL that resolves to a denied branch. J84 flipped the only denied URL row to allowed. To see it fail at 946fb80: drop the `http` test from the `if` in `merge_reason` so a URL is taken as a branch name; the corpus stays green, while `gh pr merge <url>` of a `meta/` pull request is allowed. The brief's "a number that resolves to `meta/` stays denied" had no row either, though the `99` row does cover number resolution. Fixed in 130a12b: fixture entries and rows for number 14 and `pull/14`. The same mutant now fails on the `pull/14` row, and the restored hook is green.
- S2, `tools/gates/pipeline.py:477` and `:498`: two docstrings still gave "plan/ and meta/ branches are Liam's (D50)" as the reason for the UI baseline and lock rules. D62 makes that false for `plan/`. Outside the brief's grep list, so not the builder's miss, but the exemption reads as though an unreviewed branch could change the baseline. It cannot: `uikit/` is in neither the `plan` nor the `meta` glob list in `wsc.toml`, so `core/warscape/policy.py:207` refuses it first. Fixed in 0cdc077, docstrings only.

**Report gap (no fix needed):** the brief's Finish asks for the corpus counts before and after and the `gates` and `policy` output, and `report.md` gives only "30 tests ok" without naming the omission. Recorded here instead: the `merge` family went from 19 rows to 21 at 946fb80 and 23 with S1; `gates` and `policy` are above.

**Later:**
- L1, core: `core/docs/REVIEW.md:68` still says `plan/` branches wait for the owner, which contradicts D62 for this game (`docs/REVIEW.md` overrides it here). It needs a warscape-core `docs/BACKLOG.md` line. Not filed in this round: this session is confined to its worktree.
- L2, for Liam: `gh pr merge plan/x -R liam-rowley/warscape-core` is now allowed, as the brief required, but D62 is a Napoleon decision and the core's `REVIEW.md` keeps `plan/` for the owner. An agent working here can now merge a warscape-core `plan/` branch. If that is not intended, the hook should deny `plan/` when `-R` names another repository.
- L3, repo: `gh pr merge $(echo meta/x)` is allowed because the target is taken as a literal branch name. This predates J84 (the old regex allowed it too) and needs deliberate evasion. A target holding `$(` or a backtick could go down the unresolvable path.

### Effect on other branches
No rule that open job branches must meet changes. From this merge on, `plan/` writers queue their own merge; D62 accepts that a `plan/` branch can change `CLAUDE.md` and `docs/REVIEW.md` on green CI alone until J103 lands.
