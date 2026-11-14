import copy
import unittest
from pathlib import Path
from ai_movie_investigator import snapshot_review as s
from ai_movie_investigator.contracts import encoded
from ai_movie_investigator.disclosure import aliases, evidence_alias
from ai_movie_investigator.responses_protocol import schema_value
from test_snapshot_review import fixture, CASE, VERSION, NOW


class FilmScopeTests(unittest.TestCase):
    def setUp(self):
        snap, source, catalogue, attestation = fixture()
        self.p = s.projection(snap, attestation['snapshot_sha256'], CASE, VERSION,
                              source, catalogue, attestation, now=NOW)
        self.prepared = s.build_film_scope(self.p)
        run = self.prepared['run']
        refs = [evidence_alias(run, 'source'), evidence_alias(run, 'catalogue')]
        def finding(aspect, disposition, source_field, catalogue_field, explanation):
            return dict(aspect=aspect, disposition=disposition, source_field=source_field,
                        catalogue_field=catalogue_field, explanation=explanation, evidence=refs[:])
        self.answer = dict(binding_hash=aliases(run), kind='final', lookups=[], result=dict(
            status='supported_candidate', candidate=self.p['citation_eligible_pair'], alternatives=[],
            citations=[dict(evidence_id=refs[0], claim='source_identity'),
                       dict(evidence_id=refs[1], claim='crosswalk')],
            rationale='The film details support the same underlying film.',
            uncertainty='Physical edition and current queue are unknown.', next_action='human_review'),
            film_findings=[finding('title','supports','title','title','The titles match.'),
                finding('year','supports','year','festival_years','The listing year matches the festival year.'),
                finding('people','supports','cast','cast','An actor matches.'),
                finding('runtime_description','conflicts','description_runtime_minutes','runtime_minutes',
                        'Listing and catalogue durations differ.'),
                finding('runtime_nfo','reconciled','nfo_runtime_milliseconds','runtime_minutes','The uploader video duration differs.'),
                finding('ids','supports','imdb','imdb','The listed identifiers match.')], film_blockers=[])

    def test_supported_film_does_not_require_edition_or_queue(self):
        schema_value(self.answer, self.prepared['request']['text']['format']['schema'])
        result = s.validate_film_scope(self.p, self.prepared, self.answer, now=NOW)
        self.assertEqual(result['status'], 'supported_candidate')
        self.assertEqual(result['film_findings'][1]['catalogue_field'], 'festival_years')

    def test_unresolved_requires_film_blocker(self):
        answer = copy.deepcopy(self.answer)
        result = answer['result']
        result.update(status='unresolved', candidate=None, citations=[])
        answer['film_findings'][0].update(disposition='unknown', evidence=[evidence_alias(self.prepared['run'],'source')])
        answer['film_blockers'] = [dict(aspect='title',reason='ambiguous_film_evidence',evidence=[evidence_alias(self.prepared['run'],'source')])]
        self.assertEqual(s.validate_film_scope(self.p,self.prepared,answer,now=NOW)['status'],'unresolved')
        answer['film_blockers'] = []
        with self.assertRaises(ValueError): s.validate_film_scope(self.p,self.prepared,answer,now=NOW)

    def test_unsupported_field_and_stale_evidence_are_refused(self):
        answer = copy.deepcopy(self.answer)
        answer['film_findings'][1]['catalogue_field'] = 'theatrical_year'
        with self.assertRaises(ValueError): s.validate_film_scope(self.p,self.prepared,answer,now=NOW)
        with self.assertRaises(ValueError): s.validate_film_scope(self.p,self.prepared,self.answer,now=NOW+31)
        answer = copy.deepcopy(self.answer)
        answer['film_findings'][0]['evidence'] = ['unapproved']
        with self.assertRaises(ValueError): s.validate_film_scope(self.p,self.prepared,answer,now=NOW)

    def test_legacy_v3_bytes_unchanged(self):
        self.assertEqual(encoded(s.build(self.p)),Path('tests/fixtures/snapshot-v3-invented-build.json').read_bytes())

    def test_different_title_cannot_be_claimed_as_exact_reconciliation(self):
        p=copy.deepcopy(self.p);p['listing']['title']='A Different Invented Title'
        prep=s.build_film_scope(p);answer=copy.deepcopy(self.answer)
        answer['film_findings'][0]['disposition']='reconciled'
        with self.assertRaises(ValueError):s.validate_film_scope(p,prep,answer,now=NOW)

    def test_placeholders_and_subtitle_are_not_film_support(self):
        p=copy.deepcopy(self.p)
        p['listing']['cast']=['Unknown'];p['catalogue']['cast']=['Unknown']
        prep=s.build_film_scope(p)
        with self.assertRaises(ValueError):s.validate_film_scope(p,prep,self.answer,now=NOW)
        p=copy.deepcopy(self.p);p['listing']['nfo_runtime_kind']='subtitle'
        p['listing']['nfo_runtime_milliseconds']=p['catalogue']['runtime_minutes']*60000
        prep=s.build_film_scope(p);answer=copy.deepcopy(self.answer)
        answer['film_findings'][4]['disposition']='supports'
        with self.assertRaises(ValueError):s.validate_film_scope(p,prep,answer,now=NOW)

    def test_prior_id_conflict_cannot_be_supported(self):
        p=copy.deepcopy(self.p);p['conflicting_ids']=True;p['citation_eligible_pair']=None
        p['source_identifiers']['asserted_tmdb']=456
        prep=s.build_film_scope(p);answer=copy.deepcopy(self.answer)
        with self.assertRaises(ValueError):s.validate_film_scope(p,prep,answer,now=NOW)

    def test_collector_conflict_cites_collector_and_catalogue(self):
        p=copy.deepcopy(self.p);p['conflicting_ids']=True;p['citation_eligible_pair']=None
        p['source_identifiers']['asserted_tmdb']=456
        prep=s.build_film_scope(p);answer=copy.deepcopy(self.answer);result=answer['result']
        result.update(status='unresolved',candidate=None,citations=[])
        refs=[evidence_alias(prep['run'],'collector'),evidence_alias(prep['run'],'catalogue')]
        answer['film_findings'][-1].update(disposition='conflicts',source_field='asserted_tmdb',catalogue_field='tmdb',evidence=refs)
        answer['film_blockers']=[dict(aspect='ids',reason='conflicting_film_evidence',evidence=refs)]
        self.assertEqual(s.validate_film_scope(p,prep,answer,now=NOW)['film_findings'][-1]['evidence'],['collector','catalogue'])
        answer['film_findings'][-1]['evidence']=[evidence_alias(prep['run'],'source'),refs[1]]
        with self.assertRaises(ValueError):s.validate_film_scope(p,prep,answer,now=NOW)

    def test_v4_request_limit_is_explicit_and_legacy_remains_limited(self):
        from ai_movie_investigator.supervised_credit import request_value
        raw=encoded(self.prepared['request'])
        self.assertGreater(len(raw),8192)
        self.assertEqual(request_value(raw,film_scope=True),self.prepared['request'])
        with self.assertRaises(ValueError):request_value(raw)

    def test_false_conflicts_on_overlapping_evidence_are_refused(self):
        for index in (0,1,2):
            answer=copy.deepcopy(self.answer);answer['film_findings'][index]['disposition']='conflicts'
            with self.subTest(index=index),self.assertRaises(ValueError):
                s.validate_film_scope(self.p,self.prepared,answer,now=NOW)
        p=copy.deepcopy(self.p);p['listing']['nfo_runtime_milliseconds']=p['catalogue']['runtime_minutes']*60000
        answer=copy.deepcopy(self.answer);answer['film_findings'][4]['disposition']='conflicts'
        with self.assertRaises(ValueError):s.validate_film_scope(p,s.build_film_scope(p),answer,now=NOW)

    def test_supported_film_cannot_hide_substantive_title_conflict(self):
        p=copy.deepcopy(self.p);p['listing']['title']='Unrelated Invented Title'
        answer=copy.deepcopy(self.answer);answer['film_findings'][0]['disposition']='conflicts'
        with self.assertRaises(ValueError):s.validate_film_scope(p,s.build_film_scope(p),answer,now=NOW)
