# J48: Watcher: a virtual display restore whose position is gone

Phase 1, harness. When the display topology changes under a pending `vdisplay_restore.json`, the saved origin can no longer be applied, the
restore fails every minute and every `launch` is refused until someone moves the file aside by hand (J44 report, Deviations; J44 left the
guard "to J18", which did not build it: J18 report, nothing on restores). Target: such a restore recovers by itself, says so in the log, and a
stale record never blocks a launch. The fix is in the core (`harness/vdisplay_probe.ps1`, `harness/watcher.ps1`): a warscape-core PR, a tag
Liam cuts, a pin bump here.

Model: Sonnet (medium, the D15 default); PowerShell with host tests, no reverse engineering. Budget about 120 tool calls; at the cap, stop,
commit, report what is left. Subagents are not needed. Waiting belongs to the harness: the 20-pass run goes in the background inside one call.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J48`; "The core": the change is made in a `warscape-core` clone beside this one,
  `/c/Users/liamr/repos/warscape-core`, `git pull` first, on branch `napoleon-j48`). `core/docs/CONSUMING.md` "Upgrading and releasing".
  `jobs/J40/brief.md` and `report.md` are the model for a job that is a core PR plus pin bump; `jobs/J18/report.md` for the watcher
  version bump, the update flow and the acceptance run.
- Read `core/harness/vdisplay_probe.ps1` in full (`Get-OriginPlan`, `Apply-ToVirtual`, `Save-Prev`, the `-Restore` branch),
  `core/harness/watcher.ps1` (`Vdisplay-Restore`, `Vdisplay-Housekeeping`, `Headless-Display`, the "left by an earlier lock" block in the
  headless refusal path, `$Version`), `core/harness/tests/Test-Unit.ps1` (the `Get-OriginPlan` case around "-Origin plans refuse", topologies
  `$topoA`/`$topoB`) and `Test-Integration.ps1` (the fake display tool `fake_vdisplay.ps1` and the case "a virtual display at another size is
  set"). `harness/README.md` "Headless launch (J13)" and "Display tool" are the docs to keep true.
- Search before writing: `python3 core/wsc.py find vdisplay restore topology`.

## The failure, from the evidence (check it again before relying on it)
- `C:\napoleon_remastered_pc\watcher\watcher.log` lines 2717 to 2751 (2026-10-30 16:58 to 17:22 UTC): `vdisplay: RESTORE FAILED (the game has
  exited and the lock is released): APPLY FAILED: \\.\DISPLAY11 is not 3840x2160 at 3839,2160 after the change (display tool exit 5)`, once a
  minute for 24 minutes (26 lines), and at 16:59:37 `job ... [launch owner=j44] refused exit=-2 - headless: an earlier display mode could
  not be restored yet`. At 17:26:21 the restore finally worked, after Liam moved the file aside, and put the display `back at 3840x2160@60 at
  2560,1440`. The record is kept at `C:\napoleon_remastered_pc\watcher\_to_delete\vdisplay_restore.json.stale_j44_20261030T1700Z`: saved
  16:55:49 UTC, `x`=3839, `y`=2160, 3840x2160@60. Use it as the fixture (copy it into `core/harness/tests/fixtures/`).
- Cause: `-Restore` applies the saved mode **and** the saved origin together, and only `Get-OriginPlan` (overlap with another display) guards the
  origin. 3839,2160 overlaps nothing in the new topology but is no longer a position Windows accepts (the 4K primary it touched had left the
  list), so `Apply-ToVirtual` fails its read-back and `exit 5`s, whatever the mode. Nothing ever tries the mode without the origin, and the
  record is never given up.
- Two more ways the same record dies: the saved origin overlaps a display that moved in (`REFUSED`, exit 7), and the virtual display is gone
  (`-Restore` exits 3, the retry loop runs forever).

## Decisions already made for this job
- **A restore whose saved position cannot apply restores the mode at the display's current origin.** `-Restore` order: (1) already back at
  the saved mode and origin: ok; (2) the saved origin is legal (`Get-OriginPlan`) and applies and verifies: ok, as today; (3) otherwise apply
  the saved width, height and rate at the display's **current** origin (which cannot overlap anything, it is where the display is now), verify,
  and exit 0 with a line `VIRTUAL RESTORED (position gone): ... mode back at WxH@Hz; saved origin X,Y not applicable (<reason>), kept X2,Y2`.
  Exit 5 only when the mode itself cannot be applied. `Apply-ToVirtual` must stop calling `exit` inside so (3) can follow (2); its other
  callers (`-Set`, `-Origin`) keep their exit codes and messages.
- **Only the virtual display is ever touched.** The `Get-OtherChanges` check stays on every apply, including the fallback; the tool must still
  refuse or report if any other display changed. The cursor put-back stays.
- **A missing virtual display drops the record.** When the watcher's restore gets exit 3 (no unique virtual display), there is nothing to
  restore: move the file to `_to_delete\` as `vdisplay_restore_<utc>.json.dropped`, log `vdisplay: pending restore dropped (no virtual display:
  <tool summary>)` and carry on; the next launch's `-Check` refuses on its own if the display is still missing. Exits 5, 6 and 7 keep the
  record and the fail-closed launch refusal, now rare; the refusal text and the `RESTORE FAILED` line name the file and the one safe fix.
- A repeated identical `RESTORE FAILED` is logged once with a count, not every 60 s.
- The record format is unchanged (`name`, `device`, `w`, `h`, `hz`, `x`, `y`, `saved_utc`); the watcher `$Version` gets a minor bump (the
  rule-79 streak is per watcher version) and `harness/README.md` and the tool header (`purpose`/`usage`, which feed the tools registry row)
  say what a restore does when the position is gone.
- Out of scope: the J13 `-Set` path, the cursor logic, J18's guards, moving the virtual display on purpose, any change to the proxy or DLL.

## Deliverables
1. **The failing test first** (commit it red, then the fix), in the core:
   - `Test-Unit.ps1`: a pure restore planner (a new function next to `Get-OriginPlan`, dot-sourced through `-LibOnly`) given a display list,
     the selection and a saved record returns which of the three steps applies and the reason. Fixture: the 2026-10-30 record against a topology
     without the 4K primary (build it from `$topoA`; the log gives the later origin 2560,1440) must pick the current-origin fallback; an
     overlapping origin must too; a record whose display is absent must say "drop".
   - The apply-time fallback (exit 5 at the saved origin, then the mode at the current origin) behind an injectable apply step, so a unit test
     can drive "first apply fails, second succeeds" and "both fail".
   - `Test-Integration.ps1`: extend `fake_vdisplay.ps1` with an exit-3 restore; the record is moved aside as `.dropped`, the log says so, and
     the next launch is not refused for it. The existing restore cases stay unchanged and green.
2. The fix in `vdisplay_probe.ps1` and `watcher.ps1` as decided above; the version bump; tool header; `harness/README.md` (this repo) and
   `core/docs` where the restore is described.
3. The warscape-core PR (green in the core's CI, VERSION at the next minor after the latest tag: `git tag` in the clone; if J8's capture PR
   merges first, take the next one and rebase). Open it, say in the report what Liam must merge and tag, commit and push the job branch, end
   the turn. Do not wait or poll. Resume when Liam says it is tagged: pin bump here (`CONSUMING.md`, `wsc.toml` `[core] version`), `wsc gates`.
4. **Live check on the real tool, on the PC** (watcher ps1 job, owner `j48`, scratch under `job.sh scratch j48`): a restore file whose origin
   is far outside the desktop (for example 12000,12000) and whose mode is the display's current one. Before the fix (old watcher): exit 5 or 7,
   the display unchanged. After: exit 0, the `(position gone)` line, the display at the same mode and origin, no other display changed (record
   the `displays` listing the tool prints before and after). Then the same record through the watcher's own `Vdisplay-Restore` (copy it to
   `vdisplay_restore.json` with no game running and no lock): moved to `_to_delete\`, logged. The tool changes only the virtual display; if
   any real display changes or the cursor ends up elsewhere, stop (kill criteria).
5. Update the watcher on the PC (`update kit=<id>` through `ctl.py`/`job.sh`, as J18 did) and the **20-pass acceptance run**: rule 79 counts a
   core pin move that changes the core's `harness/`, and the streak is per DLL build id and watcher version. The DLL is unchanged (build id from
   `core/proxy/tools/build_id.py`; do not reinstall it), so the new watcher version needs its 20 consecutive passes
   (`acceptance.py run --passes 20 --run <date>_j48acc`, in the background; J18 report "Acceptance" for the first-pass trap after a fresh
   install). Commit the ledger lines and pass files.

## Kill criteria
- The host test cannot be made to fail on the 2026-10-30 fixture after about 15 calls on it: write down what the fixture lacks (the topology
  after the 4K primary left is not recorded anywhere), take the apply-time fallback as the fix and test that, and say so in the report.
- Any step of the live check changes a real monitor, or the virtual display cannot be put back to its start mode and origin: stop, restore it
  with `vdisplay_probe.ps1 -Restore` on a record saved before the step, report, and ask Liam before another try.
- The watcher update fails or rolls back twice: stop and report; do not keep re-running (the update has a dead-man switch).
- The 20-pass run fails twice for a cause in this change: stop and report; a failure with an unrelated cause (see J18 open questions) is
  noted in the report and the run restarted once.
- Over about 120 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J48/report.md`: the failure and cause as found, the core PR and tag, the tests (red, then green), the live-check output, the
watcher version and the 20-pass run id and ledger streak, deviations from this brief and why, open questions. Then
`wsc reg set jobs J48 status=review report=jobs/J48/report.md`.
