import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pending_actions as pa


class PendingActionTests(unittest.TestCase):
    def test_action_round_trip_and_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            with patch.object(pa, "STORE_PATH", path):
                token = pa.create_action({"movie": {"tmdb_id": 1}, "release": {"download_url": "SECRET"}})
                row = pa.get_action(token)
                self.assertEqual(row["movie"]["tmdb_id"], 1)
                self.assertEqual(row["release"]["download_url"], "SECRET")
                self.assertTrue(pa.delete_action(token))
                self.assertIsNone(pa.get_action(token))

    def test_store_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            with patch.object(pa, "STORE_PATH", path):
                pa.create_action({"movie": {"tmdb_id": 1}})
                mode = os.stat(path).st_mode & 0o777
                self.assertEqual(mode, 0o600)

    def test_existing_temporary_file_is_private_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            temporary = Path(tmp) / "actions.json.tmp"
            temporary.touch(mode=0o644)
            with patch.object(pa, "STORE_PATH", path), patch.object(pa.json, "dump") as dump:
                def check_mode(*args, **kwargs):
                    self.assertEqual(temporary.stat().st_mode & 0o777, 0o600)
                dump.side_effect = check_mode
                pa.create_action({"movie": {"tmdb_id": 1}})

    def test_expired_action_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            with patch.object(pa, "STORE_PATH", path), patch.object(pa.time, "time", return_value=1000):
                token = pa.create_action({"movie": {"tmdb_id": 1}}, ttl_seconds=60)
            with patch.object(pa, "STORE_PATH", path), patch.object(pa.time, "time", return_value=1061):
                self.assertIsNone(pa.get_action(token))


if __name__ == "__main__":
    unittest.main()
