# J96 review

## Round 1 (2026-11-06, branch job/J96 at 2c5a256c)

**Verdict: merge.**

Review session `1cf83bbb-a48a-4d90-b1f4-9f78d18d12a3`. The code and four of the five probe verdicts hold. Two evidence faults are fixed on the branch. The report still carries two wrong statements, corrected below because a reviewer may not edit it.

### Checked
- **Machines.** `wsc gates` on 5af53a58 and again with the reviewer fixes in the tree: 13 ok, 2 warn, 0 failed (674 host tests). Both warnings are not this job's: the `ci_render` W23 note and the skipped tests. CI on 5af53a5: all 9 checks passed or skipped. The host Python has no numpy, so the gates skip the upscale image tests; `tests/test_upscale.py` in the art_build Python: 35 pass. No `proxy/` or `harness/` change and no pin move, so rule 79 does not apply. `origin/main` is the branch's merge base, 36923c6e.
- **Risk-first reading:** `upscale/core/batch.py`, `rules.py` and `cli.py`, because they decide what is overwritten and what verifies. `run`, `plan` and `verify_entry` share one size rule, and `decide` has no other caller. Resume redoes an old plain-size output. `wsc upscale` passes `--force-disk` through and returns exit 2. The work folder exists before the guard reads the disk.
- **Report numbers, re-run read-only on the real work folder:** 6 changed files, the same list. Estimate 3,398,915,024 against 3,398,903,131 real. `loading_screen` +0.15 %, `portrait` -0.51 %, the rest 0.0 %. `verify` fails exactly those 6 DDS files. `ui\flags\spain\large.dds`: 11 levels, no texel above alpha even at tolerance 0.
- **Probes, by the shots:** Steam button blank under DXT5 with the text kept (probe 1); solid DXT1 and DXT5 at 4802x3002 (probe 2); magenta band at 4800 px (probe 3); tabs vanilla in `t1`, doubled in `t2` (probe 4); the font crops match the table (probe 5).
- **Route 1 control.** The `t1` pack has no in-pack control, so a refusal could have meant a pack that never loaded. `proxy.log` settles it: 12 packs and 86996 entries in `t1`, 11 and 86995 in `t2`, and the redirect hit is at `raw/t2/proxy.log:215`.
- **End state.** `snap_end` equals `snap_after_j32`. Against `snap_start` the only difference is `napoleon_remastered.ini`, which is still in the game folder.

### Blockers
None.

### Should-fix
1. **Fixed (4bf0df7d): evidence was on no branch.** `.gitignore:9` `*.log` dropped all eight `raw/*/proxy.log` files and `raw/evidence/foreign_windows.log`, which the run README cites. They existed only in the builder's worktree. `uiscale/runs/**/*.log` is now excepted and the logs are committed.
2. **Fixed (2c5a256c), but still wrong in the report: "not on that screen".** `jobs/J96/report.md:32`, the run README and `napoleon.ui_art.dxt_target_multiple_of_4` said the five affected `ui\frontend ui\loadingscreen` files are not on the loading screen. They are: the plaque, the blue and red boxes and the bar in `raw/evidence/load_land_markers_absent.jpg` are those vanilla files, decoded and compared by eye, and their only copy in any pack is `boot.pack`. `raw/load/proxy.log` indexes all seven probe entries (87002 against 86995), yet vanilla was drawn. So a movie-pack entry did not replace them; why is not proven. "Unproven" still stands for these files, and the README and the fact now give the right reason. See Later 1.
3. **Not fixable here: the report understates the budget.** `jobs/J96/report.md` Deviations says about 95 tool calls and about 40 on the PC. The builder's transcript has 154 unique tool calls, 76 of which name the PC tooling (a loose count, like the report's). The brief's kill criterion is about 90 and about 30, so the job ran well past both. The overrun is named but its size is not. This did not harm the work, so it does not hold the merge; the real numbers are for sizing later briefs.

### Later
1. **Can a movie pack replace a `boot.pack` file at all?** 17 `loading_screen` rows sit in `boot.pack`, and the seven DXT files probed did not take. If this holds, those outputs never reach the screen, and the rerun of `run --roles loading_screen` gains nothing for the five files. It may also limit `napoleon.assets.pack_order`, which says order is type then name. It needs a one-launch probe with a TGA at one of these paths, then a queue row. Liam's call.
2. **`upscale/napoleon/cli.py:123`:** the disk guard counts every item, so `--limit` can be refused for a run that would fit. It errs safe, and `--force-disk` gets past it.
3. **`tools/verbs/upscale.py` header:** the usage line does not name `--force-disk`. It works, because the verb passes the rest through.
4. **`uiscale/runs/2026-11-06_j96/sit.sh`:** it does not stop when the lock is missing, which is how the first sitting ran with no lock or kit. A check at the top would refuse that. A shared sitting helper is the place for it, if one is written.
5. **`napoleon_remastered.ini` in the game folder** (report Open question 1): still there, and `play.py install` refuses on it. Liam's or J32's to clear.
