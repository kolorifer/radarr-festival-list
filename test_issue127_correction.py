import json
import os
import sqlite3
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from ai_movie_investigator import pilot_fixture
from ai_movie_investigator.contracts import Refusal, decode, encoded
from ai_movie_investigator.parent_pilot import run_pilot
from ai_movie_investigator.pilot_account import FixtureIssuer
from ai_movie_investigator.responses_http import HTTPResult
from ai_movie_investigator.weekly_ledger import ExistingWeeklyLedger, PROFILE


class CorrectedAdmissionDisclosure(unittest.TestCase):
    def make(self, root, *, reason=None, minutes=91):
        original = pilot_fixture.synthetic_case
        def selected(n):
            raw, binding, evidence = original(n)
            if reason:
                raw['data']['outcome'].update(status='unresolved', reason=reason)
            if minutes != 91:
                next(row for row in evidence if row['kind'] == 'source')['text'] = 'Synthetic 124 minute alternate edition.'
            return raw, binding, evidence
        source = Path(pilot_fixture.__file__).read_text()
        assert source.count('Duration : 91 min') == 2
        namespace = dict(vars(pilot_fixture), synthetic_case=selected)
        exec(compile(source[source.index('def make_fixture('):].replace('Duration : 91 min', f'Duration : {minutes} min'), '<invented-fixture>', 'exec'), namespace)
        return namespace['make_fixture'](Path(root).resolve())

    def run_case(self, parent):
        return run_pilot(parent, command=parent.owner_event['command'], enabled=True)

    def test_original_exhausted_and_deferred_routes_never_claim_or_send(self):
        for reason in ('retry_exhausted', 'metadata_rate_limited'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp, reason=reason)
                with self.assertRaisesRegex(Refusal, 'pilot_not_unresolved_eligible'):
                    self.run_case(parent)
                self.assertEqual(parent.control.read(), [])
                self.assertFalse(parent.catalogue.requests or parent.counter.requests or parent.model.requests)

    def test_runtime_and_edition_are_withheld_and_cannot_be_forged(self):
        for minutes in (91, 124):
            with self.subTest(minutes=minutes), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp, minutes=minutes)
                self.run_case(parent)
                body = decode(parent.counter.requests[0]['body'], 65536)
                message = json.loads(body['input'][0]['content'][0]['text'])
                source = next(row for row in message['evidence'] if row['kind'] == 'source')
                self.assertNotIn('runtime', source['claims'])
                self.assertNotIn('edition', source['claims'])
                self.assertNotIn('Duration :', encoded(body).decode())
                self.assertEqual(len(parent.model.requests), 1)
                self.assertEqual(sum(e['type'] == 'pilot_model_settled' for e in parent.control.read()), 1)
        for claim in ('runtime', 'edition'):
            with self.subTest(forged=claim), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                body = decode(parent.model.response.body, 32768)
                reply = decode(body['output'][-1]['content'][0]['text'])
                source = reply['result']['citations'][1]
                source['claim'] = claim
                body['output'][-1]['content'][0]['text'] = encoded(reply).decode()
                parent.model.response = HTTPResult(200, encoded(body), parent.model.response.request_id)
                self.run_case(parent)
                result = [e for e in parent.history.read() if e['type'] == 'result'][-1]
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['reason'], 'pilot_citation_claim_not_disclosed')

    def test_fresh_post_effect_ids_are_bound_and_settled_once(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make(temp)
            selection = decode(parent.blob, 131072)
            self.assertNotIn('count_receipt', selection)
            self.assertNotIn('model_receipt', selection)
            parent.counter.receipt['request_id'] = 'fresh_count_after_selection'
            response = decode(parent.model.response.body, 32768)
            response['id'] = 'resp_fresh_after_selection'
            parent.model.response = HTTPResult(200, encoded(response), 'req_fresh_after_selection')
            parent.model.receipt.update(request_id='req_fresh_after_selection', response_id='resp_fresh_after_selection')
            self.run_case(parent)
            events = parent.control.read()
            count = next(e for e in events if e['type'] == 'pilot_count_settled')['receipt']
            model = next(e for e in events if e['type'] == 'pilot_model_settled')
            self.assertEqual(count['request_id'], 'fresh_count_after_selection')
            self.assertEqual(model['receipt']['request_id'], 'req_fresh_after_selection')
            self.assertEqual(model['receipt']['response_id'], 'resp_fresh_after_selection')
            reserved = next(e for e in events if e['type'] == 'pilot_model_reserved')
            sent = next(e for e in events if e['type'] == 'pilot_model_sent')
            self.assertEqual(model['receipt']['local_request_id'], model['accounting']['local_request_id'])
            self.assertEqual(reserved['local_request_id'], sent['local_request_id'])
            self.assertEqual(sent['local_request_id'], model['receipt']['local_request_id'])
            self.assertNotEqual(count['local_request_id'], model['receipt']['local_request_id'])
            with self.assertRaises(Refusal):
                self.run_case(parent)
            self.assertEqual(len(parent.counter.requests), 1)
            self.assertEqual(len(parent.model.requests), 1)
            self.assertEqual(sum(e['type'] == 'pilot_model_settled' for e in parent.control.read()), 1)

    def test_bad_post_effect_receipts_keep_holds_without_replay(self):
        mutations = {'known': False, 'project': 'foreign', 'run': 'foreign',
                     'request_hash': 'f' * 64, 'local_request_id': 'foreign',
                     'operation': 'foreign', 'issuer': 'foreign', 'extra_conflicting_field': 'foreign'}
        for phase in ('count', 'generation'):
            for field, value in mutations.items():
                with self.subTest(phase=phase, field=field), tempfile.TemporaryDirectory() as temp:
                    parent = self.make(temp)
                    issuer = parent.counter.issuer if phase == 'count' else parent.model.issuer
                    issue = issuer._issue
                    def bad(receipt):
                        receipt = dict(receipt, **{field: value})
                        return issue(receipt)
                    with patch.object(issuer, '_issue', side_effect=bad):
                        try:
                            self.run_case(parent)
                        except Refusal:
                            pass
                    events = parent.control.read()
                    self.assertTrue(any(e['type'] == 'pilot_count_reserved' for e in events))
                    if phase == 'count':
                        self.assertFalse(any(e['type'] == 'pilot_count_settled' for e in events))
                        self.assertFalse(parent.model.requests)
                    else:
                        self.assertTrue(any(e['type'] == 'pilot_model_sent' for e in events))
                        self.assertFalse(any(e['type'] == 'pilot_model_settled' for e in events))
                    with self.assertRaises(Refusal):
                        self.run_case(parent)
                    self.assertEqual(len(parent.counter.requests), 1)
                    self.assertLessEqual(len(parent.model.requests), 1)

    def test_distinct_site_receipt_must_match_http_response_ids(self):
        for field in ('request_id', 'response_id'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                parent.model.receipt[field] = 'foreign_' + field
                self.run_case(parent)
                self.assertTrue(any(e['type'] == 'pilot_model_sent' for e in parent.control.read()))
                self.assertFalse(any(e['type'] == 'pilot_model_settled' for e in parent.control.read()))
                self.assertEqual(len(parent.model.requests), 1)

    def test_count_and_generation_reject_noncanonical_altered_wire_bytes(self):
        for phase in ('count', 'generation'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                site = parent.counter if phase == 'count' else parent.model
                method = 'count' if phase == 'count' else 'post'
                original = getattr(site, method)
                def altered(body, *args, **kwargs):
                    return original(body + b'\n', *args, **kwargs)
                with patch.object(site, method, side_effect=altered):
                    try:
                        self.run_case(parent)
                    except Refusal:
                        pass
                self.assertEqual(site.requests, [])
                self.assertFalse(any(e['type'] == 'pilot_model_settled' for e in parent.control.read()))
                if phase == 'count':
                    self.assertFalse(any(e['type'] == 'pilot_count_settled' for e in parent.control.read()))
                with self.assertRaises(Refusal):
                    self.run_case(parent)

    def test_count_and_generation_reject_different_canonical_request(self):
        for phase in ('count', 'generation'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                site = parent.counter if phase == 'count' else parent.model
                method = 'count' if phase == 'count' else 'post'
                original = getattr(site, method)
                def altered(body, *args, **kwargs):
                    body = decode(body, 65536)
                    body['max_output_tokens'] = 1
                    return original(encoded(body), *args, **kwargs)
                with patch.object(site, method, side_effect=altered):
                    try:
                        self.run_case(parent)
                    except Refusal:
                        pass
                self.assertEqual(site.requests, [])
                self.assertFalse(any(e['type'] == 'pilot_model_settled' for e in parent.control.read()))
                if phase == 'count':
                    self.assertFalse(any(e['type'] == 'pilot_count_settled' for e in parent.control.read()))

    def test_changed_returned_response_cannot_settle_the_signed_body(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make(temp)
            original = parent.model.post
            def altered(*args, **kwargs):
                result = original(*args, **kwargs)
                body = decode(result.body, 32768)
                reply = decode(body['output'][-1]['content'][0]['text'])
                reply['result']['rationale'] = 'A different synthetic response.'
                body['output'][-1]['content'][0]['text'] = encoded(reply).decode()
                return HTTPResult(result.status, encoded(body), result.request_id)
            with patch.object(parent.model, 'post', side_effect=altered):
                self.run_case(parent)
            self.assertFalse(any(e['type'] == 'pilot_model_settled' for e in parent.control.read()))
            self.assertEqual(len(parent.model.requests), 1)

    def test_valid_long_response_and_request_ids_settle(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make(temp)
            request_id, reply_id = 'req_' + 'a' * 100, 'resp_' + 'b' * 100
            count_id = 'count_' + 'c' * 100
            parent.counter.receipt['request_id'] = count_id
            body = decode(parent.model.response.body, 32768)
            body['id'] = reply_id
            parent.model.response = HTTPResult(200, encoded(body), request_id)
            parent.model.receipt.update(request_id=request_id, response_id=reply_id)
            self.run_case(parent)
            settled = [e for e in parent.control.read() if e['type'] == 'pilot_model_settled']
            self.assertEqual(len(settled), 1)
            self.assertEqual(settled[0]['receipt']['response_id'], reply_id)
            counted = [e for e in parent.control.read() if e['type'] == 'pilot_count_settled']
            self.assertEqual(counted[0]['receipt']['request_id'], count_id)

    def test_changed_current_native_ledger_is_rejected_before_claim(self):
        for mode in ('not_queued', 'material'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                ledger = ExistingWeeklyLedger(parent.ledger_directory, clock=parent.clock, profile=PROFILE)
                with ledger.tx() as conn:
                    if mode == 'not_queued':
                        conn.execute('update jobs set status="awaiting_evidence"')
                    else:
                        row = conn.execute('select material from evidence').fetchone()
                        material = json.loads(row['material'])
                        material['facts']['year'] = 2025
                        conn.execute('update evidence set material=?', (encoded(material).decode(),))
                with self.assertRaisesRegex(Refusal, 'pilot_ledger_material_unbound'):
                    self.run_case(parent)
                self.assertEqual(parent.control.read(), [])
                self.assertFalse(any(e['type'] == 'research_started' for e in parent.history.read()))
                self.assertFalse(parent.catalogue.requests or parent.counter.requests or parent.model.requests)

    def test_busy_ledger_refuses_without_a_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make(temp)
            ledger_file = parent.ledger_directory / ExistingWeeklyLedger.filename
            conn = sqlite3.connect(str(ledger_file), isolation_level=None)
            try:
                conn.execute('BEGIN IMMEDIATE')
                with self.assertRaisesRegex(Refusal, 'pilot_preclaim_ledger_refused'):
                    self.run_case(parent)
            finally:
                conn.rollback()
                conn.close()
            self.assertEqual(parent.control.read(), [])
            self.assertFalse(parent.catalogue.requests or parent.counter.requests or parent.model.requests)

    def test_owner_and_expiry_are_rechecked_after_ledger_wait(self):
        for mode in ('owner', 'expiry'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                original = ExistingWeeklyLedger.tx
                changed = []
                @contextmanager
                def alter(store):
                    with original(store) as conn:
                        if not changed:
                            changed.append(True)
                            if mode == 'owner':
                                parent.owner_event['edited'] = True
                            else:
                                parent.clock.advance(300)
                        yield conn
                with patch.object(ExistingWeeklyLedger, 'tx', alter):
                    with self.assertRaises(Refusal):
                        self.run_case(parent)
                self.assertEqual(parent.control.read(), [])
                self.assertFalse(parent.catalogue.requests or parent.counter.requests or parent.model.requests)

    @unittest.skipUnless(hasattr(os, 'fork'), 'local POSIX history lock')
    def test_history_writer_cannot_supersede_during_preclaim(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make(temp)
            marker = Path(temp) / 'competing-writer-finished'
            original = ExistingWeeklyLedger.tx
            child = []
            launched = []
            @contextmanager
            def observed(store):
                if not launched:
                    launched.append(True)
                    read_fd, write_fd = os.pipe()
                    pid = os.fork()
                    if pid == 0:
                        try:
                            os.dup2(write_fd, 1)
                            os.closerange(3, 256)
                            os.write(1, b'x')
                            with parent.history.transaction(write=True) as (_, append):
                                append(dict(type='synthetic_concurrent_writer', at=parent.clock()))
                                marker.write_text('completed')
                        except BaseException:
                            os._exit(4)
                        os._exit(0)
                    child.append(pid)
                    os.close(write_fd)
                    self.assertEqual(os.read(read_fd, 1), b'x')
                    os.close(read_fd)
                    time.sleep(.15)
                    self.assertFalse(marker.exists(), 'history writer passed the preclaim lock')
                with original(store) as conn:
                    yield conn
            try:
                with patch.object(ExistingWeeklyLedger, 'tx', observed):
                    self.run_case(parent)
            finally:
                if child:
                    _, result = os.waitpid(child[0], 0)
                    self.assertEqual(os.waitstatus_to_exitcode(result), 0)
            self.assertTrue(marker.exists())
            self.assertEqual(sum(e['type'] == 'pilot_claim' for e in parent.control.read()), 1)

    def test_same_name_issuer_substitution_is_refused_before_and_during_effects(self):
        for phase in ('before_count', 'during_count', 'before_model', 'during_model'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                parent = self.make(temp)
                site = parent.counter if 'count' in phase else parent.model
                replacement = FixtureIssuer(site.issuer.identity)
                if phase.startswith('before'):
                    site.issuer = replacement
                    with self.assertRaises(Refusal):
                        self.run_case(parent)
                    self.assertFalse(parent.control.read())
                    continue
                method = 'count' if 'count' in phase else 'post'
                original = getattr(site, method)
                def swap(*args, **kwargs):
                    value = original(*args, **kwargs)
                    site.issuer = replacement
                    return value
                with patch.object(site, method, side_effect=swap):
                    try:
                        self.run_case(parent)
                    except Refusal:
                        pass
                events = parent.control.read()
                target = 'pilot_count_settled' if 'count' in phase else 'pilot_model_settled'
                self.assertFalse(any(event['type'] == target for event in events))

    def test_foreign_enrolled_site_cannot_rename_itself_to_selected_issuer(self):
        for field in ('counter', 'model'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
                parent, foreign = self.make(first), self.make(second)
                selected_site = getattr(parent, field)
                foreign_site = getattr(foreign, field)
                foreign_site.issuer.identity = selected_site.issuer.identity
                setattr(parent, field, foreign_site)
                with self.assertRaisesRegex(Refusal, 'pilot_external_issuer_unknown'):
                    self.run_case(parent)
                self.assertEqual(parent.control.read(), [])
                self.assertFalse(parent.catalogue.requests or parent.counter.requests or parent.model.requests)

if __name__ == '__main__':
    unittest.main()
