"""Watch labels come from live Radarr tags, never from monitoring or scores."""
import unittest
from unittest.mock import patch

import movie_intel_service as svc
import radarr_client as rc


class WatchedNotificationTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            'event': 'action.rejected',
            'data': {'release': {'type': 'movie', 'title': 'Example', 'year': 2022,
                                 'name': 'Example.2022.1080p'},
                     'result': {'rejections': ['Movie is not monitored']}}}
        self.meta = {'tmdb_id': 99, 'imdb_id': 'tt1234567', 'title': 'Example',
                     'year': 2022, 'poster_url': 'https://image.invalid/p.jpg'}
        self.movie = {'imdb_id': 'tt1234567', 'qualified': True,
                      'routes': ['evidence_score_225'], 'tspdt_rank': 395,
                      'imdb': {'rating': 7.4, 'votes': 111000}}
        self.existing = {'id': 10, 'tmdbId': 99, 'imdbId': 'tt1234567',
                         'monitored': False, 'tags': [7, 42]}

    def context(self, existing=None, rows=None, meta=None, movie=True):
        if existing is None:
            existing = self.existing
        if rows is None:
            rows = [{'id': 42, 'label': 'watched'}, {'id': 7, 'label': 'movie-list'}]
        with patch.object(svc, 'find_local', return_value=self.movie if movie else None), \
             patch.object(svc, 'INDEX', {}), \
             patch.object(svc, 'lookup_listing', return_value={'reason': 'disabled'}), \
             patch.object(svc, 'resolve_movie', return_value=meta or self.meta), \
             patch.object(rc, '_request', side_effect=[
                 existing if isinstance(existing, Exception) else ([existing] if existing else []), rows]) as request, \
             patch.object(svc, 'decision_log'):
            result = svc.build_movie_context(self.payload)
        return result, request

    def test_watched_replaces_assessment_preserving_movie_details(self):
        context, request = self.context()
        text = context['text']
        self.assertIn('<b>Watched</b>', text)
        self.assertNotIn('POTENTIAL FALSE NEGATIVE', text)
        self.assertNotIn('Our model:', text)
        for value in ('IMDb 7.4', 'TSPDT #395', 'Movie is not monitored', 'Example.2022.1080p'):
            self.assertIn(value, text)
        self.assertEqual(context['poster_url'], self.meta['poster_url'])
        self.assertEqual([call.args[0] for call in request.call_args_list],
                         ['/movie?tmdbId=99&excludeLocalCovers=true', '/tag'])
        self.assertTrue(all(not call.kwargs for call in request.call_args_list))
        self.assertEqual(self.existing['tags'], [7, 42])

    def test_unmonitored_or_missing_movie_is_not_watched(self):
        for existing in ({}, dict(self.existing, tags=[]), dict(self.existing, tags=[7])):
            with self.subTest(existing=existing):
                context, _ = self.context(existing=existing)
                self.assertNotIn('<b>Watched</b>', context['text'])
                self.assertNotIn('POTENTIAL FALSE NEGATIVE', context['text'])
                self.assertIn('Our model: QUALIFIES', context['text'])

    def test_watched_outside_catalog_and_not_qualified(self):
        context, _ = self.context(movie=False)
        self.assertIn('<b>Watched</b>', context['text'])
        self.movie['qualified'] = False
        context, _ = self.context()
        self.assertIn('<b>Watched</b>', context['text'])
        self.assertNotIn('does not currently qualify', context['text'])

    def test_lookup_failure_does_not_drop_notification(self):
        for existing, rows in ((rc.RadarrError('unavailable'), []),
                               (self.existing, rc.RadarrError('unavailable')),
                               (self.existing, {'invalid': 'tags'})):
            context, _ = self.context(existing=existing, rows=rows)
            self.assertNotIn('<b>Watched</b>', context['text'])
            self.assertIn('Movie is not monitored', context['text'])

    def test_mismatched_or_unresolved_identity_cannot_show_watched(self):
        for existing in (dict(self.existing, tmdbId=100),
                         dict(self.existing, imdbId='tt7654321')):
            context, request = self.context(existing=existing)
            self.assertNotIn('<b>Watched</b>', context['text'])
            self.assertEqual(request.call_count, 1)
        for status in ('needs_review', 'unresolved', 'imdb_associated'):
            context, request = self.context(meta=dict(self.meta, identity_status=status))
            self.assertNotIn('<b>Watched</b>', context['text'])
            request.assert_not_called()

    def test_verified_external_identity_uses_watched_tag(self):
        self.payload['data']['release']['meta_imdb'] = self.meta['imdb_id']
        with patch.object(svc, 'resolve_external_movie',
                          return_value=dict(self.meta, identity_status='verified_tmdb')):
            context, _ = self.context()
        self.assertIn('<b>Watched</b>', context['text'])


class TagLookupTests(unittest.TestCase):
    def test_only_assigned_exact_label_matches_and_ids_are_not_hardcoded(self):
        for label, expected in (('watched', True), (' Watched ', True),
                                ('unwatched', False), ('watched-later', False)):
            with patch.object(rc, '_request', return_value=[{'id': 123, 'label': label}]) as request:
                self.assertEqual(rc.movie_has_tag({'tags': [123]}, 'watched'), expected)
                request.assert_called_once_with('/tag')
        with patch.object(rc, '_request', return_value=[{'id': 124, 'label': 'watched'}]):
            self.assertFalse(rc.movie_has_tag({'tags': [123]}, 'watched'))

    def test_missing_or_malformed_tag_ids_cannot_claim_watched(self):
        for movie in (None, {}, {'tags': None}, {'tags': 'watched'},
                      {'tags': [True, '42', {}, [], 0]}):
            with patch.object(rc, '_request') as request:
                self.assertFalse(rc.movie_has_tag(movie, 'watched'))
                request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
