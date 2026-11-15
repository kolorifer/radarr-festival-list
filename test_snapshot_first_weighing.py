"""Invented first-case Mini route after mixed retained Nano/Mini history."""
import copy,hashlib,io,time,unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.credit_test import MINI_PROFILE
import test_snapshot_weighing_integration as prior
import test_supervised_envelope as framing

class FirstWeighingTests(unittest.TestCase):
 def setUp(self):
  self.previous=prior.WeighingIntegrationTests('test_wrong_pins_refuse_before_reservation');self.previous.setUp();self.addCleanup(self.previous.doCleanups)
  self.f=self.previous.f;self.root=self.previous.root;self.credit=self.previous.credit
  from ai_movie_investigator import keychain_credential
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,self.f.f.selected.data)
   consume=auth.consume_snapshot_completion
   def proof(g,a):return dict(consume(g,a),simulated=False)
   with framing.wire(self.previous.response(grant)),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()):gate.execute(self.f.state,self.f.f.selected,self.f.output)
  self.events=self.root.read();self.credit_rows=self.credit.read()
  self.old_case=self.f.record['attestation']['case_id']
  self.prepare('outcome-'+'e'*64,conflict=self._testMethodName.endswith('unresolved'))
 def prepare(self,case_id,conflict=False):
  f=self.f;r=copy.deepcopy(f.record);r.pop('weighing_reassessment',None);r.pop('first_assessment',None)
  snap=decode(Path(r['snapshot']['path']).read_bytes(),1048576);src=decode(Path(r['source']['path']).read_bytes())
  snap['cases'][0]['case_id']=snap['items'][0]['case_id']=src['case_id']=case_id
  if conflict:
   snap['cases'][0]['source_identity']['asserted_tmdb']=456;snap['items'][0]['facts']['tmdb']=456
  r['snapshot']=f.pin('first-snapshot-'+str(time.monotonic_ns())+'.json',encoded(snap));r['source']=f.pin('first-source-'+str(time.monotonic_ns())+'.json',encoded(src))
  att=r['attestation'];att.update(case_id=case_id,snapshot_sha256=r['snapshot']['sha256'],source_sha256=r['source']['sha256'])
  self.p=review.projection(encoded(snap),r['snapshot']['sha256'],case_id,att['version'],encoded(src),Path(r['catalogue']['path']).read_bytes(),att,now=time.time())
  proof=dict(kind='snapshot_first_weighing_v1',model_profile=copy.deepcopy(MINI_PROFILE),model_evidence_sha256=digest(f.f.selected.data),request_sha256=digest(review.build_film_weighing(self.p,first=True)['request']))
  r.update(first_assessment=proof,root_count=len(self.events),root_prefix_sha256=digest(self.events))
  out=f.root/('first-output-'+str(time.monotonic_ns()));out.mkdir(mode=0o700);st=out.stat();r.update(output_dir=str(out),output_identity=[st.st_dev,st.st_ino]);f.output=out
  r['owner_scope']=f.pin('first-scope-'+str(time.monotonic_ns())+'.json',encoded(dict(kind='snapshot_first_weighing_scope_v1',case_id=case_id,version=att['version'],max_calls=1,disclosure_allowed=True,production_allowed=False,model_profile_sha256=digest(MINI_PROFILE))))
  mr=decode(Path(r['main_review']['path']).read_bytes());mr.pop('weighing_reassessment_sha256',None);mr.update(owner_scope_sha256=r['owner_scope']['sha256'],snapshot_sha256=r['snapshot']['sha256'],source_sha256=r['source']['sha256'],first_assessment_sha256=digest(proof))
  r['main_review']=f.pin('first-review-'+str(time.monotonic_ns())+'.json',encoded(mr));f.record=r;self.save()
 def save(self):self.f.authority=self.f.pin('first-authority-'+str(time.monotonic_ns())+'.json',encoded(self.f.record))
 def response(self,grant,*,unresolved=False,long_text=False):
  raw=self.previous.response(grant,unresolved=unresolved,long_text=False)
  if unresolved:
   v=decode(raw,65536);a=decode(v['output'][-1]['content'][0]['text']);a['result']['primary_blocker'].update(aspect='ids',reason='conflicting_film_evidence',support_considered='The listing and catalogue share cast and title.',material_conflict='The asserted TMDb identifier names a different catalogue record.')
   v['output'][-1]['content'][0]['text']=encoded(a).decode();raw=encoded(v)
  return raw
 def test_scope_and_consumed_case_refuse(self):
  original=copy.deepcopy(self.f.record)
  for field in ('request_sha256','model_evidence_sha256'):
   self.f.record=copy.deepcopy(original);self.f.record['first_assessment'][field]='f'*64
   mr=decode(Path(self.f.record['main_review']['path']).read_bytes());mr['first_assessment_sha256']=digest(self.f.record['first_assessment']);self.f.record['main_review']=self.f.pin('bad-review-'+str(time.monotonic_ns())+'.json',encoded(mr));self.save()
   with self.subTest(field=field),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   self.assertFalse((self.f.state/'attempt-16').exists());self.assertEqual(self.credit.read(),self.credit_rows)
  for delta in (dict(max_calls=2),dict(disclosure_allowed=False),dict(production_allowed=True),dict(model_profile_sha256='f'*64),dict(case_id=self.old_case)):
   self.f.record=copy.deepcopy(original);scope=decode(Path(original['owner_scope']['path']).read_bytes());scope.update(delta)
   self.f.record['owner_scope']=self.f.pin('bad-owner-'+str(time.monotonic_ns())+'.json',encoded(scope))
   mr=decode(Path(original['main_review']['path']).read_bytes());mr['owner_scope_sha256']=self.f.record['owner_scope']['sha256'];self.f.record['main_review']=self.f.pin('bad-main-'+str(time.monotonic_ns())+'.json',encoded(mr));self.save()
   with self.subTest(scope=delta),self.assertRaises(Refusal),self.f.gate():pass
   self.assertEqual(self.credit.read(),self.credit_rows)
  self.f.record=copy.deepcopy(original);self.f.record['weighing_reassessment']={};self.save()
  with self.assertRaisesRegex(Refusal,'snapshot_reassessment_changed'),self.f.gate():pass
  self.f.record=original;self.prepare(self.old_case)
  with self.f.gate(),self.assertRaisesRegex(Refusal,'snapshot_case_consumed'):gate.authorize(self.f.state,self.f.f.selected)
  self.assertFalse((self.f.state/'attempt-16').exists())
 def test_malformed_answer_burns_once(self):
  from ai_movie_investigator import keychain_credential
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,self.f.f.selected.data)
   v=decode(self.response(grant),65536);v['output'][-1]['content'][0]['text']='{}'
   with framing.wire(encoded(v)),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()),self.assertRaises(Refusal):gate.execute(self.f.state,self.f.f.selected,self.f.output)
   count=len(self.credit.read())
   with self.assertRaises(Refusal):gate.execute(self.f.state,self.f.f.selected,self.f.output)
   self.assertEqual(len(self.credit.read()),count)
  self.assertEqual(self.credit.read()[:-1],self.credit_rows);self.assertEqual(self.credit.read()[-1]['reserved_usd'],[15,100]);self.assertFalse((self.f.output/'movie-review.html').exists())
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
  template=Path('automation/snapshot_review_UNISSUED.py').read_text();interpreter=Path(sys.executable).resolve(strict=True);env=os.environ.copy()
  if sys.platform.startswith('linux'):
   interpreter=f.root/'fixture-result-python';shutil.copyfile(Path(sys.executable).resolve(strict=True),interpreter);interpreter.chmod(0o700)
   lib=sysconfig.get_config_var('LIBDIR')
   if lib:env['LD_LIBRARY_PATH']=lib
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'result-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=f.record['root_prefix_sha256'],expected_slot=16)
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
  completion=next(r for r in self.root.read() if r.get('slot')==16 and r.get('type')=='supervised_completed')
  self.assertEqual(completion['historical_report']['assessment_label'],'first_mini_film_weighing')
  self.assertNotIn('previous_assessment',completion['historical_report'])
  self.assertEqual(completion['historical_report']['result']['status'],'unresolved' if unresolved else 'supported_candidate')
  html=(f.output/'movie-review.html').read_text();self.assertIn('Computed evidence comparisons',html);self.assertIn('unresolved' if unresolved else 'supported_candidate',html)
 def test_installed_weighing_unresolved(self):self.installed(True)
 def test_installed_weighing_supported(self):self.installed(False)
