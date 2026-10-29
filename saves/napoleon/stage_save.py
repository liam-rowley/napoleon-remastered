#!/usr/bin/env python3
"""stage_save.py: the only writer into Napoleon's save_games folder: stages test saves under a zz_ prefix, sha-checked, and moves them out again.

purpose: copy a save into save_games as zz_<name>.save (sha-checked, zz_ names only) so `autostart campaign:zz_<name>` can load it; move every zz_ file to <state>/_to_delete afterwards; keep read-only, sha-checked copies of saves under <state>/saves
usage: python3 -I saves/napoleon/stage_save.py stage SRC zz_NAME | clear | list | keep SAVE_NAME [--as NAME]   [--save-dir DIR] [--state DIR]
when: before every load-ladder or scenario launch of an edited save (stage), after the run (clear), and to take a copy of Liam's or a QuickSave's file out of save_games before reading or editing it (keep)
not-a-verb: a PC-side file mover with its own safety rules (zz_ prefix, sha check, nothing deleted), run in Git Bash on the PC beside job.sh

Rules (J14 brief): the game reads saves only from save_games; nothing there is touched except zz_ files, which this tool alone writes;
nothing is deleted (clear moves files to <state>/_to_delete/saves_<utc>/); the saves in <state>/saves are never edited, recipes
write their output elsewhere and it is staged from there.
"""
import argparse
import datetime
import hashlib
import os
import shutil
import stat
import sys
from pathlib import Path

PREFIX = 'zz_'
EXT = '.save'
DEFAULT_STATE = r'C:\napoleon_remastered_pc'


def default_save_dir():
    return Path(os.environ.get('APPDATA', '')) / 'The Creative Assembly' / 'Napoleon' / 'save_games'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def utc_stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def checked_copy(src, dest):
    """copy src to dest through a .partial file, sha-checked, renamed into place; returns the sha"""
    want = sha(src)
    tmp = dest.with_name(dest.name + '.partial')
    shutil.copyfile(src, tmp)
    if sha(tmp) != want:
        tmp.rename(tmp.with_name(tmp.name + '.bad'))
        raise SystemExit('stage_save: copy of %s does not match its sha; left as %s.bad' % (src, tmp.name))
    os.replace(tmp, dest)
    return want


def save_name(name):
    """zz_<name> -> zz_<name>.save; refuses anything without the prefix or with a path in it"""
    base = name[:-len(EXT)] if name.endswith(EXT) else name
    if not base.startswith(PREFIX) or len(base) <= len(PREFIX):
        raise SystemExit('stage_save: refusing %r: staged saves must be named %s<name>' % (name, PREFIX))
    if os.path.basename(base) != base or any(c in base for c in '<>:"/\\|?*'):
        raise SystemExit('stage_save: refusing %r: a plain file name only' % name)
    return base + EXT


def stage(src, name, save_dir):
    src, save_dir = Path(src), Path(save_dir)
    fname = save_name(name)
    if not save_dir.is_dir():
        raise SystemExit('stage_save: no save folder %s' % save_dir)
    dest = save_dir / fname
    if dest.exists():
        if sha(dest) == sha(src):
            print('already staged %s (same sha)' % dest)
            return fname[:-len(EXT)]
        raise SystemExit('stage_save: %s exists with other content; run `clear` first' % dest)
    h = checked_copy(src, dest)
    print('staged %s sha256 %s\nautostart target: campaign:%s' % (dest, h[:16], fname[:-len(EXT)]))
    return fname[:-len(EXT)]


def staged(save_dir):
    d = Path(save_dir)
    return sorted(p for p in d.iterdir() if p.is_file() and p.name.startswith(PREFIX)) if d.is_dir() else []


def clear(save_dir, state):
    files = staged(save_dir)
    if not files:
        print('nothing staged in %s' % save_dir)
        return []
    out = Path(state) / '_to_delete' / ('saves_' + utc_stamp())
    out.mkdir(parents=True, exist_ok=True)
    for p in files:
        shutil.move(str(p), str(out / p.name))
        print('moved %s -> %s' % (p.name, out))
    return [out / p.name for p in files]


def keep(name, save_dir, state, as_name=None):
    """copy save_games/<name> into <state>/saves/ (read only from then on); same sha already there is fine, other content refuses"""
    src = Path(save_dir) / (name if name.endswith(EXT) else name + EXT)
    if not src.is_file():
        raise SystemExit('stage_save: no save %s' % src)
    if as_name is not None and (os.path.basename(as_name) != as_name or any(c in as_name for c in '<>:"/\\|?*')):
        raise SystemExit('stage_save: refusing --as %r: a plain file name only' % as_name)
    dest_dir = Path(state) / 'saves'
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (as_name or src.name)
    if dest.exists():
        if sha(dest) != sha(src):
            raise SystemExit('stage_save: %s exists with other content; pick another --as name' % dest)
        print('already kept %s (same sha)' % dest)
        return dest
    h = checked_copy(src, dest)
    os.chmod(dest, stat.S_IREAD)   # kept saves are read only on disk: a recipe that writes OUT over its IN fails here
    print('kept %s sha256 %s size %d' % (dest, h, dest.stat().st_size))
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['stage', 'clear', 'list', 'keep'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--save-dir', default=None, help='default: %%APPDATA%%\\The Creative Assembly\\Napoleon\\save_games')
    ap.add_argument('--state', default=DEFAULT_STATE)
    ap.add_argument('--as', dest='as_name')
    a = ap.parse_args(argv)
    save_dir = Path(a.save_dir) if a.save_dir else default_save_dir()
    if a.cmd == 'stage':
        if len(a.args) != 2:
            sys.exit('usage: stage SRC zz_NAME')
        stage(a.args[0], a.args[1], save_dir)
    elif a.cmd == 'clear':
        clear(save_dir, a.state)
    elif a.cmd == 'list':
        for p in staged(save_dir):
            print('%s %d %s' % (p.name, p.stat().st_size, sha(p)[:16]))
    else:
        if len(a.args) != 1:
            sys.exit('usage: keep SAVE_NAME [--as NAME]')
        keep(a.args[0], save_dir, a.state, a.as_name)


if __name__ == '__main__':
    main()
