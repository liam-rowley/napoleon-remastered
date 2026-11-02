#!/usr/bin/env python3
"""Build and check a release folder: `Napoleon Remastered <version>\\` and its zip, from the repo, the CI-built DLL and the component rows.

purpose: build the player release folder (payload per component, manifest.json with every file's target, size and sha256, the installer scripts and .cmd entry points, README.txt, generated LICENSES.txt and RELEASE_NOTES.txt) and its zip from a clean checkout; --check verifies a built folder against its manifest; refuses a dirty tree, a DLL whose embedded build id is not this tree's (build_id.py) or an unpinned DXVK
usage: python3 release/core/build_release.py [--out build/release] [--dll build/proxy/napoleon/d3d9.dll] [--external uiscale=DIR] [--no-zip] [--allow-dirty] | --check <release folder>
when: to make a release (one command, then Install.cmd on a PC); --check on a built or unzipped folder before it goes anywhere; it builds files only, publishing is Liam's call and never done by it
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
    'Uninstall.cmd': ('uninstall', '', 'Removes it and checks the game folder is exactly as it was before the install.'),
    'Repair.cmd': ('repair', '', 'Puts back missing or changed files (for example after Steam "Verify integrity of game files").'),
    'Check.cmd': ('check', '', 'Checks every installed file and the game exe.'),
    'Support.cmd': ('support', '', 'Makes a support bundle (logs and versions, personal names removed) to send when something goes wrong.'),
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


def version_problems(version, releases):
    """The version is well formed and higher than every recorded release (releases: [{version, jobs_done}])."""
    try:
        v = parse_version(version)
    except ValueError as e:
        return [str(e)]
    prev = [parse_version(r['version']) for r in releases]
    if prev and v <= max(prev):
        return [f'version {version} is not higher than the last recorded release {".".join(map(str, max(prev)))} (release/napoleon/releases.json)']
    return []


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


def key_text(v):
    import gen_tables
    return gen_tables.key_type(v)[1]


# ---- config keys and the player ini (pure) ------------------------------------------------------------------------------------------
def omitted(key, rel):
    pi = rel['player_ini']
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
            sections.setdefault(sec, []).append((name, k['description'], k.get('release_value', k['default'])))
    byid = {k['id']: k for k in keys}
    for kid, v in sorted((ini_set or {}).items()):
        sec, name = kid.split('.', 1)
        desc = byid[kid]['description'] if kid in byid else 'set by a release component'
        sections.setdefault(sec, []).append((name, desc + ' (set by the UI scale component of this release)', v))
    for sec, items in sections.items():
        lines += ['', f'[{sec}]']
        for name, desc, v in items:
            lines += [f'; {desc}', f'{name}={gen_tables.key_type(v)[1]}']
    return '\r\n'.join(lines) + '\r\n'


def is_off_key(kid, rel):
    r = rel['release_values']
    return (any(kid.startswith(p) for p in r['off_prefixes']) or any(kid.endswith(s) for s in r['off_suffixes'])
            or kid in r['off_ids'] or any(p in kid for p in r['off_patterns'])) and kid not in r['inert_parameters']


def value_problems(keys, rel, dev_ini_text=None, dev_ini_expected=None):
    """The release-value gate: every dev, proof and test key is off at its release value; the required keys have their value (the exe guard on,
    the forced mismatch off, minidump 2); every key the player ini omits has default == release value; the shipped dev-side ini equals the generated one."""
    errs = []
    req = rel['release_values']['required']
    ids = {k['id']: k for k in keys}
    for kid, want in req.items():
        if kid not in ids:
            errs.append(f'required release key {kid} is not in the config_keys registry')
        elif ids[kid].get('release_value', ids[kid]['default']) != want:
            errs.append(f"{kid}: release_value {ids[kid].get('release_value', ids[kid]['default'])!r}, the release needs {want!r}")
    for k in keys:
        v = k.get('release_value', k['default'])
        if is_off_key(k['id'], rel) and not_off(v):
            errs.append(f"{k['id']}: release_value {v!r} is not off (false, 0 or empty)")
        if omitted(k, rel) and v != k['default']:
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


# ---- components and ownership (pure) ------------------------------------------------------------------------------------------------
def owned_paths(targets, mod_dir):
    """What the installer owns: each target outside the mod folder exactly, the whole mod folder (runtime logs, dumps and DXVK files too)."""
    out = set()
    for t in targets:
        out.add(mod_dir + '/' if t.startswith(mod_dir + '/') else t)
    return sorted(out)


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


def dll_problem(dll, want_id):
    """The DLL must carry the build id of this tree's DLL inputs (build_id.py), clean."""
    if want_id.endswith('-dirty'):
        return f'build id {want_id} is dirty: a DLL input differs from HEAD'
    b = Path(dll).read_bytes()
    if want_id.encode('ascii') not in b:
        return f"{dll} does not carry build id {want_id} (its inputs differ from this tree: rebuild it with core/proxy/tools/build.sh --docker dll, or download the CI artifact of this commit)"
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
        if meta.is_file():
            want = read_json(meta).get('sha256')
            if want and sha256_file(p) != want:
                raise SystemExit(f'build_release: {p} does not match the sha256 in {meta.name} (a stale or partial build output)')
        return p
    raise SystemExit(f'build_release: unknown source {s!r} for {cf["target"]}')


def write_text(p, text, crlf=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if crlf:
        text = text.replace('\r\n', '\n').replace('\n', '\r\n')
    p.write_bytes(text.encode('ascii'))


def cmd_text(verb, extra, blurb):
    return ('@echo off\r\nrem ' + blurb + '\r\n'
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\\rr.ps1" {verb}{extra} %*\r\n'
            'set RR_EXIT=%ERRORLEVEL%\r\necho.\r\nif "%RR_EXIT%"=="0" (echo Done.) else (echo Finished with problems, exit code %RR_EXIT%. See the lines above.)\r\npause\r\nexit /b %RR_EXIT%\r\n')


def readme_text(rel, ident, version, comps, lic):
    credit = [e['credit_line'] for e in lic['entries'] if e.get('shipped') and e.get('credit_line')]
    L = [f"{rel['product']} {version}", '=' * 40, '',
         f"An unofficial, fan-made modification for {ident['game']} (Steam). It never changes {ident['exe_name']} on disk: it only adds files to the game folder.", '',
         'WHAT YOU NEED', f"  The Steam build of {ident['game']}, unmodified; an NVIDIA graphics card; Windows 10 or 11. Close the game first.", '',
         'INSTALL', '  Unzip this folder anywhere EXCEPT inside the game folder (uninstalling the game would delete it).',
         '  Double-click Install.cmd. It finds the game by itself (Steam), takes a snapshot of the game folder first, checks every file, and copies the mod in.',
         '  If it cannot find the game, run:  Install.cmd -GamePath "D:\\path\\to\\Napoleon Total War"', '',
         'UNINSTALL', '  Double-click Uninstall.cmd. It moves everything the mod added away and checks the game folder against the snapshot.',
         '  It ends with "identical to the pre-install snapshot" when the folder is exactly as before. Nothing is ever deleted: removed files go to the installer\'s state folder.', '',
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


def build(out, dll, external=None, no_zip=False, allow_dirty=False, version=None, dxvk=None):
    rel = read_json(ROOT / 'release' / 'napoleon' / 'release.json')
    comps = read_json(ROOT / 'release' / 'napoleon' / 'components.json')
    lic = gen_licenses.load(ROOT / 'release' / 'napoleon' / 'licenses.json')
    keys = [json.loads(l) for l in (ROOT / 'registries' / 'config_keys.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    ident_path = ROOT / rel['identity']
    ident = read_json(ident_path)
    version = version or (ROOT / 'release' / 'napoleon' / 'VERSION').read_text(encoding='ascii').strip()
    rpath = ROOT / 'release' / 'napoleon' / 'releases.json'
    releases = read_json(rpath)['releases'] if rpath.is_file() else []
    errs = version_problems(version, releases) + ownership_problems(comps) + gen_licenses.problems(lic, comps, ROOT) + value_problems(keys, rel)
    if errs:
        raise SystemExit('build_release: refusing:\n  ' + '\n  '.join(errs))
    dirty = tree_dirty()
    if dirty and not allow_dirty:
        raise SystemExit('build_release: the working tree has uncommitted changes to tracked files: commit them (a release is built from a commit), or --allow-dirty for a throwaway build')
    bid = subprocess.run([sys.executable, str(ROOT / 'core' / 'proxy' / 'tools' / 'build_id.py')], capture_output=True, text=True).stdout.strip()
    p = dll_problem(dll, bid)
    if p:
        raise SystemExit('build_release: refusing: ' + p)
    if dxvk is None:
        sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
        import fetch_dxvk   # the pinned, sha256-checked stock DXVK; an unpinned one cannot get here
        dxvk = fetch_dxvk.fetch(ROOT / 'build' / 'dxvk')
    ext = dict(comps.get('external', {}))
    ext.update(external or {})
    ini_set = {}
    for c in comps['components']:
        ini_set.update(c.get('ini_set', {}))
    ini_text = player_ini(keys, rel, ident, ini_set)
    ctx = {'dll': dll, 'dxvk': dxvk, 'external': ext, 'player_ini': ini_text}
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
            add_extra(x['path'], resolve({'source': x['source'], 'target': x['path']}, c, ctx).read_bytes(), c['id'])
    add_extra('installer/rr.ps1', INSTALLER.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'), 'installer')
    idb = ident_path.read_bytes()
    add_extra('installer/exe_identity.json', idb, 'installer')
    for cmd, (verb, extra, blurb) in CMDS.items():
        add_extra(cmd, cmd_text(verb, extra, blurb).encode('ascii'), 'installer')
    mod = ident['mod_dir']
    commit = git('rev-parse', 'HEAD')
    ctag = core_tag()
    prev = releases[-1]['version'] if releases else ''
    jobs = jobs_since(jobs_rows(), releases)
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
           'files': entries, 'extras': extras, 'pending': gen_licenses.pending(lic)}
    (folder / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n', encoding='utf-8')
    for k in man['pending']:
        print(f'build_release: warning: {k} is still pending in licenses.json (Liam decides): the shipped LICENSES.txt says so')
    if dirty:
        print('build_release: warning: built from a dirty tree (--allow-dirty): not a releasable build')
    bad = check_folder(folder)
    if bad:
        raise SystemExit('build_release: the folder it just built does not check:\n  ' + '\n  '.join(bad))
    print(f"build_release: {folder} ({len(entries)} payload files, {len(extras)} others, DLL build {bid}, core {ctag})")
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
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=str(ROOT / 'build' / 'release'))
    ap.add_argument('--dll', default=str(ROOT / 'build' / 'proxy' / 'napoleon' / 'd3d9.dll'))
    ap.add_argument('--external', action='append', default=[], metavar='NAME=DIR')
    ap.add_argument('--no-zip', action='store_true')
    ap.add_argument('--allow-dirty', action='store_true')
    ap.add_argument('--check', metavar='FOLDER')
    a = ap.parse_args()
    if a.check:
        bad = check_folder(a.check)
        print('\n'.join(['build_release --check: PROBLEMS'] + ['  ' + b for b in bad]) if bad else f'build_release --check: {a.check} ok')
        return 1 if bad else 0
    build(a.out, a.dll, dict(x.split('=', 1) for x in a.external), a.no_zip, a.allow_dirty)
    return 0


if __name__ == '__main__':
    sys.exit(main())
