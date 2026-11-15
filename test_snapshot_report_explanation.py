"""Pure invented renderer checks; no state, provider or source access."""
import copy,hashlib,unittest
from html import escape
from ai_movie_investigator.contracts import encoded,digest
from ai_movie_investigator.snapshot_private_report import render
import test_snapshot_report_readability as baseline
import test_snapshot_reobservation as temporal

class ExplanationTests(unittest.TestCase):
 def setUp(self):
  self.f=baseline.ReadabilityTests();self.f.setUp()
 def show(self,report):return self.f.show(report)
 def test_supported_incomplete_prose_preserved_below_factual_explanation(self):
  report=self.f.make_report();raw=('The current listing and catalogue agree, while the earlier observation ' *20)[:600]
  report['result']['rationale']=raw
  before=copy.deepcopy((report,self.f.p,self.f.local));old_hash=digest(report)
  html=self.show(report)
  self.assertIn('A film identity is proposed for human review.',html)
  self.assertIn('Recorded decision and observed evidence',html)
  self.assertIn('possibly incomplete wording',html);self.assertIn('only a punctuation heuristic',html)
  self.assertIn(escape(raw),html);self.assertEqual(html.count(escape(raw)),1)
  self.assertLess(html.index('Recorded decision and observed evidence'),html.index('possibly incomplete wording'))
  self.assertIn('listing title: Example Movie matches catalogue title: Example Movie.',html)
  self.assertIn('Open the exact source listing',html)
  primary=html.split('Recorded decision and observed evidence',1)[1].split('<h2>Identification problem',1)[0]
  self.assertIn('catalogue theatrical',primary);self.assertIn('catalogue festival',primary)
  self.assertEqual((report,self.f.p,self.f.local),before);self.assertEqual(digest(report),old_hash)
 def test_complete_prose_and_false_grammar_certainty(self):
  report=self.f.make_report();report['result']['rationale']='The current cast supports this interpretation.';report['result']['uncertainty']='Edition remains unknown.'
  html=self.show(report);self.assertNotIn('possibly incomplete wording',html);self.assertIn(escape(report['result']['rationale']),html)
  self.assertIn('Model interpretation, distinct from the factual summary',html)
  # A period is not claimed to prove grammatical or semantic completeness.
  report['result']['rationale']='Because the.';html=self.show(report);self.assertIn('Because the.',html);self.assertNotIn('verified complete',html)
 def test_unresolved_and_withheld_qualifications_remain(self):
  report=self.f.make_report();report['result'].update(status='unresolved',candidate=None,citations=[],rationale='The evidence remains unresolved because')
  report['previous_assessment']=dict(slot=1,status='supported_candidate',candidate=dict(imdb='tt1234567',tmdb=123),rationale='retained')
  html=self.show(report)
  self.assertIn('Film identity remains unresolved; no identity is proposed.',html);self.assertIn('Earlier distinct assessment',html)
  self.assertIn('Identity and acquisition remain unapproved',html);self.assertIn('source independence is not established',html)
  self.assertIn('they are not themselves a model verdict',html)
  report['prose_handling']['rationale']['status']='withheld';html=self.show(report)
  self.assertIn('original text is not retained',html);self.assertNotIn(report['result']['rationale'],html)
 def test_uncertainty_only_incomplete_and_escaping(self):
  report=self.f.make_report();report['result']['uncertainty']='Unverified <img src=x> & source'
  self.f.p['listing']['title']='<script>invented</script>';report['projection_sha256']=digest(self.f.p)
  html=self.show(report);self.assertIn('possibly incomplete wording',html)
  self.assertIn(escape(report['result']['uncertainty']),html);self.assertNotIn('<img src=x>',html)
  self.assertIn('&lt;script&gt;invented&lt;/script&gt;',html);self.assertNotIn('<script>invented</script>',html)
 def test_dated_discrepancy_preserves_both_ids_and_unknown_fetch(self):
  p=temporal.ReobservationTests().project(temporal.material());report=self.f.make_report()
  local=encoded(dict(tracker_url='https://example.invalid/listing',release_name='Invented release',nfo_text='Invented NFO'))
  report.update(projection_sha256=digest(p),local_context_sha256=hashlib.sha256(local).hexdigest())
  report['result']['rationale']='Earlier evidence differs because'
  before=copy.deepcopy((report,p,local));html=render(report,digest(report),p,local,hashlib.sha256(local).hexdigest())
  primary=html.split('<h2>Recorded decision and observed evidence</h2>',1)[1].split('<h2>Identification problem</h2>',1)[0]
  for text in ('tt7654321','tt1234567','evidence present by','exact fetch time is unknown','later listing observation','not the model’s reasoning'):self.assertIn(text,primary)
  self.assertIn('Dated same-listing ID discrepancy',html);self.assertEqual((report,p,local),before)
