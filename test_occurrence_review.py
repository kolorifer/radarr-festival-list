import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from bs4 import BeautifulSoup
import occurrence_review as review
import movie_intel_service as svc
import pending_actions as store
from test_torrent_research_evidence import PAGE
from torrent_research_evidence import extract

class OccurrenceReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        p=patch.object(store,'STORE_PATH',Path(self.temp.name)/'actions.json');p.start();self.addCleanup(p.stop)
        self.release={'name':'A Film 1940 BluRay','title':'A Film','year':1940,'external_id':'1','info_url':'https://www.torrentleech.org/torrent/1','download_url':'https://private.invalid/secret','protocol':'torrent'}
        self.indexer={'name':'TorrentLeech','identifier':'torrentleech'}
        self.listing={'reason':'listing_id_found','source':'torrentleech_listing','imdb_id':'tt1234567','torrent_evidence':extract(BeautifulSoup(PAGE,'html.parser'))}
        self.meta={'identity_status':'needs_review','identity_source':'torrentleech_listing','identity_reason':'year_conflict'}
        self.context={'category':'unknown_movie','meta':self.meta,'review_listing':self.listing}
        self.payload={'data':{'release':self.release,'indexer':self.indexer,'result':{'rejections':['Unknown Movie']}}}
        self.target={'identity_status':'verified_tmdb','identity_reason':'external_id_verified','imdb_id':'tt7654321','tmdb_id':123,'title':'A Film','year':'1940'}
    def offer(self):return svc.create_identity_review(self.payload,self.context)
    def post(self,token,body):
        handler=object.__new__(svc.Handler);handler._html=Mock();handler.headers={'Content-Length':str(len(body))};handler.rfile=io.BytesIO(body.encode())
        with patch.object(svc,'lookup_listing',return_value=self.listing),patch.object(svc,'resolve_external_movie',return_value=self.target),patch.object(svc,'find_local',return_value=None),patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab,patch.object(svc,'_telegram_request') as telegram:
            handler._handle_action_post_locked(token)
            for m in (add,grab,telegram):m.assert_not_called()
        return handler
    def test_repeated_same_torrent_requires_new_choice(self):
        first=self.offer();self.post(first,'imdb=tt7654321&tmdb=123&confirm_identity=yes')
        second=self.offer();self.assertNotEqual(first,second);self.assertFalse(store.get_action(second).get('chosen'))
    def test_choice_only_no_download_offer_created(self):
        token=self.offer()
        with patch.object(svc,'create_pending_action') as acquire:
            handler=self.post(token,'imdb=tt7654321&tmdb=123&confirm_identity=yes')
        acquire.assert_not_called();self.assertEqual(handler._html.call_args.args[0],200)
        self.assertTrue(store.get_action(token)['chosen']);self.assertIn('No download started',handler._html.call_args.args[1])
    def test_confirmation_and_valid_ids_required(self):
        for body in ('imdb=tt7654321&tmdb=123','imdb=bad&tmdb=123&confirm_identity=yes','imdb=tt7654321&tmdb=123&confirm_identity=yes&other=yes','imdb=tt7654321&tmdb=123&tmdb=124&confirm_identity=yes'):
            token=self.offer();h=self.post(token,body);self.assertEqual(h._html.call_args.args[0],409);self.assertFalse(store.get_action(token).get('chosen'))
    def test_changed_evidence_and_mapping_fail(self):
        action=store.get_action(self.offer());changed=copy.deepcopy(self.listing);changed['imdb_id']='tt9999999'
        resolver=Mock(return_value=self.target)
        with self.assertRaises(ValueError):review.verified_target(action,'tt7654321',123,Mock(return_value=changed),resolver)
        resolver.assert_not_called()
        for change in ({'identity_status':'needs_review'},{'tmdb_id':124},{'imdb_id':'tt9999999'}):
            with self.assertRaises(ValueError):review.verified_target(action,'tt7654321',123,Mock(return_value=self.listing),Mock(return_value=self.target|change))
    def test_native_ids_invalid_listing_other_reasons_stay_blocked(self):
        self.release['meta_imdb']='tt1234567';self.assertIsNone(self.offer());self.release.pop('meta_imdb')
        for reason in ('invalid_external_id','local_identity_conflict','listing_id_conflict'):
            self.context['meta']=self.meta|{'identity_reason':reason};self.assertIsNone(self.offer())
    def test_render_evidence_without_private_references(self):
        action=store.get_action(self.offer())
        with patch.object(review,'candidates',return_value=[]):text=review.render(action)
        self.assertIn('NFO',text);self.assertIn('1940',text);self.assertIn('tt1234567',text)
        self.assertNotIn('private.invalid',text);self.assertNotIn('torrentleech.org',text)
        self.assertIn('No matching research proposal',text)
    def test_render_candidate_and_missing_evidence(self):
        action=store.get_action(self.offer())
        row={'candidate':{'record':{'id':123,'imdb':'tt7654321','title':'<script>','date':'1940','runtime':100,'directors':['Director']},'support_gaps':['screenshot_visual_review_pending']},'current':False}
        with patch.object(review,'candidates',return_value=[row]):text=review.render(action)
        self.assertNotIn('<script>',text);self.assertIn('Historical research',text);self.assertIn('screenshot_visual_review_pending',text);self.assertIn('name="tmdb" value="123"',text)
    def test_selected_occurrence_must_exist_and_match_at_acquisition(self):
        token=self.offer();self.post(token,'imdb=tt7654321&tmdb=123&confirm_identity=yes')
        action={'release':self.release,'indexer':self.indexer,'movie':self.target|{'identity_choice':{'review_token':token}}}
        with patch.object(svc,'lookup_listing',return_value=self.listing),patch.object(svc,'resolve_external_movie',return_value=self.target),patch.object(svc,'find_local',return_value=None):self.assertTrue(svc.reviewed_action_current(action))
        store.delete_action(token);self.assertFalse(svc.reviewed_action_current(action))
    def test_expired_review_is_gone(self):
        token=self.offer();store.update_action(token,expires_at=0);h=self.post(token,'imdb=tt7654321&tmdb=123&confirm_identity=yes')
        self.assertEqual(h._html.call_args.args[0],410)
    def test_past_approval_cannot_change_fresh_context(self):
        with patch.object(svc,'find_local',return_value=None),patch.object(svc,'lookup_listing',return_value=self.listing),patch.object(svc,'resolve_external_movie',return_value=self.meta.copy()),patch.object(svc,'decision_log'),patch('reviewed_corrections.lookup',return_value={'target_imdb':'tt7654321','target_tmdb':123}) as lookup:
            result=svc.build_movie_context(self.payload)
        lookup.assert_not_called();self.assertEqual(result['meta']['identity_status'],'needs_review')
    def test_button_is_review_not_download(self):
        token=self.offer();markup=svc._reply_markup('https://synthetic.invalid/action/'+token)
        self.assertIn('Review evidence',markup['inline_keyboard'][0][0]['text'])
    def test_prepare_only_creates_separate_confirmation(self):
        token=self.offer();self.post(token,'imdb=tt7654321&tmdb=123&confirm_identity=yes')
        with patch.object(svc,'create_pending_action',return_value='synthetic-next-token') as prepare,patch.object(svc,'PUBLIC_BASE_URL','https://synthetic.invalid'):
            h=self.post(token,'prepare_download=yes')
        self.assertEqual(h._html.call_args.args[0],200);self.assertEqual(prepare.call_args.args[1]['identity_choice'],{'review_token':token})
    def test_old_replay_cannot_change_selected_identity(self):
        token=self.offer();self.post(token,'imdb=tt7654321&tmdb=123&confirm_identity=yes')
        h=self.post(token,'imdb=tt7654321&tmdb=123&confirm_identity=yes');self.assertEqual(h._html.call_args.args[0],409)
    def test_ordinary_download_duplicate_protection_unchanged(self):
        action={'movie':self.target,'release':self.release};token=store.create_action(action);store.update_action(token,status='needs_review')
        self.assertEqual(store.create_action(action),token);self.assertEqual(store.get_action(token)['status'],'needs_review')

    def test_http_review_get_and_choice_never_call_acquisition(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen,Request
        token=self.offer()
        server=ThreadingHTTPServer(('127.0.0.1',0),svc.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url='http://127.0.0.1:'+str(server.server_port)+'/action/'+token
        try:
            with patch.object(svc,'lookup_listing',return_value=self.listing),patch.object(svc,'resolve_external_movie',return_value=self.target),patch.object(svc,'find_local',return_value=None),patch.object(svc,'selection_context') as radarr,patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab,patch.object(svc,'_telegram_request') as telegram:
                with urlopen(url) as response:
                    self.assertEqual(response.status,200);self.assertEqual(response.headers['Referrer-Policy'],'no-referrer');self.assertIn(b'Review movie identity',response.read())
                with urlopen(Request(url,data=b'imdb=tt7654321&tmdb=123&confirm_identity=yes')) as response:
                    self.assertEqual(response.status,200);self.assertIn(b'No download started',response.read())
                for mock in (radarr,add,grab,telegram):mock.assert_not_called()
        finally:server.shutdown();server.server_close();thread.join()

    def test_invalid_chosen_occurrence_blocks_before_remote_write(self):
        action={'movie':self.target|{'identity_source':'owner_occurrence_choice','identity_choice':{'review_token':'expired'}},'release':self.release,'indexer':self.indexer}
        token=store.create_action(action)
        with patch.object(svc,'update_action') as update,patch.object(svc,'selection_context') as radarr:
            h=self.post(token,'root_folder=/movies&quality_profile=1')
        self.assertEqual(h._html.call_args.args[0],409);update.assert_not_called();radarr.assert_not_called()
