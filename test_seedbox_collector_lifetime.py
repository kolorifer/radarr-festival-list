"""Actual SQLite helper lifetime, invented databases only."""
import errno,json,os,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_reviewed_telegram_operator import fixture_acl

DRIVER='''import sys,os,errno,json,sqlite3
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from automation.seedbox_confinement import prevent_collector_creation,confine
from automation.seedbox_host_io import collector_lifetime,database
root=Path(sys.argv[2]);mode=sys.argv[3]
def absent(*a,**kw):raise OSError(errno.ENODATA,'invented ACL absence')
os.getxattr=absent
actor=root/'actor/outcomes.sqlite3';collector=root/'collector/inbox.sqlite3';st=collector.stat()
pin=dict(path=str(collector),identity=[st.st_dev,st.st_ino],journal_mode='wal')
config=dict(state=str(root/'state'),credential={'path':str(root/'credential/key.cred')},source_configuration={'path':str(root/'environment')},cookie_file={'path':str(root/'cookie')},actor_database={'path':str(actor),'journal_mode':'delete'},collector_database=pin,sender={'process':{'pid':os.getpid()},'deployed_files':{}})
prevent_collector_creation(config)
if mode=='race':
 original=sqlite3.connect
 def connect(*a,**kw):
  print('OPEN',flush=True);sys.stdin.readline();return original(*a,**kw)
 sqlite3.connect=connect
 try:
  with collector_lifetime(pin):raise AssertionError('missing sidecar accepted')
 except (sqlite3.OperationalError,FileNotFoundError):pass
 assert not Path(str(collector)+'-wal').exists() and not Path(str(collector)+'-shm').exists()
 print('NO_CREATE',flush=True);sys.exit(0)
with collector_lifetime(pin):
 exists=Path.exists
 def selected_exists(p):return True if str(p)=='/run/systemd/io.systemd.Credentials' else exists(p)
 with patch.object(Path,'exists',selected_exists):confine(config,root/'code')
 print('READY',flush=True)
 for expected in (1,2,3):
  sys.stdin.readline()
  with database(pin) as c:
   assert c.execute('select count(*) from fixture').fetchone()[0]==expected
   try:c.execute('insert into fixture values(999)')
   except sqlite3.OperationalError:pass
   else:raise AssertionError('collector write permitted')
  print('READ'+str(expected),flush=True)
'''

class LifetimeTests(unittest.TestCase):
 def setUp(self):
  fixture_acl(self);old=os.umask(0o077);self.addCleanup(os.umask,old)
  self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
  for name in ('actor','collector','state','code','credential'):(self.root/name).mkdir(mode=0o700)
  self.db=self.root/'collector/inbox.sqlite3';self.writer=sqlite3.connect(self.db);self.addCleanup(self.writer.close)
  self.writer.execute('pragma journal_mode=wal');self.writer.execute('create table fixture(value integer)');self.writer.execute('insert into fixture values(1)');self.writer.commit()
  c=sqlite3.connect(self.root/'actor/outcomes.sqlite3');c.execute('create table fixture(value integer)');c.commit();c.close()
  for name in ('environment','cookie','credential/key.cred'):(self.root/name).write_bytes(b'INVENTED')
 def test_real_helper_observes_later_commits_without_reopening_guard_fd(self):
  from automation.seedbox_host_io import collector_lifetime,database
  st=self.db.stat();pin=dict(path=str(self.db),identity=[st.st_dev,st.st_ino],journal_mode='wal')
  with collector_lifetime(pin):
   self.writer.close()
   actor=self.root/'actor/outcomes.sqlite3';a=actor.stat()
   with database(dict(path=str(actor),identity=[a.st_dev,a.st_ino],journal_mode='delete')) as c:self.assertEqual(c.execute('select count(*) from fixture').fetchone()[0],0)
   for n in (1,2):
    if n==2:
     c=sqlite3.connect(self.db);c.execute('insert into fixture values(2)');c.commit();c.execute('pragma wal_checkpoint(truncate)');c.close()
    with patch('automation.seedbox_host_io.os.open',wraps=os.open) as opened:
     with database(pin) as c:self.assertEqual(c.execute('select count(*) from fixture').fetchone()[0],n)
     self.assertFalse(any(str(call.args[0]) in (str(self.db),self.db.name) for call in opened.call_args_list))
 def child(self,mode):
  if not sys.platform.startswith('linux'):self.skipTest('Linux Landlock lifetime regression')
  import ctypes
  from identity_triage_sandbox import _kernel,_call
  try:abi=_call(_kernel(),444,ctypes.c_void_p(),ctypes.c_size_t(0),ctypes.c_uint(1))
  except OSError:self.skipTest('Landlock unavailable')
  if abi<6:self.skipTest('Landlock ABI6 unavailable')
  driver=self.root/'driver.py';driver.write_text(DRIVER)
  p=subprocess.Popen([sys.executable,'-I','-B',str(driver),str(Path.cwd()),str(self.root),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda:p.kill() if p.poll() is None else None)
  return p
 def test_confined_helper_survives_producer_close_and_fresh_commits(self):
  p=self.child('live');self.assertEqual(p.stdout.readline().strip(),'READY')
  self.writer.close()
  for n in (1,2,3):
   if n>1:
    c=sqlite3.connect(self.db);c.execute('insert into fixture values(?)',(n,));c.commit();self.assertEqual(c.execute('pragma wal_checkpoint(truncate)').fetchone()[0],0);c.close()
   p.stdin.write('read\n');p.stdin.flush();self.assertEqual(p.stdout.readline().strip(),'READ'+str(n))
  out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,0,err)
 def test_producer_cleanup_between_validation_and_open_cannot_create_sidecars(self):
  p=self.child('race');self.assertEqual(p.stdout.readline().strip(),'OPEN')
  self.writer.close();self.assertFalse(Path(str(self.db)+'-wal').exists());self.assertFalse(Path(str(self.db)+'-shm').exists())
  out,err=p.communicate('continue\n',timeout=10);self.assertEqual(p.returncode,0,err);self.assertIn('NO_CREATE',out)
