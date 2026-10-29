# Review of J6 (Empire to Napoleon diff)

## Round 1 (2026-10-29, branch `job/J6` at 600ee06)

Reviewer: a fresh Opus 5.5 Claude Code session on the PC (session `7971a56a-6060-49e0-9512-c471e5dfca14`) that built none of the
branch. Checked against `jobs/J6/brief.md`, `jobs/J6/report.md` and `docs/DECISIONS.md`. About 35 tool calls.

**Verdict: merge.**

### Machines
- CI on 512a8db (run 40895788310): `gates`, `proxy` and `harness-windows` succeeded; only `policy` failed, for the missing review
  and the `review` status (this file fixes both).
- Local `wsc gates` (Windows, Git Bash first on PATH): 11 ok, 1 failed. The two failures are `test_job_sh` (path separator) and
  `test_pc_deploy` (Windows process check). Neither touches J6 code, and both pass on Linux CI. The report's count of 10 was taken
  with the WSL `bash` first on PATH. Same root cause, a different symptom count.
- `wsc discovery check`: 6 area files valid, README current.

### Claims checked against evidence
- **Determinism.** I re-ran all six passes (`discovery/core/{packs,layouts,fonts,lua_api,shaders,exe}.py`) over the builder's
  extracts and the two installs. Every committed `discovery/diff/*.json` came out byte-identical.
- **Empire.exe not stock.** The 33 of 52 stock value bytes intact at their offsets is confirmed. The patch windows mask those
  value bytes (`exe.py` `signatures`).
- **Exe sizes and imports** in `napoleon.diff.exe.pe` match `exe.json`. Napoleon is 17,895,424 bytes, Empire 16,711,680.
- **Layouts.** No loose layouts under Napoleon `data\UI`: I counted 0 extensionless files there, which matches the layouts pass.
- **Shaders.** `shaders.json` records technique names per fx file, as the brief asks. The loose `*_scripted.lua` entry points are
  covered (`lua_api.py` row "loose entry points").
- **Function signatures.** Of the 1,191 unique function hits, 1,143 keep Empire's address order in Napoleon (48 inversions), so
  most hits are real matches and not noise.
- **Read only.** `empire-remastered` is clean (`git status`). In both games, nothing under `data\` has changed since 2026-10-29,
  and both exes are older than that (Napoleon 2026-10-24, Empire 2026-10-26). The only files in the game folders dated
  2026-10-29 are the Napoleon proxy deploy (`d3d9.dll`, `napoleon_remastered\dxvk`) and Empire's `rml_mod` watcher files. Neither
  comes from J6.
- **Facts.** The 16 `napoleon.diff.*` facts are dated and point at their area file. The inferences (V039 fields, candidates, J8
  flags, API surface) are `open`, and the byte-signature hits are not `engine_sites` rows, as the brief requires.

### Brief
All 8 deliverables are present. The deviations are named with reasons: no device VM, Empire read from the install, signatures
taken from Empire.exe bytes, V039 stopped at the kill criterion, and Lua compared against `engine_api.json`. No scope creep.
`proxy/tools/pack_list.py` was extended (`read_header`, `--ext`, `--under`), not duplicated. Its `read_index` output is
unchanged.

### Risk-first reading
I picked `discovery/core/exe.py`, because its candidates are what J9 starts from, and `extracted.py` / `pack_list.py`, which the
other jobs share. I read them in depth and skimmed the rest.

### Findings
**Blocker:** none.

**Should-fix, fixed by the reviewer** (commit 70dd12e on this branch):
1. `discovery/core/exe.py` `run_search`: 33 function signatures were classed `unique` although a different Empire function's
   unique hit is the same Napoleon address. 14 Napoleon RVAs were claimed this way. To see it, count `napoleon_rva[0]` over
   `class == unique` in the old `exe.json`. These hits are now class `shared`. A guard site and its own function annotation (same
   Empire VA) still count as one, so the 6 guard and 2 patch candidates are unchanged. Test:
   `test_two_signatures_on_one_address_are_shared_not_unique`. Fact `napoleon.diff.exe.function_candidates` is now 1,159 unique
   and 33 shared.
2. `discovery/core/exe.py` `main`: the "Empire exe is the stock build" row put Empire's on-disk sha1 in the **Napoleon** column of
   the README table. That row now carries both shas in the Empire column and `-` for Napoleon.

**Later (this repo):**
- **For J9.** `exe.py` `mask_for` treats any 4 consecutive bytes whose value falls inside Empire's image as an address,
  including across instruction boundaries. For example, `c7 87 84 00` in the shadow-sweep window gets masked. It also leaves a
  rel32 cut off at a window edge unmasked. The first over-masks (weaker, more `multiple` hits). The second can turn a real match
  into `none`. J9 should treat `none` as "not found this way", not "absent", and filter candidates by fixed-byte count:
  `32 - masked` is in `detail.signatures`, and 44 unique hits rest on 12 fixed bytes or fewer.
- **For J8.** Napoleon.exe imports `d3dx9d_40.dll`, the debug D3DX, where Empire imports `d3dx9_40.dll`. This is recorded in
  `napoleon.diff.exe.pe` but not flagged for J8. It could matter for shader compile cost and effect behaviour, and J8 should check
  it.
- **Lua pass.** `discovery/core/lua_api.py:36` and `tests/test_discovery_lua.py:108` open files without closing them
  (`ResourceWarning` noise in the gates output). Use `with open(...)`.

**Later (core):** none new. The report's "moves to the core" list stands.
