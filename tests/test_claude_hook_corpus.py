"""J76: the command-shape corpus for tools/claude_hook.py. Every row is (family, command, cwd, 'deny'|'allow'[, mode]) run through the real
decide() with fixture roots; the denied rows are the bypasses the 2026-11-03 audit (H1, H6, H12, R11, P6) lists, the allowed rows are what the
pipeline runs and the look-alikes that must keep working. Every protected path here is a fixture: nothing touches a game folder or the PC state
folder. Set HOOK_UNDER_TEST=<path to an older claude_hook.py> to count red rows against it (the report's red/green numbers)."""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_SHORT = None
HOOK = Path(os.environ.get('HOOK_UNDER_TEST') or ROOT / 'tools' / 'claude_hook.py')
spec = importlib.util.spec_from_file_location('claude_hook_under_test', HOOK)
ch = importlib.util.module_from_spec(spec)
sys.modules.pop('hook_parse', None)
spec.loader.exec_module(ch)
REAL_SHORT = getattr(ch, 'expand_short', None)

NAP = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
NAPU = 'C:/Program Files (x86)/Steam/steamapps/common/Napoleon Total War'
EMP = 'C:/Program Files (x86)/Steam/steamapps/common/Empire Total War'
STATE = '/c/napoleon_remastered_pc'
APP = 'C:/Users/fixture/AppData/Roaming/The Creative Assembly/Napoleon'
ROOTS = ([ch.norm(NAP), ch.norm(EMP)], ch.norm(STATE), [ch.norm(APP + '/scripts/preferences.script.txt'), ch.norm(APP + '/save_games')])
REPO = ch.norm(ROOT)
SIBLING = ch.norm(ROOT.parent / 'nap-job-J99')   # a worktree beside the checkout
SID = 'abc-123'
TR = f' --trailer "Claude-Session: {SID}"'
GITCONFIG = tempfile.NamedTemporaryFile('w', suffix='.gitconfig', delete=False)
GITCONFIG.write('[user]\n\tname = x\n[alias]\n\tci = commit -v\n\tst = status\n')
GITCONFIG.close()
PRS = {'12': 'plan/x', '13': 'job/J76', 'https://github.com/o/r/pull/12': 'plan/x', None: 'meta/y', '77': 'brief/J76'}


def short(p):
    return p.replace('progra~2', 'program files (x86)').replace('napole~1', 'napoleon total war')


def setUpModule():
    ch.expand_short = short
    ch.alias_files = lambda: [Path(GITCONFIG.name)]
    if hasattr(ch, 'read_aliases'):
        ch.read_aliases.cache_clear()
    ch.PR_HEAD = lambda target, repo, cwd: PRS.get(target)


def tearDownModule():
    os.unlink(GITCONFIG.name)


D, A = 'deny', 'allow'
P = 'ps'
CASES = []


def add(family, rows):
    for r in rows:
        r = tuple(r)
        cmd, verdict = r[0], r[1]
        cwd = r[2] if len(r) > 2 and r[2] else REPO
        CASES.append((family, cmd, cwd, verdict, r[3] if len(r) > 3 else ''))


add('exempt', [
    ('python3 core/proxy/tools/pc_deploy.py status; rm -rf ' + STATE + '/watcher', D),
    ('bash core/harness/job.sh status && echo x > ' + STATE + '/watcher/watcher.ini', D),
    (f'python3 /tmp/pc_deploy.py install --kit k --game "{NAP}" --state {STATE}', D),
    (f'python3 core/proxy/tools/pc_deploy.py status > "{NAPU}/x.log"', D),
    (f'cd {STATE} ; bash core/harness/job.sh status; touch kits/x', D),
    ('echo pc_deploy.py job.sh > ' + STATE + '/watcher/watcher.ini', D),
    (f'bash core/harness/job.sh j18 - <<< "launch owner=j18" > {STATE}/x.log', D),
    ('python3 core/proxy/tools/pc_deploy.py status', A),
    (f'python3 core/proxy/tools/pc_deploy.py install --kit k --game "{NAP}" --state {STATE}', A),
    ('bash core/harness/job.sh scratch j76 && echo x > ' + STATE + '/_scratch/j76/a.txt', A),
])
add('writers', [
    (f'install -m 644 a.dll "{NAPU}/d3d9.dll"', D),
    (f'rsync -a build/ "{NAPU}/"', D),
    (f'dd if=/dev/zero of="{NAPU}/big.bin" bs=1 count=1', D),
    (f'tar -xf a.tar -C "{NAPU}"', D),
    (f'tar -cf "{STATE}/kits/a.tar" build', D),
    (f'ln -s /tmp/x "{NAPU}/link"', D),
    (f'robocopy build "{NAP}" /E', D),
    (f'xcopy build "{NAP}" /E /Y', D),
    (f'copy a.txt "{NAP}\\a.txt"', D),
    (f'move a.txt "{NAP}\\a.txt"', D),
    (f'ren "{NAP}\\a.txt" b.txt', D),
    (f'Rename-Item "{NAP}\\a.txt" b.txt', D, None, P),
    (f'truncate -s 0 "{NAPU}/dxvk.conf"', D),
    (f'cat > "{NAPU}/notes.txt"', D),
    (f'echo x >| "{NAPU}/n.txt"', D),
    (f'echo x &> "{NAPU}/n.txt"', D),
    (f'echo x &>> "{NAPU}/n.txt"', D),
    (f'echo x >& "{NAPU}/n.txt"', D),
    (f'echo x 1<> "{NAPU}/n.txt"', D),
    (f'ls nope 2> "{NAPU}/err.txt"', D),
    (f'G="{NAPU}"; echo x > "$G/dxvk.conf"', D),
    (f'echo "{NAPU}" > /dev/null; cp a "$SURELY_UNSET_J76/b"', D),
    ('$env:G = "' + NAP + '"; "x" | Out-File "$env:G\\o.txt"', D, None, P),
    (r'cp a.dll "C:\PROGRA~2\Steam\steamapps\common\NAPOLE~1\d3d9.dll"', D),
    (r'echo x > C:\PROGRA~2\Steam\steamapps\common\NAPOLE~1\n.txt', D),
    (f'python3 -c "open(\'{NAPU}/dxvk.conf\', \'w\').write(\'x\')"', D),
    (f'python3 - <<\'EOF\'\nimport shutil\nshutil.rmtree(r"{STATE}/watcher")\nEOF', D),
    (f'node -e "require(\'fs\').writeFileSync(\'{NAPU}/a\', \'x\')"', D),
    (f'powershell -Command "Remove-Item -Recurse \'{NAP}\\x\'"', D),
    (f'mklink "{NAP}\\l" C:\\tmp\\x', D),
    (f'Set-ItemProperty -Path "{NAP}\\a" -Name x -Value 1', D, None, P),
    (f'echo x > "{APP}/scripts/preferences.script.txt"', D),
    (f'cp saves/a.esf "{APP}/save_games/a.esf"', D),
    (f'find "{NAPU}/data" -delete', D),
    ('echo x >&2', A),
    ('cmd 2>&1', A),
    ('echo x > /dev/null 2>&1', A),
    ('echo x > "$OUT"', A),
    (f'python3 -c "print(open(\'{NAPU}/dxvk.conf\').read())"', A),
    (f'echo x > {STATE}/_scratch/j76/a.txt', A),
    (f'mkdir -p "{STATE}/_scratch/j76/x" && cp a "{STATE}/_scratch/j76/x"', A),
    ('mkdir -p build/x && cp a build/x && echo y > build/x/b', A),
    (f'cp "{NAPU}/dxvk.conf" /tmp/x && tar -cf /tmp/a.tar "{NAPU}/data"', A),
    (f'diff "{NAPU}/a" "{APP}/scripts/preferences.script.txt"', A),
])
add('git', [
    (f'G="{NAPU}"; (cd "$G" && git init)', D),
    (f'G={STATE}; cd "$G"; git init', D),
    (f'git init "{NAPU}/sub"', D),
    (f'git clone https://x.example/y.git "{EMP}/y"', D),
    (f'git -c core.worktree="{NAPU}" status', D),
    ('nice git status', D, NAPU),
    ('timeout 5 git status', D, NAPU),
    ('env -i git status', D, NAPU),
    ('sudo git status', D, NAPU),
    ('if true; then git status; fi', D, NAPU),
    ('{ git status; }', D, NAPU),
    ("bash -c 'git status'", D, NAPU),
    (f'sh -c "cd \'{NAPU}\' && git status"', D),
    (f'Start-Process git -ArgumentList "-C","{NAP}","status"', D, None, P),
    ('cmd /c git status', D, NAPU),
    (f'echo $(cd "{NAPU}"; git rev-parse HEAD)', D),
    (f'echo `cd "{NAPU}"; git rev-parse HEAD`', D),
    (f'git worktree add "{NAPU}/wt" main', D),
    (f'ls "{NAPU}" > /dev/null; cd "$SURELY_UNSET_J76"; git status', D),
    (f'echo "{STATE}"; git -C "$SURELY_UNSET_J76" log', D),
    (f'GIT_DIR="{NAPU}/.git" git log', D),
    (f'git --git-dir "{EMP}/.git" log', D),
    (f'git submodule add https://x.example/m "{NAPU}/m"', D),
    ('git status', D, STATE + '/_scratch/j76'),
    ('git status', A),
    ('git status', A, SIBLING),
    (f'ls "{NAPU}" | grep git', A),
    ('echo git', A, NAPU),
    (f'git -C {REPO} log', A, NAPU),
    ('cd "$(mktemp -d)" && git status', A),
    ('git worktree add ../nap-job-J98 -b job/J98 origin/main', A),
    ('bash -c "git status" && echo ok', A),
])
add('launch', [
    ('./Napoleon.exe &', D, NAPU),
    (f'"{NAPU}/Napoleon.exe"', D),
    ('start steam://rungameid/34030', D),
    ('Start-Process Napoleon.exe', D, None, P),
    ('cmd /c start Napoleon.exe', D),
    ('explorer steam://rungameid/34030', D),
    ('taskkill /IM Napoleon.exe /F', D),
    ('Stop-Process -Name Napoleon', D, None, P),
    ('pkill -f Napoleon', D),
    ('Get-Process Napoleon | Stop-Process', D, None, P),
    ('taskkill /IM Empire.exe', D),
    (f'sha1sum "{NAPU}/Napoleon.exe"', A),
    ('kill 1234', A),
    ('bash core/harness/job.sh j76 launch owner=j76', A),
    ('python3 core/proxy/tools/pc_deploy.py status', A),
    ('pkill -f napoleon-remastered-watch', A),
])
add('commit', [
    ('git --no-pager commit -m x', D),
    ('git -P commit -m x', D),
    ('git --git-dir=x commit -m x', D),
    ('git -c user.name=x -c y=z commit -m x', D),
    ('git -c alias.ci=commit ci -m x', D),
    ('git ci -m x', D),
    ('git config alias.ci commit', D),
    ('git commit -m x --no-verify' + TR, D),
    ('git commit -n -m x' + TR, D),
    ('git commit -an -m x' + TR, D),
    ('git commit -nm x' + TR, D),
    ('git push --no-verify', D),
    ('git -c core.hooksPath=/dev/null commit -m x' + TR, D),
    ('git merge --no-verify topic', D),
    ('git rebase --no-verify main', D),
    ('git cherry-pick --no-verify abc', D),
    ('git am --no-verify a.patch', D),
    ('git commit -m x' + TR, A),
    ('git --no-pager commit -m x' + TR, A),
    ('git -P commit -m x' + TR, A),
    ('git --git-dir=x commit -m x' + TR, A),
    ('git -c user.name=x -c y=z commit -m x' + TR, A),
    ('git -c alias.ci=commit ci -m x' + TR, A),
    ('git ci -m x' + TR, A),
    ('git commit -m "--no-verify"' + TR, A),
    ('git commit-tree HEAD^{tree}', A),
    ('git config core.hooksPath core/.githooks', A),
    ('git log --grep commit', A),
    ('git push -n origin job/J76', A),
    ('git st', A),
])
add('merge', [
    ('gh pr merge plan/x --auto --squash', D),
    ('gh pr merge meta/x --auto --squash', D),
    ('gh pr merge origin/meta/x --auto --squash', D),
    ('gh pr merge refs/heads/plan/x --squash', D),
    ('gh pr merge 12 --auto --squash', D),
    ('gh pr merge https://github.com/o/r/pull/12 --squash', D),
    ('gh pr merge --auto --squash', D),
    ('gh pr merge 99 --auto --squash', D),
    ("bash -c 'gh pr merge meta/x --auto --squash'", D),
    ('gh api -X PUT repos/o/r/pulls/1/merge', D),
    ('gh pr merge plan/x -R liam-rowley/warscape-core --squash', D),
    ('nice gh pr merge liam:meta/x --squash', D),
    ('gh api graphql -f query=\'mutation { mergePullRequest(input: {pullRequestId: "x"}) { clientMutationId } }\'', D),
    ('gh pr merge job/J76 --auto --squash', A),
    ('gh pr merge brief/J76 --auto --squash', A),
    ('gh pr merge 13 --auto --squash', A),
    ('gh pr view job/J76', A),
    ('gh pr ready job/J76', A),
    ('gh pr create --draft --base main --head job/J76 --title "J76: t" --body "b"', A),
])
add('branches', [
    ('git push origin --delete scratch/x', A),
    ('git push origin -d scratch/x', A),
    ('git push origin :scratch/x', A),
    ('git push --delete origin scratch/x scratch/y', A),
    ('gh api -X DELETE repos/o/r/git/refs/heads/scratch/x', A),
    ('git push origin --delete main', D),
    ('git push origin --delete plan/x', D),
    ('git push origin :meta/x', D),
    ('git push origin --delete job/J1', D),
    ('git push origin -d brief/J1', D),
    ('gh api -X DELETE repos/o/r/git/refs/heads/job/J1', D),
    ('git push origin job/J76', A),
    ('git push -u origin brief/J76', A),
])
add('roots', [
    (f'echo x > "{NAPU}/dxvk.conf"', D, None, 'fallback'),
    ('cp a.dll "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Empire Total War\\d3d9.dll"', D, None, 'fallback'),
    ('cd /c/napoleon_remastered_pc && git init', D, None, 'fallback'),
    ('echo x > /c/napoleon_remastered_pc/_scratch/j76/a.txt', D, None, 'fallback'),
    ('git status', A, None, 'fallback'),
    ('mkdir -p build/x && cp a build/x', A, None, 'fallback'),
    ('git commit -m x' + TR, D, None, 'nocore'),
    ('git status', A, None, 'nocore'),
    ('echo hello', A, None, 'boom'),
    (f'rm -rf "{NAPU}/data"', D, None, 'boom'),
    ('git commit -m x', D, None, 'boom'),
])
PIPELINE = [
    'bash core/harness/job.sh scratch j76', 'bash core/harness/job.sh lock', 'bash core/harness/job.sh status', 'bash core/harness/job.sh ctl status',
    'bash core/harness/job.sh j76 launch owner=j76', 'python3 core/proxy/tools/pc_deploy.py install --kit k',
    'python3 core/proxy/tools/pc_deploy.py uninstall', 'python3 core/proxy/tools/pc_deploy.py set key=value', 'python3 core/proxy/tools/pc_deploy.py status',
    'python3 core/wsc.py setup', 'python3 core/wsc.py setup --fix', 'python3 core/wsc.py gates', 'python3 core/wsc.py gates --fast',
    'python3 core/wsc.py jobs next', 'python3 core/wsc.py jobs check', 'python3 core/wsc.py jobs review', 'python3 core/wsc.py jobs fix',
    'python3 core/wsc.py policy --branch job/J76 --base origin/main', 'python3 core/wsc.py reg set jobs J76 status=review report=jobs/J76/report.md',
    'git pull', 'git checkout -b job/J76 origin/main', 'git checkout job/J76', 'git push', 'git push -u origin job/J76', 'git push -u origin brief/J76',
    'git add -A && git commit -m "x" --trailer "Claude-Session: ' + SID + '"',
    'git commit -m "$(cat <<\'EOF\'\nJ76: it\'s done (don\'t panic)\n\nClaude-Session: ' + SID + '\nEOF\n)" --trailer "Claude-Session: ' + SID + '"',
    'gh pr create --draft --base main --head job/J76 --title "J76: Agent hook hardening" --body "first paragraph"', 'gh pr view job/J76',
    'gh pr ready job/J76', 'gh pr merge job/J76 --auto --squash', 'gh pr merge brief/J76 --auto --squash',
    'gh pr create --base main --head brief/J76 --title "brief: J76 Agent hook hardening"',
    'git push origin --delete scratch/x', 'git push origin -d scratch/x', 'git push origin :scratch/x',
]
for _c in PIPELINE:
    CASES.append(('pipeline', _c, REPO, A, ''))
    CASES.append(('pipeline', _c, SIBLING, A, ''))


def event(cmd, cwd, tool='Bash'):
    return {'session_id': SID, 'cwd': cwd, 'tool_name': tool, 'tool_input': {'command': cmd}}


def run_case(case):
    """The reason (or None) for one corpus row."""
    family, cmd, cwd, verdict, mode = case
    ev = event(cmd, cwd, 'PowerShell' if mode == P else 'Bash')
    if mode == 'fallback':
        return ch.decide(ev, roots=ch.FALLBACK)
    if mode == 'nocore':
        old = (ch.CORE_OK, ch.commit_lacks_trailer)
        ch.CORE_OK, ch.commit_lacks_trailer = False, (lambda *a, **k: False)
        try:
            return ch.decide(ev, roots=ROOTS)
        finally:
            ch.CORE_OK, ch.commit_lacks_trailer = old
    if mode == 'boom':
        old_decide, old_in, old_out, old_err = ch.decide, sys.stdin, sys.stdout, sys.stderr

        def boom(*a, **k):
            raise RuntimeError('forced')
        ch.decide, sys.stdin, sys.stdout, sys.stderr = boom, io.StringIO(json.dumps(ev)), io.StringIO(), io.StringIO()
        try:
            rc = ch.main()
            out = sys.stdout.getvalue()
        finally:
            ch.decide, sys.stdin, sys.stdout, sys.stderr = old_decide, old_in, old_out, old_err
        assert rc == 0, rc
        return json.loads(out)['hookSpecificOutput']['permissionDecisionReason'] if out else None
    return ch.decide(ev, roots=ROOTS)


def failures(family=None):
    bad = []
    for case in CASES:
        if family and case[0] != family:
            continue
        try:
            why = run_case(case)
        except Exception as x:   # an older hook without the new names counts as red
            why = f'ERROR {type(x).__name__}: {x}' if case[3] == A else 'deny'
        if (why is not None) != (case[3] == D):
            bad.append((case[0], case[1], case[2], case[3], why))
    return bad


class Corpus(unittest.TestCase):
    def test_the_corpus_is_big_enough(self):
        self.assertGreaterEqual(len(CASES), 107)
        counts = {}
        for c in CASES:
            counts[c[0]] = counts.get(c[0], 0) + 1
        for fam, least in (('exempt', 6), ('writers', 24), ('git', 24), ('launch', 10), ('commit', 14), ('merge', 14), ('branches', 8), ('roots', 6)):
            self.assertGreaterEqual(counts.get(fam, 0), least, fam)

    def test_every_row_gets_its_verdict(self):
        bad = failures()
        self.assertEqual(bad, [], '\n'.join(f'{b[0]}: want {b[3]} for {b[1]!r} in {b[2]} -> {b[4]}' for b in bad))

    def test_the_whole_corpus_is_fast(self):
        t = time.perf_counter()
        failures()
        self.assertLess(time.perf_counter() - t, 3.0)

    def test_decide_time_of_a_typical_command(self):
        ev = event('cd build && git add -A && git commit -m "x y" --trailer "Claude-Session: abc-123" && git push', REPO)
        n = 200
        t = time.perf_counter()
        for _ in range(n):
            ch.decide(ev, roots=ROOTS)
        per = (time.perf_counter() - t) / n * 1000
        print(f'\ndecide() typical command: {per:.2f} ms', file=sys.stderr)
        self.assertLess(per, 25)   # the target is 5 ms; the bound is generous for a busy CI host

    def test_one_hook_process_round_trip(self):
        t = time.perf_counter()
        r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event('git status', REPO)), capture_output=True, text=True)
        el = time.perf_counter() - t
        print(f'\nhook process round trip: {el * 1000:.0f} ms', file=sys.stderr)
        self.assertEqual((r.returncode, r.stdout), (0, ''))
        self.assertLess(el, 1.5)


class PipelineIsNeverBlocked(unittest.TestCase):
    """The way out: the real decide() (real protected_roots, real core/) on every pipeline command, from the repo and from a worktree."""

    def test_real_roots_real_core(self):
        denied = []
        for cwd in (REPO, SIBLING):
            for c in PIPELINE:
                why = ch.decide(event(c, cwd))
                if why:
                    denied.append((cwd, c, why))
        self.assertEqual(denied, [])

    def test_commands_printed_by_the_job_steps(self):
        p = subprocess.run([sys.executable, str(ROOT / 'core' / 'wsc.py'), 'jobs', 'next'], cwd=ROOT, capture_output=True, text=True, timeout=120)
        if p.returncode != 0 or not p.stdout.strip():
            self.skipTest('the queue has nothing to print')
        found = re.findall(r'(?:git (?:checkout|push|pull|commit)|gh pr (?:view|create|ready|merge)|python3 core/wsc\.py)[^\n;,]*?(?=\.?\s*(?:$|\n|,|;| then| and ))',
                           p.stdout)
        for c in found:
            c = re.sub(r'<[^>]*>', 'x', c).strip()
            self.assertIsNone(ch.decide(event(c, REPO)), c)


class Parser(unittest.TestCase):
    def units(self, cmd, cwd=REPO, env=None, ps=False):
        hp = sys.modules['hook_parse']
        p = hp.Parse(cwd, env or {}, ps, short)
        p.run(cmd)
        return p.units

    def test_separators_blocks_and_wrappers_unwrap(self):
        for cmd in ('a; git x', 'a && git x', 'a || git x', 'a | git x', 'a & git x', 'a\ngit x', 'if a; then git x; fi', '{ git x; }', '( git x )',
                    'echo $(git x)', 'echo `git x`', 'nice -n 5 git x', 'timeout -s KILL 5 git x', 'env -i FOO=1 git x', 'sudo -u me git x',
                    'xargs -n 1 git x', "bash -c 'git x'", "sh -lc 'git x'", 'eval "git x"', 'cmd /c git x', 'powershell -Command "git x"',
                    'Start-Process git -ArgumentList x', 'stdbuf -oL git x', 'time git x', 'command git x', 'nohup git x'):
            self.assertIn('git', [u.name for u in self.units(cmd)], cmd)

    def test_variables_and_cwd_flow_left_to_right(self):
        u = self.units('D=/c/x/y; cd "$D"; git status; cd ..; git log')
        self.assertEqual([x.cwd for x in u if x.name == 'git'], ['c:/x/y', 'c:/x'])
        u = self.units('cd "$SURELY_UNSET_J76"; git status')
        self.assertIsNone(u[-1].cwd)
        u = self.units('$env:D = "C:\\a\\b"; Set-Location $env:D; git status', ps=True)
        self.assertEqual(u[-1].cwd, 'c:/a/b')
        u = self.units('GIT_DIR=/c/g git status')
        self.assertEqual(u[-1].env['GIT_DIR'], '/c/g')

    def test_redirects_and_heredocs_are_found(self):
        u = self.units('echo a > f1 2>> f2 &> f3 3>&- >&2; cat <<EOF > f4\n$(rm x)\nEOF\necho b')
        self.assertEqual([t for _, t in u[0].redirs if t.startswith('f')], ['f1', 'f2', 'f3'])
        self.assertTrue(any(t == 'f4' for _, t in u[1].redirs))
        self.assertEqual(u[1].hd, '$(rm x)')

    def test_too_deep_is_unparseable(self):
        hp = sys.modules['hook_parse']
        p = hp.Parse(REPO, {}, False, short)
        p.run("sh -c \"sh -c 'sh -c \\\"sh -c \\\\\\\"sh -c true\\\\\\\"\\\"'\"")
        p2 = hp.Parse(REPO, {}, False, short)
        p2.run('echo ' + '$(' * 6 + 'true' + ')' * 6)
        self.assertTrue(p.unparseable or p2.unparseable)

    def test_short_names_expand_through_the_injected_function(self):
        hp = sys.modules['hook_parse']
        self.assertEqual(hp.rp(r'C:\PROGRA~2\x', REPO, short), 'c:/program files (x86)/x')
        self.assertIs(hp.rp(r'C:\ABCDEF~1\x', REPO, lambda p: p), hp.UNKNOWN)


class ShortNames(unittest.TestCase):
    def test_the_real_expander(self):
        self.assertEqual(REAL_SHORT(str(ROOT)).lower().replace('\\', '/'), str(ROOT).lower().replace('\\', '/'))   # a long path comes back as it was
        if sys.platform == 'win32' and os.path.isdir(r'C:\Program Files (x86)'):
            self.assertEqual(REAL_SHORT('C:/PROGRA~2').lower().replace('\\', '/'), 'c:/program files (x86)')
        else:
            self.assertEqual(REAL_SHORT('C:/PROGRA~2'), 'C:/PROGRA~2')


class Messages(unittest.TestCase):
    def test_every_family_names_its_route(self):
        want = [
            (f'echo x > "{NAPU}/a"', 'pc_deploy.py'), (f'echo x > "{NAPU}/a"', 'job.sh scratch'), (f'cd "{NAPU}" && git status', 'pc_deploy.py'),
            ('git commit -m x', f'--trailer "Claude-Session: {SID}"'), ('git commit -n -m x' + TR, 'pre-push hook'),
            ('Start-Process Napoleon.exe', 'core/harness/job.sh'), ('gh pr merge plan/x --auto', 'D50'), ('gh pr merge plan/x --auto', 'Liam'),
            ('git push origin --delete main', 'scratch/'), (f'echo x > "{APP}/save_games/a.esf"', 'stage_save.py'),
            (f'echo x > "{APP}/scripts/preferences.script.txt"', 'pc_deploy.py set'),
            (f'python3 -c "open(\'{NAPU}/a\', \'w\')"', 'pc_deploy.py'),
        ]
        for cmd, route in want:
            why = ch.decide(event(cmd, REPO), roots=ROOTS)
            self.assertIn(route, why or '', cmd)
        old = (ch.CORE_OK, ch.commit_lacks_trailer)
        ch.CORE_OK = False
        try:
            self.assertIn('git submodule update --init', ch.decide(event('git commit -m x' + TR, REPO), roots=ROOTS))
        finally:
            ch.CORE_OK, ch.commit_lacks_trailer = old
        self.assertIn('restore harness/napoleon/adapter.json', ch.decide(event(f'echo x > "{NAPU}/a"', REPO), roots=ch.FALLBACK))


if __name__ == '__main__':
    unittest.main()
