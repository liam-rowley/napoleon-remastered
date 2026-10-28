# J2: watcher and PC sync

Phase 1, job 2: the watcher, the only way a cloud agent starts, stops and configures Napoleon on Liam's PC unattended, plus the
sha-checked PC sync it relies on. At the end an agent can launch Napoleon, kill it, switch a config profile and get everything back
byte for byte without Liam at the keyboard. No game features and no proxy DLL changes.

Model: Sonnet medium (D15 default: Windows scripting and file plumbing, no reverse engineering, shaders, DLL or crash work). Budget
about 180 tool calls; at the cap, stop, commit, report what is left. At most 2 subagents, only for independent cloud work (CI, host
tests). Waiting belongs to the harness: the agent helper blocks inside one device call, the agent never polls with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J2`). Read `docs/DECISIONS.md` (D2, D11, D21, D25), `docs/plans/PLAN.md` (sections 3, 4 and
  phase 1), `proxy/README.md` ("PC install and uninstall") and `jobs/J1/report.md` ("Later": the first install cannot see a vanilla
  game running; that is fixed here).
- Attach `liam-rowley/empire-remastered` (read only, never modified) as the evidence base. Port the design, not the code line by line:
  `rml_mod/docs/watcher.md` (read fully: requests, lock, status, watchdog, zombies, profiles, autostart, failure modes, update with a
  dead-man switch, side-by-side testing, changelog), `rml_mod/src/watch5.ps1`, `rml_mod/src/watch.cmd`,
  `rml_mod/tools/{install_watcher_task.ps1, spawn_detached.ps1, watcher_update.ps1}`, `rml_mod/tools/remote/{job.sh,
  watcher_selftest.sh}`, `rml_mod/profiles/README.md`, `rml_mod/docs/headless_virtual_display.md` (section "Other resolutions" and the
  VDD install guide), `rml_mod/tools/vdisplay_mode.ps1`, and `docs/learnings/LEARNINGS_HARNESS.md` section "PC access: watcher, jobs,
  game.lock, device tools". Do NOT port the v4 request files, the cutover tooling, `build.request` (nothing is built on the PC),
  `hv.sh`, or anything that talks to a control channel (J3).
- Search the tools registry first (`python3 core/wsc.py find deploy sync`): `proxy/tools/pc_deploy.py` already does sha-checked kits,
  unique staged names and byte-exact uninstall. Extend it; do not write a second sync tool.

## Target facts
From J1 (2026-10-28, `proxy/runs/`); check again and record new ones as `engine_facts` rows with date and run id.
Game folder `C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War`; AppData `C:\Users\liamr\AppData\Roaming\The Creative
Assembly\Napoleon`; PC state folder `C:\napoleon_remastered_pc` (D25). PC `officepc`, Windows x64, RTX 4090. The device VM has `python3`
and the connected folders mounted; it cannot start a Windows process (that is why the watcher exists), background processes die when
a device call returns, and deletes are refused unless allowed for the session (move to `_to_delete\` instead).
Empire's watcher v5 is probably still installed on this PC (scheduled task `rml_mod watcher`, watching Empire's `rml_mod\`): leave it
alone; it is Empire's and Empire is not modified.

## Decisions already made for this job
- **Where the code lives:** `harness/core/` (game-agnostic: the watcher, lock, watchdog, profiles, agent helper, installer) and
  `harness/napoleon/` (the adapter: paths, image names, launch command, config file list, profiles). Same pattern as J1's `proxy/core/`:
  a core-candidate that moves to warscape-core at the end of phase 1 with the proxy, so this job needs no core tag.
- **Watcher root outside the game folder:** `C:\napoleon_remastered_pc\watcher\` (requests, results, status, log, lock, profile
  snapshots). The game folder only ever receives deployed files (D25), so the byte-exact uninstall stays true.
- **One game lock across games (D11):** the watcher refuses a launch while `Napoleon.exe` or `Empire.exe` runs, and while any other
  watcher on the PC holds a lock it can see (read Empire's `rml_mod\game.lock` if present; never write it).
- **Windows PowerShell 5.1** for everything that runs on the PC (it is what the PC has; no installs). Host tests run on GitHub's
  Windows runner under `powershell.exe` 5.1, not `pwsh` 7, as a CI job next to the existing ones.

## Deliverables
1. **Watcher:** single instance per root (named mutex), FIFO job queue from `jobs\<id>.request` (atomic submit, id pattern, one result
   JSON written last with status `ok|failed|refused|timeout|lost`, real exit code, UTC times), control jobs `launch`, `kill`,
   `profile <name>|restore`, `status`, `noop`, `restart`, per-job timeout that kills the job's tree but spares the game, pruning,
   `watcher.status` JSON rewritten every 2 s, a rotated log with UTC timestamps. A launcher that restarts it on a crash.
2. **Enforced game lock:** one line with owner, session, purpose, start time and optional `hang_s`; expiry after 20 min without a
   refresh; every game-touching or config-touching job must name the owner or is refused with the reason; a script job that starts or
   kills the game needs an owner too.
3. **Hang watchdog and zombies, with no DLL change:** a hang is `IsHungAppWindow`, or no CPU-time progress and no proxy log write for
   `hang_s`; a minimised window is not a hang; a start-up grace period. On a hang: an out-of-process minidump (`MiniDumpWriteDump` from
   the watcher), the proxy log, configs and dumps archived into `runs\<utc>_hang\`, then the kill. A process that survives the kill is a
   zombie: persisted flag, every launch refused with "PC needs reboot". A heartbeat line from the proxy is J3's (it is a DLL input).
4. **Config profiles restored byte for byte:** first inventory every file the game and the mod read for settings (the AppData
   preferences script, battle preferences, `napoleon_remastered.ini`, `dxvk.conf`; record the list as an adapter table and the baseline
   sha256 of each as `engine_facts`). `profile <name>` snapshots them with sha256, installs full files and `key=value` overlays, never
   stacks; `restore` writes the snapshot back and checks each file byte for byte; restore also runs by itself when the lock is
   released, expires or changes owner (at once if the game is closed, else when it exits). Seed a `vanilla` and a `proxy-dxvk` profile.
5. **Unattended launch and kill of Napoleon:** find how Napoleon starts without a human (the exe directly with the Steam client
   running, `steam://rungameid/34030`, or another route) and measure it: pid confirmed, main menu reached (proxy log), clean kill. The
   launch refuses on a zombie, a running game (either title) or a missing lock. Record the route as an `engine_facts` row.
6. **Headless virtual display, probe only:** list the displays and the virtual display driver's modes; test 1920x1080 and 2560x1440
   with `CDS_TEST` only (Empire's driver refused both: `DISP_CHANGE_BADMODE`). If they are missing, write the exact
   `vdd_settings.xml` change for Liam (admin, he applies it) and test again after. Never apply a mode to the primary display, never
   change the topology. Putting the game window on the virtual display is a proxy change and belongs to J3 (open question 1).
7. **PC sync:** `pc_deploy.py` gains whatever the watcher needs (a kit for `harness/` files into the watcher root, a check that no game
   of either title is running before an install, done through the watcher's process list rather than the device VM's). Every kit has a
   new id and a manifest; every copy is sha-checked on the PC before use (the stale-resend bug).
8. **Install and update:** a one-time installer Liam double-clicks (scheduled task at logon, no admin; `Register-ScheduledTask`, not
   `schtasks`), an uninstaller, and an in-place update path with a dead-man switch (the new watcher must answer `noop` within a set time
   or the old one is put back).
9. **Agent helper:** `harness/core/job.sh` for the device VM: submit, block inside one device call until the result or a timeout,
   print the output, return the job's exit code (refused 2, no answer 124). It reads the watcher root from the adapter, never a default
   mount path.
10. **Registries:** a tools row for every tool (header with purpose, usage, when); `config_keys` rows for the watcher's settings if the
    schema fits, otherwise list them in `harness/README.md` and say so in the report.

## Learnings that become code (each one a guard or a test, not a paragraph)
From Empire's watcher history, each must be impossible or caught by a host test here:
- a job with no output must finish normally (5.0 wedged the queue); byte buffers returned with `return ,$x` (PowerShell unrolls arrays);
- job output written by the watcher at the end, never a redirect the game can inherit (v4 lost every later job that way); long-lived
  processes started detached, without the job's handles;
- one job's error never escapes the "finish the job" path (try/finally frees the slot);
- files written as UTF-8 without a BOM and never UTF-16 (`Tee-Object`, `*>` and `Encoding.UTF8` in 5.1 broke greps);
- status reads tolerate the file being replaced mid-read; liveness judged from a heartbeat file's mtime;
- job ids never reused, results cleared only when the new request is picked up;
- timestamps in UTC everywhere, labelled as such (Empire's local time with a `Z` suffix caused misreads);
- an expired lock restores the profile under its owner and says so in the log.

## PC test
Two short sittings at most; ask Liam before each. Sitting 1: Liam runs the installer once and confirms the scheduled task. After that
everything runs through the watcher with Liam away, using a side-by-side test root under `C:\napoleon_remastered_pc\_scratch\j2\`
first, then the live root: a) `noop`, `status`; b) refusals (no lock, wrong owner, game already running, zombie flag faked in the test
root); c) launch to the main menu, kill, relaunch; d) profile `proxy-dxvk`, launch, restore, every file byte-identical to the
baseline; e) lock expiry with a profile active restores by itself; f) a forced hang (a job that suspends the game's threads) is caught,
dumped, archived and killed; g) the display probe; h) the update path, including a rollback. Results go in a dated run report under
`harness/runs/` with the job ids and status files, and as `engine_facts` rows.

## Kill criteria
- The watcher wedges (queue stops, no result) twice for the same cause: stop, collect `watcher.status` and the log, report.
- A zombie Napoleon process: report "PC needs reboot" to Liam and stop; never retry launches.
- Unattended launch fails by every route after 3 attempts each: stop and report what each route did; the rest of the job continues
  with Liam launching.
- Any display or topology change outside the virtual display, or any write to Empire's files or task: stop at once and report.

## Finish
Write `jobs/J2/report.md`: what exists, how to install, update and uninstall the watcher, the test results with job and run ids,
deviations from this brief and why, what moves to the core later, open questions. Then
`wsc reg set jobs J2 status=review report=jobs/J2/report.md`.

## Open questions for Liam (raised while writing this brief)
1. Headless window placement (the proxy puts the game on the virtual display, Empire's `headless.cpp`) is DLL work. Proposal: add it
   to J3 (Opus, already DLL work). A brief branch may only change its own row, so J3's row is not edited here.
2. J1's open question 1 (`proxy.minidump` release value 2) also waits for the next DLL rebuild, which is J3, not this job.
