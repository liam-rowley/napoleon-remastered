#!/usr/bin/env python3
r"""Install the upscaled UI art for a play test (proxy kit + play packs) with one command, and take it all out again with one (J53).

purpose: Liam's play-test install of the 2.5x UI art, or (J66, J67: --scale 2|1.5|1.25) of the whole vanilla UI at a factor (2 for 3840x2160, 1.25 or 1.5 for 2560x1440): refuse unsafe states, snapshot the game folder, install the proxy kit (pc_deploy) with dev.skip_intro=1 and the chosen packs (install_packs.ps1, sha-checked; with --scale also dev.file_rules pointing the loose uied.templates at the scaled copy in the state folder, and the UI cache moved aside), and undo it all back to a snapshot-identical game folder
usage: python3 upscale/pc/play.py install [--roles a,b | --all | --scale 2|1.5|1.25] [--kit ID|DIR] [--intro] | uninstall | status   [--game DIR] [--state DIR] [--packs DIR] [--uiscale-work DIR]   (Git Bash on the PC, from the repo checkout)
when: before Liam sits down to play with the upscaled art (build the packs first: python3 core/wsc.py upscale pack --play --roles ..., or for --scale F: python3 core/wsc.py uiscale build --factor F), and after, to put the game folder back; never while an agent job holds the game lock
not-a-verb: a PC-side wrapper for Liam's own shell that composes pc_deploy.py and install_packs.ps1 (both stay the only writers of the game folder); agents use watcher jobs instead

Order matters on the way out: the packs leave data\ first, then `pc_deploy uninstall` (it compares the folder with the snapshot it took
at the kit install), then the folder is diffed against this tool's own pre-install snapshot and the exit code is non-zero unless it is
identical. Nothing is deleted: packs go to <state>\_to_delete\play_<stamp>\, the proxy's logs and dumps to pc_deploy's _to_delete folder.
The record is <state>\play\play.json, written before the first change so a half-finished install can still be uninstalled.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / 'core' / 'proxy' / 'tools'))
import pc_deploy  # noqa: E402

CONFIG = REPO / 'upscale' / 'napoleon' / 'config.json'
GAMES = REPO / 'discovery' / 'napoleon' / 'games.json'
DEFAULT_STATE = Path(r'C:\napoleon_remastered_pc')
INSTALL_PS1 = HERE / 'install_packs.ps1'
UISCALE = REPO / 'uiscale' / 'napoleon' / 'config.json'
UI_CACHE = Path(os.environ.get('APPDATA', r'C:\Users\Default\AppData\Roaming')) / 'The Creative Assembly' / 'Napoleon' / 'ui_cache'
NEVER_DEFAULT = ('loading_screen', 'event_picture')   # 42 % of the extra bytes (J53 brief): only by name or --all


class Refused(Exception):
    pass


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def record_path(state):
    return Path(state) / 'play' / 'play.json'


def save_record(state, rec):
    p = record_path(state)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=1) + '\n', encoding='utf-8')


def identity():
    ident = pc_deploy.default_identity()
    if not ident:
        raise Refused('no exe identity (proxy/napoleon/identity.json): run from the repo checkout')
    return ident


def lock_holder(state):
    """the game lock's line when an agent job holds it (fresh: under the watcher's 20-minute expiry), else ''"""
    p = Path(state) / 'watcher' / 'game.lock'
    try:
        age = time.time() - p.stat().st_mtime
        line = p.read_text(encoding='utf-8', errors='replace').strip().splitlines()[0]
    except (OSError, IndexError):
        return ''
    return line if age < 1200 else ''


def profile_active(state):
    """the active watcher profile's name, '' when none: `_active.json` holds it until the restore has run, and null or no file means none"""
    p = Path(state) / 'watcher' / 'profiles' / '_active.json'
    try:
        d = json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return ''
    return str(d.get('name') or d.get('profile') or 'unnamed') if isinstance(d, dict) and d else ''


def common_refusals(game, state, ident):
    """reasons not to touch the game folder now: a game running, an agent's game lock, a non-vanilla exe or a .git (pc_deploy's rules)"""
    why = pc_deploy.running_check(game, ident['mod_dir'], ident['exe_name'], state=state, other_exes=('Empire.exe',))
    if why:
        raise Refused(why + ': close the game first')
    held = lock_holder(state)
    if held:
        raise Refused(f'an agent job holds the game lock ({held}): wait until it is released (job.sh status)')
    ok, _, line = pc_deploy.exe_verdict(game, ident)
    if ok is not True:
        raise Refused(line)
    gits = pc_deploy.git_dirs(game)
    if gits:
        raise Refused('a .git in or above the game folder: ' + ', '.join(gits) + ' (never run git in a game folder)')


def pick_roles(cfg, roles, all_roles):
    if all_roles:
        return [r for r in cfg['roles']]
    if roles:
        out = [r.strip() for r in roles.split(',') if r.strip()]
        bad = [r for r in out if r not in cfg['roles']]
        if bad:
            raise Refused(f'unknown role(s) {bad}; roles: {", ".join(cfg["roles"])}')
        return out
    return [r for r in cfg['first_roles'] if r not in NEVER_DEFAULT]


def pack_files(cfg, packs_dir, roles, all_roles):
    """[(role, pack path, manifest)] for the chosen roles; a missing pack is refused (with --all, a role with no pack is left out and named)"""
    out, missing = [], []
    for r in roles:
        p = Path(packs_dir) / (cfg['play_pack_name'].format(role=r) + '.pack')
        m = Path(str(p) + '.json')
        if not p.is_file() or not m.is_file():
            missing.append(r)
            continue
        out.append((r, p, load(m)))
    if missing and not all_roles:
        raise Refused(f'no play pack for {missing} in {packs_dir}: build it with python3 core/wsc.py upscale pack --play --roles {",".join(missing)}')
    if missing:
        print(f'play: no play pack for {missing} (nothing built for them): left out')
    if not out:
        raise Refused(f'no play packs in {packs_dir}')
    return out


def scale_files(work, factor):
    """J66, J67: [(name, pack, manifest)] of the scale packs, plus (templates file, rules file) for `factor`; every file sha-checked here"""
    cfg = load(UISCALE)
    if factor not in cfg['factors']:
        raise Refused(f'--scale {factor:g}: built factors are {cfg["factors"]} (3840x2160: 2; 2560x1440: 1.25 or 1.5)')
    tag = ('%g' % factor).replace('.', '')
    work = Path(work)
    out = []
    for key in ('pack_name', 'fonts_pack_name'):
        p = work / (cfg[key].format(tag=tag) + '.pack')
        m = Path(str(p) + '.json')
        if not p.is_file() or not m.is_file():
            raise Refused(f'no {p.name} (and .pack.json) in {work}: build it with python3 core/wsc.py uiscale build --factor {factor:g}')
        out.append((key, p, load(m)))
    t = work / cfg['templates_name'].format(tag=tag)
    r = work / cfg['rules_name'].format(tag=tag)
    tm = Path(str(t) + '.json')
    if not (t.is_file() and tm.is_file() and r.is_file()):
        raise Refused(f'no scaled templates ({t.name}, .json) or rules file ({r.name}) in {work}: python3 core/wsc.py uiscale build --factor {factor:g}')
    if pc_deploy.sha256_file(t) != load(tm)['sha256']:
        raise Refused(f"{t.name} sha256 is not its .json's: rebuild (wsc uiscale build)")
    if str(t).lower() not in r.read_text(encoding='utf-8').lower():
        raise Refused(f'{r.name} does not redirect to {t}: rebuild (wsc uiscale build --work {work})')
    return out, t, r


def move_ui_cache(trash, label):
    """move every file in the engine's UI cache (AppData, never the game folder) to <trash>/<label>; returns the names moved"""
    if not UI_CACHE.is_dir():
        return []
    moved = []
    for f in sorted(UI_CACHE.iterdir()):
        dst = Path(trash) / label / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dst))
        moved.append(f.name)
    return moved


def pick_kit(state, kit):
    """the kit folder: --kit as a folder or an id under <state>/kits, else the newest sent proxy kit there"""
    kits = Path(state) / 'kits'
    if kit:
        k = Path(kit) if Path(kit).is_dir() else kits / kit
    else:
        found = sorted(d for d in kits.glob('kit_*') if (d / 'manifest.json').is_file()) if kits.is_dir() else []
        if not found:
            raise Refused(f'no proxy kit under {kits}: build and send one (pc_deploy.py kit --dll ..., then send --kit <dir> --state {state})')
        k = found[-1]
    if not (k / 'manifest.json').is_file():
        raise Refused(f'{k} is not a kit folder (no manifest.json)')
    _, bad = pc_deploy.verify_kit(k)
    if bad:
        raise Refused(f'kit {k.name} does not verify: ' + '; '.join(bad[:3]))
    return k


def run_ps1(args):
    """install_packs.ps1 the way a watcher job calls it; returns (exit code, result dict)"""
    ps = shutil.which('powershell.exe') or shutil.which('powershell')
    if not ps:
        raise Refused('Windows PowerShell (powershell.exe) not found')

    def q(v):
        return "'" + str(v).replace("'", "''") + "'"
    parts = [('@(' + ', '.join(q(x) for x in a) + ')') if isinstance(a, list) else (a if str(a).startswith('-') else q(a)) for a in args]
    r = subprocess.run([ps, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', f'& {q(INSTALL_PS1)} {" ".join(parts)}; exit $LASTEXITCODE'],
                       capture_output=True, text=True, timeout=1800)
    try:
        out = json.loads(r.stdout)
    except ValueError:
        out = {'status': 'failed', 'reason': (r.stdout + r.stderr).strip()[-400:]}
    return r.returncode, out


def install(game, state, packs_dir, roles=None, all_roles=False, kit=None, intro=False, scale=None, uiscale_work=None):
    cfg = load(CONFIG)
    game, state = Path(game), Path(state)
    if record_path(state).exists():
        raise Refused(f'a play install is already in ({record_path(state)}): python3 upscale/pc/play.py uninstall first')
    if (state / pc_deploy.STATE_FILE).exists():
        rec = load(state / pc_deploy.STATE_FILE)
        raise Refused(f"a proxy kit is already installed ({rec.get('kit_id')}): uninstall it first "
                      f'(python3 core/proxy/tools/pc_deploy.py uninstall --game "{game}" --state "{state}")')
    ident = identity()
    common_refusals(game, state, ident)
    if scale:
        if roles or all_roles:
            raise Refused('--scale installs the scale packs, which carry their own 2x art: no --roles or --all with it')
        packs, tfile, rules = scale_files(uiscale_work or (state / 'uiscale' / 'work'), scale)
    else:
        packs = pack_files(cfg, packs_dir, pick_roles(cfg, roles, all_roles), all_roles)
    # every pack check before the first change (install_packs.ps1 checks again while copying), so a refusal leaves the folder as it was
    there = [p.name for _, p, _ in packs if (game / 'data' / p.name).exists()]
    if there:
        raise Refused(f'already in {game / "data"} (never overwritten, and not ours to take out): {", ".join(there)}')
    for _, p, m in packs:
        h = pc_deploy.sha256_file(p)
        if h != m['sha256']:
            raise Refused(f"{p.name} sha256 {h[:16]} is not its .pack.json's {m['sha256'][:16]}: rebuild it (wsc upscale pack --play)")
    k = pick_kit(state, kit)
    stamp = pc_deploy.utc_stamp()
    snap = state / 'play' / f'snap_before_{stamp}.json'
    snap.parent.mkdir(parents=True, exist_ok=True)
    before = pc_deploy.snapshot(game)
    snap.write_text(json.dumps(before), encoding='utf-8')
    print(f'play: snapshot {len(before)} entries -> {snap}')
    rec = {'status': 'installing', 'stamp': stamp, 'snapshot': str(snap), 'kit': k.name, 'game': str(game),
           'trash': str(state / '_to_delete' / f'play_{stamp}'), 'skip_intro': not intro,
           'packs': [{'role': r, 'name': p.name, 'sha256': m['sha256'], 'bytes': m['bytes'], 'entries': m['entries'],
                      'held_back': len(m.get('held_back', []))} for r, p, m in packs]}
    if scale:
        rec['scale'] = {'factor': scale, 'templates': str(tfile), 'templates_sha256': pc_deploy.sha256_file(tfile), 'rules': str(rules),
                        'ui_cache': str(UI_CACHE), 'ui_cache_moved_install': [], 'ui_cache_moved_uninstall': []}
    save_record(state, rec)
    try:
        pc_deploy.install(k, game, state)
        keys = ([] if intro else ['dev.skip_intro=1']) + ([f'dev.file_rules={rules}'] if scale else [])
        if keys:
            pc_deploy.set_keys(game, keys, None, state)
    except SystemExit as e:
        raise Refused(f'proxy install failed ({e}); the record is kept: python3 upscale/pc/play.py uninstall puts the folder back')
    code, res = run_ps1(['-Mode', 'install', '-Game', str(game), '-Packs', [str(p) for _, p, _ in packs], '-Trash', rec['trash']])
    if code != 0:
        raise Refused(f"pack install {res.get('status')}: {res.get('reason')}; python3 upscale/pc/play.py uninstall puts the folder back")
    if scale:
        rec['scale']['ui_cache_moved_install'] = move_ui_cache(rec['trash'], 'ui_cache_install')
    rec['status'] = 'installed'
    rec['installed_utc'] = pc_deploy.utc_stamp()
    save_record(state, rec)
    mb = sum(p['bytes'] for p in rec['packs']) / 1e6
    print(f"play: installed kit {k.name} and {len(packs)} play pack(s), {mb:.0f} MB: {', '.join(r for r, _, _ in packs)}")
    if scale:
        print(f"play: UI at {scale:g}x: dev.file_rules={rules} (the loose uied.templates comes from {tfile}); "
              f"UI cache files moved aside: {len(rec['scale']['ui_cache_moved_install'])}")
    print(f"play: logs {game / ident['mod_dir'] / 'logs'}, crash dumps {game / ident['mod_dir'] / 'dumps'}")
    print('play: launch the game from Steam as usual; afterwards (or at anything odd): python3 upscale/pc/play.py uninstall')
    return 0


def uninstall(game, state):
    game, state = Path(game), Path(state)
    rp = record_path(state)
    if not rp.exists():
        raise Refused(f'no play install recorded ({rp}); for a proxy kit alone use pc_deploy.py uninstall')
    rec = load(rp)
    ident = identity()
    why = pc_deploy.running_check(game, ident['mod_dir'], ident['exe_name'], state=state, other_exes=('Empire.exe',))
    if why:
        raise Refused(why + ': close the game first')
    active = profile_active(state)
    if active:
        # J67: the watcher's restore wrote the mod ini back after pc_deploy had removed it, and the uninstall ended "added napoleon_remastered.ini"
        raise Refused(f'a watcher profile is still active ({active}): its restore writes the config files, so an uninstall now would not end '
                      'identical. Release the lock and wait for job.sh status to show profile_active null')
    md = game / ident['mod_dir']
    dumps = sorted((md / 'dumps').glob('*.dmp')) if (md / 'dumps').is_dir() else []
    if dumps:
        print(f'play: {len(dumps)} crash dump(s) from the session: {", ".join(d.name for d in dumps)} (moved, with the logs, by pc_deploy uninstall)')
    names = [p['name'] for p in rec['packs']]
    code, res = run_ps1(['-Mode', 'uninstall', '-Game', str(game), '-Names', names, '-Trash', rec['trash']])
    if code != 0:
        raise Refused(f"pack uninstall {res.get('status')}: {res.get('reason')} (nothing else changed; run uninstall again)")
    print(f"play: {len(names)} pack name(s) moved to {rec['trash']}")
    if rec.get('scale'):
        rec['scale']['ui_cache_moved_uninstall'] = move_ui_cache(rec['trash'], 'ui_cache_uninstall')
        print(f"play: UI cache files written at {rec['scale']['factor']:g}x moved aside: {len(rec['scale']['ui_cache_moved_uninstall'])}")
    if (state / pc_deploy.STATE_FILE).exists():
        if not pc_deploy.uninstall(game, state):
            print('play: pc_deploy uninstall did not end identical to its own snapshot (above)')
    diffs = pc_deploy.diff_snapshots(load(rec['snapshot']), pc_deploy.snapshot(game))
    stamp = pc_deploy.utc_stamp()
    rec.update({'status': 'uninstalled' if not diffs else 'uninstalled_differs', 'uninstalled_utc': stamp, 'diffs': diffs[:50]})
    hist = state / 'play' / 'history' / f'play_{rec["stamp"]}.json'
    hist.parent.mkdir(parents=True, exist_ok=True)
    hist.write_text(json.dumps(rec, indent=1) + '\n', encoding='utf-8')
    os.replace(rp, state / 'play' / 'history' / f'play_{rec["stamp"]}.record.json')
    if diffs:
        print('play: game folder DIFFERS from the pre-install snapshot:\n  ' + '\n  '.join(diffs[:50]))
        return 1
    print(f'play: identical: the game folder matches the snapshot taken before the install ({rec["snapshot"]})')
    return 0


def status(game, state):
    game, state = Path(game), Path(state)
    ident = identity()
    ok, _, line = pc_deploy.exe_verdict(game, ident)
    rp = record_path(state)
    if not rp.exists():
        print('play: no play install in')
        print('  ' + line)
        return 0 if ok else 1
    rec = load(rp)
    bad_t = False
    if rec.get('scale'):
        sc = rec['scale']
        t = Path(sc['templates'])
        bad_t = not (t.is_file() and pc_deploy.sha256_file(t) == sc['templates_sha256'])
        print(f"play: UI scale {sc['factor']:g}x, templates {'BAD' if bad_t else 'ok '} {t}, rules {sc['rules']}")
    print(f"play: {rec['status']} (kit {rec['kit']}, since {rec.get('installed_utc') or rec['stamp']}, dev.skip_intro={1 if rec.get('skip_intro') else 'vanilla'})")
    bad = ok is not True or bad_t
    for p in rec['packs']:
        f = game / 'data' / p['name']
        good = f.is_file() and pc_deploy.sha256_file(f) == p['sha256']
        bad |= not good
        print(f"  {'ok ' if good else 'BAD'} data/{p['name']} ({p['entries']} entries, {p['bytes'] / 1e6:.0f} MB, {p['held_back']} held back)")
    kr = state / pc_deploy.STATE_FILE
    if kr.exists():
        krec = load(kr)
        for f in krec['files']:
            good = (game / f['path']).is_file() and pc_deploy.sha256_file(game / f['path']) == f['sha256']
            ini = f['path'] == krec.get('config_file')   # dev.skip_intro=1 changed it on purpose
            bad |= not good and not ini
            print(f"  {'ok ' if good else ('set' if ini else 'BAD')} {f['path']}")
        foreign, _ = pc_deploy.foreign_files(game, state, krec)
        mine = {'data/' + p['name'] for p in rec['packs']}
        foreign = [x for x in foreign if x.split(None, 1)[1] not in mine]
        print(f'  foreign: {len(foreign)}' + ''.join('\n    ' + x for x in foreign[:20]))
    else:
        print('  proxy: not installed (the kit record is gone)')
    md = game / ident['mod_dir']
    dumps = sorted((md / 'dumps').glob('*.dmp')) if (md / 'dumps').is_dir() else []
    print(f'  dumps: {len(dumps)}' + (' ' + ', '.join(d.name for d in dumps) if dumps else ''))
    print('  ' + line)
    print('play: to take it all out: python3 upscale/pc/play.py uninstall')
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['install', 'uninstall', 'status'])
    ap.add_argument('--roles', help='install: comma list of roles (default: the config first_roles)')
    ap.add_argument('--all', action='store_true', help='install: every role that has a play pack')
    ap.add_argument('--kit', help='install: a kit id under <state>/kits or a kit folder (default: the newest sent kit_*)')
    ap.add_argument('--intro', action='store_true', help='install: keep the splash screens and intro (default: dev.skip_intro=1)')
    ap.add_argument('--game', default=load(GAMES)['napoleon']['root'])
    ap.add_argument('--state', default=str(DEFAULT_STATE))
    ap.add_argument('--packs', help=r'play pack folder (default <state>\upscale\work\<play_packs_dir>)')
    ap.add_argument('--scale', type=float, help='install: the vanilla UI at this factor (2 for 3840x2160; 1.25 or 1.5 for 2560x1440; one at a time) instead of the 2.5x role packs')
    ap.add_argument('--uiscale-work', help=r'install --scale: the uiscale build folder (default <state>\uiscale\work)')
    a = ap.parse_args(argv)
    packs = a.packs or str(Path(a.state) / 'upscale' / 'work' / load(CONFIG)['play_packs_dir'])
    try:
        if a.action == 'install':
            if a.roles and a.all:
                raise Refused('--roles or --all, not both')
            return install(a.game, a.state, packs, a.roles, a.all, a.kit, a.intro, a.scale, a.uiscale_work)
        if a.action == 'uninstall':
            return uninstall(a.game, a.state)
        return status(a.game, a.state)
    except Refused as e:
        print(f'play {a.action}: refused: {e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
