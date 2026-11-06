"""Dummy native Keychain and framed sockets only; no real credential/provider access."""
import ctypes,io,json,os,subprocess,sys,time,unittest
from pathlib import Path
from contextlib import contextmanager,redirect_stdout,redirect_stderr
from unittest.mock import patch
from ai_movie_investigator import keychain_credential as keychain,supervised_credit as command
from ai_movie_investigator.contracts import Refusal,decode,encoded
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.responses_protocol import parse_response,INTEGRATION_MODEL
import test_historical_nano as historical
from test_responses_compatibility import documented,FIXTURE_CODE
from test_supervised_envelope import wire_code

@contextmanager
def one_shot_fixture():
    # Explicit invented process-capability injection for fast unit fixtures only.
    marker=keychain._ONE_SHOT.set(keychain._CLI_TOKEN)
    try:yield
    finally:keychain._ONE_SHOT.reset(marker)

class Function:
    def __init__(self,fn):self.fn=fn
    def __call__(self,*args):return self.fn(*args)

class NativeFixture:
    def __init__(self,status=0,wrong_type=False,secret=b'sk-DUMMY_KEYCHAIN_PRIVATE'):
        self.status=status;self.query={};self.strings={};self.released=[];self.calls=0;self.interactions=[];self.initial_interaction=1;self.interaction_get_status=0;self.interaction_set_status=0
        self.buffer=ctypes.create_string_buffer(secret);self.secret=secret
        self.cf=type('CF',(),{})();self.sec=type('Security',(),{})()
        funcs=dict(CFStringCreateWithCString=self.string,CFDictionaryCreateMutable=lambda *a:99,
            CFDictionarySetValue=lambda q,k,v:self.query.__setitem__(k,v),CFGetTypeID=lambda v:2 if wrong_type else 1,
            CFDataGetTypeID=lambda:1,CFDataGetLength=lambda v:len(secret),
            CFDataGetBytePtr=lambda v:ctypes.addressof(self.buffer),CFRelease=self.released.append)
        for name,fn in funcs.items():setattr(self.cf,name,Function(fn))
        self.sec.SecItemCopyMatching=Function(self.copy)
        self.sec.SecKeychainGetUserInteractionAllowed=Function(self.get_interaction)
        self.sec.SecKeychainSetUserInteractionAllowed=Function(self.set_interaction)
    def get_interaction(self,result):
        ctypes.cast(result,ctypes.POINTER(ctypes.c_ubyte))[0]=self.initial_interaction
        return self.interaction_get_status
    def set_interaction(self,value):
        self.interactions.append(int(value));return self.interaction_set_status
    def string(self,allocator,value,encoding):
        assert encoding==0x08000100
        number=10+len(self.strings);self.strings[number]=value.decode();return number
    def copy(self,query,result):
        self.calls+=1;assert query==99;assert self.interactions==[0]
        ctypes.cast(result,ctypes.POINTER(ctypes.c_void_p))[0]=55
        return self.status
    def contexts(self):
        from contextlib import ExitStack
        stack=ExitStack();stack.enter_context(one_shot_fixture());stack.enter_context(patch.object(keychain.sys,'platform','darwin'))
        stack.enter_context(patch.object(keychain,'_frameworks',return_value=(self.sec,self.cf)))
        stack.enter_context(patch.object(keychain,'_constant',side_effect=lambda lib,name:name))
        return stack

class KeychainNativeTests(unittest.TestCase):
    def test_native_query_exact_project_single_item_no_ui(self):
        f=NativeFixture()
        with f.contexts():value=keychain.credential('proj_fixture')
        self.assertEqual(value.value,'sk-DUMMY_KEYCHAIN_PRIVATE');self.assertEqual(f.calls,1);self.assertEqual(f.interactions,[0,1])
        self.assertEqual(f.query,dict(kSecClass='kSecClassGenericPassword',kSecAttrService=10,kSecAttrAccount=11,
            kSecReturnData='kCFBooleanTrue',kSecMatchLimit='kSecMatchLimitOne',kSecUseAuthenticationUI='kSecUseAuthenticationUIFail'))
        self.assertEqual(f.strings,{10:keychain.SERVICE,11:'proj_fixture'})
        self.assertEqual([v.value if isinstance(v,ctypes.c_void_p) else v for v in f.released],[55,99,11,10])
        self.assertNotIn('DUMMY',repr(value))

    def test_missing_locked_denied_unknown_and_malformed_are_finite_no_fallback(self):
        for status,reason in [(-25300,'keychain_missing'),(-25308,'keychain_interaction_required'),
                              (-25293,'keychain_denied'),(-128,'keychain_denied'),(-999,'keychain_query_failed'),(-25291,'keychain_not_available'),(-50,'keychain_parameter_invalid'),(-34018,'keychain_entitlement_missing')]:
            f=NativeFixture(status)
            with self.subTest(status=status),f.contexts(),self.assertRaisesRegex(Refusal,reason):keychain.credential('proj_fixture')
            self.assertEqual(f.calls,1);self.assertEqual(len(f.released),4)
        for options in (dict(wrong_type=True),dict(secret=b''),dict(secret=b'x'*4097),dict(secret=b'sk-SECRET\n'),dict(secret=b'bad')):
            f=NativeFixture(**options)
            with f.contexts(),self.assertRaisesRegex(Refusal,'keychain_data_invalid'):keychain.credential('proj_fixture')
        with one_shot_fixture(),patch.object(keychain,'_native') as native:
            with self.assertRaisesRegex(Refusal,'keychain_project'):keychain.credential('other')
        native.assert_not_called()
        with one_shot_fixture(),patch.object(keychain,'_native',side_effect=RuntimeError('PRIVATE_SECRET')):
            with self.assertRaisesRegex(Refusal,'^keychain_unavailable$'):keychain.credential('proj_fixture')

class SafeResponseReasonTests(unittest.TestCase):
    def test_finite_predicates_keep_strict_acceptance_without_remote_values(self):
        cases=[([], 'responses_object_invalid'),({'object':'other'},'responses_object_invalid'),
            ({'model':'other'},'responses_model_mismatch'),({'error':{'message':'PRIVATE_REMOTE'}},'responses_error_present'),
            ({'status':'failed'},'responses_status_failed'),({'status':'cancelled'},'responses_status_cancelled'),
            ({'status':'queued'},'responses_status_queued'),({'status':'in_progress'},'responses_status_in_progress'),
            ({'status':'PRIVATE_REMOTE'},'responses_status_other'),({'status':[]},'responses_status_other'),
            ({'incomplete_details':{}},'responses_incomplete_details_present')]
        for reason,code in [('max_output_tokens','responses_incomplete_max_output_tokens'),('content_filter','responses_incomplete_content_filter'),('PRIVATE_REMOTE','responses_incomplete_other'),([], 'responses_incomplete_other')]:
            cases.append((dict(status='incomplete',incomplete_details=dict(reason=reason,private='PRIVATE_REMOTE')),code))
        for changes,code in cases:
            value=documented()
            if type(changes) is list:value=changes
            else:value.update(changes)
            with self.subTest(code=code),self.assertRaisesRegex(Refusal,'^'+code+'$') as caught:
                parse_response(encoded(value),output_schema(),expected_model=INTEGRATION_MODEL)
            self.assertEqual(command.safe_reason(caught.exception),code)
            self.assertEqual(command.refusal_category(caught.exception),'protocol_refused')
        parse_response(encoded(documented()),output_schema(),expected_model=INTEGRATION_MODEL)

class KeychainCommandTests(unittest.TestCase):
    def setUp(self):
        self.h=historical.HistoricalNanoTests('test_connected_historical_report_preserves_18c_and_qualified_output')
        self.h.setUp();self.addCleanup(self.h.doCleanups);self.f=self.h.f
    def snapshot(self):return {p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
    def test_preflight_refuses_before_keychain_and_missing_key_preserves_every_byte(self):
        before=self.snapshot()
        with one_shot_fixture(),patch.object(keychain,'_native') as native:
            with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,7,keychain=True)
            with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,8,historical=True,keychain=True)
        native.assert_not_called();self.assertEqual(before,self.snapshot())
        with one_shot_fixture(),patch.object(keychain,'_native',side_effect=Refusal('keychain_missing')) as native,patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'keychain_missing'):command.run(self.f.state,self.f.selected,None,keychain=True)
        native.assert_called_once_with('proj_fixture');prompt.assert_not_called();self.assertEqual(before,self.snapshot())
        self.h.authorize()
        with one_shot_fixture(),patch.object(keychain,'_native') as native:
            with self.assertRaisesRegex(Refusal,'historical_pending_grant'):command.run(self.f.state,self.f.selected,None,keychain=True)
        native.assert_not_called()

    def test_synthetic_keychain_cli_is_one_call_and_budget_precedes_next_lookup(self):
        out=io.StringIO()
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_KEYCHAIN_PRIVATE') as native,self.f.wire(8),redirect_stdout(out),patch('getpass.getpass') as prompt:
            result=command.main(['--state',str(self.f.state),'run-next-keychain','--evidence',str(self.f.selected.path)])
        self.assertEqual(result,0);native.assert_called_once_with('proj_fixture');prompt.assert_not_called()
        self.assertEqual(out.getvalue().count('OFFLINE_AUTHORIZED_BOUNDARY'),1)
        self.assertNotIn('sk-DUMMY_KEYCHAIN_PRIVATE',out.getvalue())
        self.assertEqual(len(History(self.f.state/'credit').read()),7);self.h.preserve()
        selected=self.f.select(dict(self.f.e,available_usd=[21,100]));before=self.snapshot()
        with one_shot_fixture(),patch.object(keychain,'_native') as native,redirect_stderr(io.StringIO()):
            result=command.main(['--state',str(self.f.state),'run-next-keychain','--evidence',str(selected.path)])
        self.assertEqual(result,1);native.assert_not_called();self.assertEqual(self.snapshot(),before)

    def test_one_shot_historical_keychain_uncertain_retains_debit_no_replay(self):
        self.h.authorize()
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_KEYCHAIN_PRIVATE') as native,self.h.frame(True),redirect_stdout(io.StringIO()),patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'responses_usage_invalid'):command.run(self.f.state,self.f.selected,8,historical=True,keychain=True)
        native.assert_called_once_with('proj_fixture');prompt.assert_not_called()
        self.assertEqual(len(History(self.f.state/'credit').read()),7);self.h.preserve()
        with one_shot_fixture(),patch.object(keychain,'_native') as native:
            with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,8,historical=True,keychain=True)
        native.assert_not_called()
        self.assertNotIn(b'sk-DUMMY_KEYCHAIN_PRIVATE',b''.join(self.snapshot().values()))
        self.assertIsNone(command._PROMPTED.get())

    def test_installed_noninteractive_keychain_bound_report_and_no_second_read(self):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        self.h.authorize()
        installed=self.f.f.root/'installed-keychain';installed.mkdir(mode=0o700)
        manifest=install_runtime(Path(__file__).resolve().parent,installed);self.assertEqual(len(manifest),42)
        hooks=self.f.f.root/'keychain-hooks';hooks.mkdir(mode=0o700)
        hook='''
import atexit,errno,os,sys
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
    assert project=='proj_fixture';print('DUMMY_KEYCHAIN_READ',flush=True);return b'sk-DUMMY_KEYCHAIN_PRIVATE'
keychain._native=dummy
@atexit.register
def status():print('NETWORK_ATTEMPTS='+str(len(_attempts)),flush=True)
'''+FIXTURE_CODE+'''
from ai_movie_investigator.history import History
from ai_movie_investigator.contracts import decode,encoded
from ai_movie_investigator.disclosure import aliases
from pathlib import Path
rows=History(Path(sys.argv[sys.argv.index('--state')+1])).read()
grant=next(r['historical'] for r in rows if r.get('slot')==8 and 'historical' in r)
value=documented();answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
value['output'][-1]['content'][0]['text']=encoded(answer).decode();selected_raw=encoded(value);framing='chunked'
'''+wire_code()+"\n_wire=wire_fixture('completed');_wire.__enter__()\n"
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(installed),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        argv=[sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),
            'run-historical-keychain','--evidence',str(self.f.selected.path),'--slot','8']
        def invoke():return subprocess.run(argv,cwd=installed,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
        first=invoke();output=first.stdout+first.stderr
        self.assertEqual(first.returncode,0,output);self.assertEqual(output.count(b'DUMMY_KEYCHAIN_READ'),1)
        self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1);self.assertIn(b'NETWORK_ATTEMPTS=0',output)
        self.assertNotIn(b'sk-DUMMY_KEYCHAIN_PRIVATE',output)
        report=History(self.f.state).read()[-1]['historical_report'];self.assertFalse(report['captured_bytes'])
        self.assertEqual(report['request_sha256'],report['receipt']['request_sha256'])
        second=invoke();self.assertEqual(second.returncode,1);self.assertNotIn(b'DUMMY_KEYCHAIN_READ',second.stdout+second.stderr)
        self.assertEqual(len(History(self.f.state/'credit').read()),7);self.h.preserve()
        self.assertNotIn(b'sk-DUMMY_KEYCHAIN_PRIVATE',b''.join(self.snapshot().values()))
        self.assertEqual(verify_installation(installed),manifest)

if __name__=='__main__':unittest.main()
