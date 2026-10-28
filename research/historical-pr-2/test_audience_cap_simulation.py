import copy
import unittest

import audience_cap_simulation as sim
import audience_calibration_enrichment as ace


class AudienceCapTests(unittest.TestCase):
    def inputs(self):
        return {
            "backcatalog-details.json": {"candidates": [
                {"imdb_id": "tt1", "title": "Strong", "year": 2015, "tspdt_rank": 1},
                {"imdb_id": "tt2", "title": "Missing LB", "year": 2024},
                {"imdb_id": "tt3", "title": "Weak audience", "year": 2018}]},
            "sources/phase-b-institutional.json": {"films": []},
            "simulation-qualifiers.json": [{"imdb_id": "tt1", "routes": ["convergence"]}],
            "sources/imdb-audience-discovery.json": {"films": []},
            "audience-ratings.json": {"ratings": {
                "tt1": {"reeldb": {
                    "imdb": {"rating": 8.5, "votes": 500000},
                    "letterboxd": {"rating": 4.3, "votes": 500000},
                    "trakt": {"rating": 90, "votes": 50000},
                    "metacritic": {"rating": 95, "votes": 70},
                    "tomatoes": {"rating": 99, "votes": 300}}},
                "tt3": {"reeldb": {
                    "imdb": {"rating": 6, "votes": 200000},
                    "letterboxd": {"rating": 2.5, "votes": 200000}}}}},
            "sources/evidence-families.json": {
                "ranked_sources": {
                    "sight_sound": {"published_depth": 250, "eligible_through_year": 2022,
                                    "films": [{"imdb_id": "tt1", "rank": 1}]},
                    "bbc_21c": {"published_depth": 100, "eligible_through_year": 2016, "films": []},
                    "nyt_21c": {"published_depth": 100, "eligible_through_year": 2025, "films": []}},
                "films": {"tt1": {"family_scores": {
                    "us_institutional": 100, "european_recognition": 100,
                    "independent_cinema": 100, "critics_groups_consensus": 70}}}},
        }

    def shared(self):
        return sim.prepare_shared(self.inputs(), {"ratings": {
            "tt2": {"rating": 8.5, "votes": 500000}}})

    def test_only_audience_weight_changes(self):
        shared = self.shared()
        a = {r["imdb_id"]: r for r in sim.score_variant(shared, 150)}
        b = {r["imdb_id"]: r for r in sim.score_variant(shared, 200)}
        self.assertEqual(set(a), set(b))
        for iid in a:
            self.assertEqual(a[iid]["non_audience_points"], b[iid]["non_audience_points"])
            self.assertEqual(a[iid]["qualified"], b[iid]["qualified"])
            self.assertEqual(a[iid]["routes"], b[iid]["routes"])
        self.assertEqual(a["tt1"]["audience_score"], 150)
        self.assertEqual(b["tt1"]["audience_score"], 200)
        self.assertEqual(b["tt1"]["overall_score"] - a["tt1"]["overall_score"], 50)
        self.assertNotIn("trakt_audience", b["tt1"]["source_points"])

    def test_canon_and_european_weight_are_preserved_in_both(self):
        row = next(r for r in self.shared() if r["imdb_id"] == "tt1")
        self.assertEqual(row["non_audience_points"]["tspdt_21c"], 100)
        self.assertEqual(row["non_audience_points"]["sight_sound"], 50)
        self.assertEqual(row["canon_correlation"]["joint_canon_points"], 150)
        self.assertEqual(row["non_audience_points"]["european_recognition"], 200)
        self.assertLessEqual(row["non_audience_points"]["critics_groups_consensus"], 100)
        self.assertGreater(row["non_audience_points"]["critics_groups_consensus"], 70)
        self.assertEqual(row["non_audience_eligible_max"], 850)

    def test_missing_source_is_not_renormalized_or_called_weak(self):
        rows = {r["imdb_id"]: r for r in sim.score_variant(self.shared(), 150)}
        missing, weak = rows["tt2"], rows["tt3"]
        self.assertEqual(missing["audience_score"], 75)
        self.assertFalse(missing["audience_complete"])
        self.assertEqual(missing["audience_coverage"]["imdb"]["origin"],
                         "IMDb official title.ratings")
        self.assertTrue(weak["audience_complete"])
        self.assertEqual(weak["audience_score"], 0)
        self.assertFalse(missing["qualified"])

    def test_prepare_and_scoring_do_not_mutate_inputs(self):
        inputs = self.inputs()
        before = copy.deepcopy(inputs)
        shared = sim.prepare_shared(inputs, {})
        saved = copy.deepcopy(shared)
        sim.score_variant(shared, 150)
        sim.score_variant(shared, 200)
        self.assertEqual(before, inputs)
        self.assertEqual(saved, shared)

    def test_deterministic_ties_report_ordinal_and_competition_ranks(self):
        shared = self.shared()
        one = copy.deepcopy(shared[0])
        two = copy.deepcopy(one)
        one.update(imdb_id="tt9", title="Same")
        two.update(imdb_id="tt4", title="Same")
        forward = sim.score_variant([one, two], 150)
        reverse = sim.score_variant([two, one], 150)
        self.assertEqual(forward, reverse)
        self.assertEqual([r["imdb_id"] for r in forward], ["tt4", "tt9"])
        self.assertEqual([r["score_rank"] for r in forward], [1, 1])

    def test_empty_distribution_and_bands_cover_all_scores(self):
        self.assertEqual(sim.distribution([])["count"], 0)
        self.assertEqual(sim.band(0), "0-<100")
        self.assertEqual(sim.band(99.99), "0-<100")
        self.assertEqual(sim.band(100), "100-<150")
        self.assertEqual(sim.band(600), "600+")
        rows = sim.score_variant(self.shared(), 150)
        dist = sim.distribution(rows)
        self.assertEqual(sum(dist["bands"].values()), len(rows))

    def test_score_delta_and_crossings_do_not_requalify(self):
        shared = self.shared()
        row = copy.deepcopy(shared[0])
        row["non_audience_points"] = {k: (100 if k == "tspdt_21c" else 0)
                                     for k in sim.FAMILY_WEIGHTS}
        row["non_audience_score"] = 100
        row["qualified"] = False
        a, b = sim.score_variant([row], 150), sim.score_variant([row], 200)
        result = sim.compare({150: a, 200: b})
        self.assertEqual(result["movements"][0]["crossed_boundaries"], [300])
        self.assertFalse(a[0]["qualified"])
        self.assertFalse(b[0]["qualified"])
        self.assertEqual(result["summary"]["score_changed"], 1)

    def test_rounding_invariant_for_fractional_component_sums(self):
        base = self.shared()[0]
        for raw in (0, 1, 33.31, 49.38, 100.02, 183.73, 200):
            row = copy.deepcopy(base)
            row["audience_raw_sum"] = raw
            row["audience_raw_points"] = {"imdb": round(raw / 2, 2),
                                          "letterboxd": round(raw - round(raw / 2, 2), 2)}
            result = sim.compare({cap: sim.score_variant([row], cap) for cap in sim.CAPS})
            actual = result["movements"][0]["score_change"]
            self.assertLessEqual(abs(actual - raw / 4), 0.010001)

    def test_comparison_rejects_changed_non_audience_or_universe(self):
        variants = {cap: sim.score_variant(self.shared(), cap) for cap in sim.CAPS}
        variants[200][0]["non_audience_points"]["european_recognition"] += 1
        with self.assertRaises(ValueError):
            sim.compare(variants)
        variants = {cap: sim.score_variant(self.shared(), cap) for cap in sim.CAPS}
        variants[200].pop()
        with self.assertRaises(ValueError):
            sim.compare(variants)


if __name__ == "__main__":
    unittest.main()
