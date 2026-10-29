# J2 report: watcher and PC sync

Branch `job/J2`, 2026-10-28/29 (UTC). Built by a Sonnet-medium agent (D15) for the cloud side up to CI round 6, then finished by
the session that picked the job up (Opus 5.5, see deviations) after a container restart stopped the agent: CI rounds 7-9, the probe
fix, the whole PC test, this report. **Tested watcher: commit f57f8e9** (`watcher.ps1` sha256 `d05f1e6d66eb…`), CI run
**40791989477** green (unit 25/25, integration 20/20, plus the existing gates and proxy jobs). PC run: `harness/runs/20261029_pctest/`.

## What exists

| brief deliverable | where | evidence |
|---|---|---|
| 1 watcher | `harness/core/watcher.ps1` (named-mutex single instance, FIFO `jobs\<id>.request`, result `<id>.done` written last, `launch kill profile status noop restart update`, per-job timeout that spares the game, pruning, `watcher.status` every 2 s, rotated UTC log), launcher `watch.cmd` (restarts on a crash), `spawn_detached.ps1` | CI; PC a, c |
| 2 game lock | `game.lock` one line (owner, session, purpose, started, `hang_s`), expiry 20 min (moved to `_to_delete`), owner required for game- and config-touching jobs and for scripts that start/kill the game or write its config; Empire's `rml_mod\game.lock` read, never written | CI; PC b, e |
| 3 hang watchdog, zombies | `IsHungAppWindow` or no CPU progress and no heartbeat-file write for `hang_s`; minimised/hidden is not a hang; 180 s start-up grace; `dump.ps1` (MiniDumpWriteDump out of process, target bitness), archive `runs\<utc>_hang\`, kill; zombie flag persisted, launches refused "PC needs reboot" | CI; PC f, b (faked flag) |
| 4 config profiles | adapter table `harness/napoleon/adapter.json` `config_files` (4 files, absent is a recorded state); `profile <name>` snapshots with sha256, full files and `key=value` overlays, never stacks; `restore` checks byte for byte; auto-restore on release, expiry or owner change, deferred while the game runs; profiles `vanilla`, `proxy-dxvk` | CI; PC d, e; baselines in `engine_facts` |
| 5 unattended launch | route `exe`: `Napoleon.exe` directly with Steam running; fact `napoleon.launch.unattended_route` | PC c, d |
| 6 display probe | `vdisplay_probe.ps1`, `CDS_TEST` only, display matched by name, never the primary | PC g; fact `napoleon.display.vdd_modes` |
| 7 PC sync | `proxy/tools/pc_deploy.py kit --what harness` (new id, manifest, unique staged names, CRLF/ASCII normalisation for PC scripts); install/uninstall ask the watcher's process list whether either game runs | `tests/test_pc_deploy.py`; every kit this run sha-checked on the PC |
| 8 install, update | `Install watcher.cmd` / `Uninstall watcher.cmd` -> `install.ps1` (Register-ScheduledTask at logon, no admin, refuses Empire's task name); `update kit=<id>` -> `update.ps1` (backup, swap, noop within 60 s, healthy 90 s, stable 30 s, else revert byte-exact) | Liam's install 2026-10-28T23:07Z; PC h (2 confirmed, 1 reverted) |
| 9 agent helper | `harness/core/job.sh` (root from the adapter, atomic submit, blocks inside one call, exit codes: refused 2, no answer 124; `lock/touch/unlock/status/root`) | `tests/test_job_sh.py`; used for every PC job |
| 10 registries | a tools row for every harness file; watcher settings listed in `harness/README.md` (Settings) because `config_keys` rows feed the proxy's generated tables and would not fit; 6 new `engine_facts` rows | `wsc gates` |

Learnings that became code: each has a host test in `harness/tests/Test-Unit.ps1` or `Test-Integration.ps1` (no-output job, `return ,$x`,
output written by the watcher not a redirect, detached long-lived processes, try/finally slot, UTF-8 without BOM, tolerant status
reads and heartbeat by mtime, ids never reused, UTC everywhere, expiry restores under the owner). New ones from this job, also code:
a lock caught mid-rewrite (0 bytes) is not a release (auto-restore waits a pass; test added); PowerShell names are case-insensitive, a
test-local `$g` shadowed the suite's `$G` (renamed); a probe that tests nothing exits 2 instead of passing; each test prints a START
line and the CI step times out before the job so a hang keeps its log.

## How to install, update, uninstall

- Install (once, done 2026-10-28): cloud `python3 proxy/tools/pc_deploy.py kit --what harness`, copy the kit to
  `C:\napoleon_remastered_pc\kits\<id>\` with `device_commit_files`, check its sha256 against the manifest, Liam double-clicks
  `Install watcher.cmd` in it.
- Update (no click): build and copy a new kit the same way, then `echo "update kit=<id>" | job.sh <owner> -`; read
  `watcher\update\run_<utc>\update.log` for CONFIRMED or REVERTED.
- Uninstall: `Uninstall watcher.cmd` from any harness kit (stops the watcher, removes the task, moves the root's code to `_to_delete`).

## PC test

All of a-h pass: `harness/runs/20261029_pctest/README.md` (job ids, files, baselines). Liam's only part was the install. The game
folder ended identical to vanilla (1564 files); the J1 proxy was installed for d and uninstalled after.

## Deviations from the brief, and why

- **Model:** the build agent ran on Sonnet medium as briefed; the picking-up session, which finished the job after the agent was lost
  to a container restart, runs on Opus 5.5 (the model the chat was opened on), not Sonnet. No Opus subagents.
- **No side-by-side test root on the PC:** every PC test ran on the live root. The side-by-side cases (zombie, refusals, update
  rollbacks) all pass on a separate root in CI on every push, and the live root was idle (no other owner), so a second watcher on the PC
  added a start-up path but no coverage. The zombie on the PC is therefore a **faked flag** (a live stand-in pid), not a process that
  survived a kill; the survive-the-kill path is CI-only.
- **Main menu not confirmed:** vanilla Napoleon writes no log the watcher can see, and the proxy log ends at `Direct3DCreate9` (no
  frame or menu line). The launch evidence is the pid, a visible window and CPU progress; a "menu reached" signal needs a proxy
  heartbeat line, which is J3's (a DLL input).
- **Steam route not measured:** the `exe` route worked first time, so `steam://rungameid/34030` was never tried (the brief's 3-attempt
  rule only applies on failure).
- **Display probe fixed during the PC test** (commit 7c2509b) after its first PC run passed while testing nothing.
- **CI:** 9 rounds to green; no single cause failed 4 times (kill criterion not hit). Round 8 was cancelled at the job timeout with no
  log (GitHub kept none) and the hang did not recur in round 9; cause unknown (open question 3).

## What moves to the core later

All of `harness/core/` (watcher, launcher, update, install, dump, freeze, spawn, probe, `job.sh`) and the harness parts of
`pc_deploy.py`, with the tests; `harness/napoleon/` stays as the game adapter. Same plan as J1's `proxy/core/` (end of phase 1).

## Open questions for Liam

1. **Virtual display modes:** the driver offers only 3840x2160. To get 1080p and 1440p, as administrator open
   `C:\VirtualDisplayDriver\vdd_settings.xml` in Notepad and inside `<resolutions>` add, keeping the 3840x2160 blocks:
   `<resolution><width>1920</width><height>1080</height><refresh_rate>60</refresh_rate></resolution>` and
   `<resolution><width>2560</width><height>1440</height><refresh_rate>60</refresh_rate></resolution>`; the file must still start with
   `<?xml`; then VDD Control -> Reload driver (or disable/enable it in Device Manager). Then the probe runs again
   (`vdisplay_probe.ps1 -Test 1920x1080,2560x1440`). Not needed until headless runs at those sizes (J3/J4).
2. From the brief: headless window placement (the game on the virtual display) and J1's `proxy.minidump` value both belong to J3's DLL
   rebuild; J3's row is not edited here (a job branch changes only its own row). J3 also needs a proxy heartbeat line for "menu reached".
3. CI round 8's unexplained hang (run 40788567359): the START lines and step timeout now make the next one diagnosable.
4. `update kit=<id>` checks every sha256 against the manifest but not that the manifest's `kit_id` matches the folder name (seen while
   building the test kit on the PC); harmless today, worth a guard when the harness moves to the core.
5. `hung_window_s`=60 may be short for a very long first load (shader cache cold); the 180 s start-up grace covers the cases seen so far.
