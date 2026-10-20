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
        for _ in range(40):self.s.reserve_request(lease,'tmdb');self.now+=2
        with self.assertRaisesRegex(RetryBudget,'retry_request_budget'):self.s.reserve_request(lease,'tmdb')
        self.s.cooldown('listing',3600,False)
        with self.assertRaisesRegex(RetryBudget,'cooldown'):self.s.reserve_request(lease,'listing')
        self.s.cooldown('tmdb',0,True)
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        with self.assertRaisesRegex(RetryBudget,'auth'):self.s.reserve_request(lease,'tmdb')
        self.assertEqual(self.s.summary()['requests_rolling_day'],40)
    def test_budget_deferral_survives_restart_without_consuming_attempt(self):
        lease=self.ready()
        with self.s.tx() as c:
            for n in range(40):c.execute('insert into retry_requests values(NULL,?,?,?)',('older','tmdb',self.now-100+n))
            c.execute('update retry_jobs set expires=?',(self.now+8*86400,))
        self.s.defer(lease,'retry_request_budget','tmdb')
        self.assertEqual(self.s.metrics()['pending'],0)
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        self.assertIsNone(self.s.lease())
        with self.s.tx() as c:
            due=c.execute('select due from retry_jobs').fetchone()[0]
            self.assertEqual(due,self.now-100+86400+1)
            # Extend only this fixture's source lifetime to test budget reopening.
            c.execute('update retry_jobs set expires=?',(due+100,))
        self.now=due
        self.assertEqual(self.s.lease()['number'],1)

    def test_cooldown_deferral_counts_partial_request_but_not_empty_wait(self):
        lease=self.ready();self.s.cooldown('listing',100,False)
        self.s.defer(lease,'retry_provider_cooldown','listing');self.now+=101
        lease=self.s.lease();self.assertEqual(lease['number'],1)
        self.s.reserve_request(lease,'tmdb')
        self.s.cooldown('listing',100,False)
        self.s.defer(lease,'retry_provider_cooldown','listing');self.now+=101
        self.assertEqual(self.s.lease()['number'],2)

    def test_budget_block_does_not_publish_false_failure(self):
        from identity_request_guard import reserve
        self.s.admit(self.item,SOURCES);self.now+=901
        with self.s.tx() as c:
            for n in range(40):c.execute('insert into retry_requests values(NULL,?,?,?)',('older','tmdb',self.now))
        def resolve(p):
            try:reserve('tmdb')
            except RetryBudget:pass
            return context()
        run_one(self.s,resolve)
        self.assertEqual(self.s.metrics()['pending'],0)
        self.assertEqual(self.s.summary()['states'],{'pending':1})

    def test_daily_policy_migrates_only_waiting_budget_jobs_once(self):
        lease=self.ready()
        self.s.finish(lease,'retry_request_budget')
        with self.s.tx() as c:
            c.execute('delete from retry_policy') # fixture simulates pre-upgrade schema
            c.execute('update retry_jobs set due=?',(self.now+6*86400,))
            c.execute('insert into retry_requests values(NULL,?,?,?)',('older','listing',self.now-2*86400))
            c.execute('insert into retry_provider values(?,?,?)',('listing',self.now+3600,1))
            before=c.execute('select * from retry_attempts').fetchall()
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        with self.s.tx() as c:
            self.assertEqual(c.execute('select due from retry_jobs').fetchone()[0],self.now+60)
            self.assertEqual(c.execute('select count(*) from retry_requests').fetchone()[0],1)
            self.assertEqual(c.execute('select * from retry_attempts').fetchall(),before)
            self.assertEqual(c.execute('select auth from retry_provider').fetchone()[0],1)
            c.execute('update retry_jobs set due=?',(self.now+5000,))
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        with self.s.tx() as c:self.assertEqual(c.execute('select due from retry_jobs').fetchone()[0],self.now+5000)

    def test_migration_does_not_reopen_review_expired_or_leased_jobs(self):
        lease=self.ready()
        with self.s.tx() as c:
            c.execute('delete from retry_policy')
            c.execute('update retry_jobs set reason="retry_request_budget"')
            before=c.execute('select * from retry_jobs').fetchall()
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        with self.s.tx() as c:
            self.assertEqual(c.execute('select * from retry_jobs').fetchall(),before)
            c.execute('delete from retry_policy')
            c.execute('update retry_jobs set state="review",due=?',(self.now+6*86400,))
            before=c.execute('select * from retry_jobs').fetchall()
        self.s=RetryStore(self.s.directory,clock=lambda:self.now)
        with self.s.tx() as c:self.assertEqual(c.execute('select * from retry_jobs').fetchall(),before)

    def test_yesterdays_requests_do_not_block_today_but_recent_requests_do(self):
        lease=self.ready()
        with self.s.tx() as c:
            for n in range(20):c.execute('insert into retry_requests values(NULL,?,?,?)',('older','listing',self.now-86401))
        self.s.reserve_request(lease,'listing');self.now+=2
        with self.s.tx() as c:
            for n in range(19):c.execute('insert into retry_requests values(NULL,?,?,?)',('older','listing',self.now))
        with self.assertRaisesRegex(RetryBudget,'retry_request_budget'):self.s.reserve_request(lease,'listing')

    def test_temporary_notification_is_clear_without_promising_recovery(self):
        from movie_intel_service import format_message
        text=format_message(self.p,meta=context('listing_temporary_http')['meta'])
        self.assertIn('temporarily unavailable',text)
        self.assertIn('Approval unavailable',text)
        text=format_message(self.p,meta=context('title_conflict')['meta'])
        self.assertNotIn('temporarily unavailable',text)

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
        self.assertEqual(self.s.summary()['requests_rolling_day'],1)
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
    def test_first_observation_age_survives_new_evidence_freshness(self):
        p=self.ingest();first=self.snapshot()['cases'][0]['first_observed_at']
        event=envelope(p,context('no_exact_match'),SOURCES)
        self.stage.ingest(normalize(event,SOURCES,'outcome'),'outcome')
        snapshot=validate_snapshot(self.snapshot(),self.now)
        self.assertEqual(snapshot['cases'][0]['first_observed_at'],first)
        self.assertGreaterEqual(snapshot['cases'][0]['observed_at'],first)

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
    def test_resolved_case_marks_previous_research_proposal_historical(self):
        p=self.ingest();snapshot=self.snapshot();store=RecurringStore(self.root/'research')
        store.admit(snapshot['items'][0]);run=store.start();lease=store.lease(run)
        store.finish(lease,{'reason':'candidate_review'});store.end(run)
        event=envelope(p,context('external_id_verified','verified_tmdb'),SOURCES)
        self.stage.ingest(normalize(event,SOURCES,'outcome'),'outcome')
        snapshot=self.snapshot();store.reconcile(snapshot['items']);write_report(store.directory,snapshot,store)
        report=json.loads((store.directory/'review-report.json').read_text())
        self.assertEqual(report['cases'][0]['route'],'verified')
        self.assertFalse(report['cases'][0]['proposal']['current_evidence'])

    def test_atomic_private_output_rejects_symlink(self):
        path=self.root/'data.json';tmp=self.root/'data.json.new';tmp.symlink_to(self.root/'target')
        with self.assertRaises(ValueError):atomic_json(path,{'a':1})


class ApolloTests(unittest.TestCase):
    def test_preserves_episode_type_only_for_typed_diagnostic(self):
        # Sanitized autobrr/rls v0.8.1 output shape; no tracker reference.
        p=payload(type='episode',category='Movies :: WEBRip',title='Apollo 10 1',year=2022,
                  name='Apollo 10 1 - 2 A Space Age Childhood 2022 1080p WEBRip',episode=2)
        p['event']='action.rejected'
        from movie_intel_service import movie_category_type_conflict
        self.assertTrue(movie_category_type_conflict(p))
        event=envelope(p,context('movie_category_type_conflict','needs_review'),SOURCES)
        self.assertEqual(p['data']['release']['episode'],2)
        self.assertEqual(event['data']['release']['type'],'episode')
        row=normalize(event,SOURCES,'outcome');self.assertEqual(row['metadata']['original_type'],'episode')
        self.assertEqual(selection.route(row['outcome']),'quarantine')
        p['event']='release.new'
        with self.assertRaises(Reject):normalize(p,SOURCES)
    def test_malformed_or_tv_category_never_promoted(self):
        from movie_intel_service import movie_category_type_conflict
        for p in ({'event':'action.rejected','data':[]},{'event':'action.rejected','data':{'release':[]}},payload(type='episode',category='TV :: HD')):
            self.assertFalse(movie_category_type_conflict(p))

    def test_fraction_title_context_stays_blocked_in_actor(self):
        import tmdb_resolver as tmdb
        tmdb._ID_CACHE.clear()
        details={'id':123,'title':'18½','original_title':'18½','release_date':'2021-01-01',
                 'external_ids':{'imdb_id':'tt1234567'}}
        with patch.object(tmdb,'_get',side_effect=lambda path,params: {'movie_results':[{'id':123}]} if path.startswith('/find/') else details):
            result=tmdb.resolve_external_movie('18 1 2',2021,imdb_id='tt1234567')
        self.assertEqual(result['identity_status'],'needs_review')
        self.assertEqual(result['identity_reason'],'title_conflict')

    def test_diagnostic_labels_case_without_private_url_or_identity_promotion(self):
        from movie_intel_service import type_conflict_message
        p=payload(title='Apollo 10 1',year=2022,type='episode')
        self.assertIn('Apollo 10 1 (2022)',type_conflict_message(p))
        p['data']['release']['title']='https://private.invalid/download?token=secret'
        self.assertNotIn('private.invalid',type_conflict_message(p))


class ResearchPunctuationTests(unittest.TestCase):
    def test_colon_candidate_is_investigated_but_never_approved(self):
        from identity_triage_worker import investigate
        from unittest.mock import Mock
        item=case(1,False);item['facts'].update(title='Synthetic Documentary',imdb=None,variants=['Synthetic Documentary'])
        provider=Mock()
        provider.get.side_effect=[{'reason':'ok','data':{'results':[{'id':123,'title':'Synthetic: Documentary','original_title':None}]}},
                                  {'reason':'ok','data':{'results':[]}},
                                  {'reason':'ok','data':{'id':123,'title':'Synthetic: Documentary','original_title':None,'aliases':[],'translations':[],'date':'2025-01-01','imdb':None,'runtime':60,'directors':[]}}]
        result=investigate({'item':item},provider)
        self.assertEqual(result['reason'],'candidate_review');self.assertFalse(result['runtime_correction'])
        self.assertEqual(result['candidates'][0]['confidence'],'review_required')
        self.assertEqual(provider.get.call_count,3)
    def test_existing_search_evidence_visible_without_reopening_ledger(self):
        from identity_investigation_report import search_candidates
        result={'original_facts':{'title':'Synthetic Documentary','year':2025},'reason':'no_supported_candidate',
                'evidence':[{'method':'movie_search','result':{'data':{'results':[{'id':123,'title':'Synthetic: Documentary','original_title':None,'date':'2025-01-01','type':'movie'}]}}}]}
        before=deepcopy(result);rows=search_candidates(result)
        self.assertEqual(rows[0]['confidence'],'search_only_unverified');self.assertTrue(rows[0]['year_agrees'])
        self.assertEqual(result,before)


class HandoffFailureTests(unittest.TestCase):
    def test_connect_timeout_reports_only_fixed_diagnostics(self):
        import identity_research_handoff as handoff
        import io
        output=io.StringIO()
        with patch('identity_triage_observer.read_config',return_value={'port':40715}), patch.object(handoff.socket,'create_connection',side_effect=TimeoutError('PRIVATE_URL_TOKEN')), patch('sys.stdout',output):
            self.assertEqual(handoff.main(),1)
        self.assertIn('stage=connect reason=timeout',output.getvalue());self.assertNotIn('PRIVATE',output.getvalue())
    def test_scan_retry_is_bounded_and_does_not_repeat_worker(self):
        import identity_research_scan as scan
        from unittest.mock import Mock
        import io
        with patch.object(scan.subprocess,'run',return_value=Mock(returncode=1)) as run, patch.object(scan.time,'sleep') as sleep, patch('sys.stdout',io.StringIO()):
            self.assertEqual(scan.main(),1)
        self.assertEqual(run.call_count,3);self.assertEqual(sleep.call_count,2)
        self.assertTrue(all(call.kwargs['timeout']==15 for call in run.call_args_list))
        self.assertNotIn('identity_triage_worker',scan.COMMAND[-1])
        self.assertNotIn('Restart=',Path('deploy/identity-investigation-scan.service').read_text())
    def test_handoff_retry_stops_after_success(self):
        import identity_research_scan as scan
        from unittest.mock import Mock
        with patch.object(scan.subprocess,'run',side_effect=[Mock(returncode=1),Mock(returncode=0)]) as run, patch.object(scan.time,'sleep'):
            self.assertEqual(scan.main(),0)
        self.assertEqual(run.call_count,2)
