# J3 review: dev control channel and load time

2026-10-29. Independent reviewer: Opus 5.5, fresh chat (did not build `job/J3`). Reviewed at `6aac513`, fix commit on top listed below.

**Verdict: merge after fixes.**

The job delivers what the brief asks for, and its numbers hold up. The one thing to fix before merging is the map check (finding 1).
It is the check the brief singles out (Empire ran "Flanders" on Anatolia), and as built it does not show which map the engine
actually loaded.

## What I ran

- `wsc gates`: 11 ok (31 host tests). `proxy/tools/build.sh all`: DLL builds with only system imports and the expected exports
  (`luaopen_wsp`, `wsp_sentinel` added), 592 host checks pass (test_dev 135, test_crash 18). `build.sh repro`: identical from
  another path.
- I recomputed the baseline from the raw timelines with the committed tool:
  `timeline_table.py movies=B1..B5 skip=S1..S5` gives front end 131.36 (130.70-131.70) / 6.99 (6.85-7.39) and land battle
  deployed 154.17 / 26.36. These match the report exactly.
- PC (read only): the watcher log at 10:34:12Z shows all five config targets restored with 0 mismatches. The post-uninstall
  snapshot `snapshots/pre_install_20261029T103610Z.json` has the same 1564 files with the same sha256 as the 08:17Z pre-install
  snapshot. Only Steam's `installscript.vdf` mtime moved; its content is the same. No `.cmd` was left in `ctl\`.
- I could not read the CI run list: the session had no GitHub API access.

## Risk-first reading

I read these in depth: the dev gating in `dllmain.cpp`/`DevInit` (with every key off it must behave as J1), `hooks.cpp` (IAT
writes), `files.cpp` (it sits on every file open the game makes), `luabridge.cpp` (it works on the engine's `lua_State`),
`crash.cpp`/`crashpolicy.h`, and the control channel (`dev.cpp` `HandleRequest`/`CtlThread`, `job.sh ctl`).

- Gating is sound. With no dev key, `DevInit` returns before doing anything. Pass-through logs and returns. Every entry point checks
  `s_active`. `test_dev.cpp` lints the order of these checks.
- The Lua bridge follows the Empire safety rules: it never raises a Lua error from C and never calls back into Lua. The lint test
  enforces both.
- The crash policy is a good change and is host-tested.

## Findings

### Blocker
None.

### Should-fix

1. **The map check does not show what the engine loaded.**
   - Where: `proxy/core/files.cpp:47-60`, `proxy/core/dev.cpp:176` and `:204-206`.
   - What happens: `battle.map_folder` is erased before `autostart.lua` runs. The front end's map-list walk then probes every map's
     preset folder, and the last folder it probes is the selected map. `MapProbe` reports a folder only when it differs from
     `s_lastMap`, so when the battle load probes that same folder, the probe is suppressed. The value sent as `map_folder_loaded` is
     then the front end's selection probe, not anything the load opened.
   - How to see it: `proxy/runs/20261029_j3pc2/raw/f_resets10/proxy.log`, first launch. Lines 85-94 hold ten `battle.map_folder`
     reports, all before `frontend -> loading` at line 98, and none between the loading start and the battle at line 107. On the
     second cycle the walk ended on `nap_mp_homestead`, so the load's own probe of `nap_mp_grassy_flatlands` does show (line 149,
     0.7 s after loading began). The load does probe the folder; the dedup hides it.
   - What it misses: the check passes without evidence when the load probes nothing, or when it probes a folder equal to the
     walk's last one.
   - Fix: clear `s_lastMap` (a `FilesMapReset()`) and erase `battle.map_folder` at `OnLoadRequested`, after `autostart.lua`
     returns, so only probes made during loading count. Then confirm on one PC launch per preset. If the load ever probes nothing,
     the check fails closed: "the engine opened no map preset folder".
   - The report's "map checked every time" needs that PC run to be true.

2. **The baseline is narrower than the brief, and the report does not say so.**
   - Brief deliverable 2 asks for at least 5 launches per arm into a land battle, a naval battle and a new campaign.
   - What ran: the movies arm has front end and land battle only. Naval and siege have n=3 and campaign n=4, all with the intro skip
     on.
   - This barely changes the numbers, since battle load is 18.2 s in both arms. But it is a deviation, so it belongs in the report's
     Deviations section. That is one line for the job chat.

3. **Fixed in this review (`8c0fa90`): `job.sh ctl` left an unanswered request in place, and the proxy would run it on a later
   launch.**
   - The cause: `CtlThread` runs every `*.cmd` it finds with no staleness check (`dev.cpp:364-375`), and the no-answer path of
     `job.sh ctl` said "The request stays".
   - What could go wrong: a timed-out `exit` or `reset` would fire into the next launch that has `dev.ctl=1`.
   - The fix: on no answer, `job.sh` now renames the request to `<id>.cmd.expired`. This races the proxy's rename to `.cmd.taken`,
     and only one rename wins. If the proxy already took the request, `job.sh` says so instead.
   - Tests: `tests/test_job_sh.py` gains `test_ctl_ok_and_exit_codes`, the first tests of `ctl` at all, and
     `test_ctl_no_answer_withdraws_the_request`, which fails on the old script. `proxy/README.md` documents the behaviour.
   - Not a DLL input, so the build id is unchanged.
   - Follow-up for the job chat: the PC's device-VM copy of `job.sh` should be re-synced.

### Later

4. Every kit now ships the dev pack and the dev Lua files (`proxy/tools/pc_deploy.py:58-67`). They are inert with the keys off, but
   a release kit should drop them. Belongs with packaging; not in this phase's scope.
5. `job.sh ctl` works out the ctl folder from the watcher root (`harness/core/job.sh:38`, `dirname $ROOT/ctl`) and does not read
   `dev.ctl_dir`. If someone changes the key, every call times out with only a hint. Read the folder from the adapter, or the
   kit's ini, in one place (J12, since both move to the core).
6. Empire repeat: the mid-sitting Lua sync and the stale-resend workaround (unique staged names plus a sha check) live only in the
   PC scratch `j3run.sh`. "A learning becomes code first" means a `pc_deploy.py sync-lua` (or similar) verb. J4's control API is
   the natural owner.
7. `proxy/core/hooks.cpp:3-4`: the header comment is garbled (the static-CRT fact appears twice, the parentheses are unbalanced,
   and it says `<game>` where it means Napoleon). Fix it with the next DLL change; touching it now would move the build id away from
   the PC-tested one.
8. The `core_pin` gate sees the superproject's git status from a linked worktree (report open question 4). This is a warscape-core
   fix and goes to that repo's `docs/BACKLOG.md`. I did not file it: this session could not attach warscape-core.

## Brief compliance (summary)

- Deliverables 1, 3-8, 10 and 11 are present with evidence.
- 2: see finding 2.
- 9: the battle reset is done: 10 in a row, +1.5 MB per cycle, no crash. The campaign reset is left open, which the brief allows
  (relaunch as the fallback), and the report names it.
- Kill criteria were respected. The 4K crash was investigated from the WER dumps, not by relaunching.
- The DXVK state-cache default is removed as briefed.
- Scope: J16 was split off correctly as a plan PR.

## To merge

1. The job chat fixes finding 1 and records one PC launch per preset showing `map_folder_loaded` coming from a probe made during
   loading.
2. It adds the finding-2 line to the report.
3. A re-review of the change then sets `status=done review=jobs/J3/review.md`. This review leaves the row at `review`.
