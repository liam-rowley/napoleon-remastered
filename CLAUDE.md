# Napoleon: Total War Remastered: rules for every chat and agent

**The repo is the single source of truth.** If it isn't in the repo, the next chat can't see it and it doesn't exist.

## Before you start
1. `git pull`. Read `README.md`, `docs/DECISIONS.md`, and the plan doc for your area (`docs/plans/`).
2. Look things up before rediscovering them: the registries (tools, scenarios, assets, UI elements, engine sites, config keys,
   hotkeys, engine facts) once they exist (`docs/plans/PLAN.md` section 3). Until then, `empire-remastered` holds the evidence:
   `docs/learnings/` and `docs/plans/PIPELINE_V2.md`. Napoleon is the same engine lineage, but every Empire fact about the exe,
   shaders or Lua API is checked again on Napoleon before it is relied on.

## Where agents run (D30)
- Claude Code on Liam's PC, started in this repo's folder, shell = Git Bash. No cloud sessions and no device bridge: tools read the
  game folder, the AppData folder and `C:\napoleon_remastered_pc` directly.
- Clones live side by side under `%USERPROFILE%\repos\` (`/c/Users/liamr/repos/` in Git Bash): `napoleon-remastered` (this repo),
  `empire-remastered` and, only when making a core change, `warscape-core`. **`empire-remastered` is read-only evidence: never
  edit, commit or push there from Napoleon work.** Bring it into a session with `--add-dir ../empire-remastered` when a job needs it.
- **The game is launched, killed and profiled only through the watcher** (`harness/README.md`, `core/harness/job.sh`), never by
  starting `Napoleon.exe` yourself: the watcher holds the game lock, the hang watchdog and the profile restore.
- One-time setup and its check: run `python3 core/wsc.py setup` (`--fix` for the safe fixes); every line says how to fix a failure.
- Every commit carries a `Claude-Session: <session id>` trailer: the `.claude/settings.json` hook refuses a `git commit` without it
  and names the flag, and `tools/pr_policy.py` refuses a job whose report or review has a commit without one.

## The core (`core/`, warscape-core pinned at a tag)
- Clone with `git clone --recurse-submodules` (or `git submodule update --init` after a plain clone); set the hook once per clone:
  `git config core.hooksPath core/.githooks` (the core's `hooks` gate warns until you do).
  The submodule is enough to read the core; a core change is made in a separate `warscape-core` clone beside this one.
- Everything goes through `python3 core/wsc.py <verb>`: `find <words>` searches every registry, `reg add|set|render` changes them,
  `gates` runs the checks CI runs (`--fast` is what the pre-push hook runs). Views are not committed (J55): `reg render` writes them to `_scratch/registries/`.
- Since J12 the core carries the proxy sources and tools (`core/proxy/src`, `core/proxy/tools`), the watcher kit (`core/harness/`) and the
  ESF tools (`core/saves/`); this repo keeps the adapters (`proxy/napoleon`, `harness/napoleon`, `saves/napoleon`). `python3 core/proxy/tools/layout.py`
  shows what the tools use.
- **Never change files inside `core/`.** A change the game needs goes to warscape-core as a PR and arrives with a new tag
  (`core/docs/CONSUMING.md`); the `core_pin` gate fails on local edits.

## Jobs (D16, D21): what Liam means by "pick up the next job" and "review the next job"
- The queue is the `jobs` registry (`registries/jobs/J<n>.json`, one file per job; status page: `python3 core/wsc.py jobs view`). Each job has a folder
  `jobs/<id>/` with `brief.md` (the full prompt), then `report.md` and `review.md`. A job in progress is a remote branch `job/<id>`.
  `wsc jobs check` (run by the `tests` gate) enforces the statuses, their files and the brief shape (`tools/verbs/jobs.py`).
- **"Pick up the next job":** `git pull`, then `python3 core/wsc.py jobs next`. It names the job and its steps, or the brief to write
  (on `brief/<id>`, then queue its merge on green CI: D33), or what every open job is waiting for. Say which job you took.
- **"Review the next job":** `python3 core/wsc.py jobs review` names the branch; follow `docs/REVIEW.md` on it. A `merge` verdict
  ends with the reviewer queueing the merge on green CI (D32); any other verdict is never merged.
- The `wsc jobs view --serve` buttons start the same sessions (`claude --bg`, named `J<n>-<action>`, one session per name; no count cap: D34).
- Never mark your own job `done`, and never review a job you built (CI's `policy` check refuses a review written by a session that
  wrote the report).
- **All work goes through the queue (D21).** The branch name decides what a pull request may change; the kinds and their files are
  the docstring of `tools/pr_policy.py`, which CI's `policy` check runs (run it locally before opening a pull request). Work Liam asks
  for that isn't in the queue becomes a `needs_brief` row on a `plan/` branch first. Reviewer fixes go on the job branch itself.
- **Rule 79 and history edits (J45):** the DLL build id is a hash of the DLL inputs' content (`core/proxy/tools/build_id.py`), so a reword,
  rebase or merge of `main` after the 20-pass run keeps the passes when it leaves those inputs unchanged; when `main` brings in a
  change to them, the branch needs a new run either way. Rebase or merge as you like.

## While you work
- Work on a branch; commit and push after every meaningful step. `main` changes only through a pull request: a job branch
  is merged by its independent reviewer on green CI (D32, `docs/REVIEW.md`), a `brief/` branch by its writer on green CI
  (D33); `plan/` and `meta/` branches by Liam (or the orchestrator, once there is one). End every job with a report: what was built, evidence
  (run ids), deviations from the brief and why, open questions (`wsc jobs check` checks the headings).
- **A learning becomes code first.** When something bites (a timing, a trap, a wrong default), fix it in the tool, its default, a
  guard or a gate so the next agent cannot hit it. Write prose only when it cannot be coded, and then into the doc that owns the topic.
- **Exe stays vanilla on disk** (D2). Runtime patches and detours go in the proxy DLL, every engine address in the engine-sites
  registry with its anchor bytes, behind the exe-identity guard. Guard: `pc_deploy.py` refuses an install on a non-vanilla exe and checks the
  sha after every install, uninstall and set; the watcher refuses a launch (`exe_check`); `pc_deploy.py status` and `wsc setup` report it.
- **The PC game folder is a deploy target.** Change the repo, then sync with a sha-checked copy (`pc_deploy.py`).
- **PC experiments live under `<state>\_scratch\<you>\`** (`job.sh scratch <you>`); anything worth keeping comes back to the repo. Guard: the
  hook (`tools/claude_hook.py`) denies shell writes into a game folder or the state folder elsewhere; `pc_deploy.py status` lists foreign files.
- **Never run git in a game folder.** Guard: the hook denies git there (cwd, `cd`, `-C`, `--git-dir`, `GIT_DIR`), the watcher refuses a script
  that runs git, and `pc_deploy.py status` and `wsc setup` fail on a `.git` in or above a game folder.
- **Reuse before you write.** Search the tools registry first; extend an existing tool or CLI verb rather than adding a near-duplicate.
  Every tool has a header and a registry row (`tools` gate; header format: `core/warscape/tools.py`).
- **"Verified" carries a date and a run id** (`verified_dates` gate for docs; structured fields in registries).
- **One owner per topic.** When a fact changes, grep for the old claim and fix every living copy. Keep docs short: link, don't copy.
- Windows-safe names only: the `windows_paths` gate is the rule.
- Never edit generated copies: the claude.ai Project docs, review pages and anything a generator writes. Change the source and regenerate.

## Usage (D15, D34)
Sonnet medium by default; Opus only with a reason in the brief (reverse engineering, shaders, DLL, crashes, independent checks);
no fixed cap on agents at once: Liam decides (D34); every job brief states a call budget and a kill criterion (`wsc jobs check`); waiting and polling belong to the harness, not
to an agent making repeated calls.
