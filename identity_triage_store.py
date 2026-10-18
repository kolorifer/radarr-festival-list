"""Private observational inbox. No provider, notification or action dependencies."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
import uuid
from contextlib import contextmanager

SCHEMA_VERSION = 1
CHANNELS = {'release_new', 'outcome', 'retained', 'seed'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def private_path(path, directory=False):
    path = Path(path)
    s = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (not kind(s.st_mode) or s.st_uid != os.getuid()
            or stat.S_IMODE(s.st_mode) != (0o700 if directory else 0o600)
            or (not directory and s.st_nlink != 1)):
        raise ValueError('private_permissions')
    return path


def private_directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('private_path')
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    return private_path(path, True)


def create_private(path):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    private_path(path)


class Store:
    def __init__(self, directory, max_deliveries=1_000_000, timeout=0.25):
        self.directory = private_directory(directory)
        self.path = self.directory / 'inbox.sqlite3'
        self.max_deliveries = max_deliveries
        self.timeout = timeout
        try:
            create_private(self.path)
        except FileExistsError:
            pass
        self.check_permissions()
        with self.connection() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('PRAGMA journal_size_limit=8388608')
            c.execute('BEGIN IMMEDIATE')
            version = c.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise ValueError('schema_version')
            if version == 0:
                for statement in (
                    'CREATE TABLE cases (id TEXT PRIMARY KEY, grouping TEXT UNIQUE NOT NULL, status TEXT NOT NULL CHECK(status="unresolved"), provisional INTEGER NOT NULL CHECK(provisional=1))',
                    'CREATE TABLE releases (fingerprint TEXT PRIMARY KEY)',
                    'CREATE TABLE evidence (id TEXT PRIMARY KEY, release TEXT NOT NULL REFERENCES releases(fingerprint), case_id TEXT NOT NULL REFERENCES cases(id), version INTEGER NOT NULL, metadata TEXT NOT NULL, UNIQUE(release,version))',
                    'CREATE TABLE deliveries (channel TEXT NOT NULL, event_id TEXT NOT NULL, signature TEXT NOT NULL, evidence TEXT REFERENCES evidence(id), reason TEXT, source_time REAL, received REAL NOT NULL, PRIMARY KEY(channel,event_id))',
                    'CREATE TABLE conflicts (channel TEXT NOT NULL, event_id TEXT NOT NULL, signature TEXT NOT NULL, PRIMARY KEY(channel,event_id,signature))',
                    'CREATE TABLE outcomes (evidence TEXT NOT NULL REFERENCES evidence(id), category TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL, PRIMARY KEY(evidence,category,status,reason))',
                    'CREATE TABLE seeds (evidence TEXT NOT NULL REFERENCES evidence(id), provenance TEXT NOT NULL, contradictions TEXT NOT NULL, PRIMARY KEY(evidence,provenance))',
                    'CREATE TABLE counters (channel TEXT NOT NULL, name TEXT NOT NULL, value INTEGER NOT NULL, PRIMARY KEY(channel,name))',
                    'CREATE INDEX evidence_release ON evidence(release)',
                ):
                    c.execute(statement)
                c.execute('PRAGMA user_version=1')
            c.commit()
        self.check_permissions()

    def check_permissions(self):
        private_path(self.directory, True)
        for suffix in ('', '-wal', '-shm', '-journal'):
            p = Path(str(self.path) + suffix)
            if p.exists() or p.is_symlink():
                private_path(p)

    @contextmanager
    def connection(self, readonly=False):
        self.check_permissions()
        c = sqlite3.connect(self.path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                            uri=True, timeout=self.timeout, isolation_level=None)
        try:
            c.execute('PRAGMA foreign_keys=ON')
            c.execute('PRAGMA synchronous=FULL')
            yield c
            self.check_permissions()
        finally:
            c.close()  # uncommitted work is rolled back, including commit failures

    @staticmethod
    def count(c, channel, name):
        c.execute('INSERT INTO counters VALUES (?,?,1) ON CONFLICT(channel,name) DO UPDATE SET value=value+1', (channel, name))

    def reject(self, channel):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.count(c, channel, 'rejected')
            c.commit()

    def ingest(self, record, channel):
        # record is the normalizer's allowlisted output, never an upstream payload.
        if channel not in CHANNELS:
            raise ValueError('channel')
        signature = digest({k: v for k, v in record.items() if k != 'time'})
        now = time.time()
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            previous = c.execute('SELECT signature FROM deliveries WHERE channel=? AND event_id=?',
                                 (channel, record['event_id'])).fetchone()
            if previous:
                result = 'duplicate_event' if previous[0] == signature else 'event_conflict'
                if result == 'event_conflict':
                    if c.execute('SELECT count(*) FROM conflicts').fetchone()[0] >= self.max_deliveries:
                        raise sqlite3.OperationalError('capacity')
                    c.execute('INSERT OR IGNORE INTO conflicts VALUES (?,?,?)', (channel, record['event_id'], signature))
                    self.count(c, channel, 'quarantined')
                self.count(c, channel, result)
                c.commit()
                return result
            if c.execute('SELECT count(*) FROM deliveries').fetchone()[0] >= self.max_deliveries:
                raise sqlite3.OperationalError('capacity')
            evidence_id = None
            reason = record.get('reason')
            result = 'quarantined' if reason else 'accepted'
            if not reason:
                meta = record['metadata']
                release = record['release']
                evidence_id = digest([release, meta])
                existing = c.execute('SELECT 1 FROM evidence WHERE id=?', (evidence_id,)).fetchone()
                if existing:
                    self.count(c, channel, 'duplicate_evidence')
                else:
                    # Claims remain unverified; different/missing IDs partition groups.
                    grouping = digest([meta['title_key'], meta['year'], meta['imdb'], meta['tmdb']])
                    c.execute('INSERT OR IGNORE INTO cases VALUES (?, ?, "unresolved", 1)', (str(uuid.uuid4()), grouping))
                    case_id = c.execute('SELECT id FROM cases WHERE grouping=?', (grouping,)).fetchone()[0]
                    c.execute('INSERT OR IGNORE INTO releases VALUES (?)', (release,))
                    version = c.execute('SELECT coalesce(max(version),0)+1 FROM evidence WHERE release=?', (release,)).fetchone()[0]
                    c.execute('INSERT INTO evidence VALUES (?,?,?,?,?)',
                              (evidence_id, release, case_id, version, json.dumps(meta, sort_keys=True)))
                if 'outcome' in record:
                    o = record['outcome']
                    c.execute('INSERT OR IGNORE INTO outcomes VALUES (?,?,?,?)',
                              (evidence_id, o['category'], o['status'], o['reason']))
                if 'seed' in record:
                    s = record['seed']
                    c.execute('INSERT OR IGNORE INTO seeds VALUES (?,?,?)',
                              (evidence_id, s['provenance'], json.dumps(s['contradictions'])))
            c.execute('INSERT INTO deliveries VALUES (?,?,?,?,?,?,?)',
                      (channel, record['event_id'], signature, evidence_id, reason, record.get('time'), now))
            self.count(c, channel, result)
            c.commit()  # HTTP success is permitted only after this returns.
        return result

    def metrics(self):
        with self.connection(readonly=True) as c:
            counts = {}
            for channel, name, value in c.execute('SELECT channel,name,value FROM counters'):
                counts.setdefault(channel, {})[name] = value
            last, lag = c.execute('SELECT max(received), max(max(0,received-source_time)) FROM deliveries WHERE channel="release_new" AND evidence IS NOT NULL').fetchone()
            tables = {name: c.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                      for name, table in (('observed_movie_deliveries', 'deliveries WHERE evidence IS NOT NULL'),
                                          ('distinct_releases', 'releases'), ('evidence_versions', 'evidence'),
                                          ('provisional_cases', 'cases'), ('seed_associations', 'seeds'))}
        return dict(tables, counters=counts, last_good_release_delivery=last, max_delivery_lag_seconds=lag,
                    coverage='incomplete', publisher_outbox=False,
                    source_health='no_delivery_observed' if last is None else 'stale_or_quiet' if time.time()-last > 900 else 'recent_delivery',
                    source_gap_detection='cannot_distinguish_quiet_source_from_lost_events')

    def backup(self, destination):
        destination = Path(destination)
        private_directory(destination.parent)
        create_private(destination)  # never overwrite an earlier backup
        try:
            with self.connection(readonly=True) as source:
                target = sqlite3.connect(destination)
                try:
                    source.backup(target)
                    if target.execute('PRAGMA quick_check').fetchone() != ('ok',):
                        raise ValueError('backup_integrity')
                finally:
                    target.close()
            private_path(destination)
            with destination.open('rb') as f:
                os.fsync(f.fileno())
            fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except Exception:
            # An incomplete backup is never presented as usable.
            destination.unlink(missing_ok=True)
            raise
