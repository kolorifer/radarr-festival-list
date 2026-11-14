"""One explicit captured 401 successor; invented state and fake HTTP only."""
import copy,io,json,time,unittest,subprocess,sys
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a
from ai_movie_investigator.contracts import encoded,digest,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_captured_activation as activation_fixture
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class CapturedContinuation(unittest.TestCase):
 def setUp(self):
  self.x=activation_fixture.Activation('test_exact_context_receipt_report_and_reset_without_gate_patch');self.x.setUp();self.addCleanup(self.x.doCleanups)
  self.x.reader.stop() # Use the actual private-file reader for this continuation fixture.
  self.f=self.x.f
 def fail_first(self,variant='rejected'):
  with self.x.context(),a._simulated_captured_io():
   self.f.authorize()
   with diagnostics.DiagnosticTests().inputs(),diagnostics.wire_fixture(variant),redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(Refusal,'responses_http_401' if variant=='rejected' else 'invalid_json'):c.run(self.f.f.state,self.f.selected,7,captured=True)
  self.oldroot=(self.f.f.state/FILENAME).read_bytes();self.oldcase=(self.f.case.directory/FILENAME).read_bytes();self.oldcredit=(self.f.f.state/'credit'/FILENAME).read_bytes();self.oldattempt=(self.f.f.state/'attempt-7'/FILENAME).read_bytes()
 def propose(self,change=None):
  evidence=dict(self.f.selected.data,owner_reference='Explicit owner updated credential and requests one continuation')
  ep=self.x.root/'fresh-evidence.json';ep.write_bytes(encoded(evidence));ep.chmod(0o600);self.f.selected=c.read_evidence(ep)
  with self.f.root.transaction(write=True) as (events,_):
   with self.f.case.transaction(write=True) as (rows,_):
    consent=n.captured_continuation_consent(self.f.root,events,self.f.case,rows,digest(self.f.request),evidence,prior_slot=7,owner_reference=evidence['owner_reference'])
  if change:change(consent)
  self.f.consent=consent;self.f.path=self.x.root/'successor-authority.json';self.f.path.write_bytes(encoded(consent));self.f.path.chmod(0o600)
  self.x.record['authority']=dict(path=str(self.f.path),sha256=digest(consent));self.x.write_record()
 def test_same_request_new_slot_retains_failure_and_completes_once(self):
  self.fail_first();self.propose()
  with self.x.context(),a._simulated_captured_io():
   self.assertEqual(self.f.authorize()['slot'],8)
   with diagnostics.DiagnosticTests().inputs(),framing.wire(self.f.response()),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.f.state,self.f.selected,8,captured=True)['status'],'completed')
   with self.assertRaises(Refusal):self.f.authorize()
   with self.assertRaises(Refusal):c.run(self.f.f.state,self.f.selected,8,captured=True)
  for p,b in [(self.f.f.state/FILENAME,self.oldroot),(self.f.case.directory/FILENAME,self.oldcase),(self.f.f.state/'credit'/FILENAME,self.oldcredit)]:self.assertTrue(p.read_bytes().startswith(b))
  self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),self.oldattempt)
  credit=History(self.f.f.state/'credit').read();self.assertEqual(len(credit),7)
  self.assertEqual(credit[-1]['wire_request_hash'],credit[-2]['request_hash']);self.assertNotEqual(credit[-1]['request_hash'],credit[-2]['request_hash'])
  report=self.f.case.read()[-1]['report'];self.assertEqual(report['receipt_hash'],digest(History(self.f.f.state/'attempt-8').read()[-1]));self.assertFalse(report['draft']['sent'])
  self.assertFalse((self.f.f.state/'attempt-9').exists())
 def test_uncertain_or_other_terminal_cannot_continue(self):
  self.fail_first('malformed')
  with self.assertRaisesRegex(Refusal,'captured_continuation_prior'):self.propose()
  self.assertFalse((self.f.f.state/'attempt-8').exists())
 def test_mismatched_request_or_attestation_refuses_before_allocation(self):
  self.fail_first();self.propose(lambda a:a['continuation'].update(material_credential_correction_attested=False))
  with self.assertRaises(Refusal),self.x.context():self.f.authorize()
  self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.oldroot)
 def test_prior_receipt_cannot_continue(self):
  with self.x.context(),a._simulated_captured_io():self.f.authorize();self.f.run_case()
  with self.assertRaises(Refusal):self.propose()
 def test_wrong_request_binding_refuses(self):
  self.fail_first();self.propose(lambda a:a['request'].update(store=True))
  with self.assertRaises(Refusal),self.x.context():self.f.authorize()
  self.assertFalse((self.f.f.state/'attempt-8').exists())
 def test_cannot_chain_a_second_correction(self):
  self.fail_first();self.propose()
  with self.x.context(),a._simulated_captured_io():
   self.f.authorize()
   with diagnostics.DiagnosticTests().inputs(),diagnostics.wire_fixture('rejected'),redirect_stdout(io.StringIO()):
    with self.assertRaises(Refusal):c.run(self.f.f.state,self.f.selected,8,captured=True)
  with self.f.root.transaction(write=True) as (events,_):
   with self.f.case.transaction(write=True) as (rows,_):
    e=dict(self.f.selected.data,owner_reference='Another changed key')
    with self.assertRaisesRegex(Refusal,'captured_continuation_owner'):
     n.captured_continuation_consent(self.f.root,events,self.f.case,rows,digest(self.f.request),e,prior_slot=8,owner_reference=e['owner_reference'])
 def test_installed_module_completes_or_refuses_unsafe_host(self):
  from ai_movie_investigator.installation import install_runtime
  self.fail_first();self.propose()
  runtime=self.x.root/'installed-successor';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_bytes())
  self.x.record['runtime_manifest_sha256']=digest(manifest);self.x.write_record()
  code="""import sys,runpy,atexit,ctypes
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen' or (event=='ctypes.dlopen' and args[0]!='/usr/lib/libSystem.B.dylib'):
  attempts.append(event);raise AssertionError('unexpected external I/O')
sys.addaudithook(audit)
@atexit.register
def done():print('TRIPWIRE='+str(len(attempts)))
"""
  code+='sys.path.insert(0,'+repr(str(runtime))+')\n'
  code+="""from pathlib import Path
from ai_movie_investigator import new_case as n,supervised_credit as c,keychain_credential as k,supervised_authorization as a
from ai_movie_investigator.history import History
from ai_movie_investigator.contracts import digest
k._native=lambda project:b'sk-DUMMY_CAPTURED'
"""
  code+='from ai_movie_investigator.private_files import private_chain\nfrom ai_movie_investigator.contracts import Refusal\n'
  code+='try:\n with private_chain(Path('+repr(str(self.x.root))+')):pass\nexcept Refusal as error:\n if str(error)!="storage_acl":raise\n print("INSTALLED_HOST_REFUSAL=storage_acl");raise SystemExit(0)\n'
  code+='selected_raw='+repr(self.f.response())+"\nframing='chunked'\n"+framing.wire_code()
  code+='\nwith n.approved_captured_wrapper('+repr(str(self.x.path))+','+repr(self.x.sha)+'),a._simulated_captured_io(),wire_fixture("completed"):\n'
  code+=' n.authorize_captured('+','.join(map(repr,[str(self.f.f.state)]))+',c.read_evidence('+repr(str(self.f.selected.path))+'),'+repr(str(self.f.case.directory))+','+repr(digest(self.f.request))+','+repr(str(self.f.path))+','+repr(digest(self.f.consent))+')\n'
  code+=' sys.argv='+repr(['ai_movie_investigator.supervised_credit','--state',str(self.f.f.state),'run-captured-keychain','--evidence',str(self.f.selected.path),'--slot','8'])+'\n'
  code+=" runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)\n"
  script=self.x.root/'installed-successor.py';script.write_text(code)
  result=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=runtime,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=40)
  output=result.stdout+result.stderr
  self.assertEqual(result.returncode,0,output);self.assertIn(b'TRIPWIRE=0',output)
  if b'INSTALLED_HOST_REFUSAL=storage_acl' in output:
   # Hosted ancestors may carry ACLs. Prove fail-closed behavior; never mask ACL I/O.
   self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',output)
   self.assertFalse((self.f.f.state/'attempt-8').exists())
   self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.oldroot)
   self.assertEqual((self.f.case.directory/FILENAME).read_bytes(),self.oldcase)
   return
  self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
  report=self.f.case.read()[-1]['report'];self.assertEqual(report['receipt_hash'],digest(History(self.f.f.state/'attempt-8').read()[-1]))
  self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),self.oldattempt)
 def test_no_supplied_answer_fallback_after_failure(self):
  self.fail_first()
  with self.assertRaisesRegex(Refusal,'captured_completion_unbound'):n.complete(self.f.case,digest(self.f.request),self.f.reply,dict(mode='supervised_supplied',chat_reference='forbidden'))

if __name__=='__main__':unittest.main()
