"""Actual Linux filesystem boundary; no network, credential or service calls."""
import hashlib,os,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_reviewed_telegram_operator import fixture_acl
from automation.seedbox_sender import journal_clean

class JournalTests(unittest.TestCase):
 def setUp(self):
  fixture_acl(self);old=os.umask(0o077);self.addCleanup(os.umask,old)
  self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
 def test_existing_journal_refuses_without_opening_or_repair(self):
  db=self.root/'outcomes.sqlite3';db.write_bytes(b'INVENTED_DB');journal=self.root/'outcomes.sqlite3-journal';journal.write_bytes(b'INVENTED_INTERRUPTED_JOURNAL')
  with self.assertRaisesRegex(ValueError,'host_actor_journal_present'):journal_clean({'path':str(db)})
  self.assertEqual(db.read_bytes(),b'INVENTED_DB');self.assertEqual(journal.read_bytes(),b'INVENTED_INTERRUPTED_JOURNAL')
 @unittest.skipUnless(sys.platform.startswith('linux'),'Linux Landlock filesystem check')
 def test_real_kernel_rollback_journal_and_collector_readonly(self):
  import ctypes
  from identity_triage_sandbox import _kernel,_call
  lib=_kernel()
  try:abi=_call(lib,444,ctypes.c_void_p(),ctypes.c_size_t(0),ctypes.c_uint(1))
  except OSError:self.skipTest('Landlock unavailable on this test host')
  if abi<6:self.skipTest('Landlock ABI6 unavailable on this test host')
  for name in ('actor','collector','state','code','credential'): (self.root/name).mkdir(mode=0o700)
  actor=self.root/'actor/outcomes.sqlite3';c=sqlite3.connect(actor);c.execute('create table fixture(value integer)');c.commit();c.close()
  collector=self.root/'collector/inbox.sqlite3';writer=sqlite3.connect(collector);self.addCleanup(writer.close);writer.execute('pragma journal_mode=wal');writer.execute('create table fixture(value integer)');writer.execute('insert into fixture values (1)');writer.commit()
  for name in ('environment','cookie','denied','credential/key.cred'):(self.root/name).write_bytes(b'INVENTED')
  driver=self.root/'driver.py';driver.write_text('''import sys,os,json,sqlite3,errno\nfrom pathlib import Path\nfrom unittest.mock import patch\nsys.path.insert(0,sys.argv[1])\nfrom automation.seedbox_confinement import confine\nfrom ai_movie_investigator.private_files import private_chain\nroot=Path(sys.argv[2]);actor=root/'actor/outcomes.sqlite3';collector=root/'collector/inbox.sqlite3'\nconfig=dict(state=str(root/'state'),credential={'path':str(root/'credential/key.cred')},source_configuration={'path':str(root/'environment')},cookie_file={'path':str(root/'cookie')},actor_database={'path':str(actor),'journal_mode':'delete'},collector_database={'path':str(collector),'journal_mode':'wal'},sender={'process':{'pid':os.getpid()},'deployed_files':{}})\nexists=Path.exists\ndef selected_exists(path):return True if str(path)=='/run/systemd/io.systemd.Credentials' else exists(path)\n# IPC existence is invented ONLY for this filesystem test; no credential call.\nwith patch.object(Path,'exists',selected_exists):confine(config,root/'code')\nwith private_chain(root/'state') as fd:os.mkdir('retained',0o700,dir_fd=fd)\nc=sqlite3.connect(actor);assert c.execute('pragma journal_mode').fetchone()[0]=='delete';c.execute('pragma synchronous=full');c.execute('begin immediate');c.execute('insert into fixture values(2)');assert Path(str(actor)+'-journal').exists();c.commit();assert not Path(str(actor)+'-journal').exists();c.close()\nc=sqlite3.connect(collector.as_uri()+'?mode=ro',uri=True);assert c.execute('select value from fixture').fetchone()==(1,)\ntry:c.execute('insert into fixture values(2)')\nexcept sqlite3.OperationalError:pass\nelse:raise AssertionError('collector write accepted')\nc.close()\ntry:fd=os.open(root/'denied',os.O_WRONLY)\nexcept PermissionError:pass\nelse:os.close(fd);raise AssertionError('unrelated write accepted')\nprint('actual_journal_create_commit_remove_and_source_readonly_verified')\n''')
  result=subprocess.run([sys.executable,'-I','-B',str(driver),str(Path.cwd()),str(self.root)],capture_output=True,timeout=20)
  self.assertEqual(result.returncode,0,result.stderr.decode());self.assertIn(b'actual_journal_create',result.stdout)
