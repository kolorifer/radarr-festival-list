"""Invented real Handler/SQLite tests; no socket creation or external I/O."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

import identity_triage_capture as capture
import identity_triage_service as service
from identity_triage_store import Store
from identity_triage_intake import normalize
from test_identity_triage import payload, SOURCES


class FakeSocket:
    def __init__(self, request): self.input = io.BytesIO(request); self.output = bytearray()
    def makefile(self, *args): return self.input
    def sendall(self, data): self.output.extend(data)
    def shutdown(self, *args): pass
    def settimeout(self, *args): pass


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = Store(self.root / 'state')
        self.config = self.root / 'config.json'
        self.cfg = dict(version=1, enabled=True, port=12345, sources=SOURCES,
                        release_key='a'*43, outcome_key='b'*43)
        # Real Server initialization using an inherited fake listener, no bind.
        class Listener:
            def getsockname(self): return ('127.0.0.1', 12345)
        self.server = service.Server(('127.0.0.1', 12345), self.config, self.store, Listener())
        self.save()
        self.p = payload(); self.store.ingest(normalize(self.p, SOURCES), 'release_new')

    def save(self):
        self.config.write_text(json.dumps(self.cfg)); self.config.chmod(0o600)

    def outcome(self, **changes):
        e = deepcopy(self.p); e.update(id=str(uuid.uuid4()), event='identity.outcome', **changes)
        e['data']['outcome'] = dict(status='unresolved', category='unknown_movie', reason='no_exact_match')
        return e

    def arm(self, **changes):
        self.server.capture.context()
        g = dict(version=1, nonce=self.server.capture.nonce, source='example', channel='outcome',
                 filter=dict(mode='exact_external_id',external_id='123', status='unresolved', reason='no_exact_match'),
                 expires_at=time.time()+600, destination=dict(body=capture.BODY, receipt=capture.RECEIPT),
                 privacy='private_local_raw_observer_body_no_api_disclosure')
        g.update(changes); raw=capture.encoded(g)
        p=self.store.directory/capture.GRANT; p.write_bytes(raw); p.chmod(0o600)
        self.cfg.update(capture_prepare=True,capture_grant_sha256=hashlib.sha256(raw).hexdigest());self.save()
        return g

    def request(self, e=None, *, get=False, key=None):
        raw = json.dumps(e, indent=1).encode() if e is not None else b''
        path='/health' if get else '/v1/outcome'
        key=key or self.cfg['release_key' if get else 'outcome_key']
        request=(f'{"GET" if get else "POST"} {path} HTTP/1.0\r\nX-Identity-Intake-Key: {key}\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\n\r\n').encode()+raw
        sock=FakeSocket(request)
        service.Handler(sock,('127.0.0.1',1),self.server)
        return bytes(sock.output),raw

    def test_raw_native_receipt_and_default_health(self):
        with patch.object(service,'read_config',wraps=service.read_config) as reads:
            before,_=self.request(get=True)
            self.assertEqual(reads.call_count,2)
        self.assertNotIn(b'capture_nonce',before)
        self.assertEqual(before.split(b'\r\n\r\n')[1],b'{"ok":true}')
        self.assertFalse(self.server.capture.initialized)
        self.arm();health,_=self.request(get=True);self.assertIn(self.server.capture.nonce.encode(),health)
        e=self.outcome();response,raw=self.request(e);self.assertIn(b'200 OK',response)
        self.assertEqual((self.store.directory/capture.BODY).read_bytes(),raw)
        r=json.loads((self.store.directory/capture.RECEIPT).read_bytes())
        self.assertEqual(r['body_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r['event_id'],e['id'])
        with self.store.connection(True) as c:
            self.assertEqual(c.execute('select event_id,evidence from deliveries where rowid=?',(r['delivery_rowid'],)).fetchone(),(e['id'],r['evidence_id']))
            self.assertEqual(c.execute('select version from selection_current where case_key=?',(r['case_id'],)).fetchone(),(r['case_version'],))
            self.assertEqual(c.execute('select evidence from selection_events where id=?',(r['selection_event'],)).fetchone(),(r['evidence_id'],))
        for name in (capture.GRANT,capture.RESERVATION,capture.BODY,capture.RECEIPT):
            self.assertEqual((self.store.directory/name).stat().st_mode&0o777,0o600)
        self.assertNotIn(self.cfg['outcome_key'],(self.store.directory/capture.BODY).read_text())

    def test_default_off_does_not_access_capture_files(self):
        with patch.object(capture,'read_at',side_effect=AssertionError('read')),patch.object(capture,'write_at',side_effect=AssertionError('write')):
            self.assertIn(b'200 OK',self.request(self.outcome())[0])
        self.assertFalse(self.server.capture.burned)

    def test_reservation_failure_burns_through_reload_toggle_restart(self):
        self.arm()
        with patch.object(capture,'write_at',side_effect=OSError('invented disk full')):
            self.assertIn(b'200 OK',self.request(self.outcome())[0])
        self.assertTrue(self.server.capture.burned)
        self.cfg.pop('capture_grant_sha256');self.cfg['capture_prepare']=False;self.save()
        self.request(self.outcome());self.arm();self.request(self.outcome())
        self.assertFalse((self.store.directory/capture.BODY).exists())
        old=self.server.capture.nonce
        self.server.capture=capture.Capture(self.store.directory)
        self.assertNotEqual(old,self.server.capture.nonce)
        self.request(self.outcome());self.assertFalse(self.server.capture.burned)
        self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_nonce_failure_never_retried(self):
        with patch.object(capture.secrets,'token_hex',side_effect=OSError('entropy')) as gen:
            self.server.capture=capture.Capture(self.store.directory)
            self.arm();self.request(self.outcome());self.cfg['capture_prepare']=False;self.save()
            self.request(self.outcome());self.arm();self.request(self.outcome())
            self.assertEqual(gen.call_count,1)
        self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_fsync_and_partial_failure_no_replacement(self):
        self.arm()
        with patch.object(capture.os,'fsync',side_effect=OSError('fsync')):
            self.assertIn(b'200 OK',self.request(self.outcome())[0])
        self.assertTrue(self.server.capture.burned);self.assertTrue((self.store.directory/capture.RESERVATION).exists())
        self.request(self.outcome());self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_partial_receipt_failure_preserves_body_and_ack(self):
        self.arm();original=capture.write_at
        def write(parent,name,raw):
            if name==capture.RECEIPT:raise OSError('receipt')
            return original(parent,name,raw)
        with patch.object(capture,'write_at',side_effect=write):
            response,raw=self.request(self.outcome())
        self.assertIn(b'200 OK',response);self.assertEqual((self.store.directory/capture.BODY).read_bytes(),raw)
        self.request(self.outcome());self.assertEqual((self.store.directory/capture.BODY).read_bytes(),raw)
        self.assertFalse((self.store.directory/capture.RECEIPT).exists())

    def test_concurrent_candidates_capture_once(self):
        self.arm()
        with ThreadPoolExecutor(4) as pool:results=list(pool.map(self.request,[self.outcome() for _ in range(4)]))
        self.assertTrue(all(b'200 OK' in r[0] for r in results))
        self.assertIn((self.store.directory/capture.BODY).read_bytes(),[r[1] for r in results])
        self.assertTrue(self.server.capture.burned)

    def test_expired_wrong_filter_unknown_private_field(self):
        self.arm(expires_at=time.time()-1);self.request(self.outcome());self.assertFalse(self.server.capture.burned)
        self.arm(filter=dict(mode='exact_external_id',external_id='other',status='unresolved',reason='no_exact_match'))
        self.request(self.outcome());self.assertFalse(self.server.capture.burned)
        self.arm();e=self.outcome();e['data']['release']['download_url']='https://private.invalid/secret'
        self.assertIn(b'200 OK',self.request(e)[0]);self.assertFalse(self.server.capture.burned)

    def test_delayed_selected_material_mismatch(self):
        newer=self.outcome(timestamp=(datetime.now(timezone.utc)+timedelta(seconds=10)).isoformat())
        self.request(newer);self.arm();self.request(self.outcome())
        self.assertFalse(self.server.capture.burned)

    def test_symlink_no_overwrite_and_unauthorized_health(self):
        self.arm();target=self.root/'untouched';target.write_bytes(b'protected')
        (self.store.directory/capture.BODY).symlink_to(target)
        self.assertIn(b'200 OK',self.request(self.outcome())[0]);self.assertEqual(target.read_bytes(),b'protected')
        self.assertTrue(self.server.capture.burned)
        self.assertNotIn(self.server.capture.nonce.encode(),self.request(get=True,key='bad')[0])

    def test_duplicate_and_conflict_do_not_burn(self):
        e=self.outcome();self.request(e);self.arm()
        self.assertIn(b'200 OK',self.request(e)[0]);self.assertFalse(self.server.capture.burned)
        e['data']['outcome']['reason']='year_conflict'
        self.assertIn(b'409 Conflict',self.request(e)[0]);self.assertFalse(self.server.capture.burned)

    def test_commit_failure_burns_and_never_retains(self):
        self.arm()
        from contextlib import contextmanager
        original=self.store.connection
        class Connection:
            def __init__(self,c):self.c=c
            def __getattr__(self,k):return getattr(self.c,k)
            def commit(self):raise sqlite3.OperationalError('invented failure')
        @contextmanager
        def failing(*a,**kw):
            with original(*a,**kw) as c:yield Connection(c)
        with patch.object(self.store,'connection',failing):
            self.assertIn(b'503 Service Unavailable',self.request(self.outcome())[0])
        self.assertTrue(self.server.capture.burned);self.request(self.outcome())
        self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_grant_symlink_and_wrong_mode_refuse_without_reading_target(self):
        self.arm();g=self.store.directory/capture.GRANT;raw=g.read_bytes();g.unlink()
        target=self.root/'outside-grant';target.write_bytes(raw);target.chmod(0o600);g.symlink_to(target)
        self.request(self.outcome());self.assertFalse(self.server.capture.burned)
        g.unlink();g.write_bytes(raw);g.chmod(0o644)
        self.request(self.outcome());self.assertFalse(self.server.capture.burned)

    def test_future_clamped_and_unmatched_do_not_capture(self):
        self.arm();e=self.outcome(timestamp=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
        self.request(e);self.assertFalse(self.server.capture.burned)
        e=self.outcome();e['data']['release']['name']='Different.Movie.2025'
        self.request(e);self.assertFalse(self.server.capture.burned)

    def test_interrupted_after_commit_never_replaces(self):
        self.arm()
        with patch.object(self.server.capture,'finish',side_effect=self.server.capture.abandon):
            self.assertIn(b'200 OK',self.request(self.outcome())[0])
        self.request(self.outcome());self.assertFalse((self.store.directory/capture.BODY).exists())
        self.server.capture=capture.Capture(self.store.directory)
        self.request(self.outcome());self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_strict_capture_configuration(self):
        for changes in ({'capture_prepare':1},{'capture_grant_sha256':'a'*64},
                        {'capture_prepare':True,'capture_grant_sha256':'bad'}):
            original=dict(self.cfg);self.cfg.update(changes);self.save()
            with self.assertRaises(ValueError):service.read_config(self.config)
            self.cfg=original
        self.save();self.assertEqual(service.read_config(self.config),self.cfg)

    def test_isolated_six_module_default_startup(self):
        import subprocess,sys,shutil
        isolated=self.root/'isolated';isolated.mkdir()
        for name in ('service','intake','store','sandbox','capture'):
            shutil.copyfile(Path(__file__).parent/('identity_triage_'+name+'.py'),isolated/('identity_triage_'+name+'.py'))
        shutil.copyfile(Path(__file__).parent/'identity_selection.py',isolated/'identity_selection.py')
        code="""import sys
sys.path.insert(0,sys.argv[1])
def audit(event,args):
 if event.startswith('socket.'):raise RuntimeError('socket tripwire')
sys.addaudithook(audit)
import identity_triage_service as service
from identity_triage_store import Store
class Listener:
 def getsockname(self):return ('127.0.0.1',12345)
s=service.Server(('127.0.0.1',12345),sys.argv[2],Store(sys.argv[3]),Listener())
assert service.read_config(sys.argv[2]).get('capture_prepare',False) is False
assert not s.capture.burned
print('isolated_default_startup_passed')
"""
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(isolated),str(self.config),str(self.root/'isolated-state')],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('isolated_default_startup_passed',result.stdout)

    def test_first_matching_mode_and_volatile_phase(self):
        self.arm(filter=dict(mode='first_matching',status='unresolved',reason='no_exact_match'))
        self.assertEqual(self.server.capture.context()['capture_phase'],'ready')
        self.request(self.outcome())
        self.assertEqual(self.server.capture.context()['capture_phase'],'complete')
        self.assertTrue(self.server.capture.context()['capture_phase_volatile'])

    def test_capture_close_errors_preserve_accepted_ack(self):
        self.arm();close=capture.os.close
        def fail_after_close(fd):
            close(fd);raise OSError('invented close failure')
        with patch.object(capture.os,'close',side_effect=fail_after_close):
            response,_=self.request(self.outcome())
        self.assertIn(b'200 OK',response)
        self.assertTrue(self.server.capture.burned)

    def test_grant_io_failure_disables_lifetime_no_replacement(self):
        self.arm()
        with patch.object(capture,'read_at',side_effect=OSError('read failed')):
            self.assertIn(b'200 OK',self.request(self.outcome())[0])
        self.assertTrue(self.server.capture.unavailable)
        self.assertEqual(self.server.capture.context()['capture_phase'],'validation_failed')
        self.request(self.outcome());self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_revoke_config_before_burn(self):
        self.arm();read=capture.read_at
        def revoke(*args):
            raw=read(*args);self.cfg.pop('capture_grant_sha256');self.cfg['capture_prepare']=False;self.save();return raw
        with patch.object(capture,'read_at',side_effect=revoke):
            self.assertIn(b'200 OK',self.request(self.outcome())[0])
        self.assertFalse(self.server.capture.burned)
        self.assertFalse((self.store.directory/capture.BODY).exists())

    def test_atime_only_allowed_content_metadata_change_refused(self):
        self.arm();parent=os.open(self.store.directory,os.O_RDONLY|os.O_DIRECTORY)
        self.addCleanup(os.close,parent)
        original=capture.os.fstat
        from types import SimpleNamespace
        names=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns','st_atime_ns')
        for field,should_fail in (('st_atime_ns',False),('st_mtime_ns',True),('st_ctime_ns',True),('st_size',True)):
            calls=[0]
            def stat_change(fd):
                st=original(fd);d={k:getattr(st,k) for k in names};calls[0]+=1
                if calls[0]==2:d[field]+=1
                return SimpleNamespace(**d)
            with patch.object(capture.os,'fstat',side_effect=stat_change):
                if should_fail:
                    with self.assertRaises(ValueError):capture.read_at(parent,capture.GRANT,4096)
                else:self.assertTrue(capture.read_at(parent,capture.GRANT,4096))


if __name__=='__main__':unittest.main()
