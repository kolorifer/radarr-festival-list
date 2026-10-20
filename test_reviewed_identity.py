"""Issue #45 regressions: fictional IDs and release references, no live effects."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import reviewed_identity as reviewed
import movie_intel_service as svc
import tmdb_resolver as tmdb
from deployment_config import configuration_errors
from test_movie_intel_actions import PAYLOAD


class ReviewedIdentityTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.tmp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.path = Path(self.tmp) / 'reviewed.json'
        self.stack.enter_context(patch.dict(os.environ, {reviewed.ENV_NAME: str(self.path)}))
        # Synthetic host: real host/redirect checks remain in adapter regressions.
        self.url_check = self.stack.enter_context(patch.object(reviewed, 'valid_listing_url', return_value=True))
        self.stack.enter_context(patch.object(svc, 'INDEX', {}))
        self.stdout = io.StringIO()
        self.stack.enter_context(contextlib.redirect_stdout(self.stdout))
        self.legacy = self.stack.enter_context(patch.object(svc, 'resolve_movie', side_effect=AssertionError('no title fallback')))
        self.create = self.stack.enter_context(patch.object(svc, 'create_action', return_value='synthetic-token'))
        self.send = self.stack.enter_context(patch.object(svc, '_telegram_request', side_effect=AssertionError('no Telegram')))
        for name in ('ensure_movie', 'push_release'):
            self.stack.enter_context(patch.object(svc, name, side_effect=AssertionError('no acquisition')))
        self.setup_case('hamnet-2025')

    def setup_case(self, rule):
        observed, year, canonical, canonical_year = reviewed.RULES[rule]
        self.rule = rule
        self.imdb = 'tt0000001' if rule == 'hamnet-2025' else 'tt0000002'
        self.movie_id = 101 if rule == 'hamnet-2025' else 102
        self.payload = copy.deepcopy(PAYLOAD)
        self.payload['data']['indexer'] = {'name': 'TorrentLeech'}
        self.payload['data']['release'].update(title=observed, year=int(year),
            name='Synthetic reviewed release', info_url='https://tracker.invalid/listing/fixture')
        self.details = dict(id=self.movie_id, title=canonical, original_title=canonical,
            release_date=f'{canonical_year}-01-01', external_ids={'imdb_id': self.imdb})
        self.find = {'movie_results': [{'id': self.movie_id}]}
        self.registry = {'version': 1, 'rules': [{'rule': rule, 'imdb_id': self.imdb,
            'tmdb_id': self.movie_id, 'source_sha256': reviewed.source_fingerprint(self.payload['data']['release'], self.imdb),
            'evidence_sha256': 'a' * 64}]}
        self.write_registry()
        tmdb._ID_CACHE.clear()

    def write_registry(self):
        self.path.write_text(json.dumps(self.registry))
        self.path.chmod(0o600)

    def context(self, lookup=None):
        lookup = lookup or {'reason': 'listing_id_found', 'source': 'torrentleech_listing', 'imdb_id': self.imdb}
        with patch.object(svc, 'lookup_listing', return_value=lookup), \
             patch.object(tmdb, '_get', side_effect=lambda path, params: self.find if path.startswith('/find/') else self.details):
            return svc.build_movie_context(self.payload)

    def test_hamnet_full_correction_and_title_only_failure(self):
        before = copy.deepcopy(self.payload)
        with patch.object(tmdb, '_get', side_effect=lambda path, params: self.find if path.startswith('/find/') else self.details):
            self.assertEqual(tmdb.resolve_external_movie('Hamnet 2025', 2016, imdb_id=self.imdb)['identity_reason'], 'title_conflict')
            self.assertEqual(tmdb.resolve_external_movie('Hamnet', 2016, imdb_id=self.imdb)['identity_reason'], 'year_conflict')
        context = self.context()
        self.assertEqual(context['meta']['identity_status'], 'verified_tmdb')
        self.assertEqual(context['meta']['identity_correction'], self.rule)
        self.assertEqual(context['meta']['year'], '2025')
        self.assertIn('<b>Hamnet</b> (2025)', context['text'])
        self.assertIn('Synthetic reviewed release', context['text'])
        self.assertEqual(self.payload, before)
        self.create.assert_not_called()
        self.send.assert_not_called()
        self.legacy.assert_not_called()

    def test_bruce_typo_exact_binding_and_revocation(self):
        self.setup_case('bruce-almiighty-2003')
        before = copy.deepcopy(self.payload)
        self.assertEqual(self.context()['meta']['identity_correction'], self.rule)
        self.assertEqual(self.payload, before)
        for field, value in [('title', 'Bruce Almiighty Extra'), ('title', 'bruce almiighty'),
                             ('year', 2004), ('name', 'Another edition'),
                             ('info_url', 'https://tracker.invalid/listing/another')]:
            self.setup_case('bruce-almiighty-2003')
            self.payload['data']['release'][field] = value
            self.assertNotIn('identity_correction', self.context()['meta'])
        self.setup_case('bruce-almiighty-2003')
        self.registry['rules'][0]['tmdb_id'] = 999
        self.write_registry()
        self.assertEqual(self.context()['meta']['identity_reason'], 'identity_conflict')
        self.setup_case('bruce-almiighty-2003')
        self.assertEqual(self.context()['meta']['identity_status'], 'verified_tmdb')
        self.registry['rules'] = []
        self.write_registry()
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')
        self.create.assert_not_called()
        self.send.assert_not_called()

    def test_all_three_reviewed_rules_can_coexist(self):
        rows = []
        for rule in reviewed.RULES:
            self.setup_case(rule)
            rows.extend(self.registry['rules'])
        self.registry['rules'] = rows
        self.write_registry()
        self.assertEqual(len(reviewed.read_rules(str(self.path))), 3)

    def test_exact_jazz_alias_only(self):
        self.setup_case('not-not-jazz-2024')
        self.assertEqual(self.context()['meta']['identity_status'], 'verified_tmdb')
        self.assertEqual(self.context()['meta']['identity_correction'], self.rule)
        for title in ('Medeski Martin Wood Not Not Jazz Extra', 'Medeski Martin Wood Other Film',
                      'medeski martin wood not not jazz', 'Medeski, Martin & Wood Not Not Jazz'):
            with self.subTest(title=title):
                self.payload['data']['release']['title'] = title
                self.assertNotEqual(self.context()['meta']['identity_status'], 'verified_tmdb')

    def test_exact_provenance_changes_rejected(self):
        for rule in reviewed.RULES:
            for field, value in [('title', 'Hamnet 2025 2016'), ('year', 2023), ('name', 'Different release'),
                                 ('info_url', 'https://tracker.invalid/listing/other')]:
                with self.subTest(rule=rule, field=field):
                    self.setup_case(rule)
                    self.payload['data']['release'][field] = value
                    self.assertNotEqual(self.context()['meta']['identity_status'], 'verified_tmdb')
                    self.assertNotIn('identity_correction', self.context()['meta'])

    def test_wrong_source_and_conflicting_indexer_names_rejected(self):
        for indexer in ({}, {'name': 'Other'}, {'identifier': 'TorrentLeech', 'name': 'Other'}):
            self.payload['data']['indexer'] = indexer
            self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')
        self.setup_case('hamnet-2025')
        self.assertEqual(self.context({'reason': 'listing_id_found', 'source': 'other', 'imdb_id': self.imdb})['meta']['identity_reason'], 'title_conflict')

    def test_native_ids_do_not_substitute_for_reviewed_listing_provenance(self):
        self.payload['data']['release'].update(meta_imdb=self.imdb, meta_tmdb=self.movie_id)
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')

    def test_changed_listing_id_and_listing_failure_block(self):
        self.assertNotEqual(self.context({'reason': 'listing_id_found', 'source': 'torrentleech_listing', 'imdb_id': 'tt0000003'})['meta']['identity_status'], 'verified_tmdb')
        for reason in ('listing_mismatch', 'listing_id_conflict', 'login_required', 'rate_limited'):
            self.assertEqual(self.context({'reason': reason, 'source': 'torrentleech_listing'})['meta']['identity_status'], 'unresolved')

    def test_unique_mapping_roundtrip_expected_id_and_year_still_required(self):
        for change, reason in [('missing', 'tmdb_mapping_missing'), ('ambiguous', 'ambiguous_id_mapping'),
                               ('tv', 'non_movie_identity'), ('different_id', 'identity_conflict'),
                               ('roundtrip', 'identity_conflict'), ('year', 'year_conflict'), ('title', 'title_conflict')]:
            with self.subTest(change=change):
                self.setup_case('hamnet-2025')
                if change == 'missing': self.find = {'movie_results': []}
                if change == 'ambiguous': self.find['movie_results'].append({'id': 999})
                if change == 'tv': self.find['tv_results'] = [{'id': 999}]
                if change == 'different_id': self.find['movie_results'] = [{'id': 999}]
                if change == 'roundtrip': self.details['external_ids']['imdb_id'] = 'tt0000003'
                if change == 'year': self.details['release_date'] = '2016-01-01'
                if change == 'title': self.details.update(title='Another Movie', original_title='Another Movie')
                context = self.context()
                self.assertEqual(context['meta']['identity_reason'], reason)
                self.assertNotIn('identity_correction', context['meta'])
                with patch.object(svc, 'radarr_configured', return_value=True):
                    self.assertIsNone(svc.create_pending_action(self.payload, context['meta']))
                self.create.assert_not_called()

    def test_wrong_jazz_year_and_id_remain_blocked(self):
        self.setup_case('not-not-jazz-2024')
        self.details['release_date'] = '2023-01-01'
        self.assertEqual(self.context()['meta']['identity_reason'], 'year_conflict')
        self.setup_case('not-not-jazz-2024')
        self.registry['rules'][0]['tmdb_id'] = 999
        self.write_registry()
        self.assertEqual(self.context()['meta']['identity_reason'], 'identity_conflict')

    def test_local_canonical_identity_conflict_is_not_bypassed(self):
        with patch.object(svc, 'find_local', side_effect=lambda title, year, index: {'imdb_id': 'tt0000003'} if title == 'Hamnet' else None):
            self.assertEqual(self.context()['meta']['identity_reason'], 'local_identity_conflict')

    def test_revocation_ignores_warmed_identity_cache(self):
        self.assertEqual(self.context()['meta']['identity_status'], 'verified_tmdb')
        self.registry['rules'] = []
        self.write_registry()
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')

    def test_missing_disabled_invalid_and_insecure_file_fail_closed(self):
        self.path.unlink()
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')
        self.write_registry()
        self.path.chmod(0o644)
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')
        self.path.chmod(0o600)
        self.path.write_text('{malformed')
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')
        with patch.dict(os.environ, {reviewed.ENV_NAME: ''}):
            self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')

    def test_file_schema_rejects_unapproved_rules_duplicates_and_extra_fields(self):
        mutations = [lambda d: d.update(version=True), lambda d: d['rules'][0].update(rule='another-film'),
                     lambda d: d['rules'].append(copy.deepcopy(d['rules'][0])),
                     lambda d: d['rules'][0].update(title='Arbitrary Movie'),
                     lambda d: d['rules'][0].update(tmdb_id=True),
                     lambda d: d['rules'][0].update(source_sha256='bad'),
                     lambda d: d['rules'][0].update(evidence_sha256='bad')]
        original = copy.deepcopy(self.registry)
        for mutate in mutations:
            self.registry = copy.deepcopy(original)
            mutate(self.registry)
            self.write_registry()
            with self.assertRaises(ValueError): reviewed.read_rules(str(self.path))
            self.assertTrue(any(reviewed.ENV_NAME in e for e in configuration_errors({reviewed.ENV_NAME: str(self.path)})))
            self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')

    def test_symlink_oversize_and_invalid_url_rejected(self):
        link = Path(self.tmp) / 'link'
        link.symlink_to(self.path)
        with self.assertRaises(OSError): reviewed.read_rules(str(link))
        self.path.write_text(' ' * 17000)
        with self.assertRaises(ValueError): reviewed.read_rules(str(self.path))
        self.write_registry()
        self.url_check.return_value = False
        self.assertEqual(self.context()['meta']['identity_reason'], 'title_conflict')

    def test_other_four_pending_titles_never_get_correction(self):
        for title in ('Fragmentos', 'Steve Howe Live Legends', 'Syd Barrett Up Close And Personal', 'Rainbow In Performance'):
            self.payload['data']['release'].update(title=title, year=2025)
            self.find = {'movie_results': []}
            tmdb._ID_CACHE.clear()
            context = self.context()
            self.assertEqual(context['meta']['identity_status'], 'imdb_associated')
            with patch.object(svc, 'radarr_configured', return_value=True):
                self.assertIsNone(svc.create_pending_action(self.payload, context['meta']))
        self.create.assert_not_called()

    def test_eligible_action_keeps_original_release_and_audit_marker(self):
        for rule in reviewed.RULES:
            self.setup_case(rule)
            before = copy.deepcopy(self.payload)
            meta = self.context()['meta']
            with patch.object(svc, 'radarr_configured', return_value=True):
                self.assertEqual(svc.create_pending_action(self.payload, meta), 'synthetic-token')
            action = self.create.call_args.args[0]
            for key in ('title', 'year', 'name', 'download_url', 'info_url'):
                self.assertEqual(action['release'][key], before['data']['release'][key])
            self.assertEqual(action['movie']['identity_correction'], rule)
            self.assertEqual(self.payload, before)
        self.assertNotIn('tracker.invalid', self.stdout.getvalue())
        self.assertNotIn('tt000000', self.stdout.getvalue())

    def test_routine_notifications_still_skip_corrections(self):
        self.payload['data']['result']['rejections'] = ['Existing file meets cutoff']
        with patch.object(svc, 'reviewed_context') as correction:
            self.context()
        correction.assert_not_called()


if __name__ == '__main__':
    unittest.main()
