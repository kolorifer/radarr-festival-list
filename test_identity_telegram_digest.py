from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from identity_telegram_digest import Digest, projection, read_report, start, FLAG


class DigestTests(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve();self.now=time.time()
        self.d=Digest(self.root/'digest');self.send=Mock(return_value=200)
        self.report={'version':1,'generated_at':self.now,'cases':[{
            'case_id':'outcome-'+'a'*64,'version':'b'*64,'title':'Aberfan: The Village That Fought Back',
            'year':2026,'route':'eligible','reason':'listing_id_missing','observed_at':self.now,
            'research_status':'awaiting_evidence','proposal':{'current_evidence':True,
            'search_candidates':[{'record':{'id':1796471,'type':'movie'}}]}}]}
    def rows(self):return projection(self.report,self.now)
    def test_changed_case_only_restart_and_fresh_timestamp(self):
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now),1)
        self.d=Digest(self.d.directory)
        self.report['generated_at']+=1;self.report['cases'][0]['observed_at']+=1
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now),0)
        self.report['cases'][0]['version']='c'*64
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now),1)
        self.assertEqual(self.send.call_count,2)
    def test_complete_report_not_latest_delta_is_consumed(self):
        self.report['changed_cases']=[]
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now),1)
        self.assertIn('movie 1796471',self.send.call_args.args[0])
        self.assertIn('unverified',self.send.call_args.args[0])
    def test_noise_excluded_and_recovery_only_after_review(self):
        row=self.report['cases'][0]
        for route in ('verified','routine','unassessed','existing_seed'):
            row['route']=route;self.assertEqual(self.d.tick(self.rows(),self.send,self.now),0)
        row['route']='quarantine';self.d.tick(self.rows(),self.send,self.now)
        row['route']='verified';self.assertEqual(self.d.tick(self.rows(),self.send,self.now),1)
    def test_proposal_change_notifies_and_stale_candidate_not_forwarded(self):
        self.d.tick(self.rows(),self.send,self.now)
        self.report['cases'][0]['proposal']['current_evidence']=False
        self.d.tick(self.rows(),self.send,self.now)
        text=self.send.call_args.args[0];self.assertIn('stale',text);self.assertNotIn('1796471',text)
    def test_safe_allowlist_and_no_action_controls(self):
        row=self.report['cases'][0];row['title']='Title https://private.invalid/passkey SECRET'
        row['source_identity']={'token':'PRIVATE'};row['proposal']['result']={'evidence':'PRIVATE'}
        with patch.dict(os.environ,{'RADARR_API_KEY':'SECRET'}):
            self.d.tick(self.rows(),self.send,self.now)
        text=self.send.call_args.args[0]
        for value in ('SECRET','PRIVATE','https://','passkey'):self.assertNotIn(value,text)
        self.assertIn('No correction or download performed',text)
    def test_ambiguous_failure_is_durable_and_not_retried(self):
        self.send.side_effect=TimeoutError('private detail')
        self.d.tick(self.rows(),self.send,self.now)
        self.assertEqual(Digest(self.d.directory).tick(self.rows(),self.send,self.now+10000),0)
        self.assertEqual(self.d.summary(),{'uncertain':1})
    def test_crash_after_reservation_does_not_duplicate(self):
        self.send.side_effect=KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):self.d.tick(self.rows(),self.send,self.now)
        self.assertEqual(Digest(self.d.directory).tick(self.rows(),self.send,self.now),0)
    def test_explicit_rate_limit_retries_after_delay(self):
        self.send.side_effect=HTTPError('hidden',429,'limited',{},io.BytesIO(b'{"parameters":{"retry_after":7200}}'))
        self.d.tick(self.rows(),self.send,self.now)
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now+3601),0)
        self.send.side_effect=None
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now+7201),1)
        self.assertEqual(self.d.summary(),{'sent':1})
    def test_concurrent_reservation_only_sends_once(self):
        with ThreadPoolExecutor(2) as pool:
            counts=list(pool.map(lambda _:self.d.tick(self.rows(),self.send,self.now),range(2)))
        self.assertEqual(sum(counts),1);self.send.assert_called_once()
    def test_storage_failure_prevents_send(self):
        with self.d.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):self.d.tick(self.rows(),self.send,self.now)
        self.send.assert_not_called()
    def test_chunk_bound_and_remaining_cases_not_lost(self):
        self.report['cases']=[dict(self.report['cases'][0],case_id='outcome-'+str(i)*64) for i in range(9)]
        for count in (4,4,1,0):self.assertEqual(self.d.tick(self.rows(),self.send,self.now),count)
        for call in self.send.call_args_list:self.assertLess(len(call.args[0].encode('utf-16-le'))//2,3800)
    def test_report_validation_private_mode_size_staleness(self):
        p=self.root/'report.json';p.write_text(json.dumps(self.report))
        self.assertEqual(read_report(p,self.now),self.rows())
        p.chmod(0o644)
        with self.assertRaises(ValueError):read_report(p,self.now)
        p.chmod(0o600)
        with self.assertRaises(ValueError):read_report(p,self.now+172801)
        link=self.root/'link';link.symlink_to(p)
        with self.assertRaises(ValueError):read_report(link,self.now)
        self.report['cases'].append(deepcopy(self.report['cases'][0]))
        with self.assertRaises(ValueError):self.rows()
    def test_plain_language_retry_and_review_explanations(self):
        row=self.report['cases'][0];row.update(route='retry_later',reason='metadata_api_unavailable',research_status='not_admitted',proposal={})
        text=self.rows()[0][3]
        self.assertIn('Temporary metadata lookup problem',text)
        self.assertIn('daily allowance',text)
        for code in ('retry_later','not admitted','metadata api unavailable'):self.assertNotIn(code,text)
        row.update(route='review_only',reason='title_conflict')
        self.assertIn('release title disagrees',self.rows()[0][3])

    def test_wording_change_preserves_existing_delivery_key(self):
        import hashlib
        row=self.report['cases'][0]
        legacy=(row['title']+' (2026)\nStatus: eligible; listing id missing. Research: awaiting evidence.'
                '\nPossible TMDb matches (unverified): movie 1796471.'
                '\nDetails, media type and source crosswalk require review.')
        key=hashlib.sha256(json.dumps({'version':row['version'],'text':legacy,'proposal':row['proposal']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.d.connect() as c:c.execute('insert into delivery values(?,?,?,?)',(row['case_id'],key,'sent',self.now))
        self.assertEqual(self.rows()[0][1],key)
        self.assertEqual(self.d.tick(self.rows(),self.send,self.now),0)
        self.send.assert_not_called()

    def test_disabled_start_has_no_thread_or_state(self):
        with patch.dict(os.environ,{FLAG:'0'}), patch('threading.Thread') as thread:
            self.assertIsNone(start(self.send));thread.assert_not_called()
    def test_transport_is_plain_text_without_keyboard(self):
        from movie_intel_service import _telegram_payload
        body=_telegram_payload('review',parse_mode=None)
        self.assertNotIn('reply_markup',body);self.assertNotIn('parse_mode',body)
