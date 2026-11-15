"""Invented v9 contracts, no inference quality claim or real operations."""
import copy,hashlib,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.new_case import explanation_prose,_captured_prose_copy
from ai_movie_investigator.credit_test import MINI_PROFILE,MINI_POLICY,MINI_DEBIT,MINI_INPUT_RATE,MINI_OUTPUT_RATE,retained_total
from ai_movie_investigator.contracts import encoded,digest,Refusal
from test_snapshot_film_context import ContextTests
from test_snapshot_review import NOW

class WeighingTests(unittest.TestCase):
 def setUp(self):
  f=ContextTests();f.setUp();self.p=f.p;self.a=f.answer;self.b=s.build_film_weighing(self.p)
 def unresolved(self):
  a=copy.deepcopy(self.a);r=a['result'];r.pop('source_citation');r.pop('catalogue_citation');r.update(status='unresolved',candidate=None,primary_blocker=dict(aspect='title',reason='ambiguous_film_evidence',support_considered='Listing/title/cast observations support one film.',material_conflict='The alternate title describes a different subject despite matching people.'))
  return a
 def test_prose_and_disclosure(self):
  for v in ('Title/year/runtime differences do not outweigh matching people.','Actor/director/title evidence agrees.','NFO = 84 minutes; 95 > 84 in the description.','Conclusion: why does a year / runtime difference matter?'):
   self.assertEqual(explanation_prose(v),v)
  for v in ('/Users/owner/file','path=/Users/owner/file','value=/private/data','../file','docs/../../private','./file','~/file','C:\\file','https://example.invalid','mailto:owner@example.invalid','token: abc','<script>unsafe</script>','<img src=x>','password = invented','person@localhost','a\nb','x'*601):
   with self.subTest(value=v),self.assertRaises(Refusal):explanation_prose(v)
  a=self.unresolved();a['result']['rationale']='Title/year/runtime differences need context.'
  kept,h=_captured_prose_copy(a,film_weighing=True);self.assertEqual(h['rationale']['status'],'retained')
  self.assertEqual(s.validate_film_weighing(self.p,self.b,kept,now=NOW)['rationale'],a['result']['rationale'])
 def test_label_only_rejected(self):
  for text in ('conflicting_film_evidence','title conflict title conflict','runtime','ambiguous film evidence','year difference year difference'):
   a=self.unresolved();a['result']['primary_blocker']['material_conflict']=text
   with self.subTest(text=text),self.assertRaisesRegex(Refusal,'snapshot_justification_label_only'):s.validate_film_weighing(self.p,self.b,a,now=NOW)
 def test_profile_frozen_legacy_and_bound(self):
  self.assertEqual(encoded(s.build_film_context(self.p)),Path('tests/fixtures/snapshot-v8-invented-build.json').read_bytes())
  self.assertEqual(self.b['request']['model'],MINI_POLICY['model']);self.assertEqual(400000*MINI_INPUT_RATE+25000*MINI_OUTPUT_RATE,MINI_DEBIT)
  for change in ('title','ids','binding'):
   p=copy.deepcopy(self.p);a=copy.deepcopy(self.a)
   if change=='title':p['listing']['title']='Completely unrelated invented film'
   elif change=='ids':p['conflicting_ids']=True;p['citation_eligible_pair']=None
   else:a['binding_hash']='f'*64
   with self.subTest(change=change),self.assertRaises(Refusal):s.validate_film_weighing(p,s.build_film_weighing(p),a,now=NOW)
 def test_maximum_fields_fit_existing_limit(self):
  a=self.unresolved();r=a['result'];r['rationale']='𐐀'*600;r['uncertainty']='𐐀'*300
  b=[dict(aspect=x,reason='ambiguous_film_evidence',support_considered='𐐀'*140,material_conflict='𐐀'*140) for x in s.FILM_ASPECTS];r.update(primary_blocker=b[0],additional_blockers=b[1:])
  self.assertLessEqual(len(encoded(a)),32768);s.validate_film_weighing(self.p,self.b,a,now=NOW)

 def test_arithmetic_escaped_and_sensitive_copy_withheld(self):
  from ai_movie_investigator.snapshot_private_report import render
  a=self.unresolved();a['result']['rationale']='NFO = 84 minutes; 95 > 84 and 84 < 95 in the description.'
  kept,handling=_captured_prose_copy(a,film_weighing=True)
  result=s.validate_film_weighing(self.p,self.b,kept,now=NOW)
  local=encoded(dict(tracker_url='https://example.invalid/listing',release_name='Invented',nfo_text='Invented'))
  report=dict(kind='receipt_bound_snapshot_review_v1',projection_sha256=digest(self.p),local_context_sha256=hashlib.sha256(local).hexdigest(),generation_invoked=True,provider_receipt_correlated=True,sent=False,result=result,prose_handling=handling)
  html=render(report,digest(report),self.p,local,hashlib.sha256(local).hexdigest())
  self.assertIn('95 &gt; 84 and 84 &lt; 95',html)
  self.assertEqual(kept,a)
  for text in ('password = invented-value','<script>invented</script>','../private-file'):
   a['result']['rationale']=text;before=copy.deepcopy(a)
   kept,handling=_captured_prose_copy(a,film_weighing=True)
   self.assertEqual(a,before);self.assertEqual(handling['rationale']['status'],'withheld')
   self.assertNotIn(text.encode(),encoded(kept));self.assertNotEqual(digest(a),digest(kept))
