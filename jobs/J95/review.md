# J95 review

## Round 1 (2026-11-07, branch job/J95 at e5281a8)

**Verdict: merge.**

No blockers and no should-fix items. This round changes nothing outside the job folder and the row. Item 10 is carried by row J88 (pull request #229, merged before this verdict), which was the condition for merging.

### Machines
- CI on the head: gates run 42323359960 at e5281a8 (push) passed, 15 ok, 1 warn, 0 failed. `proxy`, `harness-windows` and `viewer` were skipped correctly: the branch changes four files, in `jobs/` and `registries/`.
- `policy` run 42323365536 was skipped because the pull request is a draft, so it counts as nothing. The real run is on the head this round pushes, after `gh pr ready`.
- Local at e5281a8 (Windows, 2026-11-07): `gates` 14 ok, 2 warn, 0 failed; `jobs check` 110 rows ok; `reg check` ok. `policy` refused only for the missing review and the row not being `done`, which this round supplies. It also warns that the report cites `job/W141`: that branch is in warscape-core, so the warning is harmless.
- Latest main: the branch forks at ef8ca7e9; origin/main is 7536e79a. The one commit between is #229, which changes only `registries/jobs/J88.json`. It shares no file with this branch, and `git merge-tree` is clean.
- Rule 79: the branch touches no `proxy/` or `harness/` input and does not move the pin. No baseline change.

### The core route: W141 in place of a pull request inside J95
The brief and D56 ask for one warscape-core pull request inside J95. What landed is core row W141 and pull request #185, reviewed and merged in the core's own queue. I accept this.
- **Was the single pull request met?** Yes for the code. All seven items are in #185 (16 files: `discovery/` code and tests, `docs/UPGRADING.md`, W141's job files and row). The other two core pull requests hold no code: #183 is W141's row and brief, #187 is the later row W142.
- **Why the departure.** The core's `policy` takes code only on `job/W<n>` with its brief on `main`, so the brief's route could not be followed as written. The report names this as deviation 1.
- **What it cost and gained.** J95's review cannot judge core code, so that check moved to W141's review. That is a stronger check, not a weaker one: the commits of #185 show review session 8d273b80 apart from builder session 9371181e, and neither is this session. The review reverted each fix on its own (18 reverts, all failed their tests).
- **What I checked myself.** #185 is merged at 409414a, its `gates` and `policy` passed, and `gates` on the core's `main` passed at 409414a and 96735f9. I did not repeat the reverts; those results are W141's.
- **Brief proof.** One test per item 1 to 7 stands on W141's review. Item 2 is test-exempt by the brief.

### Item 10, the pin bump
- **Inside the brief.** Item 10 is conditional: bump only if a tag carrying Part A exists at the finish, otherwise say so. No tag existed when the builder finished, and none exists at this review: the newest tag is v0.50.0, and release pull request #188 for v0.50.1 is open. So the report's "not done" is an allowed outcome, not a missed deliverable.
- **Why it still needed a condition.** D56 says the core fixes are followed by a pin bump, and no open row named W141 or the `exe.py` re-run. J88 named only the process train tags, and a later bump could have reached W141 by chance while skipping the re-run, so J95 going `done` would have dropped it.
- **What had to hold before merge.** A row on `main` carrying the bump. J88 now does (#229): the target must be v0.50.1 or later, and the job must run `discovery render` and `check`, re-run `exe.py`, commit `exe.json`, and re-check the lost signatures against `engine_sites` and `engine_facts`. I used J88 rather than a new row because J104 already rules out two pin bumps at once, and #225 set the pattern of a `plan/` row edit carrying review items.
- **Why not bump here.** A bump changes the gitlink, which is outside the job folder and row, so no merge round can make it. It also crosses every UPGRADING section from v0.47.0, which is J88's work.
- **Rule 79 at the bump.** The core's `proxy/` and `harness/` have no changed file from v0.47.0 to v0.50.0 (GitHub compare, 53 files), and nothing after v0.50.0 touches them. So this span needs no acceptance run; J88 still judges its final tag.

### The 26 signatures
The report's open question counts 19 signatures that lost `unique`. W141's review counts 26 that lost a candidate class (those 19 plus 7 `shared`), none within 32 bytes of any of the 64 `engine_sites` rows. The 26 is the number to use, and J88 now states it.

I did not reproduce it: a read-only run of the merged `exe.py` was refused by this session's worktree guard, so the figure is W141's. J88 re-runs it on the real file, which is where it matters. This also answers the report's open question 1: the bump job re-runs `exe.py`, as the report recommended. Nothing else in this repo reads `exe.json`, and until the bump it stays on the old rule.

### Claims checked (items 8 and 9)
- Item 8: `napoleon.assets.pack_order` keeps `verified`, evidence and date. The last clause and `notes` say assumed. No other copy of the old clause is left in `docs/`, `registries/` or `discovery/`.
- Item 9: I re-read the shipped exe with `exe_info.py --imports` (read-only): user32 57, gdi32 only `SelectObject`, dwmapi and shcore empty. All 19 named calls are present and none of the claimed-absent calls is. `detail.napoleon_pe.imports` in `discovery/diff/exe.json` agrees on 57, so 19 and 38 more is right. No copy of "37 more" is left.
- Report deviations 2 to 6 are named with reasons. Deviation 5 (`MIN_FIXED_BYTES` stays 6) is D56's answer.

### Risk-first reading
I picked the two fact edits and the bump's carry, because the code risk sits in the core and was reviewed there. `exe.py` is the one change that moves committed facts, and its effect waits for the bump.

### Findings
No blockers. No should-fix.

**Later:**
1. `jobs/J95/report.md:3` says #185 is a draft waiting for review, and line 18 says it is unmerged with v0.49.0 the newest tag. Those are out of date now: #185 merged at 409414a and the newest tag is v0.50.0. Not edited, as the report is the builder's.
2. `registries/engine_facts/napoleon.exe.window_imports.json:6` keeps the date 2026-10-29 though the count changed on 2026-11-07. The fact's `evidence` file holds counts only; the names come from the command in `notes`, which says so. Set the date the next time the row is touched.
3. A brief that puts core code inside a game job cannot be followed as written, because the core takes code only on a `job/W` branch whose brief is on its `main`. The `warscape-brief` skill or `jobs check` could ask for the W row first. This bit once, so it is a note and not a core row.
