# Run 20261103_j71pc: 32-bit vs 64-bit Vulkan ray-tracing extensions on the project PC (J71)

Date: 2026-11-03. Job: J71 (`jobs/J71/brief.md`). Fact filed: `napoleon.vulkan.rt_32bit`, state **refuted**.
No game launch, no game lock, no watcher; nothing installed, downloaded or changed on the PC. Every command ran with this folder as the
working directory, from 64-bit Git Bash.

**Answer:** the 32-bit NVIDIA Vulkan ICD (`nvoglv32.dll`, driver 617.14) exposes **none** of `VK_KHR_ray_query`,
`VK_KHR_acceleration_structure`, `VK_KHR_deferred_host_operations` (nor `VK_KHR_ray_tracing_pipeline`, `VK_KHR_ray_tracing_maintenance1`,
`VK_NV_ray_tracing`) on the RTX 4090; the 64-bit ICD of the same driver exposes all six.

## Pins
| item | value | file |
|---|---|---|
| GPU, driver (`nvidia-smi --query-gpu=name,driver_version --format=csv,noheader`) | NVIDIA GeForce RTX 4090, 617.14 | `pins_nvidia_smi.txt` |
| Windows (`cmd //c ver`) | 10.0.26200.9711 | `pins_winver.txt` |
| Vulkan instance version (both loaders) | 1.4.341 | `summary_*.txt` |

| file | bytes | sha256 | PE machine |
|---|---|---|---|
| `C:\Windows\SysWOW64\vulkaninfo.exe` | 2,626,608 | `dd963d5a5da3da40e7f2327e6ccb8e02eb6a12ed13c977b1d8fb991068ddb730` | 0x14c (32-bit) |
| `C:\Windows\SysWOW64\vulkan-1.dll` | 1,542,192 | `2fb9c7742624733bc743a36a6424197f35ddbe6cb54b2fa3b1c794da8ee3e04d` | 0x14c (32-bit) |
| `C:\Windows\System32\vulkaninfo.exe` | 3,082,800 | `c1ed6b230e4c3096684c20a4ed02da588b3609fdaf3ba1a275bf3e6b8d74238a` | 0x8664 (64-bit) |
| `C:\Windows\System32\vulkan-1.dll` | 1,730,096 | `12195bbe9f2d8c27606772f72dae564bb7a7ddb9669d169e1676c3edc1c61f3e` | 0x8664 (64-bit) |

(`pins_files.tsv`; the PE field read with a few lines of Python: `e_lfanew` at 0x3c, `Machine` = the u16 after the `PE\0\0` signature.)
`help_32.txt` is `vulkaninfo.exe --help` of the 32-bit build; its flags (`--summary`, `--text`) were used for both builds.

## Commands
For `bits=32` (`/c/Windows/SysWOW64/vulkaninfo.exe`) and `bits=64` (`/c/Windows/System32/vulkaninfo.exe`):
```
VK_LOADER_DEBUG=driver <exe> --summary > summary_<bits>.txt 2> loader_summary_<bits>.txt
VK_LOADER_DEBUG=driver <exe> --text    > vulkaninfo_<bits>.txt 2> loader_<bits>.txt
```
Layer-off control (32-bit only, because the 32-bit list lacked the extensions):
```
VK_LOADER_DEBUG=driver,layer VK_LOADER_LAYERS_DISABLE='~implicit~' /c/Windows/SysWOW64/vulkaninfo.exe --text \
    > vulkaninfo_32_nolayers.txt 2> loader_32_nolayers.txt
```
All five runs exited 0. The full outputs are under 1 MB (largest 183 KB), so none is gzipped. Text files are committed with LF line
endings (git normalises the CRLF output), so their on-disk sha256 is not pinned here; the extension lists are.

## Which ICD each run loaded (loader log, quoted)
- 32-bit (`loader_32.txt`): `Found ICD manifest file C:\WINDOWS\System32\DriverStore\FileRepository\nv_dispi.inf_amd64_da865124972e1f80\nv-vk32.json, version 1.0.1`
  and `Using "NVIDIA GeForce RTX 4090" with driver: "C:\WINDOWS\System32\DriverStore\FileRepository\nv_dispi.inf_amd64_da865124972e1f80\nvoglv32.dll"`
- 64-bit (`loader_64.txt`): `Found ICD manifest file C:\WINDOWS\System32\DriverStore\FileRepository\nv_dispi.inf_amd64_da865124972e1f80\nv-vk64.json, version 1.0.1`
  and `Using "NVIDIA GeForce RTX 4090" with driver: "C:\WINDOWS\System32\DriverStore\FileRepository\nv_dispi.inf_amd64_da865124972e1f80\nvoglv64.dll"`

A second device is listed in every run: GPU1, `AMD Radeon(TM) Graphics` (integrated, vendorID 0x1002, `amdvlk32.dll` / `amdvlk64.dll`
via `amd-vulkan32.json` / `amd-vulkan64.json`). It is ignored for the fact (D13: NVIDIA only). For the record, it shows the same split:
its 64-bit list has the three KHR extensions, its 32-bit list has none.

## Devices (NVIDIA, GPU0 in both runs)
| | 32-bit | 64-bit |
|---|---|---|
| deviceName / type | NVIDIA GeForce RTX 4090, DISCRETE_GPU | NVIDIA GeForce RTX 4090, DISCRETE_GPU |
| driverVersion / driverInfo | 617.14.0.0 / 617.14 | 617.14.0.0 / 617.14 |
| device apiVersion | 1.4.351 | 1.4.351 |
| device extensions | 270 (`extensions_32.txt`) | 289 (`extensions_64.txt`) |
| implicit layers listed | 5: `VK_LAYER_AMD_switchable_graphics`, `VK_LAYER_NV_optimus`, `VK_LAYER_NV_present`, `VK_LAYER_VALVE_steam_fossilize`, `VK_LAYER_VALVE_steam_overlay` | the same 5 |

`only_64.txt`: 19 extensions, every one ray-tracing or NVX/CUDA/optical-flow related (`VK_KHR_acceleration_structure`,
`VK_KHR_deferred_host_operations`, `VK_KHR_ray_query`, `VK_KHR_ray_tracing_pipeline`, `VK_KHR_ray_tracing_maintenance1`,
`VK_KHR_ray_tracing_position_fetch`, `VK_KHR_opacity_micromap`, `VK_EXT_opacity_micromap`, `VK_EXT_pipeline_library_group_handles`,
`VK_EXT_ray_tracing_invocation_reorder`, `VK_NV_ray_tracing`, `VK_NV_ray_tracing_invocation_reorder`, `VK_NV_ray_tracing_motion_blur`,
`VK_NV_cluster_acceleration_structure`, `VK_NV_partitioned_acceleration_structure`, `VK_NV_cuda_kernel_launch`, `VK_NV_optical_flow`,
`VK_NVX_binary_import`, `VK_NVX_image_view_handle`). `only_32.txt` is empty: the 32-bit list is a strict subset.

## RT extensions, 32 against 64 (NVIDIA RTX 4090, driver 617.14)
| extension | 32-bit | 64-bit | 32-bit, implicit layers off |
|---|---|---|---|
| `VK_KHR_ray_query` | absent | present | absent |
| `VK_KHR_acceleration_structure` | absent | present | absent |
| `VK_KHR_deferred_host_operations` | absent | present | absent |
| `VK_KHR_ray_tracing_pipeline` | absent | present | absent |
| `VK_KHR_ray_tracing_maintenance1` | absent | present | absent |
| `VK_NV_ray_tracing` | absent | present | absent |

The lists were cut from the `Device Extensions: count = N` block of the GPU whose `vendorID = 0x10de`, and the script asserted the name
count equals N for every run (270, 289, 270).

## Controls
- **Positive (64-bit):** the 64-bit run lists `VK_KHR_ray_query` and `VK_KHR_acceleration_structure` on the RTX 4090: the setup measures
  what it should. Pass.
- **Validity (32-bit):** the 32-bit run lists the RTX 4090 as `PHYSICAL_DEVICE_TYPE_DISCRETE_GPU`, driver 617.14 (same as `nvidia-smi`),
  through NVIDIA's `nv-vk32.json` / `nvoglv32.dll` per the loader log. Pass, so the step 5 fallback probe program was not needed or built.
- **Layers off:** with `VK_LOADER_LAYERS_DISABLE=~implicit~` the loader log shows all five implicit layers "forced disabled", the device is
  still `nvoglv32.dll`, and `extensions_32_nolayers.txt` is byte-identical to `extensions_32.txt` (270 names). No overlay layer hides them.

## Deviations
- `loader_summary_<bits>.txt` (the `--summary` runs' stderr) is kept beside `loader_<bits>.txt`; the brief named only the latter.
