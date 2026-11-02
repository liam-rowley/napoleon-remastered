# J30 PC run 2026-11-02: the RmlUi host in game

Lock owner `j30`, watcher 1.2.0, DXVK backend, headless (virtual display) at 1920x1080, 2560x1440 and 3840x2160. Driver `run.py` (one
call per phase, everything waited for by `core/harness/ctl.py` and `job.sh`), summary `summary.py` (`--recheck` reruns the checks).
Raw step records: `results.jsonl` (lines before 18:50:30 UTC are the first cells run, which hung in the battle; kept as the record).

## Builds
| build id | what | where it ran |
|---|---|---|
| `j30pc3`, `j30pc4` | dev builds (manual id): first start-up crash fixed (j30pc3), FPU-safe timers and relative image paths (j30pc4) | smoke |
| `j30pc5` | dev build: + the VtableHook chain fix | cells at 1080p, front end and campaign at 1440p and 4K, the bisection |
| `68a9bc84bb05` | the would-be final id: Napoleon `job/J30` + core at warscape-core branch `napoleon-j30` `f12b56e` as the gitlink (local commit, not pushed); sha256 `13a4411e60055bcdb830ed11fe1e652a9d2531022fa3401de0ebe8dc8260c5a1`, 4,224,512 B | battles at 1440p and 4K, all perf cells |

Before the host: 973,312 B (main's kit `kit_20261102T154016Z_23dbc9e2d143`, build `23dbc9e2d143`). Imports after: advapi32, dbghelp, kernel32,
msvcrt, user32 (system only). `build.sh --docker all` 415 s locally with the RmlUi/FreeType objects compiled fresh for mingw and the host
(about 155 s with them cached); `repro`: identical from another path (both on 68a9bc84bb05 and j30pc5).

## Start-up and hang history (both fixed in the core, both learnings now code)
1. 18:11 and 18:12 UTC (two launches, document shown): access violation at EIP 0 in `CompileShaders` (dumps
   `napoleon_remastered\dumps\20261102T18114*Z-*.dmp`, now in `_to_delete`): the D3DCompile blob was a TU-local abstract C++ class and GCC
   turned every call through it into `call 0`. Now a C-style vtable; `test_ui_core` lints it.
2. 18:30 and 18:39 UTC (a document; then the idle host): every land battle load hung (watcher kills `runs\20261102T183258Z_hang`,
   `runs\20261102T184216Z_hang`). With `ui.enabled=0` the same DLL loaded in 12.6 s. Cause: the battle loader's 1x1 helper device shares the
   main device's vtable; the dev side re-hooked Present in front of the host's hook and the two called each other forever. Fixed in
   `VtableHook` (a detour already in a slot's chain is never installed again); with the fix the battle loaded with the document in 16.1 s.
   Fact `napoleon.ui.helper_device_rehook`.

## b) dumps and checks (`tools/ui_hosttest.py check`, `checks/*.json`, crops in `crops/`)
| cell | rules solid | box edges | H height | note |
|---|---|---|---|---|
| front end, campaign, battle, after warm reset at 1080p x 100 | ok | ok | ok | |
| the same at 1440p x 100 | ok | ok | ok | dp 1.3333 |
| the same at 4K x 100 | ok | ok | ok | |
| front end, campaign, battle at 1080p x 85 | **fail** | ok | ok | the 1 dp rule on a half pixel vanished (fact `rmlui63.sub_pixel_rule`); the other four are one solid row |
| front end, campaign, battle at 4K x 125 | ok | ok | **fail (1 of 4)** | 14 dp at 35 px: H ink 26 rows against a 24.2 px cap height (20, 28, 40 dp within 0.6 px) |
"H height" compares the H ink with the font's cap height (OS/2 sCapHeight / em, 0.692) x size x dp ratio, within 1 px of the strict or the
faint ink extent. No blended edge rows anywhere (`blend_rows` 0). The crispness verdict is Liam's, from `crops/`.
Full PNGs (91 MB, not committed) are on the PC in `C:\napoleon_remastered_pc\_scratch\j30\dumps\`; sha256:
```
1fb6ca1e2335d696d2f9aa5d7c4982a1e48e4ab3cd1321d3ca83155a67c83681  after_reset_1080.png
1783d3fa0a00c509582cfa475ea451a5386b11b495777aae938b969d67f1529a  after_reset_1440.png
038bd209019e432d71693bc925e9a5ce9036c0a3674eb917ee5f367410d72c5d  after_reset_2160.png
6313a11f02b3ca71dc4a371c6d41e9604470b900e930f5c99a4865791cd19b2f  battle_1080_100.png
76bc778cccbf3f92174d988731c14a71c0278e0d0d958ed7e724ab0d23afca8b  battle_1080_85.png
64e881c6465a2da744604e2e2484b1e5125df1d22b576651d37a7d9c1fc380e1  battle_1440_100.png
02da48c0101aeab957283e30b4ae54da64d3a69117a3de5e47b60eac734f4203  battle_2160_100.png
1411810d0250b22fa78cb9ccf1f366f56b1aec2feba6ee61916d4bd5120be480  battle_2160_125.png
8e7e4a734282105d69393880c9d95d1d01b4fb9963b8d553f80aa9dec5cce526  campaign_1080_100.png
9a3592149a2f52177224c61cbb2d3143802a3737d4187e5fe416148f5ca769b0  campaign_1080_85.png
95ce225073920c8031ced6364546202dcb7ff81abcdaa4a9080b85612809fe78  campaign_1440_100.png
1e1c331c4b7ff316292571442176638b1c105f29c572555d7058f826edd9ef4b  campaign_2160_100.png
54b3d986e4718b5ef9921391c6ade49aafdd425286c94e178d8e37e55f639f5c  campaign_2160_125.png
f76b9f3235d9a2243b42394b42bd6dc49a4c17fb6542c71d93aa0d1b3e1a462d  frontend_1080_100.png
3068ea5ecb48bbc8449b241fb553a0b62dc71833837f2e4a493ae78547dfd820  frontend_1080_85.png
89a98b2e68ca94a0d0879ce86cf2e899ceab8f1116630ee22654755a47f73126  frontend_1440_100.png
fb07f26b880160d882e3aca87d78a92bb12106a02237ab701fd14aa14e633901  frontend_2160_100.png
e11783c73c10aa4a82d25a3377f95da4caee419bf70ff0bd78ea73628761f2bb  frontend_2160_125.png
dd59701102f0b79376034ca63ec5b2d9c93b30e6ce56c6b48ecd4eed2a6a44ac  smoke_fe_1080.png
```

## c) interaction (`results.jsonl` step `interaction`)
Every cell after the fixes passed all nine checks: a click on the target counts in RmlUi (down/up [1,0]) and not the engine; a click off
the document is the engine's ([0,1]) and the counter stays; a press begun on the engine and released over the document stays the engine's;
the wheel over the list goes to RmlUi and scrolls it (`scrolled.list` > 0 a second later), over the button or the game it goes to the
engine; hidden, the target's spot is the engine's; shown again and reloaded, RmlUi's. Cells: front end, campaign and battle at 1080p, 1440p
and 4K, and after a warm reset from the battle at each size. (The first cells run's 1440p and 4K battle lines failed because ctl.py
relaunched the battle at its default 1080p; `run.py` now relaunches at the cell's size.)

## d) frame cost (DXVK; `perf 10` x 3 per cell; `ui state` cost over the same window)
`summary.py` prints the table. Host CPU cost per drawn frame (Context::Update + render): p50 0.06-0.11 ms in every scene and size, p99
0.14-0.18 ms (first frames up to 24 ms while fonts and textures are made); idle host (ui.enabled=1, nothing shown): p50 0.000 ms, the hook
returns at once. Frame-time p50 with the document minus off: front end +0.06/+0.05/+0.08 ms, campaign +0.11/+0.52/+0.13 ms, battle
-0.05/+0.12/+0.11 ms at 1080p/1440p/4K; the frame-time spread between runs of one cell is about 0.3 ms, so the idle host is not
separable from off. Memory: address space +2-8 MB and commit +0-6 MB with the document over off. System d3d9 backend: not measured, the
headless launch with `proxy.backend=system` failed before the front end with the host off (`HEADLESS FAILED: no on_virtual status`).
