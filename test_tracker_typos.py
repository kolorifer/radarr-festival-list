"""Synthetic identity tests; no notifications, action creation or acquisition."""
import copy
import os
import unittest
from unittest.mock import patch
import tmdb_resolver as tmdb
import movie_intel_service as svc
from test_movie_intel_actions import PAYLOAD


class TrackerTypoTests(unittest.TestCase):
    def setUp(self):
        tmdb._ID_CACHE.clear()
        self.details = dict(id=310, title='Bruce Almighty', original_title='Bruce Almighty',
                            release_date='2003-01-01', external_ids={'imdb_id': 'tt0000001'})
        self.find = {'movie_results': [{'id': 310}]}

    def resolve(self, title='Bruce Almiighty', year=2003, **kwargs):
        with patch.object(tmdb, '_get', side_effect=lambda path, params: self.find if path.startswith('/find/') else self.details):
            return tmdb.resolve_external_movie(title, year, imdb_id='tt0000001', **kwargs)

    def test_single_edits_and_transposition(self):
        for title in ('Bruce Almiighty', 'Bruce Almghty', 'Bruce Almlghty', 'Bruce Almihgty'):
            with self.subTest(title=title):
                result = self.resolve(title, allow_minor_typo=True)
                self.assertEqual(result['identity_status'], 'verified_tmdb')
                self.assertEqual(result['identity_title_basis'], 'tracker_minor_typo')
        self.assertNotIn('identity_title_basis', self.resolve('Bruce Almighty', allow_minor_typo=True))

    def test_six_letter_title_single_edits_require_verified_id_and_year(self):
        self.details.update(title='Carrie', original_title='Carrie', release_date='1976-01-01')
        for title in ('Carrue', 'Carrrie', 'Caarie'):
            tmdb._ID_CACHE.clear()
            with self.subTest(title=title):
                result=self.resolve(title,1976,allow_minor_typo=True)
                self.assertEqual(result['identity_status'],'verified_tmdb')
                self.assertEqual(result['identity_title_basis'],'tracker_minor_typo')
        tmdb._ID_CACHE.clear()
        self.assertEqual(self.resolve('Carrue',1976)['identity_reason'],'title_conflict')
        tmdb._ID_CACHE.clear()
        self.assertEqual(self.resolve('Carrue',1977,allow_minor_typo=True)['identity_reason'],'year_conflict')
        tmdb._ID_CACHE.clear();self.find={'movie_results':[{'id':310},{'id':311}]}
        self.assertEqual(self.resolve('Carrue',1976,allow_minor_typo=True)['identity_reason'],'ambiguous_id_mapping')

    def test_policy_cache_isolation(self):
        self.assertEqual(self.resolve(allow_minor_typo=True)['identity_status'], 'verified_tmdb')
        self.assertEqual(self.resolve()['identity_reason'], 'title_conflict')
        tmdb._ID_CACHE.clear()
        self.assertEqual(self.resolve()['identity_reason'], 'title_conflict')
        self.assertEqual(self.resolve(allow_minor_typo=True)['identity_status'], 'verified_tmdb')

    def test_five_letter_word_requires_unchanged_substantial_context(self):
        for title in ('Charlie Victor Romeon', 'Charlie Victor Romoe', 'Charlie Victor Rameo'):
            self.details.update(title='Charlie Victor Romeo', original_title='Charlie Victor Romeo',
                                release_date='2014-01-29', release_dates={'results':[{
                                    'release_dates':[{'release_date':'2013-01-21'}]}]})
            tmdb._ID_CACHE.clear()
            with self.subTest(title=title):
                result = self.resolve(title, 2013, allow_minor_typo=True)
                self.assertEqual(result['identity_status'], 'verified_tmdb')
                self.assertEqual(result['identity_title_basis'], 'tracker_minor_typo')
                self.assertEqual(result['identity_year_basis'], 'release_dates')
        for observed, candidate in [('Romeon','Romeo'), ('The Romeon','The Romeo'),
                                     ('Charlie Vuctor Romeon','Charlie Victor Romeo'),
                                     ('Charlie Victor Romeon II','Charlie Victor Romeo III'),
                                     ('Charlie Victor Rone','Charlie Victor Rome')]:
            with self.subTest(observed=observed):
                self.assertFalse(tmdb._minor_title_typo(observed, candidate))

    def test_contextual_short_typo_still_requires_identity_and_year(self):
        self.details.update(title='Charlie Victor Romeo', original_title='Charlie Victor Romeo', release_date='2013-01-21')
        self.assertEqual(self.resolve('Charlie Victor Romeon',2013)['identity_reason'],'title_conflict')
        self.assertEqual(self.resolve('Charlie Victor Romeon',2014,allow_minor_typo=True)['identity_reason'],'year_conflict')
        self.details['external_ids']['imdb_id']='tt0000002'
        self.assertEqual(self.resolve('Charlie Victor Romeon',2013,allow_minor_typo=True)['identity_reason'],'identity_conflict')

    def test_unsafe_title_changes(self):
        for a,b in [('Alien','Aliens'),('The Think','The Thing'),('Rocky II','Rocky III'),
                    ('Rocky 2','Rocky 3'),('Movie 10','Movie 11'),('Bruce Almighty Extra','Bruce Almighty'),
                    ('Bruce Almiighty Extra','Bruce Almighty'),('Bruce Almyghtyy','Bruce Almighty'),
                    ('Brue Almghty','Bruce Almighty'),('Different Film','Bruce Almighty')]:
            with self.subTest(a=a,b=b):
                # The Think is deliberately excluded here by the short-title bound.
                self.assertFalse(tmdb._minor_title_typo(a,b))

    def test_identity_and_year_gates(self):
        self.assertEqual(self.resolve(year=2004,allow_minor_typo=True)['identity_reason'],'year_conflict')
        for response, reason in [({'movie_results':[]},'tmdb_mapping_missing'),
                                 ({'movie_results':[{'id':310},{'id':311}]},'ambiguous_id_mapping'),
                                 ({'movie_results':[{'id':310}],'tv_results':[{'id':1}]},'non_movie_identity')]:
            tmdb._ID_CACHE.clear();self.find=response
            self.assertEqual(self.resolve(allow_minor_typo=True)['identity_reason'],reason)
        self.find={'movie_results':[{'id':310}]};tmdb._ID_CACHE.clear()
        self.details['external_ids']['imdb_id']='tt0000002'
        self.assertEqual(self.resolve(allow_minor_typo=True)['identity_reason'],'identity_conflict')

    def test_tmdb_only_cannot_enable_typo(self):
        with patch.object(tmdb,'_get',return_value=self.details):
            self.assertEqual(tmdb.resolve_external_movie('Bruce Almiighty',2003,tmdb_id=310,allow_minor_typo=True)['identity_reason'],'title_conflict')

    def context(self, native=False, indexer=None, local=None):
        payload=copy.deepcopy(PAYLOAD)
        payload['data']['release'].update(title='Bruce Almiighty',year=2003)
        payload['data']['indexer']=indexer or {'name':'TorrentLeech'}
        if native:payload['data']['release']['meta_imdb']='tt0000001'
        before=copy.deepcopy(payload)
        with patch.dict(os.environ,{'MOVIE_INTEL_TRACKER_TYPO_ENABLED':'1'}), \
             patch.object(svc,'find_local',side_effect=lambda title,year,index: local if title=='Bruce Almighty' else None), \
             patch.object(svc,'lookup_listing',return_value={'reason':'listing_id_found','source':'torrentleech_listing','imdb_id':'tt0000001'}), \
             patch.object(tmdb,'_get',side_effect=lambda path,params:self.find if path.startswith('/find/') else self.details), \
             patch.object(svc,'create_action',side_effect=AssertionError('action forbidden')), \
             patch.object(svc,'_telegram_request',side_effect=AssertionError('send forbidden')), \
             patch.object(svc,'ensure_movie',side_effect=AssertionError('acquisition forbidden')), \
             patch.object(svc,'push_release',side_effect=AssertionError('acquisition forbidden')):
            result=svc.build_movie_context(payload)
        self.assertEqual(payload,before)
        return result['meta']

    def test_service_only_verified_listing_and_unchanged_release(self):
        self.assertEqual(self.context()['identity_title_basis'],'tracker_minor_typo')
        self.assertEqual(self.context(native=True)['identity_reason'],'title_conflict')
        self.assertEqual(self.context(indexer={'name':'TorrentLeech','identifier':'Other'})['identity_reason'],'title_conflict')
        self.assertEqual(self.context(local={'imdb_id':'tt0000002'})['identity_reason'],'local_identity_conflict')
