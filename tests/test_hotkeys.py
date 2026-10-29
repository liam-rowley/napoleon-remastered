"""Host tests for tools/verbs/hotkeys.py: the key-file parser, the clash rules the schema cannot express, and this repo's own registry.

The clash rules (J21): same binding in a clashing context; a bare key that fires with modifiers (ANY with every one, ALLOW_SHIFT with
Shift added); OS combos. They sit over the schema's own unique/F4/combo checks (core backlog B3) and do not replace them. The last test
runs them on registries/hotkeys.jsonl, which is what makes them a gate today: the `tests` gate runs this file.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('hotkeys_verb', ROOT / 'tools' / 'verbs' / 'hotkeys.py')
hk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hk)

# Vanilla rows allowed to be an OS combo: (row id, reason). Empty today: no vanilla binding is one (J21, 2026-10-29).
KNOWN_OS_COMBO = []
# Vanilla pairs allowed to clash: (id, id, reason). The engine takes the mode-specific binding first (unproven, J21 open question).
KNOWN_VANILLA_CLASH = [('vanilla.fps.deselect_all.0', 'vanilla.fps.end_turn.0',
                        'Return deselects (mode all) and ends the turn (campaign): a vanilla double binding')]


def row(rid, binding, context='battle', **kw):
    r = {'id': rid, 'description': rid, 'binding': binding, 'action': rid, 'context': context, 'source': 'mod', 'source_ref': 'test'}
    r.update(kw)
    return r


def wild(rid, binding, kind, context='battle'):
    return row(rid, binding, context, source='vanilla', source_ref=f'x#fps/{rid} modifier={kind}')


def via_folder(rows):
    """The rows as a registry file in a temp folder, read back (the fixtures are small registries, not in-memory lists)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'hotkeys.jsonl'
        p.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()]


def problems(rows, **kw):
    return hk.find_problems(via_folder(rows), **kw)


class ClashRules(unittest.TestCase):
    def test_clean_registry_passes(self):
        self.assertEqual(problems([row('a', 'Ctrl+K'), row('b', 'Ctrl+K', 'campaign'), row('c', 'Alt+K', 'global')]), [])

    def test_same_binding_same_context_names_both_rows(self):
        p = problems([row('mod.one', 'Ctrl+K'), row('vanilla.two', 'Ctrl+K')])
        self.assertEqual(len(p), 1)
        self.assertIn('mod.one', p[0])
        self.assertIn('vanilla.two', p[0])

    def test_global_clashes_with_every_context(self):
        p = problems([row('g', 'K', 'global'), row('c', 'K', 'campaign')])
        self.assertTrue(p and 'g' in p[0] and 'c' in p[0])

    def test_context_family_clashes(self):
        self.assertTrue(problems([row('b', 'K', 'battle'), row('n', 'K', 'battle_naval')]))
        self.assertEqual(problems([row('l', 'K', 'battle_land'), row('n', 'K', 'battle_naval')]), [])

    def test_bare_key_any_takes_every_modifier(self):
        for mods in ('Ctrl+', 'Alt+', 'Shift+', 'Ctrl+Alt+Shift+'):
            p = problems([wild('vanilla.esc', 'Escape', 'ANY'), row('mod.x', mods + 'Escape')])
            self.assertTrue(any('vanilla.esc' in m and 'mod.x' in m for m in p), (mods, p))   # Alt+Escape is also an OS combo

    def test_bare_key_other_context_is_free(self):
        self.assertEqual(problems([wild('v', 'Space', 'ANY', 'battle'), row('m', 'Ctrl+Space', 'campaign')]), [])

    def test_allow_shift_takes_shift_only(self):
        self.assertTrue(problems([wild('v.w', 'W', 'ALLOW_SHIFT'), row('m.shift', 'Shift+W')]))
        self.assertEqual(problems([wild('v.w', 'W', 'ALLOW_SHIFT'), row('m.ctrl', 'Ctrl+W')]), [])

    def test_os_combos_always_fail(self):
        for b in ('Alt+F4', 'Alt+Tab', 'Alt+Esc', 'Alt+Escape', 'Win+E', 'win+d', 'Ctrl+Alt+Delete', 'Ctrl+Shift+Escape', 'Windows+R'):
            p = problems([row('m.os', b, 'campaign')])
            self.assertTrue(p and 'm.os' in p[0] and 'OS combo' in p[0], b)

    def test_vanilla_os_combo_needs_a_known_entry_and_stale_entries_fail(self):
        v = row('vanilla.fps.x.0', 'Alt+Esc', source='vanilla')
        self.assertTrue(problems([v]))
        self.assertEqual(problems([v], known_os_combo=[(v['id'], 'vanilla binds it')]), [])
        self.assertIn('stale', problems([row('vanilla.fps.x.0', 'K')], known_os_combo=[(v['id'], 'r')])[0])
        self.assertIn('stale', problems([], known_os_combo=[(v['id'], 'r')])[0])

    def test_known_clash_must_still_clash(self):
        a, b = row('a', 'K', 'global'), row('b', 'K', 'campaign')
        self.assertEqual(problems([a, b], known_clash=[('a', 'b', 'r')]), [])
        self.assertIn('stale', problems([a, row('b', 'L', 'campaign')], known_clash=[('a', 'b', 'r')])[0])

    def test_free_keys_skip_clashes_f4_and_os_combos(self):
        free = hk.free_keys([row('v', 'K', 'battle'), wild('e', 'Escape', 'ANY', 'global')], contexts=('battle', 'campaign'))
        self.assertNotIn('K', free['battle'])
        self.assertIn('K', free['campaign'])
        for ctx in free.values():
            self.assertFalse({'F4', 'Alt+F4', 'Ctrl+F4'} & set(ctx))


FIXTURE = '''<shortcuts version="32">
  <mode>battle</mode><mode>campaign</mode><mode>all</mode>
  <keyset name="fps"><category name="universal"><group name="g">
    <func name="two_keys"><key modifier="CTRL">0</key><key>0</key></func>
    <func name="shifted"><key modifier="SHIFT">F9</key></func>
    <func name="alted"><key modifier="ALT">S</key></func>
    <func name="escape_menu"><key modifier="ANY">ESCAPE</key></func>
    <func name="step"><key modifier="ALLOW_SHIFT">NUMPAD5</key></func>
    <func name="both"><key>PAGE_UP</key></func>
    <func name="naval"><key modifier="ALT">1</key></func>
    <func name="nomap"><key modifier="CTRL">Q</key></func>
  </group></category></keyset>
  <mappings>
    <mode name="battle"><func name="two_keys" component="c"/><func name="both" component="c"/><func name="naval" component="c"/></mode>
    <mode name="campaign"><func name="shifted" component="c"/><func name="both" component="c"/></mode>
    <mode name="all"><func name="alted" component="c"/><func name="escape_menu" component="c"/><func name="step" component="c"/></mode>
  </mappings>
</shortcuts>'''
CUSTOM = '''<custom_keys version="32"><keyset name="fps"><category name="c"><group name="g">
  <func name="usegroup0" hidden="1"><key modifier="CTRL">0</key><key modifier="NONE">0</key><mapping mode="battle" component="x"/></func>
  <func name="cam_up"><key modifier="ALLOW_SHIFT">X</key><mapping mode="battle" component="x"/><mapping mode="campaign" component="x"/></func>
</group></category></keyset></custom_keys>'''


class Parser(unittest.TestCase):
    def parse(self, text, **kw):
        return hk.parse_keys(text, 'fps', 'f.xml', **kw)

    def test_default_file_rows(self):
        rows, probs = self.parse(FIXTURE, loc={hk.LOC_PREFIX + 'shifted': 'Save view'})
        self.assertEqual(probs, [])
        by = {r['id']: r for r in rows}
        self.assertEqual([by[f'vanilla.fps.two_keys.{n}']['binding'] for n in (0, 1)], ['Ctrl+0', '0'])
        self.assertEqual(by['vanilla.fps.shifted.0']['binding'], 'Shift+F9')
        self.assertEqual(by['vanilla.fps.shifted.0']['context'], 'campaign')
        self.assertEqual(by['vanilla.fps.shifted.0']['description'], 'Save view')
        self.assertEqual(by['vanilla.fps.alted.0']['binding'], 'Alt+S')
        self.assertEqual(by['vanilla.fps.alted.0']['context'], 'global')       # mode all
        self.assertEqual(by['vanilla.fps.both.0']['context'], 'global')        # battle + campaign
        self.assertEqual(by['vanilla.fps.nomap.0']['context'], 'global')       # no mapping
        self.assertEqual(by['vanilla.fps.escape_menu.0']['binding'], 'Escape')
        self.assertTrue(by['vanilla.fps.escape_menu.0']['source_ref'].endswith('modifier=ANY'))
        self.assertEqual(by['vanilla.fps.step.0']['binding'], 'Numpad5')
        self.assertTrue(by['vanilla.fps.step.0']['source_ref'].endswith('modifier=ALLOW_SHIFT'))
        self.assertEqual(by['vanilla.fps.alted.0']['description'], 'alted')    # no loc: the func name
        self.assertEqual(hk.find_problems(rows), [])
        self.assertEqual(self.parse(FIXTURE)[0], rows[:0] + self.parse(FIXTURE)[0])   # same input, same rows

    def test_custom_file_inline_mappings(self):
        rows, probs = self.parse(CUSTOM)
        self.assertEqual(probs, [])
        self.assertEqual([(r['id'], r['binding'], r['context']) for r in rows],
                         [('vanilla.fps.usegroup0.0', 'Ctrl+0', 'battle'), ('vanilla.fps.usegroup0.1', '0', 'battle'),
                          ('vanilla.fps.cam_up.0', 'X', 'global')])

    def test_naval_land_contexts(self):
        self.assertEqual(hk.context_of({'battle'}, 'battle_naval_toggle_boarding'), 'battle_naval')
        self.assertEqual(hk.context_of({'battle'}, 'battle_land_melee'), 'battle_land')
        self.assertEqual(hk.context_of({'battle'}, 'toggle_pause'), 'battle')

    def test_unspellable_and_os_keys_are_problems_naming_the_func(self):
        text = '<s><keyset name="fps"><func name="odd"><key>OEM_102</key></func><func name="win"><key modifier="CTRL">LWIN</key></func>' \
               '<func name="close"><key modifier="ALT">F4</key></func><func name="mod"><key modifier="HYPER">A</key></func>' \
               '<func name="fine"><key>B</key></func></keyset></s>'
        rows, probs = self.parse(text)
        self.assertEqual([r['id'] for r in rows], ['vanilla.fps.fine.0'])
        self.assertEqual(len(probs), 4)
        for name, p in zip(('odd', 'win', 'close', 'mod'), probs):
            self.assertIn(name, p)

    def test_missing_keyset_raises(self):
        with self.assertRaises(ValueError):
            hk.parse_keys(FIXTURE, 'nope', 'f.xml')

    def test_key_spelling(self):
        self.assertEqual([hk.spell_key(k) for k in ('a', '7', 'F12', 'ESCAPE', 'NUMPAD3', 'PAGE_DOWN', 'OEM_102', '')],
                         ['A', '7', 'F12', 'Escape', 'Numpad3', 'PageDown', None, None])


class RealRegistry(unittest.TestCase):
    """registries/hotkeys.jsonl: seeded from the vanilla table, clash-free apart from the listed pairs, and the rules hold on it."""

    def setUp(self):
        text = (ROOT / 'registries' / 'hotkeys.jsonl').read_text(encoding='utf-8')
        self.rows = [json.loads(l) for l in text.splitlines() if l.strip()]

    def test_registry_is_clean(self):
        self.assertEqual(hk.find_problems(self.rows, KNOWN_OS_COMBO, KNOWN_VANILLA_CLASH), [])

    def test_seeded_from_the_vanilla_table(self):
        vanilla = [r for r in self.rows if r['source'] == 'vanilla']
        self.assertGreaterEqual(len(vanilla), 108)
        self.assertEqual(len({r['action'] for r in vanilla}), 108)
        any_keys = {r['action'] for r in vanilla if r['source_ref'].endswith('modifier=ANY')}
        self.assertEqual(any_keys, {'escape_menu', 'toggle_tracking', 'context_camera', 'show_allied_units_proxies'})

    def test_vanilla_alt_rows_are_listed_for_the_gesture(self):
        alt = sorted(r['binding'] for r in self.rows if r['source'] == 'vanilla' and hk.split(r['binding'])[0] == ['Alt'])
        self.assertEqual(alt, sorted(['Alt+S', 'Alt+M'] + [f'Alt+{n}' for n in range(1, 10)] + [f'Alt+{n}' for n in range(1, 5)]))

    def test_mod_rows_obey_the_rules(self):
        for r in self.rows:
            if r['source'] == 'mod':
                self.assertNotIn('win', r['binding'].lower().split('+')[:-1])


if __name__ == '__main__':
    unittest.main()
