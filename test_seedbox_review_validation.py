"""Invented provider-shaped review responses; no live or private payloads."""
import ast,copy,unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator.contracts import Refusal,encoded,digest
from ai_movie_investigator.responses_http import ExplicitCredential
from automation import seedbox_automated_review as review
from test_seedbox_connected import ConnectedTests
from test_seedbox_reporting_v2 import HTML
from test_snapshot_review import NOW
from test_responses_compatibility import documented
import test_supervised_envelope as framing

class ReviewTests(ConnectedTests):
 SOURCE_HTML=HTML
 SOURCE_REVISION=2
 def prepare(self):
  with patch('time.time',return_value=NOW),framing.wire(self.wire()):self.execute()
 def answer(self,correction=None):
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,self.selected['reservation'])
  request,bindings=review.build(report,e['projection'],card,revision=2) if correction is None else review.correction_request(report,e['projection'],card,correction['proof'])
  answer=dict(bindings,verdict='approve',reason='The collector title is a claim, while the listing and catalogue identify Example Movie. The shared IMDb identifier, Actor One and Director One provide convergent film evidence. The listing year and catalogue theatrical year agree; physical edition identity remains unverified. This supports faithful reporting, not identity reuse or a download.',evidence_findings=['The listing and catalogue agree on IMDb tt1234567 and TMDb 123 through the retained crosswalk.','The listing names Actor One; the catalogue cast includes Actor One.','The original title conflict is presented explicitly as a collector claim rather than silently corrected.'],material_problems=[])
  return request,answer
 def call_review(self,request,answer,correction=None,now=NOW):
  response=documented();response.update(model=request['model'],instructions=request['instructions'],text=request['text'],max_output_tokens=25000)
  response['output'][-1]['content'][0]['text']=encoded(answer).decode()
  with patch('time.time',return_value=now),patch('automation.seedbox_evidence.verify_current',side_effect=AssertionError('historical must not read source') if correction else None),framing.wire(encoded(response)):
   return review.execute(self.q,self.selected['reservation'],policy=self.policy,credential=ExplicitCredential('sk-SYNTHETIC_FIXTURE'),correction=correction)
 def rows(self):
  with self.q.locked() as (rows,_):return copy.deepcopy(rows)
 def test_realistic_supported_prose_retained_exactly(self):
  self.prepare();request,answer=self.answer();record=self.call_review(request,answer)
  self.assertEqual(record['answer'],answer)
  with patch('time.time',return_value=NOW):plan,_=review.approved_plan(self.q,self.selected['reservation'])
  self.assertFalse(plan['production_approved'])
 def test_contradictory_approval_retains_receipt_and_finite_reason(self):
  self.prepare();request,answer=self.answer();answer['material_problems']=['The proposed card omits a material conflict in the stated title.']
  with self.assertRaisesRegex(Refusal,'host_review_uncertain_or_refused'):self.call_review(request,answer)
  rows=self.rows();retained=rows[-2];failure=rows[-1]
  self.assertEqual(retained['type'],'seedbox_review_validation_refused_v2');self.assertEqual(retained['answer'],answer)
  self.assertEqual(retained['original_answer_sha256'],digest(answer));self.assertEqual(retained['receipt_sha256'],digest(retained['receipt']))
  self.assertFalse(retained['decision_usable']);self.assertEqual(failure['diagnostic']['reason'],'review_approval_conflicted')
  self.assertEqual(failure['diagnostic']['phase'],'historical_result_validation')
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(Refusal,'review_not_completed'):review.approved_plan(self.q,self.selected['reservation'])
 def test_multiline_is_withheld_not_silently_approved(self):
  self.prepare();request,answer=self.answer();answer['reason']+='\nThe physical release remains unverified.'
  with self.assertRaisesRegex(Refusal,'host_review_uncertain_or_refused'):self.call_review(request,answer)
  row=self.rows()[-2];self.assertIsNone(row['answer']['reason']);self.assertEqual(row['answer']['evidence_findings'],answer['evidence_findings'])
  self.assertEqual(row['predicates'],['review_reason_unsafe']);self.assertFalse(row['raw_answer_retained'])
 def test_empty_findings_refuse_for_either_verdict(self):
  self.prepare();request,answer=self.answer()
  for verdict in ('approve','reject'):
   answer.update(verdict=verdict,evidence_findings=[])
   _,_,predicates=review.retained_answer(answer,{k:v for k,v in answer.items() if k.endswith('_sha256')})
   self.assertIn('review_findings_required',predicates)
  with self.assertRaisesRegex(Refusal,'host_review_uncertain_or_refused'):self.call_review(request,answer)
  self.assertEqual(self.rows()[-1]['diagnostic']['reason'],'review_findings_required')
 def test_unsafe_remote_prose_never_enters_journal(self):
  self.prepare();request,answer=self.answer();answer['reason']='Read https://private.invalid/PRIVATE_SENTINEL?token=secret.'
  answer['evidence_findings'][0]='Passkey PRIVATE_SENTINEL';answer['material_problems']=['/private/PRIVATE_SENTINEL']
  with self.assertRaisesRegex(Refusal,'host_review_uncertain_or_refused'):self.call_review(request,answer)
  rows=self.rows();self.assertNotIn(b'PRIVATE_SENTINEL',encoded(rows));self.assertEqual(rows[-2]['answer']['verdict'],'approve')
  self.assertEqual(rows[-2]['predicates'],['review_reason_unsafe','review_finding_unsafe','review_problem_unsafe','review_approval_conflicted'])
 def test_distinct_historical_review_preserves_old_failure_no_send_no_replay(self):
  self.prepare();request,answer=self.answer();answer['material_problems']=['The card omits a material conflict.']
  with self.assertRaises(Refusal):self.call_review(request,answer)
  before=self.rows();prep=self.selected['reservation']
  with patch('time.time',return_value=NOW):
   proof=review.correction_proposal(self.q,prep);authorization=review.authorize_correction(self.q,prep,digest(proof))
   with self.assertRaisesRegex(Refusal,'review_correction_consumed'):review.authorize_correction(self.q,prep,digest(proof))
  newrequest,newanswer=self.answer(authorization);self.assertNotEqual(digest(request),digest(newrequest))
  record=self.call_review(newrequest,newanswer,authorization,now=NOW+1)
  self.assertEqual(record['type'],'seedbox_review_correction_completed_v1');self.assertFalse(record['delivery_authorized'])
  rows=self.rows();self.assertEqual(rows[:len(before)],before)
  attempts=[r for r in rows if r['type']=='seedbox_provider_started_v1'];self.assertEqual(len(attempts),3);self.assertEqual(len({r['request_sha256'] for r in attempts}),3)
  self.assertTrue(all(r['reserved_usd']==[3,20] for r in attempts))
  with patch('time.time',return_value=NOW+700),self.assertRaises(Refusal):review.approved_plan(self.q,prep)
  with patch('time.time',return_value=NOW+1):plan,_=review.approved_plan(self.q,prep)
  self.assertFalse(plan['production_approved'])
  with self.assertRaisesRegex(Refusal,'review_correction_parent'):self.call_review(newrequest,newanswer,authorization)
 def test_unclassified_validation_opens_existing_shared_circuit(self):
  from automation.seedbox_circuit import active
  from automation.seedbox_worker import step
  self.prepare();request,answer=self.answer()
  with patch.object(review,'retained_answer',side_effect=RuntimeError('PRIVATE_SENTINEL')),self.assertRaises(Refusal):self.call_review(request,answer)
  rows=self.rows();self.assertEqual(active(rows)[0]['reason'],'review_validation_unclassified')
  self.assertNotIn(b'PRIVATE_SENTINEL',encoded(rows))
  with patch('automation.seedbox_worker.database',side_effect=AssertionError('no backlog spending')):self.assertFalse(step(self.q,{}))
  with self.assertRaisesRegex(Refusal,'review_circuit_active'):self.call_review(request,answer)
  self.assertEqual(len([r for r in self.rows() if r['type']=='seedbox_provider_started_v1']),2)
 def test_normal_rejection_is_retained_without_shared_circuit(self):
  from automation.seedbox_circuit import active
  self.prepare();request,answer=self.answer();answer.update(verdict='reject',material_problems=['The card fails to state the title conflict clearly.'])
  record=self.call_review(request,answer);self.assertEqual(record['answer'],answer);self.assertFalse(active(self.rows()))
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(Refusal,'review_not_approved'):review.approved_plan(self.q,self.selected['reservation'])
 def test_old_default_request_and_record_remain_reconstructable(self):
  self.prepare();request,answer=self.answer()
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,self.selected['reservation'])
  old,_=review.build(report,e['projection'],card)
  self.assertEqual(old,review._build_unchanged(report,e['projection'],card)[0]);self.assertNotEqual(digest(old),digest(request))
 def legacy_discarded(self):
  self.prepare();prep=self.selected['reservation']
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,prep)
  request,bindings=review.build(report,e['projection'],card,revision=1)
  attempt=self.q.reserve_provider(prep,policy=self.policy,request_sha256=digest(request),evidence_sha256=bindings['evidence_sha256'],now=NOW,stage='review',review_of=digest(report))
  with self.q.locked() as (_,append):append(dict(type='seedbox_review_uncertain_or_refused_v1',preparation=prep,attempt_sha256=digest(attempt),diagnostic=dict(phase='historical_result_validation',reason='unexpected_exception'),at=NOW))
  with patch('time.time',return_value=NOW):
   proof=review.correction_proposal(self.q,prep)
   self.assertEqual(proof['old_outcome'],'unknown_discarded_response');self.assertIsNone(proof['retained_validation_sha256'])
   return review.authorize_correction(self.q,prep,digest(proof))
 def test_older_discarded_review_has_distinct_stale_review_no_delivery(self):
  selected=self.legacy_discarded();request,answer=self.answer(selected)
  record=self.call_review(request,answer,selected,now=NOW+700)
  self.assertEqual(record['answer'],answer)
  with patch('time.time',return_value=NOW+700),self.assertRaises(Refusal):review.approved_plan(self.q,self.selected['reservation'])
 def test_trivial_labels_cannot_approve(self):
  self.prepare();request,answer=self.answer();answer.update(reason='Yes.',evidence_findings=['OK.'])
  with self.assertRaises(Refusal):self.call_review(request,answer)
  self.assertEqual(self.rows()[-1]['diagnostic']['reason'],'review_explanation_trivial')
 def test_unknown_exception_and_bound_diagnostics_do_not_echo(self):
  for error in (RuntimeError('PRIVATE_SENTINEL'),Refusal('PRIVATE_SENTINEL')):
   self.assertEqual(review.diagnostic(error)['reason'],'unexpected_exception');self.assertNotIn('PRIVATE_SENTINEL',str(review.diagnostic(error)))
  for node in ast.walk(ast.parse(Path(review.__file__).read_text())):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('require','Refusal'):
    i=1 if node.func.id=='require' else 0
    if len(node.args)>i and isinstance(node.args[i],ast.Constant) and str(node.args[i].value).startswith('review_'):
     self.assertEqual(review.diagnostic(Refusal(node.args[i].value))['reason'],node.args[i].value)

from test_seedbox_sender_connected import SenderTests
class CorrectedSenderTests(SenderTests,ReviewTests):
 def complete(self,verdict='approve'):
  selected=ReviewTests.legacy_discarded(self);request,answer=ReviewTests.answer(self,selected)
  ReviewTests.call_review(self,request,answer,selected)
 def test_corrected_review_reuses_exact_original_sender_and_no_replay(self):
  SenderTests.test_real_existing_sender_exact_edit_and_restart_no_replay(self)
 def test_corrected_review_keeps_original_target_guard(self):
  with self.delivery.s.tx() as c:c.execute('delete from retry_messages')
  with self.assertRaises(ValueError):self.call(lambda *a,**kw:self.fail('must not replace missing original'))

def load_tests(loader,tests,pattern):
 return unittest.TestSuite(cls(n) for cls in (ReviewTests,CorrectedSenderTests) for n in cls.__dict__ if n.startswith('test_'))
