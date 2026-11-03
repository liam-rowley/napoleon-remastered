"""Napoleon's rules for the job pipeline: the hook module warscape-core's `wsc jobs` and `wsc policy` load (`wsc.toml` [jobs] hooks; napoleon J62).

purpose: the game-specific half of the job pipeline, as the five hook names of warscape/hooks.py: the found-path rule for briefs (row 80, J11) and its registry-gap count on the `jobs check` line, rule 76 (every core candidate folder has a promotion job), rule 79 (a change to proxy/ or harness/, or a core pin that changes the core's own proxy/ or harness/, needs 20 consecutive acceptance passes on the final build, J4, J44, J45, J58) and the PC line of the status page (rule 75, J44; its usage half J49: Claude usage read from Claude Code's own local transcripts by tools/usage_reader.py, read-only, no conversation text, cost shown as an estimate)
usage: not run by hand: `python3 core/wsc.py jobs check|view` and `python3 core/wsc.py policy --branch <branch>` call it; `python3 -m unittest tests.test_jobs_hooks` tests it
when: automatic, through wsc.toml [jobs] hooks; edit it when one of those rules changes (rules 76 and 79 in docs/plans/PLAN.md section 4, the J5 ledger)
not-a-verb: a hook module the core's jobs and policy verbs import; it has no command line of its own

Everything generic (branch kinds, the decisions file, the session-trailer rule, review rounds) is in the core. What stays here needs this repo's folders:
discovery/core/briefpaths.py (moves with discovery/core in J64), harness/napoleon/adapter.json, harness/acceptance/, `<area>/core/` candidate folders.
The legacy id sets that exempt old jobs from two rules are data (`jobs/legacy.json`, read by the core), not code.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# ------------------------------------------------------------------ brief rule (row 80, J11): game-side paths only as registry ids
_KNOWN = {}


def _briefpaths(root):
    here = str(Path(root) / 'discovery' / 'core')   # briefpaths imports its siblings (tsvgz) later, so the folder stays on the path
    if here not in sys.path:
        sys.path.insert(0, here)
    import briefpaths
    return briefpaths


def brief_problems(ctx, jid, row, text):
    bp = _briefpaths(ctx.root)
    if str(ctx.root) not in _KNOWN:
        _KNOWN[str(ctx.root)] = bp.load_known(ctx.root)
    return [f'found path: {e}' for e in bp.found_path_problems(text, _KNOWN[str(ctx.root)])]


def summary(ctx, rows, read):
    bp = _briefpaths(ctx.root)
    gaps = sum(len(bp.registry_gaps(read(f'jobs/{r["id"]}/brief.md') or '')[0]) for r in rows)
    return f'{gaps} registry gaps in briefs'


# ------------------------------------------------------------------ rule 76 (PLAN section 4, J5 ledger row 76; code since J12)
# Every core candidate folder (`<area>/core/`) is listed here with the job that promotes it to warscape-core, or None while that job has no
# row yet (named needs_brief in the promoting job's report). A folder whose promotion job is done must be gone (its code lives in the core now),
# and an unlisted folder fails.
PROMOTIONS = {
    'proxy/core': 'J12',      # -> warscape-core proxy/src
    'harness/core': 'J12',    # -> warscape-core harness/
    'saves/core': 'J12',      # -> warscape-core saves/
    'discovery/core': None,   # phase 2 promotion, after the discovery gate J11 (no row yet)
    'upscale/core': None,     # its own promotion, after J50 and J51 (no row yet)
    'uiscale/core': None,     # J66 stop-gap scaler; its promotion follows J67 (no row yet)
    'viewer/core': None,      # the review viewer (J31): promotion with the RmlUi host work (no row yet)
    'release/core': None,     # the release builder, installer scripts and support bundle (J38): a core job when a second game ships (no row yet)
}


def promotion_problems(rows, tracked_dirs, table=None):
    """Rule 76 errors. `tracked_dirs`: repo-relative folders holding tracked files; `table`: folder -> promoting job id or None."""
    table = PROMOTIONS if table is None else table
    by = {r['id']: r for r in rows}
    cores = sorted({'/'.join(d.split('/')[:2]) for d in tracked_dirs if len(d.split('/')) >= 2 and d.split('/')[1] == 'core'
                    and d.split('/')[0] != 'core'})
    errs = []
    for d in cores:
        if d not in table:
            errs.append(f'rule 76: {d}/ is a core candidate with no promotion job: add it to PROMOTIONS in tools/jobs_hooks.py '
                        '(the job id, or None until its row exists)')
            continue
        j = table[d]
        if j and j not in by:
            errs.append(f'rule 76: {d}/ is promoted by {j}, which has no row')
        elif j and by[j].get('status') == 'done':
            errs.append(f'rule 76: {d}/ still exists but its promotion job {j} is done: the code belongs in warscape-core now')
    return errs


def queue_problems(ctx, rows, files):
    return promotion_problems(rows, {str(Path(f).parent.as_posix()) for f in files})


# ------------------------------------------------------------------ rule 75 (J44): the PC's state on the status page
USAGE_NOTE = ('tokens and tool calls from Claude Code\'s own transcripts, cost is Claude Code\'s estimate not a bill; '
              'plan and weekly-limit usage is not on disk: read it in the Claude app (Settings, Usage)')


def _usage_reader():
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import usage_reader
    return usage_reader


def usage_state(root, projects_dir=None, now=None):
    """The usage half of rule 75 (J49): {'source': one line, 'error': text or None, 'week': {...}, 'jobs': [per-job rows], 'unattributed': {...}}.
    Fails soft: a missing folder or an odd file only changes the text."""
    ur = _usage_reader()
    root = Path(root)
    u = ur.usage_by_session(projects_dir, cache_path=ur.cache_file(root), now=now)
    if u['error']:
        return {'source': f'{u["error"]}; {USAGE_NOTE}', 'error': u['error'], 'week': None, 'jobs': [], 'unattributed': None}
    rows = []
    for p in sorted((root / 'registries' / 'jobs').glob('*.json')):
        try:
            rows.append(json.loads(p.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            pass
    since = ur.week_start(now)
    r = ur.usage_by_job(rows, u['sessions'], ur.branch_trailers(root, {x['id'] for x in rows}), since)
    out = []
    for jid, j in sorted(r['jobs'].items(), key=lambda kv: int(kv[0][1:]) if kv[0][1:].isdigit() else 0):
        try:
            budget = ur.budget_from_brief((root / 'jobs' / jid / 'brief.md').read_text(encoding='utf-8'))
        except OSError:
            budget = None
        out.append({'id': jid, 'sessions': j['sessions'], 'routes': j['routes'], 'calls': j['calls'], 'budget': budget, 'cost': j['cost'],
                    'wall_s': j['wall_s'], 'models': ur.model_line(j['models']), 'last': (j['last'] or '')[:10]})
    wk, un = r['week'], r['unattributed']
    wtok = sum(sum(v) for v in wk['models'].values())
    src = (f'{u["source"]}, {u["files"]} files read {u["read_at"]}, {u["skipped"]} lines skipped; last 7 days: {wk["sessions"]} sessions, {wk["calls"]} tool calls, '
           f'{ur.tok(wtok)} tokens ({ur.model_line(wk["models"])}); {USAGE_NOTE}')
    return {'source': src, 'error': None, 'week': wk, 'jobs': out,
            'unattributed': {'sessions': un['sessions'], 'calls': un['calls'], 'cost': un['cost'], 'models': ur.model_line(un['models'])}}


def usage_html(us):
    """The per-job table of a usage_state (a closed <details>): calls actual / budget, tokens by model, the cost estimate."""
    import html
    if not us or not us.get('jobs'):
        return ''
    e = html.escape
    rows = []
    for j in us['jobs']:
        wall = '' if j['wall_s'] is None else f'{j["wall_s"] / 3600:.1f} h span'
        bud = f' / {j["budget"]}' if j['budget'] else ''
        rows.append(f'<tr><td><a href="#{e(j["id"])}">{e(j["id"])}</a></td><td>{j["sessions"]}</td><td>{j["calls"]}{bud}</td><td>{e(j["models"])}</td>'
                    f'<td>~${j["cost"]:.2f} (estimate)</td><td>{e(wall)}</td><td>{e(j["last"])}</td></tr>')
    un = us['unattributed']
    tail = (f'<p class="muted">Unattributed (no Claude-Session trailer on a job or brief branch, no job branch, no J&lt;n&gt;- name): {un["sessions"]} sessions, '
            f'{un["calls"]} tool calls, ~${un["cost"]:.2f} (estimate).</p>') if un else ''
    return ('<details class="doc"><summary>Claude usage per job</summary><table><tr><th>job</th><th>sessions</th><th>tool calls / brief budget</th>'
            '<th>tokens by model</th><th>cost</th><th>wall</th><th>last</th></tr>' + ''.join(rows) + '</table>' + tail + '</details>')


def pc_state(root, read_json=None, projects_dir=None):
    """The PC's state for the view, or None off the PC (no adapter state_dir). Lock holder, watcher version and heartbeat age, the installed
    kit and DLL build, the last acceptance pass (the ledger on this checkout) and the usage source."""
    import time as _time
    root = Path(root)
    try:
        ad = json.loads((root / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    state = Path(ad.get('state_dir', ''))
    if not state.is_dir():
        return None
    w = state / ad.get('watcher_subdir', 'watcher')

    def text(p):
        try:
            return p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return None
    lock = (text(w / 'game.lock') or '').strip()
    st, inst = {}, {}
    try:
        st = json.loads(text(w / 'watcher.status') or '{}')
    except ValueError:
        pass
    try:
        inst = json.loads(text(state / 'install.json') or '{}')
    except ValueError:
        pass
    alive = w / 'watcher.alive'
    age = int(_time.time() - alive.stat().st_mtime) if alive.exists() else None
    try:
        us = usage_state(root, projects_dir)
    except Exception as ex:   # the usage half must never break the view
        us = {'source': f'unavailable ({ex.__class__.__name__}); {USAGE_NOTE}', 'jobs': [], 'unattributed': None}
    ledger = [l for l in (text(root / 'harness' / 'acceptance' / 'ledger.jsonl') or '').splitlines() if l.strip()]
    last = json.loads(ledger[-1]) if ledger else None
    return {'lock': lock or 'free', 'watcher': st.get('version'), 'heartbeat_age_s': age,
            'game': (st.get('game_state') or {}).get('state'), 'kit': inst.get('kit_id') or 'not installed', 'build': inst.get('build_id'),
            'last_acceptance': ({k: last.get(k) for k in ('pass', 'result', 'build_id', 'watcher', 'utc', 'run')} if last else None),
            'usage': us['source'], 'usage_detail': us}


def pc_block(pc):
    import html
    if not pc:
        return ''
    e = html.escape
    la = pc['last_acceptance']
    acc = (f"pass {la['pass']} {la['result']} on build {la['build_id']}, watcher {la['watcher']} ({la['utc']}, {la['run']})" if la else 'none in the ledger')
    hb = 'no heartbeat' if pc['heartbeat_age_s'] is None else f"heartbeat {pc['heartbeat_age_s']} s ago"
    return (f'<p class="muted">PC: lock <code>{e(pc["lock"])}</code> · watcher {e(str(pc["watcher"]))} ({e(hb)}, game {e(str(pc["game"]))}) · '
            f'kit <code>{e(pc["kit"])}</code> · last acceptance: {e(acc)} · usage source: {e(pc["usage"])}</p>' + usage_html(pc.get('usage_detail')))


def view_panel(ctx):
    return pc_block(pc_state(ctx.root))


# ------------------------------------------------------------------ rule 79 (J4, J44, J45, J58): acceptance passes for proxy/ and harness/
ACC_LEDGER = 'harness/acceptance/ledger.jsonl'
ACC_BASELINE = 'harness/acceptance/baseline.json'
ACC_NEEDED = 20
ACC_CHECKERS = ('core/harness/acceptance.py', 'harness/core/acceptance.py')   # after J12, then before it (an older base)


def _git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, check=True).stdout


def show(root, ref, path):
    """File text at ref, or None when it does not exist there. A path under `core/` is read inside the submodule at the commit the ref's
    gitlink pins (`git show <ref>:core/...` does not reach into a submodule; J12)."""
    try:
        return _git(root, 'show', f'{ref}:{path}')
    except subprocess.CalledProcessError:
        pass
    if path.startswith('core/'):
        try:
            pin = _git(root, 'rev-parse', f'{ref}:core').strip()
            return subprocess.run(['git', '-C', str(Path(root) / 'core'), 'show', f'{pin}:{path[5:]}'],
                                  capture_output=True, text=True, check=True).stdout
        except (subprocess.CalledProcessError, OSError):
            return None
    return None


def show_first(root, ref, *paths):
    """The first of `paths` that exists at ref (the harness moved from harness/core/ to the core's harness/ in J12)."""
    for p in paths:
        t = show(root, ref, p)
        if t is not None:
            return t
    return None


def dll_build_id(root):
    """The final DLL's build id at HEAD, committed content only: the core's proxy/tools/build_id.py, the implementation build.sh uses (J45)."""
    import importlib.util
    root = Path(root)
    try:
        tool = next(p for p in (root / 'core/proxy/tools/build_id.py', root / 'proxy/tools/build_id.py') if p.is_file())
        spec = importlib.util.spec_from_file_location('build_id', tool)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.build_id(root, 'HEAD', dirty=False)
    except (OSError, ValueError) as e:   # an input not committed: no ledger line can match, so rule 79 refuses and names it
        return f'nogit ({e})'


def acc_exempt(path):
    """runs/ folders, READMEs and the acceptance files themselves; by path segment and name, never by substring (J4 review 6)."""
    parts = path.split('/')
    return 'runs' in parts[:-1] or parts[-1] == 'README.md' or path.startswith('harness/acceptance/')


def acceptance_active(ledger, baseline, checker_src, root=None):
    """Rule 79 is on only when the base holds the ledger and a valid baseline (J4 review 1): a ledger alone cannot be satisfied, since
    acceptance refuses to run without a baseline (rule 74), and would refuse every proxy/ and harness/ job, including the one that builds it.
    The baseline is judged by `checker_src`, the BASE's acceptance.py (J4 review round 2): a branch that weakens baseline_problems in its own
    copy cannot switch the rule off for itself."""
    if ledger is None or baseline is None or not checker_src:
        return False
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    ns = {'__name__': 'acceptance_base', '__file__': str(root / ACC_CHECKERS[0])}
    try:
        exec(compile(checker_src, f'<base>/{ACC_CHECKERS[0]}', 'exec'), ns)
        return not ns['baseline_problems'](json.loads(baseline))
    except (ValueError, TypeError, AttributeError, KeyError, SyntaxError):
        return False


def rule79_path(path):
    """A proxy/ or harness/ path that rule 79 counts, in this repo or inside the core (J58)."""
    return path.startswith(('proxy/', 'harness/')) and not acc_exempt(path)


def core_pin_diff(base, head='HEAD', root=None):
    """The core's paths changed between the commits the gitlink pins at `base` and at `head` (J58), or a str saying why the pins cannot
    be compared: rule 79 then counts the pin change, as before J58 (fail closed)."""
    root = Path(root) if root else Path(_git('.', 'rev-parse', '--show-toplevel').strip())
    run = lambda *a: subprocess.run(['git', '-C', str(root), *a], capture_output=True, text=True)
    pins = [run('rev-parse', '--verify', '--quiet', f'{r}:core').stdout.strip() for r in (base, head)]
    a, b = (p[:12] or '?' for p in pins)
    if not all(pins):
        return f'cannot compare core pins {a}..{b}: {base if not pins[0] else head} has no core gitlink'
    p = run('-C', 'core', 'diff', '--no-renames', '--name-only', pins[0], pins[1])   # a rename out of proxy/ lists its old path too
    if p.returncode:
        return (f'cannot compare core pins {a}..{b}: {(p.stderr.strip().splitlines() or ["git diff failed"])[-1]} '
                f'(fetch both: git -C core fetch origin {pins[0]} {pins[1]})')
    return [l for l in p.stdout.splitlines() if l]


def acceptance_problems(changed, acc):
    """Rule 79. `acc` is None (skip) or {'active': acceptance_active() on the base, 'ledger': its text on the branch or None, 'build_id', 'watcher', 'branch',
    'exists': path -> bool on the branch, 'core_diff': core_pin_diff() when the pin moved}. A change to proxy/ or harness/ needs ACC_NEEDED passes in a row
    at the end of the ledger on this build and watcher, each run for this branch and naming its run and a committed evidence file; a fail, a pass of
    another build or branch, or a pass without evidence ends the run. A pin change counts only when the core's own proxy/ or harness/ changed
    between the two pins, or when they cannot be compared (J58)."""
    if not acc or not acc.get('active'):
        return []
    code = [p for p in changed if rule79_path(p)]
    if 'core' in changed:   # the pin (J12): judged on the core's diff (J58)
        diff = acc.get('core_diff')
        if isinstance(diff, list):
            code += [f'core/{p}' for p in diff if rule79_path(p)]
        else:
            code.append(f'core ({diff or "cannot compare core pins: no core diff was computed"})')
    if not code:
        return []
    exists = acc.get('exists') or (lambda p: False)
    n, unproved, foreign = 0, None, None
    for line in reversed([l for l in (acc.get('ledger') or '').splitlines() if l.strip()]):
        r = json.loads(line)
        if not (r.get('result') == 'pass' and r.get('build_id') == acc['build_id'] and r.get('watcher') == acc['watcher']):
            break
        if r.get('branch') != acc.get('branch'):
            # J44 review: harness/ is not in the build id, so a branch changing only harness/ would inherit the previous branch's passes
            foreign = f"pass {r.get('pass')} was run for {r.get('branch') or 'no branch'}"
            break
        if not (r.get('run') and r.get('evidence') and exists(r['evidence'])):
            unproved = r.get('evidence') or f"pass {r.get('pass')} names no evidence file"
            break
        n += 1
    if n >= ACC_NEEDED:
        return []
    why = (f' (the streak ends at a line whose evidence is not committed: {unproved})' if unproved else
           f' (the streak ends at a line of another branch: {foreign})' if foreign else '')
    return [f'rule 79: this branch changes {code[0]}{" and more" if len(code) > 1 else ""} but {ACC_LEDGER} holds {n} consecutive acceptance passes '
            f'on build {acc["build_id"]}, watcher {acc["watcher"]}{why} (need {ACC_NEEDED}): run `python3 core/harness/acceptance.py run` on the final build']


def collect_acceptance(root, facts):
    """The inputs of rule 79 for the branch in `facts` (the core's `collect_facts` plus 'kind'), read from git: what the old `pr_policy.main` gathered."""
    base, mb, changed = facts['base'], facts['merge_base'], facts['changed']
    wsrc = show_first(root, 'HEAD', 'core/harness/watcher.ps1', 'harness/core/watcher.ps1') or ''
    wm = re.search(r"^\$Version\s*=\s*'([^']+)'", wsrc, re.M)
    return {'active': acceptance_active(show(root, base, ACC_LEDGER), show(root, base, ACC_BASELINE), show_first(root, base, *ACC_CHECKERS), root),
            'ledger': show(root, 'HEAD', ACC_LEDGER), 'build_id': dll_build_id(root), 'watcher': wm.group(1) if wm else '?', 'branch': facts['branch'],
            'exists': lambda p: show(root, 'HEAD', p) is not None, 'core_diff': core_pin_diff(mb, 'HEAD', root) if 'core' in changed else None}


def policy_problems(ctx, facts):
    """Rule 79 on job branches. `facts['acceptance']` (the tests and the J62 replay pass recorded inputs) replaces the git reads."""
    if facts.get('kind') != 'job':
        return []
    acc = facts.get('acceptance') or collect_acceptance(ctx.root, facts)
    return acceptance_problems(facts['changed'], acc)
