"""Trusted-wrapper delta with invented files/receipt and fake socket I/O only."""
import copy,hashlib,io,json,os,socket,sys,time,unittest,subprocess
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import new_case as n, supervised_credit as c, supervised_authorization as a, installation
from ai_movie_investigator.contracts import encoded,digest,Refusal
from ai_movie_investigator.replay import synthetic_case
from ai_movie_investigator.history import History
import test_captured_generation as captured_fixture
h=lambda x:hashlib.sha256(x).hexdigest()
class Activation(unittest.TestCase):
 def setUp(self):
  # Invented fixture filesystem I/O stays entirely in the /private/tmp checkout.
  # It cannot establish production ancestor/ACL evidence; installed guards unchanged.
  self.reader=patch.object(c,'read_private',side_effect=lambda p,limit:Path(p).read_bytes());self.reader.start();self.addCleanup(self.reader.stop)
  self.f=captured_fixture.CapturedGenerationTests('test_connected_receipt_draft_and_restarts');self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.root=self.f.f.f.root;raw,_,_=synthetic_case(165);self.body=encoded(raw);b=self.f.packet['binding']
  self.receipt=dict(version=1,source=b['source'],channel='outcome',case_id=b['case_id'],case_version=b['version'],event_id=b['occurrence']['event_id'],selection_event='a'*64,delivery_rowid=b['occurrence']['delivery_id'],evidence_id='b'*64,source_time=1,received_at=2,grant_sha256='c'*64,body_sha256=h(self.body),body_bytes=len(self.body),privacy='private_local_raw_observer_body_no_api_disclosure',api_disclosure_authorized=False)
  self.manifest={'invented.py':'d'*64};self.runtime=patch.object(installation,'verify_installation',return_value=self.manifest);self.runtime.start();self.addCleanup(self.runtime.stop)
  def pin(name,data):
   p=self.root/(name+'.json');p.write_bytes(data);p.chmod(0o600);return {'path':str(p),'sha256':h(data)}
  self.record=dict(kind='trusted_wrapper_one_captured_case_v1',owner_scope=pin('owner',encoded({'fixture':'owner scope'})),main_review=pin('review',encoded({'fixture':'review'})),authority={'path':str(self.f.path),'sha256':h(self.f.path.read_bytes())},body=pin('body',self.body),receipt=pin('receipt',encoded(self.receipt)),sources={'synthetic':'Synthetic Index'},runtime_manifest_sha256=digest(self.manifest),issued_at=time.time()-1,expires_at=self.f.consent['expires_at'])
  self.path=self.root/'activation.json';self.write_record()
 def write_record(self):self.path.write_bytes(encoded(self.record));self.path.chmod(0o600);self.sha=h(self.path.read_bytes())
 def context(self):return n.approved_captured_wrapper(self.path,self.sha)
 def test_installed_wrapper_uses_real_bounded_module_with_fake_keychain_wire(self):
  import test_supervised_envelope as framing
  runtime=self.root/'runtime';runtime.mkdir(mode=0o700)
  actual=installation.install_runtime(Path(__file__).resolve().parent,runtime)
  # Parent method is mocked for other unit checks; read actual installed manifest.
  actual=json.loads((runtime/'runtime-files.json').read_bytes())
  self.record['runtime_manifest_sha256']=digest(actual);self.write_record()
  script=self.root/'trusted_fixture.py'
  code="""
import sys,runpy,atexit,ctypes
from pathlib import Path
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','ctypes.dlopen'):
  attempts.append(event);raise AssertionError('unexpected real I/O')
sys.addaudithook(audit)
@atexit.register
def done():print('INDEPENDENT_TRIPWIRE='+str(len(attempts)))
"""
  code+='sys.path.insert(0,'+repr(str(runtime))+')\n'
  code+="""
from ai_movie_investigator import new_case as n,supervised_credit as c,keychain_credential as k,supervised_authorization as a
from ai_movie_investigator.contracts import encoded
# Invented filesystem/Keychain I/O; no guard or provenance monkeypatch.
c.read_private=lambda p,limit:Path(p).read_bytes()
k._native=lambda project:b'sk-DUMMY_CAPTURED'
"""
  code+='selected_raw='+repr(self.f.response())+"\nframing='chunked'\n"+framing.wire_code()
  code+='\nwith n.approved_captured_wrapper('+repr(str(self.path))+','+repr(self.sha)+'), a._simulated_captured_io(), wire_fixture("completed"):\n'
  code+=' n.authorize_captured('+repr(str(self.f.f.state))+',c.read_evidence('+repr(str(self.f.selected.path))+'),'+repr(str(self.f.case.directory))+','+repr(digest(self.f.request))+','+repr(str(self.f.path))+','+repr(digest(self.f.consent))+')\n'
  code+=' sys.argv='+repr(['ai_movie_investigator.supervised_credit','--state',str(self.f.f.state),'run-captured-keychain','--evidence',str(self.f.selected.path),'--slot','7'])+'\n'
  code+=" runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)\n"
  script.write_text(code)
  result=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=runtime,env={'PATH':'/usr/bin:/bin','TMPDIR':'/private/tmp'},capture_output=True,timeout=30)
  output=result.stdout+result.stderr;self.assertEqual(result.returncode,0,output);self.assertIn(b'INDEPENDENT_TRIPWIRE=0',output);self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1);self.assertNotIn(b'sk-DUMMY_CAPTURED',output)
  report=self.f.case.read()[-1]['report'];self.assertTrue(report['connected_transport_invoked']);self.assertFalse(report['generation_invoked']);self.assertFalse(report['draft']['sent'])
 def test_default_closed_before_artifact_reads(self):
  with patch.object(c,'_read_evidence',side_effect=AssertionError('read')):
   with self.assertRaisesRegex(Refusal,'captured_real_activation_unissued'):n.require_captured_activation()
 def test_exact_context_receipt_report_and_reset_without_gate_patch(self):
  with self.context(),a._simulated_captured_io():
   self.f.authorize();self.assertEqual(self.f.run_case()['status'],'completed')
   with self.assertRaises(Refusal):self.f.run_case()
  report=self.f.case.read()[-1]['report'];receipt=History(self.f.f.state/'attempt-7').read()[-1]
  self.assertEqual(report['receipt_hash'],digest(receipt));self.assertTrue(report['connected_transport_invoked']);self.assertFalse(report['generation_invoked']);self.assertFalse(report['draft']['sent'])
  with self.assertRaisesRegex(Refusal,'captured_real_activation_unissued'):n.require_captured_activation()
 def test_changed_artifact_stops_before_prompt_or_debit(self):
  with self.context(),a._simulated_captured_io():
   self.f.authorize();Path(self.record['body']['path']).write_bytes(b'changed')
   with patch.object(c,'prompt_credential',side_effect=AssertionError('credential')):
    with self.assertRaisesRegex(Refusal,'captured_activation_artifact_changed'):self.f.run_case()
  self.assertEqual(History(self.f.f.state/'attempt-7').read(),[])
 def test_same_hash_label_altered_facts_cannot_bind(self):
  with self.context():
   active=n._APPROVED_CAPTURE.get();bad=copy.deepcopy(self.f.packet);bad['facts']['title']='Altered assertion'
   self.assertEqual(bad['original_hash'],self.f.packet['original_hash'])
   with self.assertRaisesRegex(Refusal,'captured_activation_packet'):active.bind(self.f.consent,bad)
 def test_other_consent_and_replaced_receipt_refuse(self):
  with self.context():
   bad=copy.deepcopy(self.f.consent);bad['project']='proj_other'
   with self.assertRaisesRegex(Refusal,'captured_activation_authority'):n._APPROVED_CAPTURE.get().bind(bad)
   p=Path(self.record['receipt']['path']);raw=p.read_bytes();p.unlink();p.write_bytes(raw);p.chmod(0o600)
   with self.assertRaisesRegex(Refusal,'captured_activation_artifact_changed'):n.require_captured_activation()
 def test_expiry_and_runtime_refuse(self):
  self.record['expires_at']=time.time()-2;self.write_record()
  with self.assertRaises(Refusal):
   with self.context():pass
  self.record['expires_at']=self.f.consent['expires_at'];self.record['runtime_manifest_sha256']='0'*64;self.write_record()
  with self.assertRaisesRegex(Refusal,'captured_activation_runtime'):
   with self.context():pass
 def test_receipt_body_mismatch_and_clock_rollback_refuse(self):
  with self.context():
   active=n._APPROVED_CAPTURE.get()
   with patch.object(n.time,'time',return_value=active.last_time-1):
    with self.assertRaisesRegex(Refusal,'captured_activation_expired'):n.require_captured_activation()
  self.receipt['body_sha256']='0'*64;p=Path(self.record['receipt']['path']);p.write_bytes(encoded(self.receipt));self.record['receipt']['sha256']=h(p.read_bytes());self.write_record()
  with self.assertRaisesRegex(Refusal,'captured_receipt_body'):
   with self.context():pass
 def test_uncertain_transport_does_not_allow_retry_or_supplied_completion(self):
  with self.context(),a._simulated_captured_io():
   self.f.authorize();raw=json.loads(self.f.response());raw['usage']['total_tokens']=1
   with self.assertRaisesRegex(Refusal,'responses_usage_invalid'):self.f.run_case(encoded(raw))
   with self.assertRaises(Refusal):self.f.run_case()
   with self.assertRaises(Refusal):n.complete(self.f.case,digest(self.f.request),self.f.reply,{'mode':'supervised_supplied','chat_reference':'forbidden fallback'})

if __name__=='__main__':
 with patch.object(socket,'socket',side_effect=AssertionError('network')),patch.object(socket,'getaddrinfo',side_effect=AssertionError('DNS')):unittest.main(verbosity=2)
