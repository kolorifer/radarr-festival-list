"""Invented local comparisons, no provider or private data."""
import copy,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,Refusal
from ai_movie_investigator.responses_protocol import schema_value
from test_snapshot_film_scope import FilmScopeTests
from test_snapshot_review import NOW


class ComparisonTests(unittest.TestCase):
 def setUp(self):
  sample=FilmScopeTests();sample.setUp();self.p=sample.p
  self.prepared=s.build_film_comparisons(self.p);self.answer=copy.deepcopy(sample.answer)
  self.answer.pop('film_findings');self.answer['film_blockers']=[]
 def test_facts_distinguish_years_and_runtime_measurement(self):
  facts=s.film_comparisons(self.p)
  self.assertEqual([r['relation'] for r in facts['year'][:2]],['different','exact'])
  self.assertEqual(facts['runtime_description'][0]['difference_minutes'],1)
  self.assertEqual(facts['runtime_nfo'][0]['difference_milliseconds'],60000)
  self.assertEqual(facts['runtime_nfo'][0]['nfo_kind'],'video')
  schema_value(self.answer,self.prepared['request']['text']['format']['schema'])
  result=s.validate_film_comparisons(self.p,self.prepared,self.answer,now=NOW)
  self.assertEqual(result['status'],'supported_candidate');self.assertEqual(result['film_comparisons'],facts)
 def test_missing_placeholders_and_partial_people_are_not_negative(self):
  p=copy.deepcopy(self.p);p['listing']['cast']=['Unknown'];p['listing']['directors']=['Person A'];p['catalogue']['directors']=['Person B'];p['listing']['description_runtime_minutes']=None
  facts=s.film_comparisons(p);self.assertEqual(facts['people'][0]['relation'],'missing');self.assertEqual(facts['people'][1]['relation'],'no_observed_overlap');self.assertEqual(facts['runtime_description'][0]['relation'],'missing')
 def test_unresolved_retains_film_blocker(self):
  a=copy.deepcopy(self.answer);a['result'].update(status='unresolved',candidate=None,citations=[])
  a['film_blockers']=[dict(aspect='title',reason='ambiguous_film_evidence')]
  self.assertEqual(s.validate_film_comparisons(self.p,self.prepared,a,now=NOW)['status'],'unresolved')
  a['film_blockers']=[]
  with self.assertRaisesRegex(Refusal,'snapshot_comparison_blocker_missing'):s.validate_film_comparisons(self.p,self.prepared,a,now=NOW)
 def test_conflicting_ids_or_title_never_silently_support(self):
  p=copy.deepcopy(self.p);p['conflicting_ids']=True;p['citation_eligible_pair']=None
  with self.assertRaises(Refusal):s.validate_film_comparisons(p,s.build_film_comparisons(p),self.answer,now=NOW)
  p=copy.deepcopy(self.p);p['listing']['title']='Different invented title'
  with self.assertRaisesRegex(Refusal,'snapshot_comparison_title_conflict'):s.validate_film_comparisons(p,s.build_film_comparisons(p),self.answer,now=NOW)
 def test_producer_disagreement_and_unfounded_blockers_are_visible(self):
  p=copy.deepcopy(self.p);p['title']='Different collector title'
  facts=s.film_comparisons(p);self.assertEqual(facts['title'][1]['relation'],'different')
  self.assertEqual(facts['title'][1]['left_origin'],'collector')
  a=copy.deepcopy(self.answer);a['result'].update(status='unresolved',candidate=None,citations=[])
  for reason,code in [('missing_film_evidence','snapshot_comparison_blocker_no_missing'),('conflicting_film_evidence','snapshot_comparison_blocker_no_difference')]:
   a['film_blockers']=[dict(aspect='title',reason=reason)]
   with self.subTest(reason=reason),self.assertRaisesRegex(Refusal,code):s.validate_film_comparisons(self.p,self.prepared,a,now=NOW)
 def test_v5_wire_is_frozen_and_long_unicode_fits_v6_bound(self):
  self.assertEqual(encoded(s.build_film_structure(self.p)),Path('tests/fixtures/snapshot-v5-invented-build.json').read_bytes())
  a=copy.deepcopy(self.answer);a['result']['rationale']=a['result']['uncertainty']='🎞'*600
  a['film_blockers']=[dict(aspect='runtime_description',reason='conflicting_film_evidence') for _ in range(6)]
  schema_value(a,self.prepared['request']['text']['format']['schema'])
  self.assertGreater(len(encoded(a)),8192);self.assertLessEqual(len(encoded(a)),32768)
 def test_larger_answer_is_only_for_bound_v6_receipt(self):
  from types import SimpleNamespace
  from ai_movie_investigator import supervised_authorization as auth
  from ai_movie_investigator.contracts import digest
  grant=dict(contract_version='film_comparisons_v6',request=self.prepared['request'])
  result=SimpleNamespace(request_sha256=digest(grant['request']))
  root=SimpleNamespace(require_write_transaction=lambda events:None)
  session=SimpleNamespace(received=result,root=root,events=[],snapshot_grant=grant)
  token=auth._ACTIVE.set(session)
  try:
   self.assertEqual(auth.selected_answer_limit(result),32768)
   self.assertEqual(auth.selected_answer_limit(SimpleNamespace()),8192)
   grant['contract_version']='film_structure_v5';self.assertEqual(auth.selected_answer_limit(result),8192)
   grant['contract_version']='film_comparisons_v6';result.request_sha256='f'*64
   with self.assertRaises(Refusal):auth.selected_answer_limit(result)
  finally:auth._ACTIVE.reset(token)
