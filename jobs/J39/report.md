# J39 report: Job viewer launches Claude Code sessions

2026-10-30, session dd229d41 (Opus 5.5 at effort medium; see Deviations), branch `job/J39`.

## What was built
All of it is in `tools/verbs/jobs.py` and `tests/test_jobs.py`. The server section is 148 lines, so there is no second module.

- **One readiness rule: `not_ready(action, jid, by, branches, on_branch)`.** It returns the reason, or None when the job can start.
  - **brief:** status `needs_brief`, every `depends_on` done, no `brief/<id>` branch.
  - **build:** status `queued`, every `depends_on` done, no `job/<id>` branch.
  - **review:** a `job/<id>` branch whose row (read on that branch) says `review`, and no `jobs/<id>/review.md` on it.
  - An id with no row on main is refused for every action.
  - `pick_next`, `pick_review`, `--id`, the page's buttons and the server all call it. `pick_next` keeps its waiting text. The 16
    existing tests pass unchanged.
- **`branch_rows`:** the per-branch fetch and row read, taken out of `jobs review`. The review path, the view and the server use it.
- **`jobs next --id J<n>` and `jobs review --id J<n>`.**
  - For a ready job they print the same steps as the plain verb. `build_steps`, `brief_steps` and `review_steps` are now functions.
  - Otherwise they exit 1 with `jobs: <reason>` on stderr: unknown id, wrong status, dependencies not done, branch on origin,
    already reviewed.
- **The page.**
  - Each card gets a **Write brief**, **Implement** or **Review** button where the rule allows it.
  - Written page (copy mode): the button copies `cd "<repo>"; claude --bg --name J<n>-<action> --model <m> --effort medium "<prompt>"`.
    When the clipboard is refused, it shows the command in a selectable textarea instead.
  - Served page: the button posts `{id, action, token}` and shows the answer inline: green when started, red when refused.
  - The look, the filter, the Markdown rendering and the dark mode are unchanged. The new styles use the existing colour variables.
- **`jobs view --serve [--port N] [--dry-run] [--no-open]`.**
  - The server is `JobServer`, a `ThreadingHTTPServer` on 127.0.0.1, port 0 by default.
  - `GET /` renders the page fresh on every request, from the working tree, `git ls-remote` and the job branches. It returns 403 to
    any other `Host`, so a DNS-rebound name never sees the token.
  - `POST /launch` checks, in this order:
    1. the token, compared with `secrets.compare_digest`: 403
    2. `Origin` and `Host`: 403
    3. the content type is `application/json`: 415
    4. the id is a row and the action is known: 400
    5. readiness against a fresh snapshot: 409
    6. a working session with the same name (case-insensitive): 429
    7. 2 or more `state == "working"` sessions (D15): 429, naming them
    8. `claude` on PATH: 503
    9. the launch, or the argv on `--dry-run`

    When `claude agents` fails, the server refuses with 503 (fail closed). A lock covers steps 6 to 9, so a double click cannot get
    past the cap twice. The body is limited to 4 KB.
  - The prompts and the argv are written by the server (`PROMPTS`, `launch_argv`). No permission flag is ever passed.
  - Model: `sonnet` for a brief, the row's model for build and review.
- **Seams.** `JobServer(snapshot, agents, launch, which, ...)`. The real implementations are `list_agents` and `start_session`.
  Both run `claude` with stdout and stderr in temp files, not pipes, so a session left behind holding the handles cannot block the
  call. On Windows they also pass `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`, so Ctrl+C on the server or closing its console
  does not reach the session.
- **Tests:** 12 new, 28 in all in `tests/test_jobs.py`.
  - The readiness rule: each launchable case and each refusal.
  - `--id` on the command line: an unknown id, a done job, and review.
  - Buttons on the right cards, with and without `on_branch`. Copy mode with its exact command. Served mode with the token.
  - Real servers on port 0 in threads:
    - the exact argv for all three actions
    - the page is served only to its own `Host`
    - refused: a bad or empty token (403), a foreign `Origin` (403), a form content type (415), an unknown id or action (400)
    - unready jobs get 409
    - the cap gives 429 and names the sessions; finished sessions are not counted
    - a same-name session gives 429
    - a failing `claude agents` gives 503, and a missing `claude` is refused
    - `--dry-run` does not call the launcher
- **Prose:**
  - the `jobs.py` header (`usage`, `when`, the doc paragraph)
  - the `wsc.jobs` tools row, refreshed with `wsc reg add tools tools/verbs/jobs.py`
  - the README line for `registries/jobs.md`
  - the CLAUDE.md "Jobs" line

## The claude CLI facts, as checked
Checked 2026-10-30 with Claude Code 2.1.312 on Liam's PC. Both hold as the brief states them.
- `claude --help` lists `--bg, --background`, `-n, --name`, `--effort`, and `agents`, `attach`.
- `claude agents --json` prints an array of `{pid, id, cwd, kind, startedAt, sessionId, name, status, state}`:
  - `status` is `busy` or `idle`
  - `state` is `working` or `done`
  - finished sessions stay in the list
  - `startedAt` (epoch ms) is not in the brief, but is there
- Session names are free text that people type, for example `j7 brief`. That is why the same-name check ignores case.
- `claude --bg` itself was not run, because the brief says no real session. What it prints is not confirmed. `start_session` takes
  the first 8-hex or UUID token from stdout and falls back to the whole stdout.

## Evidence
- Commits on `job/J39`:
  - `d02c56b`: rule, `--id`, buttons, server
  - the tests and prose commit
  - this report commit
- `wsc gates`: 11 ok, 1 warn (`hooks`: this worktree's `core.hooksPath` is an absolute path, set before this job), 0 failed;
  `tests` 144 host tests passed. CI runs on the pull request.
- Live check, 2026-10-30, against the real queue and origin:
  - **The real server**, `python3 core/wsc.py jobs view --serve --dry-run --no-open --port 8765`, read the live
    `claude agents --json` for the cap:
    ```
    buttons on the page: J15:build J16:build J18:build J21:brief J22:brief J31:brief J36:brief
    POST J15 build -> 429 refused: 2 sessions are working (j13 status brief, j39 queue requirements); D15 allows 2 at once
    POST J21 build -> 409 refused: J21 is needs_brief, not queued
    POST J1 build -> 409 refused: J1 is done, not queued
    ```
  - **The same server with this session left out of the count.** This session was one of the two working ones, so the cap refused
    every argv click. To show the argv, a scratch script built the same `JobServer` and dropped only this session's `sessionId` from
    the `claude agents` list:
    ```
    POST J18 build -> 200 dry run, would start: C:\Users\liamr\.local\bin\claude.EXE --bg --name J18-build --model sonnet --effort medium "Pick up job J18: git pull, then run python3 core/wsc.py jobs next --id J18 and follow it."
    POST J36 brief -> 200 dry run, would start: C:\Users\liamr\.local\bin\claude.EXE --bg --name J36-brief --model sonnet --effort medium "Write the brief for job J36: git pull, then run python3 core/wsc.py jobs next --id J36 and follow it."
    POST J39 review -> 409 refused: J39 is queued on job/J39, not review (no report yet)
    POST J5 review -> 409 refused: J5 is done on job/J5, not review (no report yet)
    ```
    The J5 line showed a wording bug: "(no report yet)" was printed for a done job. It is fixed: the note is now added only when the
    branch row is `queued`.
  - **The written page**, `jobs view --no-open --offline`, is in copy mode (`const SERVE = null`). The J15 button holds
    `cd "C:/Users/liamr/repos/napoleon-remastered/.claude/worktrees/job-J39"; claude --bg --name J15-build --model opus --effort medium "Pick up job J15: ..."`.
  - **`--id` on the real queue:**
    - `next --id J15` printed J15's build steps
    - `next --id J39` gave `J39 (queued): in progress on job/J39`, exit 1
    - `next --id J1` gave `J1 is done, not queued or needs_brief`, exit 1
    - `next --id J99` gave `not a row`, exit 1
    - `review --id J39` gave `not review`, exit 1

## Deviations from the brief, and why
- **The model.** The brief says Sonnet. This session ran on Opus 5.5 at effort medium, because Liam started it with "pick up j39"
  in an Opus session rather than from a Sonnet launch.
- **The live check was not clicked in a browser.** The Claude in Chrome extension was not connected. The checks above ran
  a scratch client (`click.py`, kept outside the repo), which does what the page's script does: it GETs the page, reads the token and the buttons from the HTML, and
  POSTs `/launch` with the same `Origin` and content type. The in-browser parts, copying to the clipboard and showing results on the
  card, are not tested live. Liam's first click covers them.
- **No Review button live.** No job branch was waiting for review, so the review argv is shown only by the tests (exact argv).
- **The cap was satisfied by leaving this session out of the count** for the argv clicks, as described in Evidence. The real
  server's own answer was the 429.
- **The cap's order.** The same-name check runs before the count check, so a double click gets the more specific message. Both are
  429, as the brief asks.

## Open questions
- Should the server also offer **Stop** (`claude stop <id>`) and show each job's running session on its card?
- `claude --bg` has not been started from the server. Whether it returns at once when started from a Python subprocess with
  `CREATE_NO_WINDOW`, and what it prints, is confirmed only by Liam's first real click. If it blocks or prints no id, the kill
  criterion applies: drop `--serve` and keep the copy buttons.
- The launched session inherits the server's environment. When the server is itself started inside a Claude Code session, that
  includes `CLAUDE_CODE_*` variables such as `CLAUDE_CODE_SESSION_ID`. Should `start_session` remove them? It is meant to be run
  from Liam's own terminal.
- Every `GET /` fetches each job branch (`branch_rows`), so a reload takes a few seconds with many branches. Is that acceptable, or
  should the page cache for a minute?
