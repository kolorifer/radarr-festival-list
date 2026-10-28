"""Synthetic loopback/store fixtures only; no production integrations."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import contextmanager
import http.client
import io
import json
import os
import queue
import sqlite3
import threading
import time
import unittest
from unittest.mock import Mock, patch

import identity_triage_observer as observer
import identity_triage_service as service
from identity_outcome_outbox import Outbox
import test_identity_triage as fixtures

CANARY = 'PRIVATE https://tracker.invalid/download?passkey=secret token header release body'


class ObserverDeliveryTests(fixtures.Base):
    def setUp(self):
        super().setUp()
        self.cfg={'version':1,'enabled':True,'port':40715,'sources':fixtures.SOURCES,
                  'release_key':'r'*43,'outcome_key':'o'*43}
        self.config=self.root/'server.json'
        self.config.write_text(json.dumps(self.cfg));self.config.chmod(0o600)
        self.server=service.Server(('127.0.0.1',0),self.config,self.store)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start();self.addCleanup(fixtures.HTTPTests.close,self)
        config=self.root/'observer.json'
        config.write_text(json.dumps({'port':self.server.server_address[1],
                                     'key':self.cfg['outcome_key'],'sources':fixtures.SOURCES}))
        config.chmod(0o600)
        self.enterContext(patch.dict(os.environ,{'MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED':'1',
                                                'MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG':str(config)}))
        self.enterContext(patch.object(observer,'_STATS',Counter()))
        self.box=Outbox(self.root/'outbox')
        self.item=observer.envelope(fixtures.payload(),{},fixtures.SOURCES)
        self.box.put(self.item)
        self.pending=self.box.next()

    def test_waits_for_collector_writer_past_old_half_second_timeout(self):
        attempting,finished=threading.Event(),threading.Event()
        original=self.store.connection
        @contextmanager
        def connection(*args,**kwargs):
            attempting.set()
            try:
                with original(*args,**kwargs) as c:yield c
            finally:finished.set()
        with ThreadPoolExecutor(max_workers=1) as pool:
            try:
                with self.store.connection() as c:
                    c.execute('BEGIN IMMEDIATE')
                    with patch.object(self.store,'connection',connection):
                        attempt=pool.submit(observer._deliver_pending,self.box,self.pending)
                        self.assertTrue(attempting.wait(3))
                        # Old 0.5 s sender finishes as a failed delivery here;
                        # the fixed sender still awaits the collector's result.
                        with self.assertRaises(FutureTimeout):attempt.result(timeout=0.8)
                attempt.result(timeout=4)
            finally:
                self.assertTrue(finished.wait(4))
        self.assertEqual(self.box.metrics(),{'persisted':1,'delivered':1,'pending':0})
        self.assertEqual(self.store.metrics()['counters']['outcome'],{'accepted':1})
        self.assertEqual(self.server.storage_failures,0)

    def test_full_writer_wait_returns_http_503_then_retry_keeps_same_event(self):
        output=io.StringIO()
        with self.store.connection() as c, patch('sys.stdout',output):
            c.execute('BEGIN IMMEDIATE')
            observer._deliver_pending(self.box,self.pending)
        self.assertIn('delivery_failed stage=send reason=http_status http_status=503',output.getvalue())
        self.assertEqual(self.server.storage_failures,1)
        self.assertEqual(self.store.metrics()['observed_movie_deliveries'],0)
        retry=self.box.next(now=time.time()+10)
        self.assertEqual(retry,(self.pending[0],self.item,1))
        observer._deliver_pending(self.box,retry)
        self.assertEqual(self.box.metrics(),{'persisted':1,'delivery_failures':1,'delivered':1,'pending':0})
        self.assertEqual(self.store.metrics()['counters']['outcome'],{'accepted':1})

    def test_lost_response_and_timeout_retain_event_then_deduplicate(self):
        for mode in ('disconnect','timeout'):
            with self.subTest(mode=mode):
                item=observer.envelope(fixtures.payload(),{},fixtures.SOURCES)
                self.box.put(item)
                # Remove the unused setup fixture from this local test outbox.
                self.box.ack(self.pending[0])
                pending=self.box.next()
                release,finished=threading.Event(),threading.Event()
                def lost_reply(handler,status,metrics=None):
                    if mode=='timeout':release.wait(3)
                    handler.close_connection=True
                    finished.set()
                output=io.StringIO()
                try:
                    with patch.object(service.Handler,'reply',lost_reply), patch.object(observer,'DELIVERY_TIMEOUT',0.05), patch('sys.stdout',output):
                        observer._deliver_pending(self.box,pending)
                finally:
                    release.set();self.assertTrue(finished.wait(3))
                reason='timeout' if mode=='timeout' else 'connection_lost'
                self.assertIn('delivery_failed stage=send reason='+reason,output.getvalue())
                retry=self.box.next(now=time.time()+10)
                self.assertEqual(retry,(pending[0],item,1))
                observer._deliver_pending(self.box,retry)
                self.assertEqual(self.box.metrics()['pending'],0)
        counts=self.store.metrics()['counters']['outcome']
        self.assertEqual(counts,{'accepted':2,'duplicate_event':2,'duplicate_evidence':1})

    def test_ack_failure_is_distinct_from_transport_and_preserves_retry(self):
        error=sqlite3.OperationalError(CANARY);error.sqlite_errorcode=sqlite3.SQLITE_BUSY
        output=io.StringIO()
        with patch.object(self.box,'ack',side_effect=error),patch('sys.stdout',output):
            observer._deliver_pending(self.box,self.pending)
        self.assertIn('delivery_failed stage=ack reason=sqlite_busy http_status=200',output.getvalue())
        self.assertNotIn(CANARY,output.getvalue())
        retry=self.box.next(now=time.time()+10)
        self.assertEqual(retry,(self.pending[0],self.item,1))
        observer._deliver_pending(self.box,retry)
        self.assertEqual(self.box.metrics()['pending'],0)
        self.assertEqual(self.store.metrics()['counters']['outcome'],{'accepted':1,'duplicate_event':1})

    def test_configuration_failure_does_not_send_or_ack(self):
        output=io.StringIO()
        with patch.object(observer,'read_config',side_effect=ValueError(CANARY)),patch.object(observer,'_send') as send,patch('sys.stdout',output):
            observer._deliver_pending(self.box,self.pending)
        send.assert_not_called()
        self.assertIn('delivery_failed stage=configuration reason=validation http_status=none',output.getvalue())
        self.assertNotIn(CANARY,output.getvalue())
        self.assertEqual(self.box.next(now=time.time()+10),(self.pending[0],self.item,1))

    def test_http_failure_logs_status_without_reason_headers_or_body(self):
        def private_response(handler,status,metrics=None):
            body=CANARY.encode()
            handler.send_response(503,CANARY)
            handler.send_header('X-Private',CANARY)
            handler.send_header('Content-Length',str(len(body)))
            handler.end_headers();handler.wfile.write(body)
            handler.close_connection=True
        output=io.StringIO()
        with patch.object(service.Handler,'reply',private_response),patch('sys.stdout',output):
            observer._deliver_pending(self.box,self.pending)
        self.assertRegex(output.getvalue(),r'^triage_observer delivery_failed stage=send reason=http_status http_status=503 elapsed_ms=\d+\n$')
        self.assertNotIn(CANARY,output.getvalue())
        self.assertEqual(self.box.next(now=time.time()+10),(self.pending[0],self.item,1))

    def test_retry_bookkeeping_failure_does_not_hide_original_error(self):
        class StopLoop(BaseException):pass
        error=sqlite3.OperationalError(CANARY);error.sqlite_errorcode=sqlite3.SQLITE_FULL
        output=io.StringIO()
        with patch.object(observer,'Outbox',return_value=self.box),patch.object(observer._QUEUE,'get',side_effect=queue.Empty),patch.object(observer,'_send',side_effect=TimeoutError(CANARY)),patch.object(self.box,'failed',side_effect=error),patch.object(observer.time,'sleep',side_effect=StopLoop),patch('sys.stdout',output):
            with self.assertRaises(StopLoop):observer._run()
        self.assertIn('delivery_failed stage=send reason=timeout http_status=none',output.getvalue())
        self.assertIn('prepersist_failed stage=retry_state reason=sqlite_full http_status=none',output.getvalue())
        self.assertNotIn(CANARY,output.getvalue())
        self.assertEqual(self.box.next(),self.pending)


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(observer,'_STATS',Counter()))

    def test_fixed_categories_and_redaction(self):
        class HostileError(Exception):
            def __str__(self):raise AssertionError('must not stringify exception')
        cases=[(TimeoutError(CANARY),'timeout'),(ConnectionRefusedError(CANARY),'connection_refused'),
               (ConnectionResetError(CANARY),'connection_lost'),(BrokenPipeError(CANARY),'connection_lost'),
               (http.client.RemoteDisconnected(CANARY),'connection_lost'),
               (http.client.BadStatusLine(CANARY),'http_protocol'),(http.client.IncompleteRead(CANARY.encode()),'http_protocol'),
               (PermissionError(CANARY),'permission'),(FileNotFoundError(CANARY),'path_missing'),
               (OSError(CANARY),'os_other'),(ValueError(CANARY),'validation'),
               (HostileError(CANARY),'unexpected'),(queue.Full(CANARY),'queue_full'),
               (observer.CollectorHTTPError(503),'http_status')]
        for code,reason in ((sqlite3.SQLITE_BUSY | 512,'sqlite_busy'),(sqlite3.SQLITE_LOCKED,'sqlite_locked'),
                            (sqlite3.SQLITE_FULL,'sqlite_full'),(sqlite3.SQLITE_IOERR,'sqlite_io'),
                            (sqlite3.SQLITE_READONLY,'sqlite_readonly'),(sqlite3.SQLITE_ERROR,'sqlite_other')):
            error=sqlite3.OperationalError(CANARY);error.sqlite_errorcode=code;cases.append((error,reason))
        for error,reason in cases:
            with self.subTest(reason=reason),patch.object(observer,'_STATS',Counter()),patch.object(observer.time,'monotonic',return_value=10):
                output=io.StringIO()
                with patch('sys.stdout',output):observer.count('delivery_failed',error=error,stage='send',started=9)
                status='503' if isinstance(error,observer.CollectorHTTPError) else 'none'
                self.assertEqual(output.getvalue(),f'triage_observer delivery_failed stage=send reason={reason} http_status={status} elapsed_ms=1000\n')
                self.assertEqual(observer.metrics()['delivery_failed'],1)

    def test_diagnostic_metadata_is_allowlisted_and_timing_bounded(self):
        output=io.StringIO()
        with patch('sys.stdout',output),patch.object(observer.time,'monotonic',return_value=100):
            observer.count('delivery_failed',error=observer.CollectorHTTPError(CANARY),stage=CANARY,started=-100,http_status=CANARY)
        self.assertEqual(output.getvalue(),'triage_observer delivery_failed stage=unknown reason=http_status http_status=none elapsed_ms=60000\n')

    def test_observe_still_queues_without_waiting_for_network(self):
        work=queue.Queue(maxsize=1)
        with patch.dict(os.environ,{'MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED':'1','MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG':'unused'}),patch.object(observer,'read_config',return_value={'sources':fixtures.SOURCES}),patch.object(observer,'_WORKER',Mock()),patch.object(observer,'_QUEUE',work),patch.object(observer,'_send') as send,patch('sys.stdout',new_callable=io.StringIO) as output:
            observer.observe(fixtures.payload(),{})
            self.assertEqual(work.qsize(),1)
            observer.observe(fixtures.payload(),{})
            self.assertIn('queue_full stage=enqueue reason=queue_full',output.getvalue())
            send.assert_not_called()


if __name__=='__main__':unittest.main()
