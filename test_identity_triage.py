"""Synthetic fixtures only; tests never reach trackers, Telegram or Radarr."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import http.client
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

import identity_triage_admin as admin
import identity_triage_intake as intake
import identity_triage_observer as observer
import identity_triage_service as service
from identity_triage_store import Store, digest, private_path

SOURCES = {'example': 'Example'}


def payload(**release_changes):
    r = {'type': 'movie', 'protocol': 'torrent', 'implementation': 'IRC',
         'title': 'Synthetic Movie', 'name': 'Synthetic.Movie.2025.1080p.Group', 'year': 2025,
         'external_id': '123', 'meta_imdb': 'tt1234567'}
    r.update(release_changes)
    return {'id': str(uuid.uuid4()), 'version': '1.0', 'event': 'release.new',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': {'release': r, 'indexer': {'identifier': 'example', 'name': 'Example'}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = Store(self.root / 'state')

    def ingest(self, p=None, channel='release_new'):
        return self.store.ingest(intake.normalize(p or payload(), SOURCES, channel), channel)

    def sql(self, query):
        with self.store.connection(readonly=True) as c:
            return c.execute(query).fetchall()


class NormalizationTests(Base):
    def test_installed_schema_accepts_movie_and_missing_optional_ids(self):
        p = payload(); p['data']['release'].pop('meta_imdb')
        r = intake.normalize(p, SOURCES)
        self.assertIsNone(r['metadata']['imdb']); self.assertIsNone(r['metadata']['tmdb'])
        self.assertEqual(self.ingest(p), 'accepted')

    def test_unsupported_event_and_source_spoof(self):
        for field, value in [('event', 'action.rejected'), ('version', '2.0')]:
            p = payload(); p[field] = value
            with self.assertRaises(intake.Reject): intake.normalize(p, SOURCES)
        for key in ('identifier', 'name'):
            p = payload(); p['data']['indexer'][key] = 'spoof'
            with self.assertRaises(intake.Reject): intake.normalize(p, SOURCES)

    def test_invalid_ids_quarantined(self):
        for key, values in {'meta_imdb': ['https://example.invalid', False, 0, [], 'tt1', 'tt١٢٣٤٥٦٧'], 'meta_tmdb': [0, False, '123', -1, []]}.items():
            for value in values:
                with self.subTest(key=key,value=value):
                    r = intake.normalize(payload(**{key: value}), SOURCES)
                    self.assertEqual(r['reason'], 'invalid_movie_metadata')
                    self.assertNotIn('metadata', r)

    def test_movie_like_missing_type_and_year_quarantine(self):
        for fields in ({'type': ''}, {'year': None}, {'title': None}, {'implementation': 'bogus'}):
            self.assertEqual(self.ingest(payload(**fields)), 'quarantined')
        with self.assertRaises(intake.Reject): intake.normalize(payload(type='episode'), SOURCES)

    def test_missing_event_id_and_invalid_date_quarantine(self):
        for field in ('id', 'timestamp'):
            p = payload(); del p[field]
            self.assertEqual(self.ingest(p), 'quarantined')
        self.assertEqual(self.store.metrics()['provisional_cases'], 0)

    def test_negative_secret_field_redaction(self):
        secret = 'CANARY_PRIVATE_CAPABILITY_DO_NOT_STORE'
        p = payload(download_url='https://private.invalid/'+secret, magnet_uri='magnet:?xt='+secret,
                    info_url='https://private.invalid/'+secret, approval_token=secret)
        p['authorization'] = secret; p['data']['result'] = {'rejections': [secret]}
        self.ingest(p)
        self.store.backup(self.root/'backup.sqlite3')
        self.assertNotIn(secret.encode(), (self.root/'backup.sqlite3').read_bytes())
        self.assertNotIn('https', str(self.sql('select metadata from evidence')))

    def test_hostile_allowed_fields_never_retained(self):
        for value in ('<script>canary</script>', 'https://invalid/canary', 'magnet:?canary', 'abc\ncanary', 'passkey=canary', 'x'*513):
            self.assertEqual(self.ingest(payload(title=value)), 'quarantined')
        self.assertEqual(self.sql('select count(*) from evidence'), [(0,)])

    def test_normal_punctuation_and_sql_text_are_data(self):
        for title in ("Synthetic: One & Two", "Synthetic'); DROP TABLE cases; --"):
            self.assertEqual(self.ingest(payload(title=title)), 'accepted')
        self.assertEqual(self.sql('select count(*) from cases'), [(2,)])

    def test_strict_json_and_oversize(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[]', b'\xff', b'['*2000, b'x'*65537):
            with self.assertRaises(intake.Reject): intake.decode(raw)


class StoreTests(Base):
    def test_event_and_regenerated_uuid_dedup(self):
        p = payload(); self.ingest(p)
        self.assertEqual(self.ingest(p), 'duplicate_event')
        p['id'] = str(uuid.uuid4()); self.ingest(p)
        m = self.store.metrics()
        self.assertEqual((m['distinct_releases'], m['evidence_versions'], m['provisional_cases']), (1,1,1))
        self.assertEqual(m['counters']['release_new']['duplicate_evidence'], 1)

    def test_distinct_release_same_provisional_case(self):
        self.ingest(); self.ingest(payload(external_id='124',name='Synthetic.Movie.2025.2160p.Group'))
        m = self.store.metrics(); self.assertEqual((m['distinct_releases'],m['evidence_versions'],m['provisional_cases']), (2,2,1))

    def test_material_change_versions_and_out_of_order(self):
        old = payload(); self.ingest(old)
        new = deepcopy(old); new['id'] = str(uuid.uuid4()); new['data']['release']['year'] = 2024; self.ingest(new)
        old['id'] = str(uuid.uuid4()); self.ingest(old)
        self.assertEqual(self.sql('select version from evidence order by version'), [(1,),(2,)])
        self.assertEqual(self.store.metrics()['evidence_versions'], 2)

    def test_conflicting_ids_never_merge_verified(self):
        self.ingest(); self.ingest(payload(meta_imdb='tt7654321',external_id='125'))
        self.assertEqual(self.sql('select status,provisional from cases'), [('unresolved',1),('unresolved',1)])

    def test_same_uuid_changed_payload_conflict(self):
        p = payload(); self.ingest(p); p['data']['release']['year'] = 2023
        self.assertEqual(self.ingest(p), 'event_conflict')
        self.assertEqual(self.sql('select count(*) from conflicts'), [(1,)])
        self.assertEqual(self.store.metrics()['evidence_versions'], 1)

    def test_outcome_correlates_without_resolving_case(self):
        p=payload(); self.ingest(p)
        event=observer.envelope(p,{'meta': {'identity_status':'imdb_associated','identity_reason':'tmdb_mapping_missing'}}, SOURCES)
        self.ingest(event,'outcome')
        self.assertEqual(self.store.metrics()['evidence_versions'],1)
        self.assertEqual(self.sql('select status from cases'),[('unresolved',)])
        self.assertEqual(self.sql('select status,reason from outcomes'),[('imdb_associated','tmdb_mapping_missing')])

    def test_concurrent_duplicates(self):
        record = intake.normalize(payload(), SOURCES)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.ingest(record,'release_new'), range(24)))
        self.assertEqual(results.count('accepted'),1); self.assertEqual(results.count('duplicate_event'),23)

    def test_concurrent_distinct_events(self):
        records = [intake.normalize(payload(external_id=str(n)), SOURCES) for n in range(16)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda r: self.store.ingest(r,'release_new'), records))
        self.assertEqual(results, ['accepted']*16)
        self.assertEqual(self.store.metrics()['provisional_cases'],1)

    def test_crash_before_commit_rolls_back(self):
        script = '''import sqlite3,os,sys
c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); c.execute('INSERT INTO releases VALUES (?)', ('crash',)); os._exit(9)
'''
        p = subprocess.run([sys.executable,'-c',script,str(self.store.path)],capture_output=True)
        self.assertEqual(p.returncode,9)
        self.assertEqual(self.sql('select count(*) from releases'),[(0,)])
        self.ingest(); self.assertEqual(self.store.metrics()['distinct_releases'],1)

    def test_crash_after_commit_recovers_duplicate(self):
        p = payload()
        script = '''import json,os,sys
from identity_triage_store import Store
from identity_triage_intake import normalize
Store(sys.argv[1]).ingest(normalize(json.loads(sys.argv[2]), {'example':'Example'}),'release_new'); os._exit(9)
'''
        run = subprocess.run([sys.executable,'-c',script,str(self.store.directory),json.dumps(p)],capture_output=True)
        self.assertEqual(run.returncode,9,run.stderr)
        self.assertEqual(self.ingest(p),'duplicate_event')

    def test_sql_busy_does_not_ack_or_partially_write(self):
        c = sqlite3.connect(self.store.path); c.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(sqlite3.OperationalError): self.ingest()
        finally: c.rollback(); c.close()
        self.assertEqual(self.store.metrics()['evidence_versions'],0)

    def test_actual_sqlite_full_rolls_back(self):
        original = self.store.connection
        @contextmanager
        def limited(*args,**kwargs):
            with original(*args,**kwargs) as c:
                count = c.execute('pragma page_count').fetchone()[0]
                c.execute('pragma max_page_count='+str(count))
                yield c
        failed = False
        with patch.object(self.store,'connection',limited):
            for n in range(300):
                try: self.ingest(payload(external_id=str(n),name='N'+str(n)+'x'*40))
                except sqlite3.OperationalError as exc:
                    self.assertIn('full',str(exc)); failed=True; break
        self.assertTrue(failed)
        self.assertEqual(self.sql('pragma integrity_check'),[('ok',)])
        self.assertEqual(self.sql('select count(*) from releases'),self.sql('select count(*) from evidence'))

    def test_permissions_and_symlinks_fail_closed(self):
        self.store.path.chmod(0o644)
        with self.assertRaises(ValueError): self.ingest()
        self.store.path.chmod(0o600)
        self.store.directory.chmod(0o755)
        with self.assertRaises(ValueError): self.store.metrics()
        self.store.directory.chmod(0o700)
        link = self.root/'link'; link.symlink_to(self.store.directory, target_is_directory=True)
        with self.assertRaises(ValueError): Store(link)

    def test_wal_shm_permissions_and_backup_rotation(self):
        with self.store.connection() as c:
            self.ingest(); self.store.check_permissions()
            for suffix in ('-wal','-shm'):
                private_path(Path(str(self.store.path)+suffix))
        target = self.root/'backup.sqlite3'; self.store.backup(target); private_path(target)
        with self.assertRaises(FileExistsError): self.store.backup(target)
        c = sqlite3.connect(target); self.addCleanup(c.close)
        self.assertEqual(c.execute('pragma quick_check').fetchone(),('ok',))

    def test_repeatable_migration_and_unknown_version_refusal(self):
        self.ingest(); Store(self.store.directory)
        self.assertEqual(self.store.metrics()['distinct_releases'],1)
        with self.store.connection() as c: c.execute('pragma user_version=2')
        with self.assertRaises(ValueError): Store(self.store.directory)

    def test_capacity_explicit_failure_duplicate_still_safe(self):
        self.store.max_deliveries=1; p=payload(); self.ingest(p)
        self.assertEqual(self.ingest(p),'duplicate_event')
        with self.assertRaises(sqlite3.OperationalError): self.ingest()

    def test_coverage_metrics_never_claim_exhaustive(self):
        self.assertEqual(self.store.metrics()['source_health'],'no_delivery_observed')
        self.ingest(); m=self.store.metrics()
        self.assertEqual(m['coverage'],'incomplete'); self.assertFalse(m['publisher_outbox'])
        self.assertIsNotNone(m['last_good_release_delivery'])


class HTTPTests(Base):
    def setUp(self):
        super().setUp()
        self.cfg={'version':1,'enabled':True,'port':40715,'sources':SOURCES,'release_key':'r'*43,'outcome_key':'o'*43}
        self.config=self.root/'config.json'; self.write_config()
        self.server=service.Server(('127.0.0.1',0),self.config,self.store)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def write_config(self):
        self.config.write_text(json.dumps(self.cfg));self.config.chmod(0o600)

    def request(self, body=None,key=None,path='/v1/release',method='POST',headers=None):
        raw=json.dumps(body if body is not None else payload()).encode()
        h={'Content-Type':'application/json','X-Identity-Intake-Key':key or self.cfg['release_key']}
        h.update(headers or {})
        c=http.client.HTTPConnection(*self.server.server_address,timeout=5)
        try:
            c.request(method,path,raw,h);r=c.getresponse();return r.status,r.read()
        finally:c.close()

    def test_committed_before_success(self):
        self.assertEqual(self.request()[0],200)
        self.assertEqual(self.store.metrics()['distinct_releases'],1)

    def test_auth_failure_and_separate_route_credentials(self):
        self.assertEqual(self.request(key='bad')[0],401)
        self.assertEqual(self.request(key=self.cfg['outcome_key'])[0],401)
        self.assertEqual(self.store.metrics()['distinct_releases'],0)

    def test_unsupported_and_spoof_rejected(self):
        p=payload();p['event']='action.rejected';self.assertEqual(self.request(p)[0],400)
        p=payload();p['data']['indexer']['identifier']='spoof';self.assertEqual(self.request(p)[0],400)

    def test_malformed_movie_persisted_as_quarantine(self):
        self.assertEqual(self.request(payload(year='invalid'))[0],200)
        self.assertEqual(self.sql('select reason from deliveries'),[('invalid_movie_metadata',)])

    def test_fixed_responses_no_payload_reflection(self):
        status,body=self.request(payload(title='<script>secret</script>'))
        self.assertEqual((status,body),(200,b'{"ok":true}'))
        status,body=self.request(path='/secret-token?canary')
        self.assertEqual(status,404);self.assertNotIn(b'canary',body)

    def test_oversize_and_chunked_requests_rejected(self):
        self.assertEqual(self.request(headers={'Content-Length':'65537'})[0],413)
        self.assertEqual(self.request(headers={'Transfer-Encoding':'chunked'})[0],400)

    def test_immediate_disable_no_store_write(self):
        self.cfg['enabled']=False;self.write_config()
        self.assertEqual(self.request()[0],503)
        self.assertEqual(self.sql('select count(*) from deliveries'),[(0,)])

    def test_busy_or_storage_failure_not_acknowledged(self):
        with patch.object(self.store,'ingest',side_effect=sqlite3.OperationalError('private-error-must-not-log')):
            with patch('sys.stdout',new_callable=io.StringIO) as output:
                status,body=self.request()
            self.assertEqual(status,503);self.assertNotIn('private-error',output.getvalue());self.assertNotIn(b'private-error',body)

    def test_authenticated_metrics(self):
        self.assertEqual(self.request(path='/metrics',method='GET',key='bad')[0],401)
        status,body=self.request(path='/metrics',method='GET')
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['coverage'],'incomplete')

    def test_hard_connection_deadline(self):
        with socket.create_connection(self.server.server_address, timeout=7) as client:
            client.sendall(b'POST /v1/release HTTP/1.1\r\n')
            stop = threading.Event()
            def trickle():
                while not stop.wait(0.1):
                    try:
                        client.sendall(b'x')
                    except OSError:
                        return
            sender = threading.Thread(target=trickle, daemon=True)
            sender.start()
            try:
                self.assertEqual(client.recv(1024), b'')
            finally:
                stop.set()
                sender.join(timeout=1)
        self.assertEqual(self.store.metrics()['distinct_releases'], 0)

    def test_no_outbound_connections_from_receiver(self):
        # Allow the test client to connect; any receiver connect attempt would fail.
        original=socket.socket.connect
        def connect(sock,address):
            if threading.current_thread() is not threading.main_thread():
                raise AssertionError('collector attempted outbound connection')
            return original(sock,address)
        with patch.object(socket.socket,'connect',connect): self.assertEqual(self.request()[0],200)


class AdminAndObserverTests(Base):
    def test_four_seed_cases_unresolved_and_idempotent(self):
        rows=[]
        for n in range(4):
            p=payload(title='Synthetic Case '+str(n),external_id=str(n));p['data']['seed']={'provenance':digest(n),'contradictions':['missing_crosswalk']};rows.append(p)
        bundle=self.root/'seed.json';bundle.write_text(json.dumps({'version':1,'cases':rows}));bundle.chmod(0o600)
        self.assertEqual(admin.seed(self.store,bundle,SOURCES),['accepted']*4)
        self.assertEqual(admin.seed(self.store,bundle,SOURCES),['duplicate_event']*4)
        self.assertEqual(self.sql('select status from cases'),[('unresolved',)]*4)
        self.assertEqual(self.store.metrics()['seed_associations'],4)

    def test_seed_insufficient_evidence_rejected_before_write(self):
        bundle=self.root/'seed.json';bundle.write_text('{"version":1,"cases":[]}');bundle.chmod(0o600)
        with self.assertRaises(ValueError):admin.seed(self.store,bundle,SOURCES)
        self.assertEqual(self.store.metrics()['distinct_releases'],0)

    def test_limited_reconciliation_is_readonly_and_separate(self):
        database=self.root/'autobrr.sqlite3';c=sqlite3.connect(database)
        c.execute('create table release(id,type,torrent_id,title,year,torrent_name,timestamp,"indexer",protocol,implementation)')
        p=payload();r=p['data']['release']
        for i,t in enumerate(('movie','episode','movie'),1):
            c.execute('insert into release values(?,?,?,?,?,?,?,?,?,?)',(i,t,str(i),r['title'],r['year'],r['name'],p['timestamp'],'example','torrent','IRC'))
        c.commit();c.close();before=database.read_bytes()
        result=admin.reconcile(self.store,database,SOURCES,limit=2)
        self.assertEqual(result['rows_scanned'],2);self.assertEqual(result['results'],{'accepted':1,'rejected':1})
        self.assertEqual(database.read_bytes(),before)
        self.assertIsNone(self.store.metrics()['last_good_release_delivery'])
        self.assertEqual(admin.reconcile(self.store,database,SOURCES,limit=2)['results']['duplicate_event'],1)

    def test_observer_default_off_and_failure_is_contained(self):
        p=payload();original=deepcopy(p)
        with patch.dict(os.environ,{},clear=True),patch.object(observer,'_send') as send:
            observer.observe(p,{});send.assert_not_called()
        with patch.dict(os.environ,{'MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED':'1'},clear=True),patch('sys.stdout',new_callable=io.StringIO):
            observer.observe(p,{})
        self.assertEqual(p,original)

    def test_observer_only_allowlisted_metadata_crosses_boundary(self):
        p=payload(download_url='https://private.invalid/capability'); original=deepcopy(p)
        row=observer.envelope(p,{'text':'private capability','meta':{'identity_status':'needs_review','identity_reason':'unsafe text'}}, SOURCES)
        self.assertNotIn('private',json.dumps(row));self.assertEqual(p,original)
        self.assertEqual(row['data']['outcome']['reason'],'other')

    def test_service_preflight_refuses_readable_action_directory(self):
        (self.root/'.config').mkdir();(self.root/'.config/movie-intel').mkdir()
        with self.assertRaises(ValueError): service.isolation_check(self.root)

    def test_config_credential_permissions_and_distinct_keys(self):
        cfg={'version':1,'enabled':False,'port':40715,'sources':SOURCES,'release_key':'r'*43,'outcome_key':'r'*43}
        path=self.root/'config';path.write_text(json.dumps(cfg));path.chmod(0o600)
        with self.assertRaises(ValueError):service.read_config(path)
        cfg['outcome_key']='o'*43;path.write_text(json.dumps(cfg));self.assertFalse(service.read_config(path)['enabled'])
        path.chmod(0o644)
        with self.assertRaises(ValueError):service.read_config(path)


if __name__=='__main__':unittest.main()
