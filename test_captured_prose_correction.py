"""Finite second defect correction; invented complete historical lineage."""
import copy, unittest
from unittest.mock import patch
from ai_movie_investigator import new_case as n, supervised_credit as c, supervised_authorization as a
from ai_movie_investigator.contracts import Refusal,digest
from ai_movie_investigator.history import History,FILENAME
import test_captured_completion_correction as correction
import test_captured_freshness as freshness
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class ProseCorrection(unittest.TestCase):
    def test_full_lineage_safe_completion_no_repeat_or_raw_retention(self):
        f=freshness.CapturedFreshness('test_prior_401_successor_refresh_preserves_debit_and_report')
        f.continuation=True;f.setUp();self.addCleanup(f.doCleanups);f.propose()
        consume=a.consume_captured_completion
        def real(held,answer):return dict(consume(held,answer),simulated=False)
        with f.x.context(),a._simulated_captured_io():
            f.refresh()
            with patch.object(n,'_CAPTURED_PROVENANCE',n._OLD_CAPTURED_PROVENANCE),patch.object(a,'consume_captured_completion',real),diagnostics.DiagnosticTests().inputs(),framing.wire(f.f.response()):
                with self.assertRaisesRegex(Refusal,'unsafe_text'):c.run(f.f.f.state,f.f.selected,8,captured=True,clock=lambda:f.now)
        helper=correction.CompletionCorrection();helper.f=f.f;helper.activation=f.x;helper.prior_slot=8
        helper.propose()
        response=copy.deepcopy(f.f.reply);response['result'].update(rationale='Invented source/title evidence',uncertainty='Which cut?')
        with f.x.context(),a._simulated_captured_io():
            self.assertEqual(f.f.authorize()['slot'],9)
            # Model the previous accepted code: no prose-copy stage yet.
            with patch.object(n,'_captured_prose_copy',side_effect=lambda answer:(answer,{})),patch.object(a,'consume_captured_completion',real),diagnostics.DiagnosticTests().inputs(),framing.wire(f.f.response(response)):
                with self.assertRaisesRegex(Refusal,'unsafe_text'):c.run(f.f.f.state,f.f.selected,9,captured=True,clock=lambda:f.now)
        old={p:p.read_bytes() for p in (f.f.f.state/FILENAME,f.f.case.directory/FILENAME,f.f.f.state/'credit'/FILENAME,*[f.f.f.state/f'attempt-{i}'/FILENAME for i in (7,8,9)])}
        original_request=copy.deepcopy(f.f.request);original_packet=copy.deepcopy(f.f.packet)
        # Distinct proof and consent paths preserve earlier pinned artifacts.
        proofdir=f.x.root/'prose-proof';proofdir.mkdir(mode=0o700);f.x.root=proofdir;helper.prior_slot=9
        def prose_proof(fix):fix.update(kind='captured_prose_retention_correction_v1',purpose='one_corrected_captured_assessment_with_explicit_prose_withholding')
        with patch.object(n,'captured_completion_correction_consent',n.captured_prose_correction_consent):helper.propose(prose_proof)
        with f.x.context(),a._simulated_captured_io():
            self.assertEqual(f.f.authorize()['slot'],10)
            with patch.object(a,'consume_captured_completion',real),diagnostics.DiagnosticTests().inputs(),framing.wire(f.f.response(response)):
                self.assertEqual(c.run(f.f.f.state,f.f.selected,10,captured=True,clock=lambda:f.now)['status'],'completed')
            with self.assertRaises(Refusal):c.run(f.f.f.state,f.f.selected,10,captured=True,clock=lambda:f.now)
            with self.assertRaises(Refusal):f.f.authorize()
        for p,raw in old.items():self.assertTrue(p.read_bytes().startswith(raw))
        for i in (7,8,9):
            p=f.f.f.state/f'attempt-{i}'/FILENAME;self.assertEqual(p.read_bytes(),old[p])
        report=f.f.case.read()[-1]['report'];root=f.f.root.read()[-1]
        self.assertTrue(report['generation_invoked']);self.assertFalse(report['draft']['sent'])
        self.assertEqual(report['reply_hash'],digest(response));self.assertEqual(report['retained_reply_hash'],digest(root['answer']))
        self.assertEqual(report['receipt_hash'],digest(History(f.f.f.state/'attempt-10').read()[-1]))
        self.assertEqual(report['prose_handling']['rationale']['status'],'withheld')
        self.assertEqual(report['prose_handling']['uncertainty']['status'],'withheld')
        for p in (f.f.case.directory/FILENAME,f.f.f.state/FILENAME):
            self.assertNotIn(b'Invented source/title',p.read_bytes());self.assertNotIn(b'Which cut?',p.read_bytes())
        rows=f.f.case.read();self.assertEqual(len([r for r in rows if r['type']=='new_case_generation_started']),4)
        self.assertEqual(len([r for r in rows if r['type']=='new_case_completion_rejected']),2)
        credit=History(f.f.f.state/'credit').read();self.assertEqual(len(credit),9);self.assertEqual(len({r['request_hash'] for r in credit}),9)
        self.assertEqual(f.f.request,original_request);self.assertEqual(f.f.packet,original_packet)
        self.assertFalse((f.f.f.state/'attempt-11').exists())
        helper.prior_slot=10
        with patch.object(n,'captured_completion_correction_consent',n.captured_prose_correction_consent),self.assertRaisesRegex(Refusal,'captured_correction_prior'):helper.propose(prose_proof)
        with self.assertRaises(Refusal):n.complete(f.f.case,digest(f.f.request),response,dict(mode='supervised_supplied',chat_reference='no recovery'))

    def test_wrong_predecessor_refuses_before_allocation(self):
        helper=correction.CompletionCorrection('test_wrong_code_proof_refuses_before_new_attempt');helper.setUp();self.addCleanup(helper.doCleanups);helper.fail_label()
        def change(fix):fix.update(kind='captured_prose_retention_correction_v1',purpose='one_corrected_captured_assessment_with_explicit_prose_withholding')
        with patch.object(n,'captured_completion_correction_consent',n.captured_prose_correction_consent),self.assertRaisesRegex(Refusal,'captured_correction_prior'):helper.propose(change)
        self.assertFalse((helper.f.f.state/'attempt-8').exists())

if __name__=='__main__':unittest.main()
