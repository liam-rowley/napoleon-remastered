"""Gate: Napoleon's gesture adapter (J29 over warscape-core W6): the C++ host test of proxy/napoleon/gesture_rules.h and the wiring the
DLL build cannot test off the PC. Runs in `wsc gates` (tests gate).

- The C++ host test tests/cpp/test_gesture_napoleon.cpp (the rules against the core's gesture maths): native g++ when on PATH (CI's
  runner has it); else Docker when the proxy inputs (wsc.toml [ci] inputs) changed against origin/main (CI's ubuntu image plus g++,
  about 40 s); else a skip that says why.
- Source checks: adapter.cpp hands the core a GestureAdapter in the DLL build only (the core's host tests compile adapter.cpp natively,
  where the drivers do not exist), in the core's member order with Napoleon's constants; the controls.gestures config_keys row and its
  generated ini line; the ctl launch keys the layer needs (controls.gestures, dev.orders, dev.camera, the scene tracker's dev.lua_bridge).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ci_inputs import ci  # noqa: E402

TEST = 'tests/cpp/test_gesture_napoleon.cpp'
INCLUDES = ['core/proxy/src', 'proxy/napoleon', 'core/proxy/tests']
FLAGS = ['-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror']
IMAGE = 'ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852'   # core/proxy/tools/build.sh's CI image
OUT = 'build/tests_nap/test_gesture_napoleon'


def compile_cmd(out=OUT):
    return ['g++', *FLAGS, *[f'-I{i}' for i in INCLUDES], '-o', out, TEST]


def route(env, files, which=shutil.which, docker_ok=None):
    """('native'|'docker'|'skip', reason)."""
    if which('g++'):
        return 'native', 'g++ on PATH'
    if env.get('GITHUB_ACTIONS'):
        return 'skip', 'CI without g++ (unexpected on ubuntu-latest)'
    if files is not None and not ci.classify(files)['proxy']:
        return 'skip', 'proxy inputs unchanged against origin/main'
    if (docker_ok or _docker_ok)():
        return 'docker', 'Docker answering'
    return 'skip', 'no g++ and Docker is not answering (start Docker Desktop, or rely on CI)'


def _docker_ok():
    try:
        return subprocess.run(['docker', 'info'], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class HostTest(unittest.TestCase):
    def test_gesture_rules_host_test(self):
        _, files = ci.local_changes(ROOT)
        kind, why = route(os.environ, files)
        if kind == 'skip':
            self.skipTest(f'test_gesture_napoleon NOT RUN: {why}')
        (ROOT / 'build' / 'tests_nap').mkdir(parents=True, exist_ok=True)
        if kind == 'native':
            p = subprocess.run(compile_cmd(), cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = subprocess.run([str(ROOT / OUT)], cwd=ROOT, capture_output=True, text=True, timeout=120)
        else:
            mnt = str(ROOT)
            script = ('set -e; apt-get update -q >/dev/null; DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends g++ '
                      '>/dev/null; ' + ' '.join(compile_cmd()) + f'; ./{OUT}')
            p = subprocess.run(['docker', 'run', '--rm', '-v', f'{mnt}:/src', '-w', '/src', IMAGE, 'bash', '-c', script],
                               capture_output=True, text=True, timeout=540, env=dict(os.environ, MSYS_NO_PATHCONV='1'))
        out = p.stdout + p.stderr
        self.assertEqual(p.returncode, 0, out[-3000:])
        self.assertRegex(out, r'test_gesture_napoleon: \d+ passed, 0 failed')
        print(re.search(r'test_gesture_napoleon: .*', out).group(0), file=sys.stderr)


class Route(unittest.TestCase):
    def test_native_first(self):
        self.assertEqual(route({}, ['docs/x.md'], which=lambda n: '/usr/bin/g++')[0], 'native')

    def test_unchanged_inputs_skip_without_docker(self):
        def no(*_):
            raise AssertionError('docker probed')
        self.assertEqual(route({}, ['docs/x.md'], which=lambda n: None, docker_ok=no)[0], 'skip')

    def test_changed_inputs_use_docker(self):
        for f in ('proxy/napoleon/gesture_rules.h', 'tests/cpp/test_gesture_napoleon.cpp', 'tests/test_gesture_adapter.py', 'viewer/pins.json'):
            self.assertEqual(route({}, [f], which=lambda n: None, docker_ok=lambda: True)[0], 'docker', f)


def adapter_src():
    return (ROOT / 'proxy' / 'napoleon' / 'adapter.cpp').read_text(encoding='utf-8')


class Wiring(unittest.TestCase):
    def test_gesture_adapter_only_in_the_dll_build(self):
        s = adapter_src()
        win = s.index('#ifdef _WIN32\nGestureScene GestScene')
        other = s.index('#else\nconst GestureAdapter* const kGesturePtr = nullptr;')
        self.assertLess(win, other)
        self.assertIn('const GestureAdapter* const kGesturePtr = &kGesture;', s[win:other])
        self.assertRegex(s, r'#ifdef _WIN32\n#include "dev\.h"')

    def test_initialiser_order_matches_the_core(self):
        s = adapter_src()
        m = re.search(r'const GestureAdapter kGesture = \{([^}]*)\};', s)
        got = [x.strip() for x in m.group(1).replace('\n', ' ').split(',')]
        self.assertEqual(got, ['GestScene', 'GestCamera', 'GestGround', 'GestSelection', 'nap::Placeable', 'GestCommit', 'nap::kDragPx',
                               'nap::kShortDragM', 'nap::kMoveMods', 'nap::kRotateMods', 'nap::kPivotFwdM', 'nap::kRotGain', 'nap::kRotSign'])
        core = (ROOT / 'core' / 'proxy' / 'src' / 'adapter.h').read_text(encoding='utf-8')
        body = core[core.index('struct GestureAdapter {'):core.index('};', core.index('struct GestureAdapter {'))]
        members = re.findall(r'\(\*(\w+)\)|^\s*(?:int|double|unsigned)\s+([\w, ]+);', body, re.M)
        names = []
        for fn, data in members:
            names += [fn] if fn else [n.strip() for n in data.split(',')]
        self.assertEqual(names, ['scene', 'cameraRead', 'groundAt', 'selection', 'placeable', 'commit', 'dragPx', 'shortDragM', 'moveMods',
                                 'rotateMods', 'pivotFwdM', 'rotGain', 'rotSign'])

    def test_game_adapter_has_fourteen_members_last_the_gesture(self):
        s = adapter_src()
        m = re.search(r'static const GameAdapter a = \{([^}]*)\};', s)
        got = [x.strip() for x in re.sub(r'//[^\n]*', '', m.group(1)).replace('\n', ' ').split(',')]
        self.assertEqual(len(got), 14)
        self.assertEqual(got[-1], 'kGesturePtr')

    def test_camera_offsets_match_the_fact(self):
        fact = json.loads((ROOT / 'registries' / 'engine_facts' / 'napoleon.battle.camera_route.json').read_text(encoding='utf-8'))
        self.assertIn('position (+8), target (+0x14)', fact['claim'])
        self.assertIn('70.0 degree vertical fov', fact['claim'])
        rules = (ROOT / 'proxy' / 'napoleon' / 'gesture_rules.h').read_text(encoding='utf-8')
        self.assertIn('const int kCamPosOff = 0x8;', rules)
        self.assertIn('const int kCamTargetOff = 0x14;', rules)
        self.assertIn('const double kFovYDeg = 70.0;', rules)

    def test_config_row_and_ini(self):
        rows = [json.loads(l) for l in (ROOT / 'registries' / 'config_keys.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
        r = {x['id']: x for x in rows}['controls.gestures']
        self.assertIs(r['default'], True)
        self.assertIs(r['release_value'], True)
        self.assertEqual(r['owner'], 'proxy')
        ini = (ROOT / 'proxy' / 'napoleon' / 'napoleon_remastered.ini').read_text(encoding='utf-8')
        self.assertRegex(ini, r'\[controls\]\r?\n;[^\n]*\n?gestures=1')

    def test_launch_keys_the_layer_needs(self):
        keys = json.loads((ROOT / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))['ctl']['launch']['keys']
        for k in ('controls.gestures', 'dev.orders', 'dev.camera', 'dev.lua_bridge', 'dev.ctl'):
            self.assertEqual(keys.get(k), '1', k)


if __name__ == '__main__':
    unittest.main()
