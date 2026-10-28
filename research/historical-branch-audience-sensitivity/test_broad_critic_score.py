import unittest

from broad_critic_score import apply, broad_critic_points, merge_critics_family


class BroadCriticScoreTests(unittest.TestCase):
    def test_broad_critic_is_capped_at_40(self):
        rr = {
            "metacritic": {"rating": 90, "votes": 100},
            "tomatoes": {"rating": 95, "votes": 500},
        }
        self.assertEqual(broad_critic_points(rr), 40.0)

    def test_merge_keeps_group_signal_and_adds_small_corroboration(self):
        self.assertEqual(merge_critics_family(70, 40), 80.0)
        self.assertEqual(merge_critics_family(0, 40), 40.0)

    def test_apply_adds_non_audience_coverage_without_changing_qualification(self):
        payload = {
            "mode": "base",
            "qualification_unchanged": True,
            "score_policy": {},
            "sources": {"critics_groups_consensus": {"type": "family", "max_points": 100}},
            "films": [{
                "title": "Film",
                "imdb_id": "tt1",
                "overall_score": 180.0,
                "source_points": {"imdb_audience": 60.0},
                "source_evidence": {},
                "source_hits": 1,
                "has_non_audience_evidence": False,
                "audience_only_candidate": True,
                "candidate_sources": ["audience_discovery"],
                "eligible_max_score": 900,
                "eligible_score_pct": 20.0,
                "qualified": False,
                "routes": [],
            }],
        }
        ratings = {"ratings": {"tt1": {"reeldb": {
            "metacritic": {"rating": 90, "votes": 100},
            "tomatoes": {"rating": 95, "votes": 500},
        }}}}
        out = apply(payload, ratings)
        row = out["films"][0]
        self.assertEqual(row["source_points"]["critics_groups_consensus"], 40.0)
        self.assertEqual(row["overall_score"], 220.0)
        self.assertTrue(row["has_non_audience_evidence"])
        self.assertFalse(row["audience_only_candidate"])
        self.assertFalse(row["qualified"])
        self.assertEqual(row["routes"], [])
        self.assertEqual(out["mode"], "research-evidence-score-v8-audience200-broadcritics40-officialss250")
        self.assertEqual(out["sources"]["sight_sound"]["depth"], 250)


if __name__ == "__main__":
    unittest.main()
