"""Throwaway (J42 review): a deliberately failing test so CI's `gates` job fails on a push and the gates.yml `notify` job is proved; reverted next."""
import unittest


class Proof(unittest.TestCase):
    def test_deliberate_failure(self):
        self.fail('J42 review proof d: a red `gates` on a push must comment on PR #57 (gates.yml notify)')
