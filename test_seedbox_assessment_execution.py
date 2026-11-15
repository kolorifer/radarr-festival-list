"""Real v13 builder/parser/validator/report with explicitly invented socket I/O.

No live provider, credential, independently reviewed movie or notification.
"""
import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from automation.seedbox_assessment_queue import Queue
from ai_movie_investigator import seedbox_authorization as host,snapshot_review as review
from ai_movie_investigator.contracts import encoded,digest
from ai_movie_investigator.responses_http import ExplicitCredential
from ai_movie_investigator.credit_test import MINI_MODEL
from test_reviewed_telegram_operator import fixture_acl
import test_seedbox_credit_policy as credit_fixture
from test_snapshot_review import fixture,NOW,CASE
import test_snapshot_assessment as assessment_fixture
from test_responses_compatibility import documented
import test_supervised_envelope as framing

class HostExecutionTests(unittest.TestCase):
 def setUp(self):
  fixture_acl(self);old=os.umask(0o077);self.addCleanup(os.umask,old)
  self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name).resolve()
  self.policy=credit_fixture.CreditPolicyTests().policy();self.policy.update(observed_at=NOW-100,delegated_at=NOW-50,expires_at=NOW+900,credit_expires_at=NOW+1000)
  Queue.enroll(self.path,collector_identity='a'*64,prior_consumed_cases=[],prior_history_sha256='b'*64,prior_credit_sha256='c'*64,delegated_policy=self.policy)
  self.q=Queue(self.path);snap,_,_,_=fixture()
  event=dict(cursor=1,event_id='f'*64,case_id=CASE,observed_at=NOW-20,received_at=NOW-19,outcome=dict(reason='title_conflict',status='needs_review',category='unknown_movie'),metadata={})
  self.q.ingest(dict(kind='collector_assessment_events_v1',after=0,through=1,high_water=1,events=[event]),collector_identity='a'*64)
  self.selected=self.q.reserve(snap,now=NOW)
  self.f=assessment_fixture.AssessmentTests();self.f.setUp();self.p=self.f.p;self.p.update(evidence_expires_at=NOW+600,generated_at=NOW-5)
  for key in ('listing','catalogue'):self.p[key]['expires_at']=NOW+600
  self.local=encoded(dict(tracker_url='https://example.invalid/listing/1',release_name='Invented release',nfo_text='Invented NFO'))
 def wire(self):
  built=review.build_film_prose(self.p);response=documented();response.update(model=MINI_MODEL,instructions=built['request']['instructions'],text=built['request']['text'],max_output_tokens=25000)
  response['output'][-1]['content'][0]['text']=encoded(self.f.answer_for(self.p)).decode()
  return encoded(response)
 def execute(self):
  with patch('automation.seedbox_evidence.load',return_value=dict(projection=self.p,local_raw=self.local,evidence_sha256='e'*64)),patch('automation.seedbox_evidence.verify_current'),patch('automation.seedbox_evidence.persist_report'):
   return host.execute(self.q,self.selected['reservation'],policy=self.policy,credential=ExplicitCredential('sk-SYNTHETIC_FIXTURE'))
 def test_connected_v13_receipt_private_report_and_no_replay(self):
  with patch.object(host.time,'time',return_value=NOW),framing.wire(self.wire()):out=self.execute()
  self.assertEqual(out['report']['assessment_label'],'complete_film_explanation_v13');self.assertIn('Invented release',out['html']);self.assertFalse(out['report']['identity_approval'])
  with patch.object(host.time,'time',return_value=NOW),self.assertRaisesRegex(ValueError,'queue_provider_consumed'):self.execute()
 def test_uncertain_wire_keeps_debit_and_does_not_reopen(self):
  with patch.object(host.time,'time',return_value=NOW),patch('socket.getaddrinfo',side_effect=OSError('invented outage')),self.assertRaisesRegex(ValueError,'host_assessment_uncertain'):self.execute()
  self.assertEqual(self.q.pending_preparations(),[])
  with self.q.locked() as (rows,_):self.assertEqual([r['reserved_usd'] for r in rows if r['type']=='seedbox_provider_started_v1'],[[3,20]])
