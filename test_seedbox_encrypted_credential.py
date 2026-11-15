import contextlib,hashlib,io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from automation import seedbox_encrypted_credential as k
from automation import seedbox_credential_provision as p
from test_reviewed_telegram_operator import fixture_acl

class EncryptedCredentialTests(unittest.TestCase):
 def setUp(self):
  fixture_acl(self);self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd());self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
  self.path=self.root/'key.cred';self.path.write_bytes(b'INVENTED_CIPHERTEXT');self.path.chmod(0o600)
  self.pin=dict(kind='seedbox_systemd_user_encrypted_v1',path=str(self.path),sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),project='proj_fixture',name=k.NAME,executable_sha256=hashlib.sha256(b'INVENTED_EXECUTABLE').hexdigest())
 def test_exact_user_decrypt_captured_memory_no_secret_argv_env_or_output(self):
  from subprocess import CompletedProcess
  calls=[]
  def command(argv,data,**kw):
   calls.append((argv,dict(kw,data=data)));return b'sk-SYNTHETIC_FIXTURE'
  output=io.StringIO()
  with patch('automation.reviewed_telegram_UNISSUED.read_file',return_value=b'INVENTED_EXECUTABLE'),patch('automation.seedbox_child.captured',side_effect=command),contextlib.redirect_stdout(output):
   value=k.credential(self.pin,project='proj_fixture')
  self.assertEqual(value.value,'sk-SYNTHETIC_FIXTURE');self.assertEqual(output.getvalue(),'');self.assertNotIn('SYNTHETIC',repr(value))
  argv,kw=calls[0];self.assertEqual(argv,['/usr/bin/systemd-creds','--user','--name='+k.NAME,'--newline=no','decrypt','-','-']);self.assertEqual(kw['data'],b'INVENTED_CIPHERTEXT');self.assertEqual(kw['environment'],{'PATH':'/usr/bin:/bin'})
  self.assertNotIn('SYNTHETIC',repr((argv,kw)))
 def test_changed_pin_refuses_before_child(self):
  self.path.write_bytes(b'CHANGED')
  with patch('automation.seedbox_child.captured') as child,self.assertRaisesRegex(ValueError,'host_credential_changed'):k.credential(self.pin,project='proj_fixture')
  child.assert_not_called()
 def test_encryption_writes_only_ciphertext_and_never_replays(self):
  from subprocess import CompletedProcess
  state=self.root/'new';state.mkdir(mode=0o700)
  fake=type('Input',(),{'buffer':io.BytesIO(b'sk-SYNTHETIC_FIXTURE')})()
  with patch.object(p.sys,'stdin',fake),patch('automation.reviewed_telegram_UNISSUED.read_file',return_value=b'INVENTED_EXECUTABLE'),patch('automation.seedbox_child.captured',return_value=b'INVENTED_CIPHERTEXT') as child:
   self.assertEqual(p.provision(state,'2026-12-01T00:00:00Z','proj_fixture','a'*64,self.pin['executable_sha256'])['status'],'encrypted_credential_stored')
   with self.assertRaises(FileExistsError):p.provision(state,'2026-12-01T00:00:00Z','proj_fixture','a'*64,self.pin['executable_sha256'])
  self.assertEqual(child.call_count,1)
  for path in state.iterdir():self.assertNotIn(b'sk-SYNTHETIC_FIXTURE',path.read_bytes())
