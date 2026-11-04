"""Manual supplied replies, never generated or claimed as actual model output."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_movie_investigator.contracts import Refusal, decode, encoded
from ai_movie_investigator.manual_supervised import prepare, complete, constraints, validate_answer
from test_manual_expanded import envelope, no_id_envelope


@contextlib.contextmanager
def fixture_chain(path):
    # Unit fixture only; real private-chain behavior retains its separate tests.
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:yield fd
    finally:os.close(fd)


class SupervisedManualTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.out=self.root/'out';self.out.mkdir(mode=0o700)
        for module in ('manual_offline','manual_supervised'):
            for name,replacement in [('private_chain',fixture_chain),('safe_acl',lambda *a:'fixture')]:
                p=patch('ai_movie_investigator.'+module+'.'+name,replacement);p.start();self.addCleanup(p.stop)
        self.socket=patch('socket.socket',side_effect=AssertionError('network forbidden'));self.socket.start();self.addCleanup(self.socket.stop)
        self.input=self.root/'input.json';self.write(self.input,envelope())
        self.selected=prepare(self.input,self.out)
        self.data=decode((self.out/'model-input.json').read_bytes(),32768)

    def write(self,path,raw):
        path.write_bytes(raw);path.chmod(0o600)

    def answer(self):
        d=self.data['historical_observations']['catalogue']
        support=[('historical_observations/catalogue/0/data/movies',d[0]['data']['movies']),
                 ('historical_observations/catalogue/1/data/imdb','tt12345678'),
                 ('historical_observations/catalogue/1/data/id',12345),
                 ('historical_observations/catalogue/1/data/title','Example'),
                 ('historical_observations/catalogue/1/data/date','2026-03-14')]
        conflicts,missing=constraints(self.data)
        return dict(**{k:self.selected[k] for k in ('assessment_id','input_sha256','request_sha256')},
            kind='supervised_historical_assessment',status='historical_candidate_proposal',
            candidate=dict(imdb='tt12345678',tmdb=12345,title='Example',year=2026),
            support=[dict(path=p,value=encoded(v).decode()) for p,v in support],
            rationale='Fixture author proposes the dated catalogue match.',uncertainty='The physical file remains unverified.',
            contradictions=conflicts,missing_facts=missing,disposition='human_review_no_approval')

    def submit(self,answer):
        raw=encoded(answer);self.write(self.root/'reply.json',raw)
        provenance=dict(chat_id='00000000-0000-0000-0000-000000000000',source_reference='TEST supplied reply, not a model response',reply_sha256=hashlib.sha256(raw).hexdigest())
        self.write(self.root/'provenance.json',encoded(provenance))
        return complete(self.out,self.root/'reply.json',self.root/'provenance.json')

    def test_complete_retains_bound_reply_and_distinct_historical_result(self):
        answer=self.answer();report=self.submit(answer)
        self.assertEqual(report['assessment']['candidate'],dict(imdb='tt12345678',tmdb=12345,title='Example',year=2026))
        self.assertEqual(report['provenance_status'],'external_chat_verification_required')
        self.assertIsNone(report['software_generated_answer']);self.assertIsNone(report['simulation'])
        self.assertFalse(report['completion_invoked_generation']);self.assertFalse(report['identity_approval'])
        self.assertIsNone(report['provider_receipt']);self.assertIsNone(report['token_bill'])
        self.assertEqual((self.out/'reply.json').read_bytes(),encoded(answer))
        self.assertEqual(report,decode((self.out/'review-report.json').read_bytes(),65536))
        self.assertEqual((self.out/'review-report.json').stat().st_mode & 0o777,0o600)
        with self.assertRaisesRegex(Refusal,'completion_consumed'):self.submit(answer)

    def test_wrong_binding_rejects_and_preserves_original_then_blocks_changed_reply(self):
        a=self.answer();a['request_sha256']='0'*64
        with self.assertRaisesRegex(Refusal,'manual_reply_binding'):self.submit(a)
        self.assertEqual(decode((self.out/'reply.json').read_bytes()),a)
        self.assertFalse((self.out/'review-report.json').exists())
        with self.assertRaisesRegex(Refusal,'completion_consumed'):self.submit(self.answer())

    def test_each_input_selection_binding_and_invented_path_refuses(self):
        for key in ('assessment_id','input_sha256','request_sha256'):
            a=self.answer();a[key]='0'*64
            with self.subTest(key=key),self.assertRaisesRegex(Refusal,'manual_reply_binding'):
                validate_answer(a,self.selected,self.data)
        a=self.answer();a['support'][0]['path']='historical_observations/nonexistent'
        with self.assertRaisesRegex(Refusal,'manual_evidence_path'):
            validate_answer(a,self.selected,self.data)

    def test_unsupported_candidate_refuses(self):
        a=self.answer();a['candidate']['tmdb']=999
        with self.assertRaisesRegex(Refusal,'manual_candidate_unsupported'):self.submit(a)

    def test_invented_evidence_refuses(self):
        a=self.answer();a['support'][1]['value']='"tt99999999"'
        with self.assertRaisesRegex(Refusal,'manual_evidence_claim_mismatch'):self.submit(a)

    def test_missing_uncertainty_and_hidden_conflict_refuse(self):
        a=self.answer();a['contradictions']=[]
        with self.assertRaisesRegex(Refusal,'manual_qualifications_missing'):self.submit(a)

    def test_changed_prepared_request_refuses_before_completion(self):
        before=(self.out/'request.json').read_bytes();self.write(self.out/'request.json',before+b' ')
        with self.assertRaisesRegex(Refusal,'manual_prepared_changed'):self.submit(self.answer())
        self.assertFalse((self.out/'reply.json').exists())

    def test_malformed_reply_is_retained_and_consumes_completion(self):
        a=self.answer();del a['uncertainty']
        with self.assertRaises(Refusal):self.submit(a)
        self.assertEqual(decode((self.out/'reply.json').read_bytes()),a)
        with self.assertRaisesRegex(Refusal,'completion_consumed'):self.submit(self.answer())

    def test_current_candidate_status_is_not_a_manual_outcome(self):
        a=self.answer();a['status']='supported_candidate'
        with self.assertRaises(Refusal):self.submit(a)

    def test_changed_input_refuses_and_prepare_is_not_replayed(self):
        with self.assertRaisesRegex(Refusal,'manual_directory_consumed'):prepare(self.input,self.out)
        e=decode((self.out/'input.json').read_bytes(),65536);e['packet']['source_sha256']='0'*64
        self.write(self.out/'input.json',encoded(e))
        with self.assertRaisesRegex(Refusal,'manual_prepared_changed'):self.submit(self.answer())


    def test_no_ids_prepare_complete_unresolved_and_invented_candidate_refuses(self):
        self.out = self.root/'unknown'; self.out.mkdir(mode=0o700)
        self.write(self.input, no_id_envelope())
        self.selected = prepare(self.input, self.out)
        self.data = decode((self.out/'model-input.json').read_bytes(),32768)
        conflicts, missing = constraints(self.data)
        answer = dict(**{k:self.selected[k] for k in ('assessment_id','input_sha256','request_sha256')},
            kind='supervised_historical_assessment',status='unresolved',candidate=None,
            support=[dict(path='historical_observations/missing_observations',
                          value=encoded(self.data['historical_observations']['missing_observations']).decode())],
            rationale='SYNTHETIC supplied unresolved reply: identity and catalogue evidence were not observed.',
            uncertainty='No candidate identity is established.',contradictions=conflicts,missing_facts=missing,
            disposition='human_review_no_approval')
        invented = copy.deepcopy(answer)
        invented.update(status='historical_candidate_proposal',candidate=dict(imdb='tt12345678',tmdb=12345,title='Example',year=2026))
        with self.assertRaisesRegex(Refusal,'manual_crosswalk_missing'):
            validate_answer(invented,self.selected,self.data)
        report = self.submit(answer)
        self.assertIsNone(report['assessment']['candidate'])
        self.assertEqual(report['assessment']['status'],'unresolved')
        self.assertIn('asserted_imdb',report['assessment']['missing_facts'])
        self.assertIn('reported_candidate_tmdb',report['assessment']['missing_facts'])
        self.assertEqual(report['observations']['missing_observations']['movie_search'],'not_observed')
        self.assertIsNone(report['provider_receipt'])
