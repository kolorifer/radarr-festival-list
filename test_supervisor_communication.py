"""Synthetic host/child integration. Never calls gh, Codex or external services."""
import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from automation import github_worker as w
from automation import supervisor_policy as p
from automation.terminal_receipt import validate_receipt
from test_github_worker import TASK, ISSUE, comment
from test_supervisor_policy import AUTH, item


CANARY = b'SYNTHETIC_PRIVATE_INPUT_IDENTITY_EVIDENCE'
DIAGNOSTIC = {'repository': p.PRIVATE_REPOSITORY, 'path': 'operations/synthetic-terminal.json',
              'expected_blob': 'absent'}


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


INPUT = {'repository': p.PRIVATE_REPOSITORY, 'path': 'fixtures/synthetic.txt',
         'commit': 'c'*40, 'blob': blob(CANARY), 'sha256': hashlib.sha256(CANARY).hexdigest(),
         'alias': 'input.txt'}


def task_body(inputs=None, artifact=True, diagnostic=True):
    body = TASK
    if inputs is not None:
        body += 'PRIVATE_INPUTS: ' + json.dumps({'inputs': inputs}) + '\n'
    if artifact:
        body += 'PRIVATE_ARTIFACT: ' + json.dumps(AUTH) + '\n'
    if diagnostic:
        body += 'PRIVATE_DIAGNOSTIC: ' + json.dumps(DIAGNOSTIC) + '\n'
    return body


class CapabilityTests(unittest.TestCase):
    def test_exact_owner_only_and_latest_only(self):
        body = task_body([INPUT])
        self.assertEqual(p.private_inputs(body), [INPUT])
        self.assertEqual(p.private_diagnostic(body), DIAGNOSTIC)
        self.assertIsNone(w.choose_task([comment(body, login='stranger')], 'owner', set()))
        selected = w.choose_task([comment(body), comment(TASK.replace('TASK: 1', 'TASK: 2'), 2),
                                  comment(body, 3, 'stranger')], 'owner', set())
        self.assertEqual(p.private_inputs(selected['body']), [])
        self.assertIsNone(p.private_diagnostic(selected['body']))

    def test_unpinned_malformed_paths_aliases_and_repositories_refused(self):
        for key, value in [('repository', 'other/private'), ('path', '../x.txt'),
                           ('path', '/x.txt'), ('path', 'fixtures//x.txt'), ('path', 'fixtures/./x.txt'),
                           ('path', 'fixtures/*.txt'), ('path', 'fixtures/x?ref=main'),
                           ('path', '.git/config'), ('commit', 'main'), ('commit', 'c'*7),
                           ('blob', 'absent'), ('sha256', 'x'*64), ('alias', '../input.txt'),
                           ('alias', '/input.txt'), ('alias', 'input/one.txt'), ('alias', '.env')]:
            with self.subTest(key=key, value=value), self.assertRaises(p.PolicyError):
                w.choose_task([comment(task_body([dict(INPUT, **{key: value})]))], 'owner', set())
        for inputs in ([], [INPUT]*2, [INPUT]*9,
                       [INPUT, dict(INPUT, path='fixtures/other.txt')],
                       [INPUT, dict(INPUT, alias='other.txt')], [dict(INPUT, extra='ignored')]):
            with self.subTest(inputs=inputs), self.assertRaises(p.PolicyError):
                p.private_inputs(task_body(inputs))

    def test_duplicate_json_keys_and_directives_rejected(self):
        for name, value in [('PRIVATE_INPUTS', {'inputs': [INPUT]}), ('PRIVATE_DIAGNOSTIC', DIAGNOSTIC),
                            ('PRIVATE_ARTIFACT', AUTH)]:
            line = name + ': ' + json.dumps(value)
            for body in (line+'\n'+line, ' '+line, line.lower(),
                         line.replace('"repository":', '"repository":"other/private","repository":')):
                with self.subTest(body=body), self.assertRaises(p.PolicyError):
                    w.choose_task([comment(TASK+body)], 'owner', set())

    def test_diagnostic_cannot_infer_adjacent_output_authorization(self):
        for change in ({'path': AUTH['path']}, {'path': 'operations/*.json'},
                       {'path': 'operations/../x.json'}, {'path': 'operations/x.md'},
                       {'repository': 'other/private'}, {'expected_blob': 'main'},
                       {'source': 'receipt.json'}):
            value = dict(DIAGNOSTIC, **change)
            with self.subTest(change=change), self.assertRaises(p.PolicyError):
                p.private_diagnostic(task_body(artifact=True, diagnostic=False)
                                     + 'PRIVATE_DIAGNOSTIC: ' + json.dumps(value))


class BoundaryRunner(w.Runner):
    """Real temporary Git checkout; exact synthetic GitHub responses and CAS."""
    def __init__(self, root):
        self.events = []
        self.body = task_body([INPUT])
        self.source = CANARY
        self.node_mode = '100644'
        self.node_size = len(CANARY)
        self.metadata = {'private': True, 'full_name': p.PRIVATE_REPOSITORY, 'default_branch': 'main'}
        self.remote_files = {}
        self.corrupt_readback = None
        self.fail_write = None
        self.fail_result = False
        self.fail_running = False
        self.fail_claim = False
        self.child_count = 0
        self.child_mode = 'READY_FOR_REVIEW'
        self.invalid_result = None
        self.mutate_input = False
        self.public_change = None
        self.external_child = False
        self.real_run = subprocess.run
        args = argparse.Namespace(repo=root, issue=11, github_repo='owner/project', base='main',
                                  sessions=root/'sessions', interval=10, once=True, dry_run=False)
        super().__init__(args)

    def git(self, *args):
        if args == ('fetch', 'origin'):
            return ''
        if args[0] in ('push', 'commit', 'add'):
            self.events.append(('git-public', args))
        return super().git(*args)

    def comments(self):
        return [comment(self.body)]

    def api(self, endpoint, **data):
        self.events.append(('api', endpoint))
        if endpoint == 'user':
            return {'login': 'owner'}
        if endpoint.endswith('/issues/11'):
            return ISSUE
        if '/matching-refs/' in endpoint:
            return []
        if endpoint.endswith('/git/refs'):
            assert int(data['ref'].rsplit('-', 1)[1]) in json.loads(self.state_file.read_text())['consumed']
            if self.inputs:
                assert self.verification['inputs_verified']
            if self.fail_claim:
                raise subprocess.CalledProcessError(1, ['fake'], stderr=CANARY.decode())
            return {}
        if endpoint == 'repos/'+p.PRIVATE_REPOSITORY:
            return self.metadata
        if '/git/commits/' in endpoint:
            return {'sha': INPUT['commit'], 'tree': {'sha': 'd'*40}}
        if '/git/trees/' in endpoint:
            sha = endpoint.rsplit('/', 1)[1]
            node = ({'path': 'fixtures', 'mode': '040000', 'type': 'tree', 'sha': 'e'*40}
                    if sha == 'd'*40 else {'path': 'synthetic.txt', 'mode': self.node_mode,
                                           'type': 'blob', 'sha': INPUT['blob'], 'size': self.node_size})
            return {'sha': sha, 'tree': [node], 'truncated': False}
        if '/contents/fixtures/' in endpoint:
            assert endpoint.endswith('?ref='+INPUT['commit'])
            return item(self.source, INPUT['blob'])
        raise AssertionError('Unexpected fake endpoint: '+endpoint)

    def gh(self, *args):
        assert args[0] == 'api'
        path = args[1].split('/contents/')[1].split('?')[0]
        self.events.append(('read', path))
        if path not in self.remote_files:
            raise subprocess.CalledProcessError(1, ['fake'], stderr='HTTP 404')
        data = self.remote_files[path]
        if self.corrupt_readback == path:
            data = b'synthetic corruption'
        return json.dumps(item(data, blob(data)))

    def run(self, command, **kwargs):
        if command[:2] != ['gh', 'api']:
            return super().run(command, **kwargs)
        assert '--method' in command and command[command.index('--method')+1] == 'PUT'
        path = command[2].split('/contents/')[1]
        self.events.append(('write', path))
        if path == DIAGNOSTIC['path']:
            # A crash during PUT must leave a conservative local delivery record.
            delivery = json.loads((self.state_dir/f'delivery-{self.claimed_task}.json').read_text())
            assert delivery['receipt'] == 'unavailable' and not delivery['public_result']
        if self.fail_write == path:
            raise subprocess.CalledProcessError(1, ['fake'], stderr=CANARY.decode())
        payload = json.loads(kwargs['input'])
        if path in self.remote_files:
            assert payload['sha'] == blob(self.remote_files[path])
        else:
            assert 'sha' not in payload
        self.remote_files[path] = base64.b64decode(payload['content'])
        return '{}'

    def post(self, body):
        self.events.append(('post', body))
        if (self.fail_result and 'WORKER_RESULT:' in body) or (self.fail_running and 'STATE: RUNNING' in body):
            raise subprocess.CalledProcessError(1, ['fake'], stderr=CANARY.decode())

    def child(self, command, **kwargs):
        if command[0] != 'codex':
            return self.real_run(command, **kwargs)
        self.events.append(('child', None)); self.child_count += 1
        assert 'sandbox_workspace_write.network_access=false' in command
        assert '--ignore-user-config' in command and '--ignore-rules' in command
        assert all(k not in kwargs['env'] for k in ('GH_TOKEN', 'GITHUB_TOKEN', 'SSH_AUTH_SOCK'))
        grants = [command[i+1] for i, value in enumerate(command) if value == '--add-dir']
        assert all(str(v['path'].parent) not in grants for v in self.inputs)
        for entry in self.inputs:
            assert str(entry['path']) in kwargs['input']
            assert stat.S_IMODE(entry['path'].stat().st_mode) == 0o400
            assert stat.S_IMODE(entry['path'].parent.stat().st_mode) == 0o500
        output = Path(command[command.index('--output-last-message')+1])
        staging = Path(grants[0]) if grants else None
        if self.external_child:
            # Actual isolated Python subprocess, fake Codex sandbox transport.
            # Network calls are forbidden in this fixture; no real gh/Codex used.
            script = '''import json,os,socket,sys
from pathlib import Path
def deny(*a, **k): raise RuntimeError("synthetic network disabled")
socket.socket = deny
assert all(k not in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN","SSH_AUTH_SOCK"))
source, dest, result = map(Path, sys.argv[1:])
dest.write_bytes(source.read_bytes() + b" processed")
result.write_text(json.dumps(dict(state="READY_FOR_REVIEW", tests="private", summary="private", questions="private")))
'''
            return self.real_run([sys.executable, '-c', script, str(self.inputs[0]['path']),
                                  str(staging/'artifact.md'), str(output)], cwd=self.repo,
                                 env=kwargs['env'], check=True, stdout=kwargs['stdout'], stderr=kwargs['stderr'])
        if staging:
            (staging/'artifact.md').write_bytes(CANARY+b' processed')
        if self.mutate_input:
            source = self.inputs[0]['path']; source.chmod(0o600); source.write_text('changed')
        if self.public_change == 'file':
            (self.repo/'leak.txt').write_bytes(CANARY)
        if self.public_change == 'history':
            self.real_run(['git', 'commit', '--allow-empty', '-m', 'synthetic child commit'],
                          cwd=self.repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if self.child_mode == 'FAILED':
            raise subprocess.CalledProcessError(1, ['fake-child'], stderr=CANARY.decode())
        result = dict(state=self.child_mode, tests=CANARY.decode(), summary=CANARY.decode(), questions=CANARY.decode())
        output.write_text(self.invalid_result if self.invalid_result is not None else json.dumps(result))
        return subprocess.CompletedProcess(command, 0)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        def git(*args):
            subprocess.run(['git', *args], cwd=self.root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git('init', '-b', 'automation/issue-11-worker')
        git('config', 'user.email', 'synthetic@example.invalid'); git('config', 'user.name', 'Synthetic')
        (self.root/'base.txt').write_text('synthetic base')
        git('add', '.'); git('commit', '-m', 'Synthetic base')
        git('remote', 'add', 'origin', 'https://github.com/owner/project.git')
        self.runner = BoundaryRunner(self.root)
        self.addCleanup(self.clean_staging, self.runner)

    @staticmethod
    def clean_staging(runner):
        for key in ('staging', 'input_staging'):
            for value in runner.state.get(key, {}).values():
                path = Path(value)
                if path.exists():
                    path.chmod(0o700)
                    shutil.rmtree(path)

    def run_task(self):
        with patch.object(w, 'quota_remaining', return_value=80), \
                patch.object(w.subprocess, 'run', side_effect=self.runner.child), \
                patch.dict(os.environ, GH_TOKEN='SYNTHETIC_HOST_TOKEN', GITHUB_TOKEN='SYNTHETIC_HOST_TOKEN',
                           SSH_AUTH_SOCK='/synthetic/socket'), contextlib.redirect_stdout(io.StringIO()) as stdout:
            try:
                self.runner.start()
            finally:
                self.assertNotIn(CANARY.decode(), stdout.getvalue())

    def receipt(self):
        return json.loads(self.runner.remote_files[DIAGNOSTIC['path']])

    def assert_no_leak(self):
        public = '\n'.join(v for k, v in self.runner.events if k == 'post')
        for value in (CANARY.decode(), INPUT['path'], INPUT['commit'], INPUT['sha256'],
                      DIAGNOSTIC['path'], AUTH['path'], str(self.root), 'SYNTHETIC_HOST_TOKEN'):
            self.assertNotIn(value, public)
        self.assertFalse(any(k == 'git-public' for k, v in self.runner.events))
        return public

    def separate_launcher(self):
        """Keep the issue branch older than main, as on a real host launcher."""
        git = self.runner.git
        git('branch', '-m', 'main')
        git('branch', self.runner.branch)
        (self.root/'launcher-only.txt').write_text('synthetic launcher revision')
        git('add', 'launcher-only.txt'); git('commit', '-m', 'Synthetic launcher')
        git('update-ref', 'refs/remotes/origin/main', git('rev-parse', 'HEAD').strip())
        self.runner.events.clear()

    def edit_child_checkout(self):
        original = self.runner.child
        def child(command, **kwargs):
            if command[0] == 'codex':
                checkout = self.runner.repo
                (checkout/'base.txt').write_text('synthetic staged bytes')
                self.runner.real_run(['git', 'add', 'base.txt'], cwd=checkout, check=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (checkout/'base.txt').write_text('synthetic unstaged bytes')
                (checkout/'partial.txt').write_text('synthetic untracked bytes')
            return original(command, **kwargs)
        self.runner.child = child

    def assert_issue_retention(self, expected_state, partial=False):
        runner = self.runner
        checkout = runner.state_dir/'checkout'
        self.assertEqual(runner.repo, self.root)
        self.assertEqual(runner.git('branch', '--show-current').strip(), 'main')
        self.assertEqual(runner.git('status', '--porcelain').strip(), '')
        retained = runner.state['retained']
        self.assertEqual(retained['checkout'], str(checkout))
        self.assertEqual(retained['state'], expected_state)
        self.assertEqual(retained['snapshot'], p.snapshot(checkout))
        self.assertNotEqual(retained['snapshot'], p.snapshot(self.root))
        self.assertEqual(json.loads(runner.state_file.read_text())['retained'], retained)
        with tarfile.open(runner.state_dir/'retained-1.tar') as backup:
            expected = set(runner.git('-C', str(checkout), 'ls-files', '-z').split('\0')) - {''}
            expected.update(runner.git('-C', str(checkout), 'ls-files', '--others', '--exclude-standard', '-z').split('\0'))
            expected.discard('')
            self.assertEqual(set(backup.getnames()), expected)
            self.assertNotIn('launcher-only.txt', backup.getnames())
            for name in expected:
                self.assertEqual(backup.extractfile(name).read(), (checkout/name).read_bytes())
        index_patch = (runner.state_dir/'retained-1-index.patch').read_text()
        self.assertEqual(index_patch, runner.git('-C', str(checkout), 'diff', '--cached', '--binary'))
        if partial:
            self.assertIn('+synthetic staged bytes', index_patch)
            self.assertEqual((checkout/'partial.txt').read_text(), 'synthetic untracked bytes')
        public = self.assert_no_leak()
        self.assertIn('RETAINED_SNAPSHOT: '+retained['snapshot'], public)
        self.assertEqual(runner.events.count(('write', DIAGNOSTIC['path'])), 1)
        follow = comment(TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 2') +
                         'CONTINUE_FROM: '+json.dumps({'task': 1, 'snapshot': retained['snapshot']}))
        self.assertTrue(runner.retained(follow, checkout))
        self.assertEqual(runner.git('stash', 'list'), '')
        return follow

    def test_separate_launcher_child_and_receipt_failure_preserve_exact_backup_and_continuation(self):
        self.separate_launcher()
        self.edit_child_checkout()
        self.runner.child_mode = 'FAILED'
        self.runner.fail_write = DIAGNOSTIC['path']
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(json.loads((self.runner.state_dir/'terminal-1.json').read_text())['code'],
                         'PUBLIC_CHANGE_REFUSED')
        self.assertEqual(json.loads((self.runner.state_dir/'execution-1.json').read_text())['child_process'],
                         'failed')
        follow = self.assert_issue_retention('FAILED', partial=True)
        checkout = self.runner.state_dir/'checkout'
        before = p.snapshot(checkout)
        backup = (self.runner.state_dir/'retained-1.tar').read_bytes()
        self.assertEqual(json.loads((self.runner.state_dir/'terminal-1.json').read_text())['retained_snapshot'], before)
        self.assertEqual(json.loads((self.runner.state_dir/'delivery-1.json').read_text())['code'],
                         'RECEIPT_PUBLICATION_FAILED')
        # Actually enter the next authorized child with the exact bytes/index;
        # do not stash, reset, or manufacture a clean continuation checkout.
        self.runner.body = follow['body']
        def next_child(command, **kwargs):
            if command[0] != 'codex':
                return self.runner.real_run(command, **kwargs)
            self.assertEqual(self.runner.repo, checkout)
            self.assertEqual(p.snapshot(checkout), before)
            self.runner.child_count += 1
            Path(command[command.index('--output-last-message')+1]).write_text(json.dumps(
                dict(state='NEEDS_USER', tests='', summary='', questions='')))
            return subprocess.CompletedProcess(command, 0)
        self.runner.child = next_child
        self.run_task()
        self.assertEqual(self.runner.child_count, 2)
        self.assertEqual(self.runner.state['consumed'], [1, 2])
        self.assertEqual((self.runner.state_dir/'retained-1.tar').read_bytes(), backup)
        self.assertEqual(p.snapshot(checkout), before)
        self.assertEqual(self.runner.git('stash', 'list'), '')

    def test_separate_launcher_ready_receipt_failure_retains_issue_checkout(self):
        self.separate_launcher()
        self.runner.fail_write = DIAGNOSTIC['path']
        self.run_task()
        self.assert_issue_retention('FAILED')
        self.assertIn('STATE: FAILED', self.assert_no_leak())

    def test_separate_launcher_blocked_receipt_failure_preserves_captured_retention(self):
        self.separate_launcher()
        self.runner.body = task_body(artifact=False)
        self.edit_child_checkout()
        self.runner.child_mode = 'NEEDS_USER'
        self.runner.fail_write = DIAGNOSTIC['path']
        self.run_task()
        # NEEDS_USER was already captured before receipt publication failed.
        self.assert_issue_retention('NEEDS_USER', partial=True)
        self.assertIn('STATE: FAILED', self.assert_no_leak())

    def test_checkout_creation_and_receipt_failure_never_snapshot_launcher(self):
        self.separate_launcher()
        real_git = self.runner.git
        def git(*args):
            if args[:2] == ('worktree', 'add'):
                raise subprocess.CalledProcessError(1, ['synthetic-checkout'], stderr=CANARY.decode())
            return real_git(*args)
        self.runner.git = git
        self.runner.fail_write = DIAGNOSTIC['path']
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.runner.repo, self.root)
        self.assertNotIn('retained', self.runner.state)
        self.assertFalse((self.runner.state_dir/'retained-1.tar').exists())
        self.assertFalse((self.runner.state_dir/'checkout').exists())
        receipt = json.loads((self.runner.state_dir/'terminal-1.json').read_text())
        self.assertEqual(receipt['code'], 'CHECKOUT_FAILED')
        self.assertIsNone(receipt['retained_snapshot'])
        self.assertIsNone(receipt['runtime']['checkout_revision'])
        self.assertNotIn('RETAINED_SNAPSHOT:', self.assert_no_leak())

    def test_terminal_requires_confirmed_ownership(self):
        with self.assertRaisesRegex(w.Stop, 'confirmed task ownership'):
            self.runner.terminal(comment(self.runner.body), 1, 'NEEDS_USER', 'CLAIM_FAILED')
        self.assertEqual(self.runner.events, [])
        self.assertEqual(self.runner.remote_files, {})

    def other_host(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        self.runner.real_run(['git', 'clone', '--no-local', str(self.root), str(root)],
                             check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.runner.real_run(['git', 'remote', 'set-url', 'origin', 'https://github.com/owner/project.git'],
                             cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        runner = BoundaryRunner(root)
        self.addCleanup(self.clean_staging, runner)
        runner.remote_files = self.runner.remote_files
        return runner

    def run_selection(self, runner, selection):
        runner.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with patch.object(w, 'quota_remaining', return_value=80), \
                patch.object(w.subprocess, 'run', side_effect=runner.child), \
                contextlib.redirect_stdout(io.StringIO()) as stdout, \
                w.lock(runner.dispatch_dir/'dispatcher.lock') as runner.global_lock_fd, \
                w.lock(runner.state_dir/'runner.lock') as runner.lock_fd:
            runner.run_selected(*selection)
        self.assertNotIn(CANARY.decode(), stdout.getvalue())

    def assert_unowned_consumed(self, runner):
        self.assertEqual(runner.child_count, 0)
        self.assertEqual(runner.state['consumed'], [1])
        self.assertEqual(json.loads(runner.state_file.read_text())['consumed'], [1])
        self.assertTrue((runner.state_dir/'claim-failure-1.json').exists())
        self.assertFalse((runner.state_dir/'terminal-1.json').exists())
        self.assertFalse((runner.state_dir/'delivery-1.json').exists())
        self.assertFalse(any(k in ('write', 'post') for k, v in runner.events))
        # No supervisor parser may consume this host's warning as a result.
        public = [comment(v) for k, v in runner.events if k == 'post']
        self.assertEqual(w.remote_consumed(public, {'owner'}), set())

    def race_claim(self, ambiguous_loser=False, lost_winner_response=False):
        first = self.runner
        second = self.other_host()
        claims = {}
        attempts = {first: 0, second: 0}
        nested = None
        for runner in (first, second):
            original = runner.api
            def api(endpoint, _runner=runner, _original=original, **data):
                if '/matching-refs/' in endpoint:
                    return [{'ref': ref} for ref in claims]
                if endpoint.endswith('/git/refs'):
                    attempts[_runner] += 1
                    self.assertEqual(json.loads(_runner.state_file.read_text())['consumed'], [1])
                    self.assertTrue(_runner.verification['inputs_verified'])
                    if data['ref'] in claims:
                        if ambiguous_loser:
                            raise subprocess.TimeoutExpired(['synthetic-claim'], 1, stderr=CANARY.decode())
                        raise subprocess.CalledProcessError(422, ['synthetic-claim'], stderr=CANARY.decode())
                    claims[data['ref']] = data['sha']
                    # Winner owns the ref, but has not posted RUNNING or written
                    # a receipt. The loser must not occupy the absent destination.
                    if nested:
                        self.assertEqual(first.remote_files, {})
                        nested()
                        self.assertEqual(first.remote_files, {})
                    if lost_winner_response:
                        raise subprocess.TimeoutExpired(['synthetic-claim'], 1, stderr=CANARY.decode())
                    return {'ref': data['ref']}
                return _original(endpoint, **data)
            runner.api = api
        # Both independent hosts discover before the atomic create. Their
        # consumed sets are stale when the second host attempts its claim.
        selected_first = first.eligible(ISSUE, 'owner')
        selected_second = second.eligible(ISSUE, 'owner')
        self.assertIsNotNone(selected_first); self.assertIsNotNone(selected_second)
        nested = lambda: self.run_selection(second, selected_second)
        self.run_selection(first, selected_first)
        self.assert_unowned_consumed(second)
        self.assertEqual(attempts, {first: 1, second: 1})
        self.assertEqual(len(claims), 1)
        if lost_winner_response:
            self.assert_unowned_consumed(first)
            self.assertEqual(first.remote_files, {})
        else:
            self.assertEqual(first.child_count, 1)
            self.assertEqual(self.receipt()['state'], 'READY_FOR_REVIEW')
            self.assertEqual(first.events.count(('write', DIAGNOSTIC['path'])), 1)
            self.assertEqual(first.events.count(('write', AUTH['path'])), 1)
        # Re-polling either host cannot consume again or retry claim/publication.
        before = dict(attempts)
        for runner in (first, second):
            with contextlib.redirect_stdout(io.StringIO()): runner.start()
        self.assertEqual(attempts, before)
        self.assertEqual(first.child_count + second.child_count, 0 if lost_winner_response else 1)
        self.assertEqual(first.events.count(('write', DIAGNOSTIC['path'])), 0 if lost_winner_response else 1)
        self.assert_no_leak()

    def test_two_hosts_discover_then_existing_claim_loser_cannot_publish(self):
        self.race_claim()

    def test_two_hosts_ambiguous_claim_loser_cannot_publish(self):
        self.race_claim(ambiguous_loser=True)

    def test_lost_successful_claim_response_neither_host_can_publish_or_rerun(self):
        self.race_claim(lost_winner_response=True)

    def test_end_to_end_pinned_input_external_child_output_receipt_public_order(self):
        self.runner.external_child = True
        self.run_task()
        self.assertEqual(self.runner.child_count, 1)
        self.assertEqual(self.runner.remote_files[AUTH['path']], CANARY+b' processed')
        receipt = validate_receipt(self.receipt())
        self.assertEqual(receipt['state'], 'READY_FOR_REVIEW')
        self.assertTrue(all(receipt['verification'].values()))
        self.assertEqual(receipt['artifacts'][0]['sha256'], hashlib.sha256(CANARY+b' processed').hexdigest())
        self.assertEqual(receipt['runtime']['checkout_revision'], self.runner.git('rev-parse', 'HEAD').strip())
        events = self.runner.events
        artifact = events.index(('write', AUTH['path']))
        diagnostic = events.index(('write', DIAGNOSTIC['path']))
        terminal = next(i for i, (k, v) in enumerate(events) if k == 'post' and 'WORKER_RESULT' in v)
        self.assertLess(artifact, diagnostic); self.assertLess(diagnostic, terminal)
        self.assertTrue(any(k == 'read' for k, v in events[artifact+1:diagnostic]))
        self.assertEqual(events[terminal-1], ('read', DIAGNOSTIC['path']))
        public = self.assert_no_leak()
        self.assertIn('PRIVATE_RECEIPT: verified', public)
        self.assertIn('CLAIMED_AT:', public); self.assertIn('Historical claim', public)
        self.assertFalse(json.loads((self.runner.state_dir/'heartbeat.json').read_text())['active'])
        self.assertEqual(json.loads((self.runner.state_dir/'delivery-1.json').read_text())['public_result'], True)

    def test_blocked_state_and_snapshot_are_available_privately(self):
        self.runner.child_mode = 'NEEDS_USER'
        self.run_task()
        receipt = self.receipt()
        self.assertEqual(receipt['code'], 'WORKER_BLOCKED')
        self.assertEqual(receipt['state'], 'NEEDS_USER')
        self.assertEqual(receipt['next_action'], 'new_task')
        self.assertTrue(receipt['retained_snapshot'])
        self.assertEqual(receipt['artifacts'], [])
        self.assertNotIn(AUTH['path'], self.runner.remote_files)
        self.assert_no_leak()

    def test_failed_child_receipt_without_exception_or_stderr(self):
        self.runner.child_mode = 'FAILED'
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        receipt = self.receipt()
        self.assertEqual((receipt['state'], receipt['code']), ('FAILED', 'CHILD_FAILED'))
        self.assertTrue(receipt['retained_snapshot'])
        self.assertNotIn(CANARY.decode(), json.dumps(receipt))
        self.assertTrue((self.runner.state_dir/'worker-1.log').exists())
        self.assert_no_leak()

    def test_input_mutation_prevents_artifact_publication(self):
        self.runner.mutate_input = True
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.receipt()['code'], 'INPUT_CHANGED')
        self.assertFalse(self.receipt()['verification']['inputs_unchanged'])
        self.assertNotIn(AUTH['path'], self.runner.remote_files)
        self.assert_no_leak()

    def test_private_inputs_alone_disable_public_publication(self):
        self.runner.body = task_body([INPUT], artifact=False)
        self.run_task()
        self.assertEqual(self.receipt()['state'], 'READY_FOR_REVIEW')
        self.assertEqual(self.receipt()['artifacts'], [])
        self.assert_no_leak()

    def assert_public_change_refused(self, change):
        self.runner.public_change = change
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.receipt()['code'], 'PUBLIC_CHANGE_REFUSED')
        self.assertNotIn(AUTH['path'], self.runner.remote_files)
        self.assert_no_leak()

    def test_public_file_changes_refused(self):
        self.assert_public_change_refused('file')

    def test_public_history_changes_refused(self):
        self.assert_public_change_refused('history')

    def test_invalid_model_result_cannot_supply_receipt_fields(self):
        self.runner.invalid_result = json.dumps({'state': 'READY_FOR_REVIEW', 'tests': '', 'summary': '',
                                                'questions': '', 'code': CANARY.decode()})
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.receipt()['code'], 'INVALID_RESULT')
        self.assertNotIn(CANARY.decode(), json.dumps(self.receipt()))
        self.assert_no_leak()

    def test_claim_failure_is_local_only_no_child_and_task_consumed(self):
        self.runner.fail_claim = True
        self.run_task()
        self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.runner.remote_files, {})
        self.assertFalse(any(k == 'post' for k, v in self.runner.events))
        self.assertFalse((self.runner.state_dir/'terminal-1.json').exists())
        self.assertEqual(json.loads((self.runner.state_dir/'claim-failure-1.json').read_text()),
                         {'code': 'CLAIM_FAILED', 'ownership': 'unconfirmed', 'consumed': True})
        self.assertEqual(self.runner.state['consumed'], [1])
        self.assert_no_leak()

    def test_running_comment_failure_still_attempts_failed_receipt(self):
        self.runner.fail_running = True
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.receipt()['code'], 'RESULT_PUBLICATION_FAILED')
        self.assertEqual(self.runner.state['consumed'], [1])

    def test_changed_source_before_reservation_has_no_claim_or_child(self):
        self.runner.source = b'changed after pin'
        with self.assertRaisesRegex(w.Stop, 'INPUT_VALIDATION_FAILED'): self.run_task()
        self.assertEqual(self.runner.state['consumed'], [])
        self.assertEqual(self.runner.child_count, 0)
        self.assertFalse(any('/git/refs' in v for k, v in self.runner.events if k == 'api'))
        self.assertEqual(self.runner.remote_files, {})
        self.assert_no_leak()

    def test_pin_mismatches_do_not_consume_task(self):
        for key, value in [('commit', 'f'*40), ('blob', 'f'*40), ('sha256', 'f'*64)]:
            self.runner.body = task_body([dict(INPUT, **{key: value})])
            with self.subTest(key=key), self.assertRaises(w.Stop): self.run_task()
            self.assertEqual(self.runner.child_count, 0)
            self.assertEqual(self.runner.state['consumed'], [])
            self.assertEqual(self.runner.remote_files, {})

    def test_partial_input_validation_does_not_stage_or_consume(self):
        self.runner.body = task_body([INPUT, dict(INPUT, path='fixtures/other.txt', alias='other.txt')])
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.runner.inputs, [])
        self.assertNotIn('input_staging', self.runner.state)
        self.assertEqual(self.runner.state['consumed'], [])

    def stage_only(self):
        self.runner.state_dir.mkdir(parents=True, exist_ok=True)
        self.runner.stage_inputs(comment(self.runner.body), 1)

    def test_local_input_link_replacement_is_detected(self):
        self.stage_only()
        source = self.runner.inputs[0]['path']
        source.parent.chmod(0o700)
        source.unlink(); source.symlink_to(self.root/'base.txt')
        source.parent.chmod(0o500)
        with self.assertRaises(w.Stop): self.runner.verify_inputs()

    def test_input_directory_symlink_replacement_is_detected(self):
        self.stage_only()
        directory = self.runner.inputs[0]['path'].parent
        moved = directory.with_name(directory.name+'-moved')
        directory.chmod(0o700)  # macOS requires directory write permission to rename it.
        directory.rename(moved)
        moved.chmod(0o500)
        self.addCleanup(lambda: (moved.chmod(0o700), shutil.rmtree(moved)))
        directory.symlink_to(moved, target_is_directory=True)
        self.addCleanup(directory.unlink)
        with self.assertRaises(w.Stop): self.runner.verify_inputs()

    def test_source_advancement_keeps_exact_pinned_request(self):
        self.run_task()
        reads = [v for k, v in self.runner.events if k == 'api' and '/contents/fixtures/' in v]
        self.assertEqual(len(reads), 1)
        self.assertTrue(reads[0].endswith('?ref='+INPUT['commit']))
        self.assertNotIn('?ref=main', reads[0])

    def test_post_child_failure_still_checks_input_immutability(self):
        self.runner.child_mode = 'FAILED'; self.runner.mutate_input = True
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.receipt()['code'], 'INPUT_CHANGED')
        self.assertNotIn(AUTH['path'], self.runner.remote_files)

    def test_no_output_grant_never_adds_input_writable_directory(self):
        self.runner.body = task_body([INPUT], artifact=False, diagnostic=False)
        self.run_task()
        self.assertEqual(self.runner.child_count, 1)
        self.assertEqual(self.runner.remote_files, {})
        self.assert_no_leak()

    def test_remote_symlink_and_oversize_refused_before_blob_read_or_claim(self):
        self.runner.node_mode = '120000'
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.runner.child_count, 0)
        self.assertFalse(any('/contents/fixtures/' in v for k, v in self.runner.events if k == 'api'))
        self.runner.node_mode = '100644'; self.runner.node_size = p.MAX_PRIVATE_BYTES+1
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.runner.state['consumed'], [])

    def test_repository_identity_or_visibility_mismatch_refused(self):
        for key, value in [('full_name', 'other/private'), ('private', False), ('default_branch', 'other')]:
            self.runner.metadata = dict(full_name=p.PRIVATE_REPOSITORY, private=True, default_branch='main')
            self.runner.metadata[key] = value
            with self.subTest(key=key), self.assertRaises(w.Stop): self.run_task()
            self.assertEqual(self.runner.state['consumed'], [])
            self.assertEqual(self.runner.child_count, 0)

    def test_artifact_readback_failure_yields_failed_receipt(self):
        self.runner.corrupt_readback = AUTH['path']
        with self.assertRaises(w.Stop): self.run_task()
        self.assertEqual(self.receipt()['code'], 'ARTIFACT_PUBLICATION_FAILED')
        self.assertFalse(self.receipt()['verification']['artifact_readback'])
        self.assertNotIn('STATE: READY_FOR_REVIEW', self.assert_no_leak())

    def test_receipt_cas_race_does_not_claim_success_or_retry(self):
        self.runner.fail_write = DIAGNOSTIC['path']
        self.run_task()
        public = self.assert_no_leak()
        self.assertIn('STATE: FAILED', public)
        self.assertIn('REASON_CODE: RECEIPT_PUBLICATION_FAILED', public)
        self.assertIn('PRIVATE_RECEIPT: unavailable', public)
        self.assertEqual(self.runner.events.count(('write', DIAGNOSTIC['path'])), 1)
        self.assertTrue((self.runner.state_dir/'terminal-1.json').exists())
        self.assertTrue((self.runner.state_dir/'artifact-1.bin').exists())
        self.assertEqual(self.runner.state['retained']['state'], 'FAILED')

    def test_receipt_readback_failure_preserves_uncertain_remote_write(self):
        self.runner.corrupt_readback = DIAGNOSTIC['path']
        self.run_task()
        self.assertIn(DIAGNOSTIC['path'], self.runner.remote_files)
        self.assertIn('STATE: FAILED', self.assert_no_leak())
        delivery = json.loads((self.runner.state_dir/'delivery-1.json').read_text())
        self.assertEqual(delivery['receipt'], 'unavailable')
        self.assertEqual(delivery['code'], 'RECEIPT_PUBLICATION_FAILED')

    def test_receipt_divergence_refuses_without_write(self):
        self.runner.remote_files[DIAGNOSTIC['path']] = b'previous divergent receipt'
        self.run_task()
        self.assertNotIn(('write', DIAGNOSTIC['path']), self.runner.events)
        self.assertIn('STATE: FAILED', self.assert_no_leak())

    def test_public_result_failure_after_private_write_never_reexecutes_or_overwrites_receipt(self):
        self.runner.fail_result = True
        with self.assertRaises(subprocess.CalledProcessError): self.run_task()
        self.assertEqual(self.receipt()['state'], 'READY_FOR_REVIEW')
        delivery = json.loads((self.runner.state_dir/'delivery-1.json').read_text())
        self.assertEqual((delivery['code'], delivery['receipt'], delivery['public_result']),
                         ('RESULT_PUBLICATION_FAILED', 'verified', False))
        self.assertEqual(self.runner.events.count(('write', DIAGNOSTIC['path'])), 1)
        self.runner.fail_result = False
        self.run_task()
        self.assertEqual(self.runner.child_count, 1)
        self.assertEqual(self.runner.state['consumed'], [1])

    def test_no_diagnostic_grant_writes_only_artifact(self):
        self.runner.body = task_body([INPUT], diagnostic=False)
        self.run_task()
        self.assertEqual(set(self.runner.remote_files), {AUTH['path']})
        self.assertIn('PRIVATE_RECEIPT: not_authorized', self.assert_no_leak())


class LocalInputAndReceiptTests(unittest.TestCase):
    def test_local_symlink_oversize_and_directory_replacement_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root/'target'; target.write_bytes(b'synthetic')
            link = root/'link'; link.symlink_to(target)
            with self.assertRaises(w.Stop): w.Runner.regular_bytes(link)
            target.write_bytes(b'x'*(p.MAX_PRIVATE_BYTES+1))
            with self.assertRaises(w.Stop): w.Runner.regular_bytes(target)

    def test_receipt_allowlist_rejects_arbitrary_fields_and_diagnostics(self):
        receipt = {'schema_version': 1, 'identity': {'repository': 'owner/project', 'issue': 11, 'task': 1},
                   'state': 'FAILED', 'code': 'CHILD_FAILED', 'next_action': 'inspect_local',
                   'runtime': {'python': '3.9.6', 'runner_revision': None, 'checkout_revision': 'a'*40},
                   'retained_snapshot': None, 'verification': dict.fromkeys(w.FLAGS, False), 'artifacts': []}
        self.assertEqual(validate_receipt(receipt), receipt)
        for key, value in [('schema_version', 2), ('code', CANARY.decode()), ('next_action', 'rerun'),
                           ('logs', CANARY.decode()), ('retained_snapshot', '/private/path'),
                           ('runtime', {'python': '3.9.6', 'environment': CANARY.decode()}),
                           ('verification', {'inputs_verified': 'true'}), ('artifacts', [AUTH])]:
            with self.subTest(key=key), self.assertRaises(p.PolicyError):
                validate_receipt(dict(receipt, **{key: value}))


if __name__ == '__main__':
    unittest.main()
