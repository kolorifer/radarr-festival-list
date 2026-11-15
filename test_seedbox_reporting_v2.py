"""Invented actual-shaped DOM; legacy receipts and rejection remain intact."""
import copy,hashlib,unittest
from unittest.mock import patch
from automation.seedbox_source_evidence import listing_facts,actor_listing
from automation import seedbox_evidence as evidence,seedbox_automated_review as review
from ai_movie_investigator.snapshot_review import build_film_prose,validate_film_prose
from ai_movie_investigator.contracts import encoded,decode,digest
from test_seedbox_connected import ConnectedTests
from test_snapshot_review import NOW,CASE,VERSION

HTML=b'<h2 id="torrentnameid">Invented release</h2><input name="imdbID" value="tt1234567"><div class="torrent-info-details"><h3>Example Movie</h3><div class="torrent-extra-info"><p><strong>Year:</strong> 2021</p><p>Stars: <a>Actor One</a>, <a>Actor Two</a></p><p>Director: Director One</p><p>Runtime: 95 min</p></div></div>'

class ExtractionTests(unittest.TestCase):
 def parse(self,raw=HTML,revision=2):return listing_facts(raw,release_name='Invented release',case_id=CASE,version=VERSION,observed_at=NOW-10,expires_at=NOW+600,revision=revision)
 def test_bare_title_separate_year_and_linked_stars(self):
  old=self.parse(revision=1);new=self.parse()
  self.assertIsNone(old['title']);self.assertIsNone(old['year']);self.assertEqual(old['cast'],[])
  self.assertEqual((new['title'],new['year'],new['cast']),('Example Movie',2021,['Actor One','Actor Two']))
  self.assertEqual(old['description_runtime_minutes'],new['description_runtime_minutes'])
 def test_adjacent_linked_stars_remain_separate(self):
  self.assertEqual(self.parse(HTML.replace(b'</a>, <a>',b'</a><a>'))['cast'],['Actor One','Actor Two'])
 def test_conflicting_titles_and_years_remain_unknown(self):
  raw=HTML.replace(b'</h3>',b'</h3><h3>Different Film (1998)</h3>')
  value=self.parse(raw);self.assertIsNone(value['title']);self.assertIsNone(value['year'])
 def test_inline_general_length_preserves_exact_container_milliseconds(self):
  nfo=b'<pre id="nfo_text">General : Invented.other.release.mkv\nLength : 7.25 GiB for 2 h 13 min 27 s 418 ms\nVideo #0 : invented\nAudio #0 : invented\nLength : 1 GiB for 0 h 1 min 0 s 0 ms</pre>'
  value=self.parse(HTML+nfo);self.assertEqual(value['nfo_runtime_milliseconds'],8007418);self.assertEqual(value['nfo_runtime_kind'],'container')
  self.assertIsNone(self.parse(HTML+nfo,revision=1)['nfo_runtime_milliseconds'])
  for altered in (nfo.replace(b'13 min',b'63 min'),nfo.replace(b'418 ms',b'1418 ms'),nfo.replace(b'27 s',b'77 s'),nfo.replace(b'2 h',b'25 h'),nfo.replace(b'General :',b'Text #0 :')):
   self.assertIsNone(self.parse(HTML+altered)['nfo_runtime_milliseconds'])
  for heading in (b'  Audio #0 : invented',b'  Text #0 : invented',b'  Subtitle #0 : invented'):
   only_audio=b'<pre id="nfo_text">General : Invented.mkv\nTitle : invented\n'+heading+b'\nLength : 1 GiB for 0 h 1 min 0 s 0 ms</pre>'
   self.assertIsNone(self.parse(HTML+only_audio)['nfo_runtime_milliseconds'])
  for heading in (b'  Audio #0 : invented',b'  Text #0 : invented',b'  Subtitle #0 : invented'):
   old_syntax=b'<pre id="nfo_text">General\nTitle : invented\n'+heading+b'\nDuration : 00:01:00.000</pre>'
   self.assertIsNone(self.parse(HTML+old_syntax)['nfo_runtime_milliseconds'])
  conflicting=nfo.replace(b'Video #0 :',b'General : Another.invented.mkv\nLength : 2 GiB for 1 h 0 min 0 s 0 ms\nVideo #0 :')
  self.assertIsNone(self.parse(HTML+conflicting)['nfo_runtime_milliseconds'])
 def test_unlinked_or_missing_original_never_invents_target(self):
  from unittest.mock import Mock
  connection=Mock();connection.execute.return_value.fetchall.return_value=[]
  with self.assertRaisesRegex(ValueError,'host_listing_ambiguous_or_missing'):actor_listing(connection,'outcome-'+'a'*64,{'source':'fixture'},{},'fixture')

class CorrectedTests(ConnectedTests):
 SOURCE_HTML=HTML
 SOURCE_REVISION=2
 def test_connected_new_contract_has_typed_collector_and_truthful_review(self):
  self.complete()
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,self.selected['reservation']);plan,_=review.approved_plan(self.q,self.selected['reservation'])
  wire=build_film_prose(self.p);data=decode(wire['request']['input'][0]['content'][0]['text'],65536)
  row=next(x for x in data['evidence'] if x['kind']=='collector')
  self.assertEqual(row['facts']['title'],self.p['title']);self.assertEqual(row['facts']['year'],self.p['year'])
  self.assertNotIn('supervisor reviewed',wire['request']['instructions'].lower());self.assertTrue(all(x['facts'] for x in data['evidence']));self.assertIn('collector_imdb',row['facts']);self.assertIn('Collector claim:',card['text'])
  request,_=review.build(report,self.p,card)
  self.assertIn('unresolved assessment may be approved for REPORTING',request['instructions'])
  self.assertIn('not film verification',request['input'][0]['content'][0]['text']);self.assertNotIn('verified original listing',request['input'][0]['content'][0]['text'])
 def test_unresolved_card_keeps_material_blocker_and_claim_label(self):
  self.complete('reject')
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,self.selected['reservation'])
  report=copy.deepcopy(report);report['result'].update(status='unresolved',candidate=None,uncertainty='fragment',film_blockers=[dict(aspect='title',reason='conflicting_film_evidence',material_conflict='The listing title names another film.')])
  card=review.proposal(report,self.p,e['local_raw'],e['target_pin'],'a'*64)
  self.assertTrue(card['text'].startswith('Film identity unresolved.'));self.assertIn('Collector claim:',card['text']);self.assertIn('title / conflicting film evidence',card['summary']['uncertainty']);self.assertIn('another film',card['summary']['uncertainty'])
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'review_not_approved'):review.approved_plan(self.q,self.selected['reservation'])
 def test_real_conflict_still_refuses_supported_assessment(self):
  p=copy.deepcopy(self.p);p['listing']['title']='Unrelated Film'
  with self.assertRaises(ValueError):validate_film_prose(p,build_film_prose(p),self.f.answer_for(p),now=NOW)

class LegacyCorrectionTests(ConnectedTests):
 SOURCE_HTML=HTML
 def test_old_receipts_stable_and_correction_is_append_only_not_retry(self):
  self.complete('reject');prep=self.selected['reservation']
  with self.q.locked() as (rows,_):before=copy.deepcopy(rows)
  with patch('time.time',return_value=NOW):
   old=evidence.load(self.q,prep);self.assertNotIn('host_reporting_revision',old['projection'])
   report,_,card=review.assessment(self.q,prep);request,_=review.build(report,old['projection'],card)
   proof=evidence.record_correction(self.q,prep);again=evidence.record_correction(self.q,prep)
   self.assertEqual(proof,again);self.assertEqual(proof['proposal']['changed_fields'],['title','year','cast']);self.assertFalse(proof['proposal']['provider_execution_authorized'])
   self.assertEqual(review.build(*[report,old['projection'],card])[0],request)
  with self.q.locked() as (rows,_):self.assertEqual(rows[:-1],before);self.assertEqual(len(rows),len(before)+1)
  with self.assertRaisesRegex(ValueError,'queue_provider_consumed'):self.q.reserve_provider(prep,policy=self.policy,request_sha256='f'*64,evidence_sha256='e'*64,now=NOW)

class ExecutableCorrectionTests(ConnectedTests):
 SOURCE_HTML=HTML
 def corrected_fixture(self):
  self.complete('reject');oldprep=self.selected['reservation']
  oldhtml=(self.path/('report-'+oldprep+'.html')).read_bytes()
  with patch('time.time',return_value=NOW):
   proof=evidence.correction_proposal(self.q,oldprep)
   result=evidence.authorize_correction(self.q,oldprep,digest(proof))
   with self.assertRaisesRegex(ValueError,'host_correction_consumed'):evidence.authorize_correction(self.q,oldprep,digest(proof))
  newprep=result['preparation'];self.assertNotEqual(newprep,oldprep)
  path=self.path/('evidence-'+oldprep);bundle={k:(path/(k+'.bin')).read_bytes() for k in evidence.RAW_FIELDS}
  manifest=decode((path/'manifest.json').read_bytes(),65536)
  source=listing_facts(HTML,release_name='Invented release',case_id=CASE,version=VERSION,observed_at=NOW-1,expires_at=NOW+600,revision=2)
  bundle['source']=encoded(source);cat=decode(bundle['catalogue']);cat['observed_at']=NOW-1;bundle['catalogue']=encoded(cat)
  att=copy.deepcopy(manifest['attestation']);att['source_sha256']=hashlib.sha256(bundle['source']).hexdigest();att['catalogue_sha256']=hashlib.sha256(bundle['catalogue']).hexdigest();att['observed_at']=NOW
  bundle.update(attestation=att,target_pin=manifest['target_pin'],coverage=manifest['coverage'],derivation_revision=2)
  return oldprep,newprep,bundle,oldhtml
 def test_distinct_fresh_corrected_pair_keeps_old_receipts_and_reservations(self):
  oldprep,newprep,bundle,oldhtml=self.corrected_fixture()
  with patch('time.time',return_value=NOW):self.p=evidence._retain(self.q,newprep,bundle)['projection']
  self.selected={'reservation':newprep};self.complete()
  with patch('time.time',return_value=NOW):plan,_=review.approved_plan(self.q,newprep)
  self.assertIn('Collector claim:',plan['text']);self.assertEqual((self.path/('report-'+oldprep+'.html')).read_bytes(),oldhtml)
  with self.q.locked() as (rows,_):
   attempts=[r for r in rows if r['type']=='seedbox_provider_started_v1'];self.assertEqual(len(attempts),4);self.assertEqual(len({r['request_sha256'] for r in attempts}),4)
   self.assertTrue(all(r['reserved_usd']==[3,20] for r in attempts))
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'queue_provider_consumed'):self.execute()
 def bad_clock(self,field,clock):
  oldprep,newprep,bundle,_=self.corrected_fixture()
  value=decode(bundle[field]);value['observed_at']=clock;bundle[field]=encoded(value)
  bundle['attestation'][field+'_sha256']=hashlib.sha256(bundle[field]).hexdigest()
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'host_correction_observation_not_new'):evidence._retain(self.q,newprep,bundle)
  with self.q.locked() as (rows,_):self.assertEqual(sum(r['type']=='seedbox_provider_started_v1' for r in rows),2)
 def test_equal_source_clock_refuses_before_new_request(self):self.bad_clock('source',NOW-10)
 def test_older_catalogue_clock_refuses_before_new_request(self):self.bad_clock('catalogue',NOW-20)
 def test_uncertain_parent_record_refuses_even_with_completed_pair(self):
  self.complete('reject');prep=self.selected['reservation']
  with self.q.locked() as (_,append):append(dict(type='seedbox_review_uncertain_or_refused_v1',preparation=prep,at=NOW))
  with self.assertRaisesRegex(ValueError,'host_correction_uncertain_parent'):evidence.correction_proposal(self.q,prep)
 def test_approved_prior_review_cannot_authorize_correction(self):
  self.complete()
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'host_correction_rejected_review_required'):evidence.correction_proposal(self.q,self.selected['reservation'])


def load_tests(loader,tests,pattern):
 return unittest.TestSuite(cls(name) for cls in (ExtractionTests,CorrectedTests,LegacyCorrectionTests,ExecutableCorrectionTests) for name in cls.__dict__ if name.startswith('test_'))
