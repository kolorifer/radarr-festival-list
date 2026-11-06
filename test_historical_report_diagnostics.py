"""Invented schema-valid answers; receipt truth is separate from report acceptance."""
import copy,io,unittest
from types import SimpleNamespace
from unittest.mock import patch
from ai_movie_investigator import historical_nano as historical,supervised_credit as command
from ai_movie_investigator.contracts import Refusal,decode,digest,encoded
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.responses_protocol import parse_response,INTEGRATION_MODEL
from ai_movie_investigator.disclosure import aliases,evidence_alias
from ai_movie_investigator.supervised_authorization import diagnostic_scope,diagnostic_phase
from test_responses_compatibility import FIXTURE_CODE


def specimen(variant):
    ns={};exec(FIXTURE_CODE,ns);value=ns['documented']()
    grant=dict(run='invented-report-run',case={'fixture':'case'},input_sha256='a'*64,
        disclosure={'rows':{'invented-evidence':{'view':{'claims':[]}}}},request={'input':[{'content':[{'text':encoded(dict(qualifications={'historical':True},historical_observations={})).decode()}]}]})
    answer=decode(value['output'][-1]['content'][0]['text']);answer['binding_hash']=aliases(grant['run'])
    if variant=='slash':answer['result']['rationale']='Identity and edition/cut remain uncertain'
    elif variant=='long':answer['result']['uncertainty']='word '*121
    elif variant=='keyword':answer['result']['rationale']='No password is included'
    elif variant=='null':answer['result']=None
    elif variant=='binding':answer['binding_hash']='run-wrong'
    elif variant=='unknown_citation':answer['result']['citations']=[{'evidence_id':'unknown','claim':'title'}]
    elif variant=='undisclosed_claim':answer['result']['citations']=[{'evidence_id':evidence_alias(grant['run'],'invented-evidence'),'claim':'title'}]
    elif variant=='candidate_status':answer['result']['candidate']={'imdb':'tt1234567','tmdb':123}
    elif variant=='unsupported_candidate':answer['result'].update(status='supported_candidate',candidate={'imdb':'tt1234567','tmdb':123})
    elif variant=='empty_alternative':answer['result']['alternatives']=[{'candidate':{'imdb':'tt1234567','tmdb':123},'citations':[]}]
    value['output'][-1]['content'][0]['text']=encoded(answer).decode()
    parsed,accounting=parse_response(encoded(value),output_schema(),expected_model=INTEGRATION_MODEL)
    receipt=dict(type='bound_send_receipt',request_sha256=digest(grant['request']),accounting=accounting)
    history=SimpleNamespace(read=lambda:[{'type':'bound_send_reserved'},{'type':'bound_send_attempted'},receipt])
    return grant,decode(parsed),history

CASES={'slash':('unsafe_text','historical_result_validation'),'long':('unsafe_text','historical_result_validation'),
       'keyword':('unsafe_text','historical_result_validation'),'null':('pilot_one_generation_required','historical_alias_validation'),
       'binding':('pilot_run_alias_changed','historical_alias_validation'),'unknown_citation':('pilot_citation_alias_unknown','historical_alias_validation'),
       'undisclosed_claim':('pilot_citation_claim_not_disclosed','historical_alias_validation'),
       'candidate_status':('candidate_status','historical_result_validation'),
       'unsupported_candidate':('candidate_evidence_missing','historical_result_validation'),
       'empty_alternative':('alternative_evidence_missing','historical_result_validation')}

class ReportContractTests(unittest.TestCase):
    def test_schema_valid_variations_remain_refused_with_static_reason_and_stage(self):
        for variant,(reason,phase)in CASES.items():
            grant,answer,history=specimen(variant)
            with self.subTest(variant=variant),diagnostic_scope():
                with self.assertRaises(Refusal)as caught:historical.report(grant,answer,history)
                self.assertEqual(str(caught.exception),reason)
                self.assertEqual(command.safe_reason(caught.exception),reason)
                self.assertEqual(diagnostic_phase(),phase)
                self.assertEqual(history.read()[-1]['type'],'bound_send_receipt')
    def test_valid_report_preserves_receipt_without_inventing_retained_answer(self):
        grant,answer,history=specimen('valid')
        with diagnostic_scope():
            result=historical.report(grant,answer,history)
            self.assertEqual(diagnostic_phase(),'historical_report_preparation')
        self.assertEqual(result['result'],answer['result']);self.assertEqual(result['receipt'],history.read()[-1])
        self.assertNotIn('answer',result['receipt']);self.assertNotIn('body',result['receipt'])
    def test_versioned_schema_rejects_lookup_null_alias_candidate_and_citations(self):
        from ai_movie_investigator.responses_protocol import schema_value
        _,schema=historical.final_contract('invented-report-run')
        for variant in ('null','binding','unknown_citation','undisclosed_claim','candidate_status','unsupported_candidate','empty_alternative'):
            _,answer,_=specimen(variant)
            with self.subTest(variant=variant),self.assertRaisesRegex(Refusal,'responses_answer_schema'):schema_value(answer,schema)
        _,answer,_=specimen('valid');schema_value(answer,schema)
        answer['kind']='lookup'
        with self.assertRaisesRegex(Refusal,'responses_answer_schema'):schema_value(answer,schema)
        # No acceptance claim for strings: unchanged local text policy still applies.
        _,answer,_=specimen('slash');schema_value(answer,schema)

    def test_unknown_exception_or_refusal_never_echoes_arbitrary_text(self):
        class Derived(Refusal):pass
        for error in (Refusal('PRIVATE_REMOTE_TEXT'),ValueError('PRIVATE_REMOTE_TEXT'),Derived('pilot_one_generation_required')):
            self.assertEqual(command.safe_reason(error),'unexpected_exception')
            self.assertNotIn('PRIVATE_REMOTE_TEXT',repr(command.safe_diagnostic(error)))

class GenericParserTests(unittest.TestCase):
    def test_custom_parent_cannot_select_a_non_generic_response_schema(self):
        import dataclasses
        import test_bound_integration as fixtures
        from ai_movie_investigator.bound_send import _send_bound
        from ai_movie_investigator.responses_replay import simulated_response
        f=fixtures.BoundIntegrationTest('test_connected_path_only_replaces_http_io');f.setUp();self.addCleanup(f.doCleanups)
        request=decode(f.body);request['text']['format']['schema']['properties']['kind']['enum']=['final']
        body=encoded(request);f.parent.expected=body
        answer=dict(binding_hash=aliases('fixture'),kind='final',lookups=[],result=dict(status='unresolved',candidate=None,alternatives=[],citations=[],rationale='Fixture',uncertainty='Unknown',next_action='human_review'))
        response=simulated_response(answer,1);value=decode(response.body);value['text']['format']['schema']=request['text']['format']['schema']
        response=dataclasses.replace(response,body=encoded(value))
        with patch('socket.socket',side_effect=AssertionError('network')),patch('ai_movie_investigator.responses_http.FixedResponsesHTTP.post',return_value=response),self.assertRaisesRegex(Refusal,'responses_contract_changed'):
            _send_bound(f.history,body,run='fixture',case=f.parent.case,parent=f.parent,credential=None,context_sha256=f.parent.context)
        self.assertEqual(len(f.history.read()),2)

if __name__=='__main__':unittest.main()
