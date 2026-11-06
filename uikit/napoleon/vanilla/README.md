# uikit/napoleon/vanilla: the vanilla UI reference (J99)

Every vanilla screen and every reusable vanilla component kind on one private page, beside the live shots and the Engraved Plate library's twins, so J69's
sittings start from what vanilla looks like (D55).

**The page:** https://claude.ai/artifact/UjDeJAHtEQts6c9WG1rk67 ("Vanilla UI reference", private). Liam comments there; acting on comments is J69's.

| File | What |
|---|---|
| `inventory.py` | writes `components.json` from the atlas and the assets registry; `--check` compares a rebuild, `--stats` prints the counts |
| `components.json` | one line per kind: sizes, states with `assets` ids, use count, surfaces, `ui_elements` ids and `library`, the proposed J34 class or `gap` (`uncertain: true` where it is a guess). Ids, keys, sizes and counts only (J7) |
| `gallery.py` | the composites, the state strips, the twins and the staged page |
| `page.html` | the page itself; it reads `data.json` beside it |

The twin screen is `viewer/napoleon/vanilla_ref/` (its RML is written by `gallery.py twins`). Tests: `tests/test_uikit_vanilla.py`.

## Rebuild and publish

On the PC (it reads the game's packs in place and the 2.5x master packs under the PC state folder). Images go to `_scratch/j99/` and never to git:

```sh
python3 uikit/napoleon/vanilla/inventory.py
python3 uikit/napoleon/vanilla/gallery.py compose     # 298 composites, composites.json
python3 uikit/napoleon/vanilla/gallery.py strips      # sprite sheets of every kind's states and 2x masters, strips.json
python3 uikit/napoleon/vanilla/gallery.py twins       # needs build/viewer/out and Playwright
python3 uikit/napoleon/vanilla/gallery.py page        # checks the J10 shots' sha256, writes data.json, stages the page
```

Publish `_scratch/j99/vanilla_ui_reference.html` with the Artifact tool, `url` the page above, `root` `_scratch/j99`, and the other files in `files`. One publish takes at
most 255 files and 64 MB and the site is 348 files, 67 MB, so it goes in three publishes; files a publish leaves out are kept. An artifact holds at most 511 files, which is why strips are sprite
sheets. If Docker cannot fetch the viewer's sources, take `viewer-wasm` from the newest run that built it and compare `viewer.wasm` with `baseline.json` `wasm_sha256`.

## How a composite is drawn

`gallery.py`'s header holds the decode. The atlas keeps art ids per state but not where each image use sits, so the compositor reads the layouts through `uic` and `tpl`. Composites are
references: scripts fill rows, swap states and hide panels at run time, so the live shots are the truth where they exist. Pink text is a field the game fills, shown by its key. A hatched box is art
the game does not ship at the path the layout names. A use with an empty path is a flat rule or fill in its own colour.

Front-end surfaces draw the `spanish_skin` copy of an art file where one exists, because that is what the live shots show (`engine_facts` `napoleon.ui.frontend_skin`). Component strips do not: both
families are on the Components view under their own names.
