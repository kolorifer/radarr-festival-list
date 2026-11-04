import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator.bound_send import _send_bound, send
from ai_movie_investigator.contracts import encoded, decode, digest, Refusal
from ai_movie_investigator.history import History
from ai_movie_investigator.responses_protocol import MODEL, OUTPUT_TOKENS
from ai_movie_investigator.responses_replay import simulated_response


class Parent:
    def authorize(self, selected, body):
        return dict(selection=selected, project='proj_recording', model=MODEL,
                    expires_at=200, input_limit=2000, output_limit=OUTPUT_TOKENS,
                    maximum_debit=[1, 2], currency='TEST-USD')
    def validate(self, permit, body):
        return True
    def validate_receipt(self, permit, result, accounting):
        return True


class Sink:
    def __init__(self):
        self.calls = []
    def post(self, body, **kwargs):
        self.calls.append((body, kwargs))
        reply = dict(binding_hash='fixture', kind='final', lookups=[], result=dict(
            status='unresolved', candidate=None, alternatives=[], citations=[],
            rationale='Fixture', uncertainty='Unknown', next_action='human_review'))
        return simulated_response(reply, 1)


class BoundSendTest(unittest.TestCase):
    def test_bound_receipt_and_restart_refusal(self):
        with tempfile.TemporaryDirectory() as d, patch('socket.socket', side_effect=AssertionError('network')):
            path = Path(d).resolve()
            h = History(path, clock=lambda: 100)
            sink = Sink()
            body = encoded(dict(model=MODEL, max_output_tokens=OUTPUT_TOKENS))
            args = dict(case=dict(source='fixture', case_id='outcome-'+'a'*64, version='b'*64, occurrence=None),
                        run='fixture', parent=Parent(), credential=None)
            with patch('ai_movie_investigator.bound_send.FixedResponsesHTTP.post', side_effect=sink.post):
                _send_bound(h, body, **args)
            self.assertEqual(sink.calls[0][0], body)
            self.assertIsNone(sink.calls[0][1]['credential'])
            self.assertEqual(sink.calls[0][1]['project'], 'proj_recording')
            self.assertEqual(sink.calls[0][1]['authorization'], h.read()[0]['permit'])
            self.assertEqual(sink.calls[0][1]['authorization']['selection'], dict(run='fixture', case=args['case'], request_sha256=digest(decode(body))))
            self.assertEqual(sink.calls[0][1]['timeout'], 25)
            self.assertEqual([x['type'] for x in h.read()], ['bound_send_reserved','bound_send_attempted','bound_send_receipt'])
            with self.assertRaisesRegex(Refusal, 'binding_attempt_consumed'):
                _send_bound(History(path, clock=lambda: 100), body, **args)
            self.assertEqual(len(sink.calls), 1)

    def test_production_closed(self):
        with patch('socket.socket', side_effect=AssertionError('network')):
            with self.assertRaisesRegex(ValueError, 'responses_real_authorization_unimplemented'):
                send(enabled=True, parent=Parent(), http=Sink())

    def test_uncertain_attempt_burns_reservation_across_restart(self):
        with tempfile.TemporaryDirectory() as d, patch('socket.socket', side_effect=AssertionError('network')):
            path = Path(d).resolve()
            body = encoded(dict(model=MODEL, max_output_tokens=OUTPUT_TOKENS))
            args = dict(case=dict(source='fixture', case_id='outcome-'+'a'*64, version='b'*64, occurrence=None),
                        run='fixture', parent=Parent(), credential=None)
            with patch('ai_movie_investigator.bound_send.FixedResponsesHTTP.post', side_effect=TimeoutError):
                with self.assertRaises(TimeoutError):
                    _send_bound(History(path, clock=lambda: 100), body, **args)
            with self.assertRaisesRegex(Refusal, 'binding_attempt_consumed'):
                _send_bound(History(path, clock=lambda: 100), body, **args)
            self.assertEqual(len(History(path).read()), 2)

    def test_fake_parent_cannot_unlock_real_boundary(self):
        with tempfile.TemporaryDirectory() as d, patch('socket.socket', side_effect=AssertionError('network')):
            with self.assertRaisesRegex(Refusal, 'responses_real_authorization_unimplemented'):
                _send_bound(History(Path(d).resolve(), clock=lambda: 100),
                    encoded(dict(model=MODEL, max_output_tokens=OUTPUT_TOKENS)),
                    case=dict(source='fixture', case_id='outcome-'+'a'*64, version='b'*64, occurrence=None),
                    run='fixture', parent=Parent(), credential=None)

    def test_parent_refusal_and_receipt_refusal(self):
        for stage, expected in [('validate', 0), ('validate_receipt', 2)]:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as d:
                h = History(Path(d).resolve(), clock=lambda: 100)
                parent = Parent()
                setattr(parent, stage, lambda *args: False)
                sink = Sink()
                with patch('socket.socket', side_effect=AssertionError('network')), patch(
                        'ai_movie_investigator.bound_send.FixedResponsesHTTP.post', side_effect=sink.post):
                    with self.assertRaises(Refusal):
                        _send_bound(h, encoded(dict(model=MODEL, max_output_tokens=OUTPUT_TOKENS)),
                            case=dict(source='fixture', case_id='outcome-'+'a'*64, version='b'*64, occurrence=None),
                            run='fixture', parent=parent, credential=None)
                self.assertEqual(len(h.read()), expected)

    def test_excess_usage_never_creates_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            h = History(Path(d).resolve(), clock=lambda: 100)
            parent = Parent()
            original = parent.authorize
            parent.authorize = lambda *args: dict(original(*args), input_limit=1)
            with patch('socket.socket', side_effect=AssertionError('network')), patch(
                    'ai_movie_investigator.bound_send.FixedResponsesHTTP.post', side_effect=Sink().post):
                with self.assertRaisesRegex(Refusal, 'binding_usage_unknown'):
                    _send_bound(h, encoded(dict(model=MODEL, max_output_tokens=OUTPUT_TOKENS)),
                        case=dict(source='fixture', case_id='outcome-'+'a'*64, version='b'*64, occurrence=None),
                        run='fixture', parent=parent, credential=None)
            self.assertEqual(len(h.read()), 2)
