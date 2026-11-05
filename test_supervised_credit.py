import copy
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.credit_test import request,count_request
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.history import History
from ai_movie_investigator.responses_http import HTTPResult,ExplicitCredential
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL


class SupervisedCreditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.state=self.root/'state';self.state.mkdir(mode=0o700)
        command.enroll(self.state)
        self.evidence=dict(project='proj_fixture',account_reference='FIXTURE-account',observed_at=90,
            expires_at=200,credit_expires_at=300,available_usd=[19,1],billing_reference='FIXTURE-no-billing',
            paid_fallback=False,owner_reference='FIXTURE-owner',count_fee_reference='FIXTURE-fee',
            count_fee_maximum=[1,100],count_coverage_reference='FIXTURE-coverage')
        # Only this absent external verifier and the HTTP boundary are simulated.
        self.gate=patch.object(command,'real_activation_refusal',return_value=None)
        self.gate.start();self.addCleanup(self.gate.stop)
        self.key='sk_SYNTHETIC_NOT_REAL'
        self.seen=[]

    def count(self,body,**kw):
        self.assertEqual(len(History(self.state/'credit').read()),1)
        self.assertEqual(body,count_request('synthetic-integration-1'))
        self.seen.append('count')
        return HTTPResult(200,encoded(dict(object='response.input_tokens',input_tokens=1200)),
            'req_fixture_count',digest(decode(body)),kw['project'],'/v1/responses/input_tokens')

    def generate(self,body,**kw):
        self.assertEqual(len(History(self.state/'credit').read()),2)
        self.assertEqual(body,request('synthetic-integration-1'))
        self.assertEqual(kw['authorization']['input_limit'],1200)
        self.seen.append('generation')
        reply=dict(binding_hash=aliases('synthetic-integration-1'),kind='final',lookups=[],result=dict(
            status='unresolved',candidate=None,alternatives=[],citations=[],rationale='Synthetic only',
            uncertainty='No real evidence',next_action='human_review'))
        raw=decode(simulated_response(reply,1).body);raw['model']=INTEGRATION_MODEL
        raw.pop('prompt_cache_options');raw['usage']['input_tokens_details']={'cached_tokens':0}
        return HTTPResult(200,encoded(raw),'req_fixture_generation',digest(decode(body)),kw['project'],'/v1/responses')

    def test_executable_command_no_echo_count_generation_and_restart_refusal(self):
        evidence=self.root/'evidence.json';evidence.write_bytes(encoded(self.evidence));evidence.chmod(0o600)
        args=['--state',str(self.state),'run','--evidence',str(evidence),'--slot','1']
        out=io.StringIO();err=io.StringIO()
        with patch('socket.socket',side_effect=AssertionError('network')),patch.object(command.sys.stdin,'isatty',return_value=True),\
             patch.object(command.sys.stderr,'isatty',return_value=True),patch('getpass.getpass',return_value=self.key) as prompt,\
             patch('ai_movie_investigator.supervised_credit.time.time',return_value=100),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.count',side_effect=self.count),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=self.generate):
            # run() binds its default time callable at definition; control it through this narrow test shim.
            original=command.run
            with patch.object(command,'run',side_effect=lambda d,e,s:original(d,e,s,clock=lambda:100)):
                # redirect only stdout so the isatty check is exercised on patched stderr.
                with redirect_stdout(out):self.assertEqual(command.main(args),0)
                with redirect_stdout(out):self.assertEqual(command.main(args),1)
            self.assertEqual(prompt.call_count,1)
        self.assertEqual(self.seen,['count','generation'])
        self.assertNotIn(self.key,out.getvalue())
        for path in self.state.rglob('*.jsonl'):self.assertNotIn(self.key,path.read_text())
        self.assertEqual(History(self.state).read()[-1]['reserved_usd'],[2,100])

    def test_unknown_fee_or_coverage_refuses_before_prompt_and_debit(self):
        for change in ({'count_fee_reference':None},{'count_fee_maximum':None},
                       {'count_coverage_reference':'unknown'},{'paid_fallback':True},{'expires_at':99}):
            with patch.object(command,'prompt_credential') as prompt:
                with self.assertRaises((Refusal,TypeError)):
                    command.run(self.state,dict(self.evidence,**change),1,clock=lambda:100)
            prompt.assert_not_called()
        self.assertEqual(History(self.state/'credit').read(),[])

    def test_count_timeout_burns_cent_and_never_generates_or_replays(self):
        with patch.object(command,'prompt_credential',return_value=ExplicitCredential(self.key)),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.count',side_effect=TimeoutError) as count,\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post') as generate:
            with self.assertRaises(TimeoutError):command.run(self.state,self.evidence,1,clock=lambda:100)
            with self.assertRaisesRegex(Refusal,'supervised_attempt_consumed'):
                command.run(self.state,self.evidence,1,clock=lambda:100)
        self.assertEqual(count.call_count,1);generate.assert_not_called()
        self.assertEqual(len(History(self.state/'credit').read()),1)

    def test_closed_gate_refuses_before_prompt_reservation_or_slot(self):
        self.gate.stop()
        before=History(self.state).read()
        with patch.object(command,'prompt_credential') as prompt,patch('socket.socket',side_effect=AssertionError('network')):
            with self.assertRaisesRegex(Refusal,'responses_real_authorization_unimplemented'):
                command.run(self.state,self.evidence,1,clock=lambda:100)
        prompt.assert_not_called()
        self.assertEqual(History(self.state).read(),before)
        self.assertEqual(History(self.state/'credit').read(),[])

    def test_forged_evidence_never_unlocks_real_network(self):
        with patch.object(command,'prompt_credential',return_value=ExplicitCredential(self.key)),\
             patch('socket.socket',side_effect=AssertionError('network')):
            with self.assertRaisesRegex(Refusal,'responses_real_authorization_unimplemented'):
                command.run(self.state,self.evidence,1,clock=lambda:100)
        self.assertEqual(len(History(self.state/'credit').read()),1)

    def test_non_tty_refuses_credential_and_no_getpass_fallback(self):
        with patch.object(command.sys.stdin,'isatty',return_value=False),patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'supervised_interactive_terminal_required'):command.prompt_credential()
        prompt.assert_not_called()

    def test_enrollment_not_recreated_and_missing_journal_refuses(self):
        with self.assertRaisesRegex(Refusal,'supervised_enrollment_exists'):command.enroll(self.state)
        (self.state/'credit'/'ai-investigator-v1.jsonl').unlink()
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(FileNotFoundError):command.run(self.state,self.evidence,1,clock=lambda:100)
        prompt.assert_not_called()
