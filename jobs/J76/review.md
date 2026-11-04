## Round 2 (2026-11-04, branch job/J76 at 1eb89b1)

**Verdict: merge.**

All three round 1 findings were answered in `## Fix round 1` of the report and I checked each against the branch.
- **Blocker 1 (hard-coded path):** `tests/test_claude_hook.py:149` is now `REPO = ch.norm(ch.ROOT)`. Run 41817052172 is green on `gates` and `harness-windows`; `proxy` and `viewer` are skipped as unaffected.
- **Should-fix 2 (sibling exemption):** `tools/claude_hook.py:642-669` accepts a script only under this checkout or a `git worktree list` entry. The two `evil/` commands are corpus rows 80-81, both `deny`.
- **Should-fix 3 (writers):** curl/wget output flags and `perl -i` count as writes, with corpus rows. Remaining flags are listed as residuals in the hook header.
- **Later 4:** unchanged by design (CI's `policy` owns the own-review rule).

Local `tests.test_claude_hook` and `tests.test_claude_hook_corpus` pass (30 tests). Rule 79 does not apply (no `proxy/` or `harness/` change). No open findings.

## Round 1 (2026-11-04, branch job/J76 at 18db6b4)

**Verdict: merge after fixes.**

The hook work itself is strong: I replayed 25 further command shapes through the real `decide()` (wrapped and nested git, `--no-pager`/`-c` before `commit`, `--no-verify` on commit and push, `&>`, `python3 -c`, unexported `$D` taint, `sed -i`, `dd`, `install`, `ln`, `truncate`, `rsync`, PowerShell `Set-Content`, `taskkill`, `cmd /c start`, `git push origin :main`, `gh pr merge plan/...`) and all were denied; local `tests.test_claude_hook` and `tests.test_claude_hook_corpus` pass (30 tests; 0.12 ms per `decide()`, 52 ms per process round trip). Two required checks are red, though, and there is one bypass in the exemption.

### Blockers
1. **A test hard-codes the author's machine path, so both required checks are red.** `tests/test_claude_hook.py:149` sets `REPO = '/c/Users/liamr/repos/napoleon-remastered'` and `:224` runs `python3 proxy/tools/pc_deploy.py install ...` from it, expecting `None`. On the author's PC it passes only through the sibling-clone rule in `tools/claude_hook.py:644` (`under(p, parent)` is true because the path sits under `repos/`); on a CI checkout (`/home/runner/work/...`, `D:\a\...`) neither the checkout nor the parent rule matches, so the hook says "looks like a sanctioned script". Fails in `gates` (`test_reads_scratch_and_the_sanctioned_writers_pass`, run 41797921815) and in `harness-windows` (same test, same run). Fix: derive `REPO` from `ch.ROOT` (and use `core/proxy/tools/pc_deploy.py` in the fixture), then re-run both jobs. Gate coverage: the corpus claims "from the repo and from a worktree"; it should also be run from a path that is not the author's.

### Should-fix
2. **The sanctioned-script exemption accepts any sibling directory.** `tools/claude_hook.py:642-644`: a script is exempt if it ends in `proxy/tools/pc_deploy.py` or `harness/job.sh` and sits two levels under `ROOT.parent`. An agent can write such a file anywhere under `repos/` (not a protected root, so the hook allows it) and run it against the game folder. See it fail:
   `decide()` with cwd the worktree and `python3 /c/Users/liamr/repos/evil/proxy/tools/pc_deploy.py cp x "<Napoleon folder>"` returns `None` (allowed); `bash /c/Users/liamr/repos/evil/harness/job.sh "<Napoleon folder>"` likewise. Fix: accept a sibling only if it is a git worktree of this repo (its `.git` file points into this checkout's common dir, or it appears in `git worktree list`), and require the `core/` form (drop the bare `proxy/tools/` and `harness/job.sh` suffixes, which the brief does not name). Add both commands above to the corpus as `deny`.
3. **Writers that bypass the verb list.** `curl -o "<Napoleon folder>/a" http://x` and `perl -pi -e s/a/b/ "<Napoleon folder>/a"` are allowed. The brief's decision 5 names a verb list, so this is within spec, but neither is in the header's residuals. Add `-o/-O/--output` for curl/wget, `-i` for perl, and `Out-File`-style flags, or list them as residuals in the file header and `CLAUDE.md`.

### Later
4. `gh pr merge job/<id>` is allowed by design (the reviewer's D32 merge); the hook cannot tell a reviewer from the builder. The own-review rule stays with CI's `policy`. Nothing to change here, noted so nobody thinks the hook enforces it.

### Checked and fine
- Brief deliverables present: `tools/hook_parse.py` (new), per-unit rules, 247-row corpus (above the 107 floor), six settings deny rows, the screening wrapper with its tests, header/registry/`CLAUDE.md` updated, no change in `core/`, `harness/`, `proxy/` or `docs/DECISIONS.md`.
- Risk-first reading: the exemption and the git/launch/merge rules in `tools/claude_hook.py` (where a mistake lets a write reach the PC), and the settings wrapper (fail-open path); the parser I skimmed, covered by the corpus.
- Rule 79 does not apply (no `proxy/` or `harness/` change).

Round 2 should show the two required checks green.
