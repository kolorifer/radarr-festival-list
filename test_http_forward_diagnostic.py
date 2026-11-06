"""Invented ambiguous HTTP predecessor and finite forward observation only."""
import io,os,subprocess,sys,time,unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import historical_nano as historical,supervised_credit as command,keychain_credential as keychain,responses_http as http
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.credit_test import POLICY
from test_keychain_diagnostic import one_shot_fixture
import test_historical_renewal as renewal_fixtures
from test_supervised_envelope import wire_code


class StatusTests(unittest.TestCase):
    def test_finite_rejections_never_read_headers_body_or_retain_remote_values(self):
        for status in (400,401,403,404,408,409,422,429,500,503,599,301,302,418,777,'PRIVATE',None):
            class Response:
                def getheaders(self):raise AssertionError('must not read headers')
                def read1(self,*a):raise AssertionError('must not read error body')
            response=Response();response.status=status
            expected='responses_http_'+(str(status) if status in (400,401,403,404,408,409,422,429) else '5xx' if type(status)is int and 500<=status<=599 else 'other')
            with self.assertRaises(Refusal) as caught:http.read_response(response,b'{}','proj_fixture','/v1/responses',32768,lambda:None)
            self.assertEqual(str(caught.exception),expected)
            safe=command.safe_diagnostic(caught.exception)
            self.assertEqual(safe['reason'],expected);self.assertNotIn('PRIVATE',repr(safe))
            self.assertNotEqual(safe['category'],'unclassified_refusal')


class HTTPForwardTests(unittest.TestCase):
    def setUp(self):
        self.r=renewal_fixtures.RenewalTests('test_same_disclosure_clocks_new_explicit_correlation_and_unknown_prior')
        self.r.setUp();self.addCleanup(self.r.doCleanups);self.f=self.r.f
        self.r.grant()
        # Retain an invented OLD generic refusal, not an observed provider status.
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_HTTP_ONLY'),self.r.h.frame(),redirect_stdout(io.StringIO()),patch.object(http,'read_response',side_effect=Refusal('responses_http_rejected')):
            with self.assertRaisesRegex(Refusal,'responses_http_rejected'):
                command.run(self.f.state,self.f.selected,9,historical=True,keychain=True)
        self.events=History(self.f.state).read()
        self.prior=next(e['historical'] for e in self.events if e.get('slot')==9 and 'historical'in e)
        identity=digest('invented-explicit-http-diagnostic');proposed=historical.renewed_proposal(self.prior,identity)
        self.a=dict(kind='historical_forward_diagnostic_authorization',diagnostic_id=identity,purpose=historical.HTTP_RENEWAL_PURPOSE,
            owner_reference='invented-owner-http-observation',root_prefix_sha256=digest(self.events),prior_slot=9,
            prior_grant_sha256=digest(self.prior),prior_attempt_sha256=digest(History(self.f.state/'attempt-9').read()),
            prior_terminal_sha256=digest(self.events[-1]),prior_run=self.prior['run'],project='proj_fixture',input_sha256=self.prior['input_sha256'],
            prior_request_sha256=digest(self.prior['request']),request_sha256=digest(proposed['request']),policy=POLICY,
            maximum_debit_usd=[3,100],max_requests=1,not_before=time.time()-1,expires_at=time.time()+600)
        self.path=self.f.f.root/'http-renewal.json';self.write(self.a)
        self.before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
    def write(self,a):self.path.write_bytes(encoded(a));self.path.chmod(0o600)
    def grant(self):return historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(self.a))
    def preserved(self):
        for p,b in self.before.items():
            self.assertTrue(p.read_bytes().startswith(b) if p.parent==self.f.state else p.read_bytes()==b)
    def test_chain_same_content_clocks_and_one_child_no_original_grant(self):
        self.assertEqual(self.grant()['slot'],10)
        new=History(self.f.state).read()[-2]['historical']
        self.assertEqual(new['prepared_at'],self.prior['prepared_at'])
        self.assertEqual(new['input_sha256'],self.prior['input_sha256'])
        old_data=decode(self.prior['request']['input'][0]['content'][0]['text'])
        data=decode(new['request']['input'][0]['content'][0]['text'])
        data['binding_hash']=old_data['binding_hash']
        for row,old in zip(data['evidence'],old_data['evidence']):row['alias']=old['alias']
        self.assertEqual(data,old_data)
        self.assertEqual(historical.validate(new,'proj_fixture'),encoded(new['request']))
        with self.assertRaises(Refusal):self.grant()
        with self.assertRaises(Refusal):self.r.h.authorize()
        self.preserved()
    def test_purpose_predecessor_and_lineage_pins_are_not_interchangeable(self):
        for key,value in (('prior_run','1'*64),('prior_grant_sha256','2'*64),('prior_terminal_sha256','3'*64),
                          ('prior_attempt_sha256','4'*64),('purpose','retry'),('prior_slot',8)):
            a=dict(self.a,**{key:value});self.write(a)
            with self.subTest(key=key),patch.object(keychain,'_native')as native,self.assertRaises(Refusal):
                historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
            native.assert_not_called();self.assertEqual(self.before,{p:p.read_bytes()for p in self.f.state.rglob(FILENAME)})
        a=dict(self.a,purpose=historical.RENEWAL_PURPOSE);a.pop('prior_run');self.write(a)
        with self.assertRaises(Refusal):
            historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
    def test_expired_ancestor_is_historical_only_and_new_authority_must_be_current(self):
        future=self.prior['renewal']['authorization']['expires_at']+1
        self.a.update(not_before=future-1,expires_at=future+600);self.write(self.a)
        # Only the lineage check uses historical dates; no live evidence freshness bypass.
        new=historical.renewed_proposal(self.prior,self.a['diagnostic_id'])
        new['renewal']=dict(path=str(self.path),sha256=digest(self.a),authorization=self.a)
        new['consent']=historical.consent(new,'proj_fixture');new['authorization_binding']=digest(new['consent'])
        with patch.object(historical.time,'time',return_value=future):
            historical.renewal_history(History(self.f.state),self.events,new,creating=True)
        with patch.object(historical.time,'time',return_value=future+601),self.assertRaisesRegex(Refusal,'historical_renewal_expired'):
            historical.renewal_history(History(self.f.state),self.events,new,creating=True)
        self.assertEqual(self.before,{p:p.read_bytes()for p in self.f.state.rglob(FILENAME)})
    def test_installed_m_path_finite_rejection_no_receipt_restart_or_new_child(self):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        runtime=self.f.f.root/'http-forward-runtime';runtime.mkdir(mode=0o700)
        manifest=install_runtime(Path(__file__).resolve().parent,runtime)
        hooks=self.f.f.root/'http-forward-hooks';hooks.mkdir(mode=0o700)
        hook='''
import atexit,errno,os,sys
attempts=[]
def audit(event,args):
 if event.startswith('socket.'):
  attempts.append(event);raise AssertionError('network forbidden')
sys.addaudithook(audit)
if sys.platform.startswith('linux'):
 def absent(*a,**kw):raise OSError(errno.ENODATA,'fixture')
 os.getxattr=absent
from ai_movie_investigator import keychain_credential as keychain
def dummy(project):
 assert project=='proj_fixture';print('DUMMY_LOOKUP');return b'sk-DUMMY_HTTP_ONLY'
keychain._native=dummy
@atexit.register
def finish():print('NETWORK_ATTEMPTS='+str(len(attempts)))
selected_raw=b'PRIVATE_ERROR_BODY';framing='chunked'
'''+wire_code().replace("status=401 if variant=='rejected' else 200","status=401")+"\nif 'run-historical-keychain' in sys.argv:\n _wire=wire_fixture('completed');_wire.__enter__()\n"
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        def invoke(action,args):
            r=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),action,'--evidence',str(self.f.selected.path)]+args,cwd=runtime,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
            output=r.stdout+r.stderr
            self.assertNotIn(b'PRIVATE_ERROR_BODY',output);self.assertNotIn(b'sk-DUMMY_HTTP_ONLY',output)
            self.assertIn(b'NETWORK_ATTEMPTS=0',output)
            return r,output
        args=['--authorization',str(self.path),'--authorization-sha256',digest(self.a)]
        r,out=invoke('authorize-historical-renewal',args);self.assertEqual(r.returncode,0,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        r,out=invoke('run-historical-keychain',['--slot','10']);self.assertEqual(r.returncode,1,out)
        self.assertEqual(out.count(b'DUMMY_LOOKUP'),1);self.assertEqual(out.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
        terminal=History(self.f.state).read()[-1]
        self.assertEqual((terminal['phase'],terminal['reason']),('http_response_received','responses_http_401'))
        self.assertEqual(len(History(self.f.state/'attempt-10').read()),2)
        for action,args2 in [('run-historical-keychain',['--slot','10']),('authorize-historical-renewal',args)]:
            r,out=invoke(action,args2);self.assertEqual(r.returncode,1);self.assertNotIn(b'DUMMY_LOOKUP',out)
        # Classified refusals cannot become another generic HTTP forward grant.
        events=History(self.f.state).read();prior=next(e['historical']for e in events if e.get('slot')==10 and 'historical'in e)
        a=dict(self.a,prior_slot=10,prior_run=prior['run'],diagnostic_id=digest('different-id'),root_prefix_sha256=digest(events),
            prior_grant_sha256=digest(prior),prior_attempt_sha256=digest(History(self.f.state/'attempt-10').read()),
            prior_terminal_sha256=digest(events[-1]),prior_request_sha256=digest(prior['request']))
        a['request_sha256']=digest(historical.renewed_proposal(prior,a['diagnostic_id'])['request']);self.write(a)
        with self.assertRaisesRegex(Refusal,'historical_renewal_prior'):
            historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
        self.assertFalse((self.f.state/'attempt-11').exists())
        self.assertEqual(len(History(self.f.state/'credit').read()),9)
        self.assertTrue(all(b'PRIVATE_ERROR_BODY'not in p.read_bytes() for p in self.f.state.rglob(FILENAME)))
        self.assertEqual(manifest,verify_installation(runtime))
        # Credit appended once; all older attempt files and root prefix retained.
        for p,b in self.before.items():
            self.assertTrue(p.read_bytes().startswith(b))

    def test_ancestor_valid_at_start_but_expired_at_attempt_is_refused(self):
        rows=History(self.f.state/'attempt-9').read()
        rows[-1]['at']=self.prior['renewal']['authorization']['expires_at']+1
        self.a['prior_attempt_sha256']=digest(rows);self.write(self.a)
        new=historical.renewed_proposal(self.prior,self.a['diagnostic_id'])
        new['renewal']=dict(path=str(self.path),sha256=digest(self.a),authorization=self.a)
        new['consent']=historical.consent(new,'proj_fixture');new['authorization_binding']=digest(new['consent'])
        original=History.read
        def invented_read(h):
            return rows if h.directory==self.f.state/'attempt-9' else original(h)
        with patch.object(History,'read',invented_read),self.assertRaisesRegex(Refusal,'historical_renewal_expired'):
            historical.renewal_history(History(self.f.state),self.events,new,creating=True)
        self.assertEqual(self.before,{p:p.read_bytes()for p in self.f.state.rglob(FILENAME)})

if __name__=='__main__':unittest.main()
