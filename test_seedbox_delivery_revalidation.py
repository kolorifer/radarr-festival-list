"""Invented complete-card and same-facts source revalidation, no live I/O."""
import copy,hashlib,unittest
from contextlib import nullcontext
from unittest.mock import patch
from ai_movie_investigator.contracts import encoded,decode,digest,Refusal
from ai_movie_investigator.snapshot_review import projection
from automation import seedbox_automated_review as review,seedbox_evidence as evidence,seedbox_delivery_evidence as delivery
from automation.seedbox_assessment_queue import Queue
from test_seedbox_sender_connected import SenderTests
from test_seedbox_reporting_v2 import HTML
from test_snapshot_review import NOW


def bundle_for(test,now):
 prep=test.selected['reservation']
 with patch('time.time',return_value=NOW):old=evidence.load(test.q,prep)
 manifest=old['manifest'];path=test.path/('evidence-'+prep)
 bundle={k:(path/(k+'.bin')).read_bytes() for k in evidence.RAW_FIELDS}
 snap=decode(bundle['snapshot'],1048576);snap['generated_at']=now;bundle['snapshot']=encoded(snap)
 for field in ('source','catalogue'):
  obj=decode(bundle[field]);obj.update(observed_at=now,expires_at=now+900);bundle[field]=encoded(obj)
 h=lambda b:hashlib.sha256(b).hexdigest()
 att=copy.deepcopy(manifest['attestation']);att.update(snapshot_sha256=h(bundle['snapshot']),source_sha256=h(bundle['source']),catalogue_sha256=h(bundle['catalogue']),observed_at=now,expires_at=now+900)
 p=projection(bundle['snapshot'],h(bundle['snapshot']),old['projection']['case_id'],old['projection']['version'],bundle['source'],bundle['catalogue'],att,now=now)
 bundle.update(projection=p,derivation_revision=2,attestation=att,target_pin=manifest['target_pin'],coverage=manifest['coverage'])
 return bundle,old


def retain_fixture(test,now):
 prep=test.selected['reservation'];bundle,old=bundle_for(test,now)
 with patch('time.time',return_value=now):
  proof=delivery.proposal(test.q,prep)
  with test.q.locked() as (_,append):
   start=dict(type='seedbox_delivery_revalidation_started_v1',preparation=prep,proof=proof,proof_sha256=digest(proof),at=now);append(start)
  return delivery._retain(test.q,prep,bundle,start,old)


class DeliveryTests(SenderTests):
 SOURCE_HTML=HTML
 SOURCE_REVISION=2
 def setUp(self):
  original=Queue.enroll
  def enroll(directory,**kw):
   self.revalidation_config={'state':str(directory),'collector_database':{'fixture':True}}
   kw['configuration_sha256']=digest(self.revalidation_config)
   return original(directory,**kw)
  with patch.object(Queue,'enroll',side_effect=enroll):super().setUp()
 def revalidate(self,bundle=None,exception=None):
  prep=self.selected['reservation'];now=NOW+700
  if bundle is None:bundle,_=bundle_for(self,now)
  with patch('time.time',return_value=now):proof=delivery.proposal(self.q,prep)
  with patch('time.time',return_value=now),patch('automation.seedbox_host_io.database',return_value=nullcontext(None)),patch('automation.seedbox_host_io.selected_snapshot',return_value=(bundle['snapshot'],{},{})),patch('automation.seedbox_host_io.acquire',return_value=bundle,side_effect=exception) as acquire:
   result=delivery.revalidate(self.q,self.revalidation_config,prep,digest(proof))
   self.assertEqual(acquire.call_count,1);return result
 def test_stale_approved_report_revalidated_unchanged_and_original_sent_once(self):
  prep=self.selected['reservation']
  with self.q.locked() as (rows,_):before=copy.deepcopy(rows)
  old_html=(self.path/('report-'+prep+'.html')).read_bytes()
  with patch('time.time',return_value=NOW+700),self.assertRaises(Refusal):review.approved_plan(self.q,prep)
  self.revalidate()
  with self.q.locked() as (rows,_):
   self.assertEqual(rows[:len(before)],before);self.assertEqual(sum(r['type']=='seedbox_provider_started_v1' for r in rows),2)
  self.assertEqual((self.path/('report-'+prep+'.html')).read_bytes(),old_html)
  self.delivery_time=NOW+700;self.config['sender']['expires_at']=NOW+880
  SenderTests.test_real_existing_sender_exact_edit_and_restart_no_replay(self)
  with patch('time.time',return_value=NOW+701),self.assertRaisesRegex(Refusal,'delivery_revalidation_consumed'):delivery.proposal(self.q,prep)
 def test_changed_material_fact_refuses_and_cannot_fall_back(self):
  bundle,_=bundle_for(self,NOW+700);bundle['projection']['catalogue']['runtime_minutes']+=1
  with self.assertRaisesRegex(Refusal,'delivery_material_facts_changed'):self.revalidate(bundle)
  with patch('time.time',return_value=NOW),self.assertRaises(Refusal):delivery.current(self.q,self.selected['reservation'])
 def test_changed_target_refuses(self):
  bundle,_=bundle_for(self,NOW+700);bundle['target_pin']=copy.deepcopy(bundle['target_pin']);bundle['target_pin']['ref']['message_id']+=1
  with self.assertRaisesRegex(Refusal,'delivery_context_target_changed'):self.revalidate(bundle)
 def test_interrupted_read_burns_selection_without_fallback(self):
  prep=self.selected['reservation']
  with patch('time.time',return_value=NOW):proof=delivery.proposal(self.q,prep)
  with self.q.locked() as (_,append):append(dict(type='seedbox_delivery_revalidation_started_v1',preparation=prep,proof=proof,proof_sha256=digest(proof),at=NOW))
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(Refusal,'delivery_revalidation_incomplete'):delivery.current(self.q,prep)
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(Refusal,'delivery_revalidation_consumed'):delivery.proposal(self.q,prep)
 def test_new_proof_expiry_and_byte_change_refuse(self):
  self.revalidate();prep=self.selected['reservation']
  with patch('time.time',return_value=NOW+1601),self.assertRaises(Refusal):delivery.current(self.q,prep)
  p=self.path/('delivery-evidence-'+prep)/'source_original.bin';p.write_bytes(b'changed')
  with patch('time.time',return_value=NOW+701),self.assertRaisesRegex(Refusal,'host_evidence_changed'):delivery.current(self.q,prep)
 def test_source_auth_denial_opens_existing_shared_circuit(self):
  from automation.seedbox_host_io import SourceFailure
  from automation.seedbox_circuit import active
  with self.assertRaisesRegex(Refusal,'source_auth_denied'):self.revalidate(exception=SourceFailure('source_auth_denied'))
  with self.q.locked() as (rows,_):self.assertEqual(active(rows)[0]['reason'],'source_auth_denied')
 def test_source_rate_limit_pauses_other_source_reads(self):
  from automation.seedbox_host_io import SourceFailure
  from automation.seedbox_worker import source_paused
  with self.assertRaisesRegex(Refusal,'source_rate_limited'):self.revalidate(exception=SourceFailure('source_rate_limited',retry_after=120))
  with self.q.locked() as (rows,_):self.assertTrue(source_paused(rows,NOW+701));self.assertFalse(source_paused(rows,NOW+821))
 def test_rate_limit_longer_than_one_day_is_preserved(self):
  from automation.seedbox_host_io import SourceFailure
  from automation.seedbox_worker import source_paused
  with self.assertRaisesRegex(Refusal,'source_rate_limited'):self.revalidate(exception=SourceFailure('source_rate_limited',retry_after=172800))
  with self.q.locked() as (rows,_):self.assertTrue(source_paused(rows,NOW+700+86401));self.assertFalse(source_paused(rows,NOW+700+172800))
 def test_expiry_crossing_at_locked_callback_prevents_edit(self):
  from automation.seedbox_sender import deliver_reviewed
  self.revalidate();clock=[NOW+700];self.config['sender']['expires_at']=NOW+880
  def advance(*a,**kw):clock[0]=NOW+1590
  from pathlib import Path
  with patch('time.time',side_effect=lambda:clock[0]),patch('automation.seedbox_sender._process',return_value={'pid':123}),patch('automation.seedbox_sender._deployed',side_effect=lambda pin:Path(pin['fixture']).read_bytes()),patch('automation.seedbox_evidence.verify_current',side_effect=advance),patch('automation.reviewed_telegram_UNISSUED.urlopen',side_effect=AssertionError('expired proof must never send')) as wire:
   result=deliver_reviewed(self.q,self.config,self.selected['reservation'])
  self.assertEqual(result['status'],'uncertain');self.assertEqual(wire.call_count,0)
 def test_changed_selected_target_refuses_before_source_credentials(self):
  from automation.seedbox_host_io import acquire
  bundle,old=bundle_for(self,NOW+700);prep=self.selected['reservation']
  with patch('time.time',return_value=NOW+700):proof=delivery.proposal(self.q,prep)
  with self.q.locked() as (rows,_):claim=next(r for r in rows if r['type']=='seedbox_preparation_claimed_v1' and digest(r)==prep)
  target=copy.deepcopy(old['target_pin']);target['ref']['message_id']+=1
  binding=dict(url=decode(old['local_raw'])['tracker_url'],actor_version=target['version'],target=target,release_name='Invented release')
  with patch('time.time',return_value=NOW+700),patch('automation.seedbox_host_io.database',return_value=nullcontext(None)),patch('automation.seedbox_source_evidence.actor_listing',return_value=binding),patch('automation.seedbox_host_io._configuration',side_effect=AssertionError('must not read source credentials')):
   with self.assertRaisesRegex(Refusal,'delivery_selected_target_changed'):acquire(dict(actor_database={},sources={},listing_source='fixture'),claim,bundle['snapshot'],{},revalidation=proof)
 def test_complete_long_uncertainty_no_fallback_and_caption_bound(self):
  with patch('time.time',return_value=NOW):report,e,oldcard=review.assessment(self.q,self.selected['reservation'])
  report=copy.deepcopy(report)
  report['result']['rationale']='The cast and independently linked identifiers support the film proposal despite the producer title discrepancy, which is preserved here as a collector claim and not silently treated as a corrected original identification.'
  report['result']['uncertainty']='The reported year differs from the catalogue theatrical year and the duration is shorter than the catalogue runtime, so the retained observations cannot establish whether this is a festival cut, a shortened edition or a catalogue measurement difference.'
  new=review.proposal(report,e['projection'],e['local_raw'],e['target_pin'],oldcard['html_sha256'],revision=2)
  self.assertEqual(new['summary']['evidence'],report['result']['rationale']);self.assertEqual(new['summary']['uncertainty'],report['result']['uncertainty'])
  old=review.proposal(report,e['projection'],e['local_raw'],e['target_pin'],oldcard['html_sha256'])
  self.assertEqual(old['summary']['uncertainty'],'Physical edition remains unverified.')
  target=copy.deepcopy(e['target_pin']);target['ref']['kind']='caption'
  report['result']['rationale']='Complete retained explanation. '*35
  with self.assertRaisesRegex(Refusal,'review_card_size'):review.proposal(report,e['projection'],e['local_raw'],target,oldcard['html_sha256'],revision=2)
  new=review.proposal(report,e['projection'],e['local_raw'],e['target_pin'],oldcard['html_sha256'],revision=2);self.assertGreater(len(new['text'].encode('utf-16-le'))//2,1024)
 def test_every_blocker_detail_retained_and_oversize_refuses(self):
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,self.selected['reservation'])
  report=copy.deepcopy(report);report['result'].update(candidate=None,status='unresolved',film_blockers=[dict(aspect='year',reason='conflicting_film_evidence',support_considered='Cast agrees with the proposed identity.',material_conflict='The dated year evidence remains contradictory.')])
  new=review.proposal(report,e['projection'],e['local_raw'],e['target_pin'],card['html_sha256'],revision=2)
  for value in report['result']['film_blockers'][0].values():self.assertIn(value.replace('_',' '),new['text'])
  report['result']['rationale']='X'*4096
  with self.assertRaisesRegex(Refusal,'review_card_size'):review.proposal(report,e['projection'],e['local_raw'],e['target_pin'],card['html_sha256'],revision=2)


def load_tests(loader,tests,pattern):return unittest.TestSuite(DeliveryTests(n) for n in DeliveryTests.__dict__ if n.startswith('test_'))
