"""Exact failed-v10 correction, installed wrapper and fabricated HTTP only."""
import copy,hashlib,io,time,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_snapshot_assessment_integration as prior
import test_supervised_envelope as framing
class QualityIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.previous=prior.AssessmentIntegrationTests('test_first_supported');self.previous.setUp();self.addCleanup(self.previous.doCleanups)
  base=self.previous;self.f=base.f;self.root=base.root;self.credit=base.credit;self.p=base.p
  from ai_movie_investigator import keychain_credential
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):g=gate.proposal(self.root,events,self.f.f.selected.data)
   consume=auth.consume_snapshot_completion
   def proof(g,a):return dict(consume(g,a),simulated=False)
   with framing.wire(self.response(g,unresolved=True)),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()),self.assertRaisesRegex(Refusal,'snapshot_runner_failed'):
    gate.execute(self.f.state,self.f.f.selected,self.f.output)
  self.events=self.root.read();self.credit_rows=self.credit.read();self.slot=17
  self.assertFalse(any(x.get('slot')==16 and x.get('type')=='supervised_completed' for x in self.events));self.assertFalse(list(self.f.output.iterdir()))
  start=next(x for x in self.events if x.get('type')=='supervised_standing_attempt_started' and x.get('slot')==16)
  terminal=next(x for x in self.events if x.get('type')=='supervised_diagnostic' and x.get('slot')==16)
  self.assertEqual((terminal['phase'],terminal['reason']),('receipt_recorded','snapshot_assessment_justification'))
  rows=History(self.f.state/'attempt-16').read();r=copy.deepcopy(self.f.record)
  proof=r['assessment'];proof.update(kind='snapshot_film_quality_v11',mode='correction',request_sha256=digest(review.build_film_quality(self.p)['request']),prior=dict(slot=16,start_sha256=digest(start),grant_sha256=digest(start['historical']),terminal_sha256=digest(terminal),attempt_sha256=digest(rows),receipt_sha256=digest(rows[-1]),credit_sha256=digest(self.credit_rows),credit_count=len(self.credit_rows),request_sha256=start['request_sha256'],projection_sha256=start['historical']['projection_sha256'],local_context_sha256=start['historical']['local_context_sha256']))
  r.update(root_prefix_sha256=digest(self.events),root_count=len(self.events))
  scope=decode(Path(r['owner_scope']['path']).read_bytes());scope.update(kind='snapshot_film_quality_scope_v11',mode='correction',prior_slot=16)
  r['owner_scope']=self.f.pin('v11-owner.json',encoded(scope));mr=decode(Path(r['main_review']['path']).read_bytes());mr.update(assessment_sha256=digest(proof),owner_scope_sha256=r['owner_scope']['sha256']);r['main_review']=self.f.pin('v11-main.json',encoded(mr))
  if 'publisher' in self._testMethodName:
   pub=dict(kind='publisher_edition_observation_v1',case_id=self.p['case_id'],version=self.p['version'],title=self.p['catalogue']['title'],year=self.p['catalogue']['theatrical_year'],edition_label='Invented restored edition',publisher='Invented Publisher',runtime_minutes=102,observed_at=time.time()-1,expires_at=time.time()+1800,provenance_sha256='a'*64,source_url='https://publisher.invalid/edition?private=fixture',source_reviewed=True,title_year_linkage_reviewed=True)
   proof['publisher_edition']=self.f.pin('v11-publisher.json',encoded(pub));self.p=copy.deepcopy(self.p);self.p['publisher_edition']=review.publisher_edition_context(encoded(pub),self.p,now=time.time());proof['request_sha256']=digest(review.build_film_quality(self.p)['request'])
   scope['publisher_edition_sha256']=proof['publisher_edition']['sha256'];r['owner_scope']=self.f.pin('v11-publisher-owner.json',encoded(scope));mr.update(assessment_sha256=digest(proof),owner_scope_sha256=r['owner_scope']['sha256'],publisher_edition_sha256=proof['publisher_edition']['sha256'],publisher_source_reviewed=True,publisher_title_year_linkage_reviewed=True);r['main_review']=self.f.pin('v11-publisher-main.json',encoded(mr))
  out=self.f.root/'v11-output';out.mkdir(mode=0o700);st=out.stat();r.update(output_dir=str(out),output_identity=[st.st_dev,st.st_ino]);self.f.output=out;self.f.record=r;self.f.authority=self.f.pin('v11-authority.json',encoded(r))
 def response(self,grant,*,unresolved=False,long_text=False):
  raw=self.previous.response(grant,unresolved=unresolved);v=decode(raw,65536);a=decode(v['output'][-1]['content'][0]['text'])
  if unresolved:a['result']['primary_blocker'].update(support_considered='Title conflict title conflict.',material_conflict='Title conflict title conflict.')
  v['output'][-1]['content'][0]['text']=encoded(a).decode();return encoded(v)
 def test_installed_correction_unresolved(self):self.installed(True)
 def test_installed_correction_supported(self):self.installed(False)
 def test_installed_correction_publisher(self):self.installed(True)
 def test_wrong_proof_and_first_mode_cannot_reuse_case(self):
  original=copy.deepcopy(self.f.record);before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
  for key in ('terminal_sha256','receipt_sha256','credit_sha256','projection_sha256','request_sha256'):
   r=copy.deepcopy(original);r['assessment']['prior'][key]='f'*64;mr=decode(Path(r['main_review']['path']).read_bytes());mr['assessment_sha256']=digest(r['assessment']);r['main_review']=self.f.pin('v11-bad-main-'+key+'.json',encoded(mr));self.f.record=r;self.f.authority=self.f.pin('v11-bad-'+key+'.json',encoded(r))
   with self.subTest(key=key),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
  r=copy.deepcopy(original);r['assessment'].pop('prior');r['assessment']['mode']='first';scope=decode(Path(r['owner_scope']['path']).read_bytes());scope.pop('prior_slot');scope['mode']='first';r['owner_scope']=self.f.pin('v11-first-owner.json',encoded(scope));mr=decode(Path(r['main_review']['path']).read_bytes());mr.update(assessment_sha256=digest(r['assessment']),owner_scope_sha256=r['owner_scope']['sha256']);r['main_review']=self.f.pin('v11-first-main.json',encoded(mr));self.f.record=r;self.f.authority=self.f.pin('v11-first-authority.json',encoded(r))
  with self.f.gate(),self.assertRaisesRegex(Refusal,'snapshot_case_consumed'):gate.authorize(self.f.state,self.f.f.selected)
  for p,raw in before.items():self.assertEqual(p.read_bytes(),raw)
 def installed(self,unresolved):
  import json,os,shutil,subprocess,sys,sysconfig
  from ai_movie_investigator.installation import install_runtime
  f=self.f;runtime=f.root/'installed-result';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_text());f.manifest.clear();f.manifest.update(manifest)
  f.record['runtime_manifest_sha256']=digest(manifest);f.authority=f.pin('result-installed-authority.json',encoded(f.record))
  with f.gate():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,f.f.selected.data)
   response=self.response(grant,unresolved=unresolved,long_text=True)
   self.assertNotIn('publisher.invalid',encoded(grant['request']).decode())
  template=Path('automation/snapshot_review_UNISSUED.py').read_text();interpreter=Path(sys.executable).resolve(strict=True);env=os.environ.copy()
  if sys.platform.startswith('linux'):
   interpreter=f.root/'fixture-result-python';shutil.copyfile(Path(sys.executable).resolve(strict=True),interpreter);interpreter.chmod(0o700)
   lib=sysconfig.get_config_var('LIBDIR')
   if lib:env['LD_LIBRARY_PATH']=lib
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'result-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=f.record['root_prefix_sha256'],expected_slot=self.slot)
  wrapper=f.root/'issued-result-wrapper.py';wrapper.write_text(template.replace('ISSUED = None','ISSUED = '+repr(issued),1));wrapper.chmod(0o600)
  f.pin('result-acceptance.json',encoded(dict(decision='accepted_exact_normalized_snapshot_assessment',wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),issued_pins=issued)))
  driver="""import sys,runpy,os,errno
from pathlib import Path
if sys.platform.startswith('linux'):
 def fixture_absent_acl(*args,**kwargs):raise OSError(errno.ENODATA,'fixture absent ACL')
 os.getxattr=fixture_absent_acl
sys.path.insert(0,"""+repr(str(runtime))+""")
from ai_movie_investigator import keychain_credential as k,supervised_authorization as a
k._native=lambda project:b'sk-SYNTHETIC_FIXTURE'
consume=a.consume_snapshot_completion
def fixture_proof(grant,answer):return dict(consume(grant,answer),simulated=False)
a.consume_snapshot_completion=fixture_proof
"""
  driver+='''
from ai_movie_investigator import bound_send as bs
from ai_movie_investigator.responses_http import HTTPResult
original_parse=bs.parse_response
def checked_parse(raw,schema,request_id=None,**kw):
 result=kw['http_result'];assert kw['expected_model']=='gpt-5-mini-2025-08-07'
 assert a.response_limits(result,raw,request_id,kw['expected_model'])==(1048576,1048576)
 copied=HTTPResult(result.status,result.body,result.request_id,result.request_sha256,result.project,result.path)
 assert a.response_limits(copied,raw,request_id,kw['expected_model'])==(32768,16384)
 try:a.response_limits(result,raw,request_id,'gpt-5-nano-2025-08-07')
 except ValueError:pass
 else:raise AssertionError('wrong model obtained selected limits')
 return original_parse(raw,schema,request_id,**kw)
bs.parse_response=checked_parse
'''
  driver+='selected_raw='+repr(response)+"\nframing='chunked'\n"+framing.wire_code()
  driver+='\nnamespace=runpy.run_path('+repr(str(wrapper))+',run_name="fixture_wrapper")\nsys.argv=['+repr(str(wrapper))+',"--main-accepted-snapshot-review"]\n'
  driver+='''
trips=[]
def audit(event,args):
 if event in ('socket.connect','subprocess.Popen','os.system'):
  trips.append(event);raise AssertionError('real IO forbidden')
sys.addaudithook(audit)
'''
  driver+='with a._simulated_captured_io(),wire_fixture("completed"):\n namespace["main"]()\n'
  driver+='''
import socket,subprocess
assert not trips
def forbidden(*args,**kwargs):
 trips.append('external');raise AssertionError('external IO forbidden')
k._native=forbidden
socket.socket=forbidden
socket.create_connection=forbidden
subprocess.Popen=forbidden
from ai_movie_investigator.contracts import Refusal
try:
 namespace['main']()
except ValueError as error:
 assert str(error)=='root_prefix_changed'
except SystemExit as error:
 assert error.code not in (0,None)
else:raise AssertionError('duplicate accepted')
assert not trips
print('duplicate_refused_no_external_io')
'''
  path=f.root/'result-driver.py';path.write_text(driver)
  old={p:p.read_bytes() for p in f.state.rglob(FILENAME)}
  result=subprocess.run([str(interpreter),'-I','-S','-B',str(path)],cwd=runtime,env=env,capture_output=True,timeout=90)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));self.assertIn(b'private_report_written',result.stdout)
  self.assertIn(b'duplicate_refused_no_external_io',result.stdout)
  for p,raw in old.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
  self.assertEqual(len(self.credit.read()),len(self.credit_rows)+1)
  self.assertEqual(self.credit.read()[-1]['reserved_usd'],[15,100])
  self.assertEqual(self.credit.read()[-1]['model'],'gpt-5-mini-2025-08-07')
  completion=next(r for r in self.root.read() if r.get('slot')==self.slot and r.get('type')=='supervised_completed')
  self.assertEqual(completion['historical_report']['assessment_label'],'quality_separated_film_assessment_v11')
  self.assertEqual(completion['historical_report'].get('previous_assessment'),self.f.record['assessment'].get('prior',{}).get('summary'))
  if unresolved:
   self.assertEqual(completion['historical_report']['result']['film_blockers'][0]['material_conflict'],'Title conflict title conflict.')
   self.assertTrue(completion['historical_report']['result']['explanation_quality'])
   self.assertIn('Explanation quality caveats',(f.output/'movie-review.html').read_text())
  self.assertEqual(completion['historical_report']['result']['status'],'unresolved' if unresolved else 'supported_candidate')
  html=(f.output/'movie-review.html').read_text();self.assertIn('Computed evidence comparisons',html);self.assertIn('unresolved' if unresolved else 'supported_candidate',html)
