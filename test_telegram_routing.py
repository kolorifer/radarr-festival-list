import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import movie_intel_service as svc
from telegram_routing import notification_route,topic_fields
from deployment_config import configuration_errors
from test_deployment_config import VALID

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict('os.environ',{'TELEGRAM_ADD_GRAB_TOPIC_ID':'1466','TELEGRAM_GRAB_ANYWAY_TOPIC_ID':'1468'})
        self.env.start();self.addCleanup(self.env.stop)
    def test_defaults_and_nested_isolation(self):
        self.assertEqual(topic_fields('458')['message_thread_id'],458)
        with notification_route('add_grab'):
            self.assertEqual(topic_fields('458')['message_thread_id'],1466)
            with notification_route('alternative'):self.assertEqual(topic_fields('458')['message_thread_id'],1468)
            self.assertEqual(topic_fields('458')['message_thread_id'],1466)
        self.assertEqual(topic_fields('458')['message_thread_id'],458)
    def test_concurrent_routes_never_leak(self):
        def call(kind):
            with notification_route(kind):return topic_fields('458')['message_thread_id']
        with ThreadPoolExecutor(4) as pool:self.assertEqual(list(pool.map(call,['add_grab','alternative']*20)),[1466,1468]*20)
        self.assertEqual(topic_fields('458')['message_thread_id'],458)
    def test_photo_fallback_chunks_and_supplemental_share_route(self):
        for kind,topic in [('alternative',1468),('add_grab',1466)]:
            with self.subTest(kind=kind), patch.object(svc,'get_action',return_value={'kind':kind}),patch.object(svc,'_telegram_request',return_value=200) as send:
                svc.send_movie_notification('line\n'*1500,'https://example.org/poster','https://example.org/action/token')
                self.assertGreater(len(send.call_args_list),2)
                self.assertTrue(all(c.args[1]['message_thread_id']==topic for c in send.call_args_list))
            calls=[]
            def transport(method,body):
                calls.append((method,body))
                if method=='sendPhoto':raise RuntimeError('image failed')
                return 200
            with notification_route(kind),patch.object(svc,'_telegram_request',side_effect=transport):svc.send_movie_notification('short','https://example.org/poster')
            self.assertEqual([body['message_thread_id'] for _,body in calls],[topic,topic])
    def test_unresolved_unknowns_routed_before_action_exists(self):
        payload={'data':{'result':{'rejections':['Unknown Movie']}}}
        with notification_route(svc.notification_kind(payload)),patch.object(svc,'_telegram_request',return_value=200) as send:
            svc.send_movie_notification('retrying')
            self.assertEqual(send.call_args.args[1]['message_thread_id'],1466)
    def test_old_receipts_edit_original_without_topic_or_send(self):
        with patch.object(svc,'TELEGRAM_CHAT_ID','-100'),patch.object(svc,'_telegram_request',return_value=200) as send:
            svc.edit_retry_message([{'chat_id':'-100','message_id':123,'kind':'text'}],{'text':'updated','token':None})
            method,body=send.call_args.args
            self.assertEqual(method,'editMessageText');self.assertEqual(body['message_id'],123)
            self.assertNotIn('message_thread_id',body)
    def test_fallback_and_configuration_validation(self):
        for key in ['TELEGRAM_ADD_GRAB_TOPIC_ID','TELEGRAM_GRAB_ANYWAY_TOPIC_ID']:
            for value in ['0','-1','invalid']:
                self.assertTrue(any(key in e for e in configuration_errors({**VALID,key:value})))
        with patch.dict('os.environ',{'TELEGRAM_ADD_GRAB_TOPIC_ID':''}),notification_route('add_grab'):
            self.assertEqual(topic_fields('458')['message_thread_id'],458)
