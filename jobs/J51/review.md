# J51 review

Reviewed 2026-10-31 on `job/J51` (head a6a1c19) by an independent session (`840895c9`) that did not build it (builder `81e5ee96`).

**Verdict: merge.**

## What I ran
- `python3 core/wsc.py gates` on a6a1c19: 11 ok, 1 warn (the clone's absolute `core.hooksPath`), 0 failed; 332 host tests passed.
- `python3 tools/pr_policy.py --branch job/J51 --base origin/main`: refused only for the missing review and the `review` status, which this review resolves.
- `git merge-tree` against origin/main (6e94e28, one commit ahead: the J45 brief): merges clean.

## Claims against evidence (checked on the PC, `C:\napoleon_remastered_pc\upscale`)
- **Spot check:** `j51_sampleA` and `j51_sampleB` manifests both hold 144 entries with the same ids; all 144 `out.sha256` equal. Holds.
- **Full run:** `run_j51.log` ends `done 5953, skipped 2, failed 1, 376.0s`, as reported. The work manifest has an output for all 5954 assets of the
  nine roles; the two without are the `no_header` flag TGAs. The resume pass is not in that log, but the manifest entry for
  `ui/flags/spain/large.dds` is `done`, DXT2, 1280x640, 11 mips.
- **DXT2 output:** decoded the stored blocks of that file myself: 0 of 819,200 texels have colour above alpha, so it really is premultiplied. Holds.
- **Packs:** all nine present beside J36's four; byte sizes match the table; sha256 of `technology_icon`, `map_pip` and `flag` re-hashed: the first 16
  characters match the report.
- **Registry:** against origin/main, `assets.jsonl` changes 5954 rows, only `upscale_status` and `upscale_method`, only in the nine roles. Every `done` row's
  method equals its manifest entry's method. No `todo` left; the two `not_needed` rows were already so on main with `skipped:no_header`. The six
  `lanczos->2.5x (no model: side under 8px)` rows are J36's existing tiny-side rule, not a method change.
- **Sheets:** nine JPGs, 2.5 MB in all; looked at `flag.jpg`: before/after pairs, alpha cut-outs (`hud_left`, `id_flag_cavalry`) intact.

## The brief
Every deliverable is present except that `upscale/README.md` was not touched; it holds no count or command this job changed, so none was needed.
Nothing was installed and the game folder was not written, as the brief narrowed. The deviations (role order, the DXT2 fix mid-run, the disk bound from the
spot check, built in an interactive session) are each named with a reason. The commits are co-authored by Opus where the brief says Sonnet; the report
names the interactive session but not the model. No kill criterion was hit.

## Risk-first reading
I read `upscale/core/dds.py`'s DXT2 change and its test in full: it is the only code change and it writes every DXT2 output. The header stays vanilla
(FourCC `DXT2` kept), decode unpremultiplies DXT3 blocks, encode premultiplies each mip level after the straight-alpha mip chain is built, and
texconv/quicktex are kept away from DXT2. The registry writer (`apply_registry`) was not changed; its effect is checked above.

## Findings

### Blocker
None.

### Should-fix (fixed on the branch)
1. `upscale/napoleon/cli.py:31` `items_for` returned rows in registry order, so `--roles` order (the brief's "small roles first") was silently ignored;
   the report noted it as a deviation. Fixed in c43aab7: rows come in `--roles` order, registry order within a role; host test
   `RoleOrder.test_items_follow_the_roles_order_not_the_registry_order` (fails on a6a1c19, passes now). `--sample` is unaffected (it sorts by role name).

### Later
2. `upscale/napoleon/cli.py` `plan`: the brief asks for a free-disk check "against the plan's output size", but `plan` reports none, so the bound came
   from hand arithmetic on the spot check. Have `plan` estimate output bytes (target size x format bytes per texel x mip factor) and `run` refuse when the
   work drive would keep less than 20 % free: the kill criterion becomes a guard.
3. `upscale/core/batch.py` `verify` (around line 208) checks format, size and flatness but not the premultiplied invariant; a DXT2 output with colour above
   alpha would pass. Cheap to add (decode the level as DXT3, require max(RGB) <= A + a small tolerance). One asset today, so later.
4. `upscale/napoleon/config.json` `native_cap` is tested on the source size, so 23 loading-screen outputs are 4800 px wide (report Open question 1). If J50
   finds the engine refuses them, cap the target instead: a size-rule change for Liam (D35), not for this job.
5. `run_j51.log` holds only the first pass; the resume pass's numbers (1 fresh, 23.6 s) have no log behind them (the manifest confirms the result).
   Having `run` append its summary line to a log in the work folder would make every run leave one.

## Rules for other open branches
The role-order fix changes no rule other job branches must meet.
