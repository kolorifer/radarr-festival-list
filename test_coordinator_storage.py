"""Synthetic parser -> claimed parent -> sole fake child. No host commissioning."""
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from automation import coordinator_storage as c
from automation import github_worker as w
from automation import supervisor_policy as p
import test_supervisor_communication as s
from test_github_worker import TASK, comment

DIRECTIVE = 'COORDINATOR_STORAGE: {"input":"coordinator-storage.json"}\n'


class ParserTests(unittest.TestCase):
    def body(self):
        return (s.task_body([dict(s.INPUT, alias='coordinator-storage.json')])
                + 'PUBLICATION_MODE: operations_only\n' + DIRECTIVE)

    def test_latest_owner_only_and_omission(self):
        old = comment(self.body())
        latest = comment(TASK.replace('TASK: 1', 'TASK: 2'), 2)
        chosen = w.choose_task([old, latest, comment(self.body(), 3, 'stranger')], 'owner', set())
        self.assertIsNone(p.coordinator_storage(chosen, 'owner'))
        with self.assertRaises(p.PolicyError):
            p.coordinator_storage(comment(self.body(), login='stranger'), 'owner')
        self.assertIsNone(w.choose_task([comment(self.body(), login='stranger')], 'owner', set()))
        self.assertIsNone(w.choose_task([old], 'owner', {1}))
        self.assertEqual(p.coordinator_storage(old, 'owner'), {'input': 'coordinator-storage.json'})

    def test_malformed_duplicate_spacing_case_and_incompatible(self):
        valid = self.body()
        variants = [valid + DIRECTIVE, valid.replace(DIRECTIVE, DIRECTIVE.lower()),
                    valid.replace(DIRECTIVE, ' ' + DIRECTIVE),
                    valid.replace('STORAGE: {', 'STORAGE:  {'),
                    valid.replace('STORAGE: {', 'STORAGE:{'),
                    valid.replace(DIRECTIVE, DIRECTIVE.rstrip() + ' \n'),
                    valid.replace('"input":', '"input": '),
                    valid.replace('"input":', '"extra":1,"input":'),
                    valid.replace('"input":', '"input":"x.json","input":'),
                    valid.replace('coordinator-storage.json"}', '../input.json"}'),
                    valid.replace('coordinator-storage.json"}', 'Coordinator-storage.json"}'),
                    valid.replace('operations_only', 'code'),
                    valid.replace('PUBLICATION_MODE: operations_only\n', ''),
                    valid.replace('"alias": "coordinator-storage.json"', '"alias": "input.txt"')]
        variants += ['\n'.join(line for line in valid.splitlines() if not line.startswith(name))
                     for name in ('PRIVATE_ARTIFACT:', 'PRIVATE_DIAGNOSTIC:', 'PRIVATE_INPUTS:')]
        for body in variants:
            with self.subTest(body=body), self.assertRaises(p.PolicyError):
                w.choose_task([comment(body)], 'owner', set())

    def test_strict_selection_and_environment_not_authority(self):
        home = '/synthetic/account'
        value = dict(version=1, path=home+c.SUFFIX, expected='absent')
        with patch.object(c.pwd, 'getpwuid', return_value=types.SimpleNamespace(pw_dir=home)) as lookup, \
                patch.dict(os.environ, HOME='/other', USER='other'):
            self.assertEqual(c.selection(json.dumps(value).encode()), value)
            lookup.assert_called_with(os.geteuid())
            for change in ({'version': True}, {'version': 2}, {'extra': 1},
                           {'expected': {'dev': True, 'ino': 1}}, {'expected': {'dev': 0, 'ino': False}},
                           {'expected': {'dev': -1, 'ino': 2}}, {'expected': {'dev': 0, 'ino': 0}},
                           {'expected': {'dev': 0, 'ino': 1, 'extra': 1}},
                           *({'path': v} for v in ('relative', home+c.SUFFIX+'/', home+c.SUFFIX.upper(),
                              home+'//.local/state/movie-project-coordinator-private',
                              home+'/./.local/state/movie-project-coordinator-private',
                              home+'/../account'+c.SUFFIX, '${HOME}'+c.SUFFIX, '/other'+c.SUFFIX,
                              home+c.SUFFIX+'é', home+'/.local/state/sibling'))):
                with self.subTest(change=change), self.assertRaises(c.StorageError):
                    c.selection(json.dumps(dict(value, **change)).encode())
            for raw in (b'{}', b'null', b'{"version":1,"version":1}', b'NaN',
                        b' '*16385, b'\xff', json.dumps(value).encode()+b' trailing'):
                with self.subTest(raw=raw[:60]), self.assertRaises(c.StorageError): c.selection(raw)


class BoundaryTests(unittest.TestCase):
    setUp = s.IntegrationTests.setUp
    clean_staging = staticmethod(s.IntegrationTests.clean_staging)
    receipt = s.IntegrationTests.receipt

    def configure(self, expected='absent', raw=None):
        if not hasattr(self, 'home'):
            temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
            self.fixture = Path(temporary.name).resolve()
            self.home = self.fixture/'synthetic-home'
            (self.home/'.local'/'state').mkdir(parents=True, mode=0o700)
            self.home.chmod(0o700); (self.home/'.local').chmod(0o700)
            self.target = Path(str(self.home)+c.SUFFIX)
            # Mock only OS-account/ACL and system ancestors of temporary homes.
            # All selected-home/intermediate/target metadata and traversal are real.
            real_stat, real_fstat = os.stat, os.fstat
            ancestors = { (real_stat(v).st_dev, real_stat(v).st_ino)
                          for v in self.fixture.parents }
            def safe(info):
                if (info.st_dev, info.st_ino) in ancestors:
                    values = list(info); values[0] &= ~0o022; values[4] = 0
                    return os.stat_result(values)
                return info
            stat_patch = patch.object(c.os, 'stat', side_effect=lambda *a, **k: safe(real_stat(*a, **k)))
            fstat_patch = patch.object(c.os, 'fstat', side_effect=lambda *a, **k: safe(real_fstat(*a, **k)))
            for mocked in (stat_patch, fstat_patch,
                           patch.object(c.pwd, 'getpwuid', return_value=types.SimpleNamespace(pw_dir=str(self.home))),
                           patch.object(c, 'acl_identity', return_value='synthetic-no-acl')):
                mocked.start(); self.addCleanup(mocked.stop)
        self.selected = dict(version=1, path=str(self.target), expected=expected)
        data = json.dumps(self.selected).encode() if raw is None else raw
        pin = dict(s.INPUT, alias='coordinator-storage.json', blob=s.blob(data), sha256=hashlib.sha256(data).hexdigest())
        mocked = patch.object(s, 'INPUT', pin); mocked.start(); self.addCleanup(mocked.stop)
        self.runner.source = data; self.runner.node_size = len(data)
        self.runner.body = (s.task_body([pin]) + 'PUBLICATION_MODE: operations_only\n' + DIRECTIVE)
        return pin

    def run_task(self):
        return s.IntegrationTests.run_task(self)

    def evidence(self):
        return json.loads((self.runner.state_dir/'storage-grant-1.json').read_text())

    def hook_child(self, before=None, after=None):
        original = self.runner.child
        def child(command, **kwargs):
            if command[0] != 'codex': return original(command, **kwargs)
            grants = [command[i+1] for i, v in enumerate(command) if v == '--add-dir']
            self.assertEqual(grants[1:], [str(self.target)])
            self.assertEqual(len(grants), 2)
            self.assertIn(str(self.target), kwargs['input'])
            self.assertIn('COORDINATOR STORAGE: exact verified enclosing directory', kwargs['input'])
            self.assertIn('workspace-write', command)
            self.assertIn('approval_policy="never"', command)
            self.assertEqual(kwargs['pass_fds'], self.runner.inherited_locks())
            self.assertEqual(len(kwargs['pass_fds']), 2)
            self.assertEqual(command[command.index('--model')+1], w.MODEL)
            self.assertIn('model_reasoning_effort="high"', command)
            if before: before()
            try: return original(command, **kwargs)
            finally:
                if after: after()
        self.runner.child = child

    def assert_refused(self, reason=None, preflight=False):
        with self.assertRaises((w.Stop, c.StorageError, subprocess.CalledProcessError)):
            self.run_task()
        self.assertNotIn(s.AUTH['path'], self.runner.remote_files)
        if preflight:
            self.assertEqual(self.runner.state['consumed'], [])
            self.assertEqual(self.runner.child_count, 0)
        else:
            self.assertEqual(self.receipt()['state'], 'FAILED')
            self.assertIn(self.receipt()['code'], ('EXECUTION_FAILED', 'INPUT_CHANGED', 'CHILD_FAILED', 'PUBLIC_CHANGE_REFUSED'))
            if reason: self.assertEqual(self.evidence()['reason'], reason)
        public = '\n'.join(v for k,v in self.runner.events if k == 'post')
        self.assertNotIn(str(self.home), public)
        self.assertNotIn(str(self.home), json.dumps(self.runner.remote_files.get(s.DIAGNOSTIC['path'], b'').decode()))

    def test_create_only_one_grant_no_adapter_state_and_no_replay(self):
        pin = self.configure(); self.hook_child()
        self.run_task()
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o700)
        self.assertEqual(self.evidence()['source'], pin)
        self.assertEqual(self.evidence()['state'], 'created')
        self.assertEqual(self.evidence()['task'], 1)
        self.assertTrue(all(self.receipt()['verification'].values()))
        self.assertEqual(self.receipt()['code'], 'OK')
        self.run_task(); self.assertEqual(self.runner.child_count, 1)
        self.assertFalse(any(k == 'git-public' for k,v in self.runner.events))

    def test_expected_existing_even_empty_refused(self):
        self.configure(); self.target.mkdir(mode=0o700)
        self.assert_refused('storage_exists'); self.assertEqual(self.runner.child_count, 0)

    def test_missing_state_is_never_created(self):
        self.configure(); (self.home/'.local'/'state').rmdir()
        self.assert_refused('storage_missing'); self.assertFalse(self.target.parent.exists())

    def test_symlink_target_is_never_adopted(self):
        self.configure(); self.target.symlink_to(self.home, target_is_directory=True)
        self.assert_refused('storage_exists'); self.assertTrue(self.target.is_symlink())

    def test_exact_reuse_retains_contents(self):
        self.configure(); self.target.mkdir(mode=0o700)
        (self.target/'retained.txt').write_text('synthetic retained')
        info = self.target.stat(); self.configure({'dev': info.st_dev, 'ino': info.st_ino})
        self.hook_child(); self.run_task()
        self.assertEqual(self.evidence()['state'], 'reused')
        self.assertEqual((self.target/'retained.txt').read_text(), 'synthetic retained')

    def test_missing_reuse_refused_without_creation(self):
        self.configure({'dev': 0, 'ino': 1}); self.assert_refused('storage_missing')
        self.assertFalse(self.target.exists())

    def test_wrong_reuse_identity_refused(self):
        self.configure(); self.target.mkdir(mode=0o700)
        info = self.target.stat(); self.configure({'dev': info.st_dev, 'ino': info.st_ino+1})
        self.assert_refused('storage_identity')

    def test_reuse_unsafe_mode_is_never_repaired(self):
        self.configure(); self.target.mkdir(mode=0o700); self.target.chmod(0o750)
        info = self.target.stat(); self.configure({'dev': info.st_dev, 'ino': info.st_ino})
        self.assert_refused('storage_mode')
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o750)

    def test_failed_and_lost_claim_zero_storage_mutation(self):
        self.configure(); self.runner.fail_claim = True
        with patch.object(c.Grant, 'prepare', side_effect=AssertionError('no prepare')):
            self.run_task()
        self.assertFalse(self.target.exists()); self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.runner.state['consumed'], [1])
        self.assertFalse((self.runner.state_dir/'storage-grant-1.json').exists())
        self.assertFalse(self.runner.remote_files)

    def test_json_failure_before_claim(self):
        self.configure(raw=b'{"version":false}')
        self.assert_refused(preflight=True); self.assertFalse(self.target.exists())

    def test_bad_pin_before_claim(self):
        self.configure(); self.runner.source += b'changed'
        self.assert_refused(preflight=True); self.assertFalse(self.target.exists())

    def test_wrong_absolute_selection_before_claim(self):
        self.configure(raw=b'{"version":1,"path":"/synthetic/wrong","expected":"absent"}')
        self.assert_refused(preflight=True); self.assertFalse(self.target.exists())

    def test_unsafe_home_and_intermediate_modes(self):
        self.configure(); (self.home/'.local').chmod(0o777)
        self.assert_refused('storage_mode'); self.assertFalse(self.target.exists())

    def test_unsafe_ownership(self):
        self.configure(); original = c.os.fstat
        victim = (self.home/'.local').stat().st_ino
        def changed(fd):
            info = original(fd)
            if info.st_ino == victim:
                values = list(info); values[4] = os.geteuid()+1
                return os.stat_result(values)
            return info
        # The mismatch is already unsafe at the entry/descriptor race guard.
        with patch.object(c.os, 'fstat', side_effect=changed):
            self.assert_refused('storage_changed')
        self.assertFalse(self.target.exists())

    def test_shared_acl_refused(self):
        self.configure()
        with patch.object(c, 'acl_identity', side_effect=c.StorageError('storage_acl')):
            self.assert_refused('storage_acl')
        self.assertFalse(self.target.exists())

    def test_symlink_intermediate_refused(self):
        self.configure(); state = self.home/'.local'/'state'
        state.rename(state.with_name('retained-state')); state.symlink_to('retained-state')
        self.assert_refused('storage_filesystem'); self.assertFalse(self.target.exists())

    def test_case_alias_refused(self):
        self.configure(); state = self.home/'.local'/'state'
        state.rename(state.with_name('STATE'))
        # Portable simulation of case-insensitive stat lookup, with real spelling enumeration.
        original = c.os.stat
        def alias(path, *args, **kwargs):
            try: return original(path, *args, **kwargs)
            except FileNotFoundError:
                if path == 'state': return original('STATE', *args, **kwargs)
                raise
        with patch.object(c.os, 'stat', side_effect=alias): self.assert_refused('storage_spelling')

    def test_overlap_refused_before_create(self):
        self.configure(); self.runner.dispatch_dir = self.home/'.local'/'state'
        self.assert_refused('storage_overlap'); self.assertFalse(self.target.exists())

    def test_replaced_target_after_child_refuses_publication(self):
        self.configure()
        def replace():
            self.target.rename(self.target.with_name('retained-original'))
            self.target.mkdir(mode=0o700)
        self.hook_child(after=replace); self.assert_refused('storage_changed')
        self.assertEqual(self.evidence()['state'], 'uncertain')

    def test_replaced_ancestor_after_child_refuses_publication(self):
        self.configure()
        def replace():
            state = self.target.parent
            state.rename(state.with_name('retained-state')); state.mkdir(mode=0o700)
            self.target.mkdir(mode=0o700)
        self.hook_child(after=replace); self.assert_refused('storage_changed')

    def test_changed_mode_after_failed_child_still_checked(self):
        self.configure(); self.runner.child_mode = 'FAILED'
        self.hook_child(after=lambda: self.target.chmod(0o750))
        self.assert_refused('storage_mode')

    def test_prelaunch_replacement_refused(self):
        self.configure(); original = self.runner.record_outcome
        def record(n, **values):
            original(n, **values)
            if values.get('child_process') == 'running':
                self.target.rename(self.target.with_name('retained-original'))
                self.target.mkdir(mode=0o700)
        self.runner.record_outcome = record
        self.assert_refused('storage_changed'); self.assertEqual(self.runner.child_count, 0)

    def test_ancestor_changed_during_preparation_no_grant(self):
        self.configure(); original = c.Grant.separation
        def replace(grant, observations):
            original(grant, observations)
            state = self.target.parent
            state.rename(state.with_name('retained-state')); state.mkdir(mode=0o700)
        with patch.object(c.Grant, 'separation', replace):
            self.assert_refused('storage_changed')
        self.assertFalse(self.target.exists()); self.assertEqual(self.runner.child_count, 0)

    def test_prelaunch_ancestor_replacement_refused(self):
        self.configure(); original = self.runner.record_outcome
        def record(n, **values):
            original(n, **values)
            if values.get('child_process') == 'running':
                self.target.parent.rename(self.target.parent.with_name('retained-state'))
                self.target.parent.mkdir(mode=0o700); self.target.mkdir(mode=0o700)
        self.runner.record_outcome = record
        self.assert_refused('storage_changed'); self.assertEqual(self.runner.child_count, 0)

    def test_acl_changes_after_child_refuse(self):
        self.configure()
        def changed():
            mocked = patch.object(c, 'acl_identity', side_effect=c.StorageError('storage_acl'))
            mocked.start(); self.addCleanup(mocked.stop)
        self.hook_child(after=changed); self.assert_refused('storage_acl')

    def test_interruption_after_creation_preserved_no_replay(self):
        self.configure(); original = c.Grant.persist
        def interrupt(grant, state, reason, identities=None):
            original(grant, state, reason, identities)
            if reason == 'storage_verify_pending': raise SystemExit('synthetic interruption')
        with patch.object(c.Grant, 'persist', interrupt), self.assertRaises(SystemExit): self.run_task()
        self.assertTrue(self.target.is_dir()); self.assertEqual(self.evidence()['state'], 'created')
        self.run_task(); self.assertEqual(self.runner.child_count, 0)
        self.assertEqual(self.runner.state['consumed'], [1])

    def test_input_change_prevents_artifact_even_with_valid_grant(self):
        self.configure(); self.runner.mutate_input = True
        self.hook_child(); self.assert_refused()
        self.assertEqual(self.evidence()['reason'], 'storage_verified')

    def test_checkout_change_prevents_artifact_even_with_valid_grant(self):
        self.configure(); self.runner.public_change = 'file'
        self.hook_child(); self.assert_refused()
        self.assertEqual(self.receipt()['code'], 'PUBLIC_CHANGE_REFUSED')

    def test_ordinary_task_does_not_lookup_account_or_touch_storage(self):
        self.runner.body = s.task_body([s.INPUT])
        with patch.object(c.pwd, 'getpwuid', side_effect=AssertionError('no account lookup')), \
                patch.object(c.Grant, 'prepare', side_effect=AssertionError('no storage')):
            self.run_task()
        self.assertEqual(self.receipt()['code'], 'OK')
        self.assertFalse((self.runner.state_dir/'storage-grant-1.json').exists())


class ACLTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'darwin', 'Darwin descriptor API fixture only')
    def test_native_empty_acl_on_temporary_fixture_only(self):
        with tempfile.TemporaryDirectory() as directory:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                self.assertEqual(len(c.acl_identity(fd)), 64)
            finally:
                os.close(fd)

    def darwin(self, tags):
        lib = Mock()
        lib.acl_get_fd_np.return_value = 10
        lib.acl_valid.return_value = 0
        lib.acl_size.return_value = 64
        text = ctypes.create_string_buffer(b'synthetic deny ACL')
        def to_text(acl, length):
            length._obj.value = len(text.value)
            return ctypes.addressof(text)
        lib.acl_to_text.side_effect = to_text
        iterator = iter(tags)
        def entry(acl, index, output):
            try: tag = next(iterator)
            except StopIteration:
                ctypes.set_errno(errno.EINVAL); return -1
            output._obj.value = tag
            return 0
        lib.acl_get_entry.side_effect = entry
        def tag(entry, output): output._obj.value = entry.value; return 0
        lib.acl_get_tag_type.side_effect = tag
        return lib

    def test_darwin_empty_and_deny_only_preserved_allow_unknown_rejected(self):
        for tags in ([], [2], [2,2], [1], [3], [2]*129):
            lib = self.darwin(tags)
            with self.subTest(tags=tags[:3]), patch.object(c.ctypes, 'CDLL', return_value=lib):
                if all(t == 2 for t in tags) and len(tags) <= 128:
                    self.assertEqual(len(c._darwin_acl(123)), 64)
                else:
                    with self.assertRaises(c.StorageError): c._darwin_acl(123)
                lib.acl_free.assert_any_call(10)
                self.assertFalse(lib.acl_set_fd.called)

    def test_darwin_unavailable_and_oversize_refuse(self):
        for attribute, value in (('acl_get_fd_np', None), ('acl_valid', -1), ('acl_size', 16385)):
            lib = self.darwin([]); getattr(lib, attribute).return_value = value
            with patch.object(c.ctypes, 'CDLL', return_value=lib), self.assertRaises(c.StorageError):
                c._darwin_acl(123)

    def test_darwin_absence_requires_successful_supported_metadata(self):
        for support, stat_result, query, present, success in (
                (1, 0, 0, 0, True), (-1, 0, 0, 0, False), (0, 0, 0, 0, False),
                (1, -1, 0, 0, False), (1, 0, -1, 0, False),
                (1, 0, 0, 1, False), (1, 0, 0, -1, False)):
            lib = self.darwin([])
            def absent(*args): ctypes.set_errno(errno.ENOENT); return None
            lib.acl_get_fd_np.side_effect = absent
            lib.fpathconf.return_value = support; lib.filesec_init.return_value = 20
            lib.fstatx_np.return_value = stat_result
            def property(security, key, output): output._obj.value = present; return query
            lib.filesec_query_property.side_effect = property
            with self.subTest(support=support, stat_result=stat_result, query=query, present=present), \
                    patch.object(c.ctypes, 'CDLL', return_value=lib):
                if success: self.assertEqual(len(c._darwin_acl(123)), 64)
                else:
                    with self.assertRaises(c.StorageError): c._darwin_acl(123)
                if support == 1: lib.filesec_free.assert_called_once_with(20)

    def test_unsupported_platforms_refuse_without_acl_probe(self):
        for platform in ('linux', 'unsupported'):
            with patch.object(c.sys, 'platform', platform), \
                    patch.object(c.ctypes, 'CDLL', side_effect=AssertionError('no native probe')), \
                    self.assertRaises(c.StorageError):
                c.acl_identity(123)
