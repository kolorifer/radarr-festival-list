"""Manual renewal of a proven pre-reservation failure; all data is disposable."""
import io
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded
from ai_movie_investigator.credit_test import request, reserve, ledger_total, TOTAL
from ai_movie_investigator.history import History, FILENAME
from ai_movie_investigator.responses_http import FixedResponsesHTTP, HTTPResult
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL
from ai_movie_investigator.responses_transport import real_activation_refusal
from ai_movie_investigator.disclosure import aliases
import test_supervised_credit as fixtures


class ReauthorizationTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time()
        self.f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        with patch('time.time',return_value=self.now-600):self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.state=self.f.state
        with History(self.state).transaction(write=True) as (_,append):
            append(dict(type='supervised_started',slot=1,at=self.now-600,evidence_hash=digest(self.f.evidence)))
        self.new=dict(self.f.evidence,observed_at=self.now-1,expires_at=self.now+200,
                      credit_expires_at=self.now+300,owner_reference='FIXTURE-fresh-owner')
        self.path=self.f.root/'fresh-evidence.json'
        self.path.write_bytes(encoded(self.new));self.path.chmod(0o600)
        self.selected=command.read_evidence(self.path)
        self.prefix=(self.state/FILENAME).read_bytes()
        self.old_bytes=self.f.path.read_bytes()
        self.credit_pin=command.file_identity(History(self.state/'credit'))

    def renew(self):return command.reauthorize(self.state,self.f.selected,self.selected)

    def unchanged(self):
        self.assertEqual((self.state/FILENAME).read_bytes(),self.prefix)
        self.assertEqual(self.f.path.read_bytes(),self.old_bytes)

    def generate(self,body,**kw):
        self.assertEqual(body,request('synthetic-integration-2'))
        args=dict(body=body,credential=kw['credential'],project=kw['project'],path='/v1/responses')
        self.assertIsNone(real_activation_refusal(kw['authorization'],**args))
        self.assertIsNone(real_activation_refusal(kw['authorization'],**args,consume=False))
        self.assertIsNotNone(real_activation_refusal(kw['authorization'],**args))
        reply=dict(binding_hash=aliases('synthetic-integration-2'),kind='final',lookups=[],result=dict(
            status='unresolved',candidate=None,alternatives=[],citations=[],rationale='Synthetic only',
            uncertainty='No real evidence',next_action='human_review'))
        raw=decode(simulated_response(reply,1).body);raw['model']=INTEGRATION_MODEL
        raw.pop('prompt_cache_options');raw['usage']['input_tokens_details']={'cached_tokens':0}
        return HTTPResult(200,encoded(raw),'req_fixture_reauthorized',digest(decode(body)),kw['project'],'/v1/responses')

    def test_manual_command_preserves_prefix_and_allows_only_unused_slot(self):
        with patch('socket.socket',side_effect=AssertionError('network')),patch('socket.getaddrinfo',side_effect=AssertionError('DNS')),\
             patch('getpass.getpass') as prompt,patch.object(FixedResponsesHTTP,'post') as send:
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(command.main(['--state',str(self.state),'reauthorize',
                    '--previous-evidence',str(self.f.path),'--evidence',str(self.path)]),0)
            self.assertEqual(decode(out.getvalue()),dict(status='reauthorized_no_api_call',permitted_slot=2))
            prompt.assert_not_called();send.assert_not_called()
        after=(self.state/FILENAME).read_bytes()
        self.assertTrue(after.startswith(self.prefix));self.assertEqual(len(History(self.state).read()),4)
        self.assertEqual(self.f.path.read_bytes(),self.old_bytes)
        self.assertEqual((self.state/'credit'/FILENAME).read_bytes(),b'')
        self.assertEqual(command.file_identity(History(self.state/'credit')),self.credit_pin)
        with patch('getpass.getpass') as prompt:
            for old in (self.f.selected,self.selected):
                with self.assertRaises(Refusal):command.run(self.state,old,1)
        prompt.assert_not_called()
        with patch('socket.socket',side_effect=AssertionError('network')),patch('socket.getaddrinfo',side_effect=AssertionError('DNS')),\
             patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',return_value=self.f.key),patch.object(FixedResponsesHTTP,'post',side_effect=self.generate) as send:
            result=command.run(self.state,command.read_evidence(self.path),2)
            self.assertEqual(result['reserved_usd'],[3,100]);self.assertEqual(send.call_count,1)
            with self.assertRaises(Refusal):command.run(self.state,self.selected,2)
        events=History(self.state).read()
        self.assertEqual([e.get('slot') for e in events if e['type']=='supervised_started'],[1,2])
        self.assertEqual(list((self.state/'attempt-1').iterdir()),[])
        self.assertEqual(ledger_total(History(self.state/'credit').read(),'proj_fixture'),TOTAL*3/5)
        self.assertTrue((self.state/FILENAME).read_bytes().startswith(self.prefix))
        self.assertEqual(self.f.path.read_bytes(),self.old_bytes)
        with self.assertRaises(Refusal):self.renew()

    def test_second_renewal_refuses_without_append(self):
        self.renew();before=(self.state/FILENAME).read_bytes()
        with self.assertRaisesRegex(Refusal,'supervised_reauthorization_state'):self.renew()
        self.assertEqual((self.state/FILENAME).read_bytes(),before)

    def test_charged_ledger_refuses_even_if_attempt_journal_missing(self):
        credit=History(self.state/'credit')
        reserve(credit,project='proj_fixture',request_hash=digest('charged'),input_bound=65536,
                now=self.now,file_identity=self.credit_pin)
        ledger=(credit.directory/FILENAME).read_bytes()
        with self.assertRaisesRegex(Refusal,'supervised_reauthorization_uncertain'):self.renew()
        self.unchanged();self.assertEqual((credit.directory/FILENAME).read_bytes(),ledger)

    def test_attempt_records_empty_journals_and_unknown_files_all_refuse(self):
        for slot in (1,2):
            for name,raw in ((FILENAME,b''),(FILENAME,b'uncertain or incomplete'),('unknown',b'')):
                with self.subTest(slot=slot,name=name,raw=raw):
                    p=self.state/f'attempt-{slot}'/name;p.write_bytes(raw);p.chmod(0o600)
                    try:
                        with self.assertRaisesRegex(Refusal,'supervised_reauthorization_uncertain'):self.renew()
                        self.unchanged();self.assertEqual(p.read_bytes(),raw)
                    finally:p.unlink()

    def test_extra_or_unknown_root_event_refuses(self):
        with History(self.state).transaction(write=True) as (_,append):
            append(dict(type='uncertain_send',slot=2))
        before=(self.state/FILENAME).read_bytes()
        with self.assertRaisesRegex(Refusal,'supervised_reauthorization_state'):self.renew()
        self.assertEqual((self.state/FILENAME).read_bytes(),before)

    def test_new_project_invalid_expiry_and_changed_cost_facts_refuse(self):
        for delta in ({'project':'proj_different'},{'observed_at':self.f.evidence['observed_at']},
                      {'expires_at':self.now-1},{'context_window':1},{'input_rate':[0,1]},
                      {'paid_fallback':True},{'model':'other'}):
            with self.subTest(delta=delta):
                self.path.write_bytes(encoded(dict(self.new,**delta)))
                self.selected=command.read_evidence(self.path)
                with self.assertRaises(Refusal):self.renew()
                self.unchanged()

    def test_same_path_or_hardlink_cannot_replace_old_evidence(self):
        with self.assertRaises(Refusal):command.reauthorize(self.state,self.f.selected,self.f.selected)
        hardlink=self.f.root/'hardlink.json';hardlink.hardlink_to(self.f.path)
        with self.assertRaises(Refusal):command.reauthorize(self.state,self.f.selected,command.read_evidence(hardlink))
        self.unchanged()

    def test_modified_original_selection_or_fresh_selection_refuses(self):
        for p,raw in ((self.f.path,encoded(dict(self.f.evidence,owner_reference='changed'))),
                      (self.path,encoded(dict(self.new,owner_reference='changed')))):
            original=p.read_bytes();p.write_bytes(raw)
            try:
                with self.assertRaises(Refusal):self.renew()
                self.assertEqual((self.state/FILENAME).read_bytes(),self.prefix)
            finally:p.write_bytes(original)
        self.assertEqual(self.f.path.read_bytes(),self.old_bytes)

    def test_fresh_evidence_expires_before_append(self):
        with patch('time.time',side_effect=[self.now,self.now+201]):
            with self.assertRaisesRegex(Refusal,'supervised_evidence_stale'):self.renew()
        self.unchanged()

    def test_storage_replacement_and_unsafe_permissions_refuse(self):
        credit=self.state/'credit'/FILENAME
        saved=self.state/'credit'/'retained';credit.rename(saved)
        credit.write_bytes(b'');credit.chmod(0o600)
        with self.assertRaisesRegex(Refusal,'supervised_storage_changed'):self.renew()
        self.unchanged();credit.unlink();saved.rename(credit)
        attempt=self.state/'attempt-1';attempt.chmod(0o775)
        try:
            with self.assertRaises(Refusal):self.renew()
            self.unchanged()
        finally:attempt.chmod(0o700)

    def test_renewed_selection_change_after_prompt_refuses_and_burns_slot(self):
        self.renew()
        def changed(*args):
            self.path.write_bytes(encoded(dict(self.new,owner_reference='changed')))
            return self.f.key
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',side_effect=changed),patch.object(FixedResponsesHTTP,'post') as send:
            with self.assertRaisesRegex(Refusal,'supervised_evidence_changed'):command.run(self.state,self.selected,2)
        send.assert_not_called()
        self.assertEqual(History(self.state/'credit').read(),[])
        self.assertEqual(History(self.state).read()[-1]['slot'],2)
        with self.assertRaises(Refusal):self.renew()

    def test_renewed_timeout_keeps_debit_and_no_recovery_or_replay(self):
        self.renew()
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',return_value=self.f.key),patch.object(FixedResponsesHTTP,'post',side_effect=TimeoutError) as send:
            with self.assertRaises(TimeoutError):command.run(self.state,self.selected,2)
            with self.assertRaises(Refusal):command.run(self.state,self.selected,2)
            with self.assertRaises(Refusal):self.renew()
        self.assertEqual(send.call_count,1)
        self.assertEqual([r['reserved_usd'] for r in History(self.state/'credit').read()],[[3,100]])
