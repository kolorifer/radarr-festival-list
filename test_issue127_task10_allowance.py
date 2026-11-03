"""Offline, invented-data tests for the single retained #127 Task 10."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from automation import github_worker as worker
from test_github_worker import FakeRunner
from test_issue127_corrective_allowance import CorrectionRunner, REPO, SNAPSHOT

BODY = (Path(__file__).parent / 'automation/authorizations/issue-127-task-10.txt').read_text().removesuffix('\n')
TASK9_LAUNCHER = '2d3b54376f8f18f0936162b1f1282c1fa0560999'


class Task10Runner(CorrectionRunner):
    def __init__(self, root):
        fresh = not (root / '.git/github-worker/127/state.json').exists()
        super().__init__(root)
        self.messages = [dict(id=7000000010, user=self.issue['user'], issue_url=self.issue['url'],
                              created_at='2026-11-08T10:00:00Z', updated_at='2026-11-08T10:00:00Z', body=BODY)]
        self.refs.append(dict(ref='refs/heads/automation/issue-127-claim-9', object={'sha': TASK9_LAUNCHER}))
        if fresh:
            self.state.update(consumed=list(range(1, 10)), retained=dict(task=9, state='NEEDS_USER',
                              snapshot=SNAPSHOT, checkout=str(self.checkout.resolve())))
            worker.save(self.state_file, self.state)

    def api(self, endpoint, **data):
        if endpoint == f'repos/{REPO}/issues/127':
            return copy.deepcopy(self.issue)
        if endpoint == f'repos/{REPO}/git/refs':
            assert json.loads(self.state_file.read_text())['consumed'] == list(range(1, 11))
            assert data['ref'] == 'refs/heads/automation/issue-127-claim-10'
        return FakeRunner.api(self, endpoint, **data)


class Task10Tests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Task10Runner(Path(tmp.name).resolve())

    def test_exact_owner_body_and_embedded_review(self):
        self.assertEqual(hashlib.sha256(BODY.encode()).hexdigest(),
                         'f0797e7f1da3681d0e82f885a3d0efaf40daeee730d1a3f7e5daa4c265bc1c4e')
        review = BODY.split('EXACT_PRIOR_REVIEW:\n', 1)[1].split('\n\n', 1)[1]
        restored = '\n'.join(line[2:] if line.startswith('> ') else '' for line in review.split('\n'))
        self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),
                         'f3de236217e10f5784774aa98e310459556080f0f7c5944f03b3c3737a0b486d')
        self.assertEqual(worker.task_number(BODY), 10)

    def test_only_exact_task_claims_once_and_restart_does_not_relaunch(self):
        r = self.fixture()
        original = copy.deepcopy(r.refs)
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT), patch.object(r, 'refresh_quota', return_value=80):
            r.start()
        self.assertEqual(r.state['consumed'], list(range(1, 11)))
        self.assertEqual(r.refs[:9], original)
        self.assertEqual([c for c in r.calls if c[0] == 'execute'], [('execute', 10)])
        restarted = Task10Runner(r.repo)
        restarted.refs = r.refs
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT):
            restarted.start()
        self.assertFalse(any(c[0] == 'execute' for c in restarted.calls))

    def test_each_authority_and_claim_drift_refuses(self):
        changes = {
            'owner bytes': lambda r: r.messages[0].update(body=BODY + ' '),
            'edited comment': lambda r: r.messages[0].update(updated_at='2026-11-08T10:01:00Z'),
            'old comment': lambda r: r.messages[0].update(id=6605436294),
            'missing prior claim': lambda r: r.refs.pop(),
            'wrong ninth claim': lambda r: r.refs[-1]['object'].update(sha='0'*40),
            'wrong earlier claim': lambda r: r.refs[0]['object'].update(sha='0'*40),
            'old retained task': lambda r: r.state['retained'].update(task=8),
            'wrong retained state': lambda r: r.state['retained'].update(state='FAILED'),
            'wrong snapshot': lambda r: r.state['retained'].update(snapshot='0'*64),
            'missing consumed': lambda r: r.state['consumed'].pop(),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                r = self.fixture()
                change(r)
                with patch.object(worker, 'snapshot', return_value=SNAPSHOT):
                    self.assertIsNone(r.eligible(r.issue, 'kolorifer'))
                self.assertFalse(any(c[0] == 'execute' for c in r.calls))

    def test_latest_authority_is_rechecked_before_reservation(self):
        r = self.fixture()
        def quota():
            r.messages[0]['body'] += ' '
            return 80
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT), patch.object(r, 'refresh_quota', side_effect=quota):
            with self.assertRaises(worker.Stop):
                r.start()
        self.assertEqual(r.state['consumed'], list(range(1, 10)))
        self.assertEqual(len(r.refs), 9)

    def test_exact_task_launches_terra_high_in_existing_sandbox(self):
        r = self.fixture()
        r.state['consumed'].append(10)
        worker.save(r.state_file, r.state)
        r.repo = r.checkout
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT), patch.object(r, 'verify_storage'), \
                patch.object(worker.subprocess, 'run', side_effect=RuntimeError('intercepted')) as launch:
            with self.assertRaisesRegex(RuntimeError, 'intercepted'):
                worker.Runner.execute_in_checkout(r, r.issue, r.messages[0], 10)
        command = launch.call_args.args[0]
        self.assertEqual(command[command.index('--model') + 1], 'gpt-6.1-terra')
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn('sandbox_workspace_write.network_access=false', command)
        self.assertIn(BODY, launch.call_args.kwargs['input'])

    def test_unrelated_tasks_and_quota_keep_model_and_limit(self):
        r = self.fixture()
        for repo, issue, n in ((REPO, 127, 11), (REPO, 125, 10), ('other/repo', 127, 10)):
            r.args.github_repo, r.args.issue = repo, issue
            self.assertFalse(r.is_correction_127(n))
        probe = worker.quota_probe_command(Path('repo'))
        self.assertEqual(probe[probe.index('--model') + 1], 'gpt-6.1-sol')

