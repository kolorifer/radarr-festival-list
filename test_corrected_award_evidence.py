import copy, json, unittest
from pathlib import Path
from identity_integrity import OUT, restore_corrected_awards

class CorrectedAwardTests(unittest.TestCase):
    def setUp(self):
        self.frozen = json.loads((OUT/"inputs/corrected-award-evidence.json").read_text())
        self.scope = self.frozen["scope_imdb_ids"]
        self.snapshot = {"films": {iid:{"title":iid} for iid in self.scope}}
        self.snapshot["films"]["tt2562232"] = {"family_scores":{"us_institutional":100,"independent_cinema":85}}

    def test_new_identity_recovers_existing_rules_without_changing_other_films(self):
        outside = copy.deepcopy(self.snapshot["films"]["tt2562232"])
        scored = restore_corrected_awards(self.snapshot,self.frozen,self.scope)
        self.assertEqual({"us_institutional":30.0,"independent_cinema":33.0},
                         scored["tt11416746"]["family_scores"])
        self.assertEqual({"european_recognition":10.0},scored["tt0278731"]["family_scores"])
        self.assertEqual(outside,self.snapshot["films"]["tt2562232"])
        self.assertNotIn("family_scores",self.snapshot["films"]["tt0806125"])
        self.assertNotIn("family_scores",self.snapshot["films"]["tt12913444"])

    def test_reject_unrelated_award_evidence(self):
        self.frozen["event_records"]["academy"].append(
            {"imdb_id":"tt2562232","award":"oscar","category":"best picture","status":"winner"})
        with self.assertRaisesRegex(ValueError,"unrelated"):
            restore_corrected_awards(self.snapshot,self.frozen,self.scope)

    def test_do_not_overwrite_existing_film_evidence(self):
        self.snapshot["films"]["tt11416746"]["family_scores"]={"us_institutional":65}
        with self.assertRaisesRegex(ValueError,"overwrite"):
            restore_corrected_awards(self.snapshot,self.frozen,self.scope)

if __name__=="__main__":unittest.main()
