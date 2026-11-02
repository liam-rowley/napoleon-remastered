## Round 1 (2026-11-02, branch job/J66 at 42e4172)

**Verdict: merge.**

Reviewer session `b1ca2e6e-2bf9-4ee9-80af-4570e3771985` (Opus, independent check per D15), which did not build or fix this branch.

### Machines
- `python3 core/wsc.py gates`: 11 ok, 1 warn (skips only), 0 failed. CI on `job/J66` at 42e4172: all 8 checks passed or were skipped.
- `python3 tools/pr_policy.py --branch job/J66 --base origin/main` before the review: it refused only for the missing review and the row
  not yet `done`, which is expected.
- `tests/test_uiscale_fonts.py` in the art_build Python: 5/5 pass once the face resolves (see finding 1). As committed they were skipped everywhere.

### Claims checked against evidence
- **Fonts byte-identical to Empire's 2x fonts:** confirmed and stronger than claimed. I read `ui_scale_2x_fonts.pack` (sha `5f510b27afa3`)
  and the `ui_scale_2x_fonts.pack` installed in the Empire game folder. All five Napoleon slot files (`frontend_24`, `frontend_38`,
  `ingame_18`, `ingame_24` and `ingame_b_24`) have the same sha256 as their Empire counterparts. So the HarfBuzz rebuild that was not launched
  matches fonts already proven in game.
- **Install and uninstall:** I read the whole `upscale/pc/play.py` diff, picked because it writes the game folder and AppData.
  - Every refusal comes before the first change, and the templates sha is checked against its `.json`.
  - The rules file must name the templates path.
  - `dev.file_rules` goes through `pc_deploy.set_keys`, so `pc_deploy uninstall` restores it.
  - The UI cache moves only under `%APPDATA%\The Creative Assembly\Napoleon\ui_cache`, which exists on this PC, into the play trash.
  - `status` flags a changed templates file.
  - The run report shows the start and end snapshots identical (1564 entries) and the lock released.
- **Shots:** `r2_land.jpg` and `r2_campaign.jpg` show the battle HUD, unit cards, advisor and campaign bottom bar at 2x, docked as at
  1080p. They also show the radar group misplaced, as reported.
- **Scaler** (`uiscale/core/scale.py`): absolute edge snapping with `px = floor(x + 0.5)` applies to x/y, spans, uses and keyframes. Image defs
  with a path become `ceil(t*f)`, and the image-use tail is never written. This matches the brief.

### Findings
**Blocker:** none.

**Should-fix**
1. *Fixed in 08a7a7c.* `tests/test_uiscale_fonts.py:22` hard-coded `FACE` to the vendored `uiscale/fonts/Lora-Variable.ttf`, which is not
   in the repo until J68. The build itself falls back to the empire-remastered clone (`uiscale/napoleon/config.json` `font_faces`). So the
   5 encoder tests were skipped on every machine, including the art_build Python and the builder's worktree, and the report's "passes in the
   art_build Python" could not have come from the committed file. To see it fail, run the tests at 42e4172 with the art_build Python: 5 skipped.
   The test now resolves the face exactly as the build does, and they run 5/5 OK in the art_build Python.

**Later (this repo, for J67 / Liam's play test)**
2. **Campaign minimap content stays 1x inside the 2x frame.** In `uiscale/runs/2026-11-02_j66/raw/r2_campaign.jpg` (bottom left), the map
   image fills roughly a quarter of the frame. It is missing from the report's "Still 1x or wrong" list and from the fact
   `napoleon.ui.scale_2x_packs`. J67 should add it, probably next to the battle radar, which is also engine-placed.
3. **Not seen in game:** tooltips, the settlement panel and the campaign unit-card row. The report names this deviation, since there is no
   click or hover verb. Liam's first play test should look at these first, as the report says.
4. The build reads the Lora face from an absolute path into the read-only empire-remastered clone until J68 vendors it. This is accepted
   under D42. Remove the fallback when J68 lands, so the build does not quietly depend on the evidence repo.
5. The template route-1 probe is undecided, and the per-context font-size probe was not done. Both are deviations the report names. The
   shipped route-2 redirect is proven by the proxy.log hit, and the slots are Empire's proven set.

### Merge effects on other branches
None. No gate, policy or rule changes. `tools/verbs/jobs.py` only adds the `uiscale/core` promotion entry.
