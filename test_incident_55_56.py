"""Read-only incident characterizations. Synthetic envelopes; no live handlers.

These preserve current fail-closed behavior and reproduce the presentation gap.
They do not implement the proposed retry, alias or upstream parser changes.
"""
import unittest
from unittest.mock import patch

import movie_intel_service as svc
import tmdb_resolver as tm
from identity_triage_intake import normalize, Reject
from identity_selection import route
from test_identity_triage import payload, SOURCES


def details(title='Example Film', year=2021, imdb='tt1234567'):
    return {'id':123,'title':title,'original_title':title,
            'release_date':f'{year}-01-01','external_ids':{'imdb_id':imdb}}


def resolve(title,year,document,imdb='tt1234567',found=None):
    found={'movie_results':[{'id':123}]} if found is None else found
    with patch.object(tm,'_get',side_effect=lambda p,q: found if p.startswith('/find/') else document):
        return tm._resolve_external(title,year,imdb,None)


class IncidentCharacterizations(unittest.TestCase):
    def test_recovered_http_lookup_is_retry_not_missing_catalog(self):
        self.assertEqual(route({'category':'unknown_movie','status':'unresolved','reason':'listing_http_error'}),'retry_later')
        self.assertEqual(resolve('Example Film',2021,details())['identity_status'],'verified_tmdb')

    def test_missing_crosswalk_does_not_authorize_same_title_candidate(self):
        self.assertEqual(resolve('Example Film',2021,details(),found={'movie_results':[]})['identity_reason'],'tmdb_mapping_missing')
        # A tempting title/year candidate with another IMDb is still contradictory.
        self.assertEqual(resolve('Example Film',2021,details(imdb='tt7654321'))['identity_reason'],'identity_conflict')

    def test_undocumented_release_year_stays_review_only(self):
        for original,label in ((2012,2011),(2014,2017)):
            result=resolve('Example Film',label,details(year=original))
            self.assertEqual(result['identity_reason'],'year_conflict')
            # The later conflict-investigation path admits this for research only.
            self.assertEqual(result['identity_status'], 'needs_review')
            self.assertEqual(route({'category':'unknown_movie','status':result['identity_status'],'reason':result['identity_reason']}),'eligible')

    def test_added_documented_date_can_resolve_prior_year_conflict(self):
        d=details(year=2021)
        self.assertEqual(resolve('Example Film',2023,d)['identity_reason'],'year_conflict')
        d['release_dates']={'results':[{'release_dates':[{'release_date':'2023-01-01'}]}]}
        self.assertEqual(resolve('Example Film',2023,d)['identity_status'],'verified_tmdb')
        self.assertEqual(resolve('Example Film',2024,d)['identity_reason'],'year_conflict')

    def test_fraction_rendering_requires_review_not_fuzzy_acceptance(self):
        d=details(title='18½')
        self.assertEqual(resolve('18 1 and 2',2021,d)['identity_reason'],'title_conflict')
        self.assertEqual(resolve('18½',2021,d)['identity_status'],'verified_tmdb')
        self.assertEqual(resolve('18½',2020,d)['identity_reason'],'year_conflict')
        self.assertEqual(resolve('18½',2021,d,imdb='tt7654321')['identity_reason'],'identity_conflict')

    def test_same_title_multiple_crosswalks_stay_ambiguous(self):
        result=resolve('Example Film',2021,details(),found={'movie_results':[{'id':123},{'id':456}]})
        self.assertEqual(result['identity_reason'],'ambiguous_id_mapping')

    def test_apollo_parsed_episode_bypasses_movie_and_raw_fallback_is_noisy(self):
        p=payload(type='episode',title='Apollo 10 1',sub_title='A Space Age Childhood',
                  episode=2,year=2022,category='Movies :: WEBRip',
                  name='Apollo 10 1 - 2 A Space Age Childhood 2022 1080p WEB-DL-EXAMPLE',
                  download_url='https://example.invalid/download?passkey=synthetic')
        p['event']='action.rejected';p['data']['result']={'rejections':['Unknown Movie']}
        self.assertFalse(svc.valid_movie_payload(p))
        # Rendering only: never dispatch notification/approval handlers.
        rendered=svc.passthrough_message(p)
        self.assertIn('"episode": 2',rendered)
        self.assertIn('"event": "action.rejected"',rendered)
        self.assertNotIn('https://example.invalid',rendered)
        p['event']='release.new'
        with self.assertRaisesRegex(Reject,'non_movie'):normalize(p,SOURCES)

    def test_real_tv_is_not_promoted_by_movie_like_category(self):
        p=payload(type='episode',title='Example Show',episode=2,category='Movies :: WEBRip')
        p['event']='action.rejected';p['data']['result']={'rejections':['Unknown Movie']}
        self.assertFalse(svc.valid_movie_payload(p))
