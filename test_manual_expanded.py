"""Offline source-to-request regression; no private source fixture or live I/O."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator.contracts import decode, digest, encoded, Refusal
from ai_movie_investigator.manual_offline import parse_packet, build_request, rehearse
from ai_movie_investigator.responses_http import SimulatedHTTP
from test_manual_offline import packet


def retained():
    p = packet()
    detail = dict(id=12345, imdb='tt12345678', title='Example', original_title='Example',
                  type='movie', date='2026-03-14', dates=['2026-04-24'], runtime=105,
                  directors=['Example Director'], cast=['Actor One', 'Actor Two'])
    nfo = ('Complete name : private-example.mkv Duration : 1 h 45 min '
           'Video ID : 1 Duration : 1 h 45 min Audio ID : 2 Duration : 1 h 45 min '
           'Text ID : 3 Duration : 1 h 44 min')
    result = dict(original_facts=dict(title=p['title'], year=1998, imdb=p['asserted_imdb'],
        torrent_evidence=dict(description=dict(text='Example Year: 2026 Duration: 105 min Stars: Actor One, Actor Two'),
                             nfo=dict(text=nfo), truncated=True, unavailable_images=1)),
        missing_crosswalk=False,
        candidates=[dict(record=dict(id=12345), contradictions=['title_conflict','year_conflict'],
                         source_contradictions=['title_conflict'],
                         source_review=dict(description_independent_of_tracker_id=False))],
        evidence=[dict(method='find', query='tt12345678', result=dict(observed_at=100, expires_at=200,
                     reason='ok', data=dict(movies=[{k:detail[k] for k in ('id','title','original_title','type','date')}]))),
                  dict(method='details', query=12345, result=dict(observed_at=102,expires_at=202,reason='ok',data=detail)),
                  dict(method='movie_search', query=p['title'],result=dict(observed_at=101,expires_at=201,reason='ok',data=dict(results=[])))])
    return dict(case_id=p['case_id'],version=p['version'],title=p['title'],year=1998,reason='title_conflict',
                first_observed_at=p['first_observed'],observed_at=p['last_observed'],
                source_identity=dict(asserted_imdb='tt12345678'),proposal=dict(result=result))


def envelope(case=None):
    case = retained() if case is None else case
    return encoded(dict(kind='historical_retained_case', packet=packet(), retained_case=case,
                        retained_case_sha256=digest(case)))


class ExpandedManualTest(unittest.TestCase):
    def project(self, case=None):
        p, sha = parse_packet(envelope(case))
        _, _, _, body = build_request(p, sha, now=300)
        return p, sha, body, decode(decode(body)['input'][0]['content'][0]['text'])

    def test_source_parser_to_actual_body_preserves_independent_expected_facts(self):
        p, sha, body, data = self.project()
        o = data['historical_observations']
        # Literal expected values taken from fixture source fields, not mapper output.
        self.assertEqual(o['stream_durations'], [dict(stream='container',minutes=105),
            dict(stream='video',minutes=105),dict(stream='audio',minutes=105),dict(stream='subtitle',minutes=104)])
        by = {r['method']:r for r in o['catalogue']}
        self.assertEqual(by['find']['data']['movies'][0]['id'],12345)
        self.assertEqual(by['details']['data']['imdb'],'tt12345678')
        self.assertEqual(by['details']['data']['runtime'],105)
        self.assertEqual(by['details']['data']['directors'],['Example Director'])
        self.assertEqual(by['details']['data']['cast'],['Actor One','Actor Two'])
        self.assertEqual(by['details']['data']['date'],'2026-03-14')
        self.assertEqual(by['details']['data']['dates'],['2026-04-24'])
        self.assertEqual((by['details']['observed_at'],by['details']['expires_at']),(102,202))
        self.assertEqual(by['details']['expiry_status'],'expired')
        self.assertEqual(by['movie_search']['data']['results'],[])
        self.assertEqual(o['description'],dict(year=2026,runtime_minutes=105,cast=['Actor One','Actor Two'],independent_of_tracker_id=False))
        self.assertEqual(o['candidate_conflicts'][0]['contradictions'],['title_conflict','year_conflict'])
        self.assertFalse(o['missing_crosswalk'])
        self.assertTrue(o['source_truncated'])
        self.assertEqual(o['unavailable_images'],1)
        self.assertEqual(data['qualifications']['first_observed'],1793629799.735184)
        self.assertEqual(data['qualifications']['last_observed'],1793630704.271945)
        self.assertTrue(data['qualifications']['report_partial'])
        self.assertEqual(data['qualifications']['currentness'],'unknown')
        self.assertFalse(data['qualifications']['physical_source_verified'])
        self.assertFalse(data['qualifications']['authenticated_provider_receipt'])
        self.assertEqual(o['missing_fields'],[])
        for private in (p['case_id'],p['version'],p['source_sha256'],'private-example.mkv','Complete name'):
            self.assertNotIn(private,body.decode())

    def test_rehearsal_actually_sends_expanded_body_to_only_fixture(self):
        p, sha = parse_packet(envelope())
        original = SimulatedHTTP.post
        seen=[]
        def capture(http,body,**kwargs):
            seen.append(body)
            return original(http,body,**kwargs)
        with tempfile.TemporaryDirectory() as tmp, patch('socket.socket',side_effect=AssertionError('network')), patch.object(SimulatedHTTP,'post',capture):
            report=rehearse(p,sha,Path(tmp).resolve(),ceiling=[10,1])
        self.assertEqual(report['state'],'validated_simulated_response')
        self.assertTrue(report['simulation'])
        self.assertEqual(len(seen),1)
        self.assertEqual(decode(seen[0]),report['constructed_request'])
        observed=decode(decode(seen[0])['input'][0]['content'][0]['text'])['historical_observations']
        self.assertEqual(observed['stream_durations'][-1],dict(stream='subtitle',minutes=104))
        self.assertEqual(observed['catalogue'][1]['data']['runtime'],105)

    def test_missing_evidence_is_visible_not_silently_discarded(self):
        c=retained();r=c['proposal']['result'];r['evidence']=r['evidence'][:1]
        del r['original_facts']['torrent_evidence']['nfo']
        del r['original_facts']['torrent_evidence']['description']
        _,_,_,data=self.project(c);o=data['historical_observations']
        for missing in ('evidence.details','evidence.movie_search','nfo.duration.video','description.year'):
            self.assertIn(missing,o['missing_fields'])
        self.assertIsNone(o['description']['year'])
        self.assertEqual(o['stream_durations'],[])

    def test_binding_hash_privacy_bounds_and_duplicate_refuse(self):
        c=retained();c['version']='0'*64
        with self.assertRaisesRegex(Refusal,'retained_case_binding'):self.project(c)
        e=decode(envelope());e['retained_case_sha256']='0'*64
        with self.assertRaisesRegex(Refusal,'retained_case_hash'):parse_packet(encoded(e))
        c=retained();c['proposal']['result']['evidence'][1]['result']['data']['title']='https://private.invalid/token'
        with self.assertRaises(Refusal):self.project(c)
        c=retained();c['proposal']['result']['evidence'].append(c['proposal']['result']['evidence'][0])
        with self.assertRaisesRegex(Refusal,'retained_duplicate_method'):self.project(c)
        c=retained();c['proposal']['result']['original_facts']['torrent_evidence']['nfo']['text']='x'*16385
        with self.assertRaisesRegex(Refusal,'retained_nfo_size'):self.project(c)

    def test_unlabelled_cast_tail_is_not_disclosed_and_future_clock_is_visible(self):
        c=retained()
        c['proposal']['result']['original_facts']['torrent_evidence']['description']['text'] += ' internalTrackerCode ABC123'
        _,_,body,data=self.project(c)
        self.assertNotIn('internalTrackerCode',body.decode())
        self.assertNotIn('ABC123',body.decode())
        self.assertIsNone(data['historical_observations']['description']['cast'])
        self.assertIn('description.cast_unparsed_or_not_catalogue_bound',data['historical_observations']['missing_fields'])
        p,sha=parse_packet(envelope())
        _,_,_,body=build_request(p,sha,now=50)
        observations=decode(decode(body)['input'][0]['content'][0]['text'])['historical_observations']['catalogue']
        self.assertTrue(all(r['expiry_status']=='future_observation_unverified' for r in observations))

    def test_packet_occurrence_clock_mismatch_refuses(self):
        e=decode(envelope())
        e['packet']['first_observed'] -= 86400
        with self.assertRaisesRegex(Refusal,'retained_occurrence_clock_binding'):
            parse_packet(encoded(e))
        e=decode(envelope())
        e['packet']['last_observed'] += 60
        with self.assertRaisesRegex(Refusal,'retained_occurrence_clock_binding'):
            parse_packet(encoded(e))

    def test_legacy_remains_explicitly_reduced(self):
        p,sha=parse_packet(encoded(packet()));_,_,_,body=build_request(p,sha)
        self.assertNotIn('historical_observations',decode(decode(body)['input'][0]['content'][0]['text']))
        with tempfile.TemporaryDirectory() as tmp:
            report=rehearse(p,sha,Path(tmp).resolve(),ceiling=[1,2])
        self.assertIn('incomplete evidence',report['disclosure_limit'])
