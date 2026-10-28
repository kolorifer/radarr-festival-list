"""Offline numerical-policy experiment; all input evidence is frozen/synthetic."""
import ast
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from research.identity_scoring.scorer import Policy,evaluate,score_candidate,title_similarity
from research.identity_scoring.evaluate import FIXTURES,controls,report

class OfflineScoringTests(unittest.TestCase):
    def setUp(self):
        self.document=json.loads(FIXTURES.read_text());self.cases=self.document['cases']
        self.hero=deepcopy(next(c for c in self.cases if c['name']=='2018 Everyone Is a Hero'))
    def test_owner_reviewed_replays_and_only_one_changed_decision(self):
        r=report(self.document)
        self.assertEqual([x['name'] for x in r['cases'] if x['changed_from_baseline']],['2018 Everyone Is a Hero'])
        selected=[x for x in r['cases'] if x['selected_id'] is not None]
        self.assertEqual(len(selected),3)
        self.assertTrue(all(x['selected_id']==x['expected_id'] for x in selected))
        self.assertEqual(sum(x['kind']=='reviewed_identity' for x in r['cases']),3)
    def test_twenty_synthetic_controls(self):
        cases=controls(self.cases);self.assertEqual(len(cases),20)
        for case in cases:
            with self.subTest(case=case['name']):self.assertEqual(evaluate(case)['decision'],case['expected_decision'])
    def test_runtime_is_continuous_monotonic_not_an_exact_match_gate(self):
        scores=[]
        for minutes in (150,149,148,147,146,145,144):
            c=deepcopy(self.hero);c['source']['runtime']=minutes;scores.append(evaluate(c)['ranked'][0]['score'])
        self.assertEqual(scores,[75,74,73,72,71,70,69])
        for duration in (90,120,180):
            c=deepcopy(self.hero);c['candidates'][0]['runtime']=duration;c['source']['runtime']=duration*.98
            self.assertAlmostEqual(evaluate(c)['ranked'][0]['score'],72)
    def test_missing_facts_never_renormalize_upward(self):
        baseline=evaluate(self.hero)['ranked'][0]['score']
        for key in ('runtime','year','language','imdb'):
            c=deepcopy(self.hero);c['source'][key]=None
            self.assertLessEqual(evaluate(c)['ranked'][0]['score'],baseline)
        c=deepcopy(self.hero);c['source'].update(runtime=None,language=None)
        r=evaluate(c);self.assertEqual(r['ranked'][0]['score'],50);self.assertEqual(r['decision'],'review')
    def test_repeated_aliases_and_release_codec_do_not_add_points(self):
        original=evaluate(self.hero)
        self.hero['candidates'][0]['titles']*=3
        self.hero['source'].update(codec='DDP5.1',resolution='2160p',release_group='RUDR',movie_title_again=self.hero['source']['title'])
        self.assertEqual(evaluate(self.hero),original)
    def test_label_and_past_human_choice_never_enter_score(self):
        original=evaluate(self.hero);self.hero['expected_id']=123
        self.hero['human_choice']='another';self.hero['baseline']='identify'
        self.assertEqual(evaluate(self.hero),original)
    def test_candidate_order_invariant_and_ties_never_choose_first(self):
        rival=deepcopy(self.hero['candidates'][0]);rival.update(id=999999,imdb='tt1234567')
        self.hero['candidates'].append(rival);first=evaluate(self.hero)
        self.hero['candidates'].reverse();self.assertEqual(first,evaluate(self.hero));self.assertIsNone(first['selected_id'])
    def test_missing_rival_facts_do_not_create_a_fake_margin(self):
        rival=deepcopy(self.hero['candidates'][0]);rival.update(id=999999,imdb='tt1234567',runtime=None,language=None)
        self.hero['candidates'].append(rival);r=evaluate(self.hero)
        self.assertEqual(r['ranked'][1]['score'],50);self.assertEqual(r['ranked'][1]['upper_score'],75)
        self.assertEqual(r['margin'],-2);self.assertIsNone(r['selected_id'])
    def test_lowering_score_threshold_cannot_override_conflicting_identity(self):
        self.hero['source']['imdb']='tt1234567'
        r=evaluate(self.hero,Policy(threshold=0,margin=1))
        self.assertIn('tracker_id_conflict',r['reasons']);self.assertIsNone(r['selected_id'])
    def test_madame_does_not_turn_a_wrong_tracker_link_into_automatic_choice(self):
        c=next(c for c in self.cases if c['name']=='Madame Bovary');r=evaluate(c)
        self.assertEqual(r['ranked'][0]['candidate_id'],253161)  # Explicitly expose this limitation.
        self.assertEqual(c['expected_id'],45184);self.assertIsNone(r['selected_id'])
        self.assertIn('source_conflict_or_unknown',r['reasons'])
    def test_numeric_and_roman_sequels_not_fuzzy_typos(self):
        for a,b in [('Movie 2','Movie 3'),('Movie II','Movie III'),('2018','2019')]:
            self.assertEqual(title_similarity(a,b),0)
        self.assertGreater(title_similarity('Bruce Almiighty','Bruce Almighty'),.9)
        self.assertEqual(title_similarity('2018: Everyone Is a Hero','2018 Everyone Is A Hero'),1)
    def test_invalid_nonfinite_and_boolean_inputs_refused(self):
        for val in (float('nan'),float('inf'),True,-1,0):
            c=deepcopy(self.hero);c['source']['runtime']=val
            with self.assertRaises(ValueError):evaluate(c)
        for kwargs in ({'threshold':float('nan')},{'margin':0},{'runtime_scale':0},{'weights':dict.fromkeys(Policy().weights,30)}):
            with self.assertRaises(ValueError):Policy(**kwargs)
        c=deepcopy(self.hero);c['candidates']*=2
        with self.assertRaises(ValueError):evaluate(c)
    def test_blind_spot_is_exposed_not_counted_as_a_success(self):
        r=report(self.document)['synthetic_blind_spots'][0]
        self.assertTrue(r['wrong_labeled_automatic_choice'])
        self.assertEqual(r['selected_id'],999999)
        self.assertEqual(r['expected_id'],866440)
    def test_deterministic_results_match_checked_in_report(self):
        actual=report(self.document);saved=json.loads(FIXTURES.with_name('results.json').read_text());saved.pop('fixture_sha256')
        self.assertEqual(actual,saved)
    def test_evaluation_uses_no_network_or_action_imports(self):
        before=deepcopy(self.document)
        with patch.object(socket,'socket',side_effect=AssertionError('network forbidden')),patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            report(self.document)
        self.assertEqual(before,self.document)
        allowed={'dataclasses','math','re','unicodedata','argparse','copy','hashlib','json','pathlib','scorer'}
        for name in ('scorer.py','evaluate.py'):
            tree=ast.parse(FIXTURES.with_name(name).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):self.assertTrue(all(x.name.split('.')[0] in allowed for x in node.names))
                elif isinstance(node,ast.ImportFrom):self.assertIn(node.module,allowed)
        for name in ('movie_intel_service.py','tracker_metadata.py','tmdb_resolver.py','torrent_evidence_identity.py','identity_triage_worker.py'):
            self.assertNotIn('identity_scoring',Path(name).read_text())

if __name__=='__main__':unittest.main()
