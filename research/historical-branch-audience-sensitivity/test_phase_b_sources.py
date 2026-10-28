import json
import tempfile
import unittest
from pathlib import Path

import phase_b_sources as pb


class PhaseBSourceTests(unittest.TestCase):
    def test_cached_index_reuses_source_and_resolved_titles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phase-b.json"
            path.write_text(json.dumps({"films": [{
                "title": "La vita è bella",
                "year": 2000,
                "imdb_id": "tt1",
                "resolved_title": "Life Is Beautiful",
                "resolved_year": 1999,
            }]}), encoding="utf-8")
            idx = pb.cached_index(path)
        self.assertEqual(pb.exact_lookup("La vita e bella", 2000, idx)[0], "tt1")
        self.assertEqual(pb.exact_lookup("Life Is Beautiful", 2000, idx)[0], "tt1")

    def test_cached_index_rejects_wrong_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phase-b.json"
            path.write_text(json.dumps({"films": [{
                "title": "Crash",
                "year": 2004,
                "imdb_id": "tt1",
                "resolved_title": "Crash",
                "resolved_year": 2004,
            }]}), encoding="utf-8")
            idx = pb.cached_index(path)
        self.assertIsNone(pb.exact_lookup("Crash", 1996, idx))

    def test_ambiguous_cached_identity_is_not_guessed(self):
        idx = {pb.norm("Same Title"): [
            ("tt1", "Same Title", 2005),
            ("tt2", "Same Title", 2005),
        ]}
        self.assertIsNone(pb.exact_lookup("Same Title", 2005, idx))


if __name__ == "__main__":
    unittest.main()
