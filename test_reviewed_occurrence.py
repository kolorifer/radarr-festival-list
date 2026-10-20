"""Review closure never becomes reusable identification or download approval."""
import copy,time,unittest,uuid
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock
from test_identity_selection import Base
from test_identity_triage import payload
import identity_selection as selection
from identity_research_handoff import validate_snapshot
from identity_telegram_digest import Digest,projection
from identity_queue_reconcile import refreshed_report
from identity_triage_store import digest

class ReviewedOccurrenceTests(Base):
    def setup_case(self):
        self.p=payload();self.ingest(self.p)
        self.event=self.outcome(self.p,'year_conflict','needs_review');self.ingest(self.event,'outcome')
        self.before=self.snap();self.row=self.before['cases'][0]
    def snap(self):
        with self.s.connection(True) as c:return selection.snapshot(c,time.time())
    def close(self,**kwargs):
        with self.s.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            result=selection.review_occurrence(c,self.row['case_id'],kwargs.pop('version',self.row['version']),kwargs.pop('imdb','tt0041615'),kwargs.pop('tmdb',45184),kwargs.pop('year',1949))
            c.commit();return result
    def test_review_is_closed_not_verified_and_preserves_evidence(self):
        self.setup_case();before=self.export()[0];self.close();s=self.snap()
        validate_snapshot(s,time.time());r=s['cases'][0]
        self.assertEqual(r['route'],'reviewed_occurrence');self.assertEqual(r['reason'],'year_conflict');self.assertEqual(self.export(),[])
        self.assertEqual(r['source_identity'],self.row['source_identity'])
        with self.s.connection(True) as c:
            self.assertEqual(c.execute('select count(*) from selection_events').fetchone()[0],1)
            self.assertEqual(c.execute('select imdb,tmdb,year from selection_reviews').fetchone(),('tt0041615',45184,1949))
        self.assertEqual(before['facts']['contradictions'],['year_conflict'])
    def test_same_event_redelivery_stays_closed_but_new_identical_outcome_reopens(self):
        self.setup_case();self.close();self.ingest(self.event,'outcome');self.assertEqual(self.routes(),{'reviewed_occurrence':1})
        new=copy.deepcopy(self.event);new['id']=str(uuid.uuid4())
        # Even equal timestamps and identical evidence are a new accepted event.
        self.ingest(new,'outcome');s=self.snap();self.assertEqual(s['cases'][0]['route'],'eligible')
        self.assertNotEqual(s['cases'][0]['version'],self.row['version']);self.assertEqual(len(self.export()),1)
        self.assertNotEqual(self.export()[0]['provenance'][0]['digest'],self.row['version'])
        validate_snapshot(s,time.time())
    def test_new_source_observation_reopens_and_cannot_reuse_review(self):
        self.setup_case();self.close();new=copy.deepcopy(self.p);new['id']=str(uuid.uuid4());self.ingest(new)
        self.assertEqual(self.routes(),{'eligible':1})
        with self.assertRaises(ValueError):self.close()
    def test_out_of_order_event_conservatively_reopens(self):
        self.setup_case();self.close();new=copy.deepcopy(self.event);new['id']=str(uuid.uuid4());new['timestamp']=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        self.ingest(new,'outcome');self.assertEqual(self.routes(),{'eligible':1})
    def test_stale_invalid_and_nontransaction_reviews_are_rejected(self):
        self.setup_case()
        for kwargs in ({'version':'wrong'},{'imdb':'invalid'},{'tmdb':True},{'year':True}):
            with self.assertRaises(ValueError):self.close(**kwargs)
        self.assertEqual(self.routes(),{'eligible':1})
        with self.s.connection() as c:
            with self.assertRaises(ValueError):selection.review_occurrence(c,self.row['case_id'],self.row['version'],'tt0041615',45184,1949)
        self.close()
        self.row=self.snap()['cases'][0]
        with self.assertRaises(ValueError):self.close()
    def test_report_age_digest_and_next_encounter(self):
        self.setup_case();row=dict(self.row,research_status='awaiting_evidence',proposal={'current_evidence':True,'result':{}})
        old={'version':1,'generated_at':time.time(),'cases':[row],'versions':{row['case_id']:digest(row)}}
        self.close();updated=refreshed_report(old,self.snap(),[row['case_id']])
        self.assertEqual(updated['oldest_unresolved_age_seconds'],0)
        self.assertFalse(updated['cases'][0]['proposal']['current_evidence'])
        rows=projection(updated,time.time());self.assertIn('Reviewed for this occurrence only',rows[0][3]);self.assertNotIn('stale',rows[0][3])
        d=Digest(self.root/'digest');send=Mock(return_value=200)
        self.assertEqual(d.tick(rows,send,time.time()),0);send.assert_not_called()
        new=copy.deepcopy(self.event);new['id']=str(uuid.uuid4());self.ingest(new,'outcome')
        reopened=refreshed_report(updated,self.snap(),[row['case_id']])
        self.assertEqual(d.tick(projection(reopened,time.time()),send,time.time()),1)
    def test_next_selected_filter_event_reopens(self):
        from test_identity_selected import selected
        self.setup_case();self.close()
        p=selected();self.ingest(p,'selected')
        self.assertEqual(self.routes(),{'eligible':1})
        validate_snapshot(self.snap(),time.time())
    def test_other_releases_not_closed(self):
        self.setup_case();self.close();p=payload(external_id='another')
        self.ingest(p);self.ingest(self.outcome(p,'year_conflict','needs_review'),'outcome')
        self.assertEqual(self.routes(),{'reviewed_occurrence':1,'eligible':1})

if __name__=='__main__':unittest.main()
