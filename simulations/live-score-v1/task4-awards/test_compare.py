"""Offline behavior/provenance tests; synthetic cases never establish real awards."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import compare as task


class AwardsPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = task.calculate()
        cls.evidence = task.read(task.ROOT / 'inputs/evidence.json')
        cls.identities = {f['identity']['imdb_id']: f['identity'] for f in cls.result['films']}

    def fact(self, component, status='winner', iid='tt14905854', year=2026):
        return {'imdb_id': iid, 'component': component, 'status': status,
                'event_year': year, 'source_url': 'https://example.org/synthetic'}

    def bonus(self, kind='screenplay', venue='Cannes', section='main_competition', status='winner'):
        return {'candidate_kind': kind, 'institution': venue, 'section': section,
                'status': status, 'unique_film_attribution': True}

    def test_exact_eight_film_manifest_and_retained_release_context(self):
        expected = [('tt14905854',858024,2025),('tt28607951',1064213,2024),
                    ('tt8999762',549509,2024),('tt17526714',933260,2024),
                    ('tt27714581',1124566,2025),('tt36491653',1456349,2025),
                    ('tt29271639',1527449,2026),('tt38991615',1455247,2026)]
        self.assertEqual([(f['imdb_id'],f['tmdb_id'],f['year']) for f in self.identities.values()],expected)
        cohort=task.read(task.BASE / 'source-validation/cohort.json')['films']
        self.assertEqual([f['identity'] for f in self.result['films']],cohort)
        self.assertNotIn('tt29893755',self.identities)
        self.assertEqual(self.identities['tt38991615']['tmdb_release_events'][0]['startDate'],'2026-12-04')

    def test_baseline_bytes_match_hashes_and_pinned_git_objects(self):
        manifest=task.verify_preservation()
        self.assertGreater(len(manifest['files']),30)
        for name,digest in manifest['files'].items():
            data=subprocess.check_output(['git','show',task.BASELINE+':'+name],cwd=task.REPO)
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest,name)
        # Check the historical source pin as well; no production scorer execution.
        historical=task.read(task.BASE / 'inputs/historical-manifest.json')
        meta=historical['sources/evidence-families.json']
        data=subprocess.check_output(['git','show',meta['revision']+':sources/evidence-families.json'],cwd=task.REPO)
        self.assertEqual(hashlib.sha256(data).hexdigest(),meta['sha256'])

    def test_inventory_precedes_research_and_spans_eight_by_fourteen(self):
        inv=task.inventory()
        self.assertEqual(inv,task.read(task.ROOT / 'inputs/gap-inventory.json'))
        self.assertEqual(len(inv['entries']),112)
        for iid in self.identities:
            entries=[e for e in inv['entries'] if e['imdb_id']==iid]
            self.assertEqual(len({e['institution'] for e in entries}),14)
            self.assertEqual({c for e in entries for c in e['components']},set(task.policy.POLICY))

    def test_evidence_identity_and_source_attribution(self):
        for fact in self.evidence['facts']:
            self.assertEqual(fact['film_title'],self.identities[fact['imdb_id']]['title'])
            self.assertEqual(fact['tmdb_id'],self.identities[fact['imdb_id']]['tmdb_id'])
            self.assertEqual(fact['institution'],self.evidence['sources'][fact['source_id']]['institution'])
        c=copy.deepcopy(self.evidence['checks'][0]);c['tmdb_id']=123
        with self.assertRaisesRegex(ValueError,'identity'):
            task.validate_checks([c],[],self.identities,self.evidence['sources'])
        c=copy.deepcopy(self.evidence['checks'][0]);c['component']='academy_best_picture'
        with self.assertRaisesRegex(ValueError,'Institution'):
            task.validate_checks([c],[],self.identities,self.evidence['sources'])

    def test_repeated_sources_and_win_nominee_use_maximum_once(self):
        records=[self.fact('academy_best_picture','nominee'),self.fact('academy_best_picture')]
        records+=records*3
        scored=task.score(records)
        self.assertEqual(scored['components']['academy_best_picture']['normalized_points'],100)
        self.assertEqual(scored['observed_points']['us_institutional'],10)
        self.assertEqual(len(scored['components']['academy_best_picture']['evidence']),8)

    def test_distinct_components_add_and_caps_hold(self):
        records=[self.fact(k) for k in task.policy.POLICY]
        scored=task.score(records)
        self.assertEqual(scored['observed_points'],task.policy.FAMILIES)
        uncapped=task.score([self.fact('cannes_main','competition'),self.fact('cannes_grand_prix')])
        self.assertEqual(uncapped['normalized_uncapped']['european_recognition'],65)
        self.assertEqual(uncapped['observed_points']['european_recognition'],13)

    def test_sundance_convergence_and_dedup_are_unchanged(self):
        records=[self.fact('sundance_grand_jury'),self.fact('sundance_audience')]
        result=task.score(records*3)
        self.assertEqual(result['normalized_uncapped']['independent_cinema'],100)
        self.assertEqual(result['observed_points']['independent_cinema'],10)
        result=task.score([self.fact('sundance_grand_jury','competition')])
        self.assertEqual(result['observed_points']['independent_cinema'],0.8)

    def test_four_variants_bonuses_off_in_base_and_once_with_caps(self):
        bonuses=[self.bonus(),self.bonus(venue='Venice'),self.bonus('tiff','TIFF','main')]
        base=task.score([],bonuses,'base')['observed_points']
        self.assertEqual(sum(base.values()),0)
        self.assertEqual(sum(task.score([],bonuses,'tiff')['observed_points'].values()),4)
        self.assertEqual(sum(task.score([],bonuses,'screenplay')['observed_points'].values()),6)
        self.assertEqual(sum(task.score([],bonuses,'both')['observed_points'].values()),10)
        self.assertEqual(task.score([self.fact(k) for k in task.policy.POLICY],bonuses,'both')['observed_points'],task.policy.FAMILIES)

    def test_bonus_exclusions_and_unique_attribution(self):
        invalid=[self.bonus(venue='Sundance'),self.bonus(section='orizzonti'),
                 self.bonus(status='nominee'),self.bonus('tiff','TIFF','international'),
                 self.bonus('tiff','TIFF','main','runner_up')]
        invalid.append({**self.bonus(),'unique_film_attribution':False})
        for fact in invalid:
            with self.assertRaises(ValueError):task.score([], [fact], 'both')

    def test_same_scope_positive_absence_conflict_is_rejected(self):
        c=next(c for c in self.evidence['checks'] if c['status']=='verified_no_award')
        records=[self.fact(c['component'],'winner',c['imdb_id'],c['event_year'])]
        with self.assertRaisesRegex(ValueError,'contradicts'):
            task.validate_checks([c],records,self.identities,self.evidence['sources'])
        entry={'imdb_id':c['imdb_id'],'components':[c['component']],
               'edition_envelope':[c['event_year']],'focus_edition':c['event_year'],
               'institution':task.policy.POLICY[c['component']][1]}
        conflicting=[dict(c,id='synthetic_absence'),dict(c,id='synthetic_pending',status='not_yet_announced')]
        with self.assertRaisesRegex(ValueError,'absence versus pending'):
            task.coverage_matrix([entry],[],conflicting)

    def test_nominee_and_different_winner_absence_are_compatible(self):
        c=next(c for c in self.evidence['checks'] if c['stage']=='winner' and c['source_id']=='gotham25final')
        task.validate_checks([c],[self.fact(c['component'],'nominee',c['imdb_id'],c['event_year'])],self.identities,self.evidence['sources'])

    def test_absence_cannot_come_from_failed_fetch_or_snippet(self):
        c=copy.deepcopy(next(c for c in self.evidence['checks'] if c['source_id']=='lafca25'))
        c['status']='verified_no_award'
        with self.assertRaisesRegex(ValueError,'complete inspected'):
            task.validate_checks([c],[],self.identities,self.evidence['sources'])

    def test_pending_unavailable_and_unchecked_stay_unresolved(self):
        for film in self.result['films']:
            self.assertIsNone(film['complete_recognition_score'])
            self.assertTrue(film['unresolved_cell_keys'])
            for variant in film['variants'].values():self.assertIsNone(variant['complete_recognition_score'])
        cells={c['key']:c for c in self.result['coverage']}
        self.assertEqual(cells['tt29271639/efa_best_film/2027/winner']['status'],'not_yet_announced')
        self.assertEqual(cells['tt38991615/lafca_best_film/2025/winner']['status'],'source_not_checked')
        self.assertEqual(cells['tt14905854/lafca_best_film/2025/winner']['status'],'unavailable')
        self.assertEqual(cells['tt29271639/sundance_grand_jury/2026/selection_or_nomination']['status'],'source_not_checked')
        self.assertEqual(cells['tt29271639/sundance_grand_jury/2026/winner']['status'],'verified_no_award')

    def test_new_base_and_bonus_deltas_are_separate_from_task2(self):
        expected={'tt14905854':(15.8,4,0),'tt28607951':(41,0,0),'tt8999762':(26.3,0,0),
                  'tt17526714':(14.7,0,6),'tt27714581':(30.8,0,0),'tt36491653':(24.4,0,0),
                  'tt29271639':(2,0,6),'tt38991615':(0,0,0)}
        for film in self.result['films']:
            base,tiff,screenplay=expected[film['identity']['imdb_id']]
            self.assertEqual(film['new_base_observed_subtotal'],base)
            self.assertEqual(film['signed_evidence_delta'],0)
            for key,delta in [('base',0),('tiff',tiff),('screenplay',screenplay),('both',tiff+screenplay)]:
                v=film['variants'][key]
                self.assertAlmostEqual(v['observed_recognition_subtotal'],base+delta)
                self.assertEqual(v['evidence_delta_vs_task2_same_variant'],0)
                self.assertEqual(v['bonus_delta_vs_new_base'],delta)

    def test_synthetic_new_evidence_delta_is_not_bonus_delta(self):
        records=[self.fact('cannes_main','competition')]
        base=task.compare_variant(records,[self.bonus()],'base',0,0)
        optional=task.compare_variant(records,[self.bonus()],'screenplay',0,6)
        self.assertEqual(base['evidence_delta_vs_task2_same_variant'],2)
        self.assertEqual(base['bonus_delta_vs_new_base'],0)
        self.assertEqual(optional['evidence_delta_vs_task2_same_variant'],2)
        self.assertEqual(optional['bonus_delta_vs_new_base'],6)
        self.assertEqual(optional['total_delta_vs_task2_base'],8)

    def test_no_audience_overall_or_rank_outputs(self):
        for film in self.result['films']:
            self.assertFalse({'ratings','audience','overall_score','overall_rank','rank'} & film.keys())
            for variant in film['variants'].values():
                self.assertFalse({'ratings','audience','overall_score','overall_rank','rank'} & variant.keys())
        self.assertEqual(len(self.result['films']),8)

    def test_deterministic_regeneration_and_committed_bytes(self):
        first=task.outputs(self.result)
        self.assertEqual(first,task.outputs(task.calculate()))
        for name,content in first.items():
            self.assertEqual((task.ROOT/name).read_bytes(),content.encode('utf-8'),name)
        self.assertEqual(len(first['comparison.csv'].splitlines()),9)

    def test_actual_closed_gaps_come_from_new_scoped_records(self):
        by_key={c['key']:c for c in self.result['coverage']}
        for f in self.result['films']:
            for key in f['closed_gap_keys']:
                cell=by_key[key]
                self.assertEqual(cell['status'],'verified_no_award')
                checks=[c for c in self.result['checks'] if c['id'] in cell['check_ids']]
                self.assertTrue(any(c['origin']=='task4' for c in checks))
        self.assertGreater(self.result['diagnostics']['closed_evidence_gaps'],0)


if __name__=='__main__':unittest.main()
