import unittest

from canon_overlap_score import adjusted_sight_sound, apply


class CanonOverlapScoreTests(unittest.TestCase):
    def test_sight_sound_is_half_strength_when_tspdt_present(self):
        self.assertEqual(adjusted_sight_sound(80, 60), 30.0)
        self.assertEqual(adjusted_sight_sound(100, 100), 50.0)

    def test_sight_sound_keeps_full_strength_without_tspdt(self):
        self.assertEqual(adjusted_sight_sound(0, 80), 80.0)

    def test_joint_canon_never_exceeds_150(self):
        self.assertEqual(adjusted_sight_sound(130, 100), 20.0)

    def test_apply_updates_score_and_eligible_max_without_qualification_change(self):
        payload = {
            "mode": "base",
            "current_score_ceiling": 1000,
            "score_policy": {"non_audience_max": 800},
            "sources": {"tspdt_21c": {}, "sight_sound": {}},
            "films": [{
                "title": "Film",
                "year": 2010,
                "imdb_id": "tt1",
                "source_points": {"tspdt_21c": 90.0, "sight_sound": 60.0},
                "source_evidence": {"sight_sound": ["sight_sound #100"]},
                "overall_score": 400.0,
                "overall_rank": 1,
                "source_hits": 2,
                "eligible_max_score": 1000,
                "eligible_score_pct": 40.0,
                "qualified": True,
                "routes": ["canon"],
            }],
        }
        out = apply(payload)
        row = out["films"][0]
        self.assertEqual(row["source_points"]["sight_sound"], 30.0)
        self.assertEqual(row["raw_correlated_source_points"]["sight_sound"], 60.0)
        self.assertEqual(row["overall_score"], 370.0)
        self.assertEqual(row["eligible_max_score"], 950)
        self.assertTrue(row["qualified"])
        self.assertEqual(row["routes"], ["canon"])
        self.assertEqual(out["current_score_ceiling"], 950)
        self.assertEqual(out["score_policy"]["non_audience_max"], 750)
        self.assertEqual(out["mode"], "research-evidence-score-v10-canon150-audience200-broadcritics40")

    def test_eligible_max_drops_even_when_film_is_not_on_sight_sound(self):
        payload = {
            "mode": "base",
            "current_score_ceiling": 1000,
            "score_policy": {"non_audience_max": 800},
            "sources": {"tspdt_21c": {}, "sight_sound": {}},
            "films": [{
                "title": "Eligible but unlisted",
                "year": 2014,
                "imdb_id": "tt2",
                "source_points": {"tspdt_21c": 80.0},
                "source_evidence": {},
                "overall_score": 300.0,
                "overall_rank": 1,
                "source_hits": 1,
                "eligible_max_score": 1000,
                "eligible_score_pct": 30.0,
                "qualified": False,
                "routes": [],
            }, {
                "title": "Too new",
                "year": 2024,
                "imdb_id": "tt3",
                "source_points": {"tspdt_21c": 80.0},
                "source_evidence": {},
                "overall_score": 300.0,
                "overall_rank": 2,
                "source_hits": 1,
                "eligible_max_score": 800,
                "eligible_score_pct": 37.5,
                "qualified": False,
                "routes": [],
            }],
        }
        out = apply(payload)
        by_id = {row["imdb_id"]: row for row in out["films"]}
        self.assertEqual(by_id["tt2"]["eligible_max_score"], 950)
        self.assertEqual(by_id["tt2"]["eligible_score_pct"], 31.58)
        self.assertEqual(by_id["tt3"]["eligible_max_score"], 800)

    def test_apply_is_idempotent(self):
        payload = {
            "mode": "base",
            "current_score_ceiling": 1000,
            "score_policy": {"non_audience_max": 800},
            "sources": {"tspdt_21c": {}, "sight_sound": {}},
            "films": [{
                "title": "Film",
                "year": 2010,
                "imdb_id": "tt1",
                "source_points": {"tspdt_21c": 90.0, "sight_sound": 60.0},
                "source_evidence": {"sight_sound": ["sight_sound #100"]},
                "overall_score": 400.0,
                "overall_rank": 1,
                "source_hits": 2,
                "eligible_max_score": 1000,
                "eligible_score_pct": 40.0,
                "qualified": True,
                "routes": ["canon"],
            }],
        }
        once = apply(payload)
        score_once = once["films"][0]["overall_score"]
        max_once = once["films"][0]["eligible_max_score"]
        twice = apply(once)
        self.assertEqual(twice["films"][0]["overall_score"], score_once)
        self.assertEqual(twice["films"][0]["eligible_max_score"], max_once)


if __name__ == "__main__":
    unittest.main()
