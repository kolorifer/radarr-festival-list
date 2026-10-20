import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import reviewed_corrections as review
from test_torrent_research_evidence import PAGE
from torrent_research_evidence import extract

class ReviewedCorrectionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()/'reviews'
        self.release={'name':'A Film 1940 BluRay','title':'A Film','year':1940,'external_id':'1','info_url':'https://www.torrentleech.org/torrent/1'}
        self.indexer={'name':'TorrentLeech','identifier':'torrentleech'}
        self.listing={'reason':'listing_id_found','imdb_id':'tt1234567','torrent_evidence':extract(BeautifulSoup(PAGE,'html.parser'))}
        self.meta={'identity_status':'needs_review','identity_source':'torrentleech_listing','identity_reason':'year_conflict'}
        self.bound=review.binding(self.release,self.indexer,self.listing,'year_conflict')
        self.record=self.bound|{'target_imdb':'tt7654321','target_tmdb':123,'review_note':'Owner explicitly approved this source evidence and identity.'}
        self.target={'identity_status':'verified_tmdb','identity_reason':'external_id_verified','imdb_id':'tt7654321','tmdb_id':123,'title':'A Film','year':'1940'}
        self.resolve=Mock(return_value=self.target)
    def apply(self):return review.apply(self.release,self.indexer,self.listing,self.meta,self.resolve,self.root)
    def test_no_decision_no_override_no_provider_call(self):
        self.assertIsNone(self.apply());self.resolve.assert_not_called()
    def test_generic_decision_roundtrip_and_revocation(self):
        ident=review.approve(self.record,self.root)
        corrected=self.apply();self.assertEqual(corrected['identity_review']['decision_id'],ident)
        self.assertEqual(corrected['imdb_id'],'tt7654321')
        self.resolve.assert_called_once_with('A Film',1940,imdb_id='tt7654321',tmdb_id=123)
        with self.assertRaises(ValueError):review.approve(self.record,self.root)
        review.revoke(ident,'Owner revoked.',self.root)
        self.assertIsNone(self.apply())
        with review.connection(self.root) as c:
            self.assertEqual(c.execute('select count(*) from decisions').fetchone()[0],1)
            self.assertEqual(c.execute('select count(*) from revocations').fetchone()[0],1)
    def test_changed_source_identity_title_year_or_evidence_requires_new_review(self):
        review.approve(self.record,self.root)
        for field,value in [('name','Other release'),('title','Other Film'),('year',1941),('external_id','2'),('info_url','https://www.torrentleech.org/torrent/2')]:
            original=self.release;self.release=dict(original,**{field:value})
            self.assertIsNone(self.apply());self.release=original
        self.listing['torrent_evidence']=extract(BeautifulSoup(PAGE.replace('118 min','120 min'),'html.parser'))
        self.assertIsNone(self.apply());self.resolve.assert_not_called()
    def test_tracker_id_change_native_assertion_and_unverified_listing_block(self):
        review.approve(self.record,self.root)
        original=copy.deepcopy(self.listing)
        for changed in ({'imdb_id':'tt9999999'},{'reason':'listing_mismatch'},{'reason':'listing_id_conflict'}):
            self.listing=original|changed;self.assertIsNone(self.apply())
        self.listing=original;self.release['meta_imdb']='tt1234567'
        self.assertIsNone(self.apply());self.resolve.assert_not_called()
    def test_target_still_requires_verified_crosswalk_title_year(self):
        review.approve(self.record,self.root)
        for changed in ({'identity_status':'needs_review'},{'identity_status':'imdb_associated'},{'imdb_id':'tt9999999'},{'tmdb_id':999}):
            self.resolve.return_value=self.target|changed;self.assertIsNone(self.apply())
    def test_private_state_permissions_and_symlinks_fail_closed(self):
        review.approve(self.record,self.root)
        path=self.root/'decisions.sqlite3';path.chmod(0o644)
        self.assertIsNone(self.apply());path.chmod(0o600)
        path.rename(self.root/'original.sqlite3');path.symlink_to(self.root/'original.sqlite3')
        self.assertIsNone(self.apply())
    def test_unapproved_scope_cannot_be_used(self):
        review.approve(self.record,self.root)
        for reason in ('invalid_metadata','listing_id_conflict','local_identity_conflict','identity_conflict'):
            self.meta['identity_reason']=reason;self.assertIsNone(self.apply())
        self.resolve.assert_not_called()
    def test_actor_uses_private_approval_without_creating_actions_or_notifications(self):
        import movie_intel_service as svc
        review.approve(self.record,self.root)
        payload={'data':{'release':self.release,'indexer':self.indexer,'result':{'rejections':['Unknown Movie']}}}
        source=copy.deepcopy(self.meta)|{'imdb_id':'tt1234567'}
        with patch.object(review,'directory',return_value=self.root),patch.object(svc,'find_local',return_value=None),patch.object(svc,'INDEX',{}),patch.object(svc,'lookup_listing',return_value=self.listing|{'source':'torrentleech_listing'}),patch.object(svc,'resolve_external_movie',side_effect=[source,self.target]),patch.object(svc,'decision_log'),patch.object(svc,'create_action') as action,patch.object(svc,'_telegram_request') as telegram,patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab:
            context=svc.build_movie_context(payload)
        self.assertEqual(context['meta']['identity_status'],'verified_tmdb')
        self.assertEqual(context['meta']['imdb_id'],'tt7654321')
        self.assertEqual(context['identity_observation']['asserted_imdb'],'tt7654321')
        for mock in (action,telegram,add,grab):mock.assert_not_called()
    def test_pending_action_requires_same_current_review_and_identity(self):
        import movie_intel_service as svc
        marker={'decision_id':'sample','source_key':'a'*64}
        action={'movie':self.target|{'identity_review':marker},'release':self.release,'indexer':self.indexer}
        with patch.object(svc,'build_movie_context',return_value={'meta':self.target|{'identity_review':marker}}):self.assertTrue(svc.reviewed_action_current(action))
        for meta in (self.meta,self.target,self.target|{'identity_review':marker,'tmdb_id':999}):
            with patch.object(svc,'build_movie_context',return_value={'meta':meta}):self.assertFalse(svc.reviewed_action_current(action))
        self.assertTrue(svc.reviewed_action_current({'movie':self.target}))

    def test_revoked_confirmation_stops_before_any_acquisition_write(self):
        import movie_intel_service as svc
        action={'movie':self.target|{'identity_review':{'decision_id':'sample'}},'release':self.release}
        handler=object.__new__(svc.Handler);handler._html=Mock()
        with patch.object(svc,'get_action',return_value=action),patch.object(svc,'reviewed_action_current',return_value=False),patch.object(svc,'ensure_movie') as add,patch.object(svc,'push_release') as grab,patch.object(svc,'update_action') as update:
            handler._handle_action_post_locked('synthetic-token')
        self.assertEqual(handler._html.call_args.args[0],409)
        for mock in (add,grab,update):mock.assert_not_called()
        self.assertFalse(svc.reviewed_action_current({'movie':{'identity_source':'owner_reviewed_source'}}))

    def test_offer_preserves_review_and_exact_source_for_revalidation(self):
        import movie_intel_service as svc
        marker={'decision_id':'sample','source_key':'a'*64}
        payload={'data':{'release':self.release|{'download_url':'https://synthetic.invalid/file'},'indexer':self.indexer,'result':{'rejections':['Unknown Movie']}}}
        with patch.object(svc,'radarr_configured',return_value=True),patch.object(svc,'build_release_push'),patch.object(svc,'create_action',return_value='token') as create,patch.object(svc,'decision_log'):
            self.assertEqual(svc.create_pending_action(payload,self.target|{'identity_review':marker}),'token')
        stored=create.call_args.args[0]
        self.assertEqual(stored['movie']['identity_review'],marker)
        self.assertEqual(stored['release']['external_id'],'1')
        self.assertEqual(stored['indexer']['identifier'],'torrentleech')

if __name__=='__main__':unittest.main()
