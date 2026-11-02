"""The extra #127 slot uses the normal reservation and claim path. No real worker."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from automation import github_worker as worker
from test_github_worker import FakeRunner


REPO = 'kolorifer/radarr-festival-list'
SNAPSHOT = '66925204ee394f632ed6ef1991f034c729127f2aec1fe91bb91c537b536168df'
LAUNCHER = 'b463a2bae25c0efd7c77ea9911be87fb3993efa1'
BODY = (Path(__file__).parent / 'automation/authorizations/issue-127-task-9.txt').read_text().removesuffix('\n')


class CorrectionRunner(FakeRunner):
    def __init__(self, root):
        super().__init__(root, issue=127, github_repo=REPO)
        self.origin = f'https://github.com/{REPO}.git'
        self.issue = dict(number=127, user={'login': 'kolorifer'}, state='open',
                          url=f'https://api.github.com/repos/{REPO}/issues/127', body='')
        self.messages = [dict(id=7000000000, user=self.issue['user'], issue_url=self.issue['url'],
                              created_at='2026-11-08T10:00:00Z', updated_at='2026-11-08T10:00:00Z', body=BODY)]
        self.refs = [dict(ref=f'refs/heads/automation/issue-127-claim-{i}', object={'sha': LAUNCHER})
                     for i in range(1, 9)]
        self.checkout = self.state_dir / 'checkout'
        self.checkout.mkdir(exist_ok=True)
        if not self.state_file.exists():
            self.state.update(consumed=list(range(1, 9)), retained=dict(task=8, state='NEEDS_USER',
                              snapshot=SNAPSHOT, checkout=str(self.checkout.resolve())))
            worker.save(self.state_file, self.state)

    def git(self, *args):
        if args == ('branch', '--show-current'):
            return 'automation/launcher-coordinator-runtime-122'
        if args[:1] == ('-C',) and args == ('-C', str(self.checkout), 'branch', '--show-current'):
            return self.branch
        return super().git(*args)

    def api(self, endpoint, **data):
        if endpoint == f'repos/{REPO}/issues/127':
            return copy.deepcopy(self.issue)
        if endpoint == f'repos/{REPO}/git/refs':
            assert json.loads(self.state_file.read_text())['consumed'] == list(range(1, 10))
            assert data['ref'] == 'refs/heads/automation/issue-127-claim-9'
        return super().api(endpoint, **data)


class CorrectionTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return CorrectionRunner(Path(tmp.name).resolve())

    def test_only_exact_continuation_runs_once_and_restart_is_inert(self):
        r = self.fixture()
        original_refs = copy.deepcopy(r.refs)
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT), patch.object(r, 'refresh_quota', return_value=80):
            r.start()
        self.assertEqual(r.state['consumed'], list(range(1, 10)))
        self.assertEqual(r.refs[:8], original_refs)
        self.assertEqual([v for v in r.calls if v[0] == 'execute'], [('execute', 9)])
        restarted = CorrectionRunner(r.repo)
        restarted.refs = r.refs
        restarted.start()
        self.assertFalse(any(v[0] == 'execute' for v in restarted.calls))

    def test_ninth_slot_requires_all_prior_history_and_exact_owner_comment(self):
        changes = {
            'missing local claim': lambda r: r.state['consumed'].pop(),
            'missing remote claim': lambda r: r.refs.pop(),
            'divergent remote claim': lambda r: r.refs[0]['object'].update(sha='0'*40),
            'misnamed remote claim': lambda r: r.refs[0].update(ref='refs/heads/automation/issue-127-claim-extra-1'),
            'different snapshot': lambda r: r.state['retained'].update(snapshot='0'*64),
            'wrong previous state': lambda r: r.state['retained'].update(state='FAILED'),
            'wrong checkout': lambda r: r.state['retained'].update(checkout=str(r.repo)),
            'missing checkout': lambda r: r.checkout.rmdir(),
            'different task scope': lambda r: r.messages[0].update(body=BODY+'\nMore work'),
            'broader capability': lambda r: r.messages[0].update(body=BODY.replace('NETWORK_ACCESS: disabled','NETWORK_ACCESS: enabled')),
            'stale comment': lambda r: r.messages[0].update(id=6579481611),
            'edited comment': lambda r: r.messages[0].update(updated_at='2026-11-08T10:00:01Z'),
            'wrong issue URL': lambda r: r.messages[0].update(issue_url=r.issue['url']+'0'),
            'different owner': lambda r: r.messages[0].update(user={'login':'other'}),
            'tenth task': lambda r: r.messages[0].update(body=BODY.replace('SUPERVISOR_TASK: 9','SUPERVISOR_TASK: 10')),
        }
        for label, change in changes.items():
            with self.subTest(label=label):
                r = self.fixture()
                change(r)
                self.assertIsNone(r.eligible(r.issue, 'kolorifer'))
                self.assertFalse(any(v[0] == 'execute' for v in r.calls))

    def test_lost_history_does_not_make_task_nine_a_normal_assignment(self):
        r = self.fixture()
        r.refs.pop()
        r.state['consumed'].pop()
        self.assertIsNone(r.eligible(r.issue, 'kolorifer'))

    def test_normal_execute_never_recreates_a_missing_retained_checkout_for_nine(self):
        r = self.fixture()
        r.checkout.rmdir()
        r.state['consumed'].append(9)
        with self.assertRaisesRegex(worker.Stop, 'original retained checkout'):
            worker.Runner.execute(r, r.issue, r.messages[0], 9)
        self.assertFalse(r.checkout.exists())

    def test_normal_execute_refuses_changed_bytes_after_the_claim(self):
        r = self.fixture()
        r.state['consumed'].append(9)
        with patch.object(worker, 'snapshot', return_value='0'*64):
            with self.assertRaisesRegex(worker.Stop, 'immediately preceding retained state'):
                worker.Runner.execute(r, r.issue, r.messages[0], 9)

    def test_changed_final_baseline_never_marks_child_running_or_launches(self):
        r = self.fixture()
        r.state['consumed'].append(9)
        worker.save(r.state_file, r.state)
        r.repo = r.checkout
        task = r.messages[0]
        # The retained checks see the approved snapshot. The separate final
        # sample sees different bytes before any child is allowed to start.
        with patch.object(worker, 'snapshot', side_effect=[SNAPSHOT, SNAPSHOT, '0'*64]), \
                patch.object(worker.subprocess, 'run') as launch:
            with self.assertRaisesRegex(worker.Stop, 'Correction checkout changed before child execution'):
                worker.Runner.execute_in_checkout(r, r.issue, task, 9)
        launch.assert_not_called()
        self.assertFalse((r.state_dir / 'worker-9.log').exists())
        outcome = json.loads((r.state_dir / 'execution-9.json').read_bytes())
        self.assertNotEqual(outcome['child_process'], 'running')
        self.assertEqual(json.loads(r.state_file.read_bytes())['consumed'], list(range(1, 10)))

    def test_quota_pause_does_not_consume_and_lost_claim_is_never_replayed(self):
        r = self.fixture()
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT), patch.object(r, 'refresh_quota', return_value=15):
            r.start()
        self.assertEqual(r.state['consumed'], list(range(1, 9)))
        r.claim_error = True
        with patch.object(worker, 'snapshot', return_value=SNAPSHOT), patch.object(r, 'refresh_quota', return_value=80):
            r.start()
        self.assertEqual(r.state['consumed'], list(range(1, 10)))
        self.assertTrue((r.state_dir/'claim-failure-9.json').is_file())
        r.start()
        self.assertFalse(any(v[0]=='execute' for v in r.calls))

    def test_owner_supersession_and_changed_bytes_before_reservation_stop(self):
        for kind in ('owner','bytes'):
            with self.subTest(kind=kind):
                r = self.fixture()
                def check_quota():
                    if kind=='owner':
                        r.messages.append(dict(r.messages[0], id=7000000001,body='STATE: DONE'))
                    return 80
                with patch.object(r,'refresh_quota',side_effect=check_quota), patch.object(worker,'snapshot',
                        side_effect=[SNAPSHOT, '0'*64] if kind=='bytes' else [SNAPSHOT]):
                    with self.assertRaises(worker.Stop):
                        r.start()
                self.assertEqual(r.state['consumed'],list(range(1,9)))
                self.assertEqual(len(r.refs),8)

    def test_no_exception_for_other_issues_or_repositories(self):
        for repo, n in ((REPO,119),(REPO,122),(REPO,125),(REPO,86),('another/project',127)):
            with self.subTest(repo=repo,n=n):
                r=self.fixture()
                r.args.github_repo, r.args.issue=repo,n
                self.assertIsNone(r.eligible(dict(r.issue,number=n), 'kolorifer'))
