## Round 1 (2026-11-04, branch job/J82 at 1204590)
Verdict: merge

Checked: `wsc gates` on the branch is 13 ok, 1 warn (skips for the missing viewer wasm, Pillow and capstone: environment), 0 failed. `wsc policy` refused
only for this review and the row not being `done`, which this round supplies. The diff touches `.gitignore`, `tools/ci_failures.py`,
`tests/test_job_sh.py`, `docs/CI_FAILURES.md`, the record, the report and the row; nothing under `core/`, `proxy/` or `harness/`, so rule 79 does not apply.

- **Record.** 240 table rows in `docs/audits/LATER_TRIAGE_2026-11-04.md`, equal to the 240 bullets the report counts; the fates 107+53+29+51 add up.
- **Housekeeping.** The seven tracked `summary.json` stay tracked; the ignore rule is in; the `GUARDS["policy"]` string names the live route; `test_ctl_without_an_ini_uses_the_registered_default` passes here and is now isolated from the PC state folder (temporary game root through `WSP_GAME_ROOT`, rc 124 and `.cmd.expired` asserted on every OS).
- **Plan branch.** `plan/later-triage-2026-11-04` adds only J89 to J98 (10 files, all in `registries/jobs/`); the ids are free on `main` and not used by any other open `plan/` branch. It is Liam's to merge (D50); not merged here.
- Spot-checked J14-L1, J20-L3, J41-L1, J46-L3, J62-L3 (the cells the report asked to be checked): each cites a real row or core backlog item; J62-L3 and J20-L3 are thin but not wrong.

Later:
- The old body of the ctl test was never run, so its cause (the live `C:\napoleon_remastered_pc\ctl` folder) is inferred; the new test removes the dependency either way.
- The report says a probe copy of `job.sh` was briefly placed in `core/harness`; the diff shows `core` unchanged, so no harm, but the hook or a gate should refuse a write there.
- Core `docs/BACKLOG.md` is at 30,606 of 30,720 bytes: the next addition needs the file split first (the core owns it).
- Rows J89 to J98 and B64 to B84 move into core W32's later registry when it reaches napoleon.
