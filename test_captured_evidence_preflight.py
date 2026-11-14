"""Pure invented observations; no account, provider, or private state."""
import copy, hashlib, time, unittest
from ai_movie_investigator.contracts import Refusal, encoded, digest
from ai_movie_investigator.captured_evidence_preflight import derive_candidate_evidence, assemble_successor_packet, preflight_successor, validate_attested_citations

class Preflight(unittest.TestCase):
 def setUp(self):
  self.now=time.time();self.binding=dict(source='fixture',case_id='outcome-'+'a'*64,version='b'*64,occurrence=dict(event_id='event',delivery_id=1))
  self.cat=dict(kind='catalogue_external_ids',imdb='tt9000127',tmdb=9000127)
  self.source=dict(kind='source_release_identity',binding=self.binding,asserted_imdb='tt9000127')
 def pin(self,raw,origin):return dict(sha256=hashlib.sha256(raw).hexdigest(),origin=origin,observed_at=self.now-1,expires_at=self.now+60)
 def attestation(self,cp,sp):return dict(kind='main_reviewed_source_derivation_v1',binding=self.binding,catalogue_sha256=cp['sha256'],source_sha256=sp['sha256'],catalogue_pin_sha256=digest(cp),source_pin_sha256=digest(sp),attested_at=self.now-0.5,expires_at=self.now+60,catalogue_original_sha256='c'*64,source_original_sha256='d'*64,local_context_sha256='e'*64,source_occurrence_verified=True,provenance_reviewed=True)
 def derive(self,cat=None,source=None):
  c=encoded(self.cat if cat is None else cat);s=encoded(self.source if source is None else source)
  cp=self.pin(c,'catalogue');sp=self.pin(s,'source')
  att=self.attestation(cp,sp)
  return derive_candidate_evidence(self.binding,c,cp,s,sp,att,now=self.now)
 def test_exact_crosswalk_and_independent_source(self):
  rows=self.derive();self.assertEqual([r['claims'] for r in rows],[['crosswalk'],['source_identity']]);self.assertEqual(rows[0]['candidate'],rows[1]['candidate'])
 def test_conflicting_or_missing_id_refused(self):
  for value in ('tt9000128',None):
   source=dict(self.source,asserted_imdb=value)
   with self.assertRaisesRegex(Refusal,'source_identity_unproven'):self.derive(source=source)
 def test_wrong_occurrence_refused(self):
  source=copy.deepcopy(self.source);source['binding']['occurrence']['delivery_id']=2
  with self.assertRaisesRegex(Refusal,'source_identity_unproven'):self.derive(source=source)
 def test_changed_digest_refused(self):
  c=encoded(self.cat);s=encoded(self.source);pin=self.pin(c,'catalogue');pin['sha256']='0'*64
  with self.assertRaisesRegex(Refusal,'observation_digest'):derive_candidate_evidence(self.binding,c,pin,s,self.pin(s,'source'),self.attestation(pin,self.pin(s,'source')),now=self.now)
 def test_origin_and_freshness_cannot_change_after_attestation(self):
  c=encoded(self.cat);s=encoded(self.source);cp=self.pin(c,'catalogue');sp=self.pin(s,'source');att=self.attestation(cp,sp)
  for field,value in (('origin','other'),('observed_at',self.now),('expires_at',self.now+120)):
   changed=dict(cp,**{field:value})
   with self.assertRaisesRegex(Refusal,'source_attestation_required'):
    derive_candidate_evidence(self.binding,c,changed,s,sp,att,now=self.now)
 def test_malformed_timestamp_refused(self):
  c=encoded(self.cat);s=encoded(self.source);cp=self.pin(c,'catalogue');sp=self.pin(s,'source');att=self.attestation(cp,sp)
  for field in ('observed_at','expires_at'):
   with self.assertRaises(Refusal):derive_candidate_evidence(self.binding,c,dict(cp,**{field:'invalid'}),s,sp,att,now=self.now)
 def test_unbound_occurrence_refused(self):
  self.binding['occurrence']=None
  with self.assertRaisesRegex(Refusal,'source_occurrence_required'):self.derive()
 def test_malformed_observation_refused(self):
  for v in ([],{},'text'):
   with self.assertRaisesRegex(Refusal,'observation_kind'):self.derive(cat=v)
 def test_existing_candidate_free_row_remains_ineligible(self):
  from ai_movie_investigator.replay import synthetic_case
  from ai_movie_investigator.contracts import captured_outcome
  from ai_movie_investigator.new_case import projection, admitted
  raw,binding,evidence=synthetic_case(165)
  for r in evidence:r.update(observed_at=self.now-1,expires_at=self.now+60)
  evidence[0].update(candidate=None,claims=['title','year'])
  packet=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=binding,evidence=evidence,decisions=[],trusted_issuers=['synthetic_owner'])
  self.binding=binding;self.source['binding']=binding
  cat=encoded(self.cat);src=encoded(self.source);cp=self.pin(cat,'catalogue');sp=self.pin(src,'source')
  baseline=copy.deepcopy(packet)
  result=assemble_successor_packet(packet,cat,cp,src,sp,self.attestation(cp,sp),now=self.now)
  self.assertEqual(packet,baseline);self.assertEqual(result['evidence'][:-2],baseline['evidence'])
  self.assertIsNone(result['evidence'][0]['candidate']);self.assertEqual(result['evidence'][0]['claims'],['title','year'])
  rec=admitted(result,binding,self.now);projected,_=projection(result,rec,self.now)
  proposal=preflight_successor(packet,cat,cp,src,sp,self.attestation(cp,sp),now=self.now)
  self.assertNotIn('Synthetic retained',str(proposal['projection']))
  self.assertTrue(proposal['citation_eligibility']['catalogue']);self.assertTrue(proposal['citation_eligibility']['source'])
  good=dict(status='supported_candidate',citations=[dict(evidence_id=proposal['citation_eligibility']['catalogue'][0],claim='crosswalk'),dict(evidence_id=proposal['citation_eligibility']['source'][0],claim='source_identity')],alternatives=[])
  validate_attested_citations(good,proposal['projection'])
  bad_cites=copy.deepcopy(good);bad_cites['citations'][0]['evidence_id']='evidence-1'
  with self.assertRaisesRegex(Refusal,'attested_citations_required'):validate_attested_citations(bad_cites,proposal['projection'])
  self.assertEqual(proposal['citation_eligibility']['catalogue'],sorted(proposal['citation_eligibility']['catalogue']))
  self.assertEqual(proposal['citation_eligibility']['source'],sorted(proposal['citation_eligibility']['source']))
  self.assertNotIn('evidence-1',proposal['citation_eligibility']['catalogue'])
  bad=copy.deepcopy(packet);bad['facts']['imdb']='tt9000999'
  with self.assertRaisesRegex(Refusal,'conflicting_ids_require_review'):
   preflight_successor(bad,cat,cp,src,sp,self.attestation(cp,sp),now=self.now)
  self.assertIsNone(projected['evidence'][0]['candidate']);self.assertEqual(projected['evidence'][-2]['claims'],['crosswalk']);self.assertEqual(projected['evidence'][-1]['claims'],['source_identity'])
if __name__=='__main__':unittest.main()
