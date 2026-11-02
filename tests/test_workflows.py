"""Workflow `if:` rules, read from .github/workflows as text (J57; no new dependency, no YAML parser).

- gates.yml: a failed `changes` job must not skip the slow jobs (`proxy`, `viewer`, `harness-windows`): a skipped required check counts as
  passed for branch protection and auto-merge. Each slow job's `if:` is evaluated here for every combination of event and `changes` result
  by a small translation to Python, including GitHub's implicit `success()` when the expression has no status function.
- policy.yml: `policy` still skips draft pull requests (J54) and `notify` does not comment on the `ready_for_review` run, which is red
  by design because the reviewer marks the pull request ready before pushing the review commit (docs/REVIEW.md "Merging").
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / '.github' / 'workflows'


def job_ifs(text):
    """{job name: its top-level `if:` expression, with any ${{ }} wrapper removed, or None}."""
    jobs_at = re.search(r'^jobs:\s*$', text, re.M)
    body = text[jobs_at.end():]
    out = {}
    parts = re.split(r'^  ([A-Za-z0-9_-]+):\s*$', body, flags=re.M)   # [pre, name, block, name, block, ...]
    for name, block in zip(parts[1::2], parts[2::2]):
        m = re.search(r'^    if:\s*(.+?)\s*$', block, re.M)
        expr = m.group(1) if m else None
        if expr and expr.startswith('${{') and expr.endswith('}}'):
            expr = expr[3:-2].strip()
        out[name] = expr
    return out


def effective(expr, event, changes_result, output):
    """Does a job needing `changes` run? `expr` is its `if:`; cancellation is assumed not to happen."""
    has_status_fn = bool(re.search(r'!cancelled\(\)|\bsuccess\(\)|\bfailure\(\)|\balways\(\)', expr))
    py = expr.replace('!cancelled()', 'True')
    py = re.sub(r'needs\.changes\.outputs\.\w+', 'OUT', py)
    py = py.replace('needs.changes.result', 'RESULT').replace('github.event_name', 'EVENT')
    py = py.replace('&&', ' and ').replace('||', ' or ')
    py = re.sub(r'!(?!=)', ' not ', py)
    ran = eval(py, {'__builtins__': {}}, {'OUT': output, 'RESULT': changes_result, 'EVENT': event, 'True': True})
    return bool(ran) and (has_status_fn or changes_result == 'success')   # no status function = implicit success()


class GatesChanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ifs = job_ifs((WORKFLOWS / 'gates.yml').read_text(encoding='utf-8'))

    def test_the_three_slow_jobs_run_when_changes_did_not_succeed(self):
        for job in ('proxy', 'viewer', 'harness-windows'):
            expr = self.ifs[job]
            self.assertIn('!cancelled()', expr, job)
            self.assertIn("needs.changes.result != 'success'", expr, job)

    def test_a_failed_changes_job_runs_every_slow_job_on_push(self):
        for job in ('proxy', 'viewer', 'harness-windows'):
            for result in ('failure', 'skipped'):
                self.assertTrue(effective(self.ifs[job], 'push', result, ''), f'{job} skipped after changes {result}')

    def test_push_behaviour_with_a_good_changes_job_is_unchanged(self):
        for job in ('proxy', 'viewer', 'harness-windows'):
            self.assertTrue(effective(self.ifs[job], 'push', 'success', 'true'), job)
            self.assertFalse(effective(self.ifs[job], 'push', 'success', 'false'), job)

    def test_dispatch_behaviour_is_unchanged(self):
        """proxy and viewer never run on a workflow_dispatch; harness-windows always does (J19)."""
        for result in ('success', 'failure'):
            for out in ('true', 'false', ''):
                self.assertFalse(effective(self.ifs['proxy'], 'workflow_dispatch', result, out))
                self.assertFalse(effective(self.ifs['viewer'], 'workflow_dispatch', result, out))
                self.assertTrue(effective(self.ifs['harness-windows'], 'workflow_dispatch', result, out))

    def test_the_old_lines_fail_these_checks(self):
        """The pre-J57 expressions: a failed `changes` skipped the job (the evaluator is not vacuous)."""
        old = {'proxy': "github.event_name != 'workflow_dispatch' && needs.changes.outputs.proxy == 'true'",
               'harness-windows': "github.event_name == 'workflow_dispatch' || needs.changes.outputs.harness == 'true'"}
        for job, expr in old.items():
            self.assertNotIn('!cancelled()', expr)
            self.assertFalse(effective(expr, 'push', 'failure', ''), job)

    def test_the_pass_markers_save_nothing_without_a_tree_hash(self):
        text = (WORKFLOWS / 'gates.yml').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r"needs\.changes\.outputs\.\w+_tree != ''", text)), 6)   # two steps in each slow job


class PolicyReady(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ifs = job_ifs((WORKFLOWS / 'policy.yml').read_text(encoding='utf-8'))

    def test_policy_still_skips_draft_pull_requests(self):
        self.assertIn('github.event.pull_request.draft == false', self.ifs['policy'])

    def test_notify_is_silent_for_the_ready_for_review_run(self):
        self.assertIn('failure()', self.ifs['notify'])
        self.assertIn("github.event.action != 'ready_for_review'", self.ifs['notify'])

    def test_policy_runs_on_a_push_to_a_ready_pull_request(self):
        text = (WORKFLOWS / 'policy.yml').read_text(encoding='utf-8')
        self.assertRegex(text, r'types:\s*\[[^\]]*synchronize[^\]]*ready_for_review[^\]]*\]|types:\s*\[[^\]]*ready_for_review[^\]]*synchronize[^\]]*\]')


if __name__ == '__main__':
    unittest.main()
