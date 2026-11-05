# J37 desk run 2026-11-03_j37_static: static RE of the engine's font path

Static reverse engineering only: no PC, no game launch, no game-folder read. The input is a copy of the vanilla `Napoleon.exe` in the session
scratch folder (sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, the `proxy/napoleon/identity.json` exe), read with `discovery/core/x86re.py`
in the pinned `discovery/core/re_env.py` venv (capstone 5.0.6, pefile 2024.8.26). Strings from `discovery/napoleon/exe_strings.tsv.gz`.
Every address is a VA at ImageBase 0x400000 (RVA = VA - 0x400000). Every claim below is a static reading: a candidate until the PC slot's file survey
(the PC plan in `uiscale/runs/2026-11-03_j37_static/pc_plan.md`) confirms it. The anchor bytes are what a later engine_sites row would pin; no engine site is added here (no hook is built: D2, rule 79).

## 1. Font names: a fixed list of 19, unknown names fall back to `Ingame 12, Normal`
- Table of 19 `char *` at **0x1464120** (null-terminated), in this order: `Ingame 10/12/14/16/18/24` Normal and Bold (12 entries, Normal before Bold),
  then `Frontend 12, 14, 16, 18, 22, 24, 38` Normal (7). This is the list `jobs/J37/brief.md` cites at rva 0xff1d78 (the strings) and Empire's FONTS.md "Exe findings".
- **0x1029fd0** `FontIdByName(name)`: walks the table with a string compare (`0x4f1000` = not-equal) and returns the index; a name not in the list returns **2**
  (`Ingame 12, Normal`). Anchor `83ec14535633db33f6578b7c2424895c2410`; the default is the `mov eax, 2 / cmovne eax, esi` at 0x102a033.
- Its one caller is the layout state reader (0x102197a, function 0x1021410): for layout version >= 27 (0x1b) it reads the font name string and stores the
  index at `state+0xbc`; older versions read a numeric id and map it through the dword table at 0x14644d0 (**0x1029fc0**, anchor `8b4424048b0485d0444601c3`).
- **Consequence:** a layout or template font name that is not one of the 19 (for example `Tooltip 24, Normal`, `Ingame 20, Normal`, `Frontend 32, Normal`) draws as
  `Ingame 12, Normal`. The slot check (`uiscale check-fonts`) refuses such a name in a scaled build.

## 2. The preload: the 19 names become 19 font objects at UI start
- The function around **0x102afc0 .. 0x102b470** calls the renderer's `GetFont(family, size, bold)` 19 times, in the list order, with lower-case families
  (`"ingame"` 0x13f29a8, `"frontend"` 0x1314b24) and immediate sizes 10, 12, 14, 16, 18, 24 (each Normal then Bold), 12, 14, 16, 18, 22, 24 and **38** (0x26, the last call at
  0x102b430, anchor `68244b31018b078bb020020000e8be534cff6a006a26`), appending each result to the vector at `this+0x14`. The font id from section 1 indexes this vector.

## 3. `GetFont(family, size, bold)`: even sizes 6 to 32 only
- Called through slot **0x220** of the renderer vtable at **0x140cc30** (installed at 0x1132549 and 0x113965a): slot 0x220 = **0x11aa7e0** `add ecx, 0x699ac; jmp 0x116cbb0`
  (anchor `81c1ac990600e9c523fcff`), so the font cache is a member at renderer+0x699ac. It is the only jump or call into 0x116cbb0 in `.text`.
- **0x116cbb0** (`ret 0xc`, three arguments; anchor `558bec83ec288b450c535657660f6ec0`): size goes through float and a CRT rounding call (0x1288900) back to an integer `n`;
  then **`n` odd -> `n - 1`; `n < 6` -> 6; `n > 32` -> 32** (anchor at 0x116cc24: `f6c30174014b83fb067307bb06000000eb0ab8200000003bd80f47d8`);
  file name = family + `_` + (`b_` if bold) + `n` + `.cuf`; looked up by name in the cache (0x116cb60) and, on a miss, opened by **0x11597d0** as `font/` + name (anchor `83ec405668842e4101`).
- **Consequences** (static, to be confirmed by the PC file survey):
  - `Frontend 38, Normal` opens **`frontend_32.cuf`**, not `frontend_38.cuf`. No `GetFont` caller can open `frontend_38.cuf`, `tooltip_36.cuf` or any size above 32.
    J66's 2x fonts pack (`ui_scale_2x_fonts.pack`) ships a Lora `frontend_38.cuf` for the layouts it maps to `Frontend 38` and no `frontend_32.cuf`: if this holds in game,
    every `Frontend 38` text in J66's 2x build draws the vanilla CA `frontend_32` face at h2 32 (84 % of the planned height), and J66's `frontend_38.cuf` is never read.
    The fix is font data only: the 2x pack carries `frontend_32.cuf` = the Lora render J66 builds for the `Frontend 38` slot (section 7).
  - Odd sizes never load through this path: `Ingame 10..24` and `Frontend 12..24` in the list are all even, so the list itself is unaffected.
  - The engine cannot be asked for a larger font than 32 by data: a factor that would want h2 > 32 for a slot stays at 32 (the 2x set already sits at the top: 24 and 32).

## 4. Fixed-size callers outside the list (engine-drawn text)
Every other site that loads a family string and calls slot 0x220 (scan of `[reg+0x220]` loads next to a family-string push, `getfont.py` in the session scratch):

| site | call | file | what it is (evidence) |
|---|---|---|---|
| 0xdae510 (anchor at 0xdae51c `6880d330018b7b208b078bb020020000e8cf2274ff6a006a16`) | `GetFont("Frontend", 22, 0)` | `frontend_22.cuf` | a text style (size 0x10, 2, 1, colour 0xffffffff, font) registered by 0xdae6d0; built once by the MVC manager's "Create UIs" step (call at 0x480de2). Candidate: the front-end version string and other engine overlay text |
| 0x1215a20 (anchor at 0x1215b62 `6880d330018b078bb020020000e88cac2dff6a006a168d4424`) | `GetFont("Frontend", 22, 0)` | `frontend_22.cuf` | called from 0x11db970, which loads `ribbon.fx`: text drawn along a ribbon (candidate: campaign map region and sea names) |
| 0xe33450 | `GetFont("console", 12)`, `("frontend", 12)`, `("frontend", 16)` | `console_12`, `frontend_12`, `frontend_16` | the dev console, created in the MVC open handler (0x480ea8). Dev only |
| 0x1197430 | `GetFont("ingame", 16)` | `ingame_16` | the "Rendering statistics" debug overlay. Dev only |
| 0x117fb10 | `GetFont("editor", 12)` | `editor_12` | `UI\WarscapeTwin\gadgets` (the editor). Not UI text |

`frontend_22.cuf` is therefore the engine-text slot: J66's scaled layouts no longer name `Frontend 22` (the scaler maps it to `Frontend 38` or `Frontend 24`), so at a factor
it can carry a Lora render at 22 x factor without changing any scaled layout's text.

## 5. The loading-screen quote: largest of `frontend_20` .. `frontend_10` that fits
- Six strings `frontend_20.cuf` .. `frontend_10.cuf` (0x140cfe0 .. 0x140d030) are copied into a static array at **0x1835010** (stride 0xc) by the once-only init at 0x110d907.
- The quote function (loop head 0x110d859, anchor `57bd1050830133ff6a016a6455e865bf040083c40cc74424`) opens each file **directly** through 0x11597d0 (`font/` + name; not through
  `GetFont`, so no clamp), tries to lay the quote into the text box (0x1196ae0; box width and height are floats at box+0x1c and box+0x20) and **stops at the first file that fits**
  (loop step 0x110d8a6 `83c70c83c50c83ff4872b08b`: six entries). The text is drawn into an offscreen texture of the box size (0x4c9b60) and shown as a quad whose x and y
  scale are set to 1.0 (0x110d8bf `c7412c0000803fc741300000803f`).
- **Consequence:** the quote's size follows the font data and the box. Lora renders of the six files at the factor make the quote larger only if the box is larger at 4K; with a
  1080p-sized box the loop steps down to a smaller file and the quote stays the same size (never clipped: the loop only accepts a fit). Where the box size comes from (screen
  pixels or the 1280x960 canvas) is not settled statically: the PC file survey shows which file the loop accepts at 1080p and at 4K.

## 6. Other text paths read
- **Credits:** `text/credits.xml` `<line>` / `<string colour fontsize indent>` with `left`, `right`, `gap` (parser 0x4635b0, attribute reads at 0x4638b0 / 0x4638d9). The credits
  size is data, not an exe constant; it reaches `GetFont`, so it obeys section 3's 6..32 rule (static reading of the attribute only; the call into `GetFont` is not traced).
- **Subtitles:** the option (`Display subtitles during movies`, `subtitles <true|false>`), `subtitles_table`, `videos_subtitles_junctions_table`, `read_subtitles_file`. No
  `GetFont` site with a subtitle string was found; the subtitle text most likely takes a font from the preload list by id. Not settled statically (PC: file survey with a movie).
- `fontsize` (rva 0xf1565c) is the credits attribute, not a subtitle or preference setting.

## 7. Where a scale factor could apply, and the route
- No resolution or UI-scale input reaches the font choice: `GetFont` takes a constant or a list size, the quote loop takes a fixed file list, and the quote quad scale is a
  constant 1.0. The only runtime size changes are the engine's own shrink-to-fit (text taller than its box is drawn smaller: Empire FONTS.md "Line spacing") and the quote's step-down.
- So engine text can be made larger and crisp **only by font data**, per install factor (the brief's decision; D7, D2): put the glyphs at factor x size into the files the
  engine opens. Which files those are, per text item, is the inventory `uiscale/napoleon/engine_text.json`; the data model is `uiscale/napoleon/font_slots.json` `engine`.
- An exe constant (the 22 at 0xdae533 and 0x1215b76, the clamp 0x20 at 0x116cc37, the quad scale) would be a patch (D2, rule 79): out of scope, and not needed for 2x.
