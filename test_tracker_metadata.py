"""Synthetic exact-listing transport and parser fixtures; no tracker traffic."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests
import tracker_metadata as tracker
from deployment_config import configuration_errors
from test_deployment_config import VALID


NAME = 'Arrival.2016.2160p.UHD.BluRay.REMUX'
URL = 'https://www.torrentleech.org/torrent/1'  # Synthetic fixture, never requested.
PAGE = f'<h2 id="torrentName">{NAME}</h2><input name="imdbID" value="tt2543164">'


class ListingParserTests(unittest.TestCase):
    def test_structural_release_and_single_id_required(self):
        self.assertEqual(tracker.parse_listing(PAGE, NAME)['imdb_id'], 'tt2543164')
        self.assertEqual(tracker.parse_listing(PAGE, 'Other')['reason'], 'listing_mismatch')
        self.assertEqual(tracker.parse_listing(PAGE.replace('torrentName', 'changed'), NAME)['reason'], 'listing_mismatch')

    def test_login_missing_invalid_duplicate_and_conflicting_ids(self):
        for page, reason in ((PAGE + '<input type="password">', 'login_required'),
                             (PAGE.replace('imdbID', 'unknown'), 'listing_id_invalid'),
                             (PAGE.replace('tt2543164', 'tt1'), 'listing_id_invalid'),
                             (PAGE + '<input name="imdbID" value="tt2543164">', 'listing_id_invalid'),
                             (PAGE + '<a href="https://www.imdb.com/title/tt1234567/">Other</a>', 'listing_id_conflict')):
            with self.subTest(reason=reason):
                self.assertEqual(tracker.parse_listing(page, NAME)['reason'], reason)

    def test_unrelated_body_mention_cannot_validate_listing(self):
        page = f'<h2 id="torrentName">Different release</h2><p>{NAME}</p><input name="imdbID" value="tt2543164">'
        self.assertEqual(tracker.parse_listing(page, NAME)['reason'], 'listing_mismatch')

    def test_url_allowlist_rejects_ssrf_and_downloads(self):
        self.assertTrue(tracker.valid_listing_url(URL))
        for url in ('http://www.torrentleech.org/torrent/1', 'https://127.0.0.1/torrent/1',
                    URL + '?token=secret', URL + '#fragment', URL + '/download', URL + '\n',
                    'https://www.torrentleech.org.evil.invalid/torrent/1',
                    'https://user:pass@www.torrentleech.org/torrent/1',
                    'https://www.torrentleech.org:443/torrent/1',
                    'https://www.torrentleech.org/torrent/%31',
                    'https://www.torrentleech.org/download/1',
                    'https://www.torrentleech.org/torrent/../1', None):
            with self.subTest(url=url):
                self.assertFalse(tracker.valid_listing_url(url))


class ListingTransportTests(unittest.TestCase):
    def setUp(self):
        tracker._CACHE.clear()
        tracker._NEXT_REQUEST = 0
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'cookies.json'
        self.path.write_text(json.dumps({'session': 'synthetic-private-cookie'}))
        self.path.chmod(0o600)
        self.env = patch.dict(os.environ, {'MOVIE_INTEL_TL_METADATA_ENABLED': '1',
                                         'MOVIE_INTEL_TL_COOKIE_FILE': str(self.path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.release = {'info_url': URL, 'name': NAME, 'download_url': 'https://download.invalid/PRIVATE'}
        self.indexer = {'name': 'TorrentLeech'}

    def lookup(self):
        return tracker.lookup_listing(self.release, self.indexer)

    def response(self, session, status=200, body=PAGE.encode(), headers=None):
        instance = session.return_value.__enter__.return_value
        response = instance.get.return_value.__enter__.return_value
        response.status_code = status
        response.headers = headers or {'Content-Type': 'text/html'}
        response.iter_content.return_value = [body]
        return instance, response

    def test_only_exact_listing_get_no_redirect_proxy_or_download(self):
        with patch.object(tracker.requests, 'Session') as session:
            instance, response = self.response(session)
            result = self.lookup()
        self.assertEqual(result['imdb_id'], 'tt2543164')
        instance.get.assert_called_once()
        args, kwargs = instance.get.call_args
        self.assertEqual(args, (URL,))
        self.assertFalse(kwargs['allow_redirects'])
        self.assertFalse(instance.trust_env)
        self.assertTrue(kwargs['stream'])
        self.assertEqual(kwargs['timeout'], (3, 5))
        instance.cookies.set.assert_called_once_with('session', 'synthetic-private-cookie', domain='www.torrentleech.org', path='/')
        self.assertNotIn('PRIVATE', str(result))
        self.assertNotIn('synthetic-private-cookie', str(result))
        self.assertNotIn('torrent/1', str(result))

    def test_disabled_or_other_indexer_never_reads_auth_or_network(self):
        with patch.object(tracker, 'cookie_file') as cookie, patch.object(tracker.requests, 'Session') as session:
            with patch.dict(os.environ, {'MOVIE_INTEL_TL_METADATA_ENABLED': '0'}):
                self.assertEqual(self.lookup()['reason'], 'disabled')
            self.indexer = {'name': 'Another tracker'}
            self.assertEqual(self.lookup()['reason'], 'unsupported_indexer')
        cookie.assert_not_called()
        session.assert_not_called()

    def test_redirects_errors_content_and_body_limits(self):
        for status, body, headers, reason in (
                (302, b'', {'Location': 'https://evil.invalid'}, 'listing_http_error'),
                (403, b'', None, 'listing_http_error'),
                (200, b'', {'Content-Type': 'application/x-bittorrent'}, 'listing_content_invalid'),
                (200, b'x' * (tracker.MAX_BODY + 1), None, 'listing_limit_exceeded')):
            tracker._CACHE.clear()
            tracker._NEXT_REQUEST = 0
            with self.subTest(reason=reason), patch.object(tracker.requests, 'Session') as session:
                instance, response = self.response(session, status, body, headers)
                self.assertEqual(self.lookup()['reason'], reason)
                instance.get.assert_called_once()

    def test_time_budget_expires(self):
        with patch.object(tracker.requests, 'Session') as session:
            self.response(session)
            with patch.object(tracker.time, 'monotonic', side_effect=[0, 11]):
                self.assertEqual(tracker._fetch(URL, NAME, {'session': 'fixture'})['reason'], 'listing_limit_exceeded')

    def test_timeout_negative_cache_and_rotation(self):
        with patch.object(tracker, '_fetch', side_effect=requests.Timeout('PRIVATE')) as fetch:
            self.assertEqual(self.lookup()['reason'], 'listing_unavailable')
            self.assertEqual(self.lookup()['reason'], 'listing_unavailable')
            self.assertEqual(fetch.call_count, 1)
            tracker._NEXT_REQUEST = 0
            self.path.write_text('{"session":"rotated-cookie"}')
            self.assertEqual(self.lookup()['reason'], 'listing_unavailable')
            self.assertEqual(fetch.call_count, 2)

    def test_success_cache_expiry_and_release_name_isolation(self):
        with patch.object(tracker, '_fetch', return_value={'reason': 'listing_id_found', 'imdb_id': 'tt2543164'}) as fetch:
            self.lookup()
            self.lookup()
            self.assertEqual(fetch.call_count, 1)
            self.release['name'] = 'Changed'
            tracker._NEXT_REQUEST = 0
            self.lookup()
            self.assertEqual(fetch.call_count, 2)
            with patch.object(tracker.time, 'monotonic', return_value=float('inf')):
                self.lookup()
            self.assertEqual(fetch.call_count, 3)

    def test_429_honors_retry_after_globally_and_no_waiting(self):
        with patch.object(tracker.requests, 'Session') as session, patch.object(tracker.time, 'monotonic', return_value=100):
            instance, response = self.response(session, 429, headers={'Retry-After': '3600'})
            self.assertEqual(self.lookup()['reason'], 'rate_limited')
            self.release['info_url'] = URL + '2'
            self.assertEqual(self.lookup()['reason'], 'rate_limited')
            instance.get.assert_called_once()
            self.assertEqual(tracker._NEXT_REQUEST, 3700)
        self.assertEqual(tracker._backoff('invalid'), 60)
        self.assertEqual(tracker._backoff('-1'), 60)

    def test_single_flight_and_rate_guard(self):
        with tracker._LOCK, patch.object(tracker, '_fetch') as fetch:
            self.assertEqual(self.lookup()['reason'], 'lookup_busy')
        fetch.assert_not_called()
        tracker._NEXT_REQUEST = float('inf')
        with patch.object(tracker, '_fetch') as fetch:
            self.assertEqual(self.lookup()['reason'], 'rate_limited')
        fetch.assert_not_called()

    def test_bad_cookie_file_fails_closed_and_preflight_redacts_values(self):
        env = dict(VALID, MOVIE_INTEL_TL_METADATA_ENABLED='1', MOVIE_INTEL_TL_COOKIE_FILE=str(self.path))
        self.assertEqual(configuration_errors(env), [])
        for content in ('not json', '{}', '[]', '{"session":"cookie\\nheader"}'):
            self.path.write_text(content)
            with patch.object(tracker, '_fetch') as fetch:
                self.assertEqual(self.lookup()['reason'], 'authentication_unavailable')
            fetch.assert_not_called()
            errors = configuration_errors(env)
            self.assertTrue(errors)
            self.assertNotIn(str(self.path), str(errors))
        self.path.write_text('{"session":"fixture"}')
        self.path.chmod(0o644)
        self.assertEqual(self.lookup()['reason'], 'authentication_unavailable')
        link = self.path.parent / 'symlink.json'
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            tracker.cookie_file(str(link))
        self.assertTrue(configuration_errors(dict(VALID, MOVIE_INTEL_TL_METADATA_ENABLED='yes')))


if __name__ == '__main__':
    unittest.main()
