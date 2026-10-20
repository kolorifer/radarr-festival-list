import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from identity_triage_store import digest
from identity_telegram_digest import Digest
from identity_queue_reconcile import prepare,refreshed_report,suppress_refresh

class QueueReconcileTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time();self.cid='outcome-'+'a'*64;self.other='outcome-'+'b'*64
        def row(cid):return {'case_id':cid,'version':'c'*64,'title':'Example','year':2000,'route':'review_only','reason':'title_conflict','observed_at':self.now-50,'first_observed_at':self.now-100,'research_status':'not_admitted','proposal':None,'source_identity':{'imdb':None,'tmdb':None,'asserted_imdb':None,'asserted_tmdb':None},'correlation':'strong_source_id','original_type':'movie','proposed_fix':'Review'}
        self.old={'version':1,'generated_at':self.now-20,'cases':[row(self.cid),row(self.other)],'coverage':{},'versions':{}}
        self.old['versions']={r['case_id']:digest({k:v for k,v in r.items() if k!='observed_at'}) for r in self.old['cases']}
        self.snapshot={'cases':copy.deepcopy(self.old['cases']),'coverage':{'refreshed':True},'generated_at':self.now}
        self.snapshot['cases'][0].update(version='d'*64,route='verified',reason='external_id_verified',observed_at=self.now)
    def test_scoped_refresh_preserves_unrelated_and_marks_old_proposal_stale(self):
        self.old['cases'][0]['proposal']={'current_evidence':True,'result':{'candidates':[]}}
        result=refreshed_report(self.old,self.snapshot,[self.cid])
        self.assertEqual(result['cases'][0]['route'],'verified');self.assertFalse(result['cases'][0]['proposal']['current_evidence'])
        self.assertEqual(result['cases'][1],self.old['cases'][1]);self.assertEqual(self.old['cases'][0]['route'],'review_only')
    def test_unrelated_drift_and_missing_case_refused(self):
        self.snapshot['cases'][1]['version']='e'*64
        with self.assertRaises(ValueError):refreshed_report(self.old,self.snapshot,[self.cid])
        with self.assertRaises(ValueError):refreshed_report(self.old,self.snapshot,[])
    def test_silent_receipt_prevents_only_reconciled_notification(self):
        result=refreshed_report(self.old,self.snapshot,[self.cid])
        with tempfile.TemporaryDirectory() as tmp:
            d=Digest(Path(tmp).resolve()/'digest')
            with d.connect() as c:
                c.execute('INSERT INTO delivery VALUES (?,?,?,?)',(self.cid,'old','sent',self.now-10))
                self.assertEqual(suppress_refresh(c,result,[self.cid],self.now),1)
            from identity_telegram_digest import projection
            send=Mock(return_value=200)
            rows=projection(result,self.now)
            self.assertEqual(d.tick([r for r in rows if r[0]==self.cid],send,self.now),0);send.assert_not_called()
            self.assertEqual(d.tick([r for r in rows if r[0]==self.other],send,self.now),1)
            self.assertEqual(d.summary()['suppressed'],1)
    def test_prepare_binds_exact_case_and_metadata_and_rejects_transient(self):
        current={'case_key':self.cid,'version':'v','material':{'metadata':{'exact':True},'outcome':{'status':'needs_review'}}}
        rec={'release':'a'*64,'metadata':{'exact':True},'outcome':{'status':'verified_tmdb'}}
        with patch('identity_triage_observer.envelope',return_value={'event':'safe'}),patch('identity_triage_intake.normalize',return_value=rec):
            self.assertEqual(prepare({}, {'category':'unknown_movie'},current,{})['expected_version'],'v')
            rec['outcome']['status']='unresolved'
            with self.assertRaises(ValueError):prepare({}, {'category':'unknown_movie'},current,{})
            rec['outcome']['status']='verified_tmdb';rec['metadata']={'different':True}
            with self.assertRaises(ValueError):prepare({}, {'category':'unknown_movie'},current,{})
