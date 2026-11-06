"""Owner-attested credential correction; invented ledger and complete offline wire."""
import io,os,subprocess,sys,time,unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import historical_nano as historical,supervised_credit as command,keychain_credential as keychain,responses_http as http
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.history import History,FILENAME
import test_http_forward_diagnostic as fixtures
from test_keychain_diagnostic import one_shot_fixture
from test_supervised_envelope import wire_code
from test_responses_compatibility import FIXTURE_CODE

class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.h=fixtures.HTTPForwardTests('test_chain_same_content_clocks_and_one_child_no_original_grant')
        self.h.setUp();self.addCleanup(self.h.doCleanups);self.f=self.h.f
        self.h.grant()
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_CORRECTION'),self.h.r.h.frame(),redirect_stdout(io.StringIO()),patch.object(http,'read_response',side_effect=Refusal('responses_http_401')):
            with self.assertRaisesRegex(Refusal,'responses_http_401'):command.run(self.f.state,self.f.selected,10,historical=True,keychain=True)
        self.events=History(self.f.state).read()
        self.prior=next(e['historical'] for e in self.events if e.get('slot')==10 and 'historical'in e)
        identity=digest('invented-explicit-owner-correction')
        self.a=dict(self.h.a,diagnostic_id=identity,purpose=historical.CREDENTIAL_CORRECTION_PURPOSE,
            material_credential_correction_attested=True,owner_reference='invented-owner-reported-material-correction',
            root_prefix_sha256=digest(self.events),prior_slot=10,prior_run=self.prior['run'],
            prior_grant_sha256=digest(self.prior),prior_attempt_sha256=digest(History(self.f.state/'attempt-10').read()),
            prior_terminal_sha256=digest(self.events[-1]),prior_request_sha256=digest(self.prior['request']),
            request_sha256=digest(historical.renewed_proposal(self.prior,identity)['request']))
        self.path=self.f.f.root/'correction.json';self.write(self.a)
        self.before={p:p.read_bytes()for p in self.f.state.rglob(FILENAME)}
    def write(self,a):self.path.write_bytes(encoded(a));self.path.chmod(0o600)
    def grant(self):return historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(self.a))
    def test_missing_false_or_nonboolean_attestation_and_wrong_pins_no_allocation(self):
        bad=[]
        missing=dict(self.a);missing.pop('material_credential_correction_attested');bad.append(missing)
        for k,v in [('material_credential_correction_attested',False),('material_credential_correction_attested',1),
                    ('owner_reference','unknown'),('project','proj_wrong'),('prior_slot',9),('prior_run','1'*64),
                    ('prior_grant_sha256','2'*64),('input_sha256','3'*64),('request_sha256','4'*64),
                    ('prior_terminal_sha256','5'*64),('prior_attempt_sha256','6'*64),('prior_request_sha256','7'*64),
                    ('expires_at',time.time()-1),('credential_sha256','8'*64)]:bad.append(dict(self.a,**{k:v}))
        for a in bad:
            self.write(a)
            with self.subTest(a=a),patch.object(keychain,'_native')as native,self.assertRaises(Refusal):
                historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
            native.assert_not_called();self.assertEqual(self.before,{p:p.read_bytes()for p in self.f.state.rglob(FILENAME)})
    def test_same_entire_request_except_aliases_and_one_child_across_new_ids(self):
        self.assertEqual(self.grant()['slot'],11)
        grant=History(self.f.state).read()[-2]['historical']
        new=decode(historical.validate(grant,'proj_fixture'));old=self.prior['request']
        data=decode(new['input'][0]['content'][0]['text']);old_data=decode(old['input'][0]['content'][0]['text'])
        data['binding_hash']=old_data['binding_hash']
        for row,previous in zip(data['evidence'],old_data['evidence']):row['alias']=previous['alias']
        new['input'][0]['content'][0]['text']=encoded(data).decode();self.assertEqual(new,old)
        for k in ('prepared_at','case','disclosure','fingerprint','input_sha256'):self.assertEqual(grant[k],self.prior[k])
        a=dict(self.a,diagnostic_id=digest('another-correction-id'),root_prefix_sha256=digest(History(self.f.state).read()))
        a['request_sha256']=digest(historical.renewed_proposal(self.prior,a['diagnostic_id'])['request']);self.write(a)
        with self.assertRaises(Refusal):historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
    def test_other_terminal_reason_cannot_use_correction(self):
        for reason in ('responses_http_rejected','responses_http_403','responses_http_429','responses_not_completed'):
            events=decode(encoded(self.events));events[-1]['reason']=reason
            a=dict(self.a,root_prefix_sha256=digest(events),prior_terminal_sha256=digest(events[-1]));self.write(a)
            grant=historical.renewed_proposal(self.prior,a['diagnostic_id']);grant['renewal']=dict(path=str(self.path),sha256=digest(a),authorization=a)
            grant['consent']=historical.consent(grant,'proj_fixture');grant['authorization_binding']=digest(grant['consent'])
            with self.subTest(reason=reason),self.assertRaisesRegex(Refusal,'historical_renewal_prior'):
                historical.renewal_history(History(self.f.state),events,grant,creating=True)
    def installed(self,outcome):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        runtime=self.f.f.root/'correction-runtime';runtime.mkdir(mode=0o700)
        manifest=install_runtime(Path(__file__).resolve().parent,runtime)
        hooks=self.f.f.root/'correction-hooks';hooks.mkdir(mode=0o700)
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
from ai_movie_investigator.contracts import Refusal
@atexit.register
def finish():print('NETWORK_ATTEMPTS='+str(len(attempts)))
def dummy(project):
 assert project=='proj_fixture';print('DUMMY_LOOKUP')
'''+(" raise Refusal('keychain_denied')\n"if outcome=='denied'else" return b'sk-DUMMY_CORRECTION'\n")+'''keychain._native=dummy
'''+FIXTURE_CODE+'''
if 'run-historical-keychain' in sys.argv:
 from ai_movie_investigator.history import History
 from ai_movie_investigator.contracts import decode,encoded
 from ai_movie_investigator.disclosure import aliases
 from pathlib import Path
 rows=History(Path(sys.argv[sys.argv.index('--state')+1])).read()
 grant=next(r['historical'] for r in rows if r.get('slot')==11 and 'historical'in r)
 value=documented();answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
 value['output'][-1]['content'][0]['text']=encoded(answer).decode();selected_raw=encoded(value);framing='chunked'
'''+wire_code().replace("status=401 if variant=='rejected' else 200","status="+('401'if outcome=='401'else'200'))+"\nif 'run-historical-keychain' in sys.argv:\n _wire=wire_fixture('completed');_wire.__enter__()\n"
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        def invoke(action,args):
            r=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),action,'--evidence',str(self.f.selected.path)]+args,cwd=runtime,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
            out=r.stdout+r.stderr;self.assertIn(b'NETWORK_ATTEMPTS=0',out);self.assertNotIn(b'sk-DUMMY_CORRECTION',out)
            return r,out
        args=['--authorization',str(self.path),'--authorization-sha256',digest(self.a)]
        r,out=invoke('authorize-historical-renewal',args);self.assertEqual(r.returncode,0,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        credit=History(self.f.state/'credit').read()
        r,out=invoke('run-historical-keychain',['--slot','11']);self.assertEqual(r.returncode,0 if outcome=='success'else 1,out)
        self.assertEqual(out.count(b'DUMMY_LOOKUP'),1);self.assertEqual(out.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),0 if outcome=='denied'else 1)
        if outcome=='denied':
            self.assertEqual(History(self.f.state/'credit').read(),credit)
            self.assertEqual(History(self.f.state/'attempt-11').read(),[])
            self.assertIn(b'keychain_denied',out)
        else:
            self.assertEqual(len(History(self.f.state/'credit').read()),len(credit)+1)
            self.assertEqual(len(History(self.f.state/'attempt-11').read()),3 if outcome=='success'else 2)
            terminal=History(self.f.state).read()[-1]
            if outcome=='success':
                report=terminal['historical_report'];self.assertEqual(report['forward_diagnostic']['purpose'],historical.CREDENTIAL_CORRECTION_PURPOSE)
                self.assertEqual(report['forward_diagnostic']['prior_cause'],'unknown');self.assertFalse(report['forward_diagnostic']['prior_outcome_reinterpreted'])
            else:self.assertEqual((terminal['phase'],terminal['reason']),('http_response_received','responses_http_401'))
            for action,arg in [('run-historical-keychain',['--slot','11']),('authorize-historical-renewal',args)]:
                r,out=invoke(action,arg);self.assertEqual(r.returncode,1,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        self.assertEqual(manifest,verify_installation(runtime))
        for p,b in self.before.items():self.assertTrue(p.read_bytes().startswith(b))
    def test_installed_success_receipt_report_and_restart(self):self.installed('success')
    def test_installed_401_refusal_and_restart(self):self.installed('401')
    def test_installed_denied_key_no_debit_or_send(self):self.installed('denied')

if __name__=='__main__':unittest.main()
