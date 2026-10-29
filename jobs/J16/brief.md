# J16: In-game resolution change crash (stack overflow at device recreation)

Phase 1, job 16. If Liam changes the resolution in the options screen from 2560x1440 to 3840x2160, the game dies. Launching
straight into 3840x2160 works. Before J3's crash-handler fix (build `99c4503`) it crashed: the main thread overflowed its 1 MB stack
while the game recreated its D3D device on DXVK. Since that fix it hangs instead (Liam, 2026-10-29 11:17Z, pid 11252). Find what eats
the stack, or what the main thread waits on, and fix it in the proxy or in DXVK's config. Each claim about the cause rests on a dump
or an A/B launch, never on a guess.

Model: Opus, reason: crash and hang analysis from full dumps, D3D9/DXVK/Vulkan-driver behaviour and proxy DLL changes (D15). Budget
about 160 tool calls; at the cap, stop, commit, report what is left. At most 1 subagent, only for independent work (for example the
host tests while you read a dump). Waiting belongs to the harness: `job.sh` blocks inside one call; never poll.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J16`). Read `docs/DECISIONS.md` (D2, D15, D23, D26, D30, D31), `proxy/README.md` ("Config, log,
  crash capture" and the pass-through contract), `harness/README.md` (launch, profiles, hang watchdog), `jobs/J3/report.md` (the 4K
  item and its open questions) and `proxy/runs/20261029_4kcrash/README.md` (the two first crashes, the fix, the 4K-at-launch run).
- Search the registries first (`python3 core/wsc.py find crash dump dxvk resolution`). Extend `proxy/core/crash.cpp`, `crashpolicy.h`,
  `backend.cpp` and `pc_deploy.py`; do not write a second of any of them. Any dump reader you write is a committed tool with a header
  and a `tools` row, and it takes the dump path as an argument.
- `empire-remastered` (read only): search `docs/learnings/` for WER, stack, Reset and DXVK (Empire lesson 23: read WER first).

## Target facts
- Main thread = the DllMain thread, 1 MB reserve, limit `0x01871000` in both early dumps. The early overflows died in our formatter,
  then in `ntdll` (ESP 4 to 224 bytes past the limit). `nvgpucomp32.dll` and `amdvlk32.dll` frames were on the stack: an AMD Vulkan
  ICD is loaded beside the NVIDIA one on an NVIDIA PC.
- The first two crashes destroyed the 2560x1440 device and created a new one (a second `Direct3DCreate9`). The 11:17Z hang was a
  device `Reset`: DXVK's log ends after `ResetSwapChain` to 3840x2160, with no second `Direct3DCreate9`. The proxy log ends at the
  first `Direct3DCreate9` and has no deferred crash record. The loading screen stopped at about 3 %, and Liam force-closed the game
  through Steam at about 11:19.
- Dumps in `%LOCALAPPDATA%\CrashDumps\napoleon_remastered\` (not committed; copy them to `C:\napoleon_remastered_pc\_scratch\j16\`
  before anything rotates them): `Napoleon.exe.11252.dmp` (1.7 GB, the hang, written at the force-close), plus `3248` (10:01),
  `1824` and `(1).1824` (10:05) and `4556` (11:25). The last four are not tied to a known launch yet: find out what each one is
  before you use it as evidence.
- Not on the PC: cdb/WinDbg (x64dbg is installed via winget). Python `minidump` is not installed here; J3 used 0.0.24 in the cloud.
- Vanilla d3d9 path: `proxy.enabled=0` (pass-through) and `proxy.backend` other than `dxvk`. Check in `proxy/README.md` which one
  loads the system `d3d9.dll`.

## Decisions already made for this job
- **Read the hang dump first**, before any launch. Check its exception record to see how it was taken (WER after
  `TerminateProcess`, a hang report, or a real exception). Then: every thread's stack; the main thread's ESP against its limit; what
  the main thread is blocked on (a wait, a loop, a `SendMessage` to another thread); and which modules own the frames (game, our
  `d3d9.dll`, `d3d9_dxvk.dll`, the NVIDIA driver DLLs such as `nvgpucomp32`, `amdvlk32`, `vulkan-1`). Use symbols from the Microsoft symbol server for
  system DLLs, and the `-g` build of the matching commit for ours (as in `20261029_4kcrash`).
- **Debugger:** cdb (WinDbg, `winget install Microsoft.WinDbg`) is the right tool for an x86 full dump. Installing it on Liam's PC is
  his call (open question 1); until he says yes, use python `minidump` pinned by version in a venv under `_scratch\j16\`, run with
  `-I`.
- **Is the hang ours?** J3's fix turned the crash into a hang. Rule out that the proxy's handlers (record-only on overflow, then
  `EXCEPTION_CONTINUE_SEARCH`) cause it, for example a loop of guard-page faults with no stack left, or a lock held across the fault.
  The dump and the `proxy.enabled=0` arm decide this.
- **A/B arms, through the watcher only** (never start `Napoleon.exe` yourself). Each arm starts from a profile at 2560x1440 and
  switches in game:
  - a) the current kit (DXVK 3.1.1, dev keys off);
  - b) vanilla d3d9;
  - c) DXVK with the AMD ICD hidden (`VK_LOADER_DRIVERS_DISABLE` or DXVK's `DXVK_FILTER_DEVICE_NAME`: check both against the
    pinned loader and DXVK 3.1.1 before you rely on them);
  - d) other pairs: 1920x1080 to 2560x1440, 2560x1440 to 1920x1080, and 3840x2160 to 2560x1440 (is it 4K, or any in-game switch?);
  - e) windowed against fullscreen if the options allow it.

  At most 3 launches per arm, and the watcher's hang watchdog or `kill` ends each stuck one. WER LocalDumps stays on.
- **Who switches the resolution.** First try the switch through the engine's own options Lua over the J3 control channel (`ctl lua`;
  never coordinate clicks). If that cannot be done in 3 attempts, Liam does the switch by hand during a watcher launch. Tell him
  before each sitting, because the game shows on his monitor.
- **Fix where the cause is, inside D2.** `Napoleon.exe` is never changed on disk, so the PE stack reserve cannot be raised there.
  Candidate fixes, chosen by the evidence:
  - a DXVK or loader setting the proxy sets (the `backend.cpp` env defaults, or `dxvk.conf` in `napoleon_remastered\dxvk\`);
  - a proxy wrapper that breaks a re-entrant `Reset`/`CreateDevice`/window-message loop;
  - running the device call on a proxy thread with a large stack while the main thread waits, but only if the dump shows the deep
    frames are driver-side and the window's message pump cannot deadlock it.

  Any engine-code hook goes through `engine_sites` with anchor bytes behind the identity guard (D23). A new key gets a
  `config_keys` row with its default and release value.
- **No vanilla regression:** with the fix in, launch at 2560x1440 and at 3840x2160, then switch in game both ways, 3 times each. The
  pass-through contract and its lint test stay unchanged. Uninstall stays byte-identical.

## Deliverables
1. Dump analysis of `11252` and a classification of the other four dumps: what each is, the main thread's stack depth and its
   deepest repeating frames, and the module that owns the recursion or the wait. Write it as a run report
   `proxy/runs/<utc>_j16dumps/README.md` (offsets, not dumps).
2. The A/B table (arm, launches, outcome, run ids, the DXVK and proxy log tails) in `proxy/runs/<utc>_j16ab/README.md`.
3. The fix, with host tests where it is code (`tests/`), and a PC run that shows the in-game switch surviving.
4. `engine_facts` rows with date and run id for every fact found (the cause, the ICD list, the vanilla behaviour), and `config_keys`
   or `engine_sites` rows for anything the fix adds. Also the `tools` row for any dump reader.
5. If the cause is the game or a driver and no fix inside D2 holds: a guard that keeps the game alive (for example, the proxy
   turns the in-game switch into a clear "restart to apply" path), proposed in the report for Liam's decision and not shipped
   without it.

## Kill criteria
- The hang dump cannot be read after the pinned python reader and (if Liam allows it) cdb: stop that line and go to the A/B arms.
- Vanilla d3d9 (arm b) fails the same way: the bug is not DXVK's. Stop fixing; report the evidence and deliverable 5's proposal.
- Three fix approaches fail on the PC: stop, ship nothing that changes the default path, and report each attempt with its run ids.
- Any launch at the profile's starting resolution (before the switch) crashes or hangs: stop. A regression came in; do not keep
  relaunching.

## Finish
Write `jobs/J16/report.md`: the cause with the evidence chain (dump frames, then A/B arms, then fix run), the fix and why it is safe
on vanilla, run ids, deviations from this brief and why, open questions. Then
`wsc reg set jobs J16 status=review report=jobs/J16/report.md`.

## Open questions for Liam (raised while writing this brief)
1. **May the job install WinDbg** (`winget install Microsoft.WinDbg`, gives cdb)? It reads x86 full dumps with symbols far better
   than python `minidump`. If not, the job uses the pinned python reader only.
2. Four more dumps sit beside the hang dump (10:01, 10:05 x2, 11:25). Do you remember what those were (J3 sitting 2, the review
   re-check)? If not, the job classifies them from their contents.
3. If the in-game switch can't be scripted, the A/B arms need you at the PC for the switch: about 15 launches, a few seconds each.
