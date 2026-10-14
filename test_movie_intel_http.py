"""Real local HTTP workflow; no production credentials or external side effects."""
import contextlib
import copy
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import movie_intel_service as svc
import pending_actions as actions
import radarr_client as radarr
import tmdb_resolver as tmdb
from test_movie_intel_actions import PAYLOAD


class HTTPFlowTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.messages, self.added, self.pushed = [], [], []
        self.telegram_ok = True
        self.rejection = None
        outer = self

        class Integrations(BaseHTTPRequestHandler):
            def respond(self, value, status=200):
                raw = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/tmdb/search/movie":
                    self.respond({"results": [{"id": 329865, "title": "Arrival", "release_date": "2016-11-11"}]})
                elif path == "/tmdb/movie/329865":
                    self.respond({"id": 329865, "title": "Arrival", "release_date": "2016-11-11", "external_ids": {"imdb_id": "tt2543164"}})
                elif path == "/radarr/api/v3/rootfolder":
                    self.respond([{"id": 1, "path": "/movies"}])
                elif path == "/radarr/api/v3/qualityprofile":
                    self.respond([{"id": 2, "name": "4K Remux"}])
                elif path == "/radarr/api/v3/movie":
                    self.respond(outer.added)
                else:
                    self.respond({}, 404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/botTEST/sendMessage":
                    outer.messages.append(body)
                    self.respond({"ok": outer.telegram_ok, "result": {"message_id": 1}})
                elif self.path == "/radarr/api/v3/movie":
                    self.assert_radarr_key()
                    outer.added.append({**body, "id": 77})
                    self.respond(outer.added[-1], 201)
                elif self.path == "/radarr/api/v3/release/push":
                    self.assert_radarr_key()
                    outer.pushed.append(body)
                    self.respond([{"approved": not bool(outer.rejection), "rejected": bool(outer.rejection), "rejections": [outer.rejection] if outer.rejection else []}])
                else:
                    self.respond({}, 404)

            def assert_radarr_key(self):
                outer.assertEqual(self.headers.get("X-Api-Key"), "test-radarr")

            def log_message(self, *args):
                pass

        def start(handler):
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def stop():
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            self.stack.callback(stop)
            return f"http://127.0.0.1:{server.server_port}"

        integration_url = start(Integrations)
        self.logs = io.StringIO()
        self.stack.enter_context(contextlib.redirect_stdout(self.logs))
        self.base = start(svc.Handler)
        for obj, name, value in (
            (actions, "STORE_PATH", Path(directory) / "actions.json"),
            (tmdb, "CACHE_PATH", Path(directory) / "cache.json"),
            (tmdb, "TOKEN", "test-tmdb"), (tmdb, "API_BASE", integration_url + "/tmdb"),
            (radarr, "RADARR_URL", integration_url + "/radarr"), (radarr, "RADARR_API_KEY", "test-radarr"),
            (svc, "WEBHOOK_SECRET", "w" * 32), (svc, "TELEGRAM_BOT_TOKEN", "TEST"),
            (svc, "TELEGRAM_CHAT_ID", "-100123"), (svc, "TELEGRAM_TOPIC_ID", ""),
            (svc, "PUBLIC_BASE_URL", "https://example.invalid/movie-intel"), (svc, "INDEX", {}),
        ):
            self.stack.enter_context(patch.object(obj, name, value))

        def telegram_transport(request, **kwargs):
            # Rewrite transport only; production serialization/response handling
            # runs unchanged against a local Telegram stand-in.
            target = integration_url + urlsplit(request.full_url).path
            return urlopen(Request(target, data=request.data, headers=dict(request.header_items()), method=request.get_method()), **kwargs)
        self.stack.enter_context(patch.object(svc, "urlopen", side_effect=telegram_transport))

    def request(self, path, data=None, content_type="application/json", headers=None):
        request = Request(self.base + path, data=data, headers={"Content-Type": content_type, **(headers or {})})
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, response.read().decode(), response.headers
        except HTTPError as response:
            return response.code, response.read().decode(), response.headers

    def webhook(self, payload=None):
        status, body, _ = self.request("/webhook/" + "w" * 32, json.dumps(payload or PAYLOAD).encode())
        self.assertEqual(status, 200, body)
        self.assertTrue(json.loads(body)["action"])
        url = self.messages[-1]["reply_markup"]["inline_keyboard"][0][0]["url"]
        return "/action/" + url.rsplit("/", 1)[1]

    def approve(self, path, root="/movies"):
        return self.request(path, urlencode({"root_folder": root, "quality_profile": 2}).encode(), "application/x-www-form-urlencoded")

    def test_webhook_confirmation_exact_release_and_single_use(self):
        path = self.webhook()
        status, page, headers = self.request(path)
        self.assertEqual(status, 200)
        self.assertIn("4K Remux", page)
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.approve(path)[0], 200)
        self.assertFalse(self.added[0]["addOptions"]["searchForMovie"])
        self.assertEqual(self.pushed[0]["downloadUrl"], PAYLOAD["data"]["release"]["download_url"])
        self.assertEqual(self.pushed[0]["tmdbId"], 329865)
        self.assertEqual(self.approve(path)[0], 410)
        self.assertEqual(self.request(path)[0], 410)
        for public in (page, json.dumps(self.messages), self.logs.getvalue()):
            self.assertNotIn("PRIVATE", public)
            self.assertNotIn("tracker.invalid", public)
            self.assertNotIn("w" * 32, public)
        self.assertEqual(actions.STORE_PATH.stat().st_mode & 0o777, 0o600)

    def test_concurrent_approvals_push_once(self):
        path = self.webhook()
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: self.approve(path)[0], range(2)))
        self.assertEqual(sorted(statuses), [200, 410])
        self.assertEqual(len(self.added), 1)
        self.assertEqual(len(self.pushed), 1)

    def test_invalid_selection_has_no_radarr_writes(self):
        path = self.webhook()
        self.assertEqual(self.approve(path, root="/unconfigured")[0], 502)
        self.assertEqual(self.added, [])
        self.assertEqual(self.pushed, [])
        self.assertIsNotNone(actions.get_action(path.rsplit("/", 1)[1]))

    def test_rejected_push_redacts_error_and_retry_reuses_movie(self):
        path = self.webhook()
        self.rejection = "Rejected https://tracker.invalid/download/PRIVATE"
        status, page, _ = self.approve(path)
        self.assertEqual(status, 502)
        self.assertNotIn("PRIVATE", page)
        self.assertNotIn("tracker.invalid", page)
        self.rejection = None
        self.assertEqual(self.approve(path)[0], 200)
        self.assertEqual(len(self.added), 1)

    def test_webhook_auth_and_unconfigured_fail_closed(self):
        body = json.dumps(PAYLOAD).encode()
        self.assertEqual(self.request("/webhook/wrong", body)[0], 404)
        with patch.object(svc, "WEBHOOK_SECRET", ""):
            self.assertEqual(self.request("/webhook", body)[0], 503)
        self.assertEqual(self.messages, [])

    def test_plaintext_and_camelcase_passthrough_redact_urls(self):
        for body in (b"test https://tracker.invalid/PRIVATE", json.dumps({"event": "test", "data": {"downloadUrl": "PRIVATE", "magnetUrl": "PRIVATE"}}).encode()):
            self.assertEqual(self.request("/webhook/" + "w" * 32, body)[0], 200)
        self.assertNotIn("PRIVATE", json.dumps(self.messages))

    def test_telegram_failure_is_not_reported_as_success(self):
        self.telegram_ok = False
        status, body, _ = self.request("/webhook/" + "w" * 32, json.dumps(PAYLOAD).encode())
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body)["error"], "RuntimeError")

    def test_publish_date_alias_survives_pending_action(self):
        payload = copy.deepcopy(PAYLOAD)
        release = payload["data"]["release"]
        release["publishDate"] = release.pop("timestamp")
        payload.pop("timestamp")
        path = self.webhook(payload)
        self.assertEqual(self.approve(path)[0], 200)
        self.assertEqual(self.pushed[0]["publishDate"], release["publishDate"])

    def test_d016_score_route_does_not_automatically_acquire(self):
        from movie_intel import build_index
        payload = copy.deepcopy(PAYLOAD)
        index = build_index()
        sound = next(r for r in index.values() if r["title"] == "Sound of Metal")
        payload["data"]["release"].update(title=sound["title"], year=sound["year"])
        meta = {"tmdb_id": 329865, "imdb_id": "tt5363618", "title": "Sound of Metal", "year": sound["year"]}
        with patch.object(svc, "INDEX", index), patch.object(svc, "resolve_movie", return_value=meta):
            path = self.webhook(payload)
        self.assertIn("Our model: QUALIFIES", self.messages[-1]["text"])
        self.assertIn("evidence_score_225", self.messages[-1]["text"])
        self.assertNotIn("convergence", self.messages[-1]["text"])
        self.assertEqual(self.added, [])
        self.assertEqual(self.pushed, [])
        self.assertEqual(self.approve(path)[0], 200)
        self.assertEqual(len(self.added), 1)
        self.assertEqual(len(self.pushed), 1)
        self.assertFalse(self.added[0]["addOptions"]["searchForMovie"])
