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
        r,_=self.pipeline({'Example Movie':dict(self.search,total_pages=2)})
        self.assertIn('candidate_set_incomplete',r['reasons'])
        response=dict(self.search,total_results=21,results=[{'id':i} for i in range(1,22)])
        with self.assertRaisesRegex(RuntimeError,'candidate_capacity'):self.pipeline({'Example Movie':response})

    def test_misleading_alias_cannot_borrow_correct_name(self):
        self.release['title']='Unrelated Movie aka Example Movie'
        empty={'page':1,'total_pages':0,'total_results':0,'results':[]}
        r,_=self.pipeline({'Unrelated Movie':empty,'Example Movie':self.search})
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

    def test_search_alias_support_needs_id_year_and_documented_name(self):
        from research.identity_scoring.scorer import score_candidate
        src={'title':'Romanized Name III aka Example Movie III','year':1993,'imdb':'tt1234567',
             'checked_listing':True,'conflicting_evidence':False,
             'alias_search_support':[{'query':q,'count':1,'ids':[123]} for q in ('Romanized Name III','Example Movie III')]}
        candidate={'id':123,'titles':['Example Movie III'],'years':[1993],'media_type':'movie',
                   'imdb':'tt1234567','crosswalk_verified':True}
        self.assertNotIn('source_alias_not_corroborated',score_candidate(src,candidate)['blocks'])
        for change in ({'imdb':None},{'year':1992},{'checked_listing':False},
                       {'alias_search_support':[{'query':q,'count':1,'ids':[456]} for q in ('Romanized Name III','Example Movie III')]}):
            self.assertIn('source_alias_not_corroborated',score_candidate(dict(src,**change),candidate)['blocks'])
        for change in ({'crosswalk_verified':False},{'titles':['Other Movie III']},{'imdb':'tt7654321'}):
            self.assertIn('source_alias_not_corroborated',score_candidate(src,dict(candidate,**change))['blocks'])

    def test_dotted_nfo_all_tracks_and_explicit_commentary(self):
        nfo=('Example.Movie.1997.REMUX.mkv ---GENERAL---- Size............: 30 GiB '
             'Duration........: 1 h 51 min ---VIDEO---- Duration........: 9 min '
             '---AUDIO---- Title...........: Mono (Cantonese) Language........: Chinese '
             '---AUDIO (#2)---- Title...........: Stereo (Mandarin) Language........: Chinese '
             '---AUDIO (#3)---- Title...........: Surround Language........: English '
             '---AUDIO (#4)---- Title...........: Commentary by Reviewer Language........: English '
             'SUBTITLES.......: French Chapters........: 00:00:00')
        f=nfo_facts(nfo)
        self.assertEqual(f['runtime'],111)
        self.assertEqual(f['audio_languages'],['chinese','chinese','english','english'])
        self.assertEqual(f['audio_tracks'],4)
        self.assertEqual([x['role'] for x in f['audio_track_details']],['unspecified']*3+['commentary'])
        self.assertEqual(f['audio_track_details'][0]['title'],'Mono (Cantonese)')
        r=self.score(nfo)
        self.assertIsNone(r['source']['language']) # no multilingual policy activation
        self.assertEqual(r['ranked'][0]['contributions']['language'],0)
        self.assertTrue(r['nfo_facts']['filename_present'])

    def test_dotted_runtime_must_be_general_and_unique(self):
        for nfo in ('---VIDEO---- Duration........: 1 h 51 min',
                    '---GENERAL---- Duration........: 111 min Duration........: 112 min ---AUDIO---- Language........: French',
                    '---GENERAL---- Size........: 4 GiB ---AUDIO---- Duration........: 111 min'):
            self.assertIsNone(nfo_facts(nfo)['runtime'])

    def test_dotted_missing_duplicate_language_and_wrong_filename(self):
        nfo='Wrong.Movie.mkv ---GENERAL---- Duration........: 113 min ---AUDIO---- Language........: French Language........: English'
        f=nfo_facts(nfo);self.assertEqual(f['audio_languages'],[None])
        self.assertEqual(self.score(nfo)['decision'],'review')
        f=nfo_facts('---GENERAL---- Duration........: 113 min ---AUDIO---- Title........: Track one')
        self.assertEqual(f['audio_track_details'][0]['language'],None)

    def test_media_info_tracks_preserve_commentary_title(self):
        f=nfo_facts(NFO.replace('Title : 2.0','Title : Director commentary'))
        self.assertEqual(f['audio_track_details'][1]['role'],'commentary')
        self.assertEqual(f['audio_track_details'][0]['role'],'unspecified')

    def test_numbered_audio_clock_runtime_and_language_qualifier(self):
        nfo=('Example.Movie.1997.REMUX GENERAL INFO FORMAT : MKV DURATION : 01:53:25 (h:m:s) '
             'VIDEO CODEC : AVC AUDIO (1) CODEC : DTS LANGUAGE : Chinese (Cantonese) CHANNEL(S) : 1.0 '
             'AUDIO (2) CODEC : DTS LANGUAGE : Chinese (Mandarin) CHANNEL(S) : 2.0 '
             'AUDIO (3) CODEC : AC-3 LANGUAGE : English OTHER INFO : Commentary by Reviewer '
             'SUBTITLES French SCREENSHOTS none')
        f=nfo_facts(nfo)
        self.assertAlmostEqual(f['runtime'],113+25/60)
        self.assertEqual(f['audio_tracks'],3)
        self.assertEqual(f['audio_languages'],['chinese','chinese','english'])
        self.assertEqual(f['audio_track_details'][0]['language_detail'],'Cantonese')
        self.assertEqual(f['audio_track_details'][2]['role'],'commentary')
        self.assertEqual(f['filenames'],['Example.Movie.1997.REMUX'])
        self.assertIsNone(nfo_facts(nfo.replace('01:53:25','01:73:25'))['runtime'])

    def test_multilingual_audio_bonus_once_excluding_commentary_and_uncertainty(self):
        from research.identity_scoring.scorer import score_candidate
        candidate={'id':1,'titles':['Example'],'years':[2000],'language':'fr','media_type':'movie',
                   'crosswalk_verified':True,'imdb':'tt1234567'}
        src={'title':'Example','year':2000,'checked_listing':True,'conflicting_evidence':False,'nfo_bound':True}
        for codes,points in ((['fr','en'],10),(['fr','fr'],10),(['en'],0),([],0)):
            self.assertEqual(score_candidate(dict(src,audio_language_codes=codes),candidate)['contributions']['language'],points)
        r=self.score(NFO.replace('Language : French Default : No','Language : English Default : No'))
        self.assertEqual(r['ranked'][0]['contributions']['language'],10)
        r=self.score(NFO.replace('Title : 5.1 upmix','Title : Commentary').replace('Title : 2.0','Title : Commentary'))
        self.assertEqual(r['ranked'][0]['contributions']['language'],0)

    def test_chinese_varieties_need_explicit_labels_and_exclude_auxiliary_audio(self):
        from research.identity_scoring.fresh import map_audio_tracks
        tracks=[{'language':'chinese','language_detail':None,'title':title,'other_info':None,'role':role}
                for title,role in ((None,'unspecified'),('Mono (Cantonese)','unspecified'),('Mandarin','commentary'),('Audio description (Mandarin)','unspecified'))]
        facts={'audio_track_details':tracks}
        self.assertEqual(map_audio_tracks(facts,{'cantonese':{'cn'},'mandarin':{'zh'}}),['cn'])
        self.assertIsNone(tracks[0]['scoring_language_code'])
        conflict={'audio_track_details':[{'language':'english','language_detail':None,'title':'French','role':'unspecified'}]}
        self.assertEqual(map_audio_tracks(conflict,{'english':{'en'},'french':{'fr'}}),[])

    def test_four_candidates_all_visible_and_details_bounded(self):
        rows=[{'id':i,'title':'Example Movie' if i==123 else 'Rival '+str(i),'release_date':'1997-01-01'} for i in (123,124,125,126,127)]
        response=dict(self.search,total_results=5,results=rows)
        for i in (124,125,126,127):
            self.details[i]=dict(self.details[123],id=i,title='Rival '+str(i),external_ids={'imdb_id':'tt7654321'})
        r,calls=self.pipeline({'Example Movie':response})
        self.assertEqual(len(r['ranked']),5)
        self.assertEqual(sum(p.startswith('/movie/') for p,q in calls),4)
        pending=[x for x in r['ranked'] if x.get('evidence_status')=='search_only']
        self.assertEqual(len(pending),1);self.assertEqual(pending[0]['upper_score'],100)
        self.assertEqual(r['decision'],'review');self.assertIn('insufficient_margin',r['reasons'])
        self.assertLessEqual(len(calls)+1,10) # include tracker GET

    def test_alias_intersection_keeps_disagreeing_rivals(self):
        from research.identity_scoring.scorer import score_candidate
        candidate={'id':123,'titles':['Example III'],'years':[1993],'media_type':'movie','imdb':'tt1234567','crosswalk_verified':True}
        src={'title':'Romanized III aka Example III','year':1993,'imdb':'tt1234567','checked_listing':True,'conflicting_evidence':False,
             'alias_search_support':[{'query':'Romanized III','ids':[123,456],'count':2,'complete':True},{'query':'Example III','ids':[123],'count':1,'complete':True}]}
        self.assertNotIn('source_alias_not_corroborated',score_candidate(src,candidate)['blocks'])
        src['alias_search_support'][1].update(ids=[123,456],count=2)
        self.assertIn('source_alias_not_corroborated',score_candidate(src,candidate)['blocks'])

    def test_no_actor_acquisition_imports(self):
        s=Path('research/identity_scoring/refresh.py').read_text()
        for forbidden in ('movie_intel_service','radarr_client','telegram','qbittorrent','download_url'):
            self.assertNotIn(forbidden,s)

if __name__=='__main__':unittest.main()

class CompleteAliasComparisonTests(unittest.TestCase):
    def case(self):
        source={'title':'Romanized II aka Example II','year':1992,'imdb':'tt1234567',
                'runtime':113.4,'audio_language_codes':['cn','en'],'checked_listing':True,
                'conflicting_evidence':False,'nfo_bound':True,
                'alias_search_support':[{'query':q,'ids':[123,456],'count':2,'complete':True}
                    for q in ('Romanized II','Example II')]}
        winner={'id':123,'titles':['Example II'],'years':[1992],'runtime':113,'language':'cn',
                'imdb':'tt1234567','media_type':'movie','crosswalk_verified':True}
        rival=dict(winner,id=456,titles=['Example III'],imdb='tt7654321',crosswalk_verified=False)
        return {'source':source,'candidates':[winner,rival],'candidate_set_complete':True}
    def test_complete_comparison_resolves_alias_without_dropping_rivals(self):
        from research.identity_scoring.scorer import evaluate
        r=evaluate(self.case())
        self.assertEqual(r['selected_id'],123)
        self.assertEqual(r['alias_resolution'],'complete_candidate_comparison')
        self.assertEqual(len(r['ranked']),2)
        self.assertIn('tracker_id_conflict',r['ranked'][1]['blocks'])
    def test_incomplete_or_close_rivals_and_missing_support_stay_blocked(self):
        from research.identity_scoring.scorer import evaluate
        for change in ('incomplete','search_only','runtime','language','close','absent','pagination','omitted'):
            with self.subTest(change=change):
                c=self.case()
                if change=='incomplete':c['candidate_set_complete']=False
                if change=='search_only':c['candidates'][1]['evidence_status']='search_only'
                if change in ('runtime','language'):c['candidates'][1][change]=None
                if change=='close':c['candidates'][1]=dict(c['candidates'][0],id=456)
                if change=='absent':c['source']['alias_search_support'][0].update(ids=[456],count=1)
                if change=='pagination':c['source']['alias_search_support'][0]['complete']=False
                if change=='omitted':c['source']['alias_search_support'][0].update(ids=[123,456,789],count=3)
                self.assertEqual(evaluate(c)['decision'],'review')
    def test_real_conflicts_and_provenance_cannot_be_outscored(self):
        from research.identity_scoring.scorer import evaluate
        for change in ('imdb','source','sequel','crosswalk','binding','unchecked','year','no_runtime','no_audio'):
            with self.subTest(change=change):
                c=self.case()
                if change=='imdb':c['source']['imdb']='tt1111111'
                if change=='source':c['source']['conflicting_evidence']=True
                if change=='sequel':c['source']['title']='Romanized IV aka Example II'
                if change=='crosswalk':c['candidates'][0]['crosswalk_verified']=False
                if change=='binding':c['source']['nfo_bound']=False
                if change=='unchecked':c['source']['checked_listing']=False
                if change=='year':c['source']['year']=1991
                if change=='no_runtime':c['source']['runtime']=None
                if change=='no_audio':c['source']['audio_language_codes']=[]
                self.assertEqual(evaluate(c)['decision'],'review')
    def test_only_title_conflict_clears_and_asserted_ids_are_checked(self):
        from research.identity_scoring.scorer import evaluate
        from research.identity_scoring.refresh import apply_existing_conflict_guard
        for reason,ids,accepted in [('title_conflict',{},True),('id_conflict',{},False),
                (None,{},False),('title_conflict',{'asserted_imdb':'tt1111111'},False),
                ('title_conflict',{'asserted_tmdb':456},False),
                ('title_conflict',{'asserted_imdb':'tt1234567','asserted_tmdb':123},True)]:
            c=self.case();r=evaluate(c);r['source']=c['source']
            apply_existing_conflict_guard(r,{},dict(status='needs_review',reason=reason,**ids))
            self.assertEqual(r['decision']=='would_identify',accepted)
        c=self.case();r=evaluate(c);r['source']=c['source'];r['selected_id']=None;r['decision']='review'
        apply_existing_conflict_guard(r,{'tmdb':456},{})
        self.assertIn('existing_identity_conflict_requires_review',r['reasons'])
