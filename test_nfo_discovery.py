import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.identity_scoring.fresh import nfo_facts,nfo_search_title,build_case
from research.identity_scoring.refresh import (refresh_one,listing_diagnostic,attempt_refresh,
    Budget,atomic,EVIDENCE_REVISION,CHECKPOINT_REVISION)

class NfoDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.release={'title':'Misspelt Hotel','year':1979,'name':'Misspelt Hotel 1979 REMUX'}
        self.listing={'reason':'listing_id_missing'}
        self.nfo='File Name....: Misspelt Hotel 1979 REMUX.mkv General Title : Algne Hotell File size : 23 GiB Format : Matroska Duration : 1 h 23 min Video ID : 1 Audio ID : 2 Title : Stereo Language : German Default : Yes Forced : No ID : 3 Title : Stereo Language : Estonian Default : No Forced : No Text Language : English, German'
        self.detail={'id':123,'title':'Misspelled Hotel','original_title':'Algne Hotell','release_date':'1979-01-01','runtime':84,'original_language':'et','spoken_languages':[{'english_name':'Estonian','iso_639_1':'et'},{'english_name':'German','iso_639_1':'de'}],'external_ids':{'imdb_id':'tt1234567'}}
        self.search={'page':1,'total_pages':1,'total_results':1,'results':[{'id':123,'title':'Misspelled Hotel','original_title':'Algne Hotell','release_date':'1979-01-01'}]}
        self.empty={'page':1,'total_pages':0,'total_results':0,'results':[]}

    def test_unumbered_subtitle_boundary_keeps_both_audio_languages(self):
        f=nfo_facts(self.nfo)
        self.assertEqual(f['audio_languages'],['german','estonian'])
        self.assertEqual(f['container_titles'],['Algne Hotell'])
        case,_=build_case(self.release,self.listing,self.nfo,self.search,{123:self.detail},{})
        self.assertEqual(case['source']['audio_language_codes'],['de','et'])
        self.assertEqual(case['source']['title'],'Misspelt Hotel')
        self.assertEqual(nfo_search_title(self.release,self.listing,self.nfo),'Algne Hotell')

    def test_hint_requires_single_bound_filename_and_nonconflicting_title_year(self):
        for nfo in [self.nfo.replace('Misspelt Hotel 1979 REMUX.mkv','Other Film.mkv'),
                    self.nfo.replace('File Name....: Misspelt Hotel 1979 REMUX.mkv ',''),
                    self.nfo.replace('Algne Hotell','Algne Hotell (1980)'),
                    self.nfo.replace('Algne Hotell','[redacted]'),
                    self.nfo.replace('Algne Hotell','https://secret.invalid/token'),
                    self.nfo.replace('Algne Hotell','a'*257),
                    self.nfo.replace('File size :','Title : Different Film File size :')]:
            self.assertIsNone(nfo_search_title(self.release,self.listing,nfo),nfo[:80])
        for reason in ['listing_mismatch','listing_id_conflict','login_required']:
            self.assertIsNone(nfo_search_title(self.release,{'reason':reason},self.nfo))
        self.assertIsNone(nfo_search_title(self.release,self.listing,self.nfo.replace('Algne Hotell','Misspelt Hotel')))
        self.assertEqual(nfo_search_title(self.release,self.listing,self.nfo.replace('Algne Hotell','Algne Hotell (1979)')),'Algne Hotell')

    def pipeline(self, initial_empty=True):
        import tracker_metadata
        calls=[]
        def get(path,params,budget):
            calls.append((path,params))
            if path=='/search/movie':return self.empty if params['query']==self.release['title'] and initial_empty else self.search
            if path.startswith('/find/'):return {'movie_results':[{'id':123}]}
            return self.detail
        with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{})), \
             patch.object(tracker_metadata,'lookup_listing',side_effect=lambda r,i:tracker_metadata.parse_listing('<div id="nfo_text">'+self.nfo+'</div>',r['name'])), \
             patch.object(tracker_metadata,'parse_listing',return_value=self.listing), \
             patch('research.identity_scoring.refresh.metadata_get',side_effect=get):
            result=refresh_one(Path('/unused'),{},type('B',(),{'used':0})())
        return result,calls

    def test_empty_search_uses_one_bound_nfo_title_and_keeps_original_audit(self):
        result,calls=self.pipeline()
        queries=[q for p,q in calls if p=='/search/movie']
        self.assertEqual([q['query'] for q in queries],['Misspelt Hotel','Algne Hotell'])
        self.assertEqual(queries[1]['year'],1979)
        self.assertEqual([s['count'] for s in result['candidate_searches']],[0,1])
        self.assertEqual(result['ranked'][0]['candidate_id'],123)
        self.assertEqual(result['source']['title'],'Misspelt Hotel')
        self.assertIsNone(result['source']['imdb'])
        self.assertEqual(result['ranked'][0]['contributions']['source_id'],0)
        self.assertEqual(result['discovery_scope']['nfo_title_fallback']['basis'],'exact_bound_container_title')
        self.assertEqual(len(calls),4)

    def test_existing_candidates_do_not_cause_extra_nfo_search(self):
        result,calls=self.pipeline(False)
        self.assertEqual(sum(p=='/search/movie' for p,q in calls),1)
        self.assertNotIn('nfo_title_fallback',result['discovery_scope'])

    def test_two_empty_alias_queries_plus_one_fallback_stay_bounded(self):
        self.release['title']='Misspelt Hotel aka Other Transliteration'
        # pipeline mock returns empty only for the full title; replace with explicit mock.
        import tracker_metadata
        calls=[]
        def get(path,params,budget):
            calls.append((path,params))
            if path=='/search/movie':return self.search if params['query']=='Algne Hotell' else self.empty
            if path.startswith('/find/'):return {'movie_results':[{'id':123}]}
            return self.detail
        with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{})), \
             patch.object(tracker_metadata,'lookup_listing',side_effect=lambda r,i:tracker_metadata.parse_listing('<div id="nfo_text">'+self.nfo+'</div>',r['name'])), \
             patch.object(tracker_metadata,'parse_listing',return_value=self.listing), \
             patch('research.identity_scoring.refresh.metadata_get',side_effect=get):
            result=refresh_one(Path('/unused'),{},type('B',(),{'used':0})())
        self.assertEqual([q['query'] for p,q in calls if p=='/search/movie'],['Misspelt Hotel','Other Transliteration','Algne Hotell'])
        self.assertEqual(result['decision'],'review') # NFO lead cannot bypass alias corroboration.

    def test_heading_diagnostic_is_bounded_redacted_and_never_accepts_mismatch(self):
        html='<h2 id="torrentnameid">Different Release <span class="new label labelfreeleech">FREELEECH</span></h2><input id="torrentName" value="https://private.invalid/x token secret">'
        d=listing_diagnostic(html,'Expected Release')
        self.assertEqual(d['observed_headings'][0],'Different Release')
        self.assertTrue(d['diagnostic_only']);self.assertEqual(d['heading_count'],2)
        self.assertNotIn('private.invalid',json.dumps(d));self.assertNotIn('secret',json.dumps(d))
        d=listing_diagnostic('<h2 id="torrentnameid">'+'x '*500+'</h2>','x '*500)
        self.assertLessEqual(len(d['expected']),256);self.assertLessEqual(len(d['observed_headings'][0]),256)
        import tracker_metadata
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);budget=Budget(home/'budget');saved={};ledger=home/'ledger'
            def lookup(r,i):
                budget.reserve('listing')
                return tracker_metadata.parse_listing(html,r['name'])
            with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{})), \
                 patch.object(tracker_metadata,'lookup_listing',side_effect=lookup), \
                 patch('research.identity_scoring.refresh.metadata_get') as get, \
                 patch('research.identity_scoring.refresh.time.sleep'):
                attempt_refresh(home,{'key':'one'},saved,ledger,budget,100)
            self.assertEqual(saved['one']['error'],'listing_mismatch')
            self.assertEqual(saved['one']['listing_diagnostic']['observed_headings'][0],'Different Release')
            self.assertNotIn('fresh',saved['one']);get.assert_not_called()

    def test_parser_upgrade_preserves_compatible_partial_response_cache(self):
        self.assertNotEqual(EVIDENCE_REVISION,CHECKPOINT_REVISION)
        progress={'revision':CHECKPOINT_REVISION,'started':100,'listing':self.listing,'captured':{'nfo':self.nfo},'metadata':{}}
        # Mapping/search caches remain valid; deliberately fail only the uncached GET.
        with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{})), \
             patch('research.identity_scoring.refresh.time.time',return_value=200), \
             patch('tracker_metadata.lookup_listing') as listing, \
             patch('research.identity_scoring.refresh.metadata_get',side_effect=RuntimeError('shadow_request_budget')):
            with self.assertRaisesRegex(RuntimeError,'shadow_request_budget'):
                refresh_one(Path('/unused'),{},None,progress)
            listing.assert_not_called()
        self.assertEqual(progress['started'],100)

if __name__=='__main__':unittest.main()
