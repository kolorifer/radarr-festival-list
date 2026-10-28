import json
import unittest
from pathlib import Path


class OfficialSightSoundTests(unittest.TestCase):
    def test_static_snapshot_has_expected_published_positions(self):
        payload = json.loads(Path("sources/sight-sound-2022-top250-modern.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["published_depth"], 250)
        self.assertEqual(len(payload["films"]), 29)
        by_title = {row["title"]: row for row in payload["films"]}
        self.assertEqual(by_title["Get Out"]["rank"], 95)
        self.assertEqual(by_title["Parasite"]["rank"], 90)
        self.assertEqual(by_title["There Will Be Blood"]["rank"], 122)
        self.assertEqual(by_title["Melancholia"]["rank"], 211)
        self.assertEqual(by_title["Yi Yi"]["rank"], 90)

    def test_generated_snapshot_uses_official_top250(self):
        payload = json.loads(Path("sources/evidence-families.json").read_text(encoding="utf-8"))
        source = payload["ranked_sources"]["sight_sound"]
        self.assertEqual(source["published_depth"], 250)
        self.assertEqual(len(source["films"]), 29)
        self.assertEqual(payload["unresolved_ranked"]["sight_sound"], [])
        by_id = {row["imdb_id"]: row for row in source["films"]}
        self.assertEqual(by_id["tt5052448"]["rank"], 95)  # Get Out
        self.assertEqual(by_id["tt6751668"]["rank"], 90)  # Parasite
        self.assertEqual(by_id["tt0240419"]["rank"], 136)  # La cienaga / The Swamp
        self.assertEqual(by_id["tt0244316"]["rank"], 90)  # Yi Yi


if __name__ == "__main__":
    unittest.main()
