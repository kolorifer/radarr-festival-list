"""Bounded account freshness, short prompt authority, and redacted CLI refusals."""
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator import supervised_authorization as auth
from ai_movie_investigator.contracts import Refusal,encoded,decode
from ai_movie_investigator.history import History
from ai_movie_investigator.installation import install_runtime
import test_supervised_credit as fixtures


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_account_window_exact_900_and_no_expired_or_credit_extension(self):
        now=self.f.now
        e=dict(self.f.evidence,expires_at=now+899,credit_expires_at=now+1000)
        command.validate_evidence(e,now)
        for changed,at in ((dict(e,expires_at=now+900),now),(e,now+899),
                           (dict(e,credit_expires_at=now+100),now),(e,now-2)):
            with self.assertRaises(Refusal):command.validate_evidence(changed,at)

    def test_session_caps_wall_monotonic_credit_and_cannot_revive(self):
        f=self.f;root=History(f.state);rows=root.read();credit=History(f.state/'credit');attempt=History(f.state/'attempt-1')
        def session():return auth._Session(root,rows,rows[1],f.selected,1,credit,attempt,key)
        with patch.object(command,'prompt_credential',return_value=command.ExplicitCredential(f.key)):
            with command.interactive_credential(root) as key:
                s=session()
                self.assertEqual(s.deadline,s.started_wall+60)
                with patch('time.time',return_value=s.started_wall+59),patch('time.monotonic',return_value=s.started_monotonic+59):
                    self.assertLess(s.check_time(),s.deadline)
                with patch('time.time',return_value=s.started_wall+60),patch('time.monotonic',return_value=s.started_monotonic+60):
                    with self.assertRaisesRegex(Refusal,'supervised_session_expired'):s.check_time()
                with self.assertRaisesRegex(Refusal,'supervised_session_expired'):s.check_time()
                s=session()
                with patch('time.monotonic',return_value=s.started_monotonic+60):
                    with self.assertRaisesRegex(Refusal,'supervised_session_expired'):s.check_time()
                s=session()
                with patch('time.time',return_value=s.started_wall-1):
                    with self.assertRaisesRegex(Refusal,'supervised_clock_rollback'):s.check_time()
                s=session()
                with patch('time.monotonic',return_value=s.started_monotonic-1):
                    with self.assertRaisesRegex(Refusal,'supervised_clock_rollback'):s.check_time()

    def test_session_uses_prompt_time_not_delayed_session_creation(self):
        f=self.f;root=History(f.state);rows=root.read()
        with patch.object(command,'prompt_credential',return_value=command.ExplicitCredential(f.key)):
            with command.interactive_credential(root) as key:
                wall,mono=command.require_prompted(root,key)
                with patch('time.time',return_value=wall+61),patch('time.monotonic',return_value=mono+61):
                    s=auth._Session(root,rows,rows[1],f.selected,1,History(f.state/'credit'),History(f.state/'attempt-1'),key)
                    with self.assertRaisesRegex(Refusal,'supervised_session_expired'):s.check_time()
        self.assertEqual(History(f.state/'credit').read(),[])

    def test_evidence_expiry_clips_session_and_operator_permit(self):
        f=self.f
        f.path.write_bytes(encoded(dict(f.evidence,expires_at=f.now+20,credit_expires_at=f.now+25)))
        selected=command.read_evidence(f.path);root=History(f.state);rows=root.read()
        with patch.object(command,'prompt_credential',return_value=command.ExplicitCredential(f.key)):
            with command.interactive_credential(root) as key:
                s=auth._Session(root,rows,rows[1],selected,1,History(f.state/'credit'),History(f.state/'attempt-1'),key)
                self.assertEqual(s.deadline,f.now+20)
                context,_=command.operator_context(selected.data,History(f.state/'attempt-1'),History(f.state/'credit'),
                    rows[1],'synthetic-integration-1',{},f.now,expires_at=s.deadline)
                self.assertEqual(decode(context.record_json)['expires_at'],s.deadline)

    def test_900_second_evidence_still_has_60_second_actual_send_gate(self):
        f=self.f;f.evidence=dict(f.evidence,expires_at=f.now+899,credit_expires_at=f.now+1000)
        f.path.write_bytes(encoded(f.evidence));f.selected=command.read_evidence(f.path)
        f.state=f.root/'fresh-state';f.state.mkdir(mode=0o700);command.enroll(f.state,f.selected)
        def sink(body,**kw):
            session=auth._ACTIVE.get()
            self.assertLessEqual(session.deadline,session.started_wall+60)
            permit=History(f.state/'attempt-1').read()[0]['permit']
            self.assertEqual(permit['expires_at'],session.deadline)
            with patch('time.monotonic',return_value=session.started_monotonic+60):
                self.assertEqual(auth.refusal(kw['authorization'],body=body,credential=kw['credential'],
                    project=kw['project'],path='/v1/responses'),'supervised_authorization_refused')
            self.assertEqual(auth.refusal(kw['authorization'],body=body,credential=kw['credential'],
                project=kw['project'],path='/v1/responses'),'supervised_authorization_refused')
            raise Refusal('binding_response_unknown')
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',return_value=f.key),patch('socket.socket',side_effect=AssertionError('network')),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=sink):
            with self.assertRaisesRegex(Refusal,'binding_response_unknown'):command.run(f.state,f.selected,1)
        self.assertEqual([r['reserved_usd'] for r in History(f.state/'credit').read()],[[3,100]])

    def test_static_categories_never_echo_unknown_exception(self):
        for error in (Refusal('sk_PRIVATE /private/input'),RuntimeError('sk_PRIVATE /private/input'),
                      OSError('sk_PRIVATE /private/input'),Refusal({'secret':'sk_PRIVATE'})):
            value=command.refusal_category(error)
            self.assertIn(value,('unclassified_refusal','io_refused'))
            self.assertNotIn('PRIVATE',value)

    def test_actual_module_redacts_expiry_file_change_unknown_and_action(self):
        f=self.f
        installed=f.root/'installed';installed.mkdir(mode=0o700)
        install_runtime(Path(__file__).resolve().parent,installed)
        hooks=f.root/'hooks';hooks.mkdir(mode=0o700)
        common='''
import errno,os,socket,ssl,sys
from ai_movie_investigator import supervised_credit as c
from ai_movie_investigator.contracts import Refusal
if sys.platform.startswith('linux'):
 def absent(*a,**k):raise OSError(errno.ENODATA,'fixture absent ACL')
 os.getxattr=absent
def blocked(*a,**k):raise AssertionError('network')
socket.socket=blocked;socket.getaddrinfo=blocked
'''
        changes={
            'evidence_expired_or_invalid_window':"c.time.time=lambda:2000000000\n",
            'evidence_changed':"old=c.read_private\ndef change(p,limit):\n raw=old(p,limit);s=p.stat();os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1));return raw\nc.read_private=change\n",
            'unclassified_refusal':"def unknown(p):raise Refusal('sk_PRIVATE /private/input body')\nc.read_evidence=unknown\n",
        }
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(hooks),str(installed))),PYTHONDONTWRITEBYTECODE='1')
        env={k:v for k,v in env.items() if not any(s in k.upper() for s in ('KEY','TOKEN','SECRET','PASSWORD'))}
        for category,hook in changes.items():
            (hooks/'sitecustomize.py').write_text(common+hook)
            result=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(f.state),
                'run','--evidence',str(f.path),'--slot','1'],cwd=installed,env=env,capture_output=True,timeout=15)
            output=result.stdout+result.stderr
            self.assertEqual(result.returncode,1)
            self.assertIn(('category='+category).encode(),output)
            self.assertIn(b'action=run; request status unconfirmed',output)
            for secret in (b'sk_PRIVATE',b'/private/input',str(f.path).encode(),b'Traceback',b'Restricted project API key'):
                self.assertNotIn(secret,output)
        (hooks/'sitecustomize.py').write_text(common+changes['unclassified_refusal'])
        for action,extra in (('enroll',[]),('reauthorize',['--previous-evidence',str(f.path)])):
            result=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit','--state',str(f.state),
                action,'--evidence',str(f.path),*extra],cwd=installed,env=env,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,1);self.assertIn(('action='+action+'; no API request').encode(),result.stderr)
        result=subprocess.run([sys.executable,'-B','-m','ai_movie_investigator.supervised_credit',
            '--state',str(f.state),'sk_PRIVATE /private/input'],cwd=installed,env=env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,2);self.assertIn(b'category=invalid_arguments; action=unknown',result.stderr)
        self.assertNotIn(b'sk_PRIVATE',result.stderr);self.assertNotIn(b'/private/input',result.stderr)
        self.assertEqual(len(History(f.state).read()),2)
        self.assertEqual(History(f.state/'credit').read(),[])
