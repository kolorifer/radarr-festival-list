"""Bounded real invented child pipes and genuine isolated bridge entry."""
import hashlib,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from automation.seedbox_child import captured
from automation.seedbox_package import build
from test_reviewed_telegram_operator import fixture_acl
import test_seedbox_credit_policy as policies

class ChildBridgeTests(unittest.TestCase):
 def setUp(self):
  fixture_acl(self);old=os.umask(0o077);self.addCleanup(os.umask,old)
  self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
 def test_bounded_child_stdout_and_deadline(self):
  argv=[sys.executable,'-I','-B','-c','import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"INVENTED_CIPHER")']
  self.assertEqual(captured(argv,b'sk-SYNTHETIC_FIXTURE',seconds=2,output_limit=32,environment={'PATH':'/usr/bin:/bin'}),b'INVENTED_CIPHER')
  with self.assertRaisesRegex(ValueError,'host_child_output_bound'):
   captured([sys.executable,'-I','-B','-c','import sys;sys.stdout.write("x"*10000)'],b'',seconds=2,output_limit=32,environment={})
  with self.assertRaisesRegex(ValueError,'host_child_deadline'):
   captured([sys.executable,'-I','-B','-c','import time;time.sleep(10)'],b'',seconds=.05,output_limit=32,environment={})
 def test_genuine_isolated_bridge_no_secret_file_argv_env_or_import_bypass(self):
  code=self.root/'code';code.mkdir(mode=0o700);built=build(Path.cwd(),code)
  state=self.root/'state';state.mkdir(mode=0o700)
  key=self.root/'ssh-key';key.write_bytes(b'INVENTED_SSH_KEY_NOT_TO_BE_READ');key.chmod(0o600);info=key.stat()
  known=self.root/'known-hosts';known.write_bytes(b'invented public host pin');known.chmod(0o600)
  policy=policies.CreditPolicyTests().policy();now=time.time();policy.update(observed_at=now-1,delegated_at=now-1,expires_at=int(now+600),credit_expires_at=now+700)
  config=dict(kind='seedbox_keychain_bridge_v1',host='fixture.invalid',user='fixture',port=22,credit_policy=policy,not_after_epoch=policy['expires_at'],ssh_key=dict(path=str(key),metadata=[info.st_dev,info.st_ino,info.st_uid,info.st_mode,info.st_nlink]),known_hosts=dict(path=str(known),sha256=hashlib.sha256(known.read_bytes()).hexdigest()),state=str(state),python='/usr/bin/python3',bootstrap='/fixture/bootstrap.py',manifest_path='/fixture/manifest.json',manifest_sha256='a'*64,destination='/fixture/private',systemd_creds_sha256='b'*64)
  raw=json.dumps(config,sort_keys=True,separators=(',',':')).encode();selection=self.root/'selection.json';selection.write_bytes(raw);selection.chmod(0o600)
  driver=self.root/'driver.py'
  driver.write_text('''import sys,os,errno,runpy\nfrom unittest.mock import patch\nsys.path.insert(0,sys.argv[1])\nimport ai_movie_investigator.keychain_credential as native\ntry:\n with native.one_shot_process():raise AssertionError('import bypass')\nexcept ValueError:pass\nelse:raise AssertionError('imported entry accepted')\ncalls=[]\ndef child(argv,data,**kw):\n assert data==b'sk-SYNTHETIC_FIXTURE'\n assert 'SYNTHETIC' not in repr((argv,kw))\n assert argv[0]=='/usr/bin/ssh' and 'StrictHostKeyChecking=yes' in argv\n calls.append(1);return b'encrypted_credential_stored\\n'\nif sys.platform.startswith('linux'):\n def absent(*a,**kw):raise OSError(errno.ENODATA,'fixture ACL absence')\n os.getxattr=absent\nconfig,sha=sys.argv[2:4]\nsys.argv=['automation.seedbox_keychain_bridge',config,sha]\nwith patch.object(native,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),patch('automation.seedbox_child.captured',side_effect=child):\n try:runpy.run_module('automation.seedbox_keychain_bridge',run_name='__main__',alter_sys=True)\n except SystemExit as e:assert e.code==0,e.code\nassert calls==[1]\nassert 'requests' not in sys.modules and 'bs4' not in sys.modules and 'automation.seedbox_confinement' not in sys.modules\nprint('genuine_bridge_invented_no_leak_verified')\n''')
  r=subprocess.run([sys.executable,'-I','-B',str(driver),str(code),str(selection),hashlib.sha256(raw).hexdigest()],capture_output=True,timeout=20)
  self.assertEqual(r.returncode,0,r.stderr.decode());self.assertNotIn(b'SYNTHETIC',r.stdout+r.stderr);self.assertIn(b'genuine_bridge_invented',r.stdout)
  for path in state.iterdir():self.assertNotIn(b'sk-SYNTHETIC_FIXTURE',path.read_bytes());self.assertNotIn(b'INVENTED_SSH_KEY_NOT_TO_BE_READ',path.read_bytes())

if __name__=='__main__':unittest.main()
