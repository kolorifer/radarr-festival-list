"""Invented bounded v13 prose, no live input or generation."""
import copy,json,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,Refusal
from ai_movie_investigator.new_case import _captured_prose_copy
import test_snapshot_assessment as base
from test_snapshot_review import NOW
class ProseHeadroomTests(unittest.TestCase):
 def setUp(self):self.f=base.AssessmentTests();self.f.setUp();self.p=self.f.p
 def answer(self):return self.f.answer_for(self.p)
 def test_long_complete_text_retained_without_truncation(self):
  a=self.answer();a['result']['rationale']='The observed title and cast corroborate this identification. '*20;a['result']['uncertainty']='The physical edition remains unverified. '*16
  kept,h=_captured_prose_copy(a,film_assessment=True,film_prose_v13=True);self.assertEqual(kept,a)
  r=s.validate_film_prose(self.p,s.build_film_prose(self.p),kept,now=NOW)
  self.assertEqual(r['rationale'],a['result']['rationale']);self.assertEqual(r['uncertainty'],a['result']['uncertainty']);self.assertEqual(r['prose_quality'],[])
  self.assertEqual(r['status'],'supported_candidate');self.assertNotIn('at most600',s.build_film_prose(self.p)['request']['instructions'])
 def test_fragments_retained_quality_only(self):
  a=self.answer();a['result']['rationale']='The title agrees because';a['result']['uncertainty']='Edition remains unknown'
  r=s.validate_film_prose(self.p,s.build_film_prose(self.p),a,now=NOW)
  self.assertEqual(r['status'],'supported_candidate');self.assertEqual(r['rationale'],a['result']['rationale']);self.assertIn({'field':'rationale','predicate':'trailing_conjunction'},r['prose_quality'])
 def test_unsafe_fields_are_wholly_withheld_not_truncated(self):
  a=self.answer();a['result']['rationale']='The title agrees. '*45+'/private/invented';kept,h=_captured_prose_copy(a,film_assessment=True,film_prose_v13=True)
  self.assertEqual(h['rationale']['status'],'withheld');r=s.validate_film_prose(self.p,s.build_film_prose(self.p),kept,now=NOW)
  self.assertNotIn('/private',encoded(r).decode());self.assertNotIn('The title agrees.',r['rationale']);self.assertFalse(any(q['field']=='rationale' for q in r['prose_quality']))
 def test_bounds_and_legacy_bytes(self):
  self.assertEqual(encoded(s.build_film_identity(self.p)),Path('tests/fixtures/snapshot-v12-invented-build.json').read_bytes())
  for field,limit in s.PROSE_LIMITS_V13.items():
   a=self.answer();a['result'][field]='A '*(limit//2)+'X'
   with self.subTest(field=field),self.assertRaises(Refusal):s.validate_film_prose(self.p,s.build_film_prose(self.p),a,now=NOW)
  a=self.answer();a['result']['rationale']='The title agrees. '*50;kept,h=_captured_prose_copy(a,film_assessment=True);self.assertEqual(h['rationale']['status'],'withheld')
 def test_worst_case_unicode_canonical_answer_fits_v13(self):
  p=copy.deepcopy(self.p);p['listing']['year']=1901;a=self.f.answer_for(p,True);r=a['result'];r['rationale']='𐐀'*2399+'.';r['uncertainty']='𐐀'*1199+'.'
  r['primary_blocker'].update(aspect='year',reason='ambiguous_film_evidence',support_considered='𐐀'*399+'.',material_conflict='𐐁'*399+'.');r['additional_blockers']=[copy.deepcopy(r['primary_blocker'])]
  raw=encoded(a);self.assertGreater(len(raw),32768);self.assertLessEqual(len(raw),65536)
  self.assertEqual(encoded(json.loads(raw)),raw)
  kept,h=_captured_prose_copy(a,film_assessment=True,film_prose_v13=True);self.assertEqual(kept,a)
  checked=s.validate_film_prose(p,s.build_film_prose(p),kept,now=NOW);self.assertEqual(checked['status'],'unresolved')
