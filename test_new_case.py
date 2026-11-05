"""Connected synthetic new occurrences; no model, source or notification call."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_movie_investigator.contracts import Refusal, captured_outcome, digest, encoded
from ai_movie_investigator.history import History
from ai_movie_investigator.new_case import prepare, complete
from ai_movie_investigator.replay import NOW, synthetic_case, owner_decision


class NewCaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.now = NOW
        self.history = History(Path(self.tmp.name).resolve(), clock=lambda: self.now)
        self.net = patch('socket.socket', side_effect=AssertionError('network forbidden'))
        self.net.start(); self.addCleanup(self.net.stop)
        self.send = patch('identity_telegram_digest.Digest.tick', side_effect=AssertionError('send forbidden'))
        self.send.start(); self.addCleanup(self.send.stop)

    def packet(self, n=1, decision=None):
        raw, binding, evidence = synthetic_case(n)
        decisions = [owner_decision(binding, decision, evidence=evidence, chosen=decision == 'confirmed_identity')] if decision else []
        return captured_outcome(encoded(raw), sources={'synthetic': 'Synthetic Index'}, binding=binding,
            evidence=evidence, decisions=decisions, trusted_issuers=['synthetic_owner'])

    def answer(self, req, supported=True):
        return dict(binding_hash=req['binding_hash'], kind='final', lookups=[], result=dict(
            status='supported_candidate' if supported else 'unresolved',
            candidate={'imdb': 'tt9000127', 'tmdb': 9000127} if supported else None,
            alternatives=[], citations=[{'evidence_id': 'evidence-1', 'claim': 'crosswalk'},
                                      {'evidence_id': 'evidence-2', 'claim': 'source_identity'}] if supported else [],
            rationale='Synthetic retained source and catalogue assert the same candidate.',
            uncertainty='Source identity and edition still need independent review.', next_action='human_review'))

    def finish(self, req, answer=None):
        return complete(self.history, digest(req), answer or self.answer(req),
                        {'mode': 'simulation', 'chat_reference': 'Synthetic test; not actual assessment'})

    def test_two_new_occurrences_connected_to_existing_notification_format(self):
        hashes=[]
        for n in (41, 42):
            p=self.packet(n);r=prepare(self.history,p,p['binding']);report=self.finish(r)
            self.assertEqual(report['binding'], p['binding']); hashes.append(r['binding_hash'])
            self.assertEqual(report['assessment']['status'],'supported_candidate')
            self.assertTrue(report['draft']['text'].startswith('Movie identification update'))
            self.assertIn('Possible TMDb matches (unverified)',report['draft']['text'])
            self.assertIn('SIMULATED',report['draft']['text'])
            self.assertFalse(report['draft']['sent']);self.assertFalse(report['draft']['identity_approval'])
            self.assertFalse(report['generation_invoked'])
            self.assertNotIn('historical',r['kind'])
        self.assertNotEqual(*hashes)

    def test_minimization_retains_facts_and_qualifies_source_claims(self):
        p=self.packet();r=prepare(self.history,p,p['binding']);body=encoded(r).decode()
        for value in (p['binding']['case_id'],p['binding']['version'],p['event']['id'],p['evidence'][0]['provenance']['digest']):
            self.assertNotIn(value,body)
        self.assertEqual(r['input']['facts']['title'],'[local reference] Harbor')
        self.assertNotIn('runtime',r['input']['evidence'][1]['claims'])
        self.assertEqual(r['input']['qualifications']['novelty'],'unknown')

    def test_missing_ids_and_evidence_can_produce_honest_unresolved_draft(self):
        p=self.packet();p['facts']['imdb']=None;p['facts']['tmdb']=None;p['evidence']=[]
        r=prepare(self.history,p,p['binding']);report=self.finish(r,self.answer(r,False))
        self.assertEqual(report['qualifications']['catalogue_evidence'],'missing')
        self.assertIn('catalogue missing; source missing',report['draft']['text'])
        self.assertIsNone(report['assessment']['candidate'])

    def test_original_route_and_prior_decision_gates(self):
        for decision in ('completed_occurrence','intentionally_skipped'):
            p=self.packet(decision=decision)
            with self.assertRaisesRegex(Refusal,'occurrence_not_eligible'):prepare(self.history,p,p['binding'])
        for route in ('review_only','unmatched','verified','routine','quarantine','retry_later'):
            p=self.packet();p['facts']['route']=route
            with self.assertRaisesRegex(Refusal,'original_route_not_eligible'):prepare(self.history,p,p['binding'])
        self.assertEqual(self.history.read(),[])

    def test_old_occurrence_decision_does_not_transfer(self):
        p=self.packet(decision='completed_occurrence');p['decisions'][0]['scope']['occurrence']['delivery_id']=99
        r=prepare(self.history,p,p['binding'])
        self.assertEqual(r['input']['decisions'][0]['applicability'],'scope_changed_or_unbound')
        self.finish(r)

    def test_exact_selection_and_captured_bytes_required(self):
        p=self.packet();selection=copy.deepcopy(p['binding']);selection['occurrence']['delivery_id']+=1
        with self.assertRaisesRegex(Refusal,'selected_occurrence_changed'):prepare(self.history,p,selection)
        p['hash_basis']='canonical_json_object'
        with self.assertRaisesRegex(Refusal,'captured_occurrence_required'):prepare(self.history,p,p['binding'])

    def test_stale_evidence_not_current_candidate_and_no_retry(self):
        p=self.packet();p['evidence'][0]['expires_at']=NOW-1
        r=prepare(self.history,p,p['binding']);self.assertEqual(r['input']['qualifications']['stale_evidence'],['evidence-1'])
        with self.assertRaisesRegex(Refusal,'stale_candidate_support'):self.finish(r)
        with self.assertRaisesRegex(Refusal,'completion_already_consumed'):self.finish(r,self.answer(r,False))

    def test_cross_occurrence_and_future_evidence_withheld(self):
        p=self.packet();p['evidence'][0]['scope']['occurrence']['delivery_id']=999
        p['evidence'][1]['observed_at']=NOW+10
        r=prepare(self.history,p,p['binding'])
        self.assertEqual(r['input']['evidence'],[]);self.assertEqual(r['input']['qualifications']['withheld_evidence'],2)
        with self.assertRaisesRegex(Refusal,'unsupported_citation'):self.finish(r)

    def test_expired_while_chat_pending_refuses_current_candidate(self):
        p=self.packet();p['evidence'][0]['expires_at']=NOW+5
        r=prepare(self.history,p,p['binding']);self.now+=6
        with self.assertRaisesRegex(Refusal,'stale_candidate_support'):self.finish(r)

    def test_superseded_input_and_redelivery_cannot_replay(self):
        p=self.packet();r=prepare(self.history,p,p['binding'])
        with self.assertRaisesRegex(Refusal,'assessment_already_consumed'):prepare(self.history,p,p['binding'])
        p['evidence'][0]['text']='Changed retained catalogue evidence.';self.history.intake(p)
        with self.assertRaisesRegex(Refusal,'selected_case_superseded'):self.finish(r)

    def test_cross_workflow_reservation(self):
        p=self.packet();r=prepare(self.history,p,p['binding'])
        with self.assertRaisesRegex(Refusal,'supervised_handoff_already_consumed'):
            self.history.start(digest(p),'different',{})
        self.finish(r)
        with self.assertRaisesRegex(Refusal,'completion_already_consumed'):self.finish(r)

    def test_reply_binding_and_invented_claim_rejected(self):
        p=self.packet();r=prepare(self.history,p,p['binding']);a=self.answer(r)
        a['binding_hash']='0'*64
        with self.assertRaisesRegex(Refusal,'reply_handoff_binding'):self.finish(r,a)

    def test_conflicting_ids_stay_unresolved(self):
        p=self.packet();p['facts']['tmdb']=12345;p['facts']['outcome']['asserted_tmdb']=9000127
        r=prepare(self.history,p,p['binding'])
        report=self.finish(r,self.answer(r,False))
        self.assertIn('Conflicting IDs: present; unresolved',report['draft']['text'])

    def test_untyped_runtime_citation_rejected(self):
        p=self.packet();r=prepare(self.history,p,p['binding']);a=self.answer(r)
        a['result']['citations'][1]['claim']='runtime'
        with self.assertRaisesRegex(Refusal,'unsupported_claim'):self.finish(r,a)

    def test_declared_research_requires_existing_receipts(self):
        p=self.packet();p['evidence'][0]['id']='research-unsupported'
        with self.assertRaisesRegex(Refusal,'research_dependency_missing'):prepare(self.history,p,p['binding'])

    def test_operational_identifiers_in_free_text_are_redacted(self):
        p=self.packet(145)
        identifiers=[p['event']['id'],'145',p['binding']['source']]
        p['evidence'][0]['text']='References: ' + ' '.join(identifiers)
        r=prepare(self.history,p,p['binding'])
        body=encoded(r).decode()
        for ident in identifiers:self.assertNotIn(ident,body)
        self.assertIn('[local reference]',r['input']['evidence'][0]['text'])

    def test_no_evidence_draft_does_not_claim_evidence_ready(self):
        p=self.packet();p['evidence']=[];p['facts']['outcome']['reason']='listing_id_missing'
        r=prepare(self.history,p,p['binding']);report=self.finish(r,self.answer(r,False))
        self.assertNotIn('Evidence is ready',report['draft']['text'])
        self.assertIn('catalogue missing; source missing',report['draft']['text'])

    def test_refused_research_replacement_does_not_supersede_valid_handoff(self):
        p=self.packet();r=prepare(self.history,p,p['binding'])
        p['evidence'][0]['id']='research-unsupported'
        with self.assertRaisesRegex(Refusal,'research_dependency_missing'):prepare(self.history,p,p['binding'])
        self.assertEqual(sum(e['type']=='intake' for e in self.history.read()),1)
        self.finish(r)

    def test_embedded_event_uuid_cannot_escape_redaction(self):
        p=self.packet(145);event=p['event']['id']
        p['evidence'][0]['text']='ReferenceX'+event+'Z'
        r=prepare(self.history,p,p['binding'])
        self.assertNotIn(event,encoded(r).decode())
        a=self.answer(r);a['result']['rationale']='Reference '+event
        report=self.finish(r,a)
        self.assertNotIn(event,report['draft']['text'])
        self.assertIn('[local reference]',report['draft']['text'])

    def test_cli_pipe_handoff_requires_no_manual_artifact_files(self):
        import subprocess,sys,json
        p=self.packet(145)
        def call(op,obj):
            result=subprocess.run([sys.executable,'-m','ai_movie_investigator.new_case',op,
                '--history-dir',str(Path(self.tmp.name).resolve())],input=encoded(obj),capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        r=call('prepare',{'packet':p,'selection':p['binding']})
        report=call('complete',{'request_hash':digest(r),'answer':self.answer(r,False),
                              'provenance':{'mode':'simulation','chat_reference':'CLI synthetic test'}})
        self.assertFalse(report['draft']['sent'])
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())),1)
