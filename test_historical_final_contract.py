"""Versioned final-only request after invented receipt-bearing local failure."""
import copy,os,subprocess,sys,time,unittest
from pathlib import Path
from ai_movie_investigator import historical_nano as h
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.installation import install_runtime,verify_installation
import test_historical_headroom as fixtures
from test_responses_compatibility import FIXTURE_CODE
from test_supervised_envelope import wire_code

class FinalContractTests(unittest.TestCase):
    def setUp(self):
        self.h=fixtures.HeadroomTests('test_same_entire_request_except_aliases_and_one_child_across_new_ids')
        self.h.setUp();self.addCleanup(self.h.doCleanups);self.f=self.h.f;self.h.grant()
        self.runtime=self.f.f.root/'final-runtime';self.runtime.mkdir(mode=0o700)
        self.manifest=install_runtime(Path(__file__).resolve().parent,self.runtime)
        self.hooks=self.f.f.root/'final-hooks';self.hooks.mkdir(mode=0o700)
        r,out=self.invoke('run-historical-keychain',['--slot','12'],mode='legacy_failure')
        self.assertEqual(r.returncode,1,out)
        self.events=History(self.f.state).read();self.prior=next(e['historical']for e in self.events if e.get('slot')==12 and 'historical'in e)
        self.assertEqual((self.events[-1]['phase'],self.events[-1]['reason']),('receipt_recorded','unexpected_exception'))
        self.assertEqual(len(History(self.f.state/'attempt-12').read()),3)
        identity=digest('invented-final-contract-correction')
        self.a=dict(self.h.a,purpose=h.FINAL_CONTRACT_PURPOSE,response_contract=h.FINAL_CONTRACT_VERSION,
            diagnostic_id=identity,owner_reference='invented-explicit-final-contract-correction',prior_slot=12,
            root_prefix_sha256=digest(self.events),prior_run=self.prior['run'],prior_grant_sha256=digest(self.prior),
            prior_attempt_sha256=digest(History(self.f.state/'attempt-12').read()),prior_terminal_sha256=digest(self.events[-1]),
            prior_request_sha256=digest(self.prior['request']),
            request_sha256=digest(h.renewed_proposal(self.prior,identity,output_limit=25000,response_contract=h.FINAL_CONTRACT_VERSION)['request']))
        self.path=self.f.f.root/'final-authority.json';self.write(self.a)
        self.before={p:p.read_bytes()for p in self.f.state.rglob(FILENAME)}
    def write(self,a):self.path.write_bytes(encoded(a));self.path.chmod(0o600)
    def grant(self):return h.authorize_renewal(self.f.state,self.f.selected,self.path,digest(self.a))
    def invoke(self,action,args,mode='valid'):
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
from ai_movie_investigator import keychain_credential as keychain,historical_nano as historical
from ai_movie_investigator.contracts import Refusal
def dummy(project):
 assert project=='proj_fixture';print('DUMMY_LOOKUP');return b'sk-DUMMY_FINAL'
keychain._native=dummy
@atexit.register
def finish():print('NETWORK_ATTEMPTS='+str(len(attempts)))
'''+FIXTURE_CODE+'''
if 'run-historical-keychain' in sys.argv:
 from pathlib import Path
 from ai_movie_investigator.history import History
 from ai_movie_investigator.contracts import decode,encoded
 from ai_movie_investigator.disclosure import aliases
 slot=int(sys.argv[sys.argv.index('--slot')+1]);rows=History(Path(sys.argv[sys.argv.index('--state')+1])).read()
 grant=next(r['historical']for r in rows if r.get('slot')==slot and 'historical'in r)
 value=documented();value['max_output_tokens']=grant['request']['max_output_tokens'];value['text']=grant['request']['text']
 answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
'''
        if mode=='legacy_failure':hook+="\n def fail(*a,**kw):raise Refusal('INVENTED_UNCLASSIFIED_LOCAL_FAILURE')\n historical.report=fail\n"
        elif mode=='null':hook+="\n answer['result']=None\n"
        elif mode=='text':hook+="\n answer['result']['rationale']='PRIVATE_MARKER edition/cut'\n"
        elif mode=='wrong_schema':hook+="\n from ai_movie_investigator.controller import output_schema\n value['text']['format']['schema']=output_schema()\n"
        hook+="\nif 'run-historical-keychain' in sys.argv:\n value['output'][-1]['content'][0]['text']=encoded(answer).decode();selected_raw=encoded(value);framing='chunked'\n"+wire_code()+"\nif 'run-historical-keychain' in sys.argv:\n _wire=wire_fixture('completed');_wire.__enter__()\n"
        (self.hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(self.hooks)+os.pathsep+str(self.runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        r=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),action,'--evidence',str(self.f.selected.path)]+args,cwd=self.runtime,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=25)
        out=r.stdout+r.stderr;self.assertIn(b'NETWORK_ATTEMPTS=0',out);self.assertNotIn(b'sk-DUMMY_FINAL',out);self.assertNotIn(b'PRIVATE_MARKER',out)
        return r,out
    def test_exact_request_diff_old_history_and_installed_completion(self):
        r,out=self.invoke('authorize-historical-renewal',['--authorization',str(self.path),'--authorization-sha256',digest(self.a)])
        self.assertEqual(r.returncode,0,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        grant=History(self.f.state).read()[-2]['historical'];new=decode(h.validate(grant,'proj_fixture'));old=self.prior['request']
        old_data=decode(old['input'][0]['content'][0]['text']);data=decode(new['input'][0]['content'][0]['text'])
        data['binding_hash']=old_data['binding_hash']
        for row,prior in zip(data['evidence'],old_data['evidence']):row['alias']=prior['alias']
        new['input'][0]['content'][0]['text']=encoded(data).decode();new['instructions']=old['instructions'];new['text']=old['text']
        self.assertEqual(new,old)
        for key in ('input_sha256','prepared_at','case','disclosure','fingerprint'):self.assertEqual(grant[key],self.prior[key])
        r,out=self.invoke('run-historical-keychain',['--slot','13']);self.assertEqual(r.returncode,0,out)
        self.assertEqual(out.count(b'DUMMY_LOOKUP'),1);self.assertEqual(out.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
        report=History(self.f.state).read()[-1]['historical_report'];self.assertEqual(report['response_contract'],h.FINAL_CONTRACT_VERSION)
        self.assertEqual(report['forward_diagnostic']['prior_cause'],'unknown');self.assertFalse(report['forward_diagnostic']['prior_outcome_reinterpreted'])
        self.assertEqual(len(History(self.f.state/'attempt-13').read()),3)
        self.restart_and_preserve()
    def restart_and_preserve(self):
        for p,raw in self.before.items():
            self.assertTrue(p.read_bytes().startswith(raw))
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
        r,out=self.invoke('run-historical-keychain',['--slot','13']);self.assertEqual(r.returncode,1,out);self.assertNotIn(b'DUMMY_LOOKUP',out)
        with self.assertRaises(Refusal):self.grant()
        self.assertEqual(self.manifest,verify_installation(self.runtime))
    def failure(self,mode,reason,phase,rows):
        self.grant();credit=History(self.f.state/'credit').read()
        r,out=self.invoke('run-historical-keychain',['--slot','13'],mode=mode);self.assertEqual(r.returncode,1,out)
        terminal=History(self.f.state).read()[-1];self.assertEqual((terminal['reason'],terminal['phase']),(reason,phase))
        self.assertEqual(len(History(self.f.state/'attempt-13').read()),rows)
        self.assertEqual(len(History(self.f.state/'credit').read()),len(credit)+1)
        self.assertFalse(any(e.get('slot')==13 and e['type']=='supervised_completed'for e in History(self.f.state).read()))
        self.assertTrue(all(b'PRIVATE_MARKER'not in p.read_bytes()for p in self.f.state.rglob(FILENAME)))
        self.restart_and_preserve()
    def test_null_refused_before_receipt(self):self.failure('null','responses_answer_schema','response_parsing',2)
    def test_wrong_schema_echo_refused_before_receipt(self):self.failure('wrong_schema','responses_contract_changed','response_parsing',2)
    def test_text_policy_keeps_receipt_but_refuses_completion_without_retaining_answer(self):self.failure('text','unsafe_text','historical_result_validation',3)
    def test_wrong_authority_pins_or_contract_no_allocation(self):
        for key,value in [('response_contract','wrong'),('max_output_tokens',4096),('prior_slot',11),('prior_attempt_sha256','a'*64),('prior_terminal_sha256','b'*64),('input_sha256','c'*64),('project','proj_wrong'),('expires_at',time.time()-1)]:
            a=dict(self.a,**{key:value});self.write(a)
            with self.subTest(key=key),self.assertRaises(Refusal):h.authorize_renewal(self.f.state,self.f.selected,self.path,digest(a))
            self.assertEqual(self.before,{p:p.read_bytes()for p in self.f.state.rglob(FILENAME)})

if __name__=='__main__':unittest.main()
