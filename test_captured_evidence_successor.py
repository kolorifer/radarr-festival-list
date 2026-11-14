"""Invented captured failure, material successor and local report; no real I/O."""
import copy, hashlib, io, time, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a
from ai_movie_investigator.contracts import encoded,digest,Refusal
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.captured_evidence_preflight import preflight_successor
from ai_movie_investigator.captured_private_report import render_private_report
import test_captured_activation as activation
import test_captured_generation as generation
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class EvidenceSuccessor(unittest.TestCase):
 def setUp(self):
  original=generation.captured_outcome
  def candidate_free(*args,**kwargs):
   packet=original(*args,**kwargs);packet['evidence'][0].update(candidate=None,claims=['title','year']);return packet
  with patch.object(generation,'captured_outcome',candidate_free):
   self.x=activation.Activation('test_exact_context_receipt_report_and_reset_without_gate_patch');self.x.setUp()
  self.addCleanup(self.x.doCleanups);self.f=self.x.f
 def old_failure(self):
  answer=copy.deepcopy(self.f.reply);answer['result']['citations'][0]['claim']='title'
  with self.x.context(),a._simulated_captured_io():
   self.f.authorize()
   with self.assertRaisesRegex(Refusal,'unsupported_candidate'):self.f.run_case(self.f.response(answer))
  self.oldroot=(self.f.f.state/FILENAME).read_bytes();self.oldcase=(self.f.case.directory/FILENAME).read_bytes()
  self.oldcredit=(self.f.f.state/'credit'/FILENAME).read_bytes();self.oldattempt=(self.f.f.state/'attempt-7'/FILENAME).read_bytes()
 def prepare_successor(self, *, deferred=False):
  now=time.time();binding=self.f.packet['binding']
  cat=encoded(dict(kind='catalogue_external_ids',imdb='tt9000127',tmdb=9000127))
  source=encoded(dict(kind='source_release_identity',binding=binding,asserted_imdb='tt9000127'))
  def pin_meta(raw,origin):return dict(sha256=hashlib.sha256(raw).hexdigest(),origin=origin,observed_at=now-1,expires_at=now+90)
  cp=pin_meta(cat,'catalogue_fixture');sp=pin_meta(source,'source_fixture')
  self.local_context=dict(tracker_url='https://example.invalid/item',release_name='Invented release',nfo='Invented NFO',provenance='Invented independently reviewed artifacts',source_facts=dict(title='Synthetic Harbor',year=2026,runtime=None,cast=None,edition=None,imdb='tt9000127',tmdb=None),catalogue_facts=dict(title='Synthetic Harbor',year=2026,runtime=110,cast=None,imdb='tt9000127',tmdb=9000127))
  att=dict(kind='main_reviewed_source_derivation_v1',binding=binding,catalogue_sha256=cp['sha256'],source_sha256=sp['sha256'],catalogue_pin_sha256=digest(cp),source_pin_sha256=digest(sp),catalogue_original_sha256=hashlib.sha256(cat).hexdigest(),source_original_sha256=hashlib.sha256(source).hexdigest(),local_context_sha256=digest(self.local_context),source_occurrence_verified=True,provenance_reviewed=True,attested_at=now,expires_at=now+100)
  proposal=preflight_successor(self.f.packet,cat,cp,source,sp,att,now=now)
  self.packet=proposal['packet'];self.eligible=proposal['citation_eligibility'];self.catraw=cat;self.sourceraw=source;self.attestation=att;self.catpin=cp;self.sourcepin=sp
  if deferred:return
  self.request=n.prepare(self.f.case,self.packet,binding,minimized_evidence=True)
  self.f.request=self.request;self.f.body=n.captured_request(self.request)
  with self.f.root.transaction(write=True) as (root,_):
   with self.f.case.transaction(write=True) as (case,_):
    self.consent=n.captured_consent(self.f.root,root,self.f.case,case,digest(self.request),self.f.selected.data)
  self.f.path=self.x.root/'enriched-authority.json';self.f.path.write_bytes(encoded(self.consent));self.f.path.chmod(0o600)
  def artifact(name,raw):
   p=self.x.root/(name+'.json');p.write_bytes(raw);p.chmod(0o600);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest())
  self.x.record['authority']=dict(path=str(self.f.path),sha256=digest(self.consent))
  self.x.record['evidence_artifacts']=dict(attestation=artifact('attestation',encoded(att)),catalogue=artifact('cat',cat),source=artifact('source',source),catalogue_original=artifact('cat-original',cat),source_original=artifact('source-original',source))
  self.x.write_record();self.catpin=cp;self.sourcepin=sp
 def test_material_successor_receipt_report_and_no_repeat(self):
  self.old_failure();self.prepare_successor();response=copy.deepcopy(self.f.reply)
  response['binding_hash']=self.request['binding_hash'];response['result']['citations']=[dict(evidence_id=self.eligible['catalogue'][0],claim='crosswalk'),dict(evidence_id=self.eligible['source'][0],claim='source_identity')]
  self.assertNotIn('Synthetic retained',str(self.request['input']))
  from ai_movie_investigator.contracts import decode
  wire=decode(n.captured_request(self.request),65536);schema=wire['text']['format']['schema']['properties']['result']['properties']
  self.assertEqual(schema['alternatives']['maxItems'],0);self.assertEqual(schema['citations']['maxItems'],2)
  self.assertIn('cite exactly the two eligible aliases',wire['instructions']);self.assertIn('do not force a positive result',wire['instructions'])
  self.assertIn('Physical edition',wire['instructions'])
  with self.x.context(),a._simulated_captured_io():
   self.assertEqual(n.authorize_captured(self.f.f.state,self.f.selected,self.f.case.directory,digest(self.request),self.f.path,digest(self.consent))['slot'],8)
   with diagnostics.DiagnosticTests().inputs(),framing.wire(self.f.response(response)),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.f.state,self.f.selected,8,captured=True)['status'],'completed')
   with self.assertRaises(Refusal):c.run(self.f.f.state,self.f.selected,8,captured=True)
  for p,b in ((self.f.f.state/FILENAME,self.oldroot),(self.f.case.directory/FILENAME,self.oldcase),(self.f.f.state/'credit'/FILENAME,self.oldcredit)):
   self.assertTrue(p.read_bytes().startswith(b))
  self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),self.oldattempt)
  report=self.f.case.read()[-1]['report'];root=self.f.root.read()[-1]
  self.assertEqual(report['retained_reply_hash'],digest(root['answer']));self.assertFalse(report['draft']['sent'])
  ctx=dict(tracker_url='https://example.invalid/item',release_name='Invented release',nfo='Invented NFO',provenance='Invented independently reviewed artifacts',prior_failure='unsupported_candidate',job=report['job'],binding=report['binding'],report_sha256=digest(report),source_evidence_sha256=self.sourcepin['sha256'],catalogue_evidence_sha256=self.catpin['sha256'],source_facts=dict(title='Synthetic Harbor',year=2026,runtime=None,cast=None,edition=None,imdb='tt9000127',tmdb=None),catalogue_facts=dict(title='Synthetic Harbor',year=2026,runtime=110,cast=None,imdb='tt9000127',tmdb=9000127))
  html=render_private_report(report,digest(report),ctx,digest(ctx),self.packet)
  self.assertIn('supported candidate',html);self.assertIn('Open the original source',html);self.assertIn('Catalogue external-ID mapping',html);self.assertIn('Source assertion',html);self.assertIn('evidence-binding failure',html);self.assertIn('Physical edition remains unverified',html)
 def test_swapped_source_refuses_before_new_attempt_or_credit(self):
  self.old_failure();self.prepare_successor()
  root_before=(self.f.f.state/FILENAME).read_bytes();credit_before=(self.f.f.state/'credit'/FILENAME).read_bytes()
  path=Path(self.x.record['evidence_artifacts']['source']['path']);path.write_bytes(b'{}')
  with self.assertRaisesRegex(Refusal,'captured_activation_artifact'):
   with self.x.context():pass
  self.assertEqual((self.f.f.state/FILENAME).read_bytes(),root_before)
  self.assertEqual((self.f.f.state/'credit'/FILENAME).read_bytes(),credit_before)
  self.assertFalse((self.f.f.state/'attempt-8').exists())

 def test_changed_prior_terminal_refuses_before_new_attempt(self):
  original=c.safe_diagnostic
  def changed(error):return dict(original(error),reason='unsupported_claim')
  with patch.object(c,'safe_diagnostic',changed):self.old_failure()
  root_before=(self.f.f.state/FILENAME).read_bytes();credit_before=(self.f.f.state/'credit'/FILENAME).read_bytes()
  with self.assertRaisesRegex(Refusal,'evidence_prior_invalid'):self.prepare_successor()
  self.assertEqual((self.f.f.state/FILENAME).read_bytes(),root_before)
  self.assertEqual((self.f.f.state/'credit'/FILENAME).read_bytes(),credit_before)
  self.assertFalse((self.f.f.state/'attempt-8').exists())

 def test_unresolved_result_remains_meaningful_unsent_report(self):
  self.old_failure();self.prepare_successor();response=copy.deepcopy(self.f.reply)
  response['binding_hash']=self.request['binding_hash'];response['result'].update(status='unresolved',candidate=None,citations=[],alternatives=[],rationale='Evidence remains insufficient.',uncertainty='Physical edition is unknown.')
  with self.x.context(),a._simulated_captured_io():
   n.authorize_captured(self.f.f.state,self.f.selected,self.f.case.directory,digest(self.request),self.f.path,digest(self.consent))
   with diagnostics.DiagnosticTests().inputs(),framing.wire(self.f.response(response)),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.f.state,self.f.selected,8,captured=True)['status'],'completed')
  report=self.f.case.read()[-1]['report'];self.assertEqual(report['assessment']['status'],'unresolved');self.assertFalse(report['draft']['sent'])
  self.assertIn('Evidence remains insufficient',report['draft']['text'])

 def test_installed_cli_creates_accepted_private_html_once(self):
  import json,os,subprocess,sys
  from ai_movie_investigator.installation import install_runtime
  self.old_failure();self.prepare_successor(deferred=True)
  runtime=self.x.root/'installed-evidence';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_bytes());self.assertGreater(len(manifest),0)
  self.x.record['runtime_manifest_sha256']=digest(manifest)
  def pin(name,raw):
   p=self.x.root/(name+'.json');p.write_bytes(raw);p.chmod(0o600);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest())
  artifacts=dict(attestation=pin('attest-install',encoded(self.attestation)),catalogue=pin('cat-install',self.catraw),source=pin('src-install',self.sourceraw),catalogue_original=pin('cat-orig-install',self.catraw),source_original=pin('src-orig-install',self.sourceraw))
  self.x.record['evidence_artifacts']=artifacts
  activation_path=self.x.root/'installed-activation.json';authority_path=self.x.root/'installed-authority.json';report_path=self.x.root/'private-report.html'
  code='''import sys,atexit,ctypes,os,json,hashlib,runpy
from pathlib import Path
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen' or (event=='ctypes.dlopen' and args[0] not in (None,'/usr/lib/libSystem.B.dylib')):
  attempts.append(event);raise AssertionError('external IO')
sys.addaudithook(audit)
@atexit.register
def done():print('TRIPWIRE='+str(len(attempts)))
'''
  code+='sys.path.insert(0,'+repr(str(runtime))+')\n'
  code+='''from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a,keychain_credential as k
from ai_movie_investigator.contracts import encoded,decode,digest
from ai_movie_investigator.history import History
from ai_movie_investigator.captured_private_report import render_private_report
c.read_private=lambda p,limit:Path(p).read_bytes()
native=[]
def invented_key(project):native.append(1);return b'sk-DUMMY_CAPTURED'
k._native=invented_key
'''
  code+='packet='+repr(self.packet)+'\nstate='+repr(str(self.f.f.state))+'\ncase='+repr(str(self.f.case.directory))+'\n'
  code+='selected=c.read_evidence('+repr(str(self.f.selected.path))+')\n'
  code+='request=n.prepare(History(Path(case)),packet,packet["binding"],minimized_evidence=True)\n'
  code+='root=History(Path(state));history=History(Path(case))\nwith root.transaction(write=True) as (events,_):\n with history.transaction(write=True) as (rows,_):consent=n.captured_consent(root,events,history,rows,digest(request),selected.data)\n'
  code+='authority=Path('+repr(str(authority_path))+');authority.write_bytes(encoded(consent));authority.chmod(0o600)\n'
  code+='record='+repr(self.x.record)+'\nrecord["authority"]={"path":str(authority),"sha256":digest(consent)}\n'
  code+='activation=Path('+repr(str(activation_path))+');activation.write_bytes(encoded(record));activation.chmod(0o600)\n'
  code+='response=decode('+repr(self.f.response())+',65536);body=decode(n.captured_request(request),65536)\n'
  code+='reply='+repr(self.f.reply)+'\nreply["binding_hash"]=request["binding_hash"];eligible=request["input"]["citation_eligibility"];reply["result"]["citations"]=[{"evidence_id":eligible["catalogue"][0],"claim":"crosswalk"},{"evidence_id":eligible["source"][0],"claim":"source_identity"}]\n'
  code+='response["instructions"]=body["instructions"];response["text"]=body["text"];response["max_output_tokens"]=body["max_output_tokens"];response["output"][-1]["content"][0]["text"]=encoded(reply).decode();selected_raw=encoded(response)\nframing="chunked"\n'+framing.wire_code()
  code+='\nwith n.approved_captured_wrapper(str(activation),digest(record)),a._simulated_captured_io(),wire_fixture("completed"):\n'
  code+=' granted=n.authorize_captured(state,selected,case,digest(request),authority,digest(consent));assert granted["slot"]==8\n'
  code+=' for attempt in range(2):\n  sys.argv='+repr(['ai_movie_investigator.supervised_credit','--state',str(self.f.f.state),'run-captured-keychain','--evidence',str(self.f.selected.path),'--slot','8'])+'\n'
  code+='''  try:runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)
  except SystemExit as e:assert e.code==(0 if attempt==0 else 1)
 assert len(native)==1
'''
  code+='report=History(Path(case)).read()[-1]["report"];completed=History(Path(state)).read()[-1];assert completed["captured_report"]==report and digest(completed["answer"])==report["retained_reply_hash"]\n'
  code+='context='+repr(dict(tracker_url='https://example.invalid/item',release_name='Invented release',nfo='Invented NFO',provenance='Invented reviewed observations',prior_failure='unsupported_candidate',job='',binding=self.packet['binding'],report_sha256='',source_evidence_sha256=self.sourcepin['sha256'],catalogue_evidence_sha256=self.catpin['sha256'],source_facts=dict(title='Synthetic Harbor',year=2026,runtime=None,cast=None,edition=None,imdb='tt9000127',tmdb=None),catalogue_facts=dict(title='Synthetic Harbor',year=2026,runtime=110,cast=None,imdb='tt9000127',tmdb=9000127)))+'\n'
  code+='context["job"]=report["job"];context["report_sha256"]=digest(report);html=render_private_report(report,digest(report),context,digest(context),packet)\n'
  code+='fd=os.open('+repr(str(report_path))+',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.write(fd,html.encode());os.close(fd);print("ONE_INVENTED_SEND_AND_REPORT")\n'
  script=self.x.root/'installed-evidence-test.py';script.write_text(code)
  result=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=runtime,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=50)
  output=result.stdout+result.stderr;self.assertEqual(result.returncode,0,output)
  self.assertIn(b'TRIPWIRE=0',output);self.assertIn(b'ONE_INVENTED_SEND_AND_REPORT',output);self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
  self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),self.oldattempt)
  self.assertEqual(report_path.stat().st_mode&0o777,0o600);self.assertIn('supported candidate',report_path.read_text())

if __name__=='__main__':unittest.main()
