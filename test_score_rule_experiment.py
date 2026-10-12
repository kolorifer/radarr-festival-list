import unittest

import score_rule_experiment as exp


class ScoreRuleExperimentTests(unittest.TestCase):
    def row(self, score, qualified=False, points=None, imdb_id="tt1"):
        return {
            "overall_score": score,
            "qualified": qualified,
            "imdb_id": imdb_id,
            "title": imdb_id,
            "source_points": points or {},
            "routes": ["old"] if qualified else [],
        }

    def test_non_audience_hits_ignores_audience(self):
        row = self.row(300, points={
            "imdb_audience": 60,
            "letterboxd_audience": 60,
            "trakt_audience": 60,
            "tspdt_21c": 20,
        })
        self.assertEqual(exp.non_audience_hits(row), 1)

    def test_tspdt_and_sight_sound_count_as_one_independent_family(self):
        row = self.row(300, points={"tspdt_21c": 90, "sight_sound": 30})
        self.assertEqual(exp.non_audience_hits(row), 1)
        self.assertEqual(exp.strongest_non_audience(row), 120.0)

    def test_audience_only_never_selected(self):
        rows = [self.row(400, points={"imdb_audience": 66, "letterboxd_audience": 66, "trakt_audience": 66})]
        result = exp.evaluate(rows, 300, 1)
        self.assertEqual(result["selected"], 0)

    def test_two_family_variant_requires_two_non_audience_sources(self):
        rows = [
            self.row(320, points={"tspdt_21c": 80, "sight_sound": 30}, imdb_id="tt1"),
            self.row(320, points={"tspdt_21c": 80, "sight_sound": 30, "us_institutional": 65}, imdb_id="tt2"),
        ]
        self.assertEqual(exp.evaluate(rows, 300, 1)["selected"], 2)
        self.assertEqual(exp.evaluate(rows, 300, 2)["selected"], 1)


if __name__ == "__main__":
    unittest.main()
