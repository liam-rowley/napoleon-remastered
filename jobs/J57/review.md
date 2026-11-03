## Round 1 (2026-11-02, branch job/J57 at 3576971)

**Verdict: merge.**

Checked: `wsc gates` on the branch (11 ok, 1 warn, 0 failed, 2026-11-02); CI on 3576971 all green; `pr_policy` refuses only for the missing review/row, as expected before review. Scratch run 41492174324 read with `gh run view`: `changes` failed by design and `gates`, `proxy`, `viewer`, `harness-windows`, `notify` all ran and succeeded, so the problem-2 kill criterion is not hit. All four commits carry the session trailer.

Risk-first reading: the three workflow `if:` expressions (a wrong one silently skips or always runs CI) and the `Deploy` setUp patch (must not weaken the running-game guard). Both are correct: dispatch behaviour per job is unchanged, `!cancelled()` removes the implicit success(), and `windows_images` is the narrowest seam, with a test that install still refuses a running game.

### Blocker
None.

### Should-fix
None.

### Later
- Live evidence for problem 1 is this job's own merge: the pushed head must show a real, non-skipped `policy` run (this review follows the new order).
- The scratch branch `scratch/j57-changes-fail` is still on origin: `git push origin --delete scratch/j57-changes-fail`.
- warscape-core backlog: its own `test_pc_deploy` copy, if any, has the same live-game dependency (unchecked).
