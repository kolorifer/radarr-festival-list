"""Explicit Nano retention binding using invented state and fake socket I/O."""
import copy
import unittest
from dataclasses import replace
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.bound_send import HistoricalDiagnosticParent
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.credit_test import POLICY, request
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL, parse_response
from ai_movie_investigator.responses_http import FixedResponsesHTTP
import test_credit_integration as credit
import test_supervised_credit as supervised
import test_supervised_envelope as framing
from test_responses_compatibility import documented

class RetentionTests(unittest.TestCase):
    def fixture(self):
        f=credit.CreditIntegrationTest('test_connected_exact_request_and_full_debit_before_http')
        f.setUp();self.addCleanup(f.doCleanups);return f

    def test_fixed_request_policy_and_hash_are_distinct_from_omitted_history(self):
        body=request('fixture');new=decode(body)
        self.assertEqual(POLICY,dict(model=INTEGRATION_MODEL,service_tier='default',prompt_cache_retention='in_memory'))
        self.assertEqual(new['prompt_cache_retention'],'in_memory')
        self.assertIs(new['store'],False);self.assertEqual(new['tools'],[])
        old=dict(new);del old['prompt_cache_retention']
        self.assertNotEqual(digest(new),digest(old))
        f=self.fixture();f.record['selection']['request_sha256']=digest(old)
        with self.assertRaisesRegex(Refusal,'operator_request_changed'):
            f.parent().authorize(f.record['selection'],body)
        self.assertEqual(f.credit.read(),[]);self.assertEqual(f.f.history.read(),[])

    def test_parent_refuses_missing_null_or_changed_policy_even_with_recomputed_pins(self):
        for value in ('absent',None,'24h','unknown'):
            f=self.fixture();body=decode(request('fixture'))
            if value=='absent':del body['prompt_cache_retention']
            else:body['prompt_cache_retention']=value
            f.record['selection']['request_sha256']=digest(body)
            with self.subTest(value=value),self.assertRaisesRegex(Refusal,'operator_request_policy'):
                f.parent().authorize(f.record['selection'],encoded(body))
            self.assertEqual(f.credit.read(),[]);self.assertEqual(f.f.history.read(),[])

    def test_parent_requires_new_policy_in_account_coverage_and_pricing_evidence(self):
        for role,reason in [('account','operator_account_unknown'),('coverage','operator_coverage_unknown'),('pricing','operator_pricing_unknown')]:
            f=self.fixture();facts=f.record['evidence'][role]['facts']
            facts['policy']=dict(POLICY);del facts['policy']['prompt_cache_retention']
            with self.subTest(role=role),self.assertRaisesRegex(Refusal,reason):
                f.parent().authorize(f.record['selection'],request('fixture'))
            self.assertEqual(f.credit.read(),[])

    def test_old_selected_owner_evidence_refuses_before_prompt_or_state_change(self):
        f=supervised.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        f.setUp();self.addCleanup(f.doCleanups)
        before={p:p.read_bytes() for p in f.state.rglob('*.jsonl')}
        e=copy.deepcopy(f.evidence);del e['policy']['prompt_cache_retention']
        f.path.write_bytes(encoded(e));selected=command.read_evidence(f.path)
        with patch.object(command,'prompt_credential') as prompt:
            with self.assertRaises(Refusal):command.run(f.state,selected,1,clock=lambda:f.now)
        prompt.assert_not_called()
        self.assertEqual({p:p.read_bytes() for p in f.state.rglob('*.jsonl')},before)

    def test_receipt_cannot_drop_or_replace_explicit_policy(self):
        f=self.fixture();parent=f.parent();body=request('fixture')
        permit=parent.authorize(f.record['selection'],body)
        result=replace(credit.response(),request_sha256=digest(decode(body)),project=f.record['project'])
        _,accounting=parse_response(result.body,output_schema(),result.request_id,expected_model=INTEGRATION_MODEL)
        self.assertEqual(accounting['policy'],POLICY)
        self.assertTrue(parent.validate_receipt(permit,result,accounting))
        for value in ('absent',None,'24h'):
            wrong=copy.deepcopy(accounting)
            if value=='absent':del wrong['policy']['prompt_cache_retention']
            else:wrong['policy']['prompt_cache_retention']=value
            with self.assertRaisesRegex(Refusal,'operator_receipt_mismatch'):
                parent.validate_receipt(permit,result,wrong)

    def test_full_documented_http_path_binds_request_and_reparsed_receipt(self):
        helper=framing.EnvelopeTests();self.addCleanup(helper.doCleanups)
        post=FixedResponsesHTTP.post;receipt=HistoricalDiagnosticParent.validate_receipt
        seen=[]
        def checked_post(owner,body,**kwargs):
            self.assertEqual(decode(body)['prompt_cache_retention'],'in_memory');seen.append('post')
            return post(owner,body,**kwargs)
        def checked_receipt(owner,permit,result,accounting):
            self.assertEqual(accounting['policy'],POLICY);seen.append('receipt')
            return receipt(owner,permit,result,accounting)
        with patch.object(FixedResponsesHTTP,'post',checked_post),patch.object(HistoricalDiagnosticParent,'validate_receipt',checked_receipt):
            helper.exercise(encoded(documented()),'chunked')
        self.assertEqual(seen,['post','receipt'])
        for value in ('absent',None,'24h'):
            v=documented()
            if value=='absent':del v['prompt_cache_retention']
            else:v['prompt_cache_retention']=value
            helper.exercise(encoded(v),reason='responses_cache_or_tier_changed')
