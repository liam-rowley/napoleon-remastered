# J39: Job viewer launches Claude Code sessions

Queue tooling. The `wsc jobs view` page gets buttons that start a background Claude Code session for a job:
- **Write brief** on a ready `needs_brief` row
- **Implement** on a ready `queued` row
- **Review** on a job branch waiting for review

The session shows in `claude agents` named after the job. Liam asked for this on 2026-10-29. It saves typing "pick up the next job" and
lets him choose which job, not only the next one.

Model: Sonnet (Python stdlib server and page changes on an existing verb with a test suite). Budget about 80 tool calls; at the cap,
stop, commit, report what is left. No subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J39`). Read `docs/DECISIONS.md` (D15, D16, D21, D30, D32, D33) and `docs/REVIEW.md`.
- Everything lives in `tools/verbs/jobs.py` (`pick_next`, `pick_review`, `lane`, `render_view`, `VIEW_PAGE`, `run`) and
  `tests/test_jobs.py`. Extend these and do not add a second module unless the server code alone passes about 150 lines. If it does,
  put it in `tools/verbs/jobs_serve.py` with its own header and tools row.
- The facts this design rests on (checked 2026-10-29 with Claude Code 2.1.312 on Liam's PC):
  - **`claude --bg [--name N] [--model M] [--effort E] "<prompt>"`** starts a background session, returns at once and prints the id
    that `claude attach`, `logs`, `stop` and `rm` take.
  - **`claude agents --json`** prints a JSON array of sessions with `id`, `sessionId`, `name`, `cwd`, `kind`, `status` (`busy` or
    `idle`) and `state` (`working` or `done`). Finished sessions stay in the list.

  Check both again before relying on them. When either one differs, record the difference in the report.
- **Why there is a server:** the page is a file opened from disk, and a page opened that way cannot start a program. A custom URL
  protocol would need a registry write per user and gives no way to return an error. A localhost server can check the request and
  answer it.

## Decisions already made for this job
- **One readiness rule.** Factor `pick_next`'s inner `ready()` into one function used by `pick_next`, the new `--id` and the server.
  Do the same for `pick_review`'s condition. A job is launchable for:
  - **brief:** status `needs_brief`, every `depends_on` done, no `brief/<id>` branch on origin
  - **build:** status `queued`, every `depends_on` done, no `job/<id>` branch
  - **review:** a `job/<id>` branch whose row says `review` and that has no `jobs/<id>/review.md`

  The page shows a button only where this rule allows it. The server checks again on every click, against fresh `git ls-remote`
  branches, because the page may be stale.
- **`jobs next --id J<n>` and `jobs review --id J<n>`.**
  - For a ready job, print the same steps the plain verb prints for that job.
  - Otherwise exit 1 with the reason (wrong status, the dependencies not done, a branch already on origin, already reviewed).
  - Without `--id`, nothing changes.
  - A launched session is told to run these, so it works on the job it was given, and the verb refuses it when the job stopped being
    ready.
- **The command.**
  - It runs as an argv list (no shell) in the repo root: `claude --bg --name J<n>-<action> --model <m> --effort medium "<prompt>"`.
  - Model: `sonnet` for brief (D15 default), and the row's `model` for build and review.
  - `claude` is resolved with `shutil.which`. When it is missing, refuse with that reason.
  - Never pass a permission-mode or skip-permissions flag. Sessions run under Liam's own settings.
  - Prompts, written by the server only. The page never sends text:
    - brief: `Write the brief for job J<n>: git pull, then run python3 core/wsc.py jobs next --id J<n> and follow it.`
    - build: `Pick up job J<n>: git pull, then run python3 core/wsc.py jobs next --id J<n> and follow it.`
    - review: `Review job J<n>: git pull, then run python3 core/wsc.py jobs review --id J<n> and follow docs/REVIEW.md.`
- **`wsc jobs view --serve [--port N]`.**
  - stdlib `http.server` (`ThreadingHTTPServer`), bound to `127.0.0.1` only, port 0 by default (the OS picks). It prints the URL,
    opens the browser unless `--no-open`, and runs until Ctrl+C.
  - `GET /` renders the page fresh on each request, from the working tree and `git ls-remote`, so a reload refreshes it.
  - `POST /launch` takes JSON `{"id", "action", "token"}`. Requests are checked in this order:
    1. The token is a `secrets.token_urlsafe` made per run and embedded in the served page. Wrong or missing: 403.
    2. The `Origin` must be the server's own origin, and the `Host` must be `127.0.0.1:<port>`: 403 otherwise.
    3. The content type must be `application/json`: 415 otherwise (a plain form post cannot set it).
    4. The id must be a registry row and the action one of `brief`, `build` or `review`: 400 otherwise.
    5. The job must pass the readiness rule: 409 with the reason otherwise.
    6. The D15 cap and the duplicate check: 429 with the names of the running sessions.
    7. Launch, and return the session id that `claude --bg` printed.
  - **D15 as code:** refuse when 2 or more sessions in `claude agents --json` have `state == "working"`. Also refuse when a working
    session already has the same name, so a double click cannot start two sessions on the same job. When `claude agents` fails, refuse
    (fail closed) and say why.
  - The page shows each answer inline on the card. A start reads `started J<n>-<action>: claude attach <id>`. A refusal shows the
    reason.
  - `--dry-run`: do every check, but return the argv instead of running it.
- **Without `--serve`** (the default page, unchanged otherwise), each button copies the full command line with
  `navigator.clipboard`. Where that fails, it shows the command in a selectable box. Then Liam can paste it into a terminal.
- **Testable seams.** The server takes the launcher (argv in, id out), the agent lister and the branch reader as functions, so the
  tests never start `claude` or reach the network.
- **Prose.** Update the `jobs.py` header (`usage`, `when`), its tools row and the README line for `registries/jobs.md`. CLAUDE.md
  "Jobs" gets one line: "the `wsc jobs view --serve` buttons start the same sessions".

## Deliverables
1. The shared readiness function, with `pick_next` and `pick_review` using it. The existing `tests/test_jobs.py` stays green unchanged.
2. `jobs next --id` and `jobs review --id`, with tests: a ready job, each refusal reason, and an unknown id.
3. The server and its tests in `tests/test_jobs.py`. Each test runs a real server on port 0 in a thread with fakes behind the seams:
   - the right token, origin and content type launch, and the argv is exact for each action
   - a bad token, a foreign `Origin` and a form content type are refused
   - an unready job gets 409
   - 2 working sessions give 429
   - a working session with the same name gives 429
   - a failing `claude agents` refuses
   - `--dry-run` returns the argv without calling the launcher
4. The page: buttons on the right cards only (tested on rendered HTML for each lane), copy mode when served statically, inline results
   when served. It keeps the existing look, filter and Markdown rendering, and works in both colour schemes.
5. A live check on the PC, pasted into the report:
   - `wsc jobs view --serve --dry-run` in the browser: one click per button kind shows the argv
   - one refused click on an unready job
   - `claude agents --json` read once for the cap

   Do **not** start a real session. Liam makes the first real click.
6. The header, tools row, README and CLAUDE.md lines above, with `wsc gates` green.

## Kill criteria
- `claude --bg` started from a Python subprocess without a console does not start a session, or blocks, for a reason you cannot fix in
  about 5 calls. Ship the readiness rule, `--id` and the copy buttons, drop `--serve`, and report the exact behaviour.
- The output of `claude agents --json` has no field that tells a running session from a finished one. Make the cap count every
  `kind == "background"` session started in the last 12 hours, and report it as a deviation.
- Anything would need a change in `core/` or in `empire-remastered`: stop and ask Liam.
- A security check from the list above cannot be made to hold in the stdlib server: stop and report. Do not ship an endpoint that
  starts sessions without it.

## Finish
Write `jobs/J39/report.md`. Cover:
- what was built, including the readiness rule as it now reads
- the `claude` CLI facts as checked, with the date
- evidence: commits, CI run ids and the live check output
- deviations from this brief and why
- open questions (for example: should the server also offer **Stop** through `claude stop <id>`?)

Then `wsc reg set jobs J39 status=review report=jobs/J39/report.md`.
