import copy
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


class SourceGuardTests(unittest.TestCase):
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
        meta={'identity_status':'verified_tmdb','identity_source':'torrentleech_listing','identity_reason':'external_id_verified','imdb_id':'tt33498897','tmdb_id':1471951,'title':'Undertone','year':'2025','runtime':12,'poster_url':'https://image.tmdb.org/wrong.jpg'}
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

if __name__=='__main__':unittest.main()
