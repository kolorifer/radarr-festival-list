"""Invented dated same-listing evidence; no real source or provider access."""
import copy,hashlib,time,unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
import test_snapshot_review as fixture
import test_snapshot_first_weighing as first

def proof_for(record,local,old_pin):
 return dict(kind='same_listing_imdb_reobservation_v1',source='invented',external_id='fixture-42',historical_original=old_pin,current_original_sha256=record['attestation']['source_original_sha256'],old_asserted_imdb='tt7654321',historical_time_basis='evidence_present_by_outcome_time',historical_evidence_present_by=record['historical_at'],current_observed_at=record['current_at'],historical_release_sha256=hashlib.sha256(local['release_name'].encode()).hexdigest(),current_release_sha256=hashlib.sha256(local['release_name'].encode()).hexdigest(),historical_nfo_sha256=hashlib.sha256(local['nfo_text'].encode()).hexdigest(),current_nfo_sha256=hashlib.sha256(local['nfo_text'].encode()).hexdigest(),same_listing_reviewed=True,assertion_origin='listing_derived_imdb')

def material():
 snap,src,cat,att=fixture.fixture();snap=decode(snap,1048576);src=decode(src)
 case='outcome-'+digest(['invented','torrent',['external','fixture-42']])
 snap['cases'][0]['case_id']=snap['items'][0]['case_id']=src['case_id']=att['case_id']=case
 snap['cases'][0]['source_identity']=dict(imdb=None,tmdb=None,asserted_imdb='tt7654321',asserted_tmdb=None)
 snap['items'][0]['facts'].update(imdb='tt7654321',tmdb=None)
 snap=encoded(snap);src=encoded(src);att.update(snapshot_sha256=hashlib.sha256(snap).hexdigest(),source_sha256=hashlib.sha256(src).hexdigest())
 local=dict(release_name='Invented release',nfo_text='Invented NFO')
 proof=proof_for(dict(attestation=att,historical_at=fixture.NOW-20,current_at=fixture.NOW-10),local,dict(path='/invented/old.json',sha256='e'*64))
 return snap,src,cat,att,local,proof

class ReobservationTests(unittest.TestCase):
 def project(self,m):
  snap,src,cat,att,local,proof=m
  return s.projection(snap,att['snapshot_sha256'],att['case_id'],att['version'],src,cat,att,now=fixture.NOW,reobservation=proof,local_context=local)
 def test_narrow_current_pair_preserves_dated_contrary_evidence(self):
  p=self.project(material());self.assertTrue(p['conflicting_ids']);self.assertFalse(p['blocking_id_conflict']);self.assertEqual(p['source_identifiers']['asserted_imdb'],'tt7654321');self.assertEqual(p['citation_eligible_pair'],dict(imdb='tt1234567',tmdb=123))
  b=s.build_film_weighing(p,first=True);data=decode(b['request']['input'][0]['content'][0]['text'],32768)
  self.assertEqual(data['historical_observations']['dated_id_discrepancy']['old_asserted_imdb'],'tt7654321');self.assertTrue(data['historical_observations']['retained_id_conflict']);self.assertFalse(data['conflicting_ids']);d=data['historical_observations']['dated_id_discrepancy'];self.assertIsNone(d['historical_exact_fetch_at']);self.assertEqual(d['historical_evidence_present_by'],p['observed_at']);self.assertEqual(d['historical_time_basis'],'evidence_present_by_outcome_time');self.assertIn('exact historical listing fetch time is unknown',b['request']['instructions'])
  statuses=[v['properties']['status']['enum'][0] for v in b['request']['text']['format']['schema']['properties']['result']['anyOf']]
  self.assertIn('supported_candidate',statuses);self.assertIn('unresolved',statuses)
  with self.assertRaises(Refusal):s.build_film_weighing(p)
 def test_exact_discrepancy_identifiers_required_in_model_explanation(self):
  from test_snapshot_film_context import ContextTests
  from ai_movie_investigator.disclosure import aliases,evidence_alias
  f=ContextTests();f.setUp();p=self.project(material());b=s.build_film_weighing(p,first=True)
  answer=copy.deepcopy(f.answer);answer['binding_hash']=aliases(b['run'])
  for key,claim in (('source','source_identity'),('catalogue','crosswalk')):answer['result'][key+'_citation']=dict(evidence_id=evidence_alias(b['run'],key),claim=claim)
  answer['result']['rationale']='Earlier tt7654321 differs from later tt1234567; current cast agrees, but the earlier observation is unexplained.'
  self.assertEqual(s.validate_film_weighing(p,b,answer,now=fixture.NOW,first=True)['status'],'supported_candidate')
  for rationale in ('The current cast agrees.','Earlier tt7654321 remains uncertain.','Later tt1234567 has matching cast.','Earlier tt76543210 differs from later tt12345678.'):
   answer['result']['rationale']=rationale
   with self.subTest(rationale=rationale),self.assertRaisesRegex(Refusal,'snapshot_reobservation_explanation'):s.validate_film_weighing(p,b,answer,now=fixture.NOW,first=True)
 def test_missing_mismatched_or_current_conflicts_never_relaxed(self):
  changes=['direct_imdb','direct_tmdb','asserted_tmdb','current_conflict','title','cast','same_time','older','external','release','nfo','origin','old_hash','old_id','unknown_title','unknown_cast','none_title','blank_title','invented_exact_time']
  for change in changes:
   m=list(material());snap,src,cat,att,local,proof=m;sj=decode(snap,1048576);so=decode(src);ca=decode(cat)
   if change=='direct_imdb':sj['cases'][0]['source_identity']['imdb']='tt1234567'
   elif change=='direct_tmdb':sj['cases'][0]['source_identity']['tmdb']=123;sj['items'][0]['facts']['tmdb']=123
   elif change=='asserted_tmdb':sj['cases'][0]['source_identity']['asserted_tmdb']=456;sj['items'][0]['facts']['tmdb']=456
   elif change=='current_conflict':ca['imdb']='tt9999999'
   elif change=='title':so['title']='Another film'
   elif change=='cast':so['cast']=[]
   elif change in ('same_time','older'):proof['current_observed_at']=so['observed_at']=proof['historical_evidence_present_by']-(1 if change=='older' else 0)
   elif change=='external':proof['external_id']='different'
   elif change=='release':proof['historical_release_sha256']='f'*64
   elif change=='nfo':proof['historical_nfo_sha256']='f'*64
   elif change=='origin':proof['assertion_origin']='unknown'
   elif change=='old_hash':proof['historical_original']['sha256']=proof['current_original_sha256']
   elif change=='invented_exact_time':proof['historical_time_basis']='exact_listing_fetch_time'
   elif change=='unknown_title':so['title']=ca['title']='unknown'
   elif change=='none_title':so['title']=ca['title']=None
   elif change=='blank_title':so['title']=ca['title']=''
   elif change=='unknown_cast':so['cast']=ca['cast']=['unknown']
   elif change=='old_id':proof['old_asserted_imdb']='tt9999999'
   m[0]=encoded(sj);m[1]=encoded(so);m[2]=encoded(ca);att.update(snapshot_sha256=hashlib.sha256(m[0]).hexdigest(),source_sha256=hashlib.sha256(m[1]).hexdigest(),catalogue_sha256=hashlib.sha256(m[2]).hexdigest())
   with self.subTest(change=change),self.assertRaises(Refusal):self.project(m)
  m=list(material());m[-1]=None;p=self.project(m);self.assertTrue(p['conflicting_ids']);self.assertIsNone(p['citation_eligible_pair'])

class InstalledReobservationTests(unittest.TestCase):
 def setUp(self):
  self.base=first.FirstWeighingTests('test_scope_and_consumed_case_refuse');self.base.setUp();self.addCleanup(self.base.doCleanups)
  b=self.base;f=b.f;r=f.record
  sj=decode(Path(r['snapshot']['path']).read_bytes(),1048576);sj['cases'][0]['source_identity']=dict(imdb=None,tmdb=None,asserted_imdb='tt7654321',asserted_tmdb=None);sj['items'][0]['facts'].update(imdb='tt7654321',tmdb=None)
  r['snapshot']=f.pin('temporal-initial.json',encoded(sj));r['attestation']['snapshot_sha256']=r['snapshot']['sha256']
  b.prepare('outcome-'+digest(['invented','torrent',['external','fixture-42']]))
  r=f.record;local=decode(Path(r['local_context']['path']).read_bytes());old=f.pin('historical-source.json',b'{"imdb":"tt7654321","source":"invented"}')
  proof=proof_for(dict(attestation=r['attestation'],historical_at=b.p['observed_at'],current_at=b.p['listing']['observed_at']),local,old)
  r['first_assessment']['reobservation']=proof
  b.p=s.projection(Path(r['snapshot']['path']).read_bytes(),r['snapshot']['sha256'],r['attestation']['case_id'],r['attestation']['version'],Path(r['source']['path']).read_bytes(),Path(r['catalogue']['path']).read_bytes(),r['attestation'],now=time.time(),reobservation=proof,local_context=local)
  r['first_assessment']['request_sha256']=digest(s.build_film_weighing(b.p,first=True)['request'])
  scope=decode(Path(r['owner_scope']['path']).read_bytes());scope['reobservation_sha256']=digest(proof);r['owner_scope']=f.pin('temporal-owner.json',encoded(scope))
  mr=decode(Path(r['main_review']['path']).read_bytes());mr.update(owner_scope_sha256=r['owner_scope']['sha256'],first_assessment_sha256=digest(r['first_assessment']),same_listing_derivation_sha256=digest(proof),same_listing_derivation_reviewed=True);r['main_review']=f.pin('temporal-main.json',encoded(mr));b.save()
  prior=b.response
  def response(grant,**kw):
   v=decode(prior(grant,**kw),65536);a=decode(v['output'][-1]['content'][0]['text']);a['result']['rationale']='Earlier tt7654321 differs from later tt1234567 on the same listing; matched cast supports review, not approval.'
   if kw.get('unresolved'):a['result']['primary_blocker'].update(reason='ambiguous_film_evidence',material_conflict='The earlier listing assertion remains unexplained despite current corroboration.')
   v['output'][-1]['content'][0]['text']=encoded(a).decode();return encoded(v)
  b.response=response
 def test_derivation_and_owner_pins_fail_before_reservation(self):
  from ai_movie_investigator import snapshot_authorization as gate
  b=self.base;f=b.f;original=copy.deepcopy(f.record)
  for key,delta in (('main_review',dict(same_listing_derivation_reviewed=False)),('main_review',dict(same_listing_derivation_sha256='f'*64)),('owner_scope',dict(reobservation_sha256='f'*64))):
   f.record=copy.deepcopy(original);obj=decode(Path(f.record[key]['path']).read_bytes());obj.update(delta);f.record[key]=f.pin('bad-temporal-'+str(time.monotonic_ns())+'.json',encoded(obj));b.save()
   with self.subTest(delta=delta),self.assertRaises(Refusal),f.gate():gate.authorize(f.state,f.f.selected)
   self.assertEqual(b.credit.read(),b.credit_rows);self.assertFalse((f.state/'attempt-16').exists())
  f.record=original;b.save();old=Path(original['first_assessment']['reobservation']['historical_original']['path']);raw=old.read_bytes()
  try:
   old.write_bytes(b'changed invented original')
   with self.assertRaises(Refusal),f.gate():pass
  finally:old.write_bytes(raw)
 def run_case(self,unresolved):
  self.base.installed(unresolved)
  html=(self.base.f.output/'movie-review.html').read_text();self.assertIn('Dated same-listing ID discrepancy',html);self.assertIn('tt7654321',html);self.assertIn('tt1234567',html);self.assertIn('Source correction intent',html);self.assertIn('Historical evidence present by outcome time',html);self.assertIn('Exact historical listing fetch time',html);self.assertIn('Unknown',html)
 def test_supported(self):self.run_case(False)
 def test_unresolved(self):self.run_case(True)
