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
    # only the --trailer flag counts: a `Claude-Session:` line in a -m body is a trailer only in the message's last paragraph, and J44's 19
    # commits put it one paragraph above `Co-Authored-By:`, so git (and tools/pr_policy.py) read no session at all
    if re.search(r'--trailer[\s=]+["\']?Claude-Session:\s*' + re.escape(sid) + r'(?![\w-])', cmd):
        return None
    return (f'Every commit in this repo names its Claude Code session (tools/pr_policy.py refuses a job whose report or review was '
            f'committed without one). Run the same command again with this flag after `git commit`: '
            f'--trailer "Claude-Session: {sid}"')


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
