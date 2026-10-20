import copy
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from research.identity_scoring.shadow import observe, scan


def proposal():
    return {'original_facts': {'title':'Example Movie','year':2023,'imdb':'tt1234567','runtime':148},
            'reason':'candidate_review','evidence':[
                {'method':'find','query':'tt1234567','result':{'reason':'ok','data':{'movies':[{'id':123,'title':'Example Movie','type':'movie','date':'2023-01-01'}],'tv':[],'tv_other':False}}},
                {'method':'details','query':123,'result':{'reason':'ok','data':{'id':123,'title':'Example Movie','type':'movie','date':'2023-01-01','runtime':150,'imdb':'tt1234567','original_language':'en'}}}]}


class ShadowTests(unittest.TestCase):
    def test_arithmetic_does_not_grant_identity_with_missing_provenance(self):
        p=proposal();before=copy.deepcopy(p);r=observe(p)
        self.assertEqual(r['ranked'][0]['score'],88)
        self.assertTrue(r['arithmetic_pass']);self.assertEqual(r['decision'],'review')
        self.assertIn('candidate_set_incomplete',r['reasons']);self.assertEqual(p,before)
    def test_failed_find_never_proves_crosswalk(self):
        p=proposal();p['evidence'][0]['result']['reason']='transport_failure'
        self.assertIn('crosswalk_unverified',observe(p)['reasons'])
    def test_conflicting_id_remains_blocked(self):
        p=proposal();p['evidence'][1]['result']['data']['imdb']='tt7654321'
        self.assertIn('tracker_id_conflict',observe(p)['reasons'])
    def test_undetailed_search_rival_is_not_discarded(self):
        p=proposal();p['evidence'].append({'method':'movie_search','result':{'reason':'ok','data':{'results':[{'id':456,'title':'Example Movie','date':'2023-01-01','type':'movie'}]}}})
        r=observe(p);self.assertEqual(len(r['ranked']),2);self.assertLess(r['margin'],15)
    def test_read_only_dedup_new_vs_historical_and_no_network(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'research.sqlite3'
            with sqlite3.connect(path) as c:
                c.executescript('create table evidence(version text,case_id text); create table proposals(version text,created real,result text);')
                for version,created in [('v1',90),('v2',110)]:
                    c.execute('insert into evidence values (?,?)',(version,'case'))
                    c.execute('insert into proposals values (?,?,?)',(version,created,json.dumps(proposal())))
                c.execute('insert into proposals select * from proposals where version="v2"')
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            with patch.object(socket,'socket',side_effect=AssertionError('network')):
                r=scan([path],100,200,120);again=scan([path],100,200,120)
            self.assertEqual(r,again);self.assertEqual(r['recorded'],2);self.assertEqual(r['new_results'],1)
            self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertTrue(scan([path],100,200,200)['expired'])
    def test_seven_day_bound(self):
        with self.assertRaises(ValueError):scan([],100,100+8*86400,101)
