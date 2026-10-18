import unittest
from unittest.mock import patch

import radarr_client as rc


class RadarrClientTests(unittest.TestCase):
    def test_selection_context_requires_explicit_multiple_choices(self):
        roots = [{"id": 1, "path": "/movies"}, {"id": 2, "path": "/archive"}]
        profiles = [{"id": 10, "name": "HD"}, {"id": 20, "name": "4K"}]
        movies = [
            {"monitored": True, "rootFolderPath": "/movies", "qualityProfileId": 20},
            {"monitored": True, "rootFolderPath": "/movies", "qualityProfileId": 20},
            {"monitored": True, "rootFolderPath": "/archive", "qualityProfileId": 10},
        ]
        with patch.object(rc, "get_root_folders", return_value=roots), \
             patch.object(rc, "get_quality_profiles", return_value=profiles), \
             patch.object(rc, "get_movies", side_effect=AssertionError("No full-library fetch")) as get_movies:
            ctx = rc.selection_context()
        self.assertIsNone(ctx["root_default"])
        self.assertIsNone(ctx["profile_default"])
        get_movies.assert_not_called()

    def test_ensure_movie_never_requests_search(self):
        added = {"id": 123, "tmdbId": 329865}
        with patch.object(rc, "get_movie_by_tmdb", side_effect=[None]), \
             patch.object(rc, "_request", return_value=added) as request:
            movie, created = rc.ensure_movie(329865, 20, "/movies", title="Arrival")
        self.assertTrue(created)
        self.assertEqual(movie["id"], 123)
        path = request.call_args.args[0]
        kwargs = request.call_args.kwargs
        self.assertEqual(path, "/movie")
        self.assertEqual(kwargs["method"], "POST")
        self.assertFalse(kwargs["payload"]["addOptions"]["searchForMovie"])
        self.assertEqual(kwargs["payload"]["qualityProfileId"], 20)
        self.assertEqual(kwargs["payload"]["rootFolderPath"], "/movies")

    def test_existing_movie_is_idempotent(self):
        existing = {"id": 77, "tmdbId": 329865}
        with patch.object(rc, "get_movie_by_tmdb", return_value=existing), \
             patch.object(rc, "_request") as request:
            movie, created = rc.ensure_movie(329865, 20, "/movies")
        self.assertFalse(created)
        self.assertEqual(movie["id"], 77)
        request.assert_not_called()

    def test_release_push_reuses_exact_private_url(self):
        release = {
            "name": "Arrival.2016.2160p.UHD.BluRay.REMUX",
            "protocol": "torrent",
            "timestamp": "2026-10-12T10:00:00Z",
            "download_url": "https://tracker.invalid/download/PRIVATE",
            "size": 123456,
            "seeders": 8,
            "leechers": 2,
        }
        body = rc.build_release_push(release, indexer={"name": "TorrentLeech"}, tmdb_id=329865)
        self.assertEqual(body["downloadUrl"], release["download_url"])
        self.assertEqual(body["title"], release["name"])
        self.assertEqual(body["tmdbId"], 329865)
        self.assertEqual(body["protocol"], "torrent")
        self.assertEqual(body["publishDate"], release["timestamp"])
        self.assertEqual(body["indexer"], "TorrentLeech")

    def test_push_surfaces_normal_radarr_rejection(self):
        release = {
            "name": "Arrival.2016.2160p",
            "protocol": "torrent",
            "timestamp": "2026-10-12T10:00:00Z",
            "download_url": "https://tracker.invalid/download/PRIVATE",
        }
        response = [{"rejected": True, "rejections": ["Quality is not wanted"]}]
        with patch.object(rc, "_request", return_value=response):
            with self.assertRaisesRegex(rc.RadarrError, "Quality is not wanted"):
                rc.push_release(release, tmdb_id=329865)

    def test_push_requires_one_confirmed_approval(self):
        release = {"name": "Arrival.2016.2160p", "protocol": "torrent", "timestamp": "2026-10-12T10:00:00Z", "download_url": "https://tracker.invalid/PRIVATE"}
        for response in (None, [], {}, [{"rejected": False}], [{"approved": False, "rejected": False}], [{"approved": True, "rejected": False}] * 2):
            with self.subTest(response=response), patch.object(rc, "_request", return_value=response):
                with self.assertRaises(rc.RadarrError):
                    rc.push_release(release)
        with patch.object(rc, "_request", return_value=[{"approved": True, "rejected": False}]):
            self.assertEqual(len(rc.push_release(release)), 1)


if __name__ == "__main__":
    unittest.main()
