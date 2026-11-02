## Round 1 (2026-11-02, branch job/J34 at 9f5f76a)

**Verdict: merge.**

Checked: `wsc gates` (11 ok, 1 warn: skipped wasm/numpy/capstone tests, 0 failed), `build.py --check`, `lint.py` (0 findings; sweep 4096 colours, 110 adjusted, 0 failing),
`tests.test_uikit` (34, 6 skipped here for no wasm). CI on the head: gates, changes and **viewer** green. The viewer job builds the wasm and runs test_viewer, test_uikit,
lint, the four-corner gate (0 findings) and `changes.py` (no change against the committed baseline), so the PC hashes reproduce on Linux (the report's stated risk did not happen).
`policy` refuses only for the missing review and row, which this round supplies. I read the committed 1080p board render: every component and state is shown, nothing clipped.

Risk-first reading: `tokens.py` `faction_tokens` (the on-colour fix; it feeds every screen's tint). The 2 % step loop terminates (it moves toward white or black, so contrast rises
monotonically), hover/pressed move away from on_fac so the ratio only rises, and the sweep tests cover both. No engine memory, PC or install code is touched; no `core/` change.

Claims against evidence: tokens, class and stylesheet counts, fonts pinned by sha256, 5 engine_facts rows, tools rows and CI wiring all present; deviations are named with reasons.

### Blocker
None.

### Should-fix
None.

### Later
- The report was written by the orchestrating chat, not the builder subagent (disclosed, with Liam's approval). Not a defect, but the policy check keys on session id: a future job done this way
  must still be reviewed by a different session (it was here).
- Open questions 2 (24 sprites), 3 (on-colour rule fix as a decision row), 6 (board lock, `ui_elements` row), 7 (blurred plate shadow) and 8 (flag slot size) are Liam's. Liam plays the board
  (private artifact in the report) and locks it; `LOCK.json` is not written. Proposed decision row (token format and faction route) is left for Liam/the orchestrator to number.
- Promotion candidates to the core (tint/contrast maths, lint engine, gate, changes, library staging in render.py) are proposed in the report, not made; a promotion row is a later brief.
- No rule changed that other open job branches must meet.
