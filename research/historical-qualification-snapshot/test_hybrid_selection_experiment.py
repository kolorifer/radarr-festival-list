import unittest

from hybrid_selection_experiment import evaluate, score_keep


class HybridSelectionTests(unittest.TestCase):
    def row(self, iid, score, qualified=False, routes=None, points=None):
        return {
            "imdb_id": iid,
            "title": iid,
            "year": 2015,
            "overall_score": score,
            "overall_rank": 1,
            "audience_score": 150,
            "qualified": qualified,
            "routes": routes or [],
            "source_points": points or {},
            "has_non_audience_evidence": bool(points),
        }

    def test_two_family_guard_rejects_single_family_new_film(self):
        row = self.row("tt1", 230, points={"critics_groups_consensus": 35})
        self.assertTrue(score_keep(row, 225, 1))
        self.assertFalse(score_keep(row, 225, 2))

    def test_tspdt_and_sight_sound_are_one_family_for_guard(self):
        row = self.row("tt1", 230, points={"tspdt_21c": 90, "sight_sound": 30})
        self.assertFalse(score_keep(row, 225, 2))
        row["source_points"]["european_recognition"] = 10
        self.assertTrue(score_keep(row, 225, 2))

    def test_guard_does_not_remove_legacy_retention(self):
        rows = [
            self.row("tt1", 190, qualified=True, routes=["convergence"], points={"tspdt_21c": 20}),
            self.row("tt2", 230, qualified=False, points={"critics_groups_consensus": 35}),
            self.row("tt3", 230, qualified=False, points={"critics_groups_consensus": 35, "us_institutional": 65}),
        ]
        policy = {
            "new_floor": 225,
            "legacy_floor": 175,
            "protect_multi_route": True,
            "min_non_audience_families": 2,
        }
        result = evaluate(rows, policy)
        self.assertEqual(result["selected"], 2)
        self.assertEqual(result["legacy_retained"], 1)
        self.assertEqual(result["promotions_vs_old"], 1)


if __name__ == "__main__":
    unittest.main()
