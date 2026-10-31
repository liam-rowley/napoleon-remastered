"""Host tests for tools/claude_hook.py (the PreToolUse hook that puts the Claude-Session trailer on every commit) and the committed
.claude/settings.json that wires it and holds the deny rules. Runs in `wsc gates` (tests gate)."""
import importlib.util
import json
import os
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'tools' / 'claude_hook.py'
spec = importlib.util.spec_from_file_location('claude_hook', HOOK)
ch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ch)


def ev(cmd, tool='Bash', sid='abc-123'):
    return {'session_id': sid, 'tool_name': tool, 'tool_input': {'command': cmd}}


class Hook(unittest.TestCase):
    def test_commits_without_this_sessions_trailer_are_denied(self):
        for c in ('git commit -m x', 'cd repo && git add -A && git commit -q -m "a b"', 'git -c user.name=x commit --amend',
                  'git commit -m x --trailer "Claude-Session: other-session"', 'git commit -m x --trailer "Claude-Session: abc-1234"'):
            why = ch.decide(ev(c))
            self.assertIsNotNone(why, c)
            self.assertIn('--trailer "Claude-Session: abc-123"', why)
        self.assertIsNotNone(ch.decide(ev('git commit -m x', tool='PowerShell')))

    def test_a_session_line_in_the_message_body_is_not_enough(self):
        # J44: a Claude-Session line one paragraph above Co-Authored-By is not a trailer; only --trailer guarantees git reads it
        self.assertIsNotNone(ch.decide(ev('git commit -m "x\n\nClaude-Session: abc-123\n\nCo-Authored-By: C <n@a.com>"')))

    def test_everything_else_passes(self):
        for c in ('git commit -m x --trailer "Claude-Session: abc-123"', 'git status', 'git commit-tree HEAD^{tree}',
                  'git log --grep commit', 'echo "do not commit"', 'gh pr create', 'mygit commit'):
            self.assertIsNone(ch.decide(ev(c)), c)
        self.assertIsNone(ch.decide(ev('git commit -m x', tool='Edit')))
        self.assertIsNone(ch.decide(ev('git commit -m x', sid='')))

    def test_protocol_on_stdin_and_stdout(self):
        r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev('git commit -m x')), capture_output=True, text=True)
        out = json.loads(r.stdout)['hookSpecificOutput']
        self.assertEqual((r.returncode, out['hookEventName'], out['permissionDecision']), (0, 'PreToolUse', 'deny'))
        r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev('git status')), capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ''))
        r = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ''))

    def test_the_settings_command_never_blocks(self):
        # J20 review: the old command ran `git rev-parse` and, outside a repo, python on /tools/claude_hook.py: exit 2 = block the call.
        cmd = next(x['command'] for h in json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))['hooks']['PreToolUse']
                   for x in h['hooks'])
        self.assertNotIn('git ', cmd)
        commit = json.dumps(ev('git commit -m x'))
        with tempfile.TemporaryDirectory() as t:   # not a repo, no project dir, or a project dir without the hook (main before J20)
            for env in ({}, {'CLAUDE_PROJECT_DIR': t}, {'CLAUDE_PROJECT_DIR': str(Path(t) / 'missing')}):
                e = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
                e.update(env)
                r = subprocess.run(['bash', '-c', cmd], input=commit, cwd=t, env=e, capture_output=True, text=True)
                self.assertEqual((r.returncode, r.stdout), (0, ''), (env, r.stderr))
            e = dict(os.environ, CLAUDE_PROJECT_DIR=str(ROOT))   # the real project dir: the hook runs and denies
            r = subprocess.run(['bash', '-c', cmd], input=commit, cwd=t, env=e, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
            r = subprocess.run(['bash', '-c', cmd], input='[1, 2]', cwd=t, env=e, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout), (0, ''))

    def test_settings_wire_the_hook_and_deny_edits(self):
        s = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        pre = s['hooks']['PreToolUse']
        self.assertTrue(any(h['matcher'] == 'Bash|PowerShell' and '$CLAUDE_PROJECT_DIR' in x['command'].replace('{', '').replace(':-.}', '')
                            and 'tools/claude_hook.py' in x['command'] for h in pre for x in h['hooks']))
        deny = s['permissions']['deny']
        for want in ('Edit(//c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War/**)', 'Edit(~/repos/empire-remastered/**)',
                     'Edit(/core/**)'):
            self.assertIn(want, deny)

    def test_settings_deny_edits_in_the_other_game_and_the_managed_state(self):
        # J18: read from the owners (games.json, adapter.json), so a moved folder fails here instead of leaving a stale rule
        deny = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))['permissions']['deny']

        def rule(p):
            return 'Edit(/' + ch.norm(p).replace('c:', '/c', 1) + ')'
        lower = [d.lower() for d in deny]
        games = json.loads((ROOT / 'discovery/napoleon/games.json').read_text(encoding='utf-8'))
        state = json.loads((ROOT / 'harness/napoleon/adapter.json').read_text(encoding='utf-8'))['state_dir']
        self.assertIn(rule(games['empire']['root'] + '/**').lower(), lower)
        for part in ('watcher/**', 'kits/**', 'backup/**', 'snapshots/**', '_to_delete/**', 'install.json'):
            self.assertIn(rule(state + '/' + part).lower(), lower, part)
        self.assertFalse(any('_scratch' in d for d in deny), 'the scratch folders stay writable')

NAP = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
EMP = 'C:/Program Files (x86)/Steam/steamapps/common/Empire Total War'
STATE = '/c/napoleon_remastered_pc'
ROOTS = ([ch.norm(NAP), ch.norm(EMP)], ch.norm(STATE))
REPO = '/c/Users/liamr/repos/napoleon-remastered'


def pc(cmd, cwd=REPO, tool='Bash'):
    return ch.decide({'session_id': 'abc-123', 'cwd': cwd, 'tool_name': tool, 'tool_input': {'command': cmd}}, roots=ROOTS)


class PcRules(unittest.TestCase):
    """J18: rows 31 and 32 of the J5 ledger. Each fixture denies one command shape; the look-alikes pass."""

    def test_norm_reads_all_three_spellings(self):
        want = 'c:/program files (x86)/steam/steamapps/common/napoleon total war'
        for s in (NAP, NAP.replace('\\', '/'), '/c/' + NAP[3:].replace('\\', '/'), NAP.upper() + '\\'):
            self.assertEqual(ch.norm(s), want, s)

    def test_roots_come_from_their_owners(self):
        games, state = ch.protected_roots()
        self.assertIn(ch.norm(json.loads((ROOT / 'harness/napoleon/adapter.json').read_text(encoding='utf-8'))['game_dir']), games)
        self.assertEqual(len(games), 2)
        self.assertEqual(state, ch.norm(json.loads((ROOT / 'harness/napoleon/adapter.json').read_text(encoding='utf-8'))['state_dir']))

    def test_git_in_a_protected_root_is_denied(self):
        for c, cwd in (('git status', '/c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War'),
                       ('git status', NAP + r'\data'),
                       ('git log', r'c:\napoleon_remastered_pc\_scratch\j18'),
                       (f'cd "{EMP}" && git status', REPO),
                       ('cd /c/napoleon_remastered_pc; git init', REPO),
                       (f'git -C "{NAP}" status', REPO),
                       (f'git --git-dir="{EMP}/.git" status', REPO),
                       (f'git --work-tree "{STATE}" add -A', REPO),
                       (rf'GIT_DIR="{NAP}\.git" git status', REPO),
                       (f'$env:GIT_WORK_TREE = "{NAP}"; git status', REPO),
                       (r'Set-Location "C:\napoleon_remastered_pc"; git.exe status', REPO)):
            why = pc(c, cwd)
            self.assertIsNotNone(why, (c, cwd))
            self.assertIn('Never run git in a game folder', why)
            self.assertIn('pc_deploy.py', why)
        self.assertIsNotNone(pc('git status', NAP, tool='PowerShell'))

    def test_git_elsewhere_passes(self):
        for c, cwd in (('git status', REPO), (f'git -C {REPO} log', NAP), (f'cd "{NAP}" && ls && cd {REPO} && git status', REPO),
                       ('cd .. && git status', REPO), (f'ls "{NAP}" | grep git', REPO), ('echo git', NAP), ('gh pr view', NAP)):
            self.assertIsNone(pc(c, cwd), (c, cwd))

    def test_writes_into_a_protected_root_are_denied(self):
        for c in (f'echo x > "{NAP}/dxvk.conf"', f'echo x >> /c/napoleon_remastered_pc/watcher/watcher.ini',
                  f'cp build/proxy/napoleon/d3d9.dll "{NAP}"', f'cp -t "{NAP}" a b', f'mv "{NAP}/d3d9.dll" /tmp/',
                  f'mkdir -p "{STATE}/kits/x"', f'touch "{EMP}/x.txt"', f'rm -rf "{STATE}/_to_delete"', f'rm "{STATE}/_scratch/x.txt"',
                  f'echo a | tee "{NAP}/n.txt"', f'sed -i s/a/b/ "{NAP}/napoleon_remastered.ini"', f'unzip a.zip -d "{EMP}"',
                  f'cd "{NAP}" && touch x', f'cd "{NAP}"; echo hi > notes.txt',
                  rf'Copy-Item a.txt -Destination "{NAP}\a.txt"', rf'Copy-Item a.txt "{NAP}"', rf'Move-Item "{NAP}\x" C:\tmp',
                  rf'New-Item -ItemType File -Path "{STATE}\install.json"', rf'Set-Content -Path "{NAP}\dxvk.conf" -Value x',
                  rf'"x" | Out-File "{EMP}\o.txt"', rf'Remove-Item -Recurse "{STATE}\snapshots"', rf'Expand-Archive k.zip -DestinationPath "{NAP}"',
                  f'mkdir "{STATE}/_scratch/Bad Owner"'):
            why = pc(c)
            self.assertIsNotNone(why, c)
            self.assertIn('protected PC folder', why)
            self.assertIn('job.sh scratch', why)

    def test_bash_escaped_spaces_are_read_as_the_path(self):
        """J18 review: tab completion writes `Napoleon\\ Total\\ War`; the backslash there is an escape, not a Windows separator."""
        esc = r'/c/Program\ Files\ \(x86\)/Steam/steamapps/common/Napoleon\ Total\ War'
        for c in (f'cd {esc} && git status', f'git -C {esc} log', f'GIT_DIR={esc}/.git git log'):
            self.assertIn('Never run git', pc(c) or '', c)
        for c in (f'cp x.dll {esc}/', f'echo x > {esc}/dxvk.conf', f'rm {esc}/d3d9.dll'):
            self.assertIn('protected PC folder', pc(c) or '', c)
        self.assertIsNone(pc(r'ls /c/Program\ Files\ \(x86\)/Steam/steamapps/common/Napoleon\ Total\ War'))
        self.assertIsNone(pc(r'cp a.txt notes\ for\ j18.txt'))

    def test_reads_scratch_and_the_sanctioned_writers_pass(self):
        for c in (f'ls -la "{NAP}"', f'cat "{NAP}/napoleon_remastered.ini"', f'sha1sum "{NAP}/Napoleon.exe"', f'cp "{NAP}/dxvk.conf" /tmp/x',
                  rf'grep -r x "{STATE}/watcher" > /tmp/out.txt', rf'Get-Content "{NAP}\dxvk.conf"', rf'Copy-Item "{NAP}\dxvk.conf" C:\tmp\x',
                  rf'mkdir -p "{STATE}/_scratch/j18/a"', rf'echo x > {STATE}/_scratch/j18/x.txt', rf'cp a.txt "C:\napoleon_remastered_pc\_scratch\j18"',
                  f'python3 proxy/tools/pc_deploy.py install --kit k --game "{NAP}" --state {STATE}',
                  f'bash harness/core/job.sh j18 - <<< "launch owner=j18" > {STATE}/x.log', f'bash harness/core/job.sh scratch j18',
                  f'ls "{NAP}" 2>&1 | head', f'cmd > /dev/null 2>&1', 'echo $X > "$OUT"', 'git commit -m "a > b" --trailer "Claude-Session: abc-123"',
                  f'cd "{NAP}" && ls && cat dxvk.conf', 'mkdir -p build/x && cp a build/x'):
            self.assertIsNone(pc(c), c)

    def test_no_roots_file_means_no_pc_rule(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertRaises(OSError, ch.protected_roots, Path(t))


if __name__ == '__main__':
    unittest.main()
