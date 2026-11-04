import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_movie_investigator.contracts import Refusal, decode, digest, encoded
from ai_movie_investigator.controller import INSTRUCTIONS, output_schema
from ai_movie_investigator.disclosure import aliases, project, row_view
from ai_movie_investigator.history import History
from ai_movie_investigator.responses_protocol import MODEL, OUTPUT_TOKENS
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.responses_transport import ResponsesTransport


class Parent:
    def __init__(self, expected, case, context):
        self.expected, self.case, self.context = expected, case, context

    def authorize(self, selected, body):
        assert body == self.expected
        assert selected == dict(run='fixture', case=self.case, request_sha256=digest(decode(body)), local_context_sha256=self.context)
        return dict(selection=selected, project='proj_recording', model=MODEL, expires_at=200,
                    input_limit=2000, output_limit=OUTPUT_TOKENS, maximum_debit=[1, 2], currency='TEST-USD')

    def validate(self, permit, body):
        return body == self.expected

    def validate_receipt(self, permit, result, accounting):
        return result.request_id == 'req_SIMULATED_1' and accounting['response_id'] == 'resp_SIMULATED_1'


class BoundIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.history = History(Path(self.tmp.name).resolve(), clock=lambda: 100)
        case = dict(source='fixture', case_id='outcome-'+'a'*64, version='b'*64, occurrence=None)
        row = dict(id='source', kind='source', candidate=None, claims=[], text='LOCAL RAW TEXT',
                   observed_at=90, expires_at=None)
        facts = dict(title='Example', year=2000, imdb=None, tmdb=None,
                     outcome=dict(asserted_imdb=None, asserted_tmdb=None, reason='unknown'))
        self.prompt = dict(protocol='retained-investigator-v1', binding=case, binding_hash=digest(case),
                           facts=facts, reconciliation=dict(conflicting_ids=False, known_identity=None),
                           evidence_index=[], query_results=[dict(rows=[row])], instruction=INSTRUCTIONS)
        self.disclosure = dict(facts=dict(title='Example', year=2000, imdb=None, tmdb=None,
                               asserted_imdb=None, asserted_tmdb=None, contradiction='unknown'),
                               rows={'source': dict(view=row_view(row), original_hash=digest(row))})
        self.body = project(self.prompt, run='fixture', disclosure=self.disclosure)
        self.parent = Parent(self.body, case, digest(dict(prompt=self.prompt, disclosure=self.disclosure)))
        self.transport = ResponsesTransport(enabled=True, clock=lambda: 100)

    def complete(self):
        return self.transport.complete_disclosed(encoded(self.prompt), schema=output_schema(),
                  history=self.history, run='fixture', disclosure=self.disclosure, parent=self.parent)

    def test_connected_path_only_replaces_http_io(self):
        def record(body, **kwargs):
            self.assertEqual(body, self.body)
            self.assertNotIn(b'LOCAL RAW TEXT', body)
            self.assertEqual(kwargs['project'], 'proj_recording')
            self.assertEqual(kwargs['authorization'], self.history.read()[0]['permit'])
            self.assertEqual([e['type'] for e in self.history.read()],
                             ['bound_send_reserved', 'bound_send_attempted'])
            return simulated_response(dict(binding_hash=aliases('fixture'), kind='final', lookups=[], result=dict(
                status='unresolved', candidate=None, alternatives=[], citations=[], rationale='Fixture',
                uncertainty='Unknown', next_action='human_review')), 1)
        with patch('socket.socket', side_effect=AssertionError('network')), patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post', side_effect=record) as sink:
            reply = decode(self.complete())
        self.assertEqual(sink.call_count, 1)
        self.assertEqual(reply['binding_hash'], self.prompt['binding_hash'])
        self.assertEqual(reply['result']['status'], 'unresolved')
        self.assertEqual(self.history.read()[-1]['type'], 'bound_send_receipt')
        with self.assertRaisesRegex(Refusal, 'binding_attempt_consumed'):
            self.complete()

    def test_unpatched_boundary_still_closed(self):
        with patch('socket.socket', side_effect=AssertionError('network')):
            with self.assertRaisesRegex(Refusal, 'responses_real_authorization_unimplemented'):
                self.complete()
        self.assertEqual(len(self.history.read()), 2)

    def test_changed_binding_refused_before_reservation(self):
        self.prompt['binding']['version'] = 'c'*64
        with self.assertRaisesRegex(Refusal, 'responses_selected_input_changed'):
            self.complete()
        self.assertEqual(self.history.read(), [])

    def test_disabled_default_prevents_reservation(self):
        self.transport = ResponsesTransport()
        with self.assertRaisesRegex(Refusal, 'model_transport_disabled'):
            self.complete()
        self.assertEqual(self.history.read(), [])

    def test_local_decision_change_cannot_reuse_parent_selection(self):
        self.prompt['reconciliation']['known_identity'] = dict(imdb='tt12345678', tmdb=123)
        self.assertEqual(project(self.prompt, run='fixture', disclosure=self.disclosure), self.body)
        with self.assertRaises(AssertionError):
            self.complete()
        self.assertEqual(self.history.read(), [])

    def test_unsupported_candidate_refused_after_response_without_retry(self):
        response = simulated_response(dict(binding_hash=aliases('fixture'), kind='final', lookups=[], result=dict(
            status='supported_candidate', candidate=dict(imdb='tt12345678', tmdb=123), alternatives=[],
            citations=[], rationale='Unproven', uncertainty='Unknown', next_action='human_review')), 1)
        with patch('socket.socket', side_effect=AssertionError('network')), patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post', return_value=response):
            with self.assertRaisesRegex(Refusal, 'candidate_evidence_missing'):
                self.complete()
        self.assertEqual(self.history.read()[-1]['type'], 'bound_send_receipt')
        with self.assertRaisesRegex(Refusal, 'binding_attempt_consumed'):
            self.complete()
