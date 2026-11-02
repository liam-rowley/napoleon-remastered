"""The old tools/changed_inputs.py API (classify, local_changes, changed_files) over warscape-core's `warscape.ci` and this repo's `wsc.toml` [ci] inputs.

Not a test: tests/test_proxy_host.py and tests/test_harness_host.py import `ci` from here to skip their slow host tests when nothing they build from changed
(J41, J54); the input sets themselves are configuration now (napoleon J62), so there is one list for CI and for these gates.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'core'))
from warscape import ci as _ci  # noqa: E402
from warscape.repo import load_config  # noqa: E402


class ci:
    SETS = _ci.input_sets(load_config(ROOT)['ci'])

    @staticmethod
    def classify(files):
        return _ci.classify(files, ci.SETS)

    @staticmethod
    def local_changes(root, git=None):
        return _ci.local_changes(root, git or _ci._git)

    @staticmethod
    def changed_files(root, base, git=None):
        return _ci.changed_files(root, base, 'HEAD', git or _ci._git)

    @staticmethod
    def known_commit(root, base, git=None):
        return _ci.known_commit(root, base, git or _ci._git)
