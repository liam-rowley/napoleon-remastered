# J99 report: Vanilla UI reference gallery

J99 built the private "Vanilla UI reference" page (https://claude.ai/artifact/UjDeJAHtEQts6c9WG1rk67): 300 screens and 1,338 component kinds, each kind beside its Engraved Plate twin or marked as a gap. 298 screens are composited from the layouts and game art, 213 of them with no hatched box; the other 2 are records nothing can read. 46 surfaces sit beside live J10 shots, which were reused after all 31 sha256 matched, so **no sitting ran, the game was not launched, and this job can have produced no crash dump**. Most library mappings are guesses for J69: 1,295 of the 1,338 kinds are marked uncertain.

## What was built

| Item | Where |
|---|---|
| Inventory and its output | `uikit/napoleon/vanilla/inventory.py`, `components.json` |
| Compositor, strips, twins, staging | `uikit/napoleon/vanilla/gallery.py`, `page.html`, `README.md` |
| Twin screen, with its baseline for review | `viewer/napoleon/vanilla_ref/`, `uikit/napoleon/baseline.json`, `uikit/napoleon/baseline/vanilla_ref_*.png` |
| Tests (20) | `tests/test_uikit_vanilla.py` |
| Run record | `harness/runs/20261106_j99pc/README.md` |
| Tools rows | `uikit.napoleon.vanilla.inventory`, `uikit.napoleon.vanilla.gallery` |
| Facts | `napoleon.ui.layout_flag_visible`, `napoleon.ui.image_use_tail`, `napoleon.ui.frontend_skin` (dated 2026-11-06, run `20261106_j99pc`) |

## Counts

| Screens | Count |
|---|---|
| Surfaces on the page | 300 (174 layouts, 126 template records) |
| Composited | 298 |
| Drawn with no hatched box | 213 |
| With at least one hatched box | 85 (380 hatched image uses) |
| Unreadable, shown as a labelled card | 2 (`uied.templates/BattleEditor`, `uied.templates/InputWindow`) |
| Stand-in glyphs | 0 |
| Surfaces holding a reached unit, shown with a shot | 46 (of J10's 44 reached units; one unit can span two surfaces) |

| Kinds | Total | Sure | Uncertain | Gap |
|---|---|---|---|---|
| Template | 141 | 8 | 101 | 32 |
| 9-slice frame | 7 | 3 | 4 | 0 |
| Frame in one component (added, see Deviations) | 60 | 0 | 60 | 0 |
| Button family | 1,130 | 0 | 1,130 | 0 |
| **All** | **1,338** | **11** | **1,295** | **32** |

Every button family is uncertain by rule: the mapping looks only at folder and name. 1,336 kinds have a state strip and 1,254 have 2x art from the masters. The 2 without a strip, `template:Initialise#arg3` and `template:SetTooltip#arg1`, are unresolved arguments from the atlas's script walk, not real templates. They stay because the brief lists every name in `templates_used`.

Page: 348 files, 67.2 MB, in three publishes plus a fourth for the 40 re-skinned front-end composites (the first attempt at the second batch was refused for a shot name I mistyped). The twin grid has 40 cells over 15 classes. Lint and the four-corner gate report 0 findings.

## Five-surface comparison

| Surface | Live shot | Result |
|---|---|---|
| `campaign.entity_lists` | `camp_lists` | Frame, gilt corners, tabs, header, dividers and scrollbar match. Rows are script-filled and absent; the selected tab differs. |
| `campaign.objectives_screens` | `camp_buildings` (J10's listing; `camp_missions` shows it too) | Panel, tabs and title match. The composite shows the default Victory Conditions tab, the shot shows Missions. |
| `common.unit_information` | none: not reached | Reads as a complete panel, with 15 pink fields; no live truth to compare. |
| `battle.land_battle_orders` | `hist_deploy` | Orders bar and central dial match. The formations panel is drawn but hidden live by a script; flags are the art's default, not the faction's. |
| `frontend.single_player` | `fe_single_player` | Plate and buttons match after the skin fix. Two buttons and the heading show keys, because their text is set at run time. |

**Ten composites by eye:** the five above less `unit_information`, plus `government_screens`, `diplomacy_panel`, `technology`, `frontend.main`, `frontend.options` and `menu_bar`. Layout and position agree on all ten. Known differences: script-filled content, default against live tab or state, and the front-end background, which is not in these layouts. `frontend.main` shows the Single Player submenu open, and `government_screens` draws a flat blue box where the portrait goes. `frontend.options` shows a tab's content where the J10 shot is empty.

This was a judgement by eye, not a measurement.

## PC test

| Check | Result |
|---|---|
| `components.json` rebuilt twice | identical (sha256 starts 9c7aafabedf00601) |
| `campaign.entity_lists` composited twice | identical, c0932d70047444934b7f14bbd85aef011b843fc9fc5130e49450d9a46727f3b5 |
| `frontend.single_player` composited twice | identical, 98bc8d1a700ada1d9ca2bfcd941d2c8859d0e07d192859c8e288bb7a91d70990 |
| `job.sh status`, `pc_deploy.py status` | not run: the brief asks for them only if a sitting ran |

## Evidence

- Run `20261106_j99pc` (`harness/runs/20261106_j99pc/README.md`) and J10's run `20261102_j10pc`.
- Artifact versions 1 to 4; the file listing after version 3 shows 348 files, the same count as staged.
- Viewer: CI run 42058592470, `viewer.wasm` equal to `baseline.json` `wasm_sha256`.

## Deviations from the brief and why

1. **Composites read the layouts, not only the atlas.** The atlas drops each image use's rect, colour and tail, without which frames cannot be placed. `gallery.py` parses them through `uic` and `tpl`, reading the packs in place.
2. **No per-unit crops.** The live tree's rects do not locate docked panels: `entity_lists` reports x=648 and sits near x=1290. Wrong crops would mislead, so the page shows whole shots.
3. **Added `state_frame` kinds (60).** Most vanilla panel frames are eight or more image uses in one component, which frame groups cannot see; leaving them out would hide the main frames.
4. **Front-end art uses `spanish_skin` where a copy exists.** Without it all 40 front-end surfaces were blue against a red game. The trigger is unknown, so this matches observation only. Strips are not re-skinned.
5. **Empty-path uses draw flat colour, not a hatch.** 397 uses have no image path; they are rules and fills, such as list dividers. Hatching them gave a full-screen hatch.
6. **Strips are sprite sheets with limits.** An artifact holds 511 files. Kinds over 256 px show their default state only, states that draw the same pixels are merged, and masters are shown per art piece (at most 12 per kind, art up to 256 px).
7. **The viewer came from CI.** `build.sh --docker all` failed on a refused connection while fetching sources, so I used the README's fallback; its hash matches the baseline. The Docker failure itself was not diagnosed.
8. **No sample images in `uikit/napoleon/runs/`.** They were optional, and the page holds them all.

## Core candidates

- The compositor core (`Canvas`, `Sheets`, the tail and flag decode) is game-agnostic given an atlas.
- The atlas (`core/discovery/ui_atlas.py`) should carry each image use's rect, colour and tail, which would remove deviation 1.
- The atlas's script walk should not report `#arg` placeholders as template names.

## Open questions

- **For the reviewer:** the new `vanilla_ref` baseline counts only once `review.md` carries `changes.py`'s line, `Baseline accepted: <sha>`. No library class or token changed.
- **Which front-end skin is the vanilla reference, and does it depend on the install?** Default: red, as the shots show. The fact `napoleon.ui.frontend_skin` records only that observation, because the `ratchet` gate refuses a new open fact; the trigger is still unknown.
- **2x strips from masters or nearest-neighbour?** Default stands: both, labelled.
- **Does the gallery join the D17 review page?** Default stands: yes, later, when J35 builds it.
- **States beyond the default on the Screens view?** Default stands: no.
