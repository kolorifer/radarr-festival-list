"""Fixed HTTP/framing/parser diagnostics using invented socket I/O only."""
import ast
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import contextmanager,redirect_stderr
from ai_movie_investigator import supervised_credit as command
from ai_movie_investigator.contracts import Refusal
from ai_movie_investigator.history import History,FILENAME
import test_supervised_credit as fixtures
import test_supervised_cli as executable

# Same finite wire fixture also runs inside the installed -m process.
WIRE_CODE=r'''
def wire_fixture(variant,run='synthetic-integration-1'):
    import io,socket,ssl,signal
    from contextlib import ExitStack
    from unittest.mock import patch
    from ai_movie_investigator.contracts import decode,encoded,Refusal
    from ai_movie_investigator.responses_protocol import INTEGRATION_MODEL
    from ai_movie_investigator.responses_replay import simulated_response
    from ai_movie_investigator.disclosure import aliases
    reply=dict(binding_hash=aliases(run),kind='final',lookups=[],result=dict(status='unresolved',candidate=None,alternatives=[],citations=[],rationale='Synthetic only',uncertainty='No real evidence',next_action='human_review'))
    value=decode(simulated_response(reply,1).body);value['model']=INTEGRATION_MODEL
    value.pop('prompt_cache_options');value['prompt_cache_retention']='in_memory';value['usage']['input_tokens_details']={'cached_tokens':0}
    if variant=='incomplete':value.update(status='incomplete',incomplete_details={'reason':'max_output_tokens'})
    if variant=='unsupported':value['conversation']={'id':'conv_FIXTURE'}
    if variant=='usage':value['usage']['total_tokens']=1
    if variant=='schema':value['output'][1]['content'][0]['text']='{}'
    raw=b'{' if variant=='malformed' else encoded(value)
    if variant=='large':raw=b'X'*1048577
    status=401 if variant=='rejected' else 200
    hs=['HTTP/1.1 '+str(status)+' Fixture','Content-Type: application/json','Content-Length: '+str(len(raw)+(1 if variant=='truncated' else 0)),'Connection: keep-alive' if variant in ('close_failure','close_success') else 'Connection: close']
    if variant!='missing_id':hs.append('x-request-id: req_FIXTURE')
    if variant=='shape':hs.append('Content-Encoding: gzip')
    response=('\r\n'.join(hs)+'\r\n\r\n').encode()+raw
    class OfflineSocket:
        def __init__(self,*a,**kw):pass
        def settimeout(self,value):pass
        def connect(self,address):assert address==('8.8.8.8',443)
        def getpeername(self):return ('8.8.8.8',443)
        def sendall(self,data):
            if data.startswith(b'POST '):
                assert data.startswith(b'POST /v1/responses HTTP/1.1\r\n')
                print('OFFLINE_AUTHORIZED_BOUNDARY',flush=True)
        def makefile(self,*a,**kw):return io.BytesIO(response)
        def close(self):
            if variant in ('close_failure','close_success'):raise OSError('PRIVATE_FIXTURE_SENTINEL')
    def wrap(context,sock,*,server_hostname):
        assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
        assert server_hostname=='api.openai.com' and type(sock) is OfflineSocket
        return sock
    stack=ExitStack()
    stack.enter_context(patch('socket.socket',OfflineSocket))
    stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('network forbidden')))
    stack.enter_context(patch('socket.getaddrinfo',return_value=[] if variant=='dns' else [(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',('8.8.8.8',443))]))
    stack.enter_context(patch.object(ssl.SSLContext,'wrap_socket',wrap))
    if variant=='timer':stack.enter_context(patch('signal.getitimer',return_value=(1.0,0.0)))
    if variant=='tls':stack.enter_context(patch('ssl.get_default_verify_paths',return_value=type('NoRoots',(),dict(openssl_cafile=None,openssl_capath=None))()))
    if variant=='close_failure':
        # Primary HTTP rejection must survive a secondary close exception.
        response=response.replace(b'HTTP/1.1 200 ',b'HTTP/1.1 401 ',1)
    return stack
'''
exec(WIRE_CODE)


class DiagnosticTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.SupervisedCreditTests('test_executable_generation_only_no_count_and_no_restart')
        f.setUp();self.addCleanup(f.doCleanups);return f

    @contextmanager
    def inputs(self):
        with patch.object(command.sys.stdin,'isatty',return_value=True),patch.object(command.sys.stderr,'isatty',return_value=True),patch('getpass.getpass',return_value='sk-SYNTHETIC_NOT_REAL'):
            yield

    def test_complete_fixed_http_and_parser_variants(self):
        variants={
            'incomplete':('response_parsing','responses_incomplete_max_output_tokens'),
            'unsupported':('response_parsing','responses_context_changed'),
            'usage':('response_parsing','responses_usage_invalid'),
            'schema':('response_parsing','responses_answer_schema'),
            'malformed':('response_parsing','invalid_json'),
            'missing_id':('receipt_validation','responses_identity_invalid'),
            'rejected':('http_response_received','responses_http_401'),
            'shape':('http_response_received','responses_http_shape'),
            'large':('http_response_received','responses_declared_body_limit'),
            'truncated':('http_body_read','responses_body_truncated'),
            'dns':('dns_lookup','responses_dns_failed'),
            'timer':('http_setup','responses_timer_busy'),
            'tls':('tls_setup','responses_tls_roots_unavailable'),
            'close_failure':('http_response_received','responses_http_401'),
            'close_success':('http_body_received','responses_cleanup_failed')}
        for variant,(phase,reason) in variants.items():
            with self.subTest(variant=variant):
                f=self.fixture()
                with self.inputs(),wire_fixture(variant):
                    with self.assertRaisesRegex(Refusal,reason):command.run(f.state,f.selected,1)
                terminal=History(f.state).read()[-1]
                self.assertEqual(terminal['type'],'supervised_diagnostic')
                self.assertEqual((terminal['phase'],terminal['reason']),(phase,reason))
                self.assertNotEqual(terminal['category'],'unclassified_refusal')
                self.assertEqual([r['reserved_usd'] for r in History(f.state/'credit').read()],[[3,100]])
                with patch('getpass.getpass') as prompt:
                    with self.assertRaises(Refusal):command.run(f.state,f.selected,1)
                prompt.assert_not_called()

    def test_cleanup_failure_is_local_even_inside_callers_exception_handler(self):
        f=self.fixture()
        try:raise RuntimeError('PRIVATE_CALLER_SENTINEL')
        except RuntimeError:
            with self.inputs(),wire_fixture('close_success'):
                with self.assertRaisesRegex(Refusal,'responses_cleanup_failed'):
                    command.run(f.state,f.selected,1)
        self.assertEqual(History(f.state).read()[-1]['reason'],'responses_cleanup_failed')

    def test_completed_response_records_receipt_without_failure_event(self):
        f=self.fixture()
        with self.inputs(),wire_fixture('completed'):
            self.assertEqual(command.run(f.state,f.selected,1)['status'],'completed')
        self.assertEqual(History(f.state/'attempt-1').read()[-1]['type'],'bound_send_receipt')
        self.assertEqual(History(f.state).read()[-1]['type'],'supervised_completed')
        self.assertFalse(any(e['type']=='supervised_diagnostic' for e in History(f.state).read()))

    def test_failed_diagnostic_write_keeps_primary_exception_and_consumed_slot(self):
        f=self.fixture();original=History.transaction
        @contextmanager
        def transaction(history,*a,**kw):
            with original(history,*a,**kw) as (events,append):
                def wrapped(event):
                    if event['type']=='supervised_diagnostic':raise OSError('PRIVATE_FIXTURE_SENTINEL')
                    return append(event)
                yield events,wrapped
        with self.inputs(),wire_fixture('incomplete'),patch.object(History,'transaction',transaction):
            with self.assertRaisesRegex(Refusal,'responses_incomplete_max_output_tokens'):command.run(f.state,f.selected,1)
        self.assertEqual(History(f.state).read()[-1]['type'],'supervised_started')
        self.assertEqual(len(History(f.state/'credit').read()),1)
        with self.assertRaises(Refusal):command.run(f.state,f.selected,1)

    def test_finite_reason_coverage_and_unknown_exception_no_leak(self):
        root=Path(command.__file__).parent
        for module in ('responses_http','responses_protocol','bound_send','supervised_authorization','responses_transport','contracts','spending','credit_test','supervised_credit','history','private_files','snapshot_review','snapshot_authorization','snapshot_private_report'):
            for node in ast.walk(ast.parse((root/(module+'.py')).read_text())):
                if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name):continue
                index=1 if node.func.id=='require' else 0 if node.func.id=='Refusal' else None
                if index is None or len(node.args)<=index:continue
                reason=node.args[index]
                if isinstance(reason,ast.Constant) and isinstance(reason.value,str):
                    self.assertEqual(command.safe_reason(Refusal(reason.value)),reason.value)
                    self.assertNotEqual(command.refusal_category(Refusal(reason.value)),'unclassified_refusal')
        for error in (RuntimeError('PRIVATE_FIXTURE_SENTINEL'),Refusal('PRIVATE_FIXTURE_SENTINEL'),Refusal('responses_incomplete_max_output_tokens','PRIVATE_FIXTURE_SENTINEL')):
            self.assertEqual(command.safe_reason(error),'unexpected_exception')
            self.assertNotIn('PRIVATE_FIXTURE_SENTINEL',str(command.safe_diagnostic(error)))

    def test_installed_module_full_http_parser_has_safe_reason_and_phase(self):
        f=self.fixture()
        extension=WIRE_CODE+"\nFixedResponsesHTTP.post=original_post\nwire_fixture('incomplete').__enter__()\n"
        executable.SupervisedExecutableTests().execute_fixture(f,1,hook_extension=extension,
            category='protocol_refused',expected_reason='responses_incomplete_max_output_tokens',expected_phase='response_parsing')

    def test_installed_module_unknown_exception_does_not_echo(self):
        f=self.fixture()
        executable.SupervisedExecutableTests().execute_fixture(f,1,category='unclassified_refusal',
            hook_extension="\ndef unknown(self,*a,**kw):raise RuntimeError('PRIVATE_FIXTURE_SENTINEL')\nFixedResponsesHTTP.post=unknown\n",
            expected_reason='unexpected_exception',expected_phase='wire_authorization',expect_boundary=False)
