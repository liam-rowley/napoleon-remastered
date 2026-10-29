# Run 20261029_4kcrash: game crashes when Liam changes the resolution to 3840x2160

officepc, 2026-10-29 09:23-09:24 UTC, Liam playing by hand (not a watcher launch). Proxy build `edde0cedd087` (sha256 `e07b56a9...`,
rebuilt byte-identical from the commit), every dev key off, `proxy.backend=dxvk` (3.1.1), `proxy.minidump=2`. Two launches, both
crashed right after the game recreated its device at 3840x2160 (the DXVK log shows the 2560x1440 device destroyed, a new device and
a 3840x2160 fullscreen swapchain created, then nothing; the proxy log has no detach line).

| launch (pid) | WER dump (`%LOCALAPPDATA%\CrashDumps\napoleon_remastered`) | fault | ESP vs stack limit | EDX |
|---|---|---|---|---|
| 18824 (09:23Z) | `Napoleon.exe.18824.dmp` | AV writing `0x01870fe0`, `d3d9.dll+0x4cfb1` = `_mingw_pformat` | 28 bytes past the 1 MB limit (`0x01871000`) | |
| 17648 (09:24Z) | `Napoleon.exe.17648.dmp` | AV writing `0x01870ff8`, `d3d9.dll+0x4b8c6` = `_pformat_xint` | 4 bytes past the limit | `0xC00000FD` |

Offsets symbolized with `i686-w64-mingw32-addr2line` on a `-g` build of the same commit (same `.text` layout). Both on the game's main
thread (the DllMain thread). Event log: Application Error, faulting module `d3d9.dll` (ours), 0xc0000005.

**Cause (ours):** the main thread's stack overflowed (STATUS_STACK_OVERFLOW, first-chance; EDX holds the code being formatted) and the
vectored handler (`core/crash.cpp`) formatted a log line on the exhausted stack (LogWrite alone uses ~4.3 KB), faulted inside the
formatter and killed the process. **Fix:** build `99c4503daf5e` (`core/crashpolicy.h`, `tests/test_crash.cpp`): on a stack overflow or
with under 32 KB of stack left the handlers only record the exception; it is logged later from a thread with stack ("was NOT logged
when it happened") at the next `Direct3DCreate9`, the top-level filter or detach.

**Open:** what overflows the 1 MB main stack at the 4K device recreation (the game, DXVK or the NVIDIA driver; `nvgpucomp32.dll`
and `amdvlk32.dll` frames are on the stack). With the fix in, a retry at 4K either survives (the overflow was handled by its owner)
or leaves a WER dump with the real overflow chain intact. Dumps copied to `C:\napoleon_remastered_pc\_scratch\j3\wer_4k\` (1 GB each,
not committed). Dump parsing: python `minidump` 0.0.24 on the device VM (exception record, TEB stack limits, context registers).
