"""Invented historical input and ledger; real framed transport with blocked network."""
import copy,io,os,pty,re,select,subprocess,sys,time,unittest
from pathlib import Path
from contextlib import redirect_stderr,redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command,historical_nano as historical
from ai_movie_investigator.contracts import Refusal,decode,encoded,digest
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.history import History,FILENAME
import test_standing_credit as standing
from test_manual_expanded import envelope
from test_responses_compatibility import documented
from test_supervised_envelope import wire
import test_supervised_diagnostics as diagnostics

class HistoricalNanoTests(unittest.TestCase):
    def setUp(self):
        self.f=standing.StandingTests('test_grant_preserves_legacy_hashes_and_default_cap');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.grant()
        with diagnostics.DiagnosticTests().inputs(),self.f.wire(7),redirect_stdout(io.StringIO()):command.run_next(self.f.state,self.f.selected)
        self.original={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
        self.path=self.f.f.root/'historical-input.json';self.path.write_bytes(envelope());self.path.chmod(0o600)

    def authorize(self,accept=True):
        out=io.StringIO()
        def confirm(prompt):return re.findall(r'Exact disclosure grant SHA-256: ([0-9a-f]{64})',out.getvalue())[-1] if accept else 'no'
        with redirect_stderr(out),diagnostics.DiagnosticTests().inputs(),patch('builtins.input',side_effect=confirm):
            return historical.authorize(self.f.state,self.f.selected,self.path)

    def frame(self,bad=False):
        grant=History(self.f.state).read()[-2]['historical'];value=documented()
        answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
        value['output'][-1]['content'][0]['text']=encoded(answer).decode()
        if bad:value['usage']['total_tokens']=1
        return wire(encoded(value),'chunked')

    def preserve(self):
        for p,raw in self.original.items():
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
            else:self.assertTrue(p.read_bytes().startswith(raw))

    def test_connected_historical_report_preserves_18c_and_qualified_output(self):
        self.assertEqual(self.authorize()['slot'],8)
        with diagnostics.DiagnosticTests().inputs(),self.frame(),redirect_stdout(io.StringIO()) as out:
            result=command.run(self.f.state,self.f.selected,8,historical=True)
        self.assertEqual(result['status'],'completed');self.assertEqual(out.getvalue().count('OFFLINE_AUTHORIZED_BOUNDARY'),1)
        report=History(self.f.state).read()[-1]['historical_report']
        self.assertFalse(report['captured_bytes']);self.assertEqual(report['currentness'],'unknown');self.assertEqual(report['decisions'],'unknown')
        self.assertTrue(report['generation_invoked']);self.assertFalse(report['identity_approval']);self.assertFalse(report['acquisition_approval']);self.assertFalse(report['sent'])
        self.assertEqual(report['receipt']['request_sha256'],report['request_sha256'])
        self.assertEqual([e['reserved_usd'] for e in History(self.f.state/'credit').read()],[[3,100]]*7)
        self.preserve()
        with self.assertRaises(Refusal):self.authorize()
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,8,historical=True)
        prompt.assert_not_called()

    def test_standing_grant_alone_declined_disclosure_and_wrong_route_cannot_send(self):
        before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
        with self.assertRaisesRegex(Refusal,'historical_owner_confirmation_required'):self.authorize(False)
        self.assertEqual(before,{p:p.read_bytes() for p in self.f.state.rglob(FILENAME)})
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,8,historical=True)
        prompt.assert_not_called();self.authorize()
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaisesRegex(Refusal,'historical_route_required'):command.run(self.f.state,self.f.selected,8)
            with diagnostics.DiagnosticTests().inputs():
                with self.assertRaisesRegex(Refusal,'historical_pending_grant'):command.run_next(self.f.state,self.f.selected)
        prompt.assert_not_called()

    def test_uncertain_response_retains_debit_no_new_timestamp_replay(self):
        self.authorize()
        with diagnostics.DiagnosticTests().inputs(),self.frame(True),redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(Refusal,'responses_usage_invalid'):command.run(self.f.state,self.f.selected,8,historical=True)
        self.preserve();self.assertEqual(len(History(self.f.state/'credit').read()),7)
        with self.assertRaisesRegex(Refusal,'historical_assessment_consumed'):self.authorize()
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(Refusal):command.run(self.f.state,self.f.selected,8,historical=True)
        prompt.assert_not_called()

    def test_input_tampering_refuses_before_secret_or_debit(self):
        self.authorize();self.path.write_bytes(self.path.read_bytes()+b' ')
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaisesRegex(Refusal,'historical_disclosure_changed'):command.run(self.f.state,self.f.selected,8,historical=True)
        prompt.assert_not_called();self.assertEqual(len(History(self.f.state/'credit').read()),6)


    def test_consent_binds_project_policy_source_and_ceiling(self):
        self.authorize();grant=History(self.f.state).read()[-2]['historical']
        historical.validate(grant,self.f.e['project'])
        for key,value in (('project','proj_other'),('maximum_debit_usd',[4,100]),
                          ('policy',{}),('input_sha256','f'*64),('endpoint','https://invalid.example')):
            changed=copy.deepcopy(grant);changed['consent'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(Refusal,'historical_disclosure_changed'):
                historical.validate(changed,self.f.e['project'])
        with self.assertRaisesRegex(Refusal,'historical_disclosure_changed'):
            historical.validate(grant,'proj_other')
        # Export/version/timestamp repackaging must not create another charge.
        packet=decode(self.path.read_bytes());packet['packet']['source_sha256']='f'*64
        packet['packet']['source_report_sha256']='1'*64
        packet['packet']['version']='2'*64;packet['retained_case']['version']='2'*64
        packet['retained_case_sha256']=digest(packet['retained_case'])
        self.path.write_bytes(encoded(packet))
        self.assertEqual(historical.proposal(self.path,time.time())['fingerprint'],grant['fingerprint'])

    def test_budget_policy_and_expiry_refuse_without_grant_or_secret(self):
        before={p:p.read_bytes() for p in self.f.state.rglob(FILENAME)}
        for changes in (dict(available_usd=[18,100]),dict(policy={}),dict(expires_at=time.time()-1)):
            selected=self.f.select(dict(self.f.e,**changes))
            with diagnostics.DiagnosticTests().inputs(),patch('builtins.input') as confirm,patch('getpass.getpass') as secret:
                with self.assertRaises(Refusal):historical.authorize(self.f.state,selected,self.path)
                confirm.assert_not_called();secret.assert_not_called()
            self.assertEqual(before,{p:p.read_bytes() for p in self.f.state.rglob(FILENAME)})


    def test_installed_pty_disclosure_then_single_framed_report_and_restart_refusal(self):
        from ai_movie_investigator.installation import install_runtime,verify_installation
        from test_responses_compatibility import FIXTURE_CODE
        from test_supervised_envelope import wire_code
        installed=self.f.f.root/'installed';installed.mkdir(mode=0o700)
        manifest=install_runtime(Path(__file__).resolve().parent,installed)
        self.assertEqual(len(manifest),47)
        hooks=self.f.f.root/'hooks';hooks.mkdir(mode=0o700)
        hook="""
import atexit,errno,os,sys
_network=[]
def audit(event,args):
    if event in ('socket.__new__','socket.connect','socket.getaddrinfo','socket.gethostbyname'):
        _network.append(event);raise AssertionError('network forbidden')
sys.addaudithook(audit)
if sys.platform.startswith('linux'):
    def absent(*args,**kwargs):raise OSError(errno.ENODATA,'fixture absent ACL')
    os.getxattr=absent
@atexit.register
def status():print('NETWORK_ATTEMPTS='+str(len(_network)),flush=True)
"""+FIXTURE_CODE+"""
if 'run-historical' in sys.argv:
    from ai_movie_investigator.history import History
    from ai_movie_investigator.contracts import decode,encoded
    from ai_movie_investigator.disclosure import aliases
    events=History(__import__('pathlib').Path(sys.argv[sys.argv.index('--state')+1])).read()
    grant=next(e['historical'] for e in events if e.get('slot')==8 and 'historical' in e)
    value=documented();answer=decode(value['output'][-1]['content'][0]['text'])
    answer['binding_hash']=aliases(grant['run'])
    value['output'][-1]['content'][0]['text']=encoded(answer).decode()
    selected_raw=encoded(value);framing='chunked'
"""+wire_code()+"""
if 'run-historical' in sys.argv:
    _wire=wire_fixture('completed');_wire.__enter__()
"""
        (hooks/'sitecustomize.py').write_text(hook)
        env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONPATH':str(hooks)+os.pathsep+str(installed),
             'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
        def invoke(action,extra):
            argv=[sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(self.f.state),
                  action,'--evidence',str(self.f.selected.path)]+extra
            master,slave=pty.openpty();proc=subprocess.Popen(argv,cwd=installed,env=env,
                stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
            os.close(slave);output=bytearray();entered=False;deadline=time.monotonic()+20
            try:
                while time.monotonic()<deadline:
                    ready,_,_=select.select([master],[],[],.1)
                    if ready:
                        try:part=os.read(master,8192)
                        except OSError:break
                        if not part:break
                        output.extend(part)
                        if not entered and b'Authorize this one disclosure by entering its full SHA-256:' in output:
                            value=re.findall(rb'Exact disclosure grant SHA-256: ([0-9a-f]{64})',output)[-1]
                            os.write(master,value+b'\n');entered=True
                        elif not entered and b'Secret API key (not Tracking ID or project ID; hidden):' in output:
                            os.write(master,b'sk-DUMMY_HISTORICAL_ONLY\n');entered=True
                    if proc.poll() is not None and not ready:break
                if proc.poll() is None:proc.kill()
                code=proc.wait(timeout=5)
            finally:
                os.close(master)
                if proc.poll() is None:proc.kill();proc.wait()
            self.assertIn(b'NETWORK_ATTEMPTS=0',output)
            self.assertNotIn(b'sk-DUMMY_HISTORICAL_ONLY',output)
            self.assertNotIn(b'Traceback',output)
            return code,bytes(output),entered
        code,out,entered=invoke('authorize-historical',['--input',str(self.path)])
        self.assertEqual(code,0,out);self.assertTrue(entered);self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',out)
        self.assertIn(b'proj_fixture',out);self.assertIn(b'maximum_debit_usd',out)
        code,out,entered=invoke('run-historical',['--slot','8'])
        self.assertEqual(code,0,out);self.assertTrue(entered);self.assertEqual(out.count(b'OFFLINE_AUTHORIZED_BOUNDARY'),1)
        report=History(self.f.state).read()[-1]['historical_report']
        self.assertEqual(report['receipt']['request_sha256'],report['request_sha256']);self.assertFalse(report['captured_bytes'])
        self.assertEqual(len(History(self.f.state/'credit').read()),7);self.preserve()
        code,out,entered=invoke('run-historical',['--slot','8'])
        self.assertEqual(code,1,out);self.assertFalse(entered);self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',out)
        self.assertEqual(verify_installation(installed),manifest)

if __name__=='__main__':unittest.main()
