"""Offline identity and service regressions; no provider writes or notifications."""
import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import movie_intel_service as svc
import tmdb_resolver as tmdb
from test_movie_intel_actions import PAYLOAD, META


def movie(**changes):
    return dict(id=329865, title='Arrival', original_title='Arrival',
                release_date='2016-11-10', external_ids={'imdb_id': 'tt2543164'}, **changes)


class ExternalIdentityTests(unittest.TestCase):
    def setUp(self):
        tmdb._ID_CACHE.clear()

    def resolve(self, details=None, find=None, title='Arrival', year=2016, **ids):
        details = movie() if details is None else details
        find = {'movie_results': [{'id': 329865}]} if find is None else find
        with patch.object(tmdb, '_get', side_effect=lambda path, params: find if path.startswith('/find/') else details), \
             patch.object(tmdb, '_search_exact') as search, patch.object(tmdb, '_load_cache') as cache:
            result = tmdb.resolve_external_movie(title, year, **(ids or {'imdb_id': 'tt2543164'}))
        search.assert_not_called()
        cache.assert_not_called()
        return result

    def test_matching_id_pair_verified(self):
        result = self.resolve(imdb_id='tt2543164', tmdb_id='329865')
        self.assertEqual(result['identity_status'], 'verified_tmdb')
        self.assertEqual(result['tmdb_id'], 329865)

    def test_direct_tmdb_movie_without_imdb_is_allowed_with_context(self):
        details = movie()
        details['external_ids']['imdb_id'] = None
        self.assertEqual(self.resolve(details, tmdb_id=329865)['identity_status'], 'verified_tmdb')

    def test_conflicting_pair_and_failed_round_trip(self):
        self.assertEqual(self.resolve(imdb_id='tt2543164', tmdb_id=123)['identity_reason'], 'identity_conflict')
        details = movie()
        details['external_ids']['imdb_id'] = 'tt1234567'
        self.assertEqual(self.resolve(details)['identity_reason'], 'identity_conflict')

    def test_wrong_film_assignment_requires_review(self):
        self.assertEqual(self.resolve(title='Different Film')['identity_reason'], 'title_conflict')
        self.assertEqual(self.resolve(year=2017)['identity_reason'], 'year_conflict')

    def test_only_documented_release_years_are_accepted(self):
        details = movie(release_dates={'results': [{'release_dates': [{'release_date': '2015-09-01'}]}]})
        result = self.resolve(details, year=2015)
        self.assertEqual(result['identity_status'], 'verified_tmdb')
        self.assertEqual(result['matched_release_year'], '2015')
        self.assertEqual(result['identity_year_basis'], 'release_dates')
        self.assertEqual(self.resolve(details, year=2014)['identity_reason'], 'year_conflict')

    def test_aliases_translations_and_ampersand_context(self):
        details = movie(alternative_titles={'titles': [{'title': 'Alternate & Title'}]},
                        translations={'translations': [{'data': {'title': 'Die Ankunft'}}]})
        for title in ('Alternate and Title', 'Die Ankunft'):
            with self.subTest(title=title):
                self.assertEqual(self.resolve(details, title=title)['identity_status'], 'verified_tmdb')
        self.assertEqual(self.resolve(details, title='Arrival Extra')['identity_reason'], 'title_conflict')

    def test_non_latin_titles_do_not_collapse_to_empty(self):
        self.assertNotEqual(tmdb._identity_title('到着'), tmdb._identity_title('映画'))

    def test_missing_duplicate_and_nonmovie_mappings(self):
        for response, reason in (({'movie_results': []}, 'tmdb_mapping_missing'),
                                 ({'movie_results': [{'id': 1}, {'id': 2}]}, 'ambiguous_id_mapping'),
                                 ({'movie_results': [], 'tv_results': [{'id': 1}]}, 'non_movie_identity')):
            tmdb._ID_CACHE.clear()
            self.assertEqual(self.resolve(find=response)['identity_reason'], reason)

    def test_invalid_ids_never_reach_network(self):
        for name, values in (('imdb_id', ['tt1', 'tt1234567/path', 1234567, True, [], {}, ' tt1234567']),
                             ('tmdb_id', [0, -1, True, 1.2, '01', 'movie/123', [], {}])):
            for value in values:
                with self.subTest(name=name, value=value), patch.object(tmdb, '_get') as get:
                    self.assertEqual(tmdb.resolve_external_movie('X', 2020, **{name: value})['identity_status'], 'needs_review')
                get.assert_not_called()

    def test_fragmentos_unmapped_does_not_pick_popular_namesake(self):
        result = self.resolve(find={'movie_results': []}, title='Fragmentos', year=2025, imdb_id='tt33503751')
        self.assertEqual(result['identity_status'], 'imdb_associated')
        self.assertNotIn('tmdb_id', result)

    def test_malformed_hamnet_year_is_not_repaired(self):
        details = movie()
        details.update(title='Hamnet', original_title='Hamnet', release_date='2025-11-26')
        self.assertEqual(self.resolve(details, title='Hamnet', year=2016)['identity_reason'], 'year_conflict')

    def test_cache_is_context_and_pair_specific_and_expires(self):
        self.resolve()
        with patch.object(tmdb, '_get') as get:
            cached = tmdb.resolve_external_movie('Arrival', 2016, imdb_id='tt2543164')
        get.assert_not_called()
        self.assertEqual(cached['identity_status'], 'verified_tmdb')
        self.assertEqual(self.resolve(title='Wrong')['identity_status'], 'needs_review')
        self.assertEqual(self.resolve(imdb_id='tt2543164', tmdb_id=1)['identity_status'], 'needs_review')
        with patch.object(tmdb.time, 'monotonic', return_value=float('inf')), patch.object(tmdb, '_get', return_value=None) as get:
            self.assertEqual(tmdb.resolve_external_movie('Arrival', 2016, imdb_id='tt2543164')['identity_status'], 'unresolved')
        get.assert_called_once()

    def test_provider_failure_malformed_data_and_wrong_endpoint_id(self):
        for response in (None, [], {'movie_results': None}):
            tmdb._ID_CACHE.clear()
            with patch.object(tmdb, '_get', return_value=response):
                self.assertNotIn('tmdb_id', tmdb.resolve_external_movie('Arrival', 2016, imdb_id='tt2543164'))
        details = movie()
        details['id'] = 42
        tmdb._ID_CACHE.clear()
        self.assertEqual(self.resolve(details)['identity_reason'], 'invalid_movie_identity')

    def test_busy_resolution_does_not_queue_or_search(self):
        with tmdb._ID_LOCK, patch.object(tmdb, '_get') as get:
            self.assertEqual(tmdb.resolve_external_movie('Arrival', 2016, imdb_id='tt2543164')['identity_reason'], 'metadata_lookup_busy')
        get.assert_not_called()


class ServiceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.payload = copy.deepcopy(PAYLOAD)
        self.output = io.StringIO()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(contextlib.redirect_stdout(self.output))
        self.stack.enter_context(patch.object(svc, 'INDEX', {}))

    def test_native_ids_propagate_without_listing_or_search(self):
        self.payload['data']['release'].update(meta_imdb='tt2543164', meta_tmdb=329865)
        with patch.object(svc, 'resolve_external_movie', return_value=dict(META, identity_status='verified_tmdb')) as resolve, \
             patch.object(svc, 'lookup_listing') as listing, patch.object(svc, 'resolve_movie') as search:
            context = svc.build_movie_context(self.payload)
        resolve.assert_called_once_with('Arrival', 2016, imdb_id='tt2543164', tmdb_id=329865)
        listing.assert_not_called()
        search.assert_not_called()
        self.assertEqual(context['meta']['identity_source'], 'autobrr_external_ids')

    def test_listing_id_is_used_and_lookup_itself_never_sends(self):
        with patch.object(svc, 'lookup_listing', return_value={'reason': 'listing_id_found', 'source': 'torrentleech_listing', 'imdb_id': 'tt2543164'}), \
             patch.object(svc, 'resolve_external_movie', return_value=dict(META, identity_status='verified_tmdb')) as resolve, \
             patch.object(svc, 'create_action') as create, patch.object(svc, '_telegram_request') as send:
            context = svc.build_movie_context(self.payload)
        resolve.assert_called_once_with('Arrival', 2016, imdb_id='tt2543164', tmdb_id=None)
        self.assertEqual(context['meta']['identity_source'], 'torrentleech_listing')
        create.assert_not_called()
        send.assert_not_called()

    def test_local_conflict_blocks_catalog_claim_and_grab(self):
        self.payload['data']['release']['meta_imdb'] = 'tt1234567'
        with patch.object(svc, 'find_local', return_value=dict(META, qualified=True)), \
             patch.object(svc, 'resolve_external_movie') as resolve:
            context = svc.build_movie_context(self.payload)
        self.assertIn('requires review', context['text'])
        self.assertNotIn('QUALIFIES', context['text'])
        self.assertNotIn('imdb.com', context['text'])
        resolve.assert_not_called()

    def test_unmapped_and_failed_listing_never_use_legacy_search(self):
        self.payload['data']['release']['meta_imdb'] = 'tt33503751'
        with patch.object(svc, 'resolve_external_movie', return_value={'identity_status': 'imdb_associated', 'imdb_id': 'tt33503751'}), \
             patch.object(svc, 'resolve_movie') as search:
            context = svc.build_movie_context(self.payload)
        self.assertIn('Indexer IMDb association only', context['text'])
        self.assertNotIn('Identified;', context['text'])
        search.assert_not_called()
        del self.payload['data']['release']['meta_imdb']
        with patch.object(svc, 'lookup_listing', return_value={'reason': 'listing_mismatch', 'source': 'torrentleech_listing'}), \
             patch.object(svc, 'resolve_movie') as search:
            context = svc.build_movie_context(self.payload)
        self.assertIn('Approval unavailable', context['text'])
        search.assert_not_called()

    def test_nonverified_status_cannot_create_action_even_with_tmdb_id(self):
        for status in ('needs_review', 'imdb_associated', 'unresolved'):
            with patch.object(svc, 'radarr_configured', return_value=True), patch.object(svc, 'create_action') as create:
                self.assertIsNone(svc.create_pending_action(self.payload, dict(META, identity_status=status)))
            create.assert_not_called()

    def test_verified_action_preserves_reference_and_provenance(self):
        meta = dict(META, identity_status='verified_tmdb', identity_source='torrentleech_listing')
        with patch.object(svc, 'radarr_configured', return_value=True), patch.object(svc, 'create_action', return_value='token') as create:
            self.assertEqual(svc.create_pending_action(self.payload, meta), 'token')
        action = create.call_args.args[0]
        self.assertEqual(action['release']['download_url'], self.payload['data']['release']['download_url'])
        self.assertEqual(action['movie']['identity_source'], 'torrentleech_listing')
        self.assertNotIn('PRIVATE', self.output.getvalue())

    def test_routine_rejection_skips_all_lookups(self):
        self.payload['data']['result']['rejections'] = ['Existing file meets cutoff']
        with patch.object(svc, 'lookup_listing') as listing, patch.object(svc, 'resolve_external_movie') as resolve:
            svc.build_movie_context(self.payload)
        listing.assert_not_called()
        resolve.assert_not_called()

    def test_documented_year_difference_is_visible(self):
        text = svc.format_message(self.payload, meta=dict(META, identity_status='verified_tmdb',
                                  identity_year_basis='release_dates', matched_release_year='2015'))
        self.assertIn('TMDb also records a release in 2015.', text)

    def test_torrent_external_id_is_not_a_movie_id(self):
        self.payload['data']['release']['external_id'] = '329865'
        with patch.object(svc, 'lookup_listing', return_value={'reason': 'disabled'}), \
             patch.object(svc, 'resolve_movie', return_value=None) as legacy, patch.object(svc, 'resolve_external_movie') as external:
            svc.build_movie_context(self.payload)
        legacy.assert_called_once()
        external.assert_not_called()
