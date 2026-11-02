## Round 1 (2026-11-02, branch job/J49 at 163fec7)

**Verdict: merge.**

Checked: CI on 163fec7 all 8 checks passed or skipped; `tests.test_usage_reader` + `tests.test_jobs_hooks` 44 OK (rerun here); `python3 tools/usage_reader.py` on this PC
read 200 files in 2.2 s (cold cache), 0 lines skipped, attribution by trailer, branch and name all appear; policy only refuses for the missing review (this file) and row.

Risk-first reading: `tools/usage_reader.py` `scan_file` (the only code that touches `~/.claude`): opens read-only, keeps only ids, model, token counts, tool_use count, timestamps,
branch and agent name; no prompt or tool text is stored, returned or cached; the only write is `_scratch/usage_cache.json` (cache keyed by size and mtime_ns). `usage_state` is wrapped so a
failure cannot break the view. Brief deliverables 1, 2, 4, 5 (evidence), 6 (header, registry rows, rule 75 row) and 7 are present; kill criteria not triggered (output tokens within ~1%).

### Blocker
None.

### Should-fix
None.

### Later
- Per-card usage line (brief deliverable 3) is a table in the PC panel instead; the report names the cause (the core has only `view_panel`) and the missing hook (`card_extra`).
  If Liam wants it, it is a warscape-core backlog item through a warscape-core pull request.
- `attribute` (tools/usage_reader.py) takes the first job whose trailer set holds the session; a session that committed to two job branches is counted for one only. Rare; no change needed now.
- The week cost is not shown; the report says so.
- The report's `test_job_sh` full-gate failure is not this branch's (CI green); not reproduced here.
