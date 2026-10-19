"""Post-filter action fixtures model autobrr v1.88; no real integrations."""
from contextlib import contextmanager
from copy import deepcopy
import json
import sqlite3
import uuid
import unittest
from unittest.mock import patch
from test_identity_triage import Base, payload, SOURCES
from identity_triage_intake import normalize, Reject, SELECTED_EVENTS
from identity_triage_observer import envelope
from identity_triage_store import Store
from identity_research_handoff import validate_snapshot
import identity_selection as selection
import time
import threading
import identity_triage_service as service
import test_identity_triage as fixtures


def selected(event='action.rejected', **changes):
    p=payload(**changes);p['event']=event
    p['data'].update(filter={'id':1,'name':'Synthetic filter'},
                     action={'name':'Synthetic action','type':'RADARR','client':'Synthetic client'},
                     result={'status':SELECTED_EVENTS[event],'rejections':['Unknown Movie'] if event=='action.rejected' else []})
    return p


class SelectedTests(Base):
    def ingest(self,p=None,channel='selected'):
        return super().ingest(p or selected(),channel)
    def outcome(self,p,reason='tmdb_mapping_missing',status='imdb_associated'):
        return envelope(p,{'category':'unknown_movie','meta':{'identity_status':status,'identity_reason':reason}},SOURCES)
    def test_all_three_results_do_not_verify_identity(self):
        for e in SELECTED_EVENTS:self.assertEqual(self.ingest(selected(e)), 'accepted')
        m=self.store.metrics();self.assertEqual(m['distinct_releases'],1)
        self.assertEqual(m['selected']['observations'],3)
        self.assertEqual(m['selected']['events'],dict.fromkeys(SELECTED_EVENTS,1))
        self.assertEqual(m['selection']['routes'],{})
        self.assertEqual(m['selection']['source_releases_without_outcome'],1)
    def test_unknown_movie_both_orders_strong_correlation(self):
        for n,reverse in enumerate((False,True)):
            p=selected(external_id=str(n));o=self.outcome(p)
            if reverse:self.ingest(o,'outcome')
            self.ingest(p)
            if not reverse:self.ingest(o,'outcome')
        m=self.store.metrics();self.assertEqual(m['selection']['routes'],{'eligible':2})
        self.assertEqual(m['selected']['unknown_movie_strongly_correlated'],2)
        with self.store.connection() as c:validate_snapshot(selection.snapshot(c,time.time()),time.time())
    def test_routes_still_distinguish_verified_retry_review_quarantine_unassessed(self):
        for n,(reason,status,expected) in enumerate((('external_id_verified','verified_tmdb','verified'),('metadata_api_unavailable','unresolved','retry_later'),('title_conflict','unresolved','review_only'),('listing_id_invalid','unresolved','quarantine'),('other','unresolved','unassessed'))):
            p=selected(external_id=str(n));self.ingest(p);self.ingest(self.outcome(p,reason,status),'outcome')
            self.assertIn(expected,self.store.metrics()['selection']['routes'])
    def test_uuid_and_material_dedup_separate_from_multiple_actions(self):
        p=selected();self.ingest(p);self.assertEqual(self.ingest(p),'duplicate_event')
        p['id']=str(uuid.uuid4());self.ingest(p)
        self.assertEqual(self.store.metrics()['selected']['observations'],1)
        p['id']=str(uuid.uuid4());p['data']['filter']['id']=2;self.ingest(p)
        p['id']=str(uuid.uuid4());p['data']['action']['name']='Second action';self.ingest(p)
        self.assertEqual(self.store.metrics()['selected']['observations'],3)
        self.assertEqual(self.store.metrics()['distinct_releases'],1)
        self.assertEqual(self.store.metrics()['evidence_versions'],1)
        self.assertEqual(self.store.metrics()['provisional_cases'],1)
    def test_changed_metadata_and_different_source_releases(self):
        p=selected();self.ingest(p)
        p['id']=str(uuid.uuid4());p['data']['release']['year']=2024;self.ingest(p)
        self.assertEqual(self.store.metrics()['evidence_versions'],2)
        self.ingest(selected(external_id='456'))
        self.assertEqual(self.store.metrics()['distinct_releases'],2)
    def test_announcement_selected_overlap_same_evidence_and_uuid_channels(self):
        p=selected();old=deepcopy(p);old['event']='release.new'
        self.ingest(old,'release_new');self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.store.metrics()['evidence_versions'],1)
        self.assertEqual(self.store.metrics()['selection']['correlation'],{'strong_source_id':1})
    def test_missing_id_remains_nonactionable(self):
        p=selected(external_id='');self.ingest(p);self.ingest(self.outcome(p),'outcome')
        self.assertEqual(self.store.metrics()['selection']['routes'],{'unmatched':1})
        self.assertEqual(self.store.metrics()['selected']['weak_source_observations'],1)
    def test_apollo_episode_movie_category_quarantines_not_tv(self):
        p=selected(type='episode',category='Movies :: 4K');self.ingest(p)
        self.assertEqual(self.store.metrics()['selection']['routes'],{'quarantine':1})
        self.ingest(self.outcome(p,'movie_category_type_conflict','needs_review'),'outcome')
        self.assertEqual(self.store.metrics()['selection']['correlation'],{'strong_source_id':1})
        for category in ('TV :: HD','',None):
            with self.assertRaises(Reject):normalize(selected(type='episode',category=category),SOURCES,'selected')
    def test_unsupported_notifications_and_invalid_provenance_rejected(self):
        cases=[]
        for field in ('filter','action','result'):
            p=selected();del p['data'][field];cases.append(p)
        p=selected();p['data']['filter']['id']=True;cases.append(p)
        p=selected();p['data']['result']['status']='PUSH_APPROVED';cases.append(p)
        p=selected();p['data']['action']['type']='BOGUS';cases.append(p)
        p=selected();p['data']['indexer']['name']='spoof';cases.append(p)
        p=selected();p['event']='release.new';cases.append(p)
        for p in cases:
            with self.assertRaises(Reject):normalize(p,SOURCES,'selected')
    def test_secrets_raw_errors_urls_and_names_not_persisted(self):
        p=selected('action.error',download_url='https://secret.invalid/CANARY',info_url='CANARY',magnet_uri='CANARY')
        p['data']['result']['rejections']=['private CANARY'];p['data']['action']['headers']='CANARY'
        p['data']['filter']['name']='CANARY';p['data']['action']['name']='CANARY';p['data']['action']['client']='CANARY'
        self.ingest(p);self.store.backup(self.root/'backup.sqlite3')
        self.assertNotIn(b'CANARY',(self.root/'backup.sqlite3').read_bytes())
        self.assertEqual(self.sql('select reason from selected_observations'),[('action_error',)])
    def test_timestamp_offsets_same_material_dedup(self):
        p=selected();p['timestamp']='2026-10-19T14:00:00+02:00';self.ingest(p)
        p['id']=str(uuid.uuid4());p['timestamp']='2026-10-19T12:00:00Z';self.ingest(p)
        self.assertEqual(self.store.metrics()['selected']['observations'],1)
    def test_new_uuid_after_restart_dedup_and_v1_history_preserved(self):
        p=payload();self.ingest(p,'retained')
        before=self.sql('select * from evidence')
        with self.store.connection() as c:
            c.execute('drop table selected_observations');c.commit()
        self.store=Store(self.store.directory)
        self.assertEqual(before,self.sql('select * from evidence'))
        p['event']='action.rejected';p['data'].update(selected()['data']);self.ingest(p)
        self.store=Store(self.store.directory);p['id']=str(uuid.uuid4());self.ingest(p)
        self.assertEqual(self.store.metrics()['selected']['observations'],1)
        self.assertEqual(self.sql('pragma user_version'),[(1,)])
    def test_busy_full_rollback_has_no_partial_selected_observation(self):
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):self.ingest()
        with patch('identity_selection.ingest',side_effect=sqlite3.OperationalError('database or disk is full')):
            with self.assertRaises(sqlite3.OperationalError):self.ingest()
        self.assertEqual(self.store.metrics()['selected']['observations'],0)
        self.assertEqual(self.store.metrics()['distinct_releases'],0)
    def test_wrong_movie_type_and_invalid_time_are_quarantined_without_text(self):
        p=selected(type='unknown');self.assertEqual(self.ingest(p),'quarantined')
        p=selected();p['timestamp']='bad';self.assertEqual(self.ingest(p),'quarantined')
        self.assertEqual(self.store.metrics()['selected']['observations'],0)


# Reuse just HTTP setup/helpers, not the inherited suite.
class SelectedHTTPTests(Base):
    def setUp(self):
        super().setUp()
        self.cfg={'version':1,'enabled':True,'port':40715,'sources':SOURCES,'release_key':'r'*43,'outcome_key':'o'*43}
        self.config=self.root/'config.json';self.write_config()
        self.server=service.Server(('127.0.0.1',0),self.config,self.store)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
    close=fixtures.HTTPTests.close
    write_config=fixtures.HTTPTests.write_config
    request=fixtures.HTTPTests.request
    def test_selected_only_rejects_broad_and_preserves_outcome(self):
        self.cfg['source_mode']='selected_only';self.write_config()
        self.assertEqual(self.request(payload())[0],410)
        p=selected();self.assertEqual(self.request(p,path='/v1/selected')[0],200)
        o=envelope(p,{'meta':{'identity_status':'unresolved','identity_reason':'no_exact_match'}},SOURCES)
        self.assertEqual(self.request(o,path='/v1/outcome',key=self.cfg['outcome_key'])[0],200)
        self.assertEqual(self.store.metrics()['selection']['routes'],{'eligible':1})
    def test_selected_auth_and_commit_failure(self):
        p=selected()
        self.assertEqual(self.request(p,path='/v1/selected',key=self.cfg['outcome_key'])[0],401)
        with patch.object(self.store,'ingest',side_effect=sqlite3.OperationalError('full secret')):
            status,raw=self.request(p,path='/v1/selected')
        self.assertEqual(status,503);self.assertNotIn(b'secret',raw)
        self.assertEqual(self.request(p,path='/v1/selected')[0],200)
        self.assertEqual(self.request(p,path='/v1/selected')[0],200)
        self.assertEqual(self.store.metrics()['selected']['observations'],1)
    def test_config_rollback_preserves_selected_history(self):
        self.request(selected(),path='/v1/selected')
        self.cfg['source_mode']='selected_only';self.write_config()
        self.assertEqual(self.request()[0],410)
        del self.cfg['source_mode'];self.write_config()
        self.assertEqual(self.request()[0],200)
        self.assertEqual(self.store.metrics()['selected']['observations'],1)

