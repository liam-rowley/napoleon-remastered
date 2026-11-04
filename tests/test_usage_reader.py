"""Rule 75 usage half (J49): tools/usage_reader.py on synthetic transcripts, and the usage table of the PC block."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import usage_reader as ur   # noqa: E402
import jobs_hooks as hk     # noqa: E402

SECRET = 'SECRET-PROMPT-TEXT-do-not-render'


def asst(mid, ts, out=10, model='claude-opus-5-5', tools=0, branch='main', inp=1, cr=100, cw=5):
    return json.dumps({'type': 'assistant', 'timestamp': ts, 'gitBranch': branch, 'sessionId': 's', 'isSidechain': False,
                       'message': {'id': mid, 'model': model, 'usage': {'input_tokens': inp, 'output_tokens': out, 'cache_read_input_tokens': cr, 'cache_creation_input_tokens': cw},
                                   'content': [{'type': 'text', 'text': SECRET}] + [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': SECRET}}] * tools}})


def write(path, *lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


class Reader(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        self.proj = self.d / 'projects' / 'slug'

    def tearDown(self):
        self.td.cleanup()

    def test_repeated_usage_counts_once_and_models_and_calls_sum(self):
        write(self.proj / 'a.jsonl', asst('m1', '2026-11-01T10:00:00Z', out=7, tools=2), asst('m1', '2026-11-01T10:00:01Z', out=9, tools=2),
              asst('m2', '2026-11-01T11:00:00Z', model='claude-sonnet-5-5', out=4, tools=1), json.dumps({'type': 'user', 'message': {'content': SECRET}}))
        s = ur.usage_by_session(self.d / 'projects')['sessions']['a']
        t = ur.totals(s)
        self.assertEqual(t['models']['claude-opus-5-5'], [1, 9, 100, 5])      # once, with the larger output figure
        self.assertEqual(t['models']['claude-sonnet-5-5'], [1, 4, 100, 5])
        self.assertEqual((t['calls'], t['replies']), (3, 2))

    def test_subagent_folder_counts_toward_its_session_and_cost_state_is_the_last(self):
        write(self.proj / 'a.jsonl', asst('m1', '2026-11-01T10:00:00Z', tools=1),
              json.dumps({'type': 'cost-state', 'totalCostUSD': 1.0}), json.dumps({'type': 'cost-state', 'totalCostUSD': 2.5, 'modelUsage': {'x': {'costUSD': 2.5}}}))
        write(self.proj / 'a' / 'subagents' / 'agent-1.jsonl', asst('m9', '2026-11-01T10:05:00Z', tools=4))
        u = ur.usage_by_session(self.d / 'projects')
        s = u['sessions']['a']
        self.assertEqual((ur.totals(s)['calls'], s['subagents'], s['cost']['usd'], u['files']), (5, 1, 2.5, 2))

    def test_corrupt_line_is_skipped_and_counted_and_missing_folder_says_so(self):
        write(self.proj / 'a.jsonl', asst('m1', '2026-11-01T10:00:00Z'), '{not json', '[1,2]')
        u = ur.usage_by_session(self.d / 'projects')
        self.assertEqual(u['skipped'], 2)
        self.assertEqual(ur.totals(u['sessions']['a'])['replies'], 1)
        gone = ur.usage_by_session(self.d / 'nope')
        self.assertEqual(gone['sessions'], {})
        self.assertIn('does not exist', gone['error'])

    def test_cache_hits_then_invalidates_on_a_changed_file(self):
        f = self.proj / 'a.jsonl'
        write(f, asst('m1', '2026-11-01T10:00:00Z', out=5))
        cache = self.d / 'cache.json'
        ur.usage_by_session(self.d / 'projects', cache_path=cache)
        data = json.loads(cache.read_text())
        key = next(iter(data['files']))
        data['files'][key]['r']['days']['2026-11-01']['replies'] = 99       # a marker only a cache hit returns
        cache.write_text(json.dumps(data))
        self.assertEqual(ur.totals(ur.usage_by_session(self.d / 'projects', cache_path=cache)['sessions']['a'])['replies'], 99)
        time.sleep(0.02)
        write(f, asst('m1', '2026-11-01T10:00:00Z', out=5), asst('m2', '2026-11-01T10:01:00Z', out=6))
        self.assertEqual(ur.totals(ur.usage_by_session(self.d / 'projects', cache_path=cache)['sessions']['a'])['replies'], 2)

    def test_attribution_trailer_then_branch_then_name_else_unattributed(self):
        write(self.proj / 'sa.jsonl', asst('a', '2026-11-01T10:00:00Z', branch='job/J2', tools=1))               # trailer says J1, branch says J2: trailer wins
        write(self.proj / 'sb.jsonl', asst('b', '2026-11-01T10:00:00Z', branch='job/J2', tools=2))
        write(self.proj / 'sc.jsonl', asst('c', '2026-11-01T10:00:00Z', branch='main', tools=3), json.dumps({'type': 'agent-name', 'agentName': 'J3-build'}))
        write(self.proj / 'sd.jsonl', asst('d', '2026-11-01T10:00:00Z', branch='main', tools=4), json.dumps({'type': 'agent-name', 'agentName': 'chat'}))
        write(self.proj / 'se.jsonl', asst('e', '2026-11-01T10:00:00Z', branch='brief/J4', tools=5))
        u = ur.usage_by_session(self.d / 'projects')['sessions']
        rows = [{'id': f'J{i}'} for i in range(1, 5)]
        r = ur.usage_by_job(rows, u, {'J1': {'sa'}})
        self.assertEqual({k: (v['calls'], list(v['routes'])) for k, v in r['jobs'].items()},
                         {'J1': (1, ['trailer']), 'J2': (2, ['branch']), 'J3': (3, ['name']), 'J4': (5, ['branch'])})
        self.assertEqual((r['unattributed']['sessions'], r['unattributed']['calls']), (1, 4))

    def test_budget_is_read_from_a_brief(self):
        self.assertEqual(ur.budget_from_brief('Budget about 70 tool calls; at the cap'), 70)
        self.assertEqual(ur.budget_from_brief('about 120 tool calls'), 120)
        self.assertIsNone(ur.budget_from_brief('no budget'))

    def test_block_shows_usage_and_never_the_conversation_text(self):
        repo = self.d / 'repo'
        (repo / 'registries' / 'jobs').mkdir(parents=True)
        (repo / 'registries' / 'jobs' / 'J7.json').write_text(json.dumps({'id': 'J7'}))
        (repo / 'jobs' / 'J7').mkdir(parents=True)
        (repo / 'jobs' / 'J7' / 'brief.md').write_text('Budget about 50 tool calls.')
        write(self.proj / 'a.jsonl', asst('m1', '2026-11-01T10:00:00Z', branch='job/J7', tools=3), json.dumps({'type': 'agent-name', 'agentName': 'J7-build'}))
        us = hk.usage_state(repo, self.d / 'projects', rows=[{'id': 'J7'}])
        self.assertEqual(us['jobs'][0]['budget'], 50)
        html = hk.usage_html(us) + us['source']
        self.assertIn('3 / 50', html)
        self.assertIn('estimate', html)
        self.assertNotIn(SECRET, html)
        gone = hk.usage_state(repo, self.d / 'nope', rows=[{'id': 'J7'}])
        self.assertIn('does not exist', gone['source'])
        self.assertEqual(hk.usage_html(gone), '')


if __name__ == '__main__':
    unittest.main()
