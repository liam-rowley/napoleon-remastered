# Napoleon: Total War Remastered: rules for every chat and agent

**The repo is the single source of truth.** If it isn't in the repo, the next chat can't see it and it doesn't exist.

## Before you start
1. `git pull`. Read `README.md`, `docs/DECISIONS.md`, and the plan doc for your area (`docs/plans/`).
2. Look things up before rediscovering them: the registries (tools, scenarios, assets, UI elements, engine sites, config keys,
   hotkeys, engine facts) once they exist (`docs/plans/PLAN.md` section 3). Until then, `empire-remastered` holds the evidence:
   `docs/learnings/` and `docs/plans/PIPELINE_V2.md`. Napoleon is the same engine lineage, but every Empire fact about the exe,
   shaders or Lua API is checked again on Napoleon before it is relied on.

## The core (`core/`, warscape-core pinned at a tag)
- Clone with `git clone --recurse-submodules` (or `git submodule update --init` after a plain clone); set the hook once per clone:
  `git config core.hooksPath core/.githooks`. Agent sessions attach `liam-rowley/warscape-core` too (read is enough here).
- Everything goes through `python3 core/wsc.py <verb>`: `find <words>` searches every registry, `reg add|set|render` changes them,
  `gates` runs the checks CI runs (`--fast` is what the pre-push hook runs). Never edit a generated `registries/*.md` view.
- **Never change files inside `core/`.** A change the game needs goes to warscape-core as a PR and arrives with a new tag
  (`core/docs/CONSUMING.md`); the `core_pin` gate fails on local edits.

## While you work
- Work on a branch; commit and push after every meaningful step. `main` changes only by a merge Liam (or the orchestrator, once
  there is one) approves.
- **A learning becomes code first.** When something bites (a timing, a trap, a wrong default), fix it in the tool, its default, a
  guard or a gate so the next agent cannot hit it. Write prose only when it cannot be coded, and then into the doc that owns the topic.
- **Exe stays vanilla on disk** (D2). Runtime patches and detours go in the proxy DLL, every engine address in the engine-sites
  registry with its anchor bytes, behind the exe-identity guard.
- **The PC game folder is a deploy target.** Change the repo, then sync with a sha-checked copy. Experiments on the PC live under a
  `_scratch\<you>\` folder; anything worth keeping comes back to the repo. Never run git in the game folder.
- **Reuse before you write.** Search the tools registry first; extend an existing tool or CLI verb rather than adding a near-duplicate.
  Every tool is committed, has a header (purpose, usage, when to use) and a registry row.
- **"Verified" carries a date and a run id**; an undated "verified" means nothing.
- **One owner per topic.** When a fact changes, grep for the old claim and fix every living copy. Keep docs short: link, don't copy.
- Windows-safe names only: no CON/PRN/AUX/NUL/COM1-9/LPT1-9, no `<>:"|?*`, no trailing dot or space, no names differing only in case.
- Never edit generated copies: the claude.ai Project docs, review pages and anything a generator writes. Change the source and regenerate.

## Usage (D15)
Sonnet medium by default; Opus only with a reason in the brief (reverse engineering, shaders, DLL, crashes, independent checks);
at most 2 agents at once; every job brief states a call budget and a kill criterion; waiting and polling belong to the harness, not
to an agent making repeated calls.
