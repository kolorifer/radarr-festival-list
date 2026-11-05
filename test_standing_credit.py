"""Standing promotional-credit preparation; all history/evidence/socket I/O invented."""
import copy,io,time,unittest
from fractions import Fraction
from unittest.mock import patch
from contextlib import redirect_stdout
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.credit_test import request,retained_total,ledger_total,TOTAL,reserve
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL
import test_supervised_credit as fixtures
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing
from test_responses_compatibility import documented

class StandingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.state=self.f.state;self.now=time.time();self.credit=History(self.state/'credit')
        old=dict(self.f.evidence);old['policy']=dict(old['policy']);old['policy'].pop('prompt_cache_retention')
        self.old_hashes={};attempt_rows={};old_evidence=digest(old)
        root=History(self.state)
        with root.transaction(write=True) as (events,append):
            append(dict(type='supervised_started',slot=1,at=self.now-100,evidence_hash=old_evidence))
            append(dict(type='supervised_reauthorized',at=self.now-99,previous_sha256=old_evidence,
                        evidence_sha256=old_evidence,project=old['project'],expires_at=self.now-1,
                        prefix_sha256=digest(events),permitted_slot=2))
            for slot in range(2,7):
                body=decode(request(f'synthetic-integration-{slot}'));body.pop('prompt_cache_retention')
                fingerprint=digest(body);self.old_hashes[slot]=fingerprint
                hpath=self.state/f'attempt-{slot}'
                if slot>=3:hpath.mkdir(mode=0o700)
                h=History(hpath)
                if slot>=3:
                    kind='supervised_recovery' if slot==3 else 'supervised_continuation'
                    start=dict(type=kind+'_started',at=self.now-90+slot,prefix_sha256=digest(events),
                        evidence_sha256=old_evidence,project=old['project'],expires_at=self.now-1,
                        previous_sha256=old_evidence,credit_sha256=digest(self.credit.read()),
                        attempt_sha256=digest(attempt_rows[slot-1]),request_sha256=fingerprint,
                        permitted_slot=slot,cumulative_usd=[(slot-1)*3,100])
                    append(start);append(dict(type=kind+'_authorized',at=self.now-90+slot,start_sha256=digest(start),attempt=list(h.identity)))
                append(dict(type='supervised_started',slot=slot,at=self.now-80+slot,evidence_hash=old_evidence))
                permit=dict(selection=dict(run=f'synthetic-integration-{slot}',case={},request_sha256=fingerprint,
                    local_context_sha256=old_evidence),project=old['project'],model=INTEGRATION_MODEL,
                    expires_at=self.now-1,input_limit=400000,output_limit=4096,maximum_debit=[3,100],currency='USD')
                with h.transaction(write=True) as (_,write):
                    write(dict(type='bound_send_reserved',permit=permit,at=self.now-80+slot))
                    write(dict(type='bound_send_attempted',request_sha256=fingerprint,at=self.now-80+slot))
                attempt_rows[slot]=h.read()
                with self.credit.transaction(write=True) as (_,write):
                    write(dict(type='credit_test_reserved',project=old['project'],model=INTEGRATION_MODEL,
                               request_hash=fingerprint,reserved_usd=[3,100],at=self.now-80+slot))
                if slot>=4:append(dict(type='supervised_diagnostic',slot=slot,at=self.now-70+slot,
                    phase='response_parsing',reason='responses_unsupported_shape',category='protocol_refused'))
        self.assertEqual(len(root.read()),20)
        self.original={p:p.read_bytes() for p in self.state.rglob(FILENAME)}
        self.e=dict(self.f.evidence,credit_kind='promotional',available_usd=[1,1])
        self.selected=self.select(self.e)

    def select(self,e):
        p=self.f.root/('standing-'+str(len(list(self.f.root.glob('standing-*.json'))))+'.json')
        p.write_bytes(encoded(e));p.chmod(0o600);return command.read_evidence(p)

    def preserved(self):
        for p,raw in self.original.items():
            if p.parent.name.startswith('attempt'):self.assertEqual(p.read_bytes(),raw)
            else:self.assertTrue(p.read_bytes().startswith(raw))

    def grant(self):return command.authorize_standing(self.state,self.selected)

    def wire(self,slot,*,bad=False):
        v=documented();reply=decode(v['output'][-1]['content'][0]['text']);reply['binding_hash']=aliases(f'synthetic-integration-{slot}')
        v['output'][-1]['content'][0]['text']=encoded(reply).decode()
        if bad:v['usage']['total_tokens']=1
        return framing.wire(encoded(v),'chunked')

    def test_grant_preserves_legacy_hashes_and_default_cap(self):
        with patch('getpass.getpass') as prompt,patch('socket.socket',side_effect=AssertionError('network')):
            self.assertEqual(self.grant()['status'],'standing_authorized_no_api_call')
        prompt.assert_not_called();self.preserved()
        for slot,fingerprint in self.old_hashes.items():self.assertNotEqual(fingerprint,digest(decode(request(f'synthetic-integration-{slot}'))))
        self.assertEqual(TOTAL,Fraction(5,100))
        with self.assertRaises(Refusal):ledger_total(self.credit.read(),'proj_fixture')
        with self.assertRaises(Refusal):reserve(self.credit,project='proj_fixture',request_hash=digest('unbound'),input_bound=400000,
            now=time.time(),file_identity=command.file_identity(self.credit),debit=(3,100))
        with self.assertRaises(Refusal):self.grant()

    def test_two_distinct_manual_requests_preserve_old_reservations_and_bound_policy(self):
        self.grant();out=io.StringIO()
        for slot in (7,8):
            with diagnostics.DiagnosticTests().inputs(),self.wire(slot),redirect_stdout(out):
                self.assertEqual(command.run_next(self.state,self.selected)['slot'],slot)
        self.assertEqual(out.getvalue().count('OFFLINE_AUTHORIZED_BOUNDARY'),2)
        self.assertEqual(retained_total(self.credit.read(),'proj_fixture'),Fraction(21,100));self.preserved()
        for slot in (7,8):
            with patch.object(command,'prompt_credential') as prompt:
                with self.assertRaises(Refusal):command.run(self.state,self.selected,slot)
            prompt.assert_not_called()
        self.assertEqual(History(self.state/'attempt-8').read()[-1]['type'],'bound_send_receipt')

    def test_uncertain_attempt_is_retained_without_automatic_retry(self):
        self.grant();out=io.StringIO()
        with diagnostics.DiagnosticTests().inputs(),self.wire(7,bad=True),redirect_stdout(out):
            with self.assertRaisesRegex(Refusal,'responses_usage_invalid'):command.run_next(self.state,self.selected)
        self.assertEqual(out.getvalue().count('OFFLINE_AUTHORIZED_BOUNDARY'),1)
        self.assertEqual(retained_total(self.credit.read(),'proj_fixture'),Fraction(18,100))
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(Refusal):command.run(self.state,self.selected,7)
        prompt.assert_not_called();self.assertFalse((self.state/'attempt-8').exists());self.preserved()

    def test_expiry_funds_cash_project_and_policy_refuse_before_prompt_or_append(self):
        self.grant();before=(self.state/FILENAME).read_bytes()
        for delta in ({'expires_at':self.now-1},{'available_usd':[17,100]},{'paid_fallback':True},
                      {'project':'proj_other'},{'account_reference':'different-account'},{'credit_kind':'purchased'},{'policy':dict(self.e['policy'],prompt_cache_retention='24h')},
                      {'credit_expires_at':self.e['credit_expires_at']+1}):
            selected=self.select(dict(self.e,**delta))
            with patch.object(command,'prompt_credential') as prompt:
                with self.assertRaises(Refusal):command.prepare_next(self.state,selected)
            prompt.assert_not_called();self.assertEqual((self.state/FILENAME).read_bytes(),before)
        self.preserved()

    def test_interrupted_preparation_cannot_recreate_or_replay(self):
        self.grant();original=command.Path.mkdir
        def interrupted(path,*a,**kw):
            if path.name=='attempt-7':raise OSError('invented interruption')
            return original(path,*a,**kw)
        with patch.object(command.Path,'mkdir',interrupted):
            with self.assertRaises(OSError):command.prepare_next(self.state,self.selected)
        with self.assertRaisesRegex(Refusal,'supervised_standing_interrupted'):command.prepare_next(self.state,self.selected)
        self.assertFalse((self.state/'attempt-7').exists());self.preserved()

    def test_changed_old_attempt_or_ledger_cannot_be_adopted(self):
        self.grant()
        with History(self.state/'attempt-4').transaction(write=True) as (_,append):append(dict(type='unknown'))
        with self.assertRaisesRegex(Refusal,'supervised_standing_history'):command.prepare_next(self.state,self.selected)
        self.assertFalse((self.state/'attempt-7').exists())

    def test_initial_ceiling_and_fresh_lower_balance_both_bound_next_request(self):
        self.selected=self.select(dict(self.e,available_usd=[18,100]));self.grant()
        with diagnostics.DiagnosticTests().inputs(),self.wire(7),redirect_stdout(io.StringIO()):
            command.run_next(self.state,self.selected)
        before=(self.state/FILENAME).read_bytes()
        # A larger later observation cannot enlarge the original standing ceiling.
        with self.assertRaisesRegex(Refusal,'supervised_standing_credit'):
            command.prepare_next(self.state,self.select(self.e))
        self.assertEqual((self.state/FILENAME).read_bytes(),before)
        self.assertEqual(retained_total(self.credit.read(),'proj_fixture'),Fraction(18,100))
        self.assertFalse((self.state/'attempt-8').exists())

    def test_noninteractive_command_cannot_allocate_an_attempt(self):
        self.grant();before=(self.state/FILENAME).read_bytes()
        with patch.object(command.sys.stdin,'isatty',return_value=False):
            with self.assertRaisesRegex(Refusal,'supervised_interactive_terminal_required'):
                command.run_next(self.state,self.selected)
        self.assertEqual((self.state/FILENAME).read_bytes(),before)
        self.assertFalse((self.state/'attempt-7').exists())

    def test_invalid_secret_does_not_allocate_or_consume(self):
        self.grant();before=(self.state/FILENAME).read_bytes()
        with diagnostics.DiagnosticTests().inputs(),patch('getpass.getpass',return_value='tracking-not-a-secret'):
            with self.assertRaisesRegex(Refusal,'responses_credential_invalid'):
                command.run_next(self.state,self.selected)
        self.assertEqual((self.state/FILENAME).read_bytes(),before)
        self.assertFalse((self.state/'attempt-7').exists());self.preserved()
