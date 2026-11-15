"""Invented film identity/edition separation and strict observation lineage."""
import copy,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,Refusal
import test_snapshot_assessment as base
import test_snapshot_quality as quality
from test_snapshot_review import NOW
class IdentityBoundaryTests(unittest.TestCase):
 def setUp(self):
  self.f=base.AssessmentTests();self.f.setUp();self.p=copy.deepcopy(self.f.p)
  self.p['source_identifiers'].update(imdb=None,tmdb=None,asserted_imdb=None,asserted_tmdb=None);self.p.update(reason='identifier_conflict',producer_contradictions=['identifier_conflict'])
  self.p['listing'].update(nfo_runtime_kind='container',nfo_runtime_milliseconds=6000000)
  q=quality.QualityTests();q.setUp();pub=q.publisher();pub.update(case_id=self.p['case_id'],version=self.p['version'],title=self.p['catalogue']['title'],year=self.p['catalogue']['theatrical_year'])
  self.p['publisher_edition']=s.publisher_edition_context(encoded(pub),self.p,now=NOW)
 def reply(self,p=None,negative=False):
  p=p or self.p;a=self.f.answer_for(p,negative);return a
 def test_supported_identity_preserves_runtime_edition_and_flag_limitations(self):
  self.assertEqual(s.identity_blocker_pairs(self.p),[])
  r=s.validate_film_identity(self.p,s.build_film_identity(self.p),self.reply(),now=NOW)
  self.assertEqual(r['status'],'supported_candidate');self.assertEqual(r['film_blockers'],[])
  for code in ('physical_edition_unverified','runtime_measurements_differ','publisher_claim_not_torrent_measurement','collector_resolved_outputs_missing','producer_flag_without_current_competing_id'):self.assertIn(code,r['separate_limitations'])
  self.assertEqual(r['film_comparisons'],s.film_comparisons(self.p))
 def test_unsupported_negative_paths_refused_never_rewritten(self):
  for aspect,reason in [('runtime_nfo','conflicting_film_evidence'),('runtime_description','ambiguous_film_evidence'),('ids','ambiguous_film_evidence'),('ids','missing_film_evidence'),('people','missing_film_evidence')]:
   a=self.reply(negative=True);a['result']['primary_blocker'].update(aspect=aspect,reason=reason)
   with self.subTest(aspect=aspect,reason=reason),self.assertRaises(Refusal):s.validate_film_identity(self.p,s.build_film_identity(self.p),a,now=NOW)
 def test_true_id_title_year_people_conflicts_and_insufficient_evidence(self):
  for aspect in ('ids','title','year','people','insufficient'):
   p=copy.deepcopy(self.p);p.pop('publisher_edition')
   if aspect=='ids':p['source_identifiers']['imdb']='tt9999999';p['conflicting_ids']=True;p['citation_eligible_pair']=None
   if aspect=='title':p['listing']['title']='Different invented movie'
   if aspect=='year':p['listing']['year']=1901
   if aspect=='people':p['listing'].update(cast=['Unrelated Person'],directors=['Other Director'])
   if aspect=='insufficient':p['listing'].update(title=None,year=None,cast=[],directors=[],description_runtime_minutes=None,nfo_runtime_kind='absent',nfo_runtime_milliseconds=None)
   a=self.reply(p)
   if aspect in ('ids','title','insufficient'):
    with self.subTest(aspect=aspect),self.assertRaises(Refusal):s.validate_film_identity(p,s.build_film_identity(p),a,now=NOW)
   else:self.assertEqual(s.validate_film_identity(p,s.build_film_identity(p),a,now=NOW)['status'],'supported_candidate')
   a=self.reply(p,True);pair=s.identity_blocker_pairs(p)[0];a['result']['primary_blocker'].update(aspect=pair[0],reason=pair[1])
   self.assertEqual(s.validate_film_identity(p,s.build_film_identity(p),a,now=NOW)['status'],'unresolved')
 def test_legacy_v11_bytes_and_limitations_binding(self):
  f=base.AssessmentTests();f.setUp();self.assertEqual(encoded(s.build_film_quality(f.p)),Path('tests/fixtures/snapshot-v11-invented-build.json').read_bytes())
  a=self.reply();r=s.validate_film_identity(self.p,s.build_film_identity(self.p),a,now=NOW)
  self.assertEqual(r['separate_limitations'],s.identity_limitations(self.p));self.assertNotIn('separate_limitations',a['result'])
 def test_same_case_observation_refresh_rejects_substantive_changes(self):
  from ai_movie_investigator.snapshot_authorization import _identity_refresh
  from test_snapshot_review import fixture,CASE,VERSION
  from ai_movie_investigator.contracts import decode
  snap,src,cat,att=fixture();p=s.projection(snap,att['snapshot_sha256'],CASE,VERSION,src,cat,att,now=NOW)
  old_case,old_item,_=s.select(snap,att['snapshot_sha256'],CASE,VERSION,now=NOW)
  nc=copy.deepcopy(old_case);ni=copy.deepcopy(old_item);np=copy.deepcopy(p)
  nc.update(version='f'*64,observed_at=nc['observed_at']+1);ni['observed_at']+=1;ni['provenance'][0].update(digest=nc['version'],observed_at=ni['observed_at']);np.update(version=nc['version'],observed_at=nc['observed_at'],snapshot_sha256='e'*64,generated_at=p['generated_at']+1);np['listing']['version']=nc['version']
  _identity_refresh(p,np,old_case,old_item,nc,ni,None,None)
  for field in ('case_title','case_first','item_nfo','item_history','source_year','same_clock'):
   bc=copy.deepcopy(nc);bi=copy.deepcopy(ni);bp=copy.deepcopy(np)
   if field=='case_title':bc['title']='Another film'
   if field=='case_first':bc['first_observed_at']+=1
   if field=='item_nfo':bi['facts']['nfo_digest']='f'*64
   if field=='item_history':bi['historical_candidates']=[{'invented':'new'}]
   if field=='source_year':bp['listing']['year']=1901
   if field=='same_clock':bc['observed_at']=old_case['observed_at']
   with self.subTest(field=field),self.assertRaises(Refusal):_identity_refresh(p,bp,old_case,old_item,bc,bi,None,None)

 def test_unknown_festival_year_is_ambiguity_not_proven_other_film(self):
  p=copy.deepcopy(self.p);p['listing']['year']=2020;p['catalogue'].update(theatrical_year=2021,festival_years=[])
  self.assertIn(('year','ambiguous_film_evidence'),s.identity_blocker_pairs(p))
  self.assertEqual(s.validate_film_identity(p,s.build_film_identity(p),self.reply(p),now=NOW)['status'],'supported_candidate')
  a=self.reply(p,True);a['result']['primary_blocker'].update(aspect='year',reason='ambiguous_film_evidence')
  self.assertEqual(s.validate_film_identity(p,s.build_film_identity(p),a,now=NOW)['status'],'unresolved')

 def test_matching_runtime_and_id_alone_are_not_identity_support(self):
  p=copy.deepcopy(self.p);p.pop('publisher_edition');p['listing'].update(title=None,year=None,cast=[],directors=[],description_runtime_minutes=p['catalogue']['runtime_minutes'],nfo_runtime_milliseconds=p['catalogue']['runtime_minutes']*60000)
  with self.assertRaisesRegex(Refusal,'snapshot_identity_support_missing'):s.validate_film_identity(p,s.build_film_identity(p),self.reply(p),now=NOW)

 def test_changed_original_requires_new_observation_even_if_normalized_unchanged(self):
  from ai_movie_investigator.snapshot_authorization import _identity_original_refresh
  old={'source_original':{'sha256':'a'*64},'catalogue_original':{'sha256':'b'*64}}
  for name,key in [('source_original','listing'),('catalogue_original','catalogue')]:
   authority=copy.deepcopy(old);authority[name]['sha256']='f'*64
   with self.subTest(name=name),self.assertRaisesRegex(Refusal,'snapshot_identity_refresh'):_identity_original_refresh(self.p,self.p,old,authority)
   current=copy.deepcopy(self.p);current[key]['observed_at']+=1;_identity_original_refresh(self.p,current,old,authority)
