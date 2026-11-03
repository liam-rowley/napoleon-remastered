# J71 report: 32-bit Vulkan ray-tracing extensions probe

## What was built
Measured on Liam's PC (run `harness/runs/20261103_j71pc`, 2026-11-03): the 32-bit NVIDIA Vulkan ICD (`nvoglv32.dll`, driver 617.14, RTX 4090, Windows 10.0.26200.9711) exposes none of `VK_KHR_ray_query`, `VK_KHR_acceleration_structure` or `VK_KHR_deferred_host_operations` to a 32-bit process, while the 64-bit ICD of the same driver exposes all three; engine fact `napoleon.vulkan.rt_32bit` is filed as `refuted`, and the two PLAN places that said "pending J71" now carry the dated result. D50 is not written: that is Liam's.

- Run folder `harness/runs/20261103_j71pc/`: README (pins, commands, loader lines, RT table, controls), the pins (`pins_*.txt`, `pins_files.tsv`), `help_32.txt`, `summary_{32,64}.txt`, `vulkaninfo_{32,64,32_nolayers}.txt`, `loader_{32,64,32_nolayers}.txt` (plus `loader_summary_{32,64}.txt`), `extensions_{32,64,32_nolayers}.txt`, `only_64.txt`, `only_32.txt`.
- Engine fact `registries/engine_facts/napoleon.vulkan.rt_32bit.json` (positive claim, state `refuted`, evidence the run README, date 2026-11-03).
- `docs/plans/PLAN.md`: one clause in section 6 question 6 (after "D50 (ray tracing stays out pending J71") and one in section 7's "Ray-traced shadows and AO" gate column.

## Evidence
Pins: `nvidia-smi` NVIDIA GeForce RTX 4090, 617.14; `ver` 10.0.26200.9711; `SysWOW64\vulkaninfo.exe` and `vulkan-1.dll` PE machine 0x14c (32-bit), the `System32` pair 0x8664 (64-bit), sizes and sha256 in the run README. Vulkan instance 1.4.341, device API 1.4.351 in both runs.

Loader log (`VK_LOADER_DEBUG=driver`): the 32-bit run loaded `nv-vk32.json` and used `nvoglv32.dll` for the RTX 4090; the 64-bit run `nv-vk64.json` / `nvoglv64.dll`.

| extension (RTX 4090, driver 617.14, run 20261103_j71pc) | 32-bit | 64-bit | 32-bit, implicit layers off |
|---|---|---|---|
| `VK_KHR_ray_query` | absent | present | absent |
| `VK_KHR_acceleration_structure` | absent | present | absent |
| `VK_KHR_deferred_host_operations` | absent | present | absent |
| `VK_KHR_ray_tracing_pipeline` | absent | present | absent |
| `VK_KHR_ray_tracing_maintenance1` | absent | present | absent |
| `VK_NV_ray_tracing` | absent | present | absent |

Device extensions: 270 (32-bit) against 289 (64-bit); the 19 only in 64-bit are all ray-tracing, opacity-micromap, CUDA, optical-flow or NVX extensions; none is only in 32-bit.

Controls: positive control passes (64-bit lists ray_query and acceleration_structure); the 32-bit run reaches the RTX 4090 as a discrete GPU with driver 617.14 through NVIDIA's 32-bit ICD, so the step 5 fallback program was not built; with `VK_LOADER_LAYERS_DISABLE=~implicit~` all five implicit layers are forced off and the 32-bit list is byte-identical (270 names).

Fact as filed: claim "The 32-bit NVIDIA Vulkan ICD on the project PC (RTX 4090, driver 617.14, Windows 10.0.26200.9711) exposes VK_KHR_ray_query, VK_KHR_acceleration_structure and VK_KHR_deferred_host_operations to a 32-bit process (the 64-bit ICD of the same driver: all three)", state `refuted`; notes name the six-extension result, the layer-off rerun, the two reports (ao-vk issue 22, NVIDIA forum thread 76896) and "decides drafted D50 (Liam)". `python3 core/wsc.py reg check engine_facts`: ok, 203 rows.

PLAN clauses: section 6 q6 now reads "D50 (ray tracing stays out pending J71; J71 answered no: fact `napoleon.vulkan.rt_32bit` refuted 2026-11-03, driver 617.14, run `harness/runs/20261103_j71pc`)"; section 7's gate column ends "J71 measured it: no (fact ... refuted 2026-11-03, driver 617.14, run ...: none of the RT extensions in the 32-bit list, all in the 64-bit one)".

Gates (2026-11-03, with this report and the row at `review`): `python3 core/wsc.py gates`: 13 ok, 1 warn, 0 failed (the warn is the capstone-less RE tests skipping); `jobs check`: 72 rows, ok, 0 registry gaps in briefs.

## Deviations from the brief and why
- Model: run on Opus, not Sonnet, by Liam's choice for this session (orchestrator); the brief is unchanged.
- The `--summary` runs' stderr is kept as `loader_summary_{32,64}.txt` beside the brief's `loader_{32,64}.txt`.
- The PE-header and extension-list scripts were throwaway scratch scripts, not committed (a committed script would be a tool needing a registry row); the README states what each did, and the extraction asserted every list length against the `count = N` header.
- The integrated AMD Radeon GPU (GPU1) is listed in every run and ignored for the fact (D13); the README notes it shows the same 32/64 split.
- `docs/plans/PLAN.md` section 6's line "The two measurements that change no scope are queued: J71 and J72" is left as is: the brief allows one clause in each of the two named places only.
- The builder subagent's Write of this report was refused by the harness (subagents may not write report files); per the kill criterion it stopped, and the orchestrator wrote this report from the builder's returned text, after checking the extension lists (270 / 289 lines, 0 RT names in the 32-bit list, 32-bit and layers-off lists byte-identical) and the fact's state.

## Open questions
- Re-probe on driver updates: none scheduled (the brief's recommendation); the fact names driver 617.14. Rerun this job only if an NVIDIA release note mentions 32-bit Vulkan ray tracing, or before anyone reopens D50.
- D50 (sign as drafted, edit or decline) is Liam's; the measured answer is the expected "no", so the drafted D50's "If absent" branch applies.
- Whether to refresh PLAN section 6's "queued: J71 and J72" sentence once J71 merges (outside this brief's two clauses).
