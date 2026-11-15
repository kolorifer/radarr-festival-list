"""One deliberately bound invented v8 child; no live IO or quality claims."""
import copy,hashlib,io,time,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate,snapshot_review as review,supervised_credit as c,supervised_authorization as auth
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_snapshot_context_integration as previous
import test_supervised_envelope as framing

class WeighingIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.previous=previous.ContextIntegrationTests('test_wrong_pins_refuse_before_reservation');self.previous.setUp();self.addCleanup(self.previous.doCleanups)
  self.f=self.previous.f;self.root=self.previous.root;self.credit=self.previous.credit;self.p=self.previous.p
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,self.f.f.selected.data)
   response=decode(self.previous.response(grant,unresolved=True),65536);answer=decode(response['output'][-1]['content'][0]['text'])
   answer['result'][getattr(self,'withheld_field','rationale')]='Title/year/runtime differences need contextual evidence.'
   response['output'][-1]['content'][0]['text']=encoded(answer).decode()
   consume=auth.consume_snapshot_completion
   def proof(grant,answer):return dict(consume(grant,answer),simulated=False)
   from ai_movie_investigator import keychain_credential
   with framing.wire(encoded(response)),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()):
    gate.execute(self.f.state,self.f.f.selected,self.f.output)
  self.events=self.root.read();self.start=next(x for x in self.events if x.get('type')=='supervised_standing_attempt_started' and x.get('slot')==14)
  completion=next(x for x in self.events if x.get('type')=='supervised_completed' and x.get('slot')==14)
  report=completion['historical_report'];self.rows=History(self.f.state/'attempt-14').read();self.credit_rows=self.credit.read()
  self.proof=dict(kind='snapshot_weighing_reassessment_v1',prior_slot=14,prior_start_sha256=digest(self.start),prior_grant_sha256=digest(grant),prior_completion_sha256=digest(completion),prior_report_sha256=digest(report),prior_retained_reply_sha256=report['retained_reply_hash'],prior_attempt_sha256=digest(self.rows),prior_receipt_sha256=digest(self.rows[-1]),prior_credit_sha256=digest(self.credit_rows),prior_credit_count=len(self.credit_rows),prior_request_sha256=digest(grant['request']),root_prefix_sha256=digest(self.events),new_request_sha256=digest(review.build_film_weighing(self.p)['request']),prior_status=report['result']['status'],prior_candidate=report['result']['candidate'],prior_prose_handling=report['prose_handling'],reviewed=True)
  from ai_movie_investigator.credit_test import MINI_PROFILE
  e=copy.deepcopy(self.f.f.selected.data);e.update(model=MINI_PROFILE['model'],policy=MINI_PROFILE['policy'],input_rate=MINI_PROFILE['input_rate'],cached_input_rate=MINI_PROFILE['cached_input_rate'],output_rate=MINI_PROFILE['output_rate'])
  self.f.f.selected=self.f.f.select(e)
  self.proof.update(model_profile=copy.deepcopy(MINI_PROFILE),model_evidence_sha256=digest(e))
  self.make_authority(self.proof)
 def make_authority(self,proof):
  f=self.f;record=copy.deepcopy(f.record);record.pop('context_reassessment',None);record.update(root_prefix_sha256=digest(self.events),root_count=len(self.events),weighing_reassessment=copy.deepcopy(proof))
  out=f.root/('context-output-'+str(time.monotonic_ns()));out.mkdir(mode=0o700);st=out.stat();record.update(output_dir=str(out),output_identity=[st.st_dev,st.st_ino]);f.output=out
  scope=f.pin('context-scope-'+str(time.monotonic_ns())+'.json',encoded(dict(kind='snapshot_weighing_scope_v1',case_id=self.p['case_id'],version=self.p['version'],max_calls=1,disclosure_allowed=True,production_allowed=False,prior_slot=14,model_profile_sha256=digest(proof['model_profile']))));record['owner_scope']=scope
  previous=decode(Path(record['main_review']['path']).read_bytes());previous.pop('context_reassessment_sha256',None);previous.update(owner_scope_sha256=scope['sha256'],weighing_reassessment_sha256=digest(proof))
  record['main_review']=f.pin('context-review-'+str(time.monotonic_ns())+'.json',encoded(previous));f.record=record;f.authority=f.pin('context-authority-'+str(time.monotonic_ns())+'.json',encoded(record))
 def response(self,grant,*,unresolved=False,long_text=False):
  response=decode(self.previous.response(grant,unresolved=unresolved),65536);answer=decode(response['output'][-1]['content'][0]['text']);r=answer['result']
  response['model']=grant['request']['model']
  r['rationale']='Title/year/runtime differences are metadata; matching people support the film.'
  if unresolved:r['primary_blocker'].update(support_considered='The listing title and cast support the catalogue.',material_conflict='The collector label refers to another subject whose origin is unverified.')
  if long_text:
   r['rationale']='𐐀'*600;r['uncertainty']='𐐀'*300
   if unresolved:
    r['primary_blocker'].update(support_considered='𐐀'*140,material_conflict='𐐀'*140)
    r['additional_blockers']=[dict(aspect=aspect,reason='ambiguous_film_evidence',support_considered='𐐀'*140,material_conflict='𐐀'*140) for aspect in ('year','people','runtime_description','runtime_nfo','ids')]
  self.assertLessEqual(len(encoded(answer)),32768)
  response['output'][-1]['content'][0]['text']=encoded(answer).decode();return encoded(response)
 def test_wrong_pins_refuse_before_reservation(self):
  for field in ('prior_completion_sha256','prior_report_sha256','prior_receipt_sha256','prior_credit_sha256','new_request_sha256','model_evidence_sha256'):
   bad=copy.deepcopy(self.proof);bad[field]='f'*64;self.make_authority(bad)
   with self.subTest(field=field),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   self.assertFalse((self.f.state/'attempt-15').exists())
 def test_model_scope_pricing_and_remaining_credit(self):
  from fractions import Fraction
  from ai_movie_investigator.credit_test import retained_total
  original=copy.deepcopy(self.f.f.selected.data);proof=copy.deepcopy(self.proof)
  with self.assertRaises(Refusal):c.validate_evidence(original,time.time(),standing=True)
  available=retained_total(self.credit_rows,original['project'])+Fraction(14,100)
  changes=[dict(input_rate=[1,1]),dict(output_rate=[1,1]),dict(cached_input_rate=[1,1]),dict(policy={}),dict(model_access_reference='unknown'),dict(paid_fallback=True),dict(context_window=399999),dict(available_usd=[available.numerator,available.denominator])]
  for delta in changes:
   e=dict(original,**delta);self.f.f.selected=self.f.f.select(e);bad=copy.deepcopy(proof);bad['model_evidence_sha256']=digest(e);self.make_authority(bad)
   with self.subTest(fields=list(delta)),self.f.gate(),self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)
   self.assertEqual(self.credit.read(),self.credit_rows);self.assertFalse((self.f.state/'attempt-15').exists())
  self.f.f.selected=self.f.f.select(original);bad=copy.deepcopy(proof);bad['model_profile']['reserved_usd']=[3,100];self.make_authority(bad)
  with self.assertRaises(Refusal),self.f.gate():pass
 def test_wrong_response_model_burns_full_reservation(self):
  from ai_movie_investigator import keychain_credential
  from ai_movie_investigator.credit_test import retained_total,MINI_DEBIT
  before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,self.f.f.selected.data)
   response=decode(self.response(grant,unresolved=True),65536);response['model']='gpt-5-nano-2025-08-07'
   with framing.wire(encoded(response)),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()),self.assertRaises(Refusal):gate.execute(self.f.state,self.f.f.selected,self.f.output)
   count=len(self.credit.read())
   with self.assertRaises(Refusal):gate.execute(self.f.state,self.f.f.selected,self.f.output)
   self.assertEqual(len(self.credit.read()),count)
  rows=self.credit.read();self.assertEqual(rows[-1]['reserved_usd'],[15,100]);self.assertEqual(rows[-1]['model'],'gpt-5-mini-2025-08-07')
  self.assertEqual(retained_total(rows,self.f.f.selected.data['project'])-retained_total(self.credit_rows,self.f.f.selected.data['project']),MINI_DEBIT)
  self.assertEqual(len(History(self.f.state/'attempt-15').read()),2);self.assertFalse((self.f.output/'movie-review.html').exists())
  terminal=[r for r in self.root.read() if r.get('slot')==15 and r.get('type')=='supervised_diagnostic'];self.assertEqual(terminal[-1]['reason'],'responses_model_mismatch')
  for p,raw in before.items():
   if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
   else:self.assertTrue(p.read_bytes().startswith(raw))
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
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'result-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=f.record['root_prefix_sha256'],expected_slot=15)
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
  completion=next(r for r in self.root.read() if r.get('slot')==15 and r.get('type')=='supervised_completed')
  self.assertEqual(completion['historical_report']['previous_assessment']['rationale'],self.proof['prior_prose_handling']['rationale']['status'])
  self.assertEqual(completion['historical_report']['previous_assessment']['uncertainty'],self.proof['prior_prose_handling']['uncertainty']['status'])
  html=(f.output/'movie-review.html').read_text();self.assertIn('Computed evidence comparisons',html);self.assertIn('unresolved' if unresolved else 'supported_candidate',html)
 def test_installed_weighing_unresolved(self):self.installed(True)
 def test_installed_weighing_supported(self):self.installed(False)
