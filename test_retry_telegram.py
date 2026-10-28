import copy
import os
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.error import HTTPError
import retry_telegram as nt
import movie_intel_service as svc
import pending_actions
from identity_retry import RetryStore,run_one
from identity_triage_observer import envelope
from test_identity_triage import payload,SOURCES
from test_identity_automation import context
from test_movie_intel_actions import PAYLOAD,META

class RetryMessageTests(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=time.time();self.store=RetryStore(Path(self.tmp.name).resolve()/'retry',clock=lambda:self.now)
        self.p=payload();self.p['data']['release']['download_url']='https://tracker.invalid/download/private'
        self.item={'observation':envelope(self.p,context(),SOURCES)}
        self.refs=[{'chat_id':'123','message_id':17,'kind':'text'}]
        self.store.admit(self.item,SOURCES)
    def bind(self):self.assertTrue(nt.bind(self.store,self.p,context(),self.refs,SOURCES))
    def success(self):
        self.now+=901;run_one(self.store,lambda p:context('external_id_verified','verified_tmdb'))
    def test_receipts_are_only_from_bot_response_and_thread_capture(self):
        with nt.capture() as refs:
            nt.receipt('sendMessage',{'chat_id':'123'},{'result':{'chat':{'id':123},'message_id':17}})
            nt.receipt('sendPhoto',{'chat_id':'123'},{'result':{'chat':{'id':456},'message_id':18}})
            nt.receipt('sendMessage',{'chat_id':'123'},{'result':{}})
        self.assertEqual(refs,self.refs)
    def test_success_durable_before_or_after_binding(self):
        self.success();self.bind();self.store=RetryStore(self.store.directory,clock=lambda:self.now)
        prepare=Mock(return_value={'text':'resolved','token':None});edit=Mock()
        self.assertTrue(nt.pump(self.store,prepare,edit));self.assertFalse(nt.pump(self.store,prepare,edit))
        self.assertEqual(prepare.call_args.args[0]['data']['release']['download_url'],self.p['data']['release']['download_url'])
        self.assertEqual(edit.call_args.args[0],self.refs)
    def test_failed_edit_reuses_prepared_action_after_restart(self):
        self.bind();self.success();prepare=Mock(return_value={'text':'resolved','token':'same'})
        nt.pump(self.store,prepare,Mock(side_effect=OSError()))
        self.now+=61;self.store=RetryStore(self.store.directory,clock=lambda:self.now);edit=Mock()
        nt.pump(self.store,prepare,edit)
        self.assertEqual(prepare.call_count,1);self.assertEqual(edit.call_args.args[1]['token'],'same')
    def test_five_failed_edits_stop_without_repeating_preparation(self):
        self.bind();self.success();prepare=Mock(return_value={});edit=Mock(side_effect=OSError())
        for _ in range(5):nt.pump(self.store,prepare,edit);self.now+=4000
        self.assertFalse(nt.pump(self.store,prepare,edit));self.assertEqual(prepare.call_count,1)
    def test_retry_expiry_edits_review_without_provider_calls(self):
        self.bind();self.now+=7*86400+1
        resolve=Mock();self.assertFalse(run_one(self.store,resolve));resolve.assert_not_called()
        prepare=Mock(return_value={});nt.pump(self.store,prepare,Mock())
        self.assertEqual(prepare.call_args.args[2],'retry_exhausted')
    def test_attempt_exhaustion_and_unknown_legacy_receipts(self):
        self.bind()
        for delay in (901,3601,21601):
            self.now+=delay;run_one(self.store,lambda p:context())
        prepare=Mock(return_value={});self.assertTrue(nt.pump(self.store,prepare,Mock()))
        self.assertEqual(prepare.call_args.args[2],'retry_exhausted')
        with self.store.tx() as c:c.execute('update retry_messages set refs=NULL,state="waiting"')
        self.assertFalse(nt.pump(self.store,Mock(),Mock()))
    def test_duplicate_binding_does_not_replace_reference_or_receipt(self):
        self.bind();self.p['data']['release']['download_url']='https://other.invalid/x';self.refs[0]['message_id']=99
        self.bind();self.success();prepare=Mock(return_value={});edit=Mock();nt.pump(self.store,prepare,edit)
        self.assertEqual(edit.call_args.args[0][0]['message_id'],17)
        self.assertIn('tracker.invalid',prepare.call_args.args[0]['data']['release']['download_url'])
        self.assertEqual(self.store.path.stat().st_mode & 0o777,0o600)
    def test_superseded_job_cannot_prepare_or_edit(self):
        self.bind();self.success()
        with self.store.tx() as c:c.execute('update retry_jobs set reason="superseded"')
        self.assertFalse(nt.pump(self.store,Mock(),Mock()))

class RetryMessageActorTests(unittest.TestCase):
    def test_success_prepares_exact_confirmation_but_never_acquires(self):
        meta=dict(META,identity_status='verified_tmdb')
        with tempfile.TemporaryDirectory() as tmp,patch.object(pending_actions,'STORE_PATH',Path(tmp)/'actions.json'), \
             patch.object(svc,'PUBLIC_BASE_URL','https://example.invalid'),patch.object(svc,'radarr_configured',return_value=True), \
             patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab:
            prepared=svc.prepare_retry_message(PAYLOAD,{'meta':meta},'external_id_verified')
            action=svc.get_action(prepared['token'])
            self.assertEqual(action['release']['download_url'],PAYLOAD['data']['release']['download_url'])
            self.assertNotIn('PRIVATE',prepared['text']);add.assert_not_called();grab.assert_not_called()
    def test_exhaustion_never_creates_download_action(self):
        with patch.object(svc,'create_pending_action') as create:
            p=svc.prepare_retry_message(PAYLOAD,{'meta':dict(META,identity_status='verified_tmdb')},'retry_exhausted')
        create.assert_not_called();self.assertIsNone(p['token']);self.assertIn('retries have ended',p['text'])
    def test_missing_reference_no_button_and_caption_bound(self):
        p=copy.deepcopy(PAYLOAD);p['data']['release'].pop('download_url');p['data']['release']['name']='🎬'*2000
        with patch.object(svc,'PUBLIC_BASE_URL','https://example.invalid'),patch.object(svc,'radarr_configured',return_value=True):
            r=svc.prepare_retry_message(p,{'meta':dict(META,identity_status='verified_tmdb')},'external_id_verified')
        self.assertIsNone(r['token']);self.assertLessEqual(len(r['text'].encode('utf-16-le'))//2,900)
    def test_text_and_caption_edits_use_original_ids_and_no_send(self):
        refs=[{'chat_id':'123','message_id':17,'kind':'text'},{'chat_id':'123','message_id':18,'kind':'caption'}]
        with patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'_telegram_request') as call,patch.object(svc,'get_action',return_value=None):
            svc.edit_retry_message(refs,{'text':'result','token':'expired'})
        self.assertEqual([c.args[0] for c in call.call_args_list],['editMessageText','editMessageCaption'])
        self.assertEqual([c.args[1]['message_id'] for c in call.call_args_list],[17,18])
        self.assertEqual(call.call_args_list[0].args[1]['reply_markup'],{'inline_keyboard':[]})
    def test_changed_chat_blocked_and_uncertain_actions_not_reoffered(self):
        refs=[{'chat_id':'123','message_id':17,'kind':'text'}]
        with patch.object(svc,'TELEGRAM_CHAT_ID','456'),patch.object(svc,'_telegram_request') as call:
            with self.assertRaises(ValueError):svc.edit_retry_message(refs,{'text':'x','token':None})
        call.assert_not_called()
        for status in ('executing','needs_review'):
            with patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'get_action',return_value={'status':status}),patch.object(svc,'_telegram_request') as call:
                svc.edit_retry_message(refs,{'text':'x','token':'token'})
                self.assertEqual(call.call_args.args[1]['reply_markup'],{'inline_keyboard':[]})
    def test_lost_edit_ack_is_idempotent(self):
        error=HTTPError('https://example.invalid',400,'Bad Request',{},io.BytesIO(json.dumps({'description':'Bad Request: message is not modified'}).encode()))
        with patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'_telegram_request',side_effect=error):
            svc.edit_retry_message([{'chat_id':'123','message_id':17,'kind':'text'}],{'text':'x','token':None})

class TelegramTransportIntegrationTests(unittest.TestCase):
    def test_real_local_transport_captures_receipt_and_edits_same_message(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import Request,urlopen
        import threading
        seen=[]
        class API(BaseHTTPRequestHandler):
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));seen.append((self.path,body))
                raw=json.dumps({'ok':True,'result':{'message_id':42,'chat':{'id':123}}}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),API)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            def local(req,timeout):
                return urlopen(Request('http://127.0.0.1:'+str(server.server_port)+'/'+req.full_url.rsplit('/',1)[-1],data=req.data,headers={'Content-Type':'application/json'}),timeout=timeout)
            with patch.object(svc,'TELEGRAM_BOT_TOKEN','fake-local-only'),patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'urlopen',side_effect=local):
                with nt.capture() as refs:svc.send_telegram('Retrying')
                svc.edit_retry_message(refs,{'text':'Identified','token':None})
                svc.edit_retry_message(refs,{'text':'<b>Identified</b>','parse_mode':'HTML','poster_url':'https://image.invalid/poster.jpg','token':None})
            self.assertEqual([p for p,b in seen],['/sendMessage','/editMessageText','/editMessageMedia'])
            self.assertEqual(seen[2][1]['media']['caption'],'<b>Identified</b>')
            self.assertEqual(seen[2][1]['message_id'],42)
            self.assertEqual(seen[1][1]['message_id'],42)
            self.assertEqual(seen[1][1]['text'],'Identified')
        finally:server.shutdown();server.server_close();thread.join()


class AlternativeRetryRecoveryTests(unittest.TestCase):
    setUp=RetryMessageTests.setUp
    bind=RetryMessageTests.bind
    success=RetryMessageTests.success
    def test_original_quality_reasons_and_source_guards_survive_binding(self):
        from test_alternative_grab import PAYLOAD as ALT
        p=copy.deepcopy(ALT)
        p['data']['indexer']['name']='TorrentLeech';p['data']['release']['external_id']='123';p['data']['release']['implementation']='IRC'
        p['data']['release']['season']=1
        p['data']['result']['rejections'].append('Quality not allowed')
        item=nt.binding(p,context(),self.refs,{'torrentleech':'TorrentLeech'})
        original=json.loads(item['payload'])
        self.assertEqual(original['data']['result'],p['data']['result'])
        self.assertEqual(original['data']['action'],{'type':'RADARR'})
        self.assertEqual(original['data']['release']['season'],1)
        self.assertEqual(original['_retry_original_event'],1)

    def test_durable_binding_does_not_need_sqlite_and_survives_restart(self):
        with patch.object(self.store,'tx',side_effect=RuntimeError('database busy')):
            self.assertTrue(nt.queue_binding(self.store.directory,self.p,context(),self.refs,SOURCES))
        self.success()
        self.store=RetryStore(self.store.directory,clock=lambda:self.now)
        prepare=Mock(return_value={});edit=Mock()
        self.assertTrue(nt.pump(self.store,prepare,edit))
        self.assertEqual(edit.call_args.args[0],self.refs)
        self.assertFalse(list((self.store.directory/'message-bindings').glob('*.json')))

    def test_failed_database_flush_retains_receipt_and_duplicate_keeps_first(self):
        nt.queue_binding(self.store.directory,self.p,context(),self.refs,SOURCES)
        nt.queue_binding(self.store.directory,self.p,context(),[dict(self.refs[0],message_id=99)],SOURCES)
        with patch.object(nt,'save_binding',side_effect=OSError()):
            with self.assertRaises(OSError):nt.flush_binding(self.store)
        self.assertEqual(len(list((self.store.directory/'message-bindings').glob('*.json'))),1)
        self.success();edit=Mock();nt.pump(self.store,Mock(return_value={}),edit)
        self.assertEqual(edit.call_args.args[0][0]['message_id'],17)

    def test_quality_recovery_prepares_alternative_not_add_grab(self):
        from test_alternative_grab import PAYLOAD as ALT,CURRENT,MOVIE
        import alternative_grab as alt
        p=copy.deepcopy(ALT);p['data']['indexer']['name']='TorrentLeech';p['data']['release']['external_id']='123';p['data']['release']['implementation']='IRC'
        sources={'torrentleech':'TorrentLeech'}
        self.store.admit({'observation':envelope(p,context(),sources)},sources)
        nt.queue_binding(self.store.directory,p,context(),self.refs,sources)
        self.now+=901
        # Finish both the base fixture and the actual alternative job.
        for _ in range(2):run_one(self.store,lambda _:dict(context('external_id_verified','verified_tmdb'),meta=MOVIE))
        with patch.object(pending_actions,'STORE_PATH',Path(self.tmp.name)/'actions.json'), \
             patch.dict(os.environ,{alt.CONFIG:'synthetic-config'}),patch.object(alt,'get_movie_by_tmdb',return_value=CURRENT), \
             patch.object(svc,'PUBLIC_BASE_URL','https://example.invalid'),patch.object(svc,'radarr_configured',return_value=True), \
             patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as push:
            edit=Mock();self.assertTrue(nt.pump(self.store,svc.prepare_retry_message,edit))
            prepared=edit.call_args.args[1];action=svc.get_action(prepared['token'])
            self.assertEqual(action['kind'],'alternative')
            self.assertEqual(action['rejections'],p['data']['result']['rejections'])
            self.assertEqual(action['release']['download_url'],p['data']['release']['download_url'])
            self.assertEqual(edit.call_args.args[0],self.refs)
            add.assert_not_called();push.assert_not_called()

    def test_legacy_fabricated_unknown_movie_cannot_offer_acquisition(self):
        self.bind();self.success()
        with self.store.tx() as c:
            version,raw=c.execute('select version,payload from retry_messages').fetchone()
            p=json.loads(raw);p.pop('_retry_original_event')
            c.execute('update retry_messages set payload=? where version=?',(json.dumps(p),version))
        with patch.object(svc,'create_pending_action') as create,patch.object(svc,'create_identity_review') as review:
            self.assertTrue(nt.pump(self.store,svc.prepare_retry_message,Mock()))
        create.assert_not_called();review.assert_not_called()

    def test_unavailable_message_explains_temporary_lookup(self):
        from test_alternative_grab import PAYLOAD as ALT
        text=svc.alternative_unavailable_message(ALT,{'identity_status':'unresolved','identity_reason':'listing_temporary_http'})
        self.assertIn('temporarily unavailable',text)
        self.assertIn('metadata lookup failed',text)
        self.assertNotIn('unchanged existing file',text)

    def test_actor_queues_receipt_without_opening_retry_database(self):
        (Path(self.tmp.name)/'.local/state').mkdir(parents=True)
        with patch.dict(os.environ,{'MOVIE_INTEL_IDENTITY_RETRY_MODE':'active','MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG':'synthetic'}), \
             patch('identity_triage_observer.read_config',return_value={'sources':SOURCES}), \
             patch.object(svc.Path,'home',return_value=Path(self.tmp.name)), \
             patch('identity_retry.RetryStore',side_effect=AssertionError('must not open database')):
            svc.bind_retry_message(self.p,context(),self.refs)
        paths=list((Path(self.tmp.name)/'.local/state/movie-identity-retries/message-bindings').glob('*.json'))
        self.assertEqual(len(paths),1)
        self.assertEqual(json.loads(paths[0].read_text())['refs'],json.dumps(self.refs))

    def test_recovered_mixed_rejection_and_tv_guard_do_not_offer_action(self):
        from test_alternative_grab import PAYLOAD as ALT,CURRENT,MOVIE
        import alternative_grab as alt
        for guard in ('mixed','season'):
            p=copy.deepcopy(ALT)
            p['data']['indexer']['name']='TorrentLeech'
            p['data']['release'].update(external_id='123',implementation='IRC')
            if guard=='mixed':p['data']['result']['rejections'].append('Quality not allowed')
            else:p['data']['release']['season']=1
            original=json.loads(nt.binding(p,context(),self.refs,{'torrentleech':'TorrentLeech'})['payload'])
            with patch.dict(os.environ,{alt.CONFIG:'synthetic'}),patch.object(alt,'get_movie_by_tmdb',return_value=CURRENT), \
                 patch.object(svc,'PUBLIC_BASE_URL','https://example.invalid'),patch.object(svc,'radarr_configured',return_value=True), \
                 patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as push:
                prepared=svc.prepare_retry_message(original,{'meta':MOVIE},'external_id_verified')
            self.assertIsNone(prepared['token']);add.assert_not_called();push.assert_not_called()


class RetryPresentationTests(unittest.TestCase):
    def prepared(self,**changes):
        meta=dict(META,identity_status='verified_tmdb',**changes)
        with patch.object(svc,'create_pending_action',return_value='same-token'),patch.object(svc,'PUBLIC_BASE_URL','https://example.invalid'),patch.object(svc,'INDEX',{}):
            return svc.prepare_retry_message(PAYLOAD,{'meta':meta},'external_id_verified')

    def test_verified_retry_uses_standard_message_and_poster(self):
        prepared=self.prepared()
        self.assertIn('ℹ️ Identified; not in the local Movie List catalog. Ratings and recognition unavailable locally.',prepared['text'])
        self.assertNotIn('Open the confirmation page',prepared['text'])
        self.assertNotIn('Identity verification succeeded after retry',prepared['text'])
        self.assertEqual(prepared['poster_url'],META['poster_url'])
        self.assertEqual(prepared['parse_mode'],'HTML')
        self.assertEqual(prepared['token'],'same-token')

    def test_text_message_becomes_poster_in_place_without_new_send(self):
        prepared=self.prepared()
        with patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'get_action',return_value={'status':'pending'}),patch.object(svc,'_telegram_request') as request:
            svc.edit_retry_message([{'chat_id':'123','message_id':42,'kind':'text'}],prepared)
        method,body=request.call_args.args
        self.assertEqual(method,'editMessageMedia');self.assertEqual(body['message_id'],42)
        self.assertEqual(body['media']['media'],META['poster_url'])
        self.assertEqual(body['media']['caption'],prepared['text'])
        self.assertEqual(body['media']['parse_mode'],'HTML')
        self.assertNotIn('message_thread_id',body);self.assertEqual(request.call_count,1)

    def test_repeated_media_edit_ack_is_idempotent(self):
        prepared=self.prepared()
        error=HTTPError('https://example.invalid',400,'Bad Request',{},io.BytesIO(json.dumps({'description':'Bad Request: message is not modified'}).encode()))
        with patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'get_action',return_value={'status':'pending'}),patch.object(svc,'_telegram_request',side_effect=error) as request:
            svc.edit_retry_message([{'chat_id':'123','message_id':42,'kind':'text'}],prepared)
        self.assertEqual(request.call_args.args[0],'editMessageMedia')

    def test_missing_poster_keeps_text_and_expired_approval_stays_removed(self):
        prepared=self.prepared(poster_url=None)
        with patch.object(svc,'TELEGRAM_CHAT_ID','123'),patch.object(svc,'get_action',return_value=None),patch.object(svc,'_telegram_request') as request:
            svc.edit_retry_message([{'chat_id':'123','message_id':42,'kind':'text'}],prepared)
        method,body=request.call_args.args
        self.assertEqual(method,'editMessageText');self.assertEqual(body['reply_markup'],{'inline_keyboard':[]})

    def test_long_caption_does_not_cut_html_tags_or_entities(self):
        prepared=self.prepared(title='An & unusual <title> '+'🎬'*900)
        self.assertIsNone(prepared['parse_mode'])
        self.assertLessEqual(len(prepared['text'].encode('utf-16-le'))//2,900)
        self.assertIn('An & unusual <title>',prepared['text'])
