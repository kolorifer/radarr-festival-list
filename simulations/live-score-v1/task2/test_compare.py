"""Offline Task 2 invariants: provenance, comparable ranks and signed effects."""
import copy
import hashlib
import json
import subprocess
import unittest
from unittest.mock import patch

import compare as c


class Task2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = c.calculate()
        cls.films = {f["imdb_id"]: f for f in cls.result["films"]}
        cls.baseline = c.read(c.BASE / "results.json")
        cls.evidence = c.read(c.ROOT / "inputs/observations.json")

    def test_packet_matches_exact_baseline_git_objects(self):
        manifest = c.verify_baseline()
        for name, digest in manifest["files"].items():
            original = subprocess.check_output(["git", "show", c.BASELINE + ":" + name], cwd=c.REPO)
            self.assertEqual(hashlib.sha256(original).hexdigest(), digest, name)
        self.assertEqual(set(self.films), {f["imdb_id"] for f in self.baseline["films"]})
        for old in self.baseline["films"]:
            film = self.films[old["imdb_id"]]
            for k in ("title", "tmdb_id", "year", "stratum", "ratings"):
                self.assertEqual(film[k], old[k])
            self.assertEqual(film["identity"]["tmdb_release_events"], old["tmdb_release_events"])

    def test_hash_drift_refused(self):
        real_read = c.read
        manifest = copy.deepcopy(real_read(c.ROOT / "inputs/baseline-manifest.json"))
        manifest["files"]["simulations/live-score-v1/report.md"] = "0" * 64
        with patch.object(c, "read", side_effect=lambda path: manifest if path.name == "baseline-manifest.json" else real_read(path)):
            with self.assertRaisesRegex(ValueError, "Task 1 packet changed"):
                c.calculate()

    def test_fixed_scales_strengths_and_neutral_priors(self):
        p = self.result["policy"]
        self.assertEqual(p["family_caps"], {"european_recognition": 20, "independent_cinema": 10,
                                            "us_institutional": 10, "critics_groups_consensus": 10})
        self.assertEqual(p["prior_means"], {"imdb": 7.25, "letterboxd": 3.65})
        for source, raw, adjusted, points in (("imdb", 8.5, 7.875, 18.75),
                                               ("letterboxd", 4.3, 3.975, 18.75)):
            actual = c.policy.audience_component({"rating": raw, "votes": 1000, "status": "synthetic"}, source, 1000)
            self.assertAlmostEqual(actual["adjusted_rating"], adjusted)
            self.assertAlmostEqual(actual["points"], points)

    def test_actual_east_of_wall_adjustment_raises_below_prior(self):
        film = self.films["tt21349688"]
        for source in c.policy.SCALES:
            pair = film["ratings"][source]
            for scenario, m in c.policy.SCENARIOS.items():
                expected = (pair["votes"] * pair["rating"] + m * self.result["policy"]["prior_means"][source]) / (pair["votes"] + m)
                actual = film["variants"][scenario + "/base"]["audience_components"][source]
                self.assertAlmostEqual(actual["adjusted_rating"], expected, places=6)
                self.assertGreaterEqual(actual["adjustment_points"], 0)
        self.assertAlmostEqual(film["variants"]["stronger/base"]["signed_smoothing_delta"], 15.419400, places=6)

    def test_missing_half_never_receives_prior_or_rank(self):
        for iid in ("tt29271639", "tt38991615"):
            film = self.films[iid]
            self.assertIsNone(film["audience_comparison_group"])
            for v in film["variants"].values():
                self.assertIsNone(v["audience_points"])
                self.assertIsNone(v["audience_components"]["letterboxd"]["points"])
                self.assertIsNone(v["audience_only_rank"])
                self.assertEqual(v["missing_audience_capacity"], 25)
                self.assertEqual(v["observed_audience_subtotal"], v["audience_components"]["imdb"]["points"])

    def test_heterogeneous_or_partial_pairs_cannot_enter_comparison(self):
        ratings = copy.deepcopy(self.films["tt14905854"]["ratings"])
        self.assertIsNotNone(c.audience_group(ratings))
        for field, value in (("status", "fresh"), ("votes", None), ("available_by", "2026-10-26"),
                             ("source_url", "https://example.invalid/other-batch")):
            modified = copy.deepcopy(ratings)
            modified["letterboxd"][field] = value
            self.assertIsNone(c.audience_group(modified))
        self.assertIsNone(c.audience_group({"imdb": ratings["imdb"]}))

    def test_real_ties_and_stable_results_are_not_overall_ranks(self):
        for iid, first, later in (("tt33764258", 1, 2), ("tt29768334", 9, 10), ("tt14905854", 5, 5)):
            film = self.films[iid]
            self.assertEqual(film["variants"]["unsmoothed/base"]["audience_only_rank"], first)
            for s in ("modest", "stronger"):
                v = film["variants"][s + "/base"]
                self.assertEqual(v["audience_only_rank"], later)
                self.assertEqual(v["audience_rank_change_vs_unsmoothed"], first - later)
                self.assertIsNone(v["overall_rank"])
        self.assertEqual(c.competition_ranks({"a": 5, "b": 5, "c": 3}), {"a": 1, "b": 1, "c": 3})

    def test_evidence_change_separate_from_smoothing_all_288_variants(self):
        for old in self.baseline["films"]:
            film = self.films[old["imdb_id"]]
            self.assertEqual(len(film["variants"]), 12)
            for key, v in film["variants"].items():
                self.assertEqual(v["evidence_delta_vs_task1_same_variant"], 0)
                self.assertEqual(v["recognition_evidence_delta_vs_task1"], 0)
                self.assertEqual(v["audience_evidence_delta_vs_task1"], 0)
                self.assertEqual(v["conditional_observed_subtotal"], old["variants"][key]["provisional_observed_subtotal"])
                if film["audience_comparison_group"]:
                    self.assertEqual(v["audience_rank_change_vs_task1"], 0)

    def test_corroboration_never_stacks_nomination_under_winner(self):
        film = self.films["tt30144839"]
        gotham = film["award_breakdown"]["components"]["gotham_best_feature"]
        self.assertEqual(gotham["normalized_points"], 35)
        self.assertTrue(any(r["status"] == "nominee" for r in gotham["evidence"]))
        self.assertEqual(film["variants"]["unsmoothed/base"]["recognition_observed_points"]["critics_groups_consensus"], 10)
        self.assertEqual(self.result["diagnostics"]["components_upgraded_to_direct_primary_review"], 11)
        self.assertFalse("lafca_best_film" in self.films["tt28607951"]["components_upgraded_to_direct_primary_review"])

    def test_attribution_and_source_mismatch_rejected(self):
        for field, value in (("tmdb_id", 1), ("unique_film_attribution", False),
                             ("source_url", "https://example.invalid/"), ("event_year", None)):
            evidence = copy.deepcopy(self.evidence)
            evidence["awards"][0][field] = value
            with self.assertRaises(ValueError):
                c.validate_evidence(evidence, self.baseline)

    def test_scoped_absence_cannot_conflict_with_positive_same_edition(self):
        evidence = copy.deepcopy(self.evidence)
        check = next(c for c in evidence["coverage_checks"] if c["source_id"] == "gotham24"
                     and c["imdb_ids"] == ["tt28607951"])
        check["status"] = "verified_no_award"
        with self.assertRaisesRegex(ValueError, "contradicts"):
            c.validate_evidence(evidence, self.baseline)

    def test_coverage_not_promoted_and_freshness_never_relabelled(self):
        counts = self.result["diagnostics"]
        self.assertEqual(counts["fresh_rating_pairs"], {"imdb": 0, "letterboxd": 0})
        self.assertEqual(counts["audience_comparison_film_count"], 22)
        self.assertEqual(counts["task2_coverage_check_statuses"], {"verified_positive": 19, "verified_no_award": 52,
                                                                "not_yet_announced": 8, "unavailable": 2})
        for f in self.films.values():
            for metadata in f["rating_metadata"].values():
                self.assertFalse(metadata["task2_fresh_observation"])
                self.assertIsNone(metadata["retrieved_at"])
            for v in f["variants"].values():
                self.assertIsNone(v["overall_score"])
                self.assertIsNone(v["overall_rank"])
                for family, value in v["recognition_family_scores"].items():
                    self.assertTrue(value is None or value == c.policy.FAMILIES[family])

    def test_extensions_off_in_base_and_caps_preserved(self):
        film = self.films["tt14905854"]
        for scenario in c.policy.SCENARIOS:
            base = film["variants"][scenario + "/base"]
            tiff = film["variants"][scenario + "/tiff"]
            self.assertEqual(base["enabled_extensions"], [])
            self.assertEqual(base["recognition_subtotal"], 15.8)
            self.assertEqual(tiff["recognition_subtotal"], 19.8)
        capped = c.policy.recognition([{"component": "efa_best_film", "status": "winner"},
                                      {"component": "bafta_best_film", "status": "winner"}], ["screenplay"])
        self.assertEqual(capped["observed_points"]["european_recognition"], 20)
        for f in self.films.values():
            for v in f["variants"].values():
                self.assertLessEqual(v["conditional_observed_subtotal"], 100)

    def test_byte_reproduction(self):
        self.assertEqual(c.read(c.ROOT / "results.json"), self.result)
        self.assertEqual((c.ROOT / "comparison.csv").read_bytes(), c.render_csv(self.result).encode())
        self.assertEqual((c.ROOT / "breakdowns.md").read_bytes(), c.render_comparison(self.result).encode())


if __name__ == "__main__":
    unittest.main()
