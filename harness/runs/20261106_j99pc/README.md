# J99 run 20261106_j99pc: vanilla UI reference

No sitting ran and the game was not launched. All 31 J10 shots still exist on the PC and each file's sha256 matches `harness/runs/20261102_j10pc/shots.json` (checked 2026-11-06, and again by
`gallery.py page` on every build), so the J10 shots were reused as the brief allows. Their states, files, sha256 and units stay in that `shots.json`. No crash dump can come from this job.

## Checks that fed the facts

- **Default visibility** (`napoleon.ui.layout_flag_visible`): component flag byte 3 against J10's live `Visible()`, on the four panels and HUD trees compared (`camp_lists` with `entity_lists`, `camp_gov`,
  `camp_diplomacy`, `land_deploy` with `land_battle_orders`): 816 components matched by path. Byte 3 set and visible 747, clear and hidden 48, set and hidden 20, clear and visible 1. The other six bytes do not separate them.
- **Image-use tail** (`napoleon.ui.image_use_tail`): the `entity_lists` frame uses read byte by byte, then ten composites compared by eye with their shots (`jobs/J99/report.md`).
- **Front-end skin** (`napoleon.ui.frontend_skin`): `frontend_ui_main` and `frontend_ui_single_player` against `j10_fe_main` and `j10_fe_single_player`, with and without the `spanish_skin` art.

## Hashes

Composite rgb sha256, the same on a re-run: `campaign.entity_lists` c0932d70047444934b7f14bbd85aef011b843fc9fc5130e49450d9a46727f3b5, `frontend.single_player`
98bc8d1a700ada1d9ca2bfcd941d2c8859d0e07d192859c8e288bb7a91d70990. `components.json` sha256 starts 9c7aafabedf00601 on both rebuilds.

Viewer: `viewer-wasm` from CI run 42058592470, `viewer.wasm` 2bdc8a112021772a4e4ad08004bb3e096707f9fcbff95625073f217f478b0f78, the same as `uikit/napoleon/baseline.json` `wasm_sha256`.
