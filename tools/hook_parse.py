#!/usr/bin/env python3
"""The shell parser behind tools/claude_hook.py (J76): turns one Bash or PowerShell command line into the list of simple commands that would run.

purpose: split a shell command into units (argv, redirections, tracked cwd and variables, heredoc body) through separators, if/for/{} blocks, subshells, $( ), backticks, bash -c, eval, cmd /c, powershell -Command, Start-Process and the nice/timeout/env/sudo/xargs family of wrappers, so the hook rules look at the right slice of a command (audit H1, H6)
usage: imported by tools/claude_hook.py by path; Parse(cwd, env, ps, short).run(command) then .units; test: python3 -m unittest tests.test_claude_hook_corpus
when: never run by hand; read it when a hook rule misjudges a command shape
not-a-verb: a library module loaded by the hook, not a command line tool

State (the cwd and the variables) flows left to right through the whole command with no subshell scoping: the conservative choice, because a
false "unknown" costs less than a hole. Recursion stops at depth 4; deeper text sets `unparseable`. Stdlib only, no subprocess.
"""
import base64
import posixpath
import re

DOLLAR = '\x01'   # a $ that was quoted in single quotes: never expanded
SUB = '\x00'      # stands for the output of a $( ) or backtick substitution: a value nobody can know
MAXD = 4
UNKNOWN = object()   # a path that cannot be known

ESCAPED = re.compile(r'\\(?=[ ()])')
VAR = re.compile(r'\$\{(\w+)\}|\$env:(\w+)|\$(\w+)|%(\w+)%')
ASSIGN = re.compile(r'^[A-Za-z_]\w*=')
HD = re.compile(r'''<<-?\s*(?:'([^']*)'|"([^"]*)"|(\w+))''')
SHORT83 = re.compile(r'^[^/~]{1,6}~\d+(?:\.\w*)?$')
RESERVED = {'if', 'then', 'else', 'elif', 'fi', 'do', 'done', 'while', 'until', '!', '{', '}', 'time', 'esac'}
SKIPPED = {'for', 'case', 'select', 'function', 'foreach'}
CD = {'cd', 'pushd', 'set-location', 'push-location', 'sl', 'chdir'}
WRAPPERS = {'sudo', 'xargs', 'command', 'exec', 'env', 'time', 'nohup', 'nice', 'timeout', 'stdbuf', 'setsid', 'ionice', 'start', 'call',
            'builtin', 'doas'}
SHELLS = {'bash', 'sh', 'zsh', 'dash', 'ksh'}
NULLS = {'/dev/null', 'nul', '/dev/stdout', '/dev/stderr', '/dev/tty', '$null'}


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


def rp(arg, cwd, short=None):
    """The normalised absolute path of a shell argument; None when it is no path (empty, a flag, /dev/null); UNKNOWN when it cannot be known
    ($VAR, ~, a substitution, an unexpandable 8.3 name, a relative path with no known cwd)."""
    if not arg or arg in NULLS or arg.startswith('-'):
        return None
    if SUB in arg or '$' in arg or '%' in arg or arg.startswith('~'):
        return UNKNOWN
    a = norm(ESCAPED.sub('', arg))
    if '~' in a:
        if short:
            a = norm(short(a))
        if any(SHORT83.match(c) for c in a.split('/')):
            return UNKNOWN
    if is_abs(a):
        return a
    if not cwd:
        return UNKNOWN
    return norm(posixpath.join(cwd, a))


def cname(w):
    return posixpath.basename(str(w).replace('\\', '/').lower()).removesuffix('.exe')


# ---- lexer -------------------------------------------------------------------------------------------------------------------------------

def _skip_dq(s, i):
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\':
            i += 2
            continue
        if c == '"':
            return i + 1
        if c == '$' and s.startswith('$(', i):
            j = find_close(s, i + 2)
            i = n if j < 0 else j + 1
            continue
        i += 1
    return n


def find_close(s, i):
    """Index of the ')' that closes a '(' opened just before i (quotes, nesting and heredoc bodies skipped); -1 when there is none."""
    depth, n, docs = 1, len(s), []
    while i < n:
        c = s[i]
        if c == '\\':
            i += 2
            continue
        if c == "'":
            j = s.find("'", i + 1)
            i = n if j < 0 else j + 1
            continue
        if c == '"':
            i = _skip_dq(s, i + 1)
            continue
        if c == '`':
            j = s.find('`', i + 1)
            i = n if j < 0 else j + 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        elif c == '<' and s.startswith('<<', i) and not s.startswith('<<<', i):
            m = HD.match(s, i)
            if m:
                docs.append(m.group(1) or m.group(2) or m.group(3))
                i = m.end()
                continue
        elif c == '\n' and docs:
            i += 1
            for d in docs:
                while i < n:
                    j = s.find('\n', i)
                    line = s[i:n if j < 0 else j]
                    i = n if j < 0 else j + 1
                    if line.strip() == d:
                        break
            docs = []
            continue
        i += 1
    return -1


def lex(s, ps=False):
    """Tokens: ('w', text, [substitution sources]), ('op', ';'|'&&'|'||'|'|'|'&'|'\\n'|'('|')'), ('redir', op, fd), ('hd', body)."""
    toks, i, n = [], 0, len(s)
    buf, has, subs = [], False, []
    pend, want = [], None

    def flush():
        nonlocal buf, has, subs, want
        if has:
            text = ''.join(buf)
            if want is not None:
                pend.append((text, want))
                want = None
            toks.append(('w', text, subs))
        buf, has, subs = [], False, []

    def sub(start):   # start: index just after the opening paren
        nonlocal i, has
        j = find_close(s, start)
        subs.append(s[start:n if j < 0 else j])
        buf.append(SUB)
        has = True
        i = n if j < 0 else j + 1

    while i < n:
        c = s[i]
        if c in ' \t\r':
            flush()
            i += 1
        elif c == '\n':
            flush()
            i += 1
            docs = []
            for delim, mode in pend:
                body = []
                while i < n:
                    j = s.find('\n', i)
                    line = s[i:n if j < 0 else j]
                    i = n if j < 0 else j + 1
                    if (line.lstrip('\t') if mode == 'strip' else line.rstrip('\r')) == delim:
                        break
                    body.append(line)
                docs.append(('hd', '\n'.join(body)))
            pend.clear()
            toks.extend(docs)
            toks.append(('op', '\n'))
        elif c == '#' and not has:
            while i < n and s[i] != '\n':
                i += 1
        elif c == "'":
            j = s.find("'", i + 1)
            j = n if j < 0 else j
            buf.append(s[i + 1:j].replace('$', DOLLAR))
            has = True
            i = j + 1
        elif c == '"':
            i += 1
            has = True
            while i < n and s[i] != '"':
                d = s[i]
                if ps and d == '`' and i + 1 < n:
                    buf.append(s[i + 1].replace('$', DOLLAR))
                    i += 2
                elif not ps and d == '\\' and i + 1 < n and s[i + 1] in '"$`\\':
                    buf.append('\\\\' if s[i + 1] == '\\' else s[i + 1].replace('$', DOLLAR))
                    i += 2
                elif d == '$' and s.startswith('$(', i):
                    sub(i + 2)
                elif d == '`' and not ps:
                    j = s.find('`', i + 1)
                    j = n if j < 0 else j
                    subs.append(s[i + 1:j])
                    buf.append(SUB)
                    i = j + 1
                else:
                    buf.append(d)
                    i += 1
            i += 1
        elif c == '`':
            if ps:
                if i + 1 < n:
                    buf.append(s[i + 1])
                    has = True
                i += 2
            else:
                j = s.find('`', i + 1)
                j = n if j < 0 else j
                subs.append(s[i + 1:j])
                buf.append(SUB)
                has = True
                i = j + 1
        elif c == '$' and s.startswith('$(', i):
            sub(i + 2)
        elif c == '\\' and not ps:
            nx = s[i + 1] if i + 1 < n else ''
            if nx == '\n':
                i += 2
            elif nx and nx in ' ()"\'`;&|<>':
                buf.append(nx)
                has = True
                i += 2
            elif nx == '$':
                buf.append(DOLLAR)
                has = True
                i += 2
            else:
                buf.append('\\')
                has = True
                i += 1
        elif c in '<>' and s.startswith('(', i + 1):
            sub(i + 2)
        elif c in '<>' or (c == '&' and s.startswith('&>', i)) or (c == '*' and not has and s.startswith('*>', i)):
            fd = ''
            if has and buf and ''.join(buf).isdigit():
                fd = ''.join(buf)
                buf, has = [], False
            else:
                flush()
            if c == '&':
                op = '&>>' if s.startswith('&>>', i) else '&>'
            elif c == '*':
                op = '*>>' if s.startswith('*>>', i) else '*>'
            elif c == '>':
                op = next(o for o in ('>>', '>|', '>&', '>') if s.startswith(o, i))
            else:
                op = next(o for o in ('<<<', '<<-', '<<', '<>', '<&', '<') if s.startswith(o, i))
            i += len(op)
            if op in ('<<', '<<-'):
                want = 'strip' if op == '<<-' else 'plain'
            toks.append(('redir', op, fd))
        elif c in ';|&()':
            flush()
            op = next((o for o in ('&&', '||', '|&', ';;') if s.startswith(o, i)), c)
            toks.append(('op', '|' if op == '|&' else ';' if op == ';;' else op))
            i += len(op)
        else:
            buf.append(c)
            has = True
            i += 1
    flush()
    return toks


# ---- units -------------------------------------------------------------------------------------------------------------------------------

class Unit:
    __slots__ = ('words', 'redirs', 'cwd', 'env', 'hd', 'sep', 'wrappers', 'code', 'depth')

    def __init__(self, words, redirs, cwd, env, hd, sep, wrappers, code, depth):
        self.words, self.redirs, self.cwd, self.env, self.hd = words, redirs, cwd, env, hd
        self.sep, self.wrappers, self.code, self.depth = sep, wrappers, code, depth

    @property
    def name(self):
        return cname(self.words[0]) if self.words else ''

    @property
    def args(self):
        return self.words[1:]

    def text(self):
        return ' '.join(self.words + [t for _, t in self.redirs] + [v for v in self.env.values()])


def _opt_skip(args, with_arg):
    """Drop leading options; with_arg: the ones that take a separate value."""
    i = 0
    while i < len(args) and args[i].startswith('-') and args[i] != '-':
        if args[i] == '--':
            i += 1
            break
        i += 2 if args[i] in with_arg else 1
    return args[i:]


class Parse:
    def __init__(self, cwd=None, env=None, ps=False, short=None, environ=None):
        self.cwd = cwd
        self.env = {k.upper(): v for k, v in (env or {}).items()}
        self.ps = ps
        self.short = short
        self.environ = environ if environ is not None else {}
        self.units = []
        self.unparseable = False

    # -- expansion
    def expand(self, w):
        if '$' not in w and '%' not in w:
            return w

        def rep(m):
            name = (m.group(1) or m.group(2) or m.group(3) or m.group(4)).upper()
            v = self.env.get(name)
            if v is None:
                v = self.environ.get(name)
            return m.group(0) if v is None else v
        return VAR.sub(rep, w)

    # -- driver
    def run(self, s, depth=0, sep=''):
        if depth > MAXD:
            self.unparseable = True
            return
        words, redirs, hd, subs, pend = [], [], None, [], None
        for t in lex(s, self.ps) + [('op', '\n')]:
            k = t[0]
            if k == 'w':
                subs.extend(t[2])
                if pend:
                    redirs.append((pend[0], t[1]))
                    pend = None
                else:
                    words.append(t[1])
            elif k == 'redir':
                pend = (t[1], t[2])
            elif k == 'hd':
                hd = t[1]
            else:
                for src in subs:
                    self.run(src, depth + 1)
                if words or redirs:
                    self.command(words, redirs, hd, sep, depth)
                words, redirs, hd, subs, pend = [], [], None, [], None
                sep = t[1]

    def command(self, words, redirs, hd, sep, depth):
        while words and words[0] in RESERVED:
            words = words[1:]
        while words and words[-1] == '}':
            words = words[:-1]
        if words and words[0] in SKIPPED:
            return
        prefix = {}
        while words and ASSIGN.match(words[0]):
            k, v = words[0].split('=', 1)
            prefix[k.upper()] = self.expand(v)
            words = words[1:]
        low = words[0].lower() if words else ''
        if words and len(words) >= 2 and words[0].startswith('$') and words[1] == '=':   # PowerShell $V = 'x' and $env:V = 'x'
            name = words[0][1:]
            name = name[4:] if name.lower().startswith('env:') else name
            self.env[name.upper()] = self.expand(' '.join(words[2:]))
            words = []
        elif low in ('export', 'declare', 'local', 'typeset', 'readonly', 'set', 'setx') and any(ASSIGN.match(w) for w in words[1:]):
            for w in words[1:]:
                if ASSIGN.match(w):
                    k, v = w.split('=', 1)
                    self.env[k.upper()] = self.expand(v)
            words = []
        if not words:
            if prefix:
                self.env.update(prefix)
            if redirs:
                self.record([], [(o, self.expand(t)) for o, t in redirs], {}, hd, sep, [], None, depth)
            return
        words = [self.expand(w) for w in words]
        redirs = [(o, self.expand(t)) for o, t in redirs]
        self.dispatch(words, redirs, prefix, hd, sep, depth)

    def record(self, words, redirs, prefix, hd, sep, wrappers, code, depth, cwd=None):
        env = dict(self.env)
        env.update(prefix)
        fix = (lambda w: w.replace(DOLLAR, '$'))
        self.units.append(Unit([fix(w) for w in words], [(o, fix(t)) for o, t in redirs], self.cwd if cwd is None else cwd, env,
                               hd, sep, wrappers, code, depth))

    def dispatch(self, words, redirs, prefix, hd, sep, depth):
        wrappers, cwd = [], None
        while words:
            name = cname(words[0])
            if name in CD:
                args = [w for w in words[1:] if not w.startswith('-')]
                self.record(words, redirs, prefix, hd, sep, wrappers, None, depth)
                if args:
                    p = rp(args[0], self.cwd, self.short)
                    self.cwd = None if p is None or p is UNKNOWN else p
                return
            if name in WRAPPERS:
                words = self.unwrap(name, words, prefix)
                wrappers.append(name)
                continue
            if name == 'start-process':
                words, cwd = self.start_process(words, cwd)
                wrappers.append(name)
                continue
            if name == 'cmd':
                rest = self.after_flag(words, ('/c', '/k', '/r'))
                if rest is None:
                    break
                wrappers.append(name)
                if len(rest) == 1 and ' ' in rest[0]:
                    self.record(words, redirs, prefix, hd, sep, wrappers, rest[0].replace(DOLLAR, '$'), depth)
                    self.run(rest[0].replace(DOLLAR, '$'), depth + 1)
                    return
                words = rest
                continue
            if name in ('powershell', 'pwsh'):
                rest = self.after_flag(words, ('-c', '-command', '-encodedcommand', '-ec', '-e'))
                if rest is None:
                    break
                flag = next(w.lower() for w in words[1:] if w.lower() in ('-c', '-command', '-encodedcommand', '-ec', '-e'))
                text = ' '.join(rest)
                if flag in ('-encodedcommand', '-ec', '-e'):
                    try:
                        text = base64.b64decode(rest[0] + '=' * (-len(rest[0]) % 4)).decode('utf-16-le')
                    except Exception:
                        text = ' '.join(rest)
                text = text.replace(DOLLAR, '$')
                self.record(words, redirs, prefix, hd, sep, wrappers, text, depth)
                saved = self.ps
                self.ps = True
                self.run(text, depth + 1)
                self.ps = saved
                return
            if name in SHELLS:
                a = words[1:]
                k = next((i for i, w in enumerate(a) if re.match(r'^-[a-z]*c[a-z]*$', w)), None)
                if k is not None and k + 1 < len(a):
                    text = a[k + 1].replace(DOLLAR, '$')
                    self.record(words, redirs, prefix, hd, sep, wrappers, text, depth)
                    self.run(text, depth + 1)
                    return
                self.record(words, redirs, prefix, hd, sep, wrappers, None, depth)
                if hd and not [w for w in a if not w.startswith('-')]:
                    self.run(hd, depth + 1)
                return
            if name == 'eval':
                text = ' '.join(words[1:]).replace(DOLLAR, '$')
                self.record(words, redirs, prefix, hd, sep, wrappers, text, depth)
                self.run(text, depth + 1)
                return
            break
        self.record(words, redirs, prefix, hd, sep, wrappers, None, depth, cwd)

    # -- wrappers
    @staticmethod
    def after_flag(words, flags):
        for i, w in enumerate(words[1:], 1):
            if w.lower() in flags:
                return words[i + 1:]
        return None

    def unwrap(self, name, words, prefix):
        a = words[1:]
        if name in ('sudo', 'doas'):
            return _opt_skip(a, {'-u', '-g', '-C', '-h', '-p', '-r', '-t', '-U', '-D'})
        if name == 'nice':
            return _opt_skip(a, {'-n', '--adjustment'})
        if name == 'timeout':
            a = _opt_skip(a, {'-s', '-k', '--signal', '--kill-after'})
            return a[1:]
        if name == 'env':
            i = 0
            while i < len(a):
                w = a[i]
                if ASSIGN.match(w):
                    k, v = w.split('=', 1)
                    prefix[k.upper()] = v
                    i += 1
                elif w in ('-u', '-C', '-S', '--unset', '--chdir'):
                    i += 2
                elif w.startswith('-') and w != '-' or w == '-':
                    i += 1
                else:
                    break
            return a[i:]
        if name == 'xargs':
            return _opt_skip(a, {'-n', '-I', '-L', '-P', '-d', '-E', '-s', '-a'})
        if name == 'stdbuf':
            return _opt_skip(a, {'-i', '-o', '-e'})
        if name == 'ionice':
            return _opt_skip(a, {'-c', '-n', '-p', '-P', '-u'})
        if name == 'exec':
            return _opt_skip(a, {'-a'})
        if name == 'start':
            a = [w for w in a if not re.match(r'^/[A-Za-z]+$', w)]
            return a[1:] if a and a[0] == '' else a
        return _opt_skip(a, set())   # command, nohup, time, setsid, call, builtin

    def start_process(self, words, cwd):
        a, file, argl, pos = words[1:], None, [], []
        i = 0
        while i < len(a):
            w = a[i].lower()
            if w in ('-filepath', '-path'):
                file = a[i + 1] if i + 1 < len(a) else None
                i += 2
            elif w == '-argumentlist':
                j = i + 1
                while j < len(a) and not a[j].startswith('-'):
                    argl.append(a[j])
                    j += 1
                i = j
            elif w in ('-workingdirectory', '-verb', '-windowstyle', '-redirectstandardoutput', '-redirectstandarderror',
                       '-redirectstandardinput', '-credential', '-environment'):
                if w == '-workingdirectory' and i + 1 < len(a):
                    p = rp(a[i + 1], self.cwd, self.short)
                    cwd = p if isinstance(p, str) else None
                i += 2
            elif w.startswith('-'):
                i += 1
            else:
                pos.append(a[i])
                i += 1
        if file is None and pos:
            file = pos.pop(0)
        if not argl and pos:
            argl = pos
        out = []
        for part in ','.join(argl).split(','):
            part = part.strip()
            if not part:
                continue
            if ' ' in part and not part.startswith(('"', "'")) and not re.match(r'^[A-Za-z]:[\\/]', part):
                out.extend(w[1] for w in lex(part) if w[0] == 'w')
            else:
                out.append(part)
        return ([file] if file else []) + out, cwd
