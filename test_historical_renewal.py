"""One explicit forward diagnostic; invented legacy failure, no real operations."""
import copy,io,os,subprocess,sys,time,unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import historical_nano as historical,supervised_credit as command,keychain_credential as keychain
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.credit_test import POLICY
import test_historical_nano as fixtures
import test_supervised_diagnostics as diagnostics
from test_responses_compatibility import FIXTURE_CODE
from test_supervised_envelope import wire_code
from test_keychain_diagnostic import one_shot_fixture

class RenewalTests(unittest.TestCase):
    def setUp(self):
        self.h=fixtures.HistoricalNanoTests('test_connected_historical_report_preserves_18c_and_qualified_output')
        self.h.setUp();self.addCleanup(self.h.doCleanups);self.f=self.h.f
        self.h.authorize()
        # Invent the legacy composite parser refusal. This is not a live response.
        with diagnostics.DiagnosticTests().inputs(),self.h.frame(),redirect_stdout(io.StringIO()),patch('ai_movie_investigator.bound_send.parse_response',side_effect=Refusal('responses_not_completed')):
            with self.assertRaisesRegex(Refusal,'responses_not_completed'):command.run(self.f.state,self.f.selected,8,historical=True)
        self.before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
        self.events=History(self.f.state).read();self.prior=next(e['historical'] for e in self.events if e.get('slot')==8 and 'historical' in e)
        self.a=self.authority();self.path=self.f.f.root/'renewal-authority.json';self.write(self.a)
    def authority(self):
        identity=digest('invented-explicit-forward-diagnostic-1');proposed=historical.renewed_proposal(self.prior,identity)
        return dict(kind='historical_forward_diagnostic_authorization',diagnostic_id=identity,purpose=historical.RENEWAL_PURPOSE,
            owner_reference='invented-owner-turn-one',root_prefix_sha256=digest(self.events),prior_slot=8,
            prior_grant_sha256=digest(self.prior),prior_attempt_sha256=digest(History(self.f.state/'attempt-8').read()),
            prior_terminal_sha256=digest(self.events[-1]),project='proj_fixture',input_sha256=self.prior['input_sha256'],
            prior_request_sha256=digest(self.prior['request']),request_sha256=digest(proposed['request']),
            policy=POLICY,maximum_debit_usd=[3,100],max_requests=1,not_before=time.time()-1,expires_at=time.time()+600)
    def write(self,a):self.path.write_bytes(encoded(a));self.path.chmod(0o600)
    def grant(self):return historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(self.a))
    def preserved(self):
        for p,raw in self.before.items():
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
            else:self.assertTrue(p.read_bytes().startswith(raw))
    def test_same_disclosure_clocks_new_explicit_correlation_and_unknown_prior(self):
        result=self.grant();self.assertEqual(result['slot'],9)
        new=History(self.f.state).read()[-2]['historical'];old_data=decode(self.prior['request']['input'][0]['content'][0]['text']);data=decode(new['request']['input'][0]['content'][0]['text'])
        self.assertNotIn('owner_confirmation',new);self.assertIn('authorization_binding',new)
        self.assertNotEqual(new['run'],self.prior['run']);self.assertEqual(new['prepared_at'],self.prior['prepared_at'])
        self.assertEqual(new['case'],self.prior['case']);self.assertEqual(new['fingerprint'],self.prior['fingerprint'])
        data['binding_hash']=old_data['binding_hash']
        for row,old in zip(data['evidence'],old_data['evidence']):row['alias']=old['alias']
        self.assertEqual(data,old_data)
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_RENEWAL_ONLY'),self.h.frame(),redirect_stdout(io.StringIO()):
            self.assertEqual(command.run(self.f.state,self.f.selected,9,historical=True,keychain=True)['status'],'completed')
        report=History(self.f.state).read()[-1]['historical_report'];self.assertEqual(report['forward_diagnostic']['prior_cause'],'unknown')
        self.assertFalse(report['forward_diagnostic']['prior_outcome_reinterpreted']);self.assertFalse(report['captured_bytes'])
        self.assertEqual(len(History(self.f.state/'credit').read()),8);self.preserved()
        with one_shot_fixture(),patch.object(keychain,'_native') as native:
            for slot in (8,9):
                with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,slot,historical=True,keychain=True)
        native.assert_not_called()
    def test_altered_authority_pins_expiry_policy_or_purpose_cannot_allocate(self):
        for key,value in [('project','proj_other'),('input_sha256','1'*64),('prior_grant_sha256','2'*64),
            ('prior_attempt_sha256','3'*64),('prior_terminal_sha256','4'*64),('root_prefix_sha256','5'*64),
            ('request_sha256','6'*64),('prior_request_sha256','7'*64),('purpose','classify_prior_response'),
            ('owner_reference',' UNKNOWN '),('maximum_debit_usd',[4,100]),('max_requests',2),('expires_at',time.time()-1)]:
            a=dict(self.a,**{key:value});self.write(a)
            with self.subTest(key=key),one_shot_fixture(),patch.object(keychain,'_native') as native:
                with self.assertRaises(Refusal):historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
            native.assert_not_called();self.assertEqual(self.before,{p:p.read_bytes() for p in self.f.state.rglob(FILENAME)})
    def test_renewal_consumed_even_with_new_id_no_timestamp_or_case_relabel(self):
        self.grant()
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_RENEWAL_ONLY'),self.h.frame(True),redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(Refusal,'responses_usage_invalid'):command.run(self.f.state,self.f.selected,9,historical=True,keychain=True)
        self.preserved();self.assertEqual(len(History(self.f.state/'credit').read()),8)
        a=dict(self.a,diagnostic_id=digest('different-id'),root_prefix_sha256=digest(History(self.f.state).read()))
        a['request_sha256']=digest(historical.renewed_proposal(self.prior,a['diagnostic_id'])['request']);self.write(a)
        with self.assertRaisesRegex(Refusal,'historical_renewal_consumed'):historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
        with self.assertRaises(Refusal):self.h.authorize()
    def test_post_grant_authority_change_refuses_before_keychain_or_debit(self):
        self.grant();self.path.write_bytes(self.path.read_bytes()+b' ')
        with one_shot_fixture(),patch.object(keychain,'_native') as native:
            with self.assertRaisesRegex(Refusal,'historical_renewal_changed'):command.run(self.f.state,self.f.selected,9,historical=True,keychain=True)
        native.assert_not_called();self.assertEqual(len(History(self.f.state/'credit').read()),7);self.preserved()
    def test_authority_changed_during_credential_read_burns_slot_without_new_debit(self):
        self.grant()
        def changed(project):
            self.path.write_bytes(self.path.read_bytes()+b' ')
            return b'sk-DUMMY_RENEWAL_ONLY'
        with one_shot_fixture(),patch.object(keychain,'_native',side_effect=changed),patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post') as post:
            with self.assertRaisesRegex(Refusal,'historical_renewal_changed'):command.run(self.f.state,self.f.selected,9,historical=True,keychain=True)
        post.assert_not_called();self.assertEqual(len(History(self.f.state/'credit').read()),7)
        self.assertTrue(any(e.get('slot')==9 and e['type']=='supervised_started' for e in History(self.f.state).read()))
        self.preserved()

    def test_installed_authorization_then_forward_report_and_restart(self):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        runtime=self.f.f.root/'renewal-runtime';runtime.mkdir(mode=0o700)
        manifest=install_runtime(Path(__file__).resolve().parent,runtime);self.assertEqual(len(manifest),47)
        hooks=self.f.f.root/'renewal-hooks';hooks.mkdir(mode=0o700)
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
    assert project=='proj_fixture';print('DUMMY_LOOKUP',flush=True);return b'sk-DUMMY_RENEWAL_ONLY'
keychain._native=dummy
@atexit.register
def status():print('NETWORK_ATTEMPTS='+str(len(_attempts)),flush=True)
'''+FIXTURE_CODE+'''
if 'run-historical-keychain' in sys.argv:
    from ai_movie_investigator.history import History
    from ai_movie_investigator.contracts import decode,encoded
    from ai_movie_investigator.disclosure import aliases
    from pathlib import Path
    rows=History(Path(sys.argv[sys.argv.index('--state')+1])).read()
    grant=next(r['historical'] for r in rows if r.get('slot')==9 and 'historical' in r)
    value=documented();answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
    value['output'][-1]['content'][0]['text']=encoded(answer).decode();selected_raw=encoded(value);framing='chunked'
'''+wire_code()+"\nif 'run-historical-keychain' in sys.argv:\n    _wire=wire_fixture('completed');_wire.__enter__()\n"
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        def invoke(action,args):
            return subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),action,'--evidence',str(self.f.selected.path)]+args,cwd=runtime,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
        auth_args=['--authorization',str(self.path),'--authorization-sha256',digest(self.a)]
        result=invoke('authorize-historical-renewal',auth_args);output=result.stdout+result.stderr
        self.assertEqual(result.returncode,0,output);self.assertNotIn(b'DUMMY_LOOKUP',output);self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',output)
        result=invoke('run-historical-keychain',['--slot','9']);output=result.stdout+result.stderr
        self.assertEqual(result.returncode,0,output);self.assertEqual(output.count(b'DUMMY_LOOKUP'),1);self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1);self.assertIn(b'NETWORK_ATTEMPTS=0',output)
        self.assertNotIn(b'sk-DUMMY_RENEWAL_ONLY',output)
        self.assertEqual(History(self.f.state).read()[-1]['historical_report']['forward_diagnostic']['prior_cause'],'unknown')
        result=invoke('run-historical-keychain',['--slot','9']);self.assertEqual(result.returncode,1);self.assertNotIn(b'DUMMY_LOOKUP',result.stdout+result.stderr)
        result=invoke('authorize-historical-renewal',auth_args);self.assertEqual(result.returncode,1)
        self.preserved();self.assertEqual(len(History(self.f.state/'credit').read()),8);self.assertEqual(manifest,verify_installation(runtime))

if __name__=='__main__':unittest.main()
