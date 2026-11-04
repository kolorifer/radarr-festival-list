import copy
import hashlib
from dataclasses import replace
import unittest
from unittest.mock import patch

import test_bound_integration as fixture
from ai_movie_investigator.bound_send import HistoricalDiagnosticParent, OperatorContext
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.pilot_account import COVERAGE
from ai_movie_investigator.responses_http import ExplicitCredential
from ai_movie_investigator.responses_protocol import MODEL, OUTPUT_TOKENS, parse_response
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.spending import POLICY


def context_for(f):
    selection = dict(run='fixture', case=f.prompt['binding'], request_sha256=digest(decode(f.body)),
                     local_context_sha256=digest(dict(prompt=f.prompt, disclosure=f.disclosure)))
    r = dict(mode='historical_manual_diagnostic', selection=selection, project='proj_recording', model=MODEL,
             issued_at=90, expires_at=180, history_identity=list(f.history.identity), currency='TEST-USD',
             ceiling=[1, 2], output_limit=OUTPUT_TOKENS)
    facts = dict(owner=dict(operation=r['mode'], max_calls=1, currency=r['currency'], ceiling=r['ceiling']),
                 privacy=dict(request_sha256=selection['request_sha256'], store=False, tools=[]),
                 account=dict(project=r['project'], model=MODEL, policy=POLICY),
                 credential_route=dict(project=r['project'], injection_route='fixture-object-injection'),
                 coverage=dict(request_sha256=selection['request_sha256'], policy=POLICY, coverage=COVERAGE,
                               counter_identity='FIXTURE-count-not-real', input_upper_bound=2000),
                 pricing=dict(policy=POLICY, currency='TEST-USD', input=[1,1000000], cache_read=[1,1000000],
                              cache_write=[1,1000000], output=[1,1000000], ancillary_maximum=[0,1]))
    binding = digest(r)
    r['evidence'] = {role:dict(binding_hash=binding, issuer='FIXTURE-'+role, reference='FIXTURE-record-'+role,
                             observed_at=90, expires_at=200, facts=facts[role]) for role in facts}
    return r


def pin(r):
    raw = encoded(r)
    return OperatorContext(raw, hashlib.sha256(raw).hexdigest(), tuple((k,digest(v)) for k,v in r['evidence'].items()))


class HistoricalParentTest(unittest.TestCase):
    def setUp(self):
        self.f = fixture.BoundIntegrationTest('test_connected_path_only_replaces_http_io')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.record = context_for(self.f)
        self.credential = ExplicitCredential('sk_FIXTURE_ONLY_NOT_REAL')
        self.f.transport.credential = self.credential
        self.parent = self.make_parent()
        self.response = simulated_response(dict(binding_hash=aliases('fixture'), kind='final', lookups=[], result=dict(
            status='unresolved', candidate=None, alternatives=[], citations=[], rationale='Historical fixture',
            uncertainty='Unknown', next_action='human_review')), 1)

    def make_parent(self, r=None, credential=True):
        p = HistoricalDiagnosticParent(pin(r or self.record), history=self.f.history,
                                       credential=self.credential if credential else None)
        self.f.parent = p
        return p

    def test_real_parent_logic_connected_with_only_http_recorded(self):
        def record(body, **kwargs):
            self.assertEqual(body, self.f.body)
            self.assertEqual(kwargs['authorization']['authority_context_sha256'], pin(self.record).record_sha256)
            self.assertEqual(kwargs['authorization']['maximum_debit'], [381,62500])
            self.assertIs(kwargs['credential'], self.credential)
            self.assertEqual(kwargs['project'], 'proj_recording')
            self.assertEqual(len(self.f.history.read()),2)
            return replace(self.response, request_sha256=hashlib.sha256(body).hexdigest(), project=kwargs['project'])
        with patch('socket.socket', side_effect=AssertionError('network')), patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post', side_effect=record):
            self.assertEqual(decode(self.f.complete())['result']['status'], 'unresolved')
        self.assertEqual(self.f.history.read()[-1]['retained_debit'], [381,62500])

    def test_missing_stale_mismatched_and_over_cap_evidence_refuses_before_send(self):
        changes = [lambda r:r['evidence'].pop('owner'),
                   lambda r:r['evidence']['privacy'].update(expires_at=99),
                   lambda r:r['evidence']['account']['facts'].update(project='proj_wrong'),
                   lambda r:r['evidence']['pricing']['facts'].update(input=[1,1]),
                   lambda r:r['evidence']['coverage']['facts'].update(counter_identity='unknown'),
                   lambda r:r['evidence']['credential_route']['facts'].update(injection_route='unknown')]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                r=copy.deepcopy(self.record);change(r);self.make_parent(r)
                with patch('socket.socket', side_effect=AssertionError('network')), patch(
                        'ai_movie_investigator.responses_http.FixedResponsesHTTP.post', side_effect=AssertionError('send')):
                    with self.assertRaises(Refusal):self.f.complete()
                self.assertEqual(self.f.history.read(),[])

    def test_unpinned_and_changed_disclosure_refuse(self):
        c=pin(self.record)
        self.f.parent=HistoricalDiagnosticParent(OperatorContext(c.record_json,'0'*64,c.evidence_pins),
                                               history=self.f.history,credential=self.credential)
        with self.assertRaisesRegex(Refusal,'operator_context_pin'):self.f.complete()
        self.make_parent()
        self.f.prompt['facts']['title']='Changed'
        self.f.disclosure['facts']['title']='Changed'
        with self.assertRaisesRegex(Refusal,'operator_selection_changed'):self.f.complete()
        self.assertEqual(self.f.history.read(),[])

    def test_absent_credential_and_wrong_object_refuse(self):
        self.make_parent(credential=False)
        with self.assertRaises(Refusal):self.f.complete()
        self.make_parent()
        self.f.transport.credential=ExplicitCredential(self.credential.value)
        with self.assertRaisesRegex(Refusal,'operator_credential_route_changed'):self.f.complete()
        self.assertEqual(self.f.history.read(),[])

    def test_timeout_retains_debit_across_reconstructed_parent(self):
        with patch('socket.socket', side_effect=AssertionError('network')), patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):self.f.complete()
        self.make_parent()
        with self.assertRaisesRegex(Refusal,'binding_attempt_consumed'):self.f.complete()
        self.assertEqual(len(self.f.history.read()),2)

    def test_receipt_mismatch_refuses(self):
        permit=self.parent.authorize(self.record['selection'],self.f.body)
        response=replace(self.response,request_sha256=permit['selection']['request_sha256'],project=permit['project'])
        _, accounting=parse_response(response.body,output_schema(),response.request_id)
        accounting['request_id']='req_OTHER'
        with self.assertRaisesRegex(Refusal,'operator_receipt_mismatch'):
            self.parent.validate_receipt(permit,response,accounting)

    def test_fixture_operator_context_never_opens_real_boundary(self):
        with patch('socket.socket',side_effect=AssertionError('network')):
            with self.assertRaisesRegex(Refusal,'responses_real_authorization_unimplemented'):self.f.complete()
        self.assertEqual(len(self.f.history.read()),2)

    def test_missing_or_other_request_transport_stamp_refused(self):
        permit=self.parent.authorize(self.record['selection'],self.f.body)
        for response in (self.response,
                         replace(self.response,request_sha256='0'*64,project='proj_recording'),
                         replace(self.response,request_sha256=permit['selection']['request_sha256'],project='proj_other')):
            with self.subTest(response=response.request_sha256):
                _, accounting=parse_response(response.body,output_schema(),response.request_id)
                with self.assertRaisesRegex(Refusal,'operator_receipt_correlation'):
                    self.parent.validate_receipt(permit,response,accounting)
