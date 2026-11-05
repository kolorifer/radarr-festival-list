"""Injected finite failures only; no historical replay or reproduction loop."""
import errno
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from ai_movie_investigator import supervised_authorization as auth,supervised_credit as command
from ai_movie_investigator.contracts import Refusal
import test_supervised_credit as fixtures
import test_supervised_diagnostics as diagnostics
import test_supervised_cli as executable
from ai_movie_investigator.history import History

class StaticDiagnosticTests(unittest.TestCase):
    def test_authority_preserves_only_allowlisted_reasons_and_finite_exception_classes(self):
        class CustomRefusal(Refusal):pass
        cases=[(Refusal('supervised_clock_rollback'),'supervised_clock_rollback'),
               (Refusal('storage_acl'),'storage_acl'),
               (Refusal('PRIVATE_MESSAGE /private/path'),'supervised_authorization_refused'),
               (CustomRefusal('storage_acl'),'supervised_authorization_refused'),
               (Refusal('storage_acl','PRIVATE_MESSAGE'),'supervised_authorization_refused'),
               (OSError(errno.EACCES,'PRIVATE_MESSAGE','/private/path'),'supervised_authorization_io_error'),
               (ValueError('PRIVATE_MESSAGE'),'supervised_authorization_value_error'),
               (TypeError('PRIVATE_MESSAGE'),'supervised_authorization_type_error'),
               (KeyError('PRIVATE_MESSAGE'),'supervised_authorization_key_error')]
        for error,reason in cases:
            token=auth._Permit();credential=object();bound=('/v1/responses',b'{}',credential,'proj_fixture',False)
            session=SimpleNamespace(issued={token:bound},check=Mock(side_effect=error))
            mark=auth._ACTIVE.set(session)
            try:
                with self.subTest(reason=reason):
                    actual=auth.refusal(token,path=bound[0],body=bound[1],credential=credential,project=bound[3])
                    self.assertEqual(actual,reason);self.assertEqual(session.issued[token],bound)
                    session.check.assert_called_once()
                    self.assertNotIn('PRIVATE',json.dumps(command.safe_diagnostic(Refusal(actual))))
            finally:auth._ACTIVE.reset(mark)

    def test_token_transition_and_early_binding_checks_remain_closed(self):
        token=auth._Permit();credential=object();bound=('/v1/responses',b'{}',credential,'proj_fixture',False)
        session=SimpleNamespace(issued={token:bound},check=Mock())
        mark=auth._ACTIVE.set(session)
        try:
            self.assertEqual(auth.refusal(token,path='wrong',body=b'{}',credential=credential,project=bound[3]),'supervised_wire_binding')
            session.check.assert_not_called();self.assertEqual(session.issued[token],bound)
            kw=dict(path=bound[0],body=bound[1],credential=credential,project=bound[3])
            self.assertIsNone(auth.refusal(token,**kw));self.assertTrue(session.issued[token][-1])
            self.assertEqual(auth.refusal(token,**kw),'supervised_wire_consumed')
            self.assertEqual(session.check.call_count,1)
        finally:auth._ACTIVE.reset(mark)

    def test_per_read_component_labels_use_only_existing_two_stats_and_one_read(self):
        fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
        labels=('device','inode','size','mtime','ctime')
        before=SimpleNamespace(**{k:i+100 for i,k in enumerate(fields)})
        for field,label in zip(fields,labels):
            after=SimpleNamespace(**vars(before));setattr(after,field,getattr(after,field)+1)
            with patch.object(Path,'lstat',side_effect=[before,after]) as stats,patch.object(command,'read_private',return_value=b'{}') as reader:
                with self.subTest(label=label),self.assertRaisesRegex(Refusal,'^supervised_evidence_changed_read_'+label+'$'):
                    command._read_evidence(Path('/invented/evidence'))
                self.assertEqual(stats.call_count,2);reader.assert_called_once()
        after=SimpleNamespace(**{k:0 for k in fields})
        with patch.object(Path,'lstat',side_effect=[before,after]),patch.object(command,'read_private',return_value=b'{}'):
            with self.assertRaisesRegex(Refusal,'read_device$'):command._read_evidence(Path('/invented/evidence'))

    def test_selection_component_labels_preserve_exact_equality(self):
        identity=(1,2,3,4);selected=command.SelectedEvidence('/invented/evidence',b'{}',identity,command._EVIDENCE_READER)
        for i,label in enumerate(('device','inode','size','mtime')):
            changed=list(identity);changed[i]+=1
            with patch.object(command,'_read_evidence',return_value=(b'{}',tuple(changed))) as reader:
                with self.subTest(label=label),self.assertRaisesRegex(Refusal,'^supervised_evidence_changed_selected_'+label+'$'):selected.revalidate()
                reader.assert_called_once()
        with patch.object(command,'_read_evidence',return_value=(b'{"invented":true}',identity)):
            with self.assertRaisesRegex(Refusal,'selected_bytes$'):selected.revalidate()
        for malformed in ((1,2),[1,2,3,4],(1,2,3,4,5)):
            selected.identity=malformed
            with patch.object(command,'_read_evidence',return_value=(b'{}',identity)):
                with self.assertRaises(Refusal):selected.revalidate()

    def test_existing_diagnostic_journal_retains_underlying_guard_without_releasing_debit(self):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart');f.setUp();self.addCleanup(f.doCleanups)
        original=auth._Session.check
        def checked(session,*args):
            if session.issued:raise Refusal('supervised_evidence_changed_read_ctime')
            return original(session,*args)
        with diagnostics.DiagnosticTests().inputs(),diagnostics.wire_fixture('completed'),patch.object(auth._Session,'check',checked):
            with self.assertRaisesRegex(Refusal,'supervised_evidence_changed_read_ctime'):command.run(f.state,f.selected,1)
        last=History(f.state).read()[-1]
        self.assertEqual((last['reason'],last['category']),('supervised_evidence_changed_read_ctime','evidence_changed'))
        self.assertEqual([e['reserved_usd'] for e in History(f.state/'credit').read()],[[3,100]])
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(Refusal):command.run(f.state,f.selected,1)
        prompt.assert_not_called()

    def test_installed_command_reports_injected_class_without_raw_exception(self):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart');f.setUp();self.addCleanup(f.doCleanups)
        hook="""
from ai_movie_investigator import supervised_authorization as auth
original_check=auth._Session.check
def check(session,*args):
    if session.issued:raise OSError('PRIVATE_FIXTURE_SENTINEL /private/path')
    return original_check(session,*args)
auth._Session.check=check
"""
        executable.SupervisedExecutableTests().execute_fixture(f,1,hook_extension=hook,
            category='send_or_response_refused',expected_reason='supervised_authorization_io_error',
            expected_phase='wire_authorization',expect_boundary=False)
