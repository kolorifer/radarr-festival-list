import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.identity_scoring.fresh import nfo_facts, build_case, map_audio_tracks
from research.identity_scoring import cut_discovery as cut
from research.identity_scoring.refresh import (Budget, EVIDENCE_REVISION, atomic,
    attempt_refresh, due_rows, project_entry, refresh_one)
import test_cut_discovery as fixtures
from test_cut_discovery import SEARCH, page


class EvidenceRecoveryTests(unittest.TestCase):
    def test_separator_sections_six_tracks_not_video_or_text(self):
        nfo='''File Name......: Example 2009 REMUX.mkv
        General ===== Title : Example Format : Matroska Format version : Version 2 Duration : 1 h 37 min
        ===== Video ===== Video ID : 1 Duration : 1 h 37 min
        ===== Audio ===== '''
        for i in range(2,8):
            nfo+=f'ID : {i} Format/Info : DTS Codec ID : A_DTS Channel(s) : 6 channels Title : '+('Commentary' if i==7 else 'Surround 5.1')+' Language : French Default : No Forced : No '
        nfo+='Text ID : 8 Language : English'
        facts=nfo_facts(nfo)
        self.assertEqual(facts['runtime'],97)
        self.assertEqual(facts['filenames'],['Example 2009 REMUX.mkv'])
        self.assertEqual(facts['audio_languages'],['french']*6)
        self.assertEqual(facts['audio_tracks'],6)
        self.assertEqual(facts['audio_track_details'][-1]['role'],'commentary')
        self.assertEqual(facts['audio_track_details'][0]['format_info'],'DTS')
        self.assertEqual(facts['audio_track_details'][0]['channels'],'6 channels')
        self.assertEqual(map_audio_tracks(facts,{'french':{'fr'}}),['fr'])
        self.assertFalse(facts['audio_track_details'][-1]['language_scoring_eligible'])

    def test_compact_general_length_numbered_audio_and_iso_language(self):
        nfo='''General : Example 1976 REMUX.mkv Format : Matroska at 39 Mb/s
        Length : 26 GiB for 1 h 38 min 9 s 926 ms
        Video #0 : AVC at 30 Mb/s Aspect : 1920x1080
        Audio #0 : DTS at 3 Mb/s Infos : 6 channels Language : en
        Audio #1 : AC-3 at 640 kb/s Infos : 2 channels Title : Commentary Language : en
        Text #0 : PGS Language : fr Source: BluRay'''
        facts=nfo_facts(nfo)
        self.assertAlmostEqual(facts['runtime'],98.15)
        self.assertEqual(facts['filenames'],['Example 1976 REMUX.mkv'])
        self.assertEqual(facts['audio_languages'],['en','en'])
        self.assertEqual(map_audio_tracks(facts,{'en':{'en'},'english':{'en'}}),['en'])
        f=fixtures.CutTests();f.setUp()
        case,_=build_case(dict(f.release,name='Example 1976 REMUX'),f.listing,nfo,f.search,f.details,f.maps)
        self.assertEqual(case['source']['audio_language_codes'],['en'])
        case,_=build_case(f.release,f.listing,nfo,f.search,f.details,f.maps)
        self.assertTrue(case['source']['conflicting_evidence'])
        self.assertFalse(case['source']['nfo_bound'])

    def test_ambiguous_container_and_subtitle_language_do_not_become_evidence(self):
        facts=nfo_facts('General Duration : 1 h 30 min Duration : 2 h 10 min Video ID : 1 Audio ID : 2 Title : Main Text ID : 3 Language : French')
        self.assertIsNone(facts['runtime'])
        self.assertEqual(facts['audio_languages'],[None])
        facts=nfo_facts('General Duration : 1 h 90 min Video ID : 1')
        self.assertIsNone(facts['runtime'])

    def test_alias_remaster_and_container_version_do_not_trigger_cut_search(self):
        release={'title':'Romanized III aka Example III','year':1993,
                 'name':'Romanized III aka Example III 1993 4K Remastered 1080p BluRay REMUX'}
        candidates={'titles':['Example III','Example III','Romanized III']}
        self.assertEqual(cut.extract(release,{},'Format : Matroska Format version : Version 4',candidates),[])
        release['name']='Example III 1993 Restored International Version 1080p BluRay'
        claims=cut.extract(release,{},'',candidates)
        self.assertTrue(any(c['descriptor']=='restored international' for c in claims))
        release['title']='Phoenix Example III';release['name']='Phoenix Example III 1993 1080p'
        claims=cut.extract(release,{},'',candidates)
        self.assertEqual(sum(c['label']=='phoenix' for c in claims),1)


class SchedulingRecoveryTests(unittest.TestCase):
    def row(self,key):return {'key':key,'observed':1}
    def test_unresolved_first_and_completed_versions_are_not_refetched(self):
        rows=[self.row(k) for k in ['old','new','failed','review','done']]
        saved={'old':{'fresh':{'decision':'would_identify'},'attempted':0},
               'failed':{'attempt_revision':EVIDENCE_REVISION,'next_attempt':200},
               'review':{'fresh':{'decision':'review'},'attempted':2},
               'done':{'fresh':{'decision':'review','evidence_revision':EVIDENCE_REVISION,'refresh_complete':True}}}
        self.assertEqual([r['key'] for r in due_rows(rows,saved,100)],['new','review'])
        self.assertNotIn('done',[r['key'] for r in due_rows(rows,saved,90000)])

    def test_failure_preserves_good_evidence_and_backs_off_without_leaking(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);ledger=home/'ledger';budget=Budget(home/'budget',lambda:100)
            old={'decision':'would_identify','refreshed_at':1,'ranked':[]}
            saved={'a':{'fresh':copy.deepcopy(old)}}
            with patch('research.identity_scoring.refresh.refresh_one',side_effect=RuntimeError('private URL secret')):
                attempt_refresh(home,self.row('a'),saved,ledger,budget,100)
            self.assertEqual(saved['a']['fresh'],old)
            self.assertEqual(saved['a']['error'],'refresh_incomplete')
            self.assertGreater(saved['a']['next_attempt'],3700)
            self.assertNotIn('secret',ledger.read_text())
            row={};project_entry(row,saved['a'],100000)
            self.assertEqual(row['decision'],'would_identify')
            self.assertEqual(row['refresh_status'],'retained_stale')
            self.assertEqual(row['refreshed_at'],1)

    def test_partial_day_budget_resumes_completed_gets_then_finishes_edition(self):
        import tracker_metadata
        f=fixtures.CutTests();f.setUp();calls=[]
        def lookup(release,indexer):
            budget.reserve('listing');calls.append('listing')
            return tracker_metadata.parse_listing('<div id="nfo_text">'+f.nfo+'</div>',release['name'])
        def metadata(path,params,b):
            b.reserve('tmdb');calls.append(path)
            if path.startswith('/find/'):return f.maps['tt1430132']
            if path.startswith('/movie/'):return f.details[76170]
            return f.search
        def public(url,b):
            b.reserve('edition');calls.append('edition')
            return SEARCH if '/search/' in url else page()
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);state=home/'.local/state/identity-scoring-shadow';state.mkdir(parents=True)
            path=state/'budget';ledger=state/'ledger';atomic(path,{'days':{'1970-01-01':38},'cooldowns':{},'suspended':[]})
            saved={};row=self.row('a');budget=Budget(path,lambda:100)
            with patch('research.identity_scoring.refresh.exact_release',return_value=(f.release,{'status':'needs_review','reason':'identity_conflict'})), \
                 patch.object(tracker_metadata,'lookup_listing',side_effect=lookup), \
                 patch.object(tracker_metadata,'parse_listing',return_value=f.listing), \
                 patch('research.identity_scoring.refresh.metadata_get',side_effect=metadata), \
                 patch.object(cut,'fetch',side_effect=public), \
                 patch('research.identity_scoring.refresh.time.sleep'), \
                 patch('research.identity_scoring.refresh.time.time',return_value=100):
                attempt_refresh(home,row,saved,ledger,budget,100)
                self.assertEqual(saved['a']['error'],'shadow_request_budget')
                self.assertEqual(budget.used,2);self.assertEqual(saved['a']['next_attempt'],86400)
                saved=json.loads(ledger.read_text()) # simulate process restart
                budget=Budget(path,lambda:86401)
                attempt_refresh(home,row,saved,ledger,budget,86401)
                fresh=saved['a']['fresh']
                self.assertEqual(fresh['decision'],'review')
                self.assertEqual(fresh['edition_investigation']['decision'],'would_explain_runtime')
                self.assertEqual(fresh['refreshed_at'],100)
                self.assertTrue(fresh['refresh_complete'])
                self.assertEqual(budget.used,4)
                self.assertEqual(calls.count('listing'),1)
                self.assertEqual(calls.count('/find/tt1430132'),1)
                self.assertNotIn('progress',saved['a'])
                self.assertEqual(json.loads(path.read_text())['days'],{'1970-01-01':40,'1970-01-02':4})

    def test_expired_checkpoint_cannot_reuse_listing_or_mapping(self):
        f=fixtures.CutTests();f.setUp();progress={'revision':EVIDENCE_REVISION,'started':0,'listing':f.listing,'captured':{},'metadata':{'old':{}}}
        with patch('research.identity_scoring.refresh.exact_release',return_value=(f.release,{})), \
             patch('research.identity_scoring.refresh.time.time',return_value=90000), \
             patch('tracker_metadata.lookup_listing',return_value={'reason':'listing_mismatch'}) as lookup:
            with self.assertRaisesRegex(RuntimeError,'listing_mismatch'):
                refresh_one(Path('/unused'),{},None,progress)
            lookup.assert_called_once()
        self.assertNotIn('listing',progress);self.assertEqual(progress['metadata'],{})

    def test_run_separates_carryover_and_new_and_stops_at_deadline(self):
        from research.identity_scoring.refresh import run
        import sys
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);state=home/'.local/state/identity-scoring-shadow';state.mkdir(parents=True)
            atomic(state/'pilot.json',{'started':100,'until':200,'carryover_keys':['carry']})
            rows=[dict(self.row(k),cohort=cohort,decision='review') for k,cohort in
                  [('carry','historical_baseline'),('baseline','historical_baseline'),('new','new_during_pilot')]]
            with patch('research.identity_scoring.refresh.Path.home',return_value=home), \
                 patch('research.identity_scoring.refresh.time.time',return_value=150), \
                 patch.object(sys,'argv',['refresh','--actor-code',str(home)]), \
                 patch('deploy.run.read_environment',return_value={}), \
                 patch('research.identity_scoring.refresh.scan',return_value={'rows':rows}), \
                 patch('research.identity_scoring.refresh.attempt_refresh') as attempt:
                run()
                self.assertEqual(attempt.call_count,1)
                self.assertNotEqual(attempt.call_args.args[1]['key'],'baseline')
            report=json.loads((state/'report.json').read_text())
            self.assertEqual(report['carried_over'],1)
            self.assertEqual([r['cohort'] for r in report['rows']],['carried_over','historical_baseline','new_during_pilot'])
            before=(state/'report.json').read_bytes()
            with patch('research.identity_scoring.refresh.Path.home',return_value=home), \
                 patch('research.identity_scoring.refresh.time.time',return_value=201), \
                 patch.object(sys,'argv',['refresh','--actor-code',str(home)]), \
                 patch('deploy.run.read_environment') as env, \
                 patch('research.identity_scoring.refresh.scan') as scan:
                run();env.assert_not_called();scan.assert_not_called()
            self.assertEqual((state/'report.json').read_bytes(),before)

    def test_occurrence_change_stops_before_checkpoint_reuse(self):
        with patch('research.identity_scoring.refresh.exact_release',side_effect=RuntimeError('occurrence_changed')), \
             patch('tracker_metadata.lookup_listing') as lookup:
            with self.assertRaisesRegex(RuntimeError,'occurrence_changed'):
                refresh_one(Path('/unused'),{},None,{'listing':{}})
            lookup.assert_not_called()

if __name__=='__main__':unittest.main()
