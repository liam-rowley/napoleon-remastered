#!/usr/bin/env python3
"""J45 PC step a: build a proxy kit as a non-PC machine would, without the fixed-sky pack (its builder made to fail), into OUT.
usage: python3 harness/runs/20261031_j45pc/kit_without_sky.py OUT
Run evidence for jobs/J45/report.md, not a tool: the guard it exercises is ctl.py Pc.file_rule_problems."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'proxy' / 'tools'))
import pc_deploy  # noqa: E402


def no_packs(games):
    raise SystemExit('J45 step a: the game packs are treated as unreadable (a CI kit)')


sys.modules['build_fixed_sky_pack'] = types.SimpleNamespace(build=no_packs)
kit = pc_deploy.build_kit(sys.argv[1])
print(kit)
