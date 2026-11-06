"""Purpose-bound historical generation headroom; invented ledger and complete offline wire."""
import copy,io,os,subprocess,sys,time,unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import historical_nano as historical,supervised_credit as command,keychain_credential as keychain,responses_http as http
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.history import History,FILENAME
import test_credential_correction as fixtures
from test_keychain_diagnostic import one_shot_fixture
from test_supervised_envelope import wire_code
from test_responses_compatibility import FIXTURE_CODE

class HeadroomTests(unittest.TestCase):
    def setUp(self):
        self.h=fixtures.CorrectionTests('test_same_entire_request_except_aliases_and_one_child_across_new_ids')
        self.h.setUp();self.addCleanup(self.h.doCleanups);self.f=self.h.f
        self.h.grant()
        with one_shot_fixture(),patch.object(keychain,'_native',return_value=b'sk-DUMMY_HEADROOM'),self.h.h.r.h.frame(),redirect_stdout(io.StringIO()),patch('ai_movie_investigator.bound_send.parse_response',side_effect=Refusal('responses_incomplete_max_output_tokens')):
            with self.assertRaisesRegex(Refusal,'responses_incomplete_max_output_tokens'):command.run(self.f.state,self.f.selected,11,historical=True,keychain=True)
        self.events=History(self.f.state).read()
        self.prior=next(e['historical'] for e in self.events if e.get('slot')==11 and 'historical'in e)
        identity=digest('invented-explicit-output-headroom')
        self.a=dict(self.h.a,diagnostic_id=identity,purpose=historical.OUTPUT_HEADROOM_PURPOSE,
            max_output_tokens=25000,owner_reference='invented-owner-headroom-authorization',
            root_prefix_sha256=digest(self.events),prior_slot=11,prior_run=self.prior['run'],
            prior_grant_sha256=digest(self.prior),prior_attempt_sha256=digest(History(self.f.state/'attempt-11').read()),
            prior_terminal_sha256=digest(self.events[-1]),prior_request_sha256=digest(self.prior['request']),
            request_sha256=digest(historical.renewed_proposal(self.prior,identity,output_limit=25000)['request']))
        self.a.pop('material_credential_correction_attested')
        self.path=self.f.f.root/'headroom.json';self.write(self.a)
        self.before={p:p.read_bytes()for p in self.f.state.rglob(FILENAME)}
    def write(self,a):self.path.write_bytes(encoded(a));self.path.chmod(0o600)
    def grant(self):return historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(self.a))
    def test_wrong_limit_budget_disclosure_predecessor_expiry_no_allocation(self):
        bad=[]
        missing=dict(self.a);missing.pop('max_output_tokens');bad.append(missing)
        for k,v in [('max_output_tokens',4096),('max_output_tokens',25001),('max_output_tokens',25000.0),
                    ('maximum_debit_usd',[4,100]),('project','proj_wrong'),('prior_slot',10),('prior_run','1'*64),
                    ('input_sha256','3'*64),('request_sha256','4'*64),('expires_at',time.time()-1)]:bad.append(dict(self.a,**{k:v}))
        for a in bad:
            self.write(a)
            with self.subTest(a=a),patch.object(keychain,'_native')as native,self.assertRaises(Refusal):
                historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
            native.assert_not_called();self.assertEqual(self.before,{p:p.read_bytes()for p in self.f.state.rglob(FILENAME)})
    def test_same_entire_request_except_aliases_and_one_child_across_new_ids(self):
        self.assertEqual(self.grant()['slot'],12)
        grant=History(self.f.state).read()[-2]['historical']
        new=decode(historical.validate(grant,'proj_fixture'));old=self.prior['request']
        data=decode(new['input'][0]['content'][0]['text']);old_data=decode(old['input'][0]['content'][0]['text'])
        data['binding_hash']=old_data['binding_hash']
        for row,previous in zip(data['evidence'],old_data['evidence']):row['alias']=previous['alias']
        new['input'][0]['content'][0]['text']=encoded(data).decode();self.assertEqual(new['max_output_tokens'],25000);new['max_output_tokens']=old['max_output_tokens'];self.assertEqual(new,old)
        for k in ('prepared_at','case','disclosure','fingerprint','input_sha256'):self.assertEqual(grant[k],self.prior[k])
        a=dict(self.a,diagnostic_id=digest('another-correction-id'),root_prefix_sha256=digest(History(self.f.state).read()))
        a['request_sha256']=digest(historical.renewed_proposal(self.prior,a['diagnostic_id'],output_limit=25000)['request']);self.write(a)
        with self.assertRaises(Refusal):historical.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
    def test_other_terminal_reason_cannot_use_correction(self):
        for reason in ('responses_http_401','responses_incomplete_content_filter','responses_incomplete_other','responses_not_completed'):
            events=copy.deepcopy(self.events);events[-1]['reason']=reason
            a=dict(self.a,root_prefix_sha256=digest(events),prior_terminal_sha256=digest(events[-1]));self.write(a)
            grant=historical.renewed_proposal(self.prior,a['diagnostic_id'],output_limit=25000);grant['renewal']=dict(path=str(self.path),sha256=digest(a),authorization=a)
            grant['consent']=historical.consent(grant,'proj_fixture');grant['authorization_binding']=digest(grant['consent'])
            with self.subTest(reason=reason),self.assertRaisesRegex(Refusal,'historical_renewal_prior'):
                historical.renewal_history(History(self.f.state),events,grant,creating=True)
    def installed(self,outcome):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        runtime=self.f.f.root/'headroom-runtime';runtime.mkdir(mode=0o700)
        manifest=install_runtime(Path(__file__).resolve().parent,runtime)
        hooks=self.f.f.root/'headroom-hooks';hooks.mkdir(mode=0o700)
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
 grant=next(r['historical'] for r in rows if r.get('slot')==12 and 'historical'in r)
 value=documented();value['max_output_tokens']=25000;value['usage'].update(output_tokens=5000,total_tokens=value['usage']['input_tokens']+5000);answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
 value['output'][-1]['content'][0]['text']=encoded(answer).decode();selected_raw=encoded(value);framing='chunked'
'''+("\nif 'run-historical-keychain' in sys.argv:\n value['status']='incomplete';value['incomplete_details']={'reason':'max_output_tokens'};selected_raw=encoded(value)\n" if outcome=='incomplete' else "\nif 'run-historical-keychain' in sys.argv:\n value['max_output_tokens']=4096;selected_raw=encoded(value)\n" if outcome=='wrong_echo' else "\nif 'run-historical-keychain' in sys.argv:\n value['usage'].update(output_tokens=25001,total_tokens=value['usage']['input_tokens']+25001);selected_raw=encoded(value)\n" if outcome=='over_usage' else '')+wire_code()+"\nif 'run-historical-keychain' in sys.argv:\n _wire=wire_fixture('completed');_wire.__enter__()\n"
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        def invoke(action,args):
            r=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),action,'--evidence',str(self.f.selected.path)]+args,cwd=runtime,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
            out=r.stdout+r.stderr;self.assertIn(b'NETWORK_ATTEMPTS=0',out);self.assertNotIn(b'sk-DUMMY_CORRECTION',out)
            return r,out
        args=['--authorization',str(self.path),'--authorization-sha256',digest(self.a)]
        r,out=invoke('authorize-historical-renewal',args);self.assertEqual(r.returncode,0,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        credit=History(self.f.state/'credit').read()
        r,out=invoke('run-historical-keychain',['--slot','12']);self.assertEqual(r.returncode,0 if outcome=='success'else 1,out)
        self.assertEqual(out.count(b'DUMMY_LOOKUP'),1);self.assertEqual(out.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),0 if outcome=='denied'else 1)
        if outcome=='denied':
            self.assertEqual(History(self.f.state/'credit').read(),credit)
            self.assertEqual(History(self.f.state/'attempt-12').read(),[])
            self.assertIn(b'keychain_denied',out)
        else:
            self.assertEqual(len(History(self.f.state/'credit').read()),len(credit)+1)
            self.assertEqual(len(History(self.f.state/'attempt-12').read()),3 if outcome=='success'else 2)
            terminal=History(self.f.state).read()[-1]
            if outcome=='success':
                report=terminal['historical_report'];self.assertEqual(report['forward_diagnostic']['purpose'],historical.OUTPUT_HEADROOM_PURPOSE)
                self.assertEqual(report['generation_allowance']['max_output_tokens'],25000);self.assertEqual(report['receipt']['accounting']['usage']['output_tokens'],5000);self.assertEqual(report['forward_diagnostic']['prior_cause'],'unknown');self.assertFalse(report['forward_diagnostic']['prior_outcome_reinterpreted'])
            else:self.assertEqual((terminal['phase'],terminal['reason']),('response_parsing','responses_incomplete_max_output_tokens' if outcome=='incomplete' else 'responses_usage_limit' if outcome=='over_usage' else 'responses_contract_changed'))
            for action,arg in [('run-historical-keychain',['--slot','12']),('authorize-historical-renewal',args)]:
                r,out=invoke(action,arg);self.assertEqual(r.returncode,1,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        self.assertEqual(manifest,verify_installation(runtime))
        for p,b in self.before.items():self.assertTrue(p.read_bytes().startswith(b))
    def test_installed_success_receipt_report_and_restart(self):self.installed('success')
    def test_installed_incomplete_preserves_debit_and_restart(self):self.installed('incomplete')
    def test_installed_usage_above_allowance_refused(self):self.installed('over_usage')
    def test_installed_wrong_echo_refused(self):self.installed('wrong_echo')
    def test_installed_denied_key_no_debit_or_send(self):self.installed('denied')

class DefaultLimitTests(unittest.TestCase):
    def test_no_session_or_model_flag_widens_parser(self):
        ns={};exec(FIXTURE_CODE,ns);documented=ns['documented']
        from ai_movie_investigator.responses_protocol import parse_response,INTEGRATION_MODEL
        from ai_movie_investigator.controller import output_schema
        from ai_movie_investigator.supervised_authorization import selected_output_limit,response_output_limit
        from ai_movie_investigator.credit_test import request
        self.assertEqual(decode(request('synthetic-test'))['max_output_tokens'],4096)
        self.assertEqual(selected_output_limit('a'*64),4096);self.assertEqual(response_output_limit(object()),4096)
        value=documented();value['max_output_tokens']=25000
        with self.assertRaisesRegex(Refusal,'responses_contract_changed'):
            parse_response(encoded(value),output_schema(),expected_model=INTEGRATION_MODEL)

if __name__=='__main__':unittest.main()
