"""Two invented model generations through the existing original-card sender."""
import hashlib,io,json,time,unittest,sys,sqlite3
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import test_seedbox_connected as connected
import test_seedbox_assessment_execution as execution
import test_snapshot_review as snapshot
import test_reviewed_telegram_operator as original
from test_identity_triage import SOURCES
from automation.seedbox_sender import deliver_reviewed
from automation.seedbox_circuit import active
from test_snapshot_review import NOW

class SenderTests(connected.ConnectedTests):
 def setUp(self):
  self.delivery=original.DeliveryTests('test_exact_edit_ack_restart_and_old_pump_no_overwrite')
  with patch('time.time',return_value=NOW):self.delivery.setUp()
  self.addCleanup(self.delivery.doCleanups);self.fixture_target=self.delivery.pin
  for module in [connected,execution]+[m for name,m in list(sys.modules.items()) if name.startswith('test_snapshot') and hasattr(m,'CASE')]:
   p=patch.object(module,'CASE',self.fixture_target['case_id']);p.start();self.addCleanup(p.stop)
  super().setUp();self.complete()
  env=self.path/'invented-environment';env.write_text('TELEGRAM_BOT_TOKEN=INVENTED_BOT_FIXTURE\nTELEGRAM_CHAT_ID=123\n');env.chmod(0o600)
  st=self.delivery.s.path.stat();names=('identity_triage_store.py','identity_triage_intake.py','identity_outcome_outbox.py','identity_triage_observer.py','retry_telegram.py','torrent_research_evidence.py','movie_intel_service.py','deploy/run.py')
  self.config=dict(credit_policy=self.policy,sources=SOURCES,actor_database=dict(path=str(self.delivery.s.path),identity=[st.st_dev,st.st_ino]),source_configuration=dict(path=str(env),sha256=hashlib.sha256(env.read_bytes()).hexdigest()),sender=dict(kind='main_selected_actor_topology_v1',revision='06d17aafefb5a5161364e4bf6f63667a649e1aa3',sole_edit_writer=True,single_serial_pump=True,no_original_binding_republication=True,acceptance_reference='invented:accepted-topology',observed_at=NOW-1,expires_at=NOW+500,process={'pid':123},deployed_files={name:{'fixture':name} for name in names}))
 def call(self,urlopen):
  with patch('time.time',return_value=getattr(self,'delivery_time',NOW)),patch('automation.seedbox_sender._process',return_value={'pid':123}) as process,patch('automation.seedbox_sender._deployed',side_effect=lambda pin:Path(pin['fixture']).read_bytes()),patch('automation.seedbox_evidence.verify_current'),patch('automation.reviewed_telegram_UNISSUED.urlopen',side_effect=urlopen):
   result=deliver_reviewed(self.q,self.config,self.selected['reservation'])
   return result,process.call_count
 def test_real_existing_sender_exact_edit_and_restart_no_replay(self):
  requests=[]
  def http(request,timeout):
   body=json.loads(request.data);requests.append((request.full_url,body));self.assertEqual(timeout,15)
   result=io.BytesIO(b'{"ok":true,"result":{}}');result.status=200;return result
  result,checks=self.call(http);self.assertEqual(result['status'],'acknowledged');self.assertGreaterEqual(checks,2)
  self.assertEqual(len(requests),1);self.assertTrue(requests[0][0].endswith('/editMessageText'));self.assertEqual(requests[0][1]['message_id'],17);self.assertEqual(requests[0][1]['reply_markup'],{'inline_keyboard':[]})
  again,_=self.call(lambda *a,**kw:self.fail('replayed edit'));self.assertEqual(again['status'],'uncertain_or_previously_started')
  with self.delivery.s.tx() as c:self.assertEqual(c.execute('select state from reviewed_telegram_edits').fetchone()[0],'acknowledged')
 def test_first_transaction_busy_is_proven_unsent_and_can_finish_once(self):
  blocker=sqlite3.connect(self.delivery.s.path,isolation_level=None)
  blocker.execute('begin immediate')
  try:
   with self.assertRaisesRegex(ValueError,'host_sender_pre_send_busy'):
    self.call(lambda *a,**kw:self.fail('sent while first transaction busy'))
  finally:blocker.rollback();blocker.close()
  with self.q.locked() as (rows,_):
   self.assertEqual(len([r for r in rows if r['type']=='seedbox_sender_pre_send_deferred_v1']),1)
   self.assertFalse(active(rows))
  self.delivery_time=NOW+61
  calls=[]
  def http(*a,**kw):
   calls.append(True);result=io.BytesIO(b'{"ok":true,"result":{}}');result.status=200;return result
  result,_=self.call(http);self.assertEqual(result['status'],'acknowledged');self.assertEqual(len(calls),1)
  self.call(lambda *a,**kw:self.fail('replayed completed edit'))
 def test_durable_deferrals_enforce_cooldown_and_three_check_cap(self):
  blocker=sqlite3.connect(self.delivery.s.path,isolation_level=None);blocker.execute('begin immediate')
  try:
   for number in range(3):
    self.delivery_time=NOW+number*61
    with self.assertRaisesRegex(ValueError,'host_sender_pre_send_busy'):
     self.call(lambda *a,**kw:self.fail('unexpected send'))
    if number==0:
     with self.assertRaisesRegex(ValueError,'host_sender_pre_send_cooldown'):
      self.call(lambda *a,**kw:self.fail('cooldown bypass'))
   self.delivery_time=NOW+183
   with self.assertRaisesRegex(ValueError,'host_sender_pre_send_checks_exhausted'):
    self.call(lambda *a,**kw:self.fail('fourth check'))
  finally:blocker.rollback();blocker.close()
  with self.q.locked() as (rows,_):
   self.assertEqual(len([r for r in rows if r['type']=='seedbox_sender_pre_send_deferred_v1']),3)
   self.assertFalse(any(r['type']=='seedbox_delivery_wait_v1' for r in rows))
 def test_existing_binding_spool_bytes_are_unchanged(self):
  spool=self.delivery.s.directory/'message-bindings'
  spool.mkdir(mode=0o700)
  item=dict(version='f'*64,refs=json.dumps([dict(chat_id=123,message_id=999,kind='fixture')]))
  fixture=spool/(item['version']+'.json');fixture.write_text(json.dumps(item));fixture.chmod(0o600)
  before={str(p.relative_to(spool)):p.read_bytes() for p in spool.rglob('*') if p.is_file()}
  self.assertTrue(before)
  def http(*a,**kw):
   result=io.BytesIO(b'{"ok":true,"result":{}}');result.status=200;return result
  result,_=self.call(http);self.assertEqual(result['status'],'acknowledged')
  self.assertEqual(before,{str(p.relative_to(spool)):p.read_bytes() for p in spool.rglob('*') if p.is_file()})
 def test_bot_auth_failure_global_circuit_without_retry(self):
  def denied(*a,**kw):raise HTTPError('https://fixture.invalid',401,'fixture',{},io.BytesIO(b'{}'))
  result,_=self.call(denied);self.assertEqual(result['status'],'uncertain')
  with self.q.locked() as (rows,_):self.assertEqual(active(rows)[0]['reason'],'telegram_auth_denied')
  self.call(lambda *a,**kw:self.fail('replayed denied edit'))


def load_tests(loader,tests,pattern):return unittest.TestSuite(SenderTests(name) for name in SenderTests.__dict__ if name.startswith('test_'))
