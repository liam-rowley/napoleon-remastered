# J38: Release packaging, install and support

Phase 6, designed now and grown with each feature. Build the release machinery for what exists today (the proxy DLL, stock DXVK, the
shipped ini) so that every later feature job adds one component row instead of new packaging work: a player installer that needs no
repo, Python or Git Bash, a byte-exact uninstall, a repair and a check, a support bundle, `LICENSES.txt`, release values for every config
key, and versioned releases with generated notes. Target: Liam builds a release folder from a clean checkout with one command, runs
`Install.cmd` on the real game folder, plays, runs `Uninstall.cmd`, and the folder is identical to the pre-install snapshot (D25).

Model: Sonnet (medium). Python, PowerShell and docs; no DLL change, no reverse engineering. Budget about 150 tool calls; at the cap,
stop, commit, report what is left. Subagents are not needed. Waiting belongs to the harness (`job.sh`, the acceptance runner): block or
background inside one call, never poll. PC needed: yes, one sitting with Liam present (see PC test).

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J38`). Read `docs/DECISIONS.md` (D2, D13, D14, D23, D25, D30), `docs/plans/PLAN.md` phase 6, and
  the J1 and J12 reports (`jobs/J1/report.md` "Build, install, uninstall" and open question 1; `jobs/J12/report.md`: the proxy tools,
  the harness and `pc_deploy.py` now live in `core/`, so **never edit `core/`**: a generic change is a warscape-core PR and a pin bump).
- Prior art, read only (`/c/Users/liamr/repos/empire-remastered`, never edit or commit there): `rml_mod/docs/PACKAGING.md` (sections 3
  and 4: release layout, install, uninstall, repair, check; port the ideas, drop Empire's UI packs, exe byte patches and theatre
  maps), `LICENSES.txt` (a DRAFT; its text is evidence, not a source to ship unchecked) and `rml_mod/tools/install_watcher_task.ps1`.
- Reuse before writing: `python3 core/wsc.py find pc_deploy install uninstall snapshot kit pack`. Already there: `core/proxy/tools/pc_deploy.py`
  (kit with manifest and unique staged names, sha-checked install, exe-identity refusal, snapshot, backups, uninstall by move to
  `_to_delete`, `status`, `set`, `diff`), `core/proxy/tools/fetch_dxvk.py` (pins), `core/proxy/tools/wer/`, `proxy/napoleon/identity.json`,
  `registries/config_keys.jsonl`, `proxy/napoleon/napoleon_remastered.ini` (generated), `upscale/pc/install_packs.ps1` and
  `tests/test_mod_packs.py` (the UI art packs' install; J53 builds the play-test route on it, so do not duplicate it).
- Facts to check again before relying on them: `napoleon.exe.identity`, `napoleon.crash.toplevel_filter_replaced`, `napoleon.dxvk.*`
  (`registries/engine_facts/`), and `proxy/README.md` "PC install and uninstall", "DXVK", "Crash".

## Decisions already made for this job
- **D2 and D13 stand:** the exe stays vanilla on disk; the installer writes no exe bytes and refuses a non-vanilla exe. Steam is the
  only supported target. Nothing is deleted on the PC: removals are moves to a state folder, as in D25.
- **Where the code goes:** a new top-level `release/`, split `release/core/` (game-agnostic: builder, installer scripts, support
  bundle, licence generator) and `release/napoleon/` (component list, licence data, identity pin, names). `release/core/` is a core
  candidate (rule 76): add `'release/core': None` to `PROMOTIONS` in `tools/verbs/jobs.py` and name the promotion job in the report.
  **Do not touch `proxy/` or `harness/`** (rule 79 would demand 20 PC passes): a DLL or harness change is out of scope, stop and ask.
- **Player installer = PowerShell plus `.cmd` entry points** (`Install.cmd`, `Uninstall.cmd`, `Repair.cmd`, `Check.cmd`, `Support.cmd`),
  as in Empire's plan: the player has no Python. Find the game from the script's own location, the Steam registry key and
  `libraryfolders.vdf`, or `-GamePath`. The player-side state (snapshot, backups, `install.json`, moved-aside files) lives in a folder
  **outside the game folder** (D25), `%LOCALAPPDATA%\napoleon_remastered\`, not `C:\napoleon_remastered_pc`. Behaviour parity with
  `pc_deploy.py` is the contract: same checks (closed game, vanilla exe, staged sha256 before any copy), same record, same snapshot
  diff. A host test installs and uninstalls a synthetic game folder with both implementations and compares the resulting snapshots.
- **Release components are rows in `release/napoleon/components.json`** (id, target paths, source, size, sha256, optional, licence ids).
  Today: `proxy` (d3d9.dll, ini, the DXVK DLL and its conf, tools). Everything else waits for its job (see Deferred): a component is
  added by its own job, and the builder fails on an installed file no component owns.
- **Release values:** the shipped ini is generated from `release_value` (already the case). Add a gate (in `tests/`, run by
  `wsc gates`) that every `dev.*` and test key (`headless.test_*`) has a release value equal to off, `proxy.exe_guard` is 1,
  `proxy.exe_guard_force_mismatch` is 0, and the shipped ini equals the generated one. `proxy.minidump` (J1 open question 1) was
  already set to 2 by J3 (`jobs/J3/report.md` item 10): verify the built DLL's compiled default and the ini agree, and record it as
  closed. Decide, with the reason, whether the player ini lists the dev keys at all; if it omits them the defaults must equal the release values.
- **Dumps and personal data:** a minidump holds process memory, so the support bundle never includes dumps unless the player passes
  `-IncludeDumps`; it lists them either way. The bundle holds: `proxy.log`, `proxy.prev.log`, the ini, `EXE_MISMATCH.txt`, the install
  record, `Check` output, game and release versions, Windows version, GPU names. It redacts the Windows user name (replace the profile
  path with `%USERPROFILE%`), machine name and Steam ids, and never includes saves or the game folder listing beyond owned files.
  A host test plants a user name, machine name and Steam id in logs and finds none in the bundle.
- **Versioned releases:** version `MAJOR.MINOR.PATCH` in `release/napoleon/VERSION` (first: `0.1.0`), the folder and zip named
  `Napoleon Remastered <version>`, `manifest.json` with every file's target, size and sha256, the core tag and the DLL build id. Notes
  are generated, not written: components with sizes and licences, the done jobs since the previous release (from the jobs registry and
  git), the release value of every config key that is not off, open engine facts that bound the release (for example multiplayer
  untested), and the known limits. The builder refuses a dirty tree, a DLL whose build id is not the CI-built one (`build_id.py`), or an
  unpinned DXVK. It builds files only: **publishing (GitHub release, Nexus, ModDB) is Liam's call and is never done by this job.**
- **`LICENSES.txt` is generated** from `release/napoleon/licenses.json` (component, licence, copyright line, source URL, date checked,
  `shipped` flag, text). A gate fails a shipped component with no entry and an entry marked shipped with no component. Today's entry
  that ships: DXVK 3.1.1 (zlib/libpng, texts from the pinned tarball's LICENSE, already sha256-pinned in `fetch_dxvk.py`). Add the
  entries for what is coming as `shipped: false` with the licence name and source URL, checked against upstream and dated: RmlUi (MIT),
  FreeType (FreeType Licence, required credit line), Lua 5.1 (MIT), the UI font families (OFL: J37 records which), and the upscaling
  models (CC BY 4.0 credit lines from `jobs/J36/report.md`, which the J36 review did not re-check: read the release pages yourself).
  Say in `LICENSES.txt` and the report that it is not legal advice. The unofficial-mod statement and the licence of our own code are
  Liam's decisions (open questions); until he decides, those lines read "pending" and the builder warns.

## Deliverables
1. `release/core/build_release.py` (and `release/napoleon/` data): builds `Napoleon Remastered <version>\` and its zip from a kit,
   `manifest.json`, `installer\` scripts, `README.txt`, `LICENSES.txt`, generated `RELEASE_NOTES.txt`; `--check` verifies a built folder
   against its manifest. Registered as tools (header per `core/warscape/tools.py`), a `wsc` verb only if it fits the verb contract.
2. The PowerShell installer: `install`, `uninstall` (byte-exact against the snapshot, exit 0 only when identical), `repair`, `check`
   (hash every owned file; report missing, changed, foreign files at owned paths), all refusing while the game runs and on a non-vanilla exe.
   Repair covers the two real cases: **Steam Verify** (our files are additions, so they should survive; prove it, do not assume it) and
   **a game update** (the exe sha changes: the guard falls back to pass-through; the installer then reports "game updated, remaster is
   inactive until a build for this exe exists" and offers uninstall). Wire `Enable crash dumps.cmd` (the WER LocalDumps script from the
   kit) as an optional step that asks for admin, never forced.
3. `Support.cmd` / support bundle script as above, with its redaction host test.
4. The release-value gate, the licence data and generator with its gate, and the component-ownership check.
5. Host tests for every pure part (manifest, component ownership, notes generation, redaction, snapshot parity, version rules), green
   in CI; `release/README.md` (short: build, install, uninstall, support; link, do not copy `proxy/README.md`).
6. Docs: `docs/DECISIONS.md` rows only for choices that are new (state folder, version scheme if not changed by Liam), appended.
   `proxy/README.md` is not edited (it is a DLL-adjacent doc owned by J1); link to it.

## PC test
One sitting with Liam present; ask before starting; the launches go through the watcher (`harness/README.md`), never `Napoleon.exe`.
a) Build the release folder; check it with `--check`. b) Run `Install.cmd` on the real game folder (snapshot first), then `Check.cmd`.
c) **Steam-update safety net:** with the release DLL, force the pass-through path (`proxy.exe_guard_force_mismatch=1`) and reach the
main menu: notice file, first-difference line, no engine memory touched (patch count 0). If `layout.py` lets a scratch adapter carry a
different pinned identity, also build a scratch DLL (never in the release folder) and run it on the real exe; otherwise say in the
report that only the forced path was run on the PC and the host tests cover the rest. Never alter the real exe. d) Saves: load a save
made on vanilla and a save made with the mod installed (`saves/napoleon/load_save.sh`, ladder A unchanged), mod installed and after
uninstall; both load, vanilla save sha unchanged. e) Run the support bundle, open it, confirm no personal data. f) `Repair.cmd` after
deleting one owned file, then `Uninstall.cmd`: snapshot diff identical, `Check` clean. Evidence: dated run report under
`release/runs/<date>_j38pc/` (logs, listings, no screenshots needed), run ids in the report, `engine_facts` rows for what was newly learned.

## Deferred (say so in the report; do not build now)
- The UI art packs and the RmlUi host, fonts and shader components: each arrives with its own job (J53, J30, J37 and later) and adds a
  `components.json` row, a licence entry and a clause in the release smoke test. J53 owns the play-test install of the J36 packs; J38
  only makes sure its route can be listed as a component later.
- The in-game "mod settings", a chain-load option for other d3d9 wrappers, languages other than English (D14) and multiplayer checks.

## Kill criteria
- The PowerShell uninstall cannot reproduce the pre-install snapshot byte for byte after 3 honest attempts: stop, report the diff, do
  not weaken the check.
- A launch crashes or hangs with the installed release (any crash or hang, even once): stop, collect WER dumps and the log, report;
  do not relaunch to see if it recurs.
- Any step needs a change in `proxy/`, `harness/` or `core/`: stop and ask, listing the change.
- Over about 150 tool calls, or a second PC sitting needed: stop, commit, report what is left.

## Open questions (for Liam; write the conservative reading and flag it in the report)
**Settled by Liam 2026-11-01 (D38):** 1: "Napoleon Remastered" and `0.1.0` stand. 3: the PowerShell installer with parity tests stays. 2 is still open (Liam's call): keep both "pending" and the builder warning.
1. Name and version scheme: "Napoleon Remastered", `0.1.0`, as above.
2. The unofficial-mod statement and the licence of our own code (Empire's draft left both pending).
3. Does the PowerShell installer duplicating `pc_deploy.py`'s logic stay, or should a later core job give the installer a Python-free
   route (for example a frozen exe)? Parity tests keep them aligned meanwhile.

## Finish
Write `jobs/J38/report.md`: what was built, how to build, install, uninstall and get support, the PC evidence with run ids, the
Deferred list, deviations from this brief and why, open questions (headings `## Deviations` and `## Open questions`). Then
`wsc reg set jobs J38 status=review report=jobs/J38/report.md`.
