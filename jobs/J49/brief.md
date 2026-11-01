# J49: Usage source for the PC jobs view (rule 75)

Phase 1, repo tooling. Rule 75 (`jobs/J5/rules.md`) wants `wsc jobs view`, when run on the PC, to show the PC state and a usage source.
J44 built the PC state (`pc_state` and `pc_block` in `tools/verbs/jobs.py`) but the usage half says `USAGE_SOURCE = 'none yet: no tool on the
PC can read Claude usage numbers'` (`jobs/J44/report.md`, Rules as they now stand, row 75 and the last open question). Target: the view
shows Claude usage per job (tokens and tool calls per model, with the source and the date it was read), read from what Claude Code
already writes on this PC, or, if that cannot be done reliably, a recorded reason and rule 75's usage half closed. No game code, no
DLL, no game launch.

Model: Sonnet, medium effort (D15). Python in this repo only (`tools/`, `tests/`); no core change, no game. PC: yes, but only to read
`~/.claude/` and run `claude` read-only commands; the game, the watcher and the lock are not touched. Budget about 70 tool calls; at
the cap, stop, commit, report what is left. Subagents are not needed. Waiting belongs to the harness: never poll.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J49`). Read `docs/DECISIONS.md` (D15, D34), `tools/verbs/jobs.py` (docstring, `USAGE_SOURCE`,
  `pc_state`, `pc_block`, `render_view`, `lane`/card rendering, `launch_argv`, `list_agents`) and `tests/test_jobs.py` (`PcState`).
- Rule 75's text is `jobs/J5/rules.md` row 75; its history is `jobs/J4/report.md` (row 75 "not done") and `jobs/J44/report.md`.
- Prior art, read-only, never edit or commit there: `/c/Users/liamr/repos/empire-remastered/orchestrator/tools/usage_tally.py` (it sums
  hand-written "Usage:" lines of reports; port the idea of reporting what is missing instead of guessing, not the report parsing) and
  `orchestrator/ready/rows/usage.json`.
- Search before writing: `python3 core/wsc.py find usage claude session jobs`. `tools.claude_hook` already reads the session id; a
  committed `Claude-Session: <id>` trailer is on every commit of a job branch (CLAUDE.md), so commits tie a job to its sessions.

## Target facts
Read on the PC 2026-11-01 while writing this brief (planning chat); check each again yourself and record them in the module header
with the date and the Claude Code version (`claude --version`):
- Session transcripts are `~/.claude/projects/<cwd-slug>/<session-id>.jsonl` (the slug is the working folder with separators turned to
  `-`, e.g. `C--Users-liamr-repos-napoleon-remastered--claude-worktrees-J13`). One JSON object per line.
- `type: "assistant"` lines carry `message.usage` (`input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `output_tokens_details.thinking_tokens`), `message.model` (e.g. `claude-opus-5-5`), `gitBranch`, `cwd`,
  `sessionId`, `effort`, `timestamp`, `requestId`. The same usage block repeated on several lines of one reply (3 lines in the one file
  I looked at): de-duplicate by `message.id` (else `requestId`) before summing, or tokens are counted 2 to 3 times.
- A `type: "cost-state"` line (`sessionId`, `totalCostUSD`, `totalDuration`, `modelUsage` per model with `inputTokens`, `outputTokens`,
  `cacheReadInputTokens`, `cacheCreationInputTokens`, `costUSD`) is written as the session goes; the last one is a ready per-session
  per-model total. Whether it includes sub-agent (sidechain) work, and whether it agrees with the summed assistant lines, is not known:
  step 1 finds out.
- `tools/verbs/jobs.py` documents `claude agents --json` (Claude Code 2.1.316): sessions with `state` working / blocked / done. Whether
  it prints any usage field is not known; do not guess flags, read `claude agents --help` and one real `--json` output.
- Background job sessions are named `J<n>-<action>` (`launch_argv`), so a job's sessions can be found by the transcript's `agentName` /
  `ai-title` / `gitBranch` (`job/J<n>`, `brief/J<n>`), and by the `Claude-Session` trailers on the job branch's commits.

## Decisions already made for this job
- **Source of truth is Claude Code's own local transcripts**, read-only. Never write under `~/.claude`, never copy a transcript into the
  repo, never print prompt or tool-result text: read only the structured fields above (usage, model, effort, branch, cwd, session id,
  timestamps). Nothing leaves the PC and nothing about usage is committed except tests' synthetic fixtures.
- **Report tokens and calls first; cost is a labelled estimate** (`totalCostUSD` is Claude Code's own figure, not a bill). Per job:
  sessions, assistant replies, tool calls (count the `tool_use` blocks, so the number is comparable with the brief's call budget),
  tokens by model (input, output, cache read, cache write), wall time from first to last timestamp, and the brief's budget next to the
  actual calls. State the source (`~/.claude/projects`, how many files read), the date and time it was read, and what could not be
  attributed.
- **Attribution to a job, in this order:** (1) the session id is in a `Claude-Session` trailer on a commit of `job/<id>` or
  `brief/<id>` (`git log --format=%(trailers:key=Claude-Session,valueonly)`); (2) the transcript's `gitBranch` is `job/<id>` or
  `brief/<id>`; (3) its name is `J<n>-<action>`. A session matching none is "unattributed" and its total is shown, never dropped or
  guessed. Sub-agents of a session count toward that session only if step 1 shows they are in its totals or its folder.
- **Fail soft, say so.** Off the PC, with no `~/.claude/projects`, or on an unreadable or odd line, the view says what was missing and
  keeps rendering (one skipped-lines count, no traceback). The view must stay fast: cache per-file results keyed by size and mtime in
  `_scratch/` (ignored by git), and read big files in a streaming pass, not into memory.
- **Reuse before writing:** extend `pc_state`/`pc_block` and the job cards in `tools/verbs/jobs.py`; put the transcript reader in one
  small pure module (functions take paths and return dicts, so tests use synthetic files) that `jobs.py` imports, with a tools-registry
  row and header (`tools` gate). If the verb loader forbids a sibling module, keep it in `jobs.py` and say why in the report.
- No new network call and no API key: this must not use the Anthropic API or a usage endpoint. If the only way to the numbers is an
  account usage page or an exported report, record that as the finding instead of automating a login (CLAUDE.md privacy rules).

## Deliverables
1. **Finding, first and cheap (step 1, at most about 15 calls).** On this PC: how many transcript files exist, what the assistant,
   `cost-state` and sidechain lines contain, whether summed deduplicated usage agrees with the last `cost-state` for 3 sessions (a job
   session, a brief session, one with sub-agents), whether `claude agents --json` or any other `claude` subcommand shows usage, and how
   a job maps to its sessions. Write the outcome as a short table in the report.
2. **The reader** (module or `jobs.py` functions): `usage_by_session(projects_dir)` and `usage_by_job(rows, sessions, trailers)` as
   described above, with the dedupe and the attribution order, returning the numbers plus `source`, `read_at`, `files`, `skipped`,
   `unattributed`.
3. **The view:** replace `USAGE_SOURCE` with the real source line in the PC block (with the totals for the last 7 days: PLAN section 3
   says the view shows "usage this week") and a small usage line on each job card that has sessions (calls actual / budget, tokens by
   model, cost estimate labelled as such). Off the PC the block stays hidden as today; with the folder missing it says why.
4. **Tests** in `tests/test_jobs.py` (or a new test file) with synthetic transcripts: de-duplication of repeated usage, per-model sums,
   tool-call counting, the three attribution routes and "unattributed", a corrupt line skipped and counted, a missing folder, the
   cache invalidating on a changed file, and a check that no prompt or tool-output text from the fixture reaches the rendered HTML.
   Update `PcState` for the new field; the existing tests stay green.
5. **Evidence on the real PC:** run `python3 core/wsc.py jobs view --no-open` here and quote the PC block and two job cards (a job
   with sessions, one without) in the report; compare one job's calls with its report's own "Calls" line (for example J44's "about
   340" or J58's) and say how far they differ and why.
6. **Docs:** the `jobs.py` docstring paragraph (what the usage numbers are, their source, the privacy rule), the tools-registry row, and
   a one-line correction of `USAGE_SOURCE` mentions elsewhere (`grep -rn "usage source"`). Close rule 75 in the report's rules table.
7. `python3 core/wsc.py gates` green.

## Kill criteria
- Step 1 shows the transcripts cannot give per-job numbers that match `cost-state` within about 10 percent for 2 of 3 sessions, or no
  reliable job attribution exists: stop building. Write the report with the evidence, set the view's usage text to say exactly what
  is and is not known and where Liam can read usage himself, and ask Liam before going further. That closes rule 75's usage half
  honestly; do not ship numbers you cannot defend.
- The reader needs more than about 10 seconds on this PC's `~/.claude/projects` even with the cache: stop and cut the scope to the last
  7 days or to the attributed sessions, and say so.
- Anything that would write under `~/.claude`, call an API, or print conversation text: stop and ask.
- Over about 70 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J49/report.md`: what was built, the step-1 finding table, the real-PC evidence, the tests and the gates result, deviations
from this brief and why, open questions (include: whether Liam wants cost shown at all, and whether account-level plan usage, which
Claude Code does not write to disk, is wanted). Then `wsc reg set jobs J49 status=review report=jobs/J49/report.md`.

## Open questions for Liam (the brief took the conservative reading)
- Tokens and tool calls are the headline; cost is an estimate. Say so if you want the cost left out or promoted.
- Plan or weekly-limit usage (what the Claude app shows) is not in the local files as far as I know; this job does not try to reach it.
