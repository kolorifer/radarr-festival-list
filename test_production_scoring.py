"""Frozen PR #5 parity and production-only D016 admission regressions."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import production_scoring as model
import movie_intel
import movie_intel_service as service

ROOT = Path(__file__).resolve().parent


class D016Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = model.read_json(ROOT / "production/evidence-inputs.json")
        cls.baseline = model.load_grandfathered()
        cls.catalog = model.build_catalog(cls.inputs, cls.baseline)
        cls.rows = model.unique_rows(cls.catalog["films"])

    def title(self, name):
        hits = [r for r in self.rows.values() if r["title"] == name]
        self.assertEqual(len(hits), 1, name)
        return hits[0]

    def test_frozen_1909_scores_and_family_points_exact(self):
        model.validate_frozen(self.catalog)
        expected = model.read_json(ROOT / "tests/fixtures/d016-frozen-scores.json")["films"]
        self.assertEqual(set(expected), set(self.rows))
        for iid, fields in expected.items():
            with self.subTest(imdb_id=iid):
                self.assertEqual({k:self.rows[iid][k] for k in fields}, fields)

    def test_387_equals_224_retained_and_163_new(self):
        self.assertEqual(len(self.rows), 1909)
        self.assertEqual(sum(r["qualified"] for r in self.rows.values()), 387)
        self.assertEqual(sum(r["qualified"] and not r["grandfathered"]
                             for r in self.rows.values()), 163)
        self.assertTrue(all(self.rows[i]["qualified"] for i in self.baseline))

    def test_exact_deployed_224_ids_and_routes(self):
        expected = model.read_json(ROOT / "production/provenance.json")
        baseline_bytes = (ROOT / "production/grandfathered-224.json").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_bytes).hexdigest(),
                         expected["grandfathered_sha256"])
        self.assertEqual(len(self.baseline), 224)
        self.assertEqual(set(self.baseline),
                         {r["imdb_id"] for r in self.rows.values() if r["grandfathered"]})
        for iid, row in self.baseline.items():
            self.assertEqual(self.rows[iid]["legacy_routes"]["deployed"], row["legacy_routes"])

    def test_grandfather_below_225_retained(self):
        rows = [r for r in self.rows.values() if r["grandfathered"] and r["overall_score"] < 225]
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["qualified"])
            self.assertEqual(row["routes"], ["grandfathered_production"])

    def test_score_only_newcomer(self):
        row = self.title("The Florida Project")
        self.assertFalse(row["grandfathered"])
        self.assertTrue(row["qualified"])
        self.assertEqual(row["routes"], ["evidence_score_225"])

    def test_both_routes_remain_auditable(self):
        row = self.title("Brokeback Mountain")
        self.assertGreaterEqual(row["overall_score"], 225)
        self.assertEqual(row["routes"], ["grandfathered_production", "evidence_score_225"])

    def test_non_grandfathered_below_threshold_rejected(self):
        rows = [r for r in self.rows.values() if not r["grandfathered"] and r["overall_score"] < 225]
        self.assertTrue(rows)
        self.assertTrue(all(not r["qualified"] and not r["routes"] for r in rows))

    def test_research255_is_not_grandfathered(self):
        research = {i for i,r in self.rows.items() if r["legacy_routes"]["research"]}
        extras = research - self.baseline.keys()
        self.assertEqual(len(research), 255)
        self.assertEqual(len(extras), 31)
        self.assertEqual(sum(self.rows[i]["qualified"] for i in extras), 11)
        self.assertEqual(sum(not self.rows[i]["qualified"] for i in extras), 20)

    def test_retired_legacy_route_cannot_admit_across_spider_verse(self):
        row = self.title("Spider-Man: Across the Spider-Verse")
        self.assertIn("convergence", row["legacy_routes"]["research"])
        self.assertFalse(row["grandfathered"])
        self.assertLess(row["overall_score"], 225)
        self.assertFalse(row["qualified"])
        self.assertEqual(row["routes"], [])

    def test_three_research_middle_entries_qualify_naturally(self):
        for title in ("Sound of Metal", "Coco", "The Salesman"):
            with self.subTest(title=title):
                row = self.title(title)
                self.assertFalse(row["grandfathered"])
                self.assertGreaterEqual(row["overall_score"], 225)
                self.assertLess(row["overall_score"], 250)
                self.assertEqual(row["routes"], ["evidence_score_225"])

    def test_no_special_250_route(self):
        row = self.title("Dune: Part Two")
        self.assertFalse(row["grandfathered"])
        self.assertGreaterEqual(row["overall_score"], 250)
        self.assertEqual(row["routes"], ["evidence_score_225"])

    def test_inclusive_threshold_and_no_extra_guards(self):
        self.assertEqual(model.qualification("tt999", 224.99, {}), (False, []))
        self.assertEqual(model.qualification("tt999", 225, {}), (True, ["evidence_score_225"]))
        self.assertEqual(model.qualification("tt999", 250, {}), (True, ["evidence_score_225"]))
        self.assertEqual(model.qualification("tt999", 0, {"tt999":{}}),
                         (True, ["grandfathered_production"]))

    def test_invalid_score_rejected(self):
        for score in (float("nan"), float("inf"), -1, True, "225", None):
            with self.subTest(score=score), self.assertRaises(ValueError):
                model.qualification("tt1", score, {})

    def test_duplicates_rejected(self):
        row = self.catalog["films"][0]
        with self.assertRaises(ValueError):
            model.unique_rows([row, row])

    def test_missing_grandfather_fails_generation(self):
        inputs = copy.deepcopy(self.inputs)
        iid = next(iter(self.baseline))
        inputs["films"] = [f for f in inputs["films"] if f["imdb_id"] != iid]
        with self.assertRaises(ValueError):
            model.build_catalog(inputs, self.baseline)

    def test_byte_for_byte_artifact(self):
        expected = (ROOT / "production/movie-catalog.json").read_bytes()
        self.assertEqual(model.encode(self.catalog), expected)
        self.assertEqual(model.encode(model.build_catalog(self.inputs, self.baseline)), expected)

    def test_runtime_has_no_legacy_input_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "production").mkdir()
            for name in ("movie-catalog.json", "grandfathered-224.json"):
                (root / "production" / name).write_bytes((ROOT / "production" / name).read_bytes())
            # No simulation qualifiers, audience cache, or research source modules.
            with patch.object(movie_intel, "ROOT", root):
                index = movie_intel.build_index()
            self.assertEqual(len(index), 1909)
            self.assertEqual(sum(r["qualified"] for r in index.values()), 387)

    def test_runtime_missing_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(movie_intel, "ROOT", Path(temp)):
            with self.assertRaises(FileNotFoundError):
                movie_intel.build_index()

    def test_runtime_rejects_tampered_legacy_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "production").mkdir()
            (root / "production/grandfathered-224.json").write_bytes(
                (ROOT / "production/grandfathered-224.json").read_bytes())
            catalog = copy.deepcopy(self.catalog)
            row = next(r for r in catalog["films"] if not r["qualified"])
            row["qualified"] = True
            row["routes"] = ["convergence"]
            (root / "production/movie-catalog.json").write_bytes(model.encode(catalog))
            with self.assertRaises(ValueError):
                model.load_catalog(root)

    def test_five_cleaned_tspdt_identities(self):
        status = model.read_json(ROOT / "production/data-status.json")
        self.assertEqual(len(status["identity_corrections"]), 5)
        for correction in status["identity_corrections"]:
            row = self.rows[correction["imdb_id"]]
            self.assertIsNotNone(row["tspdt_rank"])
            wrong = self.rows.get(correction["old_imdb_id"])
            self.assertTrue(wrong is None or wrong["tspdt_rank"] != row["tspdt_rank"])
        row = movie_intel.find_local("La Morte rouge", 2006, self.rows)
        self.assertEqual(row["imdb_id"], "tt0806125")
        self.assertEqual(row["tspdt_rank"], 509)
        self.assertNotIn("tt4698742", self.rows)
        self.assertIsNone(movie_intel.find_local("La Porte Rouge", 2007, self.rows))

    def test_watch_annotation_does_not_score(self):
        for iid in ("tt0240419", "tt1588895", "tt0363589"):
            self.assertEqual(self.rows[iid]["watch_state"], "unknown")
            original = next(f for f in self.inputs["films"] if f["imdb_id"] == iid)
            changed = {**original, "watch_state": "watched"}
            self.assertEqual(model.score_film(original, self.inputs["ranked_sources"]),
                             model.score_film(changed, self.inputs["ranked_sources"]))
        import backcatalog
        self.assertNotIn(("La Ciénaga", 2001), backcatalog.WATCHED)
        self.assertNotIn(("Uncle Boonmee Who Can Recall His Past Lives", 2010), backcatalog.WATCHED)
        self.assertNotIn(("Elephant", 2003), backcatalog.WATCHED)

    def test_nine_letterboxd_gaps_explicit(self):
        status = model.read_json(ROOT / "production/data-status.json")
        missing = {r["imdb_id"] for r in status["letterboxd_missing"]}
        self.assertEqual(len(missing), 9)
        self.assertEqual(missing, {i for i,r in self.rows.items() if not r["audience_complete"]})
        self.assertTrue(all(self.rows[i]["letterboxd"] == {} for i in missing))

    def test_award_gaps_and_anthology_rule_preserved(self):
        status = model.read_json(ROOT / "production/data-status.json")
        self.assertEqual(status["award_gap_counts"],
                         {"efa_best_film":8,"gotham_best_feature":1,"nsfc_best_picture":0,
                          "nyfcc_best_film":0,"lafca_best_film":1,"critics_choice_best_picture":22})
        self.assertEqual(len(status["unresolved_awards"]), 32)
        self.assertIn("Small Axe", json.dumps(status["unresolved_awards"]))
        self.assertIn("Nymphomaniac", json.dumps(status["unresolved_awards"]))

    def test_audience_150_and_trakt_tmdb_ignored(self):
        original = copy.deepcopy(self.inputs["films"][0])
        original["ratings"].update(imdb={"rating":10,"votes":1000000},
                                   letterboxd={"rating":5,"votes":1000000})
        scored = model.score_film(original, self.inputs["ranked_sources"])
        self.assertEqual(scored["audience_score"], 150)
        original["ratings"].update(trakt={"rating":100,"votes":1000000},
                                   tmdb={"rating":100,"votes":1000000})
        self.assertEqual(model.score_film(original, self.inputs["ranked_sources"]), scored)
        self.assertEqual(max(r["eligible_max_score"] for r in self.rows.values()), 1000)

    def test_canon_correlation_unchanged(self):
        self.assertEqual(model.adjusted_sight_sound(100, 100), 50)
        self.assertEqual(model.adjusted_sight_sound(0, 100), 100)

    def test_notification_uses_active_routes_only(self):
        payload = {"data":{"release":{"title":"Sound of Metal","year":2019},
                           "result":{"rejections":["Unknown Movie"]}}}
        text = service.format_message(payload, self.title("Sound of Metal"))
        self.assertIn("Our model: QUALIFIES", text)
        self.assertIn("evidence_score_225", text)
        self.assertNotIn("convergence", text)
        row = self.title("Spider-Man: Across the Spider-Verse")
        text = service.format_message(payload, row)
        self.assertIn("does not currently qualify", text)
        self.assertNotIn("convergence", text)

    def test_verified_imdb_metadata_joins_production_catalog(self):
        payload = {"data":{"release":{"title":"A verified alternative title","year":2020},
                           "result":{"rejections":["Unknown Movie"]}}}
        with patch.object(service, "INDEX", self.rows), patch.object(service, "resolve_movie",
                return_value={"imdb_id":"tt5363618","title":"Sound of Metal","year":2020}):
            context = service.build_movie_context(payload)
        self.assertEqual(context["movie"]["imdb_id"], "tt5363618")
        self.assertIn("evidence_score_225", context["text"])

    def test_unverified_title_cannot_borrow_another_identity(self):
        payload = {"data":{"release":{"title":"La Porte Rouge","year":2007},
                           "result":{"rejections":["Unknown Movie"]}}}
        with patch.object(service, "INDEX", self.rows), patch.object(service, "resolve_movie",
                return_value={"imdb_id":"tt4698742","title":"La Porte Rouge","year":2007}):
            context = service.build_movie_context(payload)
        self.assertIsNone(context["movie"])
        self.assertNotIn("QUALIFIES", context["text"])


if __name__ == "__main__":
    unittest.main()
