import copy
import json
import os
import unittest
from unittest.mock import Mock,patch
from torrent_research_evidence import fingerprint
import torrent_evidence_identity as rule

class EvidenceIdentityTests(unittest.TestCase):
    def setUp(self):
        rule._CACHE.clear();rule._UNTIL=0
        p=patch.dict(os.environ,{rule.FLAG:'1'});p.start();self.addCleanup(p.stop)
        text='General Complete name : Alias.Film.2023.WEB.mkv Format : Matroska Duration : 1 h 44 min Video ID : 1 Duration : 1 h 44 min Audio ID : 2 Duration : 1 h 44 min Language : Malayalam (IN) Default : Yes Text ID : 3 Duration : 1 h 40 min Language : English Default : No'
        self.evidence={'version':1,'description':{'text':'','digest':fingerprint('')},'nfo':{'text':text,'digest':fingerprint(text)},'images':[],'unavailable_images':0,'truncated':True}
        self.listing={'reason':'listing_id_missing','source':'torrentleech_listing','torrent_evidence':self.evidence}
        self.release={'name':'Alias Film 2023 WEB','title':'Alias Film','year':2023,'info_url':'https://www.torrentleech.org/torrent/1'}
        self.indexer={'identifier':'torrentleech'}
        self.details={'id':123,'title':'Canonical Film','original_title':'Original Film','release_date':'2022-12-11','runtime':104,'original_language':'ml','spoken_languages':[{'iso_639_1':'ml','english_name':'Malayalam'}],'external_ids':{'imdb_id':'tt1234567','wikidata_id':'Q123'},'alternative_titles':{'titles':[{'title':'Alias Film'}]},'release_dates':{'results':[]}}
        self.search={'page':1,'total_pages':1,'total_results':1,'results':[{'id':123}]}
        self.mapping={'movie_results':[{'id':123}]}
        self.get=Mock(side_effect=lambda path,params:self.search if path=='/search/movie' else self.mapping if path.startswith('/find/') else self.details)
        self.dates=Mock(return_value={'2022','2023'})
    def resolve(self):return rule.resolve(self.release,self.indexer,self.listing,self.get,self.dates)
    def text(self,value):self.evidence['nfo']={'text':value,'digest':fingerprint(value)}
    def test_alias_runtime_language_and_crosslinked_date_agree(self):
        result=self.resolve();self.assertEqual(result['tmdb_id'],123);self.assertEqual(result['matched_release_year'],'2023');self.assertEqual(result['identity_year_basis'],'wikidata_crosslinked_release_dates')
        self.assertEqual(rule.nfo_facts(self.evidence),{'runtime':104,'language':'malayalam'})
        self.dates.assert_called_once_with('Q123','tt1234567',123)
    def test_tmdb_release_year_needs_no_secondary_lookup(self):
        self.details['release_dates']={'results':[{'release_dates':[{'release_date':'2023-08-18'}]}]}
        self.assertIsNotNone(self.resolve());self.dates.assert_not_called()
    def test_missing_or_conflicting_source_id_never_overridden(self):
        for reason in ('listing_id_conflict','listing_id_found','listing_mismatch','login_required'):
            self.listing['reason']=reason;self.assertIsNone(self.resolve())
        self.listing['reason']='listing_id_missing';self.release['meta_imdb']='tt9999999';self.assertIsNone(self.resolve());self.get.assert_not_called()
    def test_incomplete_oversized_or_duplicate_search_stays_unresolved(self):
        for change in ({'total_pages':2},{'total_results':2},{'results':[]},{'results':[{'id':123},{'id':123}],'total_results':2}):
            rule._CACHE.clear();self.search.update(change);self.assertIsNone(self.resolve())
    def test_two_supported_candidates_are_not_ranked(self):
        self.search.update(total_results=2,results=[{'id':123},{'id':124}])
        def get(path,params):
            if path=='/search/movie':return self.search
            if path.startswith('/movie/'):return self.details|{'id':int(path.rsplit('/',1)[1]),'external_ids':{'imdb_id':'tt1234567' if path.endswith('123') else 'tt7654321','wikidata_id':'Q123'}}
            return {'movie_results':[{'id':123 if 'tt1234567' in path else 124}]}
        self.get.side_effect=get;self.assertIsNone(self.resolve())
    def test_missing_imdb_runtime_language_or_alias_rejected(self):
        original=copy.deepcopy(self.details)
        for change in ({'external_ids':{}},{'runtime':105},{'original_language':'en'},{'alternative_titles':{}},{'spoken_languages':[]}):
            rule._CACHE.clear();self.details=original|change;self.assertIsNone(self.resolve())
    def test_year_not_assumed_from_filename_or_tolerance(self):
        self.dates.return_value={'2022'};self.assertIsNone(self.resolve())
    def test_mapping_ambiguity_tv_or_mismatch_rejected(self):
        for data in (None,{'movie_results':[{'id':124}]},{'movie_results':[{'id':123},{'id':124}]},{'movie_results':[{'id':123}],'tv_results':[{}]}):
            rule._CACHE.clear();self.mapping=data;self.assertIsNone(self.resolve())
    def test_nfo_subtitle_runtime_not_used_multiaudio_and_truncation_refused(self):
        original=self.evidence['nfo']['text']
        for text in (original.replace('General','Other'),original.replace('Audio ID : 2','Audio ID : 2 Audio ID : 4'),original.replace('Language : Malayalam (IN)','Language : Unknown (IN)'),original.replace('1 h 44 min','1 h 45 min'),original+'a'*3000):
            rule._CACHE.clear();self.text(text);self.assertIsNone(self.resolve())
    def entity(self):
        def claim(value):return {'rank':'normal','mainsnak':{'snaktype':'value','datavalue':{'value':value}}}
        return {'entities':{'Q123':{'id':'Q123','type':'item','claims':{'P345':[claim('tt1234567')],'P4947':[claim('123')],'P577':[claim({'time':'+2023-08-18T00:00:00Z','precision':11,'before':0,'after':0,'calendarmodel':'http://www.wikidata.org/entity/Q1985727'})]}}}}
    def test_secondary_date_binds_both_ids_and_rejects_uncertain_claims(self):
        entity=self.entity();self.assertEqual(rule.release_years(entity,'Q123','tt1234567',123),{'2023'})
        self.assertEqual(rule.release_years(entity,'Q123','tt9999999',123),set())
        self.assertEqual(rule.release_years(entity,'Q123','tt1234567',124),set())
        claim=entity['entities']['Q123']['claims']['P577'][0];claim['mainsnak']['datavalue']['value']['after']=1
        self.assertEqual(rule.release_years(entity,'Q123','tt1234567',123),set())
        claim['mainsnak']['datavalue']['value']['after']=0;claim['rank']='deprecated';self.assertEqual(rule.release_years(entity,'Q123','tt1234567',123),set())
    def test_fixed_public_endpoint_no_auth_and_bounded_read(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock();response.read.return_value=json.dumps(self.entity()).encode()
        with patch.object(rule,'urlopen',return_value=response) as transport,patch.object(rule,'reserve') as reserve:
            self.assertEqual(rule.wikidata_years('Q123','tt1234567',123),{'2023'})
            req=transport.call_args.args[0];self.assertEqual(req.full_url,'https://www.wikidata.org/wiki/Special:EntityData/Q123.json');self.assertIsNone(req.get_header('Authorization'));response.read.assert_called_once_with(1048577);reserve.assert_called_once_with('tmdb')
            self.assertEqual(rule.wikidata_years('https://evil.invalid','tt1234567',123),set());self.assertEqual(transport.call_count,1)
    def test_cached_success_cannot_bypass_switch_or_changed_evidence(self):
        self.assertIsNotNone(self.resolve());count=self.get.call_count;self.assertIsNotNone(self.resolve());self.assertEqual(self.get.call_count,count)
        with patch.dict(os.environ,{rule.FLAG:'0'}):self.assertIsNone(self.resolve())
        self.text(self.evidence['nfo']['text'].replace('1 h 44 min','1 h 45 min'));self.assertIsNone(self.resolve())
    def test_actor_still_requires_download_confirmation_and_revalidation(self):
        import movie_intel_service as svc
        target=self.resolve();payload={'data':{'release':self.release,'indexer':self.indexer,'result':{'rejections':['Unknown Movie']}}}
        with patch.object(svc,'lookup_listing',return_value=self.listing),patch.object(svc,'find_local',return_value=None),patch.object(svc,'get_movie_by_tmdb',return_value={}),patch.object(rule,'resolve',return_value=target),patch.object(svc,'decision_log'),patch.object(svc,'create_action') as create,patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab,patch.object(svc,'_telegram_request') as notify:
            context=svc.build_movie_context(payload);self.assertEqual(context['meta']['identity_source'],'torrent_evidence')
            for mock in (create,add,grab,notify):mock.assert_not_called()
        action={'movie':target,'release':self.release,'indexer':self.indexer}
        with patch.object(svc,'build_movie_context',return_value=context):self.assertTrue(svc.reviewed_action_current(action))
        with patch.object(svc,'build_movie_context',return_value={'meta':{'identity_status':'unresolved'}}):self.assertFalse(svc.reviewed_action_current(action))
    def test_failed_evidence_revalidation_stops_before_remote_writes(self):
        import movie_intel_service as svc
        target=self.resolve();handler=object.__new__(svc.Handler);handler._html=Mock()
        with patch.object(svc,'get_action',return_value={'movie':target,'release':self.release,'indexer':self.indexer}),patch.object(svc,'build_movie_context',return_value={'meta':None}),patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab,patch.object(svc,'update_action') as update:
            handler._handle_action_post_locked('synthetic')
        self.assertEqual(handler._html.call_args.args[0],409)
        for mock in (add,grab,update):mock.assert_not_called()

    def test_incomplete_competing_candidate_aborts_instead_of_selecting_first(self):
        self.search.update(total_results=2,results=[{'id':123},{'id':124}])
        original=self.get.side_effect
        self.get.side_effect=lambda path,params:None if path=='/movie/124' else original(path,params)
        self.assertIsNone(self.resolve())
    def test_action_retains_evidence_marker(self):
        import movie_intel_service as svc
        target=self.resolve();release=self.release|{'download_url':'https://synthetic.invalid/file','external_id':'1'}
        payload={'data':{'release':release,'indexer':self.indexer,'result':{'rejections':['Unknown Movie']}}}
        with patch.object(svc,'radarr_configured',return_value=True),patch.object(svc,'build_release_push'),patch.object(svc,'create_action',return_value='synthetic') as create,patch.object(svc,'decision_log'):
            self.assertEqual(svc.create_pending_action(payload,target),'synthetic')
        self.assertEqual(create.call_args.args[0]['movie']['identity_evidence'],target['identity_evidence'])
    def test_local_catalog_conflict_cannot_accept_inference(self):
        import movie_intel_service as svc
        target=self.resolve();payload={'data':{'release':self.release,'indexer':self.indexer,'result':{'rejections':['Unknown Movie']}}}
        with patch.object(svc,'lookup_listing',return_value=self.listing),patch.object(svc,'find_local',side_effect=[None,{'imdb_id':'tt9999999'}]),patch.object(rule,'resolve',return_value=target),patch.object(svc,'decision_log'):
            result=svc.build_movie_context(payload)
        self.assertEqual(result['meta']['identity_reason'],'local_identity_conflict')
    def test_secondary_provider_rejection_respects_shared_cooldown(self):
        from urllib.error import HTTPError
        with patch.object(rule,'urlopen',side_effect=HTTPError('https://www.wikidata.org/',429,'limited',{'Retry-After':'120'},None)),patch.object(rule,'reserve'),patch.object(rule,'cooldown') as cooldown:
            self.assertEqual(rule.wikidata_years('Q123','tt1234567',123),set())
            cooldown.assert_called_once_with('tmdb',120)
        with patch.object(rule,'urlopen') as transport:
            self.assertEqual(rule.wikidata_years('Q123','tt1234567',123),set());transport.assert_not_called()

    def test_nfo_for_another_release_cannot_supply_supporting_facts(self):
        self.text(self.evidence['nfo']['text'].replace('Alias.Film.2023.WEB.mkv','Other.Film.2023.WEB.mkv'))
        self.assertIsNone(self.resolve());self.get.assert_not_called()
