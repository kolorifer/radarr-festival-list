"""Invented rendering cases; no provider, native access or private records."""
import copy,hashlib,unittest
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded,digest,Refusal
from ai_movie_investigator.new_case import _WITHHELD_PROSE
from ai_movie_investigator.snapshot_private_report import render
from test_snapshot_film_comparisons import ComparisonTests
from test_snapshot_review import NOW


class ReadabilityTests(unittest.TestCase):
 def setUp(self):
  f=ComparisonTests();f.setUp();self.p=f.p;self.answer=f.answer;self.prepared=f.prepared
  self.local=encoded(dict(tracker_url='https://example.invalid/listing?a=1&b=2',release_name='Invented release',nfo_text='Invented NFO'))
  self.result=s.validate_film_comparisons(self.p,self.prepared,self.answer,now=NOW)
 def make_report(self,result=None):
  return dict(kind='receipt_bound_snapshot_review_v1',projection_sha256=digest(self.p),local_context_sha256=hashlib.sha256(self.local).hexdigest(),
   generation_invoked=True,provider_receipt_correlated=True,sent=False,result=result or self.result,
   prose_handling=dict(rationale=dict(status='retained',predicate=None),uncertainty=dict(status='retained',predicate=None)))
 def show(self,report):return render(report,digest(report),self.p,self.local,hashlib.sha256(self.local).hexdigest())
 def test_supported_summary_and_evidence_categories(self):
  report=self.make_report();old=(copy.deepcopy(report),copy.deepcopy(self.p),self.local)
  html=self.show(report)
  for value in ('A film identity is proposed for human review','Open the exact source listing','a=1&amp;b=2',
   'Observed agreements','Observed differences','Missing or inconclusive observations','catalogue theatrical: 2021',
   'catalogue festival: 2020','listing description runtime: 95 minutes','listing NFO runtime: 1 h 35 min 0.000 s (video)',
   'catalogue runtime: 94 minutes','1 min 0.000 sec longer','source independence is not established','identity is proposed','Technical details and previous attempts'):
   self.assertIn(value,html)
  self.assertEqual((report,self.p,self.local),old);self.assertEqual(report['result']['status'],'supported_candidate')
 def test_withheld_rationale_is_not_reconstructed_and_blocker_has_values(self):
  answer=copy.deepcopy(self.answer);answer['result'].update(status='unresolved',candidate=None,citations=[])
  answer['film_blockers']=[dict(aspect='year',reason='conflicting_film_evidence')]
  result=s.validate_film_comparisons(self.p,self.prepared,answer,now=NOW);result['rationale']=_WITHHELD_PROSE
  report=self.make_report(result);report['prose_handling']['rationale']=dict(status='withheld',predicate='path_or_url_syntax')
  report['previous_field_refusal']=dict(slot=3,terminal_sha256='a'*64,receipt_sha256='b'*64)
  html=self.show(report)
  for value in ('Film identity remains unresolved; no identity is proposed','Model-reported film blockers',
   'conflicting film evidence','catalogue theatrical: 2021','catalogue festival: 2020',
   'original text is not retained','Summary from recorded choices','not the model’s original explanation'):
   self.assertIn(value,html)
  self.assertNotIn(_WITHHELD_PROSE,html)
  self.assertLess(html.index('Technical details and previous attempts'),html.index('earlier assessment received a receipt'))
 def test_blocked_is_not_substituted_and_uncertainty_handling_is_separate(self):
  answer=copy.deepcopy(self.answer);answer['result'].update(status='blocked',candidate=None,citations=[])
  answer['film_blockers']=[dict(aspect='runtime_nfo',reason='ambiguous_film_evidence')]
  result=s.validate_film_comparisons(self.p,self.prepared,answer,now=NOW);result['uncertainty']=_WITHHELD_PROSE
  report=self.make_report(result);report['prose_handling']['uncertainty']=dict(status='withheld',predicate='length')
  html=self.show(report);self.assertIn('The review is blocked; no identity is proposed',html)
  self.assertIn('model’s uncertainty was withheld',html);self.assertIn('NFO video: 1 h 35 min 0.000 s',html)
  self.assertEqual(report['result']['status'],'blocked');self.assertNotIn('model’s rationale was withheld',html)
 def test_escaping_and_exact_bindings(self):
  self.p['title']='<script>alert(1)</script>';self.local=encoded(dict(tracker_url='https://example.invalid/listing?a=1&b=2',release_name='<img src=x>',nfo_text='<script>bad</script>'))
  report=self.make_report();html=self.show(report)
  self.assertNotIn('<script>alert(1)</script>',html);self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',html);self.assertNotIn('<img src=x>',html)
  with self.assertRaises(Refusal):render(report,'f'*64,self.p,self.local,hashlib.sha256(self.local).hexdigest())
  changed=copy.deepcopy(self.p);changed['year']=1999
  with self.assertRaises(Refusal):render(report,digest(report),changed,self.local,hashlib.sha256(self.local).hexdigest())
  with self.assertRaises(Refusal):render(report,digest(report),self.p,self.local,'f'*64)
  self.local=encoded(dict(tracker_url='http://example.invalid/listing',release_name='Invented',nfo_text=''))
  report=self.make_report()
  with self.assertRaises(Refusal):self.show(report)
 def test_overview_names_only_agreeing_or_differing_pairs(self):
  self.p['title']='Different collector title';report=self.make_report()
  html=self.show(report);agree=html.split('<h3>Observed agreements</h3>',1)[1].split('<h3>Observed differences</h3>',1)[0]
  different=html.split('<h3>Observed differences</h3>',1)[1].split('<h3>Missing or inconclusive observations</h3>',1)[0]
  self.assertIn('listing title: Example Movie matches catalogue title: Example Movie',agree)
  self.assertNotIn('collector title: Different collector title',agree)
  self.assertIn('collector title: Different collector title differs from listing title: Example Movie',different)
  self.assertIn('listing year: 2020 matches catalogue festival: 2020',agree)
  self.assertIn('listing year: 2020 differs from catalogue theatrical: 2021',different)
 def test_earlier_film_findings_keep_field_and_citation_provenance(self):
  from test_snapshot_film_scope import FilmScopeTests
  f=FilmScopeTests();f.setUp();result=s.validate_film_scope(f.p,f.prepared,f.answer,now=NOW)
  report=self.make_report(result);html=self.show(report)
  self.assertIn('Model-reported findings',html);self.assertIn('source field: year; comparison field: festival years; cited: source, catalogue',html)
  self.assertLess(html.index('Technical details and previous attempts'),html.index('Model-reported findings'))
 def test_earlier_blocker_keeps_its_own_citations(self):
  from test_snapshot_film_scope import FilmScopeTests
  from ai_movie_investigator.disclosure import evidence_alias
  f=FilmScopeTests();f.setUp();answer=copy.deepcopy(f.answer);answer['result'].update(status='unresolved',candidate=None,citations=[])
  answer['film_findings'][0].update(disposition='unknown',source_field='none',evidence=[evidence_alias(f.prepared['run'],'catalogue')])
  answer['film_blockers']=[dict(aspect='title',reason='missing_film_evidence',evidence=[evidence_alias(f.prepared['run'],'source')])]
  result=s.validate_film_scope(f.p,f.prepared,answer,now=NOW);html=self.show(self.make_report(result))
  self.assertIn('cited evidence: source',html);self.assertIn('comparison field: title; cited: catalogue',html)
