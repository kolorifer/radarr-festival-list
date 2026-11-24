"""Release-card watched actions against an invented Radarr and private action store."""
import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import movie_intel_service as svc
import pending_actions
import radarr_client
from test_movie_intel_actions import META, PAYLOAD


MOVIE = dict(id=42, tmdbId=META['tmdb_id'], imdbId=META['imdb_id'], monitored=True,
             tags=[2, 3], hasFile=True, movieFileId=19, qualityProfileId=10,
             rootFolderPath='/unchanged')
CONTEXT = dict(roots=[dict(path='/movies')], profiles=[dict(id=7,name='Test')],
               root_default='/movies', profile_default=7)
FORM = dict(confirm_watched='yes', root_folder='/movies', quality_profile='7')


class WatchedReleaseActionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = patch.object(pending_actions,'STORE_PATH',Path(directory.name)/'actions.json')
        storage.start()
        self.addCleanup(storage.stop)
        for name, result in (('reserve',False),('watched_feedback','recorded')):
            evaluator = patch.object(svc.telegram_evaluator,name,return_value=result)
            evaluator.start()
            self.addCleanup(evaluator.stop)
        self.movie = None
        self.tags = [dict(id=5,label='watched')]
        self.writes = []
        self.token = self.create(PAYLOAD,META)

    @staticmethod
    def create(payload, meta):
        with patch.object(svc,'radarr_configured',return_value=True):
            return svc.create_pending_action(payload,meta)

    def request(self,path,method='GET',payload=None):
        if method == 'GET':
            if path.startswith('/movie?tmdbId='+str(META['tmdb_id'])+'&'):
                return [copy.deepcopy(self.movie)] if self.movie is not None else []
            if path == '/tag':
                return copy.deepcopy(self.tags)
        self.writes.append((method,path,copy.deepcopy(payload)))
        if (method,path) == ('POST','/tag'):
            self.tags.append(dict(id=5,label='watched'))
        elif (method,path) == ('POST','/movie'):
            self.movie = dict(id=42,imdbId=META['imdb_id'],**payload)
        elif (method,path) == ('PUT','/movie/editor'):
            self.movie['tags'] = sorted(set(self.movie['tags']) | set(payload['tags']))
            self.movie['monitored'] = payload['monitored']
        else:
            self.fail(f'Unexpected Radarr operation: {method} {path}')

    def handle(self, params=None, *, watched=True, rating=None, token=None, current=True, request=None):
        handler = object.__new__(svc.Handler)
        handler._html = Mock()
        handler._json = Mock()
        handler.path = '/action/' + (token or self.token) + ('/watched' if watched else '')
        if rating:
            handler.path += '/' + rating
        with (patch.object(radarr_client,'_request',side_effect=request or self.request),
              patch.object(svc,'reviewed_action_current',return_value=current),
              patch.object(svc,'selection_context',return_value=CONTEXT),
              patch.object(svc,'push_release') as grab):
            if params is None:
                handler.do_GET()
            else:
                raw = urlencode(params,doseq=True).encode()
                handler.headers = {'Content-Length': str(len(raw))}
                handler.rfile = io.BytesIO(raw)
                handler.do_POST()
            self.assertEqual(grab.call_count, int(not watched and params is not None))
        return handler._html.call_args.args

    def test_offers_watched_on_text_photo_and_retry_edit_alongside_grab(self):
        url = 'https://public.invalid/action/' + self.token
        for body in (svc._telegram_payload('Release',action_url=url),
                     svc._telegram_photo_payload('photo','Release',action_url=url)):
            self.assertEqual(body['reply_markup']['inline_keyboard'],
                             [[{'text':'➕ Add to Radarr & grab this release','url':url}],
                              [{'text':'Add as watched - Good','url':url+'/watched/good'}],
                              [{'text':'Add as watched - Bad','url':url+'/watched/bad'}]])
        with (patch.object(svc,'TELEGRAM_CHAT_ID','7'),
              patch.object(svc,'PUBLIC_BASE_URL','https://public.invalid'),
              patch.object(svc,'_telegram_request') as send):
            svc.edit_retry_message([dict(chat_id='7',message_id=12,kind='text')],
                                   dict(token=self.token,text='Release'))
        self.assertEqual(len(send.call_args.args[1]['reply_markup']['inline_keyboard']),3)
        for kind in ('alternative','identity_review'):
            token = pending_actions.create_action({'kind':kind,'movie':META})
            self.assertEqual(len(svc._reply_markup('https://public.invalid/action/'+token)['inline_keyboard']),1)
            self.assertEqual(self.handle(FORM,token=token)[0],409)
        self.assertEqual(self.writes,[])

    def test_rated_confirmation_and_legacy_links_share_one_completion(self):
        for rating, decision in (('good','watch'),('bad','skip')):
            with self.subTest(rating=rating):
                self.movie = copy.deepcopy(MOVIE)
                token = pending_actions.create_action({'movie':META})
                with patch.object(svc.telegram_evaluator,'watched_feedback',return_value='recorded') as feedback:
                    status, page = self.handle(token=token,rating=rating)
                    self.assertEqual(status,200)
                    self.assertIn(f'Confirm watched - {rating.title()}',page)
                    self.assertEqual(self.handle({'confirm_watched':'yes'},token=token,rating=rating)[0],400)
                    self.assertEqual(self.handle({'confirm_watched':rating},token=token,rating=rating,current=False)[0],409)
                    feedback.assert_not_called()
                    status, page = self.handle({'confirm_watched':rating},token=token,rating=rating)
                    self.assertEqual(status,200)
                    self.assertIn(f'The {rating.title()} rating was saved.',page)
                    for other in (None,'good','bad'):
                        self.assertIn('already marked',self.handle(
                            {'confirm_watched':other or 'yes'},token=token,rating=other)[1])
                    feedback.assert_called_once_with(META,decision=decision,note='watched',require_saved_ack=True)
        self.assertEqual(len(self.writes),2)
        self.assertTrue(all(path=='/movie/editor' for _,path,_ in self.writes))

    def test_old_link_and_uncertain_rated_feedback_are_never_replayed(self):
        self.movie = copy.deepcopy(MOVIE)
        with patch.object(svc.telegram_evaluator,'watched_feedback',side_effect=TimeoutError) as feedback:
            self.assertEqual(self.handle({'confirm_watched':'yes'})[0],200)
            self.assertEqual(self.handle({'confirm_watched':'good'},rating='good')[0],200)
            feedback.assert_not_called()
            token = pending_actions.create_action({'movie':dict(META,imdb_id=None)})
            status, page = self.handle({'confirm_watched':'bad'},token=token,rating='bad')
            self.assertEqual(status,200)
            self.assertIn('Radarr confirmed',page)
            self.assertIn('The Bad rating could not be confirmed.',page)
            self.assertEqual(self.handle({'confirm_watched':'good'},token=token,rating='good')[0],200)
            feedback.assert_called_once_with(META,decision='skip',note='watched',require_saved_ack=True)

    def test_partial_or_unpersisted_watched_update_never_sends_feedback(self):
        self.movie = copy.deepcopy(MOVIE)
        with patch.object(svc.telegram_evaluator,'watched_feedback') as feedback:
            with patch.object(svc,'ensure_watched_movie',side_effect=radarr_client.RadarrError('partial')):
                self.assertEqual(self.handle({'confirm_watched':'good'},rating='good')[0],502)
            with patch.object(svc,'update_action',return_value=False):
                self.assertEqual(self.handle({'confirm_watched':'good'},rating='good')[0],502)
            feedback.assert_not_called()

    def test_watched_get_and_post_are_independent_of_grab(self):
        status, page = self.handle()
        self.assertEqual(status,200)
        self.assertIn('Confirm watched',page)
        self.assertIn('Root folder',page)
        self.assertNotIn('tracker.invalid',page)
        self.assertEqual(self.writes,[])
        self.assertEqual(self.handle(FORM)[0],200)
        self.assertEqual(self.writes,[('POST','/movie',{
            'tmdbId':META['tmdb_id'],'qualityProfileId':7,'rootFolderPath':'/movies',
            'monitored':False,'tags':[5],'minimumAvailability':'released',
            'addOptions':{'searchForMovie':False},'title':META['title']})])
        self.assertIn('already marked',self.handle(FORM)[1])
        self.assertEqual(len(self.writes),1)
        self.assertTrue(pending_actions.get_action(self.token)['watched_completed'])
        self.assertEqual(self.handle({'root_folder':'/movies','quality_profile':'7'},watched=False)[0],200)
        self.assertIsNone(pending_actions.get_action(self.token))

    def test_existing_movie_uses_additive_editor_and_preserves_file_and_settings(self):
        self.movie = copy.deepcopy(MOVIE)
        self.assertNotIn('Root folder',self.handle()[1])
        self.assertEqual(self.handle({'confirm_watched':'yes'})[0],200)
        self.assertEqual(self.writes,[('PUT','/movie/editor',{
            'movieIds':[42],'monitored':False,'tags':[5],'applyTags':'add'})])
        self.assertEqual(self.movie,dict(MOVIE,monitored=False,tags=[2,3,5]))

    def test_partial_change_and_lost_response_are_reconciled(self):
        self.movie = copy.deepcopy(MOVIE)
        self.tags = []
        simulate_partial = True

        def request(path,method='GET',payload=None):
            if (method,path) == ('PUT','/movie/editor') and simulate_partial:
                self.writes.append((method,path,payload))
                self.movie['tags'].append(5)
                raise radarr_client.RadarrError('invented timeout')
            result = self.request(path,method,payload)
            if (method,path) in (('POST','/tag'),('PUT','/movie/editor')):
                raise radarr_client.RadarrError('invented lost response')
            return result

        self.assertEqual(self.handle({'confirm_watched':'yes'},request=request)[0],502)
        self.assertFalse(pending_actions.get_action(self.token).get('watched_completed'))
        self.assertTrue(self.movie['monitored'])
        simulate_partial = False
        self.assertEqual(self.handle({'confirm_watched':'yes'},request=request)[0],200)
        self.assertEqual(self.movie,dict(MOVIE,monitored=False,tags=[2,3,5]))
        self.assertEqual([(m,p) for m,p,_ in self.writes],
                         [('POST','/tag'),('PUT','/movie/editor'),('PUT','/movie/editor')])

    def test_concurrent_exact_add_is_reconciled_without_another_add(self):
        def request(path,method='GET',payload=None):
            if (method,path) == ('POST','/movie'):
                self.writes.append((method,path,payload))
                self.movie = copy.deepcopy(MOVIE)
                raise radarr_client.RadarrError('invented duplicate')
            return self.request(path,method,payload)

        self.assertEqual(self.handle(FORM,request=request)[0],200)
        self.assertEqual([(m,p) for m,p,_ in self.writes],[('POST','/movie'),('PUT','/movie/editor')])
        self.assertEqual(self.movie,dict(MOVIE,monitored=False,tags=[2,3,5]))

    def test_store_failure_after_radarr_success_reports_possible_change(self):
        self.movie = copy.deepcopy(MOVIE)
        with patch.object(svc,'update_action',side_effect=ValueError('invented store error')):
            status, page = self.handle({'confirm_watched':'yes'})
        self.assertEqual(status,502)
        self.assertIn('Radarr may have applied',page)
        self.assertNotIn('invented store error',page)
        self.assertEqual(self.movie,dict(MOVIE,monitored=False,tags=[2,3,5]))
        self.assertEqual(self.handle({'confirm_watched':'yes'})[0],200)
        self.assertEqual(len(self.writes),1)

    def test_stale_identity_malformed_lookup_and_invalid_confirmation_refuse(self):
        self.assertEqual(self.handle(FORM,current=False)[0],409)
        self.assertEqual(self.handle({'confirm_watched':['yes','yes']})[0],400)
        self.assertEqual(self.handle(dict(FORM,quality_profile='8'))[0],400)
        self.assertEqual(self.handle({'confirm_watched':'yes'})[0],409)
        self.movie = dict(MOVIE,imdbId='tt7654321')
        self.assertEqual(self.handle(FORM)[0],502)
        self.assertEqual(self.handle(FORM,request=lambda *args,**kwargs: None)[0],502)
        self.assertEqual(self.writes,[])
