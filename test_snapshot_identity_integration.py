"""Completed v11 -> one v12, true refreshed case version, fake installed HTTP."""
import copy,hashlib,io,time,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_snapshot_quality_integration as prior
import test_supervised_envelope as framing
class IdentityIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.previous=prior.QualityIntegrationTests('test_installed_correction_publisher');self.previous.setUp();self.addCleanup(self.previous.doCleanups)
  base=self.previous;self.f=base.f;self.root=base.root;self.credit=base.credit;self.p=base.p
  from ai_movie_investigator import keychain_credential
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):g=gate.proposal(self.root,events,self.f.f.selected.data)
   consume=auth.consume_snapshot_completion
   def proof(g,a):return dict(consume(g,a),simulated=False)
   with framing.wire(base.response(g,unresolved=True)),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()):gate.execute(self.f.state,self.f.f.selected,self.f.output)
  self.events=self.root.read();self.credit_rows=self.credit.read();self.slot=18
  start=next(x for x in self.events if x.get('type')=='supervised_standing_attempt_started' and x.get('slot')==17);done=next(x for x in self.events if x.get('type')=='supervised_completed' and x.get('slot')==17);rep=done['historical_report'];rows=History(self.f.state/'attempt-17').read();r=copy.deepcopy(self.f.record)
  self.old_version=self.p['version'];self.old_observed=self.p['observed_at']
  proof=r['assessment'];proof.update(kind='snapshot_film_identity_v12',mode='reassessment',prior=dict(slot=17,start_sha256=digest(start),grant_sha256=digest(start['historical']),completion_sha256=digest(done),report_sha256=digest(rep),retained_reply_sha256=rep['retained_reply_hash'],attempt_sha256=digest(rows),receipt_sha256=digest(rows[-1]),credit_sha256=digest(self.credit_rows),credit_count=len(self.credit_rows),request_sha256=rep['request_sha256'],projection_sha256=rep['projection_sha256'],local_context_sha256=rep['local_context_sha256'],version=self.old_version,collector_observed_at=self.old_observed,summary=dict(slot=17,status=rep['result']['status'],candidate=rep['result']['candidate'],report_sha256=digest(rep),rationale=rep['prose_handling']['rationale']['status'],uncertainty=rep['prose_handling']['uncertainty']['status'])))
  new_version='f'*64
  snap=decode(Path(r['snapshot']['path']).read_bytes(),1048576);snap['generated_at']+=0.5
  for case in snap['cases']:
   if case['case_id']==self.p['case_id']:case.update(version=new_version,observed_at=case['observed_at']+0.5)
  for item in snap['items']:
   if item['case_id']==self.p['case_id']:
    item['observed_at']+=0.5;item['provenance'][0].update(digest=new_version,observed_at=item['observed_at'])
  r['snapshot']=self.f.pin('v12-fresh-snapshot.json',encoded(snap));r['attestation'].update(snapshot_sha256=r['snapshot']['sha256'],version=new_version)
  for name in ('source','catalogue'):
   obj=decode(Path(r[name]['path']).read_bytes());obj['observed_at']+=0.5;obj['expires_at']+=0.5
   if name=='source':obj['version']=new_version
   r[name]=self.f.pin('v12-fresh-'+name+'.json',encoded(obj));r['attestation'][name+'_sha256']=r[name]['sha256']
  r['attestation']['expires_at']+=0.5;r['expires_at']+=0.5;proof['reobservation']['current_observed_at']+=0.5
  pub=decode(Path(proof['publisher_edition']['path']).read_bytes());pub['observed_at']+=0.01;pub['expires_at']+=0.5;pub['version']=new_version;proof['publisher_edition']=self.f.pin('v12-fresh-publisher.json',encoded(pub))
  self.p=review.projection(Path(r['snapshot']['path']).read_bytes(),r['snapshot']['sha256'],r['attestation']['case_id'],new_version,Path(r['source']['path']).read_bytes(),Path(r['catalogue']['path']).read_bytes(),r['attestation'],now=time.time(),reobservation=proof['reobservation'],local_context=decode(Path(r['local_context']['path']).read_bytes()),historical_observed_at=self.old_observed)
  self.p['publisher_edition']=review.publisher_edition_context(encoded(pub),self.p,now=time.time());proof['request_sha256']=digest(review.build_film_identity(self.p)['request'])
  r.update(root_prefix_sha256=digest(self.events),root_count=len(self.events))
  scope=decode(Path(r['owner_scope']['path']).read_bytes());scope.update(kind='snapshot_film_identity_scope_v12',version=new_version,mode='reassessment',prior_slot=17,same_case_reobservation_allowed=True,publisher_edition_sha256=proof['publisher_edition']['sha256'],reobservation_sha256=digest(proof['reobservation']))
  r['owner_scope']=self.f.pin('v12-owner.json',encoded(scope));mr=decode(Path(r['main_review']['path']).read_bytes());mr.update(assessment_sha256=digest(proof),owner_scope_sha256=r['owner_scope']['sha256'],same_case_reobservation_reviewed=True,publisher_edition_sha256=proof['publisher_edition']['sha256'],same_listing_derivation_sha256=digest(proof['reobservation']))
  for name in ('snapshot','source','catalogue'):mr[name+'_sha256']=r[name]['sha256']
  r['main_review']=self.f.pin('v12-main.json',encoded(mr));out=self.f.root/'v12-output';out.mkdir(mode=0o700);st=out.stat();r.update(output_dir=str(out),output_identity=[st.st_dev,st.st_ino]);self.f.output=out;self.f.record=r;self.f.authority=self.f.pin('v12-authority.json',encoded(r))
 def response(self,grant,*,unresolved=False,long_text=False):return self.previous.response(grant,unresolved=unresolved)
 def test_installed_supported_real_version_refresh(self):self.installed(False)
 def test_wrong_prior_and_scope_are_nonmutating(self):
  original=copy.deepcopy(self.f.record);before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
  for key in ('completion_sha256','receipt_sha256','credit_sha256','projection_sha256','version'):
   r=copy.deepcopy(original);r['assessment']['prior'][key]='e'*64;mr=decode(Path(r['main_review']['path']).read_bytes());mr['assessment_sha256']=digest(r['assessment']);r['main_review']=self.f.pin('v12-bad-main-'+key+'.json',encoded(mr));self.f.record=r;self.f.authority=self.f.pin('v12-bad-'+key+'.json',encoded(r))
   with self.subTest(key=key),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
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
  self.assertEqual(completion['historical_report']['assessment_label'],'film_identity_separate_edition_v12')
  self.assertEqual(completion['historical_report'].get('previous_assessment'),self.f.record['assessment'].get('prior',{}).get('summary'))
  self.assertEqual(completion['historical_report']['result']['status'],'unresolved' if unresolved else 'supported_candidate')
  self.assertIn('collector_reobservation',completion['historical_report']);self.assertEqual(completion['historical_report']['collector_reobservation']['prior_version'],self.old_version)
  html=(f.output/'movie-review.html').read_text();self.assertIn('Separate edition and evidence limitations',html);self.assertIn('Prior collector observation',html);self.assertIn('Reviewed publisher-edition claim',html);self.assertIn('Computed evidence comparisons',html);self.assertIn('unresolved' if unresolved else 'supported_candidate',html)
