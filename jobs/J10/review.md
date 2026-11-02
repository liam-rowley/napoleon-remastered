## Round 1 (2026-11-02, branch job/J10 at 41cc196)

**Verdict: merge.**

Checked: `wsc gates` (11 ok, 1 warn: skipped tests that need numpy, Pillow, capstone or the viewer build, none from this branch), `wsc discovery check` (ok), CI on the head (gates, harness-windows pass; proxy, viewer skipped). `pr_policy` refuses only for the missing review and the row not yet `done`, which this round fixes.

Verified against the data, not the report:
- `registries/ui_elements.jsonl`: 262 rows, all `atlas`, no duplicate ids, every non-engine row has `vanilla_source`, none has empty `interactions`, every data field source is `getter:`, `loc:` or `db:`.
- `registries/assets.jsonl`: 12,295 rows before and after; 6,335 changed, and only in `used_by`; every `used_by` id exists in `ui_elements`.
- Scope: nothing under `core/`, `proxy/` or `harness/core`; all 9 commits carry the session trailer.
- The call budget, crashes, display-restore record and sittings are named deviations with reasons.

### Blockers
None.

### Should-fix
None.

### Later
- 92 rows have no `data_fields` (66 templates, 10 engine, 16 others). Plausible for display-less pieces, but the rows do not say so; the contract stage should treat an empty list as "none traced" and read the atlas `unresolved` list (3,711 fields, mostly parameter and upvalue sources).
- The three getters.lua crashes (`Napoleon.exe+0x538e5`) came from one probe misuse and an orphaned driver; the pid-file guard is local to the J10 drivers. The report's core backlog item (an exclusive driver token per lock, and `ctl reset` from a historical battle) should be filed in warscape-core `docs/BACKLOG.md`.
- 69 units are `static_only` because they need a click; D39 leaves them to the contract stage.
- The run-folder probes (`tree.lua`, `fe_page.lua`, and J9's) move into `proxy/napoleon/lua/probes/` at the next DLL change (likely J24).
- Open questions for Liam, not review findings: the three J33 test screens, and whether the UI scales by height above 1080p or stays 1:1.
