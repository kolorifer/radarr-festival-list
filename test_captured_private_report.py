"""Invented local report; no filesystem/network/source access."""
import unittest
from ai_movie_investigator.contracts import digest,Refusal,encoded,captured_outcome
from ai_movie_investigator.replay import synthetic_case
from ai_movie_investigator.captured_private_report import render_private_report

class PrivateReport(unittest.TestCase):
 def setUp(self):
  raw,self.binding,evidence=synthetic_case(165)
  self.packet=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=self.binding,evidence=evidence,decisions=[],trusted_issuers=['synthetic_owner'])
  self.r=dict(kind='supervised_new_case_review',job=digest(self.packet),binding=self.binding,provenance=dict(mode='simulation'),generation_invoked=False,qualifications=dict(currentness='unknown'),draft=dict(sent=False),assessment=dict(status='unresolved',candidate=None,citations=[],alternatives=[],rationale='<script>bad</script>',uncertainty='Edition unknown',next_action='human_review'))
  self.c=dict(tracker_url='https://example.invalid/item?key=local',release_name='<img src=x onerror=bad>',nfo='Unknown',provenance='Invented fixture',job=digest(self.packet),binding=self.binding,report_sha256=digest(self.r),source_evidence_sha256=self.packet['evidence'][1]['provenance']['digest'],catalogue_evidence_sha256=self.packet['evidence'][0]['provenance']['digest'],prior_failure='unsupported_candidate',source_facts=dict(title='Film',year=1995,runtime=None,cast=None,edition='Uploader assertion'),catalogue_facts=dict(title='Film',year=1995,runtime=112,cast=None,imdb='tt9000127',tmdb=9000127))
 def test_hostile_content_escaped_and_source_facts_qualified(self):
  output=render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
  self.assertNotIn('<script>bad</script>',output);self.assertNotIn('<img src=x',output)
  self.assertIn('&lt;script&gt;bad&lt;/script&gt;',output);self.assertIn('physical edition remain unverified',output)
  self.assertIn('<h3>Retained NFO</h3><pre>',output);self.assertIn('unresolved',output);self.assertIn('unsupported_candidate',output);self.assertIn('Missing fact; cannot compare',output);self.assertNotIn('<a ',output)
 def test_wrong_pin_or_sent_refused(self):
  with self.assertRaisesRegex(Refusal,'private_report_pin'):render_private_report(self.r,'0'*64,self.c,digest(self.c),self.packet)
  self.r['draft']['sent']=True;self.c['report_sha256']=digest(self.r)
  with self.assertRaisesRegex(Refusal,'private_report_selection'):render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
 def test_mismatched_job_and_provenance_refused(self):
  self.c['job']='other'
  with self.assertRaisesRegex(Refusal,'private_report_binding'):render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
  self.c['job']=digest(self.packet);self.r['provenance']['mode']='receipt_correlated_generation';self.c['report_sha256']=digest(self.r)
  with self.assertRaisesRegex(Refusal,'private_report_provenance'):render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
 def test_unknown_is_not_reported_as_agreement(self):
  self.c['source_facts']['cast']='unknown';self.c['catalogue_facts']['cast']='unknown'
  output=render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
  self.assertIn('Missing fact; cannot compare',output)
  self.assertNotIn('<strong>cast comparison:</strong> Observed values agree',output)
 def test_unrelated_source_evidence_refused(self):
  self.c['source_evidence_sha256']='e'*64
  with self.assertRaisesRegex(Refusal,'private_report_evidence_binding'):render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
 def test_unsafe_url_refused(self):
  self.c['tracker_url']='javascript:alert(1)'
  with self.assertRaisesRegex(Refusal,'private_report_url'):render_private_report(self.r,digest(self.r),self.c,digest(self.c),self.packet)
if __name__=='__main__':unittest.main()
