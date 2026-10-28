import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research.identity_scoring.edition_discovery import proposal,search_links,parse_product,discover,fetch
from research.identity_scoring.refresh import Budget
import test_shadow_editions as fixtures
from research.identity_scoring.fresh import build_case

URL='https://www.blu-ray.com/movies/Anniversary-Blu-ray/123/'
SEARCH=('<a class="hoverlink" data-productid="123" title="Studio 75 (1950-2000)" href="'+URL+'"></a>').encode()
PRODUCT=('<h1>Studio 75 Blu-ray</h1><link rel="canonical" href="'+URL+'"><div id="longsubs"><b><a href="https://www.blu-ray.com/movies/Film-Blu-ray/1/">Goldfinger</a></b><b><a href="https://www.blu-ray.com/movies/Film-Blu-ray/2/">Other</a></b></div>').encode()
class DiscoveryTests(unittest.TestCase):
    def test_unknown_label_is_derived_without_registry(self):
        t=fixtures.EditionTests();t.setUp();t.listing.pop('_discovered_editions')
        t.release['title']='Studio 75 Goldfinger'
        case,facts=build_case(t.release,t.listing,t.nfo,t.search,t.details,t.maps)
        self.assertEqual(proposal(case['source'],case['candidates']),{'label':'studio 75','title':'Goldfinger','year':1964})
        self.assertEqual(facts['filename_count'],1)
        for title in ['Goldfinger II','Goldfinger 2049','2018','Goldfinger Goldfinger']:
            case['source']['title']=title;self.assertIsNone(proposal(case['source'],case['candidates']))
    def test_discovery_and_cache_zero_repeat_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cache';b=Budget(Path(folder)/'budget',lambda:100)
            req={'label':'Studio 75','title':'Goldfinger','year':1964}
            with patch('research.identity_scoring.edition_discovery.fetch',side_effect=[SEARCH,PRODUCT]) as get:
                r=discover(req,path,b,100);self.assertEqual(r['status'],'edition_membership_found');self.assertEqual(get.call_count,2)
                self.assertEqual(discover(req,path,b,101),r);self.assertEqual(get.call_count,2)
            with patch('research.identity_scoring.edition_discovery.fetch',return_value=b'') as get:
                r=discover(req,path,b,100+8*86400);self.assertEqual(r['status'],'edition_evidence_inconclusive');self.assertEqual(get.call_count,1)
    def test_budget_and_negative_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cache';b=Budget(Path(folder)/'budget',lambda:100);b.used=9
            req={'label':'Studio 75','title':'Goldfinger','year':1964}
            with patch('research.identity_scoring.edition_discovery.fetch') as get:
                self.assertEqual(discover(req,path,b,100)['status'],'edition_budget_deferred');get.assert_not_called()
            b.used=0
            with patch('research.identity_scoring.edition_discovery.fetch',side_effect=RuntimeError('secret')) as get:
                r=discover(req,path,b,100);self.assertEqual(r['status'],'edition_source_unavailable')
                self.assertNotIn('secret',path.read_text());discover(req,path,b,101);self.assertEqual(get.call_count,1)
    def test_untrusted_links_and_recommendations(self):
        self.assertEqual(search_links(SEARCH,'Other',1964),[])
        self.assertEqual(search_links(SEARCH,'Studio 75',2020),[])
        self.assertEqual(search_links(SEARCH.replace(URL.encode(),b'http://127.0.0.1/'),'Studio 75',1964),[])
        self.assertIsNone(parse_product(PRODUCT.replace(b'longsubs',b'recommendations'),'Studio 75',URL,100))
        self.assertIsNone(parse_product(PRODUCT,'Other',URL,100))
        self.assertIsNone(parse_product(PRODUCT,'Studio 75',URL+'x',100))
    def test_egress_restrictions(self):
        for url in ['http://127.0.0.1/','https://www.blu-ray.com.evil/search/','https://evil.org/',URL+'?secret=x']:
            with self.assertRaises(ValueError):fetch(url,None)
    def test_no_id_conflict_bypass(self):
        t=fixtures.EditionTests();t.setUp();t.listing.pop('_discovered_editions');t.details[658]['external_ids']['imdb_id']='tt1234567'
        case,_=build_case(t.release,t.listing,t.nfo,t.search,t.details,t.maps)
        self.assertIsNone(proposal(case['source'],case['candidates']))
