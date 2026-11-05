"""Exact-event pending-state query, inside the same confined read-only operation.

No source path or transport is implemented here. The host adapter must bind
the UUID to the validated selected collector result and enforce source guards,
read-only connections, no-create/unlink confinement and operation bounds.
"""
import math
import sqlite3
import time
import uuid
from . import source_rows as row_budget

_PENDING_COLUMNS = (
    (0, 'id', 'TEXT', 0, None, 1, 0),
    (1, 'body', 'TEXT', 1, None, 0, 0),
    (2, 'created', 'REAL', 1, None, 0, 0),
    (3, 'attempts', 'INTEGER', 1, '0', 0, 0),
    (4, 'due', 'REAL', 1, None, 0, 0),
)


def _authorize(action, arg1, arg2, database, source):
    # No view, trigger, other table or body-column reads. This is an additional
    # SQL restriction, not process isolation or event-specific row security.
    if action == sqlite3.SQLITE_SELECT and source is None:
        return sqlite3.SQLITE_OK
    if (action == sqlite3.SQLITE_READ and arg1 == 'pending' and arg2 == 'id'
            and database == 'main' and source is None):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_TRANSACTION and arg1 in ('BEGIN', 'ROLLBACK'):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _clock(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 < value < 10**11


def probe(db, event_uuid):
    """Return pending existence and observation time; never read pending body."""
    try:
        if type(db) is not sqlite3.Connection or type(event_uuid) is not str or len(event_uuid) != 36:
            raise ValueError('input')
        db.row_factory = row_budget.factory('observer')
        if str(uuid.UUID(event_uuid)) != event_uuid:
            raise ValueError('event')
        if not hasattr(db, 'setlimit') or not hasattr(db, 'getlimit') or not hasattr(sqlite3, 'SQLITE_LIMIT_LENGTH'):
            raise ValueError('limits')
        mono_start = time.monotonic()
        if not _clock(mono_start):
            raise ValueError('monotonic_clock')
        if any(row[1] not in ('main', 'temp') for row in db.execute('pragma database_list')):
            raise ValueError('attached')
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1048576)
        if db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) > 1048576:
            raise ValueError('limits')
        deadline = mono_start + 20
        db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        db.execute('pragma query_only=on')
        db.execute('pragma trusted_schema=off')
        if db.execute('pragma trusted_schema').fetchall() != [(0,)]:
            raise ValueError('trusted_schema')
        start = time.time()
        if not _clock(start):
            raise ValueError('clock')
        db.execute('begin')
        try:
            # Validate the table and read the selected row in the SAME SQLite
            # snapshot. A prior transaction-free schema check allowed a
            # concurrent replacement between validation and row access.
            # Reject views, virtual/shadow tables, generated/hidden columns,
            # WITHOUT ROWID and STRICT variants, or a changed documented shape.
            if db.execute("pragma main.table_list('pending')").fetchall() != [('main', 'pending', 'table', 5, 0, 0)]:
                raise ValueError('schema_type')
            if tuple(db.execute("pragma main.table_xinfo('pending')").fetchall()) != _PENDING_COLUMNS:
                raise ValueError('schema_columns')
            journal_mode = db.execute('pragma main.journal_mode').fetchone()
            if journal_mode not in (('delete',), ('wal',)):
                raise ValueError('journal_mode_unavailable')
            db.set_authorizer(_authorize)
            found = db.execute('select id from main.pending where id collate binary=? limit 2', (event_uuid,)).fetchmany(2)
        finally:
            db.rollback()
        end = time.time()
        mono_end = time.monotonic()
        if not (_clock(start) and _clock(end) and start <= end and _clock(mono_end)
                and mono_start <= mono_end <= deadline and len(found) <= 1):
            raise ValueError('clock_or_ambiguity')
        if found and (len(found[0]) != 1 or found[0][0] != event_uuid):
            raise ValueError('event')
        return {'status': 'ok', 'pending': 'present' if found else 'absent',
                'observed_at': end, 'observation_start': start, 'journal_mode':journal_mode[0]}
    except Exception:
        return {'status': 'refused', 'code': 'observer_query_failed'}
    finally:
        if type(db) is sqlite3.Connection:
            try:
                db.set_progress_handler(None, 0)
            except Exception:
                pass
