"""Invented policy/contract checks; these do not measure live model quality."""
import copy,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.new_case import film_prose,_captured_prose_copy
from ai_movie_investigator.contracts import encoded,Refusal
from ai_movie_investigator.responses_protocol import schema_value
import test_snapshot_film_result as prior
from test_snapshot_review import NOW

class ContextTests(unittest.TestCase):
 def setUp(self):
  f=prior.ResultTests();f.setUp();self.p=f.p;self.answer=f.answer;self.prepared=s.build_film_context(self.p)
 def test_safe_prose_and_legacy_frozen(self):
  for value in ('Conclusion: festival/theatrical years 2001/2002 differ; why?', 'IMDb / TMDb agree, and/or a cast overlap supports review.', 'Year 1999 / 2000; runtime (97.5 minutes) is rounded.', 'Title: An Invented Film — a dated observation.', 'Listing/catalogue titles agree; title/cast supports review.', 'Title / year and runtime/IDs need separate review.'):
   with self.subTest(value=value):self.assertEqual(film_prose(value),value)
  self.assertEqual(encoded(s.build_film_result(self.p)),Path('tests/fixtures/snapshot-v7-invented-build.json').read_bytes())
  a=copy.deepcopy(self.answer);a['result']['rationale']='Festival/theatrical dates: 2001/2002.'
  retained,h=_captured_prose_copy(a,film_context=True);self.assertEqual(h['rationale']['status'],'retained')
  self.assertEqual(s.validate_film_context(self.p,self.prepared,retained,now=NOW)['rationale'],a['result']['rationale'])
  self.assertEqual(_captured_prose_copy(a)[1]['rationale']['status'],'withheld')
 def test_disclosure_refused(self):
  for value in ('/Users/person/private','../private','./private','~/private','file.txt/private','C:\\private','festival/theatrical/private','2001/2002.txt','https://example.invalid','file:private','mailto:person','Bearer invented','token: invented','sk-invented','a'*48,'<script>oops</script>','a\nb','\u202esecret', 'x'*601,'unknown/slash','listing/catalogue/private','title/cast.json','title/cast/year','./title/cast','user@example.invalid','www.example.invalid'):
   with self.subTest(value=value),self.assertRaises(Refusal):film_prose(value)
 def test_contextual_instructions_and_material_explanation(self):
  wire=self.prepared['request'];instructions=wire['instructions']
  for phrase in ('not an automatic veto','not automatically a contradictory identity','after that support','never silently override true ID conflicts','not internal reasoning','download approval'):
   self.assertIn(phrase,instructions)
  a=copy.deepcopy(self.answer);r=a['result'];r.pop('source_citation');r.pop('catalogue_citation')
  r.update(status='unresolved',candidate=None,primary_blocker=dict(aspect='title',reason='ambiguous_film_evidence',support_considered='Listing title and cast support the catalogue.',material_conflict='The producer label describes another subject; its origin remains unverified.'))
  self.assertEqual(s.validate_film_context(self.p,self.prepared,a,now=NOW)['status'],'unresolved')
  for field in ('support_considered','material_conflict'):
   bad=copy.deepcopy(a);bad['result']['primary_blocker'].pop(field)
   with self.assertRaises(Refusal):schema_value(bad,wire['text']['format']['schema'])
 def test_real_conflicts_and_changed_binding_refused(self):
  for change in ('ids','title','binding'):
   p=copy.deepcopy(self.p);a=copy.deepcopy(self.answer)
   if change=='ids':p['conflicting_ids']=True;p['citation_eligible_pair']=None
   elif change=='title':p['listing']['title']='Unrelated invented movie'
   else:a['binding_hash']='f'*64
   with self.subTest(change=change),self.assertRaises(Refusal):s.validate_film_context(p,s.build_film_context(p),a,now=NOW)
