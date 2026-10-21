from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from research.identity_scoring.fresh import nfo_facts, result, MAX_NFO
from research.identity_scoring.refresh import Budget, atomic

NFO = ('Format : Matroska Duration : 1 h 53 min Movie name : Example Movie (1997) '
       'Encoded date : 2000 Video ID : 1 Format : AVC '+ 'codec detail '*400 +
       ' Audio #1 ID : 2 Duration : 1 h 53 min Title : 5.1 upmix Language : French Default : Yes Forced : No '
       'Audio #2 ID : 3 Duration : 1 h 53 min Title : 2.0 Language : French Default : No Forced : No '
       'Text #1 ID : 4 Duration : 9 min Language : English Default : No')

class FreshTests(unittest.TestCase):
    def setUp(self):
        self.release={'title':'Example Movie','year':1997,'name':'Example Movie 1997 REMUX'}
        self.listing={'reason':'listing_id_found','imdb_id':'tt1234567'}
        self.search={'page':1,'total_pages':1,'total_results':1,'results':[{'id':123}]}
        self.details={123:{'id':123,'title':'Example Movie','release_date':'1997-01-01','runtime':113,
                           'original_language':'fr','spoken_languages':[{'english_name':'French','iso_639_1':'fr'}],
                           'external_ids':{'imdb_id':'tt1234567'}}}
        self.maps={'tt1234567':{'movie_results':[{'id':123}]}}
    def score(self,nfo=NFO):
        return result(self.release,self.listing,nfo,self.search,self.details,self.maps)
    def test_full_nfo_and_two_same_language_tracks(self):
        r=self.score();self.assertGreater(len(NFO),3000)
        self.assertEqual(r['source']['runtime'],113);self.assertEqual(r['source']['language'],'fr')
        self.assertEqual(r['nfo_facts']['audio_tracks'],2)
        self.assertEqual(r['ranked'][0]['score'],100);self.assertEqual(r['selected_id'],123)
        self.assertEqual(r['nfo_facts']['binding'],'exact_listing_nfo_element')
        self.assertFalse(r['nfo_facts']['filename_present'])
    def test_mixed_or_missing_audio_not_assumed_from_catalog(self):
        for nfo in (NFO.replace('Language : French Default : No','Language : English Default : No'),
                    NFO.replace('Language : French Default : No','Default : No'),
                    NFO.replace('Language : French','Language : French / English')):
            self.assertIsNone(self.score(nfo)['source']['language'])
    def test_subtitles_never_count_as_audio_or_runtime(self):
        f=nfo_facts(NFO);self.assertEqual(f['audio_languages'],['french','french']);self.assertEqual(f['runtime'],113)
        f=nfo_facts(NFO.replace('Format : Matroska Duration : 1 h 53 min','Format : Matroska'))
        self.assertIsNone(f['runtime'])
    def test_over_limit_never_parses_truncated_prefix(self):
        r=self.score(NFO+'x'*MAX_NFO)
        self.assertIsNone(r['source']['runtime']);self.assertIsNone(r['source']['language'])
    def test_conflicting_tracker_id_never_identifies(self):
        self.listing['imdb_id']='tt7654321';r=self.score()
        self.assertEqual(r['decision'],'review');self.assertIn('tracker_id_conflict',r['reasons'])
    def test_unchecked_listing_and_conflicting_filename_block(self):
        self.listing['reason']='listing_mismatch';self.assertEqual(self.score()['decision'],'review')
        self.listing['reason']='listing_id_found'
        self.assertEqual(self.score('Complete name : Another Movie.mkv '+NFO)['decision'],'review')
    def test_incomplete_search_and_undetailed_rival_block(self):
        for change in ({'total_pages':2},{'total_results':2,'results':[{'id':123},{'id':456}]}):
            self.search.update(change);self.assertEqual(self.score()['decision'],'review')
    def test_mapping_missing_or_tv_is_not_verified(self):
        for mapping in ({'movie_results':[]},{'movie_results':[{'id':123}],'tv_results':[{'id':4}]}):
            self.maps['tt1234567']=mapping;self.assertIn('crosswalk_unverified',self.score()['reasons'])
    def test_conflicting_nfo_movie_title_or_year_blocks(self):
        for nfo in (NFO.replace('Movie name : Example Movie','Movie name : Other Film'),NFO.replace('(1997)','(1998)')):
            self.assertEqual(self.score(nfo)['decision'],'review')
    def test_budget_persists_failure_reservations_and_auth_stop(self):
        with tempfile.TemporaryDirectory() as folder, patch('research.identity_scoring.refresh.time.sleep'):
            path=Path(folder)/'budget.json';b=Budget(path,lambda:100)
            for _ in range(10):b.reserve('tmdb')
            with self.assertRaises(RuntimeError):b.reserve('tmdb')
            for _ in range(3):
                b=Budget(path,lambda:100)
                for _ in range(10):b.reserve('tmdb')
            with self.assertRaises(RuntimeError):Budget(path,lambda:100).reserve('listing')
            b=Budget(path,lambda:86401);b.cooldown('listing',auth=True)
            with self.assertRaises(RuntimeError):Budget(path,lambda:86402).reserve('listing')
    def test_atomic_only_replaces_own_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'state.json';atomic(p,{'a':1});atomic(p,{'a':2})
            self.assertEqual(json.loads(p.read_text()),{'a':2});self.assertEqual(list(Path(folder).iterdir()),[p])
    def test_refresh_pipeline_captures_full_page_before_projection(self):
        import tracker_metadata
        from research.identity_scoring.refresh import refresh_one
        body='<div id="nfo_text">'+NFO+'</div>'
        def lookup(release,indexer):
            return tracker_metadata.parse_listing(body,release['name'])
        def get(path,params,budget):
            if path=='/search/movie':return self.search
            if path.startswith('/find/'):return self.maps['tt1234567']
            return self.details[123]
        with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{})), \
             patch.object(tracker_metadata,'lookup_listing',side_effect=lookup), \
             patch.object(tracker_metadata,'parse_listing',return_value=self.listing), \
             patch('research.identity_scoring.refresh.metadata_get',side_effect=get):
            r=refresh_one(Path('/unused'),{},type('B',(),{'used':0})())
        self.assertEqual(r['selected_id'],123)
        self.assertGreater(len(r['full_nfo']['nfo']),3000)
        self.assertEqual(r['source']['language'],'fr')

    def test_no_actor_acquisition_imports(self):
        s=Path('research/identity_scoring/refresh.py').read_text()
        for forbidden in ('movie_intel_service','radarr_client','telegram','qbittorrent','download_url'):
            self.assertNotIn(forbidden,s)

if __name__=='__main__':unittest.main()
