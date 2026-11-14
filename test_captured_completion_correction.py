"""One explicit correction of the old static label; invented histories only."""
import copy, hashlib, time, unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import new_case as n, supervised_credit as c, supervised_authorization as a
from ai_movie_investigator.contracts import Refusal, digest, encoded
from ai_movie_investigator.history import History, FILENAME
import test_captured_provenance as provenance

class CompletionCorrection(unittest.TestCase):
    def setUp(self):
        self.x=provenance.CapturedProvenance('test_receipt_correlated_label_completes_valid_answer')
        self.x.setUp();self.addCleanup(self.x.doCleanups);self.f=self.x.f;self.activation=self.x.x

    def fail_label(self, label=None):
        with patch.object(n,'_CAPTURED_PROVENANCE',label or n._OLD_CAPTURED_PROVENANCE):
            with self.assertRaisesRegex(Refusal,'unsafe_text'):self.x.real_label_branch()
        self.oldroot=(self.f.f.state/FILENAME).read_bytes()
        self.oldcase=(self.f.case.directory/FILENAME).read_bytes()
        self.oldcredit=(self.f.f.state/'credit'/FILENAME).read_bytes()
        self.oldattempt=(self.f.f.state/'attempt-7'/FILENAME).read_bytes()

    def propose(self, change=None):
        prior_slot=getattr(self,"prior_slot",7)
        rows=self.f.case.read();root=self.f.root.read();credit=History(self.f.f.state/'credit').read()
        fix=dict(kind='captured_static_provenance_correction_v1',prior_slot=prior_slot,root_prefix_sha256=digest(root),
            case_prefix_sha256=digest(rows),credit_prefix_sha256=digest(credit),
            corrected_module_sha256=hashlib.sha256(Path(n.__file__).read_bytes()).hexdigest(),
            main_reference='Invented main accepted correction',purpose='one_corrected_captured_assessment_after_static_provenance_defect',
            reviewed=True,issued_at=time.time()-1,expires_at=self.f.selected.data['expires_at'])
        if change:change(fix)
        p=self.activation.root/'correction.json';p.write_bytes(encoded(fix));p.chmod(0o600)
        self.fix=dict(path=str(p),sha256=digest(fix))
        evidence=dict(self.f.selected.data,owner_reference=fix['main_reference']+' '+digest(fix))
        ep=self.activation.root/'corrected-evidence.json';ep.write_bytes(encoded(evidence));ep.chmod(0o600);self.f.selected=c.read_evidence(ep)
        with self.f.root.transaction(write=True) as (events,_):
            with self.f.case.transaction(write=True) as (case,_):
                consent=n.captured_completion_correction_consent(self.f.root,events,self.f.case,case,digest(self.f.request),evidence,prior_slot=prior_slot,correction=self.fix)
        self.f.consent=consent;self.f.path=self.activation.root/'corrected-consent.json';self.f.path.write_bytes(encoded(consent));self.f.path.chmod(0o600)
        self.activation.record['authority']=dict(path=str(self.f.path),sha256=digest(consent));self.activation.write_record()

    def test_successor_preserves_all_old_bytes_and_one_new_debit(self):
        self.fail_label();self.propose()
        with self.activation.context(),a._simulated_captured_io():
            self.assertEqual(self.f.authorize()['slot'],8)
            import test_supervised_diagnostics as diag, test_supervised_envelope as framing
            with diag.DiagnosticTests().inputs(),framing.wire(self.f.response()):
                self.assertEqual(c.run(self.f.f.state,self.f.selected,8,captured=True)['status'],'completed')
            with self.assertRaises(Refusal):c.run(self.f.f.state,self.f.selected,8,captured=True)
            with self.assertRaises(Refusal):self.f.authorize()
        for p,b in ((self.f.f.state/FILENAME,self.oldroot),(self.f.case.directory/FILENAME,self.oldcase),(self.f.f.state/'credit'/FILENAME,self.oldcredit)):
            self.assertTrue(p.read_bytes().startswith(b))
        self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),self.oldattempt)
        credit=History(self.f.f.state/'credit').read();self.assertEqual(len(credit),7)
        self.assertNotEqual(credit[-1]['request_hash'],credit[-2]['request_hash'])
        self.assertEqual(credit[-1]['wire_request_hash'],credit[-2]['request_hash'])
        report=self.f.case.read()[-1]['report'];self.assertFalse(report['draft']['sent'])
        self.assertEqual(report['receipt_hash'],digest(History(self.f.f.state/'attempt-8').read()[-1]))
        self.assertFalse((self.f.f.state/'attempt-9').exists())

    def test_wrong_code_proof_refuses_before_new_attempt(self):
        self.fail_label()
        with self.assertRaisesRegex(Refusal,'captured_correction_proof'):self.propose(lambda x:x.update(corrected_module_sha256='0'*64))
        self.assertEqual((self.f.f.state/FILENAME).read_bytes(),self.oldroot)
        self.assertFalse((self.f.f.state/'attempt-8').exists())

    def test_wrong_terminal_category_refuses_with_valid_proof(self):
        original=c.safe_diagnostic
        def changed(error):return dict(original(error),category='other')
        with patch.object(c,'safe_diagnostic',changed):self.fail_label()
        with self.assertRaisesRegex(Refusal,'captured_correction_prior'):self.propose()
        self.assertFalse((self.f.f.state/'attempt-8').exists())

    def test_other_unsafe_provenance_refuses_with_valid_proof(self):
        self.fail_label('Different unsafe/label')
        with self.assertRaisesRegex(Refusal,'captured_correction_prior'):self.propose()
        self.assertFalse((self.f.f.state/'attempt-8').exists())

    def test_supplied_answer_cannot_recover_rejected_completion(self):
        self.fail_label();self.propose()
        with self.assertRaisesRegex(Refusal,'captured_completion_unbound'):
            n.complete(self.f.case,digest(self.f.request),self.f.reply,dict(mode='supervised_supplied',chat_reference='not a recovery'))
        self.assertEqual((self.f.case.directory/FILENAME).read_bytes(),self.oldcase)

    def test_actual_lineage_401_freshness_rejection_correction(self):
        import test_captured_freshness as fresh
        import test_supervised_diagnostics as diag, test_supervised_envelope as framing
        self.doCleanups()
        f=fresh.CapturedFreshness('test_prior_401_successor_refresh_preserves_debit_and_report')
        f.continuation=True;f.setUp();self.addCleanup(f.doCleanups);f.propose()
        self.f=f.f;self.activation=f.x;self.prior_slot=8
        consume=a.consume_captured_completion
        def real_branch(held,answer):return dict(consume(held,answer),simulated=False)
        with f.x.context(),a._simulated_captured_io():
            self.assertEqual(f.refresh()['slot'],8)
            with patch.object(n,'_CAPTURED_PROVENANCE',n._OLD_CAPTURED_PROVENANCE),patch.object(a,'consume_captured_completion',real_branch),diag.DiagnosticTests().inputs(),framing.wire(self.f.response()):
                with self.assertRaisesRegex(Refusal,'unsafe_text'):
                    c.run(self.f.f.state,self.f.selected,8,captured=True,clock=lambda:f.now)
        old={p:p.read_bytes() for p in (self.f.f.state/FILENAME,self.f.case.directory/FILENAME,self.f.f.state/'credit'/FILENAME,self.f.f.state/'attempt-7'/FILENAME,self.f.f.state/'attempt-8'/FILENAME)}
        original_request=copy.deepcopy(self.f.request);original_packet=copy.deepcopy(self.f.packet)
        self.propose()
        with self.activation.context(),a._simulated_captured_io():
            self.assertEqual(self.f.authorize()['slot'],9)
            with patch.object(a,'consume_captured_completion',real_branch),diag.DiagnosticTests().inputs(),framing.wire(self.f.response()):
                self.assertEqual(c.run(self.f.f.state,self.f.selected,9,captured=True,clock=lambda:f.now)['status'],'completed')
            with self.assertRaises(Refusal):c.run(self.f.f.state,self.f.selected,9,captured=True,clock=lambda:f.now)
        for p,raw in old.items():self.assertTrue(p.read_bytes().startswith(raw))
        for num in (7,8):
            p=self.f.f.state/f'attempt-{num}'/FILENAME;self.assertEqual(p.read_bytes(),old[p])
        rows=self.f.case.read();report=rows[-1]['report'];self.assertFalse(report['draft']['sent'])
        self.assertTrue(report['generation_invoked']);self.assertTrue(report['provider_receipt_correlated'])
        self.assertEqual(report['receipt_hash'],digest(History(self.f.f.state/'attempt-9').read()[-1]))
        self.assertEqual(len([r for r in rows if r['type']=='new_case_generation_started']),3)
        credit=History(self.f.f.state/'credit').read();self.assertEqual(len(credit),8)
        self.assertEqual(len({r['request_hash'] for r in credit}),8)
        self.assertEqual(credit[-1]['wire_request_hash'],credit[-2]['wire_request_hash'])
        self.assertEqual(self.f.request,original_request);self.assertEqual(self.f.packet,original_packet)
        self.assertFalse((self.f.f.state/'attempt-10').exists())
        self.prior_slot=9
        with self.assertRaisesRegex(Refusal,'captured_correction_prior'):self.propose()

    def test_installed_correction_module_with_fake_wire(self):
        import json, subprocess, sys
        import test_supervised_envelope as framing
        from ai_movie_investigator.installation import install_runtime
        self.fail_label();self.propose()
        runtime=self.activation.root/'installed-correction';runtime.mkdir(mode=0o700)
        install_runtime(Path(__file__).resolve().parent,runtime)
        manifest=json.loads((runtime/'runtime-files.json').read_bytes());self.assertGreater(len(manifest),0)
        self.activation.record['runtime_manifest_sha256']=digest(manifest);self.activation.write_record()
        code='''import sys,atexit,ctypes
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen' or (event=='ctypes.dlopen' and args[0] not in (None,'/usr/lib/libSystem.B.dylib')):
  attempts.append(event);raise AssertionError('external IO')
sys.addaudithook(audit)
@atexit.register
def done():print('TRIPWIRE='+str(len(attempts)))
'''
        code+='sys.path.insert(0,'+repr(str(runtime))+')\n'
        code+='''from pathlib import Path
from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a,keychain_credential as k
# Invented fixture file and credential adapters; installed contract code intact.
c.read_private=lambda p,limit:Path(p).read_bytes()
k._native=lambda project:b'sk-DUMMY_CAPTURED'
'''
        code+='selected_raw='+repr(self.f.response())+"\nframing='chunked'\n"+framing.wire_code()
        code+='\nwith n.approved_captured_wrapper('+repr(str(self.activation.path))+','+repr(self.activation.sha)+'),a._simulated_captured_io(),wire_fixture("completed"):\n'
        code+=' selected=c.read_evidence('+repr(str(self.f.selected.path))+')\n'
        code+=' result=n.authorize_captured('+','.join(map(repr,[str(self.f.f.state)]))+',selected,'+','.join(map(repr,[str(self.f.case.directory),digest(self.f.request),str(self.f.path),digest(self.f.consent)]))+')\n'
        code+=' assert result["slot"]==8\n'
        code+=' sys.argv='+repr(['ai_movie_investigator.supervised_credit','--state',str(self.f.f.state),'run-captured-keychain','--evidence',str(self.f.selected.path),'--slot','8'])+'\n'
        code+=" import runpy;runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)\n"
        script=self.activation.root/'installed-correction.py';script.write_text(code)
        result=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=runtime,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=40)
        output=result.stdout+result.stderr
        self.assertEqual(result.returncode,0,output);self.assertIn(b'TRIPWIRE=0',output)
        self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
        self.assertEqual((self.f.f.state/'attempt-7'/FILENAME).read_bytes(),self.oldattempt)
        self.assertFalse(self.f.case.read()[-1]['report']['draft']['sent'])

if __name__=='__main__':unittest.main()
