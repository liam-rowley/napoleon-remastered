#!/usr/bin/env python3
"""Pull-request policy: every change reaches main through the job queue (D16, D21).

Purpose: Refuse a pull request whose branch is not a reviewed job, a brief, a planning change or a repo-infrastructure change.
Usage: python3 tools/pr_policy.py --branch <head branch> [--base origin/main]   (CI runs it on every pull request)
When: automatic in CI (`policy` job); locally before opening a pull request to see what CI will say.
Not-a-verb: it reads pull-request metadata that only CI has; it becomes a core gate once warscape-core supports game gates (backlog B1).

Branch kinds (the branch name decides):
  job/J<n>    any files, but only row J<n> of the jobs registry; jobs/J<n>/brief.md must already be on the base; the branch must
              carry jobs/J<n>/report.md and jobs/J<n>/review.md whose verdict line says exactly "merge"; row J<n> must be `done`;
              no session (`Claude-Session:` commit trailer) that wrote the report may write the review (never review your own job).
  brief/J<n>  only jobs/J<n>/brief.md and the jobs registry (row J<n>, which must be `queued` with its brief).
  plan/*      planning: docs, briefs, the jobs registry, README.md, CLAUDE.md. No code.
  meta/*      repo infrastructure: CI, tools/, tests/, schemas/, wsc.toml, git attributes and ignores, the core pin, registries,
              plus everything plan/* may touch. No game code (proxy/ and later feature folders).
Anything else is refused.
Every branch kind: `docs/DECISIONS.md` is append only (existing rows unchanged and in order; new rows numbered D<last+1>, D<last+2>,
with a YYYY-MM-DD date and Reversible yes or no). A reversal is a new row that names the one it replaces.
"""
import argparse
import json
import re
import subprocess
import sys
from fnmatch import fnmatchcase

PLAN = ['docs/*', 'docs/**', 'jobs/*/brief.md', 'registries/jobs.jsonl', 'registries/jobs.md', 'README.md', 'CLAUDE.md']
META = PLAN + ['.github/**', 'tools/*', 'tools/**', 'tests/*', 'tests/**', 'schemas/*', 'wsc.toml', '.gitattributes', '.gitignore',
               '.gitmodules', 'core', 'registries/*']
JOBS = 'registries/jobs.jsonl'


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def show(ref, path):
    """File text at ref, or None when it does not exist there."""
    try:
        return git('show', f'{ref}:{path}')
    except subprocess.CalledProcessError:
        return None


def rows(text):
    out = {}
    for line in (text or '').splitlines():
        if line.strip():
            r = json.loads(line)
            out[r['id']] = r
    return out


def verdict(review_text):
    """The verdict word(s) from a `Verdict: ...` line ('merge', 'merge after fixes', 'do not merge'), lower case, or None."""
    for line in (review_text or '').splitlines():
        m = re.search(r'verdict\s*:\s*(.+)', line.replace('*', ''), re.I)
        if m:
            return m.group(1).split('.')[0].strip().lower()   # up to the first full stop: '**Verdict: merge.** Looks good' -> 'merge'
    return None


DECISIONS = 'docs/DECISIONS.md'
DROW = re.compile(r'^\|\s*D(\d+)\s*\|')


def decisions_problems(base_text, head_text):
    """Errors when the head DECISIONS.md is not the base's rows plus well-formed new rows at the end."""
    rows = lambda t: [l.rstrip() for l in (t or '').splitlines() if DROW.match(l)]
    old, new, errs = rows(base_text), rows(head_text), []
    if new[:len(old)] != old:
        changed = [o.split('|')[1].strip() for i, o in enumerate(old) if i >= len(new) or new[i] != o]
        errs.append(f'{DECISIONS} is append only: rows {", ".join(changed[:5])} were changed, moved or removed '
                    f'(a reversal is a new dated row that names the one it replaces)')
    last = int(DROW.match(old[-1]).group(1)) if old else 0
    for l in new[len(old):]:
        cells = [c.strip() for c in l.strip('|').split('|')]
        n = int(DROW.match(l).group(1))
        if n != last + 1:
            errs.append(f'{DECISIONS}: new row D{n} should be D{last + 1}')
        last = n
        if len(cells) != 5 or not re.fullmatch(r'\d{4}-\d\d-\d\d', cells[1]) or cells[4] not in ('yes', 'no') or not cells[2]:
            errs.append(f'{DECISIONS}: row D{n} is not | D<n> | YYYY-MM-DD | who | decision | yes/no |')
    return errs


def allowed(path, globs):
    return any(fnmatchcase(path, g) for g in globs)


def check(branch, changed, base_rows, head_rows, base_file, head_file, sessions=None):
    """Errors for this pull request. `base_file`/`head_file` are callables path -> text or None. `sessions`: callable path ->
    set of `Claude-Session:` trailers of the branch's commits that touched it (job branches; None skips the authorship check)."""
    errs = decisions_problems(base_file(DECISIONS), head_file(DECISIONS)) if DECISIONS in changed else []
    m = re.fullmatch(r'(job|brief)/(J[1-9][0-9]*)', branch)
    other_rows_changed = lambda jid: sorted(k for k in set(base_rows) | set(head_rows)
                                             if k != jid and base_rows.get(k) != head_rows.get(k))
    if m and m.group(1) == 'job':
        jid = m.group(2)
        if base_file(f'jobs/{jid}/brief.md') is None:
            errs.append(f'{jid} has no brief on the base branch: briefs are merged before the job starts (brief/{jid})')
        if head_file(f'jobs/{jid}/report.md') is None:
            errs.append(f'jobs/{jid}/report.md is missing: every job ends with a report')
        v = verdict(head_file(f'jobs/{jid}/review.md'))
        if v is None:
            errs.append(f'jobs/{jid}/review.md is missing or has no "Verdict:" line: every job is reviewed before merge (docs/REVIEW.md)')
        elif v != 'merge':
            errs.append(f'review verdict is "{v}", not "merge": finish the fixes and get a merge verdict first')
        row = head_rows.get(jid)
        if not row or row.get('status') != 'done':
            errs.append(f'row {jid} must be `done` on the branch (the reviewer sets it with a merge verdict)')
        if other_rows_changed(jid):
            errs.append(f'a job branch may change only its own row; it also changes {", ".join(other_rows_changed(jid))}')
        if sessions:
            both = sorted(sessions(f'jobs/{jid}/report.md') & sessions(f'jobs/{jid}/review.md'))
            if both:
                errs.append(f'the review was written by a session that also wrote the report ({", ".join(both)}): '
                            f'a job is never reviewed by the chat that built it (CLAUDE.md, Jobs)')
    elif m and m.group(1) == 'brief':
        jid = m.group(2)
        ok = {f'jobs/{jid}/brief.md', JOBS, 'registries/jobs.md'}
        extra = [p for p in changed if p not in ok]
        if extra:
            errs.append(f'a brief branch may only add jobs/{jid}/brief.md and update its row; it also changes: {", ".join(extra)}')
        row = head_rows.get(jid)
        if not row or row.get('status') != 'queued' or row.get('brief') != f'jobs/{jid}/brief.md':
            errs.append(f'row {jid} must be `queued` with brief=jobs/{jid}/brief.md')
        if other_rows_changed(jid):
            errs.append(f'a brief branch may change only its own row; it also changes {", ".join(other_rows_changed(jid))}')
    elif branch.startswith('plan/'):
        extra = [p for p in changed if not allowed(p, PLAN)]
        if extra:
            errs.append(f'a plan/ branch may only touch docs, briefs, the jobs registry, README.md and CLAUDE.md; it also changes: '
                        f'{", ".join(extra)} (code goes through a job)')
    elif branch.startswith('meta/'):
        extra = [p for p in changed if not allowed(p, META)]
        if extra:
            errs.append(f'a meta/ branch may only touch repo infrastructure; it also changes: {", ".join(extra)} (game code goes through a job)')
    else:
        errs.append(f'branch "{branch}" is not job/J<n>, brief/J<n>, plan/* or meta/*: all work goes through the job queue '
                    f'(CLAUDE.md, Jobs). Rename the branch, or add the work as a job first.')
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--branch', required=True, help='the pull request head branch name')
    ap.add_argument('--base', default='origin/main', help='base ref to compare against')
    a = ap.parse_args(argv)
    mb = git('merge-base', a.base, 'HEAD').strip()
    changed = [p for p in git('diff', '--name-only', f'{mb}...HEAD').splitlines() if p]
    def sessions(path):
        out = git('log', '--format=%(trailers:key=Claude-Session,valueonly,separator=%x0a)', f'{mb}..HEAD', '--', path)
        return {l.strip() for l in out.splitlines() if l.strip()}
    errs = check(a.branch, changed, rows(show(mb, JOBS)), rows(show('HEAD', JOBS)),
                 lambda p: show(a.base, p), lambda p: show('HEAD', p), sessions)
    for e in errs:
        print(f'policy: {e}', file=sys.stderr)
    print(f'policy: {a.branch}: {"REFUSED" if errs else "ok"} ({len(changed)} files changed)')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
