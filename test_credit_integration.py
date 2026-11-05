"""Nonsensitive fixtures: no network, account access, credential or spending."""
import copy
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ai_movie_investigator.bound_send import HistoricalDiagnosticParent, _send_bound
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded
from ai_movie_investigator.credit_test import request, reserve, POLICY
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.history import History, FILENAME
from ai_movie_investigator.responses_http import ExplicitCredential
from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL, INTEGRATION_SHUTDOWN, parse_response
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.responses_transport import ResponsesTransport
from test_historical_parent import context_for, pin
import test_bound_integration as fixtures


def repin(record):
    binding = digest({k:v for k,v in record.items() if k != 'evidence'})
    for evidence in record['evidence'].values():
        evidence['binding_hash'] = binding
    return pin(record)


def response(run='fixture', model=INTEGRATION_MODEL):
    result = simulated_response(dict(binding_hash=aliases(run), kind='final', lookups=[], result=dict(
        status='unresolved', candidate=None, alternatives=[], citations=[], rationale='Synthetic input',
        uncertainty='No evidence supplied', next_action='human_review')), 1)
    body = decode(result.body)
    body['model'] = model
    body.pop('prompt_cache_options');body['prompt_cache_retention']='in_memory'
    body['usage']['input_tokens_details'] = dict(cached_tokens=100)
    return replace(result, body=encoded(body))


class CreditIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.BoundIntegrationTest('test_connected_path_only_replaces_http_io')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.credit = History(Path(self.tmp.name).resolve(), clock=lambda:100)
        with self.credit.transaction(write=True): pass
        info=(self.credit.directory / FILENAME).stat()
        self.file_identity=(info.st_dev,info.st_ino)
        self.credential = ExplicitCredential('sk_FIXTURE_ONLY_NOT_REAL')
        self.transport = ResponsesTransport(enabled=True, credential=self.credential)
        self.record = context_for(self.f)
        r = self.record
        r.update(mode='synthetic_api_integration', model=INTEGRATION_MODEL, ceiling=[1,100],
                 credit_history_identity=list(self.credit.identity),credit_history_file_identity=list(self.file_identity))
        r['selection']['request_sha256'] = digest(decode(request('fixture')))
        facts = {k:v['facts'] for k,v in r['evidence'].items()}
        facts['owner'].update(operation=r['mode'], ceiling=r['ceiling'])
        facts['privacy']['request_sha256'] = r['selection']['request_sha256']
        facts['account'].update(model=INTEGRATION_MODEL, policy=POLICY)
        facts['coverage'].update(request_sha256=r['selection']['request_sha256'], policy=POLICY)
        facts['pricing'].update(policy=POLICY, input=[5,100000000],cache_read=[5,1000000000],
                                cache_write=[0,1],output=[4,10000000])

    def parent(self, history=None, credit=None):
        return HistoricalDiagnosticParent(repin(self.record), history=history or self.f.history,
            credit_history=credit or self.credit, credential=self.credential)

    def complete(self, parent=None, history=None):
        return self.transport.complete_credit_test(history=history or self.f.history, run='fixture',
            case=self.record['selection']['case'],
            context_sha256=self.record['selection']['local_context_sha256'], parent=parent or self.parent())

    def test_connected_exact_request_and_full_debit_before_http(self):
        def post(body, **kw):
            self.assertEqual(body, request('fixture'))
            self.assertNotIn('prompt_cache_options', decode(body))
            self.assertEqual(kw['authorization']['maximum_debit'],[1,100])
            self.assertEqual(self.credit.read()[0]['reserved_usd'],[1,100])
            return replace(response(), request_sha256=hashlib.sha256(body).hexdigest(),project=kw['project'])
        with patch('socket.socket', side_effect=AssertionError('network')), patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=post) as sink:
            self.assertEqual(decode(self.complete())['result']['status'],'unresolved')
        self.assertEqual(sink.call_count,1)
        self.assertEqual(self.f.history.read()[-1]['retained_debit'],[1,100])

    def test_expiry_during_credit_reservation_retains_debit_without_http(self):
        parent=self.parent()
        original=parent.reserve_credit_test
        def reserve_then_expire(permit):
            original(permit)
            self.f.history.clock=lambda:181
        with patch.object(parent,'reserve_credit_test',side_effect=reserve_then_expire), patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post') as sink:
            with self.assertRaisesRegex(Refusal,'binding_expired'):self.complete(parent)
        sink.assert_not_called()
        self.assertEqual(self.credit.read()[0]['reserved_usd'],[1,100])

    def test_ambiguous_debit_survives_restart_and_no_second_http(self):
        with patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=TimeoutError) as sink:
            with self.assertRaises(TimeoutError): self.complete()
            h=History(self.f.history.directory,clock=lambda:100)
            c=History(self.credit.directory,clock=lambda:100)
            with self.assertRaisesRegex(Refusal,'binding_attempt_consumed'):
                self.complete(self.parent(h,c),h)
        self.assertEqual(sink.call_count,1)
        self.assertEqual(c.read()[0]['reserved_usd'],[1,100])

    def test_five_reserved_cents_survive_new_objects_and_block_sixth(self):
        for n in range(5):
            reserve(History(self.credit.directory),project='proj_recording',request_hash=digest(n),input_bound=65536,now=100+n,file_identity=self.file_identity)
        with self.assertRaisesRegex(Refusal,'credit_total_ceiling'):
            reserve(History(self.credit.directory),project='proj_recording',request_hash=digest(5),input_bound=65536,now=106,file_identity=self.file_identity)
        self.assertEqual(len(self.credit.read()),5)
        with patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post') as sink:
            with self.assertRaisesRegex(Refusal,'credit_total_ceiling'):self.complete()
        sink.assert_not_called()

    def test_duplicate_request_and_project_change_cannot_reset_budget(self):
        args=dict(project='proj_recording', request_hash=digest(1), input_bound=100, now=100,file_identity=self.file_identity)
        reserve(self.credit,**args)
        for change, error in [({},'credit_request_consumed'),({'project':'proj_other'},'credit_budget_changed'),
                              ({'now':99,'request_hash':digest(2)},'credit_clock_rollback')]:
            with self.assertRaisesRegex(Refusal,error):reserve(self.credit,**dict(args,**change))

    def test_deleted_or_replaced_journal_cannot_reset_selected_budget(self):
        reserve(self.credit,project='proj_recording',request_hash=digest(1),input_bound=100,now=100,
                file_identity=self.file_identity)
        journal=self.credit.directory / FILENAME
        journal.rename(self.credit.directory / 'retained-old-journal')
        with patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post') as sink:
            with self.assertRaisesRegex(Refusal,'history_file_missing'):self.complete()
        sink.assert_not_called()
        self.assertFalse(journal.exists())
        with self.credit.transaction(write=True):pass
        with self.assertRaisesRegex(Refusal,'history_file_identity_changed'):
            reserve(self.credit,project='proj_recording',request_hash=digest(2),input_bound=100,now=100,
                    file_identity=self.file_identity)

    def test_bad_bound_retirement_and_invalid_identity_do_not_reserve(self):
        args=dict(project='proj_recording',request_hash=digest(1),input_bound=65536,now=100,file_identity=self.file_identity)
        for change in ({'input_bound':65537},{'input_bound':True},{'now':INTEGRATION_SHUTDOWN},
                       {'request_hash':'bad'},{'project':'unknown'}):
            with self.assertRaises(Refusal):reserve(self.credit,**dict(args,**change))
        self.assertEqual(self.credit.read(),[])

    def test_no_real_activation_even_with_all_fixture_pins(self):
        with patch('socket.socket',side_effect=AssertionError('network')):
            with self.assertRaisesRegex(Refusal,'responses_real_authorization_unimplemented'):self.complete()
        self.assertEqual(len(self.credit.read()),1)

    def test_disabled_transport_does_not_reserve(self):
        self.transport.enabled=False
        with self.assertRaisesRegex(Refusal,'model_transport_disabled'):self.complete()
        self.assertEqual(self.credit.read(),[])

    def test_changed_model_pricing_or_shared_history_identity_refuses(self):
        original=copy.deepcopy(self.record)
        for mutate in (lambda r:r.update(model='gpt-6.1-sol'),
                       lambda r:r.update(credit_history_identity=[0,0]),
                       lambda r:r['evidence']['pricing']['facts'].update(input=[1,1000000000])):
            self.record=copy.deepcopy(original);mutate(self.record)
            with patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post') as sink:
                with self.assertRaises(Refusal):self.complete()
            sink.assert_not_called()
        self.assertEqual(self.credit.read(),[])

    def test_real_movie_input_cannot_enter_synthetic_profile(self):
        body=decode(request('fixture')); data=decode(body['input'][0]['content'][0]['text'])
        data['facts']['title']='A private movie';body['input'][0]['content'][0]['text']=encoded(data).decode()
        self.record['selection']['request_sha256']=digest(body)
        with self.assertRaisesRegex(Refusal,'credit_synthetic_input_required'):
            self.parent().authorize(self.record['selection'],encoded(body))

    def test_exact_model_response_and_legacy_usage(self):
        raw=response().body
        _, accounting=parse_response(raw,output_schema(),expected_model=INTEGRATION_MODEL)
        self.assertEqual(accounting['policy'],POLICY)
        zero=decode(raw);zero['usage']['input_tokens_details']['cache_write_tokens']=0
        self.assertEqual(parse_response(encoded(zero),output_schema(),expected_model=INTEGRATION_MODEL)[1],accounting)
        self.assertEqual(accounting['usage']['output_tokens_details']['reasoning_tokens'],50)
        with self.assertRaisesRegex(Refusal,'responses_not_completed'):parse_response(raw,output_schema())
        for mutate in (lambda r:r.update(model='gpt-5-nano'),
                       lambda r:r.update(prompt_cache_options={'ttl':'30m'}),
                       lambda r:r['usage']['input_tokens_details'].update(cache_write_tokens=1),
                       lambda r:r['usage']['input_tokens_details'].update(cached_tokens=True),
                       lambda r:r['usage']['output_tokens_details'].update(reasoning_tokens=301),
                       lambda r:r['usage'].update(output_tokens=4097,total_tokens=5297)):
            changed=decode(raw);mutate(changed)
            with self.assertRaises(Refusal):parse_response(encoded(changed),output_schema(),expected_model=INTEGRATION_MODEL)

    def test_wrong_response_model_retains_debit_no_receipt(self):
        with patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',return_value=response(model='gpt-6.1-sol')):
            with self.assertRaises(Refusal):self.complete()
        self.assertEqual(len(self.credit.read()),1)
        self.assertEqual(len(self.f.history.read()),2)

    def test_expanded_historical_input_reaches_parent_and_http_unchanged(self):
        from ai_movie_investigator.manual_offline import parse_packet, build_request
        from test_manual_expanded import envelope
        packet, sha=parse_packet(envelope())
        case, run, _, body=build_request(packet,sha,now=300)
        data=decode(decode(body)['input'][0]['content'][0]['text'])
        r=context_for(self.f)
        r['selection'].update(case=case,run=run,request_sha256=digest(decode(body)))
        r['evidence']['privacy']['facts'].update(request_sha256=digest(decode(body)),disclosure_sha256=digest(data))
        r['evidence']['coverage']['facts']['request_sha256']=digest(decode(body))
        context=replace(repin(r),disclosure_json=encoded(data))
        parent=HistoricalDiagnosticParent(context,history=self.f.history,credential=self.credential)
        res=simulated_response(dict(binding_hash=aliases(run),kind='final',lookups=[],result=dict(
            status='unresolved',candidate=None,alternatives=[],citations=[],rationale='Historical',
            uncertainty='Expired evidence',next_action='human_review')),1)
        def post(actual,**kw):
            self.assertEqual(actual,body)
            self.assertTrue(data['qualifications']['historical'])
            self.assertEqual(data['historical_observations']['catalogue'][0]['expiry_status'],'expired')
            return replace(res,request_sha256=digest(decode(actual)),project=kw['project'])
        for bad in (None,encoded(dict(data,qualifications={}))):
            p=HistoricalDiagnosticParent(replace(context,disclosure_json=bad),history=self.f.history,credential=self.credential)
            with self.assertRaisesRegex(Refusal,'operator_expanded_disclosure_unpinned'):p.authorize(r['selection'],body)
        with patch('socket.socket',side_effect=AssertionError('network')),patch(
                'ai_movie_investigator.responses_http.FixedResponsesHTTP.post',side_effect=post):
            _send_bound(self.f.history,body,case=case,run=run,parent=parent,credential=self.credential,
                        context_sha256=r['selection']['local_context_sha256'])
