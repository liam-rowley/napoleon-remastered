# J2 review: watcher and PC sync

2026-10-29 (UTC). Independent reviewer: a fresh Opus 5.5 chat that did not build or finish this branch (D15: independent check).
Reviewed `job/J2` at b33edba against `jobs/J2/brief.md`, `jobs/J2/report.md` and `docs/DECISIONS.md`.

**Verdict: merge after fixes.**

The code is careful and matches the brief closely. Every Empire learning in the brief has a guard or a test. Restore and update
are byte-exact and sha-verified, and Empire's task and lock are protected in code. What holds the merge back is evidence, not code:
the logs behind PC tests b, e and h never reached the repo (S1).

## What was checked
- `python3 core/wsc.py gates`: 11 ok, 0 failed; `pytest tests`: 31 passed (includes `test_pc_deploy.py` and `test_job_sh.py`).
- **Not checked independently:** CI run 40791989477 (the PowerShell unit and integration tests). This session had no GitHub API
  access to the repo, and no PowerShell to run them locally. The report's 25/25 and 20/20 are taken on trust until CI runs
  on this review's commits.
- **Not checked on the PC:** folder access to `C:\napoleon_remastered_pc` was not granted to this session, so nothing on the PC was read.
- **Read in depth (risk first):** `harness/core/watcher.ps1` all of it, because it kills processes, rewrites the game's config files
  and holds the lock. Also `harness/core/update.ps1`, because it replaces the live watcher and must roll back.
  Then the `pc_deploy.py` diff, because it gates installs into the game folder.
- **Skimmed:** `job.sh`, `install.ps1` (Empire task guard), the test suites, adapter and profiles, run folder, engine_facts rows.

## Brief vs. branch
All 10 deliverables are present. The deviations named in the report are acceptable as stated:
- Opus finished the job.
- Live root instead of a side-by-side root. CI covers the refusals, the zombie and the rollback on a separate root.
- "Main menu reached" is unconfirmed: it needs a proxy heartbeat, which is DLL work for J3. J3's brief must carry it.
- The Steam route was not tried, because the exe route worked first time.

No kill criterion was hit. Scope stayed inside the brief: no DLL changes, and nothing of Empire's was written.

## Findings

### Blocker
None.

### Should-fix
- **S1. PC-test evidence is missing from the repo** (`.gitignore:6`, `harness/runs/20261029_pctest/README.md:6`). The run README
  lists `watcher.log` and both update logs (`update_20261029T001331Z_confirmed.log`, `update_20261029T002527Z_reverted.log`) as files
  in that folder. `*.log` is ignored outside `proxy/runs/`, so none of the three was committed. That leaves these claims backed only
  by job ids: test b (refusals), e (lock expiry auto-restore) and h (update confirmed and reverted). h is the dead-man switch, the
  riskiest path. To see it fail: `ls harness/runs/20261029_pctest/` shows only README, hang note, install result and status.
  *Fixed here (e65be57):* `!harness/runs/**/*.log`.
  *Still open, for the job chat or Liam:* copy the three logs from `C:\napoleon_remastered_pc\watcher\` (`watcher.log`, plus
  `update\run_*\update.log` renamed as in the README) into the run folder and commit them on this branch.
- **S2. A zombie flag could refuse launches for good after the reboot it asks for** (`harness/core/watcher.ps1:619` before the fix).
  The flag lives in `watcher.zombie.json` and survives a reboot. The watcher cleared it only when `Get-Process -Id <pid>` found
  nothing. After a reboot that pid is often reused by an unrelated process, so the flag would stay and every launch would be
  refused with "PC needs reboot", with no recovery except deleting the file by hand. The PC test shows the mechanism: the faked
  flag pointed at a live stand-in pid (the launcher, `cmd.exe`) and stayed set until it was moved away by hand.
  *Fixed here (4ac31b5):* `Zombie-Gone` also clears the flag when the pid now belongs to another image. A unit test was added in
  `Test-Unit.ps1`; it is not run yet (no PowerShell here), so CI must confirm it. The CI zombie test uses a real
  `FakeNapoleon.exe` with the same image, so it is unaffected.

### Later
- **L1** `update.ps1:147`: `-not $st.needs_reboot` is part of the health check, so no update can land while a zombie flag is set,
  even one that fixes a wrong flag. Consider letting a flag that is present both before and after the update pass.
- **L2** `job.sh` (final `case`): a script that exits 2 returns the same code as `refused`. Callers cannot tell them apart without
  reading the `[job ...]` line. Consider mapping a failed script's exit code into a reserved range.
- **L3** `job.sh lock`: check-then-write is not atomic, so two agents taking the lock in the same second can both "win". D15 allows
  at most two agents, so this is rare. When the harness moves to the core, use an exclusive create (`set -o noclobber`) or let the
  watcher arbitrate.
- **L4** `watcher.ps1` Start-NextJob: a cmd/ps1 job that touches the game sets `holds_game` for its whole run (up to
  `job_timeout_s`, 30 min). The watchdog is off for all that time. A script that launches the game and then waits leaves a hang
  unguarded. Consider holding the game only for the start/kill itself.
- **L5** `watcher.ps1` Do-Launch, steam route: it returns success even if no game process appears within `steam_wait_s`; the launch
  job then only warns. The route is unused today; make it a failure before anyone relies on it.
- **L6 (core, gate):** this review's S1 was something a gate could catch: every file a `runs/**/README.md` names should exist in the
  repo. Belongs in warscape-core `docs/BACKLOG.md` with the harness move. Not filed from this session, because there was no push
  access to warscape-core.
- Report open question 4 (`kit_id` vs. folder name in `update`) agreed; fold it in with the core move.

## Empire repeats
None found left as prose. The new learnings in the report (lock read mid-rewrite, case-insensitive variable names, a probe that
tests nothing, START lines) are all in code or tests. S1 is a new one, and the `.gitignore` fix plus L6 are its code form.

## To merge
1. Commit the three logs (S1).
2. Push this branch and let CI run green, including the new zombie unit test.
3. A reviewer or Liam re-reads S1's logs against claims b, e and h, then sets `status=done review=jobs/J2/review.md` and changes
   the verdict line to merge. The row stays at `review` until then.
