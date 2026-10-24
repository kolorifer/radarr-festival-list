"""Evidence-backed packaging, including adversarial single-movie interpretation."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from research.identity_scoring.fresh import result
from research.identity_scoring.scorer import title_similarity

class EditionTests(unittest.TestCase):
    def setUp(self):
        self.release={'title':'Bond 50 Goldfinger','year':1964,'name':'Bond.50.Goldfinger.1964.REMUX'}
        self.listing={'reason':'listing_id_found','imdb_id':'tt0058150','torrent_evidence':{'description':{'text':'Goldfinger While investigating a gold magnate.'}}}
        self.nfo='Complete name : Bond.50.Goldfinger.1964.REMUX.mkv Format : Matroska Duration : 1 h 50 min Audio ID : 1 Language : English'
        self.details={658:{'id':658,'title':'Goldfinger','release_date':'1964-01-01','runtime':110,'original_language':'en','spoken_languages':[{'english_name':'English','iso_639_1':'en'}],'external_ids':{'imdb_id':'tt0058150'}}}
        self.maps={'tt0058150':{'movie_results':[{'id':658}]}}
        self.search={'page':1,'total_pages':1,'total_results':1,'results':[{'id':658}]}
    def score(self):return result(self.release,self.listing,self.nfo,self.search,self.details,self.maps)
    def test_documented_member(self):
        r=self.score();self.assertEqual(r['selected_id'],658);self.assertEqual(r['ranked'][0]['score'],100)
        self.assertEqual(r['ranked'][0]['title_similarity'],0)
        self.assertEqual(r['ranked'][0]['edition_resolution']['label'],'Bond 50')
    def test_unregistered_label_and_member(self):
        for title in ['Unknown 50 Goldfinger','Bond 51 Goldfinger','Bond 50 Goldfinger II','Bond 50']:
            self.release['title']=title;self.assertIsNone(self.score()['ranked'][0]['edition_resolution'])
    def test_pack_description(self):
        for desc in ['Goldfinger complete collection','Goldfinger 22 movies','Goldfinger double feature','Goldfinger movie pack']:
            self.listing['torrent_evidence']['description']['text']=desc
            self.assertEqual(self.score()['decision'],'review')
    def test_exact_single_filename_required(self):
        for nfo in [self.nfo.replace('Complete name : Bond.50.Goldfinger.1964.REMUX.mkv ',''),self.nfo.replace('Goldfinger','Other'),self.nfo+' Complete name : Other.mkv Format : AVC']:
            with self.subTest(nfo=nfo):
                original=self.nfo;self.nfo=nfo;self.assertEqual(self.score()['decision'],'review');self.nfo=original
    def test_missing_or_conflicting_evidence(self):
        changes=[('year',1965),('runtime',200),('language','fr'),('imdb','tt1234567'),('description','Another movie'),('mapping',None)]
        for kind,value in changes:
            self.setUp()
            if kind=='year':self.release['year']=value
            elif kind=='runtime':self.details[658]['runtime']=value
            elif kind=='language':self.details[658]['original_language']=value
            elif kind=='imdb':self.details[658]['external_ids']['imdb_id']=value
            elif kind=='description':self.listing['torrent_evidence']['description']['text']=value
            else:self.maps={}
            with self.subTest(kind=kind):self.assertEqual(self.score()['decision'],'review')
    def test_rivals_and_pagination_stay_blocking(self):
        self.search['total_pages']=2;self.assertEqual(self.score()['decision'],'review')
        self.search.update(total_pages=1,total_results=2,results=[{'id':658},{'id':999,'title':'Goldfinger','release_date':'1964-01-01'}])
        self.assertEqual(self.score()['decision'],'review')
    def test_generic_data_not_bond_branch(self):
        self.release.update(title='Cinema Anniversary 75 Goldfinger',name='Cinema.Anniversary.75.Goldfinger.1964.REMUX')
        self.nfo=self.nfo.replace('Bond.50','Cinema.Anniversary.75')
        import json
        records=[{'label':'Cinema Anniversary 75','source':'https://example.org/edition','retrieved':'2026-10-24','members':[{'title':'Goldfinger','year':1964}]}]
        with patch('research.identity_scoring.editions.Path.read_text',return_value=json.dumps(records)):
            self.assertEqual(self.score()['selected_id'],658)
    def test_sequel_and_numeric_title_guard_unchanged(self):
        for a,b in [('Rocky II','Rocky'),('Blade Runner 2049','Blade Runner'),('2018','2019')]:
            self.assertEqual(title_similarity(a,b),0)
