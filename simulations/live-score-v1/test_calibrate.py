"""Meaningful offline arithmetic, attribution, missingness and provenance checks."""
import copy
import hashlib
import json
import subprocess
import unittest
from unittest.mock import patch

import calibrate as c


def award(component, status="winner"):
    return {"component": component, "status": status, "category": "synthetic arithmetic fixture"}


class ArithmeticTests(unittest.TestCase):
    def test_new_audience_boundaries_and_clamps(self):
        for source, low, high in (("imdb", 6, 8.5), ("letterboxd", 3, 4.3)):
            self.assertEqual(c.quality(low - 1, source), 0)
            self.assertEqual(c.quality(low, source), 0)
            self.assertAlmostEqual(c.quality((low + high) / 2, source), 12.5)
            self.assertEqual(c.quality(high, source), 25)
            self.assertEqual(c.quality(high + 0.5, source), 25)

    def test_hand_calculated_bayesian_count_weight(self):
        result = c.audience_component({"rating": 8.5, "votes": 1000, "status": "synthetic"}, "imdb", 1000)
        self.assertEqual(result["adjusted_rating"], 7.875)
        self.assertEqual(result["points"], 18.75)
        self.assertEqual(result["adjustment_points"], -6.25)
        self.assertEqual(result["data_weight"], 0.5)

    def test_low_rating_can_increase_not_only_discount(self):
        result = c.audience_component({"rating": 6, "votes": 1000, "status": "synthetic"}, "imdb", 1000)
        self.assertEqual(result["points"], 6.25)

    def test_missing_rating_or_count_is_unknown_not_neutral(self):
        for pair in ({}, {"rating": 8}, {"votes": 123}):
            for strength in c.SCENARIOS.values():
                result = c.audience_component(dict(pair, status="unavailable"), "imdb", strength)
                self.assertIsNone(result["points"])

    def test_invalid_pairs_fail_closed(self):
        for rating, votes in ((8, 0), (8, -1), (8, 4.5), (8, True), (float("nan"), 100), (11, 100)):
            with self.assertRaises(ValueError):
                c.audience_component({"rating": rating, "votes": votes}, "imdb", 1000)

    def test_winner_replaces_nomination_and_duplicate_evidence(self):
        records = [award("academy_best_picture", "nominee"), award("academy_best_picture"),
                   award("academy_best_picture"), award("globe_best_picture")]
        r = c.recognition(records)
        self.assertEqual(r["normalized_uncapped"]["us_institutional"], 125)
        self.assertEqual(r["observed_points"]["us_institutional"], 10)
        self.assertEqual(len(r["components"]["academy_best_picture"]["evidence"]), 3)

    def test_competition_is_distinct_and_historical_additivity_retained(self):
        r = c.recognition([award("cannes_main", "competition"), award("cannes_grand_prix")])
        self.assertEqual(r["observed_points"]["european_recognition"], 13)

    def test_sundance_existing_convergence_and_family_caps(self):
        r = c.recognition([award("sundance_grand_jury"), award("sundance_audience")])
        self.assertEqual(r["normalized_uncapped"]["independent_cinema"], 100)
        self.assertEqual(r["observed_points"]["independent_cinema"], 10)

    def test_candidate_bonus_units_and_caps(self):
        r = c.recognition([award("efa_best_film"), award("bafta_best_film")], ["screenplay"])
        self.assertEqual(r["observed_points"]["european_recognition"], 20)
        r = c.recognition([award("spirit_best_feature"), award("gotham_best_feature")], ["tiff"])
        self.assertEqual(r["observed_points"]["independent_cinema"], 10)
        r = c.recognition([], ["tiff", "screenplay"])
        self.assertEqual(sum(r["observed_points"].values()), 10)

    def test_maximum_remains_100(self):
        r = c.recognition([award(k) for k in c.POLICY], ["tiff", "screenplay"])
        self.assertEqual(sum(r["observed_points"].values()) + 25 + 25, 100)

    def test_unsupported_awards_cannot_silently_score(self):
        with self.assertRaises(ValueError):
            c.recognition([award("imdb_editors_list")])
        with self.assertRaises(ValueError):
            c.recognition([award("cannes_main", "shortlisted")])


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = c.calculate()
        cls.films = {f["imdb_id"]: f for f in cls.result["films"]}

    def test_cohort_id_uniqueness_and_required_films(self):
        films = list(self.films.values())
        self.assertEqual(len(films), 24)
        self.assertEqual(len({f["tmdb_id"] for f in films}), 24)
        self.assertEqual(self.result["diagnostics"]["years"], {"2024": 10, "2025": 10, "2026": 4})
        self.assertTrue({"tt14905854", "tt28607951", "tt8999762", "tt17526714",
                         "tt27714581", "tt36491653"} <= self.films.keys())
        for f in films:
            if f["imdb_id"] == "tt32928666":
                self.assertEqual(f["year"], 2024)  # Premiere, not later US release.
                self.assertIn("2025", f["tmdb_page_title"])
                self.assertTrue(any("2024 premiere" in n for n in f["notes"]))
            else:
                self.assertIn(str(f["year"]), f["tmdb_page_title"])
            self.assertEqual(f["wikidata_label"], f["title"])

    def test_pinned_historical_awards_and_rating_slices_match_git_revision(self):
        # No network: verify exact facts against local pinned Git objects.
        repo = c.ROOT.parents[1]
        rev = "9c5a0f06e1c39e48653338fd0865ddabdc525a61"
        for filename, original in (("historical-awards.json", "sources/evidence-families.json"),
                                   ("historical-ratings.json", "audience-ratings.json")):
            data = c.load(filename)
            raw = subprocess.check_output(["git", "show", rev + ":" + original], cwd=repo)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), data["provenance"]["sha256"])
            source = json.loads(raw)
            for iid, film in data["films"].items():
                if "awards" in filename:
                    self.assertEqual(film, source["films"][iid])
                else:
                    for provider in c.SCALES:
                        self.assertEqual(film[provider], source["ratings"][iid]["reeldb"].get(provider))

    def test_all_archival_family_values_reconstruct_exactly(self):
        data = c.load("historical-awards.json")
        for iid, film in data["films"].items():
            actual = c.recognition(c.historical_records(film, data["provenance"]["url"]))
            expected = {f: film.get("family_scores", {}).get(f, 0) for f in c.FAMILIES}
            self.assertEqual(actual["normalized_capped"], expected, iid)

    def test_hamnet_audit_and_independent_extension(self):
        f = self.films["tt14905854"]
        b = f["variants"]["unsmoothed/base"]
        self.assertAlmostEqual(b["audience_points"], 18 + 25 * 1.2 / 1.3, places=5)
        self.assertEqual(b["recognition_subtotal"], 15.8)
        self.assertAlmostEqual(f["variants"]["unsmoothed/tiff"]["provisional_observed_subtotal"] -
                               b["provisional_observed_subtotal"], 4)
        self.assertEqual(f["variants"]["unsmoothed/screenplay"], b)
        self.assertTrue(any("score=1" in note for note in f["notes"]))

    def test_missing_letterboxd_half_is_not_reweighted(self):
        f = self.films["tt38991615"]
        v = f["variants"]["unsmoothed/base"]
        self.assertIsNone(v["audience_points"])
        self.assertEqual(v["observed_audience_subtotal"], 9)
        self.assertEqual(v["missing_audience_capacity"], 25)
        self.assertNotIn(f["imdb_id"], self.result["diagnostics"]["archive_paired_audience_comparison"]["ranks"]["unsmoothed"])

    def test_verified_new_fact_gaps_are_not_invented_weights(self):
        f = self.films["tt27714581"]
        self.assertEqual(sum(f["historical_recognition_projection"].values()), 8.8)
        self.assertEqual(f["variants"]["unsmoothed/base"]["recognition_subtotal"], 30.8)
        self.assertEqual(self.films["tt20221436"]["variants"]["unsmoothed/base"]["recognition_subtotal"], 30.8)

    def test_provenance_and_missingness_are_explicit(self):
        observations = c.load("observations.json")
        for fact in observations["awards"] + observations["extensions"]:
            self.assertTrue(fact["source_url"].startswith("https://"))
            self.assertEqual(fact["observed_at"], "2026-10-25")
        self.assertTrue({"verified_no_award", "not_yet_announced"} <=
                        {r["status"] for r in observations["coverage_checks"]})
        for f in self.films.values():
            self.assertEqual(len(f["variants"]), 12)
            self.assertNotIn("overall_rank", f)
            for v in f["variants"].values():
                self.assertIsNone(v["overall_score"])
                self.assertLessEqual(v["provisional_observed_subtotal"], 100)
                for family, score in v["recognition_family_scores"].items():
                    self.assertTrue(score is None or score == c.FAMILIES[family])
            self.assertTrue(all(o["measurement_date"] is None for o in f["ratings"].values()))

    def test_extensions_require_attributed_verified_facts(self):
        observations = c.load("observations.json")
        modified = copy.deepcopy(observations)
        modified["extensions"] = []
        original_load = c.load
        with patch.object(c, "load", side_effect=lambda name: modified if name == "observations.json" else original_load(name)):
            for f in c.calculate()["films"]:
                self.assertEqual(f["variants"]["modest/both"], f["variants"]["modest/base"])
        modified["extensions"] = copy.deepcopy(observations["extensions"])
        modified["extensions"][0]["unique_film_attribution"] = False
        with patch.object(c, "load", side_effect=lambda name: modified if name == "observations.json" else original_load(name)):
            with self.assertRaisesRegex(ValueError, "unique film attribution"):
                c.calculate()

    def test_committed_outputs_are_reproducible(self):
        self.assertEqual((c.ROOT / "comparison.csv").read_bytes(), c.render_csv(self.result).encode())
        self.assertEqual((c.ROOT / "breakdowns.md").read_bytes(), c.render_markdown(self.result).encode())
        self.assertEqual(json.loads((c.ROOT / "results.json").read_text()), self.result)


if __name__ == "__main__":
    unittest.main()
