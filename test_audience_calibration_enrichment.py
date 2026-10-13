import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import audience_calibration_enrichment as ace


class EnrichmentTests(unittest.TestCase):
    def inputs(self):
        return {
            "backcatalog-details.json": {"candidates": [
                {"imdb_id": "tt1", "title": "Film", "year": 2001}]},
            "sources/phase-b-institutional.json": {"films": []},
            "simulation-qualifiers.json": [
                {"imdb_id": "tt2", "title": "Qualifier only", "year": 2002}],
            "audience-ratings.json": {"ratings": {}, "unavailable": {}},
            "sources/evidence-families.json": {"films": {}, "ranked_sources": {}},
            "sources/imdb-audience-discovery.json": {"films": []},
        }

    def test_same_union_includes_qualifier_only_ids(self):
        self.assertEqual({m["imdb_id"] for m in ace.universe(self.inputs())},
                         {"tt1", "tt2"})

    def test_provider_presence_is_not_positive_score(self):
        self.assertTrue(ace.valid_provider({"rating": 6, "votes": 10}, "imdb"))
        for item in ({}, {"rating": 8}, {"rating": 11, "votes": 10},
                     {"rating": True, "votes": 100}, {"rating": float("nan"), "votes": 20},
                     {"rating": 8, "votes": -1}):
            self.assertFalse(ace.valid_provider(item, "imdb"))

    def test_response_drops_arbitrary_text_and_urls(self):
        safe = ace.safe_ratings({"imdb": {"rating": 8, "votes": 2000,
                     "url": "https://example.invalid/private", "apikey": "secret"},
                     "arbitrary": {"token": "secret"}})
        self.assertEqual(safe, {"imdb": {"rating": 8, "votes": 2000}})

    def test_imdb_dataset_matches_ids_and_skips_bad_values(self):
        stream = io.StringIO("tconst\taverageRating\tnumVotes\n"
                  "tt1\t8.0\t2000\ntt2\t\\N\t100\ntt3\t9.0\t900\n")
        self.assertEqual(ace.imdb_rows(stream, {"tt1", "tt2"}),
                         {"tt1": {"rating": 8.0, "votes": 2000}})

    def test_missing_key_spends_no_requests(self):
        with tempfile.TemporaryDirectory() as d, patch.object(
                ace, "load_inputs", return_value=self.inputs()):
            report = ace.collect_reeldb(Path(d), "", fetch=lambda *a: self.fail())
            self.assertEqual(report["network_requests"], 0)
            self.assertEqual(report["status"], "missing_REELDB_API_KEY")

    def test_rate_limit_stops_without_secret_in_report(self):
        def fetch(*args):
            raise HTTPError("https://example.invalid/?apikey=private",
                            429, "private", {}, None)
        with tempfile.TemporaryDirectory() as d, patch.object(
                ace, "load_inputs", return_value=self.inputs()):
            report = ace.collect_reeldb(Path(d), "private", fetch=fetch,
                                       sleep=lambda _: None)
            self.assertEqual(report["network_requests"], 1)
            self.assertEqual(report["status"], "stopped_HTTP_429")
            self.assertNotIn("private", json.dumps(report))

    def test_partial_response_preserves_cached_provider_and_request_budget(self):
        inputs = self.inputs()
        inputs["audience-ratings.json"]["ratings"]["tt1"] = {
            "reeldb": {"imdb": {"rating": 8.5, "votes": 200000}}}
        def fetch(*args):
            return {"imdb": {"rating": None, "votes": None},
                    "letterboxd": {"rating": 4, "votes": 100000}}
        with tempfile.TemporaryDirectory() as d, patch.object(
                ace, "load_inputs", return_value=inputs):
            report = ace.collect_reeldb(Path(d), "private", max_requests=1,
                                       fetch=fetch, sleep=lambda _: None)
            cached = json.loads((Path(d) / ace.es.AUDIENCE).read_text())
            self.assertEqual(cached["ratings"]["tt1"]["reeldb"]["imdb"]["rating"], 8.5)
            self.assertEqual(report["network_requests"], 1)
            self.assertEqual(report["status"], "request_budget_exhausted")


if __name__ == "__main__":
    unittest.main()
