import io
import errno
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.credit_test import request,count_request
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.history import History
from ai_movie_investigator.responses_http import HTTPResult,ExplicitCredential,FixedResponsesHTTP
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL
from ai_movie_investigator.responses_transport import real_activation_refusal


class SupervisedCreditTests(unittest.TestCase):
    def setUp(self):
        if sys.platform.startswith('linux'):
            # Hosted runner ancestors may have ACLs. Replace only kernel ACL
            # metadata I/O for this fixture; never relax the runtime guard.
            acl_io=patch('ai_movie_investigator.private_files.os.getxattr',
                         side_effect=OSError(errno.ENODATA,'fixture absent ACL'))
            acl_io.start();self.addCleanup(acl_io.stop)
        self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.state=self.root/'state';self.state.mkdir(mode=0o700)
        self.now=time.time()
        self.evidence=dict(project='proj_fixture',account_reference='FIXTURE-account',observed_at=self.now-1,
            expires_at=self.now+200,credit_expires_at=self.now+300,available_usd=[19,1],billing_reference='FIXTURE-no-billing',
            paid_fallback=False,owner_reference='FIXTURE-owner',model=INTEGRATION_MODEL,
            policy=dict(model=INTEGRATION_MODEL,service_tier='default'),context_window=400000,
            pricing_reference='FIXTURE-pricing',context_reference='FIXTURE-context',model_access_reference='FIXTURE-access',
            input_rate=[5,100000000],cached_input_rate=[5,1000000000],output_rate=[4,10000000])
        self.path=self.root/'evidence.json';self.path.write_bytes(encoded(self.evidence));self.path.chmod(0o600)
        self.selected=command.read_evidence(self.path)
        command.enroll(self.state,self.selected)
        self.key='sk-SYNTHETIC_NOT_REAL';self.seen=[];self.tokens=[]

    def authorize(self,path,body,kw):
        token=kw['authorization'];self.tokens.append(token)
        args=dict(body=body,credential=kw['credential'],project=kw['project'],path=path)
        # Test the actual implementation. Only HTTP I/O and local terminal I/O are replaced.
        self.assertIsNone(real_activation_refusal(token,**args))
        self.assertIsNone(real_activation_refusal(token,**args,consume=False))
        self.assertIsNotNone(real_activation_refusal(token,**args))
        self.assertIsNotNone(real_activation_refusal(token,**dict(args,project='proj_wrong'),consume=False))
        self.assertIsNotNone(real_activation_refusal(token,**dict(args,body=b'{}'),consume=False))
        self.assertIsNotNone(real_activation_refusal(token,**dict(args,credential=ExplicitCredential(self.key)),consume=False))
        self.assertIsNotNone(real_activation_refusal(token,**dict(args,path='/v1/responses/other'),consume=False))

    def generate(self,body,**kw):
        self.authorize('/v1/responses',body,kw)
        self.assertEqual(len(History(self.state/'credit').read()),1)
        self.assertEqual(History(self.state/'credit').read()[0]['reserved_usd'],[3,100])
        self.assertEqual(body,request('synthetic-integration-1'))
        self.assertEqual(History(self.state/'attempt-1').read()[0]['permit']['input_limit'],400000)
        self.seen.append('generation')
        reply=dict(binding_hash=aliases('synthetic-integration-1'),kind='final',lookups=[],result=dict(
            status='unresolved',candidate=None,alternatives=[],citations=[],rationale='Synthetic only',
            uncertainty='No real evidence',next_action='human_review'))
        raw=decode(simulated_response(reply,1).body);raw['model']=INTEGRATION_MODEL
        raw.pop('prompt_cache_options');raw['usage']['input_tokens_details']={'cached_tokens':0}
        return HTTPResult(200,encoded(raw),'req_fixture_generation',digest(decode(body)),kw['project'],'/v1/responses')

    def invoke(self,selected=None):
        return command.run(self.state,selected or self.selected,1,clock=lambda:self.now)

    def test_executable_generation_only_no_count_and_no_restart(self):
        args=['--state',str(self.state),'run','--evidence',str(self.path),'--slot','1']
        out=io.StringIO()
        with patch('socket.socket',side_effect=AssertionError('network')),patch.object(command.sys.stdin,'isatty',return_value=True),\
             patch.object(command.sys.stderr,'isatty',return_value=True),patch('getpass.getpass',return_value=self.key) as prompt,\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.count',side_effect=AssertionError('count forbidden')),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=self.generate):
            with redirect_stdout(out):self.assertEqual(command.main(args),0)
            with redirect_stdout(out):self.assertEqual(command.main(args),1)
            self.assertEqual(prompt.call_count,1)
        self.assertEqual(self.seen,['generation'])
        self.assertNotIn(self.key,out.getvalue())
        for path in self.state.rglob('*.jsonl'):self.assertNotIn(self.key,path.read_text())
        self.assertEqual(History(self.state).read()[-1]['reserved_usd'],[3,100])
        for token in self.tokens:self.assertIsNotNone(real_activation_refusal(token))

    def test_unknown_model_pricing_or_account_refuses_before_prompt_and_debit(self):
        for change in ({'pricing_reference':None},{'input_rate':None},
                       {'context_reference':'unknown'},{'model':'gpt-5-nano'},{'context_window':399999},{'paid_fallback':True},{'expires_at':self.now-1}):
            self.path.write_bytes(encoded(dict(self.evidence,**change)))
            selected=command.read_evidence(self.path)
            with patch.object(command,'prompt_credential') as prompt:
                with self.assertRaises((Refusal,TypeError)):self.invoke(selected)
            prompt.assert_not_called()
        self.assertEqual(History(self.state/'credit').read(),[])

    def test_generation_timeout_burns_three_cents_and_never_replays(self):
        def timeout(body,**kw):
            self.authorize('/v1/responses',body,kw)
            raise TimeoutError()
        with patch.object(command.sys.stdin,'isatty',return_value=True), patch.object(command.sys.stderr,'isatty',return_value=True), patch('getpass.getpass',return_value=self.key),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=timeout) as generate,\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.count') as count:
            with self.assertRaises(TimeoutError):self.invoke()
            with self.assertRaisesRegex(Refusal,'supervised_attempt_consumed'):self.invoke()
        self.assertEqual(generate.call_count,1);count.assert_not_called()
        self.assertEqual(len(History(self.state/'credit').read()),1)
        for token in self.tokens:self.assertIsNotNone(real_activation_refusal(token))

    def test_dict_or_changed_enrollment_refuses_before_prompt(self):
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaisesRegex(Refusal,'supervised_evidence_selection'):
                command.run(self.state,self.evidence,1)
            self.path.write_bytes(encoded(dict(self.evidence,project='proj_other')))
            with self.assertRaisesRegex(Refusal,'supervised_enrollment_binding'):
                self.invoke(command.read_evidence(self.path))
        prompt.assert_not_called()
        self.assertEqual(History(self.state/'credit').read(),[])

    def test_forged_json_boolean_or_unregistered_object_never_unlocks_http(self):
        with patch('socket.socket',side_effect=AssertionError('network')):
            for permit in (None,True,{'approved':True},self.evidence,object()):
                with self.assertRaisesRegex(Refusal,'responses_real_authorization_unimplemented'):
                    FixedResponsesHTTP().count(count_request('one'),credential=ExplicitCredential(self.key),
                        project='proj_fixture',timeout=1,authorization=permit)

    def test_non_tty_refuses_credential_and_no_getpass_fallback(self):
        with patch.object(command.sys.stdin,'isatty',return_value=False),patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'supervised_interactive_terminal_required'):command.prompt_credential()
        prompt.assert_not_called()

    def test_enrollment_not_recreated_and_missing_journal_refuses(self):
        with self.assertRaisesRegex(Refusal,'supervised_enrollment_exists'):command.enroll(self.state,self.selected)
        (self.state/'credit'/'ai-investigator-v1.jsonl').unlink()
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(FileNotFoundError):self.invoke()
        prompt.assert_not_called()

    def test_evidence_change_after_reservation_refuses_authorization(self):
        def changed(body,**kw):
            self.path.write_bytes(encoded(dict(self.evidence,pricing_reference='changed')))
            self.assertIsNotNone(real_activation_refusal(kw['authorization'],body=body,
                credential=kw['credential'],project=kw['project'],path='/v1/responses'))
            raise Refusal('refused')
        with patch.object(command.sys.stdin,'isatty',return_value=True), patch.object(command.sys.stderr,'isatty',return_value=True), patch('getpass.getpass',return_value=self.key),\
             patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=changed):
            with self.assertRaises(Refusal):self.invoke()
        self.assertEqual(len(History(self.state/'credit').read()),1)

    def test_expiry_after_prompt_blocks_generation_without_debit(self):
        def late_prompt(*args):
            self.now+=201
            return self.key
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',side_effect=late_prompt),patch.object(FixedResponsesHTTP,'post') as generation:
            with self.assertRaisesRegex(Refusal,'supervised_evidence_stale'):self.invoke()
        generation.assert_not_called()
        self.assertEqual(History(self.state/'credit').read(),[])

    def test_frozen_clock_cannot_bypass_actual_expiry_before_prompt(self):
        with patch('time.time',return_value=self.now+201),patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'supervised_evidence_stale'):self.invoke()
        prompt.assert_not_called()
        self.assertEqual(History(self.state/'credit').read(),[])

    def test_wall_expiry_and_rollback_refuse_issued_token(self):
        def expired(body,**kw):
            for wall in (self.now+201,self.now-10):
                with patch('time.time',return_value=wall):
                    self.assertIsNotNone(real_activation_refusal(kw['authorization'],body=body,
                        credential=kw['credential'],project=kw['project'],path='/v1/responses'))
            raise Refusal('clock_refused')
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',return_value=self.key),patch.object(FixedResponsesHTTP,'post',side_effect=expired):
            with self.assertRaisesRegex(Refusal,'clock_refused'):self.invoke()
        self.assertEqual(len(History(self.state/'credit').read()),1)

    def test_authority_requires_held_durable_transaction_and_prompt(self):
        from ai_movie_investigator.supervised_authorization import command_authority
        root=History(self.state);credit=History(self.state/'credit');history=History(self.state/'attempt-1')
        key=ExplicitCredential(self.key)
        events=root.read()
        def attempt(rows):
            with command_authority(root,rows,rows[1],self.selected,1,credit,history,key):
                self.fail('untrusted authority accepted')
        with self.assertRaisesRegex(Refusal,'history_transaction_required'):attempt(events)
        with root.transaction(write=True) as (rows,append):
            with self.assertRaisesRegex(Refusal,'supervised_prompt_required'):attempt(rows)
            invented=list(rows)
            with self.assertRaisesRegex(Refusal,'history_transaction_required'):attempt(invented)
            rows.append(dict(type='supervised_started',slot=1))
            with self.assertRaisesRegex(Refusal,'history_transaction_changed'):attempt(rows)
            rows.pop()
        with self.assertRaisesRegex(Refusal,'history_transaction_required'):root.require_write_transaction(rows)

    def test_acl_and_writable_ancestor_refuse_evidence(self):
        from ai_movie_investigator import private_files
        with patch.object(private_files,'safe_acl',side_effect=Refusal('fixture_acl')):
            with self.assertRaisesRegex(Refusal,'fixture_acl'):command.read_evidence(self.path)
        outer=self.root/'shared';outer.mkdir(mode=0o700);inner=outer/'private';inner.mkdir(mode=0o700)
        leaf=inner/'evidence.json';leaf.write_bytes(encoded(self.evidence));leaf.chmod(0o600)
        outer.chmod(0o775)
        try:
            with self.assertRaisesRegex(Refusal,'unsafe_parent'):command.read_evidence(leaf)
        finally:outer.chmod(0o700)

    def test_file_acl_checked_separately(self):
        from ai_movie_investigator import private_files
        original=private_files.safe_acl
        def check(fd,directory):
            if not directory:raise Refusal('fixture_file_acl')
            return original(fd,directory)
        with patch.object(private_files,'safe_acl',side_effect=check):
            with self.assertRaisesRegex(Refusal,'fixture_file_acl'):command.read_evidence(self.path)

    def test_ctime_between_reads_is_not_a_persistent_identity_pin(self):
        self.path.chmod(0o400);self.path.chmod(0o600)
        self.selected.revalidate()

    def test_metadata_change_during_read_still_refuses(self):
        original=command.read_private
        def changed(path,limit):
            raw=original(path,limit)
            path.chmod(0o400);path.chmod(0o600)
            return raw
        with patch.object(command,'read_private',side_effect=changed):
            with self.assertRaisesRegex(Refusal,'supervised_evidence_changed'):self.selected.revalidate()

    def test_linux_acl_absence_presence_and_unknown_are_distinct(self):
        from ai_movie_investigator.private_files import linux_acl
        with patch('os.getxattr',side_effect=OSError(errno.ENODATA,'absent'),create=True) as read:
            linux_acl(123,True)
            self.assertEqual([c.args[1] for c in read.call_args_list],
                             ['system.posix_acl_access','system.posix_acl_default'])
        for result in (b'present', OSError(errno.ENOTSUP,'unknown')):
            with patch('os.getxattr',create=True) as read:
                if isinstance(result,Exception):read.side_effect=result
                else:read.return_value=result
                with self.assertRaisesRegex(Refusal,'storage_acl'):linux_acl(123,False)

    def test_two_legacy_cents_plus_generation_preserves_five_cent_total(self):
        from ai_movie_investigator.credit_test import reserve
        credit=History(self.state/'credit')
        for n in range(2):
            reserve(credit,project='proj_fixture',request_hash=digest(['old',n]),input_bound=65536,
                    now=self.now-1,file_identity=command.file_identity(credit))
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',return_value=self.key),patch.object(FixedResponsesHTTP,'post',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):self.invoke()
        self.assertEqual([e['reserved_usd'] for e in credit.read()],[[1,100],[1,100],[3,100]])
        with patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'credit_total_ceiling'):
                command.run(self.state,self.selected,2,clock=lambda:self.now)
        prompt.assert_not_called()

    def test_old_consumed_slot_is_never_reused(self):
        with History(self.state).transaction(write=True) as (_,append):
            append(dict(type='supervised_count_attempted',slot=1,request_hash=digest('old'),at=self.now-1))
        with patch('getpass.getpass') as prompt:
            with self.assertRaisesRegex(Refusal,'supervised_attempt_consumed'):self.invoke()
        prompt.assert_not_called()

    def test_invalid_usage_keeps_full_three_cent_debit(self):
        def bad(body,**kw):
            result=self.generate(body,**kw)
            from dataclasses import replace
            raw=decode(result.body);raw['usage']['input_tokens']=400001
            return replace(result,body=encoded(raw))
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),\
             patch('getpass.getpass',return_value=self.key),patch.object(FixedResponsesHTTP,'post',side_effect=bad):
            with self.assertRaises(Refusal):self.invoke()
        self.assertEqual(History(self.state/'credit').read()[0]['reserved_usd'],[3,100])
        self.assertFalse(any(e['type']=='supervised_completed' for e in History(self.state).read()))
