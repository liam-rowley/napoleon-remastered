#!/usr/bin/env python3
"""Tell an open pull request that its CI failed: one comment naming each failed job and step, the run URL and the class to check first (J42).

purpose: post one comment on the open pull request of a branch whose CI run failed, naming each failed job and its first failed step, the run URL and which docs/CI_FAILURES.md class to check first (with the local route that reproduces it); a run that already commented (a rerun of the same attempt) is not commented again, and a branch with no open pull request gets nothing
usage: python3 tools/ci_notify.py --run-id <id> --attempt <n> --branch <head branch> [--repo owner/name] [--dry-run]   (needs `gh` with GH_TOKEN; CI's `notify` jobs in gates.yml and policy.yml run it)
when: automatic: the last job of a failed gates.yml or policy.yml run; by hand with --dry-run to see the comment a run would get
not-a-verb: CI calls it from a job without the core checkout; one GitHub API call sequence, not a registry operation
"""
import argparse
import json
import subprocess
import sys

MARK = '<!-- ci_notify run {run} attempt {attempt} -->'


def class_hint(job, step):
    """Which docs/CI_FAILURES.md class to check first for a failed job and step, and the local route that reproduces it."""
    step = step or ''
    if job == 'gates':
        return 'branch bug first: `python3 core/wsc.py gates` runs the same checks locally'
    if job == 'policy':
        return 'branch bug: `python3 tools/pr_policy.py --branch <branch> --base origin/main` says what the branch may not change'
    if job == 'proxy':
        if 'wine' in step or 'smoke' in step:
            return 'CI-only test unless `core/proxy/tools/build.sh --docker smoke` ran (the `tests` gate runs it when proxy inputs change)'
        return 'branch bug first: `core/proxy/tools/build.sh --docker all` (the `tests` gate runs it when proxy inputs change)'
    if job == 'harness-windows':
        return ('flaky only if the same commit passed elsewhere: rerun the case with '
                "`gh workflow run gates.yml --ref <branch> -f only='<case>' -f repeat=20`; otherwise branch bug "
                '(`tests/test_harness_host.py` runs the host tests on the PC)')
    if job == 'changes':
        return 'workflow: the input-set step failed (tools/changed_inputs.py)'
    return 'see docs/CI_FAILURES.md'


def failed(jobs):
    """[(job name, first failed step name)] for the jobs of one run attempt that failed or timed out."""
    out = []
    for j in jobs:
        if j.get('conclusion') in ('failure', 'timed_out', 'startup_failure'):
            step = next((s['name'] for s in j.get('steps') or [] if s.get('conclusion') in ('failure', 'timed_out')), '')
            out.append((j['name'], step))
    return out


def message(fails, run, attempt, url, branch):
    lines = [MARK.format(run=run, attempt=attempt),
             f'**CI failed** on `{branch}` ([run {run}]({url}){f", attempt {attempt}" if attempt > 1 else ""}). '
             'A failed check leaves this pull request open (D32); fix it on the branch and push.', '']
    for job, step in fails:
        lines.append(f'- `{job}`{f", step `{step}`" if step else ""}: {class_hint(job, step).replace("<branch>", branch)}')
    lines += ['', 'Classes and their guards: `docs/CI_FAILURES.md`.']
    return '\n'.join(lines)


def gh(args, run=subprocess.run):
    p = run(['gh', *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(f'ci_notify: gh {" ".join(args[:3])} failed: {(p.stderr or p.stdout).strip()[:300]}')
    return p.stdout


def main(argv=None, run=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run-id', required=True, type=int)
    ap.add_argument('--attempt', type=int, default=1)
    ap.add_argument('--branch', required=True)
    ap.add_argument('--repo', default='')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    repo = ['--repo', a.repo] if a.repo else []
    prs = json.loads(gh(['pr', 'list', *repo, '--head', a.branch, '--state', 'open', '--json', 'number'], run) or '[]')
    if not prs:
        print(f'ci_notify: {a.branch} has no open pull request: nothing to tell')
        return 0
    num = prs[0]['number']
    api = f'repos/{a.repo or "{owner}/{repo}"}'
    jobs = json.loads(gh(['api', f'{api}/actions/runs/{a.run_id}/attempts/{a.attempt}/jobs'], run))['jobs']
    fails = failed(jobs)
    if not fails:
        print(f'ci_notify: run {a.run_id} attempt {a.attempt} has no failed job (cancelled?): nothing to tell')
        return 0
    seen = gh(['api', '--paginate', f'{api}/issues/{num}/comments', '--jq', '.[].body'], run)
    if MARK.format(run=a.run_id, attempt=a.attempt) in seen:
        print(f'ci_notify: PR #{num} already has the comment for run {a.run_id} attempt {a.attempt}')
        return 0
    url = json.loads(gh(['api', f'{api}/actions/runs/{a.run_id}', '--jq', '{u: .html_url}'], run))['u']
    body = message(fails, a.run_id, a.attempt, url, a.branch)
    if a.dry_run:
        print(f'ci_notify: would comment on PR #{num}:\n{body}')
        return 0
    gh(['pr', 'comment', str(num), *repo, '--body', body], run)
    print(f'ci_notify: commented on PR #{num}: {", ".join(j for j, _ in fails)} failed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
