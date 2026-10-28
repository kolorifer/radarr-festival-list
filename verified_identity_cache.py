"""Optional private, bounded persistence for verified metadata responses.

Keys include the full caller-supplied identity context. Cache failures are misses;
no failed lookup, tracker credential, release URL or approval token is stored.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

SETTING = 'MOVIE_INTEL_VERIFIED_CACHE_PATH'
TTL = 7 * 86400
LIMIT = 1024


def configured_path(env=None):
    env = os.environ if env is None else env
    value = env.get(SETTING)
    if not value:
        return None
    from identity_triage_store import private_path
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('cache_path')
    private_path(path.parent, True)
    if path.exists():
        private_path(path)
    return path


def _connect():
    path = configured_path()
    if path is None:
        return None
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    connection = sqlite3.connect(path, timeout=0.25)
    try:
        connection.execute('create table if not exists verified_cache (key text primary key, value text not null, created real not null, expires real not null)')
    except Exception:
        connection.close()
        raise
    return connection


def _key(namespace, context):
    return hashlib.sha256(json.dumps([1, namespace, context], sort_keys=True).encode()).hexdigest()


def get(namespace, context):
    connection = None
    try:
        connection = _connect()
        if connection is None:
            return None
        row = connection.execute('select value,created,expires from verified_cache where key=?', (_key(namespace, context),)).fetchone()
        now = time.time()
        if not row or not row[1] <= now < row[2] or row[2] - row[1] > TTL or len(row[0]) > 32768:
            return None
        value = json.loads(row[0])
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return None
    finally:
        if connection is not None:
            connection.close()


def put(namespace, context, value):
    connection = None
    try:
        raw = json.dumps(value)
        if len(raw.encode()) > 32768:
            return False
        connection = _connect()
        if connection is None:
            return False
        now = time.time()
        with connection:
            connection.execute('delete from verified_cache where expires<=?', (now,))
            connection.execute('insert into verified_cache values(?,?,?,?) on conflict(key) do update set value=excluded.value,created=excluded.created,expires=excluded.expires', (_key(namespace, context), raw, now, now + TTL))
            connection.execute('delete from verified_cache where key in (select key from verified_cache order by created desc,key limit -1 offset ?)', (LIMIT,))
        return True
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return False
    finally:
        if connection is not None:
            connection.close()


def remember(context, movie, *, conflict=False, verified_at=None):
    """Atomically preserve ambiguity instead of letting the last writer win."""
    connection = None
    try:
        connection = _connect()
        if connection is None:
            return False
        now = time.time()
        created = now if verified_at is None else float(verified_at)
        if not now-TTL < created <= now:return False
        key = _key('remembered_movie', context)
        connection.execute('begin immediate')
        row = connection.execute('select value,expires,created from verified_cache where key=?', (key,)).fetchone()
        previous = json.loads(row[0]) if row and row[1] > now else {}
        old = previous.get('movie') or {}
        ambiguous = (conflict or previous.get('ambiguous') is True or
                     bool(old and any(old.get(k) != movie.get(k) for k in ('imdb_id','tmdb_id'))))
        if row and row[1] > now:
            if row[2] > created and not ambiguous:return True
            created=max(created,row[2])
        value = {'ambiguous':ambiguous, 'movie':{} if ambiguous else movie, 'verified_at':created}
        raw = json.dumps(value)
        if len(raw.encode()) > 32768:
            return False
        with connection:
            connection.execute('insert into verified_cache values(?,?,?,?) on conflict(key) do update set value=excluded.value,created=excluded.created,expires=excluded.expires', (key,raw,created,created+TTL))
            connection.execute('delete from verified_cache where expires<=?',(now,))
            connection.execute('delete from verified_cache where key in (select key from verified_cache order by created desc,key limit -1 offset ?)',(LIMIT,))
        return True
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return False
    finally:
        if connection is not None:
            connection.close()
