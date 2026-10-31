# J50 review

## Round 1 (2026-10-31, branch job/J50 at d16af14)

Reviewer session `065a3b8a-6922-48ea-a658-81c011f30578` (Opus 5.5, independent check; did not build or fix this branch).

**Verdict: merge.**

### Machines
- `python3 core/wsc.py gates`: 11 ok, 1 warn (`hooks`: the worktree's absolute `core.hooksPath`, environment), 0 failed; 387 host tests.
- `tools/pr_policy.py --branch job/J50 --base origin/main` before the review: refused only for the missing review and the row not `done` (expected).
- No pull request existed yet, so no red checks.

### Claims against evidence (checked on the PC, read-only)
- Game folder now: 11 vanilla packs, no proxy, `Napoleon.exe` sha1 `9aebcd21...` vanilla; `pc_deploy.py status`: nothing installed, no `.git`.
- `pc_deploy.py diff _scratch\j50\snap_start.json snap_end.json`: `identical` (re-run by me).
- Stage-1 install job `J50-20261031T164812Z-1327310857.out`: four packs, source = manifest = copy sha256, as the report says.
  The run copy of `install_packs.ps1` under `_scratch\j50` is the committed script up to line endings.
- Crash dump `20261031T164846Z-p33332_c0000374.dmp` exists under `_to_delete\uninstall_20261031T170615Z\` (the report's "moved by the uninstall").
- Shots back every probe result: `s2m_campaign.jpg` end-turn green, `s2m2_frontend.jpg` logo and Steam button magenta, `s2r3_land.jpg` battle HUD cyan,
  `s2d_frontend.jpg` logo blank. Shots 1.6 MB in all.
- `PackFS.from_games` reads `mod_packs` (`discovery/core/packfs.py:74`), so the skip list works; `tests/test_mod_packs.py` covers it.

### Brief
All seven deliverables are there. The deviations (J22's leftover kit, Opus, lower-case scratch owner, combined probe s2r3, guessed marker targets,
720p sharpness, `ctl.py shot` fix taken out) are named with reasons. Kill criteria respected; the J36 crash decision is argued from the dump timing
(before any data pack read) and the repeat run, and the open fact `napoleon.proxy.init_heap_corruption` records it. Nothing out of scope.

### Risk-first reading
I picked `upscale/pc/install_packs.ps1` because it is the only new code that writes into the game folder. I read it in full. The rest I skimmed:
the test, `games.json`, the facts, the README and the probe scripts (evidence only, never committed as tools).

### Findings

**should-fix (fixed on the branch by this review)**
1. `upscale/pc/install_packs.ps1:40-58` (as built): the manifest check ran inside the copy loop, so a bad manifest on pack N left packs 1..N-1 in
   `data\`; a bad copy with no `-Trash` stayed in `data\`. To see it fail: `tests/test_install_packs.py` against the branch's script fails
   `test_bad_manifest_on_a_later_pack_copies_nothing` (a pack left in data) and `test_install_needs_trash`.
   Fix `e67d444`: every source is checked before the first copy, install needs `-Trash`, and a bad copy moves this call's copies there. The new test runs the
   script under `powershell.exe` the way a watcher job calls it (skipped without one).
2. `registries/engine_facts.jsonl` `napoleon.ui_art.dds_at_tga_paths`: the refutation rests on one probe, a DXT5 written unpadded at `logo.tga`
   (500x153; 153 is not a multiple of 4, and D3D9 wants DXT top levels in multiples of 4). "Blank" may mean the texture was refused, not that the
   engine refuses a DDS at a TGA path. The only 4-aligned probe (`button_steam_store`, 148x24) was not the file on screen. To see it: `build_probes.py`
   writes `dds.write_dds(tmp, 'DXT5', w, h, ...)` at the vanilla size, and the run report's s2d row has the sizes. Vanilla has one unaligned DXT1
   (`ui\loading_screen_pictures\2.dds`, 1921x1200), which weakens the confound but does not settle it. The brief defines "blank = no", so `refuted`
   stands. Fix `1aea4a2`: the fact's notes and `upscale/README.md` now name the confound.

**later**
3. Re-probe `dds_at_tga_paths` with a DXT5 at a 4-aligned TGA path that is on screen (one launch). If it is drawn, J36's TGA outputs can carry mips.
   Write a `needs_brief` row for it if the UI host jobs want DDS.
4. The upscaler's DXT outputs: 6 UI DXT files with a role get a 2.5x target that is not a multiple of 4 (for example
   `ui\frontend ui\loadingscreen\loading_screen_heading.dds` 460x152 -> 1150x380). If the D3D9 constraint in item 2 holds, those textures may fail to draw.
   This concerns J36/J51's rules (`upscale/core/rules.py`), not J50. It needs a check, and possibly a "round DXT targets up to 4" rule.
5. Report Open question 4 (a job left J22's kit installed) is prose today. It could be a guard: `pc_deploy.py status` or the job-finish check could
   name a kit still installed by a finished job. This is for the harness owner.
6. Report Open questions 1 (init heap corruption crash job) and 5 (`ctl.py shot` at the main menu) need rows on a `plan/` branch. Liam decides.

The merge changes no rule that other open job branches must meet.
