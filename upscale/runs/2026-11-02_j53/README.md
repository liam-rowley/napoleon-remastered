# Run report 2026-11-02: UI art play packs (J53)

Session `77269dc7-d1c0-49ec-8f37-c570ba58f48e`, branch `job/J53`. PC: Windows 11, RTX 4090, headless 1920x1080 on the virtual display,
UI scale 1, game lock `J53` from 15:41:13 to about 15:46:00 UTC. Every launch went through `core/harness/ctl.py` (`scene`, `shot`) with the adapter's
`ctl.launch.keys` (`dev.skip_intro=1` among them). The raw results and shots are in `raw/`, named `<stage>_<scene>.json|jpg` (`a` = 11 roles, `b` = the default four).

## Packs
`python3 core/wsc.py upscale pack --play --roles <the 13 roles with outputs>` read the manifest and checked it (`verify: 9438 checked, 0 with problems`).
It wrote `C:\napoleon_remastered_pc\upscale\work\packs_play\` in 1 min 42 s. `cursor` has no outputs (`not_needed`), so it has no pack.

| role | entries | MB | held back | sha256 |
|---|---|---|---|---|
| ui_art | 397 | 354.4 | 0 | `867afeefcdccd9b717e5d9e3ebaab60c4f8a75b29241c5f0a4276cdff7e48d87` |
| icon | 555 | 17.8 | 0 | `6d0831cdea66d27a5434ec382cfccb4643555bcbe26740af2d2248421f4814b0` |
| panel_frame | 517 | 193.9 | 0 | `b05e93a216e27bea6229efcf808bef47f39f20e3b9840ea77144110f530e9406` |
| button_state | 2015 | 142.8 | 0 | `a8cb95baa3753fcb64bc706d0db5189889105a3a853d00089b5d5e4925089f79` |
| map_pip | 149 | 2.7 | 0 | `4a81439c4c2319fdb1c02ba14024bca86bf11a8c15509e0056861a7a10316bb8` |
| building_icon | 657 | 102.8 | 0 | `f1dd82b32d1954415b1e5569a45b35a4a73af1d702374781b010338104a813f2` |
| technology_icon | 69 | 1.4 | 0 | `afdc5d49a1b835d2d3707dfa456aba7ee1411c785b835113f537c6b0f89f8f94` |
| achievement_icon | 73 | 29.2 | 0 | `66c79f145be8b138bfa0ce513c381f804d36561fc30c6759a18bc443f9a0e06a` |
| event_picture | 229 | 537.1 | 0 | `ad208c653615ed45820a2c551b01a7134360eece7ab94293bacd5f4593ff5222` |
| unit_card | 1105 | 160.4 | 0 | `825d0df25659a1f76661e1e26f4214699174107e4e0ed84f806848f9fe4ec600` |
| portrait | 1375 | 169.2 | 0 | `9fedd5a9bd7ae9cf306eabdc2c0911c940cb9eaf60e004c90d5a15b10a70d731` |
| flag | 2258 | 1105.1 | 0 | `02970976a4355ee7de889348985b073fd0c8c9d9fa0e12480acdffb5f67e8335` |
| loading_screen | 11 | 6.4 | 28 | `9b56c1096d2e9f15bb1a470569e7ff184678ec8cd831c26562b8f69c3789091a` |
| **all 13** | **9410** | **2823.1** | **28** | |

**Held back, all in `loading_screen` (counted from the manifest):**
- 6 DXT outputs have a side that is not a multiple of 4: `loading_screen_heading.dds` 1150x380, `progressbar_background_blue.dds` 1600x110,
  `progressbar_foreground_blue.dds` 1780x110, `allied_forces_box.dds` and `enemy_forces_box.dds` 580x710, and `loading_screen_pictures\2.dds` 4803x3000.
- 23 outputs are over 4096 px on a side: the 4800x3000 loading pictures as `.dds`, `.tga` and `.jpg`, and `frontend ui\loadingscreen\screenshot.dds` 4800x2250.
  `2.dds` is in both lists, so 28 files are held back in all.
- `loading_screen` is not empty: 11 of its 39 files are in the pack. Every other role holds back nothing.

## a) Game folder and proxy
- `pc_deploy snapshot` gave `_scratch\j53\snap_start.json` (1564 files). It is **identical** to J28's `snapshots\post_uninstall_20261102T145923Z.json`.
- The proxy was not built again. The DLL inputs on this branch have build id `715e9dfc0727` (`build_id.py`), the build J28 accepted. The kit took that DLL:
  `kit_20261102T154016Z_23dbc9e2d143`, from `pc_deploy kit --dll`, then `send` (43 files sha-checked) and `install` (exe vanilla).

## b) Smoke run
The packs went in and out through watcher ps1 jobs. Each job ran a sha-identical run copy of `upscale/pc/install_packs.ps1` from `_scratch\j53`.

| step | result | evidence |
|---|---|---|
| a: 11 roles in (all but `loading_screen`, `event_picture`; 2.28 GB) | ok, 11 packs, sha256 checked | job `J53-20261102T154124Z-1203230000` |
| a: `scene land_small` + shot | ok, battle_deploy, **load 3.9 s**, launch `20261102T154206Z-p39476`, no retry | `raw/a_land_scene.json`, `a_land.jpg` |
| a: `reset frontend` + shot | ok (main menu) | `raw/a_reset.json`, `a_frontend.jpg` (job `J53-20261102T154307Z-323818408`) |
| a: `scene campaign_start` + shot | ok, campaign, load 3.3 s | `raw/a_campaign_scene.json`, `a_campaign.jpg` |
| a: proxy log | `packs: 22 packs, 96165 entries indexed`, which is 86995 vanilla (J28's log) + 9170 play | proxy.log, moved to `_to_delete` by the uninstall |
| a: kill, 11 out | ok | jobs `J53-20261102T154404Z-3121119658`, `J53-20261102T154407Z-153504669` |
| b: default four in (`ui_art`, `icon`, `panel_frame`, `button_state`; 709 MB) | ok, 4 packs, sha256 checked | job `J53-20261102T154417Z-69030222` |
| b: `scene land_small` + shot | ok, battle_deploy, **load 3.8 s**, launch `20261102T154427Z-p30528`, no retry | `raw/b_land_scene.json`, `b_land.jpg` |
| b: `reset frontend`, `scene campaign_start`, shots | ok | `raw/b_*.json`, `b_frontend.jpg`, `b_campaign.jpg` |
| b: proxy log | `15 packs, 90479 entries indexed` (86995 + 3484) | |
| b: kill, 4 out | ok | jobs `J53-20261102T154548Z-166524738`, `J53-20261102T154550Z-141046258` |

**Verdicts** (fact `napoleon.ui_art.play_packs_load`):
- No crash, dump, WER report or hang in either stage. `napoleon_remastered\dumps` was never created, WER has no Napoleon report after the start snapshot, and the watcher has no hang folder.
- Nothing is blank or drawn at the wrong size in the six shots. These were checked by eye. The roles nothing had loaded before are on screen at the vanilla size:
  - the battle unit cards and the general's portrait;
  - the unit flags over the line in battle;
  - the campaign flags and settlement icons;
  - the portrait in the advisor panel;
  - every HUD frame and button.
  So for these elements no UI code sizes the drawing from the texture's pixel size.
- Loading is not slower: 3.9 s and 3.8 s to `battle_deploy`, against 4.2 s in J50 with the four J36 packs under the unused prefix. Memory was not measured.
- Not loaded in the smoke run: `event_picture` and `loading_screen`, as the brief says. The headless shots cover the main menu, the start of a campaign and a battle in deployment.
  Event pictures, the loading screens and most panels (diplomacy, technology, building browser) were not on screen.

## c) Back out
- Lock released at about 15:46:00. The watcher restored the `headless` profile byte for byte at 15:46:05 (prefs, keys, battle prefs, mod ini: 0 mismatches), then the virtual display.
- `pc_deploy uninstall`: identical to its pre-install snapshot (1564 files), exe vanilla.
- `snap_end.json` against `snap_start.json`: **identical**. `pc_deploy status`: nothing installed, exe vanilla, no `.git`.
- Every pack was moved, never deleted, to `watcher\_to_delete\J53_packs_a` and `J53_packs_b`. The originals stay in `upscale\work\packs_play\`.
