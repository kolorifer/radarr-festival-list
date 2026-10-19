import unittest
from film_editions import claim, annotation

META={'identity_status':'verified_tmdb','imdb_id':'tt0052311','tmdb_id':1480}
def release(tail):return {'type':'movie','name':'Touch.of.Evil.1958.'+tail}

class EditionTests(unittest.TestCase):
    def test_three_distinct_cuts(self):
        for tail,key,label in [('THEATRICAL.CUT','theatrical','1958 theatrical'),('Preview-Version','preview','1958 preview'),('1998.Reconstructed','reconstructed','1998 reconstructed')]:
            self.assertEqual(claim(release(tail)['name'],1958),key)
            self.assertIn(label,annotation(release(tail),META))
    def test_unknown_and_not_a_cut(self):
        for tail in ('2160p.REMUX','4K.Remastered.Criterion.HDR-Final','RESTORED.1080p-GROUP'):
            self.assertEqual(claim(release(tail)['name'],1958),'unknown')
            self.assertIn('Edition of this release unknown',annotation(release(tail),META))
    def test_delimiters_aliases_and_title_exclusion(self):
        for tail in ("Director's.Cut","DIRECTORS_CUT",'DC'):
            self.assertEqual(claim(release(tail)['name'],1958),'directors')
        self.assertEqual(claim('The.Final.Cut.2004.1080p',2004),'unknown')
        self.assertEqual(claim('Preview.1958.1080p-Theatrical',1958),'unknown')
        self.assertEqual(claim('Movie.1958.UNDIRECTORS.CUT',1958),'unknown')
    def test_contradiction_and_metadata(self):
        self.assertEqual(claim(release('THEATRICAL.CUT')['name'],1958,'Extended Edition'),'ambiguous')
        self.assertEqual(claim(None,1958,'Theatrical Cut'),'theatrical')
    def test_identity_gates(self):
        for meta in ({},dict(META,identity_status='unresolved'),dict(META,tmdb_id=1),dict(META,tmdb_id=True),dict(META,imdb_id='tt0000001')):
            self.assertEqual(annotation(release('THEATRICAL'),meta),'')
        self.assertEqual(annotation(dict(release('THEATRICAL'),type='episode'),META),'')
    def test_existing_association_and_reconstruction_caveat(self):
        existing={'imdbId':'tt0052311','tmdbId':1480,'hasFile':True,'movieFile':{'edition':'Theatrical Cut'}}
        text=annotation(release('RECONSTRUCTED'),META,existing)
        self.assertIn('Existing: 1958 theatrical (claimed)',text)
        self.assertIn('after his death',text);self.assertIn('never personally approved',text)
        existing['tmdbId']=1
        self.assertIn('Existing: Unknown',annotation(release('RECONSTRUCTED'),META,existing))
    def test_no_untrusted_text_is_echoed_or_duration_inference(self):
        text=annotation(release('<script>SECRET</script>.110min'),META)
        self.assertNotIn('SECRET',text);self.assertIn('release unknown',text)
        self.assertEqual(claim('x'*1025,1958),'unknown')

class EditionIntegrationTests(unittest.TestCase):
    def test_quality_rejection_annotation_uses_verified_identity_and_keeps_action_disabled(self):
        from unittest.mock import patch
        import movie_intel_service as svc
        p={'event':'action.rejected','data':{'release':dict(release('2160p.REMUX'),title='Touch of Evil',year=1958,meta_imdb='tt0052311'),'result':{'rejections':['Existing file meets cutoff: Remux-2160p []']},'indexer':{}}}
        with patch.object(svc,'resolve_external_movie',return_value=META),patch.object(svc,'get_movie_by_tmdb',return_value=None):
            ctx=svc.build_movie_context(p)
        self.assertIn('Edition of this release unknown',ctx['text'])
        self.assertIsNone(svc.create_pending_action(p,META))
    def test_autobrr_array_fields_and_conflicting_claims(self):
        p=release('2160p.REMUX');p.update(edition=['Theatrical Cut'],cut=['Preview Version'])
        self.assertIn('Conflicting edition claims',annotation(p,META))
    def test_failed_identity_does_not_query_radarr_or_show_film_facts(self):
        from unittest.mock import patch
        import movie_intel_service as svc
        p={'event':'action.rejected','data':{'release':dict(release('THEATRICAL'),title='Touch of Evil',year=1958,meta_imdb='tt0052311'),'result':{'rejections':['Existing file meets cutoff']},'indexer':{}}}
        with patch.object(svc,'resolve_external_movie',return_value=dict(META,identity_status='needs_review')),patch.object(svc,'get_movie_by_tmdb') as lookup:
            ctx=svc.build_movie_context(p)
        self.assertNotIn('Multiple significant cuts',ctx['text']);lookup.assert_not_called()
