"""Public-safe synthetic issue125 dispatcher/installed-package contracts."""
import base64
from contextlib import redirect_stdout, nullcontext
from copy import deepcopy
import datetime as dt
import hashlib
import inspect
import io as streams
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch

from automation import coordinator_trial as q
from automation import coordinator_runtime as r
from automation import coordinator_sources as sources
from automation import coordinator_owner as owner
from automation import coordinator_storage as storage
from automation import coordinator_cycles as cycles
from automation import coordinator_io as io
from automation import github_worker as worker
from automation.supervisor_policy import PolicyError, PRIVATE_REPOSITORY
from identity_triage_store import digest
import test_coordinator_runtime as runtime_fixture
from test_coordinator_runtime import FakeParent, CODE, NOW, CANARY, stamp, blob
from test_coordinator_recovery import synthetic_pair
from test_coordinator_cycles import Crash

FIRST = NOW // 86400 * 86400 + 11 * 3600 + 30 * 60
if FIRST <= NOW:
    FIRST += 86400


def rehash(report):
    report['versions'] = {row['case_id']: digest({k: v for k, v in row.items() if k != 'observed_at'})
                          for row in report['cases']}
    report['changed_cases'] = deepcopy(report['cases'])


def recurring_pair(now, shape='daily', changed=False):
    movie, report = synthetic_pair(None)
    movie['generated_at'] = report['generated_at'] = now
    for case in movie['cases']:
        case['observed_at'] = now
    item = movie['items'][0]
    item['observed_at'] = now
    for p in item['provenance']:
        p['observed_at'] = now
    text = 'Synthetic changed description' if changed else 'Synthetic description'
    item['facts']['torrent_evidence'] = dict(version=1, description=dict(text=text, digest=io.digest(text.encode())),
        nfo=dict(text='', digest=io.digest(b'')), images=[], unavailable_images=0, truncated=False)
    if shape == 'legacy':
        report['budget'] = {'requests': 0}
    else:
        period = 'day' if shape == 'daily' else 'week'
        prefix = 'daily' if shape == 'daily' else 'weekly'
        report['budget'] = dict(epoch='recurring-v1', per_version_request_cap=5,
            requests_unknown=0, states={'awaiting_evidence': 1}, proposals=1, provider_suspended=False,
            **{prefix + '_case_cap': 5, prefix + '_request_cap': 25,
               'cases_rolling_' + period: 1, 'requests_rolling_' + period: 3})
    epoch = sources.producer_epoch(report['budget'])
    proposal = report['cases'][0]['proposal']
    proposal.update(evidence_version=sources.evidence_version(item, epoch), created_at=FIRST - 10)
    proposal['result']['evidence'] = [{'method': 'details', 'query': 123,
                                     'result': {'reason': 'ok', 'data': {'id': 123}}}]
    proposal['result']['candidates'] = [{'record': {'id': 123, 'type': 'movie'}}]
    for row, case in zip(report['cases'], movie['cases']):
        row.update(case)
    rehash(report)
    return movie, report


class TrialParent(FakeParent):
    def __init__(self, root):
        super().__init__(root)
        self.args.issue = q.ISSUE
        self.select_issue(q.ISSUE)
        self.state_dir.mkdir(mode=0o700)
        self.issue.update(number=q.ISSUE, url=f'https://api.github.com/repos/{r.REPOSITORY}/issues/{q.ISSUE}')
        self.published = {}
        self.put_paths = []

    def pin(self, path, raw):
        value = super().pin(path, raw)
        value['tree'] = value['commit']
        return value

    def git(self, *args):
        if len(args) == 4 and args[:3] == ('ls-tree', 'b' * 40, '--'):
            name = args[3]
            return '100644 blob ' + blob((CODE / name).read_bytes()) + '\t' + name + '\n'
        return super().git(*args)

    def comment(self, command, author='owner', now=NOW, body=None):
        return super().comment(command, author, now, body if body is not None else q.PREFIX + io.encode(command).decode())

    def api(self, endpoint, **data):
        if endpoint == f'repos/{r.REPOSITORY}/issues/{q.ISSUE}':
            return deepcopy(self.issue)
        if endpoint == f'repos/{r.REPOSITORY}/git/commits/' + self.runner_revision:
            return dict(sha=self.runner_revision, tree=dict(sha='c' * 40))
        if endpoint == f'repos/{r.REPOSITORY}/git/refs':
            self.claims += 1
            assert data['ref'] == q.CLAIM and self.journal()['status'] == 'claim_uncertain'
            assert self.claims == 1
            if self.claim_error:
                raise subprocess.CalledProcessError(1, ['synthetic'], stderr=CANARY)
            return {'ref': q.CLAIM, 'object': {'sha': data['sha']}}
        if endpoint == f'repos/{r.REPOSITORY}/git/ref/' + q.CLAIM.removeprefix('refs/'):
            return dict(ref=q.CLAIM, object=dict(sha='b' * 40))
        prefix = 'repos/' + PRIVATE_REPOSITORY + '/contents/'
        if endpoint.startswith(prefix) and endpoint.endswith('?ref=main'):
            if self.readback_error:
                raise subprocess.CalledProcessError(1, ['synthetic'], stderr=CANARY)
            path = endpoint[len(prefix):-len('?ref=main')]
            if path not in self.published:
                raise subprocess.CalledProcessError(1, ['synthetic'], stderr='HTTP 404')
            raw = self.published[path]
            return dict(path=path, sha=blob(raw), type='file', encoding='base64',
                        content=base64.b64encode(raw).decode())
        return super().api(endpoint, **data)

    def run(self, command, **kwargs):
        assert command[:2] == ['gh', 'api'] and '--method' in command and 'PUT' in command
        path = command[2].split('/contents/')[1]
        assert path not in self.put_paths and path not in self.published
        self.put_paths.append(path)
        self.puts += 1
        n = path.rsplit('/', 1)[1].split('.')[0].split('-')[-1]
        assert self.journal()['slots'][n]['status'] == 'publication_uncertain'
        data = json.loads(kwargs['input'])
        assert set(data) == {'message', 'branch', 'content'}
        raw = base64.b64decode(data['content'])
        self.published[path] = raw
        self.remote_file = raw
        selected = self.pin(path, raw)
        self.current_commit = selected['commit']
        if self.put_error:
            raise subprocess.CalledProcessError(1, ['synthetic'], stderr=CANARY)
        return json.dumps(dict(commit=dict(sha=selected['commit']), content=dict(sha=selected['blob'])))

    def journal(self):
        return io.decode((self.state_dir / q.JOURNAL).read_bytes())


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.f = runtime_fixture.RuntimeTests()
        with patch('test_coordinator_runtime.pair', side_effect=synthetic_pair):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        f = self.f
        other = f.root / 'trial-parent'
        other.mkdir(mode=0o700)
        self.p = TrialParent(other)
        self.clock = NOW
        self.clock_patch = patch.object(r.time, 'time', side_effect=lambda: self.clock)
        self.clock_patch.start(); self.addCleanup(self.clock_patch.stop)
        self.transport_patch = patch.object(r.transport, 'acquire', side_effect=self.acquire)
        self.transport_patch.start(); self.addCleanup(self.transport_patch.stop)
        self.value = {k: deepcopy(v) for k, v in f.value.items()
                      if k not in ('operation', 'request', 'independent')}
        self.value.update(issue=q.ISSUE, phase=q.PHASE, recipient_chat=q.CHAT,
            producer_identity='unknown', installed_schedule='unknown',
            code_sha256={name: io.digest((CODE / name).read_bytes()) for name in q.MANIFEST},
            windows=[dict(slot=n, start=stamp(FIRST + (n-1)*86400), end=stamp(FIRST + (n-1)*86400 + 600))
                     for n in range(1, 8)], requests=[], local_chains={})
        base = f.enclosing / 'trial-adapter'
        for n in range(1, 8):
            req = owner.request(base, q.PHASE, 'owner', 'day-' + str(n), NOW,
                base / ('intake-' + str(n)), base / 'cycles', base / ('evidence-' + str(n)),
                base / ('receipts-' + str(n)), f.staging / ('day-' + str(n) + '.json'),
                'existing-exports-only', self.value['source']['root'],
                dict(repository=PRIVATE_REPOSITORY, path='operations/issue-125/day-' + str(n) + '.json'), q.CHAT)
            del req['now']
            self.value['requests'].append(req)
        for name, path in dict(storage=f.enclosing, staging=f.staging, key_parent=f.ssh, known_hosts_parent=f.ssh).items():
            grant = storage.Grant(dict(version=1, path=str(path), expected='unused'), {}, [], lambda _: None)
            grant.home = str(f.home)
            with grant.chain(path, guard=True) as (_, observed):
                self.value['local_chains'][name] = observed
        self.selection = None
        self.changed = False
        self.stale = False

    def acquire(self, *args, **kwargs):
        self.p.acquisitions += 1
        journal = self.p.journal()
        entry = next(v for v in journal['slots'].values() if v['request'] and v['request']['now'] == self.clock)
        self.assertEqual(entry['status'], 'acquisition_uncertain')
        self.assertTrue((Path(entry['request']['base']) / owner.intent_name(entry['request'])).exists())
        self.assertEqual(kwargs['lock_fds'], self.p.inherited_locks())
        movie, report = recurring_pair(self.clock - (4000 if self.stale else 0), changed=self.changed)
        raw = [io.encode(movie), io.encode(report)]
        files = {path: dict(status='read', bytes=base64.b64encode(content).decode(), sha256=io.digest(content),
                           metadata=[1, 1, 1234, 0, stat.S_IFREG | 0o600, len(content), 1, 1, 1])
                 for path, content in zip(owner.FIXED_PATHS, raw)}
        return dict(complete=True, returncode=0, stdout=io.encode(dict(version=1, files=files)), stderr=b'')

    def command(self, action, **extra):
        return self.p.comment(dict(action=action, phase=q.PHASE, selection=self.selection, **extra), now=self.clock)

    def activate(self):
        self.selection = self.p.pin('selected/trial.json', io.encode(self.value))
        self.command('activate')
        self.poll()

    def poll(self):
        with redirect_stdout(streams.StringIO()) as output:
            with worker.lock(self.p.dispatch_dir / 'dispatcher.lock') as self.p.global_lock_fd:
                self.p.poll()
        self.assertNotIn(CANARY, output.getvalue())

    def day(self, n, late=False):
        self.clock = FIRST + (n - 1) * 86400 + (600 if late else 1)
        self.poll()
        return self.p.journal()['slots'][str(n)]

    def ack(self, n, change=None):
        entry = self.p.journal()['slots'][str(n)]
        value = dict(version=1, phase=q.PHASE, slot=n, selection=self.selection, binding=entry['attempt'],
            recipient_chat=q.CHAT, ingestion_reference='actual-distinct-synthetic-ingestion-' + str(n),
            observed_at=self.clock, publication=entry['publication'])
        if change:
            change(value)
        selected = self.p.pin('selected/ack-' + str(n) + '.json', io.encode(value))
        self.command('ack', slot=n, acknowledgement=selected)

    def test_seven_windows_quiet_missed_restart_archive_and_no_eighth(self):
        self.activate()
        self.assertEqual((self.p.claims, self.p.acquisitions, self.p.puts), (1, 0, 0))
        with patch.object(q, 'fetch', side_effect=AssertionError('not due private fetch')):
            self.poll()
        self.assertEqual(self.day(1)['status'], 'published')
        req = self.p.journal()['slots']['1']['request']
        self.assertFalse(owner.inspect(req)['archived'])
        self.ack(1); self.poll()
        self.assertTrue(owner.inspect(req)['archived'])
        self.assertEqual(self.day(2)['status'], 'quiet')
        self.assertEqual(self.p.puts, 1)
        self.assertIsNone(self.p.journal()['slots']['2']['acknowledgement'])
        self.assertEqual(self.day(3, late=True)['status'], 'missed')
        self.changed = True
        self.assertEqual(self.day(4)['status'], 'published')
        self.ack(4); self.poll()
        self.stale = True
        self.assertEqual(self.day(5)['status'], 'published')
        report = io.decode(self.p.remote_file)['report']
        self.assertEqual(report['sources']['investigations']['status'], 'stale')
        self.assertEqual(report['movies']['status'], 'unavailable')
        self.ack(5); self.poll()
        self.assertEqual(self.day(6, late=True)['status'], 'missed')
        self.assertEqual(self.day(7, late=True)['status'], 'missed')
        self.assertEqual(self.p.acquisitions, 4)
        self.clock += 86400 * 30
        before = (self.p.claims, self.p.acquisitions, self.p.puts)
        # Restart re-reads durable records; no in-memory schedule is required.
        self.p.select_issue(q.ISSUE)
        with patch.object(q, 'fetch', side_effect=AssertionError('completed private fetch')):
            self.poll()
        self.assertEqual(before, (self.p.claims, self.p.acquisitions, self.p.puts))
        self.command('reconcile', slot=8)
        with self.assertRaises(worker.Stop): self.poll()

    def test_rollback_busy_lock_and_missed_no_catchup(self):
        self.activate()
        self.day(1)
        self.clock = NOW
        with patch.object(q, 'fetch', side_effect=AssertionError('rollback private fetch')): self.poll()
        self.clock = FIRST + 86400 + 1
        # A competing process owns the actual issue lock. No selected effect.
        process = subprocess.Popen([sys.executable, '-I', '-B', '-S', '-c',
            'import fcntl,os,sys;f=os.open(sys.argv[1],os.O_RDWR);fcntl.flock(f,fcntl.LOCK_EX);print("locked",flush=True);sys.stdin.read()',
            str(self.p.state_dir / 'runner.lock')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'locked')
            with self.assertRaises(worker.Stop): self.poll()
        finally:
            process.communicate('', timeout=10)
        self.clock += 600
        self.poll()
        self.assertEqual(self.p.journal()['slots']['2']['status'], 'missed')
        self.assertEqual(self.p.acquisitions, 1)

    def test_put_uncertainty_readback_only_and_real_ack(self):
        self.activate(); self.p.put_error = True
        with self.assertRaises(PolicyError): self.day(1)
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'publication_uncertain')
        self.poll(); self.assertEqual(self.p.puts, 1)
        self.command('reconcile', slot=1)
        self.poll()
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'published')
        self.ack(1); self.poll()
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'archived')
        self.assertEqual((self.p.acquisitions, self.p.puts), (1, 1))

    def test_claim_interruption_is_consumed_no_retry(self):
        self.p.claim_error = True
        with self.assertRaises(PolicyError): self.activate()
        self.assertEqual(self.p.journal()['status'], 'claim_uncertain')
        self.clock = FIRST + 1
        self.poll()
        self.assertEqual((self.p.claims, self.p.acquisitions), (1, 0))

    def test_installed_hash_map_must_match_regular_blobs_in_reviewed_commit(self):
        original = self.p.git
        def mismatched(*args):
            if args[:1] == ('ls-tree',):
                return '100644 blob ' + '0' * 40 + '\t' + args[-1] + '\n'
            return original(*args)
        with patch.object(self.p, 'git', side_effect=mismatched):
            with self.assertRaises(PolicyError): self.activate()
        self.assertEqual((self.p.claims, self.p.acquisitions, self.p.puts), (0, 0, 0))

    def test_issue125_three_consumed_slots_preserves_other_limits(self):
        from test_github_worker import TASK
        self.p.comment({}, body=TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 3'))
        self.p.state['consumed'] = [1, 2]
        self.assertIsNotNone(self.p.eligible(self.p.issue, 'owner'))
        self.p.state['consumed'] = [1, 2, 3]
        self.assertIsNone(self.p.eligible(self.p.issue, 'owner'))
        self.p.messages[0]['body'] = TASK.replace('SUPERVISOR_TASK: 1', 'SUPERVISOR_TASK: 4')
        with self.assertRaises(worker.Stop): self.p.eligible(self.p.issue, 'owner')
        self.assertEqual(self.p.state['consumed'], [1, 2, 3])
        self.assertEqual(self.p.claims, 0)

    def test_acquisition_interruption_burns_slot(self):
        self.activate()
        with patch.object(r.transport, 'acquire', side_effect=Crash):
            with self.assertRaises(Crash): self.day(1)
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'acquisition_uncertain')
        with patch.object(r.transport, 'acquire', side_effect=AssertionError('no retry')): self.poll()
        self.assertEqual(self.day(2)['status'], 'published')

    def test_authentication_code_and_exact_manifest_refusals(self):
        for mutate in (
            lambda v: v['windows'][-1].update(slot=8),
            lambda v: v['windows'][1].update(start=v['windows'][0]['start']),
            lambda v: v.update(recipient_chat='wrong-chat'),
            lambda v: v.update(installed_schedule='verified'),
            lambda v: v['code_sha256'].pop('torrent_research_evidence.py'),
            lambda v: v['local_chains']['storage'][-1].update(acl='wrong'),
            lambda v: v['source']['key'].update(ino=0),
            lambda v: v['requests'][1].update(parent_output=v['requests'][0]['parent_output']),
        ):
            value = deepcopy(self.value); mutate(value)
            selected = self.p.pin('selected/bad.json', io.encode(value))
            self.p.messages = []
            self.p.comment(dict(action='activate', phase=q.PHASE, selection=selected))
            with self.assertRaises(PolicyError): self.poll()
            self.assertEqual((self.p.claims, self.p.acquisitions, self.p.puts), (0, 0, 0))

    def test_wrong_chat_time_binding_ack_and_replay_rejected(self):
        for change in (lambda a: a.update(recipient_chat='wrong'), lambda a: a.update(slot=2),
                       lambda a: a.update(observed_at=NOW - 1),
                       lambda a: a['binding'].update(payload_sha256='0'*64),
                       lambda a: a.update(issuer='trusted', trusted=True)):
            f = TrialTests(); f.setUp()
            try:
                f.activate(); f.day(1); f.ack(1, change)
                with self.assertRaises(PolicyError): f.poll()
                self.assertIsNone(f.p.journal()['slots']['1']['acknowledgement'])
                with patch.object(q, 'fetch', side_effect=AssertionError('consumed invalid ack fetch')): f.poll()
            finally:
                f.doCleanups()
        self.activate(); self.day(1)
        self.ack(1); self.poll(); self.poll()
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'archived')

    def test_actual_seven_acquisitions_and_exact_byte_archives(self):
        self.activate()
        for n in range(1, 8):
            self.changed = n % 2 == 0
            entry = self.day(n)
            if entry['status'] == 'published':
                raw = self.p.published[entry['request']['destination']['path']]
                self.assertEqual(io.digest(raw), entry['attempt']['payload_sha256'])
                self.ack(n); self.poll()
                result = owner.inspect(entry['request'])
                self.assertTrue(result['archived'])
                record = Path(entry['request']['cycle_root']) / 'archive' / (entry['attempt']['report'] + '.json')
                self.assertEqual(io.decode(record.read_bytes())['payload'].encode(), raw)
        self.assertEqual(self.p.acquisitions, 7)
        self.assertEqual(self.p.claims, 1)
        self.clock += 86400
        self.poll()
        self.assertEqual(self.p.acquisitions, 7)

    def test_stop_done_closed_untrusted_edited_and_superseding_engineering(self):
        self.activate()
        messages = deepcopy(self.p.messages)
        self.clock = FIRST + 1
        for kind in ('stop', 'done', 'closed', 'untrusted', 'edited', 'engineering'):
            self.p.messages = deepcopy(messages)
            self.p.issue['state'] = 'open'
            if kind == 'stop':
                self.command('stop')
            elif kind == 'done':
                self.p.comment({}, now=self.clock, body='STATE: DONE')
            elif kind == 'closed':
                self.p.issue['state'] = 'closed'
            elif kind == 'untrusted':
                self.p.messages = []
                self.p.comment(dict(action='activate', phase=q.PHASE, selection=self.selection), author='attacker')
            elif kind == 'edited':
                self.p.messages[0]['updated_at'] = stamp(self.clock)
            else:
                from test_github_worker import TASK
                self.p.comment({}, body=TASK)
            if kind == 'edited':
                with self.assertRaises(worker.Stop): self.poll()
            elif kind == 'engineering':
                with patch.object(self.p, 'run_selected', return_value=None) as engineering:
                    self.poll(); self.assertEqual(engineering.call_count, 1)
            else:
                with patch.object(q, 'fetch', side_effect=AssertionError('stopped private fetch')): self.poll()
            self.assertEqual(self.p.acquisitions, 0)

    def test_reservation_prepare_handoff_and_receipt_interruption_boundaries(self):
        # Isolated fixtures per boundary preserve the original evidence, rather
        # than resetting any consumed slot during a single trial.
        for target in ('reserve', 'prepare', 'handoff', 'receipt', 'archive'):
            f = TrialTests(); f.setUp()
            try:
                f.activate()
                original = getattr(owner, target)
                def interrupted(*args, **kw):
                    result = original(*args, **kw)
                    raise Crash()
                if target in ('receipt', 'archive'):
                    f.day(1); f.ack(1)
                    with patch.object(owner, target, side_effect=interrupted):
                        with self.assertRaises(Crash): f.poll()
                    f.poll()
                    self.assertEqual(f.p.journal()['slots']['1']['status'], 'archived')
                else:
                    with patch.object(owner, target, side_effect=interrupted):
                        with self.assertRaises(Crash): f.day(1)
                    before = (f.p.acquisitions, f.p.puts)
                    f.poll()
                    self.assertEqual(before, (f.p.acquisitions, f.p.puts))
            finally:
                f.doCleanups()

    def test_reconcile_interruption_and_two_attempt_bound(self):
        self.activate(); self.p.put_error = True
        with self.assertRaises(PolicyError): self.day(1)
        self.command('reconcile', slot=1)
        original = owner.receipt
        def crash(*args, **kwargs):
            original(*args, **kwargs)
            raise Crash()
        with patch.object(owner, 'receipt', side_effect=crash):
            with self.assertRaises(Crash): self.poll()
        self.poll()
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'published')
        self.assertEqual(self.p.puts, 1)

    def test_exact_two_failed_readback_commands_no_third_no_second_put(self):
        self.activate(); self.p.put_error = True
        with self.assertRaises(PolicyError): self.day(1)
        self.p.readback_error = True
        for attempt in range(2):
            self.command('reconcile', slot=1)
            with self.assertRaises(PolicyError): self.poll()
            with patch.object(q, 'fetch', side_effect=AssertionError('consumed readback private fetch')): self.poll()
        self.command('reconcile', slot=1)
        with self.assertRaises(worker.Stop): self.poll()
        self.assertEqual((self.p.acquisitions, self.p.puts), (1, 1))

    def test_trial_symlink_mode_owner_race_and_backpressure_refusals(self):
        for problem in ('key-symlink', 'staging-symlink', 'owner', 'source-mode', 'race', 'capacity'):
            f = TrialTests(); f.setUp()
            try:
                if problem == 'key-symlink':
                    key = f.f.ssh / 'key'
                    key.rename(f.f.ssh / 'original-key'); key.symlink_to('original-key')
                elif problem == 'staging-symlink':
                    stage = f.f.staging
                    stage.rename(stage.with_name('original-staging')); stage.symlink_to('original-staging', target_is_directory=True)
                elif problem == 'source-mode':
                    f.value['source']['ancestors'][-1][4] |= 0o020
                if problem in ('key-symlink', 'staging-symlink', 'source-mode'):
                    with self.assertRaises(PolicyError): f.activate()
                    self.assertEqual((f.p.claims, f.p.acquisitions), (0, 0))
                else:
                    f.activate()
                    if problem == 'owner':
                        actual = os.fstat
                        key_id = (f.f.ssh / 'key').stat().st_ino
                        def owner_changed(fd):
                            value = actual(fd)
                            if value.st_ino == key_id:
                                fields = list(value); fields[4] = value.st_uid + 1
                                return os.stat_result(fields)
                            return value
                        with patch.object(os, 'fstat', side_effect=owner_changed):
                            with self.assertRaises(PolicyError): f.day(1)
                        self.assertEqual(f.p.acquisitions, 0)
                    elif problem == 'capacity':
                        with patch.object(owner, 'MAX_INTENTS', 0):
                            with self.assertRaises(PolicyError): f.day(1)
                        self.assertEqual(f.p.acquisitions, 0)
                    else:
                        real = f.acquire
                        def race(*args, **kwargs):
                            result = real(*args, **kwargs)
                            key = f.f.ssh / 'key'
                            key.rename(f.f.ssh / 'retained-key')
                            key.write_bytes(b'synthetic replacement'); key.chmod(0o600)
                            return result
                        with patch.object(r.transport, 'acquire', side_effect=race):
                            with self.assertRaises(PolicyError): f.day(1)
                        self.assertEqual(f.p.puts, 0)
                        self.assertEqual(f.p.journal()['slots']['1']['status'], 'acquisition_uncertain')
            finally:
                f.doCleanups()

    def test_storage_source_credential_and_capacity_guards(self):
        self.activate()
        original = (self.f.ssh / 'key').stat()
        self.clock = FIRST + 1
        (self.f.ssh / 'key').chmod(0o640)
        with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(self.p.acquisitions, 0)
        self.assertEqual(self.p.journal()['slots']['1']['status'], 'reserved')
        (self.f.ssh / 'key').chmod(stat.S_IMODE(original.st_mode))
        # Existing guard suite supplies actual descriptor/symlink/ACL/race
        # negatives; exercise the new route's pin comparison independently.
        self.clock = FIRST + 86400 + 1
        with patch.object(storage, 'acl_identity', return_value='changed-acl'):
            with self.assertRaises(PolicyError): self.poll()
        self.assertEqual(self.p.acquisitions, 0)

    def test_installed_manifest_only_actual_dispatcher_and_missing_dependencies(self):
        bundle = self.f.root / 'installed'
        bundle.mkdir(mode=0o700)
        for name in q.MANIFEST:
            destination = bundle / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(CODE / name, destination)
        selection = self.p.pin('selected/trial.json', io.encode(self.value))
        fixture = dict(value=self.value, selection=selection, root=str(self.f.root), home=str(self.f.home),
                       registry={key: [path, base64.b64encode(raw).decode()]
                                 for key, (path, raw) in self.p.registry.items()},
                       originals=[io.encode(x).decode() for x in recurring_pair(FIRST + 1)],
                       repeat=[io.encode(x).decode() for x in recurring_pair(FIRST + 86400 + 1)])
        conf = self.f.root / 'isolated.json'
        conf.write_bytes(io.encode(fixture)); conf.chmod(0o600)
        harness = '''
import argparse, base64, contextlib, datetime as dt, hashlib, json, os
from copy import deepcopy
from pathlib import Path
import stat, subprocess, sys, types
from unittest.mock import patch
CODE=Path(sys.argv[1]);sys.path.insert(0,str(CODE))
from automation import coordinator_trial as q, coordinator_runtime as r, github_worker as worker
from automation import coordinator_storage as storage, coordinator_io as io, coordinator_owner as owner
from automation.supervisor_policy import PRIVATE_REPOSITORY
CANARY='SYNTHETIC_PRIVATE_NO_PUBLIC_OUTPUT'
NOW=1800000000
'''+inspect.getsource(blob)+'\n'+inspect.getsource(stamp)+'\n'+inspect.getsource(FakeParent)+'\n'+inspect.getsource(TrialParent)+'''
v=io.decode(Path(sys.argv[2]).read_bytes());root=Path(v['root']);home=Path(v['home'])
clock=[NOW];first=r.timestamp(v['value']['windows'][0]['start'])
# No tests, repository, site-packages or DB/provider functions are available.
stdlib=Path(os.__file__).parent
def audit(event,args):
    if event.startswith(('socket.','subprocess.','sqlite3.')):raise AssertionError('forbidden installed edge')
    if event=='open' and isinstance(args[0],str) and os.path.isabs(args[0]):
        path=Path(args[0])
        if not (any(path==base or base in path.parents for base in (root,stdlib))
                or path in root.parents and args[2]&os.O_DIRECTORY):
            raise AssertionError('undeclared installed file')
sys.addaudithook(audit)
original_stat,original_fstat=os.stat,os.fstat
ancestors={(p.stat().st_dev,p.stat().st_ino) for p in root.parents}
def safe(s):
    if (s.st_dev,s.st_ino) in ancestors:
        a=list(s);a[0]&=~0o022;a[4]=0;return os.stat_result(a)
    return s
with contextlib.ExitStack() as stack:
    stack.enter_context(patch.object(storage.os,'stat',side_effect=lambda *a,**k:safe(original_stat(*a,**k))))
    stack.enter_context(patch.object(storage.os,'fstat',side_effect=lambda *a,**k:safe(original_fstat(*a,**k))))
    stack.enter_context(patch.object(storage.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_dir=str(home))))
    stack.enter_context(patch.object(storage,'acl_identity',return_value='synthetic-acl'))
    stack.enter_context(patch.object(r.time,'time',side_effect=lambda:clock[0]))
    from identity_research_handoff import validate_snapshot
    movie=io.decode(v['originals'][0]);assert movie['items'][0]['facts']['torrent_evidence']
    validate_snapshot(movie,first+1)
    if sys.argv[3]=='validate':
        print('installed-nonempty-validator-ok');raise SystemExit(0)
    target=root/'installed-parent';target.mkdir(mode=0o700)
    p=TrialParent(target)
    p.registry={k:(path,base64.b64decode(raw)) for k,(path,raw) in v['registry'].items()}
    def acquire(*args,**kwargs):
        p.acquisitions+=1
        files={}
        for path,raw in zip(owner.FIXED_PATHS,v['originals'] if p.acquisitions==1 else v['repeat']):
            raw=raw.encode();files[path]=dict(status='read',bytes=base64.b64encode(raw).decode(),
                sha256=io.digest(raw),metadata=[1,1,1234,0,stat.S_IFREG|0o600,len(raw),1,1,1])
        return dict(complete=True,returncode=0,stdout=io.encode(dict(version=1,files=files)),stderr=b'')
    stack.enter_context(patch.object(r.transport,'acquire',side_effect=acquire))
    def command(action,**extra):
        p.comment(dict(action=action,phase=q.PHASE,selection=v['selection'],**extra),now=clock[0])
    def poll():
        with worker.lock(p.dispatch_dir/'dispatcher.lock') as p.global_lock_fd:p.poll()
    command('activate');poll();assert p.acquisitions==0
    clock[0]=first+1;poll();j=p.journal()['slots']['1'];assert j['status']=='published'
    payload=io.decode(p.remote_file)
    assert payload['report']['movies']['reason']=='incomplete_upstream'
    assert payload['report']['movies']['research_budget']['daily_case_cap']==5
    ack=dict(version=1,phase=q.PHASE,slot=1,selection=v['selection'],binding=j['attempt'],
        recipient_chat=q.CHAT,ingestion_reference='actual-distinct-isolated-ingestion',observed_at=clock[0],publication=j['publication'])
    selected=p.pin('selected/installed-ack.json',io.encode(ack));command('ack',slot=1,acknowledgement=selected);poll()
    assert p.journal()['slots']['1']['status']=='archived' and owner.inspect(j['request'])['archived']
    clock[0]=first+86400+1;poll();assert p.journal()['slots']['2']['status']=='quiet'
    for n in range(3,8):
        clock[0]=first+(n-1)*86400+600;poll();assert p.journal()['slots'][str(n)]['status']=='missed'
    clock[0]+=86400
    with patch.object(q,'fetch',side_effect=AssertionError('completed private fetch')):poll()
    assert (p.claims,p.acquisitions,p.puts)==(1,2,1)
print('installed-dispatcher-seven-slot-archive-ok')
'''
        command = [sys.executable, '-I', '-B', '-S', '-c', harness, str(bundle), str(conf), 'validate']
        for missing in ('identity_research_store.py', 'torrent_research_evidence.py'):
            path = bundle / missing
            path.rename(path.with_suffix('.withheld'))
            result = subprocess.run(command, cwd=self.f.root, env={'PATH': os.defpath}, capture_output=True, text=True, timeout=90)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ModuleNotFoundError', result.stderr)
            self.assertIn(missing[:-3], result.stderr)
            path.with_suffix('.withheld').rename(path)
        result = subprocess.run(command, cwd=self.f.root, env={'PATH': os.defpath}, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        command[-1] = 'trial'
        result = subprocess.run(command, cwd=self.f.root, env={'PATH': os.defpath}, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('installed-dispatcher-seven-slot-archive-ok', result.stdout)


class EvidenceContractTests(unittest.TestCase):
    def test_synthetic_408_known_17_current_and_each_wrong_version(self):
        movie, report = recurring_pair(FIRST)
        base, row, item = deepcopy(movie['cases'][0]), deepcopy(report['cases'][0]), deepcopy(movie['items'][0])
        movie['cases'], movie['items'], report['cases'] = [], [], []
        for n in range(408):
            case = deepcopy(base)
            case['case_id'] = 'outcome-' + digest(['synthetic-case', n])
            case['route'] = 'eligible' if n < 17 else 'review_only'
            case['version'] = digest(['synthetic-base', n])
            movie['cases'].append(case)
            output = deepcopy(row); output.update(case)
            if n < 17:
                current = deepcopy(item)
                current['case_id'] = case['case_id']
                current['provenance'][0]['digest'] = case['version']
                movie['items'].append(current)
                output['proposal']['evidence_version'] = sources.evidence_version(current, 'recurring-v1')
            else:
                output['proposal'] = None
            report['cases'].append(output)
        movie['coverage']['assessed_release_cases'] = 408
        report['coverage'] = deepcopy(movie['coverage'])
        rehash(report)
        result = sources.movie_pair(movie, report, FIRST)
        self.assertEqual((len(result['known_cases']), len(result['eligible_versions'])), (408, 17))
        for n in range(17):
            wrong = deepcopy(report)
            wrong['cases'][n]['proposal']['evidence_version'] = '0' * 64
            rehash(wrong)
            with self.assertRaisesRegex(ValueError, 'movie_proposal_version'):
                sources.movie_pair(movie, wrong, FIRST)

    def test_supported_shapes_timestamps_and_material_evidence(self):
        from identity_research_store import ResearchStore
        from identity_recurring_store import RecurringStore
        class Recorder:
            """Capture the real public writer's digest, without a DB or Store init."""
            def execute(self, sql, args=()):
                self.sql = sql
                if sql.startswith('insert into evidence'):
                    self.version = args[0]
                return self
            def fetchone(self):
                return (0,) if self.sql.startswith('select count(') else None
        for shape in ('legacy', 'daily', 'weekly'):
            movie, report = recurring_pair(FIRST, shape)
            result = sources.movie_pair(movie, report, FIRST)
            if shape == 'legacy':
                self.assertNotIn('research_budget', result)  # Retained legacy comparisons remain quiet.
            else:
                self.assertEqual(result['research_budget'], report['budget'])
            item = movie['items'][0]
            before = sources.evidence_version(item, sources.producer_epoch(report['budget']))
            writer_type = ResearchStore if shape == 'legacy' else RecurringStore
            writer = writer_type.__new__(writer_type)
            recorded = Recorder()
            writer.tx = lambda: nullcontext(recorded)
            writer.clock = lambda: FIRST
            with patch('sqlite3.connect', side_effect=AssertionError('no fixture DB')):
                self.assertEqual(writer.admit(item), 'admitted')
            self.assertEqual(before, recorded.version)
            item['observed_at'] += 30
            self.assertEqual(before, sources.evidence_version(item, sources.producer_epoch(report['budget'])))
            item['provenance'][0]['observed_at'] += 30
            after = sources.evidence_version(item, sources.producer_epoch(report['budget']))
            self.assertEqual(before == after, shape != 'legacy')
            item['facts']['torrent_evidence']['description']['text'] += ' changed'
            self.assertNotEqual(after, sources.evidence_version(item, sources.producer_epoch(report['budget'])))

    def test_incorrect_versions_epochs_full_sets_and_freshness_fail(self):
        for change in (lambda m, p: p['budget'].update(epoch='unsupported'),
                       lambda m, p: p['cases'][0]['proposal'].update(evidence_version='0'*64),
                       lambda m, p: p['cases'].pop(),
                       lambda m, p: p.update(coverage={}),
                       lambda m, p: m.update(generated_at=FIRST-3601),
                       lambda m, p: p.update(generated_at=FIRST-172801),
                       lambda m, p: p.update(generated_at=FIRST+301)):
            movie, report = recurring_pair(FIRST)
            change(movie, report); rehash(report)
            with self.assertRaises(ValueError): sources.movie_pair(movie, report, FIRST)

    def test_reader_never_constructs_store_or_enters_database(self):
        movie, report = recurring_pair(FIRST)
        with patch('sqlite3.connect', side_effect=AssertionError('database forbidden')), \
                patch('identity_research_store.ResearchStore.__init__', side_effect=AssertionError('store forbidden')):
            sources.movie_pair(movie, report, FIRST)


if __name__ == '__main__':
    unittest.main()
