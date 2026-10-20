"""Passive selection, durable retry and fail-closed correlation; no providers."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import io,json,os,queue,sqlite3,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch,MagicMock
import identity_selection as selection
import identity_triage_observer as observer
from identity_outcome_outbox import Outbox
from identity_triage_store import Store
from identity_triage_intake import normalize
from identity_research_provider import validate_case
from test_identity_triage import payload,SOURCES

class Base(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.s=Store(self.root/'inbox')
    def ingest(self,p,ch='release_new'):
        return self.s.ingest(normalize(p,SOURCES,ch),ch)
    def outcome(self,p,reason='tmdb_mapping_missing',status='imdb_associated',category='unknown_movie',**extra):
        e=deepcopy(p);e.update(event='identity.outcome',id=str(uuid.uuid4()))
        e['data']['outcome']={'reason':reason,'status':status,'category':category}|extra
        return e
    def routes(self):return self.s.metrics()['selection']['routes']
    def export(self):
        with self.s.connection(True) as c:return selection.export(c)

class SelectionTests(Base):
    def test_positive_atomic_admission_export_preserves_original(self):
        p=payload();self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.routes(),{'eligible':1});row=self.export()[0];validate_case(row)
        self.assertEqual(row['facts']['imdb'],'tt1234567')
        with self.s.connection(True) as c:
            self.assertEqual(c.execute('select distinct status from cases').fetchall(),[('unresolved',)])
            self.assertEqual(c.execute('pragma user_version').fetchone(),(1,))

    def test_only_missing_id_is_unassessed_not_failure(self):
        self.ingest(payload(meta_imdb=None));self.assertEqual(self.export(),[])
        self.assertEqual(self.s.metrics()['selection']['source_releases_without_outcome'],1)
        self.assertEqual(self.routes(),{})

    def test_routing_is_explicit_not_unknown_movie_alone(self):
        cases=[('external_id_verified','verified_tmdb','verified'),('resolved','legacy_resolved','verified'),
               ('other','unresolved','unassessed'),('no_exact_match','unresolved','eligible'),
               ('title_conflict','needs_review','eligible'),('year_conflict','needs_review','eligible'),
               ('ambiguous_exact_matches','unresolved','review_only'),('metadata_api_unavailable','unresolved','retry_later'),
               ('authentication_unavailable','unresolved','review_only'),('rate_limited','unresolved','retry_later'),
               ('non_movie_identity','needs_review','quarantine')]
        for i,(reason,status,expected) in enumerate(cases):
            p=payload(external_id=str(i));self.ingest(p);self.ingest(self.outcome(p,reason,status),'outcome')
            self.assertGreaterEqual(self.routes().get(expected,0),1)
        self.assertEqual(len(self.export()),3)

    def test_conflict_proposals_preserve_source_assertion_and_reason(self):
        p=payload();self.ingest(p)
        self.ingest(self.outcome(p,'year_conflict','needs_review',asserted_imdb='tt1234567'),'outcome')
        item=self.export()[0];validate_case(item)
        self.assertEqual(item['facts']['imdb'],'tt1234567')
        self.assertEqual(item['facts']['contradictions'],['year_conflict'])
        self.assertEqual(item['facts']['year'],p['data']['release']['year'])
        self.assertEqual(item['historical_candidates'],[])

    def test_torrent_evidence_crosses_outbox_collector_handoff_without_approval(self):
        from torrent_research_evidence import extract
        from bs4 import BeautifulSoup
        from test_torrent_research_evidence import PAGE
        from identity_research_handoff import validate_snapshot
        source=extract(BeautifulSoup(PAGE,'html.parser'))
        p=payload();self.ingest(p)
        context={'meta':{'identity_status':'needs_review'},'category':'unknown_movie',
                 'identity_observation':{'reason':'year_conflict','asserted_imdb':'tt1234567','torrent_evidence':source}}
        event=observer.envelope(p,context,SOURCES)
        Outbox.validate(event)
        self.ingest(event,'outcome')
        with self.s.connection(True) as c:snapshot=selection.snapshot(c,time.time())
        validate_snapshot(snapshot,time.time())
        item=self.export()[0];validate_case(item)
        self.assertEqual(item['facts']['torrent_evidence'],source)
        self.assertEqual(item['facts']['contradictions'],['year_conflict'])
        self.assertEqual(self.routes(),{'eligible':1})
        self.ingest(event,'outcome')
        self.assertEqual(len(self.export()),1)
        self.assertEqual(self.export()[0],item)

    def test_routine_verified_approved_repairs_never_queue(self):
        for title in ('Snowman','Hamnet','Not Not Jazz'):
            p=payload(title=title,external_id=title.replace(' ',''));self.ingest(p)
            self.ingest(self.outcome(p,'external_id_verified','verified_tmdb'),'outcome')
        for i,category in enumerate(('quality','existing','not_upgrade')):
            p=payload(external_id='routine'+str(i));self.ingest(p)
            self.ingest(self.outcome(p,category=category),'outcome')
        self.assertEqual(self.export(),[]);self.assertEqual(self.routes(),{'routine':3,'verified':3})

    def test_reordering_reconciles_when_strong_observation_arrives(self):
        p=payload();self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.routes(),{'unmatched':1});self.assertEqual(self.export(),[])
        self.ingest(p);self.assertEqual(self.routes(),{'eligible':1})

    def test_name_fallback_remains_uncertain(self):
        p=payload(external_id=None);self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.routes(),{'unmatched':1});self.assertEqual(self.export(),[])
        self.assertEqual(self.s.metrics()['selection']['correlation'],{'uncertain_name_only':1})

    def test_same_title_distinct_source_release_never_merged(self):
        for i in ('1','2'):
            p=payload(external_id=i);self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.assertEqual(len(self.export()),2)
        p=payload(external_id='1');p['data']['indexer']={'identifier':'other','name':'Other'}
        q=normalize(p,{'other':'Other'});self.s.ingest(q,'release_new')
        self.assertEqual(len(self.export()),2)
        self.assertEqual(self.s.metrics()['selection']['source_releases_without_outcome'],1)

    def test_context_and_asserted_id_conflicts_quarantined(self):
        p=payload();self.ingest(p);changed=deepcopy(p);changed['data']['release']['year']=2024
        self.ingest(self.outcome(changed),'outcome');self.assertEqual(self.routes(),{'quarantine':1})
        q=payload(external_id='2');self.ingest(q);self.ingest(self.outcome(q,asserted_imdb='tt7654321'),'outcome')
        self.assertEqual(self.routes(),{'quarantine':2});self.assertEqual(self.export(),[])

    def test_duplicates_old_events_and_verified_update(self):
        p=payload();self.ingest(p);e=self.outcome(p);self.ingest(e,'outcome')
        e['id']=str(uuid.uuid4());self.ingest(e,'outcome');self.assertEqual(len(self.export()),1)
        with self.s.connection(True) as c:self.assertEqual(c.execute('select count(*) from selection_history').fetchone(),(1,))
        verified=self.outcome(p,'external_id_verified','verified_tmdb');verified['timestamp']=(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat()
        self.ingest(verified,'outcome');self.assertEqual(self.export(),[])
        e['id']=str(uuid.uuid4());self.ingest(e,'outcome');self.assertEqual(self.routes(),{'verified':1})
        newer=self.outcome(p);newer['timestamp']=(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat()
        self.ingest(newer,'outcome');self.assertEqual(len(self.export()),1)

    def test_same_timestamp_disagreement_and_invalid_time_quarantine(self):
        p=payload();self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.ingest(self.outcome(p,'no_exact_match','unresolved'),'outcome')
        self.assertEqual(self.routes(),{'quarantine':1})

    def test_corrupt_outcome_and_tv_never_admitted(self):
        p=payload();self.ingest(p);e=self.outcome(p,asserted_imdb='https://evil.invalid/private')
        self.assertEqual(self.ingest(e,'outcome'),'quarantined');self.assertEqual(self.export(),[])
        self.assertEqual(self.ingest(payload(year='bad')),'quarantined')
        with self.assertRaises(ValueError):self.ingest(payload(type='episode'))

    def test_original_seed_history_is_preserved(self):
        p=payload();p['data']['seed']={'provenance':'a'*64,'contradictions':['missing_crosswalk']}
        self.ingest(p,'seed');self.ingest(p)
        self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.routes(),{'existing_seed':1});self.assertEqual(self.export(),[])
        self.assertEqual(self.s.metrics()['selection']['existing_unresolved_seeds'],1)

    def test_projection_failure_cannot_ack_original_event(self):
        p=payload()
        with patch.object(selection,'ingest',side_effect=sqlite3.OperationalError('full')):
            with self.assertRaises(sqlite3.OperationalError):self.ingest(p)
        self.assertEqual(self.s.metrics()['distinct_releases'],0)
        self.assertEqual(self.ingest(p),'accepted')

    def test_migration_idempotence_and_disable_rollback(self):
        p=payload();self.ingest(p);self.ingest(self.outcome(p),'outcome')
        Store(self.s.directory);self.assertEqual(len(self.export()),1)
        with self.s.connection() as c:
            # Original v1 constraints still prevent any accepted identity status.
            with self.assertRaises(sqlite3.IntegrityError):c.execute('update cases set status="resolved"')

    def test_concurrent_duplicate_projections(self):
        p=payload();self.ingest(p);e=self.outcome(p)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.ingest(e,'outcome'),range(8)))
        self.assertEqual(results.count('accepted'),1);self.assertEqual(len(self.export()),1)

class ObserverTests(Base):
    def test_legacy_reason_reaches_observer_without_inventing_failure(self):
        p=payload(meta_imdb=None)
        e=observer.envelope(p,{'meta':None,'category':'unknown_movie','identity_observation':{'reason':'no_exact_match'}},SOURCES)
        self.assertEqual(e['data']['outcome']['reason'],'no_exact_match')
        e=observer.envelope(p,{'meta':None,'category':'unknown_movie'},SOURCES)
        self.assertEqual(e['data']['outcome']['reason'],'other')

    def test_resolver_assertions_are_separate_from_original_metadata(self):
        p=payload(meta_imdb=None);e=observer.envelope(p,{'meta':{'identity_status':'imdb_associated','identity_reason':'tmdb_mapping_missing','imdb_id':'tt1234567'}},SOURCES)
        self.assertIsNone(e['data']['release']['meta_imdb']);self.assertEqual(e['data']['outcome']['asserted_imdb'],'tt1234567')
        self.assertIsNone(p['data']['release']['meta_imdb'])

    def test_saturation_is_counted_without_blocking_or_sending(self):
        q=queue.Queue(1);q.put({});worker=MagicMock();worker.is_alive.return_value=True
        cfg={'sources':SOURCES}
        with patch.dict(os.environ,{'MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED':'1','MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG':'unused'}),patch.object(observer,'read_config',return_value=cfg),patch.object(observer,'_QUEUE',q),patch.object(observer,'_WORKER',worker),patch.object(observer,'_send') as send,patch('sys.stdout',new_callable=io.StringIO):
            before=observer.metrics().get('queue_full',0);observer.observe(payload(),{})
            self.assertEqual(observer.metrics()['queue_full'],before+1);send.assert_not_called()

    def test_spool_crash_restart_retry_ack_and_duplicate(self):
        box=Outbox(self.root/'outbox');e=observer.envelope(payload(),{},SOURCES)
        box.put(e);box.put(e);self.assertEqual(box.metrics()['pending'],1)
        box=Outbox(box.directory);key,body,n=box.next();self.assertEqual(body,e)
        box.failed(key,n);self.assertIsNone(box.next());self.assertEqual(box.next(time.time()+1000)[0],key)
        box.ack(key);box.ack(key);self.assertEqual(box.metrics()['delivered'],1);self.assertEqual(box.metrics()['pending'],0)

    def test_collector_commit_then_sender_crash_replays_once(self):
        p=payload();self.ingest(p);box=Outbox(self.root/'outbox');e=self.outcome(p);box.put(e)
        key,item,_=box.next();self.assertEqual(self.ingest(item,'outcome'),'accepted')
        box=Outbox(box.directory);key,item,_=box.next();self.assertEqual(self.ingest(item,'outcome'),'duplicate_event');box.ack(key)
        self.assertEqual(len(self.export()),1)

    def test_spool_busy_permissions_and_secret_exclusion(self):
        box=Outbox(self.root/'outbox');p=payload(download_url='https://secret.invalid/capability');e=observer.envelope(p,{},SOURCES)
        with box.tx():
            with self.assertRaises(sqlite3.OperationalError):box.put(e)
        box.put(e);self.assertNotIn(b'secret.invalid',box.path.read_bytes())
        box.path.chmod(0o644)
        with self.assertRaises(ValueError):box.metrics()

class IntegrationGates(Base):
    def test_mapping_missing_without_any_imdb_assertion_is_invalid(self):
        p=payload(meta_imdb=None);self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.routes(),{'quarantine':1})

    def test_outbox_cannot_accidentally_store_raw_capabilities(self):
        box=Outbox(self.root/'outbox');e=self.outcome(payload(download_url='https://private.invalid/capability'))
        with self.assertRaises(ValueError):box.put(e)
        self.assertEqual(box.metrics()['pending'],0)

    def test_real_context_retains_legacy_resolver_failure_and_exception(self):
        import movie_intel_service as service
        p=payload(meta_imdb=None)
        with patch.object(service,'find_local',return_value=None),patch.object(service,'lookup_listing',return_value={'reason':'disabled','source':'torrentleech_listing'}),patch.object(service,'resolve_movie',return_value=None),patch.object(service,'resolution_reason',return_value='no_exact_match'),patch.object(service,'decision_log'):
            context=service.build_movie_context(p)
            self.assertEqual(context['identity_observation']['reason'],'no_exact_match')
            self.assertIsNone(context['meta'])
            self.assertEqual(observer.envelope(p,context,SOURCES)['data']['outcome']['reason'],'no_exact_match')
            with patch.object(service,'resolve_movie',side_effect=TimeoutError):
                context=service.build_movie_context(p)
                self.assertEqual(context['identity_observation']['reason'],'resolver_error')
                self.assertIsNone(context['meta'])

    def test_rollback_to_v1_layout_remains_readable_and_legacy_outcomes_explicit(self):
        p=payload();self.ingest(p)
        with self.s.connection() as c:
            eid=c.execute('select id from evidence').fetchone()[0]
            c.execute('insert into outcomes values (?,?,?,?)',(eid,'unknown_movie','unresolved','no_exact_match'))
        self.assertEqual(self.s.metrics()['selection']['legacy_outcome_rows_without_chronology'],1)
        self.assertEqual(self.export(),[])

    def test_quarantine_spool_strips_invalid_asserted_capability(self):
        e=observer.envelope(payload(),{'meta':{'imdb_id':'https://private.invalid/capability'}},SOURCES)
        self.assertNotIn('private.invalid',json.dumps(e))
        box=Outbox(self.root/'outbox');box.put(e)
        e['data']['outcome']['asserted_imdb']='https://private.invalid/capability'
        with self.assertRaises(ValueError):box.put(e)

    def test_same_timestamp_different_evidence_cannot_hide_conflict(self):
        p=payload();self.ingest(p);e=self.outcome(p);self.ingest(e,'outcome')
        e['id']=str(uuid.uuid4());e['data']['release']['meta_tmdb']=123
        self.ingest(e,'outcome')
        self.assertEqual(self.routes(),{'quarantine':1})
