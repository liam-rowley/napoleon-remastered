## Round 1 (2026-11-04, branch job/J79 at ac2f11c)
Verdict: merge

Reviewer: a fresh session that did not build the branch. The report was written by the orchestrating session from the builder's hand-back, so I checked its claims against the branch and the PC's art_build Python (read only, `-B`).

## What I checked
- **Machines:** `gates --fast` 12 ok, 1 warn (hooks wiring in this worktree), 0 failed. CI on `ac2f11c`: `gates` success; `proxy`, `viewer` and `harness-windows` skipped, which counts as passed (the diff touches neither `proxy/` nor `harness/`, so rule 79 does not apply). No red required check. `policy` needed only this review and the `done` row.
- **Tests:** `unittest tests.test_pc_state test_release test_uiscale test_uiscale_fonts test_upscale` on this checkout: 98 ran, OK, 20 skipped (game/PC only). In the PC's art_build Python (`C:\napoleon_remastered_pc\upscale\art_build\py`) `tests.test_uiscale_fonts` and `tests.test_uiscale` ran 26, OK, none skipped, so `Golden` (five fonts and the pack sha) and `Vanilla` (the long-form rule on every template state) pass against the real game files and face. The golden shas are real.
- **Deliverables against the brief:** golden shas and pack sha committed (`font_golden.json`); `_hb_pairs` raises `RuntimeError` without uharfbuzz and the GPOS fallback branch is gone from `encode` (docstring, `purpose:`/`when:`, README fixed); `requirements-ci.txt` hash-locks six packages and the `gates` job installs it with `--require-hashes` (the CI log in the report shows the suites that used to skip now run); `bootstrap.json` pins the embeddable zip and get-pip by sha256 and `setup_env.cmd` checks them on every run and deletes on mismatch; the masters' manifest sha is in `components.json` `external_provenance` and checked by `build_release.py`; PC paths come from `tools/pc_state.py`; the long-form pass is ported with tests.
- **Other deviations:** the `external_provenance` key, pefile and win hashes in the lock, the 85% `Gpos` agreement bound and D57 are reasoned and disclosed. Accepted.

## The first deviation (the refused `sed -i`)
`git diff origin/main...HEAD` shows no change to `tools/claude_hook.py` or `.claude/`. The refused edit was a line in `uiscale/README.md` naming the state folder: an ordinary repo file in the builder's worktree. Nothing was written to a game folder, the state folder or AppData. The hook's refusal was a false positive (a repo-path `sed -i` whose replacement text names a protected folder), and the editor-tool edit changed only the file the guard never meant to block. It does not matter for this merge. It was still against the brief's stop-on-deny rule: the right move was to stop and report. The builder's open question (should the hook resolve a plain repo-path target before it judges the text?) is a fair core-hook backlog item; nothing here changes it.

## Notes for the merge
- **D57 collision:** J64's branch also adds D57; `origin/main` has none yet. Whichever merges second renumbers its row to D58 and fixes its own references.
- No other open branch must meet a new rule from this merge. CI now installs `upscale/requirements-ci.txt`, so a branch that adds an import to the art, font or x86re tests must pin it there.
- The report's open question (rebuild the shipped `ui_scale_2x.pack` and templates on the PC and check long-form text in game) is a PC play-test follow-up, not a blocker.
