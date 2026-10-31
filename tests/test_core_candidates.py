"""Host test (J12): the files that move to warscape-core name no game. The game-name lint J13 wrote for display_guard.h and headless.cpp,
extended to every moved file: a moved file that said "Napoleon" (a path, an exe name, a mod folder, a fact id) would carry the game into
the core. Provenance links to the earlier remaster's repo (`empire-remastered ...`) are allowed. After the move the core keeps the same
lint over its own tree (warscape-core tests/test_no_game_names.py).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# the move set (jobs/J12/brief.md "Decisions"): folders whole, plus the generic proxy tools
MOVE_DIRS = ['proxy/core', 'proxy/tests', 'harness/core', 'harness/tests', 'saves/core', 'proxy/tools/wer']
MOVE_FILES = ['proxy/tools/' + n for n in ('build.sh', 'build_id.py', 'layout.py', 'gen_tables.py', 'fetch_dxvk.py', 'fetch_lua.py', 'pc_deploy.py',
                                           'timeline_table.py', 'survey_table.py', 'pack_list.py', 'luac_list.py', 'build_dev_pack.py')]
GAME = re.compile(r'napoleon|empire(?!-remastered)', re.I)


def moved_files():
    out = [ROOT / f for f in MOVE_FILES]
    for d in MOVE_DIRS:
        out += [p for p in (ROOT / d).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return out


class NoGameNames(unittest.TestCase):
    def test_every_moved_file_exists(self):
        self.assertEqual([str(p) for p in moved_files() if not p.is_file()], [])

    def test_no_moved_file_names_a_game(self):
        bad = []
        for p in moved_files():
            for n, line in enumerate(p.read_bytes().decode('utf-8', 'replace').splitlines(), 1):
                if GAME.search(line):
                    bad.append(f'{p.relative_to(ROOT).as_posix()}:{n}: {line.strip()[:120]}')
        self.assertEqual(bad, [], 'a file that moves to warscape-core names a game (say "the game", or take it from the adapter):\n' + '\n'.join(bad))

    def test_failing_fixture_the_pattern(self):
        for s in ('Napoleon.exe', 'proxy/napoleon/identity.json', 'Empire 5.0', 'napoleon_remastered.ini'):
            self.assertTrue(GAME.search(s), s)
        for s in ('ported from empire-remastered rml_mod/src', 'the earlier remaster', 'Game.exe'):
            self.assertFalse(GAME.search(s), s)


if __name__ == '__main__':
    unittest.main()
