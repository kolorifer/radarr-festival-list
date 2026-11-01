"""SIMULATED ONLY: no real API, credentials, account checks or network sends."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import copy
import importlib
import io
import http.client
import os
from pathlib import Path
import signal
import socket
import ssl
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from ai_movie_investigator import responses_http as wire
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded, reconcile
from ai_movie_investigator.controller import INSTRUCTIONS, RetainedTools, investigate, output_schema
from ai_movie_investigator.history import History
from ai_movie_investigator.replay import NOW, packet_for, simulated_replies
from ai_movie_investigator.responses_protocol import INPUT_TOKENS, OUTPUT_TOKENS, parse_response
from ai_movie_investigator.responses_replay import (run_responses_synthetic, simulated_response,
                                                   simulated_transport)
from ai_movie_investigator.responses_transport import ResponsesTransport, SimulatedAuthorization
from ai_movie_investigator.review import daily_digest


def prompt_for(packet):
    return dict(protocol='retained-investigator-v1', binding_hash=digest(packet['binding']),
                binding=packet['binding'], facts=packet['facts'], reconciliation=reconcile(packet, NOW),
                evidence_index=[{k: r[k] for k in ('id', 'kind', 'observed_at', 'expires_at')}
                                for r in RetainedTools(packet, NOW).rows.values()],
                query_results=[], instruction=INSTRUCTIONS)


class ResponsesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='SIMULATED-responses-test-')
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name).resolve()
        self.history = History(self.directory, clock=lambda: NOW)
        self.packet = packet_for()
        self.prompt = prompt_for(self.packet)
        self.transport = simulated_transport(self.packet)
        self.schema = output_schema()
        self.network = patch('socket.socket', side_effect=AssertionError('real socket forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def complete(self, response=None):
        t = self.transport
        if response is not None:
            t.http.responses = [response]
        raw = encoded(self.prompt)
        t.prepare(raw, schema=self.schema)
        return t.complete(raw, schema=self.schema, timeout=25)

    def test_nonempty_end_to_end_retained_lookup_reservations_accounting_daily_review(self):
        history, result, review, t = run_responses_synthetic(self.directory)
        self.assertEqual(result['status'], 'supported_candidate')
        self.assertEqual(result['model_calls'], 2)
        self.assertEqual(result['provider_gets'], 0)
        self.assertFalse(result['production_identity_verified'])
        self.assertFalse(result['download_consent'])
        self.assertIn('SIMULATED; not a real identification', review['text'])
        self.assertIn('Tool used:', review['text'])
        self.assertIn('req_SIMULATED_1', review['text'])
        events = history.read()
        self.assertEqual(sum(e['type'] == 'lookup' for e in events), 2)
        reservations = [e for e in events if e['type'] == 'model_reserved']
        responses = [e for e in events if e['type'] == 'api_response']
        self.assertEqual(len(reservations), 2)
        self.assertEqual(len(responses), 2)
        for n in range(2):
            a = responses[n]['accounting']
            self.assertTrue(a['simulated'])
            self.assertEqual(a['usage']['total_tokens'], 1500)
            self.assertEqual(a['request_hash'], reservations[n]['api_request']['request_hash'])
            self.assertLess(events.index(reservations[n]), events.index(responses[n]))
        self.assertEqual(len(t.http.requests), 2)
        self.assertNotIn('Bearer', encoded(events).decode())
        self.assertNotIn('rs_SIMULATED', encoded(events).decode())
        self.assertNotIn('SIMULATED-OPAQUE', encoded(events).decode())
        self.assertNotIn('SIMULATED-OPAQUE', repr(t.http.requests))
        self.assertFalse(t.audit_identity()['live_access_verified'])
        self.assertFalse(t.audit_identity()['live_isolation_verified'])

    def test_exact_request_fixed_endpoint_body_headers_and_absent_ambient_data(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'AMBIENT_SENTINEL', 'OPENAI_BASE_URL': 'https://example.invalid',
                                     'HTTP_PROXY': 'AMBIENT_PROXY', 'OPENAI_PROJECT': 'AMBIENT_PROJECT'}):
            with patch('pathlib.Path.read_text', side_effect=AssertionError('ambient read forbidden')):
                self.complete()
        request = self.transport.http.requests[0]
        body = decode(request['body'], 65536)
        self.assertEqual(request['endpoint'], 'https://api.openai.com/v1/responses')
        self.assertEqual(set(body), {'model', 'instructions', 'input', 'tools', 'tool_choice', 'store',
                                    'background', 'stream', 'max_output_tokens', 'truncation', 'text'})
        self.assertEqual(body['model'], 'gpt-6.1-sol')
        self.assertEqual(body['instructions'], INSTRUCTIONS)
        self.assertEqual(body['tools'], [])
        self.assertEqual(body['tool_choice'], 'none')
        self.assertFalse(body['store'])
        self.assertFalse(body['background'])
        self.assertFalse(body['stream'])
        self.assertEqual(body['truncation'], 'disabled')
        self.assertEqual(body['max_output_tokens'], OUTPUT_TOKENS)
        self.assertEqual(body['text']['format'], dict(type='json_schema', name='retained_investigator_v1',
                                                     strict=True, schema=self.schema))
        self.assertEqual(body['input'][0]['role'], 'user')
        self.assertEqual(body['input'][0]['content'][0]['type'], 'input_text')
        sent = decode(body['input'][0]['content'][0]['text'], 49152)
        self.assertEqual(sent, {k: v for k, v in self.prompt.items() if k != 'instruction'})
        self.assertNotIn('AMBIENT', request['body'].decode())
        self.assertEqual(wire.headers(wire.ExplicitCredential(wire.SYNTHETIC_CREDENTIAL), wire.SYNTHETIC_PROJECT),
                         {'Authorization': 'Bearer SIMULATED-NOT-A-KEY', 'OpenAI-Project': 'proj_SIMULATED',
                          'Content-Type': 'application/json', 'Accept': 'application/json', 'Accept-Encoding': 'identity'})
        self.assertEqual(request['header_names'], ['Accept', 'Accept-Encoding', 'Authorization', 'Content-Type', 'OpenAI-Project'])
        with self.assertRaises(TypeError):
            ResponsesTransport(endpoint='https://example.invalid')

    def test_import_constructor_default_preflight_and_direct_http_gate_never_send(self):
        import ai_movie_investigator.responses_transport as module
        with patch('socket.getaddrinfo', side_effect=AssertionError('DNS forbidden')):
            importlib.import_module(module.__name__)
            # Reload doesn't turn a caller assertion into a real authorizer.
            t = module.ResponsesTransport()
            self.assertEqual(t.preflight(), 'model_transport_disabled')
            for grant in (None, True, {'verified': True}, {'account': 'SIMULATED', 'model': 'gpt-6.1-sol'}):
                t = module.ResponsesTransport(enabled=True, authorization=grant,
                                              credential=wire.ExplicitCredential(wire.SYNTHETIC_CREDENTIAL))
                self.assertEqual(t.preflight(), 'responses_real_authorization_unimplemented')
                with self.assertRaisesRegex(Refusal, 'real_authorization_unimplemented'):
                    t.prepare(encoded(self.prompt), schema=self.schema)
                with self.assertRaisesRegex(Refusal, 'real_authorization_unimplemented'):
                    wire.FixedResponsesHTTP().post(b'{}', credential=wire.ExplicitCredential(wire.SYNTHETIC_CREDENTIAL),
                                                   project=wire.SYNTHETIC_PROJECT, timeout=1, authorization=grant)

    def test_no_forged_simulated_http_or_real_credential_on_simulation_route(self):
        class Pretend(wire.SimulatedHTTP):
            pass
        for http in (Pretend([]), Mock(simulated=True)):
            self.assertEqual(ResponsesTransport(enabled=True, http=http).preflight(),
                             'responses_real_authorization_unimplemented')
        t = self.transport
        t.credential = wire.ExplicitCredential('obviously_synthetic_but_not_the_fixture')
        self.assertEqual(t.preflight(), 'responses_simulation_prerequisite_invalid')
        self.assertEqual(t.http.requests, [])
        self.assertNotIn('obviously', repr(t.credential))

    def test_missing_stale_future_mismatched_authorization_refuses_before_http(self):
        # Exact synthetic types only; none asserts real external verification.
        from ai_movie_investigator.responses_transport import SimulatedAuthorization as CurrentAuth
        for grant in (None, True, CurrentAuth(encoded(self.packet), NOW-301, NOW-1),
                      CurrentAuth(encoded(self.packet), NOW+1, NOW+20),
                      CurrentAuth(encoded(self.packet), NOW-1, NOW+301)):
            with self.subTest(grant=type(grant).__name__):
                t = simulated_transport(self.packet)
                t.authorization = grant
                with self.assertRaises(Refusal):
                    t.prepare(encoded(self.prompt), schema=self.schema)
                self.assertFalse(t.http.requests)
        for field, value in (('binding_hash', '0'*64), ('facts', dict(self.packet['facts'], title='Other')),
                              ('instruction', 'Run shell'), ('evidence_index', []), ('reconciliation', {}),
                              ('query_results', [dict(operation={})])):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.prompt)
                changed[field] = value
                t = simulated_transport(self.packet)
                with self.assertRaises(Refusal):
                    t.prepare(encoded(changed), schema=self.schema)
                self.assertFalse(t.http.requests)
        changed = dict(self.prompt, endpoint='https://example.invalid')
        with self.assertRaises(Refusal):
            self.transport.prepare(encoded(changed), schema=self.schema)
        with self.assertRaisesRegex(Refusal, 'schema_unsupported'):
            self.transport.prepare(encoded(self.prompt), schema={})

    def test_stale_authorization_after_reservation_and_input_drift_never_send(self):
        self.transport.prepare(encoded(self.prompt), schema=self.schema)
        self.transport.clock = lambda: NOW+121
        with self.assertRaises(Refusal):
            self.transport.complete(encoded(self.prompt), schema=self.schema, timeout=25)
        self.assertFalse(self.transport.http.requests)
        self.assertIsNone(self.transport.pending)
        t = simulated_transport(self.packet)
        t.prepare(encoded(self.prompt), schema=self.schema)
        changed = dict(self.prompt, binding_hash='0'*64)
        with self.assertRaisesRegex(Refusal, 'reserved_input_changed'):
            t.complete(encoded(changed), schema=self.schema, timeout=25)
        self.assertFalse(t.http.requests)

    def test_http_status_failure_redaction_no_retry_and_no_replay(self):
        for status in (301, 302, 307, 308, 401, 429, 500, 503):
            with self.subTest(status=status):
                t = simulated_transport(self.packet, [wire.HTTPResult(status, b'PRIVATE_REMOTE_ERROR_SENTINEL')])
                job, _ = self.history.intake(self.packet)
                # Independent temporary history for each consumed invocation.
                with tempfile.TemporaryDirectory() as tmp:
                    history = History(Path(tmp).resolve(), clock=lambda: NOW)
                    job, _ = history.intake(self.packet)
                    result = investigate(history, job, 'SIMULATED-failure', t)
                    self.assertEqual(result['status'], 'blocked')
                    self.assertEqual(result['model_calls'], 1)
                    self.assertEqual(len(t.http.requests), 1)
                    self.assertNotIn('PRIVATE_REMOTE', encoded(history.read()).decode())
                    self.assertFalse(any(e['type'] in ('model_completed', 'api_response') for e in history.read()))
                    with self.assertRaisesRegex(Refusal, 'already_consumed'):
                        investigate(history, job, 'SIMULATED-retry', simulated_transport(self.packet))
                    with self.assertRaisesRegex(Refusal, 'already_consumed'):
                        t.prepare(encoded(self.prompt), schema=self.schema)

    def test_credential_echo_in_remote_success_is_refused_without_retention(self):
        response = simulated_response(simulated_replies(self.packet)[0], 1)
        body = decode(response.body, wire.MAX_RESPONSE)
        body['metadata'] = {'echo': wire.SYNTHETIC_CREDENTIAL}
        with self.assertRaisesRegex(Refusal, 'credential_echo_refused') as error:
            self.complete(replace(response, body=encoded(body)))
        self.assertNotIn(wire.SYNTHETIC_CREDENTIAL, str(error.exception))
        self.assertIsNone(self.transport.completion_accounting())
        self.assertEqual(len(self.transport.http.requests), 1)
        t = simulated_transport(self.packet, [replace(response, request_id=wire.SYNTHETIC_CREDENTIAL)])
        t.prepare(encoded(self.prompt), schema=self.schema)
        with self.assertRaisesRegex(Refusal, 'credential_echo_refused'):
            t.complete(encoded(self.prompt), schema=self.schema, timeout=25)
        self.assertIsNone(t.completion_accounting())

    def test_disconnect_timeout_and_interrupt_keep_durable_unknown(self):
        for failure in (TimeoutError('PRIVATE_SENTINEL'), ConnectionResetError('PRIVATE_SENTINEL'),
                        KeyboardInterrupt(), SystemExit()):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp:
                history = History(Path(tmp).resolve(), clock=lambda: NOW)
                job, _ = history.intake(self.packet)
                t = simulated_transport(self.packet, [failure])
                if isinstance(failure, (KeyboardInterrupt, SystemExit)):
                    with self.assertRaises(type(failure)):
                        investigate(history, job, 'SIMULATED-interrupt', t)
                    self.assertIn('failed_unknown', daily_digest(history, selected_date='2026-10-31',
                                                               timezone='UTC')['text'])
                else:
                    result = investigate(history, job, 'SIMULATED-interrupt', t)
                    self.assertEqual(result['status'], 'blocked')
                events = history.read()
                self.assertEqual(sum(e['type'] == 'model_reserved' for e in events), 1)
                self.assertFalse(any(e['type'] == 'model_completed' for e in events))
                self.assertEqual(len(t.http.requests), 1)
                self.assertNotIn('PRIVATE_SENTINEL', encoded(events).decode())
                with self.assertRaisesRegex(Refusal, 'already_consumed'):
                    investigate(history, job, 'SIMULATED-new-id', simulated_transport(self.packet))

    def test_concurrent_duplicate_invocation_can_reserve_and_send_only_once(self):
        job, _ = self.history.intake(self.packet)
        def run(n):
            try:
                return investigate(self.history, job, 'SIMULATED-concurrent-'+str(n), self.transport)
            except Refusal:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, (1, 2)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(len(self.transport.http.requests), 2)
        self.assertEqual(sum(e['type'] == 'model_reserved' for e in self.history.read()), 2)

    def test_duplicate_and_out_of_order_reservation_and_unknown_predecessor_fail(self):
        job, _ = self.history.intake(self.packet)
        runtime = self.transport.identity()
        self.history.start(job, 'SIMULATED-invocation', runtime)
        event = dict(type='model_reserved', job=job, invocation='SIMULATED-invocation', call=1,
                     prompt_hash=digest(self.prompt), runtime=runtime)
        self.history.record(event)
        with self.assertRaisesRegex(Refusal, 'reservation_sequence'):
            self.history.record(event)
        with self.assertRaisesRegex(Refusal, 'previous_model_attempt_unknown'):
            self.history.record(dict(event, call=2))

    def test_response_shape_and_reasoning_metadata_not_retained(self):
        reply = decode(self.complete())
        self.assertEqual(reply['kind'], 'lookup')
        self.assertEqual(self.transport.last_accounting['response_id'], 'resp_SIMULATED_1')
        self.assertNotIn('rs_SIMULATED', encoded(self.transport.last_accounting).decode())
        response = simulated_response(simulated_replies(self.packet)[0], 1)
        no_request_id = replace(response, request_id=None)
        _, accounting = parse_response(no_request_id.body, self.schema)
        self.assertNotIn('request_id', accounting)

    def test_refuse_actions_refusals_hidden_reasoning_and_multiple_answers(self):
        original = decode(simulated_response(simulated_replies(self.packet)[0], 1).body, wire.MAX_RESPONSE)
        mutations = []
        for kind in ('function_call', 'web_search_call', 'mcp_call', 'computer_call', 'code_interpreter_call',
                     'shell_call', 'image_generation_call', 'file_search_call', 'custom_tool_call'):
            r = copy.deepcopy(original)
            r['output'].insert(0, dict(type=kind, arguments='PRIVATE_SENTINEL'))
            mutations.append(r)
        for modify in ('refusal', 'multiple', 'reasoning', 'encrypted', 'annotations', 'role', 'content'):
            r = copy.deepcopy(original)
            if modify == 'refusal':
                r['output'][1]['content'] = [dict(type='refusal', refusal='PRIVATE_SENTINEL')]
            elif modify == 'multiple':
                r['output'].append(copy.deepcopy(r['output'][1]))
            elif modify == 'reasoning':
                r['output'][0]['summary'] = [dict(type='summary_text', text='PRIVATE_SENTINEL')]
            elif modify == 'encrypted':
                r['output'][0]['encrypted_content'] = ['PRIVATE_SENTINEL']
            elif modify == 'annotations':
                r['output'][1]['content'][0]['annotations'] = [dict(url='https://example.invalid')]
            elif modify == 'role':
                r['output'][1]['role'] = 'user'
            else:
                r['output'][1]['content'].append(copy.deepcopy(r['output'][1]['content'][0]))
            mutations.append(r)
        for r in mutations:
            with self.subTest(output=r['output'][0].get('type')):
                with self.assertRaises(Refusal) as error:
                    parse_response(encoded(r), self.schema)
                self.assertNotIn('PRIVATE_SENTINEL', str(error.exception))

    def test_reject_response_contract_status_model_usage_and_token_limits(self):
        original = decode(simulated_response(simulated_replies(self.packet)[0], 1).body, wire.MAX_RESPONSE)
        mutations = [('status', 'incomplete'), ('status', 'failed'), ('model', 'gpt-other'), ('store', True),
                     ('background', True), ('tools', [dict(type='web_search')]), ('tool_choice', 'auto'),
                     ('text', {}), ('text', None), ('unknown_schema', {}), ('output_text', 'extra answer'), ('max_output_tokens', OUTPUT_TOKENS+1), ('usage', None), ('id', 'PRIVATE/ID')]
        for key, value in mutations:
            r = dict(original, **{key: value})
            with self.subTest(key=key), self.assertRaises(Refusal):
                parse_response(encoded(r), self.schema)
        for key, value in [('input_tokens', INPUT_TOKENS+1), ('output_tokens', OUTPUT_TOKENS+1),
                           ('total_tokens', 1), ('total_tokens', True), ('input_tokens_details', {}),
                           ('output_tokens_details', dict(reasoning_tokens=10000))]:
            r = copy.deepcopy(original)
            r['usage'][key] = value
            with self.subTest(key=key), self.assertRaises(Refusal):
                parse_response(encoded(r), self.schema)

    def test_malformed_duplicate_truncated_oversized_and_schema_invalid_answers(self):
        for raw in (b'{', b'{}{}', b'{"id":"a","id":"b"}', b'x'*(wire.MAX_RESPONSE+1), b'\xff'):
            with self.subTest(length=len(raw)), self.assertRaises(Refusal):
                parse_response(raw, self.schema)
        original = decode(simulated_response(simulated_replies(self.packet)[0], 1).body, wire.MAX_RESPONSE)
        for reply in ({}, dict(simulated_replies(self.packet)[0], extra='command'),
                       dict(simulated_replies(self.packet)[0], lookups=[{}]),
                       dict(simulated_replies(self.packet)[0], kind='shell')):
            r = copy.deepcopy(original)
            r['output'][1]['content'][0]['text'] = encoded(reply).decode()
            with self.assertRaisesRegex(Refusal, 'answer_schema'):
                parse_response(encoded(r), self.schema)
        original['output'][1]['content'][0]['text'] = 'x'*8193
        with self.assertRaises(Refusal):
            parse_response(encoded(original), self.schema)

    def partition_response(self, reply, number, cached, written):
        response = simulated_response(reply, number)
        body = decode(response.body, wire.MAX_RESPONSE)
        body['usage']['input_tokens_details'] = dict(cached_tokens=cached, cache_write_tokens=written)
        return replace(response, body=encoded(body))

    def test_input_partition_accepts_zero_components_remainder_and_exact_equality(self):
        for cached, written in ((0, 0), (0, 1200), (1200, 0), (400, 500), (600, 600)):
            with self.subTest(cached=cached, written=written):
                response = self.partition_response(simulated_replies(self.packet)[0], 1, cached, written)
                answer, accounting = parse_response(response.body, self.schema)
                self.assertEqual(decode(answer), simulated_replies(self.packet)[0])
                # Preserve every reported field verbatim, without normalization.
                self.assertEqual(accounting['usage'], decode(response.body, wire.MAX_RESPONSE)['usage'])

    def test_input_partition_rejects_one_token_overflow_and_double_counting(self):
        for cached, written in ((600, 601), (601, 600), (1200, 1), (1, 1200), (1200, 1200)):
            with self.subTest(cached=cached, written=written):
                response = self.partition_response(simulated_replies(self.packet)[0], 1, cached, written)
                with self.assertRaisesRegex(Refusal, '^responses_usage_invalid$'):
                    parse_response(response.body, self.schema)

    def test_input_partition_still_requires_both_exact_nonnegative_integer_components(self):
        for field in ('cached_tokens', 'cache_write_tokens'):
            for value in (True, False, -1, 1.0, '1', None, 1201):
                with self.subTest(field=field, value=value):
                    response = self.partition_response(simulated_replies(self.packet)[0], 1, 0, 0)
                    body = decode(response.body, wire.MAX_RESPONSE)
                    body['usage']['input_tokens_details'][field] = value
                    with self.assertRaisesRegex(Refusal, '^responses_usage_invalid$'):
                        parse_response(encoded(body), self.schema)
            body = decode(response.body, wire.MAX_RESPONSE)
            del body['usage']['input_tokens_details'][field]
            with self.subTest(missing=field), self.assertRaisesRegex(Refusal, '^responses_usage_invalid$'):
                parse_response(encoded(body), self.schema)

    def test_valid_input_partitions_complete_simulated_http_loop_without_normalization(self):
        for cached, written in ((400, 500), (600, 600)):
            with self.subTest(cached=cached, written=written), tempfile.TemporaryDirectory() as tmp:
                history = History(Path(tmp).resolve(), clock=lambda: NOW)
                job, _ = history.intake(self.packet)
                responses = [self.partition_response(r, n, cached, written)
                             for n, r in enumerate(simulated_replies(self.packet), 1)]
                t = simulated_transport(self.packet, responses)
                result = investigate(history, job, 'SIMULATED-valid-partition', t)
                self.assertEqual(result['status'], 'supported_candidate')
                self.assertEqual(len(t.http.requests), 2)
                accounting = [e['accounting'] for e in history.read() if e['type'] == 'api_response']
                self.assertEqual(len(accounting), 2)
                for recorded, response in zip(accounting, responses):
                    self.assertTrue(recorded['simulated'])
                    self.assertEqual(recorded['usage'], decode(response.body, wire.MAX_RESPONSE)['usage'])

    def assert_invalid_partition_consumed(self, failed_call):
        for cached, written in ((600, 601), (1200, 1200)):
            with self.subTest(call=failed_call, cached=cached, written=written), \
                    tempfile.TemporaryDirectory() as tmp, \
                    patch('socket.socket', side_effect=AssertionError('real socket forbidden')) as sockets, \
                    patch('socket.getaddrinfo', side_effect=AssertionError('real DNS forbidden')) as dns:
                directory = Path(tmp).resolve()
                history = History(directory, clock=lambda: NOW)
                job, _ = history.intake(self.packet)
                replies = simulated_replies(self.packet)
                responses = [self.partition_response(r, n, 400, 500) for n, r in enumerate(replies, 1)]
                responses[failed_call-1] = self.partition_response(replies[failed_call-1], failed_call, cached, written)
                t = simulated_transport(self.packet, responses)
                result = investigate(history, job, 'SIMULATED-invalid-partition', t)
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['reason'], 'responses_usage_invalid')
                self.assertIsNone(result['model_result'])
                self.assertFalse(result['production_identity_verified'])
                self.assertFalse(result['download_consent'])
                self.assertEqual(result['provider_gets'], 0)
                self.assertEqual(result['model_calls'], failed_call)
                self.assertEqual(len(t.http.requests), failed_call)
                self.assertIsNone(t.completion_accounting())
                self.assertIsNone(t.pending)
                self.assertEqual(len(t.used), failed_call)
                events = history.read()
                reservations = [e for e in events if e['type'] == 'model_reserved']
                accepted = [e for e in events if e['type'] == 'api_response']
                completed = [e for e in events if e['type'] == 'model_completed']
                self.assertEqual([e['call'] for e in reservations], list(range(1, failed_call+1)))
                self.assertEqual([e['call'] for e in accepted], list(range(1, failed_call)))
                self.assertEqual([e['call'] for e in completed], list(range(1, failed_call)))
                lookups = [e for e in events if e['type'] == 'lookup']
                self.assertEqual(len(lookups), 2 if failed_call == 2 else 0)
                self.assertTrue(all(e['answer']['rows'] for e in lookups))
                self.assertFalse(any(e.get('status') == 'supported_candidate' for e in events))
                for reservation in reservations:
                    self.assertTrue(reservation['api_request']['simulated'])
                    self.assertEqual(reservation['api_request']['monetary_reservation'], 'unverified_no_live_send')
                if accepted:
                    self.assertEqual(accepted[0]['accounting']['usage'], decode(responses[0].body, wire.MAX_RESPONSE)['usage'])
                    self.assertEqual(accepted[0]['accounting']['response_id'], 'resp_SIMULATED_1')
                    self.assertEqual(accepted[0]['accounting']['request_hash'], reservations[0]['api_request']['request_hash'])
                    self.assertLess(events.index(accepted[0]), events.index(reservations[1]))
                review = daily_digest(history, selected_date='2026-10-31', timezone='UTC')['text']
                self.assertIn('SIMULATED; not a real identification', review)
                self.assertIn('do not replay an unknown attempt', review)
                self.assertEqual(review.count('API accounting (SIMULATED)'), failed_call-1)
                # Restart preserves the uncompleted reservation; neither a new invocation
                # nor the same prepared request can refund, retry or replay it.
                reopened = History(directory, clock=lambda: NOW)
                fresh = simulated_transport(self.packet)
                with self.assertRaisesRegex(Refusal, 'already_consumed'):
                    investigate(reopened, job, 'SIMULATED-retry-partition', fresh)
                payload = decode(decode(t.http.requests[-1]['body'], 65536)['input'][0]['content'][0]['text'])
                payload['instruction'] = INSTRUCTIONS
                with self.assertRaisesRegex(Refusal, 'already_consumed'):
                    t.prepare(encoded(payload), schema=self.schema)
                with self.assertRaisesRegex(Refusal, 'reservation_required'):
                    t.complete(encoded(payload), schema=self.schema, timeout=25)
                self.assertFalse(fresh.http.requests)
                self.assertEqual(len(t.http.requests), failed_call)
                self.assertEqual(reopened.read(), events)
                sockets.assert_not_called()
                dns.assert_not_called()

    def test_invalid_input_partition_on_first_response_stops_without_accounting_or_lookup(self):
        self.assert_invalid_partition_consumed(1)

    def test_invalid_input_partition_on_second_response_preserves_valid_lookup_accounting(self):
        self.assert_invalid_partition_consumed(2)

    def test_deadline_and_request_byte_bounds_no_auto_retry(self):
        ticks = iter([0, 0, 26])
        self.transport.monotonic = lambda: next(ticks)
        with self.assertRaisesRegex(Refusal, 'deadline_exceeded'):
            self.complete()
        self.assertEqual(len(self.transport.http.requests), 1)
        self.assertIsNone(self.transport.completion_accounting())
        t = simulated_transport(self.packet)
        ticks = iter([0, 26])
        t.monotonic = lambda: next(ticks)
        t.prepare(encoded(self.prompt), schema=self.schema)
        with self.assertRaisesRegex(Refusal, 'deadline_exceeded'):
            t.complete(encoded(self.prompt), schema=self.schema, timeout=25)
        self.assertFalse(t.http.requests)  # Revalidation consumed the call budget.
        t = simulated_transport(self.packet)
        with self.assertRaises(Refusal):
            t.prepare(b'x'*49153, schema=self.schema)
        self.assertFalse(t.http.requests)
        for timeout in (0, -1, 26, float('inf'), float('nan')):
            with self.subTest(timeout=timeout), self.assertRaises(Refusal):
                t.complete(encoded(self.prompt), schema=self.schema, timeout=timeout)

    def test_evidence_citation_binding_and_lookup_guards_still_apply(self):
        for modification in ('binding', 'citation', 'id', 'lookup', 'too_many'):
            replies = simulated_replies(self.packet)
            if modification == 'binding': replies[1]['binding_hash'] = '0'*64
            elif modification == 'citation': replies[1]['result']['citations'][0]['evidence_id'] = 'forged'
            elif modification == 'id': replies[1]['result']['candidate']['tmdb'] += 1
            elif modification == 'lookup': replies[0]['lookups'][0]['operation'] = 'shell'
            else: replies[0]['lookups'] *= 3
            with self.subTest(modification=modification), tempfile.TemporaryDirectory() as tmp:
                history = History(Path(tmp).resolve(), clock=lambda: NOW)
                job, _ = history.intake(self.packet)
                t = simulated_transport(self.packet, [simulated_response(r,n) for n,r in enumerate(replies)])
                result = investigate(history, job, 'SIMULATED-invalid', t)
                self.assertEqual(result['status'], 'blocked')
                self.assertLessEqual(len(t.http.requests), 2)


class WireTests(unittest.TestCase):
    """HTTP wire path with fake authorization/sockets; no verified-live claim."""
    def setUp(self):
        # Simulate only the absent external authorization verifier. Every DNS,
        # socket and TLS object below is replaced; this cannot reach a network.
        gate = patch('ai_movie_investigator.responses_transport.real_activation_refusal', return_value=None)
        gate.start()
        self.addCleanup(gate.stop)
        self.sock = Mock()
        self.sock.getpeername.return_value = ('8.8.8.8', 443)
        self.context = Mock()
        self.context.wrap_socket.return_value = self.sock
        self.response = Mock(status=200)
        self.response.getheaders.return_value = [('Content-Type','application/json'), ('Content-Length','2')]
        self.response.read1.side_effect = [b'{}', b'']
        self.connection = Mock()
        self.connection.getresponse.return_value = self.response
        for name, value in [('socket.getaddrinfo', [(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',('8.8.8.8',443))]),
                            ('socket.socket', self.sock),
                            ('ai_movie_investigator.responses_http.tls_context', self.context),
                            ('http.client.HTTPConnection', self.connection)]:
            p = patch(name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        self.credential = wire.ExplicitCredential(wire.SYNTHETIC_CREDENTIAL)

    def exchange(self, timeout=.2):
        return wire.FixedResponsesHTTP().post(b'{}', credential=self.credential,
                                                   project=wire.SYNTHETIC_PROJECT, timeout=timeout)

    def test_exact_wire_origin_tls_sni_and_proxy_independence(self):
        with patch.dict(os.environ, {'HTTPS_PROXY':'https://example.invalid', 'OPENAI_BASE_URL':'https://example.invalid'}):
            self.assertEqual(self.exchange().body, b'{}')
        socket.getaddrinfo.assert_called_once_with('api.openai.com',443,type=socket.SOCK_STREAM,proto=socket.IPPROTO_TCP)
        self.context.wrap_socket.assert_called_once_with(self.sock,server_hostname='api.openai.com')
        self.connection.request.assert_called_once_with('POST','/v1/responses',body=b'{}',
                                                         headers=wire.headers(self.credential, wire.SYNTHETIC_PROJECT))
        self.connection.close.assert_called_once()
        self.sock.connect.assert_called_once_with(('8.8.8.8',443))

    def test_real_http_serialization_with_synthetic_tls_socket(self):
        self.sock.makefile.return_value = io.BytesIO(
            b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n'
            b'x-request-id: req_SIMULATED_wire\r\nConnection: close\r\n\r\n{}')
        with patch('http.client.HTTPConnection', REAL_HTTP_CONNECTION):
            result = self.exchange()
        self.assertEqual(result.body, b'{}')
        self.assertEqual(result.request_id, 'req_SIMULATED_wire')
        sent = b''.join(call.args[0] for call in self.sock.sendall.call_args_list)
        self.assertTrue(sent.startswith(b'POST /v1/responses HTTP/1.1\r\nHost: api.openai.com:443\r\n'))
        self.assertIn(b'Authorization: Bearer SIMULATED-NOT-A-KEY\r\n', sent)
        self.assertIn(b'OpenAI-Project: proj_SIMULATED\r\n', sent)
        self.assertIn(b'Content-Length: 2\r\n', sent)
        self.assertNotIn(b'Proxy-', sent)
        self.assertTrue(sent.endswith(b'\r\n\r\n{}'))

    def test_nonpublic_dns_and_changed_peer_refused_without_send(self):
        for address in ('127.0.0.1','169.254.169.254','10.0.0.1','::1','192.0.2.1'):
            with patch('socket.getaddrinfo', return_value=[(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',(address,443))]):
                with self.subTest(address=address), self.assertRaisesRegex(Refusal,'network_denied'):
                    self.exchange()
        self.connection.request.assert_not_called()
        self.sock.connect.assert_not_called()
        self.sock.getpeername.return_value = ('1.1.1.1',443)
        with self.assertRaisesRegex(Refusal,'peer_changed'):
            self.exchange()
        self.connection.request.assert_not_called()
        self.sock.close.assert_called()

    def test_redirects_errors_no_forward_no_body_read_no_retry(self):
        for status in (301,302,303,307,308,401,429,500,503):
            self.response.status = status
            self.connection.request.reset_mock()
            with self.subTest(status=status), self.assertRaisesRegex(Refusal,'http_rejected'):
                self.exchange()
            self.connection.request.assert_called_once()
        self.response.read1.assert_not_called()

    def test_header_length_encoding_size_truncation_and_header_injection_denied(self):
        for hs, parts in [([('Content-Type','text/html')], []),
                          ([('Content-Type','application/json'),('Content-Encoding','gzip')], []),
                          ([('Content-Type','application/json'),('Content-Length','32769')], []),
                          ([('Content-Type','application/json'),('Content-Length','2'),('Content-Length','2')], []),
                          ([('Content-Type','application/json'),('Content-Length','3')],[b'{}',b'']),
                          ([('Content-Type','application/json')],[b'x'*32769])]:
            self.response.getheaders.return_value = hs
            self.response.read1.side_effect = parts
            with self.subTest(headers=hs), self.assertRaises(Refusal):
                self.exchange()
        for value in ('SIMULATED\r\nInjected', 'bad space'):
            with self.assertRaises(Refusal):
                wire.headers(wire.ExplicitCredential(value),wire.SYNTHETIC_PROJECT)
        with self.assertRaises(Refusal): wire.headers(self.credential,'proj_bad\n')

    def test_total_deadline_covers_dns_tls_headers_and_slow_reads(self):
        def slow(*args, **kwargs):
            time.sleep(.1)
            return b'x'
        for where in ('dns','tls','headers','body'):
            target = {'dns':'socket.getaddrinfo', 'tls':'ai_movie_investigator.responses_http.tls_context',
                      'headers':'http.client.HTTPConnection.getresponse'}[where] if where != 'body' else None
            self.response.getheaders.return_value = [('Content-Type','application/json')]
            if where in ('headers','body'):
                selected = self.connection.getresponse if where == 'headers' else self.response.read1
                selected.side_effect = slow
                try:
                    with self.subTest(where=where), self.assertRaisesRegex(Refusal,'completion_unknown|deadline_exceeded'):
                        self.exchange(timeout=.01)
                finally: selected.side_effect = None
            else:
                with patch(target, side_effect=slow):
                    with self.subTest(where=where), self.assertRaisesRegex(Refusal,'completion_unknown|deadline_exceeded'):
                        self.exchange(timeout=.01)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        # Signal delivery is not a substitute for phase checks. A delayed
        # timer must still reject before interpreting late data or sending.
        self.connection.request.reset_mock()
        with patch('signal.setitimer'), patch('ai_movie_investigator.responses_http.tls_context', side_effect=slow):
            with self.assertRaisesRegex(Refusal, 'deadline_exceeded'):
                self.exchange(timeout=.01)
        self.connection.request.assert_not_called()

    def test_tls_uses_compiled_trust_no_environment_overrides_or_keylog(self):
        paths = Mock(openssl_cafile='/SIMULATED/compiled.pem', openssl_capath='/SIMULATED/roots')
        ctx = Mock(check_hostname=True, verify_mode=ssl.CERT_REQUIRED)
        with patch('ssl.SSLContext', return_value=ctx), patch('ssl.get_default_verify_paths', return_value=paths):
            with patch.dict(os.environ, {'SSL_CERT_FILE':'AMBIENT', 'SSL_CERT_DIR':'AMBIENT', 'SSLKEYLOGFILE':'AMBIENT'}):
                REAL_TLS_CONTEXT()
        ctx.load_verify_locations.assert_called_once_with(cafile='/SIMULATED/compiled.pem',capath='/SIMULATED/roots')
        self.assertFalse(ctx.load_default_certs.called)
        ctx.check_hostname = False
        with patch('ssl.SSLContext', return_value=ctx), patch('ssl.get_default_verify_paths', return_value=paths):
            with self.assertRaisesRegex(Refusal,'tls_required'): REAL_TLS_CONTEXT()

    def test_non_main_thread_and_existing_timer_refuse_before_socket(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(Refusal,'timer_unavailable'):
                pool.submit(self.exchange).result()
        socket.socket.assert_not_called()
        with patch('signal.getitimer', return_value=(1.0,0.0)):
            with self.assertRaisesRegex(Refusal,'timer_busy'): self.exchange()
        socket.socket.assert_not_called()


REAL_TLS_CONTEXT = wire.tls_context
REAL_HTTP_CONNECTION = http.client.HTTPConnection

if __name__ == '__main__':
    unittest.main()
