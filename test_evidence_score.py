import unittest

from evidence_score import (
    audience_points,
    build_rows,
    imdb_points,
    letterboxd_points,
    ranked_points,
    tmdb_points,
    trakt_points,
)


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

    def test_tiny_audience_is_discounted_per_source(self):
        tiny = {
            "imdb": {"rating": 8.4, "votes": 1500},
            "letterboxd": {"rating": 4.2, "votes": 4800},
            "tmdb": {"rating": 84, "votes": 150},
            "trakt": {"rating": 84, "votes": 150},
        }
        broad = {
            "imdb": {"rating": 8.4, "votes": 500000},
            "letterboxd": {"rating": 4.2, "votes": 500000},
            "tmdb": {"rating": 84, "votes": 50000},
            "trakt": {"rating": 84, "votes": 50000},
        }
        self.assertLess(imdb_points(tiny), 10)
        self.assertLess(letterboxd_points(tiny), 40)
        self.assertLess(tmdb_points(tiny), 15)
        self.assertLess(trakt_points(tiny), 15)
        self.assertGreater(imdb_points(broad), 90)
        self.assertGreater(letterboxd_points(broad), 90)
        self.assertGreater(tmdb_points(broad), 90)
        self.assertGreater(trakt_points(broad), 90)
        self.assertGreater(audience_points(broad), 90)

    def test_sources_add_without_changing_qualification(self):
        back = {"candidates": [{"imdb_id": "tt1", "title": "Film", "year": 2015, "tspdt_rank": 1000}]}
        inst = {"films": []}
        quals = [{"imdb_id": "tt1", "title": "Film", "year": 2015, "routes": ["convergence"]}]
        audience = {"ratings": {"tt1": {"reeldb": {
            "imdb": {"rating": 8.5, "votes": 200000},
            "letterboxd": {"rating": 4.3, "votes": 200000},
            "tmdb": {"rating": 85, "votes": 20000},
            "trakt": {"rating": 85, "votes": 20000},
        }}}}
        snapshot = {
            "ranked_sources": {
                "sight_sound": {"published_depth": 100, "eligible_through_year": 2022, "films": [{"imdb_id": "tt1", "rank": 50}]},
                "bbc_21c": {"published_depth": 100, "eligible_through_year": 2016, "films": [{"imdb_id": "tt1", "rank": 20}]},
                "nyt_21c": {"published_depth": 100, "eligible_through_year": 2025, "films": []},
            },
            "films": {"tt1": {"family_scores": {"us_institutional": 65, "european_recognition": 40, "critics_groups_consensus": 70}}},
        }
        row = build_rows(back, inst, quals, audience, snapshot)[0]
        self.assertEqual(row["source_points"]["tspdt_21c"], 1.0)
        self.assertEqual(row["source_points"]["sight_sound"], 51.0)
        self.assertEqual(row["source_points"]["bbc_21c"], 81.0)
        self.assertEqual(row["source_points"]["us_institutional"], 65.0)
        self.assertEqual(row["source_points"]["european_recognition"], 40.0)
        self.assertEqual(row["source_points"]["critics_groups_consensus"], 70.0)
        self.assertEqual(row["source_points"]["imdb_audience"], 100.0)
        self.assertEqual(row["source_points"]["letterboxd_audience"], 100.0)
        self.assertEqual(row["experimental_source_points"]["tmdb_audience"], 100.0)
        self.assertEqual(row["experimental_source_points"]["trakt_audience"], 100.0)
        self.assertNotIn("tmdb_audience", row["source_points"])
        self.assertNotIn("trakt_audience", row["source_points"])
        self.assertTrue(row["qualified"])
        self.assertEqual(row["routes"], ["convergence"])

    def test_late_film_does_not_get_old_ranked_sources_in_eligible_max(self):
        back = {"candidates": [{"imdb_id": "tt2", "title": "Late Film", "year": 2024, "tspdt_rank": 10}]}
        snapshot = {"ranked_sources": {
            "sight_sound": {"published_depth": 100, "eligible_through_year": 2022, "films": []},
            "bbc_21c": {"published_depth": 100, "eligible_through_year": 2016, "films": []},
            "nyt_21c": {"published_depth": 100, "eligible_through_year": 2025, "films": []},
        }, "films": {}}
        row = build_rows(back, {"films": []}, [], {"ratings": {}}, snapshot)[0]
        self.assertEqual(row["eligible_sources"], 8)
        self.assertEqual(row["eligible_max_score"], 800)


if __name__ == "__main__":
    unittest.main()
