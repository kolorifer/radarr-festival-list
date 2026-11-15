"""Invented exact original receipts and fake Telegram; no live configuration."""
import ast,copy,json,os,sqlite3,tempfile,time,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock
from automation import reviewed_telegram_operator as t
from identity_retry import RetryStore
from identity_triage_store import digest
from identity_triage_observer import envelope
import retry_telegram
from test_identity_triage import payload,SOURCES
from test_identity_automation import context

class DeliveryTests(unittest.TestCase):
 def setUp(self):
  old=os.umask(0o077);self.addCleanup(os.umask,old)
  self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup)
  self.now=time.time();self.s=RetryStore(Path(self.tmp.name).resolve()/'retry',clock=lambda:self.now)
  self.p=payload();self.ctx=context();self.ref={'chat_id':'123','message_id':17,'kind':'text'}
  self.s.admit({'observation':envelope(self.p,self.ctx,SOURCES)},SOURCES)
  b=retry_telegram.binding(self.p,self.ctx,[self.ref],SOURCES);self.version=b['version'];retry_telegram.save_binding(self.s,b)
  with self.s.tx() as c:
   retry_telegram.completed(c,self.version,self.ctx,'title_conflict',self.now)
   c.execute('update retry_jobs set state="done",reason="title_conflict",lease=NULL,until=? where version=?',(self.now-1,self.version))
  retry_telegram.pump(self.s,lambda *a:{'text':'old','token':None},lambda *a:None)
  self.target=t.inspect_target(self.s,self.version,SOURCES)
  self.pin=dict(version=self.version,row_sha256=self.target['row_sha256'],ref=self.ref,case_id=self.target['case_id'])
  self.plan=dict(kind='reviewed_original_card_v1',case_id=self.pin['case_id'],version='d'*64,review_sha256='a'*64,report_sha256='b'*64,receipt_sha256='c'*64,html_sha256='e'*64,local_context_sha256='f'*64,source_url='https://example.invalid/listing/123',candidate=None,summary=dict(discrepancy='Mismatch.',evidence='Evidence.',uncertainty='Unknown.'),reviewed_at=self.now,text='Reviewed proposal. No download approved.\nSource listing: https://example.invalid/listing/123',production_approved=False,download_approved=False)
  self.boundary=dict(kind='main_verified_sender_boundary_v1',single_serial_pump=True,no_other_edit_writers=True,no_original_binding_republication=True,
    deployed_revision='06d17aafefb5a5161364e4bf6f63667a649e1aa3',verified_reference='invented:topology',reviewed_plan_sha256=digest(self.plan),observed_at=self.now,expires_at=self.now+120)
 def call(self,edit):return t.deliver(self.s,self.plan,self.pin,SOURCES,self.boundary,edit,clock=lambda:self.now)
 def test_exact_edit_ack_restart_and_old_pump_no_overwrite(self):
  edit=Mock();first=self.call(edit);self.assertEqual(first['status'],'acknowledged');edit.assert_called_once_with([self.ref],{'text':self.plan['text'],'token':None})
  self.s=RetryStore(self.s.directory,clock=lambda:self.now);self.assertEqual(self.call(edit),first);self.assertEqual(edit.call_count,1)
  self.assertFalse(retry_telegram.pump(self.s,Mock(side_effect=AssertionError()),Mock(side_effect=AssertionError())))
 def test_uncertain_does_not_retry_and_never_retains_error_text(self):
  edit=Mock(side_effect=RuntimeError('SYNTHETIC_SECRET_URL'))
  self.assertEqual(self.call(edit)['status'],'uncertain');self.assertEqual(self.call(edit)['status'],'uncertain');self.assertEqual(edit.call_count,1)
  with self.s.tx() as c:raw=str(c.execute('select * from reviewed_telegram_edits').fetchall())
  self.assertNotIn('SYNTHETIC_SECRET_URL',raw)
 def test_changed_pin_waiting_failed_or_superseded_refused(self):
  original=self.pin['row_sha256'];self.pin['row_sha256']='e'*64
  with self.assertRaisesRegex(ValueError,'telegram_target_changed'):self.call(Mock(side_effect=AssertionError()))
  self.pin['row_sha256']=original
  for state in ('waiting','failed'):
   with self.s.tx() as c:c.execute('update retry_messages set state=? where version=?',(state,self.version))
   self.pin['row_sha256']=t.inspect_target(self.s,self.version,SOURCES)['row_sha256']
   with self.assertRaisesRegex(ValueError,'telegram_original_not_quiescent'):self.call(Mock(side_effect=AssertionError()))
 def test_false_topology_expiry_and_expiring_original_refuse(self):
  self.boundary['single_serial_pump']=False
  with self.assertRaisesRegex(ValueError,'telegram_sender_boundary'):self.call(Mock(side_effect=AssertionError()))
  self.boundary['single_serial_pump']=True;self.boundary['expires_at']=self.now+10
  with self.assertRaisesRegex(ValueError,'telegram_sender_boundary'):self.call(Mock(side_effect=AssertionError()))
  self.boundary['expires_at']=self.now+120
  with self.s.tx() as c:c.execute('update retry_messages set created=? where version=?',(self.now-8*86400+60,self.version))
  self.pin['row_sha256']=t.inspect_target(self.s,self.version,SOURCES)['row_sha256']
  with self.assertRaisesRegex(ValueError,'telegram_receipt_expiring'):self.call(Mock(side_effect=AssertionError()))
 def test_duplicate_ref_across_versions_and_weak_name_refuse(self):
  with self.s.tx() as c:c.execute('insert into retry_messages(version,refs,created) values(?,?,?)',('f'*64,json.dumps([self.ref]),self.now))
  with self.assertRaisesRegex(ValueError,'telegram_duplicate_original_ref'):self.call(Mock(side_effect=AssertionError()))
 def test_writer_lock_held_during_edit(self):
  def edit(*args):
   other=sqlite3.connect(self.s.path,timeout=.01)
   try:
    with self.assertRaises(sqlite3.OperationalError):other.execute('BEGIN IMMEDIATE')
   finally:other.close()
  self.assertEqual(self.call(edit)['status'],'acknowledged')
 def test_reserved_crash_never_resends(self):
  with self.s.tx() as c:
   t._schema(c);c.execute('insert into reviewed_telegram_edits values(?,?,?,?,?,"reserved",NULL,?)',(self.target['message_key'],self.plan['case_id'],self.version,digest(self.plan),digest(self.pin),self.now))
  edit=Mock(side_effect=AssertionError());self.assertEqual(self.call(edit)['status'],'reserved');edit.assert_not_called()
 def test_existing_sender_uses_only_exact_edit_and_clears_keyboard(self):
  tree=ast.parse(Path('movie_intel_service.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='edit_retry_message')
  request=Mock(return_value=200);ns=dict(TELEGRAM_CHAT_ID='123',get_action=Mock(side_effect=AssertionError()),public_action_url=Mock(side_effect=AssertionError()),_telegram_request=request,HTTPError=__import__('urllib.error',fromlist=['HTTPError']).HTTPError)
  exec(compile(ast.Module(body=[function],type_ignores=[]),'reviewed-existing-sender','exec'),ns)
  self.call(ns['edit_retry_message'])
  method,body=request.call_args.args;self.assertEqual(method,'editMessageText');self.assertEqual(body,{'chat_id':'123','message_id':17,'text':self.plan['text'],'reply_markup':{'inline_keyboard':[]}})

 def test_intervening_state_change_refuses_before_sender(self):
  original=self.s.tx;count=0
  @contextmanager
  def changed():
   nonlocal count
   count+=1
   if count==2:
    with original() as c:c.execute('update retry_messages set state="waiting" where version=?',(self.version,))
   with original() as c:yield c
  self.s.tx=changed;edit=Mock(side_effect=AssertionError())
  self.assertEqual(self.call(edit)['status'],'uncertain');edit.assert_not_called()
 def test_cross_version_pending_spool_refuses(self):
  spool=self.s.directory/'message-bindings';spool.mkdir(mode=0o700)
  item=dict(version='f'*64,refs=json.dumps([self.ref]));path=spool/(item['version']+'.json');path.write_text(json.dumps(item));path.chmod(0o600)
  with self.assertRaisesRegex(ValueError,'telegram_original_spool_pending'):self.call(Mock(side_effect=AssertionError()))
 def test_enforced_wall_clock_deadline(self):
  with self.assertRaisesRegex(TimeoutError,'telegram_edit_deadline'):
   with t._deadline(.02):time.sleep(.2)

class PlanTests(unittest.TestCase):
 def fixture(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);path=Path(temp.name).resolve()/'local.json'
  from ai_movie_investigator.contracts import encoded
  raw=encoded(dict(tracker_url='https://example.invalid/listing/123',release_name='Invented release',nfo_text='Invented NFO'));path.write_bytes(raw);path.chmod(0o600)
  import hashlib
  local=dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())
  result=dict(local_context_sha256=local['sha256'],result={'candidate':{'imdb':'tt1234567','tmdb':123},'status':'supported_candidate'},provider_receipt_correlated=True,generation_invoked=True,receipt_hash='a'*64)
  completed=dict(type='supervised_completed',slot=7,historical_report=result)
  pending=dict(type='operator_pending_review_v1',reservation='r',slot=7,completion_sha256=digest(completed),report_sha256=digest(result),html={'sha256':'b'*64})
  reviewed=dict(type='operator_reviewed_v1',reservation='r',pending_sha256=digest(pending),observed_at=time.time())
  prepared=dict(type='operator_prepared_v1',reservation='r',local_context=local,projection={'case_id':'outcome-'+'c'*64,'version':'d'*64,'catalogue':{'title':'Invented Movie','theatrical_year':2001,'imdb':'tt1234567','tmdb':123}})
  rows=[prepared,pending,reviewed];root=[completed]
  class Operator:
   clock=staticmethod(time.time)
   @contextmanager
   def locked(self):yield root,rows,rows.append
  return Operator(),rows,root
 def test_bound_deterministic_qualified_plan_and_separate_delivery(self):
  op,rows,root=self.fixture();summary=dict(discrepancy='The old title was inconsistent.',evidence='The title and cast support this candidate.',uncertainty='The physical edition remains unknown.')
  a=t.prepare(op,'r',summary);self.assertEqual(t.prepare(op,'r',summary),a)
  self.assertIn('supports a candidate',a['plan']['text']);self.assertIn('No download is approved',a['plan']['text'])
  self.assertFalse(a['plan']['production_approved'])
  receipt=dict(kind='reviewed_telegram_sender_ack_v1',message_key=digest(['123',17]),ref=dict(chat_id='123',message_id=17,kind='text'),target_sha256='e'*64,acknowledged_at=time.time(),acknowledgement='existing_sender_returned',human_ingestion=False,plan_sha256=a['plan_sha256'],case_id=a['plan']['case_id'])
  self.assertEqual(t.record_delivery(op,'r',receipt)['type'],'operator_telegram_delivered_v1')
  self.assertEqual(t.record_delivery(op,'r',receipt),rows[-1])
 def test_no_review_changed_candidate_or_unsafe_summary_refuse(self):
  op,rows,root=self.fixture();summary=dict(discrepancy='Mismatch.',evidence='Evidence.',uncertainty='Unknown.')
  rows.pop()
  with self.assertRaisesRegex(ValueError,'telegram_review_required'):t.prepare(op,'r',summary)
  op,rows,root=self.fixture();summary['evidence']='https://private.invalid/token'
  with self.assertRaises(ValueError):t.prepare(op,'r',summary)


class InvocationTests(unittest.TestCase):
 def test_issued_template_exact_sender_no_environment_mutation(self):
  import hashlib,subprocess,sys
  f=DeliveryTests('test_exact_edit_ack_restart_and_old_pump_no_overwrite');f.setUp();self.addCleanup(f.doCleanups)
  from automation import reviewed_telegram_UNISSUED as wrapper
  root=f.s.directory.parent;actor=root/'actor';actor.mkdir(mode=0o700);(actor/'deploy').mkdir(mode=0o700)
  pins={}
  for relative in [n+'.py' for n in wrapper.MODULES]+['movie_intel_service.py','deploy/run.py']:
   raw=(getattr(self,'actor_fixture',Path.cwd())/relative).read_bytes();dest=actor/relative;dest.write_bytes(raw);dest.chmod(0o600);pins[relative]=hashlib.sha256(raw).hexdigest()
  def pin(name,raw):
   p=root/name;p.write_bytes(raw);p.chmod(0o600);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest())
  def obj(name,value):return pin(name,json.dumps(value,sort_keys=True).encode())
  issued=dict(actor_root=str(actor),actor_files=pins,helper=pin('helper.py',Path('automation/reviewed_telegram_operator.py').read_bytes()),
    plan=obj('plan.json',f.plan),target=obj('target.json',f.pin),sources=obj('sources.json',SOURCES),boundary=obj('boundary.json',f.boundary),
    bot_configuration=pin('private.env',b'TELEGRAM_BOT_TOKEN="SYNTHETIC_BOT_ONLY"\nTELEGRAM_CHAT_ID="123"\nUNRELATED="not exported"\n'),
    state=str(f.s.directory),output=str(root/'receipt.json'),main_acceptance_path=str(root/'acceptance.json'),
    python_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest())
  raw=Path('automation/reviewed_telegram_UNISSUED.py').read_text().replace('ISSUED = None','ISSUED = '+repr(issued),1)
  entry=pin('issued.py',raw.encode());obj('acceptance.json',dict(decision='accepted_exact_reviewed_telegram_edit',wrapper_sha256=entry['sha256'],issued_pins=issued))
  driver=root/'driver.py'
  driver.write_text("""import runpy,sys,json,io,os
before=dict(os.environ)
ns=runpy.run_path("""+repr(entry['path'])+""",run_name='fixture')
seen=[]
class Response(io.BytesIO):
 status=200
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def fake(request,timeout):
 assert timeout==15
 assert request.full_url=='https://api.telegram.org/botSYNTHETIC_BOT_ONLY/editMessageText'
 body=json.loads(request.data)
 assert body['chat_id']=='123' and body['message_id']==17
 assert body['reply_markup']=={'inline_keyboard':[]}
 seen.append(body)
 return Response(b'{"ok":true,"result":true}')
ns['main'].__globals__['urlopen']=fake
sys.argv=['fixture','--main-accepted-reviewed-telegram']
def trip(event,args):
 if event in ('socket.connect','subprocess.Popen','os.system'):raise AssertionError('external IO forbidden')
sys.addaudithook(trip)
ns['main']()
assert len(seen)==1 and dict(os.environ)==before
assert 'movie_intel_service' not in sys.modules and 'identity_retry' not in sys.modules
print('fixture_sender_only_no_actor_start')
""")
  result=subprocess.run([str(Path(sys.executable).resolve()),'-I','-S','-B',str(driver)],capture_output=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stderr.decode());self.assertIn(b'fixture_sender_only_no_actor_start',result.stdout)
  self.assertNotIn(b'SYNTHETIC_BOT_ONLY',result.stdout+result.stderr)
  receipt=json.loads((root/'receipt.json').read_text());self.assertEqual(receipt['status'],'acknowledged')
