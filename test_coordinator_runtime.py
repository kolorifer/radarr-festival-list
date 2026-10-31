"""Synthetic real-parent poll -> authenticated pins -> finite runtime. No SSH/live data."""
import argparse
import base64
from contextlib import redirect_stdout, ExitStack
from copy import deepcopy
import datetime as dt
import errno
import hashlib
import io as streams
import json
import os
from pathlib import Path
import stat
import sys
import time
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

from automation import github_worker as worker
from automation import coordinator_runtime as r
from automation import coordinator_transport as t
from automation import coordinator_storage as storage
from automation import coordinator_owner as owner
from automation import coordinator_cycles as cycles
from automation import coordinator_io as io
from automation import coordinator_parent as parent
from automation.supervisor_policy import PolicyError, PRIVATE_REPOSITORY
from test_coordinator import NOW, HEAD, snapshot
from test_coordinator_cycles import Crash
from test_coordinator_integration import pair, parent_fixture
from test_github_worker import TASK

CODE = Path(__file__).resolve().parent
CANARY = 'SYNTHETIC_PRIVATE_NO_PUBLIC_OUTPUT'


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def stamp(now):
    return dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class FakeParent(worker.Runner):
    def __init__(self, root):
        self.repo = CODE
        self.args = argparse.Namespace(repo=CODE, github_repo=r.REPOSITORY, issue=r.ISSUE,
                                       dry_run=False, once=True, interval=60, base='main')
        self.dispatch_dir = root / 'journals'
        self.dispatch_dir.mkdir(mode=0o700)
        self.runner_revision = 'a' * 40
        self.discovery = False
        self.global_lock_fd = self.lock_fd = None
        self.probe_file = self.dispatch_dir / 'quota-refresh.json'
        self.select_issue(r.ISSUE)
        self.state_dir.mkdir(mode=0o700)
        self.issue = {'number': r.ISSUE, 'state': 'open', 'user': {'login': 'owner'},
                      'url': f'https://api.github.com/repos/{r.REPOSITORY}/issues/{r.ISSUE}',
                      'body': 'Issue prose is not authority'}
        self.messages, self.registry, self.events = [], {}, []
        self.puts = self.claims = self.acquisitions = 0
        self.private = True
        self.claim_error = self.put_error = self.readback_error = False
        self.current_commit = None
        self.remote_file = None

    def pin(self, path, raw):
        commit = hashlib.sha1(path.encode() + raw).hexdigest()
        self.registry[commit] = (path, raw)
        return dict(repository=PRIVATE_REPOSITORY, path=path, commit=commit,
                    blob=blob(raw), sha256=io.digest(raw))

    def comment(self, command, author='owner', now=NOW, body=None):
        comment = dict(id=len(self.messages) + 1, user={'login': author},
                       created_at=stamp(now), updated_at=stamp(now),
                       issue_url=self.issue['url'],
                       body=body if body is not None else r.PREFIX + io.encode(command).decode())
        self.messages.append(comment)
        return comment

    def comments(self):
        return deepcopy(self.messages)

    def git(self, *args):
        self.events.append(('git', args))
        if args == ('rev-parse', 'HEAD'):
            return self.runner_revision
        if args[:2] == ('status', '--porcelain'):
            return ''
        raise AssertionError('unexpected git call')

    def run_selected(self, *args):
        raise AssertionError('finite operation must not launch engineering')

    def refresh_quota(self):
        raise AssertionError('finite operation must not launch a quota probe')

    def api(self, endpoint, **data):
        self.events.append(('api', endpoint))
        if endpoint == 'user':
            return {'login': 'owner'}
        if endpoint == f'repos/{r.REPOSITORY}/issues/{r.ISSUE}':
            return deepcopy(self.issue)
        if endpoint.startswith(f'repos/{r.REPOSITORY}/issues/comments/'):
            return deepcopy(next(c for c in self.messages if c['id'] == int(endpoint.rsplit('/', 1)[1])))
        if endpoint == f'repos/{r.REPOSITORY}/git/commits/' + 'b'*40:
            return {'sha': 'b'*40, 'tree': {'sha': 'c'*40}}
        if endpoint == f'repos/{r.REPOSITORY}/git/refs':
            self.claims += 1
            assert data['ref'] == r.CLAIM
            assert json.loads((self.state_dir / r.JOURNAL).read_text())['status'] == 'claim_uncertain'
            if self.claim_error or self.claims > 1:
                raise subprocess.CalledProcessError(1, ['synthetic'], stderr='ambiguous')
            return {'ref': r.CLAIM, 'object': {'sha': data['sha']}}
        if endpoint == 'repos/' + PRIVATE_REPOSITORY:
            return {'full_name': PRIVATE_REPOSITORY, 'private': self.private, 'default_branch': 'main'}
        prefix = 'repos/' + PRIVATE_REPOSITORY + '/'
        if endpoint.startswith(prefix):
            tail = endpoint[len(prefix):]
            if tail == 'commits/main':
                return {'sha': self.current_commit}
            if tail.startswith('git/commits/'):
                commit = tail.split('/')[-1]
                assert commit in self.registry
                return {'sha': commit, 'tree': {'sha': commit}}
            if tail.startswith('git/trees/'):
                tree = tail[len('git/trees/'):]
                # The fake tree IDs are real 40-hex strings with a lookup table.
                for commit, (path, raw) in self.registry.items():
                    parts = path.split('/')
                    for i in range(len(parts)):
                        tree_id = commit if i == 0 else hashlib.sha1((commit + '/'.join(parts[:i])).encode()).hexdigest()
                        if tree_id == tree:
                            node = {'path': parts[i], 'mode': '100644', 'type': 'blob', 'sha': blob(raw), 'size': len(raw)}
                            if i < len(parts)-1:
                                node = {'path': parts[i], 'mode': '040000', 'type': 'tree',
                                        'sha': hashlib.sha1((commit + '/'.join(parts[:i+1])).encode()).hexdigest()}
                            return {'sha': tree, 'truncated': False, 'tree': [node]}
                raise AssertionError('unknown tree')
            if tail.startswith('contents/'):
                path, ref = tail[len('contents/'):].split('?ref=')
                if ref == 'main':
                    if self.readback_error:
                        raise subprocess.CalledProcessError(1, ['synthetic'], stderr=CANARY)
                    if self.remote_file is None:
                        raise subprocess.CalledProcessError(1, ['synthetic'], stderr='HTTP 404')
                    raw = self.remote_file
                else:
                    selected_path, raw = self.registry[ref]
                    assert selected_path == path
                return {'path': path, 'sha': blob(raw), 'type': 'file', 'encoding': 'base64',
                        'content': base64.b64encode(raw).decode()}
        if '/matching-refs/' in endpoint:
            return []
        raise AssertionError('unexpected API call ' + endpoint)

    def run(self, command, **kwargs):
        assert command[:2] == ['gh', 'api'] and '--method' in command and 'PUT' in command
        self.puts += 1
        assert self.puts == 1
        assert self.journal()['status'] == 'publication_uncertain'
        data = json.loads(kwargs['input'])
        assert set(data) == {'message', 'branch', 'content'}
        assert self.remote_file is None
        self.remote_file = base64.b64decode(data['content'])
        path = command[2].split('/contents/')[1]
        pinned = self.pin(path, self.remote_file)
        self.current_commit = pinned['commit']
        if self.put_error:
            raise subprocess.CalledProcessError(1, ['synthetic'], stderr=CANARY)
        return json.dumps({'commit': {'sha': pinned['commit']}, 'content': {'sha': pinned['blob']}})

    def journal(self):
        return io.decode((self.state_dir / r.JOURNAL).read_bytes())


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.home = self.root / 'synthetic-home'
        self.enclosing = Path(str(self.home) + storage.SUFFIX)
        self.enclosing.mkdir(parents=True, mode=0o700)
        for path in (self.home, self.home / '.local', self.home / '.local/state'):
            path.chmod(0o700)
        (self.enclosing / 'retained-probe').write_bytes(b'keep')
        self.staging = self.root / 'staging'
        self.staging.mkdir(mode=0o700)
        self.ssh = self.root / 'synthetic-ssh'
        self.ssh.mkdir(mode=0o700)
        for name in ('key', 'known-hosts'):
            (self.ssh / name).write_bytes(CANARY.encode())
            (self.ssh / name).chmod(0o600)
        self.runner = FakeParent(self.root)
        # Only synthetic fixtures are inspected. Mock ACLs/account/system-temp
        # ancestors, preserving actual fixture no-follow, UID, mode and identity.
        real_stat, real_fstat = os.stat, os.fstat
        ancestors = {(p.stat().st_dev, p.stat().st_ino) for p in self.root.parents}
        def safe(s):
            if (s.st_dev, s.st_ino) in ancestors:
                values = list(s); values[0] &= ~0o022; values[4] = 0
                return os.stat_result(values)
            return s
        for p in (patch.object(storage.os, 'stat', side_effect=lambda *a, **k: safe(real_stat(*a, **k))),
                  patch.object(storage.os, 'fstat', side_effect=lambda *a, **k: safe(real_fstat(*a, **k))),
                  patch.object(storage.pwd, 'getpwuid', return_value=types.SimpleNamespace(pw_dir=str(self.home))),
                  patch.object(storage, 'acl_identity', return_value='synthetic-acl'),
                  patch.object(r.time, 'time', return_value=NOW),
                  patch.object(t, 'acquire', side_effect=self.acquire)):
            p.start(); self.addCleanup(p.stop)
        base = self.enclosing / 'adapter'
        self.req = owner.request(base, r.PHASE, 'owner', 'partial-1', NOW, base/'intake', base/'cycles',
                                 base/'evidence', base/'receipts', self.staging/'report.json', 'original-exports',
                                 '/synthetic/source', {'repository': PRIVATE_REPOSITORY,
                                 'path': 'operations/issue-122/partial-1.json'}, 'successor-coordinator')
        self.value = dict(version=1, repository=r.REPOSITORY, issue=r.ISSUE, phase=r.PHASE,
                          operation='partial-1', reviewed_revision='b'*40, deployed_revision=self.runner.runner_revision,
                          code_sha256={p: io.digest((CODE/p).read_bytes()) for p in r.MANIFEST},
                          storage={'version': 1, 'path': str(self.enclosing), 'expected': self.identity(self.enclosing, False)},
                          staging=self.identity(self.staging), source=dict(host='synthetic.invalid', port=22,
                          account='synthetic', key=self.identity(self.ssh/'key'), known_hosts=self.identity(self.ssh/'known-hosts'),
                          root='/synthetic/source', uid=1234, gid=0,
                          ancestors=[[1, i+1, 0 if i < 2 else 1234, 0,
                                      stat.S_IFDIR|(0o755 if i < 2 else 0o700)] for i in range(3)]),
                          request=self.req, recipient_chat='designated-new-chat', independent=None)
        self.export_root = self.root/'synthetic-exports'
        self.export_root.mkdir(mode=0o700)
        movie, report = pair(self.export_root)
        self.originals = {path: (json.dumps(v, indent=2)+'\n').encode()
                          for path, v in zip(owner.FIXED_PATHS, (movie, report))}
        self.selection = None

    @staticmethod
    def identity(path, include_path=True):
        s = path.stat()
        return dict(dev=s.st_dev, ino=s.st_ino, **({'path': str(path)} if include_path else {}))

    def acquire(self, *args, **kwargs):
        self.runner.acquisitions += 1
        self.assertEqual(self.runner.acquisitions, 1)
        self.assertEqual(self.runner.journal()['status'], 'acquisition_uncertain')
        self.assertTrue((Path(self.req['base'])/owner.intent_name(self.req)).exists())
        self.assertEqual(kwargs['lock_fds'], self.runner.inherited_locks())
        files = {path: {'status': 'read', 'bytes': base64.b64encode(raw).decode(),
                       'sha256': io.digest(raw), 'metadata': [1, 1, 1234, 0, stat.S_IFREG|0o600,
                                                            len(raw), 1, 1, 1]} for path, raw in self.originals.items()}
        return {'complete': True, 'returncode': 0, 'stdout': io.encode({'version': 1, 'files': files}), 'stderr': CANARY.encode()}

    def start(self):
        self.selection = self.runner.pin('selections/start.json', io.encode(self.value))
        return self.command('start')

    def command(self, action, **extra):
        return self.runner.comment(dict(action=action, phase=r.PHASE, selection=self.selection, **extra))

    def poll(self):
        with redirect_stdout(streams.StringIO()) as output:
            with worker.lock(self.runner.dispatch_dir/'dispatcher.lock') as self.runner.global_lock_fd:
                self.runner.poll()
        self.assertNotIn(CANARY, output.getvalue())
        return output.getvalue()

    def acknowledgement(self, change=None):
        journal = self.runner.journal()
        value = dict(version=1, phase=r.PHASE, operation=self.value['operation'], selection=self.selection,
                     binding=journal['attempt'], recipient_chat=self.value['recipient_chat'],
                     ingestion_reference='actual-synthetic-ingestion-1', observed_at=NOW,
                     publication=journal['publication'])
        if change: change(value)
        pin = self.runner.pin('selections/ack.json', io.encode(value))
        return self.command('ack', acknowledgement=pin)

    def assert_no_op(self):
        self.assertEqual((self.runner.claims, self.runner.acquisitions, self.runner.puts), (0, 0, 0))
        self.assertFalse((self.runner.state_dir/r.JOURNAL).exists())
        self.assertEqual(list(self.enclosing.iterdir()), [self.enclosing/'retained-probe'])

    def test_real_poll_publication_genuine_selection_archive_restart_quiet(self):
        self.start()
        real_chain = storage.Grant.chain
        from contextlib import contextmanager
        @contextmanager
        def account_profile(grant, *args, **kwargs):
            if kwargs.get('guard'):
                self.assertEqual(grant.home, str(self.home))
            with real_chain(grant, *args, **kwargs) as value:
                yield value
        with patch.object(storage.Grant, 'chain', account_profile):
            self.poll()
        self.assertEqual(self.runner.journal()['status'], 'published')
        self.assertFalse(owner.inspect(self.req)['archived'])
        self.assertEqual(self.runner.state['consumed'], [])
        self.assertFalse((self.runner.state_dir/'private-receipt.json').exists())
        self.assertEqual(self.runner.remote_file, (self.staging/'report.json').read_bytes())
        self.poll(); self.assertEqual(self.runner.acquisitions, 1)
        self.acknowledgement(); self.poll()
        self.assertEqual(self.runner.journal()['status'], 'archived')
        self.assertTrue(owner.inspect(self.req)['archived'])
        self.assertEqual((self.enclosing/'retained-probe').read_bytes(), b'keep')
        before = {str(p): p.read_bytes() for p in self.enclosing.rglob('*') if p.is_file()}
        self.poll()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.enclosing.rglob('*') if p.is_file()})
        self.assertEqual((self.runner.claims, self.runner.acquisitions, self.runner.puts), (1, 1, 1))

    def test_bad_credentials_have_zero_phase_claim_adapter_source_or_publication_effects(self):
        for problem in ('missing', 'mode', 'symlink', 'inode', 'owner', 'acl', 'parent-mode',
                        'parent-owner', 'same-file', 'empty', 'oversized', 'hardlink', 'spelling',
                        'hosts-mode', 'hosts-missing'):
            with self.subTest(problem=problem):
                fixture = RuntimeTests()
                fixture.setUp()
                try:
                    key = fixture.ssh/'key'
                    local_patches = []
                    if problem == 'hosts-mode': (fixture.ssh/'known-hosts').chmod(0o644)
                    elif problem == 'hosts-missing': (fixture.ssh/'known-hosts').unlink()
                    elif problem == 'missing': key.unlink()
                    elif problem == 'mode': key.chmod(0o644)
                    elif problem == 'symlink':
                        key.rename(fixture.ssh/'saved'); key.symlink_to(fixture.ssh/'saved')
                    elif problem == 'inode': fixture.value['source']['key']['ino'] += 1
                    elif problem == 'owner' or problem == 'parent-owner':
                        target = key if problem == 'owner' else fixture.ssh
                        original = os.fstat
                        ino = target.stat().st_ino
                        def wrong(fd):
                            value = original(fd)
                            if value.st_ino == ino:
                                values = list(value); values[4] = os.geteuid()+1
                                return os.stat_result(values)
                            return value
                        local_patches.append(patch.object(storage.os, 'fstat', side_effect=wrong))
                    elif problem == 'acl':
                        local_patches.append(patch.object(storage, 'acl_identity', side_effect=storage.StorageError('storage_acl')))
                    elif problem == 'parent-mode': fixture.ssh.chmod(0o755)
                    elif problem == 'same-file': fixture.value['source']['known_hosts'] = deepcopy(fixture.value['source']['key'])
                    elif problem == 'empty': key.write_bytes(b'')
                    elif problem == 'oversized': key.write_bytes(b'x'*(r.LIMIT+1))
                    elif problem == 'hardlink': os.link(key, fixture.ssh/'linked')
                    elif problem == 'spelling':
                        fixture.value['source']['key']['path'] = str(fixture.ssh/'KEY')
                    fixture.start()
                    with ExitStack() as stack:
                        for item in local_patches: stack.enter_context(item)
                        with self.assertRaises(PolicyError): fixture.poll()
                    fixture.assert_no_op()
                    self.assertFalse(Path(fixture.req['base']).exists())
                finally:
                    fixture.doCleanups()

    def test_bad_credentials_do_not_fetch_optional_independent_source_exports(self):
        manifest_pin = self.runner.pin('selected/manifest.json', b'{}')
        self.value['independent'] = dict(manifest=manifest_pin, engineering=None, parent_status=None)
        self.req['evidence_manifest_sha256'] = manifest_pin['sha256']
        (self.ssh/'key').chmod(0o644)
        self.start()
        with patch.object(r, 'fetch', wraps=r.fetch) as fetch:
            with self.assertRaises(PolicyError): self.poll()
        self.assertEqual([call.args[1] for call in fetch.call_args_list], [self.selection])
        self.assert_no_op()

    def test_short_ssh_parent_uses_os_account_profile_and_safe_system_ancestors(self):
        # Keep this canonical parent shorter than SUFFIX: long default macOS
        # temp paths previously concealed accidental home slicing.
        with tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform == 'darwin' else '/tmp') as directory:
            short = Path(directory).resolve()/'.ssh'; short.mkdir(mode=0o700)
            self.assertLess(len(str(short)), len(storage.SUFFIX))
            for field, name in (('key', 'key'), ('known_hosts', 'known-hosts')):
                (short/name).write_bytes(b'synthetic fixture'); (short/name).chmod(0o600)
                self.value['source'][field] = self.identity(short/name)
            original_stat, original_fstat = os.stat, os.fstat
            shared = {p.stat().st_ino for p in short.parents if p != Path(directory).resolve()}
            def safe(info):
                if info.st_ino in shared:
                    values = list(info); values[0] &= ~0o022; values[4] = 0
                    return os.stat_result(values)
                return info
            chain = storage.Grant.chain
            from contextlib import contextmanager
            @contextmanager
            def profile(grant, *args, **kwargs):
                if kwargs.get('guard'): self.assertEqual(grant.home, str(self.home))
                with chain(grant, *args, **kwargs) as result: yield result
            self.start()
            with patch.object(storage.os, 'stat', side_effect=lambda *a, **k: safe(original_stat(*a, **k))), \
                    patch.object(storage.os, 'fstat', side_effect=lambda *a, **k: safe(original_fstat(*a, **k))), \
                    patch.object(storage.Grant, 'chain', profile):
                self.poll()
            self.assertEqual(self.runner.journal()['status'], 'published')

    def test_credential_replacement_during_acquisition_fails_postcheck_before_publication(self):
        self.start()
        def replaced(*args, **kwargs):
            result = self.acquire(*args, **kwargs)
            key = self.ssh/'key'; key.rename(self.ssh/'original')
            key.write_bytes(b'replaced'); key.chmod(0o600)
            return result
        with patch.object(t, 'acquire', side_effect=replaced):
            with self.assertRaises(PolicyError): self.poll()
        self.assertEqual((self.runner.claims, self.runner.acquisitions, self.runner.puts), (1, 1, 0))
        self.poll(); self.assertEqual(self.runner.acquisitions, 1)

    def test_done_closed_stop_before_start_and_before_genuine_continuation(self):
        self.start()
        done = self.runner.comment({}, body='STATE: DONE')
        self.poll(); self.assert_no_op()
        self.runner.messages.remove(done)
        self.poll()
        self.acknowledgement()
        self.runner.comment({}, body='STATE: DONE')
        with patch.object(r, 'fetch', side_effect=AssertionError('DONE fetched private input')):
            self.poll()
        self.assertEqual(self.runner.journal()['status'], 'published')
        self.runner.messages.pop(); self.runner.issue['state'] = 'closed'
        self.poll(); self.assertEqual(self.runner.journal()['status'], 'published')

    def test_consumed_start_and_completed_archive_poll_are_quiet_before_private_fetch(self):
        self.start(); self.poll()
        with patch.object(r, 'fetch', side_effect=AssertionError('inert start fetched private input')):
            self.assertIn('No eligible', self.poll())
        self.acknowledgement(); self.poll()
        with patch.object(r, 'fetch', side_effect=AssertionError('completed ack fetched private input')), \
                patch.object(r, 'validate', side_effect=AssertionError('completed validation')):
            self.assertIn('No eligible', self.poll())

    def test_real_discovery_consumed_phase_does_not_starve_different_issue(self):
        from test_github_worker import DiscoveryRunner, comment
        self.start(); self.poll()
        for status, number in (('published', 124), ('archived', 125)):
            if status == 'archived':
                self.acknowledgement(); self.poll()
            other = DiscoveryRunner(self.root/('other-'+str(number)))
            other.args.github_repo = r.REPOSITORY
            other.origin = 'https://github.com/'+r.REPOSITORY+'.git'
            other.dispatch_dir = self.runner.dispatch_dir
            other.issues = [deepcopy(self.runner.issue), dict(self.runner.issue, number=number)]
            newer = comment(TASK, 100)
            other.issue_messages = {122: deepcopy(self.runner.messages), number: [newer]}
            with patch.object(worker, 'quota_remaining', return_value=80), redirect_stdout(streams.StringIO()), \
                    patch.object(r, 'fetch', side_effect=AssertionError('inert phase fetched private input')):
                other.start()
            self.assertEqual([call[1] for call in other.calls if call[0] == 'execute'], [(number, 1)])
        self.assertEqual(self.runner.acquisitions, 1)

    def test_consumed_failed_reconcile_quiet_and_new_explicit_reconcile_eligible(self):
        self.start(); self.runner.put_error=True
        with self.assertRaises(PolicyError): self.poll()
        self.runner.readback_error=True
        self.command('reconcile')
        with self.assertRaises(PolicyError): self.poll()
        with patch.object(r, 'fetch', side_effect=AssertionError('inert reconcile fetched private input')):
            self.assertIn('No eligible', self.poll())
        self.runner.readback_error=False
        self.command('reconcile'); self.poll()
        self.assertEqual(self.runner.journal()['status'], 'published')
        with patch.object(r, 'fetch', side_effect=AssertionError('completed reconcile fetched private input')):
            self.assertIn('No eligible', self.poll())

    def test_same_genuine_ack_and_reconcile_resume_interrupted_receipt_archive(self):
        self.start(); self.runner.put_error=True
        with self.assertRaises(PolicyError): self.poll()
        self.command('reconcile')
        with patch.object(owner, 'receipt', side_effect=Crash()):
            with self.assertRaises(Crash): self.poll()
        self.poll()
        self.assertEqual(self.runner.journal()['status'], 'published')
        self.acknowledgement()
        original = owner.archive
        def interrupted(req):
            original(req)
            raise Crash()
        with patch.object(owner, 'archive', side_effect=interrupted):
            with self.assertRaises(Crash): self.poll()
        self.poll()
        self.assertEqual(self.runner.journal()['status'], 'archived')
        self.assertEqual((self.runner.claims, self.runner.acquisitions, self.runner.puts), (1,1,1))

    def test_weak_unbound_or_malformed_phase_state_cannot_grant_continuation(self):
        self.start(); self.poll(); self.acknowledgement()
        original = (self.runner.state_dir/r.JOURNAL).read_bytes()
        for change in (lambda s:s.update(version=True), lambda s:s.update(selection_sha256='0'*64),
                       lambda s:s.update(start=dict(s['start'], id=999)), lambda s:s.update(status='retry'),
                       lambda s:s.update(claim_confirmed=False), lambda s:s.pop('request'),
                       lambda s:s['request'].update(version=True), lambda s:s.update(evidence_identity=None),
                       lambda s:s.update(acknowledgement={'pin': self.selection}),
                       lambda s:s.update(status='archived', acknowledgement={'pin': self.selection}),
                       lambda s:s.update(attempt=dict(s['attempt'], attempt='0'*64)),
                       lambda s:s.update(publication=None)):
            state = io.decode(original); change(state)
            (self.runner.state_dir/r.JOURNAL).write_bytes(io.encode(state))
            with self.assertRaises(PolicyError): self.poll()
            self.assertFalse(owner.inspect(self.req)['archived'])
        (self.runner.state_dir/r.JOURNAL).write_bytes(original)

    def test_untrusted_prose_issue_body_and_no_request_do_nothing(self):
        self.start()
        self.runner.issue['body'] = self.runner.messages[0]['body']
        self.runner.messages[0]['user']['login'] = 'stranger'
        self.poll(); self.assert_no_op()

    def test_malformed_duplicate_keys_and_engineering_action_fail_before_mutation(self):
        self.start()
        valid = self.runner.messages[0]['body']
        for body in (valid+'\n', ' '+valid, valid.replace('OPERATION:', 'operation:'),
                     valid.replace('"action":', '"action":"start","action":'),
                     valid.replace('"start"', '"run_selected"'), valid.replace('"phase":', '"extra":1,"phase":')):
            with self.subTest(body=body[:80]):
                self.runner.messages[0]['body'] = body
                with self.assertRaises(PolicyError): self.poll()
                self.assert_no_op()

    def test_wrong_repository_phase_author_revision_and_expired_start(self):
        for field, changed in (('deployed_revision', 'b'*40), ('phase', 'old-phase'), ('issue', 119),
                               ('repository', 'stranger/project'), ('code_sha256', {})):
            with self.subTest(field=field):
                original = self.value[field]; self.value[field] = changed
                self.runner.messages = []; self.start()
                with self.assertRaises(PolicyError): self.poll()
                self.assert_no_op(); self.value[field] = original
        self.runner.messages = []; self.start()
        self.runner.messages[0]['created_at'] = self.runner.messages[0]['updated_at'] = stamp(NOW-4000)
        with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()

    def test_changed_and_conflicting_pins_and_edited_comments(self):
        self.start()
        old = self.selection
        self.selection = dict(old, sha256='0'*64)
        self.command('reconcile')
        with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()
        self.runner.messages.pop(); self.selection = old
        self.runner.messages[0]['updated_at'] = stamp(NOW+1)
        with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()

    def test_pin_must_be_private_regular_exact_and_content_bound(self):
        self.start(); self.runner.private = False
        with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op(); self.runner.private = True
        pin = self.selection
        path, raw = self.runner.registry[pin['commit']]
        self.runner.registry[pin['commit']] = (path, raw + b' ')
        with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()

    def test_missing_root_symlink_mode_identity_acl_and_overlap_fail_closed(self):
        self.start()
        self.enclosing.chmod(0o750)
        with self.assertRaises(PolicyError): self.poll()
        self.enclosing.chmod(0o700); self.assert_no_op()
        self.value['storage']['expected']['ino'] += 1
        self.runner.messages=[]; self.start()
        with self.assertRaises(PolicyError): self.poll()
        self.value['storage']['expected']['ino'] -= 1; self.assert_no_op()
        self.runner.messages=[]; self.start()
        with patch.object(storage, 'acl_identity', side_effect=storage.StorageError('storage_acl')):
            with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()
        original = self.enclosing.rename(self.enclosing.with_name('retained-original'))
        self.enclosing.symlink_to(original, target_is_directory=True)
        with self.assertRaises(PolicyError): self.poll()
        self.enclosing.unlink(); original.rename(self.enclosing)
        self.assert_no_op()

    def test_ambiguous_claim_is_consumed_no_reservation_or_transport(self):
        self.runner.claim_error = True
        self.start()
        with self.assertRaises(PolicyError): self.poll()
        self.assertFalse(Path(self.req['base']).exists())
        self.poll()
        self.command('reconcile')
        with patch.object(r, 'fetch', side_effect=AssertionError('ambiguous claim is inert')):
            self.assertIn('No eligible', self.poll())
        self.assertEqual((self.runner.claims, self.runner.acquisitions, self.runner.puts), (1, 0, 0))

    def test_lost_put_response_readback_only_then_real_ack(self):
        self.start(); self.runner.put_error = True
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(self.runner.journal()['status'], 'publication_uncertain')
        self.poll(); self.assertEqual(self.runner.puts, 1)
        self.command('reconcile'); self.poll()
        self.assertEqual(self.runner.journal()['status'], 'published')
        self.acknowledgement(); self.poll()
        self.assertTrue(owner.inspect(self.req)['archived'])
        self.assertEqual(self.runner.puts, 1)

    def test_uncertain_transport_is_not_retried_and_retains_private_diagnostics(self):
        self.start()
        with patch.object(t, 'acquire', return_value={'complete': False, 'returncode': -9,
                                                    'stdout': b'', 'stderr': CANARY.encode()}) as acquire:
            self.poll(); self.poll(); self.assertEqual(acquire.call_count, 1)
        payload = json.loads(self.runner.remote_file)
        self.assertNotIn(CANARY, self.runner.remote_file.decode())
        self.assertIn(CANARY.encode(), base64.b64decode(json.loads((self.enclosing/'finite-phase-1/transport.json').read_text())['stderr']))
        self.assertEqual(payload['report']['movies']['status'], 'unavailable')

    def test_crashes_at_reserve_acquire_prepare_handoff_write_boundaries_never_replay(self):
        # Fresh fixture per crash point, exercising real parent poll each time.
        for module, name in ((owner, 'reserve'), (t, 'acquire'), (owner, 'seal'),
                             (owner, 'prepare'), (owner, 'handoff'), (r.Runtime, 'publish')):
            with self.subTest(boundary=name):
                fixture = RuntimeTests('test_real_poll_publication_genuine_selection_archive_restart_quiet')
                fixture.setUp()
                try:
                    fixture.start()
                    with patch.object(module, name, side_effect=Crash()):
                        with self.assertRaises(Crash): fixture.poll()
                    fixture.poll()
                    self.assertLessEqual(fixture.runner.acquisitions, 1)
                    self.assertEqual(fixture.runner.puts, 0)
                finally:
                    fixture.doCleanups()

    def test_false_json_wrong_chat_hash_attempt_time_and_engineering_receipt_rejected(self):
        self.start(); self.poll()
        for change in (lambda a: a.update(recipient_chat='old-chat'),
                       lambda a: a['binding'].update(recipient='owner'),
                       lambda a: a['binding'].update(payload_sha256='0'*64),
                       lambda a: a['binding'].update(attempt='0'*64),
                       lambda a: a.update(observed_at=NOW-1),
                       lambda a: a.update(issuer='successor-coordinator'),
                       lambda a: a.update(trusted=True)):
            with self.subTest(change=change):
                self.acknowledgement(change)
                with self.assertRaises(PolicyError): self.poll()
                self.assertFalse(owner.inspect(self.req)['archived'])
                self.runner.messages.pop()
        # Merely staging accepted-shaped JSON is never selected automatically.
        (Path(self.req['receipt_root'])/'recipient.json').write_text('{"trusted":true}')
        (Path(self.req['receipt_root'])/'recipient.json').chmod(0o600)
        self.poll()
        self.assertFalse(owner.inspect(self.req)['archived'])
        self.assertEqual(self.runner.puts, 1)

    def test_no_second_cycle_or_engineering_history_reset(self):
        self.start(); self.poll(); old = self.runner.journal()
        self.value['operation'] = 'partial-2'
        self.start()
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(old, self.runner.journal())
        self.assertEqual(self.runner.state['consumed'], [])
        self.assertEqual(self.runner.claims, 1)

    def test_phase_three_engineering_limit_and_issue119_eight_claim_history_preserved(self):
        self.runner.comment({}, body=TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 3'))
        self.runner.state['consumed'] = [1, 2]
        self.assertIsNotNone(self.runner.eligible(self.runner.issue, 'owner'))
        self.runner.state['consumed'] = [1, 2, 3]
        self.assertIsNone(self.runner.eligible(self.runner.issue, 'owner'))
        self.runner.messages[0]['body'] = TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 4')
        with self.assertRaises(worker.Stop): self.runner.eligible(self.runner.issue, 'owner')
        self.runner.args.issue = 119
        self.runner.discovery = True
        self.runner.state['consumed'] = list(range(1,9))
        self.runner.messages[0]['body'] = TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 9')
        with redirect_stdout(streams.StringIO()):
            self.assertIsNone(self.runner.eligible(dict(self.runner.issue, number=119), 'owner'))
        self.assertEqual(self.runner.state['consumed'], list(range(1,9)))
        self.assertEqual(self.runner.claims, 0)

    def test_newer_explicit_engineering_task_supersedes_old_operation_without_reset(self):
        self.start(); self.poll(); before = self.runner.journal()
        cm = self.runner.comment({}, body=TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 2'))
        self.runner.state['consumed'] = [1]
        selected = self.runner.eligible(self.runner.issue, 'owner')
        self.assertEqual(selected[1]['id'], cm['id'])
        self.assertNotIn('reporting_operation', selected[1])
        self.assertEqual(before, self.runner.journal())

    def test_rejected_ack_does_not_reconcile_or_mutate_publication(self):
        self.start(); self.runner.put_error=True
        with self.assertRaises(PolicyError): self.poll()
        self.acknowledgement(lambda a: a.update(recipient_chat='old-chat'))
        before = self.runner.journal()
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(before, self.runner.journal())
        self.assertFalse((Path(self.req['receipt_root'])/'publication.json').exists())

    def test_existing_adapter_and_evidence_roots_are_never_adopted(self):
        self.start()
        Path(self.req['base']).mkdir(mode=0o700)
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(self.runner.claims, 0)
        self.assertFalse((self.runner.state_dir/r.JOURNAL).exists())

    def test_canonical_path_alias_size_and_extra_request_keys_before_mutation(self):
        for change in (lambda v: v['request'].update(extra=True),
                       lambda v: v['request'].update(version=True),
                       lambda v: v['storage'].update(path=str(self.enclosing)+'/'),
                       lambda v: v.update(operation='different-cycle'),
                       lambda v: v['request'].update(parent_output=str(self.enclosing/'bad.json'))):
            original = deepcopy(self.value)
            change(self.value); self.runner.messages=[]; self.start()
            with self.assertRaises(PolicyError): self.poll()
            self.assert_no_op(); self.value = original
        # Selection size limit is checked from authenticated tree metadata first.
        raw = io.encode(self.value) + b' ' * r.LIMIT
        self.selection = self.runner.pin('selections/start.json', raw)
        self.runner.messages=[]; self.command('start')
        with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()

    def test_stale_movies_preserve_independently_selected_phase_and_eight_task_history(self):
        journals = self.root/'synthetic-selected-journals'
        parent_fixture(journals, issue=119)
        state_file = journals/'119/state.json'
        state_file.write_bytes(io.encode({'consumed': list(range(1, 9))}))
        engineering = snapshot()
        engineering['goals'][0]['issue'] = 122
        engineering['github']['issues']['items'][0]['number'] = 122
        engineering['github']['comments']['122'] = engineering['github']['comments'].pop('111')
        contents = {'engineering': engineering,
                    'parent_status': parent.export_parent(journals, 119, list(range(1, 9)), NOW)}
        manifest = cycles.empty_manifest()
        selected = {}
        for entry in manifest['sources']:
            name = entry['id']
            if name not in contents: continue
            raw = io.encode(contents[name])
            selected[name] = self.runner.pin('selected/'+name+'.json', raw)
            entry.update(path=name+'.json', sha256=io.digest(raw), collected_at=NOW)
            if name == 'engineering': entry.update(revision=HEAD, observed_at=NOW)
        raw = io.encode(manifest)
        selected['manifest'] = self.runner.pin('selected/manifest.json', raw)
        self.value['independent'] = selected
        self.req['evidence_manifest_sha256'] = io.digest(raw)
        self.originals = {name: raw.replace(str(NOW).encode(), str(NOW-200000).encode())
                          for name, raw in self.originals.items()}
        self.start(); self.poll()
        report = json.loads(self.runner.remote_file)['report']
        self.assertEqual(report['movies']['status'], 'unavailable')
        self.assertEqual(report['sources']['engineering']['status'], 'available')
        self.assertEqual(report['parent']['tasks'], list(range(1,9)))
        self.assertEqual(report['parent']['records']['state']['value']['consumed'], list(range(1,9)))
        self.assertTrue(any(task['issue'] == 122 for task in report['tasks']))

    def test_pin_tree_symlink_alias_unexpected_mode_and_sha_fail_before_claim(self):
        self.start()
        real_api = self.runner.api
        def linked(endpoint, **data):
            value = real_api(endpoint, **data)
            if '/git/trees/' in endpoint and value['tree'][0].get('type') == 'blob':
                value['tree'][0]['mode'] = '120000'
            return value
        with patch.object(self.runner, 'api', side_effect=linked):
            with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()

    def test_lock_owner_and_dry_run_cannot_bypass_ordinary_poll(self):
        self.start()
        self.runner.args.dry_run = True
        self.poll(); self.assert_no_op()
        self.runner.args.dry_run = False
        selected = r.select(self.runner.messages, self.runner.issue, r.REPOSITORY)
        with self.assertRaises(PolicyError): r.operate(self.runner, self.runner.issue, selected, 'owner')
        self.assert_no_op()
        with worker.lock(self.runner.state_dir/'runner.lock'):
            with self.assertRaises(PolicyError): self.poll()
        self.assert_no_op()

    def test_existing_destination_and_lost_readback_cannot_grant_second_put(self):
        self.start()
        self.runner.remote_file = b'existing'
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(self.runner.puts, 0)
        self.poll(); self.assertEqual(self.runner.puts, 0)

    def test_ack_conflict_rejected_before_receipt_or_archive(self):
        self.start(); self.poll(); self.acknowledgement()
        self.acknowledgement(lambda a: a.update(ingestion_reference='conflicting-ingestion'))
        before = self.runner.journal()
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(before, self.runner.journal())
        self.assertFalse((Path(self.req['receipt_root'])/'recipient.json').exists())
        self.assertFalse(owner.inspect(self.req)['archived'])

    def test_archive_crash_restart_keeps_original_receipts_exact_and_no_resend(self):
        self.start(); self.poll(); self.acknowledgement()
        original = owner.archive
        def crash_after(req):
            original(req)
            raise Crash()
        with patch.object(owner, 'archive', side_effect=crash_after):
            with self.assertRaises(Crash): self.poll()
        self.assertTrue(owner.inspect(self.req)['archived'])
        before = (Path(self.req['receipt_root'])/'recipient.json').read_bytes()
        self.poll()
        self.assertEqual(self.runner.journal()['status'], 'archived')
        self.assertEqual(before, (Path(self.req['receipt_root'])/'recipient.json').read_bytes())
        self.assertEqual((self.runner.acquisitions, self.runner.puts), (1, 1))

    def test_publication_import_crash_reuses_exact_retained_observation(self):
        self.start()
        original = owner.receipt
        def crash_publication(req, kind, evidence_id):
            original(req, kind, evidence_id)
            if kind == 'publication': raise Crash()
        with patch.object(owner, 'receipt', side_effect=crash_publication):
            with self.assertRaises(Crash): self.poll()
        before = (Path(self.req['receipt_root'])/'publication.json').read_bytes()
        self.command('reconcile'); self.poll()
        self.assertEqual(before, (Path(self.req['receipt_root'])/'publication.json').read_bytes())
        self.assertEqual(self.runner.puts, 1)


class TransportTests(unittest.TestCase):
    def test_remote_chain_exact_uid_spelling_symlink_and_ancestor_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); root.chmod(0o700)
            (root/'incoming').mkdir(mode=0o700)
            for name in t.PATHS:
                (root/name).write_bytes(b'original bytes\n'); (root/name).chmod(0o600)
            real_stat, real_fstat = os.stat, os.fstat
            shared = {(p.stat().st_dev, p.stat().st_ino) for p in root.parents}
            def safe(s):
                if (s.st_dev, s.st_ino) in shared:
                    values = list(s); values[0] &= ~0o022
                    return os.stat_result(values)
                return s
            with patch.object(t.os, 'stat', side_effect=lambda *a, **k: safe(real_stat(*a, **k))), \
                    patch.object(t.os, 'fstat', side_effect=lambda *a, **k: safe(real_fstat(*a, **k))), \
                    patch.object(t, 'acl', return_value=None):
                ancestors = [Path('/').joinpath(*root.parts[1:i]) for i in range(1,len(root.parts)+1)]
                config = dict(root=str(root), uid=os.getuid(), gid=os.getgid(),
                              ancestors=[[p.stat().st_dev, p.stat().st_ino, p.stat().st_uid,
                                          p.stat().st_gid, p.stat().st_mode] for p in ancestors])
                if os.geteuid() == 0:
                    with self.assertRaises(ValueError): t.remote(config)
                    return
                self.assertEqual(set(t.remote(config)['files']), set(t.PATHS))
                config['ancestors'][-1][1] += 1
                with self.assertRaises(ValueError): t.remote(config)
                config['ancestors'][-1][1] -= 1
                with patch.object(t, 'exact', return_value=False):
                    with self.assertRaises(ValueError): t.remote(config)
                saved = (root/'incoming').rename(root/'saved')
                (root/'incoming').symlink_to(saved, target_is_directory=True)
                with self.assertRaises(OSError): t.remote(config)

    def test_source_size_hardlink_uid_acl_and_read_race_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); root.chmod(0o700)
            path = root/'review-report.json'; path.write_bytes(b'original'); path.chmod(0o600)
            with io.directory(root) as fd, patch.object(t, 'acl', return_value=None):
                with patch.object(t, 'LIMIT', 2):
                    self.assertEqual(t.read_export(fd, path.name, os.getuid())['status'], 'oversized')
                with self.assertRaises(ValueError): t.read_export(fd, path.name, os.getuid()+1)
                os.link(path, root/'hardlink')
                with self.assertRaises(ValueError): t.read_export(fd, path.name, os.getuid())
                (root/'hardlink').unlink()
                real_read = os.read
                def race(target, amount):
                    raw = real_read(target, amount)
                    path.write_bytes(b'changed while read')
                    return raw
                with patch.object(t.os, 'read', side_effect=race):
                    with self.assertRaises(ValueError): t.read_export(fd, path.name, os.getuid())
            with patch.object(t.os, 'getxattr', return_value=b'extended-acl', create=True):
                with self.assertRaises(ValueError): t.acl(0, True)

    def selected(self, root):
        return dict(host='synthetic.invalid', account='synthetic', port=2200,
                    root='/synthetic/source', uid=1234, gid=0, ancestors=[],
                    key={'path': str(root/'key')}, known_hosts={'path': str(root/'known-hosts')})

    def test_fixed_argv_and_native_connection_free_openssh_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ('key', 'known-hosts'):
                (root/name).write_bytes(b'harmless synthetic fixture, not a credential\n')
                (root/name).chmod(0o600)
            selected = self.selected(root)
            argv = t.ssh_argv(selected)
            self.assertEqual(argv[:5], ['/usr/bin/ssh', '-F', '/dev/null', '-T', '-o'])
            self.assertEqual(argv[-2:], ['synthetic@synthetic.invalid', '/usr/bin/python3 -I -B -'])
            for option in ('StrictHostKeyChecking=yes', 'IdentityAgent=none', 'ProxyCommand=none',
                           'IdentitiesOnly=yes', 'ConnectionAttempts=1'):
                self.assertIn(option, argv)
            self.assertIn(str(root/'key'), argv)
            self.assertNotIn('/dev/fd/', ' '.join(argv))
            # -G exits after configuration evaluation; no connection/DNS/server.
            result = subprocess.run(argv[:1]+['-G']+argv[1:], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=5,
                                    env={'PATH': '/usr/bin:/bin', 'LANG': 'C'})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(b'not accessible', result.stderr)
            self.assertIn(('identityfile '+str(root/'key')).encode(), result.stdout)
            self.assertIn(('userknownhostsfile '+str(root/'known-hosts')).encode(), result.stdout)
            script = t.remote_script(selected, (CODE/'automation/coordinator_transport.py').read_bytes())
            compile(script, 'synthetic-helper', 'exec')
            self.assertNotIn(str(root/'key').encode(), script)

    def test_effective_root_wrong_uid_or_gid_fail_before_any_source_access(self):
        for uid, gid in ((0, 0), (1235, 0), (1234, 1)):
            with self.subTest(uid=uid, gid=gid), patch.object(t.os, 'geteuid', return_value=uid), \
                    patch.object(t.os, 'getegid', return_value=gid), patch.object(t, 'chain') as chain:
                with self.assertRaises(ValueError): t.remote(dict(uid=1234, gid=0))
                chain.assert_not_called()

    def test_fixed_remote_deadline_and_no_bytecode_flag(self):
        selected = self.selected(Path('/synthetic'))
        helper = (CODE/'automation/coordinator_transport.py').read_bytes()
        helper += b'\ndef remote(config): time.sleep(10)\n'
        with patch.object(t, 'REMOTE_SECONDS', 1):
            script = t.remote_script(selected, helper)
        started = time.monotonic()
        result = subprocess.run([sys.executable, '-I', '-B', '-'], input=script,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertLess(time.monotonic()-started, 4)

    def test_keeper_holds_both_locks_after_initiator_dies_and_child_closes_fds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            # No network: replace only the SSH launch with one fixed synthetic
            # child that proves its lock FDs are closed and waits for our marker.
            child = """import os,sys,time
from pathlib import Path
root=Path(sys.argv[1])
for fd in map(int,sys.argv[2:]):
    try: os.fstat(fd)
    except OSError: pass
    else: raise AssertionError('child retained lock descriptor')
(root/'ready').write_text('ready')
end=time.monotonic()+5
while not (root/'release').exists() and time.monotonic()<end: time.sleep(.02)
"""
            initiator = """import sys
from pathlib import Path
from automation import coordinator_transport as t
from automation.github_worker import lock
root=Path(sys.argv[1])
original=t.bounded_process
t.LOCAL_SECONDS=6
with lock(root/'dispatcher.lock') as first, lock(root/'runner.lock') as second:
    def synthetic(argv,script,fds):
        assert fds == ()
        return original([sys.executable,'-c',sys.argv[2],str(root),str(first),str(second)],b'',())
    t.bounded_process=synthetic
    selected=dict(host='synthetic.invalid',port=22,account='synthetic',root='/synthetic',uid=1234,gid=0,ancestors=[],key={'path':'/synthetic/key'},known_hosts={'path':'/synthetic/hosts'})
    t.acquire(selected,b'# synthetic',lambda:None,(first,second))
"""
            proc = subprocess.Popen([sys.executable, '-B', '-c', initiator, str(root), child],
                                    cwd=CODE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                end = time.monotonic()+5
                while not (root/'ready').exists() and proc.poll() is None and time.monotonic()<end:
                    time.sleep(.02)
                self.assertTrue((root/'ready').exists())
                proc.kill(); proc.wait(timeout=2)
                for name in ('dispatcher.lock', 'runner.lock'):
                    with self.assertRaises(worker.Stop):
                        with worker.lock(root/name): pass
                (root/'release').write_text('release')
                end = time.monotonic()+5
                while time.monotonic()<end:
                    try:
                        with worker.lock(root/'dispatcher.lock'), worker.lock(root/'runner.lock'): pass
                        break
                    except worker.Stop:
                        time.sleep(.02)
                else:
                    self.fail('keeper did not release locks after its child finished')
            finally:
                (root/'release').write_text('release')
                if proc.poll() is None: proc.kill()
                proc.communicate(timeout=8)

    def test_keeper_runs_pre_and_postchecks_and_bounds_its_single_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            selected = self.selected(root)
            original = t.bounded_process
            def synthetic(argv, script, fds):
                self.assertEqual(argv, t.ssh_argv(selected))
                self.assertEqual(fds, ())
                return original([sys.executable, '-c', 'import time;time.sleep(5)'], b'', ())
            def check():
                with (root/'checks').open('a') as handle: handle.write('checked\n')
            with worker.lock(root/'first') as first, worker.lock(root/'second') as second, \
                    patch.object(t, 'LOCAL_SECONDS', .2), patch.object(t, 'bounded_process', side_effect=synthetic):
                result = t.acquire(selected, b'# fixed helper', check, (first, second))
            self.assertFalse(result['complete'])
            self.assertEqual((root/'checks').read_text(), 'checked\nchecked\n')

    def test_actual_helper_reads_only_fixed_original_bytes_and_refuses_links_acl_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); root.chmod(0o700)
            (root/'incoming').mkdir(mode=0o700)
            for path in t.PATHS:
                (root/path).write_bytes(b'{"generated_at":1}\n')
                (root/path).chmod(0o600)
            ancestors = []
            for p in [Path('/')] + [Path('/').joinpath(*root.parts[1:i]) for i in range(2, len(root.parts)+1)]:
                st = p.stat(); ancestors.append([st.st_dev, st.st_ino, st.st_uid, st.st_gid, st.st_mode])
            # System temporary ancestors are intentionally shared; test the root
            # chain separately and exercise the real fixed file reader here.
            with io.directory(root) as fd, patch.object(t, 'acl', return_value=None):
                result = t.read_export(fd, 'incoming/snapshot.json', os.getuid())
                self.assertEqual(base64.b64decode(result['bytes']), b'{"generated_at":1}\n')
                (root/'review-report.json').unlink()
                (root/'review-report.json').symlink_to(root/'incoming/snapshot.json')
                with self.assertRaises(OSError): t.read_export(fd, 'review-report.json', os.getuid())
                (root/'incoming/snapshot.json').chmod(0o666)
                with self.assertRaises(ValueError): t.read_export(fd, 'incoming/snapshot.json', os.getuid())
            with patch.object(t.os, 'getxattr', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported'), create=True):
                with self.assertRaises(ValueError): t.acl(0, True)

    def test_bounded_process_stdout_stderr_and_deadline_no_live_ssh(self):
        import sys
        result = t.bounded_process([sys.executable, '-c', 'import sys;sys.stdout.write("ok")'], b'', ())
        self.assertTrue(result['complete']); self.assertEqual(result['stdout'], b'ok')
        with patch.object(t, 'OUTPUT_LIMIT', 10):
            result = t.bounded_process([sys.executable, '-c', 'print("x"*100)'], b'', ())
        self.assertFalse(result['complete'])
        with patch.object(t, 'ERROR_LIMIT', 10):
            result = t.bounded_process([sys.executable, '-c', 'import sys;sys.stderr.write("x"*100)'], b'', ())
        self.assertFalse(result['complete']); self.assertLessEqual(len(result['stderr']), 10)


if __name__ == '__main__':
    unittest.main()
