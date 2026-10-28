"""Synthetic tracker conflicts; no live providers or acquisition."""
from copy import deepcopy
import json
import os
from unittest.mock import Mock, patch
from test_identity_automation import Base, context
from test_identity_triage import payload
from identity_triage_observer import envelope
from identity_retry import RetryStore, run_one, conflict_item, TRACKER_CONFLICTS
from identity_request_guard import fresh_metadata, fresh_metadata_required
import retry_telegram
import tracker_metadata as tracker
import tmdb_resolver as tmdb

SOURCES={'torrentleech':'TorrentLeech'}

class ConflictRecheckTests(Base):
    def setUp(self):
        super().setUp()
        self.p=payload(meta_imdb=None,info_url='https://www.torrentleech.org/torrent/123')
        self.p['event']='action.rejected'
        self.p['data']['indexer']={'identifier':'torrentleech','name':'TorrentLeech'}
        self.p['data']['result']={'rejections':['Unknown Movie']}
        self.ctx=context('local_identity_conflict','needs_review')
        self.item={'observation':envelope(self.p,self.ctx,SOURCES),'listing':self.p['data']['release']['info_url']}
        self.s=RetryStore(self.root/'retry',clock=lambda:self.now)

    def test_one_conflict_recheck_after_15_minutes_and_restart(self):
        for reason in TRACKER_CONFLICTS-{'runtime_conflict'}: # runtime maps to identity_conflict on wire
            with self.subTest(reason=reason):
                s=RetryStore(self.root/reason,clock=lambda:self.now)
                item=deepcopy(self.item);item['observation']['data']['outcome']['reason']=reason
                self.assertEqual(s.admit(item,SOURCES),'admitted')
                self.now+=899;self.assertIsNone(s.lease())
                self.now+=1;s=RetryStore(s.directory,clock=lambda:self.now)
                resolver=Mock(return_value=context(reason,'needs_review'))
                self.assertTrue(run_one(s,resolver));self.assertEqual(resolver.call_count,1)
                self.assertEqual(s.admit(item,SOURCES),'duplicate')
                self.now+=86401;self.assertFalse(run_one(s,resolver))
                self.assertEqual(resolver.call_count,1)

    def test_corrected_source_preserves_initial_evidence_and_no_acquisition(self):
        self.s.admit(self.item,SOURCES);self.now+=900
        def corrected(p):
            self.assertTrue(fresh_metadata_required())
            return dict(context('external_id_verified','verified_tmdb'),review_listing={'reason':'listing_id_found'})
        with patch('movie_intel_service.ensure_movie') as add,patch('movie_intel_service.push_release') as grab,patch('movie_intel_service.send_telegram') as send:
            run_one(self.s,corrected)
        add.assert_not_called();grab.assert_not_called();send.assert_not_called()
        self.assertFalse(fresh_metadata_required())
        with self.s.tx() as c:
            body,state,reason=c.execute('select body,state,reason from retry_jobs').fetchone()
            self.assertEqual(json.loads(body),self.item);self.assertEqual((state,reason),('done','external_id_verified'))
            self.assertEqual(json.loads(c.execute('select context from retry_messages').fetchone()[0])['review_listing']['reason'],'listing_id_found')

    def test_native_assertions_wrong_source_or_listing_do_not_retry(self):
        for field,value in [('meta_imdb','tt1234567'),('meta_tmdb',123),('external_id','999')]:
            item=deepcopy(self.item);item['observation']['data']['release'][field]=value
            self.assertFalse(conflict_item(item))
        item=deepcopy(self.item);item.pop('listing');self.assertFalse(conflict_item(item))
        item=deepcopy(self.item);item['observation']['data']['indexer']['identifier']='other';self.assertFalse(conflict_item(item))
        item=deepcopy(self.item);item['observation']['data']['outcome']['reason']='invalid_external_id'
        self.assertEqual(self.s.admit(item,SOURCES),'not_retryable')

    def test_zero_request_budget_deferral_does_not_consume_recheck(self):
        from identity_request_guard import reserve
        self.s.admit(self.item,SOURCES);self.now+=900
        with self.s.tx() as c:
            for _ in range(20):c.execute('insert into retry_requests values(NULL,?,?,?)',('older','listing',self.now))
        def unavailable(p):
            try:reserve('listing')
            except Exception:pass
            return context()
        with patch('identity_retry.time.sleep'):run_one(self.s,unavailable)
        self.assertEqual(self.s.summary()['states'],{'pending':1});self.assertIsNone(self.s.lease())
        self.now+=86401
        lease=self.s.lease();self.assertEqual(lease['number'],1)

    def test_conflict_receipt_recovery_keeps_original_rejection_and_edits_only_original(self):
        self.p['data']['result']['rejections']=['Existing file on disk has a equal or higher Custom Format score: 0']
        refs=[{'chat_id':'123','message_id':17,'kind':'text'}]
        self.assertTrue(retry_telegram.bind(self.s,self.p,self.ctx,refs,SOURCES))
        self.s.admit(self.item,SOURCES);self.now+=900
        run_one(self.s,lambda p:self.ctx)
        prepare=Mock(return_value={'text':'review','token':None});edit=Mock()
        self.assertTrue(retry_telegram.pump(self.s,prepare,edit))
        self.assertEqual(prepare.call_args.args[0]['data']['result'],self.p['data']['result'])
        self.assertEqual(edit.call_args.args[0],refs)
        self.assertFalse(retry_telegram.pump(self.s,prepare,edit))

    def test_fresh_scope_bypasses_tracker_cache_and_resets_on_exception(self):
        tracker._CACHE.clear();tracker._NEXT_REQUEST=0
        release=self.p['data']['release'];indexer=self.p['data']['indexer']
        with patch.dict(os.environ,{'MOVIE_INTEL_TL_METADATA_ENABLED':'1'}),patch.object(tracker,'cookie_file',return_value={}),patch.object(tracker,'_fetch',side_effect=[{'imdb_id':'tt1234567'},{'imdb_id':'tt7654321'}]) as fetch,patch.object(tracker.time,'monotonic',side_effect=[100,100,102,102]):
            self.assertEqual(tracker.lookup_listing(release,indexer)['imdb_id'],'tt1234567')
            with fresh_metadata():self.assertEqual(tracker.lookup_listing(release,indexer)['imdb_id'],'tt7654321')
            self.assertEqual(fetch.call_count,2)
        try:
            with fresh_metadata():raise ValueError()
        except ValueError:pass
        self.assertFalse(fresh_metadata_required())
        tracker._CACHE.clear();tracker._NEXT_REQUEST=0

    def test_fresh_scope_bypasses_persistent_and_memory_tmdb_caches(self):
        tmdb._ID_CACHE.clear()
        good={'identity_status':'verified_tmdb','tmdb_id':123,'imdb_id':'tt1234567','matched_release_year':'2025'}
        with patch.object(tmdb,'_resolve_external',return_value=good),patch('verified_identity_cache.get',return_value=None),patch('verified_identity_cache.put'):
            tmdb.resolve_external_movie('Synthetic',2025,imdb_id='tt1234567')
        with fresh_metadata(),patch.object(tmdb,'_resolve_external',return_value={'identity_status':'needs_review','identity_reason':'year_conflict'}) as resolve,patch('verified_identity_cache.get') as cache:
            result=tmdb.resolve_external_movie('Synthetic',2025,imdb_id='tt1234567')
        resolve.assert_called_once();cache.assert_not_called();self.assertEqual(result['identity_status'],'needs_review')
        tmdb._ID_CACHE.clear()

    def test_actor_rechecks_corrected_listing_without_inheriting_old_asserted_id(self):
        import movie_intel_service as svc
        from test_source_identity_guard import listing
        corrected=listing('1 h 44 min');corrected['imdb_id']='tt7654321'
        self.item['observation']['data']['outcome']['asserted_imdb']='tt1234567'
        self.s.admit(self.item,SOURCES);self.now+=900
        meta={'identity_status':'verified_tmdb','identity_reason':'external_id_verified','imdb_id':'tt7654321',
              'tmdb_id':123,'title':'Synthetic Movie','year':2025,'runtime':104}
        with patch.object(svc,'INDEX',{}),patch.object(svc,'lookup_listing',return_value=corrected),patch.object(svc,'resolve_external_movie',return_value=meta) as resolve,patch.object(svc,'get_movie_by_tmdb',return_value={}),patch('identity_memory.observe'),patch('identity_memory.packet',return_value=None),patch.object(svc,'create_action') as action,patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab:
            run_one(self.s,svc.build_movie_context)
        self.assertEqual(resolve.call_args.kwargs['imdb_id'],'tt7654321')
        self.assertEqual(self.s.summary()['reasons'],{'external_id_verified':1})
        action.assert_not_called();add.assert_not_called();grab.assert_not_called()

    def test_actor_unchanged_runtime_conflict_remains_blocked_after_recheck(self):
        import movie_intel_service as svc
        from test_source_identity_guard import listing
        self.ctx=context('identity_conflict','needs_review')
        self.item['observation']=envelope(self.p,self.ctx,SOURCES)
        self.s.admit(self.item,SOURCES);self.now+=900
        meta={'identity_status':'verified_tmdb','identity_reason':'external_id_verified','imdb_id':'tt33498897',
              'tmdb_id':123,'title':'Synthetic Movie','year':2025,'runtime':126}
        with patch.object(svc,'INDEX',{}),patch.object(svc,'lookup_listing',return_value=listing('2 h 18 min')),patch.object(svc,'resolve_external_movie',return_value=meta),patch('identity_memory.observe'),patch('identity_memory.packet',return_value=None),patch.object(svc,'get_movie_by_tmdb') as radarr:
            run_one(self.s,svc.build_movie_context)
        radarr.assert_not_called()
        self.assertEqual(self.s.summary()['reasons'],{'identity_conflict':1})
        self.now+=90000;self.assertFalse(run_one(self.s,Mock()))
