"""Claude usage per session and per job, read from the transcripts Claude Code already writes on this PC (rule 75, J49).

purpose: sum tokens, tool calls and wall time per Claude Code session from `~/.claude/projects/<cwd-slug>/<session>.jsonl` (and the sub-agent files under `<session>/subagents/`), and attribute each session to a job: pure functions that take paths and return dicts, so tests use synthetic files
usage: library only, imported by tools/jobs_hooks.py (the `wsc jobs view` PC block); `python3 -m unittest tests.test_usage_reader` tests it; by hand: `python3 tools/usage_reader.py [--days 7]` prints the per-job table
when: automatic, every `wsc jobs view` on the PC; edit it when Claude Code changes its transcript format (check `claude --version` against the line below)
not-a-verb: a library module; its command line is a debugging aid and writes nothing but its cache

Read on 2026-11-02, Claude Code 2.1.316 (the format may change; an odd line is skipped and counted, never a traceback):
- One JSON object per line. `type: "assistant"` lines carry `message.id`, `message.model`, `message.usage` (input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens) and `message.content` blocks (a `tool_use` block is one tool call), plus `timestamp`, `sessionId`, `gitBranch`, `cwd`.
- One reply is written as several lines with the same `message.id` and repeated usage: sum each id once (element-wise max), or tokens are counted two to three times.
- Sub-agent work is in `<session>/subagents/agent-*.jsonl` (lines with `isSidechain: true`); it counts toward the parent session (the folder name).
- A `type: "cost-state"` line is Claude Code's own running total for the session (`totalCostUSD`, `modelUsage` per model); the last one wins. It is an estimate, not a bill, and it includes sub-agents and small side requests the transcript has no assistant line for, so it can sit a few percent above the summed lines (J49 report, finding table).
- `agent-name` lines carry the name a background session was launched with (`J<n>-<action>`).
Privacy: only the structured fields above are read. No prompt, tool input or tool result text is kept, returned, printed or cached. Nothing is written under `~/.claude`; the only file written is the cache in `_scratch/` (git-ignored). No network, no API key.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECTS = Path.home() / '.claude' / 'projects'
CACHE_NAME = 'usage_cache.json'
CACHE_VERSION = 2
FIELDS = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
JOB_BRANCH = re.compile(r'^(?:job|brief)/(J\d+)\b')
JOB_NAME = re.compile(r'^(J\d+)-[A-Za-z]')


def _day(ts):
    return str(ts or '')[:10] or 'unknown'


def scan_file(path):
    """One transcript file -> {'days': {date: {'models': {model: [in, out, cache_read, cache_write]}, 'calls': n, 'replies': n}},
    'first', 'last', 'branches': {branch: n}, 'names': [..], 'cost': {...} or None, 'skipped': n}. Streaming: one line in memory at a time."""
    replies = {}      # message id -> [day, model, usage list, calls]
    branches, names = {}, []
    first = last = None
    cost, skipped = None, 0
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
                t = o.get('type')
            except (ValueError, AttributeError):
                skipped += 1
                continue
            if t == 'cost-state':
                try:
                    cost = {'usd': float(o.get('totalCostUSD') or 0),
                            'models': {m: float(v.get('costUSD') or 0) for m, v in (o.get('modelUsage') or {}).items()}}
                except (TypeError, ValueError, AttributeError):
                    skipped += 1
                continue
            if t == 'agent-name':
                n = o.get('agentName')
                if isinstance(n, str) and n not in names:
                    names.append(n)
                continue
            ts = o.get('timestamp')
            if isinstance(ts, str):
                first = ts if first is None or ts < first else first
                last = ts if last is None or ts > last else last
            b = o.get('gitBranch')
            if isinstance(b, str) and b:
                branches[b] = branches.get(b, 0) + 1
            if t != 'assistant':
                continue
            try:
                m = o.get('message') or {}
                key = m.get('id') or o.get('requestId') or o.get('uuid')
                u = m.get('usage') or {}
                vec = [int(u.get(f) or 0) for f in FIELDS]
                calls = sum(1 for blk in (m.get('content') or []) if isinstance(blk, dict) and blk.get('type') == 'tool_use')
            except (TypeError, ValueError, AttributeError):
                skipped += 1
                continue
            if key in replies:
                r = replies[key]
                r[2] = [max(a, b2) for a, b2 in zip(r[2], vec)]
                r[3] = max(r[3], calls)
            else:
                replies[key] = [_day(ts), str(m.get('model') or 'unknown'), vec, calls]
    days = {}
    for day, model, vec, calls in replies.values():
        d = days.setdefault(day, {'models': {}, 'calls': 0, 'replies': 0})
        acc = d['models'].setdefault(model, [0, 0, 0, 0])
        for i, x in enumerate(vec):
            acc[i] += x
        d['calls'] += calls
        d['replies'] += 1
    return {'days': days, 'first': first, 'last': last, 'branches': branches, 'names': names, 'cost': cost, 'skipped': skipped}


def _load_cache(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data['files'] if data.get('version') == CACHE_VERSION else {}
    except (OSError, ValueError, KeyError, AttributeError):
        return {}


def _save_cache(path, files):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({'version': CACHE_VERSION, 'files': files}), encoding='utf-8')
    except OSError:
        pass   # a cache that cannot be written only costs time


def transcript_files(projects_dir):
    """[(path, session id, is_subagent)]: top-level `<slug>/<id>.jsonl` and `<slug>/<id>/subagents/*.jsonl`."""
    out = []
    for slug in sorted(Path(projects_dir).iterdir()):
        if not slug.is_dir():
            continue
        for f in sorted(slug.glob('*.jsonl')):
            out.append((f, f.stem, False))
        for sub in sorted(slug.glob('*/subagents/*.jsonl')):
            out.append((sub, sub.parent.parent.name, True))
    return out


def usage_by_session(projects_dir=None, cache_path=None, now=None):
    """Every session found under `projects_dir` -> {'sessions': {id: {...}}, 'source', 'read_at', 'files', 'skipped', 'error'}.
    A session: days (merged from its file and its sub-agent files), first, last, branches, names, cost (the main file's last cost-state),
    subagents, files, project (the slug). Fails soft: a missing folder gives error text and no sessions; an unreadable file is counted in skipped."""
    projects_dir = Path(projects_dir) if projects_dir else PROJECTS
    res = {'sessions': {}, 'source': str(projects_dir).replace(str(Path.home()), '~'), 'read_at': (now or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M UTC'),
           'files': 0, 'skipped': 0, 'error': None}
    if not projects_dir.is_dir():
        res['error'] = f'{res["source"]} does not exist: Claude Code has written no transcripts on this machine'
        return res
    cache = _load_cache(cache_path) if cache_path else {}
    fresh = {}
    try:
        files = transcript_files(projects_dir)
    except OSError as ex:
        res['error'] = f'{res["source"]} cannot be listed: {ex.__class__.__name__}'
        return res
    for path, sid, sub in files:
        try:
            st = path.stat()
        except OSError:
            res['skipped'] += 1
            continue
        k = str(path)
        hit = cache.get(k)
        if hit and hit.get('size') == st.st_size and hit.get('mtime') == st.st_mtime_ns:
            r = hit['r']
        else:
            try:
                r = scan_file(path)
            except OSError:
                res['skipped'] += 1
                continue
        fresh[k] = {'size': st.st_size, 'mtime': st.st_mtime_ns, 'r': r}
        res['files'] += 1
        res['skipped'] += r['skipped']
        s = res['sessions'].setdefault(sid, {'days': {}, 'first': None, 'last': None, 'branches': {}, 'names': [], 'cost': None,
                                             'subagents': 0, 'files': 0, 'project': path.parent.name if not sub else path.parent.parent.parent.name})
        s['files'] += 1
        if sub:
            s['subagents'] += 1
        elif r['cost']:
            s['cost'] = r['cost']
        for day, d in r['days'].items():
            t = s['days'].setdefault(day, {'models': {}, 'calls': 0, 'replies': 0})
            t['calls'] += d['calls']
            t['replies'] += d['replies']
            for m, vec in d['models'].items():
                acc = t['models'].setdefault(m, [0, 0, 0, 0])
                for i, x in enumerate(vec):
                    acc[i] += x
        for a in ('first',):
            if r[a] and (s[a] is None or r[a] < s[a]):
                s[a] = r[a]
        if r['last'] and (s['last'] is None or r['last'] > s['last']):
            s['last'] = r['last']
        for b, n in r['branches'].items():
            s['branches'][b] = s['branches'].get(b, 0) + n
        for n in r['names']:
            if n not in s['names']:
                s['names'].append(n)
    if cache_path and fresh != cache:
        _save_cache(cache_path, fresh)
    return res


def totals(session, since_day=None):
    """A session's numbers, optionally only days >= since_day: {'models': {m: [..4..]}, 'calls', 'replies'}."""
    out = {'models': {}, 'calls': 0, 'replies': 0}
    for day, d in session['days'].items():
        if since_day and day < since_day:
            continue
        out['calls'] += d['calls']
        out['replies'] += d['replies']
        for m, vec in d['models'].items():
            acc = out['models'].setdefault(m, [0, 0, 0, 0])
            for i, x in enumerate(vec):
                acc[i] += x
    return out


def branch_trailers(root, job_ids=None):
    """{job id: set of session ids}: the `Claude-Session` trailers of commits on `job/<id>` and `brief/<id>` branches (local and origin), not on origin/main.
    One `git log --source` for all branches (fast); fails soft (no git, no branches -> {})."""
    try:
        txt = subprocess.run(['git', '-C', str(root), 'log', '--source', '--branches=job/*', '--branches=brief/*', '--remotes=origin/job/*',
                              '--remotes=origin/brief/*', '--not', 'origin/main', '--format=%S%x09%(trailers:key=Claude-Session,valueonly,separator=%x20)'],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}
    out = {}
    for line in txt.splitlines():
        ref, _, sids = line.partition('\t')
        m = re.search(r'(?:job|brief)/(J\d+)$', ref.strip())
        if not m or (job_ids is not None and m.group(1) not in job_ids):
            continue
        for sid in sids.split():
            out.setdefault(m.group(1), set()).add(sid.strip())
    return out


def attribute(session, sid, trailers):
    """(job id, route) for one session, or (None, None). Order: a Claude-Session trailer, the transcript's gitBranch, the session name."""
    for jid, sids in trailers.items():
        if sid in sids:
            return jid, 'trailer'
    for b, _ in sorted(session['branches'].items(), key=lambda kv: -kv[1]):
        m = JOB_BRANCH.match(b)
        if m:
            return m.group(1), 'branch'
    for n in session['names']:
        m = JOB_NAME.match(n)
        if m:
            return m.group(1), 'name'
    return None, None


def usage_by_job(rows, sessions, trailers, since_day=None):
    """-> {'jobs': {id: {'sessions', 'routes', 'calls', 'replies', 'models', 'cost', 'first', 'last', 'wall_s', 'budget'}}, 'unattributed': {...}, 'week': {...}}.
    `rows`: the jobs registry rows (only their ids count as jobs); `sessions`: usage_by_session()['sessions']; `trailers`: branch_trailers()."""
    ids = {r['id'] for r in rows}
    jobs, un = {}, {'sessions': 0, 'calls': 0, 'models': {}, 'cost': 0.0}
    week = {'sessions': 0, 'calls': 0, 'models': {}, 'cost': 0.0}

    def add(dst, t):
        dst['calls'] += t['calls']
        for m, vec in t['models'].items():
            acc = dst['models'].setdefault(m, [0, 0, 0, 0])
            for i, x in enumerate(vec):
                acc[i] += x

    for sid, s in sessions.items():
        jid, route = attribute(s, sid, trailers)
        t = totals(s)
        c = (s['cost'] or {}).get('usd', 0.0)
        if since_day:
            w = totals(s, since_day)
            if w['calls'] or w['models']:
                week['sessions'] += 1
                add(week, w)
                week['cost'] += c if s['last'] and s['last'][:10] >= since_day and (s['first'] or '')[:10] >= since_day else 0.0
        if jid in ids:
            j = jobs.setdefault(jid, {'sessions': 0, 'routes': {}, 'calls': 0, 'replies': 0, 'models': {}, 'cost': 0.0, 'first': None, 'last': None, 'subagents': 0})
            j['sessions'] += 1
            j['subagents'] += s['subagents']
            j['routes'][route] = j['routes'].get(route, 0) + 1
            j['replies'] += t['replies']
            j['cost'] += c
            add(j, t)
            if s['first'] and (j['first'] is None or s['first'] < j['first']):
                j['first'] = s['first']
            if s['last'] and (j['last'] is None or s['last'] > j['last']):
                j['last'] = s['last']
        else:
            un['sessions'] += 1
            un['cost'] += c
            add(un, t)
    for j in jobs.values():
        j['wall_s'] = _span(j['first'], j['last'])
    return {'jobs': jobs, 'unattributed': un, 'week': week}


def _span(a, b):
    try:
        f = lambda x: datetime.fromisoformat(x.replace('Z', '+00:00'))
        return int((f(b) - f(a)).total_seconds())
    except (TypeError, ValueError, AttributeError):
        return None


def budget_from_brief(text):
    """The tool-call budget a brief states ('Budget about 70 tool calls', 'about 70 tool calls'), or None."""
    m = re.search(r'(?:budget|about|up to)\s+(?:about\s+)?(\d{2,3})\s+tool calls', text or '', re.I)
    return int(m.group(1)) if m else None


def tok(n):
    n = int(n)
    return f'{n / 1e6:.1f}M' if n >= 1e6 else f'{n / 1e3:.0f}k' if n >= 1e4 else str(n)


def model_line(models):
    """'opus-5-5 in 5k out 215k cache r68.0M w463k; sonnet-5-5 ...' (model names without the claude- prefix)."""
    parts = []
    for m, v in sorted(models.items(), key=lambda kv: -sum(kv[1])):
        parts.append(f'{m.replace("claude-", "")} in {tok(v[0])} out {tok(v[1])} cache r{tok(v[2])} w{tok(v[3])}')
    return '; '.join(parts) or 'no tokens'


def week_start(now=None, days=7):
    return ((now or datetime.now(timezone.utc)) - timedelta(days=days)).strftime('%Y-%m-%d')


def cache_file(root):
    return Path(root) / '_scratch' / CACHE_NAME


if __name__ == '__main__':
    t0 = time.time()
    root = Path(__file__).resolve().parent.parent
    days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 7
    u = usage_by_session(cache_path=cache_file(root))
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in (root / 'registries' / 'jobs').glob('*.json')]
    r = usage_by_job(rows, u['sessions'], branch_trailers(root), week_start(days=days))
    print(f'{u["source"]}: {u["files"]} files, {len(u["sessions"])} sessions, {u["skipped"]} lines skipped, read {u["read_at"]}, {time.time() - t0:.1f} s')
    for jid, j in sorted(r['jobs'].items(), key=lambda kv: int(kv[0][1:])):
        print(f'{jid}: {j["sessions"]} sessions {j["routes"]}, {j["calls"]} calls, ${j["cost"]:.2f} est; {model_line(j["models"])}')
    un = r['unattributed']
    print(f'unattributed: {un["sessions"]} sessions, {un["calls"]} calls, ${un["cost"]:.2f} est')
