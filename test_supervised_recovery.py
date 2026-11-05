"""One explicit recovery; invented histories, dummy key and offline HTTP only."""
from contextlib import ExitStack
from fractions import Fraction
import time
import unittest
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded
from ai_movie_investigator.credit_test import ledger_total, request, reserve, TOTAL
from ai_movie_investigator.history import History, FILENAME
from ai_movie_investigator.responses_http import FixedResponsesHTTP
from ai_movie_investigator.responses_transport import real_activation_refusal
import test_supervised_reauthorization as fixtures


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time()
        self.f=fixtures.ReauthorizationTests('test_second_renewal_refuses_without_append')
        with patch('time.time',return_value=self.now-600):
            self.f.setUp();self.f.renew()
            with self.inputs(),patch.object(FixedResponsesHTTP,'post',side_effect=TimeoutError):
                with self.assertRaises(TimeoutError):command._run(self.f.state,self.f.selected,2,clock=lambda:self.now-600)
        self.addCleanup(self.f.doCleanups)
        self.state=self.f.state
        self.path=self.f.f.root/'recovery-evidence.json'
        self.new=dict(self.f.new,observed_at=self.now-1,expires_at=self.now+200,
                      credit_expires_at=self.now+300,owner_reference='FIXTURE-recovery')
        self.path.write_bytes(encoded(self.new));self.path.chmod(0o600)
        self.selected=command.read_evidence(self.path)
        self.original={p:p.read_bytes() for p in self.state.rglob(FILENAME)}

    def inputs(self,key='sk-SYNTHETIC_NOT_REAL'):
        stack=ExitStack()
        stack.enter_context(patch.object(command.sys.stdin,'isatty',return_value=True))
        stack.enter_context(patch.object(command.sys.stderr,'isatty',return_value=True))
        stack.enter_context(patch('getpass.getpass',return_value=key))
        stack.enter_context(patch('socket.socket',side_effect=AssertionError('network')))
        stack.enter_context(patch('socket.getaddrinfo',side_effect=AssertionError('DNS')))
        return stack

    def recover(self):return command.recover_once(self.state,self.f.selected,self.selected)

    def preserved(self):
        for p,raw in self.original.items():self.assertTrue(p.read_bytes().startswith(raw))
        self.assertEqual((self.state/'attempt-2'/FILENAME).read_bytes(),self.original[self.state/'attempt-2'/FILENAME])
        self.assertEqual(list((self.state/'attempt-1').iterdir()),[])

    def test_one_manual_extension_then_one_unknown_request_retains_six_cents(self):
        with patch('getpass.getpass') as prompt,patch.object(FixedResponsesHTTP,'post') as send:
            self.assertEqual(self.recover(),dict(status='recovery_authorized_no_api_call',permitted_slot=3,cumulative_usd=[6,100]))
        prompt.assert_not_called();send.assert_not_called();self.preserved()
        def unknown(body,**kw):
            self.assertEqual(body,request('synthetic-integration-3'))
            args=dict(body=body,credential=kw['credential'],project=kw['project'],path='/v1/responses')
            self.assertIsNone(real_activation_refusal(kw['authorization'],**args))
            self.assertIsNone(real_activation_refusal(kw['authorization'],**args,consume=False))
            self.assertIsNotNone(real_activation_refusal(kw['authorization'],**args))
            raise TimeoutError()
        with self.inputs(),patch.object(FixedResponsesHTTP,'post',side_effect=unknown) as send,\
             patch.object(FixedResponsesHTTP,'count') as count:
            with self.assertRaises(TimeoutError):command.run(self.state,self.selected,3)
            for slot in (1,2,3,4):
                with self.assertRaises(Refusal):command.run(self.state,self.selected,slot)
            with self.assertRaises(Refusal):self.recover()
        self.assertEqual(send.call_count,1);count.assert_not_called();self.preserved()
        rows=History(self.state/'credit').read()
        self.assertEqual([r['reserved_usd'] for r in rows],[[3,100],[3,100]])
        self.assertEqual(ledger_total(rows,'proj_fixture',ceiling=Fraction(6,100)),Fraction(6,100))
        with self.assertRaisesRegex(Refusal,'credit_total_ceiling'):ledger_total(rows,'proj_fixture')
        credit=History(self.state/'credit')
        with self.assertRaises(Refusal):reserve(credit,project='proj_fixture',request_hash=digest('fourth'),
            input_bound=400000,now=self.now,file_identity=command.file_identity(credit),debit=(3,100))

    def test_duplicate_extension_and_invalid_key_consume_nothing(self):
        self.recover();before={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        with self.assertRaises(Refusal):self.recover()
        with self.inputs('key_TRACKING_NOT_SECRET'),patch.object(FixedResponsesHTTP,'post') as send:
            with self.assertRaisesRegex(Refusal,'responses_credential_invalid'):command.run(self.state,self.selected,3)
        send.assert_not_called()
        self.assertEqual(before,{p:p.read_bytes() for p in self.state.rglob(FILENAME)})
        self.assertEqual(list((self.state/'attempt-3').iterdir()),[])

    def test_no_extension_cannot_run_slot3(self):
        with patch('getpass.getpass') as prompt:
            with self.assertRaises(Refusal):command.run(self.state,self.selected,3)
        prompt.assert_not_called();self.preserved()

    def test_interrupted_extension_is_terminal_without_recreation(self):
        original=command.Path.mkdir
        def fail(path,*a,**kw):
            if path.name=='attempt-3':raise OSError('fixture interruption')
            return original(path,*a,**kw)
        with patch.object(command.Path,'mkdir',fail):
            with self.assertRaises(OSError):self.recover()
        self.assertEqual(len(History(self.state).read()),6)
        with self.assertRaises(Refusal):self.recover()
        with self.assertRaises(Refusal):command.run(self.state,self.selected,3)
        self.preserved()

    def test_wrong_project_expired_model_or_price_refuses_extension(self):
        for delta in ({'project':'proj_other'},{'expires_at':self.now-2},
                      {'model':'other'},{'available_usd':[5,100]},{'input_rate':[0,1]}):
            self.path.write_bytes(encoded(dict(self.new,**delta)))
            self.selected=command.read_evidence(self.path)
            with self.assertRaises(Refusal):self.recover()
            self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])

    def test_retained_attempt_change_refuses_before_prompt(self):
        self.recover()
        with History(self.state/'attempt-2').transaction(write=True) as (_,append):append(dict(type='unknown'))
        with patch('getpass.getpass') as prompt:
            with self.assertRaises(Refusal):command.run(self.state,self.selected,3)
        prompt.assert_not_called()

    def test_evidence_change_after_prompt_burns_slot_without_new_debit(self):
        self.recover()
        def changed(*a):
            self.path.write_bytes(encoded(dict(self.new,owner_reference='changed')))
            return 'sk-SYNTHETIC_NOT_REAL'
        with self.inputs(),patch('getpass.getpass',side_effect=changed),patch.object(FixedResponsesHTTP,'post') as send:
            with self.assertRaises(Refusal):command.run(self.state,self.selected,3)
        send.assert_not_called()
        self.assertEqual(len(History(self.state/'credit').read()),1)
        self.assertEqual(History(self.state).read()[-1]['slot'],3)

    def test_existing_attempt3_and_replaced_credit_inode_refuse(self):
        target=self.state/'attempt-3';target.symlink_to(self.state/'attempt-2')
        with self.assertRaises(Refusal):self.recover()
        target.unlink()
        credit=self.state/'credit'/FILENAME;saved=credit.with_name('retained')
        credit.rename(saved);credit.write_bytes(saved.read_bytes());credit.chmod(0o600)
        with self.assertRaises(Refusal):self.recover()
        self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])


if __name__=='__main__':unittest.main()
