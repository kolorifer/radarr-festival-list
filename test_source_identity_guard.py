import copy
import os
import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import source_identity_guard as guard
import movie_intel_service as svc
import tmdb_resolver as tmdb
from torrent_research_evidence import extract
from test_movie_intel_actions import PAYLOAD


def listing(runtime='1 h 33 min', suffix=''):
    evidence=extract(BeautifulSoup('<pre id="nfo_text">film.mkv ---GENERAL---- RUNTIME.........: '+runtime+' ---VIDEO---- Codec: HEVC '+suffix+'</pre>', 'html.parser'))
    return {'source':'torrentleech_listing','reason':'listing_id_found','imdb_id':'tt33498897','torrent_evidence':evidence}


def length_listing(duration='1 h 21 min 59 s 999 ms'):
    evidence=extract(BeautifulSoup('<pre id="nfo_text">General : film.mkv Format : Matroska '
                                  'Length : 14.6 GiB for '+duration+' Video #0 : AVC '
                                  'Duration : 12 min Audio #0 : DTS Length : 12 min</pre>', 'html.parser'))
    return dict(listing(), torrent_evidence=evidence)


class SourceGuardTests(unittest.TestCase):
    def verified(self, runtime):
        return {'identity_status':'verified_tmdb','identity_reason':'external_id_verified',
                'imdb_id':'tt33498897','tmdb_id':1471951,'matched_release_year':'2025',
                'runtime':runtime}

    def test_bounded_variation_accepts_reviewed_patterns(self):
        self.assertFalse(guard.runtime_conflict(listing('1 h 29 min'),self.verified(86)))
        self.assertFalse(guard.runtime_conflict(length_listing(),self.verified(80)))

    def test_variation_enforces_relative_and_absolute_boundaries(self):
        for duration, runtime, conflict in [('84 min',80,False),('84 min 1 s',80,True),
                                           ('125 min',120,False),('125 min 1 s',120,True),
                                           ('76 min',80,False),('75 min 59 s',80,True),
                                           ('115 min',120,False),('114 min 59 s',120,True),
                                           ('13 min',12,False),('14 min',12,True),
                                           ('93 min',12,True),('12 min',93,True)]:
            with self.subTest(duration=duration,runtime=runtime):
                self.assertEqual(guard.runtime_conflict(length_listing(duration),self.verified(runtime)),conflict)

    def test_wider_variation_requires_all_identity_proofs(self):
        for key, bad in [('identity_status','needs_review'),('identity_reason','title_conflict'),
                         ('imdb_id','tt0000002'),('tmdb_id',None),('matched_release_year',None)]:
            meta=self.verified(86);meta[key]=bad
            with self.subTest(key=key):
                self.assertTrue(guard.runtime_conflict(listing('89 min'),meta))
        for key,bad in [('source','unknown'),('reason','listing_mismatch'),('imdb_id',None)]:
            src=listing('89 min');src[key]=bad
            with self.subTest(key=key):
                self.assertTrue(guard.runtime_conflict(src,self.verified(86)))

    def test_approval_rechecks_length_and_approved_variation(self):
        lookup=Mock(return_value=length_listing());resolve=Mock(return_value=self.verified(80))
        self.assertTrue(guard.current(self.action(),lookup,resolve))
        resolve.return_value=self.verified(12)
        self.assertFalse(guard.current(self.action(),lookup,resolve))
        lookup.return_value=length_listing('12 min');resolve.return_value=self.verified(93)
        self.assertFalse(guard.current(self.action(),lookup,resolve))

    def test_real_resolver_and_actor_accept_both_patterns_without_actions(self):
        for observed, canonical, year, runtime, src in [
                ('Garden of Love','Garden of Love',2003,86,listing('89 min')),
                ('Charlie Victor Romeon','Charlie Victor Romeo',2013,80,length_listing())]:
            payload=copy.deepcopy(PAYLOAD)
            payload['data']['release'].update(title=observed,year=year)
            payload['data']['indexer']={'name':'TorrentLeech','identifier':'torrentleech'}
            details={'id':1471951,'title':canonical,'original_title':canonical,
                     'release_date':str(year)+'-01-01','runtime':runtime,
                     'external_ids':{'imdb_id':'tt33498897'}}
            tmdb._ID_CACHE.clear()
            with self.subTest(title=observed), patch.dict(os.environ,{'MOVIE_INTEL_TRACKER_TYPO_ENABLED':'1'}), \
                 patch.object(svc,'INDEX',{}), patch.object(svc,'lookup_listing',return_value=src), \
                 patch.object(tmdb,'_get',side_effect=lambda path,params: {'movie_results':[{'id':1471951}]} if path.startswith('/find/') else details), \
                 patch('verified_identity_cache.get',return_value=None),patch('verified_identity_cache.put'), \
                 patch('identity_memory.observe'),patch('identity_memory.packet',return_value=None), \
                 patch.object(svc,'get_movie_by_tmdb',return_value=None), \
                 patch.object(svc,'create_action') as create,patch.object(svc,'_telegram_request') as send, \
                 patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab:
                context=svc.build_movie_context(payload)
            self.assertEqual(context['meta']['identity_status'],'verified_tmdb')
            self.assertEqual(context['meta']['title'],canonical)
            for call in (create,send,add,grab):call.assert_not_called()

    def test_length_parses_duration_not_file_size_or_tracks(self):
        self.assertAlmostEqual(guard.nfo_runtime(length_listing()), 82, places=4)
        self.assertEqual(guard.nfo_runtime(length_listing('12 min')),12)
        self.assertAlmostEqual(guard.nfo_runtime(length_listing('01:21:59.999')),82,places=4)
        self.assertEqual(guard.nfo_runtime(listing('1 h 29 min')),89)

    def test_length_still_vetoes_short_versus_feature_in_both_directions(self):
        self.assertTrue(guard.runtime_conflict(length_listing('1 h 33 min'), {'runtime':12}))
        self.assertTrue(guard.runtime_conflict(length_listing('12 min'), {'runtime':93}))

    def test_duration_rejects_invalid_or_ambiguous_fields(self):
        for value in ('1 h 60 min', '12 min 60 s', '12 min 1000 ms', '01:60:00', '01:20:60',
                      '25 h 0 min', '0 min', '93 min / 12 min', '93 min Length: 12 min',
                      '12 min 999 s', '1 h 90 min 0 s'):
            with self.subTest(value=value):
                self.assertIsNone(guard.nfo_runtime(length_listing(value)))

    def test_short_film_veto_and_minute_precision(self):
        self.assertTrue(guard.runtime_conflict(listing(), {'runtime':12}))
        for runtime in (92,93,94,None,0,True,'12'):
            self.assertFalse(guard.runtime_conflict(listing(), {'runtime':runtime}))
        self.assertEqual(guard.nfo_runtime(listing()),93)

    def test_mediainfo_general_ignores_track_durations(self):
        evidence=extract(BeautifulSoup('<pre id="nfo_text">General Complete name : film.mkv Duration : 1 h 33 min Video ID : 1 Duration : 12 min Audio ID : 2 Duration : 90 min</pre>','html.parser'))
        self.assertEqual(guard.nfo_runtime({'torrent_evidence':evidence}),93)

    def test_missing_malformed_ambiguous_runtime_does_not_guess(self):
        for value in ({}, {'torrent_evidence':{}}, listing('1 h 93 min'), listing('0 min'),listing('93 min RUNTIME: 12 min')):
            self.assertIsNone(guard.nfo_runtime(value))
        self.assertEqual(guard.nfo_runtime(listing(suffix='RUNTIME: 12 min')),93)

    def test_conflict_removes_poster_links_and_action(self):
        payload=copy.deepcopy(PAYLOAD)
        meta=dict(self.verified(12),identity_source='torrentleech_listing',title='Undertone',year='2025',poster_url='https://image.tmdb.org/wrong.jpg')
        with patch.object(svc,'INDEX',{}),patch.object(svc,'lookup_listing',return_value=listing()),patch.object(svc,'resolve_external_movie',return_value=meta),patch('identity_memory.observe') as observe,patch('identity_memory.packet',return_value=None),patch.object(svc,'get_movie_by_tmdb') as radarr:
            context=svc.build_movie_context(payload)
        self.assertEqual(context['meta']['identity_reason'],'runtime_conflict')
        self.assertIsNone(context['poster_url']);self.assertNotIn('imdb_id',context['meta'])
        self.assertIn('runtime conflicts',context['text']);self.assertNotIn('wrong.jpg',context['text'])
        self.assertEqual(observe.call_args.args[1]['identity_reason'],'runtime_conflict');radarr.assert_not_called()
        with patch.object(svc,'radarr_configured',return_value=True),patch.object(svc,'create_action') as create:
            self.assertIsNone(svc.create_pending_action(payload,context['meta']))
        create.assert_not_called()

    def action(self):
        return {'movie':{'identity_source':'torrentleech_listing','imdb_id':'tt33498897','tmdb_id':1471951},'release':{'title':'Undertone','year':2025},'indexer':{'identifier':'torrentleech'}}

    def test_changed_tracker_id_cannot_reuse_approval(self):
        lookup=Mock(return_value=dict(listing(),imdb_id='tt35892608'));resolve=Mock()
        self.assertFalse(guard.current(self.action(),lookup,resolve))
        self.assertTrue(lookup.call_args.kwargs['force_refresh']);resolve.assert_not_called()

    def test_approval_rechecks_runtime_and_fresh_metadata(self):
        meta={'identity_status':'verified_tmdb','imdb_id':'tt33498897','tmdb_id':1471951,'runtime':12}
        lookup=Mock(return_value=listing());resolve=Mock(return_value=meta)
        self.assertFalse(guard.current(self.action(),lookup,resolve));self.assertTrue(resolve.call_args.kwargs['force_refresh'])
        meta['runtime']=94;self.assertTrue(guard.current(self.action(),lookup,resolve))
        lookup.side_effect=ValueError('unavailable');self.assertFalse(guard.current(self.action(),lookup,resolve))

    def test_legacy_action_does_not_invent_source(self):
        lookup=Mock();resolve=Mock();self.assertTrue(guard.current({'movie':{}},lookup,resolve));lookup.assert_not_called()

    def test_force_refresh_bypasses_both_id_caches(self):
        tmdb._ID_CACHE.clear()
        good={'identity_status':'verified_tmdb','tmdb_id':1471951,'imdb_id':'tt33498897','matched_release_year':'2025'}
        with patch.object(tmdb,'_resolve_external',return_value=good),patch('verified_identity_cache.get',return_value=None),patch('verified_identity_cache.put'):
            tmdb.resolve_external_movie('Undertone',2025,imdb_id='tt33498897')
        with patch.object(tmdb,'_resolve_external',return_value={'identity_status':'needs_review','identity_reason':'identity_conflict'}) as fresh,patch('verified_identity_cache.get') as stored:
            result=tmdb.resolve_external_movie('Undertone',2025,imdb_id='tt33498897',force_refresh=True)
        fresh.assert_called_once();stored.assert_not_called();self.assertEqual(result['identity_status'],'needs_review')

    def test_changed_source_blocks_real_get_and_post_handlers(self):
        import io
        action=self.action()
        for method in ('GET','POST'):
            handler=object.__new__(svc.Handler);handler._html=Mock()
            handler.path='/action/'+'A'*32
            handler.headers={'Content-Length':'35'};handler.rfile=io.BytesIO(b'root_folder=/movies&quality_profile=1')
            with patch.object(svc,'get_action',return_value=action),patch.object(svc,'lookup_listing',return_value=dict(listing(),imdb_id='tt35892608')),patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab,patch.object(svc,'selection_context') as choices,patch.object(svc,'update_action') as update:
                if method=='GET':handler.do_GET()
                else:handler._handle_action_post_locked('A'*32)
            self.assertEqual(handler._html.call_args.args[0],409)
            for call in (add,grab,choices,update):call.assert_not_called()

    def test_service_checks_source_before_acquisition(self):
        with patch.object(svc,'lookup_listing',return_value=dict(listing(),imdb_id='tt35892608')),patch.object(svc,'resolve_external_movie') as resolve:
            self.assertFalse(svc.reviewed_action_current(self.action()))
        resolve.assert_not_called()

    def test_length_short_feature_conflict_blocks_get_and_post(self):
        import io
        for method in ('GET','POST'):
            handler=object.__new__(svc.Handler);handler._html=Mock()
            handler.path='/action/'+'A'*32
            handler.headers={'Content-Length':'35'};handler.rfile=io.BytesIO(b'root_folder=/movies&quality_profile=1')
            with patch.object(svc,'get_action',return_value=self.action()), \
                 patch.object(svc,'lookup_listing',return_value=length_listing('12 min')), \
                 patch.object(svc,'resolve_external_movie',return_value=self.verified(93)), \
                 patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab, \
                 patch.object(svc,'selection_context') as choices,patch.object(svc,'update_action') as update:
                if method=='GET':handler.do_GET()
                else:handler._handle_action_post_locked('A'*32)
            self.assertEqual(handler._html.call_args.args[0],409)
            for call in (add,grab,choices,update):call.assert_not_called()

if __name__=='__main__':unittest.main()
