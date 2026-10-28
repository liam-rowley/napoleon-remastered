# Run 20261028_exeinfo: Napoleon.exe identity re-checked on the PC

Date 2026-10-28 19:59Z. Agent: proxy skeleton job (phase 1, job 1). Read-only: the game folder was mounted on the PC's device VM and
`proxy/tools/exe_info.py` (sha256 `4e4fdefeb193...`, the committed file) ran against `Napoleon.exe`. Nothing on the PC was written.

Result (verbatim fields from the tool's JSON):

| field | value |
|---|---|
| file size | 17,895,424 bytes |
| sha1 | `9aebcd2172f2878d781b079f7feb45b0e12e0250` (same as PLAN.md section 1) |
| sha256 | `44880ec1770f600163a336eec83b4366901484c5cceec83dc326e2932f02a054` |
| machine | 0x14c (x86, 32-bit) |
| PE TimeDateStamp | `0x645e917f` |
| SizeOfImage | `0x014eb000` |
| CheckSum | `0x00000000` |
| ImageBase / entry RVA | `0x00400000` / `0x00e6e7d0` (inside `.text`) |
| large-address-aware / ASLR / NX | yes / yes (has `.reloc`) / yes |
| sections | `.text` 0x1000 (vsize 0xf058fc), `.rdata` 0xf07000, `.data` 0x104e000 (vsize 0x3f5ed8, raw 0x1f600), `_RDATA` 0x1444000, `.rsrc` 0x1447000, `.reloc` 0x1462000 |
| DRM stub signs | none (no `.bind` section, entry point in `.text`: the code is not encrypted at DllMain) |
| d3d9.dll imports | `Direct3DCreate9`, `D3DPERF_EndEvent`, `D3DPERF_BeginEvent` |
| other imports | advapi32, binkw32, comdlg32, d3dx9d_40, dinput8, dsound, gdi32, kernel32, mss32, ole32, oleaut32, rpcrt4, shell32, shlwapi, steam_api, tbb, user32, version, winmm, ws2_32 |

Game folder top level at the time: `D3dx9d_40.dll`, `Napoleon.exe`, `binkw32.dll`, `data\`, `installscript.vdf`, `miles\`, `mss32.dll`,
`redist\`, `steam_api.dll`, `tbb.dll`, `tbbmalloc.dll`. No `d3d9.dll` (vanilla). The device seen was `officepc` (Windows x64).

Pinned from this run: `proxy/napoleon/identity.json`; facts: `registries/engine_facts.jsonl` rows `napoleon.exe.*`.
