"""Host tests for harness/core/ctl.py (J4): the result contract, scenario and pose resolution, tolerance checks, settle, the refusals, and the
rules turned into tests: row 77 (no verb returns ok without a check) and row 78 (no key or click camera moves in scenario rows, generated
files or the acceptance script). No game: a fake transport plays the proxy."""
import importlib.util
import json
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
    def __init__(self, scene='battle_deploy', fail=None):
        self.frame, self.scene, self.fail, self.lines = 0, scene, fail, []

    def __call__(self, line, wait=0):
        self.lines.append(line)
        if line == 'state':
            self.frame += 2
            return 0, {'status': 'ok', 'state': {'scene': self.scene, 'frame': self.frame, 'scene_s': 5.0}}
        if self.fail and line.startswith(self.fail):
            return 1, {'status': 'failed', 'reason': 'engine said no'}
        if line.startswith('autostart'):
            return 0, {'status': 'ok', 'map': 'NAP_MP_Grassy_Flatlands', 'load_s': 3.0}
        if line.startswith('reset'):
            return 0, {'status': 'ok'}
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
        self.assertEqual(r['check']['expected'], {'map': 'NAP_MP_Grassy_Flatlands'})

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


if __name__ == '__main__':
    unittest.main()
