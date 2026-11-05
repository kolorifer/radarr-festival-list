"""Invented complete SDK-shaped envelopes; no provider or account requests."""
import copy
import json
import unittest
from ai_movie_investigator.contracts import Refusal, encoded
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.responses_protocol import parse_response, MODEL, INTEGRATION_MODEL
import test_supervised_envelope as framing
import test_supervised_credit as fixtures
import test_supervised_cli as executable

# Independent of the older minimal simulated_response builder. Fields transcribed
# from official openai-python Responses types observed 2026-11-05; all values invented.
FIXTURE_CODE = '''
def documented(model='gpt-5-nano-2025-08-07'):
    from ai_movie_investigator.contracts import encoded
    from ai_movie_investigator.controller import output_schema
    from ai_movie_investigator.disclosure import aliases
    answer={'binding_hash':aliases('synthetic-integration-1'),'kind':'final','lookups':[],
            'result':{'status':'unresolved','candidate':None,'alternatives':[], 'citations':[],
                      'rationale':'Synthetic only','uncertainty':'No real evidence','next_action':'human_review'}}
    return {'id':'resp_DOCUMENTED','object':'response','created_at':1793900000,'completed_at':1793900001,
        'status':'completed','model':model,'error':None,'incomplete_details':None,
        'store':False,'background':False,'tools':[],'tool_choice':'none','parallel_tool_calls':True,
        'max_output_tokens':4096,'max_tool_calls':None,'instructions':'Synthetic fixture',
        'metadata':{},'temperature':1,'top_p':1,'top_logprobs':0,'truncation':'disabled',
        'conversation':None,'previous_response_id':None,'prompt':None,'image':None,
        'moderation':None,'access_programs':None,'safety_identifier':None,'user':None,
        'service_tier':'default','prompt_cache_options':None if model.startswith('gpt-5-nano') else
            {'ttl':'30m','mode':'implicit','comparison_response_id':None},
        'prompt_cache_key':None,'prompt_cache_retention':'in_memory' if model.startswith('gpt-5-nano') else None,'prompt_cache_diagnostics':None,
        'reasoning':{'effort':'medium','summary':None},
        'text':{'verbosity':'medium','format':{'type':'json_schema','name':'retained_investigator_v1',
            'schema':output_schema(),'strict':True,'description':None}},
        'output':[{'id':'rs_DOCUMENTED','type':'reasoning','summary':[],'content':None,'status':'completed',
                   'encrypted_content':'OPAQUE_FIXTURE_NOT_RETAINED'},
                  {'id':'msg_DOCUMENTED','type':'message','role':'assistant','status':'completed','phase':'final_answer',
                   'content':[{'type':'output_text','text':encoded(answer).decode(),'annotations':[],'logprobs':[]}]}],
        'usage':{'input_tokens':1200,'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':0,
                 'cache_write_tokens_details':None},'output_tokens':300,
                 'output_tokens_details':{'reasoning_tokens':50},'total_tokens':1500},
        'tool_usage':{'web_search':{'num_requests':0},'image_gen':{'input_tokens':0,'output_tokens':0,
             'total_tokens':0,'input_tokens_details':{'image_tokens':0,'text_tokens':0},
             'cached_tokens':None,'cached_tokens_details':None,'output_tokens_details':None}}}
'''
exec(FIXTURE_CODE)

class CompatibilityTests(unittest.TestCase):
    def parse(self, value):
        return parse_response(encoded(value), output_schema(), 'req_FIXTURE', expected_model=value['model'])

    def test_complete_documented_envelopes_project_only_answer_and_accounting(self):
        for model in (MODEL, INTEGRATION_MODEL):
            v=documented(model); a,b=self.parse(v)
            self.assertEqual(json.loads(a)['result']['status'],'unresolved')
            self.assertNotIn(b'OPAQUE_FIXTURE',encoded(b))
            self.assertEqual(set(b),{'response_id','model','usage','policy','request_id'})
            if model==INTEGRATION_MODEL:self.assertEqual(b['usage']['input_tokens_details'],{'cached_tokens':0})
            else:self.assertEqual(b['usage']['input_tokens_details']['cache_write_tokens_details'],{'ttl_30m_tokens':0,'ttl_12h_tokens':0})

    def test_additive_metadata_is_discarded_not_used_as_answer(self):
        v=documented(); expected=self.parse(v)
        v.update(image={'context_compression':'disabled'},future_metadata={'command':'DO_NOT_EXECUTE'},
                 output_text='DIFFERENT AGGREGATE NEVER USED')
        v['text']['format']['description']='Documentation only'
        v['output'][1]['phase']=None
        self.assertEqual(self.parse(v),expected)

    def test_safety_rejections_are_preserved_with_complete_envelope(self):
        cases=[('store',True),('background',True),('model','other'),('status','incomplete'),
               ('error',{'message':'PRIVATE'}),('incomplete_details',{}),('tools',[{'type':'web_search'}]),
               ('tool_choice','auto'),('service_tier','flex'),('conversation',{'id':'conv_OTHER'}),
               ('previous_response_id','resp_OTHER'),('prompt',{}),('prompt_cache_retention','24h'),
               ('prompt_cache_key','PRIVATE'),('max_output_tokens',4097)]
        for key,val in cases:
            v=documented();v[key]=val
            with self.subTest(key=key),self.assertRaises(Refusal) as e:self.parse(v)
            self.assertNotIn('PRIVATE',str(e.exception))
        for kind in ('function_call','web_search_call','mcp_call','computer_call','shell_call','image_generation_call','unknown_action'):
            v=documented();v['output'].append({'type':kind})
            with self.subTest(kind=kind),self.assertRaisesRegex(Refusal,'responses_action_or_output_denied'):self.parse(v)
        for phase in ('commentary','unknown'):
            v=documented();v['output'][1]['phase']=phase
            with self.assertRaisesRegex(Refusal,'responses_action_or_output_denied'):self.parse(v)
        for strict in (False,1,None):
            v=documented();v['text']['format']['strict']=strict
            with self.assertRaisesRegex(Refusal,'responses_contract_changed'):self.parse(v)

    def test_nonzero_unknown_and_malformed_tool_counters_refused(self):
        for value in ({'unknown':{}},{'web_search':{'num_requests':1}},{'web_search':{'num_requests':False}},
                      {'web_search':None}, {'image_gen':{}}, {'image_gen':dict(documented()['tool_usage']['image_gen'],cached_tokens=1)}):
            v=documented();v['tool_usage']=value
            with self.subTest(value=value),self.assertRaisesRegex(Refusal,'responses_tool_usage_denied'):self.parse(v)

    def test_cache_usage_normalizes_only_explicit_zero_and_preserves_partitions(self):
        for model in (MODEL,INTEGRATION_MODEL):
            for partition in ('absent',None,{'ttl_30m_tokens':0,'ttl_12h_tokens':0}):
                v=documented(model);d=v['usage']['input_tokens_details'];d['cache_write_tokens_details']=partition
                if partition=='absent':del d['cache_write_tokens_details']
                self.parse(v)
            for writes,partition in [(1,None),(False,None),(0,{}),(0,{'ttl_30m_tokens':False,'ttl_12h_tokens':0}),(1,{'ttl_30m_tokens':0,'ttl_12h_tokens':1})]:
                v=documented(model);v['usage']['input_tokens_details'].update(cache_write_tokens=writes,cache_write_tokens_details=partition)
                with self.assertRaises(Refusal):self.parse(v)
        v=documented(MODEL);v['usage']['input_tokens_details'].update(cache_write_tokens=1,cache_write_tokens_details={'ttl_30m_tokens':1,'ttl_12h_tokens':0});self.parse(v)
        v['prompt_cache_options']['mode']='explicit'
        with self.assertRaisesRegex(Refusal,'responses_cache_or_tier_changed'):self.parse(v)

    def test_complete_documented_envelope_through_actual_http_all_framings(self):
        helper=framing.EnvelopeTests();self.addCleanup(helper.doCleanups)
        for mode in ('length','missing','chunked'):
            with self.subTest(mode=mode):helper.exercise(encoded(documented()),mode)
        v=documented();v['tool_usage']['web_search']['num_requests']=1
        helper.exercise(encoded(v),reason='responses_tool_usage_denied')

    def test_explicit_synthetic_retention_and_unchanged_generic_policy(self):
        from ai_movie_investigator.credit_test import request
        selected=json.loads(request('synthetic-integration-1'))
        self.assertFalse(selected['store'])
        self.assertEqual(selected['prompt_cache_retention'],'in_memory')
        for model,policies in ((MODEL,('in_memory','24h')),(INTEGRATION_MODEL,(None,'24h','unknown'))):
            for policy in policies:
                v=documented(model);v['prompt_cache_retention']=policy
                with self.subTest(model=model,policy=policy),self.assertRaisesRegex(Refusal,'responses_cache_or_tier_changed'):
                    self.parse(v)
        v=documented();del v['prompt_cache_retention']
        with self.assertRaisesRegex(Refusal,'responses_cache_or_tier_changed'):self.parse(v)

    def test_genuine_installed_command_reaches_usage_validation(self):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart');f.setUp();self.addCleanup(f.doCleanups)
        extension=FIXTURE_CODE+"\nfrom ai_movie_investigator.contracts import encoded\nv=documented();v['usage']['total_tokens']=1\nselected_raw=encoded(v)\nframing='chunked'\n"+framing.wire_code()+"\nFixedResponsesHTTP.post=original_post\nwire_fixture('completed').__enter__()\n"
        executable.SupervisedExecutableTests().execute_fixture(f,1,hook_extension=extension,category='protocol_refused',expected_reason='responses_usage_invalid',expected_phase='response_parsing')
