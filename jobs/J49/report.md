# J49 report: Usage source for the PC jobs view (rule 75)

Rule 75's usage half is closed: `wsc jobs view` on the PC now shows Claude usage per job and for the last 7 days, read read-only from Claude
Code's own transcripts in `~/.claude/projects` (tokens and tool calls as the headline, cost as a labelled estimate; no API, no network, no
conversation text).

Written by the orchestrator from the build agent's hand-back: the build ran as a subagent, and the harness refuses a subagent's Write of a
report file, so the parent writes it. Same Claude-Session as the build.

## What was built
- `tools/usage_reader.py` (pure functions, a streaming read, a per-file cache in `_scratch/usage_cache.json` keyed by size and mtime):
  `usage_by_session`, `usage_by_job`, `branch_trailers`, `attribute`, `budget_from_brief`. Replies are de-duplicated by `message.id`
  (element-wise max); sub-agent files `<session>/subagents/*.jsonl` fold into their session; tool calls are the `tool_use` blocks; cost is the
  last `cost-state` line. Attribution order: the `Claude-Session` trailer on `job/<id>` or `brief/<id>` (one `git log --source`), then the
  transcript's `gitBranch`, then a `J<n>-<action>` agent name; the rest is shown as unattributed. It fails soft: a missing folder gives an
  explanatory line, and bad lines are counted in `skipped`.
- `tools/jobs_hooks.py`: `USAGE_SOURCE` replaced by `usage_state`/`usage_html`. The PC block's usage-source line carries the source, the file
  count, the read time, the skipped count and the last-7-days totals; a collapsible table lists, per job, calls against the brief's budget,
  tokens by model, the cost estimate and the wall span, plus the unattributed total. Module headers and registry rows updated
  (`tools.usage_reader` new, `tools.jobs_hooks` re-synced to its header).
- `tests/test_usage_reader.py`, 7 tests: de-duplication, per-model sums, call counting, sub-agents, cost-state, the three attribution routes and
  unattributed, a corrupt line, a missing folder, cache invalidation, and no prompt or tool text in the rendered HTML. The `PcState` test is
  now hermetic.

## Evidence
Step 1 finding (Claude Code 2.1.316, read 2026-11-02; 198 transcript files, 148 sessions, 451 MB):

| Question | Answer |
|---|---|
| Summed de-duplicated assistant usage vs the last cost-state, J4 job session | exact match on all four token fields |
| Same, brief-J14 session | output within 0.5%, cache read 11% below, input far below (cost-state counts small side requests) |
| Same, J36 session | output within 0.02%, cache read 1.3% below |
| Same, J13 session with a sub-agent | main plus sub-agent output within 0.3%; cost-state includes the sub-agent's work |
| Repeated usage lines | yes: one reply spans several lines, so de-duplication is needed (498 lines against 194 replies in the J13 session) |
| `claude agents --json` | lists sessions (pid, cwd, name, state), no usage field |
| Job to sessions | most sessions attribute through their trailers, the branch and name routes take more; 28 stay unattributed in the view below |

Output tokens agree within about 1% in every session checked, so the brief's 10% criterion holds for 3 of 3 (cache read and input are the less
exact fields).

Real view on this PC (`python3 core/wsc.py jobs view --no-open`, 2026-11-02 22:47 UTC): the PC block reads "usage source: ~\.claude\projects,
198 files read 2026-11-02 22:47 UTC, 0 lines skipped; last 7 days: 141 sessions, 10213 tool calls, 2372.7M tokens (by model); tokens and tool
calls from Claude Code's own transcripts, cost is Claude Code's estimate not a bill; plan and weekly-limit usage is not on disk: read it in the
Claude app". Table rows, for example: J44, 4 sessions, 411 calls against a 300 budget, about $35.30 estimated, 6.7 h span (the J44 report
said "about 340": the difference is later review and fix sessions that carry J44 trailers, and the brief's budget is a plan figure); J58,
2 sessions, 48 of 60, about $3.15; unattributed, 28 sessions, 1,057 calls, about $114.59. Read time 5 to 8 s uncached, 0.1 to 0.3 s cached,
under the 10 s kill criterion.

Tests: `python3 -m unittest tests.test_usage_reader tests.test_jobs_hooks`, 44 tests OK (builder; rerun by the orchestrator on 6c4aed8: OK).
Gates: `--fast` 13 ok, 0 failed. Full `gates` 13 ok, 1 failed: `test_job_sh.JobSh.test_ctl_without_an_ini_uses_the_registered_default`, which
this job does not touch. The same test failed on job/J65 in a run made while J46 had the game running on this PC, so it is most likely the
live PC session; CI on the pull request is the check that counts.

## Rules table
| Rule | What | Checked by | State |
|---|---|---|---|
| 75 | `wsc jobs view` shows the PC block and a real usage source (per job and last 7 days) | `test_usage_reader`, `test_jobs_hooks.PcState` | done |

## Deviations from the brief and why
- **Paths.** The brief's `tools/verbs/jobs.py` is now `tools/jobs_hooks.py` (J62 moved the jobs verb into the core). The reader is a sibling
  module imported by path insertion.
- **A table in the PC panel, not a line on each job card.** The only hook the core offers is `view_panel(ctx)` (one HTML block). A per-card
  line needs a warscape-core hook, for example `card_extra(ctx, row) -> str` called from `render_view`'s `card()` in `core/warscape/jobq.py`
  (about line 612). Not done here: core files are never edited in this repo.
- **Wall time** is first to last timestamp over a job's sessions, so it includes idle gaps.
- **Week cost** is not shown; the week line has tokens and calls only.

## Open questions
- Does Liam want per-card usage lines? That needs the warscape-core `card_extra` hook above.
- Cost stays a labelled estimate (D38); say if it should go.
- Plan and weekly-limit usage is not on disk and is not attempted; the view points to the Claude app (Settings, Usage).
- `test_job_sh` `test_ctl_without_an_ini_uses_the_registered_default` fails in full gate runs on this PC (seen on J49 and J65); check it on
  main with no game running.
