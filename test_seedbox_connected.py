"""Connected retained-source → real v13 wire → second review → plan fixtures.

Only invented bytes and fake sockets. No real source, API, key or Telegram use.
"""
import copy,hashlib,json,unittest
from unittest.mock import patch
from ai_movie_investigator.contracts import encoded,decode,digest
from ai_movie_investigator.responses_http import ExplicitCredential
from ai_movie_investigator import seedbox_authorization as host
from automation import seedbox_evidence as evidence,seedbox_automated_review as review
from automation.seedbox_source_evidence import listing_facts,catalogue_facts
import test_seedbox_assessment_execution as base
from test_snapshot_review import fixture,NOW,CASE,VERSION
from test_responses_compatibility import documented
import test_supervised_envelope as framing

class ConnectedTests(base.HostExecutionTests):
 def setUp(self):
  super().setUp()
  snap,_,_,att=fixture();value=decode(snap,1048576)
  value.update(kind='seedbox_selected_snapshot_v1',selected_case_id=CASE)
  value['coverage'].update(assessed_release_cases=7,routes={'eligible':7},correlation={'strong_source_id':7})
  snap=encoded(value)
  raw=b'<h2 id="torrentnameid">Invented release</h2><input name="imdbID" value="tt1234567"><div class="torrent-info-details"><h3>Example Movie (2020)</h3><div class="torrent-extra-info"><p>Cast: Actor One</p><p>Director: Director One</p><p>Runtime: 95 min</p></div></div>'
  raw=getattr(self,'SOURCE_HTML',raw)
  cat=encoded(dict(id=123,imdb_id='tt1234567',title='Example Movie',runtime=94,credits=dict(cast=[dict(name='Actor One',order=0)],crew=[dict(name='Director One',job='Director')]),release_dates=dict(results=[dict(release_dates=[dict(type=3,release_date='2021-01-01T00:00:00Z')])])))
  source=encoded(listing_facts(raw,release_name='Invented release',case_id=CASE,version=VERSION,observed_at=NOW-10,expires_at=NOW+600,revision=getattr(self,'SOURCE_REVISION',1)))
  catalogue=encoded(catalogue_facts(cat,expected_tmdb=123,expected_imdb='tt1234567',observed_at=NOW-9,expires_at=NOW+600))
  h=lambda b:hashlib.sha256(b).hexdigest()
  att.update(kind='host_authenticated_normalized_case_v1',snapshot_sha256=h(snap),source_sha256=h(source),catalogue_sha256=h(catalogue),source_original_sha256=h(raw),catalogue_original_sha256=h(cat),expires_at=NOW+600)
  self.local=encoded(dict(tracker_url='https://www.torrentleech.org/torrent/123',release_name='Invented release',nfo_text=''))
  bundle=dict(source_original=raw,catalogue_original=cat,find_original=encoded(dict(movie_results=[dict(id=123)])),snapshot=snap,source=source,catalogue=catalogue,local_raw=self.local,attestation=att,target_pin=getattr(self,'fixture_target',dict(version='c'*64,row_sha256='d'*64,ref=dict(chat_id='123',message_id=17,kind='text'),case_id=CASE)),coverage=dict(global_collector=value['coverage']))
  if getattr(self,'SOURCE_REVISION',1)==2:bundle['derivation_revision']=2
  with patch('time.time',return_value=NOW):self.p=evidence._retain(self.q,self.selected['reservation'],bundle)['projection']
 def execute(self):
  with patch('automation.seedbox_evidence.verify_current'):
   return host.execute(self.q,self.selected['reservation'],policy=self.policy,credential=ExplicitCredential('sk-SYNTHETIC_FIXTURE'))
 def complete(self,verdict='approve'):
  with patch('time.time',return_value=NOW),framing.wire(self.wire()):self.execute()
  with patch('time.time',return_value=NOW):report,e,card=review.assessment(self.q,self.selected['reservation'],card_revision=2)
  request,bindings=review.build(report,e['projection'],card,revision=2)
  answer=dict(bindings,verdict=verdict,reason='The separate observations support the proposed film and preserve edition uncertainty.',evidence_findings=['The listing and catalogue share the same IMDb crosswalk.'],material_problems=[] if verdict=='approve' else ['The proposal needs an owner audit.'])
  response=documented();response.update(model=request['model'],instructions=request['instructions'],text=request['text'],max_output_tokens=25000)
  response['output'][-1]['content'][0]['text']=encoded(answer).decode()
  with patch('time.time',return_value=NOW),patch('automation.seedbox_evidence.verify_current'),framing.wire(encoded(response)):
   review.execute(self.q,self.selected['reservation'],policy=self.policy,credential=ExplicitCredential('sk-SYNTHETIC_FIXTURE'))
 def test_separate_review_two_receipts_and_private_html(self):
  self.complete()
  with patch('time.time',return_value=NOW):plan,target=review.approved_plan(self.q,self.selected['reservation'])
  self.assertIn('Example Movie (2021)',plan['text']);self.assertIn('Collector claim:',plan['text']);self.assertFalse(plan['download_approved'])
  self.assertTrue((self.path/('report-'+self.selected['reservation']+'.html')).is_file())
  with self.q.locked() as (rows,_):
   attempts=[r for r in rows if r['type']=='seedbox_provider_started_v1'];self.assertEqual([r['stage'] for r in attempts],['assessment','review']);self.assertNotEqual(attempts[0]['request_sha256'],attempts[1]['request_sha256'])
 def test_rejection_cannot_yield_plan(self):
  self.complete('reject')
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'review_not_approved'):review.approved_plan(self.q,self.selected['reservation'])
 def test_changed_crosswalk_original_refuses_before_wire(self):
  path=self.path/('evidence-'+self.selected['reservation'])/'find_original.bin';path.write_bytes(b'{"movie_results":[]}')
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'host_evidence_changed'):self.execute()
  with self.q.locked() as (rows,_):self.assertFalse(any(r['type']=='seedbox_provider_started_v1' for r in rows))
 def test_superseded_claim_refuses_before_wire(self):
  with self.q.locked() as (_,append):append(dict(type='seedbox_preparation_superseded_v1',preparation=self.selected['reservation'],new_version='f'*64,at=NOW))
  with patch('time.time',return_value=NOW),self.assertRaisesRegex(ValueError,'queue_preparation_superseded'):self.execute()
 def test_scoped_snapshot_does_not_rewrite_global_coverage(self):
  from identity_research_handoff import validate_host_snapshot,validate_snapshot
  with patch('time.time',return_value=NOW):value=decode(evidence.load(self.q,self.selected['reservation'])['snapshot_raw'],1048576)
  self.assertEqual(validate_host_snapshot(value,NOW)['coverage']['assessed_release_cases'],7)
  with self.assertRaises(ValueError):validate_snapshot(value,NOW)

if __name__=='__main__':unittest.main()

class InstalledTests(ConnectedTests):
 def test_installed_only_nonempty_derivation_and_changed_evidence(self):
  import os,subprocess,sys,tempfile
  from pathlib import Path
  from automation.seedbox_package import build
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as d:
   root=Path(d).resolve();root.chmod(0o700);result=build(Path.cwd(),root)
   driver=root/'fixture-driver.py'
   driver.write_text('''import sys,errno,os\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nif sys.platform.startswith('linux'):\n def absent(*a,**kw):raise OSError(errno.ENODATA,'invented ACL absence')\n os.getxattr=absent\nfrom automation.seedbox_assessment_queue import Queue\nfrom automation.seedbox_evidence import load\nfrom ai_movie_investigator.snapshot_review import build_film_prose\nq=Queue(sys.argv[2]);p=load(q,sys.argv[3],now=float(sys.argv[4]));assert build_film_prose(p['projection'])['request']['input']\npath=q.path/('evidence-'+sys.argv[3])/'find_original.bin';path.write_bytes(b'CHANGED')\ntry:load(q,sys.argv[3],now=float(sys.argv[4]))\nexcept ValueError:pass\nelse:raise AssertionError('changed crosswalk accepted')\nprint('installed_nonempty_derivation_and_failure_verified')\n''')
   driver.chmod(0o600)
   r=subprocess.run([sys.executable,'-I','-B',str(driver),str(root),str(self.path),self.selected['reservation'],str(NOW)],capture_output=True,timeout=30)
   self.assertEqual(r.returncode,0,r.stderr.decode());self.assertIn(b'installed_nonempty',r.stdout)
   r=subprocess.run([sys.executable,'-I','-B',str(root/'automation/seedbox_bootstrap.py'),str(root/'seedbox-runtime.json'),result['manifest_sha256'],'verify'],capture_output=True,timeout=30)
   self.assertEqual(r.returncode,0,r.stderr.decode())
   (root/'automation/seedbox_worker.py').unlink()
   r=subprocess.run([sys.executable,'-I','-B',str(root/'automation/seedbox_bootstrap.py'),str(root/'seedbox-runtime.json'),result['manifest_sha256'],'verify'],capture_output=True,timeout=30)
   self.assertNotEqual(r.returncode,0)

class ReportRecoveryTests(ConnectedTests):
 def test_report_recreated_before_review_from_exact_retained_bytes(self):
  with patch('time.time',return_value=NOW),framing.wire(self.wire()):self.execute()
  path=self.path/('report-'+self.selected['reservation']+'.html');old=path.read_bytes();path.unlink()
  with patch('time.time',return_value=NOW):review.assessment(self.q,self.selected['reservation'])
  self.assertEqual(path.read_bytes(),old)
  with self.q.locked() as (rows,_):self.assertEqual(sum(r['type']=='seedbox_provider_started_v1' for r in rows),1)

class RateLimitTests(ConnectedTests):
 def test_provider_429_retains_attempt_and_pauses_new_cases(self):
  code=framing.wire_code().replace("status=401 if variant=='rejected' else 200",'status=429')
  ns={'selected_raw':b'{}','framing':'length'};exec(code,ns)
  with patch('time.time',return_value=NOW),ns['wire_fixture']('completed'),self.assertRaisesRegex(ValueError,'host_assessment_uncertain'):
   self.execute()
  from automation.seedbox_circuit import active
  from automation.seedbox_worker import step
  with self.q.locked() as (rows,_):
   self.assertEqual(active(rows)[0]['reason'],'responses_http_429');self.assertEqual(sum(r['type']=='seedbox_provider_started_v1' for r in rows),1)
  with patch('automation.seedbox_worker.database',side_effect=AssertionError('must not acquire')):
   self.assertFalse(step(self.q,{}))


def load_tests(loader,tests,pattern):
 suite=unittest.TestSuite(loader.loadTestsFromTestCase(ConnectedTests))
 for cls,names in ((InstalledTests,['test_installed_only_nonempty_derivation_and_changed_evidence']),
                   (ReportRecoveryTests,['test_report_recreated_before_review_from_exact_retained_bytes']),
                   (RateLimitTests,['test_provider_429_retains_attempt_and_pauses_new_cases'])):
  suite.addTests(cls(name) for name in names)
 return suite
