#!/usr/bin/env python3
"""Claude Code PreToolUse hook: refuse a `git commit` that does not carry this session's `Claude-Session:` trailer (D21, J20).

purpose: make every local Claude Code commit name its session, so tools/pr_policy.py can tell the builder of a job from its reviewer: a Bash or PowerShell call that runs `git commit` without `--trailer "Claude-Session: <this session id>"` is denied with the exact flag to add
usage: wired in .claude/settings.json (PreToolUse, matcher Bash|PowerShell); reads the hook JSON on stdin; test: echo '{"session_id":"s","tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | python3 tools/claude_hook.py
when: automatic on every shell call in a Claude Code session in this repo; never run by hand except to test it
not-a-verb: Claude Code runs it with a JSON protocol on stdin and stdout, not through the wsc CLI
"""
import json
import re
import sys

COMMIT = re.compile(r'''(?<![\w./-])git(?:\.exe)?(?:\s+-[cC]\s+(?:"[^"]*"|'[^']*'|\S+))*\s+commit(?![\w-])''')


def decide(event):
    """None to let the call through, else the reason it is denied."""
    if event.get('tool_name') not in ('Bash', 'PowerShell'):
        return None
    cmd = str((event.get('tool_input') or {}).get('command', ''))
    sid = str(event.get('session_id') or '').strip()
    if not COMMIT.search(cmd) or not sid:
        return None
    if re.search(r'Claude-Session:\s*' + re.escape(sid) + r'(?![\w-])', cmd):
        return None
    return (f'Every commit in this repo names its Claude Code session (tools/pr_policy.py refuses a job whose report or review was '
            f'committed without one). Run the same command again with this flag after `git commit`: '
            f'--trailer "Claude-Session: {sid}"')


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0   # not ours to judge: let the normal permission flow decide
    why = decide(event)
    if why:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': why}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
