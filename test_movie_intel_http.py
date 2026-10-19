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
        tmdb._ID_CACHE.clear()
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
                elif path == '/tmdb/find/tt2543164':
                    self.respond({'movie_results': [{'id': 329865}]})
                elif path == '/tmdb/find/tt33503751':
                    self.respond({'movie_results': []})
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

    def test_accepted_curated_movie_annotations_cannot_create_actions_or_outcomes(self):
        from test_film_editions import META
        value=copy.deepcopy(PAYLOAD)
        value['event']='action.approved'
        value['data']['release'].update(title='Touch of Evil',year=1958,name='Touch.of.Evil.1958.1998.RECONSTRUCTED.2160p.REMUX',meta_imdb='tt0052311')
        value['data']['result']['rejections']=[]
        existing={'imdbId':'tt0052311','tmdbId':1480,'hasFile':True,'movieFile':{'edition':'Theatrical Cut'}}
        with patch.object(svc,'resolve_external_movie',return_value=META), patch.object(svc,'get_movie_by_tmdb',return_value=existing), patch.object(svc,'create_pending_action') as action, patch.object(svc,'observe_identity_outcome') as observe, patch('identity_retry.submit') as retry:
            status,body,_=self.request('/webhook/'+svc.WEBHOOK_SECRET,json.dumps(value).encode())
        self.assertEqual(status,200);self.assertFalse(json.loads(body)['action'])
        self.assertIn('Release Accepted',self.messages[0]['text'])
        self.assertIn('1998 reconstructed',self.messages[0]['text'])
        self.assertIn('Existing: 1958 theatrical',self.messages[0]['text'])
        self.assertNotIn('reply_markup',self.messages[0])
        action.assert_not_called();observe.assert_not_called();retry.assert_not_called()
        self.assertEqual(self.added,[]);self.assertEqual(self.pushed,[])

    def test_apollo_style_episode_gets_one_plain_diagnostic_no_action(self):
        value=copy.deepcopy(PAYLOAD)
        value['data']['release'].update(type='episode',category='Movies :: HD')
        with patch.object(svc,'observe_identity_outcome') as observe, patch.object(svc,'create_pending_action') as action:
            request=Request(self.base+'/webhook/test-secret',data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
            # Use the same configured secret as the existing HTTP fixture.
            request.full_url=self.base+'/webhook/'+svc.WEBHOOK_SECRET
            with urlopen(request) as response:result=json.load(response)
        self.assertEqual(result['mode'],'identity_diagnostic');self.assertFalse(result['action'])
        self.assertEqual(len(self.messages),1)
        self.assertNotIn('reply_markup',self.messages[0]);self.assertNotIn('download',self.messages[0]['text'].lower())
        action.assert_not_called();observe.assert_called_once()
        self.assertEqual(value['data']['release']['type'],'episode')
        self.assertEqual(self.added,[]);self.assertEqual(self.pushed,[])

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

    def test_external_id_webhook_approval_still_pushes_exactly_once(self):
        payload = copy.deepcopy(PAYLOAD)
        payload['data']['release'].update(meta_imdb='tt2543164', meta_tmdb='329865')
        path = self.webhook(payload)
        self.assertEqual(self.added, [])
        self.assertEqual(self.pushed, [])
        self.assertEqual(self.approve(path)[0], 200)
        self.assertFalse(self.added[0]['addOptions']['searchForMovie'])
        self.assertEqual(self.pushed[0]['downloadUrl'], payload['data']['release']['download_url'])
        self.assertEqual(self.approve(path)[0], 410)
        self.assertEqual(len(self.pushed), 1)

    def test_unmapped_id_webhook_has_no_button_or_acquisition(self):
        payload = copy.deepcopy(PAYLOAD)
        payload['data']['release'].update(title='Fragmentos', year=2025, meta_imdb='tt33503751')
        status, body, _ = self.request('/webhook/' + 'w' * 32, json.dumps(payload).encode())
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['action'])
        self.assertNotIn('reply_markup', self.messages[-1])
        self.assertIn('Indexer IMDb association only', self.messages[-1]['text'])
        self.assertEqual(self.added, [])
        self.assertEqual(self.pushed, [])

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

    def test_uncertain_push_cannot_be_retried_even_after_reload(self):
        path = self.webhook()
        with patch.object(svc, 'push_release', side_effect=radarr.RadarrError('Unable to reach Radarr')) as push:
            self.assertEqual(self.approve(path)[0], 502)
            self.assertEqual(self.approve(path)[0], 409)
            self.assertEqual(self.request(path)[0], 409)
        push.assert_called_once()

    def test_failed_state_persistence_prevents_radarr_writes(self):
        path = self.webhook()
        with patch.object(svc, 'update_action', return_value=False):
            self.assertEqual(self.approve(path)[0], 502)
        self.assertEqual(self.added, [])
        self.assertEqual(self.pushed, [])

    def test_storage_failure_preserves_notification_without_button(self):
        with patch.object(svc, 'create_action', side_effect=OSError('private details')):
            status, body, _ = self.request('/webhook/' + 'w' * 32, json.dumps(PAYLOAD).encode())
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['action'])
        self.assertIn('Arrival', self.messages[-1]['text'])
        self.assertNotIn('private details', self.logs.getvalue())

    def test_unrecognized_result_shape_falls_back_redacted(self):
        payload = copy.deepcopy(PAYLOAD)
        payload['data']['result'] = 'unexpected https://tracker.invalid/PRIVATE'
        status, _, _ = self.request('/webhook/' + 'w' * 32, json.dumps(payload).encode())
        self.assertEqual(status, 200)
        self.assertNotIn('reply_markup', self.messages[-1])
        self.assertNotIn('PRIVATE', str(self.messages))

    def test_unresolved_movie_has_no_approval_and_keeps_release(self):
        with patch.object(svc, 'resolve_movie', return_value=None):
            status, body, _ = self.request('/webhook/' + 'w' * 32, json.dumps(PAYLOAD).encode())
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['action'])
        self.assertNotIn('reply_markup', self.messages[-1])
        self.assertIn(PAYLOAD['data']['release']['name'], self.messages[-1]['text'])
        self.assertEqual(self.added, [])

    def test_corrupt_store_returns_unavailable_without_acquisition(self):
        path = self.webhook()
        actions.STORE_PATH.write_text('{invalid')
        self.assertEqual(self.request(path)[0], 503)
        self.assertEqual(self.approve(path)[0], 503)
        self.assertEqual(self.added, [])
        self.assertEqual(self.pushed, [])
