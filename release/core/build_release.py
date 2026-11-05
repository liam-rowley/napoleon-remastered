#!/usr/bin/env python3
"""Build and check a release folder: `Napoleon Remastered <version>\\` and its zip, from the repo, the CI-built DLL and the component rows.

purpose: build the player release folder (payload per component, manifest.json with every file's target, size and sha256, the installer scripts and .cmd entry points, README.txt, generated LICENSES.txt and RELEASE_NOTES.txt) and its zip from a clean checkout; --check verifies a built folder against its manifest; refuses a dirty tree, a component ini_set that turns a dev, proof or test key on (unless release.json allowed_dev_keys names it with a decision), a DLL whose embedded build id is not this tree's clean id (build_id.py, whole-token match) or is not backed by the ledger's 20 acceptance passes (--allow-dirty skips only that count), an unpinned DXVK, an external build output without a matching .json sidecar, or a rebuild of a version releases.json records with other content; --record writes the version, manifest sha256 and build id into releases.json
usage: python3 release/core/build_release.py [--out build/release] [--dll build/proxy/napoleon/d3d9.dll] [--external uiscale=DIR] [--no-zip] [--allow-dirty] [--record] [--rebuild-unreleased] | --check <release folder>
when: to make a release (one command, then Install.cmd on a PC); --record only when Liam says this build is the one (it records, it never publishes); --check on a built or unzipped folder before it goes anywhere; publishing is Liam's call and never done by it
not-a-verb: a release-builder script (release/core is a core candidate, rule 76); game facts are in release/napoleon (components.json, release.json, licenses.json, VERSION), not here
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from fnmatch import fnmatchcase
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import gen_licenses  # noqa: E402

VERSION_RE = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')
INSTALLER = HERE / 'installer' / 'rr.ps1'
CMDS = {   # entry point -> installer verb (the player double-clicks these; no Python, Git or repo)
    'Install.cmd': ('install', ' -OfferDumps', 'Installs Napoleon Remastered into your Napoleon: Total War game folder.'),
    'Uninstall.cmd': ('uninstall', '', 'Removes it and checks the game folder against the pre-install snapshot (files a game update changed are listed apart).'),
    'Repair.cmd': ('repair', '', 'Puts back missing or changed files (for example after Steam "Verify integrity of game files").'),
    'Check.cmd': ('check', '', 'Checks every installed file and the game exe.'),
    'Support.cmd': ('support', '', 'Makes a support bundle (logs and versions, personal names removed) to send when something goes wrong.'),
    'Clean.cmd': ('clean', '', 'Frees the disk space of the files installs, repairs and uninstalls moved aside (lists them and asks first).'),
}


def sha256_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---- version and notes (pure) -------------------------------------------------------------------------------------------------------
def parse_version(v):
    m = VERSION_RE.match(v.strip())
    if not m:
        raise ValueError(f'version {v!r} is not MAJOR.MINOR.PATCH (no leading zeros, no suffix)')
    return tuple(int(x) for x in m.groups())


def is_published(r):
    """A releases.json entry Liam handed out: published true, or a hand entry from before --record (no manifest_sha256)."""
    return bool(r.get('published', 'manifest_sha256' not in r))


def version_problems(version, releases):
    """The version is well formed and higher than every recorded release (releases: [{version, jobs_done, ...}]); the same version as an entry
    --record wrote and nobody published yet passes here, and record_problems decides on its content (J81)."""
    try:
        v = parse_version(version)
    except ValueError as e:
        return [str(e)]
    prev = [parse_version(r['version']) for r in releases if r['version'] != version or is_published(r)]
    if prev and v <= max(prev):
        return [f'version {version} is not higher than the last recorded release {".".join(map(str, max(prev)))} (release/napoleon/releases.json)']
    return []


def content_sha256(man):
    """The manifest's sha256 without its build time (created_utc): two builds of one commit with the same inputs give the same value (J81)."""
    m = {k: v for k, v in man.items() if k != 'created_utc'}
    return sha256_bytes(json.dumps(m, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def record_problems(version, csha, releases, rebuild_unreleased=False):
    """A recorded version is rebuilt only with the content it was recorded with; --rebuild-unreleased overwrites an entry not yet published, never a published one."""
    for r in releases:
        if r['version'] != version or r.get('manifest_sha256') == csha:
            continue
        if is_published(r):
            return [f'{version} is published (release/napoleon/releases.json) with another content: bump `VERSION`']
        if not rebuild_unreleased:
            return [f'{version} is recorded with another content: bump `VERSION` or pass `--rebuild-unreleased`']
    return []


def record_release(rpath, entry, rebuild_unreleased=False):
    """--record: write entry (version, manifest_sha256, build_id, ...) into releases.json, newest last; a published entry is never rewritten."""
    rpath = Path(rpath)
    data = read_json(rpath) if rpath.is_file() else {'releases': []}
    errs = record_problems(entry['version'], entry['manifest_sha256'], data['releases'], rebuild_unreleased)
    if errs:
        raise SystemExit('build_release: refusing: ' + errs[0])
    old = next((r for r in data['releases'] if r['version'] == entry['version']), None)
    if old is not None and is_published(old):
        return old
    data['releases'] = sorted([r for r in data['releases'] if r['version'] != entry['version']] + [entry], key=lambda r: parse_version(r['version']))
    rpath.write_bytes((json.dumps(data, indent=1) + '\n').encode('utf-8'))   # LF on every OS, as committed
    return entry


def jobs_since(rows, releases):
    """[(id, title)] of jobs done now and not in the latest recorded release, in job-number order."""
    seen = set(releases[-1]['jobs_done']) if releases else set()
    done = [r for r in rows if r.get('status') == 'done' and r['id'] not in seen]
    return sorted(((r['id'], r.get('title', '')) for r in done), key=lambda t: int(re.sub(r'\D', '', t[0]) or 0))


def human(n):
    for u in ('bytes', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB':
            return f'{n:.0f} {u}' if u == 'bytes' else f'{n:.1f} {u}'
        n /= 1024


def not_off(v):
    return v not in (False, 0, '', None)


# ---- config keys and the player ini (pure) ------------------------------------------------------------------------------------------
def omitted(key, rel):
    pi = rel['player_ini']
    if key['id'] in pi.get('keep_ids', []):
        return False
    return key['id'] in pi['omit_ids'] or any(key['id'].startswith(p) for p in pi['omit_prefixes'])


def player_ini(keys, rel, ident, ini_set=None):
    """The player's ini: the keys a player may change at their release values, plus the components' ini_set keys. Omitted keys must have
    default == release value (value_problems), so the DLL's built-in default is what the player gets."""
    sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
    import gen_tables
    lines = [f"; {ident['config_file']} - {rel['product']} settings. GENERATED by the release builder from registries/config_keys.jsonl (release values).",
             '; A key that is not listed here takes the built-in default. Unknown keys are logged and ignored. Edit it with Notepad while the game is closed;',
             '; Repair.cmd keeps your edits.']
    sections = {}
    for k in sorted(keys, key=lambda k: k['id']):
        if not omitted(k, rel):
            sec, name = k['id'].split('.', 1)
            sections.setdefault(sec, []).append((name, k['description'], dict(k, default=k.get('release_value', k['default']))))
    byid = {k['id']: k for k in keys}
    for kid, v in sorted((ini_set or {}).items()):
        sec, name = kid.split('.', 1)
        desc = byid[kid]['description'] if kid in byid else 'set by a release component'
        sections.setdefault(sec, []).append((name, desc + ' (set by the UI scale component of this release)', dict(byid.get(kid, {'id': kid}), default=v)))
    for sec, items in sections.items():
        lines += ['', f'[{sec}]']
        for name, desc, row in items:   # row: the config_keys row with its default replaced by the value to list (key_type takes a row since core v0.16.0)
            lines += [f'; {desc}', f'{name}={gen_tables.key_type(row)[1]}']
    return '\r\n'.join(lines) + '\r\n'


def is_off_key(kid, rel):
    r = rel['release_values']
    return (any(kid.startswith(p) for p in r['off_prefixes']) or any(kid.endswith(s) for s in r['off_suffixes'])
            or kid in r['off_ids'] or any(p in kid for p in r['off_patterns'])) and kid not in r['inert_parameters']


def component_ini_set(comps):
    """What the components set in the player ini: the one place that merges their ini_set maps (build() and the tests use it)."""
    out = {}
    for c in comps['components']:
        out.update(c.get('ini_set', {}))
    return out


def value_problems(keys, rel, dev_ini_text=None, dev_ini_expected=None, ini_set=None):
    """The release-value gate: every dev, proof and test key is off at its release value; the required keys have their value (the exe guard on,
    the forced mismatch off, minidump 2); every key the player ini omits has default == release value; the shipped dev-side ini equals the generated one.
    ini_set (J74): the components' ini_set map overrides the registry's release_value, so its keys are held to the same rules: a key must be in the registry,
    an off key stays off unless release.json allowed_dev_keys names it with a decision id (D<n>), a required key keeps its value; an allow-list entry nothing sets is stale."""
    errs = []
    req = rel['release_values']['required']
    ids = {k['id']: k for k in keys}
    for kid, want in req.items():
        if kid not in ids:
            errs.append(f'required release key {kid} is not in the config_keys registry')
        elif ids[kid].get('release_value', ids[kid]['default']) != want:
            errs.append(f"{kid}: release_value {ids[kid].get('release_value', ids[kid]['default'])!r}, the release needs {want!r}")
    allowed = rel['release_values'].get('allowed_dev_keys', {})
    for kid, v in sorted((ini_set or {}).items()):
        if kid not in ids:
            errs.append(f'{kid}: set by a component (ini_set) but not in the config_keys registry')
        elif kid in req and v != req[kid]:
            errs.append(f'{kid}: a component sets {v!r}, the release needs {req[kid]!r}')
        elif is_off_key(kid, rel) and not_off(v) and kid not in allowed:
            errs.append(f'{kid}: a component sets {v!r} but it is a dev, proof or test key that must be off in a release (release.json release_values.allowed_dev_keys needs a decision for it)')
    if ini_set is not None:
        for kid, why in sorted(allowed.items()):
            if kid not in ids:
                errs.append(f'allowed_dev_keys {kid} is not a config_keys registry key')
            elif kid not in ini_set:
                errs.append(f'allowed_dev_keys {kid} is stale: no component sets it any more (remove it from release.json)')
            if not re.search(r'\bD\d+\b', str(why)):
                errs.append(f'allowed_dev_keys {kid}: the reason must cite a decision id (D<n>)')
    for k in keys:
        v = k.get('release_value', k['default'])
        if is_off_key(k['id'], rel) and not_off(v):
            errs.append(f"{k['id']}: release_value {v!r} is not off (false, 0 or empty)")
        if omitted(k, rel) and v != k['default'] and k['id'] not in (ini_set or {}):
            errs.append(f"{k['id']}: omitted from the player ini but release_value {v!r} differs from the DLL default {k['default']!r}")
    for kid in rel['release_values']['inert_parameters']:
        k = ids.get(kid)
        if k is None:
            errs.append(f'inert parameter {kid} is not a config key any more: remove it from release.json')
        elif not omitted(k, rel):
            errs.append(f'{kid}: an inert parameter must be omitted from the player ini')
    if dev_ini_text is not None and dev_ini_text != dev_ini_expected:
        errs.append('the shipped proxy ini differs from the generated one (python3 core/proxy/tools/gen_tables.py)')
    return errs


def shipped_ini_problems(ini_text, rel):
    """The gate on the rendered player ini (J74): no key under [dev] or [headless], and no dev, proof or test key, unless allow-listed."""
    allowed = rel['release_values'].get('allowed_dev_keys', {})
    errs, sec = [], None
    for line in ini_text.splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            sec = line[1:-1]
        elif '=' in line and not line.startswith(';') and sec:
            kid = f"{sec}.{line.split('=', 1)[0].strip()}"
            if (sec in ('dev', 'headless') or is_off_key(kid, rel)) and kid not in allowed:
                errs.append(f'the player ini sets {kid}, a dev, headless, proof or test key that is not allow-listed')
    return errs


# ---- components and ownership (pure) ------------------------------------------------------------------------------------------------
def owned_paths(targets, mod_dir):
    """What the installer owns: each target outside the mod folder exactly, the whole mod folder (runtime logs, dumps and DXVK files too)."""
    out = set()
    for t in targets:
        out.add(mod_dir + '/' if t.startswith(mod_dir + '/') else t)
    return sorted(out)


def provenance_problems(comps):
    """components.json `external_provenance` (J79): every named external source records the sha256 of what it was built from."""
    errs = []
    for name, srcs in comps.get('external_provenance', {}).items():
        if name not in comps.get('external', {}):
            errs.append(f'external_provenance names {name!r}, which is not an external source')
        for k, v in srcs.items():
            if not (isinstance(v.get('sha256'), str) and len(v['sha256']) == 64 and all(ch in '0123456789abcdef' for ch in v['sha256'])):
                errs.append(f'external_provenance {name}.{k}: sha256 must be 64 lower-case hex digits')
            if not isinstance(v.get('files'), int) or v['files'] <= 0:
                errs.append(f'external_provenance {name}.{k}: files must be a positive count')
    return errs


def ownership_problems(comps, installed=None, mod_dir=''):
    """Every target belongs to exactly one component and stays inside the game folder; an installed file (a path list) no component owns is an error."""
    errs, seen = [], {}
    ids = {c['id'] for c in comps['components']}
    for c in comps['components']:
        for r in c.get('requires', []):
            if r not in ids:
                errs.append(f"component {c['id']} requires {r}, which is not a component")
        for f in c['files']:
            t = f['target']
            if t.startswith('/') or '..' in t.split('/') or ':' in t or '\\' in t:
                errs.append(f"{c['id']}: target {t!r} must be a relative forward-slash path inside the game folder")
            if t.lower() in seen:
                errs.append(f"{c['id']}: target {t} is also owned by {seen[t.lower()]}")
            seen[t.lower()] = c['id']
    for p in installed or []:
        if p.lower() not in seen:
            errs.append(f'installed file {p} is owned by no component (add it to a row of release/napoleon/components.json)')
    return errs


ID_RE = re.compile(r'^[0-9a-f]{12}$')


def acceptance_streak(ledger_text, build_id, exists):
    """Consecutive `pass` rows at the end of the ledger among the rows of exactly this build id (other ids, -dirty ids included, are skipped), each naming a run
    and an evidence file that exists. The streak rule of rule 79 (tools/gates/pipeline.py) without its branch and watcher conditions."""
    rows = [json.loads(l) for l in ledger_text.splitlines() if l.strip()]
    n = 0
    for r in reversed([r for r in rows if r.get('build_id') == build_id]):
        if not (r.get('result') == 'pass' and r.get('run') and r.get('evidence') and exists(r['evidence'])):
            break
        n += 1
    return n


def dll_problem(dll, want_id, acceptance=None):
    """The DLL must carry the clean build id of this tree's DLL inputs (build_id.py) as a whole token, and no dirty literal; with `acceptance`
    ({'text': ledger text, 'passes': needed, 'exists': path -> bool}) the ledger must also hold that many consecutive passes on the id (J74)."""
    if not ID_RE.match(want_id or ''):
        return f'build id {want_id!r} is not a clean 12-hex id (an empty, malformed or -dirty id: a DLL input differs from HEAD)'
    b = Path(dll).read_bytes()
    i = want_id.encode('ascii')
    if not re.search(rb'(?<![0-9A-Za-z_-])' + i + rb'(?![0-9A-Za-z_-])', b):
        return f"{dll} does not carry build id {want_id} as a whole token (its inputs differ from this tree: rebuild it with core/proxy/tools/build.sh --docker dll, or download the CI artifact of this commit)"
    if i + b'-dirty' in b:
        return f'{dll} also carries {want_id}-dirty: the build mixed a dirty id in'
    if acceptance is not None:
        n = acceptance_streak(acceptance['text'], want_id, acceptance['exists'])
        if n < acceptance['passes']:
            return f"build {want_id}: the acceptance ledger holds {n} consecutive passes with committed evidence, a release needs {acceptance['passes']} (run `python3 core/harness/acceptance.py run` on this build)"
    return ''


# ---- building -------------------------------------------------------------------------------------------------------------------------
def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def tree_dirty():
    """Tracked changes (the core pin included), or release files not committed yet."""
    return bool(git('status', '--porcelain', '--untracked-files=no') or git('ls-files', '--others', '--exclude-standard', '--', 'release'))


def resolve(cf, comp, ctx):
    """-> (bytes | Path). Large external build outputs stay paths (hashed streaming)."""
    s = cf['source']
    if s == 'dll':
        return Path(ctx['dll'])
    if s == 'dxvk_dll':
        return Path(ctx['dxvk'][0])
    if s == 'dxvk_license':
        return Path(ctx['dxvk'][1])
    if s == 'player_ini':
        return ctx['player_ini'].encode('utf-8')
    if s.startswith('repo:'):
        return ROOT / s[5:]
    if s.startswith('crash_cmd:'):
        return crash_dump_cmd(s[10:], ctx['ident']).encode('ascii')
    if s.startswith('text:'):
        return comp['texts'][s[5:]].replace('\n', '\r\n').encode('ascii')
    if s.startswith('external:'):
        _, name, fname = s.split(':', 2)
        d = ctx['external'].get(name)
        if not d:
            raise SystemExit(f'build_release: no folder for external source {name!r} (components.json "external", or --external {name}=DIR)')
        p = Path(d) / fname
        meta = Path(str(p) + '.json')
        if not p.is_file():
            raise SystemExit(f'build_release: {p} not found (build it first: python3 core/wsc.py uiscale build)')
        problem = external_problem(p, meta, cf.get('build_id'))
        if problem:
            raise SystemExit('build_release: refusing: ' + problem)
        return p
    raise SystemExit(f'build_release: unknown source {s!r} for {cf["target"]}')


def external_problem(p, meta, pin=None):
    """An external build output needs its .json sidecar (J81 G14a): it must exist and name the file's sha256, and the build id when the
    components.json file row pins one (build_id)."""
    if not Path(meta).is_file():
        return f'{p} has no sidecar {Path(meta).name}: an external build output is taken only with the .json its build step wrote (sha256)'
    try:
        m = read_json(meta)
    except ValueError as e:
        return f'{Path(meta).name} does not parse: {e}'
    if not m.get('sha256'):
        return f'{Path(meta).name} names no sha256 for {Path(p).name}'
    if sha256_file(p) != m['sha256']:
        return f'{p} does not match the sha256 in {Path(meta).name} (a stale or partial build output)'
    if pin and m.get('build_id') != pin:
        return f"{Path(meta).name} names build {m.get('build_id')!r}, the release pins {pin} (components.json build_id)"
    return ''


def write_text(p, text, crlf=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if crlf:
        text = text.replace('\r\n', '\n').replace('\n', '\r\n')
    p.write_bytes(text.encode('ascii'))


def cmd_text(verb, extra, blurb):
    return ('@echo off\r\nrem ' + blurb + '\r\n'
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\\rr.ps1" {verb}{extra} %*\r\n'
            'set RR_EXIT=%ERRORLEVEL%\r\necho.\r\nif "%RR_EXIT%"=="0" (echo Done.) else (echo Finished with problems, exit code %RR_EXIT%. See the lines above.)\r\npause\r\nexit /b %RR_EXIT%\r\n')


def crash_dump_cmd(mode, ident):
    """tools/Enable|Disable crash dumps.cmd (J74): the core's wrapper with -ExeName and -DumpFolder added, so wer_localdumps.ps1 needs no repo. The folder goes
    in unexpanded (%LOCALAPPDATA% is written %% in a batch file) and is stored REG_EXPAND_SZ, outside the game folder."""
    on = mode == 'enable'
    out = f'%TEMP%\\rr_wer_{mode}.txt'
    folder = '%%LOCALAPPDATA%%\\CrashDumps\\' + ident['mod_dir']
    L = ['@echo off',
         "rem purpose: turn WER LocalDumps (full crash dumps, written outside the game folder) " + ('on' if on else 'off again (removes only its own registry subkey)') + " for the game's exe; asks for administrator rights once",
         'rem usage: double-click it' + ('; undo with "Disable crash dumps.cmd"' if on else ''),
         'rem when: ' + ('before you send a crash report: the dumps go to %LOCALAPPDATA%\\CrashDumps\\' + ident['mod_dir'] if on else 'when crash dumps are no longer wanted'),
         'rem not-a-verb: generated by release/core/build_release.py from the game identity; a Windows double-click wrapper around wer_localdumps.ps1']
    if on:
        L.append("echo Enabling crash dumps for the game's exe (a Windows admin prompt will appear)...")
    q = "'"
    L += ["powershell -NoProfile -ExecutionPolicy Bypass -Command \"Start-Process -Verb RunAs -Wait -FilePath powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',"
          f"'& ''%~dp0wer_localdumps.ps1'' -Mode {mode} -ExeName ''{ident['exe_name']}'' -DumpFolder ''{folder}'' *> ''{out}{q}{q}{q}\"",
          f'type "{out}"', 'echo.', 'pause']
    return '\r\n'.join(L) + '\r\n'


def readme_text(rel, ident, version, comps, lic):
    credit = [e['credit_line'] for e in lic['entries'] if e.get('shipped') and e.get('credit_line')]
    L = [f"{rel['product']} {version}", '=' * 40, '',
         f"An unofficial, fan-made modification for {ident['game']} (Steam). It never changes {ident['exe_name']} on disk: it only adds files to the game folder.", '',
         'WHAT YOU NEED', f"  The Steam build of {ident['game']}, unmodified; an NVIDIA graphics card; Windows 10 or 11. Close the game first.", '',
         'INSTALL', '  Unzip this folder anywhere. If it sits inside the game folder, the installer still finds the game, but verify-and-reinstall in Steam deletes it, so keep a copy elsewhere.',
         '  Double-click Install.cmd. It finds the game by itself (Steam), takes a snapshot of the game folder first, checks every file, and copies the mod in.',
         '  If it cannot find the game, run:  Install.cmd -GamePath "D:\\path\\to\\Napoleon Total War"', '',
         'UNINSTALL', '  Double-click Uninstall.cmd. It moves everything the mod added away, puts back the files it had backed up, and checks the game folder against the snapshot.',
         '  It ends with "identical to the pre-install snapshot" when the folder is exactly as before. After a game update it lists the files the update changed under',
         '  "changed by the game update, not by this tool" and still succeeds when everything of the mod is gone and your files are back.',
         '  Removed files go to the installer\'s state folder (_to_delete); Clean.cmd lists them with their size and deletes them after you confirm.', '',
         'IF SOMETHING GOES WRONG', '  Check.cmd lists missing, changed or foreign files. Repair.cmd puts back missing or changed ones (for example after Steam\'s "Verify integrity").',
         '  After a game update the remaster switches itself off by design (it only runs on the exe it was built for); Check.cmd says so, and Uninstall.cmd returns the game to vanilla.',
         '  Support.cmd makes a zip of logs and versions with your Windows user name, machine name and Steam ids removed. Crash dumps are never included unless you pass -IncludeDumps.',
         '  tools\\Enable crash dumps.cmd (asks for administrator rights, optional) makes Windows keep a full crash dump outside the game folder.', '',
         'WHERE THINGS ARE', f"  Installer state (snapshot, backups, install record): %LOCALAPPDATA%\\{rel['state_dir_name']}\\   Game logs: <game folder>\\{ident['mod_dir']}\\logs\\", '',
         'SETTINGS', f"  <game folder>\\{ident['config_file']} (plain text; the file lists what you may change).", '']
    if credit:
        L += ['CREDITS'] + ['  ' + c for c in credit] + ['  More in LICENSES.txt.', '']
    L += ['Multiplayer is untested. See RELEASE_NOTES.txt for the known limits.', '']
    return '\r\n'.join(L)


def notes_text(rel, version, comps_info, jobs, nonoff, facts, dll_id, core_tag, commit, prev):
    L = [f"{rel['product']} {version} - release notes (generated by release/core/build_release.py, not written by hand)", '',
         f"Built from commit {commit[:12]}, warscape-core {core_tag}, proxy DLL build {dll_id}.", '', 'COMPONENTS']
    for c in comps_info:
        L.append(f"  {c['id']}: {c['title']} - {c['files']} files, {human(c['size'])}; licences: {', '.join(c['licences']) or 'none'}")
    L += ['', f"DONE JOBS SINCE {'RELEASE ' + prev if prev else 'THE START'} ({len(jobs)})"] + [f'  {i}: {t}' for i, t in jobs]
    L += ['', 'SETTINGS THAT ARE NOT OFF IN THE PLAYER INI (release values)'] + [f'  {k} = {v}' for k, v in nonoff]
    L += ['', 'KNOWN LIMITS'] + [f'  - {s}' for s in rel['known_limits']]
    L += ['', 'OPEN ENGINE FACTS THAT BOUND THIS RELEASE'] + [f'  - {i}: {c}' for i, c in facts]
    L += ['', 'Publishing this release (GitHub, Nexus, ModDB) is not part of building it.', '']
    return '\r\n'.join(L)


def first_sentence(s, n=260):
    s = s.split('. ')[0]
    return s if len(s) <= n else s[:n - 3] + '...'


def load_facts(ids):
    out = []
    for i in ids:
        p = ROOT / 'registries' / 'engine_facts' / f'{i}.json'
        if not p.is_file():
            raise SystemExit(f'build_release: release.json limit_facts names {i}, which has no row in registries/engine_facts')
        r = read_json(p)
        out.append((i, f"[{r['state']}] " + first_sentence(r['claim'])))
    return out


def jobs_rows():
    return [read_json(p) for p in sorted((ROOT / 'registries' / 'jobs').glob('J*.json'))]


def core_tag():
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', (ROOT / 'wsc.toml').read_text(encoding='utf-8'), re.M)
    return m.group(1) if m else 'unknown'


def build(out, dll, external=None, no_zip=False, allow_dirty=False, version=None, dxvk=None, record=False, rebuild_unreleased=False):
    rel = read_json(ROOT / 'release' / 'napoleon' / 'release.json')
    comps = read_json(ROOT / 'release' / 'napoleon' / 'components.json')
    lic = gen_licenses.load(ROOT / 'release' / 'napoleon' / 'licenses.json')
    keys = [json.loads(l) for l in (ROOT / 'registries' / 'config_keys.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    ident_path = ROOT / rel['identity']
    ident = read_json(ident_path)
    version = version or (ROOT / 'release' / 'napoleon' / 'VERSION').read_text(encoding='ascii').strip()
    rpath = ROOT / 'release' / 'napoleon' / 'releases.json'
    releases = read_json(rpath)['releases'] if rpath.is_file() else []
    ini_set = component_ini_set(comps)
    errs = version_problems(version, releases) + ownership_problems(comps) + provenance_problems(comps) + gen_licenses.problems(lic, comps, ROOT) + value_problems(keys, rel, ini_set=ini_set)
    if errs:
        raise SystemExit('build_release: refusing:\n  ' + '\n  '.join(errs))
    if record and allow_dirty:
        raise SystemExit('build_release: refusing: --record records a releasable build only (not with --allow-dirty)')
    dirty = tree_dirty()
    if dirty and not allow_dirty:
        raise SystemExit('build_release: the working tree has uncommitted changes to tracked files: commit them (a release is built from a commit), or --allow-dirty for a throwaway build')
    bid = subprocess.run([sys.executable, str(ROOT / 'core' / 'proxy' / 'tools' / 'build_id.py')], capture_output=True, text=True).stdout.strip()
    acc = rel.get('acceptance')
    if not acc:
        raise SystemExit('build_release: refusing: release.json has no "acceptance" block (ledger and passes)')
    ledger = ROOT / acc['ledger']
    ledger_acc = {'text': ledger.read_text(encoding='utf-8') if ledger.is_file() else '', 'passes': acc['passes'], 'exists': lambda p: (ROOT / p).is_file()}
    p = dll_problem(dll, bid, None if allow_dirty else ledger_acc)
    if p:
        raise SystemExit('build_release: refusing: ' + p)
    if dxvk is None:
        sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
        import fetch_dxvk   # the pinned, sha256-checked stock DXVK; an unpinned one cannot get here
        dxvk = fetch_dxvk.fetch(ROOT / 'build' / 'dxvk')
    ext = dict(comps.get('external', {}))
    ext.update(external or {})
    ini_text = player_ini(keys, rel, ident, ini_set)
    bad_ini = shipped_ini_problems(ini_text, rel)
    if bad_ini:
        raise SystemExit('build_release: refusing: the rendered player ini:\n  ' + '\n  '.join(bad_ini))
    if allow_dirty:
        print('build_release: warning: --allow-dirty skips the acceptance-pass check of the DLL build id: not a releasable build')
    else:
        print(f"build_release: acceptance ledger holds {acceptance_streak(ledger_acc['text'], bid, ledger_acc['exists'])} consecutive passes on build {bid} (need {acc['passes']})")
    ctx = {'dll': dll, 'dxvk': dxvk, 'external': ext, 'player_ini': ini_text, 'ident': ident}
    name = f"{rel['product']} {version}"
    folder = Path(out) / name
    if folder.exists():
        raise SystemExit(f'build_release: {folder} already exists: a release folder is built fresh (move it away)')
    entries, infos = [], []
    for c in comps['components']:
        total = 0
        for f in c['files']:
            src = resolve(f, c, ctx)
            dest = folder / 'payload' / c['id'] / f['target']
            dest.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(src, bytes):
                dest.write_bytes(src)
            else:
                _copy_big(src, dest)
            size, h = dest.stat().st_size, sha256_file(dest)
            total += size
            entries.append({'path': f['target'], 'component': c['id'], 'size': size, 'sha256': h, 'payload': f"payload/{c['id']}/{f['target']}", 'config': bool(f.get('config'))})
        infos.append({'id': c['id'], 'title': c['title'], 'files': len(c['files']), 'size': total, 'licences': c.get('licences', [])})
    extras = []

    def add_extra(relpath, data, component):
        dest = folder / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        extras.append({'path': relpath, 'component': component, 'size': len(data), 'sha256': sha256_bytes(data)})
    for c in comps['components']:
        for x in c.get('extras', []):
            src = resolve({'source': x['source'], 'target': x['path']}, c, ctx)
            add_extra(x['path'], src if isinstance(src, bytes) else src.read_bytes(), c['id'])
    add_extra('installer/rr.ps1', INSTALLER.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'), 'installer')
    idb = ident_path.read_bytes()
    add_extra('installer/exe_identity.json', idb, 'installer')
    for cmd, (verb, extra, blurb) in CMDS.items():
        add_extra(cmd, cmd_text(verb, extra, blurb).encode('ascii'), 'installer')
    mod = ident['mod_dir']
    commit = git('rev-parse', 'HEAD')
    ctag = core_tag()
    before = [r for r in releases if r['version'] != version]   # a recorded, unpublished entry of this version is not its own predecessor
    prev = before[-1]['version'] if before else ''
    jobs = jobs_since(jobs_rows(), before)
    nonoff = []
    cur = None
    for line in ini_text.splitlines():
        if line.startswith('['):
            cur = line.strip('[]')
        elif '=' in line and not line.startswith(';'):
            k, v = line.split('=', 1)
            if v not in ('0', '', 'false'):
                nonoff.append((f'{cur}.{k}', v))
    add_extra('LICENSES.txt', gen_licenses.render(lic, ROOT).encode('utf-8'), 'docs')
    add_extra('README.txt', readme_text(rel, ident, version, comps, lic).encode('ascii'), 'docs')
    add_extra('RELEASE_NOTES.txt', notes_text(rel, version, infos, jobs, nonoff, load_facts(rel['limit_facts']), bid, ctag, commit, prev).encode('ascii', 'replace'), 'docs')
    man = {'product': rel['product'], 'version': version, 'created_utc': utc_now(), 'commit': commit, 'dirty': bool(dirty), 'core_tag': ctag, 'dll_build_id': bid,
           'game': {'name': ident['game'], 'exe_name': ident['exe_name'], 'mod_dir': mod, 'config_file': ident['config_file'], 'steam_folder': rel['game']['steam_folder'],
                    'other_exes': rel['game']['other_exes'], 'appdata_subpath': rel['game']['appdata_subpath']},
           'state_dir_name': rel['state_dir_name'], 'clear_ui_cache': bool(rel['clear_ui_cache']), 'runtime_globs': rel['runtime_globs'],
           'exe_identity': {'name': 'installer/exe_identity.json', 'sha256': sha256_bytes(idb)},
           'owned': owned_paths([e['path'] for e in entries], mod),
           'components': [{'id': c['id'], 'title': c['title'], 'optional': bool(c.get('optional')), 'requires': c.get('requires', []), 'licences': c.get('licences', [])} for c in comps['components']],
           'files': entries, 'extras': extras, 'pending': gen_licenses.pending(lic),
           'external_provenance': comps.get('external_provenance', {})}   # J79: what an external build output was made from (the 2.5x masters' manifest)
    (folder / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n', encoding='utf-8')
    csha = content_sha256(man)
    rp = record_problems(version, csha, releases, rebuild_unreleased)
    if rp:
        raise SystemExit(f'build_release: refusing: {rp[0]} (the folder {folder} is not releasable: move it away)')
    for k in man['pending']:
        print(f'build_release: warning: {k} is still pending in licenses.json (Liam decides): the shipped LICENSES.txt says so')
    if dirty:
        print('build_release: warning: built from a dirty tree (--allow-dirty): not a releasable build')
    bad = check_folder(folder)
    if bad:
        raise SystemExit('build_release: the folder it just built does not check:\n  ' + '\n  '.join(bad))
    print(f"build_release: {folder} ({len(entries)} payload files, {len(extras)} others, DLL build {bid}, core {ctag}, content sha256 {csha[:12]})")
    if record:
        e = record_release(rpath, {'version': version, 'recorded_utc': man['created_utc'], 'manifest_sha256': csha, 'build_id': bid, 'commit': commit,
                                   'jobs_done': [r['id'] for r in jobs_rows() if r.get('status') == 'done'], 'published': False}, rebuild_unreleased)
        print(f"build_release: recorded {version} in {rpath.relative_to(ROOT).as_posix()} (manifest sha256 {e['manifest_sha256'][:12]}, published {e.get('published', True)}): commit it; Liam sets published")
    if not no_zip:
        z = make_zip(folder)
        print(f'build_release: {z} ({human(z.stat().st_size)})')
    return folder


def _copy_big(src, dest, chunk=8 << 20):
    with open(src, 'rb') as a, open(dest, 'wb') as b:
        for blk in iter(lambda: a.read(chunk), b''):
            b.write(blk)


def make_zip(folder):
    z = Path(str(folder) + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for p in sorted(folder.rglob('*')):
            if p.is_file():
                zi = zipfile.ZipInfo(f'{folder.name}/{p.relative_to(folder).as_posix()}', date_time=(2026, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_STORED if p.suffix == '.pack' else zipfile.ZIP_DEFLATED
                with open(p, 'rb') as f, zf.open(zi, 'w', force_zip64=True) as w:
                    for blk in iter(lambda: f.read(8 << 20), b''):
                        w.write(blk)
    return z


def check_folder(folder):
    """Problems of a built release folder against its manifest: a missing, changed or unlisted file, a payload outside the owned paths, a version that
    does not match the folder name, the identity copy, the entry points."""
    folder = Path(folder)
    mp = folder / 'manifest.json'
    if not mp.is_file():
        return [f'{folder}: no manifest.json']
    man = read_json(mp)
    bad = []
    listed = {'manifest.json'}
    if folder.name != f"{man['product']} {man['version']}":
        bad.append(f"folder name {folder.name!r} is not '{man['product']} {man['version']}'")
    if man.get('dll_build_id', '').endswith('-dirty'):
        bad.append(f"manifest DLL build id {man['dll_build_id']} is dirty")
    for e in man['files']:
        listed.add(e['payload'])
        p = folder / e['payload']
        if not p.is_file():
            bad.append(f"{e['payload']}: missing")
        elif p.stat().st_size != e['size'] or sha256_file(p) != e['sha256']:
            bad.append(f"{e['payload']}: size or sha256 differs from the manifest")
        if e['payload'] != f"payload/{e['component']}/{e['path']}":
            bad.append(f"{e['payload']}: payload path does not follow its component and target")
        if not any(e['path'] == o or (o.endswith('/') and e['path'].startswith(o)) for o in man['owned']):
            bad.append(f"{e['path']}: outside the owned paths")
    comp_ids = {c['id'] for c in man['components']}
    for e in man['files']:
        if e['component'] not in comp_ids:
            bad.append(f"{e['path']}: owned by {e['component']}, which is not a component of this release")
    for e in man['extras']:
        listed.add(e['path'])
        p = folder / e['path']
        if not p.is_file():
            bad.append(f"{e['path']}: missing")
        elif sha256_file(p) != e['sha256']:
            bad.append(f"{e['path']}: sha256 differs from the manifest")
    for p in folder.rglob('*'):
        if p.is_file() and p.relative_to(folder).as_posix() not in listed:
            bad.append(f"{p.relative_to(folder).as_posix()}: a file the manifest does not list")
    ie = folder / 'installer' / 'exe_identity.json'
    if not ie.is_file() or sha256_file(ie) != man['exe_identity']['sha256']:
        bad.append('installer/exe_identity.json: missing or differs from the manifest')
    for cmd in CMDS:
        if not (folder / cmd).is_file():
            bad.append(f'{cmd}: missing')
    tools = folder / 'tools'
    for p in sorted(tools.glob('*')) if tools.is_dir() else []:
        if p.suffix.lower() in ('.cmd', '.ps1') and p.name != 'wer_localdumps.ps1':
            t = p.read_text(encoding='utf-8', errors='replace')
            if 'wer_localdumps.ps1' in t:
                if '-ExeName' not in t or '-DumpFolder' not in t:
                    bad.append(f'tools/{p.name}: runs wer_localdumps.ps1 without -ExeName and -DumpFolder (it then needs the repo and fails on a player PC)')
                if not (tools / 'wer_localdumps.ps1').is_file():
                    bad.append(f'tools/{p.name}: tools/wer_localdumps.ps1 is not beside it')
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=str(ROOT / 'build' / 'release'))
    ap.add_argument('--dll', default=str(ROOT / 'build' / 'proxy' / 'napoleon' / 'd3d9.dll'))
    ap.add_argument('--external', action='append', default=[], metavar='NAME=DIR')
    ap.add_argument('--dxvk-dir', help='a folder with d3d9_dxvk.dll and LICENSE.dxvk.txt already checked against the pin (default: fetch_dxvk.py downloads the pinned release)')
    ap.add_argument('--no-zip', action='store_true')
    ap.add_argument('--allow-dirty', action='store_true')
    ap.add_argument('--record', action='store_true', help='after a clean build, write version, manifest sha256 and build id into releases.json (only when Liam says so)')
    ap.add_argument('--rebuild-unreleased', action='store_true', help='overwrite a recorded entry of this version that is not published yet')
    ap.add_argument('--check', metavar='FOLDER')
    a = ap.parse_args()
    if a.check:
        bad = check_folder(a.check)
        print('\n'.join(['build_release --check: PROBLEMS'] + ['  ' + b for b in bad]) if bad else f'build_release --check: {a.check} ok')
        return 1 if bad else 0
    dxvk = None
    if a.dxvk_dir:
        sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
        import fetch_dxvk
        d, lic = Path(a.dxvk_dir) / 'd3d9_dxvk.dll', Path(a.dxvk_dir) / 'LICENSE.dxvk.txt'
        if sha256_file(d) != fetch_dxvk.PIN['d3d9_sha256'] or sha256_file(lic) != fetch_dxvk.PIN['license_sha256']:
            raise SystemExit(f'build_release: {a.dxvk_dir} does not match the DXVK pin in fetch_dxvk.py: refusing an unpinned DXVK')
        dxvk = (d, lic)
    build(a.out, a.dll, dict(x.split('=', 1) for x in a.external), a.no_zip, a.allow_dirty, dxvk=dxvk, record=a.record, rebuild_unreleased=a.rebuild_unreleased)
    return 0


if __name__ == '__main__':
    sys.exit(main())
