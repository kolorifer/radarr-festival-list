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
 def test_rate_limit_pauses_other_source_cases(self):
  q,config=self.prepare_worker()
  with patch('automation.seedbox_worker.database',side_effect=lambda _:self.store.connection(readonly=True)),patch('automation.seedbox_evidence.capture',side_effect=SourceFailure('source_rate_limited',retry_after=7200)) as fetch:
   self.assertTrue(step(q,config));self.assertFalse(step(q,config));self.assertFalse(step(q,config));self.assertEqual(fetch.call_count,1)
  with q.locked() as (rows,_):self.assertTrue(any(r['type']=='seedbox_source_cooldown_v1' and r['not_before']>time.time()+7100 for r in rows))


def load_tests(loader,tests,pattern):
 import unittest
 return unittest.TestSuite(WorkerTests(name) for name in WorkerTests.__dict__ if name.startswith('test_'))
