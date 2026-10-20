"""Per-film repairs are removed; only generic ID/context policy can identify."""
import copy
import os
import unittest
from unittest.mock import patch
import movie_intel_service as svc
import tmdb_resolver as tmdb
from deployment_config import configuration_errors
from test_movie_intel_actions import PAYLOAD


class GenericIdentityOnlyTests(unittest.TestCase):
    def context(self, title, year, canonical, canonical_year, enabled='1'):
        tmdb._ID_CACHE.clear()
        payload=copy.deepcopy(PAYLOAD)
        payload['data']['release'].update(title=title,year=year)
        payload['data']['indexer']={'name':'TorrentLeech'}
        before=copy.deepcopy(payload)
        details=dict(id=101,title=canonical,original_title=canonical,
                     release_date=f'{canonical_year}-01-01',external_ids={'imdb_id':'tt0000001'})
        # Even a lingering legacy setting cannot restore an exception at runtime.
        with patch.dict(os.environ,{'MOVIE_INTEL_TRACKER_TYPO_ENABLED':enabled,
                                   'MOVIE_INTEL_REVIEWED_CONTEXT_FILE':'/nonexistent/legacy.json'}), \
             patch.object(svc,'INDEX',{}), \
             patch.object(svc,'lookup_listing',return_value={'reason':'listing_id_found','source':'torrentleech_listing','imdb_id':'tt0000001'}), \
             patch.object(tmdb,'_get',side_effect=lambda path,params: {'movie_results':[{'id':101}]} if path.startswith('/find/') else details), \
             patch.object(svc,'create_action',side_effect=AssertionError('no action')), \
             patch.object(svc,'_telegram_request',side_effect=AssertionError('no notification')), \
             patch.object(svc,'ensure_movie',side_effect=AssertionError('no acquisition')), \
             patch.object(svc,'push_release',side_effect=AssertionError('no acquisition')):
            meta=svc.build_movie_context(payload)['meta']
        self.assertEqual(payload,before)
        self.assertNotIn('identity_correction',meta)
        return meta

    def test_bruce_generic_only_and_switch_revocation(self):
        self.assertEqual(self.context('Bruce Almiighty',2003,'Bruce Almighty',2003)['identity_title_basis'],'tracker_minor_typo')
        self.assertEqual(self.context('Bruce Almiighty',2003,'Bruce Almighty',2003,enabled='0')['identity_reason'],'title_conflict')

    def test_hamnet_has_no_title_or_year_exception(self):
        self.assertEqual(self.context('Hamnet 2025',2016,'Hamnet',2025)['identity_reason'],'title_conflict')
        self.assertEqual(self.context('Hamnet',2016,'Hamnet',2025)['identity_reason'],'year_conflict')
        self.assertEqual(self.context('Hamnet',2025,'Hamnet',2025)['identity_status'],'verified_tmdb')

    def test_jazz_has_no_performer_prefix_exception(self):
        self.assertEqual(self.context('Medeski Martin Wood Not Not Jazz',2024,'Not Not Jazz',2024)['identity_reason'],'title_conflict')
        self.assertEqual(self.context('Not Not Jazz',2024,'Not Not Jazz',2024)['identity_status'],'verified_tmdb')

    def test_legacy_registry_configuration_is_explicitly_rejected(self):
        errors=configuration_errors({'MOVIE_INTEL_REVIEWED_CONTEXT_FILE':'/nonexistent/legacy.json'})
        self.assertIn('MOVIE_INTEL_REVIEWED_CONTEXT_FILE is retired; remove this setting',errors)
        self.assertFalse(any('REVIEWED_CONTEXT' in e for e in configuration_errors({})))
