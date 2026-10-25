import copy
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import tmdb_resolver as resolver
import verified_identity_cache as cache
from deployment_config import configuration_errors

META = {'identity_status': 'verified_tmdb', 'identity_reason': 'external_id_verified',
        'imdb_id': 'tt1234567', 'tmdb_id': 99, 'title': 'Example', 'year': '2026',
        'matched_release_year': '2026', 'identity_year_basis': 'canonical_date'}


class VerifiedCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name).resolve() / 'verified.sqlite3'
        os.chmod(self.path.parent, 0o700)
        setting = patch.dict(os.environ, {cache.SETTING: str(self.path)})
        setting.start(); self.addCleanup(setting.stop)
        resolver._ID_CACHE.clear()
        self.addCleanup(resolver._ID_CACHE.clear)

    def resolve(self, **kwargs):
        return resolver.resolve_external_movie('Example', 2026, imdb_id='tt1234567', **kwargs)

    def test_verified_response_survives_memory_reset_without_network(self):
        with patch.object(resolver, '_resolve_external', return_value=copy.deepcopy(META)) as fetch:
            self.assertEqual(self.resolve(), META)
            self.assertEqual(fetch.call_count, 1)
        resolver._ID_CACHE.clear()
        with patch.object(resolver, '_resolve_external', side_effect=AssertionError('unexpected network')):
            self.assertEqual(self.resolve(), META)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_cached_response_cannot_bypass_changed_context_or_ids(self):
        with patch.object(resolver, '_resolve_external', return_value=copy.deepcopy(META)):
            self.resolve()
        for title, year, imdb, tmdb, typo in (
            ('Example 2',2026,'tt1234567',None,False),
            ('Example',2025,'tt1234567',None,False),
            ('Example',2026,'tt7654321',None,False),
            ('Example',2026,'tt1234567',100,False),
            ('Example',2026,'tt1234567',None,True),
        ):
            resolver._ID_CACHE.clear()
            blocked = {'identity_status':'needs_review','identity_reason':'identity_conflict'}
            with patch.object(resolver, '_resolve_external', return_value=blocked) as fetch:
                self.assertEqual(resolver.resolve_external_movie(title,year,imdb_id=imdb,tmdb_id=tmdb,allow_minor_typo=typo), blocked)
            fetch.assert_called_once()

    def test_failure_not_persisted_and_invalid_ids_not_cached(self):
        failure = {'identity_status':'unresolved','identity_reason':'metadata_api_unavailable'}
        with patch.object(resolver, '_resolve_external', return_value=failure) as fetch:
            self.resolve(); resolver._ID_CACHE.clear(); self.resolve()
            self.assertEqual(fetch.call_count,2)
        with patch.object(resolver, '_resolve_external') as fetch:
            self.assertEqual(resolver.resolve_external_movie('Example',2026,imdb_id='invalid')['identity_status'],'needs_review')
            fetch.assert_not_called()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('select count(*) from verified_cache').fetchone()[0],0)

    def test_expiry_and_clock_rollback_miss_without_renewing_on_read(self):
        with patch.object(cache.time,'time',return_value=1000):
            self.assertTrue(cache.put('test',['key'],META))
        for now, present in ((999,False),(1001,True),(1000+cache.TTL,False)):
            with patch.object(cache.time,'time',return_value=now):
                self.assertEqual(cache.get('test',['key']) is not None,present)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('select expires from verified_cache').fetchone()[0],1000+cache.TTL)

    def test_private_permissions_corruption_and_unavailable_store_are_misses(self):
        self.path.write_text('broken database');os.chmod(self.path,0o600)
        self.assertIsNone(cache.get('test',[]))
        self.assertFalse(cache.put('test',[],META))
        os.chmod(self.path,0o644)
        self.assertIsNone(cache.get('test',[]))
        self.assertTrue(any(cache.SETTING in e for e in configuration_errors()))
        with patch.object(resolver,'_resolve_external',return_value=META) as fetch:
            self.assertEqual(self.resolve(),META)
        fetch.assert_called_once()

    def test_capacity_and_payload_size_bounded(self):
        with patch.object(cache,'LIMIT',2):
            for number in range(3):
                with patch.object(cache.time,'time',return_value=1000+number):
                    self.assertTrue(cache.put('test',[number],META))
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('select count(*) from verified_cache').fetchone()[0],2)
        self.assertFalse(cache.put('test',[],{'oversize':'x'*32769}))

    def test_disabled_storage_never_creates_a_file(self):
        with patch.dict(os.environ,{cache.SETTING:''}):
            self.assertIsNone(cache.get('test',[]))
            self.assertFalse(cache.put('test',[],META))
        self.assertFalse(self.path.exists())

    def test_stored_response_inconsistent_with_key_is_not_accepted(self):
        key=('Example','2026','tt1234567','None',False)
        cache.put('external_movie',key,dict(META,imdb_id='tt7654321'))
        failure={'identity_status':'needs_review','identity_reason':'identity_conflict'}
        with patch.object(resolver,'_resolve_external',return_value=failure) as fetch:
            self.assertEqual(self.resolve(),failure)
        fetch.assert_called_once()
