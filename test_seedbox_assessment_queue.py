"""Invented collector events; no credentials, provider, review or notification."""
import copy,errno,os,sys,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from automation.seedbox_assessment_queue import Queue,collector_page
from identity_triage_store import Store
from ai_movie_investigator.contracts import encoded
import identity_selection
from identity_triage_intake import normalize
from test_identity_triage import payload,SOURCES

class QueueTests(unittest.TestCase):
 def setUp(self):
  old=os.umask(0o077);self.addCleanup(os.umask,old)
  if sys.platform.startswith('linux'):
   acl=patch('os.getxattr',side_effect=OSError(errno.ENODATA,'fixture absent ACL'));acl.start();self.addCleanup(acl.stop)
  self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name).resolve();self.store=Store(self.root/'collector');self.state=self.root/'queue';self.state.mkdir(mode=0o700)
 def event(self,n):
  p=payload(external_id=str(n));self.store.ingest(normalize(p,SOURCES,'release_new'),'release_new')
  p=copy.deepcopy(p);p.update(event='identity.outcome',id=str(uuid.uuid4()));p['data']['outcome']=dict(reason='title_conflict',status='needs_review',category='unknown_movie')
  self.store.ingest(normalize(p,SOURCES,'outcome'),'outcome')
 def page(self,after=0):
  with self.store.connection(readonly=True) as c:return collector_page(c,after)
 def snapshot(self):
  with self.store.connection(readonly=True) as c:return encoded(identity_selection.snapshot(c,time.time()))
 def queue(self,consumed=(),capacity=1000):
  from test_seedbox_credit_policy import CreditPolicyTests
  Queue.enroll(self.state,delegated_policy=CreditPolicyTests().policy(),collector_identity='a'*64,prior_consumed_cases=consumed,prior_history_sha256='b'*64,prior_credit_sha256='c'*64,capacity=capacity)
  return Queue(self.state)
 def test_real_collector_history_to_durable_queue_two_cases_same_hour(self):
  self.event(1);self.event(2);q=self.queue();p=self.page();self.assertEqual(q.ingest(p,collector_identity='a'*64),'accepted')
  a=q.reserve(self.snapshot(),now=time.time());q=Queue(self.state);b=q.reserve(self.snapshot(),now=time.time())
  self.assertNotEqual(a['event']['case_id'],b['event']['case_id']);self.assertEqual(q.reserve(self.snapshot(),now=time.time())['status'],'quiet')
  self.assertEqual(q.ingest(p,collector_identity='a'*64),'duplicate_page')
 def test_imported_unknown_case_never_reopened(self):
  self.event(1);p=self.page();q=self.queue([p['events'][0]['case_id']]);q.ingest(p,collector_identity='a'*64)
  self.assertEqual(q.reserve(self.snapshot(),now=time.time())['status'],'quiet')
 def test_backpressure_never_advances_cursor(self):
  self.event(1);self.event(2);q=self.queue(capacity=1)
  with self.assertRaisesRegex(ValueError,'queue_backpressure'):q.ingest(self.page(),collector_identity='a'*64)
  with q.locked() as (rows,_):self.assertEqual(len(rows),1)
 def test_changed_collector_and_reset_refuse(self):
  self.event(1);q=self.queue()
  with self.assertRaisesRegex(ValueError,'queue_collector_changed'):q.ingest(self.page(),collector_identity='d'*64)
  with self.assertRaisesRegex(ValueError,'queue_enrollment_not_empty'):self.queue()

 def test_valid_prefix_rollback_preserves_uncertain_reservation(self):
  from ai_movie_investigator.history import FILENAME
  self.event(1);q=self.queue();q.ingest(self.page(),collector_identity='a'*64)
  before=(self.state/FILENAME).read_bytes();q.reserve(self.snapshot(),now=time.time())
  (self.state/FILENAME).write_bytes(before)
  with self.assertRaisesRegex(ValueError,'queue_journal_uncertain'):Queue(self.state).reserve(self.snapshot(),now=time.time())
 def test_outcome_first_waits_for_late_source_correlation(self):
  p=payload(external_id='late');e=copy.deepcopy(p);e.update(event='identity.outcome',id=str(uuid.uuid4()));e['data']['outcome']=dict(reason='title_conflict',status='needs_review',category='unknown_movie')
  self.store.ingest(normalize(e,SOURCES,'outcome'),'outcome');q=self.queue();q.ingest(self.page(),collector_identity='a'*64)
  self.assertEqual(q.reserve(self.snapshot(),now=time.time())['status'],'waiting_for_eligible_source')
  self.store.ingest(normalize(p,SOURCES,'release_new'),'release_new')
  self.assertEqual(q.reserve(self.snapshot(),now=time.time())['status'],'needs_authenticated_evidence')

 def test_preparation_resumes_but_provider_unknown_never_replays(self):
  from test_seedbox_credit_policy import CreditPolicyTests
  self.event(1);q=self.queue();q.ingest(self.page(),collector_identity='a'*64);selected=q.reserve(self.snapshot(),now=time.time())
  self.assertEqual(len(Queue(self.state).pending_preparations()),1)
  p=CreditPolicyTests().policy();q.reserve_provider(selected['reservation'],policy=p,request_sha256='d'*64,evidence_sha256='e'*64,now=1200)
  self.assertEqual(Queue(self.state).pending_preparations(),[])
  with self.assertRaisesRegex(ValueError,'queue_provider_consumed'):q.reserve_provider(selected['reservation'],policy=p,request_sha256='d'*64,evidence_sha256='e'*64,now=1200)
 def test_successful_stream_does_not_starve_conflict(self):
  for n in range(5):
   p=payload(external_id='success'+str(n));self.store.ingest(normalize(p,SOURCES,'release_new'),'release_new')
   p=copy.deepcopy(p);p.update(event='identity.outcome',id=str(uuid.uuid4()));p['data']['outcome']=dict(reason='external_id_verified',status='verified_tmdb',category='verified')
   self.store.ingest(normalize(p,SOURCES,'outcome'),'outcome')
  self.event(99);q=self.queue(capacity=1);q.ingest(self.page(),collector_identity='a'*64)
  self.assertEqual(q.reserve(self.snapshot(),now=time.time())['status'],'needs_authenticated_evidence')

 def test_source_block_retained_without_credit_or_silent_refetch(self):
  from test_seedbox_credit_policy import CreditPolicyTests
  self.event(1);q=self.queue();q.ingest(self.page(),collector_identity='a'*64)
  claim=q.reserve(self.snapshot(),now=time.time())
  result=q.record_source_failure(claim['reservation'],reason='source_auth_denied',retry_after=None,now=time.time())
  self.assertTrue(result['owner_action']);self.assertFalse(result['provider_request_consumed'])
  self.assertEqual(Queue(self.state).pending_preparations(),[])
  with self.assertRaisesRegex(ValueError,'queue_source_blocked'):
   q.reserve_provider(claim['reservation'],policy=CreditPolicyTests().policy(),request_sha256='d'*64,evidence_sha256='e'*64,now=1200)
  with q.locked() as (rows,_):self.assertFalse(any(r['type']=='seedbox_provider_started_v1' for r in rows))
