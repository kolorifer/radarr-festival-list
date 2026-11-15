"""Invented v11 quality caveats preserve v10 and true evidence refusals."""
import copy,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,Refusal
from ai_movie_investigator.new_case import _captured_prose_copy
import test_snapshot_assessment as old
from test_snapshot_review import NOW
class QualityTests(unittest.TestCase):
 def setUp(self):
  self.f=old.AssessmentTests();self.f.setUp();self.p=self.f.p
 def test_quality_is_advisory_and_legacy_frozen(self):
  self.assertEqual(encoded(s.build_film_assessment(self.p)),Path('tests/fixtures/snapshot-v10-invented-build.json').read_bytes())
  for text,code in [('Title conflict title conflict.','category_labels_only'),('The cast agrees but','trailing_conjunction'),('The cast agrees','no_terminal_punctuation'),('123.','no_alphabetic_words')]:
   a=self.f.answer_for(self.p,True);a['result']['primary_blocker'].update(support_considered=text,material_conflict=text)
   with self.subTest(text=text):
    with self.assertRaisesRegex(Refusal,'snapshot_assessment_justification'):s.validate_film_assessment(self.p,s.build_film_assessment(self.p),a,now=NOW)
    kept,handling=_captured_prose_copy(a,film_assessment=True);self.assertEqual(kept,a)
    r=s.validate_film_quality(self.p,s.build_film_quality(self.p),kept,now=NOW)
    self.assertEqual(r['status'],'unresolved');self.assertEqual(r['film_blockers'][0]['material_conflict'],text)
    self.assertIn(code,[q['predicate'] for q in r['explanation_quality']]);self.assertIn('identical_support_and_conflict',[q['predicate'] for q in r['explanation_quality']])
 def test_safety_and_schema_are_not_quality(self):
  for text in ('/private/fixture','password: synthetic','x'*401):
   a=self.f.answer_for(self.p,True);a['result']['primary_blocker']['material_conflict']=text
   with self.subTest(text=text),self.assertRaises(Refusal):s.validate_film_quality(self.p,s.build_film_quality(self.p),a,now=NOW)
 def test_current_conflict_title_citations_and_temporal_requirements(self):
  for change in ('ids','title','citations'):
   p=copy.deepcopy(self.p)
   if change=='ids':p['conflicting_ids']=True;p['citation_eligible_pair']=None
   if change=='title':p['listing']['title']='An unrelated invented film'
   a=self.f.answer_for(p)
   if change=='citations':a['result']['source_citation']['evidence_id']='unbound'
   with self.subTest(change=change),self.assertRaises(Refusal):s.validate_film_quality(p,s.build_film_quality(p),a,now=NOW)
  import test_snapshot_reobservation as t
  p=t.ReobservationTests().project(t.material());a=self.f.answer_for(p,True);a['result']['rationale']='No historical IDs explained.'
  with self.assertRaisesRegex(Refusal,'snapshot_reobservation_explanation'):s.validate_film_quality(p,s.build_film_quality(p),a,now=NOW)
 def test_supported_and_unresolved_remain_available(self):
  for unresolved in (False,True):
   a=self.f.answer_for(self.p,unresolved);r=s.validate_film_quality(self.p,s.build_film_quality(self.p),a,now=NOW)
   self.assertEqual(r['status'],'unresolved' if unresolved else 'supported_candidate');self.assertEqual(r['explanation_quality'],[])

 def test_withheld_fields_do_not_fabricate_model_quality_claim(self):
  a=self.f.answer_for(self.p,True);a['result']['primary_blocker'].update(support_considered='/private/first-fixture',material_conflict='/private/different-fixture')
  retained,handling=_captured_prose_copy(a,film_assessment=True)
  self.assertEqual(handling['blocker_0_support_considered']['status'],'withheld');self.assertEqual(handling['blocker_0_material_conflict']['status'],'withheld')
  r=s.validate_film_quality(self.p,s.build_film_quality(self.p),retained,now=NOW)
  self.assertEqual(r['explanation_quality'],[])
  self.assertNotIn('/private/',encoded(r).decode())

 def publisher(self):
  return dict(kind='publisher_edition_observation_v1',case_id=self.p['case_id'],version=self.p['version'],title=self.p['catalogue']['title'],year=self.p['catalogue']['theatrical_year'],edition_label='Restored edition',publisher='Invented Publisher',runtime_minutes=102,observed_at=NOW-1,expires_at=NOW+1000,provenance_sha256='a'*64,source_url='https://publisher.invalid/edition?private=fixture',source_reviewed=True,title_year_linkage_reviewed=True)
 def test_publisher_context_is_optional_safe_and_not_edition_identity(self):
  pub=self.publisher();p=copy.deepcopy(self.p);p['publisher_edition']=s.publisher_edition_context(encoded(pub),p,now=NOW)
  b=s.build_film_quality(p);self.assertNotIn(pub['source_url'],encoded(b).decode());self.assertNotIn('publisher.invalid',encoded(b).decode());self.assertIn('Restored edition',encoded(b).decode())
  self.assertEqual(s.film_comparisons(p),s.film_comparisons(self.p));self.assertEqual(p['physical_edition'],'unknown')
  for unresolved in (False,True):
   r=s.validate_film_quality(p,b,self.f.answer_for(p,unresolved),now=NOW);self.assertEqual(r['status'],'unresolved' if unresolved else 'supported_candidate')
  for key,value in [('title','Wrong Film'),('year',1901),('source_reviewed',False),('title_year_linkage_reviewed',False),('expires_at',NOW),('publisher','https://publisher.invalid/secret'),('edition_label','/private/fixture'),('runtime_minutes',True),('provenance_sha256','bad')]:
   bad=dict(pub);bad[key]=value
   with self.subTest(key=key),self.assertRaises(Refusal):s.publisher_edition_context(encoded(bad),self.p,now=NOW)
  import test_snapshot_report_readability as baseline
  from ai_movie_investigator.snapshot_private_report import render
  from ai_movie_investigator.contracts import digest
  f=baseline.ReadabilityTests();f.setUp();report=f.make_report();p=copy.deepcopy(f.p)
  pub.update(case_id=p['case_id'],version=p['version'],title=p['catalogue']['title'],year=p['catalogue']['theatrical_year']);raw=encoded(pub);p['publisher_edition']=s.publisher_edition_context(raw,p,now=NOW);report['projection_sha256']=digest(p)
  html=render(report,digest(report),p,f.local,report['local_context_sha256'],publisher_raw=raw)
  self.assertIn('Reviewed publisher-edition claim',html);self.assertIn('not a measurement or identification',html);self.assertIn(pub['source_url'].replace('&','&amp;'),html)
