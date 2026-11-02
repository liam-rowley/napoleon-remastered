# J68: Vendor the Lora font face for the UI scale fonts

Phase 5 backlog from D42 (1): vendor the Lora face at `uiscale/fonts/Lora-Variable.ttf`, so the UI scale fonts no longer read it from the empire-remastered clone. J66 could not copy it:
the project deny rule `Edit(~/repos/empire-remastered/**)` in `.claude/settings.json` matched the source path of a `cp`. That rule stays; this job does not route around it.

Model: Sonnet medium (D15). Budget about 15 tool calls; at the cap, stop, commit, report what is left. No subagents, no game launch.

## Precondition (Liam does this before the job starts)
The face is in place at `uiscale/fonts/Lora-Variable.ttf` in the checkout the job runs in, copied by Liam, untracked. For example, from Git Bash:
`cp ~/repos/empire-remastered/ui_scale_mod/font_src/Lora-Variable.ttf <checkout>/uiscale/fonts/Lora-Variable.ttf`.
The alternative is that Liam first narrows the deny rule himself, naming the exact rule he approves, and says so in the chat that starts the job. The builder reads that
rule; it never edits `.claude/settings.json` or any other settings file.
Expected file: 212196 bytes, sha256 `822a6621ccbe8d97d20ac88c1c41f5615c9c2c202eaa75f272cd452aac6475a7`.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J68`). Read `docs/DECISIONS.md` D42 (1) and `jobs/J66/report.md` (Fonts, the build evidence).
- First check the precondition: `test -f uiscale/fonts/Lora-Variable.ttf`. If the file is missing, apply the first kill criterion.
- Do not copy, move or write anything under `../empire-remastered`, and do not look for another copy route (no git, python, powershell or tool-driven copy of that path).

## Deliverables
1. **Verify the file.** `sha256sum uiscale/fonts/Lora-Variable.ttf` and `sha256sum ~/repos/empire-remastered/ui_scale_mod/font_src/Lora-Variable.ttf` (reading a file to hash it is
   allowed) must be equal, and equal to the sha256 above. Put both in the report.
2. **Commit the face** with `uiscale/fonts/OFL.txt` already beside it. Check `OFL.txt` names Lora; add nothing else.
3. **References.** `uiscale/napoleon/config.json` `font_faces` already lists the vendored path first and the clone as fallback: keep both entries, and update `font_faces_note` and the
   "Font face (D42)" line in `uiscale/README.md` to say the face is vendored (the clone is only a fallback). Check `release/napoleon/licenses.json` (Lora row) still points at
   `uiscale/fonts/OFL.txt`. Run `python3 core/wsc.py find lora` and `python3 core/wsc.py find font_faces`; update any registry row they return that describes where the face lives
   (`python3 core/wsc.py reg set ...`). If none exists, say so; do not add rows for the sake of it.
4. **Same fonts.** `python3 core/wsc.py uiscale status`, and if the PC work folder allows it, `python3 core/wsc.py uiscale build`: the fonts pack must still hash
   `5f510b27afa3...` (J66, after D42). Report the hash, or why it could not be checked (it is not a failure of this job if the PC work folder is absent).
5. `python3 core/wsc.py gates` green and `python3 -m unittest tests.test_uiscale_fonts` passing.

## Out of scope
- Any change to `core/`, to `.claude/settings.json` or other settings, or to anything in `../empire-remastered`.
- Removing the clone fallback from `font_faces`, changing the face, the recipe or the slot set, a different font, or any change to `uiscale/core/`.

## Kill criteria
- Precondition not met (`uiscale/fonts/Lora-Variable.ttf` missing, or its sha256 or size differs from the expected values): stop at once, change nothing, and report which check failed.
  Do not try another route to the file.
- Any tool call is refused by a deny rule: stop and report the call and the rule; do not retry another way.
- The rebuilt fonts pack hash differs from `5f510b27afa3...`: stop and report both hashes; do not commit the font as "same".

## Finish
Write `jobs/J68/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): the two sha256 values, the references updated, the fonts
pack hash check and the gates output. Then `wsc reg set jobs J68 status=review report=jobs/J68/report.md`.
