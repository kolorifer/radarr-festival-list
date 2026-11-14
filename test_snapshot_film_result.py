"""Invented result variants and prior wire preservation."""
import copy,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,Refusal
from ai_movie_investigator.responses_protocol import schema_value
from test_snapshot_film_comparisons import ComparisonTests
from test_snapshot_review import NOW


class ResultTests(unittest.TestCase):
 def setUp(self):
  f=ComparisonTests();f.setUp();self.p=f.p;self.old=f.answer;self.prepared=s.build_film_result(self.p);self.schema=self.prepared['request']['text']['format']['schema']
  self.answer=copy.deepcopy(self.old);self.answer.pop('film_blockers');r=self.answer['result'];c=r.pop('citations')
  r.update(source_citation=c[0],catalogue_citation=c[1],primary_blocker=None,additional_blockers=[])
 def test_supported_and_unresolved_pass(self):
  schema_value(self.answer,self.schema);self.assertEqual(s.validate_film_result(self.p,self.prepared,self.answer,now=NOW)['status'],'supported_candidate')
  a=copy.deepcopy(self.answer);r=a['result'];r.pop('source_citation');r.pop('catalogue_citation');r.update(status='unresolved',candidate=None,primary_blocker=dict(aspect='title',reason='ambiguous_film_evidence'))
  schema_value(a,self.schema);self.assertEqual(s.validate_film_result(self.p,self.prepared,a,now=NOW)['status'],'unresolved')
 def test_missing_and_unbound_citations_blockers_refused_in_schema(self):
  for kind in ('empty_blocker','unsupported_reason','duplicate_citation','wrong_action','positive_blocker'):
   a=copy.deepcopy(self.answer);r=a['result']
   if kind in ('empty_blocker','unsupported_reason'):
    r.pop('source_citation');r.pop('catalogue_citation');r.update(status='unresolved',candidate=None,primary_blocker=None if kind=='empty_blocker' else dict(aspect='title',reason='missing_film_evidence'))
   elif kind=='duplicate_citation':r['catalogue_citation']=copy.deepcopy(r['source_citation'])
   elif kind=='wrong_action':r['next_action']='boundary_review'
   else:r['primary_blocker']=dict(aspect='title',reason='ambiguous_film_evidence')
   with self.subTest(kind=kind),self.assertRaises(Refusal):schema_value(a,self.schema)
 def test_v6_frozen_and_unicode_bound(self):
  self.assertEqual(encoded(s.build_film_comparisons(self.p)),Path('tests/fixtures/snapshot-v6-invented-build.json').read_bytes())
  a=copy.deepcopy(self.answer);a['result']['rationale']=a['result']['uncertainty']='🎞'*600
  schema_value(a,self.schema);self.assertLessEqual(len(encoded(a)),32768);self.assertGreater(len(encoded(a)),8192)
 def test_each_blocker_pair_matches_computed_comparisons(self):
  facts=s.film_comparisons(self.p)
  for aspect in s.FILM_ASPECTS:
   relations={r['relation'] for r in facts[aspect]}
   for reason in ('ambiguous_film_evidence','missing_film_evidence','conflicting_film_evidence'):
    a=copy.deepcopy(self.answer);r=a['result'];r.pop('source_citation');r.pop('catalogue_citation')
    r.update(status='unresolved',candidate=None,primary_blocker=dict(aspect=aspect,reason=reason))
    allowed=reason=='ambiguous_film_evidence' or (reason=='missing_film_evidence' and 'missing' in relations) or (reason=='conflicting_film_evidence' and 'different' in relations)
    with self.subTest(aspect=aspect,reason=reason):
     if allowed:schema_value(a,self.schema)
     else:
      with self.assertRaises(Refusal):schema_value(a,self.schema)
 def test_positive_variant_omitted_when_title_or_ids_conflict(self):
  for change in ('title','ids'):
   p=copy.deepcopy(self.p)
   if change=='title':p['listing']['title']='Different invented title'
   else:p['conflicting_ids']=True;p['citation_eligible_pair']=None
   with self.subTest(change=change),self.assertRaises(Refusal):schema_value(self.answer,s.build_film_result(p)['request']['text']['format']['schema'])
