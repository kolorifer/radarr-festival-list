"""Dummy-input executable checks: no real credential, state, or network."""
import unittest
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal
from ai_movie_investigator.history import History
import test_supervised_credit as fixtures
import test_supervised_cli as executable


class SecretInputTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        f.setUp();self.addCleanup(f.doCleanups);return f

    def execute(self,**kwargs):
        f=self.fixture()
        executable.SupervisedExecutableTests().execute_fixture(f,1,**kwargs)
        return f

    def test_genuine_module_tracking_and_project_identifiers_consume_nothing(self):
        for value in (b'key_SYNTHETIC_TRACKING_ID_ONLY',b'proj_SYNTHETIC_IDENTIFIER_ONLY'):
            with self.subTest(kind=value.split(b'_')[0]):
                self.execute(dummy=value,category='credential_format_invalid',invalid=True)

    def test_genuine_module_malformed_secret_consumes_nothing(self):
        self.execute(dummy=b'sk-invalid space SYNTHETIC',category='credential_format_invalid',invalid=True)

    def test_genuine_module_http_rejection_is_safe_and_keeps_reservation(self):
        self.execute(dummy=b'sk-proj-SYNTHETIC_NOT_AUTHENTICATED',failure='responses_http_rejected',category='http_rejected')

    def test_genuine_module_network_unknown_is_safe_and_keeps_reservation(self):
        self.execute(failure='responses_network_completion_unknown',category='network_outcome_unknown')

    def test_format_rejection_and_cancel_do_not_append_or_reprompt(self):
        f=self.fixture();before=(f.state/'ai-investigator-v1.jsonl').read_bytes()
        for value in ('key_SYNTHETIC_IDENTIFIER','proj_SYNTHETIC_IDENTIFIER','', 'sk_BAD_PREFIX'):
            with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
                 patch('getpass.getpass',return_value=value) as prompt,\
                 patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=AssertionError('HTTP forbidden')),\
                 patch('socket.socket',side_effect=AssertionError('network forbidden')):
                with self.assertRaisesRegex(Refusal,'responses_credential_invalid'):command.run(f.state,f.selected,1)
                self.assertEqual(prompt.call_count,1)
            self.assertEqual((f.state/'ai-investigator-v1.jsonl').read_bytes(),before)
            self.assertEqual(History(f.state/'credit').read(),[])
            self.assertEqual(list((f.state/'attempt-1').iterdir()),[])
        with patch.object(command,'prompt_credential',side_effect=EOFError):
            with self.assertRaises(EOFError):command.run(f.state,f.selected,1)
        self.assertEqual((f.state/'ai-investigator-v1.jsonl').read_bytes(),before)
