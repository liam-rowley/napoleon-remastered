"""The job queue (D16) as a verb: check the queue, pick up the next job, find the next job to review.

purpose: Check the jobs registry against jobs/ (status invariants, file links, brief shape), and pick the next job to build or review.
usage: python3 core/wsc.py jobs check | jobs next [--offline] | jobs review [--offline]
when: `next` when Liam says "pick up the next job"; `review` for "review the next job"; `check` runs in the tests gate (CI) and before pushing a brief or a job row change.
verb: jobs

The rules live here as code; CLAUDE.md ("Jobs") only says which subcommand to run. `next` and `review` read the remote branches
(`git ls-remote origin`), and `review` fetches the job branches it inspects; `--offline` uses the local remote-tracking refs instead.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

NAME = 'jobs'
HELP = 'the job queue: check it, pick the next job to build (next) or to review (review)'

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pr_policy import verdict  # noqa: E402  (one parser for the Verdict line: CI's policy check uses it too)

STATUSES_WITH = {'brief': {'queued', 'review', 'done'}, 'report': {'review', 'done'}, 'review': {'done'}}
DATED = re.compile(r'\b20\d\d-\d\d-\d\d\b')


def num(jid):
    return int(jid[1:]) if re.fullmatch(r'J\d+', jid or '') else 10 ** 9


# ------------------------------------------------------------------ check
def brief_problems(jid, row, text):
    """Shape every brief must have (D15 and the J1 template): Model line agreeing with the row (a reason when Opus), a call budget,
    kill criteria, and a Finish section that ends with the status=review command."""
    errs = []
    if not re.search(rf'^# {jid}:', text, re.M):
        errs.append(f'first heading is not "# {jid}: <title>"')
    m = re.search(r'^Model:\s*(\w+)(.*)$', text, re.M)
    if not m:
        errs.append('no "Model: <Sonnet|Opus> ..." line (D15)')
    else:
        if m.group(1).lower() != row.get('model'):
            errs.append(f'Model line says {m.group(1)}, the row says {row.get("model")}')
        if m.group(1).lower() == 'opus' and not re.search(r'\breason\b', m.group(2), re.I):
            errs.append('Opus without "reason:" on the Model line (D15: Opus only with a stated reason)')
    if not re.search(r'[Bb]udget\s+about\s+\d+\s+tool\s+calls', text):
        errs.append('no call budget ("Budget about <n> tool calls", D15)')
    kill = re.search(r'^## Kill criteria\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not kill or not re.search(r'^\s*- ', kill.group(1), re.M):
        errs.append('no "## Kill criteria" section with at least one bullet (D15)')
    fin = re.search(r'^## Finish\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    cmd = f'wsc reg set jobs {jid} status=review report=jobs/{jid}/report.md'
    if not fin or cmd not in fin.group(1):
        errs.append(f'no "## Finish" section ending with `{cmd}`')
    return errs


def report_problems(jid, text):
    """Every report says what was built, its deviations and its open questions (CLAUDE.md, While you work)."""
    errs = []
    if not re.search(rf'^# {jid} report\b', text, re.M):
        errs.append(f'first heading is not "# {jid} report: <title>"')
    for h in ('Deviations', 'Open questions'):
        if not re.search(rf'^## {h}\b', text, re.M):
            errs.append(f'no "## {h} ..." section')
    return errs


def problems(rows, read, folders=()):
    """Errors for the queue. `rows`: the jobs rows; `read(path)`: file text or None; `folders`: job ids that have a jobs/<id>/ folder."""
    errs, by = [], {r['id']: r for r in rows}
    for jid in sorted(by, key=num):
        r, st = by[jid], by[jid].get('status')
        for f in ('brief', 'report', 'review'):
            want = f'jobs/{jid}/{f}.md'
            if r.get(f) and r[f] != want:
                errs.append(f'{jid}: {f}={r[f]} points at another job (want {want})')
            text = read(want)
            if r.get(f) and text is None:
                errs.append(f'{jid}: {f}={want} but the file does not exist')
            if st in STATUSES_WITH[f] and not r.get(f):
                errs.append(f'{jid}: status {st} needs {f}={want}')
            if text is not None and not r.get(f):
                errs.append(f'{jid}: {want} exists but the row has no {f}= (set it, with the status that goes with it)')
        if st == 'needs_brief' and read(f'jobs/{jid}/brief.md') is not None:
            errs.append(f'{jid}: has a brief but is still needs_brief (set status=queued brief=jobs/{jid}/brief.md)')
        brief = read(f'jobs/{jid}/brief.md')
        if brief is not None:
            errs += [f'{jid}: brief: {e}' for e in brief_problems(jid, r, brief)]
        report = read(f'jobs/{jid}/report.md')
        if report is not None:
            errs += [f'{jid}: report: {e}' for e in report_problems(jid, report)]
        review = read(f'jobs/{jid}/review.md')
        if review is not None:
            if not DATED.search('\n'.join(review.split('\n')[:5])):
                errs.append(f'{jid}: review.md has no date in its first lines (docs/REVIEW.md: dated at the top)')
            if verdict(review) not in ('merge', 'merge after fixes', 'do not merge'):
                errs.append(f'{jid}: review.md has no Verdict line of the three allowed (docs/REVIEW.md "Output")')
            elif st == 'done' and verdict(review) != 'merge':
                errs.append(f'{jid}: done, but the review verdict is "{verdict(review)}" (only "merge" makes a job done)')
        if st in ('review', 'done'):
            late = [d for d in r.get('depends_on', []) if by.get(d, {}).get('status') != 'done']
            if late:
                errs.append(f'{jid}: {st} while its dependencies {", ".join(late)} are not done')
    for jid in sorted(set(folders) - set(by), key=num):
        errs.append(f'jobs/{jid}/ has no row in the jobs registry')
    # dependency cycles
    state = {}
    def visit(j, path):
        if state.get(j) == 1:
            errs.append('dependency cycle: ' + ' -> '.join(path[path.index(j):] + [j]))
            return
        if state.get(j) == 2 or j not in by:
            return
        state[j] = 1
        for d in by[j].get('depends_on', []):
            visit(d, path + [j])
        state[j] = 2
    for j in sorted(by, key=num):
        visit(j, [])
    return errs


# ------------------------------------------------------------------ next and review
def pick_next(rows, branches):
    """(kind, row, waiting): the lowest-numbered ready job to build ('job'), else the lowest ready job to brief ('brief'), else
    (None, None, waiting). Ready: status queued (or needs_brief), every depends_on done, no remote job/<id> (or brief/<id>) branch."""
    by = {r['id']: r for r in rows}
    waiting = []
    def ready(r, prefix):
        late = [d for d in r.get('depends_on', []) if by.get(d, {}).get('status') != 'done']
        if late:
            waiting.append(f'{r["id"]} ({r["status"]}): waits for {", ".join(late)}')
            return False
        if f'{prefix}/{r["id"]}' in branches:
            waiting.append(f'{r["id"]} ({r["status"]}): in progress on {prefix}/{r["id"]}')
            return False
        return True
    order = sorted(rows, key=lambda r: num(r['id']))
    for kind, st, prefix in (('job', 'queued', 'job'), ('brief', 'needs_brief', 'brief')):
        for r in order:
            if r.get('status') == st and ready(r, prefix):
                return kind, r, waiting
    waiting += [f'{r["id"]}: {r["status"]}' + (f' ({r.get("blocked_by")})' if r.get('blocked_by') else '')
                for r in order if r.get('status') in ('review', 'blocked')]
    return None, None, sorted(set(waiting), key=lambda w: num(w.split()[0].rstrip(':')))


def pick_review(on_branch):
    """`on_branch`: {id: (row on that job branch or None, branch has jobs/<id>/review.md)}. The lowest-numbered branch whose row
    says review and that has no review yet, or None."""
    for jid in sorted(on_branch, key=num):
        row, reviewed = on_branch[jid]
        if row and row.get('status') == 'review' and not reviewed:
            return jid
    return None


def _git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=300)
    return p.stdout if p.returncode == 0 else None


def remote_branches(root, offline):
    if offline:
        out = _git(root, 'for-each-ref', '--format=%(refname:strip=3)', 'refs/remotes/origin/') or ''
        return set(out.split())
    out = _git(root, 'ls-remote', '--heads', 'origin', 'job/*', 'brief/*')
    if out is None:
        raise ValueError('git ls-remote origin failed (no network or no origin): rerun with --offline to use local refs')
    return {l.split('refs/heads/', 1)[1] for l in out.splitlines() if 'refs/heads/' in l}


def load_rows(text):
    return [json.loads(l) for l in (text or '').splitlines() if l.strip()]


# ------------------------------------------------------------------ verb
def add_arguments(p):
    p.add_argument('action', choices=['check', 'next', 'review'])
    p.add_argument('--offline', action='store_true', help='use local remote-tracking refs instead of asking origin (a single-branch or shallow clone sees only the branches it fetched)')


def run(args, ctx):
    jobs_path = f'{ctx.config["registries_dir"]}/jobs.jsonl'
    rows = load_rows((ctx.root / jobs_path).read_text(encoding='utf-8'))

    def read(p):
        f = ctx.root / p
        return f.read_text(encoding='utf-8') if f.is_file() else None

    if args.action == 'check':
        folders = [d.name for d in (ctx.root / 'jobs').iterdir() if d.is_dir()] if (ctx.root / 'jobs').is_dir() else []
        errs = problems(rows, read, folders)
        for e in errs:
            print(f'jobs: {e}', file=sys.stderr)
        print(f'jobs check: {len(rows)} rows, {"%d problems" % len(errs) if errs else "ok"}')
        return 1 if errs else 0

    branches = remote_branches(ctx.root, args.offline)
    if args.action == 'next':
        kind, r, waiting = pick_next(rows, branches)
        if kind == 'job':
            print(f'{r["id"]}: {r["title"]} (model {r["model"]}, needs_pc {"yes" if r["needs_pc"] else "no"})\n'
                  f'Take it: git checkout -b job/{r["id"]} origin/main, follow jobs/{r["id"]}/brief.md, push early so the branch claims it.\n'
                  f'Finish: jobs/{r["id"]}/report.md, then wsc reg set jobs {r["id"]} status=review report=jobs/{r["id"]}/report.md, pushed.')
        elif kind == 'brief':
            print(f'{r["id"]}: {r["title"]} needs a brief (nothing queued is ready).\n'
                  f'Write jobs/{r["id"]}/brief.md on branch brief/{r["id"]} from the row, docs/plans/PLAN.md and the reports of '
                  f'{", ".join(r["depends_on"]) or "earlier jobs"}, in the shape `wsc jobs check` enforces (jobs/J1/brief.md is the model); '
                  f'then wsc reg set jobs {r["id"]} status=queued brief=jobs/{r["id"]}/brief.md, push, and stop for Liam\'s merge.')
        else:
            print('Nothing is ready. Waiting:\n  ' + '\n  '.join(waiting or ['(the queue is empty)']))
        return 0

    on_branch = {}
    for b in sorted(x for x in branches if x.startswith('job/')):
        jid = b.split('/', 1)[1]
        ref = f'origin/{b}'
        if not args.offline and _git(ctx.root, 'fetch', '-q', 'origin', f'+refs/heads/{b}:refs/remotes/{ref}') is None:
            raise ValueError(f'could not fetch {b}')
        row = next((x for x in load_rows(_git(ctx.root, 'show', f'{ref}:{jobs_path}')) if x.get('id') == jid), None)
        on_branch[jid] = (row, _git(ctx.root, 'cat-file', '-e', f'{ref}:jobs/{jid}/review.md') is not None)
    jid = pick_review(on_branch)
    if jid:
        print(f'{jid}: review branch job/{jid} (git checkout job/{jid}) following docs/REVIEW.md. You must not have built it: '
              f'CI\'s policy check refuses a review.md written in a session that wrote report.md.')
    else:
        print('No job branch is waiting for review: ' + (', '.join(f'{j} ({(r or {}).get("status", "no row")}'
              f'{", reviewed" if rv else ""})' for j, (r, rv) in sorted(on_branch.items(), key=lambda x: num(x[0]))) or 'no job branches'))
    return 0
