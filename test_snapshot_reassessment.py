"""Invented completed assessment and single distinct reassessment."""
import copy,hashlib,io,os,time,unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_snapshot_correction as correction
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class ReassessmentTests(unittest.TestCase):
 def setUp(self):
  self.c=correction.CorrectionTests('test_exact_successor_preserves_prior_and_refuses_second_child');self.c.setUp();self.addCleanup(self.c.doCleanups)
  self.f=self.c.f;self.root=self.c.root;self.credit=self.c.credit
  with self.f.gate(),auth._simulated_captured_io():
   gate.authorize(self.f.state,self.f.f.selected)
   grant=History(self.f.state).read()[-2]['historical'];response=decode(self.f.reply(grant))
   answer=decode(response['output'][-1]['content'][0]['text']);answer['result'].update(status='unresolved',candidate=None,citations=[],rationale='x'*601,uncertainty='Evidence remains incomplete.')
   response['output'][-1]['content'][0]['text']=encoded(answer).decode()
   consume=auth.consume_snapshot_completion
   def proof(grant,answer):return dict(consume(grant,answer),simulated=False)
   with patch.object(auth,'consume_snapshot_completion',side_effect=proof),diagnostics.DiagnosticTests().inputs(),framing.wire(encoded(response)),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.state,self.f.f.selected,8,historical=True)['status'],'completed')
  self.prior=self.root.read();self.start=next(r for r in self.prior if r.get('type')=='supervised_standing_attempt_started' and r.get('slot')==8)
  self.completed=next(r for r in self.prior if r.get('type')=='supervised_completed' and r.get('slot')==8);self.report=self.completed['historical_report']
  self.attempt=History(self.f.state/'attempt-8').read();self.credit_rows=self.credit.read();p=self.c.p
  assert self.report['prose_handling']['rationale']==dict(status='withheld',predicate='length')
  proof=dict(kind='snapshot_prose_length_reassessment_v1',prior_slot=8,prior_start_sha256=digest(self.start),prior_grant_sha256=digest(grant),prior_completion_sha256=digest(self.completed),prior_report_sha256=digest(self.report),prior_retained_reply_sha256=digest(self.completed['answer']),prior_attempt_sha256=digest(self.attempt),prior_receipt_sha256=digest(self.attempt[-1]),prior_credit_sha256=digest(self.credit_rows),prior_credit_count=len(self.credit_rows),prior_request_sha256=digest(grant['request']),root_prefix_sha256=digest(self.prior),new_request_sha256=digest(review.build(p)['request']),prior_status='unresolved',prior_candidate=None,reviewed=True)
  self.proof=proof;self.make_authority(proof)
 def make_authority(self,proof):
  f=self.f;record=copy.deepcopy(f.record);record.pop('correction',None);record.update(root_prefix_sha256=digest(self.prior),root_count=len(self.prior),reassessment=copy.deepcopy(proof))
  output=f.root/('reassessment-output-'+str(time.monotonic_ns()));output.mkdir(mode=0o700);st=output.stat();record.update(output_dir=str(output),output_identity=[st.st_dev,st.st_ino]);f.output=output
  scope=f.pin('reassessment-scope-'+str(time.monotonic_ns())+'.json',encoded(dict(kind='snapshot_reassessment_scope_v1',case_id=self.c.p['case_id'],version=self.c.p['version'],max_calls=1,disclosure_allowed=True,production_allowed=False,prior_slot=8)));record['owner_scope']=scope
  old=decode(Path(record['main_review']['path']).read_bytes());old.pop('correction_sha256',None);old.update(owner_scope_sha256=scope['sha256'],reassessment_sha256=digest(proof))
  record['main_review']=f.pin('reassessment-review-'+str(time.monotonic_ns())+'.json',encoded(old));pin=f.pin('reassessment-authority-'+str(time.monotonic_ns())+'.json',encoded(record));f.record=record;f.authority=pin
 def test_distinct_new_result_preserves_prior_and_refuses_another(self):
  old={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
  with self.f.gate(),auth._simulated_captured_io():
   allocated=gate.authorize(self.f.state,self.f.f.selected);self.assertEqual(allocated['slot'],9)
   grant=History(self.f.state).read()[-2]['historical'];response=self.f.reply(grant)
   with diagnostics.DiagnosticTests().inputs(),framing.wire(response),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.state,self.f.f.selected,9,historical=True)['status'],'completed')
   now=self.root.read()[-1]['historical_report'];self.assertEqual(now['result']['status'],'supported_candidate')
   self.assertEqual(now['previous_assessment']['status'],'unresolved');self.assertEqual(now['previous_assessment']['rationale'],'withheld_unrecoverable')
   from ai_movie_investigator.snapshot_private_report import render
   presented=copy.deepcopy(now);presented['generation_invoked']=True;presented['provider_receipt_correlated']=True
   local=Path(self.f.record['local_context']['path']).read_bytes()
   html=render(presented,digest(presented),self.c.p,local,self.f.record['local_context']['sha256'])
   self.assertIn('Earlier distinct assessment',html);self.assertIn('cannot be recovered',html)
   self.assertIn('distinct new result',html);self.assertIn('supported_candidate',html)
   with self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   with self.assertRaises(Refusal):c.run(self.f.state,self.f.f.selected,9,historical=True)
  for p,raw in old.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
  self.assertEqual(len(self.credit.read()),len(self.credit_rows)+1)
 def test_tampered_prior_proofs_refuse_before_allocation(self):
  for field in ('prior_completion_sha256','prior_report_sha256','prior_retained_reply_sha256','prior_attempt_sha256','prior_receipt_sha256','prior_credit_sha256','new_request_sha256'):
   bad=copy.deepcopy(self.proof);bad[field]='f'*64;self.make_authority(bad)
   with self.subTest(field=field),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   self.assertFalse((self.f.state/'attempt-9').exists())
 def test_installed_issued_reassessment_preserves_prior_reports(self):
  import json,subprocess,sys,shutil,sysconfig
  from ai_movie_investigator.installation import install_runtime
  f=self.f;runtime=f.root/'installed-reassessment';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_text());f.manifest.clear();f.manifest.update(manifest)
  f.record['runtime_manifest_sha256']=digest(manifest);self.make_authority(self.proof)
  with f.gate():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,f.f.selected.data)
   response=f.reply(grant)
  template=Path('automation/snapshot_review_UNISSUED.py').read_text()
  interpreter=Path(sys.executable).resolve(strict=True);child_env=os.environ.copy()
  if sys.platform.startswith('linux'):
   interpreter=f.root/'fixture-reassessment-python';shutil.copyfile(Path(sys.executable).resolve(strict=True),interpreter);interpreter.chmod(0o700)
   library_dir=sysconfig.get_config_var('LIBDIR')
   if library_dir:child_env['LD_LIBRARY_PATH']=library_dir
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'reassessment-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=digest(self.prior),expected_slot=9)
  wrapper=f.root/'issued-reassessment-wrapper.py';wrapper.write_text(template.replace('ISSUED = None','ISSUED = '+repr(issued),1));wrapper.chmod(0o600)
  f.pin('reassessment-acceptance.json',encoded(dict(decision='accepted_exact_normalized_snapshot_assessment',wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),issued_pins=issued)))
  driver="""import sys,runpy,os,errno
from pathlib import Path
if sys.platform.startswith('linux'):
 def fixture_absent_acl(*args,**kwargs):raise OSError(errno.ENODATA,'fixture absent ACL')
 os.getxattr=fixture_absent_acl
 print('LINUX_FIXTURE_ACL_SIMULATED')
sys.path.insert(0,"""+repr(str(runtime))+""")
from ai_movie_investigator import keychain_credential as k,supervised_authorization as a
k._native=lambda project:b'sk-SYNTHETIC_FIXTURE'
consume=a.consume_snapshot_completion
def fixture_proof(grant,answer):return dict(consume(grant,answer),simulated=False)
a.consume_snapshot_completion=fixture_proof
"""
  driver+='selected_raw='+repr(response)+"\nframing='chunked'\n"+framing.wire_code()
  driver+='\nnamespace=runpy.run_path('+repr(str(wrapper))+',run_name="fixture_wrapper")\nsys.argv=['+repr(str(wrapper))+',"--main-accepted-snapshot-review"]\n'
  driver+='with a._simulated_captured_io(),wire_fixture("completed"):\n namespace["main"]()\n'
  path=f.root/'reassessment-driver.py';path.write_text(driver)
  old={p:p.read_bytes() for p in f.state.rglob(FILENAME)}
  result=subprocess.run([str(interpreter),'-I','-S','-B',str(path)],cwd=runtime,env=child_env,capture_output=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
  self.assertIn(b'private_report_written',result.stdout)
  if sys.platform.startswith('linux'):self.assertIn(b'LINUX_FIXTURE_ACL_SIMULATED',result.stdout)
  html=(f.output/'movie-review.html').read_text();self.assertIn('Earlier distinct assessment',html);self.assertIn('cannot be recovered',html)
  for p,raw in old.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
  self.assertEqual(len(self.credit.read()),len(self.credit_rows)+1)
 def test_wrong_withholding_or_chain_refuses(self):
  with self.f.gate():
   with self.root.transaction(write=True) as (events,_):
    grant=gate.proposal(self.root,events,self.f.f.selected.data)
    for change in ('predicate','status','chain'):
     altered=copy.deepcopy(events)
     if change=='predicate':next(r for r in altered if r.get('type')=='supervised_completed' and r.get('slot')==8)['historical_report']['prose_handling']['rationale']['predicate']='path_or_url_syntax'
     elif change=='status':next(r for r in altered if r.get('type')=='supervised_completed' and r.get('slot')==8)['historical_report']['result']['status']='blocked'
     else:next(r for r in altered if r.get('type')=='supervised_standing_attempt_started' and r.get('slot')==8)['historical']['reassessment']={'prior_slot':7}
     with self.subTest(change=change),patch.object(self.root,'require_write_transaction'),self.assertRaises(Refusal):gate.validate_reassessment(self.root,altered,grant,creating=True)
if __name__=='__main__':unittest.main()
