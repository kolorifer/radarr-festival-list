"""One explicit slot4; invented retained history, no real input or network."""
import time
import unittest
from fractions import Fraction
from unittest.mock import patch
from contextlib import contextmanager
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal,encoded
from ai_movie_investigator.credit_test import ledger_total
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.responses_http import FixedResponsesHTTP
import test_supervised_recovery as recovery
import test_supervised_diagnostics as diagnostics
import test_supervised_cli as executable


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time()
        self.r=recovery.RecoveryTests('test_no_extension_cannot_run_slot3')
        with patch('time.time',return_value=self.now-600):
            self.r.setUp();self.r.recover()
            # Retain the precise pre-diagnostics historical eight-record shape.
            with self.r.inputs(),patch.object(FixedResponsesHTTP,'post',side_effect=TimeoutError):
                with self.assertRaises(TimeoutError):command._run(self.r.state,self.r.selected,3,clock=lambda:self.now-600)
        self.addCleanup(self.r.doCleanups)
        self.state=self.r.state;self.fixture=self.r.f.f
        self.new=dict(self.r.new,observed_at=self.now-1,expires_at=self.now+200,credit_expires_at=self.now+300,owner_reference='FIXTURE-one-slot4-nine-cent-total')
        self.path=self.fixture.root/'continuation.json';self.path.write_bytes(encoded(self.new));self.path.chmod(0o600)
        self.selected=command.read_evidence(self.path)
        self.original={p:p.read_bytes() for p in self.state.rglob(FILENAME)}

    def extend(self):return command.recover_once(self.state,self.r.selected,self.selected,slot=4)

    def preserved(self):
        for p,b in self.original.items():
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),b)
            else:self.assertTrue(p.read_bytes().startswith(b))
        self.assertEqual(list((self.state/'attempt-1').iterdir()),[])

    def test_single_manual_continuation_retains_prior_debits_and_caps_at_nine(self):
        with patch('getpass.getpass') as prompt,patch.object(FixedResponsesHTTP,'post') as post,patch('socket.socket',side_effect=AssertionError('network')):
            self.assertEqual(self.extend(),dict(status='recovery_authorized_no_api_call',permitted_slot=4,cumulative_usd=[9,100]))
        prompt.assert_not_called();post.assert_not_called();self.preserved()
        with self.r.inputs(),diagnostics.wire_fixture('incomplete','synthetic-integration-4'):
            with self.assertRaisesRegex(Refusal,'responses_not_completed'):command.run(self.state,self.selected,4)
        self.assertEqual(History(self.state).read()[-1]['phase'],'response_parsing')
        self.assertEqual(ledger_total(History(self.state/'credit').read(),'proj_fixture',ceiling=Fraction(9,100)),Fraction(9,100))
        with self.assertRaises(Refusal):ledger_total(History(self.state/'credit').read(),'proj_fixture')
        for slot in (1,2,3,4,5):
            with patch('getpass.getpass') as prompt:
                with self.assertRaises(Refusal):command.run(self.state,self.selected,slot)
            prompt.assert_not_called()
        with self.assertRaises(Refusal):self.extend()
        self.preserved()

    def test_invalid_input_and_duplicate_extension_consume_nothing(self):
        self.extend();before={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        with self.assertRaises(Refusal):self.extend()
        with self.r.inputs('key_TRACKING_NOT_SECRET'),patch.object(FixedResponsesHTTP,'post') as post:
            with self.assertRaisesRegex(Refusal,'responses_credential_invalid'):command.run(self.state,self.selected,4)
        post.assert_not_called();self.assertEqual(before,{p:p.read_bytes() for p in self.state.rglob(FILENAME)})
        self.assertEqual(list((self.state/'attempt-4').iterdir()),[])

    def test_ungranted_slot_and_slot5_refuse(self):
        with self.assertRaises(Refusal):command.run(self.state,self.selected,4)
        with self.assertRaises(Refusal):command.recover_once(self.state,self.r.selected,self.selected,slot=5)
        self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])

    def test_interrupted_continuation_is_terminal(self):
        mkdir=command.Path.mkdir
        def fail(path,*a,**kw):
            if path.name=='attempt-4':raise OSError('fixture interruption')
            return mkdir(path,*a,**kw)
        with patch.object(command.Path,'mkdir',fail):
            with self.assertRaises(OSError):self.extend()
        self.assertEqual(len(History(self.state).read()),9)
        with self.assertRaises(Refusal):self.extend()
        with self.assertRaises(Refusal):command.run(self.state,self.selected,4)
        self.preserved()

    def test_changed_prior_history_and_same_project_binding_refuse(self):
        for change in ({'project':'proj_other'},{'available_usd':[8,100]},{'expires_at':self.now-2}):
            self.path.write_bytes(encoded(dict(self.new,**change)))
            with self.assertRaises(Refusal):command.recover_once(self.state,self.r.selected,command.read_evidence(self.path),slot=4)
            self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])
        self.path.write_bytes(encoded(self.new));self.selected=command.read_evidence(self.path)
        with History(self.state/'attempt-2').transaction(write=True) as (_,append):append(dict(type='unknown'))
        with self.assertRaises(Refusal):self.extend()

    def test_failed_diagnostic_append_cannot_release_or_replay(self):
        self.extend();original=History.transaction
        @contextmanager
        def transaction(history,*a,**kw):
            with original(history,*a,**kw) as (events,append):
                def wrapped(e):
                    if e['type']=='supervised_diagnostic':raise OSError('FIXTURE')
                    return append(e)
                yield events,wrapped
        with self.r.inputs(),diagnostics.wire_fixture('incomplete','synthetic-integration-4'),patch.object(History,'transaction',transaction):
            with self.assertRaisesRegex(Refusal,'responses_not_completed'):command.run(self.state,self.selected,4)
        self.assertEqual(len(History(self.state/'credit').read()),3)
        with self.assertRaises(Refusal):command.run(self.state,self.selected,4)
        self.preserved()

    def test_genuine_installed_module_continuation_and_full_http_parser(self):
        extension=diagnostics.WIRE_CODE+"\nFixedResponsesHTTP.post=original_post\nwire_fixture('incomplete','synthetic-integration-4').__enter__()\n"
        executable.SupervisedExecutableTests().execute_fixture(self.fixture,4,continuation=self,
            hook_extension=extension,category='protocol_refused',expected_reason='responses_not_completed',expected_phase='response_parsing')
        self.preserved()
