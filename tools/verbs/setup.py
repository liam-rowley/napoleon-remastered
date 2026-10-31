"""Check that this clone and the PC are ready for local Claude Code work (D30), with a one-line fix for each failure.

purpose: check Git Bash, python3 >= 3.12, the core submodule at the pinned tag, core.hooksPath, LF shell scripts, gh auth, Docker Desktop, the empire-remastered sibling clone, Python Playwright with Chromium, the PC watcher and the PC rules (exe vanilla, no .git in or above a game folder, nothing foreign in the Napoleon folder: J18); `--fix` applies the safe fixes (a python3.exe copy, core.hooksPath)
usage: python3 core/wsc.py setup [--fix] [--skip <check>...]
when: once per clone or PC, after a reboot or tool update, and whenever a gate or the watcher route fails for an environment reason
verb: setup
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NAME = 'setup'
HELP = 'check this clone and the PC for local Claude Code work (D30); --fix for the safe fixes'
MIN_PY = (3, 12)
CHECKS = ('git_bash', 'python3', 'core_pin', 'hooks_path', 'lf_scripts', 'gh_auth', 'docker', 'empire_clone', 'playwright', 'watcher', 'pc_rules')


# ---- pure helpers (host tests: tests/test_setup.py) ------------------------------------------------------------------------------
def parse_version(text):
    """(major, minor) from `Python 3.12.4` or `3.12.4`, else None."""
    m = re.search(r'(\d+)\.(\d+)', text or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def bash_kind(path, nt=os.name == 'nt'):
    """'git' for Git for Windows' bash, 'wsl' for the System32/WindowsApps launcher (a WSL distro: other paths, other python3), 'other'
    for any other Windows bash, 'posix' off Windows, None when there is none. Windows needs 'git' (J6 report: WSL bash broke the tests)."""
    if not path:
        return None
    if not nt:
        return 'posix'
    p = str(path).replace('\\', '/').lower()
    if '/windows/system32/' in p or '/windowsapps/' in p:
        return 'wsl'
    return 'git' if '/git/' in p else 'other'


def git_bash(nt=os.name == 'nt', which=shutil.which, git_exec_path=None, isfile=os.path.isfile):
    """The bash to run repo shell scripts with: off Windows the bash on PATH; on Windows Git for Windows' bash.exe, found explicitly
    (`bash` on PATH may be the WSL launcher: J6, J22). Order: `bash` on PATH when it is Git's, the Git install that `git --exec-path`
    names, the default install folders. None when there is none. Shared helper (J41); J22's tests use it too."""
    b = which('bash')
    if not nt:
        return b
    if bash_kind(b, nt=True) == 'git':
        return b
    if git_exec_path is None:
        rc, out = _run(['git', '--exec-path'], timeout=15)
        git_exec_path = out if rc == 0 else ''
    roots = []
    p = (git_exec_path or '').strip().replace('\\', '/')   # e.g. C:/Program Files/Git/mingw64/libexec/git-core
    i = p.lower().find('/mingw')
    if i > 0:
        roots.append(p[:i])
    roots += [f'{os.environ[v]}/Git' for v in ('ProgramFiles', 'ProgramW6432', 'LOCALAPPDATA') if os.environ.get(v)]
    roots.append(f'{os.environ.get("LOCALAPPDATA", "")}/Programs/Git')
    for r in roots:
        for sub in ('bin/bash.exe', 'usr/bin/bash.exe'):   # bin/bash.exe sets up the MSYS PATH itself
            c = f'{r}/{sub}'.replace('/', '\\')
            if isfile(c):
                return c
    return None


def bash_for_tests(nt=os.name == 'nt', find=None):
    """(bash, None) or (None, reason) for a host test that runs a shell script (J22). On Windows git_bash() or a skip reason, never the
    WSL `bash` on PATH; off Windows git_bash() or plain 'bash', so a missing bash fails as before instead of skipping."""
    b = (find or git_bash)(nt=nt)
    if b or not nt:
        return b or 'bash', None
    return None, 'no Git Bash found (`python3 core/wsc.py setup` says what was looked for); the WSL bash on PATH is never used'


def cr_files(root, paths):
    """The paths (relative) whose working-tree bytes contain a CR: a CRLF shell script fails in bash (`$'\\r': command not found`)."""
    return [p for p in paths if b'\r' in (Path(root) / p).read_bytes()]


def pinned_version(toml_text):
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', re.split(r'^\[core\]\s*$', toml_text, flags=re.M)[-1], re.M)
    return m.group(1) if m else None


def main_clone(git_common_dir):
    """The main checkout folder from `git rev-parse --git-common-dir` (a worktree's common dir is the main clone's .git)."""
    return Path(git_common_dir).resolve().parent


# ---- checks: each returns (ok, detail, fix hint) ----------------------------------------------------------------------------------
def _run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 127, str(e)


def bash_check(on_path, explicit, msystem, nt=os.name == 'nt'):
    """(ok, detail, fix) for the git_bash check from the bash on PATH, the explicit git_bash() path and $MSYSTEM (J22). It fails only
    when git_bash() finds none: the repo's tools and tests run that one. On Windows a PATH bash that is not Git's (the WSL launcher), or
    a session not started from Git Bash, is a warning line: the tools still work, a bare `bash` typed in the session does not."""
    if not nt:
        return explicit is not None, f'bash at {explicit}', 'install bash'
    k = bash_kind(on_path, nt=True)
    detail = f'bash on PATH: {on_path} ({k}); MSYSTEM={msystem or "unset"}; repo tools use: {explicit}'
    if explicit and not (k == 'git' and msystem):
        detail += ('\n     warn: this session is not a Git Bash one: start Claude Code from Git Bash, or put C:\\Program Files\\Git\\usr\\bin '
                   'before WindowsApps and System32 on PATH')
    return explicit is not None, detail, 'install Git for Windows (it brings Git Bash), then start Claude Code from Git Bash'


def check_git_bash(root, fix):
    return bash_check(shutil.which('bash'), git_bash(), os.environ.get('MSYSTEM'))


def check_python3(root, fix):
    exe = shutil.which('python3')
    rc, out = _run(['python3', '--version']) if exe else (127, 'not on PATH')
    v = parse_version(out) if rc == 0 else None
    if (v is None or v < MIN_PY) and fix and os.name == 'nt' and sys.version_info[:2] >= MIN_PY:
        dst = Path(sys.executable).with_name('python3.exe')
        if not dst.exists():
            shutil.copy2(sys.executable, dst)
            print(f'setup --fix: copied {sys.executable} to {dst}')
        rc, out = _run([str(dst), '--version'])
        v = parse_version(out) if rc == 0 else None
        exe = str(dst)
    ok = v is not None and v >= MIN_PY
    return ok, f'python3 = {exe} ({out.splitlines()[0] if out else "no output"})', \
        f'install Python >= {MIN_PY[0]}.{MIN_PY[1]}, then `wsc setup --fix` (copies python.exe to python3.exe beside it) and put that folder first on PATH'


def check_core_pin(root, fix):
    want = pinned_version((root / 'wsc.toml').read_text(encoding='utf-8'))
    rc, out = _run(['git', 'describe', '--tags', '--exact-match'], cwd=root / 'core')
    return rc == 0 and out == want, f'core at {out if rc == 0 else "no tag (" + out[:60] + ")"}, wsc.toml pins {want}', \
        'git submodule update --init (and check core/ has no local edits)'


def hooks_path_ok(value):
    """Exactly core/.githooks, as the core's `hooks` gate wants: relative, so every worktree runs its own pinned core's hooks (an
    absolute path to the main clone's core/ would run another checkout's pin)."""
    return value == 'core/.githooks'


def check_hooks_path(root, fix):
    rc, out = _run(['git', 'config', '--get', 'core.hooksPath'], cwd=root)
    if not hooks_path_ok(out) and fix:
        _run(['git', 'config', 'core.hooksPath', 'core/.githooks'], cwd=root)
        print('setup --fix: git config core.hooksPath core/.githooks')
        rc, out = _run(['git', 'config', '--get', 'core.hooksPath'], cwd=root)
    return hooks_path_ok(out), f'core.hooksPath = {out or "unset"}', 'git config core.hooksPath core/.githooks'


def check_lf_scripts(root, fix):
    rc, out = _run(['git', 'ls-files', '*.sh', '*.py'], cwd=root)
    bad = cr_files(root, [p for p in out.splitlines() if p and (root / p).is_file()]) if rc == 0 else ['git ls-files failed']
    _, attr = _run(['git', 'check-attr', 'eol', '--', 'core/harness/job.sh'], cwd=root)
    _, crlf = _run(['git', 'config', '--get', 'core.autocrlf'], cwd=root)
    return not bad, f'{len(out.splitlines())} scripts, {len(bad)} with CR ({", ".join(bad[:3])}); {attr.split(": ")[-1] or "?"} attribute, core.autocrlf={crlf or "unset"}', \
        'the .gitattributes eol=lf rules must be in the checkout: git rm --cached -r . && git reset --hard (only with no local changes)'


def check_gh_auth(root, fix):
    rc, out = _run(['gh', 'auth', 'status'])
    first = next((l.strip() for l in out.splitlines() if 'Logged in' in l or 'not logged' in l.lower()), out[:80])
    return rc == 0, first, 'gh auth login'


def check_docker(root, fix):
    rc, out = _run(['docker', 'info', '--format', '{{.ServerVersion}} {{.OSType}}'], timeout=30)
    return rc == 0, f'docker server {out}' if rc == 0 else out.splitlines()[-1][:120] if out else 'docker not found', \
        'start Docker Desktop (Linux containers) and wait for "Engine running"; proxy/README.md "Build"'


def check_empire_clone(root, fix):
    rc, common = _run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=root)
    e = main_clone(common).parent / 'empire-remastered' if rc == 0 else root.parent / 'empire-remastered'
    if not (e / '.git').exists():
        return False, f'{e} missing', 'git clone https://github.com/liam-rowley/empire-remastered (beside this repo, read-only evidence)'
    rc, out = _run(['git', 'status', '--porcelain'], cwd=e)
    n = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else -1
    return n == 0, f'{e}: {n} local changes' if n else f'{e}: clean', \
        'empire-remastered is read-only evidence: move its local changes out (never commit there from Napoleon work)'


def check_playwright(root, fix):
    code = ('from playwright.sync_api import sync_playwright\nimport os\n'
            'with sync_playwright() as p: x = p.chromium.executable_path; print(x, os.path.exists(x))')
    rc, out = _run(['python3', '-c', code], timeout=90)
    ok = rc == 0 and out.endswith('True')
    return ok, out.splitlines()[-1][:120] if out else 'no output', 'python3 -m pip install playwright && python3 -m playwright install chromium'


def check_watcher(root, fix):
    bash = git_bash()
    if bash is None:
        return False, 'no Git Bash to run job.sh with', 'install Git for Windows (the git_bash check says what was looked for)'
    rc, out = _run([bash, str(root / 'harness' / 'core' / 'job.sh'), 'status'], timeout=30)
    tail = out.splitlines()[-1][:120] if out else ''
    return rc == 0, f'job.sh status exit {rc}: {tail}', 'the watcher runs as a logon task: after a reboot wait for it, or double-click <state>\\watcher\\src\\watch.cmd (harness/README.md)'


def load_pc_deploy(root):
    """core/proxy/tools/pc_deploy.py as a module: the one owner of the PC-rule damage checks (it also travels in every kit, stdlib only)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('pc_deploy', root / 'core' / 'proxy' / 'tools' / 'pc_deploy.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pc_rules_result(pd, game, state, other_games, ident):
    """(ok, detail) for the pc_rules check; None when the game or state folder is absent (CI, another host): the check is skipped."""
    if not Path(game).is_dir() or not Path(state).is_dir():
        return None
    fails, lines = pd.pc_rules(game, state, ident)
    for g in other_games:
        gits = pd.git_dirs(g) if Path(g).is_dir() else []
        lines.append(f'git ({Path(g).name}): ' + ('FAIL ' + ', '.join(gits) if gits else 'ok, no .git in that game folder or its parents'))
        fails += bool(gits)
    return fails == 0, '; '.join(l.splitlines()[0] for l in lines)


def check_pc_rules(root, fix):
    pd = load_pc_deploy(root)
    import json
    ad = json.loads((root / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
    games = json.loads((root / 'discovery' / 'napoleon' / 'games.json').read_text(encoding='utf-8'))
    r = pc_rules_result(pd, ad['game_dir'], ad['state_dir'], [games['empire']['root']], pd.default_identity())
    if r is None:
        return True, f'skipped: no game folder ({ad["game_dir"]}) or state folder ({ad["state_dir"]}) on this host', ''
    return r[0], r[1], ('python3 core/proxy/tools/pc_deploy.py status --game <game_dir> --state <state_dir> lists each failure; '
                        'an exe mismatch or a .git there is for Liam to decide (nothing is fixed here, --fix included)')


def add_arguments(p):
    p.add_argument('--fix', action='store_true', help='apply the safe fixes (python3.exe copy, core.hooksPath)')
    p.add_argument('--skip', nargs='*', default=[], choices=CHECKS, help='checks to skip')


def run(args, ctx):
    root = Path(ctx.root)
    fails = 0
    for name in CHECKS:
        if name in args.skip:
            print(f'skip {name}')
            continue
        try:
            ok, detail, hint = globals()[f'check_{name}'](root, args.fix)
        except Exception as e:   # a broken check is a failed check, never a traceback
            ok, detail, hint = False, f'{type(e).__name__}: {e}', 'see the check in tools/verbs/setup.py'
        fails += not ok
        print(f'{"ok  " if ok else "FAIL"} {name}: {detail}' + ('' if ok else f'\n     fix: {hint}'))
    print(f'setup: {len(CHECKS) - len(args.skip) - fails} ok, {fails} failed')
    return 1 if fails else 0
