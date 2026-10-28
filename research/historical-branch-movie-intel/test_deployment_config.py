import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import movie_intel_service as svc
from deployment_config import configuration_errors
from private_text import sanitize, redact_text
from deploy.run import read_environment


VALID = {
    "MOVIE_INTEL_WEBHOOK_SECRET": "w" * 32,
    "TELEGRAM_BOT_TOKEN": "test-bot", "TELEGRAM_CHAT_ID": "-100123",
    "TMDB_API_TOKEN": "test-tmdb", "RADARR_API_KEY": "test-radarr",
    "RADARR_URL": "http://127.0.0.1:7878/radarr",
    "MOVIE_INTEL_PUBLIC_BASE_URL": "https://example.invalid/movie-intel",
}


class DeploymentTests(unittest.TestCase):
    def test_valid_configuration(self):
        self.assertEqual(configuration_errors(VALID), [])

    def test_missing_values_report_names_only(self):
        with patch.dict("os.environ", {}, clear=True), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(svc.main(["--check-config"]), 1)
        self.assertIn("RADARR_API_KEY is required", err.getvalue())

    def test_rejects_unsafe_public_urls_and_bad_numbers(self):
        for value in ("http://example.invalid", "https://user:password@example.invalid", "https://example.invalid/?secret=test", "https://example.invalid/#fragment", "https://example.invalid:bad"):
            with self.subTest(value=value):
                errors = configuration_errors({**VALID, "MOVIE_INTEL_PUBLIC_BASE_URL": value, "TELEGRAM_TOPIC_ID": "not-a-number"})
                self.assertEqual(len(errors), 2)
                self.assertNotIn("password", str(errors))

    def test_local_mode_cannot_bind_publicly(self):
        with patch.object(svc, "HOST", "0.0.0.0"), patch.object(svc, "ThreadingHTTPServer") as server, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(svc.main(["--allow-unconfigured"]), 1)
        server.assert_not_called()

    def test_redacts_camelcase_urls_and_plaintext_secrets(self):
        with patch.dict("os.environ", {"RADARR_API_KEY": "synthetic-key"}):
            result = sanitize({"downloadUrl": "private-marker", "magnet_uri": "magnet:?xt=private-marker", "message": "failed https://tracker.invalid/private-marker synthetic-key"})
        self.assertNotIn("private-marker", str(result))
        self.assertNotIn("synthetic-key", str(result))
        self.assertIn("[redacted]", str(result))
        self.assertNotIn("tracker.invalid", redact_text("https://tracker.invalid/passkey"))

    def test_environment_file_does_not_evaluate_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment"
            sentinel = Path(directory) / "must-not-exist"
            path.write_text(f"# comment\nRADARR_API_KEY='$(touch {sentinel})'\nTELEGRAM_TOPIC_ID=\n")
            path.chmod(0o600)
            result = read_environment(path)
            self.assertEqual(result["RADARR_API_KEY"], f"$(touch {sentinel})")
            self.assertEqual(result["TELEGRAM_TOPIC_ID"], "")
            self.assertFalse(sentinel.exists())
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                read_environment(path)

    def test_invalid_port_and_ttl_report_names_without_traceback(self):
        env = {**os.environ, **VALID, "MOVIE_INTEL_PORT": "bad-value", "MOVIE_INTEL_ACTION_TTL_SECONDS": "bad-value"}
        result = subprocess.run([sys.executable, "movie_intel_service.py", "--check-config"], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MOVIE_INTEL_PORT", result.stderr)
        self.assertIn("MOVIE_INTEL_ACTION_TTL_SECONDS", result.stderr)
        self.assertNotIn("bad-value", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_launcher_preflight_with_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment"
            values = {**VALID, "MOVIE_INTEL_ACTION_STORE": str(Path(directory) / "actions.json"), "TMDB_CACHE_PATH": str(Path(directory) / "cache.json")}
            path.write_text("\n".join(f"{name}={value}" for name, value in values.items()))
            path.chmod(0o600)
            result = subprocess.run([sys.executable, "deploy/run.py", "--env-file", str(path), "--check-config"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("connectivity has not been checked", result.stdout)
            for name in ("RADARR_API_KEY", "TELEGRAM_BOT_TOKEN", "MOVIE_INTEL_WEBHOOK_SECRET"):
                self.assertNotIn(values[name], result.stdout + result.stderr)
