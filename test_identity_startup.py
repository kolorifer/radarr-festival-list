"""Real startup/capture entrypoints with invented kernel/I/O; no live access."""
import ctypes
from contextlib import ExitStack
import errno
import os
from pathlib import Path
import stat
import types
import unittest
from unittest.mock import Mock, patch

import identity_triage_sandbox as sandbox
import identity_triage_service as service
import identity_triage_capture as capture

HOME = Path('/invented-owner')
CONFIG = HOME / '.config/movie-identity-triage/config.json'
STATE = HOME / '.local/state/movie-identity-triage'


def identity():
    return (os.getpid(), 1, 2, (1094,) * 4, (1094,) * 4)


def confined_fixture(stack):
    """Execute real confine; replace only external kernel/filesystem observations."""
    listener = Mock(family=sandbox.socket.AF_INET, type=sandbox.socket.SOCK_STREAM)
    listener.getsockname.return_value = ('127.0.0.1', 12345)
    listener.getsockopt.return_value = 1
    stack.enter_context(patch.object(sandbox, '_kernel'))
    stack.enter_context(patch.object(sandbox.Path, 'home', return_value=HOME))
    stack.enter_context(patch.object(sandbox, '__file__', str(HOME / '.local/lib/movie-identity-triage/identity_triage_sandbox.py')))
    stack.enter_context(patch.object(sandbox, '_private_directory', side_effect=Path))
    stack.enter_context(patch.dict(os.environ, {}, clear=True))
    stack.enter_context(patch.object(sandbox.os, 'fstat', side_effect=lambda fd: types.SimpleNamespace(
        st_mode=stat.S_IFCHR if fd == 0 else stat.S_IFIFO, st_rdev=os.makedev(1, 3))))
    stack.enter_context(patch.object(sandbox.socket, 'socket', return_value=listener))
    stack.enter_context(patch.object(sandbox.resource, 'getrlimit', return_value=(64, 64)))
    stack.enter_context(patch.object(sandbox.os, 'closerange'))
    stack.enter_context(patch.object(sandbox, 'restrict', return_value=6))
    stack.enter_context(patch.object(sandbox.os, 'open', side_effect=PermissionError(errno.EACCES, 'invented')))
    stack.enter_context(patch.object(sandbox.os, 'chmod', side_effect=PermissionError(errno.EPERM, 'invented')))
    # Listener acquisition occurs before the three new-socket denial probes.
    sandbox.socket.socket.side_effect = [listener] + [PermissionError(errno.EPERM, 'invented')] * 3
    stack.enter_context(patch.object(sandbox, '_runtime_identity', side_effect=identity))
    return listener


def startup_fixture():
    with ExitStack() as stack:
        confined_fixture(stack)
        _, _, evidence = sandbox.confine(str(CONFIG), str(STATE))
        service.isolation_check(HOME)
        return sandbox.complete_startup(sandbox.prepare_startup(evidence, True))


class StartupTests(unittest.TestCase):
    def test_real_confine_complete_and_single_capture_binding(self):
        evidence = startup_fixture()
        first = capture.Capture(STATE, evidence)
        context = first.context()
        self.assertTrue(context['capture_ready'])
        self.assertEqual(context['startup_evidence']['pid'], os.getpid())
        self.assertEqual(context['startup_evidence']['uids'], [1094] * 4)
        self.assertEqual(context['startup_evidence']['loaded_code_identity'], 'not_attested')
        self.assertFalse(capture.Capture(STATE, evidence).context()['capture_ready'])
        self.assertEqual(first.context()['capture_nonce'], context['capture_nonce'])

    def test_plain_dictionary_and_incomplete_proof_never_ready(self):
        for proof in (None, {}, {'pid': os.getpid(), 'no_new_privileges': 1}):
            c = capture.Capture(STATE, proof)
            with patch.object(capture.secrets, 'token_hex', side_effect=AssertionError('nonce')):
                self.assertFalse(c.context()['capture_ready'])
                self.assertIsNone(c.prepare(None, None, None, None, None,
                                           {'capture_prepare': True, 'capture_grant_sha256': 'a'*64}, 0, None))
        with ExitStack() as stack:
            confined_fixture(stack)
            _, _, incomplete = sandbox.confine(str(CONFIG), str(STATE))
            self.assertFalse(capture.Capture(STATE, incomplete).context()['capture_ready'])

    def test_effective_denial_failure_cannot_mint(self):
        with ExitStack() as stack:
            confined_fixture(stack)
            with patch.object(sandbox, 'deny_check', side_effect=ValueError('allowed')):
                with self.assertRaises(ValueError): sandbox.confine(str(CONFIG), str(STATE))
                sandbox._runtime_identity.assert_not_called()

    def test_recheck_cannot_complete_changed_runtime(self):
        with ExitStack() as stack:
            confined_fixture(stack)
            _, _, evidence = sandbox.confine(str(CONFIG), str(STATE))
            evidence = sandbox.prepare_startup(evidence, True)
            with patch.object(sandbox, '_runtime_identity', return_value=(999,) + identity()[1:]):
                self.assertIsNone(sandbox.complete_startup(evidence))
            self.assertFalse(capture.Capture(STATE, evidence).context()['capture_ready'])

    def test_completion_runs_real_isolation_before_claiming_it(self):
        with ExitStack() as stack:
            confined_fixture(stack)
            _, _, evidence = sandbox.confine(str(CONFIG), str(STATE))
            evidence = sandbox.prepare_startup(evidence, True)
            with patch.object(sandbox.os, 'open', side_effect=OSError(errno.EIO, 'invented')):
                self.assertIsNone(sandbox.complete_startup(evidence))
            self.assertIsNone(sandbox.complete_startup(evidence))
            self.assertFalse(capture.Capture(STATE, evidence).context()['capture_ready'])

    def test_creator_pid_guard_precedes_inherited_lock_and_capture_io(self):
        c = capture.Capture(STATE, startup_fixture()); c.context()
        c.lock.acquire()
        try:
            with patch.object(capture.os, 'getpid', return_value=os.getpid()+1), \
                 patch.object(capture.os, 'open', side_effect=AssertionError('open')):
                self.assertFalse(c.context()['capture_ready'])
                self.assertIsNone(c.prepare(None, None, None, None, None,
                    {'capture_prepare': True, 'capture_grant_sha256': 'a'*64}, 0, None))
                with patch.object(capture, 'close_capture') as close, \
                     patch.object(capture, 'write_at', side_effect=AssertionError('write')):
                    c.finish((123, b'private', {})); close.assert_called_once_with(123)
        finally: c.lock.release()

    def test_main_gate_failure_prevents_store_and_server(self):
        for failed in ('confine', 'isolation'):
            with self.subTest(failed=failed), ExitStack() as stack:
                confined_fixture(stack)
                store = stack.enter_context(patch.object(service, 'Store'))
                server = stack.enter_context(patch.object(service, 'Server'))
                stack.enter_context(patch.object(service, 'read_config', return_value={'enabled': True, 'port': 12345, 'capture_prepare': True}))
                if failed == 'confine': stack.enter_context(patch.object(sandbox, 'deny_check', side_effect=ValueError('invented')))
                if failed == 'isolation': stack.enter_context(patch.object(service, 'isolation_check', side_effect=ValueError('invented')))
                self.assertEqual(service.main(['--config', str(CONFIG), '--state', str(STATE)]), 1)
                store.assert_not_called()
                server.assert_not_called()

    def test_store_time_identity_change_prevents_capture(self):
        with ExitStack() as stack:
            confined_fixture(stack)
            stack.enter_context(patch.object(service, 'read_config', return_value={'enabled': True, 'port': 12345, 'capture_prepare': True}))
            def store(*args):
                sandbox._runtime_identity.side_effect = lambda: (999,) + identity()[1:]
            stack.enter_context(patch.object(service, 'Store', side_effect=store))
            server = stack.enter_context(patch.object(service, 'Server'))
            stack.enter_context(patch.object(service.threading, 'Thread'))
            service.main(['--config', str(CONFIG), '--state', str(STATE)])
            self.assertIsNone(server.call_args.kwargs['startup_evidence'])

    def test_default_off_makes_no_new_queries_and_cannot_toggle_ready(self):
        with ExitStack() as stack:
            confined_fixture(stack)
            sandbox._runtime_identity.side_effect = AssertionError('must not query')
            stack.enter_context(patch.object(service, 'read_config', return_value={'enabled': True, 'port': 12345}))
            stack.enter_context(patch.object(service, 'Store'))
            server = stack.enter_context(patch.object(service, 'Server'))
            stack.enter_context(patch.object(service.threading, 'Thread'))
            service.main(['--config', str(CONFIG), '--state', str(STATE)])
            self.assertIsNone(server.call_args.kwargs['startup_evidence'])
            self.assertFalse(capture.Capture(STATE, None).context()['capture_ready'])
            sandbox._runtime_identity.assert_not_called()

    def test_prepared_query_denial_keeps_intake_but_no_capture(self):
        with ExitStack() as stack:
            confined_fixture(stack)
            sandbox._runtime_identity.side_effect = ValueError('query_denied')
            stack.enter_context(patch.object(service, 'read_config', return_value={'enabled': True, 'port': 12345, 'capture_prepare': True}))
            stack.enter_context(patch.object(service, 'Store'))
            server = stack.enter_context(patch.object(service, 'Server'))
            stack.enter_context(patch.object(service.threading, 'Thread'))
            service.main(['--config', str(CONFIG), '--state', str(STATE)])
            self.assertIsNone(server.call_args.kwargs['startup_evidence'])
            sandbox._runtime_identity.assert_called_once()

    def test_main_passes_real_completed_evidence_to_server(self):
        with ExitStack() as stack:
            listener = confined_fixture(stack)
            stack.enter_context(patch.object(service, 'read_config', return_value={'enabled': True, 'port': 12345, 'capture_prepare': True}))
            stack.enter_context(patch.object(service, 'Store'))
            server = stack.enter_context(patch.object(service, 'Server'))
            stack.enter_context(patch.object(service.threading, 'Thread'))
            service.main(['--config', str(CONFIG), '--state', str(STATE)])
            evidence = server.call_args.kwargs['startup_evidence']
            self.assertTrue(capture.Capture(STATE, evidence).context()['capture_ready'])
            self.assertIs(server.call_args.kwargs['listener'], listener)


class RuntimeQueries(unittest.TestCase):
    def query(self, *, nnp=1, mode=2, uid=(1094,)*3, gid=(1094,)*3, result=1094, error=0):
        libc = Mock()
        libc.prctl.side_effect = [nnp, mode]
        calls = []
        def syscall(number, sentinel):
            calls.append((number.value, sentinel.value, ctypes.get_errno()))
            ctypes.set_errno(error)
            return result
        libc.syscall.side_effect = syscall
        with patch.object(sandbox, '_kernel', return_value=libc), \
             patch.object(sandbox.os, 'getresuid', return_value=uid, create=True), \
             patch.object(sandbox.os, 'getresgid', return_value=gid, create=True):
            ctypes.set_errno(errno.EIO)
            try: return sandbox._runtime_identity(), calls
            finally: ctypes.set_errno(0)

    def test_exact_invalid_sentinel_and_stale_errno_reset(self):
        value, calls = self.query()
        self.assertEqual(value, identity())
        self.assertEqual(calls, [(122, 0xffffffff, 0), (123, 0xffffffff, 0)])

    def test_every_flag_and_identity_failure_refuses(self):
        for args in ({'nnp': 0}, {'mode': 0}, {'mode': -1}, {'uid': (1094,1094,0)},
                     {'gid': (1094,0,1094)}, {'result': 0}, {'result': -1, 'error': errno.EPERM},
                     {'result': 1094, 'error': errno.EPERM}):
            with self.subTest(args=args), self.assertRaises(ValueError): self.query(**args)


if __name__ == '__main__': unittest.main()
