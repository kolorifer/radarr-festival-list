"""Invented delayed original lifecycle; actual local source/worker boundary."""
import copy,json,time,unittest
from unittest.mock import patch
from ai_movie_investigator.contracts import digest
from automation.seedbox_original_readiness import binding,OriginalWait,transition,diagnostic
from test_reviewed_telegram_operator import DeliveryTests
from test_identity_triage import SOURCES
from identity_triage_intake import normalize

class OriginalTests(DeliveryTests):
 def setUp(self):
  super().setUp()
  with self.s.tx() as c:
   body=json.loads(c.execute('select body from retry_jobs where version=?',(self.version,)).fetchone()[0])
  self.metadata=normalize(body['observation'],SOURCES,'outcome')['metadata']
 def inspect(self):
  with self.s.tx() as c:return binding(c,self.pin['case_id'],self.metadata,SOURCES,self.metadata['source'])
 def test_delayed_original_complete_and_quiescent(self):
  with self.s.tx() as c:
   saved=c.execute('select context,prepared,terminal from retry_messages where version=?',(self.version,)).fetchone()
   c.execute('update retry_messages set context=NULL,prepared=NULL,terminal=NULL,state="waiting",attempts=0 where version=?',(self.version,))
   c.execute('update retry_jobs set state="pending",until=NULL where version=?',(self.version,))
  with self.assertRaises(OriginalWait) as error:self.inspect()
  first=error.exception.view;self.assertEqual(first['reason'],'telegram_original_incomplete')
  with self.assertRaises(OriginalWait) as error:self.inspect()
  self.assertEqual(error.exception.view,first)
  with self.s.tx() as c:c.execute('update retry_messages set context=?,prepared=?,terminal=? where version=?',(*saved,self.version))
  with self.assertRaises(OriginalWait) as error:self.inspect()
  self.assertEqual(error.exception.view['reason'],'telegram_original_not_quiescent');self.assertNotEqual(error.exception.view['local_sha256'],first['local_sha256'])
  with self.s.tx() as c:
   c.execute('update retry_messages set state="edited",attempts=1 where version=?',(self.version,))
   c.execute('update retry_jobs set state="done" where version=?',(self.version,))
  selected,view=self.inspect();self.assertEqual(view['status'],'ready');self.assertEqual(selected['actor_version'],self.version)
 def test_old_different_metadata_does_not_shadow_selected_version(self):
  with self.s.tx() as c:
   row=list(c.execute('select * from retry_jobs where version=?',(self.version,)).fetchone())
   body=json.loads(row[3]);body['observation']['data']['release']['title']='Earlier title'
   row[0]='0'*64;row[3]=json.dumps(body);row[6]='done';row[-1]='superseded'
   c.execute('insert into retry_jobs values (?,?,?,?,?,?,?,?,?,?)',row)
  selected,view=self.inspect();self.assertEqual(selected['actor_version'],self.version);self.assertEqual(view['status'],'ready')
 def test_invalid_duplicate_consumed_or_payload_not_a_wait(self):
  with self.s.tx() as c:c.execute('update retry_messages set state="reviewed_reserved" where version=?',(self.version,))
  with self.assertRaisesRegex(ValueError,'original_wait_invalid_lifecycle'):self.inspect()
  with self.s.tx() as c:
   c.execute('update retry_messages set state="edited",refs=? where version=?',(json.dumps([self.ref,self.ref]),self.version))
  with self.assertRaisesRegex(ValueError,'telegram_single_original_required'):self.inspect()
 def test_finite_diagnostic_does_not_echo(self):
  self.assertEqual(diagnostic(RuntimeError('PRIVATE'), 'source_local')['reason'],'source_unclassified')

 def worker_fixture(self):
  from pathlib import Path
  from identity_triage_store import Store
  from identity_triage_observer import envelope
  from automation.seedbox_assessment_queue import Queue,collector_page
  from automation.seedbox_host_io import selected_snapshot
  from test_seedbox_credit_policy import CreditPolicyTests
  root=Path(self.tmp.name).resolve();collector=Store(root/'collector')
  collector.ingest(normalize(self.p,SOURCES,'release_new'),'release_new')
  from test_identity_automation import context
  collector.ingest(normalize(envelope(self.p,context('title_conflict','needs_review'),SOURCES),SOURCES,'outcome'),'outcome')
  state=root/'queue';state.mkdir(mode=0o700)
  def pin(path):
   st=path.stat();return dict(path=str(path),identity=[st.st_dev,st.st_ino])
  config=dict(state=str(state),collector_database=pin(collector.path),actor_database=pin(self.s.path),collector_identity='a'*64,source_attempt_limit=3,source_configuration={},sources=SOURCES,listing_source=self.metadata['source'])
  Queue.enroll(state,collector_identity='a'*64,prior_consumed_cases=[],prior_history_sha256='b'*64,prior_credit_sha256='c'*64,delegated_policy=CreditPolicyTests().policy(),configuration_sha256=digest(config))
  q=Queue(state)
  with collector.connection(readonly=True) as c:
   page=collector_page(c,0);raw,_,_=selected_snapshot(c,self.pin['case_id'],time.time())
  q.ingest(page,collector_identity='a'*64);selected=q.reserve(raw,now=time.time())
  self.assertIn('reservation',selected)
  return q,config,selected['reservation']
 def test_worker_wait_is_quiet_then_material_completion_enters_source_once(self):
  from automation.seedbox_worker import step
  from automation.seedbox_host_io import SourceFailure
  q,config,prep=self.worker_fixture()
  with self.s.tx() as c:
   old=c.execute('select context,prepared,terminal from retry_messages where version=?',(self.version,)).fetchone()
   c.execute('update retry_messages set context=NULL,prepared=NULL,terminal=NULL where version=?',(self.version,))
  with patch('automation.seedbox_host_io._configuration',side_effect=AssertionError('credentials before original ready')) as credentials:
   step(q,config)
   with q.locked() as (rows,_):first=list(rows)
   step(q,config)
   with q.locked() as (rows,_):self.assertEqual(rows,first)
   self.assertFalse(credentials.called)
  with q.locked() as (rows,_):self.assertFalse(any(r['type']=='seedbox_source_started_v1' for r in rows))
  with self.s.tx() as c:c.execute('update retry_messages set context=?,prepared=?,terminal=? where version=?',(*old,self.version))
  # The actual capture/acquire local checks run; stop at invented configuration.
  with patch('automation.seedbox_host_io._configuration',side_effect=SourceFailure('source_configuration_unavailable')) as credentials:
   step(q,config);self.assertEqual(credentials.call_count,1)
  with q.locked() as (rows,_):
   self.assertEqual(sum(r['type']=='seedbox_source_started_v1' for r in rows),1)
   self.assertFalse(any(r['type']=='seedbox_provider_started_v1' for r in rows))
 def test_explicit_recovery_binds_unknown_history_and_current_local_original(self):
  from automation.seedbox_original_readiness import recovery_proposal,recover
  from automation.seedbox_worker import reconcile_source_interruptions
  q,config,prep=self.worker_fixture()
  with q.locked() as (rows,append):
   append(dict(type='seedbox_source_started_v1',preparation=prep,at=time.time()))
   append(dict(type='seedbox_operation_blocked_v1',preparation=prep,diagnostic=dict(reason='unexpected_exception',phase='preflight'),at=time.time()))
  proposal=recovery_proposal(q,config,prep);self.assertEqual(proposal['historical_source_outcome'],'unknown')
  with self.assertRaisesRegex(ValueError,'original_recovery_changed'):recover(q,config,prep,'a'*64)
  with q.locked() as (rows,_):before=list(rows)
  recover(q,config,prep,digest(proposal));reconcile_source_interruptions(q)
  with q.locked() as (rows,_):
   self.assertEqual(rows[:len(before)],before);self.assertEqual(len(rows),len(before)+1)
  with self.assertRaisesRegex(ValueError,'original_recovery_consumed'):recover(q,config,prep,digest(proposal))
 def test_recovery_refuses_pending_or_changed_original_and_consumed_case(self):
  from automation.seedbox_original_readiness import recovery_proposal,recover
  q,config,prep=self.worker_fixture()
  with q.locked() as (rows,append):append(dict(type='seedbox_operation_blocked_v1',preparation=prep,diagnostic=dict(reason='unexpected_exception'),at=time.time()))
  proposal=recovery_proposal(q,config,prep)
  with self.s.tx() as c:c.execute('update retry_messages set prepared=? where version=?',(json.dumps({'text':'changed','token':None}),self.version))
  with self.assertRaisesRegex(ValueError,'original_recovery_changed'):recover(q,config,prep,digest(proposal))
  with q.locked() as (rows,append):append(dict(type='seedbox_provider_started_v1',preparation=prep,case_id=self.pin['case_id'],stage='assessment'))
  with self.assertRaisesRegex(ValueError,'original_recovery_consumed'):recovery_proposal(q,config,prep)

 def test_installed_worker_wait_and_material_progress_without_ambient_source(self):
  import subprocess,sys
  from pathlib import Path
  from automation.seedbox_package import build
  q,config,prep=self.worker_fixture();root=Path(self.tmp.name).resolve()
  with self.s.tx() as c:
   saved=c.execute('select context,prepared,terminal from retry_messages where version=?',(self.version,)).fetchone()
   c.execute('update retry_messages set context=NULL,prepared=NULL,terminal=NULL where version=?',(self.version,))
  runtime=root/'runtime';runtime.mkdir(mode=0o700);build(Path.cwd(),runtime)
  fixture=root/'fixture.json';fixture.write_text(json.dumps(dict(config=config,preparation=prep,version=self.version,saved=saved)))
  script="""
import sys,json,os,errno,sqlite3,socket
from pathlib import Path
sys.path.insert(0,sys.argv[1])
if sys.platform.startswith('linux'):
 def absent(*a,**k):raise OSError(errno.ENODATA,'invented fixture ACL absence')
 os.getxattr=absent
from unittest.mock import patch
from automation.seedbox_assessment_queue import Queue
from automation.seedbox_worker import step
from automation.seedbox_host_io import SourceFailure
import automation.seedbox_original_readiness as ready
assert Path(ready.__file__).is_relative_to(Path(sys.argv[1]))
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('real socket'))
f=json.load(open(sys.argv[2]));q=Queue(f['config']['state'])
with patch('automation.seedbox_host_io._configuration',side_effect=AssertionError('credential before original')) as credential:
 step(q,f['config'])
 with q.locked() as (rows,_):old=list(rows)
 step(q,f['config'])
 with q.locked() as (rows,_):assert rows==old
 assert not credential.called
with sqlite3.connect(f['config']['actor_database']['path']) as c:
 c.execute('update retry_messages set context=?,prepared=?,terminal=? where version=?',(*f['saved'],f['version']))
with patch('automation.seedbox_host_io._configuration',side_effect=SourceFailure('source_configuration_unavailable')) as credential:
 step(q,f['config']);assert credential.call_count==1
with q.locked() as (rows,_):
 assert sum(r['type']=='seedbox_source_started_v1' for r in rows)==1
 assert not any(r['type']=='seedbox_provider_started_v1' for r in rows)
print('installed original waiting and changed-record progress passed')
"""
  result=subprocess.run([sys.executable,'-I','-B','-c',script,str(runtime),str(fixture)],capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stderr);self.assertIn('changed-record progress passed',result.stdout)

 def test_scheduling_only_changes_do_not_append_waits(self):
  from automation.seedbox_original_readiness import ready
  q,config,prep=self.worker_fixture()
  with self.s.tx() as c:c.execute('update retry_messages set context=NULL,state="waiting",attempts=1 where version=?',(self.version,))
  self.assertFalse(ready(q,config,prep))
  with q.locked() as (rows,_):before=list(rows)
  with self.s.tx() as c:c.execute('update retry_messages set due=due+600,attempts=attempts+1 where version=?',(self.version,))
  self.assertFalse(ready(q,config,prep))
  with q.locked() as (rows,_):self.assertEqual(rows,before)
 def test_exact_pre_source_race_is_retained_without_marker_or_credentials(self):
  from automation.seedbox_worker import step
  from automation import seedbox_original_readiness as original
  q,config,prep=self.worker_fixture();check=original.ready
  def change(*args):
   result=check(*args)
   with self.s.tx() as c:c.execute('update retry_messages set prepared=NULL where version=?',(self.version,))
   return result
  with patch.object(original,'ready',side_effect=change),patch('automation.seedbox_host_io._configuration',side_effect=AssertionError('credential race')) as credential:
   self.assertFalse(step(q,config));self.assertFalse(credential.called)
  with q.locked() as (rows,_):
   self.assertFalse(any(r['type']=='seedbox_source_started_v1' for r in rows))
   waits=[r for r in rows if r['type']=='seedbox_original_readiness_v1']
   self.assertEqual(waits[-1]['view']['reason'],'telegram_original_incomplete')
 def test_missing_job_waits_but_multiple_matching_jobs_refuse(self):
  with self.s.tx() as c:
   row=c.execute('select * from retry_jobs where version=?',(self.version,)).fetchone()
   c.execute('delete from retry_jobs where version=?',(self.version,))
  with self.assertRaises(OriginalWait) as error:self.inspect()
  self.assertEqual(error.exception.view['reason'],'original_job_missing')
  with self.s.tx() as c:
   c.execute('insert into retry_jobs values (?,?,?,?,?,?,?,?,?,?)',row)
   other=list(row);other[0]='0'*64;c.execute('insert into retry_jobs values (?,?,?,?,?,?,?,?,?,?)',other)
  with self.assertRaisesRegex(ValueError,'host_listing_ambiguous_or_missing'):self.inspect()


def load_tests(loader,tests,pattern):
 return unittest.TestSuite(OriginalTests(n) for n in OriginalTests.__dict__ if n.startswith('test_'))
