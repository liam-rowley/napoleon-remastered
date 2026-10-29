"""The job queue (D16) as a verb: check the queue, pick up the next job, find the next job to review.

purpose: Check the jobs registry against jobs/ (status invariants, file links, brief shape), pick the next job to build or review, and show the queue as a readable page.
usage: python3 core/wsc.py jobs check | jobs next [--id J<n>] [--offline] | jobs review [--id J<n>] [--offline] | jobs view [--offline] [--out PATH] [--no-open] | jobs view --serve [--port N] [--dry-run] [--no-open]
when: `next` when Liam says "pick up the next job" (`--id` for a named job: what a session launched from the view runs); `review` for "review the next job"; `check` runs in the tests gate (CI) and before pushing a brief or a job row change; `view` to read the queue in a browser instead of registries/jobs.md, `view --serve` to start a job's brief, build or review session from its button.
verb: jobs

The rules live here as code; CLAUDE.md ("Jobs") only says which subcommand to run. `next`, `review` and `view` read the remote
branches (`git ls-remote origin`), and `review` fetches the job branches it inspects; `--offline` uses the local remote-tracking refs
instead. `view` writes one self-contained HTML page (default `_scratch/jobs.html`, ignored by git) from the working tree and opens it.
Its cards carry a button for each action not_ready() allows (Write brief, Implement, Review). On the written page a button copies the
`claude --bg` command; `view --serve` serves the page on 127.0.0.1 and the button posts (id, action) to the server, which checks a
per-run token, Origin, Host, content type, readiness against fresh branches and no running session of the same name (`claude agents --json`, fail closed; no count cap: D34),
then runs the command itself. The prompt and the argv are written here, never by the page; no permission flag is ever passed.
"""
import html
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
ACTIONS = {'brief': ('needs_brief', 'brief'), 'build': ('queued', 'job')}   # action: (status it needs, branch prefix that claims it)


def not_ready(action, jid, by, branches, on_branch=None):
    """The one readiness rule (`jobs next`, `--id`, the view's buttons and its server): why job `jid` cannot be started for `action`,
    or None when it can. brief: needs_brief, every depends_on done, no brief/<id> branch; build: the same with queued and job/<id>;
    review: a job/<id> branch whose row says review and that has no jobs/<id>/review.md. `by`: rows on main by id; `branches`:
    remote branch names; `on_branch`: {id: (row on job/<id> or None, has review.md)} (see branch_rows)."""
    r = by.get(jid)
    if r is None:
        return f'{jid} is not a row of the jobs registry'
    if action == 'review':
        if jid not in (on_branch or {}) and f'job/{jid}' not in branches:
            return f'{jid} has no job/{jid} branch on origin'
        row, reviewed = (on_branch or {}).get(jid, (None, False))
        if not row:
            return f'job/{jid} has no {jid} row'
        if row.get('status') != 'review':
            return f'{jid} is {row.get("status")} on job/{jid}, not review' + (' (no report yet)' if row.get('status') == 'queued' else '')
        return f'{jid} is already reviewed (job/{jid} has jobs/{jid}/review.md)' if reviewed else None
    st, prefix = ACTIONS[action]
    if r.get('status') != st:
        return f'{jid} is {r.get("status")}, not {st}'
    late = [d for d in r.get('depends_on', []) if by.get(d, {}).get('status') != 'done']
    if late:
        return f'{jid} ({st}): waits for {", ".join(late)}'
    if f'{prefix}/{jid}' in branches:
        return f'{jid} ({st}): in progress on {prefix}/{jid}'
    return None


def pick_next(rows, branches):
    """(kind, row, waiting): the lowest-numbered ready job to build ('job'), else the lowest ready job to brief ('brief'), else
    (None, None, waiting). Ready: not_ready() says None for 'build' (then 'brief')."""
    by = {r['id']: r for r in rows}
    waiting = []
    order = sorted(rows, key=lambda r: num(r['id']))
    for kind, action in (('job', 'build'), ('brief', 'brief')):
        for r in order:
            if r.get('status') == ACTIONS[action][0]:
                why = not_ready(action, r['id'], by, branches)
                if why is None:
                    return kind, r, waiting
                waiting.append(why)
    waiting += [f'{r["id"]}: {r["status"]}' + (f' ({r.get("blocked_by")})' if r.get('blocked_by') else '')
                for r in order if r.get('status') in ('review', 'blocked')]
    return None, None, sorted(set(waiting), key=lambda w: num(w.split()[0].rstrip(':')))


def pick_review(on_branch):
    """`on_branch`: {id: (row on that job branch or None, branch has jobs/<id>/review.md)}. The lowest-numbered branch whose row
    says review and that has no review yet, or None."""
    for jid in sorted(on_branch, key=num):   # the rule needs a main row only to exist: the branch's row is the one that counts here
        if not_ready('review', jid, {jid: {}}, set(), on_branch) is None:
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


def branch_rows(root, branches, offline, jobs_path, only=None):
    """{id: (row on job/<id> or None, job/<id> has jobs/<id>/review.md)} for each remote job branch (or just `only`), fetching each
    one unless offline."""
    on_branch = {}
    for b in sorted(x for x in branches if x.startswith('job/')):
        jid, ref = b.split('/', 1)[1], f'origin/{b}'
        if only and jid != only:
            continue
        if not offline and _git(root, 'fetch', '-q', 'origin', f'+refs/heads/{b}:refs/remotes/{ref}') is None:
            raise ValueError(f'could not fetch {b}')
        row = next((x for x in load_rows(_git(root, 'show', f'{ref}:{jobs_path}')) if x.get('id') == jid), None)
        on_branch[jid] = (row, _git(root, 'cat-file', '-e', f'{ref}:jobs/{jid}/review.md') is not None)
    return on_branch


# ------------------------------------------------------------------ launch (the view's buttons; D15 and D30)
PROMPTS = {'brief': 'Write the brief for job {id}: git pull, then run python3 core/wsc.py jobs next --id {id} and follow it.',
           'build': 'Pick up job {id}: git pull, then run python3 core/wsc.py jobs next --id {id} and follow it.',
           'review': 'Review job {id}: git pull, then run python3 core/wsc.py jobs review --id {id} and follow docs/REVIEW.md.'}
LABELS = {'brief': 'Write brief', 'build': 'Implement', 'review': 'Review'}


def launch_argv(claude, jid, action, row):
    """The background session for one job: named <id>-<action>, Sonnet for a brief (the D15 default), the row's model otherwise. No
    permission flags: the session runs under Liam's own settings."""
    model = 'sonnet' if action == 'brief' else (row.get('model') or 'sonnet')
    return [claude, '--bg', '--name', f'{jid}-{action}', '--model', model, '--effort', 'medium', PROMPTS[action].format(id=jid)]


def command_line(argv, root=None):
    """argv as one line to paste into PowerShell or Git Bash (the page's copy mode)."""
    line = ' '.join(f'"{a}"' if re.search(r'[\s"]', a) else a for a in argv)
    return f'cd "{Path(root).as_posix()}"; {line}' if root else line


def waiting_rules(ledger_text, jid):
    """Codeable-later rows of an audit ledger (`jobs/*/rules.md`, J5 shape: | n | rule | source | before | after | why |) whose
    reason names `jid`: the rules that job's brief has to turn into code. A ledger line is the only place this hand-off lives."""
    out = []
    for line in (ledger_text or '').splitlines():
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 6 and c[0].isdigit() and c[4] == 'CL' and re.search(rf'\b{jid}\b', c[5]):
            out.append(f'row {c[0]}: {c[1]}')
    return out


def load_rows(text):
    return [json.loads(l) for l in (text or '').splitlines() if l.strip()]


# ------------------------------------------------------------------ view
# (key, heading, what it means): the page's sections, in reading order.
LANES = [('progress', 'In progress', 'a job/ or brief/ branch is open on origin'),
         ('review', 'Waiting for review', 'report written; needs an independent review (wsc jobs review)'),
         ('ready', 'Ready to pick up', 'queued, every dependency done, nobody on it'),
         ('waiting', 'Queued, waiting on dependencies', 'brief written; a dependency is not done yet'),
         ('brief', 'Needs a brief', 'no brief yet; one can be written once the dependencies make sense'),
         ('blocked', 'Blocked', 'stopped on something outside the queue'),
         ('done', 'Done', 'reviewed and merged')]


def lane(r, by, branches):
    """(lane key, short note) for one row: the registry status refined by the remote branches and the dependencies."""
    st, jid = r.get('status'), r['id']
    late = [d for d in r.get('depends_on', []) if by.get(d, {}).get('status') != 'done']
    if st == 'done':
        return 'done', ''
    if st == 'review':
        return 'review', ''
    if st == 'blocked':
        return 'blocked', r.get('blocked_by', '')
    if st == 'queued' and f'job/{jid}' in branches:
        return 'progress', f'being built on job/{jid}'
    if st == 'needs_brief' and f'brief/{jid}' in branches:
        return 'progress', f'brief being written on brief/{jid}'
    if st == 'queued':
        return ('waiting', 'waits for ' + ', '.join(late)) if late else ('ready', '')
    return 'brief', ('waits for ' + ', '.join(late)) if late else 'can be briefed now'


def render_view(rows, read, branches, generated, on_branch=None, token=None, root=None):
    """The queue as one HTML page. `read(path)`: file text or None; `branches`: remote branch names; `generated`: timestamp text;
    `on_branch`: see branch_rows (review buttons need it). Brief, report and review are embedded as escaped Markdown and rendered by
    marked.js when it loads (plain text otherwise). A card gets a button for each action not_ready() allows: with `token` (served by
    `--serve`) it posts (id, action) to /launch; without, it copies the command line (run in `root`)."""
    e = html.escape
    by = {r['id']: r for r in rows}
    order = sorted(rows, key=lambda r: num(r['id']))
    placed = {k: [] for k, _, _ in LANES}
    for r in order:
        k, note = lane(r, by, branches)
        placed[k].append((r, note))
    kind, nxt, _ = pick_next(rows, branches)
    if kind == 'job':
        head = f'Next to pick up: <a href="#{e(nxt["id"])}">{e(nxt["id"])} {e(nxt["title"])}</a>'
    elif kind == 'brief':
        head = f'Nothing queued is ready. Next brief to write: <a href="#{e(nxt["id"])}">{e(nxt["id"])} {e(nxt["title"])}</a>'
    else:
        head = 'Nothing is ready to pick up or brief.'

    def dep(d):
        st = by.get(d, {}).get('status', 'unknown')
        return f'<a class="dep s-{e(st)}" href="#{e(d)}" title="{e(d)}: {e(by.get(d, {}).get("title", "no row"))} ({e(st)})">{e(d)}</a>'

    def card(r, note):
        jid = r['id']
        docs = ''.join(f'<details class="doc"><summary>{f}</summary><pre class="md">{e(t)}</pre></details>'
                       for f in ('brief', 'report', 'review') if (t := read(f'jobs/{jid}/{f}.md')) is not None)
        deps = ' '.join(dep(d) for d in r.get('depends_on', [])) or '<span class="muted">none</span>'
        tags = [f'phase {r.get("phase", "?")}', r.get('model', '?'), 'needs PC' if r.get('needs_pc') else 'no PC']
        acts = [a for a in PROMPTS if not_ready(a, jid, by, branches, on_branch) is None]
        buttons = (('<div class="acts">' + ''.join(
            f'<button class="launch" data-id="{e(jid)}" data-act="{a}" data-cmd="{e(command_line(launch_argv("claude", jid, a, r), root))}">'
            f'{LABELS[a]}</button>' for a in acts) + '<output class="result"></output></div>') if acts else '')
        return (f'<article class="card" id="{e(jid)}" data-text="{e((jid + " " + r.get("title", "") + " " + r.get("description", "")).lower())}">'
                f'<header><span class="id">{e(jid)}</span><h3>{e(r.get("title", ""))}</h3><span class="status s-{e(r.get("status", ""))}">'
                f'{e(r.get("status", ""))}</span></header>'
                + (f'<p class="note">{e(note)}</p>' if note else '')
                + f'<p class="desc">{e(r.get("description", ""))}</p>'
                f'<p class="meta">{" · ".join(e(t) for t in tags)} · depends on {deps}</p>{buttons}{docs}</article>')

    counts = ''.join(f'<a class="count" href="#lane-{k}"><b>{len(placed[k])}</b> {e(h)}</a>' for k, h, _ in LANES)
    lanes = ''.join(f'<section class="lane" id="lane-{k}"><h2>{e(h)} <span class="muted">({len(placed[k])})</span></h2>'
                    f'<p class="muted">{e(why)}</p>' + ''.join(card(r, n) for r, n in placed[k]) + '</section>'
                    for k, h, why in LANES if placed[k])
    refresh = ('Served by <code>wsc jobs view --serve</code>: reload to refresh; the buttons start background sessions.' if token else
               'Rerun it to refresh; the buttons copy the command (<code>wsc jobs view --serve</code> makes them start it).')
    return VIEW_PAGE.format(generated=e(generated), head=head, counts=counts, lanes=lanes, total=len(rows), refresh=refresh,
                            serve=json.dumps({'token': token} if token else None))


VIEW_PAGE = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Queue</title>
<style>
:root {{ --bg:#f7f6f3; --card:#fff; --ink:#1f1f1f; --muted:#6b6b6b; --line:#e2e0da; --accent:#2f5d8a;
  --done:#2e7d4f; --review:#8a5a00; --queued:#2f5d8a; --needs:#7a7a7a; --blocked:#b03030; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161616; --card:#202020; --ink:#e8e6e1; --muted:#9a9890; --line:#333;
  --accent:#7fb0e0; --done:#5fbf86; --review:#e0a640; --queued:#7fb0e0; --needs:#9a9a9a; --blocked:#e06a6a; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width:960px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ margin:0 0 4px; font-size:24px; }} h2 {{ margin:32px 0 2px; font-size:18px; }} h3 {{ margin:0; font-size:16px; flex:1; }}
a {{ color:var(--accent); }} .muted {{ color:var(--muted); font-weight:normal; }} p {{ margin:4px 0; }}
.head {{ font-size:16px; margin:12px 0; }}
.counts {{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }}
.count {{ background:var(--card); border:1px solid var(--line); border-radius:6px; padding:4px 10px; text-decoration:none; color:var(--ink); }}
input {{ width:100%; padding:8px 10px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); font:inherit; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; margin:10px 0; }}
.card:target {{ outline:2px solid var(--accent); }}
.card header {{ display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }}
.id {{ font-weight:700; font-family:ui-monospace, Consolas, monospace; }}
.status, .dep {{ font-size:12px; border-radius:10px; padding:1px 8px; border:1px solid currentColor; text-decoration:none; }}
.s-done {{ color:var(--done); }} .s-review {{ color:var(--review); }} .s-queued {{ color:var(--queued); }}
.s-needs_brief {{ color:var(--needs); }} .s-blocked, .s-unknown {{ color:var(--blocked); }}
.note {{ color:var(--review); font-size:14px; }} .desc {{ margin:6px 0; }} .meta {{ color:var(--muted); font-size:13px; }}
.doc {{ margin-top:6px; }} .doc summary {{ cursor:pointer; color:var(--accent); }}
.doc pre.md {{ white-space:pre-wrap; font:13px/1.45 ui-monospace, Consolas, monospace; }}
.doc .rendered {{ border-left:3px solid var(--line); padding:0 0 0 12px; overflow-wrap:anywhere; }}
.rendered pre, .rendered code {{ font-family:ui-monospace, Consolas, monospace; font-size:13px; }}
.rendered pre {{ white-space:pre-wrap; background:var(--bg); padding:8px; border-radius:4px; }}
.rendered table {{ border-collapse:collapse; display:block; overflow-x:auto; }} .rendered td, .rendered th {{ border:1px solid var(--line); padding:2px 6px; }}
.acts {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:8px 0 2px; }}
.acts button {{ font:inherit; font-size:14px; padding:3px 12px; border-radius:6px; border:1px solid var(--accent); background:var(--card);
  color:var(--accent); cursor:pointer; }} .acts button:hover {{ background:var(--accent); color:var(--card); }} .acts button:disabled {{ opacity:.5; }}
.result {{ font-size:13px; font-family:ui-monospace, Consolas, monospace; overflow-wrap:anywhere; }}
.result.ok {{ color:var(--done); }} .result.err {{ color:var(--blocked); }}
.result textarea {{ width:100%; min-height:4em; font:inherit; background:var(--bg); color:var(--ink); border:1px solid var(--line); }}
</style></head>
<body><main>
<h1>Job queue</h1>
<p class="muted">{total} jobs · generated {generated} by <code>wsc jobs view</code> from registries/jobs.jsonl, jobs/ and origin's branches. {refresh}</p>
<p class="head">{head}</p>
<div class="counts">{counts}</div>
<input id="q" type="search" placeholder="Filter by id, title or description">
{lanes}
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script>
document.getElementById('q').addEventListener('input', ev => {{
  const q = ev.target.value.toLowerCase();
  document.querySelectorAll('.card').forEach(c => c.hidden = q && !c.dataset.text.includes(q));
}});
document.addEventListener('toggle', ev => {{
  const pre = ev.target.querySelector && ev.target.querySelector('pre.md');
  if (!pre || !window.marked) return;
  const div = document.createElement('div'); div.className = 'rendered';
  div.innerHTML = marked.parse(pre.textContent); pre.replaceWith(div);
}}, true);
const SERVE = {serve};
function show(out, text, cls) {{ out.className = 'result ' + cls; out.textContent = text; }}
document.querySelectorAll('button.launch').forEach(b => b.addEventListener('click', async () => {{
  const out = b.parentElement.querySelector('.result');
  if (!SERVE) {{
    try {{ await navigator.clipboard.writeText(b.dataset.cmd); show(out, 'copied, paste it into a terminal: ' + b.dataset.cmd, 'ok'); }}
    catch (err) {{
      const t = document.createElement('textarea'); t.readOnly = true; t.value = b.dataset.cmd;
      show(out, '', ''); out.append(t); t.select();
    }}
    return;
  }}
  b.disabled = true; show(out, 'starting ' + b.dataset.id + '-' + b.dataset.act + ' ...', '');
  try {{
    const r = await fetch('/launch', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ id: b.dataset.id, action: b.dataset.act, token: SERVE.token }}) }});
    const j = await r.json(); show(out, j.message, r.ok ? 'ok' : 'err');
  }} catch (err) {{ show(out, 'no answer from the server (is wsc jobs view --serve still running?): ' + err, 'err'); }}
  b.disabled = false;
}}));
</script>
</body></html>
'''


# ------------------------------------------------------------------ serve
def _claude(*args, timeout=120, cwd=None):
    """Run claude (no shell, no stdin) with its output in files, not pipes: a background session the command leaves behind may
    inherit the handles, and a pipe would then block until that session ends. `cwd`: where it runs (a session starts in its cwd).
    (returncode, stdout, stderr)."""
    claude = shutil.which('claude')
    if not claude:
        raise ValueError('claude is not on PATH')
    flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0   # Ctrl+C here spares it
    with tempfile.TemporaryFile('w+', encoding='utf-8') as out, tempfile.TemporaryFile('w+', encoding='utf-8') as err:
        try:
            rc = subprocess.run([claude, *args], stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout,
                                cwd=cwd, creationflags=flags).returncode
        except (OSError, subprocess.TimeoutExpired) as x:
            raise ValueError(f'claude {args[0]} did not finish: {x}')
        out.seek(0), err.seek(0)
        return rc, out.read(), err.read()


def list_agents():
    """`claude agents --json` as a list of sessions; ValueError when it cannot be read (the launch then fails closed)."""
    rc, out, err = _claude('agents', '--json', timeout=60)
    if rc != 0:
        raise ValueError(f'claude agents --json exited {rc}: {err.strip()[:200]}')
    try:
        agents = json.loads(out)
    except ValueError:
        raise ValueError('claude agents --json did not print JSON')
    if not isinstance(agents, list):
        raise ValueError('claude agents --json did not print a list')
    return agents


def start_session(argv, root):
    """Start `claude --bg ...` from argv in the repo root (wsc may run from a subfolder) and return the id it prints. argv[0] is
    ignored: _claude resolves claude again."""
    rc, out, err = _claude(*argv[1:], cwd=root)
    if rc != 0:
        raise ValueError(f'exited {rc}: {(err or out).strip()[:300]}')
    m = re.search(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?\b', out)
    return m.group(0) if m else out.strip()


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        if self.server.log:
            sys.stderr.write('jobs serve: ' + fmt % a + '\n')

    def _send(self, code, body, ctype):
        data = body.encode('utf-8')
        self.send_response(code)
        for k, v in (('Content-Type', ctype), ('Content-Length', str(len(data))), ('Cache-Control', 'no-store'),
                     ('X-Frame-Options', 'DENY')):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        s = self.server
        if self.headers.get('Host') != s.host:   # a DNS-rebound name never gets the page, so never the token
            return self._send(403, f'open {s.url}', 'text/plain; charset=utf-8')
        if self.path.split('?')[0] != '/':
            return self._send(404, 'not found', 'text/plain; charset=utf-8')
        try:
            page = s.page()
        except Exception as x:
            return self._send(500, f'could not render the queue: {x}', 'text/plain; charset=utf-8')
        self._send(200, page, 'text/html; charset=utf-8')

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            n = -1
        if self.path != '/launch' or not 0 <= n <= 4096:
            code, msg, extra = (404, 'not found', {}) if self.path != '/launch' else (413, 'body too large', {})
        else:
            code, msg, extra = self.server.launch_request(self.headers, self.rfile.read(n))
        self._send(code, json.dumps({'ok': code == 200, 'message': msg, **extra}), 'application/json')


class JobServer(ThreadingHTTPServer):
    """`wsc jobs view --serve` on 127.0.0.1: GET / renders the queue fresh, POST /launch starts one session after the checks of
    launch_request. Seams (the tests pass fakes): snapshot() -> (rows, read, branches, on_branch), read fresh each time; agents() ->
    the `claude agents --json` list; launch(argv) -> session id; which(name) -> path or None."""
    daemon_threads = True
    log = True   # one stderr line per request

    def __init__(self, snapshot, agents, launch, which=shutil.which, port=0, dry_run=False, root=None):
        super().__init__(('127.0.0.1', port), _Handler)
        self.snapshot, self.agents, self.launch, self.which, self.dry_run, self.root = snapshot, agents, launch, which, dry_run, root
        self.token = secrets.token_urlsafe(32)
        self.host = f'127.0.0.1:{self.server_address[1]}'
        self.url = f'http://{self.host}/'
        self.lock = threading.Lock()

    def page(self):
        rows, read, branches, on_branch = self.snapshot()
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        return render_view(rows, read, branches, stamp, on_branch, self.token, self.root)

    def launch_request(self, headers, body):
        """(HTTP code, message, extra JSON fields), checked in this order: token 403, Origin and Host 403, content type 415, id and
        action 400, readiness 409, a same-name session 429, then the launch (no count cap: D34)."""
        try:
            req = json.loads(body.decode('utf-8'))
        except ValueError:
            req = None
        req = req if isinstance(req, dict) else {}
        tok = req.get('token')
        if not isinstance(tok, str) or not secrets.compare_digest(tok, self.token):
            return 403, 'refused: bad or missing token (reload the page from this server)', {}
        if headers.get('Origin') != self.url.rstrip('/') or headers.get('Host') != self.host:
            return 403, 'refused: the request did not come from this server\'s own page', {}
        if (headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
            return 415, 'refused: the body must be application/json', {}
        try:
            rows, _, branches, on_branch = self.snapshot()
        except Exception as x:
            return 503, f'refused: cannot read the queue ({x})', {}
        by = {r['id']: r for r in rows}
        jid, action = req.get('id'), req.get('action')
        if not isinstance(jid, str) or jid not in by or action not in PROMPTS:
            return 400, f'refused: no such job or action ({jid!r}, {action!r})', {}
        why = not_ready(action, jid, by, branches, on_branch)
        if why:
            return 409, f'refused: {why}', {}
        name = f'{jid}-{action}'
        with self.lock:   # one launch at a time, so a double click cannot start the same session twice
            try:
                agents = self.agents()
            except Exception as x:
                return 503, f'refused: cannot list the running sessions ({x})', {}
            working = [a for a in agents if isinstance(a, dict) and a.get('state') == 'working']
            if any(str(a.get('name') or '').lower() == name.lower() for a in working):
                return 429, f'refused: {name} is already running', {}
            claude = self.which('claude')
            if not claude:
                return 503, 'refused: claude is not on PATH', {}
            argv = launch_argv(claude, jid, action, by[jid])
            if self.dry_run:
                return 200, 'dry run, would start: ' + command_line(argv), {'argv': argv}
            try:
                sid = self.launch(argv)
            except Exception as x:
                return 500, f'claude --bg failed: {x}', {'argv': argv}
        return 200, f'started {name}: claude attach {sid}', {'argv': argv, 'session': sid}


# ------------------------------------------------------------------ verb
def add_arguments(p):
    p.add_argument('action', choices=['check', 'next', 'review', 'view'])
    p.add_argument('--offline', action='store_true', help='use local remote-tracking refs instead of asking origin (a single-branch or shallow clone sees only the branches it fetched)')
    p.add_argument('--id', help='next, review: this job only (J<n>): its steps when it is ready, else exit 1 with the reason')
    p.add_argument('--out', default='_scratch/jobs.html', help='view: where to write the page, relative to the repo root (default %(default)s)')
    p.add_argument('--no-open', action='store_true', help='view: write the page (or start the server) but do not open a browser')
    p.add_argument('--serve', action='store_true', help='view: serve the page on 127.0.0.1 so its buttons start background Claude Code sessions (until Ctrl+C)')
    p.add_argument('--port', type=int, default=0, help='view --serve: the port (default 0: the OS picks one)')
    p.add_argument('--dry-run', action='store_true', help='view --serve: make every check, but answer with the command instead of running it')


def build_steps(r):
    return (f'{r["id"]}: {r["title"]} (model {r["model"]}, needs_pc {"yes" if r["needs_pc"] else "no"})\n'
            f'Take it: git checkout -b job/{r["id"]} origin/main, follow jobs/{r["id"]}/brief.md, push early so the branch claims it.\n'
            f'Finish: jobs/{r["id"]}/report.md, then wsc reg set jobs {r["id"]} status=review report=jobs/{r["id"]}/report.md, pushed.')


def brief_steps(r, root, lead='needs a brief (nothing queued is ready)'):
    owed = [f'{p.relative_to(root).as_posix()} {w}' for p in sorted((root / 'jobs').glob('*/rules.md'))
            for w in waiting_rules(p.read_text(encoding='utf-8'), r['id'])]
    return (f'{r["id"]}: {r["title"]} {lead}.\n'
            f'Write jobs/{r["id"]}/brief.md on branch brief/{r["id"]} from the row, docs/plans/PLAN.md and the reports of '
            f'{", ".join(r["depends_on"]) or "earlier jobs"}, in the shape `wsc jobs check` enforces (jobs/J1/brief.md is the model); '
            f'then wsc reg set jobs {r["id"]} status=queued brief=jobs/{r["id"]}/brief.md, push, then queue the merge on green CI (D33): '
            f'python3 tools/pr_policy.py --branch brief/{r["id"]} --base origin/main (must say ok), '
            f'gh pr create --base main --head brief/{r["id"]} --title "brief: {r["id"]} {r["title"]}", '
            f'gh pr merge brief/{r["id"]} --auto --squash; do not wait or poll.'
            + ''.join(f'\nThe brief must cover {o}' for o in owed))


def review_steps(jid):
    return (f'{jid}: review branch job/{jid} (git checkout job/{jid}) following docs/REVIEW.md. You must not have built it: '
            f'CI\'s policy check refuses a review.md written in a session that wrote report.md.')


def refuse(why):
    print(f'jobs: {why}', file=sys.stderr)
    return 1


def run(args, ctx):
    jobs_path = f'{ctx.config["registries_dir"]}/jobs.jsonl'
    rows = load_rows((ctx.root / jobs_path).read_text(encoding='utf-8'))
    by = {r['id']: r for r in rows}

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

    if args.action == 'view' and args.serve:
        def snapshot():   # fresh on every request: the working tree's rows and docs, origin's branches, each job branch's row
            now = load_rows((ctx.root / jobs_path).read_text(encoding='utf-8'))
            branches = remote_branches(ctx.root, args.offline)
            return now, read, branches, branch_rows(ctx.root, branches, args.offline, jobs_path)
        srv = JobServer(snapshot, list_agents, lambda argv: start_session(argv, ctx.root), port=args.port, dry_run=args.dry_run, root=ctx.root)
        print(f'jobs view: serving {srv.url}{" (dry run: nothing is started)" if args.dry_run else ""}; Ctrl+C stops it', flush=True)
        if not args.no_open:
            webbrowser.open(srv.url)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()
        return 0

    branches = remote_branches(ctx.root, args.offline)
    if args.action == 'next' and args.id:
        r = by.get(args.id)
        action = {'needs_brief': 'brief', 'queued': 'build'}.get((r or {}).get('status'))
        if r and not action:
            return refuse(f'{args.id} is {r.get("status")}, not queued or needs_brief: nothing to pick up')
        why = not_ready(action or 'build', args.id, by, branches)
        if why:
            return refuse(why)
        print(build_steps(r) if action == 'build' else brief_steps(r, ctx.root, 'needs a brief'))
        return 0

    if args.action == 'next':
        kind, r, waiting = pick_next(rows, branches)
        if kind == 'job':
            print(build_steps(r))
        elif kind == 'brief':
            print(brief_steps(r, ctx.root))
        else:
            print('Nothing is ready. Waiting:\n  ' + '\n  '.join(waiting or ['(the queue is empty)']))
        return 0

    if args.action == 'view':
        out = ctx.root / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        on_branch = branch_rows(ctx.root, branches, args.offline, jobs_path)
        out.write_text(render_view(rows, read, branches, stamp, on_branch, root=ctx.root), encoding='utf-8')
        print(f'jobs view: {len(rows)} jobs -> {out}')
        if not args.no_open:
            webbrowser.open(out.resolve().as_uri())
        return 0

    if args.id:
        why = not_ready('review', args.id, by, branches, branch_rows(ctx.root, branches, args.offline, jobs_path, only=args.id))
        if why:
            return refuse(why)
        print(review_steps(args.id))
        return 0
    on_branch = branch_rows(ctx.root, branches, args.offline, jobs_path)
    jid = pick_review(on_branch)
    if jid:
        print(review_steps(jid))
    else:
        print('No job branch is waiting for review: ' + (', '.join(f'{j} ({(r or {}).get("status", "no row")}'
              f'{", reviewed" if rv else ""})' for j, (r, rv) in sorted(on_branch.items(), key=lambda x: num(x[0]))) or 'no job branches'))
    return 0
