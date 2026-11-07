"""Invented Handler/SQLite boundary checks; no external I/O or live grant."""
from datetime import datetime, timezone
import time
import unittest
from unittest.mock import patch

import identity_triage_capture as capture
import test_identity_capture as fixtures


class CaptureDurationTests(unittest.TestCase):
    setUp = fixtures.CaptureTests.setUp
    save = fixtures.CaptureTests.save
    arm = fixtures.CaptureTests.arm
    request = fixtures.CaptureTests.request
    outcome = fixtures.CaptureTests.outcome

    def send_at(self, now):
        event = self.outcome(timestamp=datetime.fromtimestamp(now, timezone.utc).isoformat())
        with patch.object(capture.time, 'time', return_value=now):
            response, raw = self.request(event)
        self.assertIn(b'200 OK', response)
        return raw

    def assert_refused(self, expires, now):
        self.arm(expires_at=expires)
        self.send_at(now)
        self.assertFalse(self.server.capture.burned)
        for name in (capture.RESERVATION, capture.BODY, capture.RECEIPT):
            self.assertFalse((self.store.directory / name).exists())

    def test_expired_at_exact_boundary(self):
        now = time.time()
        self.assert_refused(now, now)

    def test_six_hour_exact_horizon_captures(self):
        now = time.time()
        self.assertEqual(capture.MAX_CAPTURE_HORIZON_SECONDS, 21600)
        self.arm(expires_at=now + 21600)
        raw = self.send_at(now)
        self.assertTrue(self.server.capture.burned)
        self.assertEqual((self.store.directory / capture.BODY).read_bytes(), raw)

    def test_over_horizon_refuses(self):
        now = time.time()
        self.assert_refused(now + 21600.001, now)

    def test_nan_refuses(self):
        self.assert_refused(float('nan'), time.time())

    def test_positive_infinity_refuses(self):
        self.assert_refused(float('inf'), time.time())

    def test_negative_infinity_refuses(self):
        self.assert_refused(float('-inf'), time.time())

    def test_six_hour_grant_still_captures_only_one_event(self):
        now = time.time()
        self.arm(expires_at=now + 21600)
        raw = self.send_at(now)
        retained = {name: (self.store.directory / name).read_bytes()
                    for name in (capture.RESERVATION, capture.BODY, capture.RECEIPT)}
        self.send_at(now + 1)
        self.assertTrue(self.server.capture.burned)
        self.assertEqual(retained[capture.BODY], raw)
        self.assertEqual(retained, {name: (self.store.directory / name).read_bytes()
                                    for name in retained})
