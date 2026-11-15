"""Invented v10 policy and immutable predecessors."""
import copy,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,Refusal
from ai_movie_investigator.disclosure import aliases,evidence_alias
from ai_movie_investigator.new_case import _captured_prose_copy
import test_snapshot_film_context as old
import test_snapshot_reobservation as temporal
from test_snapshot_review import NOW
class AssessmentTests(unittest.TestCase):
 def setUp(self):
  f=old.ContextTests();f.setUp();self.p=f.p;self.answer=f.answer
 def prepared(self,p=None):return s.build_film_assessment(p or self.p)
 def answer_for(self,p,unresolved=False):
  b=self.prepared(p);a=copy.deepcopy(self.answer);r=a['result'];a['binding_hash']=aliases(b['run'])
  for key,claim in (('source','source_identity'),('catalogue','crosswalk')):r[key+'_citation']=dict(evidence_id=evidence_alias(b['run'],key),claim=claim)
  r['rationale']='Title/year/runtime observations and current cast support a proposal.'
  if 'historical_id_discrepancy' in p:r['rationale']='Earlier tt7654321 differs from later tt1234567; current cast agrees but the earlier evidence remains unexplained.'
  if unresolved:
   r.pop('source_citation');r.pop('catalogue_citation');r.update(status='unresolved',candidate=None,primary_blocker=dict(aspect='ids',reason='ambiguous_film_evidence',support_considered='The current title and cast corroborate this catalogue record.',material_conflict='The older listing assertion remains unexplained despite the current agreement.'))
  return a
 def test_temporal_cast_support_missing_director_has_both_verdicts(self):
  p=temporal.ReobservationTests().project(temporal.material());p['listing']['directors']=[];p['catalogue']['directors']=[];b=self.prepared(p)
  for unresolved in (False,True):self.assertEqual(s.validate_film_assessment(p,b,self.answer_for(p,unresolved),now=NOW)['status'],'unresolved' if unresolved else 'supported_candidate')
  a=self.answer_for(p,True);a['result']['primary_blocker'].update(aspect='people',reason='missing_film_evidence')
  with self.assertRaises(Refusal):s.validate_film_assessment(p,b,a,now=NOW)
  self.assertNotIn('not a fallback',b['request']['instructions']);self.assertIn('not by itself an identity blocker',b['request']['instructions'])
 def test_current_conflicts_unrelated_title_and_inadequate_support(self):
  for change in ('ids','title','insufficient'):
   p=copy.deepcopy(self.p)
   if change=='ids':p['conflicting_ids']=True;p['citation_eligible_pair']=None
   elif change=='title':p['listing']['title']='An unrelated invented film'
   else:
    p['listing'].update(title=None,year=None,cast=[],directors=[],description_runtime_minutes=None,nfo_runtime_milliseconds=None,nfo_runtime_kind='absent');p['catalogue'].update(title=None,theatrical_year=None,festival_years=[],cast=[],directors=[],runtime_minutes=None)
   with self.subTest(change=change),self.assertRaises(Refusal):s.validate_film_assessment(p,self.prepared(p),self.answer_for(p),now=NOW)
   a=self.answer_for(p,True)
   if change=='title':a['result']['primary_blocker'].update(aspect='title',reason='conflicting_film_evidence')
   self.assertEqual(s.validate_film_assessment(p,self.prepared(p),a,now=NOW)['status'],'unresolved')
 def test_complete_prose_retention_and_envelope(self):
  a=self.answer_for(self.p,True);r=a['result'];b=r['primary_blocker']
  text='The listing cast supports the candidate, while the historical assertion names another film; its origin remains unexplained after weighing the current title and catalogue crosswalk.'
  self.assertGreater(len(text),160);b['material_conflict']=text
  kept,h=_captured_prose_copy(a,film_assessment=True);self.assertEqual(kept,a);self.assertEqual(h['blocker_0_material_conflict']['status'],'retained')
  result=s.validate_film_assessment(self.p,self.prepared(),kept,now=NOW);self.assertEqual(result['film_blockers'][0]['material_conflict'],text);self.assertEqual(result['rationale'],r['rationale'])
  for text in ('No cast overlaps.','The source contradicts this identification.','That is the record it refers to.','The title is “An Invented Film.”'):self.assertEqual(s._complete_justification(text),text)
  for text in ('conflicting_film_evidence','The cast supports this candidate but','The cast supports this candidate because.','Title conflict title conflict.'):
   with self.subTest(text=text),self.assertRaises(Refusal):s._complete_justification(text)
  r['rationale']='𐐀'*600;r['uncertainty']='𐐀'*300
  b['support_considered']='𐐀'*398+'A.';b['material_conflict']='𐐀'*398+'B.'
  r['additional_blockers']=[dict(b,aspect='title')];self.assertLessEqual(len(encoded(a)),32768)
  s.validate_film_assessment(self.p,self.prepared(),a,now=NOW)
 def test_old_v9_frozen(self):self.assertEqual(encoded(s.build_film_weighing(self.p)),Path('tests/fixtures/snapshot-v9-invented-build.json').read_bytes())

 def test_freshness_only_refresh_rejects_substantive_drift(self):
  from ai_movie_investigator.snapshot_authorization import _assessment_refresh
  old=temporal.ReobservationTests().project(temporal.material());current=copy.deepcopy(old)
  current['generated_at']+=1;current['snapshot_sha256']='f'*64
  for key in ('listing','catalogue'):current[key]['observed_at']+=1;current[key]['expires_at']+=1
  current['historical_id_discrepancy']['current_observed_at']+=1
  proof=temporal.material()[-1];new=copy.deepcopy(proof);new['current_observed_at']+=1;new['current_original_sha256']='f'*64
  _assessment_refresh(old,current,proof,new)
  for change in ('imdb','cast','title','nfo','historical_clock','assertion','older'):
   bad=copy.deepcopy(current)
   if change=='imdb':bad['listing']['imdb']='tt9999999'
   elif change=='cast':bad['listing']['cast']=['Different Actor']
   elif change=='title':bad['listing']['title']='Different title'
   elif change=='nfo':bad['listing']['nfo_runtime_milliseconds']+=1000
   elif change=='historical_clock':bad['historical_id_discrepancy']['historical_evidence_present_by']+=1
   elif change=='assertion':bad['source_identifiers']['asserted_imdb']='tt9999999'
   else:bad['listing']['observed_at']=old['listing']['observed_at']-1
   with self.subTest(change=change),self.assertRaisesRegex(Refusal,'snapshot_assessment_refresh'):_assessment_refresh(old,bad,proof,new)
