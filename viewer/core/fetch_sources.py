#!/usr/bin/env python3
"""Fetch the review viewer's pinned sources (RmlUi, FreeType by commit; Lua 5.1.1 and stb_image.h by sha256) and patch Lua to float numbers.

purpose: fetch RmlUi, FreeType, Lua and stb_image at the commits and sha256 in viewer/pins.json into build/viewer/src, check each, patch luaconf.h to float
usage: python3 viewer/core/fetch_sources.py [--pins viewer/pins.json] [--out build/viewer/src]
when: viewer/core/build.sh runs it before the wasm build (inside the emsdk container: python 3.10, git); never commit the output
not-a-verb: needs network and writes build output, not a registry operation; build.sh calls it

Lua's number type follows the engine (a 4-byte float lua_Number: discovery/core/luachunk.py). The luaconf.h edits are the
number-type half of core/proxy/tools/fetch_lua.py's patches (the proxy's dummynode and GC patches are for running on the engine's own
lua_State and do not apply here: the viewer owns its state). The viewer keeps Lua's standard libraries.
"""
import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LUACONF = [
    ('#define LUA_NUMBER_DOUBLE\n#define LUA_NUMBER\tdouble', '#define LUA_NUMBER\tfloat   /* Warscape engine build */'),
    ('#define LUA_NUMBER_SCAN\t\t"%lf"', '#define LUA_NUMBER_SCAN\t\t"%f"'),
    ('#define LUA_NUMBER_FMT\t\t"%.14g"', '#define LUA_NUMBER_FMT\t\t"%.7g"'),
    ('#define lua_str2number(s,p)\tstrtod((s), (p))', '#define lua_str2number(s,p)\t((float)strtod((s), (p)))'),
]


def git(*args, cwd):
    return subprocess.run(['git', '-c', 'safe.directory=*', '-c', 'advice.detachedHead=false', *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def fetch_git(name, pin, out):
    d = out / name
    if (d / '.git').exists() and git('rev-parse', 'HEAD', cwd=d) == pin['commit']:
        print(f'fetch_sources: {name} {pin["version"]} at {pin["commit"][:12]} already')
        return
    d.mkdir(parents=True, exist_ok=True)
    if not (d / '.git').exists():
        git('init', '-q', cwd=d)
    git('fetch', '-q', '--depth', '1', pin['repo'], pin['commit'], cwd=d)
    git('checkout', '-q', '--force', 'FETCH_HEAD', cwd=d)
    head = git('rev-parse', 'HEAD', cwd=d)
    if head != pin['commit']:
        sys.exit(f'fetch_sources: {name}: HEAD {head} is not the pinned {pin["commit"]}')
    print(f'fetch_sources: {name} {pin["version"]} at {head[:12]}')


def fetch_lua(pin, out):
    d = out / 'lua'
    stamp = d / 'PATCHED'
    if stamp.exists() and stamp.read_text().strip() == pin['sha256']:
        print(f'fetch_sources: lua {pin["version"]} already patched')
        return
    cache = out / 'downloads' / Path(pin['url']).name
    data = cache.read_bytes() if cache.exists() else None
    if data is None or hashlib.sha256(data).hexdigest() != pin['sha256']:
        with urllib.request.urlopen(pin['url'], timeout=120) as r:
            data = r.read()
        got = hashlib.sha256(data).hexdigest()
        if got != pin['sha256']:
            sys.exit(f'fetch_sources: lua tarball sha256 {got} is not the pinned {pin["sha256"]}')
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(data)
    src = d / 'src'
    src.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as t:
        for m in t.getmembers():
            p = Path(m.name)
            if m.isfile() and len(p.parts) == 3 and p.parts[1] == 'src' and p.suffix in ('.c', '.h'):
                (src / p.name).write_bytes(t.extractfile(m).read())
    conf = (src / 'luaconf.h').read_text()
    for old, new in LUACONF:
        if conf.count(old) != 1:
            sys.exit(f'fetch_sources: luaconf.h patch does not apply: {old!r}')
        conf = conf.replace(old, new)
    (src / 'luaconf.h').write_text(conf, newline='\n')
    stamp.write_text(pin['sha256'] + '\n')
    print(f'fetch_sources: lua {pin["version"]} fetched and patched to float numbers')


def fetch_file(name, pin, out):
    dest = out / name / Path(pin['url']).name
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == pin['sha256']:
        print(f'fetch_sources: {name} {pin["version"]} already')
        return
    with urllib.request.urlopen(pin['url'], timeout=120) as r:
        data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != pin['sha256']:
        sys.exit(f'fetch_sources: {name} sha256 {got} is not the pinned {pin["sha256"]}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f'fetch_sources: {name} {pin["version"]} fetched')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--pins', default=str(ROOT / 'viewer' / 'pins.json'))
    ap.add_argument('--out', default=str(ROOT / 'build' / 'viewer' / 'src'))
    a = ap.parse_args()
    pins = json.loads(Path(a.pins).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fetch_git('rmlui', pins['rmlui'], out)
    fetch_git('freetype', pins['freetype'], out)
    fetch_lua(pins['lua'], out)
    fetch_file('stb', pins['stb_image'], out)


if __name__ == '__main__':
    main()
