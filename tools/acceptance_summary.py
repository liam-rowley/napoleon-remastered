#!/usr/bin/env python3
"""Per-pass summary of acceptance runs (J24): result, build, failed steps and each shot's diff against its threshold.

purpose: print one line per acceptance pass (harness/runs/<id>/pass_*.json): passed, build id, failed steps, and every shot_match diff against its threshold, so a 20-pass run's margins and a flake's step read at a glance
usage: acceptance_summary.py RUN_ID [RUN_ID ...]   (run ids under harness/runs/, or run folder paths)
when: after `core/harness/acceptance.py run`, to see which step a failed pass broke on and how close the shots are to their thresholds (`acceptance.py streak` gives only the count)
not-a-verb: a read-only report over committed run files; core/harness/acceptance.py is the core's and is not changed from a game repo
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summarize_pass(d):
    """One pass file -> {passed, build, failed: [step], shots: {scenario: (diff, threshold)}} (steps are a dict keyed `scenario:check`)."""
    steps = d.get('steps') or {}
    failed = [k for k, v in steps.items() if isinstance(v, dict) and v.get('ok') is False]
    shots = {k.split(':')[0]: (v.get('mean_abs_diff'), v.get('threshold')) for k, v in steps.items()
             if k.endswith(':shot_match') and isinstance(v, dict)}
    return {'passed': d.get('passed'), 'build': d.get('build_id'), 'failed': failed, 'shots': shots}


def run_dir(run):
    p = Path(run)
    return p if p.is_dir() else ROOT / 'harness' / 'runs' / run


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    for run in argv:
        d = run_dir(run)
        passes = sorted(d.glob('pass_*.json'))
        if not passes:
            print(f'{run}: no pass_*.json in {d}')
        for p in passes:
            s = summarize_pass(json.loads(p.read_text(encoding='utf-8')))
            shots = ' '.join(f'{k}={v[0]}/{v[1]}' for k, v in s['shots'].items())
            print(f"{d.name} {p.stem} {'PASS' if s['passed'] else 'FAIL'} {s['build']} failed: {', '.join(s['failed']) or 'none'}")
            if shots:
                print('    shots:', shots)
    return 0


if __name__ == '__main__':
    sys.exit(main())
