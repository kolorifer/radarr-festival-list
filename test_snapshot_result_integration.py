"""Invented missing-blocker refusal and one result-contract successor."""
import copy,hashlib,io,time,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_snapshot_comparison_integration as comparison
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing


class ResultIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.previous=comparison.ComparisonIntegrationTests('test_fake_wire_one_child_preserves_receipts_and_comparisons');self.previous.setUp();self.addCleanup(self.previous.doCleanups)
  self.f=self.previous.f;self.root=self.previous.root;self.credit=self.previous.credit;self.p=self.previous.p
  with self.f.gate(),auth._simulated_captured_io():
   gate.authorize(self.f.state,self.f.f.selected);grant=self.root.read()[-2]['historical']
   response=decode(self.previous.response(grant),65536);answer=decode(response['output'][-1]['content'][0]['text'])
   answer['result'].update(status='unresolved',candidate=None,citations=[]);answer['film_blockers']=[]
   response['output'][-1]['content'][0]['text']=encoded(answer).decode()
   with diagnostics.DiagnosticTests().inputs(),framing.wire(encoded(response)),redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(Refusal,'snapshot_comparison_blocker_missing'):c.run(self.f.state,self.f.f.selected,12,historical=True)
  self.events=self.root.read();self.start=next(x for x in self.events if x.get('type')=='supervised_standing_attempt_started' and x.get('slot')==12)
  self.terminal=next(x for x in self.events if x.get('type')=='supervised_diagnostic' and x.get('slot')==12)
  self.rows=History(self.f.state/'attempt-12').read();self.credit_rows=self.credit.read()
  assert (self.terminal['phase'],self.terminal['reason'],self.terminal['category'])==('receipt_recorded','snapshot_comparison_blocker_missing','snapshot_refused')
  self.proof=dict(kind='snapshot_result_correction_v1',prior_slot=12,prior_start_sha256=digest(self.start),prior_grant_sha256=digest(grant),prior_terminal_sha256=digest(self.terminal),prior_attempt_sha256=digest(self.rows),prior_receipt_sha256=digest(self.rows[-1]),prior_credit_sha256=digest(self.credit_rows),prior_credit_count=len(self.credit_rows),prior_request_sha256=digest(grant['request']),root_prefix_sha256=digest(self.events),new_request_sha256=digest(review.build_film_result(self.p)['request']),reviewed=True)
  self.make_authority(self.proof)
 def make_authority(self,proof):
  f=self.f;record=copy.deepcopy(f.record);record.pop('comparison_correction',None);record.update(root_prefix_sha256=digest(self.events),root_count=len(self.events),result_correction=copy.deepcopy(proof))
  out=f.root/('result-output-'+str(time.monotonic_ns()));out.mkdir(mode=0o700);st=out.stat();record.update(output_dir=str(out),output_identity=[st.st_dev,st.st_ino]);f.output=out
  scope=f.pin('result-scope-'+str(time.monotonic_ns())+'.json',encoded(dict(kind='snapshot_result_scope_v1',case_id=self.p['case_id'],version=self.p['version'],max_calls=1,disclosure_allowed=True,production_allowed=False,prior_slot=12)));record['owner_scope']=scope
  previous=decode(Path(record['main_review']['path']).read_bytes());previous.pop('comparison_correction_sha256',None);previous.update(owner_scope_sha256=scope['sha256'],result_correction_sha256=digest(proof))
  record['main_review']=f.pin('result-review-'+str(time.monotonic_ns())+'.json',encoded(previous));f.record=record;f.authority=f.pin('result-authority-'+str(time.monotonic_ns())+'.json',encoded(record))
 def response(self,grant,*,unresolved=False,long_text=False):
  response=decode(self.previous.response(grant),65536);answer=decode(response['output'][-1]['content'][0]['text']);answer.pop('film_blockers');r=answer['result'];citations=r.pop('citations')
  if unresolved:r.update(status='unresolved',candidate=None,primary_blocker=dict(aspect='title',reason='ambiguous_film_evidence'),additional_blockers=[])
  else:r.update(source_citation=citations[0],catalogue_citation=citations[1],primary_blocker=None,additional_blockers=[])
  if long_text:r['rationale']=r['uncertainty']='🎞'*600
  response['output'][-1]['content'][0]['text']=encoded(answer).decode();return encoded(response)
 def test_fake_unresolved_receipt_report_and_replay_refusal(self):
  from ai_movie_investigator import keychain_credential
  old={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,self.f.f.selected.data)
   response=self.response(grant,unresolved=True,long_text=True);consume=auth.consume_snapshot_completion
   def proof(grant,answer):return dict(consume(grant,answer),simulated=False)
   with framing.wire(response),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()):
    self.assertEqual(gate.execute(self.f.state,self.f.f.selected,self.f.output)['status'],'private_report_written')
   html=(self.f.output/'movie-review.html').read_text();self.assertIn('Computed evidence comparisons',html);self.assertIn('did not provide a required film blocker',html);self.assertIn('ambiguous film evidence',html)
   with self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
  for p,raw in old.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
  self.assertEqual(len(self.credit.read()),len(self.credit_rows)+1)
 def test_changed_terminal_and_pins_refuse_before_reservation(self):
  for field in ('prior_start_sha256','prior_grant_sha256','prior_terminal_sha256','prior_receipt_sha256','prior_credit_sha256','new_request_sha256'):
   bad=copy.deepcopy(self.proof);bad[field]='f'*64;self.make_authority(bad)
   with self.subTest(field=field),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   self.assertFalse((self.f.state/'attempt-13').exists())
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
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'result-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=f.record['root_prefix_sha256'],expected_slot=13)
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
  driver+='selected_raw='+repr(response)+"\nframing='chunked'\n"+framing.wire_code()
  driver+='\nnamespace=runpy.run_path('+repr(str(wrapper))+',run_name="fixture_wrapper")\nsys.argv=['+repr(str(wrapper))+',"--main-accepted-snapshot-review"]\n'
  driver+='with a._simulated_captured_io(),wire_fixture("completed"):\n namespace["main"]()\n'
  path=f.root/'result-driver.py';path.write_text(driver)
  result=subprocess.run([str(interpreter),'-I','-S','-B',str(path)],cwd=runtime,env=env,capture_output=True,timeout=90)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));self.assertIn(b'private_report_written',result.stdout)
  html=(f.output/'movie-review.html').read_text();self.assertIn('Computed evidence comparisons',html);self.assertIn('unresolved' if unresolved else 'supported_candidate',html)
 def test_installed_unresolved(self):self.installed(True)
 def test_installed_supported(self):self.installed(False)
