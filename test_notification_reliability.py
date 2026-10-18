"""Regression cases from production diagnosis; all integration calls are fake."""
import copy
import unittest
from unittest.mock import patch

import movie_intel_service as svc
import radarr_client as rc
from test_movie_intel_actions import PAYLOAD, META


class RenderingTests(unittest.TestCase):
    def test_resolved_outside_catalog_is_not_called_unresolved(self):
        with patch.object(svc, 'INDEX', {}):
            text = svc.format_message(PAYLOAD, meta=META)
        self.assertNotIn('or unresolved', text)
        self.assertIn('not in the local', text)

    def test_routine_profile_cutoff_skips_resolver_and_poster(self):
        payload = copy.deepcopy(PAYLOAD)
        payload['data']['result']['rejections'] = ['Bluray-2160p is not wanted in profile']
        with patch.object(svc, 'resolve_movie') as resolve:
            context = svc.build_movie_context(payload)
        resolve.assert_not_called()
        self.assertIsNone(context['poster_url'])
        self.assertIn('Release Rejected', context['text'])

    def test_long_card_keeps_poster_and_button_on_complete_text(self):
        text = '<b>Example</b>\n' + 'recognition ' * 100
        with patch.object(svc, '_telegram_request', return_value=200) as send:
            svc.send_movie_notification(text, 'https://image.invalid/p.jpg', 'https://example.invalid/action/test')
        self.assertEqual([c.args[0] for c in send.call_args_list], ['sendMessage', 'sendPhoto'])
        self.assertEqual(send.call_args_list[0].args[1]['text'], text)
        self.assertIn('reply_markup', send.call_args_list[0].args[1])

    def test_optional_bad_ratings_do_not_break_identity_card(self):
        movie = {'imdb': 'unavailable', 'letterboxd': {'rating': 4, 'votes': float('nan')}}
        text = svc.format_message(PAYLOAD, movie=movie, meta=META)
        self.assertIn('Arrival', text)
        self.assertIn('Letterboxd 4', text)

    def test_full_release_not_truncated(self):
        payload = copy.deepcopy(PAYLOAD)
        name = 'Arrival.2016.' + 'Long.Release.' * 25
        payload['data']['release']['name'] = name
        self.assertIn(name, svc.format_message(payload, meta=META))

    def test_oversized_html_line_becomes_safe_bounded_plain_text(self):
        text = '<b>' + '🎬&amp;' * 2000 + '</b>'
        with patch.object(svc, '_telegram_request', return_value=200) as send:
            svc.send_movie_notification(text, action_url='https://example.invalid/action/test')
        bodies = [call.args[1] for call in send.call_args_list]
        self.assertEqual(''.join(body['text'] for body in bodies), '🎬&' * 2000)
        self.assertTrue(all(len(body['text'].encode('utf-16-le')) // 2 <= 4096 for body in bodies))
        self.assertTrue(all('parse_mode' not in body for body in bodies))
        self.assertIn('reply_markup', bodies[-1])
        self.assertTrue(all('reply_markup' not in body for body in bodies[:-1]))

    def test_photo_failure_keeps_original_card_and_button(self):
        with patch.object(svc, '_telegram_request', side_effect=[OSError('private'), 200]) as send:
            svc.send_movie_notification('<b>Movie</b>', 'https://image.invalid/p.jpg', 'https://example.invalid/action/test')
        self.assertEqual(send.call_args_list[-1].args[0], 'sendMessage')
        self.assertIn('reply_markup', send.call_args_list[-1].args[1])


class ReleaseValidationTests(unittest.TestCase):
    def test_valid_magnet_is_reused_without_substitution(self):
        release = copy.deepcopy(PAYLOAD['data']['release'])
        release.pop('download_url')
        release['magnet_uri'] = 'magnet:?xt=urn:btih:' + 'a' * 40
        body = rc.build_release_push(release, tmdb_id=META['tmdb_id'])
        self.assertEqual(body['magnetUrl'], release['magnet_uri'])
        self.assertEqual(body['title'], release['name'])
        self.assertNotIn('downloadUrl', body)

    def test_contradictory_push_response_is_uncertain_not_retryable_rejection(self):
        with patch.object(rc, '_request', return_value={'approved': True, 'rejected': True}):
            with self.assertRaises(rc.RadarrError) as caught:
                rc.push_release(PAYLOAD['data']['release'])
        self.assertNotIsInstance(caught.exception, rc.ReleaseRejected)

    def test_invalid_reference_never_becomes_approval(self):
        for url in ('garbage', 'file:///tmp/release', 'https://', 12):
            payload = copy.deepcopy(PAYLOAD)
            payload['data']['release']['download_url'] = url
            with self.subTest(url=url), patch.object(svc, 'radarr_configured', return_value=True), patch.object(svc, 'create_action') as create:
                self.assertIsNone(svc.create_pending_action(payload, META))
                create.assert_not_called()

    def test_existing_identity_must_match(self):
        with patch.object(rc, 'get_movie_by_tmdb', return_value={'id': 7, 'tmdbId': 999}), patch.object(rc, '_request') as request:
            with self.assertRaises(rc.RadarrError):
                rc.ensure_movie(329865, 2, '/movies')
        request.assert_not_called()
