"""Inert source-evidence propagation, sanitization and review-only regressions."""
import copy
import json
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import torrent_research_evidence as evidence
import tracker_metadata

NAME='A Film 1940 BluRay'
IMAGE='https://i.ibb.co/example/still-01.png'
PAGE=f'''<h2 id="torrentnameid">{NAME}</h2><input name="imdbID" value="tt1234567">
<div class="torrent-info-details"><h3>A Film</h3><div class="torrent-summary">A catalog synopsis.</div>
<div class="torrent-extra-info"><p>Year: 2010</p><p>Duration: 118 min</p><form>cookie=SECRET</form></div></div>
<div class="galleryContents">There are no images posted for this torrent.</div>
<div id="nfo_text"><img src="https://m.media-amazon.com/poster.jpg">
File Name: A Film 1940.mkv<br>IMDb URL: https://www.imdb.com/title/tt1234567/<br>
Duration : 1 h 54 min<br>Language : English<br>Screenshots<br>
<img src="{IMAGE}"><img src="{IMAGE}"></div>'''

class TorrentEvidenceTests(unittest.TestCase):
    def parse(self,page=PAGE):return evidence.extract(BeautifulSoup(page,'html.parser'))

    def test_embedded_stills_survive_empty_gallery_and_do_not_prove_identity(self):
        value=self.parse()
        self.assertEqual(len(value['images']),1)
        self.assertEqual(value['images'][0]['section'],'nfo_screenshot')
        self.assertEqual(value['images'][0]['review_status'],'not_visually_reviewed')
        self.assertEqual(value['unavailable_images'],1)
        review=evidence.assess(value,{'runtime':114})
        self.assertEqual(review['nfo_runtime_minutes'],[114])
        self.assertEqual(review['runtime_comparison'],'agrees')
        self.assertFalse(review['source_claims_verified'])
        self.assertFalse(review['description_independent_of_tracker_id'])
        self.assertEqual(evidence.assess(value,{'runtime':106})['runtime_comparison'],'differs_or_ambiguous')
        self.assertIn('Year: 2010',value['description']['text'])

    def test_projection_failure_cannot_change_listing_identification(self):
        with patch.object(evidence,'extract',side_effect=ValueError('malformed_evidence')):
            result=tracker_metadata.parse_listing(PAGE,NAME)
        self.assertEqual(result['reason'],'listing_id_found')
        self.assertEqual(result['imdb_id'],'tt1234567')
        self.assertNotIn('torrent_evidence',result)

    def test_exact_listing_required_and_identity_conflicts_stay_blocked(self):
        self.assertNotIn('torrent_evidence',tracker_metadata.parse_listing(PAGE,'Other'))
        value=tracker_metadata.parse_listing(PAGE,NAME)
        self.assertEqual(value['reason'],'listing_id_found')
        value=tracker_metadata.parse_listing(PAGE+'<a href="https://www.imdb.com/title/tt7654321/">Other</a>',NAME)
        self.assertEqual(value['reason'],'listing_id_conflict')
        self.assertIn('torrent_evidence',value)
        self.assertNotIn('imdb_id',value)

    def test_unsafe_links_and_hidden_page_secrets_never_cross_boundary(self):
        page=PAGE.replace('</div>', '<script>password=PRIVATE</script></div>',1)
        page+= '<input value="PRIVATE"><a href="https://tracker.invalid/download/passkey">DOWNLOAD</a>'
        value=self.parse(page)
        self.assertNotIn('PRIVATE',json.dumps(value))
        self.assertNotIn('imdb.com',json.dumps(value))
        for url in ('http://i.ibb.co/x/a.png','https://i.ibb.co/x/a.png?token=secret','https://i.ibb.co@127.0.0.1/x.png','https://127.0.0.1/x.png','https://i.ibb.co/x/a%2epng','https://i.ibb.co/x/a.png#x','https://i.ibb.co:443/x/a.png'):
            with self.subTest(url=url):
                self.assertFalse(self.parse(PAGE.replace(IMAGE,url))['images'])
                bad=copy.deepcopy(value);bad['images'][0]['url']=url
                with self.assertRaises(ValueError):evidence.validate(bad)

    def test_text_bounds_redaction_digest_validation_and_no_active_content(self):
        value=self.parse(PAGE.replace('Language : English','Language : English token=PRIVATE')+'')
        self.assertNotIn('PRIVATE',json.dumps(value))
        self.assertLess(len(json.dumps(self.parse(PAGE.replace('A catalog synopsis.','文 '*10000)))),65536)
        value['nfo']['text']+=' changed'
        with self.assertRaises(ValueError):evidence.validate(value)
        self.assertTrue(self.parse(PAGE.replace('A catalog synopsis.','x '*5000))['truncated'])

    def test_images_bounded_gallery_included_unknown_hosts_explicit(self):
        page=PAGE.replace('There are no images posted for this torrent.', ''.join(f'<img src="https://i.ibb.co/x/still-{n}.png">' for n in range(10)))
        value=self.parse(page)
        self.assertEqual(len(value['images']),6)
        self.assertTrue(value['truncated'])
        self.assertTrue(any(x['section']=='screenshot_gallery' for x in value['images']))

    def test_repeated_duration_deduplicates_and_conflicting_durations_remain(self):
        value=self.parse(PAGE.replace('Duration : 1 h 54 min','Duration : 1 h 54 min Duration: 114 min Duration: 118 min'))
        self.assertEqual(evidence.assess(value,{'runtime':114})['nfo_runtime_minutes'],[114,118])
        self.assertEqual(evidence.assess(value,{'runtime':114})['runtime_comparison'],'differs_or_ambiguous')

if __name__=='__main__':unittest.main()

class ActorEvidenceTests(unittest.TestCase):
    def test_native_id_conflict_collects_source_without_changing_identity_or_actions(self):
        import movie_intel_service as svc
        from test_identity_triage import payload
        p=payload();p['data']['result']={'rejections':['Unknown Movie']}
        source=evidence.extract(BeautifulSoup(PAGE,'html.parser'))
        with patch.object(svc,'find_local',return_value=None), patch.object(svc,'resolve_external_movie',return_value={'identity_status':'needs_review','identity_reason':'year_conflict','imdb_id':'tt1234567'}), patch.object(svc,'lookup_listing',return_value={'torrent_evidence':source}) as lookup, patch.object(svc,'decision_log'), patch.object(svc,'get_movie_by_tmdb') as radarr, patch.object(svc,'create_action') as action:
            context=svc.build_movie_context(p)
        lookup.assert_called_once();radarr.assert_not_called();action.assert_not_called()
        self.assertEqual(context['meta']['identity_status'],'needs_review')
        self.assertEqual(context['identity_observation']['torrent_evidence'],source)
        self.assertNotIn('i.ibb.co',context['text'])
        self.assertNotIn('imdb_id',context['meta'])

    def test_verified_identity_does_not_record_investigation_evidence(self):
        import movie_intel_service as svc
        from test_identity_triage import payload
        p=payload(meta_imdb=None);p['data']['result']={'rejections':['Unknown Movie']}
        source=evidence.extract(BeautifulSoup(PAGE,'html.parser'))
        meta={'identity_status':'verified_tmdb','identity_reason':'external_id_verified','imdb_id':'tt1234567','tmdb_id':123,'title':'Synthetic Movie','year':2025}
        with patch.object(svc,'find_local',return_value=None), patch.object(svc,'resolve_external_movie',return_value=meta), patch.object(svc,'lookup_listing',return_value={'reason':'listing_id_found','source':'torrentleech_listing','imdb_id':'tt1234567','torrent_evidence':source}), patch.object(svc,'decision_log'), patch.object(svc,'get_movie_by_tmdb',return_value={}):
            context=svc.build_movie_context(p)
        self.assertNotIn('torrent_evidence',context['identity_observation'])
        self.assertEqual(context['meta']['identity_status'],'verified_tmdb')
