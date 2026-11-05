"""Finite envelope/framing coverage with real HTTP/parser and invented sockets."""
import io,json,signal,unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator import supervised_authorization as authority
from ai_movie_investigator import responses_http as http
from ai_movie_investigator.contracts import Refusal,encoded
from ai_movie_investigator.controller import output_schema
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.responses_protocol import parse_response,INTEGRATION_MODEL
import test_supervised_credit as fixtures
import test_supervised_diagnostics as diagnostics
import test_supervised_cli as executable

# Reused inside the genuine installed-module process; all data is invented.
ENVELOPE_CODE='''
def envelope(*,target=None,opaque=20000,two=False,answer_size=None,change=None,unicode_opaque=False):
    import json
    from ai_movie_investigator.contracts import encoded
    from ai_movie_investigator.credit_test import request
    from ai_movie_investigator.disclosure import aliases
    from ai_movie_investigator.responses_replay import simulated_response
    from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL
    run='synthetic-integration-1'
    reply=dict(binding_hash=aliases(run),kind='final',lookups=[],result=dict(status='unresolved',candidate=None,alternatives=[],citations=[],rationale='',uncertainty='No real evidence',next_action='human_review'))
    if answer_size is not None:reply['result']['rationale']='A'*(answer_size-len(encoded(reply)))
    req=json.loads(request(run));v=json.loads(simulated_response(reply,1).body)
    v['model']=INTEGRATION_MODEL;v.pop('prompt_cache_options');v['prompt_cache_retention']='in_memory';v['usage']['input_tokens_details']={'cached_tokens':0}
    v['usage'].update(output_tokens=4096,total_tokens=5296)
    v.update(instructions=req['instructions'],created_at=1793900000,completed_at=1793900001,metadata={},parallel_tool_calls=True,reasoning={'effort':'medium','summary':None},temperature=1,top_p=1,truncation='disabled',previous_response_id=None)
    v['text']=req['text']
    v['output'][0]['encrypted_content']='OPAQUE_FIXTURE_'+('X'*opaque)
    if two:v['output'].insert(1,dict(v['output'][0],id='rs_SECOND'))
    if target is not None:
        v['output'][0]['encrypted_content']='OPAQUE_FIXTURE_'
        v['output'][0]['encrypted_content']+='X'*(target-len(encoded(v)))
    if unicode_opaque:v['output'][0]['encrypted_content']='é'*200000
    if change=='usage':v['usage']['total_tokens']=1
    if change=='incomplete':v.update(status='incomplete',incomplete_details={'reason':'max_output_tokens'})
    if change=='unknown':v['conversation']={'id':'conv_FIXTURE'}
    if change=='schema':v['output'][-1]['content'][0]['text']='{}'
    if change=='refusal':v['output'][-1]['content']=[{'type':'refusal','refusal':'FIXTURE'}]
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode() if unicode_opaque else encoded(v)
'''
exec(ENVELOPE_CODE)

def wire_code():
    code=diagnostics.WIRE_CODE.replace("raw=b'{' if variant=='malformed' else encoded(value)","raw=selected_raw")
    code=code.replace("response=('\\r\\n'.join(hs)+'\\r\\n\\r\\n').encode()+raw",'''
    payload=raw
    if framing=='missing':hs=[h for h in hs if not h.startswith('Content-Length:')]
    if framing=='chunked':
        hs=[h for h in hs if not h.startswith('Content-Length:')]+['Transfer-Encoding: chunked']
        payload=b''.join(('%x\\r\\n'%len(raw[i:i+4096])).encode()+raw[i:i+4096]+b'\\r\\n' for i in range(0,len(raw),4096))+b'0\\r\\n\\r\\n'
    if framing=='duplicate':hs.append('Content-Length: '+str(len(raw)))
    if framing=='invalid':hs[2]='Content-Length: not-a-number'
    if framing=='nonascii':hs[2]='Content-Length: '+chr(0xb2)
    if framing=='conflict':hs.append('Transfer-Encoding: chunked')
    if framing=='bad_transfer':hs=[h for h in hs if not h.startswith('Content-Length:')]+['Transfer-Encoding: gzip']
    if framing=='duplicate_transfer':hs=[h for h in hs if not h.startswith('Content-Length:')]+['Transfer-Encoding: chunked','Transfer-Encoding: chunked']
    if framing=='truncated':hs[2]='Content-Length: '+str(len(raw)+1)
    response=('\\r\\n'.join(hs)+'\\r\\n\\r\\n').encode('latin1')+payload
''')
    return code

def wire(raw,framing='length'):
    ns={'selected_raw':raw,'framing':framing}
    exec(wire_code(),ns)
    return ns['wire_fixture']('completed')

class EnvelopeTests(unittest.TestCase):
    def exercise(self,raw,framing='length',reason=None):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        f.setUp();self.addCleanup(f.doCleanups)
        output=io.StringIO()
        with diagnostics.DiagnosticTests().inputs(),wire(raw,framing),redirect_stdout(output):
            if reason:
                with self.assertRaisesRegex(Refusal,reason):command.run(f.state,f.selected,1)
            else:self.assertEqual(command.run(f.state,f.selected,1)['status'],'completed')
        self.assertEqual(output.getvalue().count('OFFLINE_AUTHORIZED_BOUNDARY'),1)
        self.assertEqual([e['reserved_usd'] for e in History(f.state/'credit').read()],[[3,100]])
        rows=History(f.state/'attempt-1').read()
        self.assertEqual(len(rows),2 if reason else 3)
        persisted=b''.join(p.read_bytes() for p in f.state.rglob(FILENAME))
        self.assertNotIn(b'OPAQUE_FIXTURE_',persisted);self.assertNotIn(b'X'*100,persisted)
        with patch('getpass.getpass') as prompt:
            with self.assertRaises(Refusal):command.run(f.state,f.selected,1)
        prompt.assert_not_called()
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM),signal.SIG_DFL)
        self.assertIsNone(authority._ACTIVE.get())

    def test_full_envelope_with_one_or_two_opaque_items(self):
        for two in (False,True):
            with self.subTest(two=two):self.exercise(envelope(opaque=40000,two=two))

    def test_exact_one_mib_all_framings(self):
        raw=envelope(target=1048576);self.assertEqual(len(raw),1048576)
        for framing in ('length','missing','chunked'):
            with self.subTest(framing=framing):self.exercise(raw,framing)

    def test_one_byte_over_all_framings(self):
        raw=envelope(target=1048577);self.assertEqual(len(raw),1048577)
        for framing in ('length','missing','chunked'):
            with self.subTest(framing=framing):self.exercise(raw,framing,'responses_declared_body_limit' if framing=='length' else 'responses_observed_body_limit')

    def test_canonical_parser_budget_cannot_expand_unicode_past_envelope(self):
        raw=envelope(unicode_opaque=True)
        self.assertLess(len(raw),1048576);self.assertGreater(len(encoded(json.loads(raw))),1048576)
        self.exercise(raw,reason='invalid_json')

    def test_framing_diagnostics_and_truncation(self):
        cases={'duplicate':'responses_length_duplicate','invalid':'responses_length_invalid','nonascii':'responses_length_invalid',
               'conflict':'responses_framing_conflict','bad_transfer':'responses_transfer_encoding_invalid',
               'duplicate_transfer':'responses_transfer_encoding_invalid','truncated':'responses_body_truncated'}
        for framing,reason in cases.items():
            with self.subTest(framing=framing):self.exercise(envelope(),framing,reason)

    def test_answer_and_protocol_guards_survive_wider_envelope(self):
        self.exercise(envelope(answer_size=8192));self.exercise(envelope(answer_size=8193),reason='size_limit')
        for change,reason in [('usage','responses_usage_invalid'),('incomplete','responses_not_completed'),('unknown','responses_context_changed'),('schema','responses_answer_schema'),('refusal','responses_text_required')]:
            with self.subTest(change=change):self.exercise(envelope(change=change),reason=reason)

    def test_model_name_or_fabricated_result_cannot_select_profile(self):
        raw=envelope(opaque=40000)
        fake=http.HTTPResult(200,raw,'req_FIXTURE','0'*64,'proj_fixture','/v1/responses')
        self.assertEqual(authority.response_limits(fake,raw,'req_FIXTURE',INTEGRATION_MODEL),(32768,16384))
        with self.assertRaisesRegex(Refusal,'size_limit'):parse_response(raw,output_schema(),'req_FIXTURE',expected_model=INTEGRATION_MODEL,http_result=fake)
        raw=envelope(opaque=17000)
        with self.assertRaisesRegex(Refusal,'responses_reasoning_shape'):parse_response(raw,output_schema(),'req_FIXTURE',expected_model=INTEGRATION_MODEL)


    def test_active_result_binding_rejects_swapped_body_model_or_identity(self):
        from ai_movie_investigator import bound_send
        original=bound_send.parse_response
        def checked(raw,schema,request_id=None,**kw):
            result=kw['http_result']
            self.assertEqual(authority.response_limits(result,raw,request_id,INTEGRATION_MODEL),(1048576,1048576))
            for changed in ((result,raw+b' ',request_id,INTEGRATION_MODEL),(result,raw,'req_OTHER',INTEGRATION_MODEL),(result,raw,request_id,'gpt-6.1-sol')):
                with self.assertRaisesRegex(Refusal,'supervised_observation_binding'):authority.response_limits(*changed)
            fake=http.HTTPResult(200,raw,result.request_id,result.request_sha256,result.project,result.path)
            self.assertEqual(authority.response_limits(fake,raw,request_id,INTEGRATION_MODEL),(32768,16384))
            return original(raw,schema,request_id,**kw)
        with patch.object(bound_send,'parse_response',checked):self.exercise(envelope(opaque=40000))

    def test_genuine_installed_command_full_large_envelope(self):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart');f.setUp();self.addCleanup(f.doCleanups)
        extension=ENVELOPE_CODE+"\nselected_raw=envelope(opaque=40000,two=True,change='incomplete')\nframing='chunked'\n"+wire_code()+"\nFixedResponsesHTTP.post=original_post\nwire_fixture('completed').__enter__()\n"
        executable.SupervisedExecutableTests().execute_fixture(f,1,hook_extension=extension,category='protocol_refused',expected_reason='responses_not_completed',expected_phase='response_parsing')
