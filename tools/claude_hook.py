#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the shell-call rules of this repo: the commit trailer (D21, J20), no git in a game folder and no writes
into the PC's protected folders outside `_scratch\\<owner>\\` (J18).

purpose: refuse three kinds of Bash or PowerShell call before they run: a `git commit` without `--trailer "Claude-Session: <this session id>"` (tools/pr_policy.py tells a job's builder from its reviewer by it), any `git` working in a protected root (both game folders, the PC state folder), and a write into a protected root outside `<state>\\_scratch\\<owner>\\` (redirects, cp/mv/rm/..., Copy-Item/Set-Content/...; pc_deploy.py and job.sh calls are exempt); each denial says what to run instead
usage: wired in .claude/settings.json (PreToolUse, matcher Bash|PowerShell); reads the hook JSON on stdin; test: echo '{"session_id":"s","cwd":"/c/x","tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | python3 tools/claude_hook.py
when: automatic on every shell call in a Claude Code session in this repo; never run by hand except to test it
not-a-verb: Claude Code runs it with a JSON protocol on stdin and stdout, not through the wsc CLI
"""
import json
import posixpath
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = re.compile(r'''(?<![\w./-])git(?:\.exe)?(?:\s+-[cC]\s+(?:"[^"]*"|'[^']*'|\S+))*\s+commit(?![\w-])''')
GIT = re.compile(r'''(?<![\w./$-])git(?:\.exe)?(?![\w.-])''')
SEP = re.compile(r'&&|\|\||[;\n|]|(?<!>)&(?!>)')   # 2>&1 and &> stay inside their command
SCRATCH_OWNER = re.compile(r'^[a-z0-9][a-z0-9_-]{0,31}$')
EXEMPT = re.compile(r'(?<![\w-])(pc_deploy\.py|job\.sh)(?![\w-])')
# Bash escapes a space or a parenthesis with a backslash (`Napoleon\ Total\ War`, tab completion's spelling); any other backslash is a
# Windows separator
ESCAPED = re.compile(r'\\(?=[ ()])')
REDIRECT = re.compile(r'''(?<![<>&\d])\d?>>?\|?\s*("[^"]*"|'[^']*'|(?:\\[ ()]|[^\s;&|<>])+)''')
GIT_ENV = re.compile(r'''\bGIT_(?:DIR|WORK_TREE)\s*=\s*("[^"]*"|'[^']*'|(?:\\[ ()]|[^\s;&|])+)''', re.I)
GIT_OPT = re.compile(r'''--(?:git-dir|work-tree)(?:=|\s+)("[^"]*"|'[^']*'|(?:\\[ ()]|[^\s;&|])+)''')
WRAPPERS = {'sudo', 'xargs', 'command', 'exec', 'env', 'time', 'nohup'}
CD = {'cd', 'pushd', 'set-location', 'push-location', 'sl'}
# the write commands; the value says which arguments are written: all (every path argument), last (the destination), sed (only with -i),
# unzip (the -d folder), dest (PowerShell -Destination/-DestinationPath, else the second positional)
WRITERS = {'cp': 'last', 'mv': 'all', 'mkdir': 'all', 'touch': 'all', 'rm': 'all', 'rmdir': 'all', 'tee': 'all', 'sed': 'sed',
           'unzip': 'unzip', 'copy-item': 'dest', 'move-item': 'all', 'new-item': 'all', 'set-content': 'all', 'add-content': 'all',
           'out-file': 'all', 'remove-item': 'all', 'expand-archive': 'dest', 'cpi': 'dest', 'mi': 'all', 'ni': 'all', 'ri': 'all', 'del': 'all'}


def norm(p):
    """One spelling for a Windows path: C:\\x, C:/x and /c/x all become c:/x (lower case, no trailing slash)."""
    s = str(p).strip().strip('"\'').replace('\\', '/')
    m = re.match(r'^/([a-zA-Z])(/.*)?$', s)
    if m:
        s = f'{m.group(1)}:{m.group(2) or "/"}'
    s = s.lower()
    if re.match(r'^[a-z]:', s):
        s = posixpath.normpath(s[:2] + '/' + s[2:].lstrip('/'))
    return s.rstrip('/') if len(s) > 3 else s


def is_abs(s):
    return bool(re.match(r'^[a-z]:/', s)) or s.startswith(('/', '~'))


def resolve(arg, cwd):
    """The normalised absolute path of a shell argument, or None when it cannot be known ($VAR, ~, a flag, empty)."""
    if not arg or '$' in arg or '%' in arg or arg.startswith(('-', '~')) or arg in ('/dev/null', 'nul', 'NUL'):
        return None
    a = norm(ESCAPED.sub('', arg))
    if is_abs(a):
        return a
    return norm(posixpath.join(cwd, a)) if cwd else None


def protected_roots(root=ROOT):
    """(game folders, state folder) read from their owners: harness/napoleon/adapter.json and discovery/napoleon/games.json."""
    ad = json.loads((root / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
    games = json.loads((root / 'discovery' / 'napoleon' / 'games.json').read_text(encoding='utf-8'))
    gdirs = {norm(ad['game_dir']), norm(games['napoleon']['root']), norm(games['empire']['root'])}
    return sorted(gdirs), norm(ad['state_dir'])


def under(p, r):
    return p == r or p.startswith(r + '/')


def in_roots(p, roots):
    return p is not None and any(under(p, r) for r in roots[0] + [roots[1]])


def scratch_ok(p, roots):
    """True when p lies in <state>/_scratch/<owner>/ (the owner folder itself included)."""
    rest = p[len(roots[1]) + 1:].split('/') if under(p, roots[1]) and p != roots[1] else []
    return len(rest) >= 2 and rest[0] == '_scratch' and bool(SCRATCH_OWNER.match(rest[1]))


def split_words(seg):
    seg = re.sub(r'\\(?![ ()])', '/', seg)   # Windows separators to slashes; Bash's escaped spaces stay for shlex
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return ESCAPED.sub('', seg).split()


def segments(cmd, cwd):
    """(segment text, words, cwd while it runs) for each simple command; `cd <dir>` moves the cwd for the segments after it."""
    out = []
    for seg in SEP.split(cmd):
        words = split_words(REDIRECT.sub(' ', seg))
        while words and re.match(r'^[A-Za-z_]\w*=', words[0]):   # VAR=x cmd
            words = words[1:]
        if words and words[0].lower() in CD:
            args = [w for w in words[1:] if not w.startswith('-')]
            nxt = resolve(args[0], cwd) if args else None
            cwd = nxt if nxt else (None if args else cwd)   # cd $X: the cwd is unknown from here on
        out.append((seg, words, cwd))
    return out


def written_paths(words, cwd):
    """The paths a write command writes (its arguments, by the WRITERS rule), resolved; [] when it is not a write command."""
    if not words:
        return []
    name = posixpath.basename(words[0].lower()).removesuffix('.exe')
    rule = WRITERS.get(name)
    if rule is None:
        return []
    args = words[1:]
    if rule == 'sed':
        if not any(a == '-i' or a.startswith(('-i', '--in-place')) for a in args):
            return []
        rule = 'all'
    if rule == 'unzip':
        return [resolve(args[i + 1], cwd) for i, a in enumerate(args[:-1]) if a == '-d']
    if rule == 'dest':
        for i, a in enumerate(args[:-1]):
            if a.lower() in ('-destination', '-destinationpath'):
                return [resolve(args[i + 1], cwd)]
        pos = [a for a in args if not a.startswith('-')]
        return [resolve(pos[1], cwd)] if len(pos) > 1 else []
    pos = [a for a in args if not a.startswith('-') or a.lower() in ('-path', '-literalpath', '-filepath')]
    pos = [a for a in pos if not a.startswith('-')]
    if rule == 'last':
        tgt = [args[i + 1] for i, a in enumerate(args[:-1]) if a in ('-t', '--target-directory')]
        return [resolve(t, cwd) for t in (tgt or pos[-1:])]
    return [resolve(a, cwd) for a in pos]


def git_reason(cmd, cwd, roots):
    if not GIT.search(cmd):
        return None
    for rx in (GIT_ENV, GIT_OPT):
        for m in rx.finditer(cmd):
            p = resolve(m.group(1), cwd)
            if in_roots(p, roots):
                return p
    for seg, words, wcwd in segments(cmd, cwd):
        names = [posixpath.basename(w.lower()).removesuffix('.exe') for w in words[:2]]
        i = 0 if names[:1] == ['git'] else 1 if names[:1] and names[0] in WRAPPERS and names[1:] == ['git'] else None
        if i is None:
            continue
        rest = words[i + 1:]
        for j, a in enumerate(rest[:-1]):
            if a == '-C':
                p = resolve(rest[j + 1], wcwd)
                if in_roots(p, roots):
                    return p
        if not any(a == '-C' for a in rest) and in_roots(wcwd, roots):
            return wcwd
    return None


def write_reason(cmd, cwd, roots):
    if EXEMPT.search(cmd):
        return None
    for seg, words, wcwd in segments(cmd, cwd):
        paths = [resolve(m.group(1), wcwd) for m in REDIRECT.finditer(seg) if not m.group(1).startswith('&')]
        paths += written_paths(words, wcwd)
        for p in paths:
            if in_roots(p, roots) and not scratch_ok(p, roots):
                return p
    return None


def decide(event, roots=None):
    """None to let the call through, else the reason it is denied. roots: (game folders, state folder), normalised; tests pass fixtures."""
    if event.get('tool_name') not in ('Bash', 'PowerShell'):
        return None
    cmd = str((event.get('tool_input') or {}).get('command', ''))
    sid = str(event.get('session_id') or '').strip()
    # only the --trailer flag counts: a `Claude-Session:` line in a -m body is a trailer only in the message's last paragraph, and J44's 19
    # commits put it one paragraph above `Co-Authored-By:`, so git (and tools/pr_policy.py) read no session at all
    if COMMIT.search(cmd) and sid and not re.search(r'--trailer[\s=]+["\']?Claude-Session:\s*' + re.escape(sid) + r'(?![\w-])', cmd):
        return (f'Every commit in this repo names its Claude Code session (tools/pr_policy.py refuses a job whose report or review was '
                f'committed without one). Run the same command again with this flag after `git commit`: '
                f'--trailer "Claude-Session: {sid}"')
    if roots is None:
        try:
            roots = protected_roots()
        except (OSError, ValueError, KeyError):
            return None
    cwd = norm(event['cwd']) if event.get('cwd') else None
    p = git_reason(cmd, cwd, roots)
    if p:
        return (f'Never run git in a game folder or the PC state folder (CLAUDE.md, J18): this call would run git in {p}. Work in the repo '
                f'checkout and sync files to the PC with core/proxy/tools/pc_deploy.py (sha-checked copies).')
    p = write_reason(cmd, cwd, roots)
    if p:
        return (f'This call writes into {p}, a protected PC folder (a game folder or the state folder; CLAUDE.md, J18). Game files change '
                f'only through core/proxy/tools/pc_deploy.py, the watcher only through core/harness/job.sh; experiments go under '
                f'`core/harness/job.sh scratch <owner>` (<state>\\_scratch\\<owner>\\).')
    return None


def main():
    # Never exit non-zero: exit 2 from a PreToolUse hook blocks the tool call, so a hook bug would block every shell call (J20 review).
    # A commit this hook fails to catch is still refused by tools/pr_policy.py in CI.
    try:
        event = json.load(sys.stdin)
        why = decide(event) if isinstance(event, dict) else None
    except Exception:
        return 0   # not ours to judge: let the normal permission flow decide
    if why:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': why}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
