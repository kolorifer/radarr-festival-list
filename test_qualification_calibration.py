import copy
import json
from pathlib import Path
import unittest

import qualification_calibration as qc

def film(points, audience=0, qualified=False):
    return {"non_audience_points":points,"audience_score":audience,
            "overall_score":round(sum(points.values())+audience,2),
            "qualified":qualified,"taste_positive":False,"watch_state":"unknown"}

class PolicyTests(unittest.TestCase):
    def test_threshold_is_inclusive_and_uses_published_score(self):
        r=film({"us_institutional":100,"critics_groups_consensus":25})
        self.assertTrue(qc.qualifies(r,"score_only",125))
        self.assertFalse(qc.qualifies(r,"score_only",125.01))

    def test_a_keeps_every_existing_film_even_below_threshold(self):
        r=film({},1,True)
        for t in (100,125,150,175,200,225,250,300,350,400):
            self.assertTrue(qc.qualifies(r,"A_keep_existing",t))
        self.assertFalse(qc.qualifies(r,"score_only",100))

    def test_canon_cannot_supply_two_independent_families(self):
        r=film({"tspdt_21c":50,"sight_sound":25},110)
        self.assertEqual(2,len(qc.family_keys(r,False)))
        self.assertEqual(["canon"],qc.family_keys(r))
        self.assertFalse(qc.qualifies(r,"B_two_families",100))
        self.assertTrue(qc.qualifies(r,"C_one_family",100))

    def test_zero_point_family_is_not_counted(self):
        r=film({"tspdt_21c":50,"critics_groups_consensus":0},60)
        self.assertFalse(qc.qualifies(r,"B_two_families",100))

    def test_audience_only_rejected_by_family_guards(self):
        r=film({},140)
        self.assertTrue(qc.qualifies(r,"score_only",125))
        for p in ("B_two_families","C_one_family","D_audience_half","E_low_evidence_guard"):
            self.assertFalse(qc.qualifies(r,p,125))

    def test_d_exact_half_passes(self):
        r=film({"us_institutional":75},75)
        self.assertTrue(qc.qualifies(r,"D_audience_half",150))

    def test_d_does_not_use_rounded_percentage(self):
        r=film({"us_institutional":50},50.01)
        r["audience_share_pct"]=50.0
        self.assertFalse(qc.qualifies(r,"D_audience_half",100))

    def test_e_retains_strong_single_family_b_rejects(self):
        r=film({"european_recognition":140},100)
        self.assertTrue(qc.qualifies(r,"E_low_evidence_guard",200))
        self.assertFalse(qc.qualifies(r,"B_two_families",200))

    def test_e_rejects_weak_single_family_with_dominant_audience(self):
        r=film({"critics_groups_consensus":15},140)
        self.assertTrue(qc.qualifies(r,"C_one_family",125))
        self.assertFalse(qc.qualifies(r,"E_low_evidence_guard",125))

    def test_e_is_conditional_and_does_not_hide_multifamily_dominance(self):
        r=film({"tspdt_21c":10,"critics_groups_consensus":10},150)
        self.assertTrue(qc.qualifies(r,"E_low_evidence_guard",125))
        self.assertFalse(qc.qualifies(r,"D_audience_half",125))

    def test_policy_set_relationships_and_monotonicity(self):
        rows=[film({},140),film({"tspdt_21c":90},110),
              film({"tspdt_21c":20,"sight_sound":15,"us_institutional":65},140),
              film({"european_recognition":200},100),film({},0,True)]
        for r in rows:
            for t in (100,125,150,175,200,225,250,300,350,400):
                choices={p:qc.qualifies(r,p,t) for p in qc.POLICIES}
                if choices["B_two_families"]:self.assertTrue(choices["E_low_evidence_guard"])
                if choices["E_low_evidence_guard"]:self.assertTrue(choices["C_one_family"])
                if choices["C_one_family"] or choices["D_audience_half"]:self.assertTrue(choices["score_only"])
                if choices["score_only"]:self.assertTrue(choices["A_keep_existing"])
            for p in qc.POLICIES:
                flags=[qc.qualifies(r,p,t) for t in (100,125,150,175,200,225,250,300,350,400)]
                self.assertEqual(sorted(flags,reverse=True),flags)

    def test_taste_watch_metadata_cannot_change_decisions_or_input(self):
        r=film({"tspdt_21c":90},110)
        before=copy.deepcopy(r)
        flags={p:qc.qualifies(r,p,175) for p in qc.POLICIES}
        self.assertEqual(before,r)
        r.update({"taste_positive":True,"watch_state":"watched","taste_signals":["personal-positive +1"]})
        self.assertEqual(flags,{p:qc.qualifies(r,p,175) for p in qc.POLICIES})

    def test_unknown_policy_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError,"Unknown"):
            qc.qualifies(film({},140),"new-policy",100)

    def test_d_above_300_redundant_under_150_cap(self):
        for non_aud in (150.01,200,300):
            r=film({"european_recognition":non_aud},150)
            self.assertTrue(qc.qualifies(r,"D_audience_half",300))
            self.assertFalse(qc.audience_dominant(r))

class FrozenCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parent
        cls.config=json.loads((cls.root/qc.CONFIG).read_text())
        cls.payload=json.loads((cls.root/qc.SCORE).read_text())
        cls.frozen=json.loads((cls.root/"simulation-qualifiers.json").read_text())

    def test_cleaned_inputs_model_universe_and_routes_are_frozen(self):
        hashes=qc.validate_baseline(self.root,self.config,self.payload,self.frozen)
        self.assertEqual(len(qc.FIXED)+1,len(hashes))

    def test_deployed_diagnostic_is_distinct_without_replacing_requested_baseline(self):
        deployed=json.loads((self.root/self.config["deployed_snapshot"]["path"]).read_text())
        self.assertEqual(224,len(deployed))
        self.assertEqual(255,len(self.frozen))
        self.assertEqual(31,len({r["imdb_id"] for r in self.frozen}-{r["imdb_id"] for r in deployed}))
        self.assertEqual(255,sum(r["qualified"] for r in self.payload["films"]))

    def test_route_change_is_rejected(self):
        frozen=copy.deepcopy(self.frozen)
        frozen[0]["routes"]=["changed_route"]
        with self.assertRaisesRegex(ValueError,"routes"):
            qc.validate_baseline(self.root,self.config,self.payload,frozen)

    def test_baseline_flag_change_is_rejected(self):
        payload=copy.deepcopy(self.payload)
        payload["films"][0]["qualified"]=not payload["films"][0]["qualified"]
        with self.assertRaisesRegex(ValueError,"qualification"):
            qc.validate_baseline(self.root,self.config,payload,self.frozen)

    def test_empty_distribution_has_zero_count(self):
        p=qc.population([],self.config)
        self.assertEqual(0,p["count"])
        self.assertEqual(0,sum(p["detailed_score_bands"].values()))

if __name__=="__main__":unittest.main()
