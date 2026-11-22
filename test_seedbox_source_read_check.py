"""Public invented exact source records and response fixtures."""
import hashlib
import json
import time
import unittest
from unittest.mock import patch

from ai_movie_investigator.contracts import Refusal, digest, encoded
from automation.seedbox_source_read_check import observe, select
from identity_triage_intake import normalize
from identity_triage_observer import envelope
from test_identity_automation import context
from test_identity_triage import SOURCES, payload


IMDB = 'tt1234567'
HEADING = 'Invented.Film.2001'
LISTING = f'<h2 id="torrentnameid">{HEADING}</h2><input name="imdbID" value="{IMDB}">'.encode()


def selection_fixture(configuration_sha256, now):
    actor = envelope(payload(name=HEADING), context('tmdb_mapping_missing'), SOURCES)
    record = normalize(actor, SOURCES, 'outcome')
    case_id = 'outcome-' + record['release']
    material = dict(metadata=record['metadata'], correlation='strong_source_id',
                    route='eligible', underlying_route='eligible', outcome=dict(record['outcome']))
    material['outcome']['torrent_evidence'] = dict(
        version=1, description=dict(text='', digest=hashlib.sha256(b'').hexdigest()),
        nfo=dict(text='', digest=hashlib.sha256(b'').hexdigest()), images=[],
        unavailable_images=0, truncated=False)
    return dict(kind='seedbox_source_read_selection_v1', configuration_sha256=configuration_sha256,
                excluded_case_id='outcome-'+'f'*64, paused_at=now-300,
                collector_observed_at=now-60, selected_at=now-1, expires_at=now+120,
                collector_version=digest([case_id, material]), collector_material=material,
                actor_version=digest([record['release'], record['metadata']]),
                actor_observation=actor, expected_listing_imdb=IMDB)


class SourceReadCheckTests(unittest.TestCase):
    def setUp(self):
        self.now = time.time()
        self.config = dict(sources=SOURCES, listing_source='example')
        self.config_sha = 'a'*64
        self.fixture = selection_fixture(self.config_sha, self.now)

    def select(self, **changes):
        raw = encoded(dict(self.fixture, **changes))
        return select(raw, hashlib.sha256(raw).hexdigest(), self.config, self.config_sha, self.now)

    def test_selection_excludes_old_case_and_wrong_binding(self):
        selected = self.select()
        for changes in (dict(excluded_case_id=selected['case_id']),
                        dict(paused_at=self.now-10), dict(expires_at=self.now-1),
                        dict(configuration_sha256='d'*64), dict(actor_version='d'*64),
                        dict(collector_version='d'*64)):
            with self.subTest(fields=list(changes)), self.assertRaises(Refusal):
                self.select(**changes)

    def run_observation(self, replies):
        selected = self.select()
        marks = []
        with patch('automation.seedbox_host_io._source_inputs',
                   return_value=({'TMDB_API_TOKEN':'INVENTED'}, {'session':'INVENTED'})), \
             patch('automation.seedbox_host_io._get', side_effect=[(raw,self.now) for raw in replies]) as fetch:
            result = observe(self.config, selected, marks.append, clock=lambda:self.now)
            return result, marks, fetch.call_count

    def test_exact_head_and_id_then_single_empty_or_exact_catalogue(self):
        empty = json.dumps({'movie_results':[]}).encode()
        self.assertEqual(self.run_observation([LISTING,empty]),
                         ('authenticated_no_movie_mapping',['listing_get','listing_heading_id','catalogue_find'],2))
        found = json.dumps({'movie_results':[{'id':321}]}).encode()
        detail = json.dumps({'id':321,'imdb_id':IMDB,'title':'Invented Film'}).encode()
        self.assertEqual(self.run_observation([LISTING,found,detail]),
                         ('authenticated_crosswalk',['listing_get','listing_heading_id','catalogue_find','catalogue_detail'],3))

    def test_changed_heading_or_id_never_reaches_catalogue(self):
        selected = self.select()
        for page in (LISTING.replace(b'Invented',b'Different'), LISTING.replace(b'tt1234567',b'tt7654321')):
            with patch('automation.seedbox_host_io._source_inputs',return_value=({},{})), \
                 patch('automation.seedbox_host_io._get',return_value=(page,self.now)) as fetch:
                with self.assertRaisesRegex(Refusal,'listing_heading_or_id_refused'):
                    observe(self.config,selected,lambda stage:None,clock=lambda:self.now)
                self.assertEqual(fetch.call_count,1)
