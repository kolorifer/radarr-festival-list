"""Real private History/Digest ledgers; only the final sender is replaced."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError
import sqlite3

from ai_movie_investigator.contracts import Refusal, captured_outcome, digest, encoded
from ai_movie_investigator.history import History
from ai_movie_investigator.new_case import prepare, complete
from ai_movie_investigator.draft_delivery import deliver, FOOTER
from ai_movie_investigator.replay import synthetic_case, NOW
from identity_telegram_digest import Digest


class DraftDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.now=NOW
        (self.root/'history').mkdir(mode=0o700)
        self.history=History(self.root/'history',clock=lambda:self.now)
        self.outbox=Digest(self.root/'outbox');self.send=Mock(return_value=200)
        self.packet,self.report,self.selection=self.review(146)

    def review(self,n):
        raw,binding,evidence=synthetic_case(n)
        packet=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=binding,evidence=evidence,decisions=[])
        r=prepare(self.history,packet,binding)
        answer=dict(binding_hash=r['binding_hash'],kind='final',lookups=[],result=dict(status='unresolved',candidate=None,
            alternatives=[],citations=[],rationale='Synthetic fixture has no verified current film identity.',
            uncertainty='Source and edition remain unverified.',next_action='human_review'))
        report=complete(self.history,digest(r),answer,{'mode':'simulation','chat_reference':'Synthetic delivery fixture only'})
        return packet,report,dict(job=report['job'],binding=binding,report_hash=digest(report),draft_hash=digest(report['draft']))

    def run_delivery(self,**kw):
        return deliver(self.history,self.outbox,self.selection,self.send,enabled=True,**kw)

    def restart(self):
        self.history=History(self.root/'history',clock=lambda:self.now)
        self.outbox=Digest(self.root/'outbox')

    def test_disabled_default_does_not_reserve_or_send(self):
        before=self.history.read()
        with self.assertRaisesRegex(Refusal,'investigator_delivery_disabled'):
            deliver(self.history,self.outbox,self.selection,self.send)
        self.assertEqual(before,self.history.read());self.assertEqual(self.outbox.summary(),{});self.send.assert_not_called()

    def test_exact_draft_acknowledgement_and_restart_no_duplicate(self):
        result=self.run_delivery();self.assertTrue(result['attempted'])
        sent=self.send.call_args.args[0]
        self.assertEqual(sent,self.report['draft']['text'][:-len(FOOTER)]+'Review proposal only; no identity or download approval.')
        self.assertIn('SIMULATED assessment; plumbing test only.',sent)
        self.assertNotIn('DRAFT ONLY',sent)
        receipt=result['receipt'];self.assertEqual(receipt['state'],'sent')
        self.assertTrue(receipt['transport_acknowledged']);self.assertFalse(receipt['recipient_ingestion_verified'])
        self.assertEqual(receipt['binding'],self.packet['binding'])
        self.assertEqual(receipt['draft_hash'],digest(self.report['draft']))
        self.restart();second=self.run_delivery()
        self.assertFalse(second['attempted']);self.assertEqual(second['receipt'],receipt);self.send.assert_called_once()
        self.assertEqual(sum(e['type']=='new_case_delivery_receipt' for e in self.history.read()),1)

    def test_each_exact_binding_mismatch_fails_before_sender(self):
        for field in ('job','report_hash','draft_hash'):
            old=self.selection[field];self.selection[field]='0'*64
            with self.assertRaises(Refusal):self.run_delivery()
            self.selection[field]=old
        self.selection['binding']['occurrence']['delivery_id']+=1
        with self.assertRaisesRegex(Refusal,'notification_selection_changed'):self.run_delivery()
        self.send.assert_not_called();self.assertEqual(self.outbox.summary(),{})

    def test_uncertain_timeout_survives_restart_without_replay(self):
        self.send.side_effect=TimeoutError('synthetic uncertain transport')
        first=self.run_delivery();self.assertEqual(first['receipt']['state'],'uncertain')
        self.assertFalse(first['receipt']['transport_acknowledged'])
        self.restart();self.now+=10
        self.assertFalse(self.run_delivery()['attempted']);self.send.assert_called_once()

    def test_crash_inside_sender_burns_opportunity(self):
        self.send.side_effect=KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):self.run_delivery()
        self.restart();self.send.side_effect=None
        result=self.run_delivery();self.assertFalse(result['attempted'])
        self.assertEqual(result['receipt']['state'],'uncertain');self.send.assert_called_once()

    def test_known_storage_failure_before_send_can_resume_safely(self):
        with self.outbox.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):self.run_delivery()
        self.send.assert_not_called();self.assertEqual(self.outbox.summary(),{})
        self.restart();self.assertTrue(self.run_delivery()['attempted']);self.send.assert_called_once()

    def test_explicit_429_only_retries_after_existing_delay(self):
        self.send.side_effect=HTTPError('fixture',429,'limited',{},io.BytesIO(b'{"parameters":{"retry_after":7200}}'))
        self.assertEqual(self.run_delivery()['receipt']['state'],'retry')
        self.restart();self.now+=3601
        self.assertFalse(self.run_delivery()['attempted'])
        self.send.side_effect=None;self.now+=3600
        self.assertEqual(self.run_delivery()['receipt']['state'],'sent');self.assertEqual(self.send.call_count,2)

    def test_non_200_does_not_count_as_acknowledgement(self):
        self.send.return_value=503
        self.assertEqual(self.run_delivery()['receipt']['state'],'uncertain')
        self.restart();self.send.return_value=200
        self.assertFalse(self.run_delivery()['attempted']);self.send.assert_called_once()

    def test_outbox_switch_cannot_refund_an_uncertain_attempt(self):
        self.send.side_effect=TimeoutError
        self.run_delivery();self.outbox=Digest(self.root/'replacement')
        with self.assertRaisesRegex(Refusal,'notification_outbox_or_selection_changed'):self.run_delivery()
        self.assertEqual(self.outbox.summary(),{});self.send.assert_called_once()

    def test_superseded_case_is_not_sent(self):
        p=copy.deepcopy(self.packet);p['evidence'][0]['text']='Changed evidence.';self.history.intake(p)
        with self.assertRaisesRegex(Refusal,'selected_case_superseded'):self.run_delivery()
        self.send.assert_not_called()

    def test_freshness_change_cannot_silently_rewrite_selected_draft(self):
        self.now+=86401
        with self.assertRaisesRegex(Refusal,'notification_draft_stale_or_changed'):self.run_delivery()
        self.send.assert_not_called()

    def test_distinct_occurrence_uses_distinct_delivery_binding(self):
        first=self.run_delivery()
        self.packet,self.report,self.selection=self.review(147)
        second=self.run_delivery()
        self.assertNotEqual(first['receipt']['delivery_key'],second['receipt']['delivery_key'])
        self.assertEqual(self.send.call_count,2)

    def test_replaced_and_restored_outbox_cannot_repeat_send(self):
        # Replace/restore inside the sole fake sender, not a mocked ledger.
        # This reproduces a successful external effect whose ledger then vanishes.
        import os
        original=self.outbox.path
        displaced=original.with_name('displaced.sqlite3')
        backup=self.root/'empty.sqlite3'
        with sqlite3.connect(backup) as c:
            c.execute('CREATE TABLE delivery (case_id TEXT, version TEXT, state TEXT, due REAL, PRIMARY KEY(case_id,version))')
        c.close()
        backup.chmod(0o600)
        def swap_after_effect(body):
            os.rename(original,displaced)
            os.rename(backup,original)
            return 200
        self.send.side_effect=swap_after_effect
        with self.assertRaisesRegex(Refusal,'notification_outbox_changed'):self.run_delivery()
        # Restore originally pinned inode but remove the reserved delivery row,
        # equivalent to tick having used a transient replacement during the send.
        original.unlink();os.rename(displaced,original)
        with self.outbox.connect() as c:c.execute('DELETE FROM delivery')
        self.restart();self.send.side_effect=None
        with self.assertRaisesRegex(Refusal,'notification_uncertain_ledger_missing'):self.run_delivery()
        self.send.assert_called_once()

    def test_retry_state_cannot_refund_a_non_rejected_send(self):
        self.send.side_effect=TimeoutError
        self.run_delivery()
        with self.outbox.connect() as c:c.execute("UPDATE delivery SET state='retry',due=0")
        self.restart();self.send.side_effect=None
        self.assertFalse(self.run_delivery()['attempted']);self.send.assert_called_once()

    def test_preexisting_ledger_success_is_not_an_acknowledgement(self):
        # A provable pre-send storage failure retains selection but no start.
        with self.outbox.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):self.run_delivery()
        chosen=next(e['chosen'] for e in self.history.read() if e['type']=='new_case_delivery_selected')
        key=digest(dict(purpose='investigator-draft-delivery-v1',**chosen))
        with self.outbox.connect() as c:
            c.execute('INSERT INTO delivery VALUES (?,?,?,?)',(self.packet['binding']['case_id'],key,'sent',self.now))
        with self.assertRaisesRegex(Refusal,'notification_unbound_delivery_state'):self.run_delivery()
        self.send.assert_not_called()
        self.assertFalse(any(e['type']=='new_case_delivery_receipt' for e in self.history.read()))

    def test_ledger_success_without_returned_200_is_not_acknowledgement(self):
        self.send.side_effect=TimeoutError;self.run_delivery()
        with self.outbox.connect() as c:c.execute("UPDATE delivery SET state='sent'")
        self.restart();self.send.side_effect=None
        with self.assertRaisesRegex(Refusal,'notification_transport_proof_missing'):self.run_delivery()
        self.send.assert_called_once()

    def test_changed_retry_due_cannot_shorten_actual_429_delay(self):
        self.send.side_effect=HTTPError('fixture',429,'limited',{},io.BytesIO(b'{"parameters":{"retry_after":7200}}'))
        original=self.outbox.tick
        def corrupted_readback(*args,**kwargs):
            result=original(*args,**kwargs)
            with self.outbox.connect() as c:c.execute('UPDATE delivery SET due=0')
            return result
        # Fault injection after real parsing/ledger update; final sender is fake.
        self.outbox.tick=corrupted_readback
        with self.assertRaisesRegex(Refusal,'notification_transport_proof_missing'):self.run_delivery()
        rejected=next(e for e in self.history.read() if e['type']=='new_case_delivery_rejected_429')
        self.assertEqual(rejected['due'],NOW+7200)
        self.restart();self.now+=1;self.send.side_effect=None
        self.assertFalse(self.run_delivery()['attempted']);self.send.assert_called_once()
