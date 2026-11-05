"""One manually selected fifth slot, invented consumed history and offline I/O."""
import time
import unittest
from fractions import Fraction
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator import supervised_authorization as authority
from ai_movie_investigator.contracts import Refusal,encoded,digest
from ai_movie_investigator.credit_test import ledger_total,reserve,TOTAL
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.responses_http import FixedResponsesHTTP
import test_supervised_continuation as continuation
import test_supervised_diagnostics as diagnostics
import test_supervised_cli as executable


class FifthTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time()
        self.c=continuation.ContinuationTests('test_ungranted_slot_and_slot5_refuse')
        def unknown(*a,**kw):
            authority.observe_phase('response_parsing' if self._testMethodName=='test_wrong_terminal_diagnostic_refuses_before_extension' else 'http_receive')
            raise Refusal('responses_network_completion_unknown')
        with patch('time.time',return_value=self.now-600):
            self.c.setUp();self.c.extend()
            with self.c.r.inputs(),patch.object(FixedResponsesHTTP,'post',side_effect=unknown):
                with self.assertRaisesRegex(Refusal,'responses_network_completion_unknown'):
                    command.run(self.c.state,self.c.selected,4,clock=lambda:self.now-600)
        self.addCleanup(self.c.doCleanups)
        self.state=self.c.state;self.fixture=self.c.fixture
        self.new=dict(self.c.new,observed_at=self.now-1,expires_at=self.now+200,
                      credit_expires_at=self.now+300,owner_reference='FIXTURE-one-slot5-twelve-cent-total')
        self.path=self.fixture.root/'fifth.json';self.path.write_bytes(encoded(self.new));self.path.chmod(0o600)
        self.selected=command.read_evidence(self.path)
        self.original={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        self.assertEqual(len(History(self.state).read()),12)
        self.assertEqual(History(self.state).read()[-1]['category'],'network_outcome_unknown')

    def extend(self):return command.recover_once(self.state,self.c.selected,self.selected,slot=5)

    def preserved(self):
        for p,b in self.original.items():
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),b)
            else:self.assertTrue(p.read_bytes().startswith(b))
        self.assertEqual(list((self.state/'attempt-1').iterdir()),[])

    def test_one_extension_conserves_twelve_cents_and_refuses_replay_or_sixth(self):
        with patch('getpass.getpass') as prompt,patch.object(FixedResponsesHTTP,'post') as post,patch('socket.socket',side_effect=AssertionError('network')):
            self.assertEqual(self.extend(),dict(status='recovery_authorized_no_api_call',permitted_slot=5,cumulative_usd=[12,100]))
        prompt.assert_not_called();post.assert_not_called();self.preserved()
        with self.c.r.inputs(),diagnostics.wire_fixture('completed','synthetic-integration-5'):
            self.assertEqual(command.run(self.state,self.selected,5)['status'],'completed')
        rows=History(self.state/'credit').read()
        self.assertEqual([e['reserved_usd'] for e in rows],[[3,100]]*4)
        self.assertEqual(ledger_total(rows,'proj_fixture',ceiling=Fraction(12,100)),Fraction(12,100))
        self.assertEqual(TOTAL,Fraction(5,100))
        with self.assertRaises(Refusal):ledger_total(rows,'proj_fixture')
        credit=History(self.state/'credit')
        with self.assertRaises(Refusal):reserve(credit,project='proj_fixture',request_hash=digest('sixth'),input_bound=400000,
            now=self.now,file_identity=command.file_identity(credit),debit=(3,100))
        for slot in range(1,7):
            with patch('getpass.getpass') as prompt:
                with self.assertRaises(Refusal):command.run(self.state,command.read_evidence(self.path),slot)
            prompt.assert_not_called()
        with self.assertRaises(Refusal):self.extend()
        self.preserved()

    def test_invalid_input_and_duplicate_grant_change_nothing(self):
        self.extend();before={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        with self.assertRaises(Refusal):self.extend()
        with self.c.r.inputs('key_TRACKING_NOT_SECRET'),patch.object(FixedResponsesHTTP,'post') as post:
            with self.assertRaisesRegex(Refusal,'responses_credential_invalid'):command.run(self.state,self.selected,5)
        post.assert_not_called();self.assertEqual(before,{p:p.read_bytes() for p in self.state.rglob(FILENAME)})
        self.assertEqual(list((self.state/'attempt-5').iterdir()),[])

    def test_ungranted_slot_five_and_six_refuse_without_prompt(self):
        with patch('getpass.getpass') as prompt:
            for slot in (5,6):
                with self.assertRaises(Refusal):command.run(self.state,self.selected,slot)
                with self.assertRaises(Refusal):command.recover_once(self.state,self.c.selected,self.selected,slot=6)
        prompt.assert_not_called();self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])

    def test_interrupted_grant_is_terminal(self):
        original=command.Path.mkdir
        def fail(path,*a,**kw):
            if path.name=='attempt-5':raise OSError('fixture interruption')
            return original(path,*a,**kw)
        with patch.object(command.Path,'mkdir',fail):
            with self.assertRaises(OSError):self.extend()
        self.assertEqual(len(History(self.state).read()),13)
        with self.assertRaises(Refusal):self.extend()
        with self.assertRaises(Refusal):command.run(self.state,self.selected,5)
        self.assertFalse((self.state/'attempt-5').exists());self.preserved()

    def test_changed_evidence_or_prior_history_refuses(self):
        for delta in ({'project':'proj_other'},{'available_usd':[11,100]},{'expires_at':self.now-2}):
            self.path.write_bytes(encoded(dict(self.new,**delta)))
            with self.assertRaises(Refusal):command.recover_once(self.state,self.c.selected,command.read_evidence(self.path),slot=5)
            self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])
        self.path.write_bytes(encoded(self.new));self.selected=command.read_evidence(self.path)
        with History(self.state/'attempt-3').transaction(write=True) as (_,append):append(dict(type='unknown'))
        with self.assertRaises(Refusal):self.extend()

    def test_wrong_terminal_diagnostic_refuses_before_extension(self):
        with self.assertRaisesRegex(Refusal,'supervised_recovery_state'):self.extend()
        self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])

    def test_genuine_installed_module_fifth_slot_uses_full_http_and_120_second_window(self):
        extension=diagnostics.WIRE_CODE+'''
FixedResponsesHTTP.post=original_post
wire_fixture('incomplete','synthetic-integration-5').__enter__()
import io,time
_base=io.BytesIO
_mono=time.monotonic
_offset=[0]
class LateHeaders(_base):
    waited=False
    def readline(self,*a,**kw):
        if not self.waited:self.waited=True;_offset[0]=30
        return super().readline(*a,**kw)
io.BytesIO=LateHeaders
time.monotonic=lambda:_mono()+_offset[0]
'''
        executable.SupervisedExecutableTests().execute_fixture(self.fixture,5,fifth=self,hook_extension=extension,
            category='protocol_refused',expected_reason='responses_not_completed',expected_phase='response_parsing')
        self.preserved()
