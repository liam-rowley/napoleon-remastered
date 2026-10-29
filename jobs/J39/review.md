# Review of J39 (Job viewer launches Claude Code sessions)

## Round 1 (2026-10-29, branch `job/J39` at abd86a5)

Reviewer: a fresh Opus chat (session `2e933838-7ec2-4091-9d20-692c4ee7f3c4`) that built none of the branch (builder:
`dd229d41-d433-4777-8493-9f55d985d709`). Checked against `jobs/J39/brief.md` and `jobs/J39/report.md`.

**Verdict: merge.** Every deliverable is present and follows the brief's decisions:
- one readiness rule (`not_ready`) used by `pick_next`, `pick_review`, `--id`, the buttons and the server
- `next --id` and `review --id` with exit-1 refusals
- the server's checks in the brief's order: token, Origin and Host, content type, id and action, readiness, cap, launch
- the D15 cap fails closed, with a lock across cap and launch
- no permission flag, and prompts written only by the server
- copy mode on the written page
- seams for every external call, and the tests the brief lists

The report names its deviations and why: the builder ran on Opus, the browser clicks went through a scratch client because Chrome
was not connected, and no review button could be clicked live. I fixed two should-fix items on the branch.
`claude --bg` itself has never run from the server, as the brief required. The report says so, and the brief's kill criterion
covers it if Liam's first click blocks.

### Machines
- `wsc gates` locally (Windows, this worktree): 11 ok, 1 warn (`hooks`: the worktree's absolute `core.hooksPath`, not this job), 0
  failed; 144 host tests, then 145 with the test added below.
- **CI was red, and the report did not say so.** The `gates` workflow failed on the branch's last three pushes (runs 40926693022,
  40927224019, 40927617902) at `test_jobs.Buttons.test_copy_mode_and_served_mode`. The report says only "CI runs on the pull
  request". Fixed below.

### Fixed on the branch
1. **should-fix, `tests/test_jobs.py` (`test_copy_mode_and_served_mode`): the test failed on Linux CI.** It passed
   `root='C:\\repo'`. On Linux, `Path('C:\\repo').as_posix()` keeps the backslash, so the page said `cd "C:\repo"` and the test
   expected `cd "C:/repo"`. To see it fail: any of the three runs above. Fix: the test uses `/repo`, which is POSIX on every host
   (commit 7155542).
2. **should-fix, `tools/verbs/jobs.py` (`_claude`, `start_session`): sessions started in `wsc`'s cwd, not the repo root.** The
   brief says the command runs in the repo root. `subprocess.run` had no `cwd`, and `wsc` finds the root by walking up from the cwd
   (`core/warscape/repo.py`). Run from `tools/`, the server would have started the session in `tools/`, where the prompt's
   `python3 core/wsc.py` does not exist. Fix: `start_session(argv, root)` passes `cwd=root`, and a test (`StartSession`) checks
   the cwd and the argv with `subprocess.run` faked (commit 869e431).

### Report errors (left as they are: a reviewer never edits the report, and CI's `policy` check enforces it)
- `jobs/J39/report.md:82`: the evidence names commit `d02c56b`. That is a pre-amend object and is not on the branch. The commit
  it means is `57c83a3`.
- `jobs/J39/report.md:3,69,87`: the report dates itself and its checks 2026-10-30. The commits are dated 2026-10-29, around 18:00
  UTC.

Neither changes what was built.

### Later
- `tools/verbs/jobs.py:680`: the written page (plain `jobs view`) now fetches every job branch (`branch_rows`) to place the
  Review buttons. Before, it only ran `ls-remote`. It is slower and needs the network, unless you pass `--offline`. The brief did
  not ask for this, but it is the only way to show a correct Review button, so I left it.
- `tools/verbs/jobs.py:638`: under `ThreadingHTTPServer`, two concurrent requests (a reload during a click) run `git fetch` into
  the same refs at once. One can fail on a ref lock and answer 500 or 503. Retrying the click works. If it bites, a lock around
  `snapshot()` fixes it.
- `tools/verbs/jobs.py:560`: the same-name guard and the cap count only `state == "working"`. A launched session that stops to
  wait for a permission prompt may not read as `working`, because the session runs under Liam's settings with no bypass. A second
  click could then start a duplicate before the session pushes its `job/` or `brief/` branch. Check what `state` such a session
  shows after the first real launches. If it is not `working`, count sessions with the same name in any state started in the
  last hour.
- `tools/verbs/jobs.py:460`: `start_session` takes the first 8-hex word of stdout as the id, and stdout's shape is unconfirmed. Fix
  the regex once Liam's first click shows the real output.
- Report's open question on `CLAUDE_CODE_*` variables leaking into a session launched from a server started inside Claude Code:
  agreed. Strip them in `_claude` if anyone runs `--serve` from an agent. Today it is meant for Liam's own terminal.
- Report's open question on **Stop**: worth a follow-up row once launch is proven on a real click.
