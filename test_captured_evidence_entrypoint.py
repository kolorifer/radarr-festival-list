"""Exact unissued entrypoint, invented audit inputs and fake native/HTTP I/O."""
import copy,hashlib,json,os,subprocess,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a
from ai_movie_investigator.contracts import encoded,digest,Refusal,VERIFIED_IDENTITY_CHECK
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.installation import install_runtime
from ai_movie_investigator.captured_evidence_preflight import preflight_successor
import test_verified_identity_check as audit
import test_supervised_envelope as framing

class Entrypoint(unittest.TestCase):
 def setUp(self):
  original=audit.synthetic_case
  def candidate_free(*args):
   raw,b,rows=original(*args);rows[0].update(candidate=None,claims=['title','year']);return raw,b,rows
  with patch.object(audit,'synthetic_case',candidate_free):
   self.audit=audit.ConnectedAudit('test_native_capture_to_bound_response_and_private_report');self.audit.setUp()
  self.addCleanup(self.audit.doCleanups);self.x=self.audit.a;self.f=self.x.f
  answer=copy.deepcopy(self.f.reply);answer['result']['citations'][0]['claim']='title'
  with self.x.context(),a._simulated_captured_io():
   self.f.authorize()
   with self.assertRaisesRegex(Refusal,'unsupported_candidate'):self.f.run_case(self.f.response(answer))
  self.root=self.x.root;self.runtime=self.root/'entry-runtime';self.runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,self.runtime)
  self.manifest=json.loads((self.runtime/'runtime-files.json').read_bytes())
 def pin(self,name,raw):
  p=self.root/name;p.write_bytes(raw);p.chmod(0o600);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest())
 def invoke(self,*,cleanup_failure=False,mode=None):
  now=time.time();binding=self.f.packet['binding'];cat=encoded(dict(kind='catalogue_external_ids',imdb='tt9000127',tmdb=9000127));source=encoded(dict(kind='source_release_identity',binding=binding,asserted_imdb='tt9000127'))
  def meta(raw,origin):return dict(sha256=hashlib.sha256(raw).hexdigest(),origin=origin,observed_at=now-1,expires_at=now+60)
  cp=meta(cat,'catalogue_fixture');sp=meta(source,'source_fixture')
  prepared=now
  if mode=='expired':
   prepared=now-2;cp.update(observed_at=now-4,expires_at=now-1);sp.update(observed_at=now-4,expires_at=now-1)
  local=dict(tracker_url='https://example.invalid/source',release_name='Invented release',nfo='Invented NFO',provenance='Invented reviewed artifacts',source_facts=dict(title='Synthetic Harbor',year=2026,runtime=None,cast=['Actor One'],edition=None,imdb='tt9000127',tmdb=None),catalogue_facts=dict(title='Synthetic Harbor',year=2026,runtime=110,cast=['Actor One','Actor Two'],imdb='tt9000127',tmdb=9000127))
  if mode=='invalid_context':local['tracker_url']='javascript:bad'
  att=dict(kind='main_reviewed_source_derivation_v1',binding=binding,catalogue_sha256=cp['sha256'],source_sha256=sp['sha256'],catalogue_pin_sha256=digest(cp),source_pin_sha256=digest(sp),catalogue_original_sha256=hashlib.sha256(cat).hexdigest(),source_original_sha256=hashlib.sha256(source).hexdigest(),local_context_sha256=digest(local),source_occurrence_verified=True,provenance_reviewed=True,attested_at=now-3 if mode=='expired' else now,expires_at=now-1 if mode=='expired' else now+90)
  group=dict(attestation=self.pin('attest.json',encoded(att)),catalogue=self.pin('catalogue.json',cat),source=self.pin('source.json',source),catalogue_original=self.pin('catalogue-original.json',cat),source_original=self.pin('source-original.json',source))
  proposal=preflight_successor(self.f.packet,cat,cp,source,sp,att,now=prepared,purpose=VERIFIED_IDENTITY_CHECK);packet=proposal['packet'];rec=n.admitted(packet,binding,prepared,purpose=VERIFIED_IDENTITY_CHECK);request=n.request_for(packet,rec,prepared,minimized_evidence=True)
  answer=copy.deepcopy(self.f.reply);answer['binding_hash']=request['binding_hash'];answer['result']['citations']=[dict(evidence_id=proposal['citation_eligibility']['catalogue'][0],claim='crosswalk'),dict(evidence_id=proposal['citation_eligibility']['source'][0],claim='source_identity')]
  self.f.body=n.captured_request(request);response=self.f.response(answer)
  seed=copy.deepcopy(self.x.record)
  if mode=='bad_capture':seed['body']=self.pin('bad-body.json',b'{}')
  seed['runtime_manifest_sha256']=digest(self.manifest);seed['evidence_artifacts']=group
  audit_owner=self.pin('audit-owner.json',encoded(dict(decision='authorized_one_same_source_verified_identity_check_and_selective_restart')));seed['owner_scope']=audit_owner
  seed_pin=self.pin('seed.json',encoded(seed));owner=self.pin('owner-scope-new.json',encoded(dict(decision='authorized_exact_material_evidence_successor_and_private_report',prior_slot=7,same_case_only=True,packet_sha256=digest(packet))))
  root=self.f.root.read();case=self.f.case.read();credit=History(self.f.f.state/'credit').read();attempt=History(self.f.f.state/'attempt-7').read();terminal=[x for x in root if x.get('slot')==7 and x['type']=='supervised_diagnostic']
  p=dict(runtime=str(self.runtime),runtime_files=self.manifest,main_acceptance_path=str(self.root/'main-acceptance.json'),owner_scope=owner,activation_seed=seed_pin,audit_owner_scope=audit_owner,local_context=self.pin('local-context.json',encoded(local)),state=str(self.f.f.state),case_history=str(self.f.case.directory),account_evidence=dict(path=str(self.f.selected.path),sha256=self.f.selected.sha256),authority_path=str(self.root/'new-authority.json'),activation_path=str(self.root/'new-activation.json'),report_path=str(self.root/'private-report.html'),prior_slot=7,expected_slot=9 if mode=='wrong_slot' else 8,prepared_at=prepared,preparation_expires_at=now+60,root_prefix_sha256=digest(root),case_prefix_sha256=digest(case),credit_prefix_sha256=digest(credit),prior_terminal_sha256=digest(terminal[0]),prior_attempt_sha256=digest(attempt),catalogue_pin=cp,source_pin=sp,packet_sha256=digest(packet),request_hash=digest(request))
  template=(Path(__file__).resolve().parent/'automation/captured_evidence_successor_UNISSUED.py').read_text();assert template.count('ISSUED = None')==1
  wrapper=self.root/'issued-fixture.py';wrapper.write_text(template.replace('ISSUED = None','ISSUED = '+repr(p),1));wrapper.chmod(0o600)
  acceptance=dict(decision='accepted_exact_material_evidence_successor_and_private_report',wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),issued_pins=p)
  self.pin('main-acceptance.json',encoded(acceptance))
  code='''import sys,os,runpy,atexit,ctypes,io,contextlib
from pathlib import Path
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen' or (event=='ctypes.dlopen' and args[0] not in (None,'/usr/lib/libSystem.B.dylib')):
  attempts.append(event);raise AssertionError('external IO')
sys.addaudithook(audit)
@atexit.register
def done():print('TRIPWIRE='+str(len(attempts)))
'''
  code+='sys.path.insert(0,'+repr(str(self.runtime))+')\n'
  code+='''from ai_movie_investigator import supervised_credit as c,supervised_authorization as a,keychain_credential as k
c.read_private=lambda p,limit:Path(p).read_bytes()
native=[]
def fake_key(project):native.append(1);return b'sk-DUMMY_CAPTURED'
k._native=fake_key
consume=a.consume_captured_completion
def fixture_real_branch(held,answer):return dict(consume(held,answer),simulated=False)
a.consume_captured_completion=fixture_real_branch
'''
  code+='selected_raw='+repr(response)+"\nframing='chunked'\n"+framing.wire_code()
  code+='\n@contextlib.contextmanager\ndef chain(path):\n fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)\n try:\n  yield fd\n'
  code+=('  if str(path)=='+repr(str(self.root))+':raise RuntimeError("fixture_cleanup_failure")\n' if cleanup_failure else '  pass\n')
  code+=' finally:os.close(fd)\n'
  code+='namespace=runpy.run_path('+repr(str(wrapper))+',run_name="fixture_wrapper");main=namespace["main"];main.__globals__["bootstrap_guard"]=lambda runtime,pins:{"private_chain":chain,"read_private":lambda path,limit:Path(path).read_bytes()}\n'
  code+='sys.argv=['+repr(str(wrapper))+',"--main-accepted-evidence-successor"];captured=io.StringIO()\n'
  if mode:
   code+="before=[Path("+repr(str(self.f.f.state/FILENAME))+").read_bytes(),Path("+repr(str(self.f.case.directory/FILENAME))+").read_bytes(),Path("+repr(str(self.f.f.state/'credit'/FILENAME))+").read_bytes()]\n"
   code+="""with contextlib.redirect_stdout(captured),a._simulated_captured_io(),wire_fixture('completed'):
 try:main()
 except (ValueError,KeyError):pass
 else:raise AssertionError('preflight unexpectedly accepted')
assert 'private_report_ready_for_main' not in captured.getvalue()
assert not native
"""
   code+="assert before==[Path("+repr(str(self.f.f.state/FILENAME))+").read_bytes(),Path("+repr(str(self.f.case.directory/FILENAME))+").read_bytes(),Path("+repr(str(self.f.f.state/'credit'/FILENAME))+").read_bytes()]\n"
   code+='assert not Path('+repr(str(self.root/'new-authority.json'))+').exists() and not Path('+repr(str(self.root/'private-report.html'))+').exists()\n'
   code+='print("ENTRYPOINT_PREFLIGHT_REFUSED")\n'
  else:
   code+="""with contextlib.redirect_stdout(captured),a._simulated_captured_io(),wire_fixture('completed'):
 try:main()
 except RuntimeError as e:
  if str(e)!='fixture_cleanup_failure':raise
"""
   code+=('assert "private_report_ready_for_main" not in captured.getvalue()\n' if cleanup_failure else 'assert "private_report_ready_for_main" in captured.getvalue()\n')
   code+='assert len(native)==1\n'
   code+='sys.argv=['+repr(str(wrapper))+',"--main-accepted-evidence-successor"]\n'
   code+="""try:main()
except (ValueError,RuntimeError):pass
else:raise AssertionError('repeat unexpectedly accepted')
assert len(native)==1
print('ENTRYPOINT_ONCE')
"""
  script=self.root/'entry-driver.py';script.write_text(code)
  r=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=self.runtime,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=60)
  output=r.stdout+r.stderr;self.assertEqual(r.returncode,0,output);self.assertIn(b'TRIPWIRE=0',output);self.assertIn(b'ENTRYPOINT_PREFLIGHT_REFUSED' if mode else b'ENTRYPOINT_ONCE',output)
  if mode:return
  html=(self.root/'private-report.html').read_text();self.assertIn('Open the original source',html);self.assertIn('supported candidate',html)
  self.assertEqual((self.root/'private-report.html').stat().st_mode&0o777,0o600)
 def test_entrypoint_once_with_report(self):self.invoke()
 def test_invalid_context_no_writes(self):self.invoke(mode='invalid_context')
 def test_wrong_slot_no_writes(self):self.invoke(mode='wrong_slot')
 def test_expired_evidence_no_writes(self):self.invoke(mode='expired')
 def test_bad_capture_no_writes(self):self.invoke(mode='bad_capture')
 def test_cleanup_failure_has_no_success_message(self):self.invoke(cleanup_failure=True)
if __name__=='__main__':unittest.main()
