"""Operations publication boundaries with separate synthetic launcher/issue Git.

No live GitHub, Codex, service, SSH, private repository or media access.
"""
import json
from pathlib import Path
import subprocess
import unittest

from automation import github_worker as w
from automation import supervisor_policy as p
from automation.terminal_receipt import validate_receipt
import test_supervisor_communication as fixtures
from test_github_worker import TASK, ISSUE, comment


MODE = 'PUBLICATION_MODE: operations_only\n'


class ModeTests(unittest.TestCase):
    def test_strict_values_and_defaults(self):
        for suffix, expected in [('', 'code'), ('PUBLICATION_MODE: code\n', 'code'),
                                 (MODE, 'operations_only')]:
            task = w.choose_task([comment(TASK + suffix)], 'owner', set())
            self.assertEqual(p.publication_mode(task, 'owner'), expected)
        for line in ('PUBLICATION_MODE: unknown', 'PUBLICATION_MODE:',
                     'PUBLICATION_MODE:operations_only', ' PUBLICATION_MODE: operations_only',
                     'PUBLICATION_MODE : operations_only', 'publication_mode: operations_only',
                     'PUBLICATION_MODE:\toperations_only', 'PUBLICATION_MODE: operations_only ',
                     'PUBLICATION_MODE: "operations_only"', 'PUBLICATION_MODE: operations_only # comment',
                     'PUBLICATION_MODE:\noperations_only', MODE + MODE,
                     MODE + 'PUBLICATION_MODE: code', MODE + 'publication_mode: operations_only'):
            with self.subTest(line=line), self.assertRaises(p.PolicyError):
                w.choose_task([comment(TASK + line)], 'owner', set())

    def test_latest_owner_only_no_prose_or_issue_inference_or_fallback(self):
        self.assertIsNone(w.choose_task([comment(TASK + MODE, login='stranger')], 'owner', set()))
        with self.assertRaises(p.PolicyError):
            p.publication_mode(comment(TASK + MODE, login='stranger'), 'owner')
        newer = TASK.replace('TASK: 1', 'TASK: 2')
        selected = w.choose_task([comment(TASK + MODE), comment(newer, 2),
                                  comment(TASK + MODE, 3, 'stranger')], 'owner', set())
        self.assertEqual(p.publication_mode(selected, 'owner'), 'code')
        prose = TASK + 'The operations_only deployment has no diff and is complete.\n'
        self.assertEqual(p.publication_mode(comment(prose), 'owner'), 'code')
        self.assertIsNone(w.choose_task([comment(TASK + MODE)], 'owner', {1}))
        # Malformed latest trusted mode cannot fall back to an older valid task.
        with self.assertRaises(w.Stop):
            w.choose_task([comment(TASK + MODE), comment(newer + 'PUBLICATION_MODE: typo', 2)], 'owner', set())

    def test_mode_grants_no_access_or_staging(self):
        task = comment(TASK + MODE)
        self.assertEqual(w.capabilities(task, 'owner'), (False, 'none'))
        self.assertEqual(p.private_inputs(task['body']), [])
        self.assertIsNone(p.private_artifact(task['body']))
        self.assertIsNone(p.private_diagnostic(task['body']))


class OperationsTests(unittest.TestCase):
    # Reuse the synthetic transport and assertions without rediscovering its tests.
    clean_staging = staticmethod(fixtures.IntegrationTests.clean_staging)
    run_task = fixtures.IntegrationTests.run_task
    assert_no_leak = fixtures.IntegrationTests.assert_no_leak
    receipt = fixtures.IntegrationTests.receipt

    def setUp(self):
        fixtures.IntegrationTests.setUp(self)
        fixtures.IntegrationTests.separate_launcher(self)
        self.runner.body = TASK + MODE
        self.code_task = False
        self.existing_pr = False
        git, gh = self.runner.git, self.runner.gh

        def guarded_git(*args):
            self.runner.events.append(('parent-git', args))
            if args[0] in ('add', 'commit', 'push', 'merge'):
                self.assertTrue(self.code_task, 'Forbidden parent code command: ' + args[0])
            if args[0] == 'push':
                self.runner.events.append(('git-public', args))
                return ''  # Never contact a remote, including in code-default test.
            return git(*args)

        def guarded_gh(*args):
            if args[0] == 'pr':
                self.runner.events.append(('parent-pr', args))
                self.assertTrue(self.code_task, 'Forbidden PR command: ' + args[1])
                if args[1] == 'list':
                    return json.dumps([{'url': 'https://example.invalid/pr/1'}] if self.existing_pr else [])
                return 'https://example.invalid/pr/1'
            return gh(*args)

        self.runner.git, self.runner.gh = guarded_git, guarded_gh

    def outcome(self, n=1):
        return json.loads((self.runner.state_dir/f'execution-{n}.json').read_text())

    def terminal(self, n=1):
        return json.loads((self.runner.state_dir/f'terminal-{n}.json').read_text())

    def assert_operations(self, code='OK', child='exited'):
        public = self.assert_no_leak()
        self.assertIn('PR: none', public)
        self.assertIn('REASON_CODE: ' + code, public)
        self.assertIn('operations-only code publication disabled; external state not verified', public)
        self.assertNotIn('Parent diff checks passed', public)
        self.assertFalse(any(k == 'parent-pr' for k, v in self.runner.events))
        outcome = self.outcome()
        self.assertEqual(outcome['publication_mode'], 'operations_only')
        self.assertEqual(outcome['child_process'], child)
        self.assertEqual(outcome['code_publication'], 'disabled')
        self.assertEqual(outcome['public_result'], 'posted')
        self.assertEqual(self.runner.repo, self.root)
        self.assertEqual(self.runner.git('branch', '--show-current').strip(), 'main')
        self.assertEqual(self.runner.git('status', '--porcelain').strip(), '')
        return public

    def child_edit(self, edit):
        original = self.runner.child

        def child(command, **kwargs):
            if command[0] == 'codex':
                self.assertIn('do not edit or reconcile this public checkout', kwargs['input'])
                edit(self.runner.repo)
            return original(command, **kwargs)
        self.runner.child = child

    def local_git(self, checkout, *args):
        return self.runner.real_run(['git', *args], cwd=checkout, check=True,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def test_success_skips_all_code_publication_and_claims_only_parent_checks(self):
        self.run_task()
        public = self.assert_operations()
        self.assertIn('STATE: READY_FOR_REVIEW', public)
        self.assertIn('TESTS: Parent checkout fingerprint unchanged', public)
        self.assertEqual(self.runner.remote_files, {})
        self.assertEqual(self.outcome()['worker_state'], 'READY_FOR_REVIEW')
        self.assertTrue(self.outcome()['checkout_unchanged'])
        self.assertEqual(self.outcome()['checkout_baseline'], p.snapshot(self.runner.state_dir/'checkout'))
        self.assertEqual(self.terminal()['schema_version'], 1)
        self.assertNotIn('staging', self.runner.state)

    def test_existing_branch_with_earlier_commits_and_remote_ref_still_skips(self):
        checkout = self.runner.state_dir/'checkout'
        self.runner.git('worktree', 'add', str(checkout), self.runner.branch)
        self.runner.git('update-ref', 'refs/remotes/origin/'+self.runner.branch,
                        self.local_git(checkout, 'rev-parse', 'HEAD').strip())
        (checkout/'earlier.txt').write_text('earlier synthetic commit')
        self.local_git(checkout, 'add', 'earlier.txt')
        self.local_git(checkout, 'commit', '-m', 'Earlier task')
        before = p.snapshot(checkout)
        self.run_task()
        self.assert_operations()
        self.assertEqual(p.snapshot(checkout), before)
        self.assertTrue(any(k == 'parent-git' and v[0] == 'merge-base' for k, v in self.runner.events))

    def test_remote_advancement_is_refused_without_merging_or_child(self):
        checkout = self.runner.state_dir/'checkout'
        self.runner.git('worktree', 'add', str(checkout), self.runner.branch)
        before = p.snapshot(checkout)
        self.runner.git('update-ref', 'refs/remotes/origin/'+self.runner.branch,
                        self.runner.git('rev-parse', 'HEAD').strip())
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        self.assert_operations('CHECKOUT_FAILED', 'not_started')
        self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(p.snapshot(checkout), before)

    def test_deliberate_blocked_preserves_reporting(self):
        self.runner.child_mode = 'NEEDS_USER'
        self.run_task()
        self.assertIn('STATE: NEEDS_USER', self.assert_operations('WORKER_BLOCKED'))
        self.assertEqual(self.outcome()['worker_state'], 'NEEDS_USER')
        self.assertEqual(self.runner.state['retained']['state'], 'NEEDS_USER')

    def test_genuine_child_failure_preserves_reporting(self):
        self.runner.child_mode = 'FAILED'
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        self.assertIn('STATE: FAILED', self.assert_operations('CHILD_FAILED', 'failed'))
        self.assertIsNone(self.outcome()['worker_state'])
        self.assertTrue(self.outcome()['checkout_unchanged'])

    def test_invalid_worker_result_remains_distinct(self):
        self.runner.invalid_result = '{}'
        with self.assertRaises(w.Stop): self.run_task()
        self.assert_operations('INVALID_RESULT')
        self.assertIsNone(self.outcome()['worker_state'])

    def check_checkout_refusal(self, failed=False):
        if failed:
            self.runner.child_mode = 'FAILED'
        with self.assertRaises(w.Stop): self.run_task()
        self.assert_operations('PUBLIC_CHANGE_REFUSED', 'failed' if failed else 'exited')
        self.assertFalse(self.outcome()['checkout_unchanged'])
        self.assertFalse(self.terminal()['verification']['public_checkout_unchanged'])
        checkout = self.runner.state_dir/'checkout'
        self.assertEqual(self.runner.state['retained']['snapshot'], p.snapshot(checkout))
        self.assertTrue((self.runner.state_dir/'retained-1.tar').exists())
        self.assertEqual(self.runner.remote_files, {})
        return checkout

    def test_tracked_change_refused_and_preserved(self):
        self.child_edit(lambda repo: (repo/'base.txt').write_text('changed tracked bytes'))
        checkout = self.check_checkout_refusal()
        self.assertEqual((checkout/'base.txt').read_text(), 'changed tracked bytes')

    def test_untracked_change_refused_even_after_child_failure(self):
        self.runner.public_change = 'file'
        checkout = self.check_checkout_refusal(failed=True)
        self.assertEqual((checkout/'leak.txt').read_bytes(), fixtures.CANARY)

    def test_index_only_change_refused_and_preserved(self):
        def edit(repo):
            (repo/'base.txt').write_text('staged only')
            self.local_git(repo, 'add', 'base.txt')
            (repo/'base.txt').write_text('synthetic base')
        self.child_edit(edit)
        checkout = self.check_checkout_refusal()
        self.assertIn('staged only', self.local_git(checkout, 'diff', '--cached'))
        self.assertEqual((checkout/'base.txt').read_text(), 'synthetic base')

    def test_head_change_refused_and_preserved(self):
        self.runner.public_change = 'history'
        checkout = self.check_checkout_refusal()
        self.assertIn('synthetic child commit', self.local_git(checkout, 'log', '-1', '--oneline'))

    def test_branch_only_change_refused_and_preserved(self):
        self.child_edit(lambda repo: self.local_git(repo, 'switch', '-c', 'synthetic-other'))
        checkout = self.check_checkout_refusal()
        self.assertEqual(self.local_git(checkout, 'branch', '--show-current').strip(), 'synthetic-other')

    def test_detached_head_refused_with_usable_retained_snapshot(self):
        self.child_edit(lambda repo: self.local_git(repo, 'switch', '--detach'))
        checkout = self.check_checkout_refusal()
        self.assertEqual(self.local_git(checkout, 'branch', '--show-current').strip(), '')

    def test_tracked_deletion_refused_and_preserved(self):
        self.child_edit(lambda repo: (repo/'base.txt').unlink())
        checkout = self.check_checkout_refusal()
        self.assertFalse((checkout/'base.txt').exists())

    def check_retained_baseline(self, private=False):
        checkout = self.runner.state_dir/'checkout'
        self.runner.git('worktree', 'add', str(checkout), self.runner.branch)
        (checkout/'base.txt').write_text('retained index')
        self.local_git(checkout, 'add', 'base.txt')
        (checkout/'base.txt').write_text('retained worktree')
        (checkout/'retained.txt').write_text('retained untracked')
        self.runner.state['consumed'] = [1]
        baseline = self.runner.record_retained(1, 'NEEDS_USER', checkout)
        backup = (self.runner.state_dir/'retained-1.tar').read_bytes()
        body = fixtures.task_body([fixtures.INPUT]) if private else TASK
        self.runner.body = body.replace('TASK: 1', 'TASK: 2') + MODE + 'CONTINUE_FROM: ' + json.dumps(
            {'task': 1, 'snapshot': baseline})
        self.run_task()
        self.assertEqual(self.runner.child_count, 1)
        self.assertEqual(p.snapshot(checkout), baseline)
        self.assertEqual(self.outcome(2)['checkout_baseline'], baseline)
        self.assertTrue(self.outcome(2)['checkout_unchanged'])
        self.assertEqual(self.outcome(2)['worker_state'], 'READY_FOR_REVIEW')
        self.assertEqual(self.outcome(2)['terminal_state'], 'READY_FOR_REVIEW')
        self.assertEqual((self.runner.state_dir/'retained-1.tar').read_bytes(), backup)
        self.assertIn('PR: none', self.assert_no_leak())
        self.assertEqual(self.local_git(checkout, 'stash', 'list'), '')

    def test_exact_preexisting_retained_baseline_accepted_unchanged(self):
        self.check_retained_baseline()

    def test_private_operations_exact_retained_baseline_accepted_without_reconciliation(self):
        self.check_retained_baseline(private=True)
        self.assertTrue(self.receipt()['verification']['public_checkout_unchanged'])
        self.assertTrue(self.receipt()['verification']['artifact_readback'])

    def test_new_dirt_before_child_is_never_promoted_to_baseline(self):
        original = self.runner.verify_inputs
        def verify():
            original()
            if self.runner.repo != self.root:
                (self.runner.repo/'unexpected.txt').write_text('pre-child drift')
        self.runner.verify_inputs = verify
        with self.assertRaises(w.Stop): self.run_task()
        self.assert_operations('PUBLIC_CHANGE_REFUSED', 'not_started')
        self.assertEqual(self.runner.child_count, 0)
        self.assertIsNone(self.outcome()['checkout_baseline'])
        self.assertEqual((self.runner.state_dir/'checkout'/'unexpected.txt').read_text(), 'pre-child drift')

    def test_clean_head_drift_before_child_is_never_promoted_to_baseline(self):
        original = self.runner.verify_inputs
        def verify():
            original()
            if self.runner.repo != self.root:
                self.local_git(self.runner.repo, 'commit', '--allow-empty', '-m', 'Pre-child drift')
        self.runner.verify_inputs = verify
        with self.assertRaises(w.Stop): self.run_task()
        self.assert_operations('PUBLIC_CHANGE_REFUSED', 'not_started')
        self.assertEqual(self.runner.child_count, 0)
        self.assertIsNone(self.outcome()['checkout_baseline'])

    def test_ignored_cache_is_outside_fingerprint_contract(self):
        common = Path(self.runner.git('rev-parse', '--git-common-dir').strip())
        if not common.is_absolute():
            common = self.root/common
        with (common/'info'/'exclude').open('a') as stream:
            stream.write('\nsynthetic-cache/\n')
        def cache(repo):
            (repo/'synthetic-cache').mkdir()
            (repo/'synthetic-cache'/'cache.txt').write_text('ignored cache')
        self.child_edit(cache)
        self.run_task()
        self.assert_operations()
        self.assertTrue(self.outcome()['checkout_unchanged'])
        self.assertTrue((self.runner.state_dir/'checkout'/'synthetic-cache'/'cache.txt').exists())

    def test_malformed_mode_stops_before_claim_child_or_private_writes(self):
        self.runner.body = TASK + 'PUBLICATION_MODE: unknown\n'
        self.run_task()
        self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.runner.state['consumed'], [])
        self.assertFalse(any(k == 'api' and v.endswith('/git/refs') for k, v in self.runner.events))
        self.assertEqual(self.runner.remote_files, {})
        self.assertIn('REASON_CODE: INVALID_TASK', self.assert_no_leak())

    def test_issue_body_and_other_comment_do_not_enable_mode(self):
        selected = comment(TASK)
        self.runner.body = selected['body']
        prompt = w.prompt_for(dict(ISSUE, body=MODE), selected, self.root, '', self.runner.branch)
        self.assertIn('PUBLICATION_MODE: code. This controls parent publication only', prompt)
        self.assertEqual(p.publication_mode(selected, 'owner'), 'code')

    def test_changed_retained_state_is_refused_before_claim_or_child(self):
        checkout = self.runner.state_dir/'checkout'
        self.runner.git('worktree', 'add', str(checkout), self.runner.branch)
        (checkout/'retained.txt').write_text('retained')
        self.runner.state['consumed'] = [1]
        baseline = self.runner.record_retained(1, 'FAILED', checkout)
        self.runner.body = TASK.replace('TASK: 1', 'TASK: 2') + MODE + 'CONTINUE_FROM: ' + json.dumps(
            {'task': 1, 'snapshot': baseline})
        (checkout/'retained.txt').write_text('changed after capture')
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.runner.state['consumed'], [1])
        self.assertEqual((checkout/'retained.txt').read_text(), 'changed after capture')

    def test_private_operations_keep_canaries_and_artifact_receipt_order(self):
        self.runner.body = fixtures.task_body([fixtures.INPUT]) + MODE
        self.runner.external_child = True
        self.run_task()
        self.assert_operations()
        receipt = validate_receipt(self.receipt())
        self.assertTrue(all(receipt['verification'].values()))
        self.assertEqual(self.runner.remote_files[fixtures.AUTH['path']], fixtures.CANARY+b' processed')
        events = self.runner.events
        artifact = events.index(('write', fixtures.AUTH['path']))
        diagnostic = events.index(('write', fixtures.DIAGNOSTIC['path']))
        public = next(i for i, (k, v) in enumerate(events) if k == 'post' and 'WORKER_RESULT' in v)
        self.assertLess(artifact, diagnostic)
        self.assertLess(diagnostic, public)
        self.assertTrue(any(k == 'read' for k, v in events[artifact+1:diagnostic]))
        self.assertTrue(any(k == 'read' for k, v in events[diagnostic+1:public]))

    def test_private_input_change_still_refused(self):
        self.runner.body = fixtures.task_body([fixtures.INPUT]) + MODE
        self.runner.mutate_input = True
        with self.assertRaises(w.Stop): self.run_task()
        self.assert_operations('INPUT_CHANGED')
        self.assertNotIn(fixtures.AUTH['path'], self.runner.remote_files)

    def test_diagnostic_alone_does_not_authorize_an_artifact(self):
        self.runner.body = fixtures.task_body(artifact=False) + MODE
        self.run_task()
        self.assert_operations()
        self.assertEqual(set(self.runner.remote_files), {fixtures.DIAGNOSTIC['path']})
        self.assertEqual(self.receipt()['artifacts'], [])

    def test_artifact_readback_failure_records_completed_child(self):
        self.runner.body = fixtures.task_body([fixtures.INPUT]) + MODE
        self.runner.corrupt_readback = fixtures.AUTH['path']
        with self.assertRaises(w.Stop): self.run_task()
        self.assert_operations('ARTIFACT_PUBLICATION_FAILED')
        self.assertEqual(self.outcome()['worker_state'], 'READY_FOR_REVIEW')
        self.assertFalse(self.receipt()['verification']['artifact_readback'])

    def test_receipt_readback_failure_keeps_execution_and_delivery_distinct(self):
        self.runner.body = fixtures.task_body([fixtures.INPUT]) + MODE
        self.runner.corrupt_readback = fixtures.DIAGNOSTIC['path']
        self.run_task()
        self.assert_operations('RECEIPT_PUBLICATION_FAILED')
        self.assertEqual(self.outcome()['worker_state'], 'READY_FOR_REVIEW')
        self.assertEqual(self.outcome()['receipt'], 'unavailable')
        self.assertEqual(self.outcome()['terminal_state'], 'FAILED')
        self.assertEqual(self.runner.events.count(('write', fixtures.DIAGNOSTIC['path'])), 1)
        self.run_task()
        self.assertEqual(self.runner.child_count, 1)

    def test_public_result_failure_never_reexecutes_or_rewrites_receipt(self):
        self.runner.body = fixtures.task_body([fixtures.INPUT]) + MODE
        self.runner.fail_result = True
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        self.assertEqual(self.outcome()['child_process'], 'exited')
        self.assertEqual(self.outcome()['worker_state'], 'READY_FOR_REVIEW')
        self.assertEqual(self.outcome()['receipt'], 'verified')
        self.assertEqual(self.outcome()['public_result'], 'unconfirmed')
        self.assertEqual(self.outcome()['terminal_code'], 'RESULT_PUBLICATION_FAILED')
        before = (self.runner.state_dir/'execution-1.json').read_bytes()
        receipt = self.runner.remote_files[fixtures.DIAGNOSTIC['path']]
        self.runner.fail_result = False
        self.run_task()
        self.assertEqual(self.runner.child_count, 1)
        self.assertEqual(self.runner.remote_files[fixtures.DIAGNOSTIC['path']], receipt)
        self.assertEqual((self.runner.state_dir/'execution-1.json').read_bytes(), before)
        self.assert_no_leak()

    def test_default_code_task_still_commits_pushes_and_creates_pr(self):
        self.code_task = True
        self.runner.body = TASK
        self.runner.public_change = 'file'
        self.run_task()
        git_commands = [v[0] for k, v in self.runner.events if k == 'git-public']
        self.assertEqual(git_commands, ['add', 'commit', 'push'])
        self.assertEqual([v[1] for k, v in self.runner.events if k == 'parent-pr'], ['list', 'create'])
        self.assertEqual(self.outcome()['code_publication'], 'completed')
        self.assertFalse(self.outcome()['checkout_unchanged'])
        self.assertEqual(self.outcome()['publication_mode'], 'code')
        self.assertEqual(self.local_git(self.runner.state_dir/'checkout', 'status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
