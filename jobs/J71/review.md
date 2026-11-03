## Round 1 (2026-11-03, branch job/J71 at fc57e13)

**Verdict: merge.**

Checked against the brief, not the report:
- CI on fc57e13: all checks passed or skipped. The branch changes no code (run folder, fact row, two PLAN clauses, report, job row).
- Evidence re-read: `extensions_32.txt` has 270 names and none of the six RT names; `extensions_64.txt` has 289 and carries `VK_KHR_ray_query` and `VK_KHR_acceleration_structure` (positive control passes); `extensions_32_nolayers.txt` is byte-identical to the 32-bit list (`cmp`); `loader_32.txt` names `nv-vk32.json` / `nvoglv32.dll`; `nvidia-smi` still says 617.14. Pins, controls and the step-5 skip are consistent with the brief.
- Fact `napoleon.vulkan.rt_32bit`: positive claim, state `refuted`, evidence and date set, notes carry both reports, the layer-off rerun and "decides drafted D50 (Liam)". Matches step 6.
- PLAN: exactly the two clauses of step 7; no D50 text, no decision changed; the moonshots record is untouched.
- Deviations (Opus, extra `loader_summary_*` files, uncommitted scratch scripts, orchestrator-written report) are named in the report and harmless.
- Local `wsc gates` on this PC: 13 ok, 1 failed: `test_job_sh.JobSh.test_ctl_without_an_ini_uses_the_registered_default`. The branch touches no `job.sh`, ini or test input, and CI's `gates` is green on the same head, so this is local PC state, not caused by J71. Not a blocker.

### Blockers
None.

### Should-fix
None.

### Later
- PLAN section 6 still says "The two measurements that change no scope are queued: J71 and J72"; refresh it when J72 lands (the report flags this).
- `test_ctl_without_an_ini_uses_the_registered_default` fails on the project PC; a host test that depends on PC state should isolate it (core backlog candidate, not filed here).
