"""Host tests for harness/core/ctl.py (J4): the result contract, scenario and pose resolution, tolerance checks, settle, the refusals, and the
rules turned into tests: row 77 (no verb returns ok without a check) and row 78 (no key or click camera moves in scenario rows, generated
files or the acceptance script). No game: a fake transport plays the proxy."""
import importlib.util
import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ctl', ROOT / 'harness' / 'core' / 'ctl.py')
ctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctl)

ROWS = {
    'land_small': {'id': 'land_small', 'kind': 'land', 'map': 'NAP_MP_Grassy_Flatlands', 'camera_poses': {'wide': {'x': 1, 'y': 2, 'z': 3, 'yaw': 90, 'pitch': -30}}},
    'hist': {'id': 'hist', 'kind': 'historical', 'map': 'x'},
    'camp': {'id': 'camp', 'kind': 'campaign', 'map': 'mp_eur_napoleon', 'save': 's'},
}
ADAPTER = {'game': 'napoleon', 'ctl': {'settle': {'frames': 3, 'quiet_ms': 1000, 'timeout_s': 5, 'ready_scenes': ['battle_deploy']},
                                        'routes': {'camera': {'status': 'unreachable', 'why': 'no api', 'fact': 'f.x'}}}}


class FakeGame:
    """Answers ctl lines; the frame counter advances 2 per state call."""
    def __init__(self, scene='battle_deploy', fail=None, here='frontend'):
        self.frame, self.scene, self.fail, self.lines, self.here = 0, scene, fail, [], here   # here: the scene until an autostart or reset

    def __call__(self, line, wait=0):
        self.lines.append(line)
        if line == 'state':
            self.frame += 2
            return 0, {'status': 'ok', 'state': {'scene': self.here or self.scene, 'frame': self.frame, 'scene_s': 5.0}}
        if self.fail and line.startswith(self.fail):
            return 1, {'status': 'failed', 'reason': 'engine said no'}
        if line.startswith('autostart'):
            self.here = None
            return 0, {'status': 'ok', 'map': 'NAP_MP_Grassy_Flatlands', 'load_s': 3.0}
        if line.startswith('reset'):
            self.here = None if 'frontend' not in line else 'frontend'
            return 0, {'status': 'ok', 'autostart': {'map': 'NAP_MP_Grassy_Flatlands', 'load_s': 2.5}}
        if line.startswith('perf'):
            return 0, {'status': 'ok', 'frames': 600, 'frame_ms': {'p50': 16.6, 'p99': 20.0, 'max': 30.0}, 'mem': {'va_used_mb': 1700}}
        return 1, None


def make(game=None, **kw):
    clock = [0.0]
    def now():
        clock[0] += 0.5
        return clock[0]
    return ctl.Ctl(game or FakeGame(), ROWS, ADAPTER, battles_dir=ROOT / 'proxy' / 'napoleon' / 'lua' / 'battles', clock=now, sleep=lambda s: None, **kw)


class Contract(unittest.TestCase):
    def test_every_result_has_the_contract_fields(self):
        r = make().run('state')
        for k in ('status', 'reason', 'settle', 'check', 'evidence', 'start_utc', 'end_utc'):
            self.assertIn(k, r)
        self.assertEqual(ctl.exit_code(r), 0)

    def test_row77_ok_without_a_check_becomes_failed(self):
        r = ctl.make_result('x', 'ok')
        self.assertEqual(r['status'], 'failed')
        self.assertIn('rule 77', r['reason'])

    def test_row77_no_verb_returns_ok_without_a_check(self):
        """Every verb that can answer ok in the fake game carries a non-empty check; the verbs that cannot are refused with a reason."""
        c = make(shotter=lambda name: (f'/tmp/{name}.jpg', 1000))
        answers = [c.run('state'), c.run('scene', 'land_small'), c.run('shot', 'a'), c.run('reset'), c.run('reset', 'land_small'), c.run('perf', '10'),
                   c.run('cam', 'land_small:wide'), c.run('order', 'u', 'halt'), c.run('pause', 'on'), c.run('speed', '2')]
        for r in answers:
            if r['status'] == 'ok':
                self.assertTrue(r['check'], r['verb'])
            else:
                self.assertTrue(r['reason'], r['verb'])
        self.assertEqual([r['status'] for r in answers[:6]], ['ok'] * 6)

    def test_exit_codes(self):
        self.assertEqual([ctl.exit_code({'status': s}) for s in ('ok', 'failed', 'refused')], [0, 1, 2])


class Scenes(unittest.TestCase):
    def test_unknown_scenario_is_refused_with_the_known_ids(self):
        r = make().run('scene', 'nope')
        self.assertEqual(r['status'], 'refused')
        self.assertIn('land_small', r['reason'])

    def test_scene_resolves_a_preset_and_settles(self):
        g = FakeGame()
        r = make(g).run('scene', 'land_small')
        self.assertEqual(r['status'], 'ok')
        self.assertIn('autostart battle:land_small 240', g.lines)
        self.assertTrue(r['settle']['settled'])
        self.assertEqual(r['check']['expected'], {'map': 'NAP_MP_Grassy_Flatlands', 'deployment': 'running'})

    def test_historical_and_campaign_name_their_open_state(self):
        self.assertIn('historical', make().run('scene', 'hist')['reason'])
        self.assertEqual(make().run('scene', 'camp')['status'], 'refused')

    def test_autostart_failure_names_the_step_and_keeps_evidence(self):
        r = make(FakeGame(fail='autostart')).run('scene', 'land_small')
        self.assertEqual(r['status'], 'failed')
        self.assertIn('step autostart battle:land_small', r['reason'])
        self.assertIn('ctl', r['evidence'])

    def test_settle_times_out_when_the_scene_never_becomes_ready(self):
        r = make(FakeGame(scene='loading')).run('scene', 'land_small')
        self.assertEqual(r['status'], 'failed')
        self.assertIn('step settle', r['reason'])
        self.assertFalse(r['settle']['settled'])


class Poses(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(ctl.parse_pose('1 2 3 90 -30'), {'x': 1, 'y': 2, 'z': 3, 'yaw': 90, 'pitch': -30})
        self.assertEqual(ctl.parse_pose('1,2,3,90,-30,45')['fov'], 45)
        for bad in ('1 2 3', '1 2 3 a b', ''):
            with self.assertRaises(ctl.Refused):
                ctl.parse_pose(bad)

    def test_resolve_by_id_and_errors(self):
        self.assertEqual(ctl.resolve_pose(ROWS, 'land_small:wide')['yaw'], 90)
        with self.assertRaises(ctl.Refused):
            ctl.resolve_pose(ROWS, 'land_small:nope')
        with self.assertRaises(ctl.Refused):
            ctl.resolve_pose(ROWS, 'ghost:wide')

    def test_tolerance(self):
        exp = {'x': 10, 'y': 5, 'z': 0, 'yaw': 359, 'pitch': -30}
        ok, d = ctl.pose_check(exp, {'x': 10.2, 'y': 5, 'z': 0, 'yaw': 1, 'pitch': -30.1}, {'default': 0.5, 'yaw': 3})
        self.assertTrue(ok, d)   # yaw wraps: 359 against 1 is 2 degrees
        ok, d = ctl.pose_check(exp, {'x': 12, 'y': 5, 'z': 0, 'yaw': 359, 'pitch': -30}, {'default': 0.5})
        self.assertFalse(ok)
        self.assertFalse(d['x']['within'])
        ok, _ = ctl.pose_check(exp, {'x': 10}, {'default': 0.5})
        self.assertFalse(ok)   # a missing readback fails


class Refusals(unittest.TestCase):
    def test_unreachable_routes_refuse_with_reason_and_fact(self):
        r = make().run('cam', 'land_small:wide')
        self.assertEqual(r['status'], 'refused')
        self.assertIn('no api', r['reason'])
        self.assertIn('f.x', r['reason'])
        self.assertEqual(make().run('order', 'u', 'halt')['status'], 'refused')

    def test_bad_arguments_are_refused(self):
        self.assertEqual(make().run('pause', 'maybe')['status'], 'refused')
        self.assertEqual(make().run('speed', 'fast')['status'], 'refused')
        self.assertEqual(make(shotter=lambda n: ('p', 1)).run('shot', '../x')['status'], 'refused')

    def test_perf_checks_its_numbers(self):
        r = make().run('perf', '10')
        self.assertEqual(r['frame_ms']['p50'], 16.6)
        self.assertEqual(r['frames'], 600)

    def test_main_refuses_probe_verbs_and_unknown_verbs(self):
        for v in ctl.PROBE_ONLY + ('bogus',):
            self.assertEqual(ctl.main([v]), 2)


class Rule78(unittest.TestCase):
    """Camera poses are stored by id, never as key-tap scripts: scenario rows, generated files and the acceptance script carry no key/click moves."""
    BAD = re.compile(r'(\bctl\b.*[\'"]\s*(key|click)\s|\bjob\.sh\s+ctl\b.*\b(key|click)\b|[\'"](key|click)\s+\S)')

    def files(self):
        out = [ROOT / 'registries' / 'scenarios.jsonl']
        out += sorted((ROOT / 'proxy' / 'napoleon' / 'lua' / 'battles').glob('*.txt'))
        out += [p for p in [ROOT / 'harness' / 'core' / 'acceptance.py'] if p.exists()]
        return out

    def test_no_key_or_click_in_scenario_rows_generated_files_or_acceptance(self):
        for p in self.files():
            for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
                self.assertIsNone(self.BAD.search(line), f'{p.name}:{n} moves the camera with key or click: store a pose by id (rule 78)')

    def test_the_rule_catches_a_violation(self):
        self.assertIsNotNone(self.BAD.search('job.sh ctl me "key w"'))
        self.assertIsNotNone(self.BAD.search('"click 10 20"'))
        self.assertIsNone(self.BAD.search('"scene land_small"'))


# ---- J43: cam, pause and speed through per-kind routes, against a game that projects a real pinhole camera ----------------------------
campose = ctl.campose
CAM = {'status': 'reachable', 'why': 'w', 'fact': 'f.cam', 'set': 'S.lua', 'read': 'R.lua', 'settle_ms': 200, 'max_rms_px': 0.05,
       'tolerance': {'x': 0.05, 'y': 0.05, 'z': 0.05, 'yaw': 0.05, 'pitch': 0.05, 'fov': 0.05},
       'clamps': {'pitch': [-45, 45], 'height_above_terrain': [2.5, 44.556]}}
CLOCK = {'status': 'reachable', 'why': 'w', 'fact': 'f.speed', 'chunk': 'C.lua', 'lead_s': 0.5, 'measure_s': 4}
ROUTES = {'camera': {'land': CAM, 'naval': {'status': 'unknown', 'why': 'not probed at sea', 'fact': 'f.naval'}},
          'speed': {'land': dict(CLOCK, rates={'0.5': 'slow', '1': 'play', '2': 'fwd', '4': 'ffwd'}, measured={'slow': 0.43}, tolerance=0.1)},
          'pause': {'land': dict(CLOCK, tolerance=0.02, min_running_rate=0.25)}}
ADAPTER2 = {'game': 'napoleon', 'ctl': {'settle': ADAPTER['ctl']['settle'], 'routes': ROUTES}}


def cam_read_text(pose, w=1920, h=1080, fov=70.0):
    """What ctl/cam_read.lua returns for a camera at `pose`: C, S and a 3x3x3 cluster 100 m ahead (as the chunk builds it)."""
    c = [pose['x'], pose['y'], pose['z']]
    yaw, pitch = math.radians(pose['yaw']), math.radians(pose['pitch'])
    f = (h / 2) / math.tan(math.radians(fov / 2))
    fw = (math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch))
    pts = []
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            for oz in (-1, 0, 1):
                p = [c[k] + 100 * fw[k] + 20 * o for k, o in enumerate((ox, oy, oz))]
                sx, sy = campose.project(c, yaw, pitch, f, p, w, h)
                pts.append(f'{p[0]:.3f},{p[1]:.3f},{p[2]:.3f},{sx:.4f},{sy:.4f},0.99,{math.dist(p, c):.4f}')
    return f'cam C={c[0]:.4f},{c[1]:.4f},{c[2]:.4f} S={w},{h} P=' + ';'.join(pts)


class CamGame(FakeGame):
    """A battle: cam_set moves the camera (height clamped like the engine), speed.lua runs a battle clock against a windows clock."""
    def __init__(self, naval=0, conflict=True, ground=15.0, rates=None):
        super().__init__(scene='battle')
        self.naval, self.conflict, self.ground = naval, conflict, ground
        self.pose = {'x': 0, 'y': 59, 'z': 446, 'yaw': 180, 'pitch': -25}
        self.wt, self.ebt, self.tick, self.paused = 1000.0, 50.0, 'play', False
        self.rates = rates or {'slow': 0.43, 'play': 1.0, 'fwd': 2.0, 'ffwd': 4.0}

    def advance(self, s):
        self.wt += s
        if self.conflict and not self.paused:
            self.ebt += s * self.rates[self.tick]

    def __call__(self, line, wait=0):
        if line == 'state':
            self.lines.append(line)
            self.frame += 2
            return 0, {'status': 'ok', 'state': {'scene': self.scene, 'frame': self.frame, 'scene_s': 5.0, 'battle': {'naval': self.naval}}}
        if not line.startswith('lua '):
            return super().__call__(line, wait)
        self.lines.append(line)
        args = line.split(' -- ', 1)[1] if ' -- ' in line else ''
        if line.startswith('lua S.lua'):
            x, y, z, yaw, pitch = (float(v) for v in args.split(','))
            y = min(max(y, self.ground + 2.5), self.ground + 44.556)
            self.pose = {'x': x, 'y': y, 'z': z, 'yaw': yaw, 'pitch': max(-45, min(45, pitch))}
            return 0, {'status': 'ok', 'chunk': 'cam_set ok'}
        if line.startswith('lua R.lua'):
            return 0, {'status': 'ok', 'chunk': cam_read_text(self.pose)}
        if line.startswith('lua C.lua'):
            said = ''
            if args == 'pause':
                self.paused, said = True, 'set=pause '
            elif args == 'resume':
                self.paused, said = False, 'set=resume '
            elif args in self.rates:
                self.tick, self.paused, said = args, False, f'set={args} '
            self.advance(0.1)
            tick = 'pause' if self.paused else self.tick
            return 0, {'status': 'ok', 'chunk': f'speed {said}ebt={self.ebt} wt={self.wt} tick={tick} conflict={"true" if self.conflict else "false"}'}
        return 1, None


def make2(game):
    return ctl.Ctl(game, ROWS, ADAPTER2, battles_dir=ROOT / 'proxy' / 'napoleon' / 'lua' / 'battles', clock=lambda: 0.0, sleep=game.advance)


class CamPose(unittest.TestCase):
    def test_the_solver_returns_the_pose_it_was_given(self):
        for pose in ({'x': 10, 'y': 50, 'z': 300, 'yaw': 90, 'pitch': -30}, {'x': -150, 'y': 45, 'z': 50, 'yaw': -45, 'pitch': 10},
                     {'x': 0, 'y': 59.02, 'z': 446.14, 'yaw': 180, 'pitch': -25}):
            got = campose.solve(campose.parse(cam_read_text(pose)))
            for k in ('x', 'y', 'z', 'pitch'):
                self.assertAlmostEqual(got[k], pose[k], delta=0.01)
            self.assertAlmostEqual(min(abs(got['yaw'] - pose['yaw']), 360 - abs(got['yaw'] - pose['yaw'])), 0, delta=0.01)
            self.assertAlmostEqual(got['fov'], 70.0, delta=0.01)
            self.assertLess(got['rms_px'], 0.01)

    def test_unreadable_and_empty_results_raise(self):
        for text in ('', 'cam none: no BattleUI.BackProjectPosition (not a battle?)', 'cam C=1,2 S=1920,1080 P='):
            with self.assertRaises(campose.PoseError):
                campose.solve(campose.parse(text))


class CamVerb(unittest.TestCase):
    def test_a_pose_is_set_read_back_and_checked(self):
        g = CamGame()
        r = make2(g).run('cam', '10', '30', '300', '90', '-30')
        self.assertEqual(r['status'], 'ok', r['reason'])
        self.assertTrue(r['check']['ok'])
        self.assertEqual(r['kind'], 'land')
        self.assertTrue(all(f['within'] for f in r['check']['fields'].values()))
        self.assertTrue(any(l.startswith('lua S.lua 20 -- 10.0,30.0,300.0,90.0,-30.0') for l in g.lines))

    def test_a_named_pose_resolves_from_the_scenario_row(self):
        g = CamGame()
        g.ground = -10   # the row's pose (y 2) is 12 m above this ground: inside the clamp
        r = make2(g).run('cam', 'land_small:wide')
        self.assertEqual(r['status'], 'ok', r['reason'])

    def test_a_clamped_height_fails_and_names_the_clamp(self):
        r = make2(CamGame()).run('cam', '10', '200', '300', '90', '-30')
        self.assertEqual(r['status'], 'failed')
        self.assertIn('height above terrain', r['reason'])
        self.assertFalse(r['check']['fields']['y']['within'])

    def test_a_pitch_outside_the_clamp_is_refused_before_any_set(self):
        g = CamGame()
        r = make2(g).run('cam', '10', '30', '300', '90', '-60')
        self.assertEqual(r['status'], 'refused')
        self.assertFalse(any(l.startswith('lua S.lua') for l in g.lines))

    def test_the_route_is_chosen_per_kind(self):
        r = make2(CamGame(naval=1)).run('cam', '10', '30', '300', '90', '-30')
        self.assertEqual(r['status'], 'refused')
        self.assertIn('camera (naval)', r['reason'])
        self.assertIn('f.naval', r['reason'])

    def test_a_refused_set_fails_the_verb(self):
        class NoCam(CamGame):
            def __call__(self, line, wait=0):
                if line.startswith('lua S.lua'):
                    return 0, {'status': 'ok', 'chunk': 'cam_set refused: dev.camera=0'}
                return super().__call__(line, wait)
        r = make2(NoCam()).run('cam', '10', '30', '300', '90', '-30')
        self.assertEqual(r['status'], 'failed')
        self.assertIn('dev.camera=0', r['reason'])


class SpeedAndPause(unittest.TestCase):
    def test_each_offered_speed_is_set_and_measured(self):
        for x, tick in (('2', 'fwd'), ('4', 'ffwd'), ('1', 'play'), ('0.5', 'slow')):
            r = make2(CamGame()).run('speed', x)
            self.assertEqual(r['status'], 'ok', (x, r['reason'], r['check']))
            self.assertEqual(r['check']['got']['tick'], tick)

    def test_slow_is_checked_against_its_measured_rate(self):
        r = make2(CamGame(rates={'slow': 0.5, 'play': 1.0, 'fwd': 2.0, 'ffwd': 4.0})).run('speed', '0.5')
        self.assertEqual(r['status'], 'failed')   # the engine's slow is 0.43, a clock at 0.5 is not it

    def test_a_speed_the_engine_does_not_offer_is_refused(self):
        self.assertEqual(make2(CamGame()).run('speed', '3')['status'], 'refused')

    def test_deployment_is_refused_and_nothing_is_set(self):
        g = CamGame(conflict=False)
        r = make2(g).run('speed', '2')
        self.assertEqual(r['status'], 'refused')
        self.assertIn('deployment', r['reason'])
        self.assertFalse(any(l.endswith('-- fwd') for l in g.lines))
        self.assertEqual(g.tick, 'play')

    def test_pause_on_stops_the_clock_and_off_resumes_it(self):
        g = CamGame()
        c = make2(g)
        r = c.run('pause', 'on')
        self.assertEqual(r['status'], 'ok', r['check'])
        self.assertEqual(r['check']['got'], 0.0)
        r = c.run('pause', 'off')
        self.assertEqual(r['status'], 'ok', r['check'])
        self.assertGreater(r['check']['got'], 0.9)

    def test_a_clock_that_does_not_stop_fails_pause(self):
        class NoPause(CamGame):
            def __call__(self, line, wait=0):
                return super().__call__(line.replace('-- pause', '-- read'), wait)
        self.assertEqual(make2(NoPause()).run('pause', 'on')['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
