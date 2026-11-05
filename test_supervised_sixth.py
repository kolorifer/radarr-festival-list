"""One explicit slot6 on invented retained state; dummy input and offline I/O."""
import io,time,unittest
from contextlib import redirect_stdout
from fractions import Fraction
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator import supervised_authorization as authority
from ai_movie_investigator.contracts import Refusal,encoded,digest
from ai_movie_investigator.credit_test import ledger_total,reserve,TOTAL
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.responses_http import FixedResponsesHTTP
import test_supervised_fifth as fifth
import test_supervised_envelope as envelope
import test_supervised_cli as executable


class SixthTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time()
        self.f=fifth.FifthTests('test_ungranted_slot_five_and_six_refuse_without_prompt')
        def terminal(*a,**kw):
            authority.observe_phase('http_body_read' if self._testMethodName=='test_wrong_terminal_refuses' else 'http_response_received')
            raise Refusal('responses_body_limit')
        with patch('time.time',return_value=self.now-600):
            self.f.setUp();self.f.extend()
            with self.f.c.r.inputs(),patch.object(FixedResponsesHTTP,'post',side_effect=terminal):
                with self.assertRaisesRegex(Refusal,'responses_body_limit'):
                    command.run(self.f.state,self.f.selected,5,clock=lambda:self.now-600)
        self.addCleanup(self.f.doCleanups)
        self.state=self.f.state;self.fixture=self.f.fixture
        self.new=dict(self.f.new,observed_at=self.now-1,expires_at=self.now+200,credit_expires_at=self.now+300,
                      owner_reference='FIXTURE-one-slot6-fifteen-cent-total')
        self.path=self.fixture.root/'sixth.json';self.path.write_bytes(encoded(self.new));self.path.chmod(0o600)
        self.selected=command.read_evidence(self.path)
        self.original={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        self.assertEqual(len(History(self.state).read()),16)
        self.assertEqual(len(History(self.state/'credit').read()),4)

    def extend(self):return command.recover_once(self.state,self.f.selected,self.selected,slot=6)

    def preserved(self):
        for p,b in self.original.items():
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),b)
            else:self.assertTrue(p.read_bytes().startswith(b))
        self.assertEqual(list((self.state/'attempt-1').iterdir()),[])

    def test_single_extension_retains_fifteen_cents_default_cap_and_no_replay(self):
        with patch('getpass.getpass') as prompt,patch.object(FixedResponsesHTTP,'post') as post,patch('socket.socket',side_effect=AssertionError('network')):
            self.assertEqual(self.extend(),dict(status='recovery_authorized_no_api_call',permitted_slot=6,cumulative_usd=[15,100]))
        prompt.assert_not_called();post.assert_not_called();self.preserved()
        ns={};exec(envelope.ENVELOPE_CODE.replace("run='synthetic-integration-1'","run='synthetic-integration-6'"),ns)
        ns.update(selected_raw=ns['envelope'](opaque=40000,two=True),framing='chunked');exec(envelope.wire_code(),ns)
        output=io.StringIO()
        with self.f.c.r.inputs(),ns['wire_fixture']('completed','synthetic-integration-6'),redirect_stdout(output):
            self.assertEqual(command.run(self.state,self.selected,6)['status'],'completed')
        self.assertEqual(output.getvalue().count('OFFLINE_AUTHORIZED_BOUNDARY'),1)
        rows=History(self.state/'credit').read();self.assertEqual([e['reserved_usd'] for e in rows],[[3,100]]*5)
        self.assertEqual(ledger_total(rows,'proj_fixture',ceiling=Fraction(15,100)),Fraction(15,100))
        self.assertEqual(TOTAL,Fraction(5,100))
        with self.assertRaises(Refusal):ledger_total(rows,'proj_fixture')
        credit=History(self.state/'credit')
        with self.assertRaises(Refusal):reserve(credit,project='proj_fixture',request_hash=digest('seventh'),input_bound=400000,
            now=self.now,file_identity=command.file_identity(credit),debit=(3,100))
        for slot in range(1,8):
            with patch('getpass.getpass') as prompt:
                with self.assertRaises(Refusal):command.run(self.state,command.read_evidence(self.path),slot)
            prompt.assert_not_called()
        with self.assertRaises(Refusal):self.extend()
        self.assertNotIn(b'OPAQUE_FIXTURE_',b''.join(p.read_bytes() for p in self.state.rglob(FILENAME)))
        self.preserved()

    def test_invalid_input_and_duplicate_grant_change_nothing(self):
        self.extend();before={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        with self.assertRaises(Refusal):self.extend()
        with self.f.c.r.inputs('key_TRACKING_NOT_SECRET'),patch.object(FixedResponsesHTTP,'post') as post:
            with self.assertRaisesRegex(Refusal,'responses_credential_invalid'):command.run(self.state,self.selected,6)
        post.assert_not_called();self.assertEqual(before,{p:p.read_bytes() for p in self.state.rglob(FILENAME)})
        self.assertEqual(list((self.state/'attempt-6').iterdir()),[])

    def test_ungranted_sixth_and_seventh_refuse_without_prompt(self):
        with patch('getpass.getpass') as prompt:
            for slot in (6,7):
                with self.assertRaises(Refusal):command.run(self.state,self.selected,slot)
            with self.assertRaises(Refusal):command.recover_once(self.state,self.f.selected,self.selected,slot=7)
        prompt.assert_not_called();self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])

    def test_interrupted_grant_stays_terminal(self):
        original=command.Path.mkdir
        def fail(path,*a,**kw):
            if path.name=='attempt-6':raise OSError('fixture interruption')
            return original(path,*a,**kw)
        with patch.object(command.Path,'mkdir',fail):
            with self.assertRaises(OSError):self.extend()
        self.assertEqual(len(History(self.state).read()),17)
        with self.assertRaises(Refusal):self.extend()
        with self.assertRaises(Refusal):command.run(self.state,self.selected,6)
        self.assertFalse((self.state/'attempt-6').exists());self.preserved()

    def test_changed_project_credit_or_retained_history_refuses(self):
        for delta in ({'project':'proj_other'},{'available_usd':[14,100]},{'expires_at':self.now-2}):
            self.path.write_bytes(encoded(dict(self.new,**delta)))
            with self.assertRaises(Refusal):command.recover_once(self.state,self.f.selected,command.read_evidence(self.path),slot=6)
            self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])
        self.path.write_bytes(encoded(self.new));self.selected=command.read_evidence(self.path)
        with History(self.state/'attempt-4').transaction(write=True) as (_,append):append(dict(type='unknown'))
        with self.assertRaises(Refusal):self.extend()

    def test_wrong_terminal_refuses(self):
        with self.assertRaisesRegex(Refusal,'supervised_recovery_state'):self.extend()
        self.assertEqual((self.state/FILENAME).read_bytes(),self.original[self.state/FILENAME])

    def test_genuine_installed_sixth_uses_one_mib_and_120_seconds(self):
        extension=envelope.ENVELOPE_CODE.replace("run='synthetic-integration-1'","run='synthetic-integration-6'")
        extension+="""
import json
from ai_movie_investigator.contracts import encoded
_value=json.loads(envelope(target=1048576,change='incomplete'))
_extra=len(encoded(_value))-1048576
assert _extra>0
_value['output'][0]['encrypted_content']=_value['output'][0]['encrypted_content'][:-_extra]
selected_raw=encoded(_value)
assert len(selected_raw)==1048576
framing='chunked'
"""+envelope.wire_code()+"\nFixedResponsesHTTP.post=original_post\nwire_fixture('completed','synthetic-integration-6').__enter__()\n"
        extension+='''
import io,time
_base=io.BytesIO
_mono=time.monotonic
_offset=[0]
class LateHeaders(_base):
    waited=False
    def readline(self,*a,**kw):
        if not self.waited:self.waited=True;_offset[0]=30
        return super().readline(*a,**kw)
io.BytesIO=LateHeaders
time.monotonic=lambda:_mono()+_offset[0]
'''
        executable.SupervisedExecutableTests().execute_fixture(self.fixture,6,sixth=self,hook_extension=extension,
            category='protocol_refused',expected_reason='responses_not_completed',expected_phase='response_parsing')
        self.preserved()
