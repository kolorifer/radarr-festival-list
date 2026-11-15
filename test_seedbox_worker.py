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
 def test_missing_original_stays_pre_http_source_block_without_replacement(self):
  q,config=self.prepare_worker()
  with patch('automation.seedbox_worker.database',side_effect=lambda _:self.store.connection(readonly=True)),patch('automation.seedbox_evidence.capture',side_effect=ValueError('telegram_original_missing')):
   self.assertTrue(step(q,config))
  with q.locked() as (rows,_):
   self.assertTrue(any(r['type']=='seedbox_source_blocked_v1' and r['reason']=='telegram_original_missing' for r in rows))
   self.assertFalse(any(r['type']=='seedbox_provider_started_v1' for r in rows));self.assertFalse(active(rows))
 def test_rate_limit_pauses_other_source_cases(self):
  q,config=self.prepare_worker()
  with patch('automation.seedbox_worker.database',side_effect=lambda _:self.store.connection(readonly=True)),patch('automation.seedbox_evidence.capture',side_effect=SourceFailure('source_rate_limited',retry_after=7200)) as fetch:
   self.assertTrue(step(q,config));self.assertFalse(step(q,config));self.assertFalse(step(q,config));self.assertEqual(fetch.call_count,1)
  with q.locked() as (rows,_):self.assertTrue(any(r['type']=='seedbox_source_blocked_v1' and r['reason']=='source_rate_limited' and r['retry_not_before']>time.time()+7100 for r in rows))


class CrashCircuitTests(base.QueueTests):
 def test_durable_source_denial_alone_pauses_all_new_work(self):
  self.event(1);q=self.queue();q.ingest(self.page(),collector_identity='a'*64);claim=q.reserve(self.snapshot(),now=time.time())
  q.record_source_failure(claim['reservation'],reason='source_auth_denied',retry_after=None,now=time.time())
  with patch('automation.seedbox_worker.database',side_effect=AssertionError('must not reacquire after restart')):
   self.assertFalse(step(base.Queue(self.state),{}))
 def test_durable_429_alone_preserves_cross_case_cooldown(self):
  from automation.seedbox_worker import source_paused
  self.event(1);q=self.queue();q.ingest(self.page(),collector_identity='a'*64);claim=q.reserve(self.snapshot(),now=time.time())
  q.record_source_failure(claim['reservation'],reason='source_rate_limited',retry_after=7200,now=time.time())
  with base.Queue(self.state).locked() as (rows,_):self.assertTrue(source_paused(rows,time.time()))


def load_tests(loader,tests,pattern):
 import unittest
 return unittest.TestSuite(cls(name) for cls in (WorkerTests,CrashCircuitTests) for name in cls.__dict__ if name.startswith('test_'))
