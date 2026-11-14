"""Same unstarted slot freshness; invented private state, fake HTTP only."""
import copy,io,json,time,unittest,subprocess,sys
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path
from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a
from ai_movie_investigator.contracts import encoded,digest,Refusal
from ai_movie_investigator.history import History,FILENAME
import test_captured_activation as fixtures
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class CapturedFreshness(unittest.TestCase):
 def setUp(self):
  self.x=fixtures.Activation('test_exact_context_receipt_report_and_reset_without_gate_patch');self.x.setUp();self.addCleanup(self.x.doCleanups)
  self.f=self.x.f;self.slot=7 # Unit fixture file bytes; installed child uses real guards.
  e=dict(self.f.selected.data,expires_at=time.time()+30)
  p=self.x.root/'old-short-evidence.json';p.write_bytes(encoded(e));p.chmod(0o600);self.f.selected=c.read_evidence(p)
  with self.f.root.transaction(write=True) as (events,_):
   with self.f.case.transaction(write=True) as (rows,_):self.f.consent=n.captured_consent(self.f.root,events,self.f.case,rows,digest(self.f.request),e)
  self.f.path.write_bytes(encoded(self.f.consent));self.x.record['authority']['sha256']=digest(self.f.consent);self.x.record['expires_at']=e['expires_at'];self.x.write_record()
  with self.x.context(),a._simulated_captured_io():self.f.authorize()
  if getattr(self,'continuation',False):
   with self.x.context(),a._simulated_captured_io(),diagnostics.DiagnosticTests().inputs(),diagnostics.wire_fixture('rejected'),redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(Refusal,'responses_http_401'):c.run(self.f.f.state,self.f.selected,7,captured=True)
   self.slot=8;e=dict(e,owner_reference='Owner corrected rejected credential')
   p=self.x.root/'successor-evidence.json';p.write_bytes(encoded(e));p.chmod(0o600);self.f.selected=c.read_evidence(p)
   with self.f.root.transaction(write=True) as (events,_):
    with self.f.case.transaction(write=True) as (rows,_):self.f.consent=n.captured_continuation_consent(self.f.root,events,self.f.case,rows,digest(self.f.request),e,prior_slot=7,owner_reference=e['owner_reference'])
   self.f.path=self.x.root/'successor.json';self.f.path.write_bytes(encoded(self.f.consent));self.f.path.chmod(0o600);self.x.record['authority']=dict(path=str(self.f.path),sha256=digest(self.f.consent));self.x.write_record()
   with self.x.context(),a._simulated_captured_io():self.f.authorize()
  self.before=(self.f.f.state/FILENAME).read_bytes();self.case_before=(self.f.case.directory/FILENAME).read_bytes();self.credit_before=(self.f.f.state/'credit'/FILENAME).read_bytes()
  self.now=e['expires_at']+1
  self.clock=patch.object(time,'time',side_effect=lambda:self.now);self.clock.start();self.addCleanup(self.clock.stop)
  original=History.__init__
  def fixed(history,directory,clock=None):original(history,directory,clock=lambda:self.now)
  self.hclock=patch.object(History,'__init__',fixed);self.hclock.start();self.addCleanup(self.hclock.stop)
  self.f.root.clock=self.f.case.clock=lambda:self.now
  fix=dict(kind='captured_slot_access_fix',slot=self.slot,root_prefix_sha256=digest(self.f.root.read()),owner_reference='Owner verified local access correction',material_access_fix_verified=True,prior_failure='keychain_denied',issued_at=self.now-1,expires_at=self.now+90)
  p=self.x.root/'access-fix.json';p.write_bytes(encoded(fix));p.chmod(0o600);self.fix=dict(path=str(p),sha256=digest(fix))
  e=dict(e,observed_at=self.now,expires_at=self.now+60,owner_reference=fix['owner_reference']+'; exact fix '+digest(fix))
  p=self.x.root/'fresh-evidence.json';p.write_bytes(encoded(e));p.chmod(0o600);self.f.selected=c.read_evidence(p)
 def propose(self):
  with self.f.root.transaction(write=True) as (events,_):
   with self.f.case.transaction(write=True) as (rows,_):self.f.consent=n.captured_freshness_consent(self.f.root,events,self.f.case,rows,self.f.selected.data,self.fix)
  self.f.path=self.x.root/'fresh-authority.json';self.f.path.write_bytes(encoded(self.f.consent));self.f.path.chmod(0o600)
  self.x.record.update(issued_at=self.now,expires_at=self.f.selected.data['expires_at'],authority=dict(path=str(self.f.path),sha256=digest(self.f.consent)));self.x.write_record()
 def refresh(self):return n.refresh_captured(self.f.f.state,self.f.selected,self.f.case.directory,self.f.path,digest(self.f.consent),self.fix)
 def test_same_slot_preserved_prefix_and_complete_report_once(self):
  self.propose()
  with self.x.context(),a._simulated_captured_io():
   self.assertEqual(self.refresh()['slot'],7)
   self.assertTrue((self.f.f.state/FILENAME).read_bytes().startswith(self.before))
   self.assertEqual((self.f.case.directory/FILENAME).read_bytes(),self.case_before);self.assertEqual((self.f.f.state/'credit'/FILENAME).read_bytes(),self.credit_before)
   self.assertEqual(History(self.f.f.state/'attempt-7').read(),[])
   with self.assertRaisesRegex(Refusal,'captured_freshness_state'):self.refresh()
   with diagnostics.DiagnosticTests().inputs(),framing.wire(self.f.response()),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.f.state,self.f.selected,7,captured=True,clock=lambda:self.now)['status'],'completed')
   with self.assertRaises(Refusal):c.run(self.f.f.state,self.f.selected,7,captured=True,clock=lambda:self.now)
  report=self.f.case.read()[-1]['report'];self.assertEqual(report['receipt_hash'],digest(History(self.f.f.state/'attempt-7').read()[-1]));self.assertFalse(report['draft']['sent'])
  self.assertEqual(len(History(self.f.f.state/'credit').read()),6);self.assertFalse((self.f.f.state/'attempt-8').exists())
 def test_access_fix_changes_refuse_before_start(self):
  self.propose()
  with self.x.context():
   self.refresh();p=Path(self.fix['path']);raw=p.read_bytes();p.unlink();p.write_bytes(raw);p.chmod(0o600)
   with patch.object(c,'prompt_credential',side_effect=AssertionError('credential')),self.assertRaisesRegex(Refusal,'captured_freshness_access_fix'):
    c.run(self.f.f.state,self.f.selected,7,captured=True,clock=lambda:self.now)
  self.assertEqual(History(self.f.f.state/'attempt-7').read(),[]);self.assertEqual((self.f.f.state/'credit'/FILENAME).read_bytes(),self.credit_before)
 def test_owner_account_and_original_request_pins_refuse(self):
  self.propose();self.f.consent['request']['store']=True;self.f.path.write_bytes(encoded(self.f.consent));self.x.record['authority']['sha256']=digest(self.f.consent);self.x.write_record()
  with self.x.context(),self.assertRaisesRegex(Refusal,'captured_authority_changed'):self.refresh()
  self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.before)
 def test_preexisting_attempt_work_refuses(self):
  with History(self.f.f.state/'attempt-7').transaction(write=True) as (_,append):append(dict(type='uncertain'))
  with self.assertRaises(Refusal):self.propose()
  self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.before)
 def test_not_expired_and_wrong_fix_refuse(self):
  self.now-=2
  with self.assertRaisesRegex(Refusal,'captured_freshness_not_expired'):self.propose()
  self.now+=2;self.fix['sha256']='0'*64
  with self.assertRaisesRegex(Refusal,'captured_freshness_access_fix'):self.propose()
  self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.before)

 def test_changed_account_and_owner_fix_are_rejected(self):
  original=self.f.selected
  for delta in ({'account_reference':'other'},{'owner_reference':'No owner access fix binding'}):
   p=self.x.root/'bad-evidence.json';p.write_bytes(encoded(dict(original.data,**delta)));p.chmod(0o600);self.f.selected=c.read_evidence(p)
   with self.assertRaises(Refusal):self.propose()
   self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.before)
  self.f.selected=original
 def test_started_root_record_cannot_refresh(self):
  rows=self.f.root.read();start=rows[-2]
  with self.f.root.transaction(write=True) as (_,append):append(dict(type='supervised_started',slot=7,at=rows[-1]['at']+0.001,evidence_hash=start['evidence_hash']))
  with self.assertRaisesRegex(Refusal,'captured_freshness_started'):self.propose()
 def test_runtime_rejects_changed_case_without_debit(self):
  self.propose()
  with self.x.context():
   self.refresh()
   with self.f.case.transaction(write=True) as (_,append):append(dict(type='unrelated_observation',at=self.now))
   with patch.object(c,'prompt_credential',side_effect=AssertionError('credential')),self.assertRaisesRegex(Refusal,'captured_freshness_changed'):
    c.run(self.f.f.state,self.f.selected,7,captured=True,clock=lambda:self.now)
  self.assertEqual((self.f.f.state/'credit'/FILENAME).read_bytes(),self.credit_before)
 def test_prior_401_successor_refresh_preserves_debit_and_report(self):
  self.doCleanups();self.continuation=True;self.setUp();self.propose()
  old=(self.f.f.state/'attempt-7'/FILENAME).read_bytes()
  with self.x.context(),a._simulated_captured_io():
   self.assertEqual(self.refresh()['slot'],8)
   with diagnostics.DiagnosticTests().inputs(),framing.wire(self.f.response()),redirect_stdout(io.StringIO()):
    self.assertEqual(c.run(self.f.f.state,self.f.selected,8,captured=True,clock=lambda:self.now)['status'],'completed')
  self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),old)
  credit=History(self.f.f.state/'credit').read();self.assertEqual(len(credit),7)
  self.assertEqual(credit[-1]['wire_request_hash'],credit[-2]['request_hash']);self.assertNotEqual(credit[-1]['request_hash'],credit[-2]['request_hash'])
  self.assertEqual(self.f.case.read()[-1]['report']['receipt_hash'],digest(History(self.f.f.state/'attempt-8').read()[-1]));self.assertFalse((self.f.f.state/'attempt-9').exists())
 def test_installed_same_slot_complete_or_explicit_host_refusal(self):
  from ai_movie_investigator.installation import install_runtime
  self.propose();runtime=self.x.root/'installed-freshness';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_bytes());self.assertGreater(len(manifest),0)
  self.x.record['runtime_manifest_sha256']=digest(manifest);self.x.write_record()
  code="""import sys,runpy,atexit,ctypes,time
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen' or (event=='ctypes.dlopen' and args[0]!='/usr/lib/libSystem.B.dylib'):
  attempts.append(event);raise AssertionError('unexpected external I/O')
sys.addaudithook(audit)
@atexit.register
def done():print('TRIPWIRE='+str(len(attempts)))
"""
  code+='time.time=lambda:'+repr(self.now)+'\nsys.path.insert(0,'+repr(str(runtime))+')\n'
  code+="""from pathlib import Path
from ai_movie_investigator import new_case as n,supervised_credit as c,keychain_credential as k,supervised_authorization as a
from ai_movie_investigator.private_files import private_chain
from ai_movie_investigator.contracts import Refusal
k._native=lambda project:b'sk-DUMMY_CAPTURED'
"""
  code+='try:\n with private_chain(Path('+repr(str(self.x.root))+')):pass\nexcept Refusal as error:\n if str(error)!="storage_acl":raise\n print("INSTALLED_HOST_REFUSAL=storage_acl");raise SystemExit(0)\n'
  code+='selected_raw='+repr(self.f.response())+"\nframing='chunked'\n"+framing.wire_code()
  code+='\nwith n.approved_captured_wrapper('+repr(str(self.x.path))+','+repr(self.x.sha)+'),a._simulated_captured_io(),wire_fixture("completed"):\n'
  code+=' n.refresh_captured('+repr(str(self.f.f.state))+',c.read_evidence('+repr(str(self.f.selected.path))+'),'+repr(str(self.f.case.directory))+','+repr(str(self.f.path))+','+repr(digest(self.f.consent))+','+repr(self.fix)+')\n'
  code+=' sys.argv='+repr(['ai_movie_investigator.supervised_credit','--state',str(self.f.f.state),'run-captured-keychain','--evidence',str(self.f.selected.path),'--slot','7'])+'\n'
  code+=" runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)\n"
  script=self.x.root/'installed-check.py';script.write_text(code)
  result=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=runtime,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=40)
  output=result.stdout+result.stderr;self.assertEqual(result.returncode,0,output);self.assertIn(b'TRIPWIRE=0',output)
  if b'INSTALLED_HOST_REFUSAL=storage_acl' in output:
   self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',output);self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.before);self.assertEqual((self.f.case.directory/FILENAME).read_bytes(),self.case_before)
   return
  self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
  self.assertEqual(self.f.case.read()[-1]['report']['receipt_hash'],digest(History(self.f.f.state/'attempt-7').read()[-1]))
  self.assertTrue((self.f.f.state/FILENAME).read_bytes().startswith(self.before));self.assertFalse((self.f.f.state/'attempt-8').exists())

if __name__=='__main__':unittest.main()
