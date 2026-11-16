"""Invented ownership and absent movie lookup; never live source/model/send."""
import copy,hashlib,json,unittest
from unittest.mock import patch
from automation.seedbox_source_evidence import missing_movie_facts
from automation.seedbox_original_ownership import target,completed,pin
from test_seedbox_original_readiness import OriginalTests
from test_identity_triage import SOURCES
from test_snapshot_review import fixture,NOW,CASE,VERSION
from ai_movie_investigator.contracts import encoded,decode
from ai_movie_investigator import snapshot_review as review

class MissingTests(unittest.TestCase):
 def projection(self):
  snap,source,_,att=fixture();raw=encoded({'movie_results':[],'tv_results':[]})
  cat=encoded(missing_movie_facts(raw,requested_imdb='tt1234567',observed_at=NOW-2,expires_at=NOW+40))
  att.update(kind='host_authenticated_no_movie_mapping_v1',catalogue_crosswalk_verified=False,catalogue_sha256=hashlib.sha256(cat).hexdigest(),catalogue_original_sha256=hashlib.sha256(raw).hexdigest())
  p=review.projection(snap,att['snapshot_sha256'],CASE,VERSION,source,cat,att,now=NOW);p['host_reporting_revision']=2
  return p
 def test_observed_absence_reaches_model_without_supported_candidate(self):
  p=self.projection();self.assertIsNone(p['citation_eligible_pair']);built=review.build_film_prose(p)
  data=decode(built['request']['input'][0]['content'][0]['text'].encode())
  self.assertEqual(data['historical_observations']['catalogue']['movie_lookup']['crosswalk_verified'],False)
  self.assertIn('returned no movie mapping',built['request']['instructions'])
  self.assertIn(('ids','missing_film_evidence'),review.identity_blocker_pairs(p))
 def test_empty_error_missing_and_ambiguous_are_not_absence(self):
  for value in ({},{'movie_results':None},{'movie_results':{},'success':True},{'movie_results':[],'success':False},{'movie_results':[],'status_code':7},{'movie_results':[{'id':1}]},{'movie_results':[{'id':1},{'id':2}]}):
   with self.assertRaises(ValueError):missing_movie_facts(encoded(value),requested_imdb='tt1234567',observed_at=NOW-2,expires_at=NOW+40)

 def test_legacy_request_and_html_exact_pr212_bytes(self):
  # Independently generated from merge5545dc9 before this change.
  from test_snapshot_assessment import AssessmentTests
  from test_snapshot_report_readability import ReadabilityTests
  f=AssessmentTests();f.setUp();r=ReadabilityTests();r.setUp()
  for revision,request_sha,html_sha in ((None,'fb0f944d9643a6c47dae6a65ce0fc7c8732d8983698237827e26de0893fc8e0a','59f470e3b5fc6c170d5796acb6ab5e8915ada2ff8dc1f2523ade6ac6311cba39'),(2,'3ecf870df4bd496e564437c94c021301f0d0c5baface04cf129fad7cbf9f8e18','67863325ad242a4635ab85293bd71bd172725cbe0d4f1cac82966a21444b6fe0')):
   if revision:f.p['host_reporting_revision']=revision;r.p['host_reporting_revision']=revision
   self.assertEqual(hashlib.sha256(encoded(review.build_film_prose(f.p))).hexdigest(),request_sha)
   self.assertEqual(hashlib.sha256(r.show(r.make_report()).encode()).hexdigest(),html_sha)

class OwnershipTests(OriginalTests):
 def test_initial_receipt_permits_assessment_but_not_edit(self):
  with self.s.tx() as c:
   c.execute('update retry_messages set context=NULL,terminal=NULL,prepared=NULL,state="waiting",attempts=0 where version=?',(self.version,))
   c.execute('update retry_jobs set state="pending" where version=?',(self.version,))
   selected=target(c,self.version,SOURCES)
   config=dict(actor_database={'invented':True},sender={'invented':True},sources=SOURCES)
   chosen=pin(dict(target=selected),config)
   with self.assertRaisesRegex(ValueError,'telegram_original_incomplete'):completed(c,chosen,config)
   self.assertEqual(selected['ref'],self.ref)
 def test_owned_receipt_change_or_duplicate_refuses(self):
  with self.s.tx() as c:
   selected=target(c,self.version,SOURCES);config=dict(actor_database={},sender={},sources=SOURCES);chosen=pin(dict(target=selected),config)
   c.execute('update retry_messages set refs=? where version=?',(json.dumps([dict(self.ref,message_id=18)]),self.version))
   with self.assertRaisesRegex(ValueError,'ownership_changed'):completed(c,chosen,config)


class LifecycleTests(OriginalTests):
 def setUp(self):
  super().setUp()
  import time
  from pathlib import Path
  from test_identity_automation import context
  from identity_triage_observer import envelope
  from test_seedbox_credit_policy import CreditPolicyTests
  self.clock=time.time();self.now=self.clock;self.ctx=context(getattr(self,'INITIAL_REASON','tmdb_mapping_missing'),'needs_review' if getattr(self,'INITIAL_REASON',None)=='title_conflict' else 'unresolved')
  # Invented initial record; no production job is changed by this test.
  with self.s.tx() as c:
   body=json.loads(c.execute('select body from retry_jobs where version=?',(self.version,)).fetchone()[0])
   body['observation']=envelope(self.p,self.ctx,SOURCES)
   c.execute('update retry_jobs set body=?,state="pending",reason="tmdb_mapping_missing",due=?,until=NULL where version=?',(json.dumps(body),self.clock+21600,self.version))
   c.execute('update retry_messages set context=NULL,terminal=NULL,prepared=NULL,state="waiting",attempts=0 where version=?',(self.version,))
   for i in range(2):c.execute('insert into retry_attempts values(?,?,?,?,?)',((str(i+1)*32),self.version,self.clock-20+i,self.clock-19+i,'tmdb_mapping_missing'))
  root=Path(self.tmp.name).resolve();cookie=root/'cookie';cookie.write_text('{"fixture":"invented"}');cookie.chmod(0o600)
  env=root/'env';env.write_text('TELEGRAM_BOT_TOKEN=INVENTED_FIXTURE\nTELEGRAM_CHAT_ID=123\n');env.chmod(0o600)
  policy=CreditPolicyTests().policy();policy.update(observed_at=self.clock-100,delegated_at=self.clock-50,expires_at=self.clock+86400,credit_expires_at=self.clock+86400)
  names=('identity_triage_store.py','identity_triage_intake.py','identity_outcome_outbox.py','identity_triage_observer.py','retry_telegram.py','torrent_research_evidence.py','movie_intel_service.py','deploy/run.py')
  self.worker_outcome_context=self.ctx
  self.worker_config_extra=dict(credit_policy=policy,cookie_file=dict(path=str(cookie),sha256=hashlib.sha256(cookie.read_bytes()).hexdigest()),source_configuration=dict(path=str(env),sha256=hashlib.sha256(env.read_bytes()).hexdigest()),sender=dict(kind='main_selected_actor_topology_v1',revision='06d17aafefb5a5161364e4bf6f63667a649e1aa3',sole_edit_writer=True,single_serial_pump=True,no_original_binding_republication=True,acceptance_reference='invented:topology',observed_at=self.clock-1,expires_at=self.clock+86000,process={'pid':123},deployed_files={n:{'fixture':n} for n in names}))
  self.q,self.config,self.prep=self.worker_fixture();self.clock=time.time()+1;self.gets=[]
  self.html=b'<h2 id="torrentnameid">Invented release</h2><input name="imdbID" value="tt1234567"><div class="torrent-info-details"><h3>Example Movie (2020)</h3><div class="torrent-extra-info"><p>Cast: Actor One</p><p>Director: Director One</p><p>Runtime: 95 min</p></div></div>'
  self.html=self.html.replace(b'Invented release',self.metadata['name'].encode())
  self.lookup=encoded(dict(movie_results=[],tv_results=[]))
 def source(self,url,**kwargs):
  self.gets.append(url)
  if '/torrent/' in url:return self.html,self.clock
  self.assertIn('/find/tt1234567?',url);return self.lookup,self.clock
 def source_context(self):
  from contextlib import ExitStack
  stack=ExitStack();stack.enter_context(patch('time.time',side_effect=lambda:self.clock))
  stack.enter_context(patch('automation.seedbox_host_io._configuration',return_value=dict(TMDB_API_TOKEN='INVENTED',MOVIE_INTEL_TL_COOKIE_FILE=self.config['cookie_file']['path'],MOVIE_INTEL_TL_METADATA_ENABLED='1')))
  stack.enter_context(patch('automation.seedbox_host_io._get',side_effect=self.source))
  return stack
 def capture(self):
  from automation.seedbox_evidence import capture
  with self.source_context():return capture(self.q,self.config,self.prep)
 def models(self):
  from automation import seedbox_evidence,seedbox_automated_review as separate
  from automation.seedbox_worker import step
  from ai_movie_investigator.responses_http import ExplicitCredential
  from test_snapshot_assessment import AssessmentTests
  from test_responses_compatibility import documented
  from ai_movie_investigator.credit_test import MINI_MODEL
  import test_supervised_envelope as framing
  p=seedbox_evidence.load(self.q,self.prep)['projection'];f=AssessmentTests();f.setUp();a=f.answer_for(p,True)
  a['result']['primary_blocker'].update(reason='missing_film_evidence',support_considered='The listing supplies a title and cast for further review.',material_conflict='The authenticated exact IMDb lookup returned no movie mapping.')
  a['result']['rationale']='The exact authenticated IMDb lookup returned no movie mapping, so no catalogue candidate is supported.'
  built=review.build_film_prose(p);response=documented();response.update(model=MINI_MODEL,instructions=built['request']['instructions'],text=built['request']['text'],max_output_tokens=25000);response['output'][-1]['content'][0]['text']=encoded(a).decode()
  with patch('automation.seedbox_worker.load_key',return_value=ExplicitCredential('sk-INVENTED')),framing.wire(encoded(response)):self.assertTrue(step(self.q,self.config))
  report,e,card=separate.assessment(self.q,self.prep,card_revision=3);request,bindings=separate.build(report,e['projection'],card,revision=2)
  answer=dict(bindings,verdict='approve',reason='The report honestly preserves the missing catalogue mapping and does not propose a candidate.',evidence_findings=['The exact authenticated lookup contains no movie results.'],material_problems=[])
  response=documented();response.update(model=request['model'],instructions=request['instructions'],text=request['text'],max_output_tokens=25000);response['output'][-1]['content'][0]['text']=encoded(answer).decode()
  with patch('automation.seedbox_worker.load_key',return_value=ExplicitCredential('sk-INVENTED')),framing.wire(encoded(response)):self.assertTrue(step(self.q,self.config))
  return p
 def terminal(self,ingest=True):
  from identity_retry import run_one
  from identity_triage_store import Store
  from identity_triage_observer import envelope
  from identity_triage_intake import normalize
  from datetime import datetime,timezone
  import retry_telegram
  self.clock+=21601;self.now=self.clock
  def timed(*args):
   self.clock+=0.1;self.now=self.clock
   result=envelope(*args);result['timestamp']=datetime.fromtimestamp(self.clock,timezone.utc).isoformat().replace('+00:00','Z')
   self.clock+=0.1;self.now=self.clock;return result
  with patch('identity_retry.envelope',side_effect=timed):self.assertTrue(run_one(self.s,lambda _:self.ctx))
  pending=self.s.next();self.assertIsNotNone(pending)
  self.terminal_raw=pending[1];collector=Store(__import__('pathlib').Path(self.config['collector_database']['path']).parent)
  held=self.enterContext(collector.connection())
  if ingest:collector.ingest(normalize(pending[1],SOURCES,'outcome'),'outcome')
  self.s.ack(pending[0]);retry_telegram.pump(self.s,lambda *a:{'text':'ordinary terminal','token':None},lambda *a:None)
  self.clock+=121;self.now=self.clock
 def test_early_models_quiet_wait_terminal_handoff_and_one_edit(self):
  import io
  from pathlib import Path
  from automation.seedbox_worker import step
  with self.source_context():
   self.capture();self.models()
   htmlpath=self.q.path/('report-'+self.prep+'.html');html=htmlpath.read_bytes();self.assertIn(b'no movie mapping',html)
   with self.q.locked() as (rows,_):reports=[r for r in rows if r['type'] in ('seedbox_assessment_pending_review_v1','seedbox_automated_review_completed_v1')]
   with patch('automation.seedbox_worker.load_key',side_effect=AssertionError('regeneration')):
    step(self.q,self.config)
    with self.q.locked() as (rows,_):waiting=list(rows)
    step(self.q,self.config)
    with self.q.locked() as (rows,_):self.assertEqual(rows,waiting);self.assertFalse(any(r['type']=='seedbox_operation_blocked_v1' for r in rows))
    self.assertEqual(len(self.gets),2)
    self.terminal();requests=[]
    from automation.seedbox_host_io import database
    from automation.seedbox_assessment_queue import collector_page
    with database(self.config['collector_database']) as c:collector_page(c,0)
    def http(req,timeout):
     requests.append(json.loads(req.data));out=io.BytesIO(b'{"ok":true,"result":{}}');out.status=200;return out
    with patch('automation.seedbox_sender._process',return_value={'pid':123}),patch('automation.seedbox_sender._deployed',side_effect=lambda p:Path(p['fixture']).read_bytes()),patch('automation.reviewed_telegram_UNISSUED.urlopen',side_effect=http):
     step(self.q,self.config)
     with self.q.locked() as (rows,_):self.assertFalse(any(r['type']=='seedbox_operation_blocked_v1' for r in rows),rows[-4:])
     self.assertEqual(len(requests),1,rows[-5:]);self.assertEqual(requests[0]['message_id'],17);self.assertEqual(len(self.gets),4)
     step(self.q,self.config);self.assertEqual(len(requests),1);self.assertEqual(len(self.gets),4)
   self.assertEqual(htmlpath.read_bytes(),html)
   with self.q.locked() as (rows,_):
    self.assertEqual([r for r in rows if r['type'] in ('seedbox_assessment_pending_review_v1','seedbox_automated_review_completed_v1')],reports)
    self.assertEqual(sum(r['type']=='seedbox_provider_started_v1' for r in rows),2)
    self.assertEqual(sum(r['type']=='seedbox_delivery_revalidation_started_v1' for r in rows),1)

 def test_acquisition_rejects_error_missing_multiple_not_empty_evidence(self):
  from automation.seedbox_host_io import database,selected_snapshot,acquire
  from ai_movie_investigator.contracts import digest
  with self.q.locked() as (rows,_):claim=next(r for r in rows if r['type']=='seedbox_preparation_claimed_v1')
  claim=dict(claim,ownership_admission=True)
  with self.source_context():
   with database(self.config['collector_database']) as c:raw,metadata,_=selected_snapshot(c,claim['case_id'],self.clock)
   for value in ({},{'movie_results':[],'success':False},{'movie_results':[],'status_code':7},{'movie_results':[{'id':1},{'id':2}]},{'movie_results':None}):
    self.lookup=encoded(value)
    with self.subTest(value=value),self.assertRaisesRegex(ValueError,'host_catalogue_ambiguous'):acquire(self.config,claim,raw,metadata)
   self.lookup=encoded({'movie_results':[]});bundle=acquire(self.config,claim,raw,metadata)
   self.assertFalse(bundle['attestation']['catalogue_crosswalk_verified']);self.assertIsNone(bundle['projection']['citation_eligible_pair'])
   self.assertTrue(all('/movie/' not in u for u in self.gets))
 def test_terminal_without_collector_outcome_waits_no_source_or_models(self):
  from automation.seedbox_assessment_handoff import before_delivery
  with self.source_context():
   self.capture();self.models();self.terminal(ingest=False)
   self.assertFalse(before_delivery(self.q,self.config,self.prep));self.assertEqual(len(self.gets),2)
   with self.q.locked() as (rows,_):old=list(rows)
   self.assertFalse(before_delivery(self.q,self.config,self.prep))
   with self.q.locked() as (rows,_):self.assertEqual(rows,old)
 def test_changed_listing_burns_one_handoff_without_regeneration(self):
  from automation.seedbox_assessment_handoff import before_delivery
  with self.source_context():
   self.capture();self.models();self.terminal();self.html=self.html.replace(b'Actor One',b'Changed Person')
   with self.assertRaisesRegex(ValueError,'delivery_material_facts_changed'):before_delivery(self.q,self.config,self.prep)
   calls=len(self.gets)
   with self.assertRaises(ValueError):before_delivery(self.q,self.config,self.prep)
   self.assertEqual(len(self.gets),calls)
   with self.q.locked() as (rows,_):
    self.assertEqual(sum(r['type']=='seedbox_provider_started_v1' for r in rows),2)
    self.assertEqual(sum(r['type']=='seedbox_delivery_revalidation_started_v1' for r in rows),1)
    self.assertFalse(any(r['type']=='seedbox_sender_started_v1' for r in rows))
 def test_unlinked_expiry_and_new_same_release_event_refuse(self):
  import uuid
  from identity_triage_store import Store
  from identity_triage_intake import normalize
  from pathlib import Path
  from automation.seedbox_assessment_handoff import observe,verify_collector
  from automation.seedbox_host_io import database
  with self.source_context():
   self.capture();self.models();self.terminal();proof=observe(self.q,self.config,self.prep)
   collector=Store(Path(self.config['collector_database']['path']).parent)
   new=copy.deepcopy(self.p);new['id']=str(uuid.uuid4());collector.ingest(normalize(new,SOURCES,'release_new'),'release_new')
   with database(self.config['collector_database']) as c:
    with self.assertRaisesRegex(ValueError,'handoff_new_or_unknown_occurrence'):verify_collector(c,proof)
   with self.assertRaisesRegex(ValueError,'handoff_new_or_unknown_occurrence'):observe(self.q,self.config,self.prep)
 def test_unlinked_terminal_uuid_refuses(self):
  import uuid
  from pathlib import Path
  from identity_triage_store import Store
  from identity_triage_intake import normalize
  from automation.seedbox_assessment_handoff import observe
  with self.source_context():
   self.capture();self.models();self.terminal(ingest=False)
   event=copy.deepcopy(self.terminal_raw);event['id']=str(uuid.uuid4())
   Store(Path(self.config['collector_database']['path']).parent).ingest(normalize(event,SOURCES,'outcome'),'outcome')
   with self.assertRaisesRegex(ValueError,'handoff_retry_link'):observe(self.q,self.config,self.prep)
 def test_explicit_early_recovery_preserves_unknown_old_attempt(self):
  from automation.seedbox_original_readiness import recovery_proposal,recover
  from automation.seedbox_worker import reconcile_source_interruptions
  with self.source_context():
   with self.q.locked() as (rows,append):
    append(dict(type='seedbox_source_started_v1',preparation=self.prep,at=self.clock-10))
    append(dict(type='seedbox_operation_blocked_v1',preparation=self.prep,diagnostic=dict(reason='unexpected_exception'),at=self.clock-9))
   proof=recovery_proposal(self.q,self.config,self.prep,assessment=True)
   self.assertEqual(proof['historical_source_outcome'],'unknown');self.assertEqual(proof['view']['purpose'],'assessment')
   with self.q.locked() as (rows,_):old=list(rows)
   recover(self.q,self.config,self.prep,review.digest(proof),assessment=True);reconcile_source_interruptions(self.q)
   with self.q.locked() as (rows,_):self.assertEqual(rows[:-1],old)
   self.capture();self.assertEqual(len(self.gets),2)
 def test_tied_terminal_attempt_and_changed_ownership_refuse(self):
  from automation.seedbox_assessment_handoff import observe
  with self.source_context():
   self.capture();self.models();self.terminal()
   with self.s.tx() as c:
    row=c.execute('select version,started,ended,reason from retry_attempts order by started desc limit 1').fetchone()
    c.execute('insert into retry_attempts values(?,?,?,?,?)',('e'*32,*row))
   with self.assertRaisesRegex(ValueError,'handoff_retry_link'):observe(self.q,self.config,self.prep)
   with self.s.tx() as c:
    c.execute('delete from retry_attempts where id=?',('e'*32,))
    c.execute('update retry_messages set refs=? where version=?',(json.dumps([dict(self.ref,message_id=88)]),self.version))
   with self.assertRaisesRegex(ValueError,'ownership_changed'):observe(self.q,self.config,self.prep)
 def test_installed_ownership_lookup_and_terminal_lineage_failure(self):
  import subprocess,sys
  from pathlib import Path
  from automation.seedbox_package import build
  with self.source_context():
   self.capture();self.models();self.terminal()
   runtime=Path(self.tmp.name).resolve()/'runtime';runtime.mkdir(mode=0o700);result=build(Path.cwd(),runtime)
   driver="""
import sys,json,os,errno,socket
from pathlib import Path
sys.path.insert(0,sys.argv[1])
if sys.platform.startswith('linux'):
 def absent(*a,**k):raise OSError(errno.ENODATA,'fixture absent ACL')
 os.getxattr=absent
from unittest.mock import patch
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('real socket'))
from automation.seedbox_assessment_queue import Queue
from automation.seedbox_assessment_handoff import observe,before_delivery,retained
from ai_movie_investigator.snapshot_review import build_film_prose
q=Queue(sys.argv[2]);config=json.loads((q.path/'configuration.json').read_bytes());prep=sys.argv[3]
with patch('time.time',return_value=float(sys.argv[4])):
 evidence=retained(q,prep);assert evidence['projection']['catalogue_lookup_status'];assert build_film_prose(evidence['projection'])['request']['input']
 proof=observe(q,config,prep);assert proof['lineage']['links'];assert proof['lineage']['current_anchor']['material']['route']=='review_only'
 with patch('automation.seedbox_host_io._configuration',side_effect=ValueError('invented refusal')):
  try:before_delivery(q,config,prep)
  except ValueError:pass
  else:raise AssertionError('failure accepted')
 with q.locked() as (rows,_):assert sum(r['type']=='seedbox_delivery_revalidation_failed_v1' for r in rows)==1
print('installed early ownership, lookup, terminal lineage and failure verified')
"""
   r=subprocess.run([sys.executable,'-I','-B','-c',driver,str(runtime),str(self.q.path),self.prep,str(self.clock)],capture_output=True,text=True,timeout=30)
   self.assertEqual(r.returncode,0,r.stderr);self.assertIn('terminal lineage and failure verified',r.stdout)
   r=subprocess.run([sys.executable,'-I','-B',str(runtime/'automation/seedbox_bootstrap.py'),str(runtime/'seedbox-runtime.json'),result['manifest_sha256'],'verify'],capture_output=True,text=True,timeout=30)
   self.assertEqual(r.returncode,0,r.stderr)

class CompletedTests(LifecycleTests):
 INITIAL_REASON='title_conflict'
 def test_completed_original_before_capture_proves_terminal_at_old_cursor(self):
  from automation.seedbox_assessment_handoff import before_delivery,observe
  with self.source_context():
   self.terminal();self.capture();self.models();proof=observe(self.q,self.config,self.prep)
   self.assertTrue(proof['lineage']['links']);self.assertTrue(before_delivery(self.q,self.config,self.prep));self.assertEqual(len(self.gets),2)
   self.assertLessEqual(proof['lineage']['links'][-1]['cursor'],proof['lineage']['current_anchor']['delivery_cursor'])

 def test_fresh_completed_sender_rechecks_new_delivery_under_final_boundary(self):
  import uuid
  from pathlib import Path
  from identity_triage_store import Store
  from identity_triage_intake import normalize
  from automation.seedbox_sender import deliver_reviewed
  from automation.seedbox_assessment_handoff import before_delivery
  with self.source_context():
   self.terminal();self.capture();self.models();self.assertTrue(before_delivery(self.q,self.config,self.prep));checks=[]
   def process(_):
    checks.append(True)
    if len(checks)==2:
     event=copy.deepcopy(self.p);event['id']=str(uuid.uuid4())
     Store(Path(self.config['collector_database']['path']).parent).ingest(normalize(event,SOURCES,'release_new'),'release_new')
    return {'pid':123}
   with patch('automation.seedbox_sender._process',side_effect=process),patch('automation.seedbox_sender._deployed',side_effect=lambda p:Path(p['fixture']).read_bytes()),patch('automation.reviewed_telegram_UNISSUED.urlopen',side_effect=AssertionError('must not send')) as http:
    result=deliver_reviewed(self.q,self.config,self.prep);self.assertEqual(result['status'],'uncertain');http.assert_not_called()
    again=deliver_reviewed(self.q,self.config,self.prep);self.assertEqual(again['status'],'uncertain_or_previously_started');http.assert_not_called()

def load_tests(loader,tests,pattern):
 return unittest.TestSuite(cls(n) for cls in (MissingTests,OwnershipTests,LifecycleTests,CompletedTests) for n in cls.__dict__ if n.startswith('test_'))
