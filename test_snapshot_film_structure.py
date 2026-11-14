"""Invented v5 schema and v4 wire preservation tests."""
import copy
import unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,decode,Refusal
from ai_movie_investigator.responses_protocol import schema_value
from test_snapshot_film_scope import FilmScopeTests
from test_snapshot_review import NOW


class FilmStructureTests(unittest.TestCase):
 def setUp(self):
  sample=FilmScopeTests();sample.setUp();self.p=sample.p;self.old=sample.answer
  self.prepared=s.build_film_structure(self.p);self.answer=copy.deepcopy(self.old)
  self.answer['film_findings']={f['aspect']:{k:v for k,v in f.items() if k!='aspect'} for f in self.old['film_findings']}
  self.schema=self.prepared['request']['text']['format']['schema']
 def test_supported_and_unresolved_are_not_forced(self):
  schema_value(self.answer,self.schema)
  self.assertEqual(s.validate_film_structure(self.p,self.prepared,self.answer,now=NOW)['status'],'supported_candidate')
  a=copy.deepcopy(self.answer);a['result'].update(status='unresolved',candidate=None,citations=[])
  a['film_findings']['title'].update(disposition='unknown',evidence=[a['film_findings']['title']['evidence'][0]])
  a['film_blockers']=[dict(aspect='title',reason='ambiguous_film_evidence',evidence=a['film_findings']['title']['evidence'])]
  schema_value(a,self.schema);self.assertEqual(s.validate_film_structure(self.p,self.prepared,a,now=NOW)['status'],'unresolved')
 def test_missing_extra_and_invalid_aspect_fields_refused(self):
  for kind in ('missing','extra','field'):
   a=copy.deepcopy(self.answer)
   if kind=='missing':del a['film_findings']['year']
   elif kind=='extra':a['film_findings']['other']=copy.deepcopy(a['film_findings']['title'])
   else:a['film_findings']['year']['source_field']='title'
   with self.subTest(kind=kind),self.assertRaises(Refusal):schema_value(a,self.schema)
  with self.assertRaises(Refusal):decode('{"film_findings":{"title":{},"title":{}}}')
 def test_v4_bytes_and_input_preserved(self):
  self.assertEqual(encoded(s.build_film_scope(self.p)),Path('tests/fixtures/snapshot-v4-invented-build.json').read_bytes())
  self.assertEqual(self.prepared['request']['input'],s.build_film_scope(self.p)['request']['input'])
 def test_worst_case_unicode_fits_answer_bound(self):
  a=copy.deepcopy(self.answer);a['result']['rationale']=a['result']['uncertainty']='🎞'*80
  for finding in a['film_findings'].values():finding['explanation']='🎞'*40
  refs=a['film_findings']['ids']['evidence'];a['film_blockers']=[dict(aspect='runtime_description',reason='conflicting_film_evidence',evidence=refs) for _ in range(6)]
  schema_value(a,self.schema);self.assertLessEqual(len(encoded(a)),8192)
