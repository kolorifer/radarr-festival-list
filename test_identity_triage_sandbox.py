"""Unit gates and isolated kernel checks; full user-service proof is deployment-gated."""
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import identity_triage_sandbox as sandbox
from identity_triage_service import Server
from identity_triage_store import Store


class PolicyTests(unittest.TestCase):
    def test_kernel_structure_layout(self):
        self.assertEqual(ctypes.sizeof(sandbox.Ruleset),24)
        self.assertEqual(ctypes.sizeof(sandbox.Beneath),12)
        self.assertFalse(sandbox.STATE & 1)  # no executable state
        self.assertFalse(sandbox.STATE & (1<<13))  # no cross-tree file moves
        self.assertEqual(sandbox.HANDLED_FS,65535)

    def test_unsupported_platform_fails_closed(self):
        with patch.object(sandbox.platform,'system',return_value='Other'):
            with self.assertRaises(ValueError):sandbox._kernel()

    def test_old_abi_fails_before_rules_or_restrict_self(self):
        with patch.object(sandbox,'_kernel'),patch.object(sandbox,'_call',return_value=5) as call:
            with self.assertRaises(ValueError):sandbox.restrict([],Path('/not-used'))
            self.assertEqual(call.call_count,1)

    def test_kernel_refusal_propagates_without_fallback(self):
        with patch.object(sandbox,'_kernel'),patch.object(sandbox,'_call',side_effect=PermissionError):
            with self.assertRaises(PermissionError):sandbox.restrict([],Path('/not-used'))

    def test_denial_gate_rejects_success_and_unexpected_errors(self):
        with self.assertRaises(ValueError):sandbox.deny_check(lambda:None)
        with self.assertRaises(ValueError):sandbox.deny_check(lambda:(_ for _ in ()).throw(OSError(5,'io')))
        sandbox.deny_check(lambda:(_ for _ in ()).throw(PermissionError(13,'denied')))
        with self.assertRaises(ValueError):sandbox.deny_check(lambda:(_ for _ in ()).throw(FileNotFoundError(2,'missing')))

    def test_private_layout_rejects_permissions_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();root.chmod(0o700)
            self.assertEqual(sandbox._private_directory(root),root)
            link=root/'link';link.symlink_to(root,target_is_directory=True)
            with self.assertRaises(ValueError):sandbox._private_directory(link)
            root.chmod(0o755)
            with self.assertRaises(ValueError):sandbox._private_directory(root)

    def test_socket_activation_does_not_create_another_socket(self):
        with tempfile.TemporaryDirectory() as temporary:
            store=Store(Path(temporary).resolve()/'state')
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(8)
            with patch.object(socket,'socket',side_effect=AssertionError('new socket')):
                server=Server(listener.getsockname(),Path(temporary)/'unused',store,listener=listener)
                self.assertEqual(server.socket,listener);server.server_close()

    def test_no_plain_unconfined_service_start(self):
        result=subprocess.run([sys.executable,'identity_triage_service.py','--config','/missing/config','--state','/missing/state'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertNotIn('sandbox_verified',result.stdout)
        self.assertNotIn('Traceback',result.stderr)

    def test_unit_has_effective_complement_without_namespace_claims(self):
        text=Path('deploy/identity-triage.service').read_text()
        for required in ('NoNewPrivileges=yes','SystemCallArchitectures=native','socket socketpair connect',
                         '@chown chmod fchmod fchmodat fchmodat2','utimensat','fremovexattr',
                         'pidfd_getfd','io_uring_setup','StandardInput=null','UMask=0077'):
            self.assertIn(required,text)
        for unsupported in ('PrivateUsers=','InaccessiblePaths=','ProtectHome=','BindPaths='):
            self.assertNotIn(unsupported,text)
        self.assertIn('ListenStream=127.0.0.1:40715',Path('deploy/identity-triage.socket').read_text())

    def test_real_kernel_filesystem_policy_in_disposable_child(self):
        if sys.platform!='linux' or sandbox.platform.machine()!='x86_64':
            self.skipTest('Linux x86-64 required; actual provider unit separately verified')
        try:
            libc=sandbox._kernel();abi=sandbox._call(libc,444,ctypes.c_void_p(),ctypes.c_size_t(0),1)
        except OSError:
            self.skipTest('kernel Landlock unavailable; startup must fail closed')
        if abi<6:self.skipTest('kernel ABI6 unavailable; startup must fail closed')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            for d in ('code','config','state','protected'):(root/d).mkdir(mode=0o700)
            (root/'protected/canary').write_text('synthetic')
            (root/'state/escape').symlink_to(root/'protected/canary')
            code='''import json,os,sys,sqlite3
from pathlib import Path
from identity_triage_sandbox import restrict,deny_check
root=Path(sys.argv[1]);restrict([root/'code',root/'config'],root/'state')
for p in (root/'protected/canary',root/'state/escape'):
 deny_check(lambda p=p:os.open(p,os.O_RDONLY));deny_check(lambda p=p:os.open(p,os.O_WRONLY))
c=sqlite3.connect(root/'state/proof.sqlite3');c.execute('pragma journal_mode=wal');c.execute('create table proof(v)');c.execute('insert into proof values(1)');c.commit();assert c.execute('select v from proof').fetchone()==(1,);c.close();print('kernel_policy_passed')
'''
            result=subprocess.run([sys.executable,'-c',code,str(root)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),'kernel_policy_passed')


if __name__=='__main__':unittest.main()
