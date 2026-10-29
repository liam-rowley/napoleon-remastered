"""Host tests for tools/claude_hook.py (the PreToolUse hook that puts the Claude-Session trailer on every commit) and the committed
.claude/settings.json that wires it and holds the deny rules. Runs in `wsc gates` (tests gate)."""
import importlib.util
import json
import subprocess
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

    def test_settings_wire_the_hook_and_deny_edits(self):
        s = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        pre = s['hooks']['PreToolUse']
        self.assertTrue(any(h['matcher'] == 'Bash|PowerShell' and 'tools/claude_hook.py' in x['command'] for h in pre for x in h['hooks']))
        deny = s['permissions']['deny']
        for want in ('Edit(//c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War/**)', 'Edit(~/repos/empire-remastered/**)',
                     'Edit(/core/**)'):
            self.assertIn(want, deny)


if __name__ == '__main__':
    unittest.main()
