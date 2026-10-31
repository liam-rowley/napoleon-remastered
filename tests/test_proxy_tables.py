"""Gate: the proxy's generated tables (proxy/<game>/generated/tables.h and the default config) are current and every engine site
and config key is valid (core/proxy/tools/gen_tables.py --check). Runs in `wsc gates` (tests gate) on every push."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProxyTables(unittest.TestCase):
    def test_generated_tables_current(self):
        p = subprocess.run([sys.executable, str(ROOT / 'core/proxy/tools/gen_tables.py'), '--check'], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()
