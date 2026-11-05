"""Bounded response observation, real fixed HTTP/framing/parser, invented I/O."""
import io,signal,time,unittest
from unittest.mock import patch
from ai_movie_investigator import responses_http as http
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator import supervised_authorization as authority
from ai_movie_investigator.contracts import Refusal
from ai_movie_investigator.history import History
from ai_movie_investigator.responses_transport import real_activation_refusal
import test_supervised_diagnostics as fixtures
import test_supervised_cli as executable


class ObservationTests(fixtures.DiagnosticTests):
    # Select only this class's tests below; inherited diagnostic regressions are
    # already exercised by their original module, not duplicated here.
    def fixture(self):return super().fixture()

    def restored(self):
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM),signal.SIG_DFL)

    def test_valid_response_after_25_seconds_completes_without_second_post(self):
        f=self.fixture();base=io.BytesIO;posts=[]
        namespace={'observed_posts':posts}
        exec(fixtures.WIRE_CODE.replace("print('OFFLINE_AUTHORIZED_BOUNDARY',flush=True)","observed_posts.append(True)"),namespace)
        class Delayed(base):
            waited=False
            def readline(self,*a,**kw):
                if not self.waited:self.waited=True;time.sleep(26)
                return super().readline(*a,**kw)
        started=time.monotonic()
        with self.inputs(),namespace['wire_fixture']('completed'),patch('io.BytesIO',Delayed):
            self.assertEqual(command.run(f.state,f.selected,1)['status'],'completed')
        self.assertGreaterEqual(time.monotonic()-started,26)
        self.assertEqual(posts,[True]);self.restored()
        self.assertEqual(History(f.state/'attempt-1').read()[-1]['type'],'bound_send_receipt')

    def test_absolute_trickle_deadline_never_renews(self):
        f=self.fixture();base=io.BytesIO;mono=time.monotonic;offset=[0]
        class Trickle(base):
            def read1(self,*a,**kw):
                offset[0]+=1
                return super().read1(1)
        with self.inputs(),fixtures.wire_fixture('completed'),patch('io.BytesIO',Trickle),patch('time.monotonic',side_effect=lambda:mono()+offset[0]):
            with self.assertRaisesRegex(Refusal,'responses_observation_deadline_exceeded'):command.run(f.state,f.selected,1)
        row=History(f.state).read()[-1]
        self.assertEqual(row['phase'],'http_body_read');self.assertEqual(row['category'],'local_deadline_outcome_unknown')
        self.assertLessEqual(offset[0],120);self.assertEqual(len(History(f.state/'credit').read()),1);self.restored()

    def test_setup_limit_stays_25_seconds(self):
        f=self.fixture();mono=time.monotonic;offset=[0]
        with self.inputs(),fixtures.wire_fixture('completed'):
            import ssl
            wrap=ssl.SSLContext.wrap_socket
            def slow(context,*a,**kw):
                result=wrap(context,*a,**kw);offset[0]=26;return result
            with patch.object(ssl.SSLContext,'wrap_socket',slow),patch('time.monotonic',side_effect=lambda:mono()+offset[0]):
                with self.assertRaisesRegex(Refusal,'responses_setup_deadline_exceeded'):command.run(f.state,f.selected,1)
        self.assertEqual(History(f.state).read()[-1]['phase'],'tls_handshake');self.restored()

    def test_expired_send_authority_cannot_resend_but_bound_receipt_completes(self):
        f=self.fixture();base=io.BytesIO;wall=time.time;mono=time.monotonic;offset=[0];refusals=[]
        class Later(base):
            waited=False
            def readline(self,*a,**kw):
                if not self.waited:
                    self.waited=True;offset[0]=65
                    session=authority._ACTIVE.get();token=next(iter(session.issued))
                    path,body,credential,project,used=session.issued[token]
                    for consume in (False,True):
                        refusals.append(real_activation_refusal(token,body=body,credential=credential,project=project,path=path,consume=consume))
                return super().readline(*a,**kw)
        with self.inputs(),fixtures.wire_fixture('completed'),patch('io.BytesIO',Later),patch('time.time',side_effect=lambda:wall()+offset[0]),patch('time.monotonic',side_effect=lambda:mono()+offset[0]):
            self.assertEqual(command.run(f.state,f.selected,1,clock=lambda:wall()+offset[0])['status'],'completed')
        self.assertEqual(refusals,['supervised_session_expired','supervised_wire_consumed'])
        self.assertEqual(len(History(f.state/'credit').read()),1);self.restored()

    def test_real_alarm_reason_and_single_observation_transition(self):
        with self.assertRaisesRegex(Refusal,'responses_setup_deadline_exceeded'):
            with http.total_deadline(.03,response_observation=120):time.sleep(.1)
        self.restored()
        real_arm=signal.setitimer;armed=[]
        def quick(which,seconds,*a):
            armed.append(seconds)
            return real_arm(which,.03 if seconds>25 else seconds,*a)
        with patch('signal.setitimer',side_effect=quick):
            with self.assertRaisesRegex(Refusal,'responses_observation_deadline_exceeded'):
                with http.total_deadline(25,response_observation=120) as check:
                    check.begin_observation(time.monotonic());time.sleep(.1)
        self.assertTrue(any(119<seconds<=120 for seconds in armed));self.restored()
        with http.total_deadline(25,response_observation=120) as check:
            check.begin_observation(time.monotonic())
            with self.assertRaisesRegex(Refusal,'responses_observation_transition'):check.begin_observation(time.monotonic())
        self.restored()
        with self.assertRaises(TimeoutError):
            with http.total_deadline(.03):time.sleep(.1)
        self.assertIsNone(authority.response_observation_window(None,b'{}',None,'proj_fixture','/v1/responses'))
        self.restored()

    def test_installed_command_observation_cutoff_is_safe(self):
        f=self.fixture()
        extension=fixtures.WIRE_CODE+'''
FixedResponsesHTTP.post=original_post
wire_fixture('completed').__enter__()
import io,time
_base=io.BytesIO
_mono=time.monotonic
_offset=[0]
class LateHeaders(_base):
    waited=False
    def readline(self,*a,**kw):
        if not self.waited:self.waited=True;_offset[0]=121
        return super().readline(*a,**kw)
io.BytesIO=LateHeaders
time.monotonic=lambda:_mono()+_offset[0]
'''
        executable.SupervisedExecutableTests().execute_fixture(f,1,hook_extension=extension,
            category='local_deadline_outcome_unknown',expected_reason='responses_observation_deadline_exceeded',expected_phase='http_response_received')


# Inherit just the fixture helpers, not the parent's unrelated test methods.
for _name in list(vars(fixtures.DiagnosticTests)):
    if _name.startswith('test_') and _name not in vars(ObservationTests):setattr(ObservationTests,_name,None)
