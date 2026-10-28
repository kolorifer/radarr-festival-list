import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research.identity_scoring import cut_discovery as cut
from research.identity_scoring.refresh import Budget
from research.identity_scoring.fresh import build_case

URL='https://www.blu-ray.com/movies/Example-Blu-ray/123/'
def page(label='Unleashed Extended Edition', runtime=138, imdb='tt1430132',year=2013):
    return (f'<h1>The Wolverine 3D Blu-ray</h1><link rel="canonical" href="{URL}">'
            f'<span class="subheadingtitle">{label} / Blu-ray 3D + Blu-ray</span>'
            f'<span class="subheading"><a href="https://www.blu-ray.com/movies/movies.php?year={year}">{year}</a>'
            f' | 1 Movie, 2 Cuts | <span id="runtime">{runtime} min</span></span>'
            f'<a id="imdb_icon" href="https://www.imdb.com/title/{imdb}/">IMDb</a>').encode()
SEARCH=f'<a class="hoverlink" data-productid="123" title="The Wolverine 3D (2013)" href="{URL}"></a>'.encode()

class CutTests(unittest.TestCase):
    def setUp(self):
        self.release={'title':'The Wolverine','year':2013,'name':'The.Wolverine.2013.Extended.Cut.REPACK.1080p.BluRay.REMUX-GROUP'}
        self.listing={'reason':'listing_id_found','imdb_id':'tt1430132','torrent_evidence':{'description':{'text':'The Wolverine visits Japan.'}}}
        self.nfo='Complete name : '+self.release['name']+'.mkv Format : Matroska Duration : 2 h 18 min Audio ID : 1 Language : English'
        self.details={76170:{'id':76170,'title':'The Wolverine','release_date':'2013-07-01','runtime':126,
                             'original_language':'en','spoken_languages':[{'english_name':'English','iso_639_1':'en'}],
                             'external_ids':{'imdb_id':'tt1430132'}}}
        self.maps={'tt1430132':{'movie_results':[{'id':76170}]}}
        self.search={'page':1,'total_pages':1,'total_results':1,'results':[{'id':76170}]}
    def request(self):
        case,facts=build_case(self.release,self.listing,self.nfo,self.search,self.details,self.maps)
        return cut.proposal(self.release,self.listing,self.nfo,case,facts)
    def test_unfamiliar_names_syntax_not_registry(self):
        for name in ['The Reborn Cut','Phoenix Edition','Restored International Version','Director’s Cut']:
            self.assertTrue(cut.labels(name),name)
        self.assertEqual(cut.labels('The Reborn Cut')[0]['descriptor'],'reborn')
        self.assertEqual(cut.labels('Edition: The Stardust Version')[0]['descriptor'],'stardust')
        self.assertEqual(cut.labels('It includes the Reborn Cut')[0]['descriptor'],'reborn')
        self.assertTrue(cut.labels('not the Reborn Cut')[0]['negated'])
        self.assertEqual(cut.labels('a'*65537),[])
    def test_all_sources_and_unknown_leftovers(self):
        self.listing['torrent_evidence']['description']['text']='Edition: Extended Version'
        r=self.request();self.assertEqual(r['candidate_id'],76170)
        self.assertEqual({c['origin'] for c in r['claims']},{'release_suffix','tracker_description','bound_nfo'})
        self.release['name']=self.release['name'].replace('Extended.Cut','Phoenix')
        self.nfo=self.nfo.replace('Extended.Cut','Phoenix')
        r=self.request();self.assertIn('unexplained_label',[c['kind'] for c in r['claims']])
    def test_numeric_title_and_technical_tokens_not_edition(self):
        self.release['name']='The.Wolverine.2013.1080p.BluRay.REMUX-GROUP'
        self.nfo=self.nfo.replace('Extended.Cut.REPACK.','')
        r=self.request();self.assertEqual(r['claims'],[])
        self.assertEqual(r['trigger'],'runtime_disagreement')
        self.details[76170]['runtime']=138
        self.assertIsNone(self.request())
        self.assertEqual(cut.extract({'title':'Final Cut','year':2022,'name':'Final.Cut.2022.1080p'},
            {'torrent_evidence':{'description':{'text':'Final Cut'}}},'',{'titles':['Final Cut']}),[])
    def test_identity_provenance_and_binding_blocks(self):
        for mutate in [lambda:self.maps.clear(),
                       lambda:self.listing.update(imdb_id='tt1234567'),
                       lambda:self.details[76170].update(release_date='2000-01-01'),
                       lambda:setattr(self,'nfo',self.nfo.replace(self.release['name'],'Other')),
                       lambda:setattr(self,'nfo',self.nfo.replace('Complete name : '+self.release['name']+'.mkv ',''))]:
            self.setUp();mutate();self.assertIsNone(self.request())
    def test_structured_product_and_reject_other_movie(self):
        r=self.request();record=cut.parse_product(page(),r,URL,100)
        self.assertEqual(record['runtime'],138);self.assertTrue(record['multiple_cuts'])
        self.assertEqual(cut.search_links(SEARCH,r),[URL])
        for bad in [page(imdb='tt1234567'),page(year=2014),page().replace(b'id="runtime"',b'id="reviewruntime"'),
                    page().replace(b'The Wolverine 3D Blu-ray',b'Another Film Blu-ray'),
                    page().replace(URL.encode(),b'https://evil.invalid/'),
                    page('Extended Edition / Theatrical Cut'),page().replace(b'1 Movie, 2 Cuts',b'2 Movies')]:
            self.assertIsNone(cut.parse_product(bad,r,URL,100))
        self.assertEqual(cut.search_links(SEARCH.replace(b'(2013)',b'(2014)'),r),[])
    def test_reborn_fixture_requires_matching_claim_and_runtime(self):
        r=self.request();r['claims']=[{'label':'The Reborn Cut','descriptor':'reborn','negated':False,'origin':'release_suffix'}]
        r['nfo_runtime']=158
        record=cut.parse_product(page('The Reborn Cut',158),r,URL,100)
        result=cut.comparison(r,{'status':'cut_evidence_found','record':record})
        self.assertEqual(result['decision'],'would_explain_runtime')
        self.assertFalse(result['comparison']['changes_identity_decision'])
        record['runtime']=150
        self.assertEqual(cut.comparison(r,{'status':'cut_evidence_found','record':record})['decision'],'review')
    def test_wolverine_comparison_and_conflicting_claims(self):
        r=self.request();finding={'status':'cut_evidence_found','record':cut.parse_product(page(),r,URL,100)}
        result=cut.comparison(r,finding)
        self.assertEqual(result['decision'],'would_explain_runtime')
        self.assertAlmostEqual(result['comparison']['candidate_score_with_edition_runtime'],100)
        r['claims'].append({'descriptor':'theatrical','negated':False})
        self.assertEqual(cut.comparison(r,finding)['reasons'],['edition_claims_conflict'])
        r=self.request();r['claims'][0]['negated']=True
        self.assertEqual(cut.comparison(r,finding)['decision'],'review')
    def test_cache_budget_ttl_and_bound_egress(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cache';b=Budget(Path(folder)/'budget',lambda:100)
            r=self.request()
            with patch.object(cut,'fetch',side_effect=[SEARCH,page()]) as get:
                first=cut.discover(r,path,b,100)
                self.assertEqual(first['status'],'cut_evidence_found');self.assertEqual(get.call_count,2)
                r['nfo_runtime']=200 # reuse sourced movie evidence, not a past verdict
                second=cut.discover(r,path,b,101);self.assertTrue(second['cache_hit']);self.assertEqual(get.call_count,2)
                self.assertEqual(cut.comparison(r,second)['decision'],'review')
            b.used=9
            with patch.object(cut,'fetch') as get:
                self.assertEqual(cut.discover(r,path,b,100+8*86400)['status'],'cut_budget_deferred');get.assert_not_called()
            b.used=0
            with patch.object(cut,'fetch',side_effect=RuntimeError('private_url_secret')) as get:
                x=cut.discover(r,path,b,100+8*86400);self.assertEqual(x['status'],'cut_source_unavailable')
                self.assertTrue(cut.discover(r,path,b,101+8*86400)['cache_hit']);self.assertEqual(get.call_count,1)
                self.assertNotIn('secret',path.read_text())
    def test_duplicate_mapping_does_not_create_request(self):
        self.maps['tt1430132']['movie_results'].append({'id':999})
        self.assertIsNone(self.request())
    def test_full_refresh_records_comparison_and_reuses_cache(self):
        import tracker_metadata
        from research.identity_scoring.refresh import refresh_one
        def lookup(release,indexer):
            b.reserve('listing')
            return tracker_metadata.parse_listing('<div id="nfo_text">'+self.nfo+'</div>',release['name'])
        def metadata(path,params,budget):
            b.reserve('tmdb')
            if path.startswith('/find/'):return self.maps['tt1430132']
            if path.startswith('/movie/'):return self.details[76170]
            return self.search
        def fetch(url,budget):
            budget.reserve('edition')
            return SEARCH if '/search/' in url else page()
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);state=home/'.local/state/identity-scoring-shadow';state.mkdir(parents=True)
            b=Budget(state/'budget',lambda:100)
            with patch('research.identity_scoring.refresh.exact_release',return_value=(self.release,{'status':'needs_review','reason':'identity_conflict'})), \
                 patch.object(tracker_metadata,'lookup_listing',side_effect=lookup), \
                 patch.object(tracker_metadata,'parse_listing',return_value=self.listing), \
                 patch('research.identity_scoring.refresh.metadata_get',side_effect=metadata), \
                 patch.object(cut,'fetch',side_effect=fetch) as public, \
                 patch('research.identity_scoring.refresh.time.sleep'):
                result=refresh_one(home,{},b)
                self.assertEqual(result['requests'],6);self.assertEqual(public.call_count,2)
                self.assertEqual(result['decision'],'review')
                self.assertEqual(result['edition_investigation']['decision'],'would_explain_runtime')
                self.assertAlmostEqual(result['ranked'][0]['score'],85.71428571428571)
                b=Budget(state/'budget',lambda:101)
                result=refresh_one(home,{},b)
                self.assertEqual(result['requests'],4);self.assertEqual(public.call_count,2)
                self.assertTrue(result['edition_investigation']['discovery']['cache_hit'])

    def test_no_auto_approval_even_when_evidence_agrees(self):
        from research.identity_scoring.refresh import apply_existing_conflict_guard
        r=self.request();scored={'decision':'would_identify','selected_id':76170,'ranked':[{'candidate_id':76170}],
          'reasons':[],'source':{'imdb':'tt1430132'},'edition_investigation':cut.comparison(r,{'status':'cut_evidence_found','record':cut.parse_product(page(),r,URL,100)})}
        apply_existing_conflict_guard(scored,self.release,{'status':'needs_review','reason':'identity_conflict'})
        self.assertEqual(scored['decision'],'review');self.assertEqual(scored['edition_investigation']['decision'],'would_explain_runtime')

if __name__=='__main__':unittest.main()
