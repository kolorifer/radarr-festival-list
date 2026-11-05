"""Dormant count-path tests; every wire object is fake, no credentials."""
import copy
import unittest
from dataclasses import replace
from unittest.mock import patch
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded
from ai_movie_investigator.credit_test import request, count_request, count_receipt
from ai_movie_investigator.responses_http import FixedResponsesHTTP, HTTPResult, headers
import test_responses_transport as fixtures


class CreditCountTests(unittest.TestCase):
    def test_count_covers_instructions_input_and_output_schema_exactly(self):
        generation=decode(request('one')); count=decode(count_request('one'))
        self.assertEqual(set(count),{'model','instructions','input','text','tools','tool_choice','truncation'})
        for key,value in count.items():self.assertEqual(value,generation[key])
        self.assertNotIn('max_output_tokens',count)

    def test_both_routes_still_refuse_before_socket(self):
        with patch('socket.socket',side_effect=AssertionError('network')):
            for method in ('count','post'):
                with self.assertRaisesRegex(Refusal,'responses_real_authorization_unimplemented'):
                    getattr(FixedResponsesHTTP(),method)(count_request('one'),credential=None,
                        project='proj_fixture',timeout=1,authorization={'claimed':True})

    def test_fixed_count_wire_and_correlated_processed_count(self):
        f=fixtures.WireTests('test_exact_wire_origin_tls_sni_and_proxy_independence')
        f.setUp();self.addCleanup(f.doCleanups)
        body=count_request('one')
        raw=encoded(dict(object='response.input_tokens',input_tokens=1234))
        f.response.getheaders.return_value=[('Content-Type','application/json'),
            ('Content-Length',str(len(raw))),('x-request-id','req_count_fixture')]
        f.response.read1.side_effect=[raw,b'']
        result=FixedResponsesHTTP().count(body,credential=f.credential,project='proj_fixture',timeout=.2)
        f.connection.request.assert_called_once_with('POST','/v1/responses/input_tokens',body=body,
            headers=headers(f.credential,'proj_fixture'))
        receipt=count_receipt(result,run='one',project='proj_fixture')
        self.assertEqual(receipt['generation_sha256'],digest(decode(request('one'))))
        self.assertEqual(receipt['input_tokens'],1234)

    def test_count_wrong_project_request_model_binding_and_limits_refuse(self):
        result=HTTPResult(200,encoded(dict(object='response.input_tokens',input_tokens=1234)),
            'req_fixture',digest(decode(count_request('one'))),'proj_fixture','/v1/responses/input_tokens')
        for changed in (replace(result,project='proj_other'),replace(result,request_sha256='0'*64),
                        replace(result,request_id=None),replace(result,status=429),
                        replace(result,path=None),replace(result,path='/v1/responses')):
            with self.assertRaises(Refusal):count_receipt(changed,run='one',project='proj_fixture')
        with self.assertRaises(Refusal):count_receipt(result,run='other',project='proj_fixture')
        for tokens in (True,-1,0,65537,1.5):
            bad=replace(result,body=encoded(dict(object='response.input_tokens',input_tokens=tokens)))
            with self.assertRaises(Refusal):count_receipt(bad,run='one',project='proj_fixture')
        for value in ({'input_tokens':1234},{'object':'response.input_tokens','input_tokens':1234,'extra':1}):
            with self.assertRaises(Refusal):count_receipt(replace(result,body=encoded(value)),run='one',project='proj_fixture')
