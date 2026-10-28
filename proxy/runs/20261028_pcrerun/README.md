# Run 20261028_pcrerun: proxy head build on the PC (J1 review findings 2 and 6)

Date 2026-10-28, 21:56Z to 21:59Z. PC `officepc` (Windows x64, RTX 4090, NVIDIA 617.14). Liam present and launching the game from
Steam; the agent read logs, changed the config and uninstalled through the device VM. Build under test: **30a7b815163a** (the head
build of `job/J1`; `d3d9.dll` sha256 `b15bf2bba2f6fb97fac57429d295da7158cf5ef289b2f0cda4392670ea774e36`, the same bytes the cloud
container builds from the branch and `build.sh repro` reproduces), kit `kit_20261028T212023Z_30a7b815163a`, installed 21:23Z
(verified, pre-install snapshot `pre_install_20261028T212314Z`). DXVK 3.1.1. WER LocalDumps on for Napoleon.exe (every log: `on, DumpType 2`).

Re-runs b and d of `20261028_pctest` on the head build, as the review asked (`jobs/J1/review.md` findings 2 and 6). Steps a and c were
not repeated: a is vanilla, and c's backend path is the one d runs (d uses DXVK).

| step | setup | launch id | result | evidence |
|---|---|---|---|---|
| b | `backend=system` | `20261028T215649Z-p14112` | guard `match`, plan all on; **`file ImageBase 0x00400000, delta 0x00210000`** at base 0x00610000 (finding 2: the delta is no longer 0); 0 sites; system d3d9 from `C:\WINDOWS\system32`; main menu; `process detach (process exit)` | `b_system_proxy.log` |
| d | `backend=dxvk`, `exe_guard_force_mismatch=1`, `minidump=2` | `20261028T215820Z-p7484` | `FORCED MISMATCH` -> plan all off, `patch_engine: not run (pass-through)`, notice written; DXVK serving, its log and caches in `napoleon_remastered\dxvk\`, 0 `err:` lines; main menu, **borderless** (Liam); clean exit; mode 2 wrote no dump | `d_mismatch_dxvk_proxy.log`, `d_EXE_MISMATCH.txt`, `d_dxvk_d3d9.log` |
| e | `pc_deploy.py uninstall` | - | owned files moved to `_to_delete\uninstall_20261028T215920Z\`; `identical: true, diffs: []` against the pre-install snapshot (1564 files); the post-uninstall snapshot also equals `vanilla_before_a.json` (1564 files, 0 differences) | `e_install_history.json` |

Dumps (finding 6): `crashdumps_before.txt` (21:22:56Z) and `crashdumps_after.txt` are `ls -laR` listings of
`%LOCALAPPDATA%\CrashDumps` taken by the agent; they differ only in the VM session path, so no dump was written by either launch, and
`napoleon_remastered\dumps\` was never created. Kill criteria: not hit.

## Found

1. **The game replaces the top-level crash filter**, so `minidump=1` (the release value) never dumps an unhandled crash in-process on
   this PC: `CSERHelper.dll+0x12571` holds it by the first `Direct3DCreate9`, `Napoleon.exe+0xe6f074` by process detach (both launches).
   WER LocalDumps still works, and mode 2 ran a launch without a false dump. Not changed in J1: the shipped value lives in
   `proxy/napoleon/`, a DLL input, so changing it would make the head binary differ from the one tested here. Fact
   `napoleon.crash.toplevel_filter_replaced`; open question 1 in `jobs/J1/report.md`.
2. The first `uninstall` attempt (21:59:09Z) stopped before anything was removed because deletion was not yet allowed for the game
   folder from the device VM; it had copied `d3d9.dll` into `_to_delete\uninstall_20261028T215909Z\` (a stray copy, harmless). With
   deletion allowed, the second attempt completed. The tool behaved as `proxy/README.md` describes; the stray copy is Liam's to delete.

## Facts recorded

`napoleon.loader.mapped_imagebase_rewritten` (notes: confirmed on the PC), `napoleon.crash.toplevel_filter_replaced` (verified),
`napoleon.dxvk.menu_display_mode` (open: one observation).
