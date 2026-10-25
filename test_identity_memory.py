"""Remembered identity is a proposal; real acquisition transports are never used."""
import copy
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

import alternative_grab as alt
import identity_memory as memory
import movie_intel_service as svc
import pending_actions as actions
import verified_identity_cache as cache
from test_alternative_grab import PAYLOAD,CURRENT,MOVIE


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name).resolve();os.chmod(self.directory,0o700)
        patches=[patch.dict(os.environ,{cache.SETTING:str(self.directory/'cache.sqlite3'),alt.CONFIG:'synthetic'}),
                 patch.object(actions,'STORE_PATH',self.directory/'actions.json'),
                 patch.object(svc,'PUBLIC_BASE_URL','https://example.invalid'),
                 patch.object(svc,'radarr_configured',return_value=True),
                 patch.object(alt,'get_movie_by_tmdb',return_value=copy.deepcopy(CURRENT)),
                 patch.object(svc,'find_local',return_value=None)]
        for p in patches:p.start();self.addCleanup(p.stop)
        self.payload=copy.deepcopy(PAYLOAD)
        self.payload['data']['indexer']['name']='TorrentLeech'
        self.payload['data']['release']['external_id']='123'
        self.payload['data']['release']['info_url']='https://www.torrentleech.org/torrent/123'
        self.meta=dict(MOVIE,identity_reason='external_id_verified',identity_source='torrentleech_listing')
        self.context={'meta':{'identity_status':'unresolved','identity_reason':'listing_temporary_http'},'category':'quality'}
        memory.observe(self.payload,self.meta)
        self.new=copy.deepcopy(self.payload)
        self.new['data']['release'].update(external_id='456',name='Touch.of.Evil.1958.1080p.OTHER-CUT',
            download_url='https://www.torrentleech.org/rss/download/456/SYNTHETIC/new.torrent',
            info_url='https://www.torrentleech.org/torrent/456',cut='Other cut')

    def offer(self):return svc.create_identity_review(self.new,self.context)

    def post(self,token,body):
        handler=object.__new__(svc.Handler);handler._html=Mock()
        handler.headers={'Content-Length':str(len(body))};handler.rfile=io.BytesIO(body.encode())
        with patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as push, \
             patch.object(alt,'execute') as acquire,patch.object(svc,'_telegram_request') as telegram:
            handler._handle_action_post_locked(token)
            for operation in (add,push,acquire,telegram):operation.assert_not_called()
        return handler._html.call_args.args

    def choose_and_prepare(self):
        token=self.offer();self.assertTrue(token)
        self.assertEqual(self.post(token,'confirm_identity=yes')[0],200)
        self.assertEqual(self.post(token,'prepare_download=yes')[0],200)
        return token,actions.get_action(token)['next_token']

    def test_new_release_is_only_a_proposal_until_explicit_identity_choice(self):
        proposal=memory.packet(self.new,self.context)
        self.assertEqual(proposal['candidate']['tmdb_id'],MOVIE['tmdb_id'])
        self.assertIsNone(svc.create_pending_action(self.new,self.context['meta']))
        token=self.offer();review=actions.get_action(token)
        self.assertEqual(review['kind'],'identity_review');self.assertFalse(review.get('chosen'))
        with patch.object(svc,'create_pending_action') as create:
            status,body=self.post(token,'confirm_identity=yes')
        create.assert_not_called();self.assertEqual(status,200);self.assertIn('No download started',body)
        self.assertIsNone(actions.get_action(token).get('next_token'))

    def test_separate_confirmation_retains_original_rejection_new_source_and_cut(self):
        token,next_token=self.choose_and_prepare();child=actions.get_action(next_token)
        self.assertEqual(child['kind'],'alternative')
        self.assertEqual(child['rejections'],self.new['data']['result']['rejections'])
        self.assertEqual(child['release']['external_id'],'456')
        self.assertEqual(child['release']['cut'],'Other cut')
        self.assertEqual(child['release']['download_url'],self.new['data']['release']['download_url'])
        self.assertEqual(child['movie']['identity_memory_choice']['review_token'],token)
        self.assertTrue(svc.reviewed_action_current(child))
        alt.validate_action(child)
        markup=svc._reply_markup('https://example.invalid/action/'+next_token)
        self.assertEqual(markup['inline_keyboard'][0][0]['text'],'⬇️ Grab Anyway')

    def test_form_cannot_skip_identity_or_choose_arbitrary_ids(self):
        for body in ('prepare_download=yes','confirm_identity=no','confirm_identity=yes&tmdb=5',
                     'confirm_identity=yes&confirm_identity=yes','confirm_alternative=yes'):
            token=self.offer();self.assertEqual(self.post(token,body)[0],409)
            self.assertFalse(actions.get_action(token).get('chosen'))

    def test_used_child_cannot_be_recreated_by_review_replay(self):
        token,next_token=self.choose_and_prepare();actions.delete_action(next_token)
        with patch.object(svc,'create_pending_action') as create:
            status,body=self.post(token,'prepare_download=yes')
        create.assert_not_called();self.assertEqual(status,200)
        self.assertEqual(actions.get_action(token)['next_token'],next_token)
        self.assertIsNone(actions.get_action(next_token))

    def test_conflict_revokes_pending_review_and_acquisition_including_helper_gate(self):
        token,next_token=self.choose_and_prepare();child=actions.get_action(next_token)
        memory.observe(self.new,dict(self.meta,tmdb_id=999,imdb_id='tt7654321'))
        self.assertIsNone(memory.candidate(self.new))
        self.assertEqual(self.post(token,'prepare_download=yes')[0],409)
        self.assertFalse(svc.reviewed_action_current(child))
        with self.assertRaises(ValueError):alt.validate_action(child)
        # Another success cannot overwrite known ambiguity.
        memory.observe(self.new,self.meta);self.assertIsNone(memory.candidate(self.new))

    def test_expired_or_revoked_memory_never_enables_download(self):
        token,next_token=self.choose_and_prepare();child=actions.get_action(next_token)
        import sqlite3
        with sqlite3.connect(self.directory/'cache.sqlite3') as connection:
            connection.execute('update verified_cache set expires=0')
        self.assertFalse(svc.reviewed_action_current(child))
        self.assertEqual(self.post(token,'prepare_download=yes')[0],409)
        actions.delete_action(token)
        self.assertFalse(svc.reviewed_action_current(child))
        with self.assertRaises(ValueError):alt.validate_action(child)

    def test_new_year_title_source_tv_and_supplied_conflicting_ids_do_not_match(self):
        for field,value in (('year',1959),('title','Touch of Evil 2'),('season',1),('episode',1),
                            ('type','episode'),('meta_imdb','tt7654321'),('meta_tmdb',999)):
            p=copy.deepcopy(self.new);p['data']['release'][field]=value
            self.assertIsNone(memory.packet(p,self.context))
        p=copy.deepcopy(self.new);p['data']['indexer']['identifier']='other'
        self.assertIsNone(memory.packet(p,self.context))

    def test_new_listing_assertion_conflicts_even_when_tmdb_is_unavailable(self):
        meta={'identity_status':'unresolved','identity_reason':'metadata_api_unavailable','imdb_id':'tt7654321'}
        self.assertIsNone(memory.packet(self.new,{'meta':meta}))
        memory.observe(self.new,meta)
        self.assertIsNone(memory.candidate(self.new))

    def test_mixed_reasons_and_non_temporary_failures_do_not_offer_memory(self):
        p=copy.deepcopy(self.new);p['data']['result']['rejections'].append('Quality not allowed')
        self.assertIsNone(memory.packet(p,self.context))
        for reason in ('listing_id_conflict','listing_mismatch','listing_id_missing','listing_auth_failure',
                       'invalid_external_id','title_conflict','tmdb_mapping_missing'):
            self.assertIsNone(memory.packet(self.new,{'meta':{'identity_status':'unresolved','identity_reason':reason}}))

    def test_reviewed_choices_and_typo_repairs_are_not_learned(self):
        p=copy.deepcopy(self.payload);p['data']['release']['title']='Different'
        for change in ({'identity_source':'owner_remembered_choice'}, {'identity_source':'owner_occurrence_choice'},
                       {'identity_source':'torrent_evidence'},{'identity_title_basis':'tracker_minor_typo'},
                       {'identity_status':'unresolved'}):
            memory.observe(p,dict(self.meta,**change));self.assertIsNone(memory.candidate(p))

    def test_review_binding_cannot_be_retargeted(self):
        token=self.offer();review=actions.get_action(token)
        review['original_event']['data']['release']['external_id']='999'
        with self.assertRaises(ValueError):memory.target(review)
        token,next_token=self.choose_and_prepare();child=actions.get_action(next_token)
        child['release']['download_url']='https://www.torrentleech.org/rss/download/456/CHANGED/new.torrent'
        self.assertFalse(svc.reviewed_action_current(child))

    def test_repeated_occurrences_need_their_own_choice(self):
        first,_=self.choose_and_prepare();second=self.offer()
        self.assertNotEqual(first,second);self.assertFalse(actions.get_action(second).get('chosen'))

    def test_rendered_review_contains_movie_and_exact_release_not_private_url(self):
        token=self.offer();body=memory.render(actions.get_action(token))
        self.assertIn('Touch of Evil',body);self.assertIn('1080p.OTHER-CUT',body)
        self.assertNotIn('SYNTHETIC',body);self.assertNotIn('torrentleech.org',body)
        label=svc._reply_markup('https://example.invalid/action/'+token)['inline_keyboard'][0][0]['text']
        self.assertEqual(label,'🔎 Confirm remembered movie')

    def test_service_learns_verified_result_then_outage_offers_review(self):
        with patch.object(svc,'lookup_listing',return_value={'reason':'listing_id_found','source':'torrentleech_listing','imdb_id':MOVIE['imdb_id']}), \
             patch.object(svc,'resolve_external_movie',return_value=self.meta),patch.object(svc,'get_movie_by_tmdb',return_value=CURRENT):
            svc.build_movie_context(self.payload)
        with patch.object(svc,'lookup_listing',return_value={'reason':'listing_temporary_http','source':'torrentleech_listing'}), \
             patch.object(svc,'resolve_external_movie') as resolve:
            result=svc.build_movie_context(self.new)
        resolve.assert_not_called()
        self.assertEqual(result['meta']['identity_status'],'unresolved')
        self.assertIn('Confirm the remembered movie',result['text'])
        self.assertTrue(svc.create_identity_review(self.new,result))

    def test_concurrent_distinct_verified_matches_preserve_ambiguity(self):
        from concurrent.futures import ThreadPoolExecutor
        other=dict(self.meta,imdb_id='tt7654321',tmdb_id=999)
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda meta:memory.observe(self.new,meta),(self.meta,other)))
        self.assertIsNone(memory.candidate(self.new))

    def test_historical_verification_retains_age_and_rejects_stale_bootstrap(self):
        import sqlite3,time
        p=copy.deepcopy(self.payload);p['data']['release']['title']='Historical'
        observed=time.time()-3600
        memory.observe(p,self.meta,verified_at=observed)
        self.assertEqual(memory.candidate(p)['verified_at'],observed)
        with sqlite3.connect(self.directory/'cache.sqlite3') as connection:
            self.assertEqual(connection.execute('select expires from verified_cache where key=?',
                (cache._key('remembered_movie',memory.context(p['data']['release'],p['data']['indexer'])),)).fetchone()[0],observed+cache.TTL)
        p['data']['release']['title']='Stale'
        memory.observe(p,self.meta,verified_at=time.time()-cache.TTL-1)
        self.assertIsNone(memory.candidate(p))

    def test_unknown_movie_review_keeps_original_event_and_requires_same_choice(self):
        self.new['data']['result']['rejections']=['Unknown Movie']
        self.new['timestamp']='2026-10-25T10:00:00Z'
        token,next_token=self.choose_and_prepare();child=actions.get_action(next_token)
        self.assertNotEqual(child.get('kind'),'alternative')
        self.assertEqual(child['movie']['identity_source'],'owner_remembered_choice')
        self.assertTrue(svc.reviewed_action_current(child))
        actions.delete_action(token);self.assertFalse(svc.reviewed_action_current(child))


class MemoryHTTPTests(unittest.TestCase):
    setUp=MemoryTests.setUp

    def test_webhook_review_and_separate_confirmation_over_http(self):
        import json,threading
        from http.server import ThreadingHTTPServer
        from urllib.request import Request,urlopen
        from urllib.parse import urlparse
        server=ThreadingHTTPServer(('127.0.0.1',0),svc.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        def request(path,body=None,json_body=False):
            data=None if body is None else (json.dumps(body).encode() if json_body else body.encode())
            with urlopen(Request(base+path,data=data,headers={'Content-Type':'application/json' if json_body else 'application/x-www-form-urlencoded'}),timeout=3) as response:
                return response.status,response.read().decode()
        try:
            with patch.object(svc,'WEBHOOK_SECRET','synthetic'),patch.object(svc,'lookup_listing',return_value={'reason':'listing_temporary_http','source':'torrentleech_listing'}), \
                 patch.object(svc,'send_movie_notification') as notify,patch.object(svc,'observe_identity_outcome'),patch('identity_retry.submit'), \
                 patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as push,patch.object(alt,'execute') as acquire:
                status,body=request('/webhook/synthetic',self.new,True)
                self.assertEqual(status,200);self.assertTrue(json.loads(body)['action'])
                url=notify.call_args.kwargs['action_url'];path=urlparse(url).path
                self.assertIn('Confirm remembered movie',request(path)[1])
                self.assertIn('No download started',request(path,'confirm_identity=yes')[1])
                status,body=request(path,'prepare_download=yes');self.assertEqual(status,200)
                token=path.rsplit('/',1)[-1];child=actions.get_action(token)['next_token']
                status,body=request('/action/'+child)
                self.assertEqual(status,200);self.assertIn('Grab Anyway',body)
                self.assertIn('OTHER-CUT',body)
                for operation in (add,push,acquire):operation.assert_not_called()
        finally:
            server.shutdown();server.server_close();thread.join()
