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

    def test_research_envelope_version_binds_collector_provenance(self):
        import sqlite3
        from contextlib import closing
        from identity_triage_store import digest
        from research.identity_scoring.refresh import exact_release
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            for sub in ('.local/state/movie-identity-triage','.local/state/movie-identity-research','.apps/autobrr'):
                (home/sub).mkdir(parents=True)
            meta=dict(self.release,source='torrentleech',release_key_basis='external_id')
            material={'metadata':meta,'route':'eligible','correlation':'strong_source_id','outcome':{}}
            with closing(sqlite3.connect(home/'.local/state/movie-identity-triage/inbox.sqlite3')) as c:
                c.executescript('create table selection_current(case_key text,version text,release text); create table selection_history(version text,material text);')
                c.execute('insert into selection_current values (?,?,?)',('case','collector-version',digest(['torrentleech','torrent',['external','123']])))
                c.execute('insert into selection_history values (?,?)',('collector-version',json.dumps(material)));c.commit()
            with closing(sqlite3.connect(home/'.local/state/movie-identity-research/recurring-v1.sqlite3')) as c:
                c.execute('create table evidence(version text,case_id text,material text)')
                c.execute('insert into evidence values (?,?,?)',('research-version','case',json.dumps({'provenance':[{'source':'stage1_outcome','digest':'collector-version'}]})));c.commit()
            with closing(sqlite3.connect(home/'.apps/autobrr/autobrr.db')) as c:
                c.execute('create table release(torrent_id integer,info_url text,torrent_name text,year integer)')
                c.execute('insert into release values (?,?,?,?)',(123,'https://www.torrentleech.org/torrent/123',self.release['name'],1997));c.commit()
            release,_=exact_release(home,{'case_id':'case','version':'research-version'})
            self.assertEqual(release['name'],self.release['name'])
            with self.assertRaisesRegex(RuntimeError,'occurrence_changed'):
                exact_release(home,{'case_id':'case','version':'wrong-version'})

    def pipeline(self, responses, listing=None):
        import tracker_metadata
        from research.identity_scoring.refresh import refresh_one
        calls=[]
        def get(path,params,budget):
            calls.append((path,params))
            if path=='/search/movie':return responses[params['query']]
            if path.startswith('/find/'):return self.maps['tt1234567']
            return self.details[int(path.rsplit('/',1)[-1])]
        with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{})), \
             patch.object(tracker_metadata,'lookup_listing',side_effect=lambda r,i:tracker_metadata.parse_listing('<div id="nfo_text">'+NFO+'</div>',r['name'])), \
             patch.object(tracker_metadata,'parse_listing',return_value=listing or self.listing), \
             patch('research.identity_scoring.refresh.metadata_get',side_effect=get):
            return refresh_one(Path('/unused'),{},type('B',(),{'used':0})()),calls

    def test_alias_queries_merge_duplicates_and_score_supported_aliases(self):
        self.release['title']='Alternate Name aka Example Movie'
        self.details[123]['alternative_titles']={'titles':[{'title':'Alternate Name'}]}
        r,calls=self.pipeline({'Alternate Name':self.search,'Example Movie':self.search})
        self.assertEqual(r['selected_id'],123)
        self.assertEqual(r['ranked'][0]['contributions']['title'],30)
        self.assertEqual(sum(p=='/movie/123' for p,q in calls),1)
        self.assertEqual([q['query'] for p,q in calls if p=='/search/movie'],['Alternate Name','Example Movie'])

    def test_imdb_candidate_survives_complete_empty_title_search(self):
        empty={'page':1,'total_pages':0,'total_results':0,'results':[]}
        r,calls=self.pipeline({'Example Movie':empty})
        self.assertEqual(r['selected_id'],123)
        self.assertTrue(calls[0][0].startswith('/find/'))

    def test_missing_id_and_empty_search_stays_unresolved(self):
        empty={'page':1,'total_pages':0,'total_results':0,'results':[]}
        with self.assertRaisesRegex(RuntimeError,'candidate_search_empty'):
            self.pipeline({'Example Movie':empty},{'reason':'listing_id_missing'})

    def test_partial_and_oversized_search_cannot_hide_rivals(self):
        for response,reason in ((dict(self.search,total_pages=2),'candidate_search_incomplete'),
                                (dict(self.search,total_results=4,results=[{'id':i} for i in range(1,5)]),'candidate_capacity')):
            with self.assertRaisesRegex(RuntimeError,reason):self.pipeline({'Example Movie':response})

    def test_misleading_alias_cannot_borrow_correct_name(self):
        self.release['title']='Unrelated Movie aka Example Movie'
        r,_=self.pipeline({'Unrelated Movie':self.search,'Example Movie':self.search})
        self.assertEqual(r['decision'],'review')
        self.assertIn('source_alias_not_corroborated',r['reasons'])

    def test_aliases_preserve_sequel_numbers(self):
        from research.identity_scoring.scorer import score_candidate,source_titles
        candidate={'id':1,'titles':['Wong Fei Hung II','Once Upon a Time in China II'],
                   'media_type':'movie','crosswalk_verified':True,'imdb':'tt0105839'}
        src={'title':'Wong Fei Hung II aka Once Upon a Time in China II','checked_listing':True,'conflicting_evidence':False}
        self.assertEqual(score_candidate(src,candidate)['contributions']['title'],30)
        src['title']='Wong Fei Hung III aka Once Upon a Time in China III'
        self.assertEqual(score_candidate(src,candidate)['contributions']['title'],-30)
        src['title']='Wong Fei Hung II aka Once Upon a Time in China III'
        self.assertIn('source_alias_sequel_conflict',score_candidate(src,candidate)['blocks'])
        self.assertEqual(source_titles('A / B'),['A / B'])
        self.assertEqual(source_titles('A aka B aka C'),['A aka B aka C'])

    def test_no_actor_acquisition_imports(self):
        s=Path('research/identity_scoring/refresh.py').read_text()
        for forbidden in ('movie_intel_service','radarr_client','telegram','qbittorrent','download_url'):
            self.assertNotIn(forbidden,s)

if __name__=='__main__':unittest.main()
