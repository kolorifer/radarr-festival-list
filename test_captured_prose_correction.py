"""Finite second defect correction; invented complete historical lineage."""
import copy, unittest
from unittest.mock import patch
from ai_movie_investigator import new_case as n, supervised_credit as c, supervised_authorization as a
from ai_movie_investigator.contracts import Refusal,digest
from ai_movie_investigator.history import History,FILENAME
import test_captured_completion_correction as correction
import test_captured_freshness as freshness
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing

class ProseCorrection(unittest.TestCase):
    def test_full_lineage_safe_completion_no_repeat_or_raw_retention(self):
        self.exercise_lineage()

    def test_installed_module_safe_persistence_and_restart_refusal(self):
        self.exercise_lineage(installed=True)

    def exercise_lineage(self,installed=False):
        f=freshness.CapturedFreshness('test_prior_401_successor_refresh_preserves_debit_and_report')
        f.continuation=True;f.setUp();self.addCleanup(f.doCleanups);f.propose()
        consume=a.consume_captured_completion
        def real(held,answer):return dict(consume(held,answer),simulated=False)
        with f.x.context(),a._simulated_captured_io():
            f.refresh()
            with patch.object(n,'_CAPTURED_PROVENANCE',n._OLD_CAPTURED_PROVENANCE),patch.object(a,'consume_captured_completion',real),diagnostics.DiagnosticTests().inputs(),framing.wire(f.f.response()):
                with self.assertRaisesRegex(Refusal,'unsafe_text'):c.run(f.f.f.state,f.f.selected,8,captured=True,clock=lambda:f.now)
        helper=correction.CompletionCorrection();helper.f=f.f;helper.activation=f.x;helper.prior_slot=8
        helper.propose()
        response=copy.deepcopy(f.f.reply);response['result'].update(rationale='Invented source/title evidence',uncertainty='Which cut?')
        with f.x.context(),a._simulated_captured_io():
            self.assertEqual(f.f.authorize()['slot'],9)
            # Model the previous accepted code: no prose-copy stage yet.
            with patch.object(n,'_captured_prose_copy',side_effect=lambda answer:(answer,{})),patch.object(a,'consume_captured_completion',real),diagnostics.DiagnosticTests().inputs(),framing.wire(f.f.response(response)):
                with self.assertRaisesRegex(Refusal,'unsafe_text'):c.run(f.f.f.state,f.f.selected,9,captured=True,clock=lambda:f.now)
        old={p:p.read_bytes() for p in (f.f.f.state/FILENAME,f.f.case.directory/FILENAME,f.f.f.state/'credit'/FILENAME,*[f.f.f.state/f'attempt-{i}'/FILENAME for i in (7,8,9)])}
        original_request=copy.deepcopy(f.f.request);original_packet=copy.deepcopy(f.f.packet)
        # Distinct proof and consent paths preserve earlier pinned artifacts.
        proofdir=f.x.root/'prose-proof';proofdir.mkdir(mode=0o700);f.x.root=proofdir;helper.prior_slot=9
        def prose_proof(fix):fix.update(kind='captured_prose_retention_correction_v1',purpose='one_corrected_captured_assessment_with_explicit_prose_withholding')
        with patch.object(n,'captured_completion_correction_consent',n.captured_prose_correction_consent):helper.propose(prose_proof)
        if installed:self.installed_successor(f,response)
        else:
            with f.x.context(),a._simulated_captured_io():
                self.assertEqual(f.f.authorize()['slot'],10)
                with patch.object(a,'consume_captured_completion',real),diagnostics.DiagnosticTests().inputs(),framing.wire(f.f.response(response)):
                    self.assertEqual(c.run(f.f.f.state,f.f.selected,10,captured=True,clock=lambda:f.now)['status'],'completed')
                with self.assertRaises(Refusal):c.run(f.f.f.state,f.f.selected,10,captured=True,clock=lambda:f.now)
                with self.assertRaises(Refusal):f.f.authorize()
        for p,raw in old.items():self.assertTrue(p.read_bytes().startswith(raw))
        for i in (7,8,9):
            p=f.f.f.state/f'attempt-{i}'/FILENAME;self.assertEqual(p.read_bytes(),old[p])
        report=f.f.case.read()[-1]['report'];root=f.f.root.read()[-1]
        self.assertEqual(report['generation_invoked'],not installed);self.assertFalse(report['draft']['sent'])
        self.assertEqual(report['reply_hash'],digest(response));self.assertEqual(report['retained_reply_hash'],digest(root['answer']))
        self.assertEqual(report['receipt_hash'],digest(History(f.f.f.state/'attempt-10').read()[-1]))
        self.assertEqual(report['prose_handling']['rationale']['status'],'withheld')
        self.assertEqual(report['prose_handling']['uncertainty']['status'],'withheld')
        for p in (f.f.case.directory/FILENAME,f.f.f.state/FILENAME):
            self.assertNotIn(b'Invented source/title',p.read_bytes());self.assertNotIn(b'Which cut?',p.read_bytes())
        rows=f.f.case.read();self.assertEqual(len([r for r in rows if r['type']=='new_case_generation_started']),4)
        self.assertEqual(len([r for r in rows if r['type']=='new_case_completion_rejected']),2)
        credit=History(f.f.f.state/'credit').read();self.assertEqual(len(credit),9);self.assertEqual(len({r['request_hash'] for r in credit}),9)
        self.assertEqual(f.f.request,original_request);self.assertEqual(f.f.packet,original_packet)
        self.assertFalse((f.f.f.state/'attempt-11').exists())
        helper.prior_slot=10
        with patch.object(n,'captured_completion_correction_consent',n.captured_prose_correction_consent),self.assertRaisesRegex(Refusal,'captured_correction_prior'):helper.propose(prose_proof)
        with self.assertRaises(Refusal):n.complete(f.f.case,digest(f.f.request),response,dict(mode='supervised_supplied',chat_reference='no recovery'))

    def installed_successor(self,f,response):
        import json,subprocess,sys
        from pathlib import Path
        from ai_movie_investigator.installation import install_runtime
        runtime=f.x.root/'installed-prose';runtime.mkdir(mode=0o700)
        install_runtime(Path(__file__).resolve().parent,runtime)
        manifest=json.loads((runtime/'runtime-files.json').read_bytes());self.assertGreater(len(manifest),0)
        f.x.record['runtime_manifest_sha256']=digest(manifest);f.x.write_record()
        code='''import sys,atexit,ctypes,time
attempts=[]
def audit(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen' or (event=='ctypes.dlopen' and args[0] not in (None,'/usr/lib/libSystem.B.dylib')):
  attempts.append(event);raise AssertionError('external IO')
sys.addaudithook(audit)
@atexit.register
def done():print('TRIPWIRE='+str(len(attempts)))
'''
        code+='time.time=lambda:'+repr(f.now)+'\nsys.path.insert(0,'+repr(str(runtime))+')\n'
        code+='''from pathlib import Path
from ai_movie_investigator import new_case as n,supervised_credit as c,supervised_authorization as a,keychain_credential as k
c.read_private=lambda p,limit:Path(p).read_bytes()
native=[]
def invented_key(project):native.append(1);return b'sk-DUMMY_CAPTURED'
k._native=invented_key
'''
        code+='selected_raw='+repr(f.f.response(response))+"\nframing='chunked'\n"+framing.wire_code()
        code+='\nwith n.approved_captured_wrapper('+repr(str(f.x.path))+','+repr(f.x.sha)+'),a._simulated_captured_io(),wire_fixture("completed"):\n'
        code+=' selected=c.read_evidence('+repr(str(f.f.selected.path))+')\n'
        code+=' granted=n.authorize_captured('+repr(str(f.f.f.state))+',selected,'+','.join(map(repr,[str(f.f.case.directory),digest(f.f.request),str(f.f.path),digest(f.f.consent)]))+')\n assert granted["slot"]==10\n'
        code+=' import runpy\n for attempt in range(2):\n  sys.argv='+repr(['ai_movie_investigator.supervised_credit','--state',str(f.f.f.state),'run-captured-keychain','--evidence',str(f.f.selected.path),'--slot','10'])+'\n'
        code+='''  try:runpy.run_module('ai_movie_investigator.supervised_credit',run_name='__main__',alter_sys=True)
  except SystemExit as result:assert result.code==(0 if attempt==0 else 1)
 assert len(native)==1
 print('ONE_INVENTED_CREDENTIAL')
'''
        script=f.x.root/'installed-prose.py';script.write_text(code)
        result=subprocess.run([sys.executable,'-I','-S','-B',str(script)],cwd=runtime,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=40)
        output=result.stdout+result.stderr;self.assertEqual(result.returncode,0,output)
        self.assertIn(b'TRIPWIRE=0',output);self.assertIn(b'ONE_INVENTED_CREDENTIAL',output)
        self.assertEqual(output.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)

    def test_wrong_predecessor_refuses_before_allocation(self):
        helper=correction.CompletionCorrection('test_wrong_code_proof_refuses_before_new_attempt');helper.setUp();self.addCleanup(helper.doCleanups);helper.fail_label()
        def change(fix):fix.update(kind='captured_prose_retention_correction_v1',purpose='one_corrected_captured_assessment_with_explicit_prose_withholding')
        with patch.object(n,'captured_completion_correction_consent',n.captured_prose_correction_consent),self.assertRaisesRegex(Refusal,'captured_correction_prior'):helper.propose(change)
        self.assertFalse((helper.f.f.state/'attempt-8').exists())

if __name__=='__main__':unittest.main()
