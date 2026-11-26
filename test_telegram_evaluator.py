"""Invented evaluator and Telegram replies. No live requests."""
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import movie_intel_service as svc
import pending_actions
from radarr_client import ReleaseRejected
import telegram_evaluator as ev
from test_movie_intel_actions import META, PAYLOAD
from torrent_research_evidence import extract
from bs4 import BeautifulSoup


TOKEN = 'A'*32
URL = 'https://public.invalid/action/'+TOKEN
NAME = '  Exact.Film.2021.1080p.<Remux>.GROÜP  '
ACTION = {'movie':META,'release':{'name':NAME}}
REQUEST = {'raw_text':NAME}
IDENTIFICATION = {'canonical_title':'Actual <Movie>','year':2020,'imdb_id':'tt1234567','tmdb_id':42,
                  'match_confidence':'medium','disambiguation_note':'Distinct director and release year'}


class EvidenceRequestTests(unittest.TestCase):
    def test_reuses_checked_source_evidence_and_keeps_false_and_exact_name(self):
        page = '''<div class="torrent-info-details"><p class="torrent-summary">Invented synopsis
        https://tracker.invalid/private</p></div><div id="nfo_text">General Duration : 1 h 53 min
        Video ID : 1 Audio #1 ID : 2 Language : French Default : Yes
        Audio #2 ID : 3 Language : English Default : No Text ID : 4 Language : Italian</div>'''
        listing = {'imdb_id':'tt1234567','freeleech':True,
                   'torrent_evidence':extract(BeautifulSoup(page,'html.parser'))}
        release = {'name':NAME,'title':'A Movie','year':2021,'category':'Movies :: 4K','meta_tmdb':'42',
                   'size':67_300_000_000,'freeleech':False,'resolution':'2160p','source':'UHD.BluRay',
                   'media_processing':'REMUX','language':['GERMAN','MULTi'],
                   'download_url':'https://tracker.invalid/token','external_id':'987'}
        request = ev.evaluation_request(release,{'name':'TorrentLeech'},listing)
        self.assertEqual(request['raw_text'],NAME)
        self.assertEqual((request['hint_title'],request['hint_year']),('A Movie',2021))
        self.assertIs(request['force_refresh'],True)
        info = request['torrent_info']
        self.assertEqual({key:value for key,value in info.items() if key not in ('description','nfo_text')},
                         {'indexer':'TorrentLeech','category':'Movies :: 4K','imdb_id':'tt1234567','tmdb_id':42,
                          'size_gb':67.3,'freeleech':False,'resolution':'2160p','source':'UHD BluRay REMUX',
                          'runtime_minutes':113,'audio_languages':['French','English']})
        self.assertIn('Invented synopsis',info['description'])
        self.assertIn('Video ID',info['nfo_text'])
        self.assertNotIn('tracker.invalid',str(request))
        self.assertNotIn('987',str(request))

    def test_announced_language_fallback_and_source_deduplication(self):
        release = {'name':NAME,'language':['DL','DUTCH','MULTi','NORDiC','GERMAN'],
                   'source':'UHD.BluRay.REMUX','media_processing':'REMUX','meta_imdb':'tt7654321'}
        info = ev.evaluation_request(release,{}, {'imdb_id':'tt1234567'})['torrent_info']
        self.assertEqual(info,{'audio_languages':['Dutch','German'],'source':'UHD BluRay REMUX'})

    def test_omits_missing_fields_and_refuses_private_raw_names(self):
        release = {'name':NAME,'title':'magnet:?xt=not-for-evaluator','year':True,'runtime_minutes':0,
                   'language':['MULTi','DL'],'size':0,'freeleech':'false','meta_imdb':'invalid'}
        self.assertEqual(ev.evaluation_request(release,{}),REQUEST)
        for name in ('Movie api_key=private-value','file:///private/path','Movie https://tracker.invalid/secret'):
            self.assertIsNone(ev.evaluation_request({'name':name},{}))

    def test_hints_alone_also_bypass_the_raw_text_cache(self):
        self.assertEqual(ev.evaluation_request({'name':NAME,'title':'Distinct','year':2020},{}),
                         dict(REQUEST,hint_title='Distinct',hint_year=2020,force_refresh=True))

    def test_structured_proposal_requires_success_and_uses_actual_response_fields(self):
        response = json.dumps({'identification':IDENTIFICATION}).encode()
        with patch.object(ev,'_post',return_value=(200,response)):
            result = ev.evaluation(REQUEST)
        self.assertEqual(result.proposal, {'title':'Actual <Movie>','year':2020,'imdb_id':'tt1234567','tmdb_id':42,
                                           'confidence':'medium','reason':'Distinct director and release year'})
        with patch.object(ev,'_post',return_value=(422,response)):
            self.assertIsNone(ev.evaluation(REQUEST).proposal)
        with patch.object(ev,'_post',return_value=(200,b'{"identification":{"title":"Other"}}')):
            self.assertIsNone(ev.evaluation(REQUEST).proposal)


class EvaluatorClientTests(unittest.TestCase):
    def test_rated_feedback_uses_exact_decision_and_note(self):
        for decision in ('watch','skip'):
            ack = json.dumps({'status':'saved','decision':decision,'total_feedback':2}).encode()
            with patch.object(ev,'_post',return_value=(200,ack)) as post:
                self.assertEqual(ev.watched_feedback(
                    META,decision=decision,note='watched',require_saved_ack=True),'recorded')
            post.assert_called_once_with('/feedback',{
                'imdb_id':META['imdb_id'],'tmdb_id':META['tmdb_id'],'title':META['title'],
                'decision':decision,'note':'watched'},4)

    def test_rated_feedback_requires_the_installed_saved_ack(self):
        for reply in ((202,b'{"status":"saved","decision":"watch","total_feedback":2}'),
                      (200,b'{}'),(200,b'{"ok":false}'),(200,b'not JSON'),
                      (200,b'{"status":"saved","decision":"skip","total_feedback":2}'),
                      (200,b'{"status":"saved","decision":"watch","total_feedback":true}'),
                      (200,b'{"status":"saved","decision":"watch","total_feedback":0}')):
            with self.subTest(reply=reply),patch.object(ev,'_post',return_value=reply) as post:
                self.assertEqual(ev.watched_feedback(META,note='watched',require_saved_ack=True),'unconfirmed')
                post.assert_called_once()

    def test_exact_release_only_and_complete_safe_json(self):
        body = {'identification':{'title':'A < B'},'ratings':{'rating':8},'recognition':[],
                'decision_aid':{'reason':'See https://private.invalid/download'},
                'cached':False,'api_key':'invented credential',
                'https://private.invalid/key':42}
        with patch.object(ev,'_post',return_value=(200,json.dumps(body).encode())) as post:
            result = ev.evaluation(REQUEST).text
        post.assert_called_once_with('/evaluate',{'raw_text':NAME},80)
        parsed = json.loads(result.split('\n',1)[1])
        self.assertEqual(parsed['identification'],body['identification'])
        self.assertEqual(parsed['ratings'],body['ratings'])
        self.assertEqual(parsed['recognition'],[])
        self.assertFalse(parsed['cached'])
        self.assertEqual(parsed['api_key'],'[redacted]')
        self.assertEqual(parsed['[redacted URL]'],42)
        self.assertNotIn('private.invalid',result)
        self.assertNotIn('invented credential',result)

    def test_errors_preserve_details_and_timeout_is_single_attempt(self):
        detail = {'detail':[{'loc':['body','raw_text'],'msg':'Problem <bad>','input':NAME}]}
        with patch.object(ev,'_post',return_value=(422,json.dumps(detail).encode())):
            result = ev.evaluation(REQUEST).text
        self.assertIn('HTTP 422',result)
        self.assertEqual(json.loads(result.split('\n',1)[1]),detail)
        with patch.object(ev,'_post',return_value=(502,b'Error\nAuthorization: Bearer invented-token\nlast line')):
            result = ev.evaluation(REQUEST).text
        self.assertIn('last line',result)
        self.assertNotIn('invented-token',result)
        with patch.object(ev,'_post',side_effect=TimeoutError) as post:
            self.assertIn('timed out',ev.evaluation(REQUEST).text)
            post.assert_called_once()
        with patch.object(ev,'_post',return_value=(200,b'a'*(ev.MAX_REPLY+1))):
            self.assertIn('exceeded',ev.evaluation(REQUEST).text)

    def test_compound_credential_keys_and_labels_are_redacted(self):
        body = {'access_token':'PRIVATE_ONE','clientSecret':'PRIVATE_TWO',
                'details':"refresh_token: PRIVATE_THREE\napi_key: 'PRIVATE FOUR'",
                'token_count':17}
        with patch.object(ev,'_post',return_value=(200,json.dumps(body).encode())):
            result = ev.evaluation(REQUEST).text
        parsed = json.loads(result.split('\n',1)[1])
        self.assertEqual(parsed['access_token'],'[redacted]')
        self.assertEqual(parsed['clientSecret'],'[redacted]')
        self.assertEqual(parsed['token_count'],17)
        self.assertNotIn('PRIVATE_',result)
        self.assertNotIn('PRIVATE FOUR',result)
        plain = b'clientSecret=PRIVATE_FIVE\naccess_token: PRIVATE_SIX\nEOF'
        with patch.object(ev,'_post',return_value=(502,plain)):
            result = ev.evaluation(REQUEST).text
        self.assertNotIn('PRIVATE_',result)
        self.assertTrue(result.endswith('EOF'))

    def test_unexpected_evaluator_failure_still_delivers_error(self):
        deliver = Mock()
        with (patch.object(ev,'_QUEUE',Mock(**{'get.side_effect':[(REQUEST,deliver),StopIteration]})),
              patch.object(ev,'evaluation',side_effect=RuntimeError('private invented detail')),
              patch.object(ev,'release') as release):
            with self.assertRaises(StopIteration):
                ev._run()
        deliver.assert_called_once_with(ev.Evaluation('Evaluator failed before a complete reply was available.'))
        release.assert_called_once()

    def test_reserved_queue_entry_is_evaluated_when_taken(self):
        deliver = Mock()
        with (patch.object(ev,'_QUEUE',Mock(**{'get.side_effect':[(REQUEST,deliver),StopIteration]})),
              patch.object(ev,'evaluation',return_value='result') as evaluate, patch.object(ev,'release')):
            with self.assertRaises(StopIteration):
                ev._run()
        evaluate.assert_called_once_with(REQUEST)
        deliver.assert_called_once_with('result')


class TelegramEvaluationTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(svc,'TELEGRAM_CHAT_ID','7'))
        stack.enter_context(patch.object(svc,'TELEGRAM_BOT_TOKEN','INVENTED'))
        stack.enter_context(patch.object(svc,'PUBLIC_BASE_URL','https://public.invalid'))
        stack.enter_context(patch.object(svc,'_PENDING_EVALUATIONS',{}))
        stack.enter_context(patch.dict(os.environ,{'TELEGRAM_ADD_GRAB_TOPIC_ID':'89'}))

    @staticmethod
    def telegram_response():
        answer = io.BytesIO(b'{"ok":true,"result":{"chat":{"id":7},"message_id":123,"message_thread_id":89}}')
        answer.status = 200
        return answer

    def test_action_card_sends_before_evaluation_and_photo_fallback_queues_once(self):
        methods = []

        def send(request, timeout):
            method = request.full_url.rsplit('/',1)[-1]
            methods.append(method)
            if method == 'sendPhoto':
                raise OSError('invented photo failure')
            sent = json.loads(request.data)
            if sent.get('reply_markup'):
                self.assertEqual(sent['reply_markup']['inline_keyboard'][1][0]['url'],URL+'/watched/good')
                self.assertEqual(sent['reply_markup']['inline_keyboard'][2][0]['url'],URL+'/watched/bad')
            else:
                self.assertEqual(sent['reply_parameters'],{'message_id':123,'allow_sending_without_reply':False})
                self.assertEqual(sent['message_thread_id'],89)
                self.assertIn('&lt;invented&gt;',sent['text'])
                self.assertNotIn('<invented>',sent['text'])
            return self.telegram_response()

        with (patch.object(svc,'get_action',return_value=ACTION),
              patch.object(ev,'reserve',return_value=True),
              patch.object(ev,'submit') as submit,
              patch.object(svc,'urlopen',side_effect=send)):
            self.assertEqual(svc.send_movie_notification('Movie','https://image.invalid/poster',URL),200)
            self.assertEqual(methods,['sendPhoto','sendMessage'])
            submit.assert_called_once()
            name,callback = submit.call_args.args
            self.assertEqual(name,REQUEST)
            callback(ev.Evaluation('Evaluator result\n<invented>'))
        self.assertEqual(methods,['sendPhoto','sendMessage','sendMessage'])

    def test_overflow_is_full_private_thread_attachment(self):
        result = 'Result\n'+'<invented>🍿'*1000
        with patch.object(svc,'urlopen',return_value=self.telegram_response()) as send:
            svc._evaluation_reply({'chat_id':'7','message_id':22,'message_thread_id':89},ev.Evaluation(result))
        request = send.call_args.args[0]
        self.assertTrue(request.full_url.endswith('/sendDocument'))
        self.assertIn('multipart/form-data',request.headers['Content-type'])
        self.assertIn(b'name="message_thread_id"\r\n\r\n89',request.data)
        self.assertIn(b'{"message_id": 22, "allow_sending_without_reply": false}',request.data)
        self.assertIn(result.encode(),request.data)

    def test_missing_or_malformed_send_receipt_does_not_repeat_the_card(self):
        for bad in (True, [], {'chat':True,'message_id':123},
                    {'chat':{'id':7},'message_id':True}):
            response = io.BytesIO(json.dumps({'ok':True,'result':bad}).encode())
            response.status = 200
            with (self.subTest(result=bad),patch.object(svc,'get_action',return_value=ACTION),
                  patch.object(ev,'reserve',return_value=True),patch.object(ev,'submit') as submit,
                  patch.object(ev,'release') as release,
                  patch.object(svc,'urlopen',return_value=response) as send):
                self.assertEqual(svc.send_movie_notification('Movie','https://image.invalid/poster',URL),200)
                send.assert_called_once()
                self.assertTrue(send.call_args.args[0].full_url.endswith('/sendPhoto'))
                submit.assert_not_called()
                release.assert_called_once()

    def test_capacity_error_remains_visible_and_only_actionable_cards_queue(self):
        with (patch.object(svc,'get_action',return_value=ACTION),
              patch.object(ev,'reserve',return_value=False) as reserve,
              patch.object(ev,'submit') as submit,
              patch.object(svc,'_telegram_request') as send):
            svc.send_movie_notification('Movie',action_url=URL)
            sent = send.call_args.args[1]
            self.assertIn('queue could not accept this release',sent['text'])
            self.assertEqual(len(sent['reply_markup']['inline_keyboard']),3)
            reserve.assert_called_once()
            submit.assert_not_called()
        with (patch.object(svc,'get_action',return_value=dict(ACTION,kind='identity_review')),
              patch.object(ev,'reserve') as reserve,
              patch.object(svc,'_telegram_request')):
            svc.send_movie_notification('Review',action_url=URL)
            reserve.assert_not_called()

    def test_initial_no_token_gets_proposed_movie_on_final_card_not_supplemental_poster(self):
        from copy import deepcopy
        payload = deepcopy(PAYLOAD)
        payload['data']['release'].update(name=NAME,freeleech=False)
        received = []

        def send(req, timeout):
            received.append((req.full_url.rsplit('/',1)[-1],json.loads(req.data)))
            response = io.BytesIO(json.dumps({'ok':True,'result':{'chat':{'id':7},
                'message_id':len(received),'message_thread_id':89}}).encode())
            response.status = 200
            return response

        with (patch.object(ev,'reserve',return_value=True),patch.object(ev,'submit') as submit,
              patch.object(svc,'urlopen',side_effect=send),
              patch.object(svc,'create_action') as create,patch.object(svc,'update_action') as update):
            svc.send_movie_notification('Movie unidentified\n'*320,'https://image.invalid/poster',
                                        payload=payload,context={'meta':None})
            self.assertEqual([method for method,_ in received],['sendMessage','sendMessage','sendPhoto'])
            request,deliver = submit.call_args.args
            self.assertEqual(request['raw_text'],NAME)
            self.assertIs(request['torrent_info']['freeleech'],False)
            deliver(ev.Evaluation('Full result',ev._proposal(IDENTIFICATION)))
            create.assert_not_called()
            update.assert_not_called()
        reply = received[-1][1]
        self.assertEqual(reply['reply_parameters']['message_id'],2)
        self.assertEqual(reply['message_thread_id'],89)
        self.assertIn('Actual &lt;Movie&gt; (2020)',reply['text'])
        self.assertIn('tt1234567 · TMDb: 42',reply['text'])
        self.assertIn('Distinct director and release year',reply['text'])
        self.assertNotIn('reply_markup',reply)

    def test_unidentified_review_reply_reuses_only_the_bound_review_link(self):
        from copy import deepcopy
        payload = deepcopy(PAYLOAD)
        payload['data']['release']['name'] = NAME
        for action,eligible in (
            (dict(ACTION,kind='identity_review',review={'bound':{'source_key':'fixture'}}),True),
            (dict(ACTION,kind='identity_review',review={'type':'remembered_movie'}),False),
            (ACTION,False),
        ):
            with (self.subTest(eligible=eligible),patch.object(svc,'get_action',return_value=action),
                  patch.object(svc,'update_action',return_value=True) as update,
                  patch.object(ev,'reserve',return_value=True),patch.object(ev,'submit') as submit,
                  patch.object(svc,'urlopen',side_effect=lambda *a,**kw:self.telegram_response()) as send):
                svc.send_movie_notification('Review',action_url=URL,payload=payload,context={'meta':None})
                _,deliver = submit.call_args.args
                proposal = ev._proposal(IDENTIFICATION)
                deliver(ev.Evaluation('Full result',proposal))
                reply = json.loads(send.call_args.args[0].data)
                self.assertEqual('reply_markup' in reply,eligible)
                if eligible:
                    update.assert_called_once_with(TOKEN,evaluator_proposal=proposal)
                    self.assertEqual(reply['reply_markup']['inline_keyboard'][0][0]['url'],URL)
                else:
                    update.assert_not_called()

    def test_high_confidence_without_token_uses_checked_ids_and_normal_actions(self):
        from copy import deepcopy
        payload = deepcopy(PAYLOAD)
        payload['_evaluation_original'] = {'torrent_info':{'description':'inbound spoof'}}
        context = {'meta':None,'evaluation_listing':{'reason':'unsupported_indexer'}}
        identification = IDENTIFICATION | {'match_confidence':'high','imdb_id':META['imdb_id'],
                                           'tmdb_id':META['tmdb_id']}
        proposal = ev._proposal(identification)
        canonical = dict(META,identity_status='verified_tmdb')
        checked = dict(canonical,identity_source='evaluator_catalogue_match',evaluator_verified=True)
        stored = {'movie':checked,'event_timestamp':payload.get('timestamp'),
                  'release':{k:v for k,v in payload['data']['release'].items() if k in svc.REVIEW_RELEASE_KEYS},
                  'indexer':{k:v for k,v in payload['data']['indexer'].items() if k in ('name','protocol','identifier')}}
        with (patch.object(ev,'reserve',return_value=True),patch.object(ev,'submit') as submit,
              patch.object(svc,'urlopen',side_effect=lambda *a,**kw:self.telegram_response()) as send,
              patch.object(svc,'resolve_uncached_title',return_value=canonical),
              patch.object(svc,'resolve_external_movie',return_value=canonical) as resolver,
              patch.object(svc,'find_local',return_value=None),
              patch.object(svc,'get_action',return_value=stored),
              patch.object(svc,'create_pending_action',return_value=TOKEN) as offer,
              patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as push):
            svc.send_movie_notification('Unidentified',payload=payload,context=context)
            offer.assert_not_called()
            request,deliver = submit.call_args.args
            self.assertNotIn('inbound spoof',str(request))
            deliver(ev.Evaluation('Full result',proposal))
            release = payload['data']['release']
            resolver.assert_called_once_with(release['title'],release['year'],imdb_id=META['imdb_id'],
                                             tmdb_id=META['tmdb_id'],force_refresh=False)
            offer.assert_called_once_with(payload,checked)
            add.assert_not_called()
            push.assert_not_called()
        body = json.loads(send.call_args.args[0].data)
        self.assertIn('Movie independently verified for this release',body['text'])
        self.assertIn(META['title'],body['text'])
        self.assertEqual([row[0]['url'] for row in body['reply_markup']['inline_keyboard']],
                         [URL,URL+'/watched/good',URL+'/watched/bad'])

    def test_evaluator_does_not_link_or_mutate_a_legacy_or_uncertain_duplicate(self):
        target = dict(META,identity_source='torrentleech_listing',evaluator_verified=True)
        stored = {'movie':target,'event_timestamp':PAYLOAD.get('timestamp'),
                  'release':{k:v for k,v in PAYLOAD['data']['release'].items() if k in svc.REVIEW_RELEASE_KEYS},
                  'indexer':{k:v for k,v in PAYLOAD['data']['indexer'].items() if k in ('name','protocol','identifier')}}
        for returned in (dict(stored,movie=META),dict(stored,status='needs_review'),
                         dict(stored,movie=dict(target,imdb_id='tt9876543')),
                         dict(stored,indexer={'name':'another-indexer'}),
                         dict(stored,event_timestamp='2020-01-01T00:00:00Z'),
                         dict(stored,release={'name':'another release'})):
            with (self.subTest(returned=returned),patch.object(svc,'create_pending_action',return_value=TOKEN),
                  patch.object(svc,'get_action',return_value=returned),
                  patch.object(svc,'update_action') as update,patch.object(svc,'delete_action') as delete):
                self.assertIsNone(svc._evaluator_action_url(PAYLOAD,target))
                update.assert_not_called()
                delete.assert_not_called()

    def test_high_confidence_cannot_bypass_source_conflicts_or_missing_binding(self):
        proposal = ev._proposal(IDENTIFICATION | {'match_confidence':'high'})
        for context in (
            {'meta':{'identity_status':'needs_review'},'evaluation_listing':{'reason':'disabled'}},
            {'identity_observation':{'reason':'ambiguous_exact_matches'},'evaluation_listing':{'reason':'disabled'}},
            {'evaluation_listing':{'reason':'listing_id_found','imdb_id':'tt9876543'}},
            {'evaluation_listing':{'reason':'login_required'}},
            {},
        ):
            with (self.subTest(context=context),patch.object(svc,'find_local',return_value=None),
                  patch.object(svc,'resolve_external_movie') as resolve):
                self.assertIsNone(svc._verified_evaluator_target(PAYLOAD,context,proposal))
                resolve.assert_not_called()

    def test_catalogue_proposal_is_rechecked_at_confirmation(self):
        movie = dict(META,identity_status='verified_tmdb',identity_source='evaluator_catalogue_match',
                     evaluator_verified=True)
        action = {'movie':movie,**{key:PAYLOAD['data'][key] for key in ('release','indexer')}}
        with (patch.object(svc,'lookup_listing',return_value={'reason':'unsupported_indexer'}),
              patch.object(svc,'find_local',return_value=None),
              patch.object(svc,'resolve_uncached_title',return_value=movie),
              patch.object(svc,'resolve_external_movie',return_value=movie) as resolve):
            self.assertTrue(svc.reviewed_action_current(action))
            self.assertIs(resolve.call_args.kwargs['force_refresh'],True)
            resolve.return_value = dict(movie,imdb_id='tt9876543')
            self.assertFalse(svc.reviewed_action_current(action))

    def test_no_listing_requires_independent_title_selection(self):
        proposal = ev._proposal(IDENTIFICATION | {'match_confidence':'high'})
        with (patch.object(svc,'find_local',return_value=None),
              patch.object(svc,'resolve_movie',return_value=META) as cached,
              patch.object(svc,'resolve_uncached_title',return_value=None) as independent,
              patch.object(svc,'resolve_external_movie') as crosswalk):
            self.assertIsNone(svc._verified_evaluator_target(
                PAYLOAD,{'evaluation_listing':{'reason':'unsupported_indexer'}},proposal))
        independent.assert_called_once()
        cached.assert_not_called()
        crosswalk.assert_not_called()

    def test_listing_proposal_refuses_later_local_catalogue_conflict(self):
        movie = dict(META,identity_status='verified_tmdb',identity_source='torrentleech_listing',
                     evaluator_verified=True)
        action = {'movie':movie,**{key:PAYLOAD['data'][key] for key in ('release','indexer')}}
        listing = {'reason':'listing_id_found','imdb_id':movie['imdb_id']}
        with (patch.object(svc,'lookup_listing',return_value=listing),
              patch.object(svc,'resolve_external_movie',return_value=movie) as resolve,
              patch.object(svc,'find_local',side_effect=(None,None,None,{'imdb_id':'tt9876543'}))):
            self.assertTrue(svc.reviewed_action_current(action))
            self.assertFalse(svc.reviewed_action_current(action))
        self.assertEqual(resolve.call_count,2)

    def test_superseded_initial_reply_and_repeated_no_token_edit_do_not_send_twice(self):
        ref = {'chat_id':'7','message_id':123,'kind':'text'}
        approved = {'meta':dict(META,identity_status='verified_tmdb')}
        with (patch.object(ev,'reserve',return_value=True),patch.object(ev,'release'),
              patch.object(ev,'submit') as submit,
              patch.object(svc,'urlopen',side_effect=lambda *a,**kw:self.telegram_response()) as send,
              patch.object(svc,'create_pending_action',return_value=None)):
            svc.send_movie_notification('Unidentified',payload=PAYLOAD,context={'meta':None})
            _,old = submit.call_args.args
            prepared = svc.prepare_retry_message(PAYLOAD,approved,'external_id_verified')
            svc.edit_retry_message([ref],prepared)
            _,current = submit.call_args.args
            with patch.object(svc,'_telegram_request',side_effect=HTTPError(
                    URL,400,'Bad Request',{},io.BytesIO(b'{"description":"message is not modified"}'))):
                svc.edit_retry_message([ref],prepared)
            old(ev.Evaluation('Stale result',ev._proposal(IDENTIFICATION)))
            self.assertEqual(send.call_count,2)
            current(ev.Evaluation('Current result',ev._proposal(IDENTIFICATION)))
            self.assertEqual(send.call_count,3)
            self.assertNotIn('Proposed movie',json.loads(send.call_args.args[0].data)['text'])
            self.assertEqual(submit.call_count,2)

    def test_corrected_card_queues_once_and_background_result_never_edits(self):
        action = dict(ACTION)
        refs = [{'chat_id':'7','message_id':47,'kind':'caption'}]
        prepared = {'token':TOKEN,'text':'Corrected <b>card</b>','parse_mode':'HTML'}

        def receipt(method, body, *, edit_receipt=None):
            if edit_receipt is not None:
                edit_receipt.update(chat_id=body['chat_id'],message_id=body['message_id'])

        with (patch.object(svc,'get_action',side_effect=lambda _:dict(action)),
              patch.object(svc,'update_action',side_effect=lambda _,**kw:action.update(kw) or True),
              patch.object(ev,'reserve',return_value=True),
              patch.object(ev,'submit') as submit,
              patch.object(svc,'_telegram_request',side_effect=receipt) as request):
            svc.edit_retry_message(refs,prepared)
            svc.edit_retry_message(refs,prepared)
            self.assertEqual([c.args[0] for c in request.call_args_list],['editMessageCaption']*2)
            self.assertEqual(request.call_args.args[1]['reply_markup']['inline_keyboard'][0][0]['url'],URL)
            submit.assert_called_once()
            name,callback = submit.call_args.args
            self.assertEqual(name,REQUEST)
            callback(ev.Evaluation('Full evaluation'))
            self.assertEqual(request.call_args.args[0],'sendMessage')
            self.assertEqual(request.call_args.args[1]['reply_parameters']['message_id'],47)
            self.assertNotIn('message_thread_id',request.call_args.args[1])

    def test_retry_reply_uses_topic_from_edit_ack_instead_of_current_setting(self):
        action = dict(ACTION)
        refs = [{'chat_id':'7','message_id':123,'kind':'caption'}]
        prepared = {'token':TOKEN,'text':'Corrected card','parse_mode':'HTML'}
        with (patch.dict(os.environ,{'TELEGRAM_ADD_GRAB_TOPIC_ID':'333'}),
              patch.object(svc,'get_action',return_value=action),
              patch.object(svc,'update_action',return_value=True),
              patch.object(ev,'reserve',return_value=True),
              patch.object(ev,'submit') as submit,
              patch.object(svc,'urlopen',side_effect=lambda *a,**kw:self.telegram_response()) as send):
            svc.edit_retry_message(refs,prepared)
            _,callback = submit.call_args.args
            callback(ev.Evaluation('Result'))
        reply = json.loads(send.call_args.args[0].data)
        self.assertEqual(reply['message_thread_id'],89)
        self.assertEqual(reply['reply_parameters']['message_id'],123)

    def test_uncertain_legacy_topic_does_not_send_elsewhere(self):
        refs = [{'chat_id':'7','message_id':123,'kind':'caption'}]
        prepared = {'token':TOKEN,'text':'Corrected card','parse_mode':'HTML'}
        response = io.BytesIO(b'{"ok":true,"result":{"chat":{"id":7,"is_forum":true,"type":"supergroup"},"message_id":123}}')
        response.status = 200
        with (patch.object(svc,'get_action',return_value=ACTION),
              patch.object(ev,'reserve',return_value=True), patch.object(ev,'release') as release,
              patch.object(ev,'submit') as submit,
              patch.object(svc,'urlopen',return_value=response) as send):
            svc.edit_retry_message(refs,prepared)
        send.assert_called_once()
        self.assertIn('when available',json.loads(send.call_args.args[0].data)['caption'])
        submit.assert_not_called()
        release.assert_called_once()


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(pending_actions,'STORE_PATH',Path(directory.name)/'actions.json'))
        stack.enter_context(patch.object(svc,'radarr_configured',return_value=True))
        stack.enter_context(patch.object(svc,'reviewed_action_current',return_value=True))
        stack.enter_context(patch.object(svc,'selection_context',return_value={
            'roots':[{'path':'/movies'}],'profiles':[{'id':1}]}))
        stack.enter_context(patch.object(svc,'ensure_movie',return_value=({'id':9,'tmdbId':META['tmdb_id']},True)))
        self.token = svc.create_pending_action(PAYLOAD,META)

    def post(self, watched=False):
        body = b'root_folder=%2Fmovies&quality_profile=1'
        if watched:
            body = b'confirm_watched=yes&'+body
        handler = object.__new__(svc.Handler)
        handler._html = Mock()
        handler.rfile = io.BytesIO(body)
        handler.headers = {'Content-Length':str(len(body))}
        handler._handle_action_post(self.token,watched=watched)
        return handler._html.call_args.args[0]

    def test_feedback_only_after_confirmed_push_and_once(self):
        order = []
        with (patch.object(svc,'push_release',side_effect=lambda *a,**kw:order.append('accepted')),
              patch.object(ev,'_post',side_effect=lambda *a:order.append(a) or (201,b'{}'))):
            self.assertEqual(self.post(),200)
            self.assertEqual(self.post(),410)
        self.assertEqual(order,['accepted',('/feedback',{
            'imdb_id':META['imdb_id'],'tmdb_id':META['tmdb_id'],'title':META['title'],
            'decision':'watch','note':'Grabbed via Telegram'},4)])

    def test_failed_grab_and_watched_action_do_not_post_feedback(self):
        with (patch.object(svc,'push_release',side_effect=ReleaseRejected('invented rejection')),
              patch.object(svc,'watched_movie',return_value={'id':9}),
              patch.object(svc,'ensure_watched_movie'),
              patch.object(ev,'_post') as request):
            self.assertEqual(self.post(),502)
            self.assertEqual(self.post(watched=True),200)
            request.assert_not_called()

    def test_feedback_timeout_does_not_change_grab_success_or_retry(self):
        with (patch.object(svc,'push_release') as push,
              patch.object(ev,'_post',side_effect=TimeoutError) as feedback):
            self.assertEqual(self.post(),200)
            self.assertEqual(self.post(),410)
            push.assert_called_once()
            feedback.assert_called_once()
