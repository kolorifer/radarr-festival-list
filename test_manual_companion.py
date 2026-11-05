"""Synthetic companion tests; actual private retained evidence is never a fixture."""
import copy
import json
import unittest
from ai_movie_investigator.contracts import decode, digest, encoded, Refusal
from ai_movie_investigator.manual_offline import parse_packet
from ai_movie_investigator.manual_supervised import context, prepare, complete, constraints
from test_manual_expanded import envelope
from test_manual_supervised import SupervisedManualTest


def paired_input():
    e = decode(envelope())
    e['retained_case']['source_identity'].update(imdb=None, tmdb=None, asserted_tmdb=None)
    e['retained_case_sha256'] = digest(e['retained_case'])
    return encoded(e)


def companion():
    e = decode(paired_input());p=e['packet'];t=p['last_observed']
    r=dict(status='ok',case_id=p['case_id'],selection_version=p['version'],route='eligible',
        correlation='strong_source_id',reason=p['reason'],decision_history='incomplete_unknown',
        normalized_signature='source_side_match_only',captured_bytes='not_established',
        evidence_freshness='not_established',cross_store_atomic=False,intervening_changes='not_excluded',
        selection_event_digest='a'*64,event_uuid='00000000-0000-4000-8000-000000000001',
        outcome_delivery_rowid=7,review_cursor=7,historical_review_count=0,selection_reviews=[],observer_pending='absent',
        facts=dict(title=p['title'],title_status='available',source_year=p['year'],metadata_imdb=None,metadata_tmdb=None,
                   outcome_asserted_imdb=p['asserted_imdb'],outcome_asserted_tmdb=None,id_values_are_claims=True),
        event_observed_at=t,collector_observation_started_at=t+1,collector_observed_at=t+2,
        spool_observation_started_at=t+3,spool_observed_at=t+4,spool_observation_finished_at=t+5,
        collector_recheck_started_at=t+6,collector_rechecked_at=t+7)
    return dict(status='completed',case=p['case_id'],version=p['version'],source_file_size_bound=33554432,
                observer_journal_mode='delete',result=r)


class CompanionTests(unittest.TestCase):
    write=SupervisedManualTest.write
    submit=SupervisedManualTest.submit

    def setUp(self):
        SupervisedManualTest.setUp(self)
        self.out=self.root/'paired';self.out.mkdir(mode=0o700)
        self.write(self.input,paired_input());self.source=self.root/'source.json';self.write(self.source,encoded(companion()))
        self.selected=prepare(self.input,self.out,companion_path=self.source)
        self.data=decode((self.out/'model-input.json').read_bytes(),32768)

    def answer(self):
        a=SupervisedManualTest.answer(self)
        for key in ('observer_pending','collector_rechecked_at'):
            a['support'].append(dict(path='source_observation/'+key,value=encoded(self.data['source_observation'][key]).decode()))
        return a

    def test_actual_prepared_input_and_report_freeze_both_sources(self):
        self.assertEqual((self.out/'companion.json').read_bytes(),self.source.read_bytes())
        o=self.data['source_observation'];self.assertEqual(o['observer_pending'],'absent')
        self.assertFalse(o['underlying_movie_evidence_refreshed'])
        self.assertEqual(o['authenticity'],'external_operator_source_verification_required')
        self.assertTrue(all(r['expiry_status']=='expired' for r in self.data['historical_observations']['catalogue']))
        wire=(self.out/'request.json').read_text()
        for private in (companion()['case'],companion()['version'],companion()['result']['event_uuid'],companion()['result']['selection_event_digest']):self.assertNotIn(private,wire)
        report=self.submit(self.answer());self.assertEqual(report['source_observation'],o)
        self.assertEqual(report['selection']['companion_sha256'],self.selected['companion_sha256'])
        self.assertEqual(report['qualifications']['currentness'],'unknown')
        with self.assertRaisesRegex(Refusal,'completion_consumed'):self.submit(self.answer())

    def test_each_pairing_field_mismatch_refuses(self):
        raw=paired_input();p,sha=parse_packet(raw)
        for path,bad in [('case','other'),('version','b'*64),('result.case_id','other'),('result.selection_version','b'*64),
                         ('result.facts.title','Other'),('result.facts.source_year',2001),
                         ('result.facts.outcome_asserted_imdb','tt99999999'),('result.facts.metadata_tmdb',999),
                         ('result.event_observed_at',1),('result.collector_rechecked_at',99999999999)]:
            c=companion();target=c;keys=path.split('.')
            for k in keys[:-1]:target=target[k]
            target[keys[-1]]=bad
            with self.subTest(path=path),self.assertRaises(Refusal):context(p,sha,2000000000,companion=encoded(c),historical_raw=raw)

    def test_frozen_companion_tamper_and_unselected_addition_refuse(self):
        raw=(self.out/'companion.json').read_bytes();self.write(self.out/'companion.json',raw+b' ')
        with self.assertRaisesRegex(Refusal,'manual_prepared_changed'):self.submit(self.answer())
        self.assertFalse((self.out/'reply.json').exists())
        # A companion cannot be silently introduced into the legacy selection.
        self.out=self.root/'out';self.write(self.out/'companion.json',raw)
        with self.assertRaisesRegex(Refusal,'manual_unselected_companion'):self.submit(self.answer())

    def test_original_file_change_does_not_replace_frozen_bytes(self):
        self.write(self.source,b'{}')
        self.assertEqual(self.submit(self.answer())['source_observation']['observer_pending'],'absent')

    def test_missing_companion_citations_refuse_and_burn_completion(self):
        a=self.answer();a['support']=[s for s in a['support'] if not s['path'].startswith('source_observation/')]
        with self.assertRaisesRegex(Refusal,'manual_companion_citations_missing'):self.submit(a)
        with self.assertRaisesRegex(Refusal,'completion_consumed'):self.submit(self.answer())

    def test_companion_changes_request_and_assessment_binding(self):
        raw=paired_input();p,sha=parse_packet(raw);c=companion()
        a,_,_=context(p,sha,2000000000,companion=encoded(c),historical_raw=raw)
        c['result']['observer_pending']='present'
        b,_,_=context(p,sha,2000000000,companion=encoded(c),historical_raw=raw)
        self.assertNotEqual(a['assessment_id'],b['assessment_id']);self.assertNotEqual(a['request_sha256'],b['request_sha256'])
        self.assertEqual(a['input_sha256'],b['input_sha256'])

    def test_unknown_fields_partial_and_fake_authenticity_refuse(self):
        raw=paired_input();p,sha=parse_packet(raw)
        for modify in (lambda c:c.update(verified=True),lambda c:c['result'].update(status='partial'),
                       lambda c:c['result'].update(observer_pending='unknown'),lambda c:c['result'].update(cross_store_atomic=True)):
            c=companion();modify(c)
            with self.assertRaises(Refusal):context(p,sha,2000000000,companion=encoded(c),historical_raw=raw)

    def test_prior_reviews_keep_opaque_occurrence_and_no_current_approval(self):
        raw=paired_input();p,sha=parse_packet(raw);c=companion();r=c['result']
        review=dict(event='b'*64,delivery=3,reviewed=r['event_observed_at']-1,imdb='tt99999999',tmdb=9,year=1998)
        review['id']=digest([p['case_id'],review['event'],review['delivery']]);r.update(selection_reviews=[review],historical_review_count=1)
        _,request,data=context(p,sha,2000000000,companion=encoded(c),historical_raw=raw)
        self.assertNotIn(review['event'],request.decode());self.assertNotIn(review['id'],request.decode())
        projected=data['source_observation']['prior_reviews'][0]
        self.assertEqual(projected['occurrence'],'prior-occurrence-1');self.assertFalse(projected['selected_occurrence'])
        self.assertFalse(data['source_observation']['identity_approval'])
