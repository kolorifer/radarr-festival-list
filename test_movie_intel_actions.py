import unittest
from unittest.mock import patch

import movie_intel_service as svc


PAYLOAD = {
    "event": "action.rejected",
    "timestamp": "2026-10-12T10:00:00Z",
    "data": {
        "release": {
            "type": "movie",
            "name": "Arrival.2016.2160p.UHD.BluRay.REMUX",
            "title": "Arrival",
            "year": 2016,
            "protocol": "torrent",
            "timestamp": "2026-10-12T09:59:00Z",
            "download_url": "https://tracker.invalid/download/PRIVATE",
            "size": 123,
        },
        "indexer": {"name": "TorrentLeech", "protocol": "torrent"},
        "result": {"rejections": ["Unknown Movie. Unable to match to existing movie in Library using release title."]},
    },
}

META = {
    "tmdb_id": 329865,
    "imdb_id": "tt2543164",
    "title": "Arrival",
    "year": "2016",
    "poster_url": "https://image.invalid/poster.jpg",
}


class MovieIntelActionTests(unittest.TestCase):
    def test_pending_action_keeps_private_url_server_side(self):
        captured = {}

        def fake_create(row):
            captured.update(row)
            return "opaque-token"

        with patch.object(svc, "radarr_configured", return_value=True), \
             patch.object(svc, "create_action", side_effect=fake_create):
            token = svc.create_pending_action(PAYLOAD, META)
        self.assertEqual(token, "opaque-token")
        self.assertEqual(captured["release"]["download_url"], "https://tracker.invalid/download/PRIVATE")
        self.assertNotIn("download_url", str(captured["movie"]))

    def test_action_is_only_offered_for_unknown_movie(self):
        payload = {
            "event": "action.rejected",
            "data": {
                "release": dict(PAYLOAD["data"]["release"]),
                "result": {"rejections": ["Existing file meets cutoff"]},
            },
        }
        with patch.object(svc, "radarr_configured", return_value=True), patch.object(svc, "create_action") as create:
            self.assertIsNone(svc.create_pending_action(payload, META))
        create.assert_not_called()

    def test_telegram_button_contains_only_opaque_action_url(self):
        url = "https://example.invalid/movie-intel/action/opaque-token"
        body = svc._telegram_photo_payload("https://image.invalid/p.jpg", "caption", action_url=url)
        button = body["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(button["url"], url)
        self.assertNotIn("PRIVATE", str(body))

    def test_public_action_url_uses_existing_nginx_prefix(self):
        headers = {"X-Forwarded-Host": "example.invalid"}
        with patch.object(svc, "PUBLIC_BASE_URL", ""), patch.object(svc, "PUBLIC_PATH", "/movie-intel"):
            url = svc.public_action_url(headers, "abcDEF_12345678901234567890")
        self.assertEqual(url, "https://example.invalid/movie-intel/action/abcDEF_12345678901234567890")

    def test_confirmation_page_never_contains_private_download_url(self):
        action = {
            "movie": META,
            "release": {"name": "Arrival.2016.2160p", "download_url": "https://tracker.invalid/PRIVATE"},
        }
        context = {
            "roots": [{"id": 1, "path": "/movies"}],
            "profiles": [{"id": 2, "name": "4K Remux"}],
            "root_default": "/movies",
            "profile_default": 2,
        }
        page = svc.render_confirmation(action, context)
        self.assertIn("Arrival.2016.2160p", page)
        self.assertIn("4K Remux", page)
        self.assertNotIn("PRIVATE", page)
        self.assertNotIn("tracker.invalid", page)
        self.assertIn("without an indexer search", page)


if __name__ == "__main__":
    unittest.main()
