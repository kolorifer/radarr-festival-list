"""Connected durable global-denial and per-case gap fixtures; no external I/O."""
from unittest.mock import patch
import test_seedbox_assessment_queue as base
from automation.seedbox_worker import step
from automation.seedbox_host_io import SourceFailure
from automation.seedbox_circuit import active
import time

class WorkerTests(base.QueueTests):
 def prepare_worker(self):
  self.event(1);self.event(2);q=self.queue();q.ingest(self.page(),collector_identity='a'*64);q.reserve(self.snapshot(),now=time.time())
  return q,dict(collector_database={},collector_identity='a'*64,source_attempt_limit=2)
 def test_shared_auth_denial_stops_other_case_calls(self):
  q,config=self.prepare_worker()
  with patch('automation.seedbox_worker.database',side_effect=lambda _:self.store.connection(readonly=True)) as db,patch('automation.seedbox_evidence.capture',side_effect=SourceFailure('source_auth_denied')) as fetch:
   self.assertTrue(step(q,config));calls=db.call_count
   self.assertFalse(step(q,config));self.assertFalse(step(q,config))
   self.assertEqual(fetch.call_count,1);self.assertEqual(db.call_count,calls)
  with q.locked() as (rows,_):self.assertEqual(len(active(rows)),1)
 def test_missing_listing_does_not_stop_unrelated_case(self):
  q,config=self.prepare_worker()
  with patch('automation.seedbox_worker.database',side_effect=lambda _:self.store.connection(readonly=True)),patch('automation.seedbox_evidence.capture',side_effect=SourceFailure('source_missing')) as fetch:
   self.assertTrue(step(q,config));self.assertTrue(step(q,config));self.assertTrue(step(q,config))
   self.assertEqual(fetch.call_count,2)
  with q.locked() as (rows,_):self.assertFalse(active(rows))
