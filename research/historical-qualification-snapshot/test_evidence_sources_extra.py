import unittest

import evidence_sources_extra as extra


class ExtraEvidenceSourceTests(unittest.TestCase):
    def test_winners_and_nominees_parser_uses_first_film_per_year_as_winner(self):
        html = """
        <table class="wikitable">
          <tr><th>Year</th><th>Film</th><th>Director</th></tr>
          <tr><th rowspan="3">2020</th><td><a>Winner Film</a></td><td>Director A</td></tr>
          <tr><td><a>Nominee One</a></td><td>Director B</td></tr>
          <tr><td><a>Nominee Two</a></td><td>Director C</td></tr>
          <tr><th>2021 (2nd)</th><td><a>Next Winner</a></td><td>Director D</td></tr>
        </table>
        """
        rows = extra.parse_wikipedia_award_rows(html, winners_only=False)
        self.assertEqual(
            [(r["year"], r["title"], r["winner"]) for r in rows],
            [
                (2020, "Winner Film", True),
                (2020, "Nominee One", False),
                (2020, "Nominee Two", False),
                (2021, "Next Winner", True),
            ],
        )

    def test_winners_only_parser_preserves_tied_winners(self):
        html = """
        <table class="wikitable">
          <tr><th>Year</th><th>Film</th><th>Director</th></tr>
          <tr><th rowspan="2">2022</th><td><a>Film A</a></td><td>A</td></tr>
          <tr><td><a>Film B</a></td><td>B</td></tr>
        </table>
        """
        rows = extra.parse_wikipedia_award_rows(html, winners_only=True)
        self.assertEqual([r["winner"] for r in rows], [True, True])

    def test_merge_adds_new_family_and_caps_existing_family(self):
        snapshot = {
            "films": {
                "tt1": {
                    "title": "Film",
                    "year": 2020,
                    "family_scores": {"european_recognition": 85},
                    "family_evidence": {"european_recognition": ["Existing"]},
                }
            }
        }
        resolved = {
            "efa_best_film": [
                {"imdb_id": "tt1", "title": "Film", "year": 2020, "winner": True}
            ],
            "nsfc_best_picture": [
                {"imdb_id": "tt1", "title": "Film", "year": 2020, "winner": True}
            ],
            "nyfcc_best_film": [
                {"imdb_id": "tt1", "title": "Film", "year": 2020, "winner": True}
            ],
        }
        extra.merge_contributions(snapshot, resolved)
        film = snapshot["films"]["tt1"]
        self.assertEqual(film["family_scores"]["european_recognition"], 100.0)
        self.assertEqual(film["family_scores"]["critics_groups_consensus"], 70.0)
        self.assertIn("Existing", film["family_evidence"]["european_recognition"])

    def test_critics_choice_is_modest_corroboration_inside_critics_family(self):
        snapshot = {
            "films": {
                "tt1": {"title": "Winner", "year": 2020, "family_scores": {}, "family_evidence": {}},
                "tt2": {"title": "Nominee", "year": 2020, "family_scores": {}, "family_evidence": {}},
            }
        }
        resolved = {
            "critics_choice_best_picture": [
                {"imdb_id": "tt1", "title": "Winner", "year": 2020, "winner": True},
                {"imdb_id": "tt2", "title": "Nominee", "year": 2020, "winner": False},
            ]
        }
        extra.merge_contributions(snapshot, resolved)
        self.assertEqual(snapshot["films"]["tt1"]["family_scores"]["critics_groups_consensus"], 25.0)
        self.assertEqual(snapshot["films"]["tt2"]["family_scores"]["critics_groups_consensus"], 8.0)
        self.assertIn(
            "Critics Choice Best Picture (winner)",
            snapshot["films"]["tt1"]["family_evidence"]["critics_groups_consensus"],
        )


if __name__ == "__main__":
    unittest.main()
