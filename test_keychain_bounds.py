"""Bounded invented native calls in disposable installed processes only."""
import ctypes,inspect,io,json,os,subprocess,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stderr
from ai_movie_investigator import keychain_credential as keychain,supervised_credit as command
from ai_movie_investigator.contracts import Refusal
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.installation import install_runtime,verify_installation
import test_keychain_diagnostic as fixtures
import test_standing_credit as standing
from test_responses_compatibility import FIXTURE_CODE
from test_supervised_envelope import wire_code

class NativeCleanupTests(unittest.TestCase):
    def test_imported_lookup_refuses_before_native_or_watchdog(self):
        with patch.object(keychain,'_native') as native,patch.object(keychain.threading,'Thread') as worker:
            with self.assertRaisesRegex(Refusal,'keychain_process_required'):keychain.credential('proj_fixture')
        native.assert_not_called();worker.assert_not_called()
        with self.assertRaisesRegex(Refusal,'keychain_process_required'):
            with keychain.one_shot_process():pass

    def test_interaction_restored_on_success_failure_cancellation_and_broken_stderr(self):
        for initial,status in ((1,0),(0,0),(1,-25300)):
            f=fixtures.NativeFixture(status);f.initial_interaction=initial
            broken=type('Broken',(),dict(write=lambda *a:(_ for _ in ()).throw(OSError('PRIVATE')),flush=lambda *a:(_ for _ in ()).throw(OSError('PRIVATE'))))()
            with f.contexts(),patch.object(keychain.sys,'stderr',broken):
                if status:
                    with self.assertRaisesRegex(Refusal,'keychain_missing'):keychain.credential('proj_fixture')
                else:keychain.credential('proj_fixture')
            self.assertEqual(f.interactions,[0,initial]);self.assertEqual(len(f.released),4)
        f=fixtures.NativeFixture();f.sec.SecItemCopyMatching=fixtures.Function(lambda *a:(_ for _ in ()).throw(KeyboardInterrupt()))
        with f.contexts(),self.assertRaises(KeyboardInterrupt):keychain.credential('proj_fixture')
        self.assertEqual(f.interactions,[0,1]);self.assertEqual(len(f.released),3)

    def test_get_disable_restore_and_release_refuse_without_releasing_credential(self):
        f=fixtures.NativeFixture();f.interaction_get_status=-1
        with f.contexts(),self.assertRaisesRegex(Refusal,'keychain_interaction_get_failed'):keychain.credential('proj_fixture')
        self.assertEqual(f.calls,0);self.assertEqual(f.interactions,[])
        f=fixtures.NativeFixture();f.interaction_set_status=-1
        with f.contexts(),self.assertRaisesRegex(Refusal,'keychain_interaction_disable_failed') as failure:keychain.credential('proj_fixture')
        self.assertEqual(f.calls,0);self.assertEqual(f.interactions,[0,1]);self.assertEqual(command.safe_diagnostic(failure.exception)['cleanup_reason'],'keychain_interaction_restore_failed')
        for status in (0,-25300):
            f=fixtures.NativeFixture(status)
            def set_flag(value):f.interactions.append(int(value));return 0 if len(f.interactions)==1 else -1
            f.sec.SecKeychainSetUserInteractionAllowed=fixtures.Function(set_flag)
            expected='keychain_missing' if status else 'keychain_interaction_restore_failed'
            with f.contexts(),self.assertRaisesRegex(Refusal,expected) as failure:keychain.credential('proj_fixture')
            if status:self.assertEqual(command.safe_diagnostic(failure.exception)['cleanup_reason'],'keychain_interaction_restore_failed')
        f=fixtures.NativeFixture();f.cf.CFRelease=fixtures.Function(lambda item:(_ for _ in ()).throw(RuntimeError('PRIVATE')))
        with f.contexts(),self.assertRaisesRegex(Refusal,'keychain_release_failed'):keychain.credential('proj_fixture')
        self.assertEqual(f.interactions,[0,1])

    def test_cleanup_failure_cannot_be_hidden_by_callers_active_exception(self):
        f=fixtures.NativeFixture()
        def set_flag(value):f.interactions.append(int(value));return 0 if len(f.interactions)==1 else -1
        f.sec.SecKeychainSetUserInteractionAllowed=fixtures.Function(set_flag)
        try:raise RuntimeError('PRIVATE_CALLER_EXCEPTION')
        except RuntimeError:
            with f.contexts(),self.assertRaisesRegex(Refusal,'^keychain_interaction_restore_failed$'):
                keychain.credential('proj_fixture')
        self.assertEqual(f.interactions,[0,1])
        self.assertEqual(keychain.LOOKUP_TIMEOUT_EXITS,dict(lookup=80,framework=81,interaction_get=82,
            interaction_disable=83,query_build=84,query=85,data=86,release=87,interaction_restore=88))
        self.assertEqual(keychain.LOOKUP_TIMEOUT_EXIT,124)

    def test_late_return_refused_even_if_watchdog_not_scheduled(self):
        class Unscheduled:
            ident=None
            def __init__(self,**kw):pass
            def start(self):pass
        with fixtures.one_shot_fixture(),patch.object(keychain.threading,'Thread',Unscheduled),patch.object(keychain.time,'monotonic',side_effect=[10,16]),patch.object(keychain,'_native',return_value=b'sk-DUMMY'):
            with self.assertRaisesRegex(Refusal,'keychain_lookup_timeout'):keychain.credential('proj_fixture')
        self.assertIsNone(keychain._STAGE.get())

class InstalledBoundTests(unittest.TestCase):
    def setUp(self):
        self.f=standing.StandingTests('test_grant_preserves_legacy_hashes_and_default_cap');self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.grant()
        self.before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
        self.runtime=self.f.f.root/'bounded-installed';self.runtime.mkdir(mode=0o700)
        self.manifest=install_runtime(Path(__file__).resolve().parent,self.runtime)
        self.hooks=self.f.f.root/'bounded-hooks';self.hooks.mkdir(mode=0o700)
    def run_installed(self,variant,action='check-keychain'):
        hook='''
import atexit,errno,os,sys,time,ctypes
_attempts=[]
def audit(event,args):
    if event in ('socket.__new__','socket.connect','socket.getaddrinfo','socket.gethostbyname'):
        _attempts.append(event);raise AssertionError('network forbidden')
sys.addaudithook(audit)
if sys.platform.startswith('linux'):
    def absent(*a,**k):raise OSError(errno.ENODATA,'fixture ACL absent')
    os.getxattr=absent
from ai_movie_investigator import keychain_credential as keychain
def dummy(project):
    assert project=='proj_fixture';print('DUMMY_NATIVE_ENTERED',flush=True)
    if VARIANT=='blocked':
        # Real blocking C function, but never a Security API or network call.
        keychain._note('query')
        libc=ctypes.CDLL(None);libc.pause.argtypes=[];libc.pause.restype=ctypes.c_int;libc.pause()
        raise AssertionError('unexpected native return')
    return b'sk-DUMMY_BOUNDED_ONLY'
_real_native=keychain._native
keychain._native=dummy
@atexit.register
def status():print('NETWORK_ATTEMPTS='+str(len(_attempts)),flush=True)
'''.replace('VARIANT',repr(variant))
        if variant=='cleanup-failure':
            hook+='\nfrom unittest.mock import patch\n'+inspect.getsource(fixtures.Function)+inspect.getsource(fixtures.NativeFixture)+"""
_f=NativeFixture(-25300)
def restore_fails(value):
    _f.interactions.append(int(value));return 0 if len(_f.interactions)==1 else -1
_f.sec.SecKeychainSetUserInteractionAllowed=Function(restore_fails)
def failed_cleanup(project):
    with patch.object(keychain.sys,'platform','darwin'),patch.object(keychain,'_frameworks',return_value=(_f.sec,_f.cf)),patch.object(keychain,'_constant',side_effect=lambda lib,name:name):
        return _real_native(project)
keychain._native=failed_cleanup
"""
        if variant=='later-send':
            hook+=FIXTURE_CODE+'''
from ai_movie_investigator.contracts import decode,encoded
from ai_movie_investigator.disclosure import aliases
value=documented();answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases('synthetic-integration-7')
value['output'][-1]['content'][0]['text']=encoded(answer).decode();selected_raw=encoded(value);framing='chunked'
'''+wire_code()+'''
_wire=wire_fixture('completed');_wire.__enter__()
from ai_movie_investigator.responses_http import FixedResponsesHTTP
_original=FixedResponsesHTTP.post
def delayed(self,*args,**kwargs):
    assert not any(t.name=='bounded-keychain-lookup' and t.is_alive() for t in __import__('threading').enumerate())
    time.sleep(6)
    return _original(self,*args,**kwargs)
FixedResponsesHTTP.post=delayed
'''
        (self.hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(self.hooks)+os.pathsep+str(self.runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        started=time.monotonic()
        r=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),action,'--evidence',str(self.f.selected.path)],cwd=self.runtime,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=15)
        return r,time.monotonic()-started
    def test_installed_cleanup_failure_reports_primary_and_safe_secondary(self):
        result,_=self.run_installed('cleanup-failure');output=result.stdout+result.stderr
        self.assertEqual(result.returncode,1,output)
        self.assertIn(b'reason=keychain_missing',output)
        self.assertIn(b'cleanup_reason=keychain_interaction_restore_failed',output)
        self.assertIn(b'NETWORK_ATTEMPTS=0',output)
        self.assertNotIn(b'sk-DUMMY',output);self.assertNotIn(b'Traceback',output)
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.f.state.rglob(FILENAME)})

    def test_blocked_native_hard_exit_without_state_or_http_work(self):
        result,elapsed=self.run_installed('blocked');output=result.stdout+result.stderr
        self.assertEqual(result.returncode,85,output);self.assertLess(elapsed,12);self.assertGreaterEqual(elapsed,5)
        self.assertIn(b'DUMMY_NATIVE_ENTERED',output);self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',output)
        self.assertNotIn(b'sk-DUMMY_BOUNDED_ONLY',output)
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.f.state.rglob(FILENAME)})
        self.assertFalse((self.f.state/'attempt-7').exists());self.assertEqual(verify_installation(self.runtime),self.manifest)
        # Hard exit released the process's shared lock; no orphan runner remains.
        with History(self.f.state).transaction(write=True):pass
    def test_availability_is_read_only_and_finished_watchdog_cannot_kill_later_send(self):
        result,_=self.run_installed('available');output=result.stdout+result.stderr
        self.assertEqual(result.returncode,0,output);self.assertIn(b'credential_available_format_only_no_api_call',output)
        self.assertIn(b'NETWORK_ATTEMPTS=0',output);self.assertNotIn(b'sk-DUMMY_BOUNDED_ONLY',output)
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.f.state.rglob(FILENAME)})
        result,elapsed=self.run_installed('later-send','run-next-keychain');output=result.stdout+result.stderr
        self.assertEqual(result.returncode,0,output);self.assertGreaterEqual(elapsed,6)
        self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1);self.assertIn(b'NETWORK_ATTEMPTS=0',output)
        self.assertEqual(len(History(self.f.state/'credit').read()),6)
        self.assertEqual(verify_installation(self.runtime),self.manifest)

if __name__=='__main__':unittest.main()
