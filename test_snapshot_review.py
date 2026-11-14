import copy
import hashlib
import unittest
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded

NOW=1794650000.0
CASE='outcome-'+'a'*64
VERSION='b'*64

def fixture():
    case=dict(case_id=CASE,version=VERSION,observed_at=NOW-20,first_observed_at=NOW-50,title='Example Movie',year=2020,route='eligible',reason='title_conflict',correlation='strong_source_id',original_type='movie',source_identity=dict(imdb='tt1234567',tmdb=123,asserted_imdb='tt1234567',asserted_tmdb=123))
    item=dict(case_id=CASE,seed=False,eligibility='explicit_unresolved',facts=dict(title='Example Movie',year=2020,imdb='tt1234567',tmdb=123,variants=['Example Movie'],contradictions=['title_conflict'],director=None,runtime=None),provenance=[dict(source='stage1_outcome',digest=VERSION,observed_at=NOW-20)],historical_candidates=[],observed_at=NOW-20)
    coverage=dict(source_releases_observed=1,source_releases_without_outcome=0,outcome_events=1,assessed_release_cases=1,routes={'eligible':1},correlation={'strong_source_id':1},existing_unresolved_seeds=0,legacy_outcome_rows_without_chronology=0,counters={},researching=0,automatic_research_enabled=False,coverage='incomplete')
    snap=encoded(dict(version=1,generated_at=NOW-5,coverage=coverage,cases=[case],items=[item]))
    source=encoded(dict(kind='selected_listing_facts_v1',case_id=CASE,version=VERSION,observed_at=NOW-10,expires_at=NOW+30,title='Example Movie',year=2020,description_runtime_minutes=95,nfo_runtime_milliseconds=5700000,nfo_runtime_kind='video',cast=['Actor One'],directors=['Director One'],imdb='tt1234567'))
    cat=encoded(dict(kind='catalogue_facts_v1',observed_at=NOW-9,expires_at=NOW+40,title='Example Movie',theatrical_year=2021,festival_years=[2020],runtime_minutes=94,cast=['Actor One'],directors=['Director One'],imdb='tt1234567',tmdb=123))
    h=lambda b: hashlib.sha256(b).hexdigest()
    att=dict(kind='main_reviewed_normalized_case_v1',snapshot_sha256=h(snap),case_id=CASE,version=VERSION,source_sha256=h(source),catalogue_sha256=h(cat),source_original_sha256='c'*64,catalogue_original_sha256='d'*64,source_linkage_verified=True,catalogue_crosswalk_verified=True,observed_at=NOW-1,expires_at=NOW+60)
    return snap,source,cat,att

class ProjectionTests(unittest.TestCase):
    def project(self,snap,src,cat,a,at=NOW): return s.projection(snap,a['snapshot_sha256'],CASE,VERSION,src,cat,a,now=at)
    def test_supported_preserves_measurement_and_unknowns(self):
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a)
        self.assertEqual(p['citation_eligible_pair'],dict(imdb='tt1234567',tmdb=123));self.assertFalse(p['conflicting_ids'])
        self.assertEqual(p['listing']['nfo_runtime_kind'],'video');self.assertEqual(p['catalogue']['festival_years'],[2020]);self.assertEqual(p['catalogue']['theatrical_year'],2021)
        self.assertEqual(p['original_capture'],'not_established');self.assertEqual(p['identity_approval'],'unknown')
    def test_conflicting_assertion_cannot_support_candidate(self):
        snap,src,cat,a=fixture();obj=s.decode(snap,1048576);obj['cases'][0]['source_identity']['asserted_tmdb']=456;obj['items'][0]['facts']['tmdb']=456;snap=encoded(obj);a['snapshot_sha256']=hashlib.sha256(snap).hexdigest()
        p=self.project(snap,src,cat,a);self.assertTrue(p['conflicting_ids']);self.assertIsNone(p['citation_eligible_pair']);self.assertEqual(p['source_identifiers']['asserted_tmdb'],456)
    def test_wrong_snapshot_or_attestation_refused(self):
        snap,src,cat,a=fixture()
        with self.assertRaises(ValueError):self.project(snap+b' ',src,cat,a)
        a['source_linkage_verified']=False
        with self.assertRaises(ValueError):self.project(snap,src,cat,a)
    def test_stale_selection_and_untrusted_runtime_label_refused(self):
        snap,src,cat,a=fixture()
        with self.assertRaises(ValueError):self.project(snap,src,cat,a,at=NOW+4000)
        obj=s.decode(src);obj['nfo_runtime_kind']='measured_film';src=encoded(obj);a['source_sha256']=hashlib.sha256(src).hexdigest()
        with self.assertRaises(ValueError):self.project(snap,src,cat,a)
    def test_inconsistent_item_and_future_snapshot_refused(self):
        snap,src,cat,a=fixture();obj=s.decode(snap,1048576);obj['items'][0]['facts']['tmdb']=999
        snap=encoded(obj);a['snapshot_sha256']=hashlib.sha256(snap).hexdigest()
        with self.assertRaises(ValueError):self.project(snap,src,cat,a)
        snap,src,cat,a=fixture();obj=s.decode(snap,1048576);obj['generated_at']=NOW+1
        snap=encoded(obj);a['snapshot_sha256']=hashlib.sha256(snap).hexdigest()
        with self.assertRaises(ValueError):self.project(snap,src,cat,a)
    def test_wire_omits_private_binding_and_validates_two_citations(self):
        from ai_movie_investigator.disclosure import aliases, evidence_alias
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a);prep=s.build(p)
        body=encoded(prep['request']);self.assertNotIn(CASE.encode(),body);self.assertNotIn(VERSION.encode(),body)
        self.assertNotIn(a['source_sha256'].encode(),body)
        result=dict(status='supported_candidate',candidate=dict(imdb='tt1234567',tmdb=123),alternatives=[],citations=[dict(evidence_id=evidence_alias(prep['run'],'source'),claim='source_identity'),dict(evidence_id=evidence_alias(prep['run'],'catalogue'),claim='crosswalk')],rationale='The source and catalogue share identifiers.',uncertainty='Edition and current queue remain unknown.',next_action='human_review')
        reply=dict(binding_hash=aliases(prep['run']),kind='final',lookups=[],result=result)
        self.assertEqual(s.validate_answer(p,prep,reply,now=NOW)['status'],'supported_candidate')
        reply['result']['citations'].pop()
        with self.assertRaises(ValueError):s.validate_answer(p,prep,reply,now=NOW)
    def test_stale_evidence_rejects_positive_answer(self):
        from ai_movie_investigator.disclosure import aliases, evidence_alias
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a);prep=s.build(p)
        result=dict(status='supported_candidate',candidate=p['citation_eligible_pair'],alternatives=[],citations=[dict(evidence_id=evidence_alias(prep['run'],'source'),claim='source_identity'),dict(evidence_id=evidence_alias(prep['run'],'catalogue'),claim='crosswalk')],rationale='Matching identifiers.',uncertainty='Edition unknown.',next_action='human_review')
        with self.assertRaises(ValueError):s.validate_answer(p,prep,dict(binding_hash=aliases(prep['run']),kind='final',lookups=[],result=result),now=NOW+31)
    def test_result_schema_binds_status_and_exact_candidate(self):
        from ai_movie_investigator.responses_protocol import schema_value
        from ai_movie_investigator.disclosure import aliases
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a);prepared=s.build(p)
        schema=prepared['request']['text']['format']['schema']
        base=dict(binding_hash=aliases(prepared['run']),kind='final',lookups=[],result=dict(status='unresolved',candidate=None,alternatives=[],citations=[],rationale='No resolution.',uncertainty='Evidence incomplete.',next_action='human_review'))
        schema_value(base,schema)
        for status,candidate,valid in [('supported_candidate',None,False),('unresolved',{'imdb':'tt1234567','tmdb':123},False),('blocked',{'imdb':'tt1234567','tmdb':123},False),('supported_candidate',{'imdb':'tt7654321','tmdb':123},False),('supported_candidate',{'imdb':'tt1234567','tmdb':124},False),('supported_candidate',{'imdb':'tt1234567','tmdb':123},True),('blocked',None,True)]:
            answer=copy.deepcopy(base);answer['result'].update(status=status,candidate=candidate)
            with self.subTest(status=status,candidate=candidate):
                if valid:schema_value(answer,schema)
                else:
                    with self.assertRaises(ValueError):schema_value(answer,schema)
        old=s.build(p,corrected=False)
        self.assertNotEqual(old['request'],prepared['request'])
        self.assertEqual(old['request']['input'],prepared['request']['input'])
    def test_legacy_wire_matches_frozen_predecessor_bytes(self):
        from pathlib import Path
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a)
        frozen=Path('tests/fixtures/snapshot-v1-invented-build.json').read_bytes()
        self.assertEqual(encoded(s.build(p,corrected=False)),frozen)
    def test_v2_wire_matches_frozen_predecessor_bytes(self):
        from pathlib import Path
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a)
        self.assertEqual(encoded(s.build(p,prose_limited=False)),Path('tests/fixtures/snapshot-v2-invented-build.json').read_bytes())
    def test_v3_string_boundaries_are_locally_enforced(self):
        from ai_movie_investigator.responses_protocol import schema_value
        from ai_movie_investigator.disclosure import aliases
        from ai_movie_investigator.new_case import _captured_prose_copy
        snap,src,cat,a=fixture();p=self.project(snap,src,cat,a);prepared=s.build(p);schema=prepared['request']['text']['format']['schema']
        answer=dict(binding_hash=aliases(prepared['run']),kind='final',lookups=[],result=dict(status='unresolved',candidate=None,alternatives=[],citations=[],rationale='x',uncertainty='y',next_action='human_review'))
        for field in ('rationale','uncertainty'):
            for size,accepted in ((0,False),(1,True),(600,True),(601,False)):
                item=copy.deepcopy(answer);item['result'][field]='x'*size
                with self.subTest(field=field,size=size):
                    if accepted:schema_value(item,schema)
                    else:
                        with self.assertRaises(ValueError):schema_value(item,schema)
        item=copy.deepcopy(answer);item['result']['rationale']='A source/path observation.';schema_value(item,schema)
        retained,handling=_captured_prose_copy(item)
        self.assertEqual(handling['rationale']['status'],'withheld');self.assertNotIn('source/path',retained['result']['rationale'])
    def test_no_eligible_pair_omits_supported_variant(self):
        from ai_movie_investigator.responses_protocol import schema_value
        from ai_movie_investigator.disclosure import aliases
        snap,src,cat,a=fixture();obj=s.decode(src);obj['imdb']=None;src=encoded(obj);a['source_sha256']=hashlib.sha256(src).hexdigest()
        p=self.project(snap,src,cat,a);prepared=s.build(p)
        answer=dict(binding_hash=aliases(prepared['run']),kind='final',lookups=[],result=dict(status='supported_candidate',candidate={'imdb':'tt1234567','tmdb':123},alternatives=[],citations=[],rationale='No.',uncertainty='Unknown.',next_action='human_review'))
        with self.assertRaises(ValueError):schema_value(answer,prepared['request']['text']['format']['schema'])
    def test_source_must_assert_catalogue_imdb(self):
        snap,src,cat,a=fixture();obj=s.decode(src);obj['imdb']=None;src=encoded(obj);a['source_sha256']=hashlib.sha256(src).hexdigest()
        self.assertIsNone(self.project(snap,src,cat,a)['citation_eligible_pair'])

class ExecutablePinTests(unittest.TestCase):
    def test_regular_executable_modes_and_hash(self):
        import tempfile,runpy
        from pathlib import Path
        ns=runpy.run_path('automation/snapshot_review_UNISSUED.py');check=ns['executable_record']
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path=Path(directory).resolve()/'python';path.write_bytes(b'invented executable');path.chmod(0o755)
            expected=hashlib.sha256(b'invented executable').hexdigest();self.assertEqual(check(path,1024),expected)
            path.write_bytes(b'changed executable');self.assertNotEqual(check(path,1024),expected)
            path.chmod(0o777)
            with self.assertRaises(ValueError):check(path,1024)
            link=path.with_name('link');link.symlink_to(path.name)
            with self.assertRaises((ValueError,OSError)):check(link,1024)

if __name__=='__main__':unittest.main()
