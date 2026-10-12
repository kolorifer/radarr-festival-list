import unittest

from evidence_score import build_rows, institutional_points, ranked_points


class EvidenceScoreTests(unittest.TestCase):
    def test_depth_100_is_exact_100_to_1(self):
        self.assertEqual(ranked_points(1, 100), 100.0)
        self.assertEqual(ranked_points(2, 100), 99.0)
        self.assertEqual(ranked_points(100, 100), 1.0)

    def test_deep_list_preserves_low_ranks(self):
        self.assertEqual(ranked_points(1, 1000), 100.0)
        self.assertGreater(ranked_points(900, 1000), 10.0)
        self.assertEqual(ranked_points(1000, 1000), 1.0)

    def test_invalid_rank_scores_zero(self):
        self.assertEqual(ranked_points(0, 100), 0.0)
        self.assertEqual(ranked_points(101, 100), 0.0)
        self.assertEqual(ranked_points(None, 100), 0.0)

    def test_institutional_strength_is_proportional(self):
        self.assertEqual(institutional_points(0), 0.0)
        self.assertEqual(institutional_points(1), 33.33)
        self.assertEqual(institutional_points(2), 66.67)
        self.assertEqual(institutional_points(3), 100.0)
        self.assertEqual(institutional_points(9), 100.0)

    def test_sources_add_without_changing_qualification(self):
        back = {"candidates": [{"imdb_id": "tt1", "title": "Film", "year": 2020, "tspdt_rank": 1000}]}
        inst = {"films": [{"imdb_id": "tt1", "title": "Film", "year": 2020, "institutional_strength": 2}]}
        quals = [{"imdb_id": "tt1", "title": "Film", "year": 2020, "routes": ["institutional"]}]
        row = build_rows(back, inst, quals)[0]
        self.assertEqual(row["source_points"]["tspdt_21c"], 1.0)
        self.assertEqual(row["source_points"]["institutional_recognition"], 66.67)
        self.assertEqual(row["overall_score"], 67.67)
        self.assertTrue(row["qualified"])
        self.assertEqual(row["routes"], ["institutional"])


if __name__ == "__main__":
    unittest.main()
