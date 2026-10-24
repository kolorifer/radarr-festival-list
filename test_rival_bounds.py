import unittest
from copy import deepcopy
from research.identity_scoring.scorer import evaluate
from research.identity_scoring.refresh import apply_existing_conflict_guard

class RivalBoundsTests(unittest.TestCase):
    def case(self):
        source={'title':'Example','year':2023,'runtime':146,'language':'fr','imdb':'tt1234567','checked_listing':True,'conflicting_evidence':False,'nfo_bound':True,'unique_tracker_movie_id':1}
        winner={'id':1,'titles':['Example'],'years':[2023],'runtime':146,'language':'fr','imdb':'tt1234567','crosswalk_verified':True,'media_type':'movie'}
        rival={'id':2,'titles':['Other'],'years':[1990],'runtime':None,'language':None,'imdb':None,'crosswalk_verified':False,'media_type':'movie','evidence_status':'search_only'}
        return {'source':source,'candidates':[winner,rival],'candidate_set_complete':False}
    def test_unseen_and_summary_aliases_keep_all_non_id_points(self):
        r=evaluate(self.case());self.assertEqual(r['decision'],'would_identify');self.assertEqual(r['margin'],25)
        self.assertEqual(r['ranked'][1]['upper_score'],75)
        self.assertEqual(r['rival_bound_audit']['unseen_upper_score'],75)
        self.assertFalse(r['rival_bound_audit']['search_complete'])
    def test_no_unique_proof_no_relaxation(self):
        c=self.case();c['source'].pop('unique_tracker_movie_id');r=evaluate(c)
        self.assertEqual(r['decision'],'review');self.assertEqual(r['ranked'][1]['upper_score'],100)
    def test_duplicate_imdb_is_conflict_not_a_bound(self):
        c=self.case();c['candidates'][1].update(imdb='tt1234567');r=evaluate(c)
        self.assertEqual(r['decision'],'review');self.assertIn('conflicting_duplicate_mapping',r['reasons'])
    def test_missing_conflicting_or_weak_leader_evidence(self):
        for field,value in [('checked_listing',False),('nfo_bound',False),('conflicting_evidence',True),('runtime',None),('language',None),('year',2022),('unique_tracker_movie_id',2)]:
            c=self.case();c['source'][field]=value
            with self.subTest(field=field):self.assertEqual(evaluate(c)['decision'],'review')
    def test_close_bound_still_review(self):
        c=self.case();c['source']['runtime']=132
        r=evaluate(c);self.assertEqual(r['decision'],'review');self.assertIn('insufficient_margin',r['reasons'])
    def test_asserted_conflicts_and_local_recheck_still_required(self):
        for outcome in [{'status':'needs_review','reason':'local_identity_conflict'}, {'status':'verified','asserted_imdb':'tt7654321'}, {'status':'verified','asserted_tmdb':2}]:
            c=self.case();r=evaluate(c);r['source']=c['source'];apply_existing_conflict_guard(r,{},outcome)
            self.assertEqual(r['decision'],'review')
    def test_known_conflicting_id_cannot_gain_identity_points(self):
        c=self.case();c['candidates'][1].update(imdb='tt7654321');r=evaluate(c)
        self.assertEqual(r['ranked'][1]['upper_score'],50)
    def test_complete_set_audit_and_original_weights(self):
        c=self.case();c['candidate_set_complete']=True;r=evaluate(c)
        self.assertIsNone(r['rival_bound_audit']['unseen_upper_score'])
        self.assertEqual(r['ranked'][0]['contributions'],{'title':30,'year':20,'runtime':15,'language':10,'source_id':25})
