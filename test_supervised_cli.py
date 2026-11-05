"""Actual -m entry in a PTY; dummy key, offline HTTP sink and socket tripwires."""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time
import unittest
from ai_movie_investigator.history import History
from ai_movie_investigator.installation import install_runtime
import test_supervised_credit as fixtures
import test_supervised_reauthorization as renewal_fixtures


class SupervisedExecutableTests(unittest.TestCase):
    def test_real_module_entry_pty_uses_canonical_authority(self):
        fixture=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.execute_fixture(fixture,1)

    def test_installed_manual_renewal_then_real_slot_two_entry(self):
        renewal=renewal_fixtures.ReauthorizationTests('test_second_renewal_refuses_without_append')
        renewal.setUp();self.addCleanup(renewal.doCleanups)
        self.execute_fixture(renewal.f,2,renewal)
        self.assertEqual(renewal.f.path.read_bytes(),renewal.old_bytes)
        self.assertTrue((renewal.state/'ai-investigator-v1.jsonl').read_bytes().startswith(renewal.prefix))
        self.assertEqual(list((renewal.state/'attempt-1').iterdir()),[])

    def execute_fixture(self,fixture,slot,renewal=None,*,dummy=b'sk-DUMMY_EXECUTABLE_FIXTURE_ONLY',
                        failure='binding_response_unknown',category='send_or_response_refused',invalid=False):
        installed=fixture.root/'installed';installed.mkdir(mode=0o700)
        install_runtime(Path(__file__).resolve().parent,installed)
        hooks=fixture.root/'hooks';hooks.mkdir(mode=0o700)
        hook='''
import errno,os,socket,ssl,sys
from ai_movie_investigator.contracts import Refusal
from ai_movie_investigator.responses_http import FixedResponsesHTTP
from ai_movie_investigator.responses_transport import real_activation_refusal
if sys.platform.startswith('linux'):
    def absent(*args,**kwargs):raise OSError(errno.ENODATA,'fixture ACL absence')
    os.getxattr=absent
def forbidden(*args,**kwargs):raise AssertionError('offline network tripwire')
socket.socket=forbidden
socket.getaddrinfo=forbidden
def trace(frame,event,arg):
    if event=='exception' and frame.f_code.co_name=='require_prompted' and isinstance(arg[1],Refusal) and arg[1].args==('supervised_prompt_required',):
        print('OFFLINE_PROMPT_CONTEXT_REFUSED',flush=True)
    return trace
sys.settrace(trace)
def sink(self,body,**kw):
    reason=real_activation_refusal(kw['authorization'],body=body,credential=kw['credential'],project=kw['project'],path='/v1/responses')
    if reason is not None:raise Refusal(reason)
    print('OFFLINE_AUTHORIZED_BOUNDARY',flush=True)
    raise Refusal('binding_response_unknown')
FixedResponsesHTTP.post=sink
'''
        hook=hook.replace("raise Refusal('binding_response_unknown')",'raise Refusal('+repr(failure)+')')
        (hooks/'sitecustomize.py').write_text(hook)
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(hooks),str(installed))),PYTHONDONTWRITEBYTECODE='1')
        # No inherited provider credential is needed or forwarded to the fixture.
        env={k:v for k,v in env.items() if not any(s in k.upper() for s in ('KEY','TOKEN','SECRET','PASSWORD'))}
        selected=fixture.path
        if renewal is not None:
            selected=renewal.path
            result=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit',
                '--state',str(fixture.state),'reauthorize','--previous-evidence',str(fixture.path),
                '--evidence',str(selected)],cwd=installed,env=env,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual(json.loads(result.stdout),dict(status='reauthorized_no_api_call',permitted_slot=2))
            self.assertEqual(History(fixture.state/'credit').read(),[])
        before=(fixture.state/'ai-investigator-v1.jsonl').read_bytes()
        master,slave=pty.openpty()
        proc=subprocess.Popen([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit',
            '--state',str(fixture.state),'run','--evidence',str(selected),'--slot',str(slot)],
            cwd=installed,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
        os.close(slave);output=bytearray();entered=False;deadline=time.monotonic()+15
        try:
            while time.monotonic()<deadline:
                ready,_,_=select.select([master],[],[],.1)
                if ready:
                    try:part=os.read(master,8192)
                    except OSError:break
                    if not part:break
                    output.extend(part)
                    if b'Secret API key (not Tracking ID or project ID; hidden):' in output and not entered:
                        os.write(master,dummy+b'\n');entered=True
                if proc.poll() is not None and not ready:break
            if proc.poll() is None:proc.kill()
            code=proc.wait(timeout=5)
        finally:
            os.close(master)
            if proc.poll() is None:proc.kill();proc.wait()
        self.assertTrue(entered,'actual terminal prompt was not reached: '+output.decode(errors='replace'))
        self.assertNotIn(dummy,output,'dummy input echoed')
        if invalid:
            self.assertNotIn(b'OFFLINE_AUTHORIZED_BOUNDARY',output)
        else:self.assertIn(b'OFFLINE_AUTHORIZED_BOUNDARY',output,'actual -m did not reach authorized offline boundary')
        self.assertEqual(code,1) # Deliberate offline stop, never a provider call.
        self.assertIn(('category='+category+'; action=run; request status unconfirmed').encode(),output)
        self.assertNotIn(failure.encode(),output)
        self.assertNotIn(b'Traceback',output)
        self.assertNotIn(str(fixture.path).encode(),output)
        if invalid:
            self.assertEqual((fixture.state/'ai-investigator-v1.jsonl').read_bytes(),before)
            self.assertEqual(History(fixture.state/'credit').read(),[])
            self.assertEqual(list((fixture.state/f'attempt-{slot}').iterdir()),[])
            return
        self.assertEqual([r['reserved_usd'] for r in History(fixture.state/'credit').read()],[[3,100]])
        self.assertEqual([r['type'] for r in History(fixture.state/f'attempt-{slot}').read()],
                         ['bound_send_reserved','bound_send_attempted'])
