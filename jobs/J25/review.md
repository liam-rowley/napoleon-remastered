# J25 review

## Round 1 (2026-11-06, branch job/J25 at 14ea1d2)

**Verdict: merge.**

The spike answers the brief, and nothing in it ships. The report's headline, **go with conditions**, is honest: criterion 2 is met only in part, and the brief's "go only if every one holds" means **J26 does not start on this review**. Liam decides, on the report's three conditions plus the two corrections below. `merge` here means the evidence and the answer may enter `main`, not that cascades are approved.

### Machines
- `wsc gates` at 14ea1d2: 13 ok, 2 warn, 0 failed. CI on 14ea1d2: all 9 checks passed or skipped.
- `wsc policy` before this review: only the two expected refusals (no review, row not `done`). No rule 79: no `proxy/`, `harness/` outside `runs/`, or pin change.
- `tests/test_run_helpers.py`: 14 tests ok, including the one added here.
- **Not run:** the spike's host tests (`test_cascade.cpp`, 235 checks). A scratch copy of the sources to apply the patches to was denied by a permission rule, so I did not build them and that count is the builder's. I read the patches instead.

### Claims checked against evidence
| claim | how checked | result |
|---|---|---|
| Cost table | recomputed from the committed `cells/*.json`, not through `cost.py` | every median and spread matches, all 6 cells; all 8 arms on one kit and build, at the right size |
| Extrapolation, VRAM arithmetic, by-scale figures | by hand | match |
| Density 21.08, 13.18, 8.78, best/worst 1.0 | re-ran `shadow_density.py --cascade` on the raw captures | match; the fit's own radius and texel in the logs agree with them (the metric is about 0.74 of 1/texel at this sun) |
| Cascade 1 within 0.13 % | engine clip matrix at the first caster, control against prototype, 24 captures | at most 0.022 % of the largest term, so inside the claim |
| Coverage, all 10 prototype launches | last counter line of each `proxy.log` | seen equals duplicated, 0 unknown, 0 no fit; `d_tint` 19,715,616 swapped and 691,590 stock (3.4 %); 0 refused from `d_*` on |
| Pick position | re-ran `pick_check.py` on `e_tint2k`, with my own rows | same size of error: deploy within 13 px on rows 480 to 560, turned within 6 px on all but one edge (29 px); my row 600 falls under the UI and is not a result |
| Question 3 | bytes of the vanilla exe and the logged stack | `0x1188e64` is a direct call to `0x1193db0`; `0x1bc8e69` and `0x1bd4763` in the stack are `0x1188e69` and `0x1194763` at delta 0xa40000; no device draw call pattern in `0x114b440`. My scan looks for direct `call [reg+disp32]` only, so it supports the fact and does not prove it alone |
| Clean end state | `pc_deploy.py status` | not installed, exe sha1 vanilla, no `.git` |

### Risk-first reading
Picked the device-path code (`patches/0001`, `0005`) and the receiver fragment, because the go decision and J26's design rest on them. Nothing here runs on anyone's game, so install risk does not apply. `dev.cascade_count=0` in the cost arms looked alarming but only switches the receiver draw counters off. State restore, texel snap, the depth row, the zero-matrix fallback and the stock CTAB splice read correct. The sphere fit's `t > splitD` branch always applies at this view, so the footprint is 114 m across at split 40, not a 40 m slice: the pick is a square in light space, not a distance. That is the same point the report makes about the units being outside it.

### Findings

**Blockers:** none.

**Should-fix, done on the branch**
1. `tools/shadow_density.py`: the cascade table went to stdout only, so the report's density rows, the heart of criterion 3, were in no committed file (`density.tsv` has control rows only, and raw `frame.txt` stays off the repo). The tool now writes `density_cascade.txt`, with a test. The run folder has the table and `density_cascade_frames.sha256`, the sha256 of the 24 frames (the brief's J8 rule). Commit "the cascade density table is kept in the run".
2. `registries/engine_facts/napoleon.shadow.blob.json`: "the near cascade removes" the sun-behind collapse was stated as settled, but the evidence is a density of 1.0 that is true by construction, at a point in the air. No shot shows it: the crops at p1 to p4 cannot be told apart by eye. The fact now says that. **The report's Blob section and its Liam question still use the stronger wording: read "removes it" as "no yaw dependence by the metric".**

**Should-fix, corrections to the report (recorded here: a reviewer who edits `report.md` fails the own-review check)**

3. **Criterion 5 has less evidence than the report says.** `jobs/J25/report.md`, Go or no-go row 5: "`c_on`'s log is lost, so that one launch has no device-error evidence". In fact `dxvk_errors.txt` exists only from `d_tint` on. `c_tint` has none committed, and **the 4 prototype cost arms have no DXVK record at all**, because `perf_baseline.py measure` does not go through `cas.sh`. No crash or hang is shown in any of them; "no device error" is unproven for those runs. J26 should treat it as open.
4. **`culled-but-needed` was not delivered and is not under Deviations.** Deliverable 3 and the "Route 1" section ask for it. The Coverage section says it was not measured, but criterion 1 reads **Met** without that caveat. The argument holds for visible pixels (same frame, same caster list, ortho along the same light), so I accept it as reasoning, not as a count. At split 60 the footprint can pass the engine's farz, where that argument is weakest.
5. **Small report errors.** Shots: "0.67 to 1.05" should be 0.65 to 1.05 at 2048, and 0.48 at 8192 (`shotdiff.md`, p6). Cost: "VA peak is +11 to +22 MB" is `land_40` only; `hist_dresden` is about +2. The Risks list omits culling and the hardware path, which the brief named; the hardware path appears only under the receiver route. The density table has no stock row and no 60 m or 140 m columns for cascade 0, which deliverable 4 implies; neither changes a criterion.
6. **`pick_check.py`'s output and its row arguments are not committed,** so "7 of 8" and "5 of 6" cannot be reproduced exactly. My re-run above gives the same order of error; the claim stands as approximate, which is how the report states it. `cost.py` also reads `summary.json`, which is not committed; the cells are, and that is what I used.

**Later**
- `tools/perf_baseline.py measure` should record the DXVK `err:` count per run, so a cost arm has device evidence (finding 3). Worth doing before J26's sittings.
- "3.4 % stock, all of those `cloth`" follows from the receiver table; the log counts stock draws without naming shaders, so I did not confirm it directly.
- The p2 tint line stays unexplained, as the report says. It is in one crop only.
- `receivers/swap/*.ps` puts compiled game shaders in a public repo as binaries. Their disassembly (`discovery/napoleon/shaders/asm`) is already public, so it is not new in kind; it belongs with Liam's open licence question (D38).
- The three core items in the report's Open questions are still for the orchestrator to file.

### For Liam
- This merge changes no rule that other open branches must meet.
- The most useful line in the report is in Design for J26: at release, J24's 8192 map already beats any 2048 cascade at its worst yaw (31.46 against at most 21.08). The real choice is whether cascades are wanted at all.
