"""Invented Harbor Lantern contract checks; no model-quality or live claims."""
import copy,hashlib,unittest
from unittest.mock import patch
from ai_movie_investigator.contracts import encoded,decode,digest,Refusal
from ai_movie_investigator.responses_protocol import schema_value
from automation import seedbox_automated_review as r
from test_snapshot_assessment import AssessmentTests


def fixture():
 f=AssessmentTests();f.setUp();p=copy.deepcopy(f.p);p['host_reporting_revision']=2
 p['title']='Harbor Lantern';p['year']=1987;p['listing'].update(title='Harbor Lantern',year=1987,cast=['Invented Actor'])
 p['catalogue'].update(title='Harbor Lantern',theatrical_year=1988,festival_years=[],cast=['Invented Actor'])
 report=dict(result=dict(status='unresolved',candidate=None,rationale='The listing says Harbor Lantern (1987), while the catalogue says Harbor Lantern (1988). Matching identifiers and Invented Actor support correspondence, but the year discrepancy remains unresolved.',uncertainty='Identity remains unresolved; physical edition and acquisition suitability are unknown.',film_blockers=[dict(aspect='year',reason='ambiguous_film_evidence',support_considered='The identifiers and cast agree.',material_conflict='The listing year is 1987 and catalogue theatrical year is 1988.')]))
 card=dict(report_sha256=digest(report),case_id=p['case_id'],candidate=None,text='Harbor Lantern: identity unresolved. Listing year 1987; catalogue theatrical year 1988. The IMDb and cast agree. Physical edition remains unknown. No identity reuse or download is approved.',source_url='https://example.invalid/private-listing',target_sha256='a'*64)
 return report,p,card

def reply(bindings):
 return dict(bindings,verdict='approve',reason='The unresolved card faithfully reports both dated year observations, matching identifiers and cast without approving identity.',evidence_findings=['The listing says 1987 and catalogue theatrical year says 1988; the card reports both.'],material_problems=[],source_uncertainties=['The release-year discrepancy and physical edition remain unresolved.'])

def defect(request,kind='omitted_conflict',location='proposed_card'):
 c=decode(request['input'][0]['content'][0]['text'],65536)['reporting_contract']
 def ref(field,values):return dict(field=field,value_sha256=values[field])
 suffixes=('.imdb','.tmdb') if kind=='unsupported_candidate' else ('.cast',) if kind=='unsupported_blocker' else ('.year','.theatrical_year')
 years=[key for key in c['observation_fields'] if key.endswith(suffixes)]
 return dict(kind=kind,location=ref(location,c['report_fields']),evidence=[ref(k,c['observation_fields']) for k in years],explanation='The proposed card omits the disclosed difference between listing year 1987 and catalogue theatrical year 1988.')

class ContractTests(unittest.TestCase):
 def setUp(self):self.report,self.p,self.card=fixture();self.request,self.bindings=r.build(self.report,self.p,self.card,revision=3)
 def check(self,answer):
  schema_value(answer,self.request['text']['format']['schema'])
  return r.retained_reporting_answer(answer,self.bindings,self.request)
 def test_truthful_unresolved_approval_keeps_source_uncertainty(self):
  a=reply(self.bindings);retained,handling,predicates=self.check(a)
  self.assertEqual(retained,a);self.assertFalse(handling);self.assertFalse(predicates)
  self.assertIn('not unresolved source identity',self.request['instructions']);self.assertNotIn(self.card['source_url'],encoded(self.request).decode())
 def test_demonstrated_legacy_gap_and_v3_no_defect_rejection(self):
  _,old=r.build(self.report,self.p,self.card,revision=2)
  a=dict(old,verdict='reject',reason='Identity remains unresolved.',evidence_findings=['The listing year is 1987 and catalogue year is 1988.'],material_problems=['The year discrepancy is unresolved.'])
  self.assertEqual(r.retained_answer(a,old)[2],[])
  new=reply(self.bindings);new['verdict']='reject'
  self.assertIn('review_rejection_without_defect',self.check(new)[2]);self.assertEqual(new['verdict'],'reject')
 def test_real_reporting_defects_can_reject_without_identity_approval(self):
  for kind,location in (('unsupported_candidate','assessment.rationale'),('unsupported_blocker','assessment.film_blockers'),('omitted_conflict','proposed_card')):
   report,p,card=fixture()
   if kind=='unsupported_candidate':
    report['result'].update(status='supported_candidate',candidate=dict(imdb='tt7654321',tmdb=999),rationale='A different unobserved IMDb and catalogue ID is verified without supporting evidence.')
    card.update(candidate=report['result']['candidate'],text='Verified Harbor Lantern, IMDb tt7654321 and TMDb 999.')
   elif kind=='unsupported_blocker':
    report['result']['film_blockers'][0]['material_conflict']='The matching cast is proof against the film identity.'
    card['text']='Harbor Lantern is unresolved because matching cast proves a different film.'
   else:card['text']='Harbor Lantern is unresolved. Its release year is undisputed. The IDs and cast agree.'
   card['report_sha256']=digest(report);request,bindings=r.build(report,p,card,revision=3)
   a=reply(bindings);a.update(verdict='reject',material_problems=[defect(request,kind,location)])
   a['material_problems'][0]['explanation']={'unsupported_candidate':'The proposed identity IDs do not occur in the disclosed supporting observations.','unsupported_blocker':'Matching cast is reported as contrary evidence without a supporting observation.','omitted_conflict':'The card declares the year undisputed while the listing and catalogue disagree.'}[kind]
   schema_value(a,request['text']['format']['schema'])
   self.assertEqual(r.retained_reporting_answer(a,bindings,request)[2],[])
  # Invented answers establish contract expressibility, not model quality.
 def test_approval_with_defect_refuses_and_never_converts_verdict(self):
  a=reply(self.bindings);a['material_problems']=[defect(self.request)]
  self.assertIn('review_approval_conflicted',self.check(a)[2])
 def test_unknown_hidden_wrong_or_duplicate_references_refuse(self):
  a=reply(self.bindings);a.update(verdict='reject',material_problems=[defect(self.request)])
  for mode in ('hidden','hash','duplicate','kind'):
   bad=copy.deepcopy(a);d=bad['material_problems'][0]
   if mode=='hidden':d['location']['field']='private_source_url'
   elif mode=='hash':d['location']['value_sha256']='f'*64
   elif mode=='duplicate':d['evidence'].append(d['evidence'][0])
   else:d['kind']='source_identity_unresolved'
   with self.subTest(mode=mode),self.assertRaises(Refusal):r.retained_reporting_answer(bad,self.bindings,self.request)
 def test_binding_mismatch_and_unsafe_new_prose(self):
  a=reply(self.bindings);a['card_sha256']='f'*64
  self.assertIn('review_binding_changed',r.retained_reporting_answer(a,self.bindings,self.request)[2])
  a=reply(self.bindings);a['source_uncertainties']=['https://private.invalid/SECRET']
  kept,handling,predicates=r.retained_reporting_answer(a,self.bindings,self.request)
  self.assertIn('review_uncertainty_unsafe',predicates);self.assertNotIn(b'SECRET',encoded(kept));self.assertTrue(handling)
 def test_null_missing_observations_remain_addressable(self):
  packet=decode(self.request['input'][0]['content'][0]['text'],65536);fields=packet['reporting_contract']['observation_fields']
  self.assertTrue(any(v==digest(None) or v==digest([]) for v in fields.values()))
 def test_legacy_request_hashes_stay_frozen(self):
  # Generated independently from accepted PR213 before changing this contract.
  expected=LEGACY_HASHES
  for revision in (1,2):self.assertEqual(digest(r.build(self.report,self.p,self.card,revision=revision)[0]),expected[revision])

LEGACY_HASHES={1: '88250e86d8c3d0cb399841a4fd4da59ddb43b8da9422752ed2cdea520e64ac3d', 2: '0065ad04ac6ad7ab5f7536df047c3397a7aba54894aa3335e13313a67c08b3cb'}



from test_seedbox_connected import ConnectedTests
from test_snapshot_review import NOW
from test_responses_compatibility import documented
from ai_movie_investigator.responses_http import ExplicitCredential
from ai_movie_investigator import snapshot_review
import test_supervised_envelope as framing

class WireTests(ConnectedTests):
 SOURCE_REVISION=2
 SOURCE_HTML=b'<h2 id="torrentnameid">Invented release</h2><input name="imdbID" value="tt1234567"><div class="torrent-info-details"><h3>Harbor Lantern (1987)</h3><div class="torrent-extra-info"><p>Cast: Invented Actor</p><p>Director: Invented Director</p><p>Runtime: 95 min</p></div></div>'
 CATALOGUE_RAW=encoded(dict(id=123,imdb_id='tt1234567',title='Harbor Lantern',runtime=95,credits=dict(cast=[dict(name='Invented Actor',order=0)],crew=[dict(name='Invented Director',job='Director')]),release_dates=dict(results=[dict(release_dates=[dict(type=3,release_date='1988-01-01T00:00:00Z')])])) )
 def wire(self):
  built=snapshot_review.build_film_prose(self.p);answer=self.f.answer_for(self.p,True)
  answer['result']['rationale']='Harbor Lantern has matching IMDb and cast observations; listing year 1987 and theatrical year 1988 remain unresolved.'
  if getattr(self,'misleading',False):answer['result']['rationale']='The physical edition is verified and the release is approved for acquisition.'
  answer['result']['primary_blocker'].update(aspect='year',reason='ambiguous_film_evidence',support_considered='The listing and catalogue IMDb and cast agree.',material_conflict='The listing year is 1987; the catalogue theatrical year is 1988.')
  response=documented();response.update(model=built['request']['model'],instructions=built['request']['instructions'],text=built['request']['text'],max_output_tokens=25000);response['output'][-1]['content'][0]['text']=encoded(answer).decode();return encoded(response)
 def prepare_review(self):
  with patch('time.time',return_value=NOW),framing.wire(self.wire()):self.execute()
  with patch('time.time',return_value=NOW):report,e,card=r.assessment(self.q,self.selected['reservation'],card_revision=2)
  request,bindings=r.build(report,e['projection'],card,revision=3)
  return request,bindings
 def run_review(self,request,answer):
  response=documented();response.update(model=request['model'],instructions=request['instructions'],text=request['text'],max_output_tokens=25000);response['output'][-1]['content'][0]['text']=encoded(answer).decode()
  with patch('time.time',return_value=NOW),patch('automation.seedbox_evidence.verify_current'),framing.wire(encoded(response)):
   return r.execute(self.q,self.selected['reservation'],policy=self.policy,credential=ExplicitCredential('sk-INVENTED'),request_revision=3)
 def test_wire_truthful_unresolved_and_reconstruction_preserve_report(self):
  request,bindings=self.prepare_review();html=self.path/('report-'+self.selected['reservation']+'.html');before=html.read_bytes()
  record=self.run_review(request,reply(bindings));self.assertEqual(record['review_request_revision'],3)
  with patch('time.time',return_value=NOW):plan,_=r.approved_plan(self.q,self.selected['reservation'])
  self.assertIsNone(plan['candidate']);self.assertFalse(plan['production_approved']);self.assertFalse(plan['download_approved']);self.assertEqual(html.read_bytes(),before)
  with self.q.locked() as (rows,_):self.assertEqual(sum(x['type']=='seedbox_provider_started_v1' for x in rows),2)
  with self.assertRaises(Refusal):self.run_review(request,reply(bindings))
 def test_wire_valid_rejection_stays_rejected_without_regeneration(self):
  self.misleading=True;request,bindings=self.prepare_review();answer=reply(bindings)
  d=defect(request,'misleading_confidence','assessment.rationale');d['explanation']='The rationale declares the physical edition verified and acquisition approved, beyond the disclosed film observations.'
  answer.update(verdict='reject',reason='The assessment makes unsupported edition and acquisition claims.',material_problems=[d])
  record=self.run_review(request,answer);self.assertEqual(record['answer'],answer)
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(Refusal,'review_not_approved'):r.approved_plan(self.q,self.selected['reservation'])
  with self.q.locked() as (rows,_):before=copy.deepcopy(rows)
  with self.assertRaises(Refusal):self.run_review(request,answer)
  with self.q.locked() as (rows,_):self.assertEqual(rows,before);self.assertFalse(any(x['type']=='seedbox_sender_started_v1' for x in rows))
 def test_wire_wrong_reference_is_consumed_without_retry_or_send(self):
  request,bindings=self.prepare_review();answer=reply(bindings);d=defect(request)
  fields=decode(request['input'][0]['content'][0]['text'],65536)['reporting_contract']['report_fields']
  d['location']['value_sha256']=next(value for value in fields.values() if value!=d['location']['value_sha256'])
  answer.update(verdict='reject',material_problems=[d])
  with self.assertRaisesRegex(Refusal,'host_review_uncertain_or_refused'):self.run_review(request,answer)
  with self.q.locked() as (rows,_):
   before=copy.deepcopy(rows);self.assertEqual(rows[-1]['diagnostic']['reason'],'review_reference_changed')
   self.assertFalse(any(x['type'] in ('seedbox_sender_started_v1','seedbox_automated_review_completed_v1') for x in rows))
  with self.assertRaises(Refusal):self.run_review(request,answer)
  with self.q.locked() as (rows,_):self.assertEqual(rows,before)
 def test_legacy_completed_review_remains_byte_exact(self):
  self.complete();prep=self.selected['reservation']
  with self.q.locked() as (rows,_):before=copy.deepcopy(rows);record=next(x for x in rows if x['type']=='seedbox_automated_review_completed_v1')
  self.assertEqual(record['review_request_revision'],2)
  with patch('time.time',return_value=NOW):r.approved_plan(self.q,prep)
  with self.q.locked() as (rows,_):self.assertEqual(rows,before)
 def test_installed_contract_nonempty_success_and_wrong_reference(self):
  from pathlib import Path
  import subprocess,sys,tempfile,json
  from automation.seedbox_package import build
  request,bindings=self.prepare_review();answer=reply(bindings);answer.update(verdict='reject',material_problems=[defect(request)])
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
   root=Path(temp).resolve();root.chmod(0o700);build(Path.cwd(),root)
   packet=root/'invented.json';packet.write_bytes(encoded(dict(request=request,bindings=bindings,answer=answer)))
   code="""
import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from automation.seedbox_automated_review import retained_reporting_answer
assert Path(sys.modules[retained_reporting_answer.__module__].__file__).is_relative_to(Path(sys.argv[1]))
v=json.loads(Path(sys.argv[2]).read_bytes());assert retained_reporting_answer(v['answer'],v['bindings'],v['request'])[2]==[]
v['answer']['material_problems'][0]['location']['value_sha256']='f'*64
try:retained_reporting_answer(v['answer'],v['bindings'],v['request'])
except ValueError:pass
else:raise AssertionError('wrong reference accepted')
print('installed reporting contract and refusal verified')
"""
   done=subprocess.run([sys.executable,'-I','-B','-c',code,str(root),str(packet)],capture_output=True,text=True,timeout=30)
   self.assertEqual(done.returncode,0,done.stderr);self.assertIn('contract and refusal verified',done.stdout)

def load_tests(loader,tests,pattern):
 return unittest.TestSuite(cls(name) for cls in (ContractTests,WireTests) for name in cls.__dict__ if name.startswith('test_'))
