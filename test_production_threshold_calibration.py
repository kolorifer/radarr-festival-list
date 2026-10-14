import copy
import json
from pathlib import Path
import unittest

import production_threshold_calibration as pt

def movie(iid,score,research=False):
    return {"imdb_id":iid,"overall_score":score,"qualified":research,
            "research_255_qualified":research,"research_255_routes":["convergence"] if research else []}

class ProductionPolicyTests(unittest.TestCase):
    def test_research_flag_does_not_grandfather(self):
        r=movie("research-only",210,True)
        self.assertFalse(pt.selected(r,{"deployed"},225))
        self.assertFalse(pt.selected(r,{"deployed"},250))

    def test_production_is_retained_even_below_both_thresholds(self):
        r=movie("deployed",108.67)
        self.assertTrue(pt.selected(r,{"deployed"},225))
        self.assertTrue(pt.selected(r,{"deployed"},250))

    def test_thresholds_inclusive_and_band_edges(self):
        for score,expected225,expected250 in ((224.99,False,False),(225,True,False),
              (249.99,True,False),(250,True,True)):
            r=movie("new",score)
            self.assertEqual(expected225,pt.selected(r,set(),225))
            self.assertEqual(expected250,pt.selected(r,set(),250))

    def test_exact_three_research_classifications(self):
        for score,label in ((224.99,"neither_threshold"),(225,"naturally_ge225_lt250"),
                            (249.99,"naturally_ge225_lt250"),(250,"naturally_ge250")):
            self.assertEqual(label,pt.classification(movie("r",score,True)))

    def test_selection_does_not_modify_scores_or_metadata(self):
        r=movie("r",240,True);before=copy.deepcopy(r)
        for t in (225,250):pt.selected(r,set(),t)
        self.assertEqual(before,r)

    def test_taste_watch_and_dominance_cannot_add_guards(self):
        r=movie("new",230)
        for annotation in ({"taste_positive":False,"watch_state":"unknown","audience_share_pct":60},
                           {"taste_positive":True,"watch_state":"watched","audience_share_pct":10}):
            r.update(annotation)
            self.assertTrue(pt.selected(r,set(),225))
            self.assertFalse(pt.selected(r,set(),250))

    def test_duplicate_qualifiers_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            pt.routes_map([{"imdb_id":"x","routes":[]},{"imdb_id":"x","routes":[]}])

class FrozenProductionComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parent
        cls.config=json.loads((cls.root/pt.CONFIG).read_text())
        cls.payload=json.loads((cls.root/pt.qc.SCORE).read_text())
        cls.research=json.loads((cls.root/"simulation-qualifiers.json").read_text())
        cls.deployed=json.loads((cls.root/cls.config["deployed_path"]).read_text())
        cls.history=json.loads((cls.root/cls.config["history_path"]).read_text())
        cls.old=json.loads((cls.root/"simulations/qualification-calibration/calibration.json").read_text())

    def rows(self):
        p=set(pt.routes_map(self.deployed));r=set(pt.routes_map(self.research))
        return [{**x,"production_qualified":x["imdb_id"] in p,
                 "research_255_qualified":x["imdb_id"] in r,
                 "P225":pt.selected(x,p,225),"P250":pt.selected(x,p,250)}
                for x in self.payload["films"]]

    def test_frozen_model_routes_history_and_latest_baseline(self):
        hashes=pt.validate(self.root,self.config,self.payload,self.research,self.deployed,self.history)
        self.assertGreaterEqual(len(hashes),15)

    def test_all_224_production_ids_retained_in_both(self):
        deployed=set(pt.routes_map(self.deployed));rows=self.rows()
        for policy in ("P225","P250"):
            selected={r["imdb_id"] for r in rows if r[policy]}
            self.assertTrue(deployed<=selected)
            self.assertEqual(224,sum(r["production_qualified"] for r in rows if r[policy]))

    def test_research_31_exact_documented_difference(self):
        extra=set(pt.routes_map(self.research))-set(pt.routes_map(self.deployed))
        self.assertEqual(31,len(extra));self.assertEqual(extra,set(self.history["research_only_ids"]))

    def test_stricter_policy_subset_and_exact_non_production_delta(self):
        rows=self.rows();a={r["imdb_id"] for r in rows if r["P225"]};b={r["imdb_id"] for r in rows if r["P250"]}
        expected={r["imdb_id"] for r in rows if not r["production_qualified"] and 225<=r["overall_score"]<250}
        self.assertTrue(b<=a);self.assertEqual(expected,a-b);self.assertEqual(36,len(expected))
        self.assertEqual(387,len(a));self.assertEqual(351,len(b))

    def test_twenty_research_only_below_threshold_are_not_selected(self):
        extras=set(self.history["research_only_ids"]);rows=self.rows()
        below=[r for r in rows if r["imdb_id"] in extras and r["overall_score"]<225]
        self.assertEqual(20,len(below));self.assertTrue(all(not r["P225"] and not r["P250"] for r in below))

    def test_original_255_reconciliation_exact_and_counts_add_up(self):
        deployed=set(pt.routes_map(self.deployed));research=set(pt.routes_map(self.research));rows=self.rows()
        for t,expected_total,expected_new,expected_removed in ((225,387,163,20),(250,351,127,23)):
            record=pt.reconcile(rows,deployed,research,self.old,t)
            self.assertEqual(expected_total,record["new_total"])
            self.assertEqual(expected_new,record["new_new"])
            self.assertEqual(expected_removed,record["research31_removed_from_old_total"])
            self.assertEqual(record["old_total"]-record["research31_removed_from_old_total"],record["new_total"])

    def test_changed_production_route_rejected(self):
        deployed=copy.deepcopy(self.deployed);deployed[0]["routes"]=["altered"]
        with self.assertRaisesRegex(ValueError,"IDs/routes"):
            pt.validate(self.root,self.config,self.payload,self.research,deployed,self.history)

    def test_empty_share_distribution_is_explicit(self):
        self.assertEqual(0,pt.statistic([], (0,50,100))["count"])

if __name__=="__main__":unittest.main()
