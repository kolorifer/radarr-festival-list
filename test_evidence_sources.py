import unittest

import evidence_sources as es
import evidence_sources_run as run


class EvidenceSourceTests(unittest.TestCase):
    def test_parse_event_yaml(self):
        text = """
'2025':
  golden lion:
    best film:
      nominee: [tt1, tt2]
      winner: [tt2]
"""
        rows = es.parse_imdb_event_yaml(text)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["award"], "golden lion")
        self.assertEqual(rows[0]["category"], "best film")
        self.assertEqual(rows[-1]["status"], "winner")
        self.assertEqual(rows[-1]["imdb_id"], "tt2")

    def test_sight_sound_parser_preserves_published_position(self):
        text = """
44012 # Old Film (1975) [X]
843 # In the Mood for Love (2000) [Wong]
1018 # Mulholland Drive (2001) [Lynch]
"""
        rows = run.parse_sight_sound(text)
        self.assertEqual([r["rank"] for r in rows], [2, 3])
        self.assertEqual(rows[0]["title"], "In the Mood for Love")

    def test_us_family_caps_and_globes_corrobate(self):
        records = {key: [] for key in es.EVENTS}
        records["academy"] = [
            {"imdb_id": "tt1", "award": "oscar", "category": "best motion picture of the year", "status": "nominee", "year": 2020},
        ]
        records["golden_globes"] = [
            {"imdb_id": "tt1", "award": "golden globe", "category": "best motion picture - drama", "status": "winner", "year": 2020},
        ]
        score = es.score_events(records)["tt1"]["family_scores"]["us_institutional"]
        self.assertEqual(score, 90.0)

    def test_sundance_double_win_reaches_100(self):
        records = {key: [] for key in es.EVENTS}
        records["sundance"] = [
            {"imdb_id": "tt2", "award": "grand jury prize", "category": "dramatic", "status": "winner", "year": 2020},
            {"imdb_id": "tt2", "award": "audience award", "category": "u.s. dramatic", "status": "winner", "year": 2020},
        ]
        score = es.score_events(records)["tt2"]["family_scores"]["independent_cinema"]
        self.assertEqual(score, 100.0)

    def test_european_family_caps_at_100(self):
        records = {key: [] for key in es.EVENTS}
        records["cannes"] = [
            {"imdb_id": "tt3", "award": "palme d'or", "category": "palme d'or", "status": "winner", "year": 2020},
        ]
        records["bafta"] = [
            {"imdb_id": "tt3", "award": "bafta film award", "category": "best film", "status": "winner", "year": 2020},
        ]
        score = es.score_events(records)["tt3"]["family_scores"]["european_recognition"]
        self.assertEqual(score, 100.0)


if __name__ == "__main__":
    unittest.main()
