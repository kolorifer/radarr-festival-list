"""Invented evaluator and Telegram replies. No live requests."""
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import movie_intel_service as svc
import pending_actions
from radarr_client import ReleaseRejected
import telegram_evaluator as ev
from test_movie_intel_actions import META, PAYLOAD


TOKEN = 'A'*32
URL = 'https://public.invalid/action/'+TOKEN
NAME = '  Exact.Film.2021.1080p.<Remux>.GROÜP  '
ACTION = {'movie':META,'release':{'name':NAME}}


class EvaluatorClientTests(unittest.TestCase):
    def test_rated_feedback_uses_exact_decision_and_note(self):
        for decision in ('watch','skip'):
            with patch.object(ev,'_post',return_value=(200,b'{}')) as post:
                self.assertEqual(ev.watched_feedback(META,decision=decision,note='watched'),'recorded')
            post.assert_called_once_with('/feedback',{
                'imdb_id':META['imdb_id'],'tmdb_id':META['tmdb_id'],'title':META['title'],
                'decision':decision,'note':'watched'},4)

    def test_exact_release_only_and_complete_safe_json(self):
        body = {'identification':{'title':'A < B'},'ratings':{'rating':8},'recognition':[],
                'decision_aid':{'reason':'See https://private.invalid/download'},
                'cached':False,'api_key':'invented credential',
                'https://private.invalid/key':42}
        with patch.object(ev,'_post',return_value=(200,json.dumps(body).encode())) as post:
            result = ev.evaluation(NAME)
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
            result = ev.evaluation(NAME)
        self.assertIn('HTTP 422',result)
        self.assertEqual(json.loads(result.split('\n',1)[1]),detail)
        with patch.object(ev,'_post',return_value=(502,b'Error\nAuthorization: Bearer invented-token\nlast line')):
            result = ev.evaluation(NAME)
        self.assertIn('last line',result)
        self.assertNotIn('invented-token',result)
        with patch.object(ev,'_post',side_effect=TimeoutError) as post:
            self.assertIn('timed out',ev.evaluation(NAME))
            post.assert_called_once()
        with patch.object(ev,'_post',return_value=(200,b'a'*(ev.MAX_REPLY+1))):
            self.assertIn('exceeded',ev.evaluation(NAME))

    def test_compound_credential_keys_and_labels_are_redacted(self):
        body = {'access_token':'PRIVATE_ONE','clientSecret':'PRIVATE_TWO',
                'details':"refresh_token: PRIVATE_THREE\napi_key: 'PRIVATE FOUR'",
                'token_count':17}
        with patch.object(ev,'_post',return_value=(200,json.dumps(body).encode())):
            result = ev.evaluation(NAME)
        parsed = json.loads(result.split('\n',1)[1])
        self.assertEqual(parsed['access_token'],'[redacted]')
        self.assertEqual(parsed['clientSecret'],'[redacted]')
        self.assertEqual(parsed['token_count'],17)
        self.assertNotIn('PRIVATE_',result)
        self.assertNotIn('PRIVATE FOUR',result)
        plain = b'clientSecret=PRIVATE_FIVE\naccess_token: PRIVATE_SIX\nEOF'
        with patch.object(ev,'_post',return_value=(502,plain)):
            result = ev.evaluation(NAME)
        self.assertNotIn('PRIVATE_',result)
        self.assertTrue(result.endswith('EOF'))

    def test_unexpected_evaluator_failure_still_delivers_error(self):
        deliver = Mock()
        with (patch.object(ev,'_QUEUE',Mock(**{'get.side_effect':[(NAME,deliver),StopIteration]})),
              patch.object(ev,'evaluation',side_effect=RuntimeError('private invented detail')),
              patch.object(ev,'release') as release):
            with self.assertRaises(StopIteration):
                ev._run()
        deliver.assert_called_once_with('Evaluator failed before a complete reply was available.')
        release.assert_called_once()

    def test_reserved_queue_entry_is_evaluated_when_taken(self):
        deliver = Mock()
        with (patch.object(ev,'_QUEUE',Mock(**{'get.side_effect':[(NAME,deliver),StopIteration]})),
              patch.object(ev,'evaluation',return_value='result') as evaluate, patch.object(ev,'release')):
            with self.assertRaises(StopIteration):
                ev._run()
        evaluate.assert_called_once_with(NAME)
        deliver.assert_called_once_with('result')


class TelegramEvaluationTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(svc,'TELEGRAM_CHAT_ID','7'))
        stack.enter_context(patch.object(svc,'TELEGRAM_BOT_TOKEN','INVENTED'))
        stack.enter_context(patch.object(svc,'PUBLIC_BASE_URL','https://public.invalid'))
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
            self.assertEqual(name,NAME)
            callback('Evaluator result\n<invented>')
        self.assertEqual(methods,['sendPhoto','sendMessage','sendMessage'])

    def test_overflow_is_full_private_thread_attachment(self):
        result = 'Result\n'+'<invented>🍿'*1000
        with patch.object(svc,'urlopen',return_value=self.telegram_response()) as send:
            svc._evaluation_reply({'chat_id':'7','message_id':22,'message_thread_id':89},result)
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
            self.assertEqual(name,NAME)
            callback('Full evaluation')
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
            callback('Result')
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
