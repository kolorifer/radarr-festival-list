"""Invented receipt-bound completion branches; no real provider claim or I/O."""
import copy
import unittest
from unittest.mock import patch
from ai_movie_investigator import new_case as n, supervised_authorization as a
from ai_movie_investigator.contracts import Refusal, digest, text
from ai_movie_investigator.history import History
import test_captured_activation as fixture


class CapturedProvenance(unittest.TestCase):
    def setUp(self):
        self.x = fixture.Activation('test_exact_context_receipt_report_and_reset_without_gate_patch')
        self.x.setUp()
        self.addCleanup(self.x.doCleanups)
        self.f = self.x.f

    def real_label_branch(self, raw=None):
        consume = a.consume_captured_completion
        calls = []

        def selected_branch(held, answer):
            # Consume the actual invented in-process receipt first. Only select
            # the real-label branch for this offline regression, not real trust.
            proof = consume(held, answer)
            self.assertTrue(proof['simulated'])
            calls.append(proof['receipt_hash'])
            return dict(proof, simulated=False)

        with self.x.context(), a._simulated_captured_io():
            self.f.authorize()
            with patch.object(a, 'consume_captured_completion', selected_branch):
                result = self.f.run_case(raw)
        self.assertEqual(len(calls), 1)
        return result

    def test_receipt_correlated_label_completes_valid_answer(self):
        self.assertEqual(self.real_label_branch()['status'], 'completed')
        report = self.f.case.read()[-1]['report']
        receipt = History(self.f.f.state / 'attempt-7').read()[-1]
        self.assertEqual(report['receipt_hash'], digest(receipt))
        self.assertEqual(report['provenance']['mode'], 'receipt_correlated_generation')
        self.assertTrue(report['generation_invoked'])
        self.assertFalse(report['provider_verified'])
        self.assertFalse(report['draft']['sent'])
        text(report['provenance']['chat_reference'], 240)
        self.assertEqual(report['assessment'], self.f.reply['result'])
        with self.assertRaises(Refusal):
            n.complete(self.f.case, digest(self.f.request), self.f.reply,
                       dict(mode='supervised_supplied', chat_reference='no replay'))

    def test_real_label_does_not_mask_answer_rejection(self):
        reply = copy.deepcopy(self.f.reply)
        reply['result']['citations'][0]['evidence_id'] = 'unsupported'
        with self.assertRaisesRegex(Refusal, 'unsupported_citation'):
            self.real_label_branch(self.f.response(reply))
        self.assertEqual(self.f.case.read()[-1]['type'], 'new_case_completion_rejected')
        self.assertEqual(History(self.f.f.state / 'attempt-7').read()[-1]['type'], 'bound_send_receipt')
        self.assertFalse(any(r['type'] == 'new_case_completed' for r in self.f.case.read()))

    def test_slash_guard_remains_unchanged(self):
        with self.assertRaisesRegex(Refusal, 'unsafe_text'):
            text('Fixed transport request/project correlation; not chat ingestion or delivery', 240)


if __name__ == '__main__':
    unittest.main()
