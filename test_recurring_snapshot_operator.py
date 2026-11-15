"""Invented intake cycles; no real sources, account or delivery."""
import copy,hashlib,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator.contracts import encoded,decode,digest,Refusal
from ai_movie_investigator.history import History
from automation.recurring_snapshot_operator import Operator,consumed_cases
from test_snapshot_review import fixture,NOW

class OperatorTests(unittest.TestCase):
 def setUp(self):
  from test_standing_credit import StandingTests
  standing=StandingTests('test_grant_preserves_legacy_hashes_and_default_cap');standing.setUp();self.addCleanup(standing.doCleanups);standing.grant()
  self.base=standing.state.parent;Operator.enroll(standing.state)
  self.now=NOW;self.op=Operator(self.base/'state',self.base/'state'/'recurring-intake-v1',clock=lambda:self.now)
  self.snap=decode(fixture()[0],1048576)
  # Two distinct stable release identities, conflict group ordered newest first.
  c=copy.deepcopy(self.snap['cases'][0]);i=copy.deepcopy(self.snap['items'][0]);c['case_id']=i['case_id']='outcome-'+'c'*64;c['first_observed_at']+=10
  self.snap['cases'].append(c);self.snap['items'].append(i);self.snap['coverage']['assessed_release_cases']=2
 def pin(self,name,raw):
  p=self.base/name;p.write_bytes(raw);p.chmod(0o600);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest())
 def select(self):
  self.snap['generated_at']=self.now-1
  return self.op.select(self.pin('snapshot.json',encoded(self.snap)),authenticated_reference='invented-authenticated-snapshot')
 def test_two_cycles_newest_conflict_first_and_restart_no_duplicate(self):
  a=self.select();self.assertEqual(a['selection']['case_id'],'outcome-'+'c'*64)
  self.assertEqual(self.select()['status'],'cycle_consumed')
  self.op=Operator(self.base/'state',self.base/'state'/'recurring-intake-v1',clock=lambda:self.now)
  self.now+=3600;b=self.select();self.assertNotEqual(a['selection']['case_id'],b['selection']['case_id'])
  self.now+=3600;self.assertEqual(self.select()['status'],'no_eligible_unassessed_case')
 def test_blocked_case_allows_other_later_without_retry(self):
  a=self.select();self.op.blocked(a['reservation'],'source_needed');self.now+=3600
  b=self.select();self.assertNotEqual(a['selection']['case_id'],b['selection']['case_id'])
  with self.assertRaises(Refusal):self.op.blocked(a['reservation'],'source_needed')
 def test_existing_consumed_including_incomplete_captured_start(self):
  case=self.snap['cases'][1]['case_id']
  with History(self.base/'state').transaction(write=True) as (_,append):append(dict(type='supervised_standing_attempt_started',captured={'authorization':{'case':{'case_id':case}}}))
  self.assertNotEqual(self.select()['selection']['case_id'],case)
  self.assertEqual(consumed_cases([{'type':'supervised_standing_attempt_started','historical':{'case':{'case_id':case,'version':'old'}}}]),{case})
 def test_stale_snapshot_and_wrong_pin_refuse_without_reservation(self):
  p=self.pin('stale.json',encoded(self.snap));self.now+=3601
  with self.assertRaises(ValueError):self.op.select(p,authenticated_reference='fixture')
  p['sha256']='f'*64
  with self.assertRaises(ValueError):self.op.select(p,authenticated_reference='fixture')
  self.assertFalse(any(x['type']=='operator_reserved_v1' for x in self.op.status()))
 def test_review_and_delivery_require_order_and_exact_pins(self):
  a=self.select();reservation=a['reservation'];html=self.pin('report.html',b'invented')
  with self.assertRaises(Refusal):self.op.delivered(reservation,review_sha256='a'*64,delivery_reference='chat:one',delivered_at=self.now)
  p=dict(type='operator_pending_review_v1',reservation=reservation,at=self.now,report_sha256='b'*64,html=html)
  with self.op.locked() as (_,__,append):append(p)
  self.op=Operator(self.base/'state',self.base/'state'/'recurring-intake-v1',clock=lambda:self.now)
  self.assertEqual(self.op.status()[-1],p)
  with self.assertRaises(Refusal):self.op.reviewed(reservation,report_sha256='c'*64,html_sha256=html['sha256'],review_reference='chat:review',observed_at=self.now)
  r=self.op.reviewed(reservation,report_sha256='b'*64,html_sha256=html['sha256'],review_reference='chat:review',observed_at=self.now)
  d=self.op.delivered(reservation,review_sha256=digest(r),delivery_reference='chat:actual-message',delivered_at=self.now)
  self.assertEqual(d['type'],'operator_delivered_v1')
  with self.assertRaises(Refusal):self.op.delivered(reservation,review_sha256=digest(r),delivery_reference='chat:actual-message',delivered_at=self.now)
 def test_root_binding_and_symlink_refused(self):
  self.select();other=self.base/'other';other.mkdir(mode=0o700)
  with self.assertRaises((Refusal,FileNotFoundError)):Operator(other,self.base/'state'/'recurring-intake-v1').status()
  link=self.base/'link';link.symlink_to(self.base/'state'/'recurring-intake-v1')
  with self.assertRaises(Refusal):Operator(self.base/'state',link)

 def test_alternate_journal_refused_and_second_instance_same_cycle(self):
  other=self.base/'alternate';other.mkdir(mode=0o700)
  with self.assertRaisesRegex(Refusal,'operator_canonical_journal'):Operator(self.base/'state',other)
  self.select();second=Operator(self.base/'state',self.base/'state'/'recurring-intake-v1',clock=lambda:self.now)
  self.assertEqual(second.select(self.pin('snapshot.json',encoded(self.snap)),authenticated_reference='fixture')['status'],'cycle_consumed')
 def test_clock_and_pin_rechecked_after_lock_wait(self):
  from contextlib import contextmanager
  p=self.pin('snapshot.json',encoded(self.snap));original=self.op.locked
  @contextmanager
  def delayed():
   self.now+=3601
   with original() as values:yield values
  with patch.object(self.op,'locked',delayed),self.assertRaisesRegex(ValueError,'snapshot_stale'):
   self.op.select(p,authenticated_reference='fixture')
  self.now=NOW
  @contextmanager
  def changed():
   Path(p['path']).write_bytes(b'changed')
   with original() as values:yield values
  with patch.object(self.op,'locked',changed),self.assertRaisesRegex(Refusal,'operator_pin_changed'):
   self.op.select(p,authenticated_reference='fixture')

 def test_missing_replaced_or_rolled_back_journal_stops(self):
  from ai_movie_investigator.history import FILENAME
  path=self.op.journal.directory/FILENAME;initial=path.read_bytes();self.select();current=path.read_bytes()
  path.write_bytes(initial)
  with self.assertRaisesRegex(Refusal,'operator_journal_uncertain'):self.select()
  path.write_bytes(current);path.unlink()
  with self.assertRaisesRegex(Refusal,'history_file_missing'):self.select()
  path.write_bytes(current);path.chmod(0o600)
  with self.assertRaisesRegex(Refusal,'history_file_identity_changed'):self.select()
 def test_enrollment_never_resets_and_highwater_mismatch_stops(self):
  with self.assertRaisesRegex(Refusal,'operator_already_enrolled'):Operator.enroll(self.base/'state')
  with self.op.journal.transaction(write=True) as (_,append):append(dict(type='invented_interrupted_append'))
  with self.assertRaisesRegex(Refusal,'operator_journal_uncertain'):self.select()

 def test_empty_unrelated_root_refused_without_new_files(self):
  from ai_movie_investigator.history import FILENAME
  empty=self.base/'empty';empty.mkdir(mode=0o700)
  with self.assertRaises(FileNotFoundError):Operator.enroll(empty)
  self.assertEqual(list(empty.iterdir()),[])
  with History(empty).transaction(write=True) as (_,append):append(dict(type='unrelated'))
  before=(empty/FILENAME).read_bytes()
  with self.assertRaisesRegex(Refusal,'operator_existing_enrollment_required'):Operator.enroll(empty)
  self.assertEqual(list(empty.iterdir()),[empty/FILENAME]);self.assertEqual((empty/FILENAME).read_bytes(),before)

class InstalledOperatorTests(unittest.TestCase):
 def test_first_v13_prepared_wrapper_receipt_report_review_delivery(self):
  from test_snapshot_prose_integration import ProseIntegrationTests
  f=ProseIntegrationTests('test_first_worst_unicode_wire_and_retention');f.setUp();self.addCleanup(f.doCleanups)
  Operator.enroll(f.f.state);journal=f.f.state/'recurring-intake-v1'
  op=Operator(f.f.state,journal)
  selected=op.select(f.f.record['snapshot'],authenticated_reference='invented-authenticated-source')
  self.assertEqual(selected['status'],'needs_main_verified_inputs');reservation=selected['reservation']
  def prepare(runtime,python,issued):
   template=f.f.pin('operator-template.py',Path('automation/snapshot_review_UNISSUED.py').read_bytes())
   output=f.f.root/'operator-wrapper';output.mkdir(mode=0o700)
   args=dict(authority=f.f.authority,account_evidence=issued['account_evidence'],runtime=runtime,
             python=python,template=template,output=output)
   event=op.prepare(reservation,**args)
   with self.assertRaisesRegex(Refusal,'operator_already_prepared'):op.prepare(reservation,**args)
   # Simulates explicit trusted main acceptance, not generated by the helper.
   p=Path(event['issued']['main_acceptance_path']);p.write_bytes(encoded(event['acceptance_proposal']));p.chmod(0o600)
   return Path(event['wrapper']['path'])
  f.prepare_operator=prepare;f.installed(True)
  html=f.f.output/'movie-review.html';raw=html.read_bytes();pin=dict(path=str(html),sha256=hashlib.sha256(raw).hexdigest())
  pending=op.pending_review(reservation,report=pin)
  self.assertEqual(pending['type'],'operator_pending_review_v1')
  op=Operator(f.f.state,journal)
  with self.assertRaises(Refusal):op.delivered(reservation,review_sha256=digest(pending),delivery_reference='fixture:not-delivered',delivered_at=time.time())
  reviewed=op.reviewed(reservation,report_sha256=pending['report_sha256'],html_sha256=pin['sha256'],review_reference='fixture:actual-full-review',observed_at=time.time())
  op.delivered(reservation,review_sha256=digest(reviewed),delivery_reference='fixture:actual-delivery',delivered_at=time.time())
  self.assertEqual(op.status()[-1]['type'],'operator_delivered_v1')
