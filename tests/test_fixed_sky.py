"""Host tests for proxy/tools/build_fixed_sky_pack.py (J44): the junction encoding round-trips byte for byte, battle_sky_types keeps exactly
one sky per (season, weather, time of day, climate) with "clear" first, and every kept junction row points at a kept sky (no group keeps two:
run 20261030_j44acc pass 1 changed lighting on 1 launch in 6 while one group still had a clear and an overcast sky)."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sky', ROOT / 'proxy' / 'tools' / 'build_fixed_sky_pack.py')
sky = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sky)

NAMES = ['key', 'season', 'weather_type', 'time_of_day', 'climate', 'sky_file', 'supports_ambient_fog', 'supports_volumetric_fog']


def row(key, tod='afternoon', file=None):
    return [key, 'season_summer', 'dry', tod, None, file or f'{key}.environment', False, True]


class FixedSky(unittest.TestCase):
    def test_junction_round_trips(self):
        rows = [('NAP_MP_A', 'day_clear_1'), ('NAP_MP_A', 'day_overcast_1'), ('rti_fort_1', 'evening_clear_2')]
        b = sky.encode_junction(b'\x01', rows)
        self.assertEqual(sky.parse_junction(b), (b'\x01', rows))

    def test_one_sky_per_group_clear_first_and_junction_remapped(self):
        skies = [row('day_overcast_1'), row('day_clear_1'), row('evening_x', 'evening')]
        kept, to = sky.choose_skies(skies, NAMES)
        self.assertEqual([r[0] for r in kept], ['day_clear_1', 'evening_x'])
        self.assertEqual(to['day_overcast_1'], 'day_clear_1')
        j = sky.remap_junction([('A', 'day_overcast_1'), ('A', 'day_clear_1'), ('B', 'day_overcast_1'), ('B', 'evening_x')], to)
        self.assertEqual(j, [('A', 'day_clear_1'), ('B', 'day_clear_1'), ('B', 'evening_x')])
        self.assertTrue({k for _, k in j} <= {r[0] for r in kept})

    def test_table_encoding_round_trips(self):
        fields = [{'name': n, 'type': t} for n, t in zip(NAMES, ['StringU16'] * 4 + ['OptionalStringU16', 'StringU16', 'Boolean', 'Boolean'])]
        b = sky.encode_table(b'\x01', fields, [row('k1'), ['k2', 's', 'w', 't', 'temperate', 'f', True, False]])
        import struct
        self.assertEqual(struct.unpack_from('<I', b, 1)[0], 2)
        self.assertIn('temperate'.encode('utf-16-le'), b)


if __name__ == '__main__':
    unittest.main()
