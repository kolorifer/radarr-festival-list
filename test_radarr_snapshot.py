"""Snapshot allowlist/privacy, read-only export and isolated publication failures."""
import base64
import copy
from datetime import datetime
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import radarr_snapshot as export
import radarr_movie_list_sync as sync

STAMP = "2026-10-14T12:00:00Z"


def movie(mid=1):
    return {"id": mid, "title": "Example", "year": 2024, "imdbId": "tt1234567",
            "tmdbId": 12345, "monitored": True, "hasFile": False,
            "movieFileId": 0, "added": STAMP, "tags": [2, 1],
            "path": "/private/movie", "rootFolderPath": "/private",
            "overview": "SECRET unrelated metadata", "downloadClient": "SECRET",
            "queue": [{"downloadUrl": "https://private.invalid/token"}]}


TAGS = [{"id": 1, "label": "movie-list"}, {"id": 2, "label": "ml-250-299"}]


class GitHub:
    def __init__(self, private=True, existing=False):
        self.private = private
        self.existing = existing
        self.calls = []
        self.data = None

    def request(self, path, method="GET", payload=None, missing=False):
        self.calls.append((path, method, payload))
        if "/contents/" not in path:
            return {"private": self.private, "full_name": export.REPOSITORY}
        if method == "PUT":
            self.data = payload["content"]
            return {"commit": {"sha": "commit"}}
        if self.data is not None:
            return {"content": self.data}
        if self.existing:
            return {"type": "file", "sha": "old-blob"}
        return None


class SnapshotTests(unittest.TestCase):
    def snapshot(self):
        return export.sanitize([movie()], TAGS, STAMP)

    def test_exact_allowlist_and_nested_metadata_excluded(self):
        data = self.snapshot()
        self.assertEqual(set(data), export.TOP_FIELDS)
        self.assertEqual(set(data["movies"][0]), export.MOVIE_FIELDS)
        encoded = export.encoded(data).decode()
        for secret in ("SECRET", "/private", "downloadUrl", "rootFolderPath", "overview", "queue"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(data["movies"][0]["tags"], ["ml-250-299", "movie-list"])

    def test_deterministic_sort_order_and_only_timestamp_changes(self):
        first = export.sanitize([movie(2), movie(1)], list(reversed(TAGS)), STAMP)
        second = export.sanitize([movie(1), movie(2)], TAGS, "2026-10-14T13:00:00Z")
        first.pop("generated_at"); second.pop("generated_at")
        self.assertEqual(export.encoded({**first, "generated_at": STAMP}),
                         export.encoded({**second, "generated_at": STAMP}))

    def test_identifiers_flags_and_null_imdb_preserved(self):
        m = movie(); m["imdbId"] = ""; m["monitored"] = False; m["hasFile"] = True
        m["movieFileId"] = 123
        row = export.sanitize([m], TAGS, STAMP)["movies"][0]
        self.assertIsNone(row["imdb_id"])
        self.assertFalse(row["monitored"]); self.assertTrue(row["has_file"])
        self.assertEqual(row["movie_file_id"], 123)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(export.SnapshotError):
            export.sanitize([movie(), movie()], TAGS, STAMP)

    def test_unknown_tag_rejected_not_silently_lost(self):
        m = movie(); m["tags"] = [99]
        with self.assertRaises(export.SnapshotError):
            export.sanitize([m], TAGS, STAMP)

    def test_duplicate_tag_ids_rejected(self):
        with self.assertRaises(export.SnapshotError):
            export.sanitize([movie()], TAGS + TAGS, STAMP)

    def test_unsafe_allowed_strings_block_export(self):
        for value in ("https://private.invalid/key", "/home/user/movies", "10.2.3.4",
                      "api_key=not-a-real-key", "Bearer: x", "C:\\private", "bad\nlabel"):
            with self.subTest(value=value), self.assertRaises(export.SnapshotError):
                m = movie(); m["title"] = value
                export.sanitize([m], TAGS, STAMP)

    def test_configured_secret_cannot_hide_in_title_or_tag(self):
        for target in ("title", "tag"):
            m = movie(); tags = copy.deepcopy(TAGS)
            if target == "title": m["title"] = "prefix SyntheticSecret suffix"
            else: tags[0]["label"] = "SyntheticSecret"
            with self.assertRaises(export.SnapshotError):
                export.sanitize([m], tags, STAMP, ["SyntheticSecret"])

    def test_unicode_and_legitimate_slash_title(self):
        m = movie(); m["title"] = "La Ciénaga / The Swamp"
        self.assertEqual(export.sanitize([m], TAGS, STAMP)["movies"][0]["title"], m["title"])

    def test_timestamp_normalization(self):
        m = movie(); m["added"] = "2026-10-14T14:00:00+02:00"
        self.assertEqual(export.sanitize([m], TAGS, STAMP)["movies"][0]["date_added"], STAMP)
        m["added"] = "2026-10-14T12:00:00"
        with self.assertRaises(export.SnapshotError):
            export.sanitize([m], TAGS, STAMP)

    def test_schema_validation_rejects_extra_fields_and_wrong_count(self):
        for mutation in ("extra", "count"):
            data = self.snapshot()
            if mutation == "extra": data["movies"][0]["path"] = "private"
            else: data["movie_count"] = 2
            with self.assertRaises(export.SnapshotError):
                export.validate(data)

    def test_public_repo_refused_before_snapshot_put(self):
        github = GitHub(private=False)
        with self.assertRaises(export.SnapshotError):
            export.publish(self.snapshot(), github)
        self.assertEqual([method for _, method, _ in github.calls], ["GET"])

    def test_wrong_repository_refused_without_requests(self):
        github = GitHub()
        with self.assertRaises(export.SnapshotError):
            export.publish(self.snapshot(), github, "kolorifer/radarr-festival-list")
        self.assertEqual(github.calls, [])

    def test_single_current_file_create_then_verified(self):
        github = GitHub()
        result = export.publish(self.snapshot(), github)
        self.assertEqual(result["status"], "published")
        writes = [c for c in github.calls if c[1] != "GET"]
        self.assertEqual(len(writes), 1)
        self.assertTrue(writes[0][0].endswith("/radarr-current.json"))
        self.assertNotIn("sha", writes[0][2])

    def test_update_uses_existing_blob_sha(self):
        github = GitHub(existing=True)
        export.publish(self.snapshot(), github)
        self.assertEqual(next(c[2] for c in github.calls if c[1] == "PUT")["sha"], "old-blob")

    def test_readback_mismatch_rejected(self):
        class Wrong(GitHub):
            def request(self, *args, **kwargs):
                result = super().request(*args, **kwargs)
                if self.data is not None and kwargs.get("method", "GET") == "GET" and result and "content" in result:
                    return {"content": base64.b64encode(b"{}").decode()}
                return result
        with self.assertRaises(export.SnapshotError):
            export.publish(self.snapshot(), Wrong())

    def test_local_atomic_private_file_on_publish_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(export.SnapshotError):
                export.refresh([movie()], TAGS, state=Path(directory), github=GitHub(False))
            path = Path(directory) / export.FILENAME
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            export.validate(json.loads(path.read_text()))
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_private_config_permissions_and_target(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"GH_TOKEN": "synthetic"}, clear=True):
            path = Path(directory) / "config"
            path.write_text("{}"); path.chmod(0o644)
            with self.assertRaises(export.SnapshotError): export.config(path)
            path.chmod(0o600)
            self.assertEqual(export.config(path), (export.REPOSITORY, "synthetic"))
            path.write_text('{"repository":"kolorifer/radarr-festival-list"}')
            with self.assertRaises(export.SnapshotError): export.config(path)

    def test_read_only_manual_export_uses_two_gets(self):
        calls = []
        def request(path, method="GET", payload=None):
            calls.append((path, method, payload))
            return [movie()] if path.startswith("/movie?") else TAGS
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sync.API, "request", side_effect=request), patch.object(export, "STATE", Path(directory)), \
                 patch.object(sync, "STATE", Path(directory) / "sync"), patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(export.main([]), 0)
        self.assertEqual(calls, [("/movie?excludeLocalCovers=true", "GET", None), ("/tag", "GET", None)])

    def test_failure_is_nonfatal_safe_and_no_retry(self):
        with patch.object(export, "refresh", side_effect=RuntimeError("SECRET URL /private")) as refresh:
            result = export.after_success({"movies": [], "tags": []})
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("SECRET", json.dumps(result))
        refresh.assert_called_once()

    def run_sync(self, mode, fail=False):
        from test_radarr_movie_list_sync import Fake
        api = Fake()
        api.movies = api.movies[:1]
        catalog = {"tt1": {"imdb_id": "tt1", "qualified": True, "overall_score": 250,
                           "title": "Existing", "year": 2020}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_config = root / "config"
            private_config.write_text('{"root_folder":"/movies","quality_profile_id":7}')
            private_config.chmod(0o600)
            with patch.object(sync.radarr, "_request", side_effect=api.request), patch.object(sync, "load_catalog", return_value=catalog), \
                 patch.object(sync, "STATE", root / "sync"), patch.object(export, "after_success", return_value={"status": "failed"}) as hook, \
                 patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
                if fail:
                    with patch.object(sync, "apply_plan", side_effect=sync.SyncError("failed")):
                        code = sync.main([mode, "--config", str(private_config), "--report", str(root / "report")])
                else:
                    code = sync.main([mode, "--config", str(private_config), "--report", str(root / "report")])
                report = json.loads((root / "report").read_text()) if (root / "report").exists() else None
                return code, hook.call_count, api.calls, report

    def test_dry_run_never_exports_or_writes(self):
        code, calls, api_calls, _ = self.run_sync("--dry-run")
        self.assertEqual((code, calls), (0, 0))
        self.assertTrue(all(method == "GET" for _, method, _ in api_calls))

    def test_failed_reconciliation_never_exports(self):
        code, calls, _, _ = self.run_sync("--apply", fail=True)
        self.assertEqual((code, calls), (1, 0))

    def test_successful_reconciliation_exports_once_failure_does_not_repeat(self):
        code, calls, api_calls, report = self.run_sync("--apply")
        self.assertEqual((code, calls), (0, 1))
        self.assertEqual(report["snapshot_publication"]["status"], "failed")
        writes = [(path, method) for path, method, _ in api_calls if method != "GET"]
        self.assertEqual(writes, [("/movie/editor", "PUT")])

    def test_http_failure_never_exposes_payload_or_token(self):
        from urllib.error import HTTPError
        github = export.GitHub("SYNTHETIC_SECRET")
        error = HTTPError("https://private.invalid", 403, "SECRET body", {}, None)
        with patch.object(github.opener, "open", side_effect=error):
            with self.assertRaises(export.SnapshotError) as caught:
                github.request("/repos/" + export.REPOSITORY)
        self.assertEqual(str(caught.exception), "GitHub request failed (HTTP 403)")

    def test_http_request_uses_only_github_and_bounded_timeout(self):
        github = export.GitHub("synthetic")
        response = io.BytesIO(b'{"private":true}')
        with patch.object(github.opener, "open", return_value=response) as opened:
            self.assertTrue(github.request("/repos/" + export.REPOSITORY)["private"])
        req = opened.call_args.args[0]
        self.assertTrue(req.full_url.startswith("https://api.github.com/repos/"))
        self.assertEqual(opened.call_args.kwargs["timeout"], 30)

    def test_redirect_refused(self):
        with self.assertRaises(export.SnapshotError):
            export.NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.invalid")


if __name__ == "__main__":
    unittest.main()
