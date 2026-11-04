#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the shell-call rules of this repo (D21, D50, J18, J20, J76): the commit trailer, no --no-verify, no git in a
protected PC folder, no writes there outside `_scratch\\<owner>\\`, no game launch or kill outside the watcher, and no `gh pr merge` of a plan/ or meta/ branch.

purpose: refuse a Bash or PowerShell call before it runs when a simple command in it (found by tools/hook_parse.py through separators, blocks, subshells, bash -c, cmd /c, powershell -Command, Start-Process and nice/timeout/env/sudo wrappers) is: a `git commit` (also behind global options or an alias) without `--trailer "Claude-Session: <this session id>"` (the rule is warscape-core's warscape/trailer.py); `--no-verify` on git commit, push, merge, rebase, cherry-pick or am; git working in a protected root (both game folders, the PC state folder; cwd, -C, --git-dir, --work-tree, GIT_DIR, init/clone/worktree arguments); a write into a protected root outside `<state>\\_scratch\\<owner>\\` or into the AppData prefs file and save_games (redirects of every kind, cp mv rm install rsync dd tar ln robocopy Copy-Item Set-Content ..., inline python/node/powershell code); starting or killing Napoleon.exe or Empire.exe (use core/harness/job.sh); `gh pr merge` or a gh api merge of a plan/ or meta/ branch (D50: only Liam merges them); deleting a remote main, plan/, meta/, job/ or brief/ branch. Only a script that is this checkout's core pc_deploy.py or job.sh is exempt, per command, and its redirections are still checked. Each denial says what to run instead
usage: wired in .claude/settings.json (PreToolUse, matcher Bash|PowerShell); reads the hook JSON on stdin; test: echo '{"session_id":"s","cwd":"/c/x","tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | python3 tools/claude_hook.py
when: automatic on every shell call in a Claude Code session in this repo; never run by hand except to test it
not-a-verb: Claude Code runs it with a JSON protocol on stdin and stdout, not through the wsc CLI

Failing closed without wedging (J20: a non-zero exit blocks the call): roots unreadable -> a conservative path pattern instead (any program files,
steamapps, napoleon_remastered_pc or total war folder; no scratch allowance); core/ missing -> `git commit` is denied with the command that fixes it;
decide() raising -> panic(), a text screen that denies only a trailer-less git commit and a protected-folder word with a write, git, launch or kill
word. main() always returns 0. An unresolvable write or git target is denied only when the command also names a protected root (brief J76 default,
open for Liam); `echo x > "$OUT"` stays allowed.

Residuals (the hook sees command text, not behaviour): `python3 script.py` and any program that writes where the shell cannot see; a write through
a shell variable that is not set in the same command or the hook's environment; a path assembled inside inline code; a rule 79 or watcher.ini
weakening done by a sanctioned script (core W25).
"""
import importlib.util
import json
import re
import shlex
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))   # the trailer rule is the core's (J62)
try:
    from warscape.trailer import commit_lacks_trailer
    CORE_OK = True
except ImportError:
    CORE_OK = False

    def commit_lacks_trailer(cmd, session_id, trailer='Claude-Session'):
        return False


def _load_parser():
    if 'hook_parse' in sys.modules:
        return sys.modules['hook_parse']
    spec = importlib.util.spec_from_file_location('hook_parse', Path(__file__).with_name('hook_parse.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules['hook_parse'] = mod
    spec.loader.exec_module(mod)
    return mod


hp = _load_parser()
norm, is_abs, rp, cname, UNKNOWN = hp.norm, hp.is_abs, hp.rp, hp.cname, hp.UNKNOWN
SCRATCH_OWNER = re.compile(r'^[a-z0-9][a-z0-9_-]{0,31}$')
ESCAPED = hp.ESCAPED
FB_PATH = re.compile(r'(?:^|/)(?:program files[^/]*|steamapps|napoleon_remastered_pc|[^/]*total war[^/]*)(?:/|$)')
FB_TEXT = re.compile(r'program files|steamapps|napoleon_remastered_pc|total war|\b(?:progra|napole|empire)\w*~\d', re.I)
SHORT_NAME = re.compile(r'\b(?:progra|napole|empire)\w*~\d', re.I)
PANIC_VERB = re.compile(r'>|\b(?:cp|mv|rm|rmdir|mkdir|touch|tee|install|rsync|dd|tar|ln|robocopy|xcopy|copy|move|ren|del|truncate|chmod|chown|'
                        r'git|sed|unzip|Remove-Item|Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|New-Item|taskkill|Stop-Process|'
                        r'pkill|killall|start|Start-Process|python3?|node|perl|ruby|powershell|pwsh)\b', re.I)
PANIC_COMMIT = re.compile(r'\bgit\b.*\bcommit(?![\w-])', re.S)
FALLBACK_NOTE = ' (protected roots unreadable: restore harness/napoleon/adapter.json and discovery/napoleon/games.json)'
NOVERIFY_SUBS = {'commit', 'push', 'merge', 'rebase', 'cherry-pick', 'am'}
LONG_VAL = {'--message', '--file', '--reuse-message', '--reedit-message', '--fixup', '--squash', '--author', '--date', '--trailer', '--template',
            '--cleanup', '--strategy', '--strategy-option', '--onto', '--exec', '--push-option', '--receive-pack'}
GIT_PLAIN = {'--no-pager', '-P', '-p', '--paginate', '--bare', '--no-optional-locks', '--no-replace-objects', '--literal-pathspecs',
             '--glob-pathspecs', '--noglob-pathspecs', '--icase-pathspecs', '--no-advice', '--no-lazy-fetch'}
GH_VAL = {'-R', '--repo', '-b', '--body', '-F', '--body-file', '-t', '--subject', '-A', '--author-email', '--match-head-commit'}
WRITE_VERB = re.compile(r'''\bopen\s*\(.*?[,=]\s*['"][^'"]*[wax+]|\.write|write_text|write_bytes|shutil\.|os\.(?:remove|rename|replace|unlink|rmdir|'''
                        r'''makedirs|mkdir|system|popen)|subprocess|rmtree|Remove-Item|Set-Content|Add-Content|Out-File|New-Item|Copy-Item|'''
                        r'''Move-Item|Rename-Item|Clear-Content|fs\.\w*(?:write|unlink|rm|mkdir|rename|append)\w*|writeFile|File\.(?:write|open|delete)|'''
                        r'''unlink|\bcp\b|\brm\b|\bdel\b|\bmv\b|\bmkdir\b''', re.I)
INLINE = {'python': ('-c',), 'python3': ('-c',), 'py': ('-c',), 'node': ('-e', '-p', '--eval'), 'perl': ('-e', '-E'), 'ruby': ('-e',)}
SCRIPT_SUFFIXES = ('core/proxy/tools/pc_deploy.py', 'proxy/tools/pc_deploy.py', 'core/harness/job.sh', 'harness/job.sh')
SANCTIONED = ('pc_deploy.py', 'job.sh')
KILLERS = {'taskkill', 'stop-process', 'spps', 'pkill', 'killall', 'wmic', 'pskill', 'tskill'}
LAUNCHERS = {'start-process', 'invoke-item', 'ii', 'explorer', 'rundll32', 'xdg-open', 'open', 'steam', 'saps'}


class Roots:
    """What the hook protects. games/state come from their owners; extra: write-protected AppData paths; fallback: the conservative pattern."""

    def __init__(self, games=(), state=None, extra=(), fallback=False):
        self.games, self.state, self.extra, self.fallback = list(games), state, list(extra), fallback
        self.forms = []
        for r in self.games + ([state] if state else []):
            self.forms += [r, '/' + r[0] + r[2:] if re.match(r'^[a-z]:/', r) else r]
        for r in self.extra:
            self.forms += [r, '/' + r[0] + r[2:] if re.match(r'^[a-z]:/', r) else r]

    def hit(self, p):
        if self.fallback:
            return bool(FB_PATH.search(p))
        return any(under(p, r) for r in self.games) or bool(self.state and under(p, self.state))

    def scratch_ok(self, p):
        if not self.state or self.fallback:
            return False
        rest = p[len(self.state) + 1:].split('/') if under(p, self.state) and p != self.state else []
        return len(rest) >= 2 and rest[0] == '_scratch' and bool(SCRATCH_OWNER.match(rest[1]))

    def protected_write(self, p):
        return any(under(p, e) for e in self.extra)

    def names(self, text):
        t = hp.ESCAPED.sub('', text).replace('\\', '/').lower()
        t = re.sub(r'/{2,}', '/', t)
        if self.fallback:
            return bool(FB_TEXT.search(t))
        return bool(SHORT_NAME.search(t)) or any(f in t for f in self.forms)


FALLBACK = Roots(fallback=True)


def under(p, r):
    return p == r or p.startswith(r + '/')


def resolve(arg, cwd):
    """The normalised absolute path of a shell argument, or None when it cannot be known ($VAR, ~, a flag, empty)."""
    p = rp(arg, cwd)
    return p if isinstance(p, str) else None


def expand_short(p):
    """8.3 short names (PROGRA~2, NAPOLE~1) to long ones with GetLongPathNameW; the path unchanged when it does not exist or off Windows."""
    if sys.platform != 'win32':
        return p
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        n = ctypes.windll.kernel32.GetLongPathNameW(p.replace('/', '\\'), buf, 1024)
        return buf.value if 0 < n < 1024 else p
    except Exception:
        return p


def _short(p):
    return expand_short(p)


def protected_roots(root=ROOT):
    """(game folders, state folder) read from their owners: harness/napoleon/adapter.json and discovery/napoleon/games.json."""
    ad = json.loads((root / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
    games = json.loads((root / 'discovery' / 'napoleon' / 'games.json').read_text(encoding='utf-8'))
    gdirs = {norm(ad['game_dir']), norm(games['napoleon']['root']), norm(games['empire']['root'])}
    return sorted(gdirs), norm(ad['state_dir'])


def appdata_paths(root=ROOT, environ=None):
    """The AppData files the Edit rows protect (the prefs file and save_games), from adapter.json `appdata_dir`; [] when unreadable."""
    import os
    try:
        ad = json.loads((root / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
        env = os.environ if environ is None else environ
        base = ad['appdata_dir'].replace('%APPDATA%', env.get('APPDATA') or str(Path.home() / 'AppData' / 'Roaming'))
        return [norm(base + '/scripts/preferences.script.txt'), norm(base + '/save_games')]
    except (OSError, ValueError, KeyError):
        return []


@lru_cache(maxsize=1)
def game_images():
    try:
        ad = json.loads((ROOT / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
        imgs = [ad['game_image']] + list(ad.get('other_images') or [])
    except (OSError, ValueError, KeyError):
        imgs = ['Napoleon.exe', 'Empire.exe']
    return [i.lower().removesuffix('.exe') for i in imgs]


def in_roots(p, roots):
    return isinstance(p, str) and roots.hit(p)


def scratch_ok(p, roots):
    return roots.scratch_ok(p)


# ---- git config aliases -------------------------------------------------------------------------------------------------------------------

def alias_files():
    import os
    out = [Path.home() / '.gitconfig']
    xdg = os.environ.get('XDG_CONFIG_HOME')
    out.append(Path(xdg) / 'git' / 'config' if xdg else Path.home() / '.config' / 'git' / 'config')
    g = ROOT / '.git'
    try:
        if g.is_file():
            gd = Path(g.read_text(encoding='utf-8', errors='replace').split(':', 1)[1].strip())
            cd = gd / 'commondir'
            out.append(((gd / cd.read_text().strip()) if cd.is_file() else gd).resolve() / 'config')
        else:
            out.append(g / 'config')
    except (OSError, IndexError, ValueError):
        pass
    return out


@lru_cache(maxsize=16)
def read_aliases(path):
    """{name: value} from the [alias] section of a git config file read as plain text (size-capped)."""
    try:
        p = Path(path)
        if p.stat().st_size > 262144:
            return {}
        text = p.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return {}
    out, on = {}, False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('['):
            on = s.lower().startswith('[alias')
        elif on and '=' in s and not s.startswith(('#', ';')):
            k, v = s.split('=', 1)
            out[k.strip().lower()] = v.strip().strip('"')
    return out


def aliases_for(opts_c):
    out = {}
    for f in alias_files():
        out.update(read_aliases(str(f)))
    for kv in opts_c:
        if kv.lower().startswith('alias.') and '=' in kv:
            k, v = kv.split('=', 1)
            out[k[6:].lower()] = v
    return out


# ---- git ----------------------------------------------------------------------------------------------------------------------------------

def git_split(args):
    """(options, subcommand, rest): options holds C, c, git-dir, work-tree lists; the subcommand is found by skipping git's global options."""
    o = {'C': [], 'c': [], 'git-dir': [], 'work-tree': []}
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-C', '-c') and i + 1 < len(args):
            o[a[1:]].append(args[i + 1])
            i += 2
        elif a.startswith(('--git-dir', '--work-tree')):
            k = a.split('=')[0][2:]
            if '=' in a:
                o[k].append(a.split('=', 1)[1])
                i += 1
            else:
                o[k].append(args[i + 1] if i + 1 < len(args) else '')
                i += 2
        elif a.startswith('--config-env='):
            o['c'].append(a.split('=', 1)[1])
            i += 1
        elif a == '--namespace':
            i += 2
        elif a.startswith('-') and a != '-':
            i += 1
        else:
            return o, a, args[i + 1:]
    return o, None, []


def canonical_sub(o, sub, rest):
    """Follow git aliases (-c alias.X=..., the config files) to the real subcommand and its arguments."""
    if sub is None:
        return sub, rest
    al = aliases_for(o['c'])
    for _ in range(3):
        val = al.get(sub.lower())
        if val is None:
            break
        if val.startswith('!'):
            if re.search(r'\bgit\b[^;&|]*\bcommit(?![\w-])|^\s*commit(?![\w-])', val[1:]):
                return 'commit', rest
            break
        try:
            toks = shlex.split(val)
        except ValueError:
            toks = val.split()
        toks = [t for t in toks if t != 'git']
        if not toks:
            break
        sub, rest = toks[0], toks[1:] + rest
    return sub, rest


def has_no_verify(sub, rest):
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == '--':
            break
        if a.startswith('--'):
            name = a.split('=')[0]
            if len(name) >= 7 and '--no-verify'.startswith(name):
                return True
            if name in LONG_VAL and '=' not in a:
                i += 1
        elif a.startswith('-') and len(a) > 1 and sub == 'commit':
            for k, c in enumerate(a[1:]):
                if c == 'n':
                    return True
                if c in 'mFCctuS':
                    if c in 'mFCct' and k == len(a) - 2:
                        i += 1
                    break
        i += 1
    return False


def positionals(args):
    return [a for a in args if not a.startswith('-')]


def git_reason(u, roots, tainted, sid):
    o, sub, rest = git_split(u.args)
    sub, rest = canonical_sub(o, sub, rest)
    if sub == 'commit':
        if not CORE_OK:
            return ('This checkout has no core/ (every commit must carry its session trailer and the rule lives there): run '
                    'git submodule update --init, then commit again.')
        canon = 'git commit ' + ' '.join(shlex.quote(a) for a in rest)
        if commit_lacks_trailer(canon, sid):
            return (f'Every commit in this repo names its Claude Code session (`wsc policy` refuses a job whose report or review was '
                    f'committed without one). Run the same command again with this flag after `git commit`: '
                    f'--trailer "Claude-Session: {sid}"')
    if sub in NOVERIFY_SUBS and (has_no_verify(sub, rest) or any(c.lower().startswith('core.hookspath=') for c in o['c'])):
        return (f'`git {sub}` with --no-verify (or a -c core.hooksPath override) switches off the repo hooks: the pre-push hook runs `wsc gates --fast` '
                f'and the commit hook checks the session trailer. Run it again without the flag; if a hook fails, fix what it reports.')
    if sub == 'config' and any(a.lower().startswith('alias.') for a in rest):
        vals = [a for a in rest if not a.startswith('-')][1:]
        if any(re.search(r'\bcommit(?![\w-])', v) for v in vals):
            return ('Do not define a git alias for `commit`: it would dodge the Claude-Session trailer check. Run `git commit ... --trailer '
                    f'"Claude-Session: {sid}"` directly.')
    # a git working in a protected root
    cwd = u.cwd
    bad = None
    for c in o['C']:
        p = rp(c, cwd, _short)
        if p is UNKNOWN:
            cwd = None
            if tainted:
                bad = bad or '<an unresolved -C folder>'
        elif p:
            if roots.hit(p):
                bad = bad or p
            cwd = p
    if bad is None:
        if cwd is None and tainted:
            bad = '<a folder the hook cannot resolve; this command names a protected folder>'
        elif cwd and roots.hit(cwd):
            bad = cwd
    if bad is None:
        cands = list(o['git-dir']) + list(o['work-tree'])
        for k in ('GIT_DIR', 'GIT_WORK_TREE'):
            if k in u.env:
                cands.append(u.env[k])
        for kv in o['c']:
            k, _, v = kv.partition('=')
            if k.lower() in ('core.worktree', 'core.hookspath'):
                cands.append(v)
        for a in rest:
            if a.startswith('--separate-git-dir'):
                cands.append(a.split('=', 1)[1] if '=' in a else '')
        pos = positionals(rest)
        if sub == 'init':
            cands += pos
        elif sub == 'clone':
            cands += pos[-1:]
        elif sub in ('worktree', 'submodule') and pos[:1] == ['add']:
            cands += pos[1:]
        for v in cands:
            p = rp(v, cwd, _short)
            if p is UNKNOWN:
                if tainted:
                    bad = '<a path the hook cannot resolve; this command names a protected folder>'
                    break
            elif p and roots.hit(p):
                bad = p
                break
    if bad:
        return (f'Never run git in a game folder or the PC state folder (CLAUDE.md, J18): this call would run git in {bad}. Work in the repo '
                f'checkout and sync files to the PC with core/proxy/tools/pc_deploy.py (sha-checked copies).')
    if sub == 'push':
        pos = positionals(rest)
        names = [p[1:] for p in pos[1:] if p.startswith(':')]
        if any(a in ('--delete', '-d') for a in rest):
            names += [p for p in pos[1:] if not p.startswith(':')]
        for n in names:
            n = re.sub(r'^refs/heads/', '', n.lstrip('+'))
            if re.match(r'^(main|plan/|meta/|job/|brief/)', n):
                return branch_msg(n)
    return None


def branch_msg(n):
    return (f'Never delete the remote branch {n}: main, plan/, meta/, job/ and brief/ branches are deleted by GitHub when their pull request merges. '
            f'Only scratch/* branches are yours to delete (git push origin --delete scratch/<name>).')


# ---- writes -------------------------------------------------------------------------------------------------------------------------------

CMD_FLAG = re.compile(r'^/[A-Za-z?]{1,2}$')


def writer_args(name, args):
    """The raw arguments a write command writes, by its rule (see the WRITERS table); [] when it is no write command."""
    pos = [a for a in args if not a.startswith('-')]
    low = [a.lower() for a in args]

    def last_or_t():
        t = [args[i + 1] for i, a in enumerate(args[:-1]) if a in ('-t', '--target-directory')]
        return t or pos[-1:]
    if name in ('cp', 'install', 'rsync', 'ln', 'copy-item', 'cpi', 'copy', 'xcopy', 'chmod', 'chown', 'expand-archive'):
        if name in ('copy-item', 'cpi', 'expand-archive'):
            for i, a in enumerate(low[:-1]):
                if a in ('-destination', '-destinationpath'):
                    return [args[i + 1]]
            return pos[1:2]
        if name in ('copy', 'xcopy'):
            return [a for a in pos if not CMD_FLAG.match(a)][-1:]
        return last_or_t()
    if name in ('mv', 'mkdir', 'touch', 'rm', 'rmdir', 'tee', 'move-item', 'mi', 'new-item', 'ni', 'set-content', 'add-content', 'out-file',
                'remove-item', 'ri', 'rni', 'rename-item', 'set-itemproperty', 'clear-content', 'tee-object', 'truncate', 'mklink'):
        return pos
    if name in ('move', 'ren', 'rename', 'del', 'erase', 'rd'):
        return [a for a in pos if not CMD_FLAG.match(a)]
    if name == 'sed':
        return pos if any(a == '-i' or a.startswith(('-i', '--in-place')) for a in args) else []
    if name == 'unzip':
        return [args[i + 1] for i, a in enumerate(args[:-1]) if a == '-d']
    if name == 'dd':
        return [a[3:] for a in args if a.startswith('of=')]
    if name == 'robocopy':
        pp = [a for a in args if not re.match(r'^/[A-Z]{1,8}(?::.*)?$', a)]
        out = pp[1:2]
        if any(a.upper() in ('/MOVE', '/MIR', '/PURGE') for a in args):
            out = pp[:2]
        return out
    if name == 'tar':
        modes = ''
        for a in args[:1]:
            if not a.startswith('-'):
                modes += a
        for a in args:
            if re.match(r'^-[A-Za-z]+$', a):
                modes += a[1:]
        out = []
        if 'x' in modes:
            out += [args[i + 1] for i, a in enumerate(args[:-1]) if a in ('-C', '--directory')]
        if any(m in modes for m in 'cru'):
            for i, a in enumerate(args[:-1]):
                if a in ('-f', '--file') or (re.match(r'^-?[A-Za-z]*f[A-Za-z]*$', a) and (a.startswith('-') or i == 0) and a != '-C'):
                    out.append(args[i + 1])
                    break
        return out
    if name == 'find' and ('-delete' in args or '-exec' in args and any(a in ('rm', 'rmdir', 'mv') for a in args)):
        out = []
        for a in args:
            if a.startswith(('-', '(', '!')):
                break
            out.append(a)
        return out
    return []


def write_reason(u, roots, tainted):
    targets = [t for op, t in u.redirs if op in ('>', '>>', '>|', '&>', '&>>', '<>', '*>', '*>>') or
               (op == '>&' and not re.fullmatch(r'\d+|-', t))]
    targets += writer_args(u.name, u.args)
    for t in targets:
        p = rp(t, u.cwd, _short)
        if p is None:
            continue
        if p is UNKNOWN:
            if tainted:
                return (f'This call writes to a target the hook cannot resolve ({t}) while naming a protected PC folder (CLAUDE.md, J18). Spell the '
                        f'target out. Game files change only through core/proxy/tools/pc_deploy.py, the watcher only through core/harness/job.sh; '
                        f'experiments go under `core/harness/job.sh scratch <owner>` (<state>\\_scratch\\<owner>\\).')
            continue
        if roots.protected_write(p):
            return (f'This call writes {p}, a game preference or save file (the Edit rows protect it too). Use saves/napoleon/stage_save.py for '
                    f'saves and core/proxy/tools/pc_deploy.py set for preferences.')
        if roots.hit(p) and not roots.scratch_ok(p):
            return (f'This call writes into {p}, a protected PC folder (a game folder or the state folder; CLAUDE.md, J18). Game files change '
                    f'only through core/proxy/tools/pc_deploy.py, the watcher only through core/harness/job.sh; experiments go under '
                    f'`core/harness/job.sh scratch <owner>` (<state>\\_scratch\\<owner>\\).')
    return None


def inline_reason(u, roots, tainted):
    codes = []
    if u.code:
        codes.append(u.code)
    name = u.name
    if name in INLINE:
        a = u.args
        for i, x in enumerate(a[:-1]):
            if x in INLINE[name]:
                codes.append(a[i + 1])
        if '-' in a and u.hd:
            codes.append(u.hd)
    if name in ('python', 'python3', 'py', 'node', 'perl', 'ruby', 'powershell', 'pwsh') and u.hd:
        codes.append(u.hd)
    codes += [t for op, t in u.redirs if op == '<<<' and name in INLINE]
    for code in codes:
        if WRITE_VERB.search(code) and (roots.names(code) or (tainted and '$' in code)):
            return (f'Inline {name} code names a protected PC folder and writes, deletes or runs a program: the hook cannot tell what it touches. '
                    f'Game files change only through core/proxy/tools/pc_deploy.py, the watcher only through core/harness/job.sh; experiments go '
                    f'under `core/harness/job.sh scratch <owner>`.')
    return None


# ---- launch and kill ------------------------------------------------------------------------------------------------------------------------

def _names_image(word):
    w = word.lower().replace('\\', '/')
    for stem in game_images():
        if re.search(r'(?<![\w-])' + re.escape(stem) + r'(?:\.exe)?(?![\w-])', w):
            return True
    return False


def launch_reason(u, units, k, exempt):
    msg = ('Launch and kill the game only through the watcher: core/harness/job.sh (CLAUDE.md "Where agents run"); it holds the game lock, the '
           'hang watchdog and the profile restore.')
    if not u.words:
        return None
    name = u.name
    if name in game_images() or u.words[0].lower().startswith('steam://'):
        return msg + f' This call starts {u.words[0]}.'
    if name in LAUNCHERS or name in KILLERS or u.wrappers and u.wrappers[-1] == 'start-process':
        if name in LAUNCHERS and any(a.lower().startswith('steam://') or (_names_image(a) and name != 'steam') for a in u.args):
            return msg
        if name == 'steam' and any(a.lower() == '-applaunch' for a in u.args):
            return msg
        if name in KILLERS and any(_names_image(a) for a in u.args):
            return msg
        if name in ('stop-process', 'spps') and not positionals(u.args) and u.sep == '|' and k > 0:
            prev = units[k - 1]
            if prev.name in ('get-process', 'gps', 'ps', 'tasklist') and any(_names_image(a) for a in prev.args):
                return msg
    return None


# ---- merge rights (D50) ---------------------------------------------------------------------------------------------------------------------

def pr_head(target, repo, cwd):
    """The head branch of a pull request (a number or URL), or of the current branch when target is None; None when it cannot be read."""
    import os
    import subprocess
    try:
        wd = cwd if cwd and os.path.isdir(cwd) else None
        if target is None:
            r = subprocess.run(['git', 'branch', '--show-current'], cwd=wd, capture_output=True, text=True, timeout=5)
        else:
            r = subprocess.run(['gh', 'pr', 'view', target, '--json', 'headRefName', '-q', '.headRefName'] + (['-R', repo] if repo else []),
                               cwd=wd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except Exception:
        return None


PR_HEAD = pr_head


def gh_args(args):
    """(positionals, repo) of a gh call, skipping the options that take a value."""
    pos, repo, i = [], None, 0
    while i < len(args):
        a = args[i]
        if a in GH_VAL:
            if a in ('-R', '--repo') and i + 1 < len(args):
                repo = args[i + 1]
            i += 2
        elif a.startswith('--repo='):
            repo = a.split('=', 1)[1]
            i += 1
        elif a.startswith('-'):
            i += 1
        else:
            pos.append(a)
            i += 1
    return pos, repo


def merge_msg(what):
    return (f'{what} D50: only Liam merges plan/ and meta/ branches, for now (CLAUDE.md "While you work"). Say the pull request is ready and stop; '
            f'job/ and brief/ branches merge with `gh pr merge <branch> --auto --squash` once their rules are met.')


def merge_reason(u):
    if u.name != 'gh':
        return None
    pos, repo = gh_args(u.args)
    if pos[:1] == ['api']:
        blob = ' '.join(u.args)
        if re.search(r'/pulls/\d+/merge|mergePullRequest|enablePullRequestAutoMerge', blob):
            return merge_msg('This gh api call merges a pull request.')
        m = re.search(r'git/refs/heads/(\S+)', blob)
        if m and re.search(r'(?:-X|--method)[ =]*delete', blob, re.I):
            n = m.group(1).strip('\'"')
            if re.match(r'^(main|plan/|meta/|job/|brief/)', n):
                return branch_msg(n)
        return None
    if pos[:2] != ['pr', 'merge']:
        return None
    t = pos[2] if len(pos) > 2 else None
    branch = None
    if t is not None and not re.fullmatch(r'\d+', t) and not t.startswith(('http://', 'https://')):
        branch = t
        for _ in range(3):
            branch = re.sub(r'^(?:origin/|refs/heads/|refs/remotes/origin/)', '', branch)
        branch = re.sub(r'^[\w.-]+:(?!//)', '', branch)
        branch = re.sub(r'^(?:origin/|refs/heads/)', '', branch)
    else:
        branch = PR_HEAD(t, repo, u.cwd)
        if not branch:
            return merge_msg('The hook cannot tell which branch this `gh pr merge` merges.') + ' Re-run it naming the branch (gh pr merge job/<id> --auto --squash).'
    if re.match(r'^(?:plan|meta)/', branch):
        return merge_msg(f'This call merges {branch}.')
    return None


# ---- decide -------------------------------------------------------------------------------------------------------------------------------

def exempt_script(u, roots):
    """True when the unit runs this checkout's core pc_deploy.py or job.sh (relative to its cwd or absolute)."""
    words = u.words
    if not words:
        return False
    name = cname(words[0])
    script = words[0]
    if name in ('python', 'python3', 'py', 'bash', 'sh', 'zsh'):
        rest = [a for a in words[1:] if not a.startswith('-')]
        script = rest[0] if rest else ''
    if Path(str(script).replace('\\', '/')).name not in SANCTIONED:
        return False
    p = rp(script, u.cwd, _short)
    if not isinstance(p, str) or not p.endswith(SCRIPT_SUFFIXES):
        return False
    base = norm(ROOT)
    parent = norm(ROOT.parent)
    return under(p, base) or (under(p, parent) and p[len(parent) + 1:].count('/') >= 2)


def look_alike(u, roots):
    if not u.words:
        return False
    cand = [u.words[0]] + [a for a in u.words[1:] if not a.startswith('-')][:1]
    return any(Path(c).name in SANCTIONED for c in cand if c)


def evaluate(cmd, cwd, roots, sid, ps=False, environ=None):
    parse = hp.Parse(cwd, {}, ps, _short, environ)
    parse.run(cmd)
    units = parse.units
    tainted = roots.names(cmd) or any(roots.names(u.text()) for u in units)
    if parse.unparseable and tainted:
        return ('This command is nested too deeply for the hook to read and names a protected PC folder. Split it into simple commands '
                '(CLAUDE.md, J18).')
    for k, u in enumerate(units):
        exempt = exempt_script(u, roots)
        if u.name == 'git':
            why = git_reason(u, roots, tainted, sid)
            if why:
                return why
        why = None if exempt else launch_reason(u, units, k, exempt)
        why = why or merge_reason(u)
        why = why or write_reason(u, roots, tainted)
        if why:
            return why
        if not exempt:
            why = inline_reason(u, roots, tainted)
            if why:
                return why
            if tainted and look_alike(u, roots) and u.name not in ('git', 'ls', 'cat', 'echo', 'sha1sum', 'grep'):
                return (f'{u.words[0]} looks like a sanctioned script but is not this checkout\'s core/proxy/tools/pc_deploy.py or core/harness/job.sh, '
                        f'and the command names a protected PC folder. Run the sanctioned script by its repo path.')
    return None


def decide(event, roots=None):
    """None to let the call through, else the reason it is denied. roots: a Roots, or (game folders, state folder[, write-protected paths]) normalised;
    tests pass fixtures."""
    if event.get('tool_name') not in ('Bash', 'PowerShell'):
        return None
    cmd = str((event.get('tool_input') or {}).get('command', ''))
    sid = str(event.get('session_id') or '').strip()
    note = ''
    if roots is None:
        try:
            roots = Roots(*protected_roots(), extra=appdata_paths())
        except (OSError, ValueError, KeyError):
            roots, note = FALLBACK, FALLBACK_NOTE
    elif not isinstance(roots, Roots):
        roots = Roots(roots[0], roots[1], roots[2] if len(roots) > 2 else ())
    note = FALLBACK_NOTE if roots.fallback else note
    cwd = norm(event['cwd']) if event.get('cwd') else None
    import os
    why = evaluate(cmd, cwd, roots, sid, event.get('tool_name') == 'PowerShell', {k.upper(): v for k, v in os.environ.items()})
    return why + note if why else None


def panic(cmd, sid=''):
    """The independent screen decide() falls back to when it raises: denies only a trailer-less git commit and a protected-folder word with a
    write, git, launch or kill word."""
    if PANIC_COMMIT.search(cmd) and 'Claude-Session' not in cmd:
        return 'The hook failed and fell back to its text screen: this git commit has no --trailer "Claude-Session: <id>". Add it and run again.'
    if FB_TEXT.search(cmd.replace('\\', '/')) and PANIC_VERB.search(cmd):
        return ('The hook failed and fell back to its text screen: this call names a protected PC folder together with a write, git, launch or '
                'kill word. Use core/proxy/tools/pc_deploy.py or core/harness/job.sh, or repair tools/claude_hook.py.')
    return None


def main():
    # Never exit non-zero: exit 2 from a PreToolUse hook blocks the tool call, so a hook bug would block every shell call (J20 review).
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        why = decide(event)
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            why = panic(str((event.get('tool_input') or {}).get('command', ''))) if event.get('tool_name') in ('Bash', 'PowerShell') else None
        except Exception:
            why = None
    if why:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': why}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
