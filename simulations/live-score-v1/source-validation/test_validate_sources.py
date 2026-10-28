import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from http.client import IncompleteRead
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('validate_sources', HERE / 'validate_sources.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
NOW = '2026-10-28T00:00:00Z'


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.expected = v.cohort()[v.EXPECTED_IDS[0]]
        self.row = copy.deepcopy(json.loads((HERE / 'fixtures/synthetic.json').read_text())['observations'][0])

    def validate(self, **changes):
        return v.validate_observation(dict(self.row, **changes), self.expected, NOW)

    def test_source_specific_scales_and_invalid_numbers(self):
        for source, valid, invalid in [('imdb', [1, 10, '7.1'], [0, 0.5, 10.1]),
                                       ('letterboxd', [0.5, 5, '3.7'], [0, 5.1, 7.1])]:
            for rating in valid:
                with self.subTest(source=source, rating=rating):
                    self.assertTrue(self.validate(source=source, rating=rating)['eligible_pair'])
            for rating in invalid + [True, float('nan'), float('inf'), 'NaN', '-1', [], '7,1']:
                with self.subTest(source=source, rating=rating):
                    with self.assertRaises(v.InvalidObservation):
                        self.validate(source=source, rating=rating)

    def test_missing_and_zero_are_distinct_no_half_substitution(self):
        for rating, count in [(None, 123), (7.1, None), ('\\N', '\\N')]:
            observed = self.validate(rating=rating, count=count)
            self.assertIn('pair_missing', observed['flags'])
            self.assertFalse(observed['eligible_pair'])
        observed = self.validate(rating=None, count=0)
        self.assertEqual(observed['count'], 0)
        self.assertIn('zero_ratings', observed['flags'])
        with self.assertRaises(v.InvalidObservation):
            self.validate(count=0)

    def test_invalid_counts_not_rounded_or_expanded(self):
        for count in [True, -1, 1.1, 123.0, float('nan'), '1.2K', '1,200', '1e3', '']:
            with self.subTest(count=count), self.assertRaises(v.InvalidObservation):
                self.validate(count=count)
        self.assertEqual(self.validate(count='123')['count'], 123)

    def test_unknown_count_meaning_precision_and_weightedness_block_pair(self):
        for changes in [dict(count_semantics=s) for s in ['watches', 'reviews', 'likes', None]] + [
                dict(count_precision='rounded'), dict(rating_semantics='composite'),
                dict(rating_semantics='normalized_score')]:
            with self.subTest(changes=changes):
                self.assertFalse(self.validate(**changes)['eligible_pair'])

    def test_exact_identity_and_source_only(self):
        for change in [dict(imdb_id='tt29893755'), dict(imdb_id=[v.EXPECTED_IDS[0]]),
                       dict(tmdb_id=999), dict(tmdb_id=None), dict(tmdb_id=858024.0), dict(source='tmdb'),
                       dict(source='mdblist_composite')]:
            with self.subTest(change=change), self.assertRaises(v.InvalidObservation):
                self.validate(**change)

    def test_measurement_clock_is_never_request_clock(self):
        unknown = self.validate()
        self.assertIsNone(unknown['measurement_at'])
        self.assertIn('measurement_time_unknown', unknown['flags'])
        old = self.validate(measurement_at='2026-08-01T00:00:00Z')
        self.assertEqual(old['measurement_at'], '2026-08-01T00:00:00Z')
        self.assertIn('measurement_at_least_30_days_old', old['flags'])
        for time in ['2026-10-29T00:00:00Z', '2026-08-01', 'garbage']:
            with self.subTest(time=time), self.assertRaises(v.InvalidObservation):
                self.validate(measurement_at=time)

    def response(self, identity):
        expected = v.cohort()[identity]
        rows = [dict(self.row, imdb_id=identity, tmdb_id=expected['tmdb_id']),
                dict(self.row, imdb_id=identity, tmdb_id=expected['tmdb_id'],
                     source='letterboxd', rating=3.7)]
        return {'status': 200, 'observations': rows}

    def test_bounded_eight_exact_operations_and_lower_account_limit(self):
        calls = []
        def transport(identity):
            calls.append(identity)
            return self.response(identity)
        result = v.SyntheticTrial().run(transport, 1000, NOW)
        self.assertEqual(calls, list(v.EXPECTED_IDS))
        self.assertEqual(result['aggregate']['valid_pairs'], 16)
        self.assertEqual(result['attempts'], 8)
        for allowance in [0, 1, 3]:
            calls.clear()
            result = v.SyntheticTrial().run(transport, allowance, NOW)
            self.assertEqual(len(calls), allowance)
            self.assertEqual(result['stop_reason'], 'allowance_exhausted')

    def test_auth_rate_limit_failures_never_retry_or_leak(self):
        canary = 'SYNTHETIC_SECRET_DO_NOT_EMIT'
        for code, reason in [(401, 'auth_failure'), (403, 'auth_failure'),
                             (429, 'rate_limited'), (500, 'http_failure')]:
            calls = []
            def transport(identity):
                calls.append(identity)
                return {'status': code, 'body': canary,
                        'headers': {'Retry-After': '120', 'Authorization': canary}}
            result = v.SyntheticTrial().run(transport, 8, NOW)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['stop_reason'], reason)
            self.assertEqual(result['retry_after_seconds'], 120)
            self.assertNotIn(canary, json.dumps(result))
        self.assertEqual(v.retry_after_seconds('Wed, 28 Oct 2026 00:02:00 GMT', NOW), 120)
        self.assertIsNone(v.retry_after_seconds(canary, NOW))

    def test_timeout_transport_error_redaction(self):
        for exception, reason in [(TimeoutError('SYNTHETIC_SECRET'), 'timeout'),
                                  (URLError('SYNTHETIC_SECRET'), 'invalid_or_unavailable_response')]:
            def transport(identity):
                raise exception
            result = v.SyntheticTrial().run(transport, 8, NOW)
            self.assertEqual(result['attempts'], 1)
            self.assertEqual(result['stop_reason'], reason)
            self.assertNotIn('SYNTHETIC_SECRET', json.dumps(result))

    def test_account_exhaustion_stops_without_sleep(self):
        def transport(identity):
            result = self.response(identity)
            result['headers'] = {'X-RateLimit-Remaining': '0'}
            return result
        self.assertEqual(v.SyntheticTrial().run(transport, 8, NOW)['attempts'], 1)

        def lower_allowance(identity):
            result = self.response(identity)
            result['headers'] = {'X-RateLimit-Remaining': '1'}
            return result
        self.assertEqual(v.SyntheticTrial().run(lower_allowance, 8, NOW)['attempts'], 2)

    def test_ambiguous_or_cross_response_pairs_rejected(self):
        for rows in [[self.row], [self.row, self.row], [], [None, None],
                     [dict(self.row, count=None), dict(self.row, rating=None)]]:
            result = v.SyntheticTrial().run(lambda _: {'status': 200, 'observations': rows}, 8, NOW)
            self.assertEqual(result['stop_reason'], 'invalid_or_unavailable_response')
            self.assertEqual(result['aggregate']['observations_checked'], 0)

        response = self.response(v.EXPECTED_IDS[0])
        response['observations'][0]['count'] = None
        response['observations'][1]['rating'] = None
        result = v.SyntheticTrial().run(lambda _: response, 1, NOW)
        self.assertEqual(result['aggregate']['valid_pairs'], 0)
        self.assertEqual(result['aggregate']['missing_pairs'], 2)

    def test_public_aggregate_allowlist_redacts_extra_fields(self):
        observed = self.validate(secret='SYNTHETIC_SECRET', raw_response='SYNTHETIC_RAW')
        result = json.dumps(v.aggregate_gate([observed]))
        for forbidden in ['SYNTHETIC_', self.row['imdb_id'], '7.1', '123', 'rating"']:
            self.assertNotIn(forbidden, result)

    def test_offline_default_and_explicit_two_part_network_gate(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(v.main([]), 0)
            self.assertEqual(json.loads(stdout.getvalue())['network_requests'], 0)
        for flags in [['--imdb-personal-check'], ['--accept-imdb-conditions']]:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                v.main(flags)
        with patch.object(v, 'imdb_personal_check', return_value={'status': 'UNAVAILABLE'}) as call:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(v.main(['--imdb-personal-check', '--accept-imdb-conditions']), 1)
            call.assert_called_once()

    def test_cohort_matches_pinned_evidence_and_task2_identity(self):
        manifest = json.loads((HERE / 'cohort.json').read_text())
        repo = HERE.parents[2]
        evidence = repo / manifest['identity_evidence_path']
        self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), manifest['identity_evidence_sha256'])
        by_id = {r['imdb_id']: r for r in json.loads(evidence.read_text())['films']}
        for row in manifest['films']:
            for key, value in row.items():
                self.assertEqual(value, by_id[row['imdb_id']][key])
        task2 = json.loads((HERE.parent / 'task2/results.json').read_text())
        # Actual baseline structure is pinned by the source packet manifest.
        self.assertIn('films', task2)
        task2_ids = {r['imdb_id']: r for r in task2['films']}
        for row in manifest['films']:
            self.assertEqual(row['tmdb_id'], task2_ids[row['imdb_id']]['tmdb_id'])

    def tsv(self, rows):
        return gzip.compress(('tconst\taverageRating\tnumVotes\n' + rows).encode())

    def test_imdb_synthetic_schema_exact_ids_missing_and_no_values(self):
        blob = self.tsv(v.EXPECTED_IDS[0] + '\t7.1\t123\n' + 'tt0000000\t9.9\t987\n')
        result = v.extract_imdb(blob, NOW)
        self.assertEqual(result['exact_ids_present'], 1)
        self.assertEqual(result['exact_ids_absent'], 7)
        self.assertEqual(result['aggregate']['valid_pairs'], 1)
        self.assertNotIn('7.1', json.dumps(result))
        absent = v.extract_imdb(self.tsv(''), NOW)
        self.assertEqual(absent['exact_ids_absent'], 8)

    def test_imdb_duplicates_bad_header_and_invalid_pair_fail_closed(self):
        row = v.EXPECTED_IDS[0] + '\t7.1\t123\n'
        for blob in [self.tsv(row + row), gzip.compress(b'wrong\theader\n'),
                     self.tsv(v.EXPECTED_IDS[0] + '\tNaN\t123\n')]:
            with self.subTest(blob_size=len(blob)), self.assertRaises(v.InvalidObservation):
                v.extract_imdb(blob, NOW)

    def test_wire_decompression_and_time_bounds(self):
        with patch.object(v, 'MAX_COMPRESSED', 3), self.assertRaises(v.InvalidObservation):
            v.read_bounded(io.BytesIO(b'1234'))
        with patch.object(v, 'MAX_DECOMPRESSED', 3), self.assertRaises(v.InvalidObservation):
            v.extract_imdb(self.tsv(''), NOW)
        with self.assertRaises(v.InvalidObservation):
            v.read_bounded(io.BytesIO(b''), clock=iter([0, 100]).__next__)

    def test_live_wrapper_one_read_no_redirect_no_raw_errors(self):
        blob = self.tsv(v.EXPECTED_IDS[0] + '\t7.1\t123\n')
        response = io.BytesIO(blob)
        response.status = 200
        response.headers = {'Last-Modified': 'Tue, 27 Oct 2026 12:00:00 GMT',
                            'ETag': '"abc123"', 'Other': 'SYNTHETIC_SECRET'}
        opener = unittest.mock.Mock()
        opener.open.return_value = response
        with patch.object(v, 'build_opener', return_value=opener):
            report = v.imdb_personal_check()
        self.assertEqual(opener.open.call_count, 1)
        request = opener.open.call_args[0][0]
        self.assertEqual(request.full_url, v.IMDB_URL)
        self.assertEqual(request.get_method(), 'GET')
        self.assertEqual(report['status'], 'CHECKED')
        self.assertEqual(report['compressed_sha256'], hashlib.sha256(blob).hexdigest())
        self.assertNotIn('SYNTHETIC_SECRET', json.dumps(report))
        self.assertIsNone(v.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org'))
        for error in [HTTPError(v.IMDB_URL, 403, 'SYNTHETIC_SECRET', {}, io.BytesIO(b'SYNTHETIC_RAW')),
                      URLError('SYNTHETIC_SECRET'), TimeoutError('SYNTHETIC_SECRET'),
                      IncompleteRead(b'SYNTHETIC_RAW', 100)]:
            opener.open.side_effect = error
            with patch.object(v, 'build_opener', return_value=opener):
                report = v.imdb_personal_check()
            self.assertEqual(report['status'], 'UNAVAILABLE')
            self.assertNotIn('SYNTHETIC_SECRET', json.dumps(report))
            self.assertNotIn('sample', report)


if __name__ == '__main__':
    unittest.main()
