"""Invented captured occurrence through framed simulation to qualified draft/outbox."""
import copy,io,json,socket,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from ai_movie_investigator.contracts import captured_outcome,encoded,decode,digest,Refusal
from ai_movie_investigator.history import History
from ai_movie_investigator.new_case import assess_offline,admitted,request_for,complete,offline_request
from ai_movie_investigator.responses_http import SimulatedHTTP,FixedResponsesHTTP,HTTPResult
from ai_movie_investigator.replay import synthetic_case,NOW,owner_decision
from ai_movie_investigator.draft_delivery import deliver
from identity_telegram_digest import Digest
from test_responses_compatibility import documented

class OfflinePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.now=NOW
        (self.root/'history').mkdir(mode=0o700)
        self.history=History(self.root/'history',clock=lambda:self.now)
        for target in ('socket.socket','socket.create_connection','socket.getaddrinfo'):
            p=patch(target,side_effect=AssertionError('independent network tripwire'));p.start();self.addCleanup(p.stop)
        raw,binding,evidence=synthetic_case(165)
        self.packet=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=binding,evidence=evidence,decisions=[],trusted_issuers=['synthetic_owner'])
        self.outbox=Digest(self.root/'outbox')

    def frame(self,*,bad=None):
        p=self.packet;r=request_for(p,admitted(p,p['binding'],self.now),self.now)
        value=documented();answer=decode(value['output'][-1]['content'][0]['text'])
        answer['binding_hash']=r['binding_hash']
        # Deterministic fixture only: never a manually supplied complete() result.
        if bad=='binding':answer['binding_hash']='0'*64
        if bad=='edition':
            answer['result'].update(status='supported_candidate',candidate={'imdb':'tt9000127','tmdb':9000127},citations=[{'evidence_id':'evidence-2','claim':'runtime'}])
        value['output'][-1]['content'][0]['text']=encoded(answer).decode()
        raw=encoded(value)
        if bad=='usage':value['usage']['total_tokens']=1;raw=encoded(value)
        payload=b''.join(('%x\r\n'%len(raw[i:i+137])).encode()+raw[i:i+137]+b'\r\n' for i in range(0,len(raw),137))+b'0\r\n\r\n'
        headers=b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nx-request-id: req_OFFLINE\r\n'
        if bad=='framing':headers+=b'Content-Length: 7\r\n'
        return headers+b'\r\n'+payload

    def run_case(self,http):return assess_offline(self.history,self.packet,self.packet['binding'],http,enabled=True)
    def restart(self):self.history=History(self.root/'history',clock=lambda:self.now);self.outbox=Digest(self.root/'outbox')
    def selected(self,report):return dict(job=report['job'],binding=report['binding'],report_hash=digest(report),draft_hash=digest(report['draft']))

    def test_executable_pipeline_receipt_minimization_and_delivery_restart(self):
        report=self.run_case(self.frame())
        req=next(e['request'] for e in self.history.read() if e['type']=='new_case_prepared')
        body=offline_request(req);wire=decode(body)
        self.assertEqual(wire['tools'],[]);self.assertEqual(wire['prompt_cache_retention'],'in_memory')
        for secret in (self.packet['binding']['case_id'],self.packet['event']['id'],self.packet['evidence'][0]['provenance']['digest']):self.assertNotIn(secret.encode(),body)
        self.assertEqual(report['assessment']['status'],'unresolved');self.assertFalse(report['generation_invoked'])
        self.assertTrue(report['simulated_transport_invoked']);self.assertIn('SIMULATED',report['draft']['text'])
        self.assertIn('edition and suitability',report['draft']['text'])
        receipt=next(e for e in self.history.read() if e['type']=='new_case_simulated_response')
        self.assertEqual(receipt['request_count'],1);self.assertEqual(receipt['wire_hash'],digest(wire));self.assertEqual(receipt['accounting']['request_id'],'req_OFFLINE')
        self.assertTrue(receipt['simulated']);self.assertFalse(receipt['provider_verified'])
        self.assertNotIn(b'OPAQUE_FIXTURE',encoded(self.history.read()))
        send=Mock(return_value=200);selection=self.selected(report)
        delivered=deliver(self.history,self.outbox,selection,send,enabled=True)
        self.assertTrue(delivered['receipt']['simulation']);self.assertFalse(delivered['receipt']['recipient_ingestion_verified'])
        self.restart();again=deliver(self.history,self.outbox,selection,send,enabled=True)
        self.assertFalse(again['attempted']);self.assertEqual(send.call_count,1)
        with self.assertRaises(Refusal):self.run_case(self.frame())

    def test_uncertain_assessment_cannot_restart_or_accept_supplied_answer(self):
        frame=b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 99\r\n\r\n{}'
        with self.assertRaises(Refusal):self.run_case(frame)
        self.restart()
        with self.assertRaises(Refusal):self.run_case(self.frame())
        req=next(e for e in self.history.read() if e['type']=='new_case_prepared')['request']
        answer=decode(documented()['output'][-1]['content'][0]['text']);answer['binding_hash']=req['binding_hash']
        with self.assertRaisesRegex(Refusal,'simulated_completion_unbound'):
            complete(self.history,digest(req),answer,{'mode':'simulation','chat_reference':'fabricated fallback'})
        self.assertFalse(any(e['type']=='new_case_completed' for e in self.history.read()))

    def test_uncertain_delivery_never_replays(self):
        report=self.run_case(self.frame());send=Mock(side_effect=TimeoutError())
        selection=self.selected(report);r=deliver(self.history,self.outbox,selection,send,enabled=True)
        self.assertEqual(r['receipt']['state'],'uncertain');self.restart()
        r=deliver(self.history,self.outbox,selection,send,enabled=True)
        self.assertFalse(r['attempted']);self.assertEqual(send.call_count,1)

    def test_frame_binding_usage_and_edition_refusals(self):
        for bad in ('framing','binding','usage','edition'):
            with self.subTest(bad=bad):
                path=self.root/bad;path.mkdir(mode=0o700);self.history=History(path,clock=lambda:self.now)
                frame=self.frame(bad=bad)
                with self.assertRaises(Refusal):self.run_case(frame)
                self.assertEqual(sum(e['type']=='new_case_simulated_send_started' for e in self.history.read()),1)
                with self.assertRaises(Refusal):self.run_case(frame)
                self.assertFalse(any(e['type']=='new_case_completed' for e in self.history.read()))

    def test_default_disabled_real_transport_and_decision_gates(self):
        http=SimulatedHTTP([])
        with self.assertRaises(Refusal):assess_offline(self.history,self.packet,self.packet['binding'],http)
        with self.assertRaisesRegex(Refusal,'offline_transport_required'):self.run_case(FixedResponsesHTTP())
        raw,binding,evidence=synthetic_case(165)
        self.packet=captured_outcome(encoded(raw),sources={'synthetic':'Synthetic Index'},binding=binding,evidence=evidence,
            decisions=[owner_decision(binding,'intentionally_skipped',evidence=evidence)],trusted_issuers=['synthetic_owner'])
        with self.assertRaisesRegex(Refusal,'occurrence_not_eligible'):self.run_case(b'invented frame')
        self.assertFalse(http.requests);self.assertEqual(self.history.read(),[])

    def test_prebuilt_uncorrelated_result_refuses(self):
        http=SimulatedHTTP([HTTPResult(200,encoded(documented()),'req_FAKE')])
        with self.assertRaisesRegex(Refusal,'offline_transport_required'):self.run_case(http)
        self.assertFalse(any(e['type']=='new_case_completed' for e in self.history.read()))

    def test_injected_transport_and_nonfixture_input_refuse_before_write(self):
        http=SimulatedHTTP([self.frame()]);callback=Mock(side_effect=AssertionError('callback forbidden'));http.post=callback
        with self.assertRaisesRegex(Refusal,'offline_transport_required'):self.run_case(http)
        callback.assert_not_called()
        self.packet['facts']['title']='Actual-looking movie'
        with self.assertRaisesRegex(Refusal,'offline_fixture_required'):self.run_case(b'frame')
        self.assertEqual(self.history.read(),[])

    def test_completion_in_prepare_gap_prevents_simulated_send(self):
        import ai_movie_investigator.new_case as module
        original=module.prepare
        def interleave(*a,**kw):
            req=original(*a,**kw);answer=decode(documented()['output'][-1]['content'][0]['text']);answer['binding_hash']=req['binding_hash']
            complete(self.history,digest(req),answer,{'mode':'simulation','chat_reference':'Race fixture'})
            return req
        with patch.object(module,'prepare',side_effect=interleave),patch.object(SimulatedHTTP,'post') as post:
            with self.assertRaisesRegex(Refusal,'completion_already_consumed'):self.run_case(self.frame())
        post.assert_not_called()
        self.assertFalse(any(e['type']=='new_case_simulated_send_started' for e in self.history.read()))

    def test_unrelated_append_before_intake_refuses_without_fixture_write(self):
        original=self.history.intake
        def interleave(*a,**kw):
            with self.history.transaction(write=True) as (_,append):append({'type':'unrelated_fixture_record'})
            return original(*a,**kw)
        with patch.object(self.history,'intake',side_effect=interleave),patch.object(SimulatedHTTP,'post') as post:
            with self.assertRaisesRegex(Refusal,'offline_history_not_empty'):self.run_case(self.frame())
        post.assert_not_called();self.assertEqual(self.history.read(),[{'type':'unrelated_fixture_record'}])

if __name__=='__main__':unittest.main()
