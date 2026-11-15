"""Invented other-process live checks under actual Linux confinement."""
import hashlib,json,os,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
from automation.seedbox_process import _validate
from test_seedbox_collector_lifetime import LifetimeTests

DRIVER='''import sys,os,errno,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from automation.seedbox_process import actor_lifetime,observe,retained
from automation.seedbox_confinement import prevent_collector_creation,confine
from automation.seedbox_host_io import collector_lifetime
root=Path(sys.argv[2]);pin=json.loads(sys.argv[3]);mode=sys.argv[4]
def absent(*a,**kw):raise OSError(errno.ENODATA,'invented ACL absence')
os.getxattr=absent
actor=root/'actor/outcomes.sqlite3';collector=root/'collector/inbox.sqlite3';st=collector.stat()
config=dict(state=str(root/'state'),credential={'path':str(root/'credential/key.cred')},source_configuration={'path':str(root/'environment')},cookie_file={'path':str(root/'cookie')},actor_database={'path':str(actor),'journal_mode':'delete'},collector_database=dict(path=str(collector),identity=[st.st_dev,st.st_ino],journal_mode='wal'),sender={'process':pin,'deployed_files':{}})
assert observe(pin)['start_ticks']==pin['start_ticks']
with actor_lifetime(pin):
 prevent_collector_creation(config)
 assert observe(pin)['start_ticks']==pin['start_ticks']
 with collector_lifetime(config['collector_database']):
  exists=Path.exists
  def selected_exists(p):return True if str(p)=='/run/systemd/io.systemd.Credentials' else exists(p)
  with patch.object(Path,'exists',selected_exists):confine(config,root/'code')
  # Real full boundary denies fresh metadata opens for the unconfined actor.
  try:fd=os.open('/proc/'+str(pin['pid'])+'/cmdline',os.O_RDONLY)
  except (PermissionError,FileNotFoundError):pass
  else:os.close(fd);raise AssertionError('fresh actor metadata open permitted')
  assert retained(pin) and observe(pin)['cmdline_sha256']==pin['cmdline_sha256']
  print('LIVE',flush=True);sys.stdin.readline()
  try:observe(pin)
  except (ValueError,ProcessLookupError):print('REFUSED',flush=True)
  else:raise AssertionError('stale process observation accepted')
assert not retained(pin)
'''

class MetadataTests(unittest.TestCase):
 def raw(self,state=b'S'):
  return b'123 (invented actor) '+b' '.join([state]+[b'0']*18+[b'456'])
 def test_pid_lifetime_command_and_zombie_refuse(self):
  pin=dict(pid=123,start_ticks=456,cmdline_sha256=hashlib.sha256(b'invented').hexdigest())
  self.assertEqual(_validate(pin,self.raw(),b'invented')['pid'],123)
  for raw,command in ((self.raw(b'Z'),b'invented'),(self.raw(),b''),(self.raw(),b'changed'),(self.raw().replace(b'456',b'457'),b'invented')):
   with self.assertRaises(ValueError):_validate(pin,raw,command)

class ProcessTests(LifetimeTests):
 def run_process_case(self,mode):
  if not sys.platform.startswith('linux'):self.skipTest('Linux process/confinement regression')
  import ctypes
  from identity_triage_sandbox import _kernel,_call
  try:abi=_call(_kernel(),444,ctypes.c_void_p(),ctypes.c_size_t(0),ctypes.c_uint(1))
  except OSError:self.skipTest('Landlock unavailable')
  if abi<6:self.skipTest('Landlock ABI6 unavailable')
  actor_code="import sys,os;print('READY',flush=True);action=sys.stdin.readline();os.execv(sys.executable,[sys.executable,'-I','-B','-c',\"import sys;print('CHANGED',flush=True);sys.stdin.readline()\"]) if action.strip()=='exec' else None"
  actor=subprocess.Popen([sys.executable,'-I','-B','-c',actor_code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda:actor.kill() if actor.poll() is None else None)
  self.assertEqual(actor.stdout.readline().strip(),'READY')
  proc=Path('/proc')/str(actor.pid);raw=(proc/'stat').read_bytes();pin=dict(pid=actor.pid,start_ticks=int(raw.rsplit(b') ',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest())
  driver=self.root/'process-driver.py';driver.write_text(DRIVER)
  child=subprocess.Popen([sys.executable,'-I','-B',str(driver),str(Path.cwd()),str(self.root),json.dumps(pin),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda:child.kill() if child.poll() is None else None)
  self.assertEqual(child.stdout.readline().strip(),'LIVE')
  if mode=='exit':actor.communicate('exit\n',timeout=10)
  else:
   actor.stdin.write('exec\n');actor.stdin.flush();self.assertEqual(actor.stdout.readline().strip(),'CHANGED')
  out,err=child.communicate('check\n',timeout=10);self.assertEqual(child.returncode,0,err);self.assertIn('REFUSED',out)
  if actor.poll() is None:actor.communicate('done\n',timeout=10)
 def test_unconfined_other_actor_held_checks_then_exit(self):self.run_process_case('exit')
 def test_unconfined_other_actor_command_change_is_reread(self):self.run_process_case('exec')
 def test_actor_handles_close_on_context_exit_and_failed_selection(self):
  if not sys.platform.startswith('linux'):self.skipTest('Linux proc/pidfd cleanup')
  from automation.seedbox_process import actor_lifetime
  proc=Path('/proc/self');raw=(proc/'stat').read_bytes();pin=dict(pid=os.getpid(),start_ticks=int(raw.rsplit(b') ',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest())
  original=os.open;pidopen=os.pidfd_open;opened=[]
  def traced(*a,**kw):
   fd=original(*a,**kw);opened.append(fd);return fd
  def traced_pid(*a,**kw):
   fd=pidopen(*a,**kw);opened.append(fd);return fd
  for changed in (False,True):
   selected=dict(pin);selected['start_ticks']+=int(changed);opened.clear()
   with patch('automation.seedbox_process.os.open',side_effect=traced),patch('automation.seedbox_process.os.pidfd_open',side_effect=traced_pid):
    if changed:
     with self.assertRaises(ValueError):
      with actor_lifetime(selected):pass
    else:
     with actor_lifetime(selected):
      self.assertTrue(all(not os.get_inheritable(fd) for fd in opened))
   for fd in opened:
    with self.assertRaises(OSError):os.fstat(fd)


def load_tests(loader,tests,pattern):
 return unittest.TestSuite(cls(name) for cls in (MetadataTests,ProcessTests) for name in cls.__dict__ if name.startswith('test_'))
