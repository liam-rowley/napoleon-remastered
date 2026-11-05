# J71: 32-bit Vulkan ray-tracing extensions probe (fact napoleon.vulkan.rt_32bit)

Phase 3, one measurement, no scope change. The moonshots record (`docs/plans/MOONSHOTS_2026-11-01.md`, "Ray tracing stops at the 32-bit NVIDIA ICD
unless a ten-minute probe says otherwise" and "Feature 3") rests its ray-tracing verdict on one question: does the **32-bit** NVIDIA Vulkan driver (ICD)
on the project PC expose `VK_KHR_ray_query`, `VK_KHR_acceleration_structure` and `VK_KHR_deferred_host_operations` to a 32-bit process? `Napoleon.exe`
is 32-bit, so DXVK inside it sees only what the 32-bit ICD offers. Two user reports (2019, driver 430.86; ao-vk issue 22, 2026-10-29, driver 621.01 on an
RTX 4080 SUPER) say it exposes none of them while the 64-bit ICD does. This job measures it on Liam's RTX 4090 with the installed driver, files the
engine fact `napoleon.vulkan.rt_32bit`, and stops. The fact decides whether the drafted D50 (PLAN section 6 question 6) is ever written; writing D50 is
Liam's, not this job's.

Model: Sonnet medium (D15). Two runs of an installed tool, a text comparison and a registry row: no reverse engineering, shader, DLL or crash work,
so nothing here earns Opus. Budget about 25 tool calls (about 40 only if the fallback probe program in step 5 is needed); at the cap, stop, commit,
report what is left. No subagents. No game launch and no watcher: the probe runs outside the game.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J71`). Read the two record sections named above (not the whole record), `docs/plans/PLAN.md` section 2 (the
  "64-bit bridge" exclusion) and section 7's "Ray-traced shadows and AO" row, and `docs/DECISIONS.md` D13 (NVIDIA only) and D30.
- `python3 core/wsc.py find vulkan driver dxvk` first: J23 pinned the GPU and driver in `perf/baseline.json` (RTX 4090, driver 617.14 on
  2026-11-01); the driver may have changed since, so read it again, do not copy it.
- `needs_pc` is true: the answer is a property of this PC's GPU and installed driver. Nothing takes the game lock; the probe may run while the watcher
  holds the game. It installs nothing, downloads nothing and writes only inside the run folder.

## What is on the PC (brief writer's read-only look, 2026-11-03)
Both loaders and both `vulkaninfo` builds ship with the driver: `/c/Windows/SysWOW64/vulkaninfo.exe` (2,626,608 bytes) and
`/c/Windows/System32/vulkaninfo.exe` (3,082,800 bytes), each beside its `vulkan-1.dll`, all dated 2026-09-19. No Vulkan SDK is installed and none is
needed. From the 64-bit Git Bash, the `SysWOW64` path reaches the 32-bit files and `System32` the 64-bit ones (no WOW64 redirection for a 64-bit
caller); the run proves which is which (step 1), it does not trust the folder names.

## Steps
Run folder: `harness/runs/<YYYYMMDD>_j71pc/` (a `runs/` folder: exempt from rule 79). Run every command with the run folder as the working directory, so
anything `vulkaninfo` writes beside itself lands there and nowhere else.
1. **Pins.** GPU name and driver version (`nvidia-smi --query-gpu=name,driver_version --format=csv,noheader`), the Windows build (`cmd //c ver`), and for
   each of the four files (both `vulkaninfo.exe`, both `vulkan-1.dll`): size, sha256 and the PE machine field (0x14c = 32-bit, 0x8664 = 64-bit; a few
   lines of Python reading the header). `vulkaninfo.exe --help` once, to use this build's own flags for the summary and the full output.
2. **Two runs, each with the loader's driver log.** For `bits` in 32 (`SysWOW64`) and 64 (`System32`): `VK_LOADER_DEBUG=driver <exe> --summary` and the
   full text output, stdout and stderr to separate files (`summary_<bits>.txt`, `vulkaninfo_<bits>.txt`, `loader_<bits>.txt`). The loader log names the
   ICD manifest each run loaded (expected: NVIDIA's 32-bit manifest for the `SysWOW64` run, the 64-bit one for `System32`); quote the line in the README.
3. **Extension lists.** From each full output, the device extensions of the NVIDIA physical device (vendorID 0x10de, the RTX 4090; ignore any other
   device such as a software rasterizer, and say if one is listed) into `extensions_<bits>.txt`, sorted, one name per line, and `only_64.txt` /
   `only_32.txt` for the differences. Record for each run, present or absent: `VK_KHR_ray_query`, `VK_KHR_acceleration_structure`,
   `VK_KHR_deferred_host_operations`, and for completeness `VK_KHR_ray_tracing_pipeline`, `VK_KHR_ray_tracing_maintenance1` and `VK_NV_ray_tracing`.
   Also record each run's `driverVersion`/`driverInfo`, the instance and device API versions, and the implicit layers listed.
4. **Controls.** Positive control: the 64-bit run must list `VK_KHR_ray_query` and `VK_KHR_acceleration_structure` (the 4090 supports both); if it does
   not, the measurement is broken (kill criteria). Validity of the 32-bit run: it must list the RTX 4090 as a discrete GPU with the same driver version
   as `nvidia-smi`, through NVIDIA's ICD per the loader log. If the 32-bit list lacks any of the three extensions, run it once more with implicit layers
   off (`VK_LOADER_LAYERS_DISABLE=~implicit~`, into `*_32_nolayers.txt`) to show no overlay layer is hiding them.
5. **Fallback only: a 32-bit probe program.** Only if the 32-bit `vulkaninfo` cannot reach the NVIDIA device (error, no device, or another ICD): a
   C file that loads `vulkan-1.dll`, creates an instance, enumerates physical devices and prints each one's name, driver version and
   `vkEnumerateDeviceExtensionProperties` list. Build it 32-bit with the D31 toolchain (`ubuntu:24.04` in Docker Desktop, `i686-w64-mingw32-gcc`; the
   Vulkan headers from the image's `libvulkan-dev`, or the few declarations written out), run it from the run folder, commit the source and the
   output, not the exe (its sha256 in the README). Skip this step when step 4 passes: `vulkaninfo` uses the same loader and ICD a 32-bit DXVK would, so
   a second program adds nothing then.
6. **The fact.** `python3 core/wsc.py reg add engine_facts id=napoleon.vulkan.rt_32bit claim=... state=... evidence=harness/runs/<id>/README.md
   date=<YYYY-MM-DD>`. The claim is the positive question, with the pins in it: "The 32-bit NVIDIA Vulkan ICD on the project PC (RTX 4090, driver <v>,
   Windows <build>) exposes VK_KHR_ray_query, VK_KHR_acceleration_structure and VK_KHR_deferred_host_operations to a 32-bit process (the 64-bit ICD of
   the same driver: <which of the three>)". State: `verified` if all three are in the 32-bit list, `refuted` if any is missing (say which are present in
   `notes`), `open` only if no run reached the NVIDIA 32-bit ICD (kill criteria). `notes`: the two report links from the record, the layer-off rerun,
   and "decides drafted D50 (Liam)".
7. **Living copies.** In `docs/plans/PLAN.md`, add the result (fact id, state, driver, date, run) to section 7's "Ray-traced shadows and AO" row (its gate
   column says "blocked before it starts unless J71 shows ...") and to section 6 question 6 where it says "D50 (ray tracing stays out pending J71)".
   One clause each; do not write or sign D50, do not change any other decision text. The moonshots record is a dated record: leave it unchanged.

## Deliverables
1. `harness/runs/<YYYYMMDD>_j71pc/` with a README (date, pins table, the two runs' commands, the loader lines naming each ICD, the RT extension table
   32 against 64, the controls, any deviation) and the files of steps 1 to 4 (and 5 if it ran). A full `vulkaninfo` output over 1 MB is committed
   gzipped (`.txt.gz`) with its sha256 in the README.
2. Engine fact `napoleon.vulkan.rt_32bit` (step 6); `python3 core/wsc.py reg check engine_facts` ok.
3. The two PLAN clauses (step 7).
4. `python3 core/wsc.py gates` green.

## Out of scope
- Any DXVK patch or rebuild, any change under `proxy/`, `harness/` (other than the run folder) or `core/`, any game or watcher launch.
- Installing or updating anything: the Vulkan SDK, a driver, a `vulkaninfo` from the web. If the measurement seems to need one, that is a kill criterion.
- Writing D50 or any decision line; RT design work (the record's J-RT-1 and later rows wait for Liam).

## Kill criteria
- The 64-bit run does not list `VK_KHR_ray_query` and `VK_KHR_acceleration_structure` on the RTX 4090: the measurement setup is wrong; stop, commit
  the run folder, report, file no fact.
- The 32-bit run reaches no NVIDIA device (after the loader log and, if run, the step 5 probe within its 15 calls): file the fact as `open` with the
  evidence, stop.
- The probe would need an install, a download or a driver change: stop and ask Liam in the report; change nothing on the PC.
- Any tool call is refused by a deny rule or the hook: stop and report the call; do not retry another way.
- Over about 25 tool calls (40 with step 5): stop, commit, report what is left.

## Finish
Write `jobs/J71/report.md` (headings `## What was built`, `## Evidence`, `## Deviations from the brief and why`, `## Open questions`): the pins, the RT
extension table 32 against 64 with the run id, the controls, the fact as filed, the two PLAN clauses, and the gates output. Then
`wsc reg set jobs J71 status=review report=jobs/J71/report.md`.

## Open questions (recommendation taken; Liam may overrule before or during the build)
- **Claim phrasing.** Recommended: the positive claim ("exposes ...") so the state answers the record's question directly: `refuted` = no in-process ray
  tracing on Windows, the expected result. The alternative (a negative claim marked `verified`) reads the same but inverts the state; pick one and keep it.
- **Re-probe on driver updates.** Recommended: none scheduled. The fact names its driver; a re-probe (one job of this size) is worth it only if an
  NVIDIA release note mentions 32-bit Vulkan ray tracing, or before anyone reopens D50.
- **The 32-bit probe program.** Recommended: fallback only (step 5). `vulkaninfo` from `SysWOW64` is the same loader and the same ICD a 32-bit DXVK
  loads, so a custom program is evidence only when `vulkaninfo` cannot reach the device.
- **PLAN clauses.** Recommended: the builder adds the dated result to the two PLAN places (step 7) so no living copy still says "pending J71"; the
  decision itself (sign D50 as drafted, edit it or decline it) stays with Liam.
