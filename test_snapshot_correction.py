"""Invented receipt-backed correction. No real case, keychain or network."""
import copy,hashlib,io,os,time,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.disclosure import aliases
import test_snapshot_integration as fixture
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class CorrectionTests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.IntegrationTests('test_default_closed_and_forged_receipt_refused');self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.root=History(self.f.state);self.credit=History(self.f.state/'credit')
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,append):
    grant=gate.proposal(self.root,events,self.f.f.selected.data);p=gate.active().revalidate();b=review.build(p,corrected=False)
    grant.pop('contract_version');grant.update(request=b['request'],run=b['run'],selected_evidence=b['selected_evidence'],disclosure=b['disclosure'])
    with patch.object(gate,'validate_grant',return_value=encoded(grant['request'])):
     c._prepare_next_locked(self.root,events,append,self.f.f.selected,create=True,historical=grant)
   response=decode(self.f.reply(grant));answer=decode(response['output'][-1]['content'][0]['text'])
   answer['result']['status']='unresolved' # deliberately inconsistent old-schema answer
   response['output'][-1]['content'][0]['text']=encoded(answer).decode()
   with patch.object(gate,'validate_grant',return_value=encoded(grant['request'])),diagnostics.DiagnosticTests().inputs(),framing.wire(encoded(response)),redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(Refusal,'candidate_status'):c.run(self.f.state,self.f.f.selected,7,historical=True)
  self.prior=self.root.read();self.oldstart=next(r for r in self.prior if r.get('type')=='supervised_standing_attempt_started' and r.get('slot')==7)
  self.terminal=next(r for r in self.prior if r.get('type')=='supervised_diagnostic' and r.get('slot')==7)
  self.attempt=History(self.f.state/'attempt-7').read();self.credit_rows=self.credit.read()
  assert self.terminal['reason']=='candidate_status' and self.terminal['phase']=='receipt_recorded'
  proof=dict(kind='snapshot_candidate_status_correction_v1',prior_slot=7,prior_start_sha256=digest(self.oldstart),prior_grant_sha256=digest(grant),prior_terminal_sha256=digest(self.terminal),prior_attempt_sha256=digest(self.attempt),prior_receipt_sha256=digest(self.attempt[-1]),prior_credit_sha256=digest(self.credit_rows),prior_credit_count=len(self.credit_rows),prior_request_sha256=digest(grant['request']),root_prefix_sha256=digest(self.prior),new_request_sha256=digest(review.build(p,prose_limited=False)['request']),reviewed=True)
  self.proof=proof;self.p=p;self.make_authority(proof)
 def make_authority(self,proof):
  f=self.f;record=copy.deepcopy(f.record);record.update(root_prefix_sha256=digest(self.prior),root_count=len(self.prior),correction=copy.deepcopy(proof))
  scope=f.pin('correction-scope-'+str(time.monotonic_ns())+'.json',encoded(dict(kind='snapshot_correction_scope_v1',case_id=self.p['case_id'],version=self.p['version'],max_calls=1,disclosure_allowed=True,production_allowed=False,prior_slot=7)))
  record['owner_scope']=scope
  old=decode(Path(record['main_review']['path']).read_bytes());old.update(owner_scope_sha256=scope['sha256'],correction_sha256=digest(proof))
  record['main_review']=f.pin('correction-review-'+str(time.monotonic_ns())+'.json',encoded(old))
  pin=f.pin('correction-authority-'+str(time.monotonic_ns())+'.json',encoded(record));f.record=record;f.authority=pin
 def test_exact_successor_preserves_prior_and_refuses_second_child(self):
  old={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
  with self.f.gate(),auth._simulated_captured_io():
   selected=self.f.f.selected;allocated=gate.authorize(self.f.state,selected);self.assertEqual(allocated['slot'],8)
   grant=History(self.f.state).read()[-2]['historical'];self.assertNotEqual(grant['request'],self.oldstart['historical']['request'])
   response=self.f.reply(grant)
   with diagnostics.DiagnosticTests().inputs(),framing.wire(response),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.state,selected,8,historical=True)['status'],'completed')
   with self.assertRaises(Refusal):gate.authorize(self.f.state,selected)
   with self.assertRaises(Refusal):c.run(self.f.state,selected,8,historical=True)
  for p,raw in old.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
  self.assertEqual(len(self.credit.read()),len(self.credit_rows)+1)
 def test_changed_receipt_terminal_credit_and_request_pins_refuse(self):
  for field in ('prior_receipt_sha256','prior_terminal_sha256','prior_credit_sha256','prior_request_sha256','new_request_sha256'):
   bad=copy.deepcopy(self.proof);bad[field]='f'*64;self.make_authority(bad)
   with self.subTest(field=field),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   self.assertFalse((self.f.state/'attempt-8').exists())
 def test_installed_issued_successor_uses_one_shot_and_preserves_history(self):
  import json,subprocess,sys,shutil,sysconfig
  from ai_movie_investigator.installation import install_runtime
  f=self.f;runtime=f.root/'installed-correction';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_text());f.manifest.clear();f.manifest.update(manifest)
  f.record['runtime_manifest_sha256']=digest(manifest);self.make_authority(self.proof)
  with f.gate():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,f.f.selected.data)
   response=f.reply(grant)
  template=Path('automation/snapshot_review_UNISSUED.py').read_text()
  interpreter=Path(sys.executable).resolve(strict=True);child_env=os.environ.copy()
  if sys.platform.startswith('linux'):
   interpreter=f.root/'fixture-correction-python';shutil.copyfile(Path(sys.executable).resolve(strict=True),interpreter);interpreter.chmod(0o700)
   library_dir=sysconfig.get_config_var('LIBDIR')
   if library_dir:child_env['LD_LIBRARY_PATH']=library_dir
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'correction-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=digest(self.prior),expected_slot=8)
  wrapper=f.root/'issued-correction-wrapper.py';wrapper.write_text(template.replace('ISSUED = None','ISSUED = '+repr(issued),1));wrapper.chmod(0o600)
  f.pin('correction-acceptance.json',encoded(dict(decision='accepted_exact_normalized_snapshot_assessment',wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),issued_pins=issued)))
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
  path=f.root/'correction-driver.py';path.write_text(driver)
  old={p:p.read_bytes() for p in f.state.rglob(FILENAME)}
  result=subprocess.run([str(interpreter),'-I','-S','-B',str(path)],cwd=runtime,env=child_env,capture_output=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
  self.assertIn(b'private_report_written',result.stdout)
  if sys.platform.startswith('linux'):self.assertIn(b'LINUX_FIXTURE_ACL_SIMULATED',result.stdout)
  self.assertTrue((f.output/'movie-review.html').exists())
  for p,raw in old.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
  self.assertEqual(len(self.credit.read()),len(self.credit_rows)+1)
 def test_wrong_phase_or_completed_old_refuses(self):
  with self.f.gate():
   with self.root.transaction(write=True) as (events,_):
    grant=gate.proposal(self.root,events,self.f.f.selected.data)
    for mutate in ('phase','completion'):
     changed=copy.deepcopy(events)
     if mutate=='phase':next(r for r in changed if r.get('type')=='supervised_diagnostic' and r.get('slot')==7)['phase']='response_parsing'
     else:changed.append(dict(type='supervised_completed',slot=7))
     with self.subTest(mutate=mutate),patch.object(self.root,'require_write_transaction'),self.assertRaises(Refusal):gate.validate_correction(self.root,changed,grant,creating=True)
if __name__=='__main__':unittest.main()
