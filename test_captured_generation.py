"""Dormant captured occurrence → actual fixed HTTP implementation → unsent draft.
All inputs and socket/native I/O are invented. No provider authentication claim.
"""
import copy,io,time,unittest,os,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr,contextmanager
from ai_movie_investigator import new_case as n, supervised_credit as c, supervised_authorization as a
from ai_movie_investigator.contracts import Refusal,captured_outcome,decode,digest,encoded
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.replay import synthetic_case
from test_responses_compatibility import documented
import test_standing_credit as standing
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class CapturedGenerationTests(unittest.TestCase):
    def setUp(self):
        self.f=standing.StandingTests('test_grant_preserves_legacy_hashes_and_default_cap')
        self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.grant()
        self.root=History(self.f.state);self.selected=self.f.selected
        path=self.f.f.root/'captured';path.mkdir(mode=0o700);self.case=History(path)
        raw,binding,evidence=synthetic_case(165)
        for row in evidence:row.update(observed_at=time.time()-10,expires_at=time.time()+150)
        self.packet=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=binding,
            evidence=evidence,decisions=[],trusted_issuers=['synthetic_owner'])
        self.request=n.prepare(self.case,self.packet,binding)
        self.body=n.captured_request(self.request)
        self.path=self.f.f.root/'captured-authority.json'
        with self.root.transaction(write=True) as (events,_):
            with self.case.transaction(write=True) as (rows,_):
                self.consent=n.captured_consent(self.root,events,self.case,rows,digest(self.request),self.selected.data)
        self.path.write_bytes(encoded(self.consent));self.path.chmod(0o600)
        self.reply=dict(binding_hash=self.request['binding_hash'],kind='final',lookups=[],result=dict(
            status='supported_candidate',candidate=dict(imdb='tt9000127',tmdb=9000127),alternatives=[],
            citations=[dict(evidence_id='evidence-1',claim='crosswalk'),dict(evidence_id='evidence-2',claim='source_identity')],
            rationale='Invented source and catalogue assert this candidate.',uncertainty='Identity and edition unverified.',next_action='human_review'))
        self.net=patch('socket.socket',side_effect=AssertionError('network forbidden'));self.net.start();self.addCleanup(self.net.stop)
        self.sender=patch('identity_telegram_digest.Digest.tick',side_effect=AssertionError('notification forbidden'))
        self.sender.start();self.addCleanup(self.sender.stop)

    @contextmanager
    def gate(self):
        with patch.object(n,'captured_activation_refusal',return_value=None),a._simulated_captured_io():yield

    def authorize(self):
        return n.authorize_captured(self.f.state,self.selected,self.case.directory,digest(self.request),self.path,digest(self.consent))

    def response(self,reply=None):
        value=documented();body=decode(self.body,65536)
        value['instructions']=body['instructions'];value['text']=body['text'];value['max_output_tokens']=body['max_output_tokens']
        value['output'][-1]['content'][0]['text']=encoded(reply or self.reply).decode()
        return encoded(value)

    def run_case(self,raw=None):
        with diagnostics.DiagnosticTests().inputs(),framing.wire(raw or self.response()),redirect_stdout(io.StringIO()):
            return c.run(self.f.state,self.selected,7,captured=True)

    def test_connected_receipt_draft_and_restarts(self):
        with self.gate():
            self.assertEqual(self.authorize()['slot'],7)
            self.assertEqual(self.run_case()['status'],'completed')
            with patch.object(c,'prompt_credential') as prompt:
                with self.assertRaises(Refusal):c.run(self.f.state,self.selected,7,captured=True)
            prompt.assert_not_called()
            with self.assertRaises(Refusal):self.authorize()
        report=self.case.read()[-1]['report'];receipt=History(self.f.state/'attempt-7').read()[-1]
        self.assertEqual(report['receipt_hash'],digest(receipt));self.assertEqual(report['assessment']['status'],'supported_candidate')
        self.assertFalse(report['generation_invoked']);self.assertFalse(report['provider_receipt_correlated']);self.assertFalse(report['provider_verified']);self.assertFalse(report['draft']['sent'])
        self.assertTrue(report['connected_transport_invoked']);self.assertIn('SIMULATED',report['draft']['text'])
        self.assertIn('completeness unknown',report['qualifications']['decision_coverage'])
        self.assertEqual(len(History(self.f.state/'credit').read()),6)
        permit=History(self.f.state/'attempt-7').read()[0]['permit']
        self.assertEqual(permit['output_limit'],25000);self.assertEqual(permit['maximum_debit'],[3,100])
        with self.assertRaises(Refusal):n.complete(self.case,digest(self.request),self.reply,dict(mode='simulation',chat_reference='copied'))
        self.f.preserved()

    def test_gate_before_private_reads_and_mutations(self):
        before=self.root.read();case=self.case.read()
        with patch.object(c,'_read_evidence',side_effect=AssertionError('private read')),patch.object(c,'prompt_credential',side_effect=AssertionError('credential')):
            with self.assertRaisesRegex(Refusal,'captured_real_activation_unissued'):self.authorize()
            with self.assertRaisesRegex(Refusal,'captured_real_activation_unissued'):c.run('/absent',None,7,captured=True)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(c.main(['--state','/absent','run-captured-keychain','--evidence','/absent','--slot','7']),1)
        self.assertEqual(before,self.root.read());self.assertEqual(case,self.case.read())

    def test_supplied_answer_remains_honest(self):
        report=n.complete(self.case,digest(self.request),self.reply,dict(mode='supervised_supplied',chat_reference='external supplied answer'))
        self.assertFalse(report['generation_invoked']);self.assertNotIn('receipt_hash',report)
        with self.gate(),self.assertRaises(Refusal):self.authorize()

    def test_uncertain_send_burns_case_and_no_supplied_fallback(self):
        with self.gate():
            self.authorize()
            raw=decode(self.response());raw['usage']['total_tokens']=1
            with self.assertRaisesRegex(Refusal,'responses_usage_invalid'):self.run_case(encoded(raw))
            with self.assertRaises(Refusal):self.run_case()
        rows=History(self.f.state/'attempt-7').read();self.assertEqual(len(rows),2)
        self.assertEqual(self.case.read()[-1]['type'],'new_case_generation_started')
        with self.assertRaisesRegex(Refusal,'captured_completion_unbound'):
            n.complete(self.case,digest(self.request),self.reply,dict(mode='simulation',chat_reference='fallback forbidden'))
        self.assertEqual(len(History(self.f.state/'credit').read()),6)

    def test_wrong_binding_and_unsupported_citation(self):
        with self.gate():
            self.authorize();reply=copy.deepcopy(self.reply);reply['result']['citations'][0]['evidence_id']='unknown'
            with self.assertRaisesRegex(Refusal,'unsupported_citation'):self.run_case(self.response(reply))
        self.assertEqual(self.case.read()[-1]['type'],'new_case_completion_rejected')
        self.assertEqual(History(self.f.state/'attempt-7').read()[-1]['type'],'bound_send_receipt')

    def test_disclosure_authority_mismatch_before_reservation(self):
        self.consent['request']['input'][0]['content'][0]['text']='{}'
        self.path.write_bytes(encoded(self.consent));before=self.root.read()
        with self.gate(),self.assertRaisesRegex(Refusal,'captured_authority_changed'):self.authorize()
        self.assertEqual(self.root.read(),before);self.assertFalse((self.f.state/'attempt-7').exists())

    def test_final_only_schema_and_no_json_receipt_capability(self):
        schema=decode(self.body,65536)['text']['format']['schema']['properties']
        self.assertEqual(schema['kind']['enum'],['final']);self.assertEqual(schema['lookups']['maxItems'],0)
        self.assertNotIn('anyOf',schema['result'])
        with self.assertRaisesRegex(Refusal,'captured_receipt_unbound'):
            a._Session.complete_captured(object(),encoded(self.reply))


    def test_wrong_final_binding_is_consumed_without_receipt(self):
        with self.gate():
            self.authorize();reply=copy.deepcopy(self.reply);reply['binding_hash']='a'*64
            with self.assertRaisesRegex(Refusal,'responses_answer_schema'):self.run_case(self.response(reply))
        self.assertEqual(len(History(self.f.state/'attempt-7').read()),2)

    def test_expired_selection_before_credential_and_reservation(self):
        with self.gate():
            self.authorize();before=self.root.read()
            with patch.object(c,'prompt_credential') as prompt:
                with self.assertRaisesRegex(Refusal,'decision_or_evidence_applicability_changed'):
                    c.run(self.f.state,self.selected,7,captured=True,clock=lambda:time.time()+160)
            prompt.assert_not_called()
            self.assertEqual(self.root.read(),before);self.assertEqual(History(self.f.state/'attempt-7').read(),[])

    def test_superseded_case_refuses_before_credential(self):
        with self.gate():
            self.authorize();changed=copy.deepcopy(self.packet)
            changed['facts']['title']+=' changed';changed['binding']['version']=digest('changed')
            for row in changed['evidence']:row['scope']=copy.deepcopy(changed['binding'])
            self.case.intake(changed)
            with patch.object(c,'prompt_credential') as prompt:
                with self.assertRaises(Refusal):c.run(self.f.state,self.selected,7,captured=True)
            prompt.assert_not_called()
        self.assertEqual(History(self.f.state/'attempt-7').read(),[])

    def test_case_lock_held_through_wire_and_completion(self):
        from ai_movie_investigator.history import _WRITE_TRANSACTIONS
        from ai_movie_investigator import responses_http
        original=responses_http.FixedResponsesHTTP.post;observed=[]
        def inspect(http,*args,**kw):
            held=n._CAPTURED.get();self.assertIsNotNone(held)
            held.root.require_write_transaction(held.root_events);held.history.require_write_transaction(held.events)
            self.assertTrue(held.started);observed.append('wire')
            with self.assertRaises(Refusal):
                with History(self.case.directory).transaction(write=True):pass
            return original(http,*args,**kw)
        with self.gate():
            self.authorize()
            with patch.object(responses_http.FixedResponsesHTTP,'post',inspect):self.run_case()
        self.assertEqual(observed,['wire']);self.assertIsNone(n._CAPTURED.get());self.assertEqual(_WRITE_TRANSACTIONS.get(),())

    def test_forged_http_object_cannot_bind_completion(self):
        from ai_movie_investigator import responses_http
        original=responses_http.FixedResponsesHTTP.post
        def replaced(http,*args,**kw):
            result=original(http,*args,**kw)
            return responses_http.HTTPResult(result.status,result.body,result.request_id,result.request_sha256,result.project,result.path)
        with self.gate():
            self.authorize()
            with patch.object(responses_http.FixedResponsesHTTP,'post',replaced):
                with self.assertRaisesRegex(Refusal,'captured_receipt_unbound'):self.run_case()
        self.assertEqual(len(History(self.f.state/'attempt-7').read()),3)
        self.assertFalse(any(row['type']=='new_case_completed' for row in self.case.read()))

    def test_grant_alone_cannot_mint_inprocess_completion(self):
        with self.gate():
            self.authorize();grant=self.root.read()[-2]['captured']
            with self.root.transaction(write=True) as (events,_):
                with n.captured_case_lock(self.root,events,grant,self.selected.data) as held:
                    held.start()
                    with self.assertRaisesRegex(Refusal,'captured_receipt_unbound'):held.complete(self.reply)
        self.assertFalse(any(row['type']=='new_case_completed' for row in self.case.read()))

    def test_supplied_provenance_cannot_claim_generation(self):
        with self.assertRaisesRegex(Refusal,'assessment_provenance'):
            n.complete(self.case,digest(self.request),self.reply,
                dict(mode='receipt_correlated_generation',chat_reference='forged claim'))
        self.assertFalse(any(r['type']=='new_case_completed' for r in self.case.read()))

    def test_changed_transport_provenance_cannot_relabel_a_receipt(self):
        from ai_movie_investigator import responses_http
        original=responses_http.FixedResponsesHTTP.post
        def replaced(http,*args,**kw):
            result=original(http,*args,**kw)
            a._CAPTURED_SIMULATED_IO.set(None)
            return result
        with self.gate():
            self.authorize()
            with patch.object(responses_http.FixedResponsesHTTP,'post',replaced):
                with self.assertRaisesRegex(Refusal,'captured_receipt_unbound'):self.run_case()
        self.assertFalse(any(r['type']=='new_case_completed' for r in self.case.read()))

    def test_selected_output_limit_reaches_parser_and_old_default_unchanged(self):
        from ai_movie_investigator.responses_protocol import OUTPUT_TOKENS
        self.assertEqual(OUTPUT_TOKENS,4096)
        self.assertEqual(decode(n.offline_request(self.request),65536)['max_output_tokens'],4096)
        with self.gate():
            self.authorize();value=decode(self.response());value['usage'].update(output_tokens=24000,total_tokens=value['usage']['input_tokens']+24000)
            value['usage']['output_tokens_details']['reasoning_tokens']=23000
            self.assertEqual(self.run_case(encoded(value))['status'],'completed')
        self.assertEqual(History(self.f.state/'attempt-7').read()[-1]['accounting']['usage']['output_tokens'],24000)

    def test_selected_output_limit_overflow_refused(self):
        with self.gate():
            self.authorize();value=decode(self.response());value['usage'].update(output_tokens=25001,total_tokens=value['usage']['input_tokens']+25001)
            with self.assertRaises(Refusal):self.run_case(encoded(value))
        self.assertEqual(len(History(self.f.state/'attempt-7').read()),2)

    def installed(self,action,*,opened=False,malformed=False):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        from test_responses_compatibility import FIXTURE_CODE
        runtime=self.f.f.root/'captured-runtime';hooks=self.f.f.root/'captured-hooks'
        if not runtime.exists():
            runtime.mkdir(mode=0o700);self.manifest=install_runtime(Path(__file__).resolve().parent,runtime)
            hooks.mkdir(mode=0o700)
        hook="""
import atexit,errno,os,sys
attempts=[]
def audit(event,args):
 if event.startswith('socket.'):
  attempts.append(event);raise AssertionError('network forbidden')
sys.addaudithook(audit)
if sys.platform.startswith('linux'):
 def absent(*a,**kw):raise OSError(errno.ENODATA,'fixture')
 os.getxattr=absent
from ai_movie_investigator import keychain_credential as k,new_case as n
from ai_movie_investigator.contracts import decode,encoded
@atexit.register
def finished():print('NETWORK_ATTEMPTS='+str(len(attempts)))
def dummy(project):
 assert project=='proj_fixture';print('DUMMY_LOOKUP');return b'sk-DUMMY_CAPTURED'
k._native=dummy
"""
        if opened:hook+="\nn.captured_activation_refusal=lambda:None\nfrom ai_movie_investigator.supervised_authorization import _simulated_captured_io\n_simulated_io=_simulated_captured_io();_simulated_io.__enter__()\n"
        if opened and action=='run-captured-keychain':
            # Only fixture bytes are embedded, never repository imports after installation.
            raw=self.response()
            if malformed:
                v=decode(raw);v['usage']['total_tokens']=1;raw=encoded(v)
            hook+="\nselected_raw="+repr(raw)+"\nframing='chunked'\n"+framing.wire_code()+"\n_wire=wire_fixture('completed');_wire.__enter__()\n"
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(runtime),
             'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        args=['--case-history',str(self.case.directory),'--request-hash',digest(self.request),'--authorization',str(self.path),'--authorization-sha256',digest(self.consent)] if action=='authorize-captured' else ['--slot','7']
        result=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit',
            '--state',str(self.f.state),action,'--evidence',str(self.selected.path),*args],cwd=runtime,env=env,
            stdin=subprocess.DEVNULL,capture_output=True,timeout=25)
        output=result.stdout+result.stderr
        self.assertIn(b'NETWORK_ATTEMPTS=0',output);self.assertNotIn(b'sk-DUMMY_CAPTURED',output)
        self.assertEqual(self.manifest,verify_installation(runtime))
        return result,output

    def test_installed_default_closed_then_explicit_simulation_complete_restart(self):
        before={p:p.read_bytes() for p in self.f.f.root.rglob(FILENAME)}
        for action in ('authorize-captured','run-captured-keychain'):
            result,out=self.installed(action);self.assertEqual(result.returncode,1,out)
            self.assertIn(b'captured_real_activation_unissued',out);self.assertNotIn(b'DUMMY_LOOKUP',out)
            self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',out)
        self.assertEqual(before,{p:p.read_bytes() for p in self.f.f.root.rglob(FILENAME)})
        result,out=self.installed('authorize-captured',opened=True);self.assertEqual(result.returncode,0,out)
        result,out=self.installed('run-captured-keychain',opened=True);self.assertEqual(result.returncode,0,out)
        self.assertEqual(out.count(b'DUMMY_LOOKUP'),1);self.assertEqual(out.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
        report=self.case.read()[-1]['report'];self.assertTrue(report['connected_transport_invoked']);self.assertFalse(report['generation_invoked'])
        result,out=self.installed('run-captured-keychain',opened=True);self.assertEqual(result.returncode,1,out)
        self.assertNotIn(b'DUMMY_LOOKUP',out);self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',out)

    def test_installed_uncertainty_retains_debit_and_refuses_restart(self):
        result,out=self.installed('authorize-captured',opened=True);self.assertEqual(result.returncode,0,out)
        result,out=self.installed('run-captured-keychain',opened=True,malformed=True);self.assertEqual(result.returncode,1,out)
        self.assertIn(b'responses_usage_invalid',out);self.assertEqual(len(History(self.f.state/'credit').read()),6)
        result,out=self.installed('run-captured-keychain',opened=True);self.assertEqual(result.returncode,1,out)
        self.assertNotIn(b'DUMMY_LOOKUP',out);self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',out)

if __name__=='__main__':unittest.main()

