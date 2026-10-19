"""Automation safety: durable bounds, no action replay, strict confined handoff."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import time
import sqlite3
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from identity_retry import RetryStore, RetryBudget, run_one
from identity_recurring_store import RecurringStore
from identity_research_store import ResearchStore, Stop
from identity_triage_observer import envelope
from identity_triage_intake import normalize, Reject
from identity_triage_store import Store
from identity_research_handoff import validate_snapshot, atomic_json
from identity_investigation_report import write_report
import identity_selection as selection
from test_identity_triage import payload, SOURCES
from test_identity_research import case


def context(reason='metadata_api_unavailable',status='unresolved'):
    return {'meta':{'identity_reason':reason,'identity_status':status},'category':'unknown_movie',
            'identity_observation':{'reason':reason}}


class Base(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.now=time.time()


class RetryTests(Base):
    def setUp(self):
        super().setUp();self.s=RetryStore(self.root/'retry',clock=lambda:self.now)
        self.p=payload();self.item={'observation':envelope(self.p,context(),SOURCES)}
    def ready(self):
        self.s.admit(self.item,SOURCES);self.now+=901;return self.s.lease()
    def test_duplicate_restarts_and_three_extra_attempts(self):
        lease=self.ready();self.assertIsNotNone(lease)
        self.assertEqual(self.s.admit(self.item,SOURCES),'duplicate')
        self.s.finish(lease,'metadata_api_unavailable');self.now+=3601
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        lease=self.s.lease();self.assertEqual(lease['number'],2)
        self.s.finish(lease,'metadata_api_unavailable');self.now+=21601
        lease=self.s.lease();self.assertEqual(lease['number'],3)
        self.s.finish(lease,'metadata_api_unavailable');self.now+=21601
        self.assertIsNone(self.s.lease());self.assertEqual(self.s.summary()['states'],{'review':1})
    def test_crash_reservation_counts_and_stale_lease_cannot_publish(self):
        a=self.ready();self.now+=121;b=self.s.lease()
        self.assertEqual(b['number'],2)
        with self.assertRaises(RetryBudget):self.s.finish(a,'external_id_verified',self.item['observation'])
        self.assertEqual(self.s.metrics()['pending'],0)
    def test_provider_limits_auth_and_retry_after_persist(self):
        lease=self.ready()
        for _ in range(5):self.s.reserve_request(lease,'tmdb');self.now+=2
        with self.assertRaisesRegex(RetryBudget,'retry_request_budget'):self.s.reserve_request(lease,'tmdb')
        self.s.cooldown('listing',3600,False)
        with self.assertRaisesRegex(RetryBudget,'cooldown'):self.s.reserve_request(lease,'listing')
        self.s.cooldown('tmdb',0,True)
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        with self.assertRaisesRegex(RetryBudget,'auth'):self.s.reserve_request(lease,'tmdb')
        self.assertEqual(self.s.summary()['requests_rolling_week'],5)
    def test_future_material_invalidates_old_lease(self):
        lease=self.ready();p=deepcopy(self.p);p['data']['release']['year']=2024
        changed={'observation':envelope(p,context(),SOURCES)}
        self.s.admit(changed,SOURCES)
        with self.assertRaises(RetryBudget):self.s.finish(lease,'external_id_verified',self.item['observation'])
    def test_non_retryable_never_admitted_and_private_url_is_allowlisted(self):
        for reason in ('listing_auth_failure','listing_redirect','listing_not_found','listing_id_invalid','title_conflict'):
            self.assertEqual(self.s.admit({'observation':envelope(self.p,context(reason),SOURCES)},SOURCES),'not_retryable')
        for item in (dict(self.item,listing='https://evil.invalid'),dict(self.item,download_url='secret')):
            with self.assertRaises(ValueError):self.s.admit(item,SOURCES)
    def test_context_only_recovery_commits_outcome_and_completion_atomically(self):
        self.s.admit(self.item,SOURCES);self.now+=901
        with patch('movie_intel_service.send_telegram') as send, patch('movie_intel_service.create_pending_action') as action:
            self.assertTrue(run_one(self.s,lambda p:context('external_id_verified','verified_tmdb')))
        send.assert_not_called();action.assert_not_called()
        self.assertEqual(self.s.metrics()['pending'],1)
        self.assertEqual(self.s.summary()['recoveries'],1)
        self.assertEqual(self.s.next(self.now)[1]['data']['outcome']['reason'],'external_id_verified')
    def test_extra_transport_gate_reserves_before_call(self):
        from identity_request_guard import reserve
        def resolve(p):reserve('tmdb');return context('external_id_verified','verified_tmdb')
        self.s.admit(self.item,SOURCES);self.now+=901;run_one(self.s,resolve)
        self.assertEqual(self.s.summary()['requests_rolling_week'],1)
    def test_expired_source_publishes_review_without_resolving(self):
        self.s.admit(self.item,SOURCES);self.now+=8*86400
        with patch('movie_intel_service.build_movie_context') as resolve:
            self.assertFalse(run_one(self.s,resolve));resolve.assert_not_called()
        self.assertEqual(self.s.next(self.now)[1]['data']['outcome']['reason'],'retry_exhausted')
    def test_sqlite_busy_rejects_admission_without_success(self):
        with self.s.tx():
            with self.assertRaises(sqlite3.OperationalError):self.s.admit(self.item,SOURCES)
        self.assertEqual(self.s.summary()['states'],{})
    def test_failed_reservation_never_reaches_transport(self):
        from identity_request_guard import reserve
        from unittest.mock import Mock
        transport=Mock()
        def resolve(p):reserve('tmdb');transport();return context()
        self.s.admit(self.item,SOURCES);self.now+=901
        with patch.object(self.s,'reserve_request',side_effect=sqlite3.OperationalError('database or disk is full')):
            with self.assertRaises(sqlite3.OperationalError):run_one(self.s,resolve)
        transport.assert_not_called();self.assertEqual(self.s.metrics()['pending'],0)

    def test_concurrent_lease_single_owner(self):
        self.s.admit(self.item,SOURCES);self.now+=901
        with ThreadPoolExecutor(2) as pool:leases=list(pool.map(lambda _:self.s.lease(),range(2)))
        self.assertEqual(sum(x is not None for x in leases),1)


class RecurringTests(Base):
    def setUp(self):
        super().setUp();self.s=RecurringStore(self.root/'research',clock=lambda:self.now)
    def ready(self,i=1):
        self.s.admit(case(i,False));run=self.s.start();return run,self.s.lease(run)
    def test_old_pilot_immutable_and_separate_epoch(self):
        old=ResearchStore(self.s.directory);old.close_pilot();before=old.path.read_bytes()
        run,lease=self.ready();self.s.finish(lease,{'reason':'candidate_review'});self.s.end(run)
        self.assertEqual(before,old.path.read_bytes());self.assertNotEqual(self.s.path,old.path)
        with self.assertRaises(ValueError):self.s.admit(case())
    def test_changed_freshness_not_material_never_reruns(self):
        run,lease=self.ready();self.s.finish(lease,{'reason':'transport_failure'});self.s.end(run)
        item=case(1,False);item['observed_at']+=100;item['provenance'][0]['observed_at']+=100
        self.assertEqual(self.s.admit(item),'duplicate');self.now+=8*86400
        run=self.s.start();self.assertIsNone(self.s.lease(run));self.s.end(run)
        item['facts']['year']=2024;self.assertEqual(self.s.admit(item),'admitted')
        run=self.s.start();self.assertIsNotNone(self.s.lease(run))
    def test_five_cases_and_twentyfive_requests_including_unknown(self):
        for i in range(6):self.s.admit(case(i,False))
        run=self.s.start()
        for i in range(5):
            lease=self.s.lease(run)
            for j in range(5):self.s.reserve(run,lease['token'],str((i,j)));self.now+=2
            with self.assertRaisesRegex(Stop,'request_budget'):self.s.reserve(run,lease['token'],'extra')
            self.s.finish(lease,{'reason':'case_request_budget'})
        with self.assertRaisesRegex(Stop,'weekly_case_budget'):self.s.lease(run)
        self.s.end(run);self.s=RecurringStore(self.s.directory,clock=lambda:self.now)
        summary=self.s.summary();self.assertEqual(summary['requests_rolling_week'],25);self.assertEqual(summary['requests_unknown'],25)
        self.assertEqual(summary['states']['queued'],1)
        self.now+=7*86400+1;run=self.s.start();self.assertIsNotNone(self.s.lease(run))
    def test_interrupted_attempt_does_not_repeat_unknown_work(self):
        run,lease=self.ready();self.now+=601;run=self.s.start();self.assertIsNone(self.s.lease(run))
        self.assertEqual(self.s.summary()['cases_rolling_week'],1)
    def test_no_longer_eligible_is_retired_without_deleting_history(self):
        self.s.admit(case(1,False));self.s.reconcile([])
        run=self.s.start();self.assertIsNone(self.s.lease(run))
    def test_auth_suspension_blocks_new_leases(self):
        run,lease=self.ready();request,_=self.s.reserve(run,lease['token'],'key')
        self.s.record(request,'key',{'reason':'auth_failure'});self.s.finish(lease,{'reason':'auth_failure'})
        self.s.admit(case(2,False));self.now+=2
        with self.assertRaisesRegex(Stop,'provider_suspended'):self.s.lease(run)


class HandoffTests(Base):
    def setUp(self):
        super().setUp();self.stage=Store(self.root/'stage')
    def snapshot(self):
        with self.stage.connection(True) as c:return selection.snapshot(c,self.now)
    def ingest(self,reason='listing_id_missing',**changes):
        p=payload(meta_imdb=None,**changes);self.stage.ingest(normalize(p,SOURCES),'release_new')
        e=envelope(p,context(reason),SOURCES);self.stage.ingest(normalize(e,SOURCES,'outcome'),'outcome')
        return p
    def test_all_routes_visible_eligible_only_researched(self):
        for i,r in enumerate(('listing_id_missing','metadata_api_unavailable','title_conflict','listing_id_invalid')):
            self.ingest(r,external_id=str(i))
        s=validate_snapshot(self.snapshot(),self.now)
        self.assertEqual(len(s['cases']),4);self.assertEqual(len(s['items']),1)
        self.assertEqual({c['route'] for c in s['cases']},{'eligible','retry_later','review_only','quarantine'})
    def test_no_outcome_remains_unassessed(self):
        self.stage.ingest(normalize(payload(),SOURCES),'release_new')
        s=validate_snapshot(self.snapshot(),self.now);self.assertEqual(s['items'],[])
        self.assertEqual(s['coverage']['source_releases_without_outcome'],1)
    def test_stale_partial_or_unsafe_snapshot_rejected(self):
        self.ingest();s=self.snapshot()
        for edit in (lambda x:x.update(generated_at=self.now-4000),lambda x:x.update(items=[]),
                     lambda x:x['cases'][0].update(title='https://private.invalid'),lambda x:x.update(secret='x')):
            bad=deepcopy(s);edit(bad)
            with self.assertRaises(ValueError):validate_snapshot(bad,self.now)
    def test_capacity_fails_closed_instead_of_silent_truncation(self):
        with patch.object(selection,'metrics',return_value={'assessed_release_cases':1001}):
            with self.assertRaisesRegex(ValueError,'capacity'):self.snapshot()
    def test_private_changed_report_retains_last_changes_on_quiet_scan(self):
        self.ingest();s=self.snapshot();store=RecurringStore(self.root/'research')
        for item in s['items']:store.admit(item)
        self.assertEqual(write_report(store.directory,s,store),1)
        previous=(store.directory/'review-changes.json').read_bytes()
        self.assertEqual(write_report(store.directory,s,store),0)
        self.assertEqual(previous,(store.directory/'review-changes.json').read_bytes())
        self.assertFalse(json.loads(previous)['telegram_digest_enabled'])
    def test_atomic_private_output_rejects_symlink(self):
        path=self.root/'data.json';tmp=self.root/'data.json.new';tmp.symlink_to(self.root/'target')
        with self.assertRaises(ValueError):atomic_json(path,{'a':1})


class ApolloTests(unittest.TestCase):
    def test_preserves_episode_type_only_for_typed_diagnostic(self):
        p=payload(type='episode',category='Movies :: HD')
        p['event']='action.rejected'
        from movie_intel_service import movie_category_type_conflict
        self.assertTrue(movie_category_type_conflict(p))
        event=envelope(p,context('movie_category_type_conflict','needs_review'),SOURCES)
        self.assertEqual(event['data']['release']['type'],'episode')
        row=normalize(event,SOURCES,'outcome');self.assertEqual(row['metadata']['original_type'],'episode')
        self.assertEqual(selection.route(row['outcome']),'quarantine')
        p['event']='release.new'
        with self.assertRaises(Reject):normalize(p,SOURCES)
    def test_malformed_or_tv_category_never_promoted(self):
        from movie_intel_service import movie_category_type_conflict
        for p in ({'event':'action.rejected','data':[]},{'event':'action.rejected','data':{'release':[]}},payload(type='episode',category='TV :: HD')):
            self.assertFalse(movie_category_type_conflict(p))
